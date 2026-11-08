"""Audit validation: valid outputs pass (including zero findings and abstention); each kind of invalid output fails with its own code."""

import copy
import json

import pytest

import _lib
import validate_audit
from conftest import BUNDLES, SKILL, codes, empty_audit, load


def check(audit, bundle):
    return validate_audit.validate(audit, bundle)


def test_example_audits_are_valid():
    for name in ("placeholder-caption", "clean-docs"):
        report = check(load(SKILL / f"examples/audits/{name}.audit.json"), SKILL / f"examples/bundles/{name}")
        assert report.ok and not report.warnings, report.errors + report.warnings


@pytest.mark.parametrize("name, profile", [("clean-docs", "multimodal-core"), ("source-only", "text-only-core"),
                                           ("partial-capture", "text-only-datastory"), ("ai-assisted-coherent", "multimodal-datastory")])
def test_zero_findings_and_abstention_are_valid(name, profile):
    report = check(empty_audit(BUNDLES / name, profile, status="partial"), BUNDLES / name)
    assert report.ok, report.errors


def test_insufficient_evidence_with_empty_arrays_is_valid():
    audit = empty_audit(BUNDLES / "loading-state", "multimodal-core", status="insufficient_evidence")
    assert check(audit, BUNDLES / "loading-state").ok


