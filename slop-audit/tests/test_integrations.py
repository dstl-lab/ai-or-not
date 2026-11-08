"""Run import, report rendering, baselines, and capture-adapter helpers."""

import csv
import json
import os
import shutil

import pytest

import _lib
import critique_baseline
import expand_prompt
import gstack_capture
import impeccable_import
import import_run
import local_checks
import render_report
import validate_audit
from conftest import BUNDLES, FIXTURES, SKILL, codes, empty_audit, load

CLEAN = BUNDLES / "clean-docs"


@pytest.fixture
def pkg(tmp_path):
    out = tmp_path / "pkg"
    expand_prompt.build_package(CLEAN, "multimodal-core", out)
    return out


@pytest.mark.parametrize("raw, status", [
    (lambda a: json.dumps(a), "ok"),
    (lambda a: "Here is the audit:\n```json\n" + json.dumps(a) + "\n```\nThanks.", "json_extracted"),
    (lambda a: "I could not complete this.", "invalid_json"),
    (lambda a: "   ", "empty"),
    (lambda a: json.dumps(dict(a, status="done")), "schema_invalid"),
    (lambda a: json.dumps(dict(a, bundle_hash="0" * 64)), "integrity_invalid"),
])
def test_import_run_records_every_parse_outcome(tmp_path, pkg, raw, status):
    raw_file = tmp_path / "reply.txt"
    raw_file.write_text(raw(empty_audit(CLEAN, "multimodal-core")), encoding="utf-8")
    rec, run_dir = import_run.import_run(raw_file, pkg, CLEAN, tmp_path / "runs", "frozen-skill", "test", "m", "unit test")
    assert rec["parse_status"] == status
    assert (run_dir / "raw_output.txt").read_text(encoding="utf-8") == raw_file.read_text(encoding="utf-8")
    assert not _lib.schema_errors(rec, _lib.load_schema("run-record.schema.json"))
    with pytest.raises(_lib.UsageError, match="never overwritten"):
        import_run.import_run(raw_file, pkg, CLEAN, tmp_path / "runs", "frozen-skill", "test", "m", "unit test")


def test_report_escapes_untrusted_text_and_derives_counts(tmp_path):
    audit, bundle = load(FIXTURES / "audits/scenario-inconsistency.audit.json"), BUNDLES / "scenario-inconsistency"
    audit["findings"][0]["observation"] = '<script>alert("x")</script> summary mismatch'
    path = tmp_path / "audit.json"
    path.write_text(json.dumps(audit), encoding="utf-8")
    out = tmp_path / "r" / "report.html"
    render_report.main([str(path), "--bundle", str(bundle), "--out", str(out)])
    html = out.read_text(encoding="utf-8")
    assert "<script>" not in html and "&lt;script&gt;" in html
    assert "1 finding<" in html and "1 contextual exception<" in html
    for src in __import__("re").findall(r'<img src="([^"]+)"', html):
        assert (out.parent / src).resolve().exists()


def test_report_for_zero_findings_and_invalid_audit(tmp_path):
    audit = empty_audit(CLEAN, "multimodal-core")
    path = tmp_path / "a.json"
    path.write_text(json.dumps(audit), encoding="utf-8")
    render_report.main([str(path), "--bundle", str(CLEAN), "--out", str(tmp_path / "ok.md")])
    assert "No accepted findings" in (tmp_path / "ok.md").read_text(encoding="utf-8")
    audit["bundle_hash"] = "0" * 64
    path.write_text(json.dumps(audit), encoding="utf-8")
    assert render_report.main([str(path), "--bundle", str(CLEAN), "--out", str(tmp_path / "bad.html")]) == 1
    assert "Validation failed" in (tmp_path / "bad.html").read_text(encoding="utf-8")


@pytest.mark.parametrize("name", sorted(p.name for p in BUNDLES.iterdir() if (p / "manifest.json").exists()))
def test_local_checks_output_is_always_valid(name):
    profile = "text-only-core" if name == "source-only" else "multimodal-datastory"
    audit = local_checks.build_audit(_lib.Bundle(BUNDLES / name), profile)
    report = validate_audit.validate(audit, BUNDLES / name)
    assert report.ok, report.errors


