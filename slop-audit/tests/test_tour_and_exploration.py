"""The hybrid evidence design: the standard tour (frozen), live exploration (logged), and the two-stage audit."""

import argparse
import copy
import csv
import json
import os
import shutil
from pathlib import Path
from urllib.robotparser import RobotFileParser

import pytest

import _lib
import bundle_digest
import explore
import explore_session as xs
import export_study_csv
import expand_prompt
import render_report
import site_capture as sc
import start_run
import validate_audit
import validate_bundle
import validate_exploration as vx
from conftest import FIXTURES, ROOT, SKILL, codes, load, questionnaire_audit

EXAMPLES = SKILL / "examples"
TOUR_BUNDLE = EXAMPLES / "bundles" / "placeholder-caption"


def tour_audit():
    return load(EXAMPLES / "audits" / "placeholder-caption.audit.json")


# --- planning the standard tour -------------------------------------------------

def test_full_tour_covers_every_desktop_screen_and_leaves_room_for_extras():
    plan, notes, extras = sc.allocate_full([4679, 800], budget=300, vh=800)
    assert [len(p["desktop"]) for p in plan] == [len(sc.positions(4679, 800)), 1]
    assert [p["desktop_needed"] for p in plan] == [6, 1]
    assert all(p["phone_quota"] >= 1 for p in plan) and extras > 100 and not notes
    big, notes, extras = sc.allocate_full([40000] * 6, budget=300, vh=800)
    assert sum(len(p["desktop"]) for p in big) <= 180 and all(p["desktop"][0] == 0 for p in big)
    assert any("desktop positions screenshotted" in n for n in notes) and extras >= 0
    no_phone, _, _ = sc.allocate_full([3000], budget=300, vh=800, mobile=False)
    assert no_phone[0]["phone_quota"] == 0


def test_share_is_proportional_with_a_floor():
    assert sc.share([5, 5], 20) == [5, 5]
    assert sc.share([10, 30], 20) == [5, 15]
    assert sc.share([1, 100, 100], 10)[0] == 1 and sum(sc.share([1, 100, 100], 10)) == 10
    assert sc.share([5, 5, 5], 2) == [1, 1, 1]          # the floor wins over the cap; the capture still reserves them


def test_full_plan_moves_sliders_to_both_ends_and_tours_the_phone_view():
    slider = {"selector": "#year", "tag": "input", "type": "range", "kind": "range", "text": "2010", "section": 0, "submits": False,
              "disabled": False, "download": False, "range": {"min": "2000", "max": "2020", "value": "2010"}}
    button = {"selector": "#go", "tag": "button", "type": "", "kind": "button", "text": "Show", "section": 0, "submits": False,
              "disabled": False, "download": False}
    info = {"metrics": {"page_h": 3000, "vh": 800}, "title": "Story", "sections": [{"selector": "main", "name": "main", "tag": "main", "rect": {}}],
            "controls": [slider, button], "untestable": [], "links": [], "signals": {"charts": 1}}
    pages = [{"url": "https://x.github.io/p/", "route": "/p/", "info": info}]
    args = argparse.Namespace(budget=300, max_controls=25, max_pages=12, no_mobile=False, withhold=[], quick=False)
    plan = sc.build_plan("https://x.github.io/p/", sc.Scope("https://x.github.io/p/"), pages, [], args, "robots.txt read")
    assert plan["capture_profile"] == "site-full" and plan["tour"] == {}
    assert [v["device_pixel_ratio"] for v in plan["viewports"]] == [1, 1]
    events = plan["pages"][0]["interactions"]
    assert [(e["action"], e["input_value"]) for e in events if e["action"] == "set_range"] == [("set_range", "2000"), ("set_range", "2020")]
    assert len({e["event_id"] for e in events}) == len(events) == 3
    shots = plan["pages"][0]["shots"]
    assert [s["scroll_y"] for s in shots if s["viewport_id"] == "V1"] == sc.positions(3000, 800)
    assert [s for s in shots if s.get("auto")][0]["quota"] >= 1
    quick = sc.build_plan("https://x.github.io/p/", sc.Scope("https://x.github.io/p/"), pages, [],
                          argparse.Namespace(budget=64, max_controls=10, max_pages=12, no_mobile=False, withhold=[], quick=True), "")
    assert quick["capture_profile"] == "site-auto" and "tour" not in quick


