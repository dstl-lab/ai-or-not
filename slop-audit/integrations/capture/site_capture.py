#!/usr/bin/env python3
"""Capture a whole website from one URL into a frozen website-slop-audit bundle (gstack browse).

    python integrations/capture/site_capture.py https://example.github.io/project/
    python integrations/capture/site_capture.py --serve path/to/site /index.html     # a local copy

This is the one-line acquisition path behind the `/website-slop-audit <url>`
command. It writes the capture plan itself, so the evidence does not depend
on which agent or model asked for it: the same URL and options give the same
kind of bundle, which can then be audited by any model or annotated by people.

What it does, in order:

1. Opens the URL in gstack's headless browser (no personal cookies or sign-ins).
2. Finds the site's pages by following links that stay on the same host and
   under the URL's folder (a GitHub Pages project stays inside its repository
   path), honoring robots.txt, up to --max-pages (default 12).
3. On each page, records its top-level sections as regions and lists its
   controls. It exercises each safe control once (up to --max-controls per
   page), on a fresh load, and records what changed.
4. Takes the standard tour (capture profile `site-full`, the default): every
   page top to bottom at desktop width, reached by scrolling smoothly so
   scroll-triggered effects fire; a mid-motion frame wherever the view was
   still changing after a load or scroll step; a fixed sample of hovers on
   every chart; sliders moved to their ends; every page top to bottom at
   phone width. One image ceiling (--budget, default 300, at most 400) is
   spent in that priority order, and every page's coverage is recorded.
   With --quick it takes the older, smaller `site-auto` capture instead
   (at most 64 images, long pages spread, no motion frames or hovers).
5. Writes RUN_DIR/bundle (validated and frozen), RUN_DIR/plan.json, and
   RUN_DIR/site.json, and prints their paths.

Safety: read-only. It never types, submits forms, downloads files, follows
links off the site, or clicks anything whose text looks like sign-in,
purchase, send, delete, or account changes (those are recorded as blocked).
Text inputs are recorded as untested (and sliders too, with --quick). Page
text is stored as data.
"""

import argparse
import contextlib
import json
import math
import re
import sys
import tempfile
import time
from collections import OrderedDict, deque
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urldefrag, urlparse, urlunparse
from urllib.robotparser import RobotFileParser

HERE = Path(__file__).resolve().parent
SLOP_ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
import gstack_capture as gc  # noqa: E402

ADAPTER = {"name": "site_capture.py", "version": "0.2.0"}
MAX_BUDGET = 400             # the bundle schema's ceiling on images per bundle
QUICK_MAX_BUDGET = 64        # the older site-auto capture
FULL_DEFAULT_BUDGET = 300
PAGE_EXTENSIONS = {"", ".html", ".htm", ".php", ".asp", ".aspx", ".shtml"}
DESKTOP = {"viewport_id": "V1", "device": "desktop", "css_width": 1280, "css_height": 800, "device_pixel_ratio": 1}
MOBILE = {"viewport_id": "V2", "device": "mobile", "css_width": 390, "css_height": 844, "device_pixel_ratio": 2}
MOBILE_FULL = dict(MOBILE, device_pixel_ratio=1)   # a whole page of phone frames at DPR 2 is four times the image data


# --- scope -------------------------------------------------------------------

def canonical(url):
    """One spelling per page: no fragment, lowercase host, no default port, 'dir/index.html' == 'dir/'."""
    url, _ = urldefrag(url)
    p = urlparse(url)
    host = (p.hostname or "").lower()
    port = f":{p.port}" if p.port and not ((p.scheme == "http" and p.port == 80) or (p.scheme == "https" and p.port == 443)) else ""
    path = p.path or "/"
    if re.search(r"/index\.html?$", path):
        path = path[: path.rfind("/") + 1]
    return urlunparse((p.scheme, host + port, path, "", p.query, ""))


