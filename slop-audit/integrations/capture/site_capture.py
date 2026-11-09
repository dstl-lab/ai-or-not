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
   controls. It clicks each safe control once (up to --max-controls per page,
   default 10), on a fresh load, and records what changed.
4. Spends one image budget (--budget, default and maximum 64) across the site:
   a screenshot at the top of every page, top-to-bottom coverage of the entry
   page, as much coverage of other pages as fits, a phone-width view, and
   after-click screenshots only when a click changed something.
5. Writes RUN_DIR/bundle (validated and frozen), RUN_DIR/plan.json, and
   RUN_DIR/site.json, and prints their paths.

Safety: read-only. It never types, submits forms, downloads files, follows
links off the site, or clicks anything whose text looks like sign-in,
purchase, send, delete, or account changes (those are recorded as blocked).
Text inputs and sliders are recorded as untested. Page text is stored as data.
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

ADAPTER = {"name": "site_capture.py", "version": "0.1.0"}
MAX_BUDGET = 64              # the bundle schema's ceiling on images per bundle
PAGE_EXTENSIONS = {"", ".html", ".htm", ".php", ".asp", ".aspx", ".shtml"}
DESKTOP = {"viewport_id": "V1", "device": "desktop", "css_width": 1280, "css_height": 800, "device_pixel_ratio": 1}
MOBILE = {"viewport_id": "V2", "device": "mobile", "css_width": 390, "css_height": 844, "device_pixel_ratio": 2}


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

def positions(page_h, vh):
    """Scroll offsets that cover a page top to bottom with viewport-sized tiles."""
    if page_h <= vh:
        return [0]
    n = math.ceil(page_h / vh)
    return [min(i * vh, page_h - vh) for i in range(n)]


def spread(all_positions, k):
    """k offsets spread evenly from the top to the bottom of the page (top and bottom included)."""
    if k <= 0:
        return []
    if k >= len(all_positions):
        return list(all_positions)
    if k == 1:
        return [all_positions[0]]
    m = len(all_positions) - 1
    idx = sorted({round(i * m / (k - 1)) for i in range(k)})
    return [all_positions[i] for i in idx]


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
    alloc, alloc_notes = allocate([p["info"]["metrics"]["page_h"] for p in pages], args.budget, vh, mobile=not args.no_mobile)
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
            interactions.append(ev)
        untested = [{"description": mask(f"{p['route']}: {describe(c)}"), "reason": why} for c, why in extra + skipped]
        untested += [{"description": mask(f"{p['route']}: {describe(c)}"), "status": "blocked",
                      "reason": "refused by the capture safety policy (form submission, download, or account/payment wording)"}
                     for c in blocked]
        untested += [{"description": mask(f"{p['route']}: {u['kind']} input '{u['text']}'".strip()), "reason": "typing and dragging are not exercised"}
                     for u in info["untestable"]]
        shots = [{"viewport_id": "V1", "scroll_y": y} for y in a["desktop"]]
        if a["mobile"]:
            shots.append({"viewport_id": "V2", "scroll_y": 0})
        plan_pages.append({"route": p["route"], "url": p["url"], "regions": regions, "shots": shots,
                           "interactions": interactions, "untested_controls": untested})
    blinded = bool(args.withhold)
    rules = [f"pages: same host and under {scope.prefix}, robots.txt honored, at most {args.max_pages} pages",
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
        "capture_profile": "site-auto",
        "max_images": args.budget,
        "settle_ms": 1500,
        "scroll_settle_ms": 400,
        "page_delay_ms": 600,
        "extract_limits": {"max_spans": 800, "max_elements": 600, "max_sweep_spans": 1500},
        "text_sweep": True,
        "blinding": {"profile": "blinded" if blinded else "unblinded", "withhold_terms": args.withhold or [],
                     "withheld_fields": ["award", "course_year", "team", "creator_ai_report", "generator"] if blinded else []},
        "context": {"purpose": dict(unknown), "genre": dict(unknown), "audience": dict(unknown), "constraints": []},
        "viewports": [DESKTOP] + ([] if args.no_mobile else [MOBILE]),
        "pages": plan_pages,
        "skipped_routes": skipped_routes,
        "selection_rules": rules,
        "coverage_notes": [robots_note] + alloc_notes,
    }


