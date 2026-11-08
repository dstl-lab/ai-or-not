"""Offline scorer: known-correct outputs for matching, undefined metrics, scope, and aggregation."""

import copy
import json
import shutil

import pytest

import _lib
import expand_prompt
import import_run
import local_checks
import score_benchmark as sb
from conftest import BUNDLES, FIXTURES, SKILL, load

SCEN = BUNDLES / "scenario-inconsistency"


def ref_item(aid, fid, locs, disposition="accepted_slop_candidate", scope="region", assoc="moderate"):
    return {"annotation_id": aid, "annotator_id": "dev-1", "feature_id": fid, "phenomenon_id": None, "scope": scope,
            "locations": [{"region_id": r, "state_id": s, "asset_id": None, "box": None} for r, s in locs],
            "disposition": disposition, "observed_evidence": "x", "confidence": "high", "slop_association": assoc,
            "contextual_exception": None, "consequence": "none_identified", "uncertainty": ""}


def annotation(items, scopes):
    return {"scopes": scopes, "items": items}


def finding(fid, locs, scope="region", assoc="moderate", n=1):
    return {"finding_id": f"F{n:03d}", "feature_id": fid, "scope": scope, "slop_association": {"level": assoc, "reason": "x"},
            "locations": [{"region_id": r, "state_id": s, "asset_id": None, "box": None, "selector": None, "source_ref": None} for r, s in locs]}


def audit(findings=(), exceptions=(), unassessed=()):
    return {"findings": list(findings), "contextual_exceptions": list(exceptions), "exploratory_candidates": [],
            "coverage": {"features": [{"feature_id": f, "status": "unassessed"} for f in unassessed]}}


SCOPE = [{"scope_id": "s", "region_ids": ["R02", "R03"], "state_ids": ["S03"], "feature_ids": ["INT-02", "LAY-01", "SUB-02"], "fully_annotated": True}]
POS = ref_item("r1", "INT-02", [("R02", "S03"), ("R03", "S03")], scope="cross-region")


def counts(s):
    t = {"tp": 0, "fp": 0, "fn": 0}
    for c in s["per_code"].values():
        for k in t:
            t[k] += c[k]
    return t


def test_perfect_match():
    s = sb.score_site(audit([finding("INT-02", [("R02", "S03"), ("R03", "S03")], "cross-region")]), annotation([POS], SCOPE))
    assert counts(s) == {"tp": 1, "fp": 0, "fn": 0}
    assert sb.prf(1, 0, 0)["f1"] == 1.0


def test_empty_output_has_undefined_precision_not_a_perfect_score():
    s = sb.score_site(audit(), annotation([POS], SCOPE))
    assert counts(s) == {"tp": 0, "fp": 0, "fn": 1}
    m = sb.prf(0, 0, 1)
    assert m["precision"] is None and m["recall"] == 0.0 and m["f1"] is None and "precision" in m["undefined"]


def test_empty_reference_and_empty_output_are_both_undefined():
    m = sb.prf(0, 0, 0)
    assert m["precision"] is None and m["recall"] is None and m["f1"] is None


def test_true_negative_site_penalizes_any_finding():
    s = sb.score_site(audit([finding("LAY-01", [("R02", "S03")])]), annotation([], SCOPE))
    assert counts(s) == {"tp": 0, "fp": 1, "fn": 0}
    assert s["fp_kinds"] == {"unsupported_in_annotated_scope": 1}


def test_duplicate_descriptions_match_one_to_one():
    dup = [finding("INT-02", [("R02", "S03"), ("R03", "S03")], "cross-region", n=1),
           finding("INT-02", [("R02", "S03")], "region", n=2)]
    s = sb.score_site(audit(dup), annotation([POS], SCOPE))
    assert counts(s) == {"tp": 1, "fp": 1, "fn": 0}


def test_partial_annotation_leaves_out_of_scope_findings_unreviewed():
    outside = finding("VIS-01", [("R01", "S01"), ("R02", "S01")], "page-pattern")
    s = sb.score_site(audit([outside]), annotation([POS], SCOPE))
    assert counts(s) == {"tp": 0, "fp": 0, "fn": 1} and s["n_unreviewed"] == 1


def test_mismatched_states_do_not_match():
    s = sb.score_site(audit([finding("INT-02", [("R02", "S01"), ("R03", "S01")], "cross-region")]),
                      annotation([POS], SCOPE + [dict(SCOPE[0], scope_id="s1", state_ids=["S01"])]))
    assert counts(s) == {"tp": 0, "fp": 1, "fn": 1}


