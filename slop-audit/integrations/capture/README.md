# Capture adapters (evidence acquisition layer)

Two ways to produce a capture bundle (`website-slop-audit/references/capture-protocol.md`):

| Adapter | Use for | Status |
|---|---|---|
| `gstack_capture.py` | Live capture of a local or permitted public page through gstack browse's headless browser | Working on local fixture sites; public capture untested |
| `supplied_bundle.py` | Building a bundle from supplied source excerpts and optional screenshots, with no browser | Working |

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
spans. One route per plan.

## supplied_bundle.py

```bash
uv run python integrations/capture/supplied_bundle.py SPEC.json --out BUNDLE --freeze
```

See its docstring for the spec fields. Screenshots must come with their
viewport and scroll metadata; nothing is guessed. A spec without screenshots
yields a bundle whose modalities say so, so auditors cannot claim visual
evidence.
