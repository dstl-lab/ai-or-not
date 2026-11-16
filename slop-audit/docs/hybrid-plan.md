# Plan: hybrid evidence for the one-command skill

Branch `slop-skill-command-hybrid`, built on `slop-skill-command-questions`.
Written 2026-11-15 before implementation; the "Built" notes at the end say what
changed while building.

## What the study needs

The study compares how people and models see perceived AI-slop features in
websites and answer the same per-website questions (phd-reviewer-v1). Two
things pull against each other:

- **Comparability.** To say "model A and model B judged differently", both must
  have judged the same evidence.
- **Human-like viewing.** Participants scroll the live site, watch animations,
  hover over charts, and click controls before answering. A model that only sees
  a few still screenshots is not doing the same task.

The hybrid gives every model both, in a fixed order, and keeps the two apart in
the output so each can be analyzed on its own:

| Layer | What it is | Same for every model? | Answers it produces |
|---|---|---|---|
| 1. Standard tour | A frozen capture that tours every page the way a careful person would: scroll top to bottom, motion caught as frames, chart hovers, every safe control | Yes, byte for byte (one `bundle_hash`) | **Tour answers**: audit + questionnaire from the tour only |
| 2. Live exploration | The model browses the live site itself through a logged, rule-bound tool, then revises | No, by design | **Explored answers**: what changed after exploring, and why |

The tour answers are written and locked before exploration starts, so
exploring cannot leak back into them. This gives three comparisons from one
run: models on identical evidence (tour vs tour), models exploring freely
(explored vs explored), and what interaction changes (tour vs explored for the
same model). Participants correspond most closely to the explored answers.

## Layer 1: the standard tour (frozen)

Written by `integrations/capture/site_capture.py` under a new capture profile
`site-full` (the default). The old `site-auto` stays available as `--quick`.

On every in-scope page (same host, under the URL's folder, robots.txt
honored, up to 12 pages):

1. **Desktop, top to bottom.** 1280x800 frames covering the whole page with no
   gaps (the previous capture spread a fixed budget, so long pages were mostly
   unseen). The page is reached by scrolling smoothly in small steps like a
   wheel, not by jumping, so scroll-triggered effects fire as they do for a
   person.
2. **Motion as frames.** After every scroll step (and after the page loads), a
   probe watches for running CSS/Web animations and DOM mutations. The settled
   view is always kept. If the view was still changing, an extra frame taken
   mid-motion is kept too, with its time offset, and the pair is recorded as a
   motion sequence (`motion` in the manifest: trigger, frames, what was
   detected, whether it loops). A frame is kept only if it differs from the
   settled view, so static pages cost nothing extra.
3. **Chart hovers.** Every chart-like graphic (SVG or canvas, at least
   ~150x100 px) is scrolled into view and a fixed sample of its marks is
   hovered (default 4 per chart, spread left to right; marks with mouse
   handlers first; canvas charts at fixed points). Each hover records the
   tooltip or other text that appeared and whether the pixels changed. A
   screenshot is kept only when something visibly changed, and "no response"
   is recorded either way.
4. **Every safe control.** Buttons, tabs, toggles, checkboxes, dropdowns (one
   other option), and now **sliders** (moved to their minimum and maximum) are
   exercised once each on a fresh load, up to 25 per page, with before/after
   text and state recorded and an after-screenshot when the view changed.
   Typing, dragging, form submission, downloads, and account or payment
   actions are never performed and are listed as untested or blocked.
5. **Phone, top to bottom.** 390x844 frames over the whole page (device pixel
   ratio 1 to keep images light), settled views only.
6. **Text and structure for the whole page** (unchanged), including text that
   only appears while scrolling.

**Budget and fairness.** One image ceiling per site (default 300, maximum
400) with a fixed priority: desktop frames for every page first, then motion
frames, hovers, and control screenshots, then phone frames. If a very large
site exceeds the ceiling, lower-priority images are spread and the gap is
recorded per page. Every page's coverage is written as numbers (desktop
frames taken of needed, charts hovered of found, controls exercised of found)
in the manifest, `site.json`, and the report.

**Why frames, not video.** Claude and most agents read still images only.
Giving Gemini video and the others frames would break equal evidence, so
motion reaches every model as the same frames.

