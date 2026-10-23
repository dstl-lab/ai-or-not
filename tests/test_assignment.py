import json
import sqlite3
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import pytest

from aiornot.config import ConfigError, load_sites
from aiornot.db import Database

COHORTS = ("lower_division", "dsc106", "agentic_internship")


def allocate(db, participant, site_ids, **kwargs):
    return db.create_session(participant, False, site_ids, "questions-v1", "sites-v1",
                             cohort="lower_division", sites_per_session=10, **kwargs)


def test_session_count_is_separate_from_active_project_pool(paths):
    raw = json.loads((paths.config_dir / "sites.json").read_text())
    for index in range(12):
        raw["pool"].append({**raw["pool"][0], "id": f"project-{index}"})
        raw["study_sites"].append(f"project-{index}")
    (paths.config_dir / "sites.json").write_text(json.dumps(raw))
    config = load_sites(paths)
    assert config.sites_per_session == 10
    assert len(config.study) == 15
    raw["sites_per_session"] = 6
    (paths.config_dir / "sites.json").write_text(json.dumps(raw))
    changed = load_sites(paths)
    assert changed.sites_per_session == 6
    assert changed.version != config.version


@pytest.mark.parametrize("bad", [True, False, 0, 11, 2.5, "10", None])
def test_invalid_session_counts_are_rejected(paths, bad):
    raw = json.loads((paths.config_dir / "sites.json").read_text())
    raw["sites_per_session"] = bad
    (paths.config_dir / "sites.json").write_text(json.dumps(raw))
    with pytest.raises(ConfigError, match="sites_per_session"):
        load_sites(paths)


def test_assignments_are_balanced_within_each_cohort(tmp_path):
    db = Database(tmp_path / "study.db")
    projects = [f"p{index}" for index in range(69)]
    for cohort in COHORTS:
        for index in range(69):
            sid = db.create_session(f"{cohort}-{index}", False, projects, "q", "s",
                                    cohort=cohort, sites_per_session=10)
            order = db.get_session(sid)["site_order"]
            assert len(order) == len(set(order)) == 10
    coverage = db.coverage(projects)
    assert len(coverage) == 69 * 3
    assert {row["assigned"] for row in coverage} == {10}
    assert {row["completed"] for row in coverage} == {0}
    assert {row["cohort"] for row in coverage} == set(COHORTS)


def test_assignment_respects_exclusions_and_does_not_reassign_on_resume(tmp_path):
    db = Database(tmp_path / "study.db")
    questions = {"version": "questions-v1", "questions": [{"id": "ai_appearance"}]}
    sites = {"p1": {"id": "p1", "commit": "abc123"}}
    sid = allocate(db, "P1", [f"p{i}" for i in range(12)],
                   excluded_site_ids=["p0", "p11"], followup_count=2,
                   dsc106_completed=False, questions_snapshot=questions, sites_snapshot=sites)
    assigned = db.get_session(sid)
    assert set(assigned["site_order"]) == {f"p{i}" for i in range(1, 11)}
    assert len(assigned["followup_order"]) == 2
    assert set(assigned["followup_order"]) <= set(assigned["site_order"])
    assert assigned["dsc106_completed"] is False
    assert assigned["questions_snapshot"] == questions
    assert assigned["sites_snapshot"] == sites
    assert assigned["cohort"] == "lower_division"
    allocate(db, "P2", [f"p{i}" for i in range(12)])
    assert db.get_session(sid) == assigned
    assert len(db.visits(sid)) == 10
    db.start_followup(sid)
    started = db.get_session(sid)["followup_started_at"]
    assert started
    db.start_followup(sid)
    assert db.get_session(sid)["followup_started_at"] == started
    assert next(row for row in db.list_sessions() if row["id"] == sid)["sites_assigned"] == 10


def test_insufficient_eligible_projects_does_not_leave_a_partial_session(tmp_path):
    db = Database(tmp_path / "study.db")
    with pytest.raises(ValueError, match="eligible"):
        allocate(db, "P1", [f"p{i}" for i in range(10)], excluded_site_ids=["p0"])
    assert db.list_sessions() == []


def test_practice_and_other_cohorts_do_not_consume_group_assignments(tmp_path):
    db = Database(tmp_path / "study.db")
    db.create_session("practice", True, ["a", "b"], "q", "s", cohort="lower_division")
    db.create_session("other", False, ["a", "b"], "q", "s", cohort="dsc106")
    db.create_session("same", False, ["a", "b"], "q", "s", cohort="lower_division")
    sid = db.create_session("new", False, ["a", "b", "c", "d"], "q", "s",
                           cohort="lower_division", sites_per_session=2)
    assert set(db.get_session(sid)["site_order"]) == {"c", "d"}
    db.complete_site(sid, "c")
    coverage = {(r["site_id"], r["cohort"]): r for r in db.coverage(["a", "b", "c", "d"])}
    assert coverage["a", "lower_division"]["assigned"] == 1
    assert coverage["c", "lower_division"]["completed"] == 1
    assert coverage["a", "dsc106"]["assigned"] == 1
    assert coverage["a", "agentic_internship"]["assigned"] == 0


def test_parallel_allocations_balance_without_double_booking(tmp_path):
    db = Database(tmp_path / "study.db")
    projects = [f"p{i}" for i in range(20)]
    with ThreadPoolExecutor(max_workers=4) as executor:
        ids = list(executor.map(lambda i: allocate(db, f"P{i}", projects), range(20)))
    assert len(set(ids)) == 20
    assigned = [row["assigned"] for row in db.coverage(projects)
                if row["cohort"] == "lower_division"]
    assert set(assigned) == {10}


def test_position_balancing_avoids_repeated_fixed_order(tmp_path):
    db = Database(tmp_path / "study.db")
    projects = [f"p{i}" for i in range(10)]
    for index in range(10):
        allocate(db, f"P{index}", projects)
    first_positions = Counter(row["site_id"] for row in db.export_rows(
        "SELECT site_id FROM site_visits WHERE position = 1"))
    assert first_positions == {project: 1 for project in projects}


def test_existing_database_migrates_without_losing_data(tmp_path):
    path = tmp_path / "study.db"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE sessions (id TEXT PRIMARY KEY, participant_id TEXT NOT NULL,"
                     " practice INTEGER NOT NULL DEFAULT 0, started_at TEXT NOT NULL,"
                     " finished_at TEXT, site_order TEXT NOT NULL, questions_version TEXT NOT NULL,"
                     " sites_version TEXT NOT NULL, user_agent TEXT, screen TEXT)")
        conn.execute("INSERT INTO sessions VALUES"
                     " ('old', 'P1', 0, '2026-01-01T00:00:00Z', NULL, '[\"a\", \"b\"]',"
                     " 'old-q', 'old-s', 'browser', '1920x1080')")
    db = Database(path)
    old = db.get_session("old")
    assert old["participant_id"] == "P1"
    assert old["site_order"] == ["a", "b"]
    assert old["cohort"] == "unclassified"
    assert old["dsc106_completed"] is None
    assert old["questions_snapshot"] is None
    assert old["sites_snapshot"] is None
    assert old["followup_order"] == []
    assert old["followup_started_at"] is None
    Database(path)  # migrations are repeatable
    sid = db.create_session("legacy-call", False, ["b", "a"], "q", "s")
    assert db.get_session(sid)["site_order"] == ["b", "a"]
