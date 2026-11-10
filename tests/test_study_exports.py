import csv
import io
import json
import sys
from dataclasses import asdict, replace

import pytest

from aiornot.config import load_sites
from aiornot.db import Database
from aiornot.export import Exporter
from aiornot.questions import load_questions


def saved_visit(paths, **metadata):
    db = Database(paths.db_file)
    # Populate stored metadata independently of assignment and onboarding.
    sid = db.create_session("P01", False, ["beta", "alpha"], "questions-old", "sites-old")
    if metadata:
        with db.connect() as conn:
            for key, value in metadata.items():
                if isinstance(value, dict):
                    value = json.dumps(value)
                conn.execute(f"UPDATE sessions SET {key} = ? WHERE id = ?", (value, sid))
    db.mark_opened(sid, "beta")
    db.save_answers(sid, "beta", {"ai_appearance": 4})
    db.complete_site(sid, "beta")
    return Exporter(db, load_sites(paths), load_questions(paths)), sid


@pytest.mark.parametrize("name", ["responses_long", "responses_wide", "sessions", "site_visits"])
def test_each_data_export_carries_audience_and_config_versions(paths, name):
    exporter, _ = saved_visit(paths, cohort="agentic_internship", dsc106_completed=True)
    columns, rows = exporter.table(name)
    for field, value in {
        "cohort": "agentic_internship", "dsc106_completed": True,
        "questions_version": "questions-old", "sites_version": "sites-old",
    }.items():
        assert field in columns
        assert rows[0][field] == value
    if name != "sessions":
        assert rows[0]["site_position"] == 1
        assert rows[0]["site_id"] == "beta"
        assert rows[0]["site_commit"] == "abc1234"


def test_historical_sites_and_question_types_survive_config_changes(paths):
    sites = load_sites(paths)
    snapshot = {"version": "old", "questions": [
        {"id": "old_boolean", "type": "boolean", "prompt": "Old question"},
        {"id": "old_cues", "type": "multi", "prompt": "Old cues", "options": [
            {"value": "old_option", "label": "Former option"},
            {"value": "unselected", "label": "Not selected"},
        ]},
    ]}
    exporter, sid = saved_visit(paths, questions_snapshot=snapshot,
                                sites_snapshot={"beta": asdict(sites.pool["beta"])})
    exporter.db.save_answers(sid, "beta", {"old_boolean": False, "old_cues": ["old_option"]})
    exporter.sites = replace(sites, pool={"alpha": sites.pool["alpha"]}, study=[sites.pool["alpha"]])

    columns, wide = exporter.table("responses_wide")
    assert wide[0]["site_title"] == "Site beta"
    assert wide[0]["site_commit"] == "abc1234"
    assert wide[0]["old_boolean"] == "FALSE"
    assert wide[0]["old_cues__old_option"] == 1
    assert wide[0]["old_cues__unselected"] == 0
    assert "old_cues__old_option" in columns
    _, long = exporter.table("responses_long")
    answers = {r["question_id"]: r for r in long}
    assert answers["old_boolean"]["question_type"] == "boolean"
    assert answers["old_boolean"]["value"] == "FALSE"


def test_project_manifest_keeps_historical_commits_for_external_creator_join(paths):
    sites = load_sites(paths)
    old = {**asdict(sites.pool["beta"]), "commit": "old-commit", "title": "Earlier beta"}
    exporter, _ = saved_visit(paths, sites_snapshot={"beta": old})
    projects = list(csv.DictReader(io.StringIO(exporter.csv("projects"))))
    rows = {(r["site_id"], r["site_commit"]): r for r in projects}
    assert ("beta", "abc1234") in rows
    assert rows[("beta", "old-commit")]["site_title"] == "Earlier beta"
    assert rows[("beta", "old-commit")]["repo"] == "example/beta"
    assert rows[("beta", "old-commit")]["url"] == "https://example.github.io/beta/"