## Layer 2: live exploration (logged)

A new command, `scripts/explore.py`, gives the model a browser session on the
live site through a small set of human-like actions. It hides the browser
engine behind the capture adapter (gstack browse in this repository), so the
skill's instructions name no browser.

```text
explore.py start  --bundle B --tour-audit RUN/audit.tour.json --out RUN/exploration
explore.py look   [--note TEXT]                 screenshot of the current view, plus what is on screen
explore.py scroll --by PX | --to Y | --to-element SEL | --top | --bottom
explore.py hover  SEL [--nth N] | --at X Y      (viewport coordinates)
explore.py click  SEL
explore.py select SEL VALUE
explore.py slide  SEL VALUE
explore.py goto   ROUTE_OR_URL                  in-scope pages only
explore.py back
explore.py find   [charts | controls | marks SEL] what can be hovered or clicked in view, with selectors
explore.py read   [SEL]                         visible text, marked as page data
explore.py wait   MS                            up to 5000 ms, reports motion
explore.py status | finish [--note TEXT]
```

Rules enforced by the tool (not left to the model):

- Same scope as the tour: in-scope pages only, robots.txt, no new tabs.
- No typing, no form submission, no downloads, nothing whose text or target
  looks like sign-in, purchase, send, delete, or account changes. Refusals are
  logged.
- No arbitrary JavaScript from the model.
- A fixed budget so models are treated alike: 40 actions and 25 screenshots by
  default (the same flags for every model in a comparison).
- Actions that change the view (scroll, hover, click, select, slide, goto)
  save a screenshot automatically while the budget lasts, because seeing the
  effect is the point.
- Page text returned to the model is labeled as data, not instructions.

Every action gets an id (`L001`, `L002`, …) and is logged with its target,
the bundle region it falls in, what changed, and its screenshot. `finish`
writes `exploration.json`, checks it, and locks it with a hash
(`exploration.lock.json`), exactly like a frozen bundle. Findings and answers
cite exploration evidence by these ids.

## Two-stage answering

1. **Tour stage.** The model audits the frozen bundle and answers the study
   questions (`audit.tour.json`), which must validate.
2. **Commit.** `explore.py start` validates the tour audit and records its
   hash in the session. From then on it cannot change.
3. **Explore** within the budget.
4. **Exploration stage.** The final `audit.json` is the tour audit unchanged
   plus an `exploration_stage` block: new findings, exceptions, quality notes,
   and candidates that each cite at least one exploration action; updates to
   tour findings (confirmed, strengthened, weakened, withdrawn, with reasons);
   the questionnaire answered again; and a `changes_from_tour` list giving a
   reason for every answer that changed.
5. **Validator** checks that the tour part still hashes to the committed value
   (`tour_answers_changed` if not), that the tour stage never cites
   exploration, that every exploration id exists, and that `changes_from_tour`
   lists exactly the answers that differ.

If exploration cannot run (no network in the agent's sandbox, a chat app, a
supplied bundle with no URL, or `--no-explore`), `exploration_stage.status`
is `not_done` with the reason, and the tour answers stand alone.

## Outputs

- **Report:** a coverage table for the tour, then the study answers with tour
  and explored answers side by side, the exploration log (actions and
  screenshots), exploration findings and updates, then everything as before.
- **CSV:** two rows per run in `responses_wide.csv`, with a new
  `evidence_phase` column (`tour`, `explored`), and the same in `marks.csv` and
  `questionnaire_reasons.csv`. All other columns stay in the study export's
  layout.
- **Run folders:** each model's run goes in its own folder,
  `<capture>/runs/<time>-<model>/`, so several models auditing one capture never
  overwrite each other.

## Running a model comparison

1. Capture each site once, with no model: `acquire_url.py URL --out
   local-runs/study/<site>`.
2. In each agent (Claude Code, Codex, Gemini CLI), run
   `/website-slop-audit local-runs/study/<site>/bundle` (`$website-slop-audit`
   in Codex). Every model gets the same tour; each explores the live site with
   the same budget.
3. Collect the CSV rows from each run folder.

