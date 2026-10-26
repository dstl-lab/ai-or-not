import csv
import io
import json

import pytest

from aiornot.config import ConfigError, load_sites
from aiornot.db import Database
from aiornot.export import Exporter, display
from aiornot.questions import AnswerError, check_answer, missing_answers, parse_questions


def annotation(**updates):
    return {
        "id": "mark-1", "page_path": "/sites/alpha/index.html#chart",
        "selector": "#chart > svg", "quote": "Average temperature",
        "rect": {"x": 120.5, "y": 640, "width": 380, "height": 240},
        "viewport": {"width": 1440, "height": 900},
        "note": "The chart labels look repetitive.\nThe same phrasing appears twice.",
        **updates,
    }


def questionnaire(**updates):
    return parse_questions({"version": "annotations-v1", "questions": [{
        "id": "annotations", "type": "annotation", "phase": "followup",
        "prompt": "Point out a feature", "required": False, **updates,
    }]})


def test_annotations_roundtrip_through_snapshot_and_optional_completion():
    questions = questionnaire()
    q = questions.by_id["annotations"]
    values = [annotation(), annotation(id="mark-2", note="This part looks deliberate.")]
    check_answer(q, values, questions.by_id)
    assert missing_answers(questions, {"annotations": values}) == []
    assert missing_answers(questions, {}) == []
    check_answer(q, [], questions.by_id)
    serialized = questions.to_client()
    assert serialized[0]["max_annotations"] == 3
    restored = parse_questions({"questions": serialized})
    check_answer(restored.by_id["annotations"], values, restored.by_id)


@pytest.mark.parametrize("bad", [True, False, 0, 11, 2.5, "3", None])
def test_annotation_limit_requires_a_small_positive_integer(bad):
    with pytest.raises(ConfigError, match="max_annotations"):
        questionnaire(max_annotations=bad)


@pytest.mark.parametrize("bad", [
    {}, "not a list", ["not an annotation"],
    [annotation(), annotation()],
    [annotation(id=f"mark-{i}") for i in range(4)],
    [annotation(id="")], [annotation(id="  ")], [annotation(id="x" * 65)],
    [annotation(page_path="https://example.test/sites/alpha/")],
    [annotation(page_path="//example.test/sites/alpha/")],
    [annotation(page_path="/elsewhere/alpha/")],
    [annotation(page_path="/sites/" + "x" * 2000)],
    [annotation(selector="x" * 1001)], [annotation(selector=None)],
    [annotation(quote="x" * 301)], [annotation(quote=3)],
    [annotation(note="")], [annotation(note="  \n")],
    [annotation(note="x" * 501)], [annotation(note=False)],
    [annotation(unexpected="<script>alert(1)</script>")],
    [{key: value for key, value in annotation().items() if key != "selector"}],
    [annotation(rect={"x": 1, "y": 2, "width": 3})],
    [annotation(rect={"x": 1, "y": 2, "width": 3, "height": 4, "extra": 5})],
    [annotation(rect={"x": True, "y": 2, "width": 3, "height": 4})],
    [annotation(rect={"x": float("nan"), "y": 2, "width": 3, "height": 4})],
    [annotation(rect={"x": 1, "y": float("inf"), "width": 3, "height": 4})],
    [annotation(rect={"x": 10**9, "y": 2, "width": 3, "height": 4})],
    [annotation(rect={"x": 1, "y": 2, "width": 0, "height": 4})],
    [annotation(rect={"x": 1, "y": 2, "width": 3, "height": -1})],
    [annotation(viewport={"width": 0, "height": 900})],
    [annotation(viewport={"width": 1440, "height": float("inf")})],
    [annotation(viewport={"width": False, "height": 900})],
    [annotation(viewport={"width": 1440})],
])
def test_malformed_annotations_are_rejected(bad):
    questions = questionnaire()
    with pytest.raises(AnswerError, match="annotations"):
        check_answer(questions.by_id["annotations"], bad, questions.by_id)


def test_configured_annotation_limit_is_enforced():
    questions = questionnaire(max_annotations=1)
    with pytest.raises(AnswerError):
        check_answer(questions.by_id["annotations"], [annotation(), annotation(id="mark-2")], questions.by_id)


