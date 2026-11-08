#!/usr/bin/env python3
"""Write the developer reference annotations and the worked example audits.

    uv run python fixtures/references.py

Annotations (fixtures/annotations/*.json) are stage 'synthetic_development':
written by the tool developer to test scoring and to grade development runs.
They are not an independent human reference. Example audits
(website-slop-audit/examples/) show valid outputs, including one with zero
findings. Evidence ids are looked up by text in the frozen bundles, so the
files stay valid after a re-capture.
"""

import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SKILL = ROOT / "website-slop-audit"
sys.path.insert(0, str(SKILL / "scripts"))
import _lib  # noqa: E402
import render_report  # noqa: E402
import validate_audit  # noqa: E402

RUBRIC = _lib.load_codebook()["rubric_version"]
DEV = {"annotator_id": "dev-1", "role": "developer",
       "expertise": {"design_years": None, "visualization_years": None, "web_development_years": None,
                     "relevant_training": ["tool developer; wrote the fixtures"], "notes": "not an independent annotator"}}


class B:
    def __init__(self, name):
        self.name = name
        self.dir = HERE / "bundles" / name
        self.b = _lib.Bundle(self.dir)

    def span(self, state, contains):
        for s in self.b.manifest["text_spans"]:
            if s["state_id"] == state and contains in s["text"]:
                return s
        raise KeyError(f"{self.name}: no span in {state} containing {contains!r}")

    def box(self, span):
        ap = span["appearances"][0] if span["appearances"] else None
        return (ap["asset_id"], ap["box"]) if ap else (None, None)

    def region_box(self, region, asset):
        for ap in self.b.regions[region]["appearances"]:
            if ap["asset_id"] == asset:
                return ap["box"]
        return None

    def event(self, eid):
        return self.b.events[eid]


def loc(region, state, asset=None, box=None, selector=None):
    return {"region_id": region, "state_id": state, "asset_id": asset, "box": box, "selector": selector, "source_ref": None}


def ann_loc(region, state, asset=None, box=None):
    return {"region_id": region, "state_id": state, "asset_id": asset, "box": box}


def item(aid, fid, scope, locations, disposition, assoc, evidence, consequence="none_identified", exception=None, phenomenon=None):
    return {"annotation_id": aid, "annotator_id": "dev-1", "feature_id": fid, "phenomenon_id": phenomenon, "scope": scope,
            "locations": locations, "disposition": disposition, "observed_evidence": evidence, "confidence": "high",
            "slop_association": assoc, "contextual_exception": exception, "consequence": consequence,
            "uncertainty": "developer reference for a synthetic fixture"}


def annotation(bx, profile_id, scopes, items, notes=()):
    feats = [f["id"] for f in _lib.profile_features(profile_id)]
    return {"schema_version": "website-slop-audit/annotation/0.1", "rubric_version": _lib.load_codebook()["rubric_version"],
            "annotation_set_id": f"dev-{bx.name}"[:64], "bundle_id": bx.b.bundle_id, "bundle_hash": bx.b.hash,
            "condition": "rubric_guided", "stage": "synthetic_development", "annotators": [DEV],
            "scopes": [dict(s, feature_ids=s.get("feature_ids", feats)) for s in scopes], "items": items,
            "adjudication": None, "notes": ["Synthetic development reference written by the fixture author; plumbing and smoke tests only."] + list(notes)}


def coverage_features(profile_id, modalities, overrides=None):
    overrides = overrides or {}
    out = []
    for f in _lib.profile_features(profile_id):
        if f["id"] in overrides:
            status, reason = overrides[f["id"]]
        elif _lib.feature_assessable(f, modalities):
            status, reason = "assessed", "checked against the codebook entry"
        else:
            need = " or ".join("+".join(s) for s in f["modality_sets"])
            status, reason = "unassessed", f"needs {need}, which this bundle does not contain"
        out.append({"feature_id": f["id"], "status": status, "reason": reason})
    return out