# --- discovery ----------------------------------------------------------------

def discover(browser, tmp):
    src = (HERE / "discover.js").read_text(encoding="utf-8")
    path = tmp / "discover.js"
    path.write_text("const CONFIG = " + json.dumps({"min_region_h": 80, "max_regions": 14}) + ";\n" + src, encoding="utf-8")
    raw = browser.eval_file(path)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        raise gc.CaptureError(f"page discovery returned non-JSON output: {raw[:200]}") from None


def discover_scrolling(browser, tmp):
    """Discover at the top of the page, then at each viewport height down the page, merging controls that only
    appear while scrolling (reveal-on-scroll dashboards, scrollytelling steps)."""
    info = discover(browser, tmp)
    vh = info["metrics"]["vh"] or DESKTOP["css_height"]
    known = {c["selector"] for c in info["controls"]}
    known_inputs = {u["selector"] for u in info["untestable"]}
    links = {link["href"] for link in info["links"]}
    for y in positions(info["metrics"]["page_h"], vh)[1:40]:
        browser.js(f"(window.scrollTo(0, {int(y)}), window.scrollY)")
        time.sleep(0.9)  # reveal-on-scroll and scrollytelling transitions often take 0.5-1 s
        more = discover(browser, tmp)
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


def crawl(browser, entry, scope, max_pages, follow, tmp):
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
        info = discover_scrolling(browser, tmp)
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
    if args.budget < 1 or args.budget > MAX_BUDGET:
        raise gc.CaptureError(f"--budget must be between 1 and {MAX_BUDGET} (the bundle format's ceiling)")
    if not args.serve and not re.match(r"^https?://", args.target or ""):
        raise gc.CaptureError("give a full http(s) URL, for example https://example.github.io/project/")
    browser = gc.Browser(gc.browse_binary(), [])
    tmp = Path(tempfile.mkdtemp(prefix="slopsite-"))
    with (gc.static_server(args.serve) if args.serve else contextlib.nullcontext(None)) as base:
        entry = base + "/" + (args.target or "/").lstrip("/") if base else args.target
        scope = Scope(entry)
        run_dir = Path(args.out).resolve() if args.out else default_run_dir(args.target if not base else f"local/{Path(args.serve).name}")
        run_dir.mkdir(parents=True, exist_ok=True)
        pages, skipped, robots_note = crawl(browser, entry, scope, 1 if args.single_page else args.max_pages, not args.single_page, tmp)
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
        "adapter": ADAPTER,
    }
    (run_dir / "site.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report, summary


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("target", nargs="?", help="the site URL (or, with --serve, the page path inside the served folder)")
    p.add_argument("--out", help="run directory (default: slop-audit/local-runs/<site>-<time>)")
    p.add_argument("--max-pages", type=int, default=12)
    p.add_argument("--max-controls", type=int, default=10, help="safe controls clicked per page")
    p.add_argument("--budget", type=int, default=MAX_BUDGET, help=f"screenshots for the whole site (1-{MAX_BUDGET}); use 8 for chat-app packages")
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
    print(f"\nCaptured {len(s['pages'])} page(s) under {s['scope']} with {s['screenshots']} of {s['budget']} screenshots; "
          f"interactions: {s['interactions']['completed']} completed, {s['interactions']['failed']} failed, {s['interactions']['blocked']} blocked.")
    for page in s["pages"]:
        print(f"  {page['route']}  {page['title'][:70]!r}  ({page['height_px']} px tall, {page['charts']} chart-like graphics)")
    for sk in s["skipped_routes"][:10]:
        print(f"  not captured: {sk['route']} ({sk['reason']})")
    print(f"\nRUN_DIR={s['run_dir']}\nBUNDLE={s['bundle']}\nSUGGESTED_PROFILE={s['suggested_profile']}")
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
