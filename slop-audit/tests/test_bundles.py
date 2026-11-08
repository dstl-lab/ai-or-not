"""Capture bundles: every fixture validates, and tampering or bad metadata fails explicitly."""

import json

import pytest

import _lib
import supplied_bundle
import validate_bundle
from conftest import BUNDLES, FIXTURES, codes, load

ALL = sorted(p.name for p in BUNDLES.iterdir() if (p / "manifest.json").exists())


@pytest.mark.parametrize("name", ALL)
def test_fixture_bundle_is_valid_and_frozen(name):
    report, bundle = validate_bundle.validate(BUNDLES / name)
    assert report.ok, report.errors
    assert load(BUNDLES / name / "bundle.lock.json")["bundle_hash"] == bundle.hash


def edit_manifest(path, change):
    m = load(path / "manifest.json")
    change(m)
    (path / "manifest.json").write_text(json.dumps(m), encoding="utf-8")


def test_changed_asset_is_detected(bundle_copy):
    b = bundle_copy("catalog-conventional")
    with open(b / "assets/A01.png", "ab") as fh:
        fh.write(b"tampered")
    report, _ = validate_bundle.validate(b)
    assert "hash_mismatch" in codes(report)


def test_change_after_freeze_is_detected(bundle_copy):
    b = bundle_copy("catalog-conventional")
    edit_manifest(b, lambda m: m["capability_limits"].append("edited later"))
    report, _ = validate_bundle.validate(b)
    assert codes(report) == {"changed_after_freeze"}


@pytest.mark.parametrize("change, code", [
    (lambda m: m["regions"][0].__setitem__("name", "generic AI hero"), "judgmental_region_name"),
    (lambda m: m["modalities"].__setitem__("source", True), "modality_unsupported"),
    (lambda m: m["modalities"].__setitem__("text", False), "modality_undeclared"),
    (lambda m: m["evidence_profile"].__setitem__("max_images", 0), "image_budget_exceeded"),
    (lambda m: m.__setitem__("site_id", "someone.github.io"), "blinding_leak"),
    (lambda m: m["capture"].__setitem__("target_locator", "http://example.test/"), "blinding_leak"),
    (lambda m: m["text_spans"][0].__setitem__("region_id", "R99"), "unknown_region"),
    (lambda m: m["text_spans"][0]["appearances"][0].__setitem__("box", {"x": 0.9, "y": 0.1, "width": 0.2, "height": 0.1}), "box_out_of_bounds"),
    (lambda m: m["assets"][0].__setitem__("pixel_width", 999), "dimension_mismatch"),
    (lambda m: m["context"]["purpose"].__setitem__("status", "unknown"), "context_status"),
])
def test_bad_metadata_fails_with_a_specific_code(bundle_copy, change, code):
    b = bundle_copy("catalog-conventional")
    (b / "bundle.lock.json").unlink()
    edit_manifest(b, change)
    report, _ = validate_bundle.validate(b)
    assert code in codes(report)


def test_completed_interaction_needs_an_after_state(bundle_copy):
    b = bundle_copy("buttons-working-broken")
    (b / "bundle.lock.json").unlink()
    edit_manifest(b, lambda m: m["interactions"][0].__setitem__("after_state_id", None))
    report, _ = validate_bundle.validate(b)
    assert "malformed_event" in codes(report)


def test_blinding_masks_withheld_terms_and_records_leakage():
    m = load(BUNDLES / "placeholder-caption/manifest.json")
    text = json.dumps(m)
    assert "Bluebird" not in text and "Spring 2026" not in text
    assert any(t["kind"] == "text_mask" for t in m["blinding"]["transformations"])
    assert m["blinding"]["known_leakage"] and all(l["kind"] == "visible_in_screenshot" for l in m["blinding"]["known_leakage"])
    assert m["capture"]["target_locator"] is None


def test_private_provenance_never_enters_the_bundle():
    secret = load(FIXTURES / "private/ai-assisted-coherent.provenance.json")["provenance"]["generator"]
    assert secret not in (BUNDLES / "ai-assisted-coherent/manifest.json").read_text(encoding="utf-8")


def test_loading_state_is_recorded_as_partial():
    m = load(BUNDLES / "loading-state/manifest.json")
    assert m["states"][0]["load_status"] == "partial"
    assert any("aria-busy" in x for x in m["capability_limits"])


def test_source_only_bundle_has_no_visual_or_text_evidence():
    m = load(BUNDLES / "source-only/manifest.json")
    assert m["modalities"] == {"screenshot": False, "text": False, "dom": False, "computed_style": False, "interaction": False, "source": True}
    assert m["assets"] == [] and m["text_spans"] == [] and all(r["selector"] is None for r in m["regions"])


def test_partial_capture_marks_uncaptured_regions():
    m = load(BUNDLES / "partial-capture/manifest.json")
    status = {c["ref"]: c["status"] for c in m["coverage"]["regions"]}
    assert status["R01"] == "captured"
    assert {status["R03"], status["R04"], status["R05"]} <= {"not_attempted", "partial"}
    assert any(c["status"] == "untested" for c in m["coverage"]["interactions"])


def test_recorded_interactions_match_the_planted_behavior():
    broken = {e["event_id"]: e for e in load(BUNDLES / "buttons-working-broken/manifest.json")["interactions"]}
    fixed = {e["event_id"]: e for e in load(BUNDLES / "buttons-fixed/manifest.json")["interactions"]}
    kinds = lambda e: {c["kind"] for c in e["observed_changes"]}
    assert "text_changed" in kinds(broken["E01"]) and "text_unchanged" in kinds(broken["E02"])
    assert "text_changed" in kinds(fixed["E02"])


def test_supplied_bundle_builder_is_deterministic_apart_from_timestamp(tmp_path):
    report = supplied_bundle.build(FIXTURES / "plans/source-only.json", tmp_path / "a")
    assert report.ok
    a, b = load(tmp_path / "a/manifest.json"), load(BUNDLES / "source-only/manifest.json")
    a["capture"]["captured_at"] = b["capture"]["captured_at"]
    assert a == b