# --- the bundle's motion records ------------------------------------------------------

def with_motion(bundle_copy):
    """A fixture bundle with one motion sequence: a mid-motion frame (a copy of A01) and the settled A01."""
    b = bundle_copy("clean-docs")
    m = load(b / "manifest.json")
    a01 = m["assets"][0]
    shutil.copyfile(b / a01["path"], b / "assets/A99.png")
    m["assets"].append(dict(a01, asset_id="A99", path="assets/A99.png", kind="motion_frame"))
    m["evidence_profile"]["max_images"] = 400
    m["motion"] = [{"sequence_id": "M01", "route": a01["route"], "viewport_id": a01["viewport_id"], "state_id": a01["state_id"],
                    "trigger": "scroll", "event_id": None, "scroll_y": 0, "detected": ["dom_mutation", "visual_change"], "looping": False,
                    "frames": [{"asset_id": "A99", "elapsed_ms": 400, "settled": False}, {"asset_id": a01["asset_id"], "elapsed_ms": 1200, "settled": True}],
                    "settled_after_ms": 1200, "note": ""}]
    m["coverage"]["tour"] = [{"route": a01["route"], "desktop_frames": 1, "desktop_needed": 1, "phone_frames": 0, "phone_needed": 0,
                              "motion_sequences": 1, "motion_frames": 1, "looping_sequences": 0, "charts_found": 0, "charts_hovered": 0,
                              "hovers": 0, "hovers_with_response": 0, "hover_shots": 0, "controls_found": 0, "controls_exercised": 0}]
    (b / "bundle.lock.json").unlink(missing_ok=True)
    return b, m


def write(path, obj):
    Path(path).write_text(json.dumps(obj, indent=1), encoding="utf-8")


def test_motion_sequences_must_link_real_frames(bundle_copy):
    b, m = with_motion(bundle_copy)
    write(b / "manifest.json", m)
    report, _ = validate_bundle.validate(b)
    assert report.ok, report.errors
    digest = bundle_digest.digest(b)
    assert "MID-MOTION" in digest and "M01 after scroll" in digest and "standard tour" in digest
    bad = copy.deepcopy(m)
    bad["motion"][0]["frames"][0]["settled"] = True
    write(b / "manifest.json", bad)
    assert "motion_frame_kind" in codes(validate_bundle.validate(b)[0])
    orphan = copy.deepcopy(m)
    orphan["motion"] = []
    write(b / "manifest.json", orphan)
    assert "orphan_motion_frame" in codes(validate_bundle.validate(b)[0])


# --- the exploration policy -------------------------------------------------------------

def info(**kw):
    base = {"selector": "#x", "tag": "button", "type": "", "visible": True, "text": "Show", "submits": False, "typing": False,
            "href": None, "download": False, "new_tab": False, "options": None, "range": None, "rect": {}, "page_url": "https://a.github.io/p/"}
    return dict(base, **kw)


def test_exploration_stays_inside_the_site_and_its_robots_rules():
    scope = sc.Scope("https://a.github.io/p/")
    robots = RobotFileParser()
    robots.parse(["User-agent: *", "Disallow: /p/private.html"])
    assert xs.refuse_goto("https://a.github.io/p/about.html", scope, robots) is None
    assert "outside" in xs.refuse_goto("https://a.github.io/other/", scope, robots)
    assert "outside" in xs.refuse_goto("https://example.com/", scope, robots)
    assert "not a web page" in xs.refuse_goto("https://a.github.io/p/data.csv", scope, robots)
    assert "robots" in xs.refuse_goto("https://a.github.io/p/private.html", scope, robots)
    assert xs.refuse_goto("mailto:a@b.c", scope, robots)


def test_exploration_refuses_typing_submitting_downloads_and_account_actions():
    scope = sc.Scope("https://a.github.io/p/")
    assert xs.refuse_click(info(), scope, None) is None
    assert xs.refuse_click(None, scope, None)
    assert "not visible" in xs.refuse_click(info(visible=False), scope, None)
    assert "typing" in xs.refuse_click(info(tag="input", typing=True), scope, None)
    assert "submit" in xs.refuse_click(info(submits=True), scope, None)
    assert "download" in xs.refuse_click(info(download=True, href="https://a.github.io/p/x.pdf"), scope, None)
    assert "sign-in" in xs.refuse_click(info(text="Log in"), scope, None)
    assert "new tab" in xs.refuse_click(info(tag="a", href="https://a.github.io/p/b.html", new_tab=True), scope, None)
    assert "outside" in xs.refuse_click(info(tag="a", href="https://example.com/"), scope, None)
    assert xs.refuse_click(info(tag="a", href="https://a.github.io/p/#method"), scope, None) is None   # in-page anchor
    assert xs.refuse_click(info(tag="a", href="https://a.github.io/p/b.html"), scope, None) is None     # another page of the site