def test_contextual_exception_reference_counts_as_contextual_false_alarm():
    exc = ref_item("r2", "LAY-01", [("R02", "S03"), ("R03", "S03")], "contextual_exception", "repeated-group", "none")
    s = sb.score_site(audit([finding("LAY-01", [("R02", "S03"), ("R03", "S03")], "repeated-group", "weak")]), annotation([POS, exc], SCOPE))
    assert s["fp_kinds"] == {"contextual_false_alarm": 1}
    assert s["presence"]["tp"] == 1  # the feature was present: presence recognition still credits it
    assert s["ordinal"] == [(1, 0)]


def test_page_pattern_claim_cannot_absorb_a_local_issue():
    local = ref_item("r3", "SUB-02", [("R03", "S03")], scope="region")
    broad = finding("SUB-02", [("R02", "S03"), ("R03", "S03")], "page-pattern")
    s = sb.score_site(audit([broad]), annotation([local], SCOPE))
    assert counts(s) == {"tp": 0, "fp": 1, "fn": 1}


def test_abstention_is_counted_against_annotated_scope():
    s = sb.score_site(audit(unassessed=["INT-02"]), annotation([POS], SCOPE))
    assert s["abstained"] == ["INT-02"] and len(s["scope_features"]) == 3


def test_box_iou_only_where_both_boxes_exist():
    ref = copy.deepcopy(POS)
    ref["locations"][0].update(asset_id="A04", box={"x": 0.1, "y": 0.1, "width": 0.4, "height": 0.2})
    f = finding("INT-02", [("R02", "S03"), ("R03", "S03")], "cross-region")
    f["locations"][0].update(asset_id="A04", box={"x": 0.1, "y": 0.1, "width": 0.4, "height": 0.2})
    s = sb.score_site(audit([f]), annotation([ref], SCOPE))
    assert s["localization"]["ious"] == [1.0]
    f["locations"][0]["box"] = None
    s = sb.score_site(audit([f]), annotation([ref], SCOPE))
    assert s["localization"]["ious"] == [] and s["localization"]["null_box_where_ref_box"] == 1


def test_spearman_handles_ties_and_constant_input():
    assert sb.spearman([(0, 0), (1, 1), (2, 2), (3, 3)]) == pytest.approx(1.0)
    assert sb.spearman([(1, 1), (1, 2), (1, 3)]) is None
    assert sb.spearman([(1, 2)]) is None


# --- end-to-end over saved runs ---------------------------------------------------

def make_run(tmp_path, bundle_dir, audit_obj, condition, model, profile="multimodal-datastory", index=1, raw=None):
    pkg = tmp_path / f"pkg-{bundle_dir.name}-{profile}"
    if not pkg.exists():
        expand_prompt.build_package(bundle_dir, profile, pkg)
    raw_path = tmp_path / f"raw-{condition}-{model}-{bundle_dir.name}-{index}.txt"
    raw_path.write_text(raw if raw is not None else json.dumps(audit_obj), encoding="utf-8")
    rec, _ = import_run.import_run(raw_path, pkg, bundle_dir, tmp_path / "runs", condition, "test", model, "unit test", run_index=index)
    return rec


def setup_scoring(tmp_path):
    ann = tmp_path / "annotations"
    ann.mkdir()
    for name in ("scenario-inconsistency", "buttons-working-broken", "branded-gradient", "catalog-conventional"):
        shutil.copy(FIXTURES / "annotations" / f"{name}.json", ann / f"{name}.json")
    return ann


def test_end_to_end_scoring_with_parse_failure_and_separate_capability_tables(tmp_path):
    ann = setup_scoring(tmp_path)
    good = load(FIXTURES / "audits/scenario-inconsistency.audit.json")
    make_run(tmp_path, SCEN, good, "frozen-skill", "model-a")
    make_run(tmp_path, SCEN, None, "frozen-skill", "model-a", index=2, raw="Sorry, I can't produce JSON for this.")
    make_run(tmp_path, SCEN, local_checks.build_audit(_lib.Bundle(SCEN), "text-only-datastory"), "deterministic-baseline", "local-checks",
             profile="text-only-datastory")
    result = sb.score(tmp_path / "runs", ann, BUNDLES)
    mm = result["systems_by_capability"]["multimodal"]["frozen-skill/model-a"]
    # run 1 finds the one positive, run 2 failed to parse: averaged within the site, not counted twice
    assert mm["primary"]["tp"] == pytest.approx(0.5) and mm["primary"]["fn"] == pytest.approx(0.5)
    assert result["operational"]["frozen-skill/model-a"]["parse_failures"] == 1
    assert result["operational"]["frozen-skill/model-a"]["schema_valid_rate"] == 0.5
    assert "text_only" in result["systems_by_capability"]  # reduced-capability runs get their own table


