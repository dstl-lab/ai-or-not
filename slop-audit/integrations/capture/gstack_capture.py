#!/usr/bin/env python3
"""Capture a website into a website-slop-audit bundle using gstack browse ($B).

    python integrations/capture/gstack_capture.py PLAN.json --out BUNDLE_DIR [--serve SITE_DIR] [--freeze]
    python integrations/capture/gstack_capture.py PLAN.json --out BUNDLE_DIR --allow-public --private-out sidecar.json

This is the acquisition adapter for hosts where gstack browse is the
permitted browser (this workspace). It drives gstack's own headless
Chromium, which carries no personal cookies or sign-ins, so captured
evidence is not personalized. The portable skill never calls this file; any
host can supply a bundle that follows references/capture-protocol.md.

Safety: only the plan's URL is opened; links are never followed; only
click, hover, select, scroll, and keypress actions on selectors named in the
plan run; form submissions and actions whose target text or selector looks
like sign-in, purchase, send, delete, or account changes are refused. A
public (non-local) URL requires --allow-public. Page text is stored as data.
"""

import argparse
import contextlib
import functools
import http.server
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
SKILL_SCRIPTS = HERE.parent.parent / "website-slop-audit" / "scripts"
sys.path.insert(0, str(SKILL_SCRIPTS))
import _lib  # noqa: E402
import validate_bundle  # noqa: E402

ADAPTER = {"name": "gstack_capture.py", "version": "0.1.0"}
PROTOCOL = "capture-protocol/0.1"
STYLE_PROPS = ["font-family", "font-size", "font-weight", "font-style", "color", "background-color", "background-image",
               "border-radius", "box-shadow", "text-transform", "letter-spacing", "animation-name", "animation-duration",
               "transition-property", "opacity", "-webkit-background-clip", "background-clip"]
UNSAFE = re.compile(r"(log ?in|log ?out|sign ?in|sign ?up|sign ?out|password|checkout|purchase|buy|pay\b|payment|"
                    r"subscribe|unsubscribe|send|submit|delete|remove|cancel|account|settings|order)", re.IGNORECASE)
ALLOWED_ACTIONS = {"click", "hover", "select", "scroll", "keypress"}
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}


class CaptureError(Exception):
    pass


def browse_binary():
    env = os.environ.get("GSTACK_BROWSE")
    candidates = [env] if env else []
    candidates.append(str(Path.home() / ".claude/skills/gstack/browse/dist/browse"))
    for c in candidates:
        if c and Path(c).is_file() and os.access(c, os.X_OK):
            return c
    raise CaptureError("gstack browse binary not found; set GSTACK_BROWSE or install gstack (see /browse)")


class Browser:
    """Thin wrapper over the $B CLI. Every call is logged for the capture notes."""

    def __init__(self, binary, log):
        self.b = binary
        self.log = log
        out = self.run("status", check=False)
        self.version = next((line for line in out.splitlines() if line.strip()), "unknown")[:120]

    def run(self, *args, check=True, timeout=60):
        proc = subprocess.run([self.b, *args], capture_output=True, text=True, timeout=timeout)
        self.log.append(" ".join(a if len(a) < 80 else a[:77] + "..." for a in args))
        out = (proc.stdout or "") + (proc.stderr or "")
        if check and proc.returncode != 0:
            raise CaptureError(f"$B {args[0]} failed: {out.strip()[-400:]}")
        return out

    def js(self, expr):
        return self.run("js", expr).strip().splitlines()[-1]

    def eval_file(self, path):
        return self.run("eval", str(path), timeout=90).strip().splitlines()[-1]


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@contextlib.contextmanager
def static_server(directory):
    handler = functools.partial(QuietHandler, directory=str(directory))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_address[1]}"
    finally:
        httpd.shutdown()


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def norm_box(rect, origin_y, width, height):
    """Clip a page rect to one screenshot and normalize it; None if it is not visible there."""
    x0, y0 = max(rect["x"], 0), max(rect["y"] - origin_y, 0)
    x1, y1 = min(rect["x"] + rect["w"], width), min(rect["y"] + rect["h"] - origin_y, height)
    if x1 - x0 < 2 or y1 - y0 < 2:
        return None
    r = lambda v: round(v, 4)
    box = {"x": r(x0 / width), "y": r(y0 / height), "width": r((x1 - x0) / width), "height": r((y1 - y0) / height)}
    box["width"] = min(box["width"], round(1 - box["x"], 4))
    box["height"] = min(box["height"], round(1 - box["y"], 4))
    return box if box["width"] > 0 and box["height"] > 0 else None


