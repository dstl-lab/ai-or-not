# AI or Not: website perception study

A local reviewer tool for exploring DSC106 final-project webpages and recording how
AI-generated they appear. The webpage stays interactive on the left; a survey sidebar
on the right saves answers to this computer.

The immediate workflow is an **internal practice trial using the existing ten projects**.
Creator surveys are collected externally and linked later by project ID and pinned commit.

## Try the sidebar locally

With git and [uv](https://docs.astral.sh/uv/) installed:

```bash
uv run aiornot serve
```

Open [localhost:8000](http://localhost:8000/) in the Codex browser/sidebar or your browser.
The first run downloads any missing project copies. Keep an internet connection: some
projects still load fonts, scripts, or other resources externally.

1. Enter a test ID, choose a background group, and tick **Practice run**. For the internship
   group, also record whether the tester completed DSC106.
2. Review each webpage. Rate AI appearance from **1 (Not at all) to 5 (Extremely)**, then
   complete the **Review checks** that open below it. Allow about five minutes per webpage
   including answers; there is no enforced time limit. **Jump to a website** opens navigation.
3. **Page not working?** opens the technical-problem question even before choosing a rating.
   If evaluation is impossible, choose **I could not evaluate the webpage** and leave its
   appearance rating blank. The footer guides you to missing answers before allowing **Next**.
4. After the initial reviews, continue to final questions about **two randomly selected
   webpages**. Select up to three cues, then optionally expand **Page notes** and choose
   **Annotate webpage**. Select a detail and write a short note in the editor above saved
   notes. Click **Save note** to keep it, or **Cancel selection** / **Cancel** to leave the
   annotation mode. Starting this stage locks the initial ratings.
5. Finish, then inspect the session and downloads at [the dashboard](http://localhost:8000/admin).
   Include practice sessions when downloading trial data.

Ratings and choices save automatically. Annotation drafts save only after **Save note**;
save or cancel a draft before moving to another webpage. Closing the tab warns about an
unfinished draft. Wait for the saved indicator before closing the tab. The dashboard's
**Resume** link reopens an interrupted session; earlier webpages remain editable until the
final-question stage begins.

Each final webpage accepts up to three annotations, with notes of up to 500 characters.
When elements overlap, use **Overlapping elements** in the note editor to select the
text, control, graphic, or surrounding area you meant. Changing the layer keeps your note.
Embedded charts are selected as a whole frame, labeled with their title. Their controls
work normally again as soon as selection ends. Open dialogs restrict selection to their
visible contents; thin SVG lines can be selected too.
In annotation mode, drag across a canvas chart to draw a box around a specific area,
then add a note. Boxes follow the canvas when the page scrolls or resizes; they do not
track data points after zooming, rotating, or changing the chart.
Use **Edit note** or **Remove** to revise a saved annotation; click its selected-element
label to show the target again. Chart labels use the chart's accessible name when available.
Highlights follow layout changes and clear if the selected element disappears. Repeat the
interaction that revealed a dynamic element, then click its annotation to show it again.
The same guidance appears when a carousel moves the selected element into a hidden slide.
Saved highlights let clicks and drags pass through, so the website remains interactive.
Annotations save locations, text, and computed visual styles (such as fonts, colors,
and rounded corners), without screenshots or full interaction replays. The metadata
is included in the existing annotation JSON in CSV exports and the optional Google Sheet.
See [mirrored-site validation](docs/mirrored-site-validation.md) for the browser checks and
known warnings in the original frozen websites.

For a quick internal trial, you can temporarily lower `sites_per_session` in
`config/sites.json` and restart the server. Its allowed range is 1–10. The current project
list does not need to change. Excluding projects at setup requires enough eligible projects
to fill the configured session size.

## Researcher setup and assignment

The setup form records three background labels: `lower_division`, `dsc106`, and
`agentic_internship`. The internship group can include either DSC106 background. These are
researcher-entered records, not an eligibility screening or consent system. Research approval,
recruitment, and any required consent remain outside this tool.

Each new session receives up to ten distinct projects from `study_sites`. Assignment favors
projects with fewer existing assignments in that group, then distributes their presentation
positions. Practice sessions do not affect this balancing. The dashboard shows assignments
and completions by group. This is local balancing within **one computer's database**, not a
guarantee of an exactly counterbalanced study.

Use participant IDs rather than names. The researcher can exclude a participant's own or
familiar projects before assignment; the survey also records familiarity discovered later.
The wrapper uses labels such as “Website 3 of 10”; original project content can still reveal
its authors or identity.

## Configuration

| Change | Where | Apply it |
|---|---|---|
| Questions, wording, choices | `config/questions.json` | Restart the server |
| Active project list | `study_sites` in `config/sites.json` | Mirror missing projects, restart |
| Number reviewed per session | `sites_per_session` in `config/sites.json` (default 10; maximum 10) | Restart |
| Project versions | Pinned `commit` values in `config/sites.json` | Prepare copies before collecting data |

Questions support `scale`, `single`, `multi`, `boolean`, `text`, and `annotation`. A question's `phase`
is `review` by default or `followup` for the two final webpages. `required` defaults to true;
`required_unless` can waive a missing answer when another choice has a specified value.
Multi-select questions support `min_selected` and `max_selected`; text questions support
`max_length`; annotation questions support `max_annotations` (three in this pilot).
The included `reviewer-pilot-v1` questionnaire has three initial-review questions and two
final-question fields: optional annotations and the cue checklist. Existing sessions keep
their saved questionnaire, including the earlier `cue_example` field where applicable.

Sessions save their own question and project definitions, version IDs, assigned order,
and final-question selection. Exports use those saved definitions after configuration
changes. Keep question IDs, stored option values, and project IDs stable across the study;
wording changes create a new question version.

Keep project commits and mirrored files fixed during a collection round. A session snapshot
preserves definitions, **not another copy of the website files**. A changed or missing mirror
blocks resuming an existing session until its original copy is restored. Use
`uv run aiornot mirror --update` only when deliberately preparing a new set of project versions.

## Data and external creator surveys

SQLite at `data/study.db` is the source of truth. **Dashboard → Download data**, or:

```bash
uv run aiornot export
```

exports five tables: `responses_wide`, `responses_long`, `sessions`, `site_visits`, and
`projects`. Add `--practice` to include internal trials. See the
[data dictionary](docs/data-dictionary.md) for fields and missing-answer meanings.

Give the external creator survey the same `site_id` and `site_commit` listed in
`projects.csv`. Use both fields to join creator forecasts to reviewer judgments; project
position is participant-specific and is not a project identifier.
Saved annotations export as JSON in the wide and long tables and the optional Google Sheet.

For a descriptive summary:

```bash
uv run --group analysis python -m analysis.summary
```

Add `--practice` to summarize internal trials. `analysis/load.py` loads all five tables as
pandas DataFrames. Stop the server and back up `data/` after collection; it includes the
answer history that CSVs do not export. Keep a backup of `mirror/` as well, since deleted
upstream repositories may no longer be downloadable.

## Google Sheet (optional)

The Sheet is a convenience mirror, with one row per session and webpage. Completed-page
answers sync in the background; later edits update that row. Local saving continues during
sync failures, which appear on the dashboard and are retried.

1. Install the Google Workspace CLI: `brew install googleworkspace-cli` (the package named
   `gws` is unrelated).
2. Sign in with `gws auth login`; if required, use the CLI's `gws auth setup` instructions.
3. Run `uv run aiornot sheet create`, or connect an accessible spreadsheet with
   `uv run aiornot sheet connect "<sheet link>"`, then restart the server.

Link settings live in `data/sheets.json`. If the export columns change, link a new Sheet
before writing the new schema; the sync guard refuses to overwrite an incompatible header.
An actual external Google Sheet sync has not been verified as part of this internal trial.

Each laptop has an independent database and assignment history. Sharing a Sheet combines
visible answer rows but does not coordinate assignments or prevent duplicate participant IDs
across laptops. Collect databases/exports separately and use IDs unique across computers.

## Commands and layout

| Command | Purpose |
|---|---|
| `uv run aiornot serve` | Start locally; supports `--no-browser` and `--port 8001` |
| `uv run aiornot check` | Validate config and check mirrored project commits |
| `uv run aiornot mirror` | Download pinned active projects; `--all` includes the pool |
| `uv run aiornot export` | Write CSVs to `data/exports/<date>/` |
| `uv run aiornot sheet create\|connect\|sync\|status` | Manage the optional Sheet |
| `uv run --group analysis pytest` | Run tests, including summary checks; Node.js is needed for browser logic tests |

`aiornot/` contains the API, storage, exports, and mirroring; `web/` is plain HTML/CSS/JS;
`config/` holds projects and questions; `analysis/` contains pandas helpers.
[docs/PLAN.md](docs/PLAN.md) records the current scope and remaining limitations.
