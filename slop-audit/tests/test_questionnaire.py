"""The human study's per-website questions: the frozen wording, the audit section, its checks, the report, and the CSVs."""

import copy
import csv
import json

import pytest

import _lib
import expand_generic
import expand_prompt
import export_study_csv
import questionnaire as Q
import render_report
import sync_study_questions
import validate_audit
from conftest import BUNDLES, SKILL, codes, load

EX = SKILL / "examples"
STUDY = Q.load()
FEATURES = [f["value"] for f in STUDY["features"]]


@pytest.fixture
def pc():
    """A fresh copy of the placeholder-caption example audit (it has a full questionnaire) and its bundle."""
    return copy.deepcopy(load(EX / "audits/placeholder-caption.audit.json")), EX / "bundles/placeholder-caption"


def answers(audit):
    return audit["study_questionnaire"]["answers"]


# --- the frozen wording -------------------------------------------------------

def test_frozen_questions_are_the_ten_answered_items_in_study_order():
    assert Q.question_ids() == sync_study_questions.ANSWERED
    assert STUDY["questionnaire_version"] == "phd-reviewer-v1"
    assert {x["id"] for x in STUDY["not_answered"]} == set(sync_study_questions.NOT_ANSWERED)
    q = {x["id"]: x for x in STUDY["questions"]}
    assert q["ai_extent"]["prompt"] == "How much of this site did AI build?"
    assert q["feature_rating"]["min"] == 0 and q["feature_rating"]["max"] == 10 and q["feature_rating"]["allow_na"]
    assert len(FEATURES) == 10 and STUDY["source"]["pull_request"] == 6


def test_sync_copies_questions_word_for_word(tmp_path):
    source = {"version": STUDY["questionnaire_version"], "option_lists": {"features": STUDY["features"]},
              "questions": STUDY["questions"] + [{"id": x["id"], "type": "single", "prompt": x["prompt"], "options": []}
                                                 for x in STUDY["not_answered"]]}
    path = tmp_path / "questions.json"
    path.write_text(json.dumps(source), encoding="utf-8")
    built = sync_study_questions.build(path, dict(STUDY["source"]))
    assert built["questions"] == STUDY["questions"] and built["features"] == STUDY["features"]
    source["questions"].append({"id": "brand_new", "type": "scale", "prompt": "New?"})
    path.write_text(json.dumps(source), encoding="utf-8")
    with pytest.raises(_lib.UsageError, match="brand_new"):
        sync_study_questions.build(path, dict(STUDY["source"]))


def test_schema_enums_match_the_frozen_questions():
    d = _lib.load_schema("audit.schema.json")["$defs"]
    props = d["study_questionnaire"]["properties"]["answers"]["properties"]
    assert list(props) == Q.question_ids()
    assert d["study_mark"]["properties"]["kind"]["enum"] == STUDY["mark_kinds"]
    assert props["feature_rating"]["properties"]["value"]["required"] == FEATURES
    for q in STUDY["questions"]:
        value = props[q["id"]]["properties"]["value"]
        if q["type"] == "single":
            assert [v for v in value["enum"] if v is not None] == [o["value"] for o in Q.options(q, STUDY)]
        if q["type"] == "scale":
            assert (value["minimum"], value["maximum"]) == (q["min"], q["max"])


# --- the audit section and its checks ---------------------------------------

def test_examples_answer_every_question_and_old_audits_stay_valid():
    for name in ("placeholder-caption", "clean-docs"):
        report = validate_audit.validate(load(EX / f"audits/{name}.audit.json"), EX / f"bundles/{name}")
        assert report.ok and not report.warnings, report.errors + report.warnings
    legacy = validate_audit.validate(load(SKILL.parent / "fixtures/audits/scenario-inconsistency.audit.json"),
                                     BUNDLES / "scenario-inconsistency")
    assert legacy.ok and [w[0] for w in legacy.warnings] == ["questionnaire_missing"]


def mark(audit):
    return answers(audit)["ai_marks"]["value"][0]