def plan_pages(plan, base_url):
    """The pages a plan captures. A plan without `pages` is one page built from its top-level fields."""
    if plan.get("pages"):
        return plan["pages"]
    return [{"route": plan.get("route", "/"), "url": base_url, "regions": plan.get("regions", []),
             "shots": plan.get("shots", []), "interactions": plan.get("interactions", []),
             "untested_controls": plan.get("untested_controls", [])}]


class Capture:
    def __init__(self, plan, out_dir, browser, base_url):
        self.plan = plan
        self.out = Path(out_dir)
        self.br = browser
        self.pages = plan_pages(plan, base_url)
        self.page = self.pages[0]
        self.url = self.page["url"]
        limits = plan.get("extract_limits", {})
        self.max_spans, self.max_elements = limits.get("max_spans", 400), limits.get("max_elements", 400)
        self.tmp = Path(tempfile.mkdtemp(prefix="slopcap-"))
        self.extract_src = (HERE / "extract.js").read_text(encoding="utf-8")
        self.viewports = {v["viewport_id"]: v for v in plan["viewports"]}
        self.primary = plan["viewports"][0]["viewport_id"]
        self.states, self.assets, self.spans, self.elements, self.events = [], [], [], [], []
        self.region_rects = {}   # (state_id) -> {region_id: rect}
        self.notes, self.limits = [], list(plan.get("capability_limits", []))
        self.coverage_interactions = []
        self.span_index = {}     # (state_id, key) -> span_id
        self.el_index = {}       # (state_id, key) -> element_id

    # --- page helpers ---------------------------------------------------------

    def extract(self, mode):
        cfg = {"regions": [{"region_id": r["region_id"], "selector": r["selector"]} for r in self.page["regions"]],
               "mode": mode, "style_props": STYLE_PROPS, "max_spans": self.max_spans, "max_elements": self.max_elements}
        path = self.tmp / f"extract-{mode}.js"
        path.write_text(f"const CONFIG = {json.dumps(cfg)};\n" + self.extract_src, encoding="utf-8")
        raw = self.br.eval_file(path)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            raise CaptureError(f"extractor returned non-JSON output: {raw[:200]}") from None

    def load(self, viewport_id):
        vp = self.viewports[viewport_id]
        self.br.run("viewport", f"{vp['css_width']}x{vp['css_height']}", "--scale", str(vp["device_pixel_ratio"]))
        self.br.run("goto", self.url)
        self.br.run("wait", "--load", check=False)
        self.br.js("document.fonts ? document.fonts.ready.then(() => document.fonts.status) : 'none'")
        time.sleep(self.plan.get("settle_ms", 600) / 1000)

    def new_state(self, viewport_id, kind, metrics, description):
        sid = f"S{len(self.states) + 1:02d}"
        fonts_ok = not (metrics["fonts_failed"] or metrics["fonts_loading"])
        complete = metrics["ready_state"] == "complete" and fonts_ok and not metrics["busy"] and metrics["images_incomplete"] == 0
        if metrics["fonts_failed"]:
            self.limits.append(f"{sid}: web font(s) failed to load ({len(metrics['fonts_failed'])} face(s)); text renders in a fallback font")
        if metrics["busy"]:
            self.limits.append(f"{sid}: page was still marked aria-busy (loading) when captured")
        self.states.append({"state_id": sid, "route": self.page["route"], "viewport_id": viewport_id, "kind": kind,
                            "load_status": "complete" if complete else "partial", "fonts_loaded": fonts_ok,
                            "description": description})
        return sid

    def screenshot(self, state_id, viewport_id, full_page=False):
        if len(self.assets) >= self.plan["max_images"]:
            raise CaptureError(f"plan exceeds its image budget of {self.plan['max_images']}")
        aid = f"A{len(self.assets) + 1:02d}"
        rel = f"assets/{aid}.png"
        target = self.out / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        # The browse daemon only writes inside its own start folder and the system temp folders,
        # so shoot into our temp folder and move the file into the bundle.
        shot = self.tmp / f"{aid}.png"
        if full_page:
            self.br.run("js", "window.scrollTo(0, 0)")
            self.br.run("screenshot", str(shot))
            sx, sy = 0, 0
        else:
            sx, sy = json.loads(self.br.js("JSON.stringify([window.scrollX, window.scrollY])"))
            self.br.run("screenshot", "--viewport", str(shot))
        shutil.move(str(shot), str(target))
        w, h = _lib.image_size(target)
        vp = self.viewports[viewport_id]
        self.assets.append({"asset_id": aid, "kind": "full_page_screenshot" if full_page else "viewport_screenshot",
                            "path": rel, "sha256": _lib.sha256_file(target), "media_type": "image/png",
                            "pixel_width": w, "pixel_height": h, "viewport_id": viewport_id,
                            "device_pixel_ratio": vp["device_pixel_ratio"], "route": self.page["route"],
                            "scroll_x": sx, "scroll_y": sy, "state_id": state_id, "crop_of": None})
        return self.assets[-1]

    def scroll_to(self, y):
        self.br.js(f"(window.scrollTo(0, {int(y)}), window.scrollY)")
        time.sleep(self.plan.get("scroll_settle_ms", 250) / 1000)
        return json.loads(self.br.js("JSON.stringify(window.scrollY)"))

    def wait_visible(self, selector, timeout_ms):
        sel = json.dumps(selector)
        probe = (f"(() => {{ const el = document.querySelector({sel}); if (!el) return 'false'; const r = el.getBoundingClientRect(); "
                 f"const cs = getComputedStyle(el); return JSON.stringify(r.width > 0 && r.height > 0 && cs.display !== 'none' "
                 f"&& cs.visibility !== 'hidden'); }})()")
        deadline = time.time() + timeout_ms / 1000
        while True:
            if json.loads(self.br.js(probe)):
                return True
            if time.time() >= deadline:
                return False
            time.sleep(0.25)

    # --- recording extracted data ---------------------------------------------

    def add_spans(self, state_id, data, keep=None):
        for s in data["spans"]:
            if keep is not None and not keep(s):
                continue
            span_id = f"T{len(self.spans) + 1:03d}"
            self.span_index[(state_id, s["key"])] = span_id
            self.spans.append({"span_id": span_id, "region_id": s["region_id"], "state_id": state_id, "text": s["text"],
                               "source": "dom", "element_id": None, "appearances": [], "_rect": s["rect"], "_key": s["key"]})

    def add_elements(self, state_id, data, keep=None):
        for e in data["elements"]:
            if keep is not None and not keep(e):
                continue
            eid = f"D{len(self.elements) + 1:03d}"
            self.el_index[(state_id, e["key"])] = eid
            span_ids = [sid for (st, key), sid in self.span_index.items() if st == state_id and key == e["key"]]
            self.elements.append({"element_id": eid, "state_id": state_id, "region_id": e["region_id"], "selector": e["key"],
                                  "tag": e["tag"], "role": e["role"], "text_span_ids": span_ids, "computed_style": e["style"]})
        for span in self.spans:
            if span["state_id"] == state_id and span["element_id"] is None:
                span["element_id"] = self.el_index.get((state_id, span["_key"]))

    def appearances_for(self, rect, state_id, page_h):
        out = []
        for a in self.assets:
            if a["state_id"] != state_id:
                continue
            vp = self.viewports[a["viewport_id"]]
            if a["kind"] == "full_page_screenshot":
                width, height, origin = vp["css_width"], page_h, 0
                box = norm_box(rect, origin, a["pixel_width"] / vp["device_pixel_ratio"], a["pixel_height"] / vp["device_pixel_ratio"])
            else:
                box = norm_box(rect, a["scroll_y"], vp["css_width"], vp["css_height"])
            if box:
                out.append({"asset_id": a["asset_id"], "box": box})
        return out

    # --- the capture -----------------------------------------------------------

    def run(self):
        page_h_by_state = {}
        multi = len(self.pages) > 1
        for page in self.pages:
            self.page, self.url = page, page["url"]
            if multi:
                time.sleep(self.plan.get("page_delay_ms", 500) / 1000)
            self.capture_page(page, page_h_by_state)
        # Region and span appearances on every screenshot of their state.
        for s in self.spans:
            s["appearances"] = self.appearances_for(s["_rect"], s["state_id"], page_h_by_state.get(s["state_id"], 0))
        self.page_h_by_state = page_h_by_state
        return self.build_manifest()

    def capture_page(self, page, page_h_by_state):
        plan = self.plan
        where = f" on {page['route']}" if len(self.pages) > 1 else ""
        shot_vps = {s["viewport_id"] for s in page["shots"]}
        for vp_id in [v["viewport_id"] for v in plan["viewports"]]:
            if vp_id != self.primary and vp_id not in shot_vps:
                continue  # no screenshots planned at this viewport for this page
            self.load(vp_id)
            mode = "full" if vp_id == self.primary else "regions_only"
            data = self.extract(mode)
            sid = self.new_state(vp_id, "initial", data["metrics"], f"{page['route']} as loaded at viewport {vp_id}")
            page_h_by_state[sid] = data["metrics"]["page_h"]
            self.region_rects[sid] = {r["region_id"]: r["rect"] for r in data["regions"] if r["found"]}
            for r in data["regions"]:
                if not r["found"]:
                    self.notes.append(f"region {r['region_id']} selector not found at viewport {vp_id}{where}")
            seen_scrolls = set()
            for shot in [s for s in page["shots"] if s["viewport_id"] == vp_id]:
                if shot.get("full_page"):
                    if data["metrics"]["page_h"] <= self.viewports[vp_id]["css_height"]:
                        self.notes.append(f"skipped the {vp_id} full-page overview: the page fits in one viewport, so it would duplicate scroll 0")
                    else:
                        self.screenshot(sid, vp_id, full_page=True)
                    continue
                actual = self.scroll_to(shot.get("scroll_y", 0))
                if actual in seen_scrolls:
                    self.notes.append(f"skipped a {vp_id} screenshot at scroll {shot.get('scroll_y')}: page too short, duplicate of scroll {actual}")
                    continue
                seen_scrolls.add(actual)
                self.screenshot(sid, vp_id)
            if mode == "full":
                visible_only = plan.get("text_scope") == "visible_in_screenshots"
                shots = [a for a in self.assets if a["state_id"] == sid]
                vp = self.viewports[vp_id]

                def in_shots(item):
                    return any(norm_box(item["rect"], a["scroll_y"], vp["css_width"], vp["css_height"]) for a in shots
                               if a["kind"] == "viewport_screenshot")

                self.add_spans(sid, data, keep=in_shots if visible_only else None)
                self.add_elements(sid, data, keep=(lambda e: True))
                self.primary_state = sid
                self.primary_data = data
                if plan.get("text_sweep") and not visible_only:
                    self.sweep_text(sid, data["metrics"]["page_h"], vp["css_height"])
        for ev in page.get("interactions", []):
            self.interaction(ev)
        for item in page.get("untested_controls", []):
            self.coverage_interactions.append({"ref": item["description"][:300], "status": item.get("status", "untested"),
                                               "reason": item["reason"][:500]})

    def sweep_text(self, state_id, page_h, vh):
        """Scroll through the page and add text that only appears while scrolling (reveal-on-scroll, scrollytelling)."""
        known = {key for (st, key) in self.span_index if st == state_id}
        cap = self.plan.get("extract_limits", {}).get("max_sweep_spans", 1500)
        added = 0
        y = vh
        while y < page_h and len(known) < cap:
            self.scroll_to(y)
            fresh = [s for s in self.extract("spans")["spans"] if s["key"] not in known]
            fresh = fresh[: max(0, cap - len(known))]
            self.add_spans(state_id, {"spans": fresh})
            known.update(s["key"] for s in fresh)
            added += len(fresh)
            y += vh
        self.scroll_to(0)
        if added:
            self.notes.append(f"{state_id}: {added} text span(s) appeared only while scrolling and were added from a scroll-through")

    def interaction(self, ev):
        if ev["action"] not in ALLOWED_ACTIONS:
            raise CaptureError(f"{ev['event_id']}: action {ev['action']!r} is not allowed (only {sorted(ALLOWED_ACTIONS)})")
        target_text = ev.get("description", "") + " " + ev["selector"]
        base = {"event_id": ev["event_id"], "action": ev["action"],
                "target": {"element_id": None, "region_id": ev.get("region_id"), "selector": ev["selector"], "description": ev.get("description", "")},
                "input_value": ev.get("input_value"), "before_state_id": self.primary_state, "after_state_id": None,
                "timing_rule": f"observe {ev.get('wait_ms', 800)} ms after the action on a fresh page load", "observed_changes": []}
        if UNSAFE.search(target_text):
            self.events.append(dict(base, execution_status="blocked", observed_result="refused by the capture safety policy (possible account, payment, or submission action)"))
            self.coverage_interactions.append({"ref": ev.get("description", ev["selector"]), "status": "blocked", "reason": "safety policy"})
            return
        self.load(self.primary)
        sel = json.dumps(ev["selector"])
        found = json.loads(self.br.js(f"(() => {{ const el = document.querySelector({sel}); if (!el) return 'null'; "
                                      f"el.scrollIntoView({{block: 'center'}}); return JSON.stringify({{submit: !!(el.closest('form') && (el.type === 'submit')), text: (el.innerText || '').slice(0, 80)}}); }})()"))
        if found is None:
            self.events.append(dict(base, execution_status="failed", observed_result="target selector not found on a fresh load"))
            self.coverage_interactions.append({"ref": ev.get("description", ev["selector"]), "status": "failed", "reason": "target not found"})
            return
        if found["submit"] or UNSAFE.search(found["text"]):
            self.events.append(dict(base, execution_status="blocked", observed_result="refused: the target submits a form or looks like an account or payment action"))
            self.coverage_interactions.append({"ref": ev.get("description", ev["selector"]), "status": "blocked", "reason": "safety policy"})
            return
        # Content revealed on scroll (lazy dashboards, scrollytelling) can need a moment after scrollIntoView;
        # wait for the target to be visible instead of letting the click time out.
        if not self.wait_visible(ev["selector"], ev.get("visible_timeout_ms", 3000)):
            self.events.append(dict(base, execution_status="failed",
                                    observed_result="target stayed hidden after it was scrolled into view; it may appear only after other steps"))
            self.coverage_interactions.append({"ref": ev.get("description", ev["selector"]), "status": "failed", "reason": "target not visible"})
            return
        time.sleep(ev.get("settle_ms", 300) / 1000)  # let scroll-triggered changes finish before the before snapshot
        el_key = ev["selector"]
        base["target"]["element_id"] = next((eid for (st, key), eid in self.el_index.items()
                                             if st == self.primary_state and key == el_key), None)
        before = self.extract("text_map")
        if ev.get("shot_before"):
            existing = next((a for a in self.assets if a["state_id"] == self.primary_state and a["kind"] == "viewport_screenshot"
                             and abs(a["scroll_y"] - before["metrics"]["sy"]) < 1), None)
            if existing is None:
                self.screenshot(self.primary_state, self.primary)
            else:
                self.notes.append(f"{ev['event_id']}: reused {existing['asset_id']} as the before image (same state and scroll)")
        url_before = before["metrics"]["href"]
        try:
            if ev["action"] == "select":
                self.br.run("select", ev["selector"], ev.get("input_value", ""))
            elif ev["action"] == "keypress":
                self.br.run("press", ev.get("input_value", "Enter"))
            elif ev["action"] == "scroll":
                self.br.run("scroll", ev["selector"])
            else:
                self.br.run(ev["action"], ev["selector"])
        except CaptureError as err:
            self.events.append(dict(base, execution_status="failed", observed_result=f"action failed: {str(err)[:300]}"))
            self.coverage_interactions.append({"ref": ev.get("description", ev["selector"]), "status": "failed", "reason": "action error"})
            return
        time.sleep(ev.get("wait_ms", 800) / 1000)
        after = self.extract("full")
        after_map = {s["key"]: s["text"] for s in after["spans"]}
        region_of = dict(before.get("regions_of", {}), **{s["key"]: s["region_id"] for s in after["spans"]})
        observe = set(ev.get("observe_region_ids", [])) | ({ev["region_id"]} if ev.get("region_id") else set())
        changes, changed_keys, outside = [], set(), []
        for key in sorted(set(before["map"]) | set(after_map)):
            old, new = before["map"].get(key), after_map.get(key)
            if old != new:
                changed_keys.add(key)
                detail = f"{key}: {json.dumps(old)} -> {json.dumps(new)}"
                if observe and region_of.get(key) not in observe:
                    # Scroll-driven pages also change on their own; keep these, but say they are outside the target's regions.
                    outside.append({"kind": "text_changed", "detail": f"[outside the observed regions] {detail}"[:500]})
                else:
                    changes.append({"kind": "text_changed", "detail": detail[:500]})
        changes += outside
        after_attrs = self.extract("text_map")["state_attrs"]  # same key format as the before snapshot
        attr_changes = sorted(set(after_attrs) - set(before["state_attrs"]))
        if attr_changes:
            changes.append({"kind": "dom_changed", "detail": f"state attributes changed: {'; '.join(attr_changes)[:420]}"})
        if not changes:
            changes.append({"kind": "text_unchanged", "detail": "no visible text changed"})
            changes.append({"kind": "dom_unchanged", "detail": "no aria-pressed/expanded/selected or input value changed"})
        if after["metrics"]["href"] != url_before:
            changes.append({"kind": "navigation", "detail": "the page location changed; the new page was not captured further"})
        sid = self.new_state(self.primary, "after_interaction", after["metrics"], f"after {ev['event_id']}: {ev['action']} on {ev.get('description', ev['selector'])}")
        self.region_rects[sid] = {r["region_id"]: r["rect"] for r in after["regions"] if r["found"]}
        self.add_spans(sid, after, keep=lambda s: s["region_id"] in observe or s["key"] in changed_keys)
        self.add_elements(sid, after, keep=lambda e: e["region_id"] in observe)
        shot_after = ev.get("shot_after", True)
        if shot_after == "if_changed":
            # Site plans spend the shared image budget only on clicks that visibly changed something.
            changed_here = any(c["kind"] == "text_changed" and not c["detail"].startswith("[outside") for c in changes)
            if not (changed_here or attr_changes):
                self.notes.append(f"{ev['event_id']}: no after screenshot (nothing changed in the observed regions)")
            elif len(self.assets) >= self.plan["max_images"]:
                self.notes.append(f"{ev['event_id']}: no after screenshot (the image budget of {self.plan['max_images']} was used up)")
            else:
                self.screenshot(sid, self.primary)
        elif shot_after:
            self.screenshot(sid, self.primary)
        self.page_h = after["metrics"]["page_h"]
        result = "text or state changed" if any(c["kind"] in ("text_changed", "dom_changed") for c in changes) else "no visible change detected"
        self.events.append(dict(base, after_state_id=sid, execution_status="completed",
                                observed_result=f"action completed; {result} within {ev.get('wait_ms', 800)} ms", observed_changes=changes))
        self.coverage_interactions.append({"ref": ev.get("description", ev["selector"]), "status": "captured", "reason": f"recorded as {ev['event_id']}"})

    # --- manifest ---------------------------------------------------------------

    def build_manifest(self):
        plan = self.plan
        regions = []
        for page in self.pages:
            for r in page["regions"]:
                appearances = []
                for sid, rects in self.region_rects.items():
                    if r["region_id"] in rects:
                        appearances += self.appearances_for(rects[r["region_id"]], sid, self.page_h_by_state.get(sid, 0))
                regions.append({"region_id": r["region_id"], "name": r["name"], "route": page["route"],
                                "description": r.get("description", ""), "selector": r["selector"], "appearances": appearances})
        routes = []
        for page in self.pages:
            page_states = [s for s in self.states if s["route"] == page["route"]]
            complete = page_states and all(s["load_status"] == "complete" for s in page_states)
            reason = "single route captured; other routes not attempted" if len(self.pages) == 1 and not plan.get("skipped_routes") \
                else f"{sum(1 for a in self.assets if a['route'] == page['route'])} screenshot(s); text from the whole page"
            routes.append({"ref": page["route"], "status": "captured" if complete else "partial", "reason": reason})
        routes += [{"ref": s["route"][:300], "status": s.get("status", "not_attempted"), "reason": s["reason"][:500]}
                   for s in plan.get("skipped_routes", [])]
        spans = [{k: v for k, v in s.items() if not k.startswith("_")} for s in self.spans]
        transformations, leakage = self.blind(spans)
        excerpts = self.source_excerpts()
        cov_regions = []
        for r in regions:
            shown = any(ap["asset_id"] for ap in r["appearances"]
                        if next(a for a in self.assets if a["asset_id"] == ap["asset_id"])["kind"] == "viewport_screenshot")
            has_text = any(s["region_id"] == r["region_id"] for s in spans)
            status, reason = ("captured", "shown in at least one viewport screenshot") if shown else \
                (("partial", "text captured but not shown in any viewport screenshot") if has_text else ("not_attempted", "outside the captured screenshots and text scope"))
            cov_regions.append({"ref": r["region_id"], "status": status, "reason": reason})
        manifest = {
            "schema_version": "website-slop-audit/capture-bundle/0.1",
            "bundle_id": plan["bundle_id"],
            "site_id": plan["site_id"],
            "capture": {"captured_at": now(), "protocol_version": PROTOCOL,
                        "adapter": dict(ADAPTER, browser=f"gstack browse ({self.br.version})"),
                        "target_kind": plan.get("target_kind", "local_server"),
                        "target_locator": None if plan["blinding"]["profile"] == "blinded" else plan.get("url", self.url),
                        "snapshot_id": plan.get("snapshot_id"),
                        "notes": self.notes + [f"{len(self.br.log)} browser commands issued"]},
            "evidence_profile": {"capture_profile": plan.get("capture_profile", "custom"), "max_images": plan["max_images"],
                                 "selection_rules_applied": plan.get("selection_rules", [])},
            "modalities": {"screenshot": bool(self.assets), "text": bool(spans), "dom": bool(self.elements),
                           "computed_style": any(e["computed_style"] for e in self.elements),
                           "interaction": bool(self.events), "source": bool(excerpts)},
            "capability_limits": self.limits + ["animation playback is not recorded; motion can only be inferred from captured styles",
                                                "HTML comments, alt text, and hidden elements are not captured as text spans"],
            "context": plan["context"],
            "blinding": {"profile": plan["blinding"]["profile"], "transformations": transformations,
                         "withheld_fields": plan["blinding"].get("withheld_fields", []), "known_leakage": leakage},
            "viewports": plan["viewports"],
            "states": self.states,
            "regions": regions,
            "assets": self.assets,
            "text_spans": spans,
            "dom_elements": self.elements,
            "interactions": self.events,
            "source_excerpts": excerpts,
            "coverage": {
                "routes": routes,
                "regions": cov_regions,
                "viewports": [{"ref": v["viewport_id"], "status": "captured", "reason": f"{sum(1 for a in self.assets if a['viewport_id'] == v['viewport_id'])} screenshot(s)"} for v in plan["viewports"]],
                "interactions": self.coverage_interactions,
                "notes": plan.get("coverage_notes", []),
            },
        }
        return manifest

    def blind(self, spans):
        terms = self.plan["blinding"].get("withhold_terms", [])
        transformations, leakage = [], []
        if self.plan["blinding"]["profile"] == "blinded":
            transformations.append({"transformation_id": "TR-locator", "kind": "locator_withheld",
                                    "description": "capture.target_locator withheld; the original is in the private sidecar", "applies_to": [self.plan["bundle_id"]]})
        for i, term in enumerate(terms, 1):
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            hit = [s for s in spans if pattern.search(s["text"])]
            if not hit:
                continue
            for s in hit:
                s["text"] = pattern.sub(f"[WITHHELD-{i}]", s["text"])
            transformations.append({"transformation_id": f"TR-mask-{i}", "kind": "text_mask",
                                    "description": f"withheld term {i} replaced with [WITHHELD-{i}] in text spans", "applies_to": [s["span_id"] for s in hit]})
            assets = sorted({ap["asset_id"] for s in hit for ap in s["appearances"]})
            if assets:
                leakage.append({"leak_id": f"LK-{i}", "kind": "visible_in_screenshot",
                                "description": f"withheld term {i} is visible in screenshots and was not altered (altering pixels would change the artifact)", "asset_ids": assets})
        return transformations, leakage

    def source_excerpts(self):
        out = []
        root = Path(self.plan.get("source_root", "."))
        for i, src in enumerate(self.plan.get("source_files", []), 1):
            lines = (root / src["path"]).read_text(encoding="utf-8").splitlines()
            text = "\n".join(lines[src["line_start"] - 1:src["line_end"]])
            out.append({"excerpt_id": f"SX{i:02d}", "path": src["path"], "line_start": src["line_start"], "line_end": src["line_end"],
                        "sha256": _lib.sha256_bytes(text.encode("utf-8")), "language": Path(src["path"]).suffix.lstrip(".") or "text",
                        "text": text, "maps_to_region_ids": src.get("maps_to_region_ids", [])})
        return out


