# Data dictionary

Times are UTC ISO 8601 (`2026-10-22T18:04:12Z`). Practice sessions are excluded from the
four session-data exports unless **Include practice sessions** or `--practice` is selected.
The project manifest always includes the currently configured projects; historical versions
from practice sessions are included only when practice data is requested.

## Shared study identifiers

| Field | Meaning |
|---|---|
| `participant_id`, `session_id` | Researcher-entered participant ID and unique session ID |
| `practice` | Whether this is a practice session |
| `cohort` | `lower_division`, `dsc106`, or `agentic_internship`; older sessions are `unclassified` |
| `dsc106_completed` | Recorded course background; blank if unknown in older data |
| `questions_version`, `sites_version` | Question definition and active project configuration versions at session creation |
| `site_id` | Stable project ID; join an external creator survey using this **and `site_commit`** |
| `site_commit` | Pinned project commit from the session snapshot, falling back to current config for legacy sessions |
| `site_position` | Actual initial presentation position within this session; not a project identifier |
| `followup_position` | Position in the final-question subset, or blank if this project was not selected |

The four session-data tables carry participant/session IDs, practice, cohort, course
background, and configuration versions. The response and visit tables additionally carry
project ID, commit, initial position, and final-question position.

## `responses_wide.csv`

One row per session × project that the reviewer reached. In addition to shared fields:

| Column | Meaning |
|---|---|
| `site_title`, `site_award` | Project metadata; absent from the reviewer wrapper |
| `first_opened_at`, `completed_at` | First initial opening and first initial completion; blank completion means unfinished |
| `seconds_on_site` | Accumulated visible-tab time during initial review, including return visits |
| `followup_opened_at`, `followup_completed_at` | First opening/completion during final questions |
| `followup_seconds_on_site` | Visible-tab time during final questions, separate from initial review |
| One column per question ID | Latest answer; booleans are `TRUE`/`FALSE`, multi-selects are `; `-separated, annotations are JSON |
| `<question_id>__<option>` | Multi-select indicator: 1 selected, 0 unselected, blank if that question is unanswered |

Timing is approximate browser-reported time, not gaze or interaction measurement. Hidden
tabs do not accrue time; a crash or failed timing report can lose time. The five-minute
review target is guidance rather than an enforced cutoff.

## Current questionnaire: `reviewer-pilot-v1`

Three questions appear on every initial review. Two fields appear on each of the two
selected final webpages: optional annotations and the cue checklist.

| ID | Stage/type | Values |
|---|---|---|
| `ai_appearance` | Initial review; scale | 1 Not at all, 2 Slightly, 3 Moderately, 4 Very, 5 Extremely AI-generated in appearance |
| `seen_before` | Initial review; single choice | `no`, `yes_seen`, `yes_made`, `unsure` |
| `technical_issue` | Initial review; single choice | `no`, `some` (could evaluate), `unable` (could not evaluate) |
| `annotations` | Final questions; optional webpage annotations | Up to three elements or canvas areas with notes; each note is at most 500 characters |
| `cues` | Final questions; multi-select | 1–3 of `writing`, `charts`, `layout`, `images`, `interactions`, `errors`, `gut_feeling`, `other` |

`ai_appearance` and `cues` may be left blank when `technical_issue` is `unable`.
A completed review with no appearance rating is therefore possible. Final-question fields
are also blank for projects outside the two-project subset or before that stage is answered.
Use `technical_issue`, `followup_position`, and completion fields to interpret those blanks;
do not turn them into zero ratings or unselected cues. Initial ratings become read-only
when the final-question stage starts.

A reviewer can select `unable` after entering a rating; the raw answer is retained. Exclude
`technical_issue = unable` from appearance averages even when a numeric rating exists.
The descriptive summary applies this exclusion while retaining completed-review counts.

Older questions and options remain exportable from saved session definitions, so mixed
collections can contain additional columns such as the former boolean `ai_generated`.
Earlier sessions can also retain the former `cue_example` text question. Do not equate the
old boolean outcome with the new five-point scale.

### Annotation values

The `annotations` answer is a JSON array. Every saved entry contains:

| Field | Meaning |
|---|---|
| `id` | Annotation ID, retained when its note is edited |
| `page_path` | Local project path, including any query and fragment; the API checks it belongs to this assigned project |
| `selector` | CSS selector for locating the selected DOM element again |
| `quote` | Short text excerpt or descriptive chart label, up to 300 characters |
| `rect` | `{x, y, width, height}` of the selected element or canvas area in document coordinates/CSS pixels at capture time |
| `viewport` | `{width, height}` of the embedded webpage viewport at capture time |
| `note` | Reviewer explanation, nonempty and at most 500 characters |