def test_deterministic_baseline_pays_for_context_blind_hits(tmp_path):
    ann = setup_scoring(tmp_path)
    for name in ("branded-gradient", "buttons-working-broken", "catalog-conventional"):
        b = BUNDLES / name
        make_run(tmp_path, b, local_checks.build_audit(_lib.Bundle(b), "multimodal-core"), "deterministic-baseline", "local-checks", profile="multimodal-core")
    s = sb.score(tmp_path / "runs", ann, BUNDLES)["systems_by_capability"]["multimodal"]["deterministic-baseline/local-checks"]
    assert s["primary"]["tp"] == 1  # the dead button
    assert s["false_alarm_breakdown"].get("contextual_false_alarm") == 1  # the required brand gradient
    assert s["per_site"][_lib.Bundle(BUNDLES / "catalog-conventional").bundle_id]["precision"] is None  # no prediction there: undefined, not perfect


def test_perturbation_pairs_behave_as_expected():
    broken = local_checks.build_audit(_lib.Bundle(BUNDLES / "buttons-working-broken"), "multimodal-core")
    fixed = local_checks.build_audit(_lib.Bundle(BUNDLES / "buttons-fixed"), "multimodal-core")
    assert "INT-01" in {f["feature_id"] for f in broken["findings"]}
    assert "INT-01" not in {f["feature_id"] for f in fixed["findings"]}
    surface = lambda a: {f["feature_id"] for f in a["findings"]} - {"INT-01"}  # noqa: E731
    assert surface(broken) == surface(fixed)
    a = local_checks.build_audit(_lib.Bundle(BUNDLES / "scenario-inconsistency"), "multimodal-datastory")
    b = local_checks.build_audit(_lib.Bundle(BUNDLES / "scenario-inconsistency-restyled"), "multimodal-datastory")
    assert {f["feature_id"] for f in a["findings"]} == {f["feature_id"] for f in b["findings"]}


def test_paired_bootstrap_is_deterministic_and_paired_over_sites(tmp_path):
    ann = setup_scoring(tmp_path)
    for name in ("scenario-inconsistency", "buttons-working-broken"):
        b = BUNDLES / name
        prof = "multimodal-datastory" if name.startswith("scenario") else "multimodal-core"
        make_run(tmp_path, b, local_checks.build_audit(_lib.Bundle(b), prof), "deterministic-baseline", "local-checks", profile=prof)
        make_run(tmp_path, b, json.loads(json.dumps({"x": 1})), "generic-prompt", "model-a", profile=prof)
    r1 = sb.score(tmp_path / "runs", ann, BUNDLES, compare=["deterministic-baseline/local-checks", "generic-prompt/model-a"], bootstrap=300, seed=7)
    r2 = sb.score(tmp_path / "runs", ann, BUNDLES, compare=["deterministic-baseline/local-checks", "generic-prompt/model-a"], bootstrap=300, seed=7)
    assert r1["comparison"] == r2["comparison"] and r1["comparison"]["sites"] == 2


def test_annotation_for_a_different_bundle_version_is_rejected(tmp_path):
    ann = setup_scoring(tmp_path)
    data = load(ann / "scenario-inconsistency.json")
    data["bundle_hash"] = "0" * 64
    (ann / "scenario-inconsistency.json").write_text(json.dumps(data), encoding="utf-8")
    make_run(tmp_path, SCEN, load(FIXTURES / "audits/scenario-inconsistency.audit.json"), "frozen-skill", "model-a")
    with pytest.raises(_lib.UsageError, match="different bundle version"):
        sb.score(tmp_path / "runs", ann, BUNDLES)


def test_human_variability_compares_pre_adjudication_sets(tmp_path):
    base = load(FIXTURES / "annotations/scenario-inconsistency.json")
    for i, assoc in enumerate(["moderate", "strong"], 1):
        s = copy.deepcopy(base)
        s.update(annotation_set_id=f"pre-{i}", stage="pre_adjudication")
        s["items"][0]["slop_association"] = assoc
        (tmp_path / f"pre-{i}.json").write_text(json.dumps(s), encoding="utf-8")
    out = sb.human_variability(tmp_path)
    assert out[0]["matched"] == 2 and out[0]["disposition_agreement"] == 1.0 and out[0]["association_exact"] == 0.5
