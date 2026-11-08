#!/usr/bin/env python3
"""Deterministic baseline: a small, transparent rule subset run over a frozen bundle.

    python integrations/baselines/local_checks.py BUNDLE --profile multimodal-datastory --out audit.json

Condition 4 of the benchmark protocol. Each rule reads only captured text,
computed styles, and recorded interactions (never pixels or source), and
emits an audit in the standard schema so it is scored exactly like a model.
Rules detect presence only: slop association is always "unassessed" and
context is never consulted, so appropriate uses still fire. That is the
point of the baseline, not a bug. It is not an origin detector.

RULES lists every rule, its codebook feature, and its trigger.
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "website-slop-audit" / "scripts"))
import _lib  # noqa: E402

VERSION = "local-checks-0.1.0"
RULES = {
    "gradient-text": ("VIS-02", "an element's computed background-clip is 'text' with a gradient background-image"),
    "tracked-caps-label": ("VIS-02", "two or more elements with text-transform uppercase, letter-spacing at least 0.1em, and font-size at most 14px"),
    "literal-placeholder": ("SUB-01", "a text span matches lorem ipsum, TODO, 'replace with', or 'insert ... here'"),
    "marketing-buzzwords": ("TXT-01", "a text span contains two or more of a fixed buzzword list"),
    "unitless-stat-tiles": ("SUB-03", "two or more short numeric spans (like '10x', '99%', '24/7') in one region"),
    "repeated-emoji": ("VIS-03", "the same emoji appears in three or more text spans"),
    "no-change-control": ("INT-01", "a completed click recorded no text and no state change"),
}
BUZZWORDS = ["unlock", "empower", "transform", "reimagine", "seamless", "next-generation", "elevate", "powerful insights", "effortless"]
PLACEHOLDER = re.compile(r"lorem ipsum|\btodo\b|replace with|insert .{0,30} here|\[placeholder\]", re.IGNORECASE)
STAT = re.compile(r"^\s*(\d+(\.\d+)?\s?(x|%)|24/7|\d+\+)\s*$", re.IGNORECASE)
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿✨]")


def px(value):
    m = re.match(r"(-?\d+(\.\d+)?)px", value or "")
    return float(m.group(1)) if m else 0.0


def loc(region_id, state_id, element=None):
    return {"region_id": region_id, "state_id": state_id, "asset_id": None, "box": None,
            "selector": element["selector"] if element else None, "source_ref": None}


def run_rules(bundle):
    m = bundle.manifest
    hits = []  # (rule, locations, evidence, observation)
    spans_by_el = {s["element_id"]: s for s in m["text_spans"] if s["element_id"]}
    initial = {s["state_id"] for s in m["states"] if s["kind"] in ("initial", "supplied")}

    caps = []
    for e in m["dom_elements"]:
        st = e["computed_style"] or {}
        if e["region_id"] is None or e["state_id"] not in initial:
            continue
        if st.get("background-clip") == "text" or st.get("-webkit-background-clip") == "text":
            if "gradient" in st.get("background-image", ""):
                span = spans_by_el.get(e["element_id"])
                ev = [{"kind": "dom", "ref_id": e["element_id"], "description": "computed background-clip: text with a gradient background-image", "quote": None}]
                if span:
                    ev.append({"kind": "text", "ref_id": span["span_id"], "description": "the styled text", "quote": span["text"][:120]})
                hits.append(("gradient-text", [loc(e["region_id"], e["state_id"], e)], ev, "Text rendered with a gradient fill (background-clip: text)."))
        size = px(st.get("font-size"))
        if st.get("text-transform") == "uppercase" and size and size <= 14 and px(st.get("letter-spacing")) >= 0.1 * size:
            caps.append(e)
    if len(caps) >= 2:
        hits.append(("tracked-caps-label", [loc(e["region_id"], e["state_id"], e) for e in caps],
                     [{"kind": "dom", "ref_id": e["element_id"], "description": "uppercase, widely tracked, small label", "quote": None} for e in caps],
                     f"{len(caps)} small uppercase labels with wide letter-spacing."))

    emoji_spans = defaultdict(list)
    stats = defaultdict(list)
    for s in m["text_spans"]:
        if s["region_id"] is None or s["state_id"] not in initial:
            continue
        text = s["text"]
        found = PLACEHOLDER.search(text)
        if found:
            hits.append(("literal-placeholder", [loc(s["region_id"], s["state_id"])],
                         [{"kind": "text", "ref_id": s["span_id"], "description": "matches a placeholder pattern", "quote": found.group(0)}],
                         f"Literal placeholder text: '{found.group(0)}'."))
        words = [w for w in BUZZWORDS if w in text.lower()]
        if len(words) >= 2:
            hits.append(("marketing-buzzwords", [loc(s["region_id"], s["state_id"])],
                         [{"kind": "text", "ref_id": s["span_id"], "description": f"contains {', '.join(words)}", "quote": None}],
                         f"Copy combining {', '.join(words)}."))
        for ch in set(EMOJI.findall(text)):
            emoji_spans[ch].append(s)
        if STAT.match(text):
            stats[s["region_id"]].append(s)
    for ch, spans in emoji_spans.items():
        if len(spans) >= 3:
            hits.append(("repeated-emoji", [loc(s["region_id"], s["state_id"]) for s in spans],
                         [{"kind": "text", "ref_id": s["span_id"], "description": "contains the repeated emoji", "quote": ch} for s in spans],
                         f"The same emoji appears in {len(spans)} text spans."))
    for region_id, spans in stats.items():
        if len(spans) >= 2:
            hits.append(("unitless-stat-tiles", [loc(region_id, spans[0]["state_id"])],
                         [{"kind": "text", "ref_id": s["span_id"], "description": "short numeric display", "quote": s["text"]} for s in spans],
                         f"{len(spans)} short numeric displays in one region."))

    for ev in m["interactions"]:
        kinds = {c["kind"] for c in ev["observed_changes"]}
        if ev["execution_status"] == "completed" and ev["action"] == "click" and not kinds & {"text_changed", "dom_changed", "navigation"}:
            region = ev["target"]["region_id"]
            if region:
                hits.append(("no-change-control", [loc(region, ev["before_state_id"]), loc(region, ev["after_state_id"])],
                             [{"kind": "interaction", "ref_id": ev["event_id"], "description": "completed click with no recorded change", "quote": None}],
                             f"Clicking '{ev['target']['description']}' produced no recorded change."))
    return hits


def build_audit(bundle, profile_id):
    feats = _lib.features_by_id()
    allowed = {f["id"] for f in _lib.profile_features(profile_id)}
    modalities = _lib.available_modalities(bundle.manifest, profile_id)
    findings, merged = [], {}
    for rule, locations, evidence, observation in run_rules(bundle):
        fid = RULES[rule][0]
        if fid not in allowed or not _lib.feature_assessable(feats[fid], modalities):
            continue
        if fid in merged:  # one finding per feature: extra hits become extra locations
            f = merged[fid]
            for l in locations:
                if (l["region_id"], l["state_id"]) not in {(x["region_id"], x["state_id"]) for x in f["locations"]}:
                    f["locations"].append(l)
            f["evidence"] += evidence
            f["observation"] = (f["observation"] + " " + observation)[:600]
            continue
        f = {
            "finding_id": f"F{len(findings) + 1:03d}", "feature_id": fid, "phenomenon_id": None, "secondary_tags": [],
            "scope": "region", "observation": observation, "locations": locations, "evidence": evidence,
            "observation_confidence": {"level": "high", "reason": f"rule {rule} matched captured data"},
            "slop_association": {"level": "unassessed", "reason": "deterministic rule; context and fit are not evaluated"},
            "contextual_fit": {"level": "unknown", "reason": "rules do not read the site's context"},
            "communication_or_interaction_consequence": {"level": "unknown", "reason": "not evaluated by rules"},
            "alternative_explanations": ["rule-based presence detection; any context-appropriate use also matches"],
            "codebook_evidence_status": feats[fid]["evidence_status"], "quality_to_slop_rationale": None,
            "limitations": [f"rule {rule}: {RULES[rule][1]}"],
        }
        findings.append(f)
        merged[fid] = f
    for f in findings:
        regions = {l["region_id"] for l in f["locations"]}
        if len(regions) > 1:
            f["scope"] = "repeated-group"
        need = feats[f["feature_id"]].get("min_regions", 1)
        if len(regions) < need:
            f["limitations"].append(f"fewer regions than the codebook minimum ({need})")
    findings = [f for f in findings if len({l['region_id'] for l in f['locations']}) >= feats[f['feature_id']].get('min_regions', 1)]
    for i, f in enumerate(findings, 1):
        f["finding_id"] = f"F{i:03d}"
    ruled = {fid for fid, _ in RULES.values()}
    coverage_features = []
    for feat in _lib.profile_features(profile_id):
        fid = feat["id"]
        if fid in ruled and _lib.feature_assessable(feat, modalities):
            coverage_features.append({"feature_id": fid, "status": "assessed", "reason": "checked by a deterministic rule"})
        else:
            coverage_features.append({"feature_id": fid, "status": "unassessed", "reason": "no deterministic rule for this feature in this baseline"})
    return {
        "schema_version": "website-slop-audit/audit/0.1",
        "rubric_version": _lib.load_codebook()["rubric_version"],
        "audit_id": f"{VERSION}-{bundle.bundle_id}"[:64],
        "bundle_id": bundle.bundle_id,
        "bundle_hash": bundle.hash,
        "analysis_profile": profile_id,
        "status": "partial",
        "inventory": {"genre": {"value": None, "basis": "unknown"}, "purpose": {"value": None, "basis": "unknown"},
                      "audience": {"value": None, "basis": "unknown"}, "main_task": {"value": None, "basis": "unknown"}, "structure": []},
        "coverage": {"assessed_modalities": sorted(modalities & {"text", "dom", "computed_style", "interaction"}),
                     "unassessed_modalities": [{"modality": m, "reason": "the rule baseline does not read this modality"}
                                               for m in sorted(modalities - {"text", "dom", "computed_style", "interaction"})],
                     "regions": [], "features": coverage_features},
        "findings": findings,
        "contextual_exceptions": [], "quality_observations": [], "exploratory_candidates": [], "untrusted_instructions_observed": [],
        "summary": {"text": f"{VERSION}: presence-only rule hits over captured text, styles, and interactions. Context, fit, and slop association are not evaluated.",
                    "major_limitations": ["Rules fire on appropriate uses too", "Screenshots and source are not read"]},
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("bundle")
    p.add_argument("--profile", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args(argv)
    bundle = _lib.Bundle(a.bundle)
    audit = build_audit(bundle, a.profile)
    Path(a.out).write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(audit['findings'])} rule finding(s) -> {a.out}")
    return 0


if __name__ == "__main__":
    _lib.run_main(main)