def test_exploration_checks_dropdown_and_slider_values():
    sel = info(tag="select", options=["a", "b"])
    assert xs.refuse_select(sel, "b") is None and "not one of" in xs.refuse_select(sel, "z")
    assert "dropdowns" in xs.refuse_select(info(), "b")
    rng = info(tag="input", type="range", range={"min": "0", "max": "10", "value": "5"})
    assert xs.refuse_slide(rng, "10") is None and "between" in xs.refuse_slide(rng, "11") and "number" in xs.refuse_slide(rng, "x")
    assert "sliders" in xs.refuse_slide(info(), "3")


# --- the exploration record ----------------------------------------------------------

def make_record(tmp, bundle_dir, tour, actions):
    """A synthetic, locked exploration record (screenshots are copies of the bundle's first image)."""
    d = Path(tmp) / "exploration"
    (d / "assets").mkdir(parents=True)
    b = _lib.Bundle(bundle_dir)
    src = b.dir / b.manifest["assets"][0]["path"]
    route = b.manifest["states"][0]["route"]
    acts = []
    for i, spec in enumerate(actions, 1):
        aid = f"L{i:03d}"
        status = spec.get("status", "completed")
        shots = []
        if status == "completed" and spec.get("shot", True):
            dst = d / "assets" / f"{aid}.png"
            shutil.copyfile(src, dst)
            w, h = _lib.image_size(dst)
            shots.append({"asset_id": aid, "path": f"assets/{aid}.png", "sha256": _lib.sha256_file(dst), "pixel_width": w, "pixel_height": h,
                          "kind": "settled", "elapsed_ms": 300, "scroll_y": 0})
        cmd = spec.get("command", "hover")
        acts.append({"action_id": aid, "command": cmd, "args": {}, "at": "2026-11-15T00:00:00Z", "route": route, "url": None, "scroll_y": 0,
                     "target": spec.get("target"), "status": status, "result": spec.get("result", "done"),
                     "observed_changes": spec.get("changes", []), "screenshots": shots, "counted": cmd not in ("find", "read")})
    counts = {"actions": sum(a["counted"] for a in acts), "screenshots": sum(len(a["screenshots"]) for a in acts),
              "refused": sum(a["status"] == "refused" for a in acts), "failed": sum(a["status"] == "failed" for a in acts),
              "inspections": sum(a["command"] in ("find", "read") for a in acts)}
    rec = {"schema_version": "website-slop-audit/exploration/0.1", "exploration_id": "x-test", "bundle_id": b.bundle_id, "bundle_hash": b.hash,
           "tour_audit_id": tour["audit_id"], "tour_commit": vx.tour_commit(tour), "started_at": "2026-11-15T00:00:00Z",
           "finished_at": "2026-11-15T00:05:00Z", "adapter": {"name": "test", "version": "0", "browser": None}, "target_locator": None,
           "scope_prefix": "/", "viewport": {"viewport_id": "V1", "device": "desktop", "css_width": 1280, "css_height": 800, "device_pixel_ratio": 1},
           "limits": {"max_actions": 40, "max_screenshots": 25, "max_inspections": 60}, "counts": counts, "routes_visited": [route],
           "actions": acts, "notes": []}
    write(d / "exploration.json", rec)
    vx.freeze(vx.Record(d))
    return d


HOVER = {"command": "hover", "target": {"selector": "#chart svg", "description": "pointer on the chart", "region_id": "R03"},
         "result": "a tooltip or label appeared", "changes": [{"kind": "text_appeared", "detail": "#tip: \"42% faster\""}]}


