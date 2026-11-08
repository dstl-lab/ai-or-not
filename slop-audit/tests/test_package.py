"""The skill package itself: portable structure, codebook integrity, schema subset."""

import re

import jsonschema
import pytest

import _lib
import build_codebook
from conftest import BUNDLES, FIXTURES, SKILL, load

PORTABLE_CORE = ["SKILL.md", "references/feature-codebook.md", "references/output-contract.md",
                 "references/capture-protocol.md", "references/benchmark-protocol.md"]


def frontmatter():
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    head, body = text.split("---", 2)[1:]
    fields = {}
    for line in head.strip().splitlines():
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    return fields, body


def test_frontmatter_follows_agent_skills_spec():
    fields, body = frontmatter()
    assert set(fields) == {"name", "description"}  # only the required portable fields
    name = fields["name"]
    assert name == SKILL.name
    assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name) and len(name) <= 64
    assert 0 < len(fields["description"]) <= 1024
    assert len(body.splitlines()) < 500


def test_every_relative_link_in_skill_md_exists():
    _, body = frontmatter()
    links = re.findall(r"\]\(([^)#]+)\)", body) + re.findall(r"`((?:scripts|references|schemas|assets|examples)/[^`\s]+)`", body)
    assert links
    for link in links:
        assert (SKILL / link).exists(), link


def test_portable_core_names_no_host_tools():
    banned = re.compile(r"gstack|\$B\b|claude[- ]in[- ]chrome|mcp__|Claude Code|AskUserQuestion", re.IGNORECASE)
    for rel in ["SKILL.md", "references/feature-codebook.md", "references/output-contract.md"]:
        assert not banned.search((SKILL / rel).read_text(encoding="utf-8")), rel


def test_generated_codebook_files_are_current():
    assert build_codebook.main(["--check"]) == 0


def test_codebook_entries_are_complete_and_sourced():
    cb = _lib.load_codebook()
    required = {"id", "family", "module", "title", "definition", "unit_of_observation", "inclusion", "exclusion",
                "minimum_evidence", "modality_sets", "positive_example", "counterexample", "alternative_explanations",
                "evidence_status", "sources", "consequence_required", "judgment", "boundaries"}
    sources = {s["id"] for s in cb["sources"]}
    ids = [f["id"] for f in cb["features"]]
    assert len(ids) == len(set(ids)) == 20
    for f in cb["features"]:
        assert required <= set(f), f["id"]
        assert set(f["sources"]) <= sources, f["id"]
        assert f["evidence_status"] in cb["evidence_status_levels"]
        assert f["evidence_status"] != "corpus_specific_empirical"  # no corpus study exists yet
        assert f["module"] in cb["modules"]
        assert all(set(s) <= set(cb["modalities"]) for s in f["modality_sets"])
    assert next(f for f in cb["features"] if f["id"] == "QLT-01")["evidence_status"] == "quality_only"
    for s in cb["sources"]:
        assert s["access_level"] in {"full_text", "abstract_only", "metadata_only", "internal"}


def test_profiles_reference_existing_modules():
    cb, profiles = _lib.load_codebook(), _lib.load_profiles()
    for pid, p in profiles["analysis_profiles"].items():
        assert set(p["modules"]) <= set(cb["modules"]), pid
        if p["capability"] == "text_only":
            assert p["max_images"] == 0


@pytest.mark.parametrize("name", ["capture-bundle.schema.json", "audit.schema.json", "annotation.schema.json", "run-record.schema.json"])
def test_schemas_use_only_the_supported_subset(name):
    schema = _lib.load_schema(name)
    assert _lib.unsupported_keywords(schema) == []
    jsonschema.Draft202012Validator.check_schema(schema)


def agree(instance, schema):
    ours = not _lib.schema_errors(instance, schema)
    ref = jsonschema.Draft202012Validator(schema).is_valid(instance)
    return ours, ref


def test_subset_validator_agrees_with_jsonschema_on_valid_documents():
    bundle_schema = _lib.load_schema("capture-bundle.schema.json")
    for manifest in BUNDLES.glob("*/manifest.json"):
        assert agree(load(manifest), bundle_schema) == (True, True), manifest
    audit_schema = _lib.load_schema("audit.schema.json")
    for audit in (SKILL / "examples/audits").glob("*.json"):
        assert agree(load(audit), audit_schema) == (True, True), audit


def test_subset_validator_agrees_with_jsonschema_on_broken_documents(example_audit):
    audit, _ = example_audit
    schema = _lib.load_schema("audit.schema.json")
    mutations = [
        lambda a: a.pop("summary"),
        lambda a: a.__setitem__("status", "done"),
        lambda a: a["findings"][0]["locations"][0].__setitem__("box", {"x": 0.5, "y": 0.1, "width": 0, "height": 0.1}),
        lambda a: a["findings"][0]["slop_association"].__setitem__("level", "none"),
        lambda a: a["findings"][0].__setitem__("finding_id", "1"),
        lambda a: a["findings"][0].__setitem__("extra", True),
        lambda a: a["coverage"]["features"].__setitem__(0, {"feature_id": "VIS-1", "status": "assessed", "reason": "x"}),
        lambda a: a["summary"].__setitem__("text", ""),
    ]
    for i, mutate in enumerate(mutations):
        broken = load(FIXTURES / "audits/scenario-inconsistency.audit.json")
        mutate(broken)
        assert agree(broken, schema) == (False, False), i
