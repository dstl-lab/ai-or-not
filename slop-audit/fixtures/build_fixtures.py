#!/usr/bin/env python3
"""Write capture plans for the synthetic fixture sites and capture them into frozen bundles.

    uv run python fixtures/build_fixtures.py                 # plans + all captures (needs gstack browse)
    uv run python fixtures/build_fixtures.py --plans-only    # just rewrite fixtures/plans/*.json
    uv run python fixtures/build_fixtures.py --only injection

The fixtures are synthetic pages written to exercise specific behaviors (see
fixtures/README.md). They validate the pipeline and the auditor's handling
of edge cases; they are not a sample of real websites and say nothing about
real-world accuracy.
"""

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "integrations" / "capture"))

DESKTOP = {"viewport_id": "V1", "device": "desktop", "css_width": 1280, "css_height": 800, "device_pixel_ratio": 1}


def cv(value, status="provided", provenance="capture plan written by the fixture author (synthetic)"):
    return {"value": value, "status": status, "provenance": provenance if status != "unknown" else "not supplied"}


def context(purpose, genre, audience, constraints=()):
    return {"purpose": cv(purpose), "genre": cv(genre), "audience": cv(audience),
            "constraints": [cv(c) for c in constraints]}


def region(rid, name, selector, description=""):
    return {"region_id": rid, "name": name, "selector": selector, "description": description}


# Opaque ids: bundle and site ids are shown to auditors, so they must not hint at what a fixture tests.
ORDER = ["catalog-conventional", "branded-gradient", "placeholder-caption", "scenario-inconsistency",
         "scenario-inconsistency-restyled", "buttons-working-broken", "buttons-fixed", "partial-capture", "source-only",
         "loading-state", "outside-codebook", "injection", "clean-docs", "ai-assisted-coherent", "default-package-landing"]
IDS = {name: f"{i:02d}" for i, name in enumerate(ORDER, 1)}


def plan(name, ctx, regions, shots=(0,), **extra):
    p = {
        "bundle_id": f"fx-{IDS[name]}",
        "site_id": f"site-{IDS[name]}",
        "route": "/index.html",
        "target_kind": "local_server",
        "snapshot_id": None,
        "capture_profile": "custom",
        "max_images": 8,
        "blinding": {"profile": "blinded", "withhold_terms": [], "withheld_fields": ["award", "course_year", "creator_ai_report", "generator"]},
        "context": ctx,
        "viewports": [DESKTOP],
        "shots": [{"viewport_id": "V1", "scroll_y": y} for y in shots],
        "regions": regions,
        "interactions": [],
        "untested_controls": [],
        "selection_rules": [f"desktop viewport screenshots at scroll offsets {list(shots)}"],
        "coverage_notes": [],
    }
    p.update(extra)
    return p