class Scope:
    """Same scheme and host, and under the folder of the entry URL."""

    def __init__(self, entry):
        self.entry = canonical(entry)
        p = urlparse(self.entry)
        self.origin = f"{p.scheme}://{p.netloc}"
        last = p.path.rsplit("/", 1)[-1]
        if p.path.endswith("/"):
            self.prefix = p.path
        elif "." not in last:          # https://user.github.io/project means the project folder, not the whole host
            self.prefix = p.path + "/"
        else:                          # https://user.github.io/project/story.html
            self.prefix = p.path[: p.path.rfind("/") + 1]

    def contains(self, url):
        p = urlparse(canonical(url))
        return f"{p.scheme}://{p.netloc}" == self.origin and (p.path.startswith(self.prefix) or p.path == self.prefix.rstrip("/"))

    def route(self, url):
        p = urlparse(canonical(url))
        return (p.path + (f"?{p.query}" if p.query else ""))[:300]


def is_page_link(url):
    p = urlparse(url)
    if p.scheme not in ("http", "https"):
        return False
    return Path(p.path).suffix.lower() in PAGE_EXTENSIONS


def slug(text, limit=44):
    s = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    return (s or "site")[:limit].strip("-") or "site"


# --- planning ----------------------------------------------------------------

positions = gc.positions   # scroll offsets that cover a page top to bottom
spread = gc.spread         # k items spread evenly from the first to the last


def share(needs, cap, minimum=1):
    """Split cap across needs in proportion (largest remainder), giving each at least `minimum` (but never more
    than it needs)."""
    if sum(needs) <= cap:
        return list(needs)
    give = [min(minimum, n) for n in needs]
    left = cap - sum(give)
    if left <= 0:
        return give
    rest = [n - g for n, g in zip(needs, give)]
    total = sum(rest)
    raw = [left * r / total for r in rest]
    add = [math.floor(x) for x in raw]
    order = sorted(range(len(raw)), key=lambda i: (raw[i] - add[i], -i), reverse=True)
    for i in order[: left - sum(add)]:
        add[i] += 1
    return [g + a for g, a in zip(give, add)]


def allocate_full(heights, budget, vh, mobile=True, max_tiles_per_page=60, desktop_share=0.6, phone_share=0.3,
                  phone_vh=MOBILE["css_height"]):
    """The standard tour's image plan. Returns ([{desktop, phone_quota, desktop_needed}], notes, extras).

    Desktop frames for every page come first (up to 60% of the budget), phone frames next (up to 30%,
    estimated from the desktop height; the capture spreads them over the real phone page), and the rest
    is left for motion frames, hovers, and after-click views, shared across pages.
    """
    need = [positions(h, vh)[:max_tiles_per_page] for h in heights]
    give = share([len(n) for n in need], int(budget * desktop_share))
    est = [max(1, math.ceil(h * 2.2 / phone_vh)) for h in heights] if mobile else [0] * len(heights)
    phone = share(est, int(budget * phone_share)) if mobile else est
    notes = [f"page {i + 1}: {give[i]} of {len(need[i])} desktop positions screenshotted (spread top to bottom); "
             "text was captured for the whole page" for i in range(len(need)) if give[i] < len(need[i])]
    notes += [f"page {i + 1}: only the first {max_tiles_per_page} desktop screens ({max_tiles_per_page * vh} px) are planned"
              for i, h in enumerate(heights) if len(positions(h, vh)) > max_tiles_per_page]
    plan = [{"desktop": spread(need[i], give[i]), "phone_quota": phone[i], "desktop_needed": len(positions(heights[i], vh))}
            for i in range(len(need))]
    return plan, notes, budget - sum(give) - sum(phone)