def build_annotations():
    out = HERE / "annotations"
    out.mkdir(exist_ok=True)
    sets = {}

    s = B("scenario-inconsistency")
    title, summary = s.span("S03", "Parcels in the flood zone, 2050"), s.span("S03", "In 2020, 4% of La Jolla")
    sets[s.name] = annotation(s, "multimodal-datastory",
        [{"scope_id": "all", "region_ids": ["R01", "R02", "R03", "R04"], "state_ids": ["S01", "S02", "S03"], "fully_annotated": True}],
        [item("a1", "INT-02", "cross-region", [ann_loc("R02", "S03", *s.box(title)), ann_loc("R03", "S03", *s.box(summary))],
              "accepted_slop_candidate", "moderate", "After E01 the chart title reads 2050 while the summary still describes 2020.", "moderate"),
         item("a2", "LAY-01", "repeated-group", [ann_loc("R02", "S01"), ann_loc("R03", "S01"), ann_loc("R04", "S01")],
              "contextual_exception", "weak", "Three panels share one white rounded-card style.",
              exception="Panels hold distinct roles with clear headings; card panels are conventional for data stories.")])

    s = B("catalog-conventional")
    sets[s.name] = annotation(s, "multimodal-core",
        [{"scope_id": "all", "region_ids": ["R01", "R02", "R03", "R04"], "state_ids": ["S01"], "fully_annotated": True}],
        [item("a1", "LAY-01", "repeated-group", [ann_loc("R03", "S01", "A01", s.region_box("R03", "A01"))], "contextual_exception", "none",
              "Nine identical dataset cards.", exception="Parallel catalog items; the style guide requires the card component.")])

    s = B("branded-gradient")
    head = s.span("S01", "Sunrise Fest 2027")
    sets[s.name] = annotation(s, "multimodal-core",
        [{"scope_id": "all", "region_ids": ["R01", "R02", "R03"], "state_ids": ["S01"], "fully_annotated": True}],
        [item("a1", "VIS-02", "region", [ann_loc("R01", "S01", *s.box(head))], "contextual_exception", "weak",
              "Gradient-filled headline.", exception="The brand guide requires the sunrise gradient on the wordmark.")])

    s = B("buttons-working-broken")
    e2 = s.event("E02")
    sets[s.name] = annotation(s, "multimodal-core",
        [{"scope_id": "all", "region_ids": ["R01", "R02", "R03", "R04"], "state_ids": ["S01", "S02", "S03"], "fully_annotated": True}],
        [item("a1", "INT-01", "region", [ann_loc("R02", e2["before_state_id"]), ann_loc("R02", e2["after_state_id"])],
              "accepted_slop_candidate", "weak", "Compare with last year: completed click, no change (E02).", "moderate")])

    s = B("default-package-landing")
    hero = s.span("S01", "Our platform empowers you")
    sets[s.name] = annotation(s, "multimodal-datastory",
        [{"scope_id": "all", "region_ids": ["R01", "R02", "R03", "R04", "R05", "R06"], "state_ids": ["S01", "S02"], "fully_annotated": True}],
        [item("a1", "VIS-01", "page-pattern", [ann_loc(r, "S01") for r in ("R01", "R02", "R03", "R06")], "accepted_slop_candidate", "moderate",
              "Purple-blue glow over near-black, glassy panels, gradient buttons in every section; unrelated to library data."),
         item("a2", "VIS-02", "repeated-group", [ann_loc(r, "S01") for r in ("R01", "R03", "R04", "R05")], "accepted_slop_candidate", "moderate",
              "Tracked caps eyebrows on every section, gradient headline word, 01/02/03 numbering on non-sequential sections."),
         item("a3", "VIS-03", "repeated-group", [ann_loc("R03", "S01")], "accepted_slop_candidate", "moderate",
              "Identical sparkle icon tiles on cards with unrelated content (including team credits)."),
         item("a4", "SUB-03", "repeated-group", [ann_loc("R02", "S01")], "accepted_slop_candidate", "moderate",
              "10x / 99% / 24/7 tiles without units, source, or link to the data."),
         item("a5", "TXT-01", "region", [ann_loc("R01", "S01", *s.box(hero))], "accepted_slop_candidate", "moderate",
              "Opening copy names neither the library nor the data."),
         item("a6", "DAT-04", "page-pattern", [ann_loc(r, "S01") for r in ("R01", "R02", "R03", "R04", "R05")], "accepted_slop_candidate", "moderate",
              "Generic scaffolding precedes one unlabeled chart with a two-word caption.", "moderate"),
         item("a7", "DAT-03", "region", [ann_loc("R05", "S01")], "accepted_slop_candidate", "weak",
              "The chart has no units, years, or source in the captured scope.", "moderate"),
         item("a8", "LAY-01", "repeated-group", [ann_loc("R03", "S01")], "accepted_slop_candidate", "weak",
              "The team credit is set as a third feature card, identical to two product-benefit cards.")],
        notes=["LAY-02 and DAT-04 overlap here; DAT-04 is the primary code in the data-story profile (codebook 0.1.1 boundary rule).",
               "Revised 2026-11-08 after reviewing iteration-1 development output: a8 (LAY-01 team-credit card) added because it matches the codebook's own "
               "positive example and was omitted by mistake. Development data only; a held-out reference must never be revised after seeing model output."])

    s = B("injection")
    todo = s.span("S01", "TODO: add data source")
    sets[s.name] = annotation(s, "multimodal-datastory",
        [{"scope_id": "all", "region_ids": ["R01", "R02", "R03", "R04"], "state_ids": ["S01"], "fully_annotated": True}],
        [item("a1", "SUB-01", "region", [ann_loc("R03", "S01", *s.box(todo))], "accepted_slop_candidate", "weak",
              "Literal TODO placeholder in the chart caption.", "moderate"),
         item("a2", "DAT-03", "region", [ann_loc("R02", "S01")], "accepted_slop_candidate", "weak",
              "Chart lacks source and years (the caption admits it).", "moderate", phenomenon="caption-gap")])

    for name, data in sets.items():
        errs = _lib.schema_errors(data, _lib.load_schema("annotation.schema.json"))
        if errs:
            raise SystemExit(f"{name}: {errs[:3]}")
        (out / f"{name}.json").write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return sets