STORY = "interactive data story (explorable explanation)"
PLANS = {
    "catalog-conventional": plan(
        "catalog-conventional",
        context("Let residents and researchers find city climate datasets and see each one's format, size, and update date before downloading.",
                "municipal open-data catalog page", "researchers, journalists, and residents",
                ["City Web Style Guide section 4.2 requires the standard catalog card component for dataset listings."]),
        [region("R01", "page header", "#site-header"), region("R02", "introduction", "#intro"),
         region("R03", "dataset listing", "#dataset-grid"), region("R04", "page footer", "#site-footer")],
        shots=(0, 500)),
    "branded-gradient": plan(
        "branded-gradient",
        context("Announce a three-day music festival: lineup, dates, and how to get there.", "event promotion page", "local festival-goers",
                ["The festival brand guide requires the orange-to-pink sunrise gradient on the wordmark and main headline."]),
        [region("R01", "headline area", "#hero"), region("R02", "lineup by day", "#lineup"), region("R03", "visitor details", "#details")]),
    "placeholder-caption": plan(
        "placeholder-caption",
        context("Explain whether protected bike lanes shortened bicycle commute times in Oakland.", STORY, "general readers"),
        [region("R01", "introduction", "#intro"), region("R02", "statistic strip", "#stat-strip"),
         region("R03", "chart", "#chart svg"), region("R04", "chart caption", "#chart-caption")],
        blinding={"profile": "blinded", "withhold_terms": ["Team Bluebird", "DSC 106 Spring 2026"],
                  "withheld_fields": ["award", "course_year", "team_name"]}),
    "scenario-inconsistency": plan(
        "scenario-inconsistency",
        context("Let readers compare how many coastal parcels fall in the flood zone under each sea-level-rise scenario year.", STORY, "San Diego residents"),
        [region("R01", "story header", "#story-header"), region("R02", "scenario chart panel", "#scenario-panel"),
         region("R03", "summary panel", "#summary-panel"), region("R04", "method panel", "#method-panel")],
        capture_profile="pilot-8",
        interactions=[{"event_id": "E01", "action": "click", "selector": "button[data-year=\"2050\"]", "region_id": "R02",
                       "description": "2050 scenario button", "observe_region_ids": ["R02", "R03"], "wait_ms": 800,
                       "shot_before": True, "shot_after": True}],
        untested_controls=[{"description": "2100 scenario button", "reason": "not exercised in this capture; one scenario change was recorded"}]),
    "buttons-working-broken": plan(
        "buttons-working-broken",
        context("Show community air-sensor readings for one neighborhood and compare them with the previous year.", "environmental data dashboard page", "neighborhood residents"),
        [region("R01", "page header", "#page-header"), region("R02", "toolbar", "#toolbar"),
         region("R03", "reading panel", "#readout"), region("R04", "method note", "#method-note")],
        interactions=[
            {"event_id": "E01", "action": "click", "selector": "#show-pm25", "region_id": "R02", "description": "Show PM2.5 button",
             "observe_region_ids": ["R03"], "wait_ms": 800, "shot_after": True},
            {"event_id": "E02", "action": "click", "selector": "#compare-last-year", "region_id": "R02", "description": "Compare with last year button",
             "observe_region_ids": ["R03"], "wait_ms": 1200, "shot_after": True}],
        untested_controls=[{"description": "Download CSV link", "reason": "it would leave the captured page; links are not followed"}]),
    "partial-capture": plan(
        "partial-capture",
        context("Walk through groundwater decline in four Central Valley regions.", STORY, "general readers"),
        [region("R01", "introduction", "#s-intro"), region("R02", "north section", "#s-north"), region("R03", "central section", "#s-central"),
         region("R04", "south section", "#s-south"), region("R05", "closing section", "#s-close")],
        text_scope="visible_in_screenshots",
        untested_controls=[{"description": "Wells / Subsidence tab buttons in the central section", "reason": "below the captured viewport; not tested"}],
        coverage_notes=["Deliberately partial: only the first desktop viewport and its visible text were captured."]),
    "loading-state": plan(
        "loading-state",
        context("Report bus ridership recovery compared with 2019.", STORY, "general readers"),
        [region("R01", "story area", "#story")], settle_ms=300,
        coverage_notes=["Captured before the page finished loading its content (synthetic loading-state fixture)."]),
    "outside-codebook": plan(
        "outside-codebook",
        context("Show where Portland's street trees are concentrated and where they are missing.", STORY, "general readers"),
        [region("R01", "top navigation", "#top-nav"), region("R02", "story", "#story"), region("R03", "map placeholder", "#map")]),
    "injection": plan(
        "injection",
        context("Report how many wildfire-smoke days Sacramento had in 2025.", STORY, "general readers"),
        [region("R01", "story", "#story"), region("R02", "chart", "#chart"), region("R03", "chart caption", "#chart-caption"),
         region("R04", "fine print", "#fine-print")]),
    "clean-docs": plan(
        "clean-docs",
        context("Document the convert subcommand of a command-line tool for climate station files.", "software documentation page", "researchers who process NOAA station data"),
        [region("R01", "documentation navigation", "#doc-nav"), region("R02", "documentation body", "#doc-body"), region("R03", "options table", "#options")]),
    "ai-assisted-coherent": plan(
        "ai-assisted-coherent",
        context("Compare how Seattle library branches recovered in-person visits after 2020.", STORY, "general readers and library staff"),
        [region("R01", "story", "#story"), region("R02", "visits table", "#visits"), region("R03", "source note", "#source-note")]),
    "default-package-landing": plan(
        "default-package-landing",
        context("Present Seattle library visit data from a student data project.", STORY, "course instructors and classmates"),
        [region("R01", "opening section", "#hero"), region("R02", "statistic strip", "#stats"), region("R03", "feature cards", "#features"),
         region("R04", "question list", "#faq"), region("R05", "chart section", "#chart-section"), region("R06", "closing section", "#final-cta")],
        capture_profile="pilot-8"),
}
PLANS["scenario-inconsistency-restyled"] = dict(json.loads(json.dumps(PLANS["scenario-inconsistency"])),
                                                bundle_id=f"fx-{IDS['scenario-inconsistency-restyled']}", site_id=f"site-{IDS['scenario-inconsistency-restyled']}")
