# Capture adapters (evidence acquisition layer)

Ways to produce a capture bundle (`website-slop-audit/references/capture-protocol.md`), and the live
exploration session (`website-slop-audit/references/exploration-protocol.md`):

| Adapter | Use for | Status |
|---|---|---|
| `site_capture.py` | The one-line URL command: the standard tour of a whole site from one URL (profile `site-full`; `site-auto` with `--quick`) | Working on local fixtures (live tests) and on public DSC 106 sites |
| `explore_session.py` | The live exploration behind `scripts/explore.py`: logged, rule-bound browsing of the audited site | Working on a local fixture (live test) and in the end-to-end run |
| `gstack_capture.py` | Live capture of a local or permitted public page from a hand-written plan (`pilot-8`, `custom`) | Working on local fixture sites and on three mirrored DSC 106 sites |
| `supplied_bundle.py` | Building a bundle from supplied source excerpts and optional screenshots, with no browser | Working |

## site_capture.py

```bash
python3 integrations/capture/site_capture.py https://someone.github.io/project/
python3 integrations/capture/site_capture.py https://someone.github.io/project/ --single-page --quick --budget 8
python3 integrations/capture/site_capture.py --serve path/to/local/copy /index.html
```

The skill reaches it through `website-slop-audit/scripts/acquire_url.py`, so
the audit instructions never name a browser. It writes the capture plan
itself, so the evidence does not depend on which agent or model asked:

- **Pages:** the URL plus pages linked from it on the same host and under the
  URL's folder (a GitHub Pages project stays in its repository path),
  breadth-first, robots.txt honored, at most `--max-pages` (12). Links to
  other hosts, files (PDF, CSV, images), `mailto:` and `javascript:` are never
  opened. Pages it would not open are listed in route coverage.
- **Regions:** each page's top-level sections, unwrapping single full-page
  wrappers and expanding `<main>`, named by their own heading.
- **Discovery while scrolling:** controls and text are collected at every
  viewport height down the page, so reveal-on-scroll content is included.