def test_legacy_sessions_export_without_inventing_cohort_or_course_background(paths):
    exporter, _ = saved_visit(paths)
    _, rows = exporter.table("responses_wide")
    assert rows[0]["cohort"] == "unclassified"
    assert rows[0]["dsc106_completed"] is None
    assert rows[0]["site_commit"] == "abc1234"


@pytest.mark.parametrize("appearance", [True, False])
def test_summary_groups_by_project_and_cohort_with_available_questions(monkeypatch, capsys, appearance):
    pd = pytest.importorskip("pandas")
    from analysis import summary

    outcome = {"ai_appearance": 4} if appearance else {"ai_generated": "TRUE"}
    wide = pd.DataFrame([
        {"participant_id": "P01", "site_id": "beta", "site_title": "Site beta",
         "site_position": 1, "cohort": "dsc106", "completed_at": "2026-10-22",
         "seconds_on_site": 240, **outcome},
        {"participant_id": "P02", "site_id": "beta", "site_title": "Site beta",
         "site_position": 3, "cohort": "dsc106", "completed_at": "2026-10-22",
         "seconds_on_site": 180, **outcome},
    ])
    monkeypatch.setattr(summary, "load", lambda **_: {
        "responses_wide": wide,
        "sessions": pd.DataFrame([{"participant_id": "P01", "finished_at": "2026-10-22"}]),
    })
    monkeypatch.setattr(sys, "argv", ["summary"])
    summary.main()
    output = capsys.readouterr().out
    assert "site_id" in output and "cohort" in output
    assert output.count("Site beta") == 1
    assert "mean_ai_appearance" in output if appearance else "pct_judged_ai" in output
    assert "mean_confidence" not in output
    assert "mean_polish" not in output


def test_exports_distinguish_random_followup_selection_and_separate_timing(paths):
    exporter, sid = saved_visit(paths)
    with exporter.db.connect() as conn:
        conn.execute("UPDATE sessions SET followup_order = ? WHERE id = ?", ('["beta"]', sid))
    exporter.db.start_followup(sid)
    exporter.db.mark_opened(sid, "beta", phase="followup")
    exporter.db.add_time(sid, "beta", 32, phase="followup")
    exporter.db.complete_site(sid, "beta", phase="followup")
    for name in ("responses_wide", "responses_long", "site_visits"):
        _, rows = exporter.table(name)
        assert rows[0]["followup_position"] == 1
    _, visits = exporter.table("site_visits")
    assert visits[0]["followup_seconds_on_site"] == 32
    assert visits[0]["seconds_on_site"] == 0
    assert visits[0]["followup_opened_at"]
    assert visits[0]["followup_completed_at"]
    _, sessions = exporter.table("sessions")
    assert sessions[0]["followup_order"] == '["beta"]'
    assert sessions[0]["followup_started_at"]
    assert sessions[0]["sites_assigned"] == 2


def test_summary_excludes_unable_review_from_appearance_average(monkeypatch, capsys):
    pd = pytest.importorskip("pandas")
    from analysis import summary

    wide = pd.DataFrame([
        {"participant_id": "P01", "site_id": "beta", "site_title": "Site beta",
         "cohort": "dsc106", "completed_at": "done", "seconds_on_site": 240,
         "ai_appearance": 4, "technical_issue": "unable"},
        {"participant_id": "P02", "site_id": "beta", "site_title": "Site beta",
         "cohort": "dsc106", "completed_at": "done", "seconds_on_site": 180,
         "ai_appearance": 2, "technical_issue": "no"},
    ])
    monkeypatch.setattr(summary, "load", lambda **_: {
        "responses_wide": wide,
        "sessions": pd.DataFrame([{"participant_id": "P01", "finished_at": "done"}]),
    })
    monkeypatch.setattr(sys, "argv", ["summary"])
    summary.main()
    row = next(line for line in capsys.readouterr().out.splitlines() if "Site beta" in line)
    assert float(row.split()[-1]) == 2.0
    assert wide.loc[0, "ai_appearance"] == 4
