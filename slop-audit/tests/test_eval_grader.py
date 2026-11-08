"""The skill-creator eval grader gives known grades for known outputs."""

import json
import shutil

import _lib
import local_checks
from conftest import FIXTURES, SKILL
import sys

sys.path.insert(0, str(FIXTURES))
import grade_eval_runs  # noqa: E402

EVALS = SKILL.parent / "website-slop-audit-evals"


def run_dir(tmp_path, audit=None, report="Report."):
    d = tmp_path / "run"
    (d / "outputs").mkdir(parents=True)
    if audit is not None:
        (d / "outputs/audit.json").write_text(json.dumps(audit), encoding="utf-8")
    (d / "outputs/report.md").write_text(report, encoding="utf-8")
    return d


def test_eval_bundles_match_the_fixtures():
    for case, spec in __import__("sync_evals").CASES.items():
        a = _lib.Bundle(EVALS / case / "files/bundle")
        b = _lib.Bundle(FIXTURES / "bundles" / spec["bundle"])
        assert a.hash == b.hash, case


def test_reference_audit_passes_every_scenario_assertion(tmp_path):
    audit = json.loads((FIXTURES / "audits/scenario-inconsistency.audit.json").read_text())
    g = grade_eval_runs.grade_run("scenario-state-inconsistency", run_dir(tmp_path, audit), EVALS / "scenario-state-inconsistency/files/bundle")
    assert g["summary"]["pass_rate"] == 1.0, g["expectations"]


def test_rule_baseline_passes_the_behavior_checks_on_the_buttons_case(tmp_path):
    bundle = EVALS / "dead-vs-working-buttons/files/bundle"
    audit = local_checks.build_audit(_lib.Bundle(bundle), "multimodal-core")
    g = grade_eval_runs.grade_run("dead-vs-working-buttons", run_dir(tmp_path, audit), bundle)
    assert [e["passed"] for e in g["expectations"]] == [True, True, True, True]


def test_citing_the_working_click_as_contrast_is_not_a_failure(tmp_path):
    bundle = EVALS / "dead-vs-working-buttons/files/bundle"
    audit = local_checks.build_audit(_lib.Bundle(bundle), "multimodal-core")
    audit["findings"][0]["evidence"].append({"kind": "interaction", "ref_id": "E01", "description": "the sibling button works, so changes are detectable", "quote": None})
    g = grade_eval_runs.grade_run("dead-vs-working-buttons", run_dir(tmp_path, audit), bundle)
    assert g["expectations"][3]["passed"]
    audit["findings"][0]["evidence"] = [e for e in audit["findings"][0]["evidence"] if e["ref_id"] != "E02"]
    g = grade_eval_runs.grade_run("dead-vs-working-buttons", run_dir(tmp_path / "b", audit), bundle)
    assert not g["expectations"][3]["passed"]


def test_missing_output_fails_cleanly(tmp_path):
    g = grade_eval_runs.grade_run("catalog-no-slop-finding", run_dir(tmp_path, None), EVALS / "catalog-no-slop-finding/files/bundle")
    assert g["summary"]["passed"] == 1  # only the "no verdict" check can pass with no audit


def test_verdict_detector_ignores_negated_disclaimers():
    assert grade_eval_runs.verdict_hits("This audit gives no probability that the site was AI-generated.") == []
    assert grade_eval_runs.verdict_hits("Verdict: AI. There is an 85% chance it was generated.") != []
