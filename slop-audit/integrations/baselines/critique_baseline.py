#!/usr/bin/env python3
"""Critique-skill baseline (condition 3): freeze the existing MCPmarket critique skill and map its output.

    # 1. build a frozen package (copies the skill files into RUN_DIR, records hashes; nothing is committed)
    python integrations/baselines/critique_baseline.py package --bundle BUNDLE --profile multimodal-datastory \\
        --critique ~/.claude/plugins/mcpmarket-me/skills/critique/SKILL.md \\
        --frontend-design PATH/TO/frontend-design/SKILL.md --out RUN_DIR

    # 2. after a model answers, a human reviewer maps its claims to codebook codes:
    python integrations/baselines/critique_baseline.py template --bundle BUNDLE --out mapping.csv
    python integrations/baselines/critique_baseline.py to-audit mapping.csv --bundle BUNDLE --profile multimodal-datastory --out audit.json

The critique skill does a broader task (a design critique ending in a pass/fail
"does this look AI-generated?" verdict and redesign commands) and expects two
dependencies: the frontend-design skill (supplied here as a pinned file) and
an interactive teach-impeccable context-gathering step, which cannot run in a
frozen benchmark; the bundle's neutral context replaces it. Its free-form
output is scored only through this human mapping (the relaxed, human-reviewed
path), never by an LLM matcher. Report these mismatches with any result.
"""

import argparse
import csv
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "website-slop-audit" / "scripts"))
import _lib  # noqa: E402
import expand_prompt  # noqa: E402

COLUMNS = ["claim_id", "critique_excerpt", "feature_id", "region_ids", "state_id", "disposition",
           "slop_association", "evidence_refs", "reviewer_id", "notes"]


def strip_frontmatter(text):
    return text.split("---", 2)[2].strip() if text.startswith("---") else text.strip()


def package(bundle_dir, profile_id, critique_path, design_path, out_dir):
    out = Path(out_dir)
    deps = out / "baseline-files"
    deps.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(critique_path, deps / "critique.SKILL.md")
    shutil.copyfile(design_path, deps / "frontend-design.SKILL.md")
    text = "\n".join([
        "## Part 1. Critique skill (frozen copy)", "",
        strip_frontmatter((deps / "critique.SKILL.md").read_text(encoding="utf-8")), "",
        "## Part 2. frontend-design skill (frozen copy, required by the critique skill)", "",
        strip_frontmatter((deps / "frontend-design.SKILL.md").read_text(encoding="utf-8")), "",
        "Benchmark note: interactive context gathering (teach-impeccable) is not available. Use the context in Part 4 "
        "as the design context. Do not browse or ask questions. Produce your critique in your normal format; "
        "the JSON schema in Part 3 and the response block in Part 5 apply to other conditions and may be ignored.",
    ])
    lock = expand_prompt.build_package(bundle_dir, profile_id, out, condition="critique-baseline", instructions=text,
                                       template_files=[deps / "critique.SKILL.md", deps / "frontend-design.SKILL.md", Path(__file__)])
    return lock