def test_exploration_record_validates_and_detects_tampering(tmp_path):
    tour = tour_audit()
    d = make_record(tmp_path, TOUR_BUNDLE, tour, [HOVER, {"command": "click", "status": "refused", "result": "refused: it would submit a form"}])
    report, rec = vx.validate(d, bundle_dir=TOUR_BUNDLE)
    assert report.ok, report.errors
    assert rec.selectors() == {"#chart svg"} and "L001" in rec.assets
    data = load(d / "exploration.json")
    data["counts"]["actions"] = 9
    write(d / "exploration.json", data)
    assert {"counts_mismatch", "changed_after_freeze"} <= codes(vx.validate(d)[0])
    data["counts"]["actions"] = 2
    data["actions"][1]["action_id"] = "L005"
    write(d / "exploration.json", data)
    assert "action_order" in codes(vx.validate(d)[0])


def test_the_tour_lock_ignores_only_the_exploration_stage():
    tour = tour_audit()
    stamped = dict(copy.deepcopy(tour), exploration_stage={"status": "not_done"})
    assert vx.tour_commit(stamped) == vx.tour_commit(tour)
    changed = copy.deepcopy(tour)
    changed["study_questionnaire"]["answers"]["polish"]["value"] = 1
    assert vx.tour_commit(changed) != vx.tour_commit(tour)


def test_exploring_needs_a_valid_tour_audit_with_answers(tmp_path):
    tour = tour_audit()
    assert vx.check_tour_audit(EXAMPLES / "audits" / "placeholder-caption.audit.json", TOUR_BUNDLE)["audit_id"] == tour["audit_id"]
    no_answers = {k: v for k, v in tour.items() if k != "study_questionnaire"}
    write(tmp_path / "a.json", no_answers)
    with pytest.raises(vx.VxError, match="study_questionnaire"):
        vx.check_tour_audit(tmp_path / "a.json", TOUR_BUNDLE)
    write(tmp_path / "b.json", dict(tour, exploration_stage={}))
    with pytest.raises(vx.VxError, match="already has"):
        vx.check_tour_audit(tmp_path / "b.json", TOUR_BUNDLE)
    broken = copy.deepcopy(tour)
    broken["findings"][0]["evidence"][0]["ref_id"] = "T999"
    write(tmp_path / "c.json", broken)
    with pytest.raises(vx.VxError, match="does not validate"):
        vx.check_tour_audit(tmp_path / "c.json", TOUR_BUNDLE)


# --- the two-stage audit -----------------------------------------------------------------

def two_stage(tour, xdir):
    rec = vx.Record(xdir)
    a = copy.deepcopy(tour)
    a["exploration_stage"] = {
        "status": "completed", "reason": "Hovered the chart and read its tooltip.", "exploration_id": rec.exploration_id,
        "exploration_hash": rec.hash, "tour_commit": rec.data["tour_commit"], "findings": [], "contextual_exceptions": [],
        "quality_observations": [{"observation_id": "Q010", "category": "usability", "related_feature_id": None,
                                  "observation": "The chart shows a tooltip on hover.",
                                  "locations": [{"region_id": "R03", "state_id": "L001", "asset_id": "L001", "box": None,
                                                 "selector": "#chart svg", "source_ref": None}],
                                  "evidence": [{"kind": "exploration", "ref_id": "L001", "description": "hover", "quote": "42% faster"}],
                                  "consequence": {"level": "none_identified", "reason": "Works."}}],
        "exploratory_candidates": [],
        "tour_item_updates": [{"item_id": "F001", "update": "confirmed", "reason": "The caption is still placeholder text.",
                               "refs": [{"kind": "exploration", "id": "L001"}]}],
        "study_questionnaire": copy.deepcopy(tour["study_questionnaire"]), "changes_from_tour": [],
        "summary": {"text": "Exploring confirmed the tour findings.", "major_limitations": []}}
    return a


@pytest.fixture
def staged(tmp_path):
    tour = tour_audit()
    xdir = make_record(tmp_path, TOUR_BUNDLE, tour, [HOVER, {"command": "click", "status": "refused", "result": "refused"}])
    return tour, xdir, two_stage(tour, xdir)


def check(audit, xdir):
    return validate_audit.validate(audit, TOUR_BUNDLE, xdir)


def test_a_two_stage_audit_validates(staged):
    tour, xdir, audit = staged
    report = check(audit, xdir)
    assert report.ok and not report.warnings, (report.errors, report.warnings)


