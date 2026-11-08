#!/usr/bin/env python3
"""Validate a capture bundle, and optionally freeze it before judging.

    python scripts/validate_bundle.py BUNDLE_DIR            # check only
    python scripts/validate_bundle.py BUNDLE_DIR --freeze   # check, then write bundle.lock.json
    python scripts/validate_bundle.py BUNDLE_DIR --json     # machine-readable report

Exit code 0 = valid, 1 = invalid, 2 = unusable input. Deterministic structural
checks only: it cannot tell whether a region name or context value is true.
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402

LOCK_NAME = "bundle.lock.json"

# Region names must be structural ("page header", "chart 2"), never verdicts.
JUDGMENT_WORDS = re.compile(
    r"\b(ai|a\.i\.|slop|sloppy|generic|fake|fabricated|bad|ugly|cheap|suspicious|template[sd]?|"
    r"broken|lazy|boring|cliche|clich[eé]|soulless|gpt|llm|generated)\b",
    re.IGNORECASE,
)
# Text that may reveal production provenance in a blinded bundle.
PROVENANCE_HINTS = re.compile(
    r"\b(generated (by|with)|made with|built with|created (by|with)) (ai|chatgpt|claude|gpt|copilot|"
    r"lovable|bolt|v0|cursor|gemini|midjourney)\b|\bai[- ]generated\b",
    re.IGNORECASE,
)


def check_box(report, box, where):
    if box is None:
        return
    x, y, w, h = box["x"], box["y"], box["width"], box["height"]
    if w <= 0 or h <= 0 or x < 0 or y < 0 or x + w > 1 + 1e-9 or y + h > 1 + 1e-9:
        report.error("box_out_of_bounds", f"{where}: box {box} must have positive size and stay inside [0, 1]")


def check_appearances(report, bundle, appearances, where):
    for ap in appearances:
        if ap["asset_id"] not in bundle.assets:
            report.error("missing_asset_ref", f"{where}: appearance references unknown asset {ap['asset_id']!r}")
        check_box(report, ap.get("box"), where)


def validate(bundle_dir):
    bundle_dir = Path(bundle_dir)
    report = _lib.Report(str(bundle_dir))
    try:
        bundle = _lib.Bundle(bundle_dir)
    except _lib.UsageError as err:
        report.error("unreadable", str(err))
        return report, None
    m = bundle.manifest

    for msg in _lib.schema_errors(m, _lib.load_schema("capture-bundle.schema.json")):
        report.error("schema", msg)
    if report.errors:
        return report, bundle  # cross-reference checks assume the schema shape

    # Unique ids per collection.
    for key, id_field in [("viewports", "viewport_id"), ("states", "state_id"), ("regions", "region_id"),
                          ("assets", "asset_id"), ("text_spans", "span_id"), ("dom_elements", "element_id"),
                          ("interactions", "event_id"), ("source_excerpts", "excerpt_id")]:
        ids = [item[id_field] for item in m[key]]
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        if dupes:
            report.error("duplicate_id", f"{key}: duplicate ids {dupes}")

    for s in m["states"]:
        if s["viewport_id"] is not None and s["viewport_id"] not in bundle.viewports:
            report.error("unknown_viewport", f"state {s['state_id']}: unknown viewport {s['viewport_id']!r}")
        if s["load_status"] in ("partial", "failed") and not m["capability_limits"]:
            report.warn("undeclared_limit", f"state {s['state_id']} is {s['load_status']} but capability_limits is empty")

    for r in m["regions"]:
        if JUDGMENT_WORDS.search(r["name"]) or JUDGMENT_WORDS.search(r["description"]):
            report.error("judgmental_region_name", f"region {r['region_id']}: name/description must be neutral, got {r['name']!r}")
        check_appearances(report, bundle, r["appearances"], f"region {r['region_id']}")

    for a in m["assets"]:
        where = f"asset {a['asset_id']}"
        path = bundle.dir / a["path"]
        if not path.is_file():
            report.error("missing_file", f"{where}: file {a['path']} not found")
            continue
        if _lib.sha256_file(path) != a["sha256"]:
            report.error("hash_mismatch", f"{where}: sha256 does not match {a['path']}")
        try:
            w, h = _lib.image_size(path)
            if (w, h) != (a["pixel_width"], a["pixel_height"]):
                report.error("dimension_mismatch", f"{where}: declared {a['pixel_width']}x{a['pixel_height']}, file is {w}x{h}")
        except _lib.UsageError as err:
            report.error("unreadable_image", f"{where}: {err}")
        if a["state_id"] not in bundle.states:
            report.error("unknown_state", f"{where}: unknown state {a['state_id']!r}")
        vp = bundle.viewports.get(a["viewport_id"]) if a["viewport_id"] else None
        if a["viewport_id"] is not None and vp is None:
            report.error("unknown_viewport", f"{where}: unknown viewport {a['viewport_id']!r}")
        if vp and a["device_pixel_ratio"] is not None and abs(vp["device_pixel_ratio"] - a["device_pixel_ratio"]) > 1e-6:
            report.warn("dpr_mismatch", f"{where}: device_pixel_ratio differs from viewport {vp['viewport_id']}")
        if a["kind"] == "crop":
            if not a["crop_of"] or a["crop_of"]["asset_id"] not in bundle.assets:
                report.error("missing_asset_ref", f"{where}: crop must reference an existing source asset")
            else:
                check_box(report, a["crop_of"]["box"], where)
    if len(m["assets"]) > m["evidence_profile"]["max_images"]:
        report.error("image_budget_exceeded",
                     f"{len(m['assets'])} images exceed the declared budget of {m['evidence_profile']['max_images']}; select views, never truncate silently")

    for t in m["text_spans"]:
        where = f"text span {t['span_id']}"
        if t["region_id"] is not None and t["region_id"] not in bundle.regions:
            report.error("unknown_region", f"{where}: unknown region {t['region_id']!r}")
        if t["state_id"] not in bundle.states:
            report.error("unknown_state", f"{where}: unknown state {t['state_id']!r}")
        if t["element_id"] is not None and t["element_id"] not in bundle.elements:
            report.error("missing_element_ref", f"{where}: unknown element {t['element_id']!r}")
        check_appearances(report, bundle, t["appearances"], where)

    for e in m["dom_elements"]:
        where = f"element {e['element_id']}"
        if e["state_id"] not in bundle.states:
            report.error("unknown_state", f"{where}: unknown state {e['state_id']!r}")
        if e["region_id"] is not None and e["region_id"] not in bundle.regions:
            report.error("unknown_region", f"{where}: unknown region {e['region_id']!r}")
        for sid in e["text_span_ids"]:
            if sid not in bundle.spans:
                report.error("missing_span_ref", f"{where}: unknown text span {sid!r}")

    for ev in m["interactions"]:
        where = f"interaction {ev['event_id']}"
        tgt = ev["target"]
        if tgt["element_id"] is not None and tgt["element_id"] not in bundle.elements:
            report.error("missing_element_ref", f"{where}: unknown target element {tgt['element_id']!r}")
        if tgt["region_id"] is not None and tgt["region_id"] not in bundle.regions:
            report.error("unknown_region", f"{where}: unknown target region {tgt['region_id']!r}")
        if ev["before_state_id"] not in bundle.states:
            report.error("unknown_state", f"{where}: unknown before state {ev['before_state_id']!r}")
        if ev["after_state_id"] is not None and ev["after_state_id"] not in bundle.states:
            report.error("unknown_state", f"{where}: unknown after state {ev['after_state_id']!r}")
        if ev["execution_status"] == "completed" and ev["after_state_id"] is None:
            report.error("malformed_event", f"{where}: a completed interaction needs an after_state_id")
        if ev["execution_status"] != "completed" and ev["after_state_id"] is not None:
            report.warn("malformed_event", f"{where}: status {ev['execution_status']} with an after state; scorers treat it as not completed")
        if ev["before_state_id"] == ev["after_state_id"]:
            report.error("malformed_event", f"{where}: before and after states must differ")

    for x in m["source_excerpts"]:
        where = f"source excerpt {x['excerpt_id']}"
        if x["line_end"] < x["line_start"]:
            report.error("invalid_source_lines", f"{where}: line_end before line_start")
        if _lib.sha256_bytes(x["text"].encode("utf-8")) != x["sha256"]:
            report.error("hash_mismatch", f"{where}: sha256 does not match the excerpt text")
        n_lines = len(x["text"].splitlines()) or 1
        if n_lines != x["line_end"] - x["line_start"] + 1:
            report.warn("line_count_mismatch", f"{where}: {n_lines} lines of text for range {x['line_start']}-{x['line_end']}")
        for rid in x["maps_to_region_ids"]:
            if rid not in bundle.regions:
                report.error("unknown_region", f"{where}: maps to unknown region {rid!r}")

    # Declared modalities must match the evidence actually present.
    present = {
        "screenshot": bool(m["assets"]),
        "text": bool(m["text_spans"]),
        "dom": bool(m["dom_elements"]),
        "computed_style": any(e["computed_style"] for e in m["dom_elements"]),
        "interaction": bool(m["interactions"]),
        "source": bool(m["source_excerpts"]),
    }
    for modality, has in present.items():
        declared = m["modalities"][modality]
        if declared and not has:
            report.error("modality_unsupported", f"modality {modality!r} is declared but the bundle has no such evidence")
        if has and not declared:
            report.error("modality_undeclared", f"bundle contains {modality} evidence but declares it unavailable")

    for key in ("purpose", "genre", "audience"):
        cv = m["context"][key]
        if (cv["status"] == "unknown") != (cv["value"] is None):
            report.error("context_status", f"context.{key}: value must be null exactly when status is 'unknown'")

    if m["blinding"]["profile"] == "blinded":
        if m["capture"]["target_locator"] is not None:
            report.error("blinding_leak", "blinded bundle must not include capture.target_locator")
        for t in m["text_spans"]:
            if PROVENANCE_HINTS.search(t["text"]):
                report.warn("possible_provenance_leak", f"text span {t['span_id']} may reveal production provenance; mask it or record it in known_leakage")
    if re.search(r"(github\.io|https?://|www\.)", m["site_id"]):
        report.error("blinding_leak", "site_id must be opaque, not a URL")

    for item in m["coverage"]["regions"]:
        if item["ref"] not in bundle.regions:
            report.error("unknown_region", f"coverage.regions: unknown region {item['ref']!r}")
    for item in m["coverage"]["viewports"]:
        if item["ref"] not in bundle.viewports:
            report.error("unknown_viewport", f"coverage.viewports: unknown viewport {item['ref']!r}")

    lock = bundle.dir / LOCK_NAME
    if lock.exists():
        locked = _lib.load_json(lock)
        if locked.get("bundle_hash") != bundle.hash:
            report.error("changed_after_freeze", f"{LOCK_NAME} hash does not match the current manifest; the bundle changed after freezing")
    return report, bundle


def freeze(bundle):
    lock = {
        "bundle_id": bundle.bundle_id,
        "bundle_hash": bundle.hash,
        "frozen_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "files": {a["path"]: a["sha256"] for a in bundle.manifest["assets"]},
    }
    (bundle.dir / LOCK_NAME).write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
    return lock


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("bundle", help="bundle directory (or its manifest.json)")
    parser.add_argument("--freeze", action="store_true", help=f"write {LOCK_NAME} when valid")
    parser.add_argument("--json", action="store_true", help="print a JSON report")
    args = parser.parse_args(argv)
    report, bundle = validate(args.bundle)
    if args.freeze and report.ok:
        lock = freeze(bundle)
        report.warnings.append(("frozen", f"wrote {LOCK_NAME} with bundle_hash {lock['bundle_hash']}"))
    if args.json:
        print(json.dumps(report.as_dict(), indent=2))
    else:
        report.print()
    return 0 if report.ok else 1


if __name__ == "__main__":
    _lib.run_main(main)