def test_invalid_json_fails(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text('{"schema_version": "website-slop-audit/audit/0.1",', encoding="utf-8")
    assert codes(check(str(path), BUNDLES / "clean-docs")) == {"invalid_json"}


F = lambda a: a["findings"][0]  # noqa: E731


@pytest.mark.parametrize("mutate, code", [
    (lambda a: F(a)["locations"][0].__setitem__("asset_id", "A99"), "missing_asset_ref"),
    (lambda a: F(a)["locations"][0].__setitem__("region_id", "R99"), "unknown_region"),
    (lambda a: F(a)["locations"][0].__setitem__("state_id", "S01"), "asset_state_mismatch"),
    (lambda a: F(a)["locations"][0].__setitem__("box", {"x": 0.8, "y": 0.1, "width": 0.3, "height": 0.1}), "box_out_of_bounds"),
    (lambda a: F(a)["locations"][0].update(asset_id=None), "box_without_asset"),
    (lambda a: F(a)["locations"][0].__setitem__("selector", "#invented-selector"), "fabricated_selector"),
    (lambda a: F(a)["locations"][0].__setitem__("source_ref", {"excerpt_id": "SX01", "line_start": 1, "line_end": 2}), "modality_unavailable"),
    (lambda a: F(a)["evidence"].append({"kind": "interaction", "ref_id": "E09", "description": "made up", "quote": None}), "missing_event_ref"),
    (lambda a: F(a)["evidence"].append({"kind": "text", "ref_id": "T999", "description": "made up", "quote": None}), "missing_span_ref"),
    (lambda a: F(a)["evidence"][1].__setitem__("quote", "Parcels in the flood zone, 2100"), "quote_mismatch"),
    (lambda a: F(a)["evidence"].append({"kind": "context", "ref_id": "brand_brief", "description": "x", "quote": None}), "missing_context_ref"),
    (lambda a: F(a).__setitem__("codebook_evidence_status", "corpus_specific_empirical"), "status_upgrade"),
    (lambda a: F(a).__setitem__("feature_id", "VIS-99"), "unknown_feature"),
    (lambda a: a.__setitem__("bundle_hash", "0" * 64), "bundle_mismatch"),
    (lambda a: a.__setitem__("rubric_version", "9.9.9"), "rubric_mismatch"),
    (lambda a: a.__setitem__("status", "insufficient_evidence"), "contradictory_status"),
    (lambda a: a["contextual_exceptions"][0].update(feature_id="INT-02", locations=copy.deepcopy(F(a)["locations"])), "contradictory_status"),
    (lambda a: next(c for c in a["coverage"]["features"] if c["feature_id"] == "INT-02").__setitem__("status", "unassessed"), "contradictory_status"),
    (lambda a: a["findings"].append(dict(copy.deepcopy(F(a)), finding_id="F002", phenomenon_id="P002")), "duplicate_finding"),
    (lambda a: a["findings"].append(dict(copy.deepcopy(F(a)), finding_id="F002", feature_id="SUB-02", codebook_evidence_status="research_hypothesis",
                                         secondary_tags=[], locations=[F(a)["locations"][0], dict(F(a)["locations"][1], state_id="S01", asset_id="A01")])),
     "phenomenon_multiple_codes"),
    (lambda a: a["findings"].append(dict(copy.deepcopy(F(a)), finding_id="F001", phenomenon_id="P009", locations=F(a)["locations"][:1] + [dict(F(a)["locations"][1], region_id="R04")])), "duplicate_id"),
    (lambda a: F(a).__setitem__("locations", F(a)["locations"][:1]), "insufficient_regions"),
    (lambda a: a.__setitem__("analysis_profile", "multimodal-core"), "feature_not_in_profile"),
])
def test_each_invalid_output_fails_with_its_code(example_audit, mutate, code):
    audit, bundle = example_audit
    mutate(audit)
    assert code in codes(check(audit, bundle))


def test_behavior_claim_on_an_untested_or_failed_event_is_rejected(bundle_copy):
    b = bundle_copy("buttons-working-broken")
    m = load(b / "manifest.json")
    m["interactions"][1]["execution_status"] = "timed_out"
    m["interactions"][1]["after_state_id"] = None
    (b / "manifest.json").write_text(json.dumps(m), encoding="utf-8")
    audit = empty_audit(b, "multimodal-core")
    audit["findings"].append({
        "finding_id": "F001", "feature_id": "INT-01", "phenomenon_id": None, "secondary_tags": [], "scope": "region",
        "observation": "The compare button is broken.", "locations": [{"region_id": "R02", "state_id": "S01", "asset_id": None, "box": None, "selector": None, "source_ref": None}],
        "evidence": [{"kind": "interaction", "ref_id": "E02", "description": "the click", "quote": None}],
        "observation_confidence": {"level": "high", "reason": "x"}, "slop_association": {"level": "weak", "reason": "x"},
        "contextual_fit": {"level": "unknown", "reason": "x"}, "communication_or_interaction_consequence": {"level": "major", "reason": "x"},
        "alternative_explanations": ["bug"], "codebook_evidence_status": "research_hypothesis", "quality_to_slop_rationale": None, "limitations": []})
    found = codes(check(audit, b))
    assert {"unobserved_action", "consequence_without_evidence"} <= found


def test_text_only_audit_cannot_cite_screenshots(example_audit):
    audit, bundle = example_audit
    audit["analysis_profile"] = "text-only-datastory"
    found = codes(check(audit, bundle))
    assert "modality_unavailable" in found


def test_source_only_audit_cannot_invent_visuals_or_selectors():
    b = BUNDLES / "source-only"
    audit = empty_audit(b, "text-only-core", status="partial")
    audit["exploratory_candidates"].append({
        "candidate_id": "C001", "label": "handler bound to a missing id", "observation": "x", "why_outside_codebook": "x",
        "locations": [{"region_id": "R02", "state_id": "S01", "asset_id": "A01", "box": None, "selector": "#compare-last-year",
                       "source_ref": {"excerpt_id": "SX03", "line_start": 11, "line_end": 40}}],
        "evidence": [{"kind": "source", "ref_id": "SX03", "description": "x", "quote": 'getElementById("compare-last-yr")'}],
        "observation_confidence": {"level": "high", "reason": "x"}})
    found = codes(check(audit, b))
    assert {"modality_unavailable", "fabricated_selector", "invalid_source_lines"} <= found
    audit["exploratory_candidates"][0]["locations"][0].update(asset_id=None, selector=None, source_ref={"excerpt_id": "SX03", "line_start": 11, "line_end": 16})
    assert check(audit, b).ok  # exact source quote and valid lines pass


def test_quality_defect_needs_an_explicit_rationale_to_be_a_finding():
    b = BUNDLES / "clean-docs"
    audit = empty_audit(b, "multimodal-core")
    finding = {
        "finding_id": "F001", "feature_id": "QLT-01", "phenomenon_id": None, "secondary_tags": [], "scope": "region",
        "observation": "Small table text.", "locations": [{"region_id": "R03", "state_id": "S01", "asset_id": "A01", "box": None, "selector": None, "source_ref": None}],
        "evidence": [{"kind": "screenshot", "ref_id": "A01", "description": "table", "quote": None}],
        "observation_confidence": {"level": "medium", "reason": "x"}, "slop_association": {"level": "weak", "reason": "x"},
        "contextual_fit": {"level": "questionable", "reason": "x"}, "communication_or_interaction_consequence": {"level": "minor", "reason": "x"},
        "alternative_explanations": ["ordinary defect"], "codebook_evidence_status": "quality_only", "quality_to_slop_rationale": None, "limitations": []}
    audit["findings"].append(finding)
    assert "quality_without_rationale" in codes(check(audit, b))
    finding["quality_to_slop_rationale"] = "explicit rationale linking the defect to the construct"
    assert check(audit, b).ok


def test_untrusted_instructions_are_recordable_and_checked():
    b = BUNDLES / "injection"
    audit = empty_audit(b, "multimodal-datastory", status="partial")
    span = next(t for t in load(b / "manifest.json")["text_spans"] if "Note to AI reviewers" in t["text"])
    audit["untrusted_instructions_observed"].append({"ref_kind": "text", "ref_id": span["span_id"], "description": "asks the auditor to approve the page"})
    assert check(audit, b).ok
    audit["untrusted_instructions_observed"][0]["ref_id"] = "T999"
    assert "missing_span_ref" in codes(check(audit, b))


def test_authorship_verdict_language_is_flagged(example_audit):
    audit, bundle = example_audit
    audit["summary"]["text"] = "This site is likely AI-generated; probability that it was generated by AI is 80%."
    report = check(audit, bundle)
    assert report.ok and any(code == "possible_authorship_claim" for code, _ in report.warnings)