def test_changing_the_tour_after_exploring_is_caught(staged):
    tour, xdir, audit = staged
    audit["study_questionnaire"]["answers"]["quality"]["value"] = 1
    assert "tour_answers_changed" in codes(check(audit, xdir))


def test_the_tour_stage_cannot_cite_exploration(staged):
    tour, xdir, audit = staged
    audit["findings"][0]["evidence"].append({"kind": "exploration", "ref_id": "L001", "description": "x", "quote": None})
    assert "exploration_in_tour" in codes(check(audit, xdir))


def test_every_changed_answer_needs_a_reason_and_only_those(staged):
    tour, xdir, audit = staged
    answers = audit["exploration_stage"]["study_questionnaire"]["answers"]
    answers["polish"] = {"value": 5 if answers["polish"]["value"] != 5 else 4, "reason": "Smooth hovers.", "refs": [{"kind": "exploration", "id": "L001"}]}
    assert "changes_unlisted" in codes(check(audit, xdir))
    audit["exploration_stage"]["changes_from_tour"] = [{"question_id": "polish", "reason": "Smooth hovers.", "refs": [{"kind": "exploration", "id": "L001"}]}]
    assert check(audit, xdir).ok
    audit["exploration_stage"]["changes_from_tour"].append({"question_id": "quality", "reason": "x", "refs": [{"kind": "exploration", "id": "L001"}]})
    assert "changes_not_changed" in codes(check(audit, xdir))
    audit["exploration_stage"]["changes_from_tour"] = [{"question_id": "polish", "reason": "x", "refs": [{"kind": "finding", "id": "F001"}]}]
    assert "no_exploration_evidence" in codes(check(audit, xdir))


def test_exploration_items_rest_on_completed_actions_and_continue_the_numbering(staged):
    tour, xdir, audit = staged
    q = audit["exploration_stage"]["quality_observations"][0]
    q["evidence"] = [{"kind": "screenshot", "ref_id": "A01", "description": "tour image", "quote": None}]
    assert "no_exploration_evidence" in codes(check(audit, xdir))
    q["evidence"] = [{"kind": "exploration", "ref_id": "L002", "description": "refused click", "quote": None}]
    q["locations"][0]["state_id"] = "L002"
    q["locations"][0]["asset_id"] = None
    assert "missing_exploration_ref" in codes(check(audit, xdir))
    q["evidence"] = [{"kind": "exploration", "ref_id": "L001", "description": "hover", "quote": "not in the record"}]
    q["locations"][0].update(state_id="L001", asset_id="L001")
    assert "quote_mismatch" in codes(check(audit, xdir))
    q["evidence"][0]["quote"] = None
    assert check(audit, xdir).ok
    reused = copy.deepcopy(tour["findings"][0])          # an exploration finding may not reuse a tour id
    reused["evidence"].append({"kind": "exploration", "ref_id": "L001", "description": "hover", "quote": None})
    audit["exploration_stage"]["findings"] = [reused]
    assert "duplicate_id" in codes(check(audit, xdir))
    reused["finding_id"] = "F010"
    assert check(audit, xdir).ok


def test_exploration_locations_use_action_ids_and_known_regions(staged):
    tour, xdir, audit = staged
    loc = audit["exploration_stage"]["quality_observations"][0]["locations"][0]
    loc["region_id"] = "unmapped"          # the action's target lies in R03, so "unmapped" is wrong here
    assert "unknown_region" in codes(check(audit, xdir))
    loc["region_id"] = "R03"
    loc["selector"] = "#not-there"
    assert "fabricated_selector" in codes(check(audit, xdir))
    loc["selector"] = None
    loc["asset_id"] = "L002"
    assert "missing_asset_ref" in codes(check(audit, xdir))


def test_marks_after_exploring_may_quote_text_the_exploration_saw(staged):
    tour, xdir, audit = staged
    route = _lib.Bundle(TOUR_BUNDLE).manifest["states"][0]["route"]
    mark = {"mark_number": 1, "page": route, "kind": "Text", "tag": "p", "text": "42% faster", "selector": "#chart-caption",
            "element_id": None, "reason": "Seen in a tooltip while exploring.", "refs": [{"kind": "exploration", "id": "L001"}]}
    sel = {e["selector"] for e in _lib.Bundle(TOUR_BUNDLE).elements.values()}
    assert "#chart-caption" in sel
    audit["exploration_stage"]["study_questionnaire"]["answers"]["ai_marks"]["value"] = [mark]
    audit["exploration_stage"]["changes_from_tour"] = [{"question_id": "ai_marks", "reason": "x", "refs": [{"kind": "exploration", "id": "L001"}]}]
    report = check(audit, xdir)
    assert report.ok and "mark_text_mismatch" not in {c for c, _ in report.warnings}, report.warnings
    mark["text"] = "words nobody saw"
    assert "mark_text_mismatch" in {c for c, _ in check(audit, xdir).warnings}