def allocate(heights, budget, vh, mobile=True, reserve=12, max_tiles_per_page=40):
    """Split one image budget across pages. Returns ([{desktop: [scroll_y...], mobile: bool}], notes).

    Priority: a top screenshot of every page, a phone view of the entry page,
    a reserve for after-click screenshots, top-to-bottom coverage of the entry
    page, then the other pages in proportion to how much of them is unseen,
    then phone views of the other pages. Unused images stay available for
    after-click screenshots.
    """
    n = len(heights)
    need = [positions(h, vh)[:max_tiles_per_page] for h in heights]
    give = [0] * n
    left = budget
    for i in range(n):                       # 1. the top of every page
        if left > 0:
            give[i], left = 1, left - 1
    phone = [False] * n
    if mobile and n and left > 0:            # 2. the entry page at phone width
        phone[0], left = True, left - 1
    held = min(reserve, left // 3)           # 3. keep some images for after-click screenshots
    left -= held
    extra = min(len(need[0]) - give[0], left) if n else 0   # 4. the whole entry page
    give[0] += extra
    left -= extra
    while left > 0:                          # 5. other pages, most-unseen first
        gaps = [(len(need[i]) - give[i]) / len(need[i]) for i in range(n)]
        best = max(range(n), key=lambda i: (gaps[i], -i))
        if gaps[best] <= 0:
            break
        give[best] += 1
        left -= 1
    for i in range(1, n):                    # 6. other pages at phone width, if anything is left
        if mobile and left > 0:
            phone[i], left = True, left - 1
    notes = []
    for i in range(n):
        if give[i] < len(need[i]):
            notes.append(f"page {i + 1}: {give[i]} of {len(need[i])} desktop viewport positions screenshotted (spread top to bottom); "
                         "text was captured for the whole page")
    return [{"desktop": spread(need[i], give[i]), "mobile": phone[i]} for i in range(n)], notes


def choose_controls(controls, max_n):
    """Safe controls to click (round-robin across sections), plus the ones left out and why."""
    chosen, extra, blocked, skipped = [], [], [], []
    safe = OrderedDict()
    seen = set()
    for c in controls:
        label = f"{c.get('text', '')} {c['selector']}"
        if c.get("disabled"):
            skipped.append((c, "disabled"))
        elif c.get("submits") or c.get("download") or gc.UNSAFE.search(label):
            blocked.append(c)
        elif c["tag"] == "select" and not [o for o in c.get("options", []) if not o["selected"]]:
            skipped.append((c, "a dropdown with a single option"))
        elif c.get("kind") == "range" and c.get("range", {}).get("min") == c.get("range", {}).get("max"):
            skipped.append((c, "a slider with a single value"))
        else:
            key = (c.get("section"), c.get("kind"), (c.get("text") or "").lower())
            if key in seen and key[2]:
                extra.append((c, "repeats a control already clicked in this section"))
                continue
            seen.add(key)
            safe.setdefault(c.get("section"), []).append(c)
    queues = [list(v) for v in safe.values()]
    while len(chosen) < max_n and any(queues):
        for q in queues:
            if q and len(chosen) < max_n:
                chosen.append(q.pop(0))
    extra += [(c, f"not clicked: the limit of {max_n} controls per page was reached") for q in queues for c in q]
    return chosen, extra, blocked, skipped


def describe(c):
    text = c.get("text") or ""
    return (f"{c.get('kind') or c['tag']} '{text}'" if text else f"{c.get('kind') or c['tag']} ({c['selector']})")[:160]


def build_plan(entry_url, scope, pages, skipped_routes, args, robots_note):
    """Turn discovered pages into a gstack_capture plan with a `pages` list."""
    vh = DESKTOP["css_height"]
    full = not getattr(args, "quick", False)
    heights = [p["info"]["metrics"]["page_h"] for p in pages]
    if full:
        alloc, alloc_notes, extras = allocate_full(heights, args.budget, vh, mobile=not args.no_mobile)
    else:
        alloc, alloc_notes = allocate(heights, args.budget, vh, mobile=not args.no_mobile)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    site = slug((urlparse(scope.entry).hostname or "") + urlparse(scope.entry).path)
    masks = [(re.compile(re.escape(t), re.IGNORECASE), f"[WITHHELD-{i}]") for i, t in enumerate(args.withhold or [], 1) if t.strip()]

    def mask(text):  # page text reused in region names and control descriptions must be masked like text spans
        for pattern, token in masks:
            text = pattern.sub(token, text)
        return text
    plan_pages, rid, eid = [], 0, 0
    for p, a in zip(pages, alloc):
        info = p["info"]
        regions, sec_region = [], {}
        for i, s in enumerate(info["sections"]):
            rid += 1
            sec_region[i] = f"R{rid:02d}"
            regions.append({"region_id": sec_region[i], "name": mask(s["name"]), "selector": s["selector"],
                            "description": f"top-level section {i + 1} of {p['route']} (detected automatically)"})
        chosen, extra, blocked, skipped = choose_controls(info["controls"], args.max_controls)
        interactions = []
        for c in chosen:
            eid += 1
            region = sec_region.get(c.get("section"))
            ev = {"event_id": f"E{eid:02d}", "action": "click", "selector": c["selector"], "region_id": region,
                  "description": mask(describe(c)), "observe_region_ids": [region] if region else [], "wait_ms": 900,
                  "settle_ms": 700, "visible_timeout_ms": 3000, "shot_before": False, "shot_after": "if_changed"}
            if c["tag"] == "select":
                option = next(o for o in c["options"] if not o["selected"])
                ev.update(action="select", input_value=option["value"],
                          description=mask(f"{describe(c)}, choosing '{option['text']}'")[:160])
            if c.get("kind") == "range":  # both ends of the slider, each on a fresh load
                rng = c.get("range", {})
                ends = [v for v in (rng.get("min"), rng.get("max")) if v is not None and v != rng.get("value")]
                for j, v in enumerate(ends):
                    if j:
                        eid += 1
                    interactions.append(dict(ev, event_id=f"E{eid:02d}", action="set_range", input_value=str(v),
                                             description=mask(f"slider {describe(c)}, moved to {v}")[:160]))
                continue
            interactions.append(ev)
        untested = [{"description": mask(f"{p['route']}: {describe(c)}"), "reason": why} for c, why in extra + skipped]
        untested += [{"description": mask(f"{p['route']}: {describe(c)}"), "status": "blocked",
                      "reason": "refused by the capture safety policy (form submission, download, or account/payment wording)"}
                     for c in blocked]
        untested += [{"description": mask(f"{p['route']}: {u['kind']} input '{u['text']}'".strip()), "reason": "typing and dragging are not exercised"}
                     for u in info["untestable"]]
        shots = [{"viewport_id": "V1", "scroll_y": y} for y in a["desktop"]]
        if full and a["phone_quota"]:
            shots.append({"viewport_id": "V2", "auto": True, "quota": a["phone_quota"]})
        elif not full and a["mobile"]:
            shots.append({"viewport_id": "V2", "scroll_y": 0})
        entry = {"route": p["route"], "url": p["url"], "regions": regions, "shots": shots,
                 "interactions": interactions, "untested_controls": untested}
        if full:
            entry.update(desktop_needed=a["desktop_needed"], controls_found=len(info["controls"]) + len(info["untestable"]))
        plan_pages.append(entry)
    blinded = bool(args.withhold)
    if full:
        rules = [f"pages: same host and under {scope.prefix}, robots.txt honored, at most {args.max_pages} pages",
                 "regions: each page's top-level sections, detected automatically and named by their own heading",
                 f"one image ceiling of {args.budget}, spent in this order: desktop frames, then phone frames, then motion "
                 "frames, hovers, and after-click views (shared across pages)",
                 f"desktop {DESKTOP['css_width']}x{DESKTOP['css_height']} at DPR 1: every page top to bottom, reached by scrolling "
                 "smoothly in small steps so scroll-triggered effects fire",
                 "motion: after the page loads and after each scroll step, the view is watched until it settles; the settled frame is "
                 "kept, plus one mid-motion frame when the view was still changing (recorded as a motion sequence)",
                 "charts: every SVG or canvas graphic of at least 150x100 px has a fixed sample of marks hovered "
                 "(4 by default, spread left to right; canvas charts at points across the middle); what appeared is recorded",
                 "phone 390x844 at DPR 1: every page top to bottom, settled frames only" if not args.no_mobile else "no phone view",
                 f"each safe control exercised once on a fresh load (at most {args.max_controls} per page), sliders moved to both "
                 "ends; after-click screenshot only when something changed",
                 "typing, dragging, form submission, downloads, and account or payment actions are never performed"]
    else:
        rules = None
    rules = rules or [f"pages: same host and under {scope.prefix}, robots.txt honored, at most {args.max_pages} pages",
             f"desktop {DESKTOP['css_width']}x{DESKTOP['css_height']} viewport tiles from one budget of {args.budget} images: "
             "the top of every page, the entry page top to bottom, then other pages as space allows (spread top to bottom)",
             "phone 390x844 (DPR 2) top-of-page view of the entry page, and of other pages if images remain" if not args.no_mobile else "no phone view",
             f"each safe control clicked once on a fresh load (at most {args.max_controls} per page); after-click screenshot only when "
             "text or state in the control's section changed and the budget allows",
             "no full-page overview images (they shrink long pages until the text is unreadable)"]
    unknown = {"value": None, "status": "unknown", "provenance": "not supplied to the one-line capture; infer it from the pages and mark it inferred"}
    return {
        "bundle_id": f"{site}-{stamp}"[:64],
        "site_id": site[:64],
        "url": entry_url,
        "target_kind": "local_server" if gc.is_local(entry_url) else "public_url",
        "snapshot_id": None,
        "capture_profile": "site-full" if full else "site-auto",
        "max_images": args.budget,
        "settle_ms": 1500,
        "scroll_settle_ms": 400,
        "page_delay_ms": 600,
        "extract_limits": {"max_spans": 800, "max_elements": 600, "max_sweep_spans": 1500},
        "text_sweep": True,
        "blinding": {"profile": "blinded" if blinded else "unblinded", "withhold_terms": args.withhold or [],
                     "withheld_fields": ["award", "course_year", "team", "creator_ai_report", "generator"] if blinded else []},
        "context": {"purpose": dict(unknown), "genre": dict(unknown), "audience": dict(unknown), "constraints": []},
        "viewports": [DESKTOP] + ([] if args.no_mobile else [MOBILE_FULL if full else MOBILE]),
        **({"tour": {}} if full else {}),
        "pages": plan_pages,
        "skipped_routes": skipped_routes,
        "selection_rules": rules,
        "coverage_notes": [robots_note] + alloc_notes,
    }


# --- discovery ----------------------------------------------------------------

def discover(browser, tmp, sliders=False):
    src = (HERE / "discover.js").read_text(encoding="utf-8")
    path = tmp / "discover.js"
    path.write_text("const CONFIG = " + json.dumps({"min_region_h": 80, "max_regions": 14, "sliders": sliders}) + ";\n" + src, encoding="utf-8")
    raw = browser.eval_file(path)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        raise gc.CaptureError(f"page discovery returned non-JSON output: {raw[:200]}") from None


def discover_scrolling(browser, tmp, sliders=False):
    """Discover at the top of the page, then at each viewport height down the page, merging controls that only
    appear while scrolling (reveal-on-scroll dashboards, scrollytelling steps)."""
    info = discover(browser, tmp, sliders)
    vh = info["metrics"]["vh"] or DESKTOP["css_height"]
    known = {c["selector"] for c in info["controls"]}
    known_inputs = {u["selector"] for u in info["untestable"]}
    links = {link["href"] for link in info["links"]}
    for y in positions(info["metrics"]["page_h"], vh)[1:40]:
        browser.js(f"(window.scrollTo(0, {int(y)}), window.scrollY)")
        time.sleep(0.9)  # reveal-on-scroll and scrollytelling transitions often take 0.5-1 s
        more = discover(browser, tmp, sliders)
        info["controls"] += [c for c in more["controls"] if c["selector"] not in known]
        known.update(c["selector"] for c in more["controls"])
        info["untestable"] += [u for u in more["untestable"] if u["selector"] not in known_inputs]
        known_inputs.update(u["selector"] for u in more["untestable"])
        info["links"] += [link for link in more["links"] if link["href"] not in links]
        links.update(link["href"] for link in more["links"])
        info["signals"]["charts"] = max(info["signals"]["charts"], more["signals"]["charts"])
        info["metrics"]["page_h"] = max(info["metrics"]["page_h"], more["metrics"]["page_h"])
    browser.js("(window.scrollTo(0, 0), 0)")
    return info


def load_robots(browser, scope):
    expr = ("fetch('/robots.txt', {cache: 'no-store'}).then(r => r.ok ? r.text() : '')"
            ".then(t => JSON.stringify(t.slice(0, 100000))).catch(() => JSON.stringify(''))")
    try:
        text = json.loads(browser.js(expr))
    except (gc.CaptureError, json.JSONDecodeError):
        text = ""
    rp = RobotFileParser()
    rp.parse(text.splitlines())
    note = f"robots.txt at {scope.origin}/robots.txt " + ("read and honored" if text.strip() else "not found or empty; all in-scope pages allowed")
    return rp, note


def crawl(browser, entry, scope, max_pages, follow, tmp, sliders=False):
    """Breadth-first over in-scope pages. Returns (pages, skipped_routes, robots_note)."""
    browser.run("viewport", f"{DESKTOP['css_width']}x{DESKTOP['css_height']}", "--scale", "1")
    queue, seen = deque([canonical(entry)]), {canonical(entry)}
    pages, skipped, robots, note = [], [], None, ""
    while queue:
        url = queue.popleft()
        if len(pages) >= max_pages:
            skipped.append({"route": scope.route(url), "status": "not_attempted", "reason": f"page limit of {max_pages} reached"})
            continue
        if robots is not None and not robots.can_fetch("*", url):
            skipped.append({"route": scope.route(url), "status": "skipped", "reason": "disallowed by robots.txt"})
            continue
        try:
            nav = browser.run("goto", url)
        except gc.CaptureError as err:
            if not pages:
                raise
            skipped.append({"route": scope.route(url), "status": "failed", "reason": f"could not load: {str(err)[:200]}"})
            continue
        status = re.search(r"\((\d{3})\)\s*$", nav.strip().splitlines()[-1] if nav.strip() else "")
        if status and int(status.group(1)) >= 400:
            if not pages:
                raise gc.CaptureError(f"{url} returned HTTP {status.group(1)}")
            skipped.append({"route": scope.route(url), "status": "failed", "reason": f"HTTP {status.group(1)} (a broken link on the site)"})
            continue
        browser.run("wait", "--load", check=False)
        time.sleep(1.0)
        if robots is None:
            robots, note = load_robots(browser, scope)
            if not robots.can_fetch("*", url):
                raise gc.CaptureError(f"robots.txt disallows {url}; nothing was captured")
        info = discover_scrolling(browser, tmp, sliders)
        final = canonical(info["href"])
        if not scope.contains(final):
            skipped.append({"route": scope.route(url), "status": "skipped", "reason": f"redirected outside the site scope to {final[:200]}"})
            continue
        if any(p["url"] == final for p in pages):
            continue
        pages.append({"url": final, "route": scope.route(final), "info": info})
        if not follow:
            continue
        for link in info["links"]:
            target = canonical(link["href"])
            if link.get("download") or not is_page_link(target) or not scope.contains(target) or target in seen:
                continue
            seen.add(target)
            queue.append(target)
        time.sleep(0.6)
    return pages, skipped, note


# --- command ----------------------------------------------------------------------

def default_run_dir(url):
    p = urlparse(url)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return SLOP_ROOT / "local-runs" / f"{slug(p.netloc + p.path, 50)}-{stamp}"


def run(args):
    ceiling = QUICK_MAX_BUDGET if args.quick else MAX_BUDGET
    if args.budget is None:
        args.budget = QUICK_MAX_BUDGET if args.quick else FULL_DEFAULT_BUDGET
    if args.max_controls is None:
        args.max_controls = 10 if args.quick else 25
    if args.budget < 1 or args.budget > ceiling:
        raise gc.CaptureError(f"--budget must be between 1 and {ceiling}" + (" with --quick" if args.quick else " (the bundle format's ceiling)"))
    if not args.serve and not re.match(r"^https?://", args.target or ""):
        raise gc.CaptureError("give a full http(s) URL, for example https://example.github.io/project/")
    browser = gc.Browser(gc.browse_binary(), [])
    tmp = Path(tempfile.mkdtemp(prefix="slopsite-"))
    with (gc.static_server(args.serve) if args.serve else contextlib.nullcontext(None)) as base:
        entry = base + "/" + (args.target or "/").lstrip("/") if base else args.target
        scope = Scope(entry)
        run_dir = Path(args.out).resolve() if args.out else default_run_dir(args.target if not base else f"local/{Path(args.serve).name}")
        run_dir.mkdir(parents=True, exist_ok=True)
        pages, skipped, robots_note = crawl(browser, entry, scope, 1 if args.single_page else args.max_pages, not args.single_page, tmp,
                                            sliders=not args.quick)
        if not pages:
            raise gc.CaptureError("no page inside the site scope could be loaded")
        plan = build_plan(entry, scope, pages, skipped, args, robots_note)
        (run_dir / "plan.json").write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        private = run_dir / "private.json" if args.withhold else None
        report = gc.run_plan(plan, run_dir / "bundle", browser, entry, allow_public=True, private_out=private, freeze=True)
    manifest = json.loads((run_dir / "bundle" / "manifest.json").read_text(encoding="utf-8"))
    charts = sum(p["info"]["signals"]["charts"] for p in pages)
    summary = {
        "url": args.target if not base else entry, "scope": scope.origin + scope.prefix, "run_dir": str(run_dir),
        "bundle": str(run_dir / "bundle"), "bundle_valid": report.ok,
        "pages": [{"route": p["route"], "title": p["info"]["title"], "height_px": p["info"]["metrics"]["page_h"],
                   "charts": p["info"]["signals"]["charts"]} for p in pages],
        "skipped_routes": skipped,
        "screenshots": len(manifest["assets"]), "budget": args.budget,
        "interactions": {k: sum(1 for e in manifest["interactions"] if e["execution_status"] == k)
                         for k in ("completed", "failed", "blocked", "skipped", "timed_out")},
        "suggested_profile": "multimodal-datastory" if charts else "multimodal-core",
        "capture_profile": manifest["evidence_profile"]["capture_profile"],
        "tour": manifest["coverage"].get("tour", []),
        "motion_sequences": len(manifest.get("motion", [])),
        "adapter": ADAPTER,
    }
    (run_dir / "site.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report, summary


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("target", nargs="?", help="the site URL (or, with --serve, the page path inside the served folder)")
    p.add_argument("--out", help="run directory (default: slop-audit/local-runs/<site>-<time>)")
    p.add_argument("--max-pages", type=int, default=12)
    p.add_argument("--max-controls", type=int, default=None, help="safe controls exercised per page (default 25; 10 with --quick)")
    p.add_argument("--budget", type=int, default=None,
                   help=f"image ceiling for the whole site (default {FULL_DEFAULT_BUDGET}, at most {MAX_BUDGET}; with --quick default and at most "
                        f"{QUICK_MAX_BUDGET}; use --quick --budget 8 for chat-app packages)")
    p.add_argument("--quick", action="store_true", help="the older, smaller site-auto capture: no motion frames or hovers, long pages spread")
    p.add_argument("--single-page", action="store_true", help="capture only the given page")
    p.add_argument("--no-mobile", action="store_true", help="skip the phone-width views")
    p.add_argument("--withhold", action="append", default=[], metavar="TERM",
                   help="text to mask in the captured text (repeatable), e.g. team member names; blinds the bundle")
    p.add_argument("--serve", help="serve this local folder on 127.0.0.1 and capture it instead of a public URL")
    a = p.parse_args(argv)
    try:
        report, summary = run(a)
    except gc.CaptureError as err:
        print(f"capture failed: {err}", file=sys.stderr)
        return 1
    report.print()
    s = summary
    print(f"\nCaptured {len(s['pages'])} page(s) under {s['scope']} with {s['screenshots']} of {s['budget']} screenshots "
          f"({s['capture_profile']}); interactions: {s['interactions']['completed']} completed, {s['interactions']['failed']} failed, "
          f"{s['interactions']['blocked']} blocked.")
    for t in s["tour"]:
        print(f"  tour {t['route']}: desktop {t['desktop_frames']}/{t['desktop_needed']} screens, phone {t['phone_frames']}/{t['phone_needed']}, "
              f"{t['motion_sequences']} motion sequence(s), {t['charts_hovered']}/{t['charts_found']} chart(s) hovered "
              f"({t['hovers_with_response']}/{t['hovers']} hovers responded)")
    for page in s["pages"]:
        print(f"  {page['route']}  {page['title'][:70]!r}  ({page['height_px']} px tall, {page['charts']} chart-like graphics)")
    for sk in s["skipped_routes"][:10]:
        print(f"  not captured: {sk['route']} ({sk['reason']})")
    print(f"\nRUN_DIR={s['run_dir']}\nBUNDLE={s['bundle']}\nSUGGESTED_PROFILE={s['suggested_profile']}")
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