def expand_pilot8(plan):
    """Set the viewports and shots of the pilot-8 capture profile (see assets/profiles.json)."""
    plan["viewports"] = [
        {"viewport_id": "V1", "device": "desktop", "css_width": 1280, "css_height": 800, "device_pixel_ratio": 1},
        {"viewport_id": "V2", "device": "mobile", "css_width": 390, "css_height": 844, "device_pixel_ratio": 2},
    ]
    plan["shots"] = [{"viewport_id": "V1", "scroll_y": y} for y in (0, 800, 1600)] + \
                    [{"viewport_id": "V2", "scroll_y": y} for y in (0, 844)] + [{"viewport_id": "V1", "full_page": True}]
    plan["max_images"] = 8
    plan["selection_rules"] = _lib.load_profiles()["capture_profiles"]["pilot-8"]["selection_rules"]
    return plan


def is_local(url):
    host = urlparse(url).hostname or ""
    return host in LOCAL_HOSTS or host.endswith((".localhost", ".test"))


def run_plan(plan, out_dir, browser, base_url, allow_public=False, private_out=None, freeze=False):
    """Capture an expanded plan into OUT_DIR, validate it, and optionally freeze it. Returns the validation report."""
    out = Path(out_dir).resolve()  # the browse daemon resolves paths against its own cwd
    for page in plan_pages(plan, base_url):
        if not is_local(page["url"]) and not allow_public:
            raise CaptureError(f"{urlparse(page['url']).hostname} is not a local host; pass --allow-public to capture a public page "
                               "(read-only, plan URL only)")
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    plan.setdefault("url", base_url)
    manifest = Capture(plan, out, browser, base_url).run()
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if private_out:
        Path(private_out).write_text(json.dumps({"bundle_id": plan["bundle_id"], "target_locator": plan.get("public_url", plan["url"]),
                                                 "withhold_terms": plan["blinding"].get("withhold_terms", []),
                                                 "captured_at": manifest["capture"]["captured_at"]}, indent=2) + "\n", encoding="utf-8")
    report, bundle = validate_bundle.validate(out)
    if report.ok and freeze:
        validate_bundle.freeze(bundle)
    return report


def capture(plan_path, out_dir, serve=None, allow_public=False, private_out=None, freeze=False):
    plan = _lib.load_json(plan_path)
    if plan.get("capture_profile") == "pilot-8":
        plan = expand_pilot8(plan)
    browser = Browser(browse_binary(), [])
    with (static_server(serve) if serve else contextlib.nullcontext(None)) as base:
        url = (base + plan.get("route", "/")) if base else plan["url"]
        plan["url"] = url
        return run_plan(plan, out_dir, browser, url, allow_public, private_out, freeze)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("plan")
    p.add_argument("--out", required=True)
    p.add_argument("--serve", help="serve this directory on 127.0.0.1 and capture plan['route'] from it")
    p.add_argument("--allow-public", action="store_true")
    p.add_argument("--private-out", help="write the withheld locator and terms to this file (keep it outside shared bundles)")
    p.add_argument("--freeze", action="store_true")
    a = p.parse_args(argv)
    try:
        report = capture(a.plan, a.out, a.serve, a.allow_public, a.private_out, a.freeze)
    except CaptureError as err:
        print(f"capture failed: {err}", file=sys.stderr)
        return 1
    report.print()
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