def template(bundle_dir, out_csv):
    bundle = _lib.Bundle(bundle_dir)
    with open(out_csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(COLUMNS)
        w.writerow(["K001", "(paste one critique claim)", "VIS-01", " ".join(sorted(bundle.regions)[:2]),
                    next(iter(bundle.states)), "accepted_slop_candidate", "weak", "", "reviewer-1", ""])
    return out_csv


def to_audit(csv_path, bundle_dir, profile_id):
    bundle = _lib.Bundle(bundle_dir)
    feats = _lib.features_by_id()
    findings, exceptions = [], []
    with open(csv_path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            fid = row["feature_id"].strip()
            if fid not in feats:
                raise _lib.UsageError(f"{row['claim_id']}: unknown feature {fid!r}")
            locs = [{"region_id": r, "state_id": row["state_id"].strip(), "asset_id": None, "box": None, "selector": None, "source_ref": None}
                    for r in row["region_ids"].split()]
            evidence = [{"kind": "context", "ref_id": "purpose", "description": f"critique claim {row['claim_id']} (human-mapped): {row['critique_excerpt'][:300]}", "quote": None}]
            for ref in row["evidence_refs"].split():
                kind, _, rid = ref.partition(":")
                evidence.append({"kind": kind, "ref_id": rid, "description": "reference chosen by the human mapper", "quote": None})
            if row["disposition"] == "contextual_exception":
                exceptions.append({"exception_id": f"X{len(exceptions) + 1:03d}", "feature_id": fid, "observation": row["critique_excerpt"][:600],
                                   "locations": locs, "evidence": evidence, "reason_not_counted": "appropriate_in_context",
                                   "rationale": row["notes"] or "mapped as an exception by the reviewer",
                                   "observation_confidence": {"level": "medium", "reason": "human-mapped from free-form critique"}})
                continue
            findings.append({
                "finding_id": f"F{len(findings) + 1:03d}", "feature_id": fid, "phenomenon_id": None, "secondary_tags": [],
                "scope": "cross-region" if len(locs) > 1 else "region", "observation": row["critique_excerpt"][:600],
                "locations": locs, "evidence": evidence,
                "observation_confidence": {"level": "medium", "reason": "human-mapped from free-form critique"},
                "slop_association": {"level": row["slop_association"] or "unassessed", "reason": "level assigned by the human mapper"},
                "contextual_fit": {"level": "unknown", "reason": "not stated in the critique format"},
                "communication_or_interaction_consequence": {"level": "unknown", "reason": "not stated in the critique format"},
                "alternative_explanations": ["not provided by the critique format"],
                "codebook_evidence_status": feats[fid]["evidence_status"],
                "quality_to_slop_rationale": "mapped from a critique claim" if fid == "QLT-01" else None,
                "limitations": ["human-mapped relaxed scoring path; the critique's own output format differs"],
            })
    return {
        "schema_version": "website-slop-audit/audit/0.1", "rubric_version": _lib.load_codebook()["rubric_version"],
        "audit_id": f"critique-mapped-{bundle.bundle_id}"[:64], "bundle_id": bundle.bundle_id, "bundle_hash": bundle.hash,
        "analysis_profile": profile_id, "status": "partial",
        "inventory": {k: {"value": None, "basis": "unknown"} for k in ("genre", "purpose", "audience", "main_task")} | {"structure": []},
        "coverage": {"assessed_modalities": [], "unassessed_modalities": [], "regions": [],
                     "features": [{"feature_id": f["id"], "status": "assessed" if any(x["feature_id"] == f["id"] for x in findings + exceptions) else "unassessed",
                                   "reason": "coverage cannot be read from a free-form critique"} for f in _lib.profile_features(profile_id)]},
        "findings": findings, "contextual_exceptions": exceptions, "quality_observations": [], "exploratory_candidates": [],
        "untrusted_instructions_observed": [],
        "summary": {"text": "Human-mapped critique-baseline output. Scored on the relaxed, human-reviewed path only.",
                    "major_limitations": ["The critique skill's task and output format differ from this audit"]},
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("package")
    for flag in ("--bundle", "--profile", "--critique", "--frontend-design", "--out"):
        a.add_argument(flag, required=True)
    t = sub.add_parser("template")
    t.add_argument("--bundle", required=True)
    t.add_argument("--out", required=True)
    m = sub.add_parser("to-audit")
    m.add_argument("mapping")
    m.add_argument("--bundle", required=True)
    m.add_argument("--profile", required=True)
    m.add_argument("--out", required=True)
    args = p.parse_args(argv)
    if args.cmd == "package":
        lock = package(args.bundle, args.profile, args.critique, args.frontend_design, args.out)
        print(f"prompt_sha256 {lock['prompt_sha256']} ({lock['prompt_chars']} chars, {lock['image_count']} images)")
    elif args.cmd == "template":
        print(f"wrote {template(args.bundle, args.out)}")
    else:
        audit = to_audit(args.mapping, args.bundle, args.profile)
        Path(args.out).write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
        print(f"{len(audit['findings'])} mapped finding(s) -> {args.out}")
    return 0


if __name__ == "__main__":
    _lib.run_main(main)
