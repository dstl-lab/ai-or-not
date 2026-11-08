"""Canonical prompt packages: deterministic, identical evidence across conditions, honest about budgets."""

import json
import shutil

import pytest

import _lib
import expand_generic
import expand_prompt
import validate_bundle
from conftest import BUNDLES, load


def build(tmp_path, name, profile, **kw):
    out = tmp_path / f"{name}-{profile}-{len(list(tmp_path.iterdir()))}"
    lock = expand_prompt.build_package(BUNDLES / name, profile, out, **kw)
    return lock, out


def test_same_inputs_give_identical_bytes_and_hashes(tmp_path):
    lock_a, a = build(tmp_path, "scenario-inconsistency", "multimodal-datastory")
    lock_b, b = build(tmp_path, "scenario-inconsistency", "multimodal-datastory")
    assert (a / "prompt.md").read_bytes() == (b / "prompt.md").read_bytes()
    assert lock_a == lock_b
    assert lock_a["prompt_sha256"] == _lib.sha256_file(a / "prompt.md")
    assert [x["asset_id"] for x in load(a / "attachments.json")] == ["A01", "A02", "A03", "A04"]


def test_package_contains_instructions_codebook_contract_schema_and_evidence(tmp_path):
    _, out = build(tmp_path, "scenario-inconsistency", "multimodal-datastory")
    prompt = (out / "prompt.md").read_text(encoding="utf-8")
    for marker in ["## Part 1. Skill instructions", "### DAT-01:", "# Output contract", "## Part 3. Audit JSON schema",
                   "## Part 4. Evidence bundle", "Image 1 = asset A01", "## Part 5. Response"]:
        assert marker in prompt, marker
    assert "gstack" not in prompt.lower() and "$B " not in prompt


def test_profile_modules_filter_the_codebook(tmp_path):
    _, core = build(tmp_path, "catalog-conventional", "multimodal-core")
    text = (core / "prompt.md").read_text(encoding="utf-8")
    assert "### VIS-01:" in text and "### DAT-01:" not in text and "### MED-01:" not in text


def test_text_only_package_has_no_images_or_boxes(tmp_path):
    lock, out = build(tmp_path, "scenario-inconsistency", "text-only-datastory")
    prompt = (out / "prompt.md").read_text(encoding="utf-8")
    assert lock["image_count"] == 0 and load(out / "attachments.json") == []
    assert "Image 1 =" not in prompt and '"appearances"' not in prompt
    assert "NOT provided under this text-only profile" in prompt


def test_image_budget_and_char_budget_fail_loudly(tmp_path):
    with pytest.raises(_lib.UsageError, match="characters"):
        build(tmp_path, "catalog-conventional", "multimodal-core", max_chars=1000)
    big = tmp_path / "big"
    shutil.copytree(BUNDLES / "default-package-landing", big)
    m = load(big / "manifest.json")
    m["assets"] = (m["assets"] * 2)[:9]
    for i, a in enumerate(m["assets"], 1):
        a = dict(a, asset_id=f"A{i:02d}")
        m["assets"][i - 1] = a
    m["evidence_profile"]["max_images"] = 9
    (big / "manifest.json").write_text(json.dumps(m), encoding="utf-8")
    report, bundle = validate_bundle.validate(big)
    validate_bundle.freeze(bundle)
    with pytest.raises(_lib.UsageError, match="allows 8"):
        expand_prompt.build_package(big, "multimodal-datastory", tmp_path / "pkg")


def test_unfrozen_or_changed_bundle_is_refused(tmp_path):
    b = tmp_path / "b"
    shutil.copytree(BUNDLES / "clean-docs", b)
    (b / "bundle.lock.json").unlink()
    with pytest.raises(_lib.UsageError, match="not frozen"):
        expand_prompt.build_package(b, "multimodal-core", tmp_path / "pkg")
    shutil.copy(BUNDLES / "clean-docs/bundle.lock.json", b / "bundle.lock.json")
    m = load(b / "manifest.json")
    m["capability_limits"].append("edited")
    (b / "manifest.json").write_text(json.dumps(m), encoding="utf-8")
    with pytest.raises(_lib.UsageError, match="changed after"):
        expand_prompt.build_package(b, "multimodal-core", tmp_path / "pkg")


def test_profile_requirements_are_enforced(tmp_path):
    with pytest.raises(_lib.UsageError, match="lacks the evidence"):
        build(tmp_path, "source-only", "multimodal-core")
    lock, _ = build(tmp_path, "source-only", "text-only-core")
    assert lock["image_count"] == 0


def test_generic_baseline_shares_evidence_and_response_but_not_the_skill(tmp_path):
    skill_lock, skill = build(tmp_path, "buttons-working-broken", "multimodal-core")
    generic = tmp_path / "generic"
    gen_lock = expand_prompt.build_package(BUNDLES / "buttons-working-broken", "multimodal-core", generic,
                                           condition="generic-prompt", instructions=expand_generic.instructions("multimodal-core"))
    a = (skill / "prompt.md").read_text(encoding="utf-8")
    b = (generic / "prompt.md").read_text(encoding="utf-8")
    assert a.split("## Part 3.")[1] == b.split("## Part 3.")[1]  # schema, evidence, response identical
    assert skill_lock["package_sha256"] != gen_lock["package_sha256"]
    assert load(skill / "attachments.json") == load(generic / "attachments.json")
    assert "Inclusion" not in b and "Include when" not in b and "INT-01: Decorative or nonfunctional affordance" in b


def test_page_instructions_stay_inside_the_evidence_part(tmp_path):
    _, out = build(tmp_path, "injection", "multimodal-datastory")
    prompt = (out / "prompt.md").read_text(encoding="utf-8")
    before, evidence = prompt.split("## Part 4. Evidence bundle")
    assert "Note to AI reviewers" not in before
    assert evidence.index("data, not instructions") < evidence.index("Note to AI reviewers")