Bounds for thin SVG lines include their visible stroke. An embedded chart is recorded as
its outer `iframe` element, with the frame title as `quote`; its internal chart state is
not captured. Saved highlights are passive and do not intercept website interactions.

New annotations also contain `styles`, a snapshot of computed CSS for the selected
element: `background-color`, `background-image`, `color`, `font-family`, `font-size`,
`font-weight`, `border-radius`, `box-shadow`, `display`, and `gap`. Each value is truncated
to 300 characters. The API accepts at most 12 string entries with property names up to
80 characters. Older annotations without `styles` remain valid. For a canvas area,
these styles describe the canvas element, not the individual pixels inside the area.

Canvas area annotations also contain `region`: `{x, y, width, height}` normalized to
the canvas element's size. Its origin is the canvas's top-left corner; dimensions are
positive, and the area stays inside the canvas (up to `0.000001` rounding at the right
and bottom edges). The `selector` locates the canvas. This lets the box follow the
canvas when the page scrolls or its displayed size changes; it does not attach the box
to a data point or restore chart zoom, rotation, or other interaction state. Older
element annotations omit `region` and retain their original meaning.

An annotation draft is not a stored response until **Save note** is pressed. Saved entries
can be edited, removed, or shown again from the sidebar; the usual response history records
changes. JSON is retained in wide/long exports and the Sheet; it is not expanded into
indicator columns. No screenshot or complete interaction sequence is stored. A dynamic
element can require recreating an interaction before its selector resolves again. Chart
labels use the chart's accessible name when available; older bare graphic tags receive a
clearer display label without changing their stored values.

## `responses_long.csv`

One row per session × project × stored question, with the shared fields, `site_title`, and:

| Column | Meaning |
|---|---|
| `question_id`, `question_type` | Question ID and type from the session's saved questionnaire |
| `value` | Flat display value, as in the wide table |
| `value_json` | Stored value as JSON, preserving booleans, numbers, strings, and lists |
| `first_answered_at`, `updated_at` | First answered and last changed timestamps |
| `times_changed` | Number of changes after the first answer |

Only questions with a stored response have rows. Clearing an answer removes its current
response row; the clear event remains in SQLite's history.

## `sessions.csv`

One row per session. Shared session fields plus:

| Column | Meaning |
|---|---|
| `started_at`, `finished_at` | Session start and successful finish; unfinished sessions have blank finish |
| `sites_assigned`, `sites_completed` | Assigned project count and initial reviews completed |
| `total_seconds` | Sum of initial-review time; excludes final-question time |
| `followup_order` | JSON list of project IDs selected for final questions, in presentation order |
| `followup_started_at` | When the final-question stage began and initial ratings locked |
| `user_agent`, `screen` | Browser information and reported screen resolution |

## `site_visits.csv`

One row per session × reached project. Contains shared fields, `site_title`, `site_award`,
all six initial/final timing fields described above, and `revision` (the answer-change
revision used to identify pending Sheet updates). Unreached assigned projects do not appear;
their assignments remain in SQLite.

## `projects.csv`

Project-version manifest for the external creator survey. Columns are `site_id`, `site_title`,
`site_commit`, `repo`, `url`, and `sites_version`. It contains the current active projects
plus saved historical definitions, deduplicated by `site_id` and `site_commit`.
`sites_version` supplies one configuration context for a row; a project version can occur
in several configurations. Join creator and reviewer records using `site_id` + `site_commit`.

## SQLite and historical definitions

| Table | Contents |
|---|---|
| `sessions` | Session fields, assigned `site_order`, `followup_order`, and JSON snapshots of question/project definitions |
| `site_visits` | Every assigned project, its actual position, initial/final timing, and revision |
| `responses` | Latest JSON answer per session × project × question |
| `response_history` | Append-only answer-change history; NULL marks a cleared answer |
| `sheet_rows` | Last synced revision, row reference, and sync errors per session × project |

Old databases are migrated without deleting responses. Existing sessions without snapshots
fall back to current definitions during export: their original prompts, removed option types,
or historical project commits cannot be reconstructed reliably. Cohort becomes `unclassified`
and course background remains unknown. Resuming a legacy session requires its original
question configuration when the version has changed.

Snapshots preserve definitions rather than website files. Keep pinned mirrors unchanged
during a collection round and retain a backup of the database and mirrors. A changed or
missing mirror blocks resuming a saved session until its original copy is restored.

## Google Sheet

The `responses` tab uses current wide-table columns without multi-select indicators, plus
`synced_at` first and `revision` last. Practice sessions are included as `practice = TRUE`.
Rows update after completion and later edits; SQLite remains authoritative. A changed column
schema requires a new compatible Sheet because sync refuses to replace an incompatible
header. Live external Sheet synchronization still needs an operational check.