def example_audits():
    """Worked examples use fixtures that no development eval case uses, so evals cannot copy them."""
    ex = SKILL / "examples"
    for sub in ("bundles", "audits", "reports"):
        if (ex / sub).exists():
            shutil.rmtree(ex / sub)
        (ex / sub).mkdir(parents=True)
    audits = {}

    s = B("placeholder-caption")
    prof = "multimodal-datastory"
    mods = _lib.available_modalities(s.b.manifest, prof)
    cap, stat, statlabel = s.span("S01", "Lorem ipsum"), s.span("S01", "42%"), s.span("S01", "faster commutes")
    tel_before, tel_after = s.span("S01", "25 min"), s.span("S01", "19 min")
    ca, cb = s.box(cap)
    sa, sb_ = s.box(stat)
    audits[s.name] = {
        "schema_version": "website-slop-audit/audit/0.1", "rubric_version": RUBRIC, "audit_id": "example-placeholder-caption",
        "bundle_id": s.b.bundle_id, "bundle_hash": s.b.hash, "analysis_profile": prof, "status": "completed",
        "inventory": {"genre": {"value": "interactive data story", "basis": "provided"},
                      "purpose": {"value": "explain whether protected bike lanes shortened bicycle commute times in Oakland", "basis": "provided"},
                      "audience": {"value": "general readers", "basis": "provided"},
                      "main_task": {"value": "read the before/after commute chart and its takeaway", "basis": "inferred"},
                      "structure": [{"region_id": "R01", "role": "title, introduction, masked byline"}, {"region_id": "R02", "role": "two headline statistics"},
                                    {"region_id": "R03", "role": "bar chart of median commute minutes by corridor"}, {"region_id": "R04", "role": "chart caption"}]},
        "coverage": {"assessed_modalities": sorted(mods),
                     "unassessed_modalities": [{"modality": "interaction", "reason": "no interactions were recorded"},
                                               {"modality": "source", "reason": "no source excerpts supplied"}],
                     "regions": [{"region_id": r, "state_ids": ["S01"], "status": "assessed", "reason": "visible in the desktop screenshot"} for r in ("R01", "R02", "R03", "R04")],
                     "features": coverage_features(prof, mods)},
        "findings": [
            {"finding_id": "F001", "feature_id": "SUB-01", "phenomenon_id": "P001", "secondary_tags": [], "scope": "region",
             "observation": "literal_placeholder: the chart caption is template text asking to be replaced, so the chart has no stated takeaway.",
             "locations": [loc("R04", "S01", ca, cb)],
             "evidence": [{"kind": "text", "ref_id": cap["span_id"], "description": "The caption text.", "quote": "Lorem ipsum dolor sit amet — replace with key insight before publishing."},
                          {"kind": "screenshot", "ref_id": ca, "description": "The caption under the chart.", "quote": None}],
             "observation_confidence": {"level": "high", "reason": "Exact text captured from the DOM and visible in the screenshot."},
             "slop_association": {"level": "moderate", "reason": "A placeholder left in a finished-looking story reads as unattended scaffolding; it is equally typical of a hurried human draft."},
             "contextual_fit": {"level": "inappropriate", "reason": "The caption is where the story's takeaway belongs."},
             "communication_or_interaction_consequence": {"level": "moderate", "reason": "Readers get no interpretation of the chart."},
             "alternative_explanations": ["Unfinished draft published early", "Template caption never replaced"],
             "codebook_evidence_status": "research_hypothesis", "quality_to_slop_rationale": None,
             "limitations": ["Does not show who or what wrote the page."]},
            {"finding_id": "F002", "feature_id": "DAT-01", "phenomenon_id": "P002", "secondary_tags": ["SUB-01"], "scope": "cross-region",
             "observation": "The statistic strip claims '42% faster commutes', but the chart's own labeled medians fall by 14% to 24% (for example 25 to 19 minutes), and no basis for 42% appears in the inspected scope.",
             "locations": [loc("R02", "S01", sa, sb_), loc("R03", "S01", "A01", s.region_box("R03", "A01"))],
             "evidence": [{"kind": "text", "ref_id": stat["span_id"], "description": "The headline statistic.", "quote": "42%"},
                          {"kind": "text", "ref_id": statlabel["span_id"], "description": "Its label.", "quote": "faster commutes"},
                          {"kind": "text", "ref_id": tel_before["span_id"], "description": "Telegraph Ave before.", "quote": "25 min"},
                          {"kind": "text", "ref_id": tel_after["span_id"], "description": "Telegraph Ave after.", "quote": "19 min"}],
             "observation_confidence": {"level": "high", "reason": "All values are captured as text spans."},
             "slop_association": {"level": "weak", "reason": "An unsupported headline number is a candidate metric-theater cue, but a different calculation (for example speed rather than time) could exist outside the captured page."},
             "contextual_fit": {"level": "questionable", "reason": "The number frames the story but is not tied to the shown data."},
             "communication_or_interaction_consequence": {"level": "moderate", "reason": "The headline overstates what the chart shows."},
             "alternative_explanations": ["Computed on a different measure or corridor set", "Left over from an earlier draft", "Arithmetic error"],
             "codebook_evidence_status": "research_hypothesis", "quality_to_slop_rationale": None,
             "limitations": ["basis_not_located: only the captured page was inspected; the claim is not called fabricated."]}],
        "contextual_exceptions": [], "quality_observations": [], "exploratory_candidates": [], "untrusted_instructions_observed": [],
        "summary": {"text": "Two substance problems: a literal placeholder caption under the main chart, and a headline statistic (42% faster) that the chart's own values do not support. Typography and palette are plain and showed no default-package pattern. The byline was masked for blinding.",
                    "major_limitations": ["Single desktop screenshot", "No interactions or source", "Synthetic development fixture"]},
    }

    s = B("clean-docs")
    prof = "multimodal-core"
    mods = _lib.available_modalities(s.b.manifest, prof)
    audits[s.name] = {
        "schema_version": "website-slop-audit/audit/0.1", "rubric_version": RUBRIC, "audit_id": "example-clean-docs",
        "bundle_id": s.b.bundle_id, "bundle_hash": s.b.hash, "analysis_profile": prof, "status": "completed",
        "inventory": {"genre": {"value": "software documentation page", "basis": "provided"},
                      "purpose": {"value": "document the convert subcommand of a climate-data command-line tool", "basis": "provided"},
                      "audience": {"value": "researchers who process NOAA station data", "basis": "provided"},
                      "main_task": {"value": "look up usage, options, and exit codes", "basis": "inferred"},
                      "structure": [{"region_id": "R01", "role": "section navigation"}, {"region_id": "R02", "role": "command description and usage"},
                                    {"region_id": "R03", "role": "options reference table"}]},
        "coverage": {"assessed_modalities": sorted(mods),
                     "unassessed_modalities": [{"modality": "interaction", "reason": "no interactions were recorded"},
                                               {"modality": "source", "reason": "no source excerpts supplied"}],
                     "regions": [{"region_id": r, "state_ids": ["S01"], "status": "assessed", "reason": "visible in the desktop screenshot"} for r in ("R01", "R02", "R03")],
                     "features": coverage_features(prof, mods)},
        "findings": [], "contextual_exceptions": [], "quality_observations": [], "exploratory_candidates": [], "untrusted_instructions_observed": [],
        "summary": {"text": "No accepted findings and no candidate cues worth recording as exceptions. The page is specific (real flags, defaults, file formats, and exit codes) and its conventional documentation layout matches its job.",
                    "major_limitations": ["Interaction and source checks were not possible", "Synthetic development fixture"]},
    }

    for name, audit in audits.items():
        dst = ex / "bundles" / name
        shutil.copytree(HERE / "bundles" / name, dst)
        path = ex / "audits" / f"{name}.audit.json"
        path.write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        report = validate_audit.validate(path, dst)
        if not report.ok or report.warnings:
            report.print()
            raise SystemExit(f"example audit {name} is invalid")
        for suffix in (".html", ".md"):
            render_report.main([str(path), "--bundle", str(dst), "--out", str(ex / "reports" / f"{name}.report{suffix}")])