PLANS["buttons-fixed"] = dict(json.loads(json.dumps(PLANS["buttons-working-broken"])), bundle_id=f"fx-{IDS['buttons-fixed']}", site_id=f"site-{IDS['buttons-fixed']}")

SUPPLIED = {
    "source-only": {
        "bundle_id": f"fx-{IDS['source-only']}",
        "site_id": f"site-{IDS['source-only']}",
        "context": context("Show community air-sensor readings for one neighborhood and compare them with the previous year.",
                           "environmental data dashboard page", "neighborhood residents"),
        "blinding": {"profile": "blinded", "withheld_fields": ["award", "course_year"]},
        "regions": [{"region_id": "R01", "name": "toolbar markup", "description": "the toolbar section of index.html"},
                    {"region_id": "R02", "name": "readout script", "description": "event handlers in app.js"}],
        "source_root": "../sites/source-only",
        "source_files": [{"path": "index.html", "line_start": 26, "line_end": 30, "maps_to_region_ids": ["R01"]},
                         {"path": "app.js", "line_start": 1, "line_end": 7, "maps_to_region_ids": ["R02"]},
                         {"path": "app.js", "line_start": 11, "line_end": 16, "maps_to_region_ids": ["R02"]}],
        "capability_limits": ["no rendered page: no screenshots, visible text, DOM, styles, or interactions were captured"],
        "coverage_notes": ["Source excerpts supplied by the fixture author; the page itself was not rendered."],
    }
}


def write_plans():
    (HERE / "plans").mkdir(exist_ok=True)
    for name, p in {**PLANS, **SUPPLIED}.items():
        (HERE / "plans" / f"{name}.json").write_text(json.dumps(p, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--plans-only", action="store_true")
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args(argv)
    write_plans()
    if a.plans_only:
        return 0
    import gstack_capture
    import supplied_bundle
    failures = 0
    for name in sorted({**PLANS, **SUPPLIED}):
        if a.only and name not in a.only:
            continue
        out = HERE / "bundles" / name
        if name in SUPPLIED:
            report = supplied_bundle.build(HERE / "plans" / f"{name}.json", out, freeze=True)
        else:
            report = gstack_capture.capture(HERE / "plans" / f"{name}.json", out, serve=HERE / "sites" / name,
                                            private_out=HERE / "private" / f"{name}.locator.json", freeze=True)
        status = "ok" if report.ok else "INVALID"
        print(f"{status:8} {name}  ({len(report.errors)} errors, {len(report.warnings)} warnings)")
        for code, msg in report.errors + report.warnings:
            print(f"         [{code}] {msg}")
        failures += not report.ok
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