@pytest.mark.parametrize("mutate,code", [
    (lambda a: mark(a).update(selector="#not-captured"), "fabricated_selector"),
    (lambda a: mark(a).update(page="/other.html"), "unknown_route"),
    (lambda a: mark(a).update(mark_number=5), "questionnaire_marks"),
    (lambda a: mark(a).update(element_id="D999"), "missing_element_ref"),
    (lambda a: mark(a).update(element_id="D010"), "element_selector_mismatch"),
    (lambda a: answers(a)["top_ai_feature"].update(value="layout"), "top_feature_inconsistent"),
    (lambda a: answers(a)["top_ai_feature"].update(value="gradients"), "top_feature_inconsistent"),
    (lambda a: answers(a)["quality"]["refs"].append({"kind": "finding", "id": "F999"}), "missing_questionnaire_ref"),
    (lambda a: answers(a)["polish"]["refs"].append({"kind": "screenshot", "id": "A99"}), "missing_questionnaire_ref"),
    (lambda a: answers(a)["feature_rating"]["rows"].__setitem__(1, dict(answers(a)["feature_rating"]["rows"][0])), "questionnaire_rows"),
    (lambda a: a["study_questionnaire"].update(questionnaire_version="phd-v0"), "questionnaire_version_mismatch"),
    (lambda a: answers(a)["ai_appearance"].update(value=6), "schema"),
    (lambda a: answers(a)["ai_appearance"].update(value="na"), "schema"),
    (lambda a: answers(a)["ai_extent"].update(value="half"), "schema"),
    (lambda a: answers(a)["feature_rating"]["value"].update(charts=11), "schema"),
    (lambda a: answers(a)["feature_rating"]["value"].pop("charts"), "schema"),
    (lambda a: answers(a)["technical_issue"].update(value=None), "schema"),
    (lambda a: answers(a).pop("polish"), "schema"),
])
def test_each_invalid_questionnaire_fails_with_its_code(pc, mutate, code):
    audit, bundle = pc
    mutate(audit)
    report = validate_audit.validate(audit, bundle)
    assert code in codes(report), report.errors


def test_na_and_unassessed_are_different_values(pc):
    audit, bundle = pc
    answers(audit)["feature_rating"]["value"]["charts"] = None      # unassessed, with its reason
    answers(audit)["top_ai_feature"]["value"] = "writing"
    answers(audit)["polish"]["value"] = None
    assert validate_audit.validate(audit, bundle).ok


def test_top_feature_none_with_a_high_rating_is_flagged(pc):
    audit, bundle = pc
    answers(audit)["top_ai_feature"]["value"] = "none"
    answers(audit)["feature_rating"]["value"]["writing"] = 8
    report = validate_audit.validate(audit, bundle)
    assert report.ok and "top_feature_inconsistent" in {w[0] for w in report.warnings}


def test_technical_issue_must_match_what_the_capture_recorded(pc, tmp_path):
    import shutil
    audit, bundle = pc
    broken = tmp_path / "bundle"
    shutil.copytree(bundle, broken)
    m = load(broken / "manifest.json")
    m["states"][0]["load_status"] = "partial"
    (broken / "manifest.json").write_text(json.dumps(m), encoding="utf-8")
    report = validate_audit.validate(audit, broken)          # bundle_mismatch too, but the warning is still raised
    assert "technical_issue_understated" in {w[0] for w in report.warnings}
    answers(audit)["technical_issue"]["value"] = "unable"
    report = validate_audit.validate(audit, bundle)
    assert "technical_issue_overstated" in {w[0] for w in report.warnings}


def test_text_only_answers_cannot_cite_screenshots(pc):
    audit, bundle = pc
    audit["analysis_profile"] = "text-only-datastory"
    assert "modality_unavailable" in codes(validate_audit.validate(audit, bundle))


def test_probability_language_in_answers_is_flagged(pc):
    audit, bundle = pc
    answers(audit)["ai_extent"]["reason"] = "There is a 90% chance this was AI-generated."
    assert "possible_authorship_claim" in {w[0] for w in validate_audit.validate(audit, bundle).warnings}


# --- report, prompt, CSV ----------------------------------------------------------------

