#!/usr/bin/env python3
"""Build a capture bundle from supplied artifacts (no browser).

    python integrations/capture/supplied_bundle.py SPEC.json --out BUNDLE_DIR [--freeze]

For evidence someone hands over: source files with line ranges, and
optionally screenshots and transcribed text. Each screenshot must come with
its viewport and scroll metadata; nothing is guessed. A spec with no
screenshots produces a source-only (or text-only) bundle whose modalities say
so, so auditors cannot claim visual evidence.

SPEC fields: bundle_id, site_id, context, blinding, regions [{region_id, name,
description}], source_root, source_files [{path, line_start, line_end,
maps_to_region_ids}], optional viewports, screenshots [{path, viewport_id,
scroll_y, state_id}], text_spans [{region_id, text}], capability_limits,
coverage_notes.
"""

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "website-slop-audit" / "scripts"))
import _lib  # noqa: E402
import validate_bundle  # noqa: E402


def build(spec_path, out_dir, freeze=False):
    spec = _lib.load_json(spec_path)
    base = Path(spec_path).parent
    out = Path(out_dir)
    if out.exists():
        shutil.rmtree(out)
    (out / "assets").mkdir(parents=True)
    states = [{"state_id": "S01", "route": spec.get("route", "/"), "viewport_id": None, "kind": "supplied",
               "load_status": "unknown", "fonts_loaded": None, "description": "evidence supplied without a live capture"}]
    assets = []
    for i, shot in enumerate(spec.get("screenshots", []), 1):
        src = base / shot["path"]
        aid = f"A{i:02d}"
        rel = f"assets/{aid}{src.suffix.lower()}"
        shutil.copyfile(src, out / rel)
        w, h = _lib.image_size(out / rel)
        vp = next(v for v in spec["viewports"] if v["viewport_id"] == shot["viewport_id"])
        assets.append({"asset_id": aid, "kind": "viewport_screenshot", "path": rel, "sha256": _lib.sha256_file(out / rel),
                       "media_type": "image/png" if rel.endswith(".png") else "image/jpeg", "pixel_width": w, "pixel_height": h,
                       "viewport_id": vp["viewport_id"], "device_pixel_ratio": vp["device_pixel_ratio"], "route": spec.get("route", "/"),
                       "scroll_x": 0, "scroll_y": shot.get("scroll_y", 0), "state_id": shot.get("state_id", "S01"), "crop_of": None})
    excerpts = []
    root = base / spec.get("source_root", ".")
    for i, src in enumerate(spec.get("source_files", []), 1):
        lines = (root / src["path"]).read_text(encoding="utf-8").splitlines()
        text = "\n".join(lines[src["line_start"] - 1:src["line_end"]])
        excerpts.append({"excerpt_id": f"SX{i:02d}", "path": src["path"], "line_start": src["line_start"], "line_end": src["line_end"],
                         "sha256": _lib.sha256_bytes(text.encode("utf-8")), "language": Path(src["path"]).suffix.lstrip(".") or "text",
                         "text": text, "maps_to_region_ids": src.get("maps_to_region_ids", [])})
    spans = [{"span_id": f"T{i:03d}", "region_id": t.get("region_id"), "state_id": "S01", "text": t["text"],
              "source": "supplied", "element_id": None, "appearances": []} for i, t in enumerate(spec.get("text_spans", []), 1)]
    manifest = {
        "schema_version": "website-slop-audit/capture-bundle/0.1",
        "bundle_id": spec["bundle_id"],
        "site_id": spec["site_id"],
        "capture": {"captured_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "protocol_version": "capture-protocol/0.1",
                    "adapter": {"name": "supplied_bundle.py", "version": "0.1.0", "browser": None},
                    "target_kind": "supplied_artifacts", "target_locator": None, "snapshot_id": spec.get("snapshot_id"),
                    "notes": spec.get("notes", [])},
        "evidence_profile": {"capture_profile": "custom", "max_images": max(len(assets), spec.get("max_images", 0)),
                             "selection_rules_applied": ["supplied artifacts only; no live capture"]},
        "modalities": {"screenshot": bool(assets), "text": bool(spans), "dom": False, "computed_style": False,
                       "interaction": False, "source": bool(excerpts)},
        "capability_limits": spec.get("capability_limits", []),
        "context": spec["context"],
        "blinding": {"profile": spec["blinding"]["profile"], "transformations": [], "withheld_fields": spec["blinding"].get("withheld_fields", []), "known_leakage": []},
        "viewports": spec.get("viewports", []),
        "states": states,
        "regions": [{"region_id": r["region_id"], "name": r["name"], "route": spec.get("route", "/"), "description": r.get("description", ""),
                     "selector": None, "appearances": []} for r in spec["regions"]],
        "assets": assets,
        "text_spans": spans,
        "dom_elements": [],
        "interactions": [],
        "source_excerpts": excerpts,
        "coverage": {"routes": [{"ref": spec.get("route", "/"), "status": "partial", "reason": "supplied artifacts only; the page was not rendered"}],
                     "regions": [{"ref": r["region_id"], "status": "partial", "reason": "described by supplied source only"} for r in spec["regions"]],
                     "viewports": [], "interactions": [{"ref": "all controls", "status": "untested", "reason": "no live page; behavior cannot be observed"}],
                     "notes": spec.get("coverage_notes", [])},
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report, bundle = validate_bundle.validate(out)
    if report.ok and freeze:
        validate_bundle.freeze(bundle)
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("spec")
    p.add_argument("--out", required=True)
    p.add_argument("--freeze", action="store_true")
    a = p.parse_args(argv)
    report = build(a.spec, a.out, a.freeze)
    report.print()
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
