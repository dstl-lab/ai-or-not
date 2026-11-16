import copy
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "website-slop-audit"
FIXTURES = ROOT / "fixtures"
BUNDLES = FIXTURES / "bundles"
for p in (SKILL / "scripts", ROOT / "integrations" / "capture", ROOT / "integrations" / "baselines"):
    sys.path.insert(0, str(p))

import _lib  # noqa: E402


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


@pytest.fixture
def example_audit():
    """A fresh copy of the known-good scenario audit (test-only) and its bundle."""
    return copy.deepcopy(load(FIXTURES / "audits/scenario-inconsistency.audit.json")), BUNDLES / "scenario-inconsistency"


@pytest.fixture
def bundle_copy(tmp_path):
    """Copy a fixture bundle so a test can tamper with it."""
    def make(name):
        dst = tmp_path / name
        shutil.copytree(BUNDLES / name, dst)
        return dst
    return make


def codes(report):
    return {code for code, _ in report.errors}


def empty_audit(bundle_dir, profile_id, status="completed"):
    """A minimal valid audit with no findings for any bundle."""
    b = _lib.Bundle(bundle_dir)
    mods = _lib.available_modalities(b.manifest, profile_id)
    feats = _lib.profile_features(profile_id)
    return {
        "schema_version": "website-slop-audit/audit/0.1", "rubric_version": _lib.load_codebook()["rubric_version"],
        "audit_id": "test-audit", "bundle_id": b.bundle_id, "bundle_hash": b.hash, "analysis_profile": profile_id, "status": status,
        "inventory": {k: {"value": None, "basis": "unknown"} for k in ("genre", "purpose", "audience", "main_task")} | {"structure": []},
        "coverage": {"assessed_modalities": sorted(mods), "unassessed_modalities": [], "regions": [],
                     "features": [{"feature_id": f["id"], "status": "assessed" if _lib.feature_assessable(f, mods) else "unassessed",
                                   "reason": "test"} for f in feats]},
        "findings": [], "contextual_exceptions": [], "quality_observations": [], "exploratory_candidates": [],
        "untrusted_instructions_observed": [], "summary": {"text": "test", "major_limitations": []},
    }


def questionnaire_audit(bundle_dir, profile_id="multimodal-datastory"):
    """A minimal valid tour-stage audit with study answers, for any bundle (no findings)."""
    import questionnaire as q
    a = empty_audit(bundle_dir, profile_id)
    b = _lib.Bundle(bundle_dir)
    ref = [{"kind": "screenshot", "id": b.manifest["assets"][0]["asset_id"]}]
    ans = lambda v: {"value": v, "reason": "Formed from the tour.", "refs": ref}
    feats = [f["value"] for f in q.features()]
    a["study_questionnaire"] = {
        "questionnaire_version": q.load()["questionnaire_version"], "basis": "Test answers formed from the tour.",
        "answers": {"ai_appearance": ans(2), "ai_marks": ans("none"),
                    "feature_rating": {"value": {f: 2 for f in feats}, "reason": "Test.", "refs": ref,
                                       "rows": [{"feature": f, "reason": "Test.", "refs": ref} for f in feats]},
                    "top_ai_feature": ans(feats[0]), "ai_extent": ans("a_little"), "design_generic": ans(2), "writing_ai": ans(1),
                    "polish": ans(3), "quality": ans(4), "technical_issue": ans("no")}}
    return a