@pytest.mark.parametrize("region", [
    {"x": 0.2, "y": 0.3, "width": 0.4, "height": 0.5},
    {"x": 0, "y": 0, "width": 1, "height": 1},
    {"x": 0.2, "y": 0.3, "width": 0.8000005, "height": 0.7000005},
])
def test_canvas_regions_accept_normalized_bounds_and_rounding(region):
    questions = questionnaire()
    check_answer(questions.by_id["annotations"], [annotation(selector="#chart > canvas", region=region)],
                 questions.by_id)


@pytest.mark.parametrize("region", [
    None, [], {},
    {"x": 0, "y": 0, "width": 1},
    {"x": 0, "y": 0, "width": 1, "height": 1, "extra": 1},
    *[{"x": 0, "y": 0, "width": 1, "height": 1, key: bad}
      for key in ("x", "y", "width", "height")
      for bad in (True, "0.2", float("nan"), float("inf"))],
    {"x": -0.01, "y": 0, "width": 0.5, "height": 0.5},
    {"x": 0, "y": -0.01, "width": 0.5, "height": 0.5},
    {"x": 0, "y": 0, "width": 0, "height": 0.5},
    {"x": 0, "y": 0, "width": 0.5, "height": -0.1},
    {"x": 0.5, "y": 0, "width": 0.50001, "height": 1},
    {"x": 0, "y": 0.5, "width": 1, "height": 0.50001},
])
def test_invalid_canvas_regions_are_rejected(region):
    questions = questionnaire()
    with pytest.raises(AnswerError, match="annotations"):
        check_answer(questions.by_id["annotations"], [annotation(region=region)], questions.by_id)


@pytest.mark.parametrize("region", [None, {"x": 0.2, "y": 0.3, "width": 0.4, "height": 0.5}])
@pytest.mark.parametrize("styles", [None, {"font-family": "system-ui", "border-radius": "24px"}])
def test_annotation_export_survives_csv_sheet_and_config_changes(paths, region, styles):
    questions = questionnaire()
    db = Database(paths.db_file)
    sites = load_sites(paths)
    sid = db.create_session("P01", False, ["alpha"], questions.version, sites.version,
                            cohort="dsc106", questions_snapshot={"version": "saved", "questions": questions.to_client()})
    values = [annotation(note='The words "click here" feel generic; <strong>labels</strong> look copied.')]
    if region is not None:
        values[0].update(selector="#chart > canvas", region=region)
    if styles is not None:
        values[0]["styles"] = styles
    check_answer(questions.by_id["annotations"], values, questions.by_id)
    db.mark_opened(sid, "alpha")
    db.save_answers(sid, "alpha", {"annotations": values})
    db.complete_site(sid, "alpha")
    exporter = Exporter(db, sites, questions)
    assert db.answers(sid)["alpha"]["annotations"] == values
    for table in ("responses_wide", "responses_long"):
        row = list(csv.DictReader(io.StringIO(exporter.csv(table))))[0]
        assert json.loads(row["annotations"] if table == "responses_wide" else row["value"]) == values
        if table == "responses_long":
            assert json.loads(row["value_json"]) == values
            assert row["question_type"] == "annotation"
    sheet_values, _ = exporter.sheet_row(sid, "alpha", "2026-10-22T00:00:00Z")
    assert json.loads(sheet_values[exporter.sheet_columns().index("annotations")]) == values
    exporter.questions = parse_questions({"questions": [{"id": "different", "type": "text", "prompt": "New question"}]})
    historical = list(csv.DictReader(io.StringIO(exporter.csv("responses_wide"))))[0]
    assert json.loads(historical["annotations"]) == values
    db.save_answers(sid, "alpha", {"annotations": []})
    assert "annotations" not in db.answers(sid).get("alpha", {})


@pytest.mark.parametrize("styles", [
    None, [], "red", {"color": 5}, {1: "red"},
    {"x" * 81: "red"}, {"color": "x" * 301},
    {f"property-{i}": "value" for i in range(13)},
])
def test_malformed_annotation_styles_are_rejected(styles):
    questions = questionnaire()
    with pytest.raises(AnswerError, match="annotations"):
        check_answer(questions.by_id["annotations"], [annotation(styles=styles)], questions.by_id)


def test_annotation_display_handles_removed_question_definitions():
    values = [annotation()]
    assert json.loads(display(None, values)) == values
    assert display(None, ["writing", "charts"]) == "writing; charts"