def test_local_checks_fire_on_the_planted_cues_and_ignore_clean_pages():
    found = lambda n, p="multimodal-datastory": {f["feature_id"] for f in local_checks.build_audit(_lib.Bundle(BUNDLES / n), p)["findings"]}  # noqa: E731
    assert {"VIS-02", "TXT-01", "VIS-03", "SUB-03"} <= found("default-package-landing")
    assert found("placeholder-caption") == {"SUB-01"}
    assert found("clean-docs", "multimodal-core") == set()
    assert found("branded-gradient", "multimodal-core") == {"VIS-02"}  # fires on an appropriate, required use


def test_impeccable_importer_maps_comparable_rules_and_keeps_exclusions_separate():
    # Shape copied from crates/foundation/src/findings.rs at the pinned commit.
    findings = [
        {"antipattern": "gradient-text", "name": "Gradient text", "description": "d", "severity": "warning", "category": "slop", "file": "a.html", "line": 3, "snippet": "s"},
        {"antipattern": "overused-font", "name": "Overused font", "description": "d", "severity": "warning", "category": "slop", "file": "a.css", "line": 1, "snippet": "Inter"},
        {"antipattern": "codex-grid-background", "name": "x", "description": "d", "severity": "warning", "category": "slop", "file": "a.css", "line": 9, "snippet": "s", "advisory": True},
        {"antipattern": "justified-text", "name": "x", "description": "d", "severity": "warning", "category": "quality", "file": "a.css", "line": 2, "snippet": "s"},
    ]
    s = impeccable_import.summarize(findings)
    assert s["hits_by_codebook_feature"] == {"VIS-02": 1}
    assert set(s["excluded_rule_hits"]) == {"overused-font", "codex-grid-background"}
    assert s["unmatched_rule_hits"] == {"justified-text": 1}
    assert s["scan_kind"] == "source"


def test_impeccable_mapping_only_uses_real_registry_ids():
    registry = {r["id"] for r in load(FIXTURES.parent / "integrations/baselines/impeccable-rules.json")["rules"]}
    assert set(impeccable_import.MAPPING) <= registry and set(impeccable_import.EXCLUDED) <= registry
    assert len(registry) == 62


def test_critique_mapping_round_trips_into_a_valid_audit(tmp_path):
    b = BUNDLES / "branded-gradient"
    path = tmp_path / "map.csv"
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(critique_baseline.COLUMNS)
        w.writerow(["K001", "Gradient headline is an AI tell", "VIS-02", "R01", "S01", "accepted_slop_candidate", "moderate", "screenshot:A01", "rev-1", ""])
        w.writerow(["K002", "Lineup list is plain", "TXT-01", "R02", "S01", "contextual_exception", "", "", "rev-1", "specific names"])
    audit = critique_baseline.to_audit(path, b, "multimodal-core")
    assert validate_audit.validate(audit, b).ok
    assert [f["feature_id"] for f in audit["findings"]] == ["VIS-02"] and len(audit["contextual_exceptions"]) == 1


def test_capture_safety_policy_and_box_math():
    for unsafe in ("Sign in", "Buy tickets", "Submit form", "Delete account", "Checkout", "Send message"):
        assert gstack_capture.UNSAFE.search(unsafe), unsafe
    for safe in ("Show PM2.5", "2050 scenario button", "Compare with last year"):
        assert not gstack_capture.UNSAFE.search(safe), safe
    assert gstack_capture.norm_box({"x": 0, "y": 900, "w": 100, "h": 50}, 0, 1280, 800) is None
    box = gstack_capture.norm_box({"x": 640, "y": 750, "w": 1280, "h": 100}, 0, 1280, 800)
    assert box["x"] + box["width"] <= 1 and box["y"] + box["height"] <= 1
    plan = gstack_capture.expand_pilot8({"viewports": [{"viewport_id": "V1"}]})
    assert [v["device"] for v in plan["viewports"]] == ["desktop", "mobile"] and plan["max_images"] == 8


@pytest.mark.skipif(os.environ.get("SLOP_LIVE_CAPTURE") != "1", reason="live gstack capture; set SLOP_LIVE_CAPTURE=1")
def test_live_capture_reproduces_a_fixture(tmp_path):
    report = gstack_capture.capture(FIXTURES / "plans/clean-docs.json", tmp_path / "b", serve=FIXTURES / "sites/clean-docs")
    assert report.ok
    fresh, frozen = load(tmp_path / "b/manifest.json"), load(BUNDLES / "clean-docs/manifest.json")
    assert [t["text"] for t in fresh["text_spans"]] == [t["text"] for t in frozen["text_spans"]]