def test_not_done_must_be_empty_and_completed_needs_its_record(staged, tmp_path):
    tour, xdir, audit = staged
    assert "exploration_missing" in codes(validate_audit.validate(audit, TOUR_BUNDLE, tmp_path / "nowhere"))
    st = audit["exploration_stage"]
    st.update(status="not_done", reason="The host has no network.", exploration_id=None, exploration_hash=None, tour_commit=None)
    assert "exploration_stage_inconsistent" in codes(check(audit, xdir))
    for key in ("quality_observations", "tour_item_updates", "changes_from_tour"):
        st[key] = []
    st["study_questionnaire"] = None
    assert check(audit, None).ok


def test_reports_show_both_stages_and_the_exploration_log(staged, tmp_path):
    tour, xdir, audit = staged
    answers = audit["exploration_stage"]["study_questionnaire"]["answers"]
    answers["polish"] = {"value": 5 if answers["polish"]["value"] != 5 else 4, "reason": "Smooth.", "refs": [{"kind": "exploration", "id": "L001"}]}
    audit["exploration_stage"]["changes_from_tour"] = [{"question_id": "polish", "reason": "The hover tooltip is tidy.", "refs": [{"kind": "exploration", "id": "L001"}]}]
    run = tmp_path / "run"
    run.mkdir()
    write(run / "audit.json", audit)
    shutil.copytree(xdir, run / "exploration")
    assert render_report.main([str(run / "audit.json"), "--bundle", str(TOUR_BUNDLE), "--out", str(run / "report.html")]) == 0
    html = (run / "report.html").read_text()
    assert "Tour answers and answers after exploring" in html and "The hover tooltip is tidy." in html and "class=changed" in html
    assert "Live exploration" in html and "exploration/assets/L001.png" in html and "What exploring showed about tour findings" in html
    assert render_report.main([str(run / "audit.json"), "--bundle", str(TOUR_BUNDLE), "--out", str(run / "report.md")]) == 0
    md = (run / "report.md").read_text()
    assert "## Live exploration" in md and "* How polished" in md


def test_csv_export_writes_a_tour_row_and_an_explored_row(staged, tmp_path):
    tour, xdir, audit = staged
    run = tmp_path / "run"
    run.mkdir()
    write(run / "audit.json", audit)
    shutil.copytree(xdir, run / "exploration")
    out, wides, marks, reasons = export_study_csv.export(run / "audit.json", TOUR_BUNDLE, run / "csv", rater="test/model")
    rows = list(csv.DictReader((run / "csv/responses_wide.csv").open()))
    assert [r["evidence_phase"] for r in rows] == ["tour", "explored"]
    assert rows[1]["exploration_id"] == "x-test" and rows[0]["exploration_id"] == ""
    assert {r["evidence_phase"] for r in csv.DictReader((run / "csv/questionnaire_reasons.csv").open())} == {"tour", "explored"}
    header = next(csv.reader((run / "csv/marks.csv").open()))
    assert header[: len(export_study_csv.MARK_COLUMNS) - 1] == export_study_csv.MARK_COLUMNS[:-1] and header[-1] == "evidence_phase"


# --- run folders, entry points, prompt package --------------------------------------------

def test_every_run_gets_its_own_folder(tmp_path):
    shutil.copytree(TOUR_BUNDLE, tmp_path / "bundle")
    a = start_run.start(tmp_path / "bundle", "openai/gpt-5-codex")
    b = start_run.start(tmp_path / "bundle", "openai/gpt-5-codex")
    assert a != b and a.parent == b.parent == tmp_path / "runs" and "openai-gpt-5-codex" in a.name
    assert load(a / "run.json")["rater"] == "openai/gpt-5-codex"