def test_reports_show_the_answers_and_note_their_absence(tmp_path):
    out = tmp_path / "r.html"
    render_report.main([str(EX / "audits/placeholder-caption.audit.json"), "--bundle", str(EX / "bundles/placeholder-caption"), "--out", str(out)])
    html = out.read_text(encoding="utf-8")
    assert "Study questionnaire" in html and "How much of this site did AI build?" in html and "A little" in html
    md = tmp_path / "r.md"
    render_report.main([str(EX / "audits/clean-docs.audit.json"), "--bundle", str(EX / "bundles/clean-docs"), "--out", str(md)])
    text = md.read_text(encoding="utf-8")
    assert "| How good is this project overall? |" in text and "| Gradients | NA |" in text
    legacy = tmp_path / "l.md"
    render_report.main([str(SKILL.parent / "fixtures/audits/scenario-inconsistency.audit.json"), "--bundle",
                        str(BUNDLES / "scenario-inconsistency"), "--out", str(legacy)])
    assert "predates them" in legacy.read_text(encoding="utf-8")


def test_skill_prompt_carries_the_verbatim_questions_and_baselines_do_not(tmp_path):
    lock = expand_prompt.build_package(EX / "bundles/placeholder-caption", "multimodal-datastory", tmp_path / "skill")
    prompt = (tmp_path / "skill/prompt.md").read_text(encoding="utf-8")
    for q in STUDY["questions"]:
        assert q["prompt"] in prompt
    assert "Also fill study_questionnaire" in prompt
    assert "website-slop-audit/assets/study-questions.json" in lock["input_file_sha256"]
    expand_prompt.build_package(EX / "bundles/placeholder-caption", "multimodal-datastory", tmp_path / "generic",
                                condition="generic-prompt", instructions=expand_generic.instructions("multimodal-datastory"))
    generic = (tmp_path / "generic/prompt.md").read_text(encoding="utf-8")
    assert "study_questionnaire" not in generic.split("## Part 3")[0] and "Also fill study_questionnaire" not in generic


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_csv_export_uses_the_study_columns_and_appends_sites(tmp_path):
    out = tmp_path / "csv"
    export_study_csv.export(EX / "audits/placeholder-caption.audit.json", EX / "bundles/placeholder-caption", out,
                            site_id="placeholder", rater="test/model")
    export_study_csv.export(EX / "audits/clean-docs.audit.json", EX / "bundles/clean-docs", out, site_id="docs",
                            rater="test/model", append=True)
    wide = read_csv(out / "responses_wide.csv")
    assert list(wide[0])[:10] == export_study_csv.LEAD
    assert [c for c in wide[0] if c.startswith("feature_rating__")] == [f"feature_rating__{f}" for f in FEATURES]
    first, second = wide
    assert first["ai_appearance"] == "3" and first["ai_extent"] == "a_little" and first["feature_rating__gradients"] == "NA"
    assert first["ai_marks"].startswith("1. Text: Lorem ipsum") and first["ai_marks__count"] == "2"
    assert second["ai_marks"] == "none" and second["ai_marks__count"] == "0" and second["questions_version"] == "phd-reviewer-v1"
    assert {r["participant_id"] for r in wide} == {"website-slop-audit:test/model"}
    marks = read_csv(out / "marks.csv")
    assert list(marks[0]) == export_study_csv.MARK_COLUMNS and [m["selector"] for m in marks] == ["#chart-caption", "#stat-strip > div:nth-of-type(2) > b"]
    assert marks[0]["page"] == ""                                            # the site's first page, as in the study export
    reasons = read_csv(out / "questionnaire_reasons.csv")
    assert {r["question_id"] for r in reasons} == set(Q.question_ids())
    assert sum(1 for r in reasons if r["question_id"] == "feature_rating" and r["item"]) == 20   # ten features per site


def test_csv_export_refuses_invalid_or_unanswered_audits(tmp_path, pc):
    audit, bundle = pc
    answers(audit)["top_ai_feature"]["value"] = "layout"
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(audit), encoding="utf-8")
    with pytest.raises(_lib.UsageError, match="does not validate"):
        export_study_csv.export(bad, bundle, tmp_path / "out")
    with pytest.raises(_lib.UsageError, match="no study_questionnaire"):
        export_study_csv.export(SKILL.parent / "fixtures/audits/scenario-inconsistency.audit.json",
                                BUNDLES / "scenario-inconsistency", tmp_path / "out")