- **Interactions:** each safe control (buttons, tabs, toggles, dropdowns,
  disclosure widgets, checkboxes, and in the standard tour sliders, moved to
  each end) used once on a fresh load, round-robin across sections, at most
  `--max-controls` (25; 10 with `--quick`) per page. Before acting it
  scrolls the target into view and waits until it is visible. Text changes
  outside the control's own section are labelled `[outside the observed
  regions]`, because scroll-driven pages also change by themselves.
- **Refused or untested:** buttons that submit forms, downloads, and anything
  worded like sign-in, purchase, send, delete, or account changes (blocked);
  text fields (and sliders, with `--quick`) untested; repeats and controls
  over the limit (untested, with the reason).
- **The standard tour (default, `site-full`):** every page top to bottom at
  1280x800, reached by smooth scrolling (`tour.js scrollSmooth`); after the
  load and after each scroll step it watches for running animations and DOM
  changes until the view settles (at most 2.5 s), keeps the settled view, and
  keeps one earlier frame when it differs (`motion_frame`, linked in the
  manifest's `motion`). Mutations caused by screenshots themselves (an
  injected style, input carets) are ignored. Every SVG or canvas graphic of at
  least 150x100 px is hovered at a fixed sample of marks (4, spread left to
  right; real pointer for SVG shapes, pointer events at points for canvas and
  overlays), with the pointer parked in a corner between charts; tooltips,
  native `<title>` text, and pixel changes are recorded as `hover`
  interactions (`H001`, …). Then every page top to bottom at 390x844, DPR 1.
- **Images:** one ceiling (`--budget`, default 300, at most 400) in priority
  order: desktop frames (up to 60%), phone frames (up to 30%), then motion
  frames, hovers, and after-click views, shared evenly across pages. Per-page
  coverage numbers go to `coverage.tour` and `site.json`. With `--quick`: one
  budget of at most 64 (the top of every page, the entry page top to bottom,
  other pages spread, phone views, after-click screenshots only on change).
  No full-page overviews in either.
- **Output:** `RUN_DIR/bundle` (validated, frozen), `plan.json`, `site.json`,
  and `private.json` when `--withhold` blinds the bundle. The default
  `RUN_DIR` is `slop-audit/local-runs/<site>-<time>`, which git ignores.

## explore_session.py

```bash
python3 integrations/capture/explore_session.py start --bundle RUN/bundle --tour-audit RUN/runs/X/audit.tour.json --out RUN/runs/X/exploration
python3 integrations/capture/explore_session.py hover --session RUN/runs/X/exploration "#chart circle" --nth 3
python3 integrations/capture/explore_session.py finish --session RUN/runs/X/exploration
```

The skill reaches it through `website-slop-audit/scripts/explore.py`. Each
command is its own process; the session lives in `session.json` and in a
gstack tab of its own (reopened at the same scroll position if the browser
restarted). It enforces the scope, robots.txt, the safety rules, and the
budget itself, logs every action (refused ones too) with its screenshot, and
on `finish` writes `exploration.json`, validates it, and locks it. `--serve
DIR` serves a local copy on 127.0.0.1 for tests (the server is stopped on
`finish`). Run one exploration at a time: explorations and captures share
gstack's browser.

## gstack_capture.py

```bash
uv run python integrations/capture/gstack_capture.py PLAN.json --out BUNDLE --serve SITE_DIR --freeze
uv run python integrations/capture/gstack_capture.py PLAN.json --out BUNDLE --allow-public --private-out private.json --freeze
```

It drives gstack's own headless Chromium (`$B`, found at
`~/.claude/skills/gstack/browse/dist/browse` or `$GSTACK_BROWSE`), not the
user's signed-in Aside browser, so evidence is not personalized. Per page and
viewport it records screenshots, visible text spans with stable ids and
boxes, DOM elements with real selectors and computed styles, and load signals
(`aria-busy`, failed or pending fonts, incomplete images). Recorded
interactions reload the page, act on the plan's selector, wait the plan's
timing, and diff text and state attributes before and after.

**Plan fields** (see `fixtures/build_fixtures.py` for examples): `bundle_id`,
`site_id` (opaque), `route`, `url` (with `--allow-public`) or `--serve DIR`,
`capture_profile` (`pilot-8` fills viewports and shots; `custom` uses
`viewports` and `shots`), `max_images`, `blinding` (`profile`,
`withhold_terms`, `withheld_fields`), `context` (values marked
provided/inferred/unknown), `regions` (neutral names and selectors),
`interactions` (`event_id`, `action`, `selector`, `region_id`,
`description`, `observe_region_ids`, `wait_ms`, `shot_before`, `shot_after`),
`untested_controls`, `source_files`, `text_scope`
(`visible_in_screenshots` to limit text to captured views), `settle_ms`,
`capability_limits`, `coverage_notes`.

**Safety.** Only the plan's URL is opened and links are never followed. Only
click, hover, select, scroll, and keypress run. Form submissions and targets
whose text or selector looks like sign-in, purchase, send, delete, or account
changes are refused and recorded as `blocked`. A non-local host requires
`--allow-public`. Page content is stored as data. Withheld terms are masked in
text spans; if they are visible in screenshots, the pixels are left alone and
a leakage entry is recorded. The original URL goes only to `--private-out`.

**Limits.** Animation playback is not recorded (only animation and transition
styles). HTML comments, alt text, and hidden elements are not captured as text
spans. One route per hand-written plan; `site_capture.py` writes multi-page plans
(a `pages` list) that this adapter also runs.

## supplied_bundle.py

```bash
uv run python integrations/capture/supplied_bundle.py SPEC.json --out BUNDLE --freeze
```

See its docstring for the spec fields. Screenshots must come with their
viewport and scroll metadata; nothing is guessed. A spec without screenshots
yields a bundle whose modalities say so, so auditors cannot claim visual
evidence.