def test_explore_finds_the_adapter_beside_the_skill_and_fails_clearly_without_one(monkeypatch, capsys):
    monkeypatch.delenv(explore.ENV, raising=False)
    assert explore.find_adapter() == ROOT / "integrations" / "capture" / "explore_session.py"
    monkeypatch.setenv(explore.ENV, "/nonexistent/adapter.py")
    assert explore.main(["status", "--session", "x"]) == 2
    assert "not_done" in capsys.readouterr().err


def test_chat_packages_record_the_exploration_as_not_done():
    text = expand_prompt.skill_instructions("multimodal-datastory")
    assert 'status "not_done"' in text


def test_skill_names_the_exploration_tool_but_no_browser():
    text = (SKILL / "SKILL.md").read_text()
    assert "scripts/explore.py" in text and "audit.tour.json" in text and "exploration_stage" in text
    front = text.split("---")[1]
    assert len(front.split("description:", 1)[1].strip()) <= 1024
    proto = (SKILL / "references/exploration-protocol.md").read_text()
    for cmd in ("look", "scroll", "hover", "click", "select", "slide", "goto", "back", "wait", "find", "read", "status", "finish"):
        assert f"`{cmd}" in proto


# --- live (gstack browse) --------------------------------------------------------------------

LIVE = pytest.mark.skipif(os.environ.get("SLOP_LIVE_CAPTURE") != "1", reason="live gstack capture; set SLOP_LIVE_CAPTURE=1")


@LIVE
def test_live_standard_tour_and_exploration_of_the_motion_fixture(tmp_path):
    site = FIXTURES / "sites/motion-site"
    args = argparse.Namespace(target="/index.html", out=str(tmp_path / "run"), max_pages=12, max_controls=None, budget=None,
                              single_page=False, no_mobile=False, withhold=[], quick=False, serve=str(site))
    report, summary = sc.run(args)
    assert report.ok and summary["capture_profile"] == "site-full"
    bundle = tmp_path / "run/bundle"
    m = load(bundle / "manifest.json")
    tour = {t["route"]: t for t in m["coverage"]["tour"]}
    assert tour["/"]["desktop_frames"] == tour["/"]["desktop_needed"] >= 5
    assert tour["/"]["phone_frames"] == tour["/"]["phone_needed"] >= 5
    assert tour["/"]["charts_found"] == tour["/"]["charts_hovered"] == 3
    triggers = {(q["trigger"], tuple(q["detected"])) for q in m["motion"]}
    assert any(t == "load" and "css_animation" in d for t, d in triggers)          # the title's entrance animation
    assert any(t == "scroll" and "dom_mutation" in d for t, d in triggers)         # the bars grown by script
    hovers = [e for e in m["interactions"] if e["action"] == "hover"]
    text = json.dumps(hovers)
    assert "Year 20" in text and "Reservoir " in text                             # SVG tooltip and canvas tooltip
    assert any(c["kind"] == "visual_unchanged" for e in hovers for c in e["observed_changes"])   # bars without handlers
    assert [e["input_value"] for e in m["interactions"] if e["action"] == "set_range"] == ["2000", "2020"]
    cov = {c["ref"]: c["status"] for c in m["coverage"]["interactions"]}
    assert cov["/: button 'Subscribe'"] == "blocked"
    # Exploration on top of a tour audit.
    tour_path = tmp_path / "audit.tour.json"
    write(tour_path, questionnaire_audit(bundle))
    xdir = tmp_path / "exploration"
    run = lambda *a: xs.main([*a])
    assert run("start", "--bundle", str(bundle), "--tour-audit", str(tour_path), "--out", str(xdir), "--serve", str(site)) == 0
    S = ["--session", str(xdir)]
    assert run("hover", *S, "#dots > circle", "--nth", "3") == 0
    assert run("scroll", *S, "--to-element", "#growth", "--frames") == 0
    assert run("click", *S, "form button") == 1                                     # submits a form: refused
    assert run("goto", *S, "https://example.com/") == 1                             # off-site: refused
    assert run("slide", *S, "#year", "2015") == 0
    assert run("finish", *S) == 0
    rec = load(xdir / "exploration.json")
    assert [a["status"] for a in rec["actions"]] == ["completed", "completed", "completed", "refused", "refused", "completed"]
    assert "Year 2013" in json.dumps(rec["actions"][1]) and (xdir / "exploration.lock.json").is_file()
    assert vx.validate(xdir, bundle_dir=bundle)[0].ok