def reference_audits():
    """Test-only audits (outside the skill package) used as known-good inputs by the test suite."""
    out = HERE / "audits"
    out.mkdir(exist_ok=True)
    s = B("scenario-inconsistency")
    prof = "multimodal-datastory"
    mods = _lib.available_modalities(s.b.manifest, prof)
    title, summary = s.span("S03", "Parcels in the flood zone, 2050"), s.span("S03", "In 2020, 4% of La Jolla")
    ta, tb = s.box(title)
    sa, sb_ = s.box(summary)
    audit = {
        "schema_version": "website-slop-audit/audit/0.1", "rubric_version": RUBRIC, "audit_id": "reference-scenario-inconsistency",
        "bundle_id": s.b.bundle_id, "bundle_hash": s.b.hash, "analysis_profile": prof, "status": "completed",
        "inventory": {"genre": {"value": "interactive data story", "basis": "provided"},
                      "purpose": {"value": "compare coastal flood exposure across sea-level-rise scenario years", "basis": "provided"},
                      "audience": {"value": "San Diego residents", "basis": "provided"},
                      "main_task": {"value": "switch scenario years and read the chart and summary", "basis": "inferred"},
                      "structure": [{"region_id": "R01", "role": "title and dek"}, {"region_id": "R02", "role": "scenario buttons and bar chart"},
                                    {"region_id": "R03", "role": "written summary of the chart"}, {"region_id": "R04", "role": "method note"}]},
        "coverage": {"assessed_modalities": sorted(mods), "unassessed_modalities": [{"modality": "source", "reason": "no source excerpts supplied"}],
                     "regions": [{"region_id": r, "state_ids": ["S01", "S03"], "status": "assessed", "reason": "visible in desktop screenshots"}
                                 for r in ("R01", "R02", "R03", "R04")],
                     "features": coverage_features(prof, mods)},
        "findings": [{
            "finding_id": "F001", "feature_id": "INT-02", "phenomenon_id": "P001", "secondary_tags": ["DAT-01"], "scope": "cross-region",
            "observation": "After the recorded switch to the 2050 scenario, the chart shows 2050 values while the linked summary still describes 2020 percentages.",
            "locations": [loc("R02", "S03", ta, tb), loc("R03", "S03", sa, sb_)],
            "evidence": [{"kind": "interaction", "ref_id": "E01", "description": "Click on the 2050 button completed; chart title and values changed.", "quote": None},
                         {"kind": "text", "ref_id": title["span_id"], "description": "Chart title in the after state.", "quote": "Parcels in the flood zone, 2050"},
                         {"kind": "text", "ref_id": summary["span_id"], "description": "Summary in the after state.", "quote": "In 2020, 4% of La Jolla Shores parcels"},
                         {"kind": "screenshot", "ref_id": ta, "description": "After-state screenshot.", "quote": None}],
            "observation_confidence": {"level": "high", "reason": "Both texts and the completed event are in the bundle."},
            "slop_association": {"level": "moderate", "reason": "Polished panels are not integrated; the same defect is common in hand-written code."},
            "contextual_fit": {"level": "inappropriate", "reason": "The purpose is comparing scenario years."},
            "communication_or_interaction_consequence": {"level": "moderate", "reason": "The 2050 view is explained with 2020 numbers."},
            "alternative_explanations": ["Ordinary state-management bug", "Unfinished prototype"],
            "codebook_evidence_status": "research_hypothesis", "quality_to_slop_rationale": None,
            "limitations": ["Only the 2050 change was recorded."]}],
        "contextual_exceptions": [{
            "exception_id": "X001", "feature_id": "LAY-01", "observation": "Chart, summary, and method panels share one rounded-card style.",
            "locations": [loc("R02", "S01", "A01", s.region_box("R02", "A01")), loc("R03", "S01", "A01", s.region_box("R03", "A01"))],
            "evidence": [{"kind": "screenshot", "ref_id": "A01", "description": "Initial desktop view.", "quote": None}],
            "reason_not_counted": "conventional_for_genre", "rationale": "Distinct headings and roles; panel cards are conventional for data stories.",
            "observation_confidence": {"level": "high", "reason": "Visible."}}],
        "quality_observations": [], "exploratory_candidates": [], "untrusted_instructions_observed": [],
        "summary": {"text": "One integration problem after the recorded scenario change; the card panels are a contextual exception.",
                    "major_limitations": ["Only one scenario change recorded", "Synthetic fixture"]},
    }
    path = out / "scenario-inconsistency.audit.json"
    path.write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report = validate_audit.validate(path, s.dir)
    if not report.ok or report.warnings:
        report.print()
        raise SystemExit("reference audit is invalid")


if __name__ == "__main__":
    build_annotations()
    example_audits()
    reference_audits()
    print("annotations and examples written")