Agent notes: exploration needs network access and gstack's state folder
(`~/.gstack`) inside the agent's sandbox, as the capture already does. Codex
needs its sandbox loosened for this (documented, not changed by us); Gemini
CLI asks to approve each shell command.

## What stays the same

The codebook, construct, profiles, evidence rules, questionnaire wording,
validation of the tour audit, report sections, CSV columns, the chat-app
prompt package (tour stage only), and older bundles and audits (still valid;
the new fields are optional).

## Limits that remain

- Animation is sampled as frames, not recorded continuously.
- Hovering samples a few marks per chart; exploration can look at more.
- Dragging (map panning, brushing) and typing are never done.
- The live site can change between models' explorations. The tour cannot.
- Long sites mean many images. Models must review page by page and keep notes,
  and runs take longer and cost more than with the 64-image capture.

## Build steps and checks

1. Fixture site with a load animation, a reveal-on-scroll transition, a
   looping animation, an SVG chart with tooltips and CSS hover, a canvas chart
   with a mousemove tooltip, a slider, a dropdown, a submit form, and an
   off-site link.
2. Tour capture (`site-full`): smooth scroll, motion probe and frames, hovers,
   sliders, phone tour, budget priority, coverage numbers; bundle schema and
   validator (motion section, new kinds, higher ceiling); digest.
3. Exploration tool, its record schema, validator, and lock.
4. Audit schema, validator, report, and CSV for the two stages; run folders.
5. SKILL.md workflow, references, README, agents notes.
6. Unit tests without a browser; live tests on the fixture behind
   `SLOP_LIVE_CAPTURE=1`; the full suite.
7. One real end-to-end `/website-slop-audit` run with Claude on a public
   student site.

## Built (2026-11-15)

Everything above was built as planned. Details that were settled while
building:

- **Ids.** Tour hovers are interactions `H001`, …; exploration actions are
  `L001`, …, their screenshots `L001` (settled) and `L001m` (mid-motion).
  Contextual exceptions already used `X…`, so exploration does not.
- **Run folders.** `scripts/start_run.py --bundle B --rater provider/model`
  makes `<capture>/runs/<time>-<model>/`; every run writes there, so any
  number of models can audit one capture.
- **Motion probe.** Screenshots themselves cause DOM changes (an injected
  style tag; input carets restyled), and off-screen animations keep running;
  both are ignored so that "the view was moving" means what a person would
  see. A view that keeps changing only because of a looping animation is
  recorded as `looping`, at most twice per page.
- **Hovers.** The real pointer is parked in a corner (a temporary 3-pixel
  element) between charts so no hover state carries over. Native tooltips
  (`<title>`, `title=`) are recorded as text, because browsers never draw
  them in screenshots.
- **Before/after text in exploration.** The explorer scrolls a control into
  view before using it, so "what changed" is about the action, not about the
  scroll.
- **Chat-app packages** still need a small capture (`--quick --budget 8`) and
  record the exploration as `not_done`.
- **Checks added.** Bundle: `motion_frame_kind`, `orphan_motion_frame`,
  `motion_route_mismatch`. Exploration record: `action_order`,
  `counts_mismatch`, `budget_exceeded`, `changed_after_freeze`. Audit:
  `tour_answers_changed`, `exploration_in_tour`, `no_exploration_evidence`,
  `missing_exploration_ref`, `exploration_mismatch`, `exploration_missing`,
  `exploration_stage_inconsistent`, `changes_unlisted`, `changes_not_changed`.
- **Tests.** 24 new (`tests/test_tour_and_exploration.py`), including a live
  tour and exploration of `fixtures/sites/motion-site/` behind
  `SLOP_LIVE_CAPTURE=1`. 214 pass; the 3 live tests pass when enabled.
- **Real run** (headless Claude Code, `drying-out-atlas`, 2026-11-15): both
  pages fully toured (46 images); tour audit valid and locked; the model
  explored with 15 of 40 actions, played the site's game through every stop
  (the tour's one-click-per-fresh-load rule reached only the first), and
  changed two answers with reasons. 0 errors, 0 warnings after one validator
  fix: marks made after exploring may quote text that only the exploration
  saw. About 24 minutes and $17.07 at API prices.
