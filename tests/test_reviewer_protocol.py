import json

import pytest
from fastapi.testclient import TestClient

from aiornot.app import create_app
from aiornot.config import ROOT


@pytest.fixture
def study(paths):
    raw = {
        "version": "review-test",
        "questions": [
            {"id": "ai_appearance", "type": "scale", "prompt": "Appearance", "min": 1, "max": 5,
             "required_unless": {"question_id": "technical_issue", "value": "unable"}},
            {"id": "seen_before", "type": "single", "prompt": "Familiar?",
             "options": ["no", "yes_seen", "yes_made"]},
            {"id": "technical_issue", "type": "single", "prompt": "Technical problem?", "options": ["no", "unable"]},
            {"id": "cues", "type": "multi", "phase": "followup", "prompt": "Cues",
             "max_selected": 2, "options": ["writing", "charts", "layout"]},
            {"id": "example", "type": "text", "phase": "followup", "prompt": "Example",
             "required": False, "max_length": 100},
            {"id": "annotations", "type": "annotation", "phase": "followup", "prompt": "Annotate", "required": False},
        ],
    }
    (paths.config_dir / "questions.json").write_text(json.dumps(raw))
    with TestClient(create_app(paths, start_sync=False)) as client:
        yield client


def start(study, **extra):
    res = study.post("/api/sessions", json={"participant_id": "P01", "cohort": "dsc106", **extra})
    assert res.status_code == 201, res.text
    return res.json()["id"]


def review_all(study, sid):
    data = study.get(f"/api/sessions/{sid}").json()
    for site in data["sites"]:
        base = f"/api/sessions/{sid}/sites/{site['id']}"
        assert study.put(base + "/answers", json={"answers": {
            "ai_appearance": 3, "seen_before": "no", "technical_issue": "no"}}).status_code == 200
        assert study.post(base + "/complete").status_code == 200
    return data


def test_group_is_required_and_internship_course_background_is_recorded(study):
    assert study.post("/api/sessions", json={"participant_id": "missing"}).status_code == 422
    assert study.post("/api/sessions", json={"participant_id": "x", "cohort": "other"}).status_code == 422
    assert study.post("/api/sessions", json={"participant_id": "x", "cohort": "agentic_internship"}).status_code == 422
    sid = start(study, cohort="agentic_internship", dsc106_completed=False)
    session = study.get(f"/api/sessions/{sid}").json()["session"]
    assert session["cohort"] == "agentic_internship"
    assert session["dsc106_completed"] is False


def test_followups_are_hidden_until_primary_ratings_are_complete_and_then_lock_them(study):
    sid = start(study)
    data = study.get(f"/api/sessions/{sid}").json()
    assert data["phase"] == "review"
    assert [q["id"] for q in data["questions"]] == ["ai_appearance", "seen_before", "technical_issue"]
    assert data["followup_questions"] == []
    site = data["sites"][0]["id"]
    assert study.put(f"/api/sessions/{sid}/sites/{site}/answers", json={"answers": {"cues": ["writing"]}}).status_code == 409
    assert study.post(f"/api/sessions/{sid}/followup").status_code == 409
    review_all(study, sid)
    assert study.post(f"/api/sessions/{sid}/finish").status_code == 409
    assert study.post(f"/api/sessions/{sid}/followup").status_code == 200
    data = study.get(f"/api/sessions/{sid}").json()
    assert data["phase"] == "followup"
    assert len(data["followup_sites"]) == 2
    assert [q["id"] for q in data["questions"]] == ["cues", "example", "annotations"]
    assert study.put(f"/api/sessions/{sid}/sites/{site}/answers", json={"answers": {"ai_appearance": 5}}).status_code == 409
    assert study.post(f"/api/sessions/{sid}/finish").status_code == 422
    for item in data["followup_sites"]:
        base = f"/api/sessions/{sid}/sites/{item['id']}"
        assert study.put(base + "/answers", json={"answers": {"cues": ["charts"], "example": "The chart labels."}}).status_code == 200
        assert study.post(base + "/complete").status_code == 200
    assert study.post(f"/api/sessions/{sid}/finish").status_code == 200


def test_invalid_followup_answers_are_not_saved(study):
    sid = start(study)
    review_all(study, sid)
    study.post(f"/api/sessions/{sid}/followup")
    site = study.get(f"/api/sessions/{sid}").json()["followup_sites"][0]["id"]
    url = f"/api/sessions/{sid}/sites/{site}/answers"
    for answers in ({"cues": ["writing", "charts", "layout"]}, {"example": "x" * 101}, {"example": 5}):
        assert study.put(url, json={"answers": answers}).status_code == 422


def test_saved_survey_and_project_definitions_survive_config_changes(study, paths):
    sid = start(study)
    original = study.get(f"/api/sessions/{sid}").json()
    raw = json.loads((paths.config_dir / "questions.json").read_text())
    raw["questions"][0]["prompt"] = "Changed question"
    (paths.config_dir / "questions.json").write_text(json.dumps(raw))
    raw_sites = json.loads((paths.config_dir / "sites.json").read_text())
    raw_sites["study_sites"] = ["alpha"]
    raw_sites["pool"] = [raw_sites["pool"][0]]
    (paths.config_dir / "sites.json").write_text(json.dumps(raw_sites))
    with TestClient(create_app(paths, start_sync=False)) as restarted:
        data = restarted.get(f"/api/sessions/{sid}").json()
        assert data["session"]["site_order"] == original["session"]["site_order"]
        assert data["questions"][0]["prompt"] == "Appearance"
        review_all(restarted, sid)


def test_cue_help_changes_only_new_session_snapshots(paths):
    current = json.loads((ROOT / "config" / "questions.json").read_text())
    previous = json.loads(json.dumps(current))
    old_help = "Select up to three. Your earlier rating is already saved."
    next(q for q in previous["questions"] if q["id"] == "cues")["help"] = old_help
    config = paths.config_dir / "questions.json"
    config.write_text(json.dumps(previous))
    with TestClient(create_app(paths, start_sync=False)) as original:
        sid = start(original)
        review_all(original, sid)
        assert original.post(f"/api/sessions/{sid}/followup").status_code == 200
        original_data = original.get(f"/api/sessions/{sid}").json()
        original_version = original_data["session"]["questions_version"]

    config.write_text(json.dumps(current))
    with TestClient(create_app(paths, start_sync=False)) as restarted:
        resumed = restarted.get(f"/api/sessions/{sid}").json()
        assert next(q for q in resumed["followup_questions"] if q["id"] == "cues")["help"] == old_help
        assert resumed["session"]["questions_version"] == original_version
        new_sid = start(restarted, participant_id="P02")
        review_all(restarted, new_sid)
        assert restarted.post(f"/api/sessions/{new_sid}/followup").status_code == 200
        created = restarted.get(f"/api/sessions/{new_sid}").json()
        assert next(q for q in created["followup_questions"] if q["id"] == "cues")["help"] == (
            "Select 1–3 cues. Your earlier rating is already saved."
        )
        assert created["session"]["questions_version"] != original_version
        assert resumed["config_changed"] is True
        assert created["config_changed"] is False


def test_late_review_time_stays_separate_from_followup_time(study):
    sid = start(study)
    data = review_all(study, sid)
    study.post(f"/api/sessions/{sid}/followup")
    site = data["sites"][0]["id"]
    assert study.post(f"/api/sessions/{sid}/sites/{site}/time", json={"seconds": 15, "phase": "review"}).status_code == 200
    followup_site = study.get(f"/api/sessions/{sid}").json()["followup_sites"][0]["id"]
    assert study.post(f"/api/sessions/{sid}/sites/{followup_site}/time", json={"seconds": 8, "phase": "followup"}).status_code == 200
    visits = {v["site_id"]: v for v in study.app.state.db.visits(sid)}
    assert visits[site]["seconds_on_site"] == 15
    assert visits[followup_site]["followup_seconds_on_site"] == 8


def test_unviewable_page_can_be_completed_without_inventing_a_rating(study):
    sid = start(study)
    site = study.get(f"/api/sessions/{sid}").json()["sites"][0]["id"]
    base = f"/api/sessions/{sid}/sites/{site}"
    response = study.put(base + "/answers", json={"answers": {"seen_before": "no", "technical_issue": "unable"}})
    assert response.status_code == 200
    assert response.json()["missing"] == []
    assert study.post(base + "/complete").status_code == 200


def test_resume_rejects_replaced_project_files(study, paths):
    sid = start(study)
    (paths.mirror_dir / "alpha" / ".mirrored-commit").write_text("different-commit")
    response = study.get(f"/api/sessions/{sid}")
    assert response.status_code == 409
    assert "frozen" in response.json()["detail"]


@pytest.mark.parametrize("path", ["/sites/other/chart.html", "/sites/{site}/../other/", "/sites/{site}/%2e%2e/other/"])
def test_annotation_must_belong_to_its_assigned_project(study, path):
    sid = start(study)
    review_all(study, sid)
    study.post(f"/api/sessions/{sid}/followup")
    site = study.get(f"/api/sessions/{sid}").json()["followup_sites"][0]["id"]
    entry = {"id": "note-1", "page_path": path.format(site=site), "selector": "h1", "quote": "Title", "rect": {"x": 0, "y": 0, "width": 100, "height": 50}, "viewport": {"width": 900, "height": 700}, "note": "A specific detail."}
    response = study.put(f"/api/sessions/{sid}/sites/{site}/answers", json={"answers": {"annotations": [entry]}})
    assert response.status_code == 422
