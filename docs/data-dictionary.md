# Data dictionary

All times are UTC, ISO 8601 (`2026-10-21T18:04:12Z`). Practice sessions are excluded from every
export unless you tick *Include practice sessions* (or pass `--practice`).

## CSV exports

### `responses_wide.csv`: one row per participant × website (main analysis table)

| Column | Meaning |
|---|---|
| `participant_id` | ID the researcher typed at the start (e.g. `P01`) |
| `session_id` | Unique id of the session (a participant could have more than one) |
| `practice` | `True` for practice runs |
| `site_position` | 1–10, the order the site was shown in |
| `site_id`, `site_title`, `site_award` | Which DSC 106 project this was (never shown to participants) |
| `first_opened_at` | When the participant first reached this site |
| `completed_at` | When they first answered everything and pressed Next (blank = not finished) |
| `seconds_on_site` | Time this site was on screen with the study tab visible, summed over visits |
| *one column per question id* | The latest answer (see question ids below). Booleans are `TRUE`/`FALSE`; multi-selects are `; `-separated |
| `cues__<option>` | 1/0 indicator for each multi-select option (1 = ticked), blank if unanswered |

### `responses_long.csv`: one row per participant × website × question

`participant_id`, `session_id`, `practice`, `site_position`, `site_id`, `site_title`, plus:

| Column | Meaning |
|---|---|
| `question_id`, `question_type` | Which question |
| `value` | Answer, flattened as in the wide table |
| `value_json` | Exact stored value as JSON (`true`, `4`, `"most"`, `["gradients"]`) |
| `first_answered_at`, `updated_at` | First answered / last changed |
| `times_changed` | How many times the answer was changed after first answering |

### `sessions.csv`: one row per session

`session_id`, `participant_id`, `practice`, `started_at`, `finished_at`, `sites_completed`,
`total_seconds`, `questions_version`, `sites_version`, `user_agent` (browser), `screen` (resolution).

`questions_version` / `sites_version` change whenever `config/questions.json` or the study sites
change, so you can tell which sessions saw which version.

### `site_visits.csv`: one row per participant × website (timing only)

`participant_id`, `session_id`, `practice`, `site_position`, `site_id`, `site_title`,
`site_award`, `first_opened_at`, `completed_at`, `seconds_on_site`, `revision` (number of answer
changes saved for this site).

## Starter questions (`config/questions.json`, version `starter-v1`)

| id | Type | Prompt | Stored values |
|---|---|---|---|
| `ai_generated` | boolean | Do you think this website was AI-generated? | true / false |
| `confidence` | scale 1–5 | How confident are you in that answer? | 1 (just guessing) – 5 (completely sure) |
| `ai_extent` | single | How much of this website do you think AI helped build? | `none`, `a_little`, `about_half`, `most`, `nearly_all` |
| `cues` | multi (≥1) | Which features influenced your judgment? | `color_scheme`, `gradients`, `typography`, `emoji_icons`, `buttons`, `layout`, `animations`, `charts`, `writing`, `navigation`, `too_polished`, `quirks`, `gut_feeling` |
| `strongest_cue` | single | Which one of those features mattered most? | one of the `cues` the participant ticked |
| `design_generic` | scale 1–5 | The visual design looks generic or template-like. | 1 strongly disagree – 5 strongly agree |
| `writing_ai` | scale 1–5 | The text on the site reads like it was written by AI. | 1 strongly disagree – 5 strongly agree |
| `polish` | scale 1–5 | How polished does this website feel overall? | 1 very rough – 5 very polished |
| `seen_before` | single | Had you seen this website before today? | `no`, `yes_seen`, `yes_made` |

Consider excluding (or analyzing separately) judgments where `seen_before` is `yes_made`.

## SQLite tables (`data/study.db`)

| Table | Contents |
|---|---|
| `sessions` | One row per session (as in `sessions.csv`; `site_order` is a JSON list) |
| `site_visits` | One row per session × site, created at session start; `revision` bumps on each answer change |
| `responses` | Latest answer per session × site × question (`value` is JSON) |
| `response_history` | Append-only log of every answer save; `value` NULL means the answer was cleared |
| `sheet_rows` | Which Google Sheet row holds each session × site, and its sync status |

## Google Sheet (`responses` tab)

The same columns as `responses_wide.csv` without the 0/1 indicator columns, plus `synced_at`
(first column) and `revision` (last column). Practice sessions are included and marked
`practice = TRUE`; filter them out in the Sheet.

## `element_marks.csv` (element-marking prototype)

One row per marked element, or one row with blank element fields for an explicit
`none = True` response. Clearing all marks without selecting “Nothing specific stood out”
produces an empty selection record with `none = False`.

- Identifiers: `participant_id`, `session_id`, `site_id`, `practice`, `updated_at`.
- Selection: `none`, `mark_number` (1–3), `reason` (`shape`, `color`, `font`, `spacing`,
  `wording`, `other`), `ai_judgment` (the participant's AI judgment when selecting).
- Element: `page` (path, query, hash), `selector` (DOM path), `tag`, `label` (short visible text).
- Evidence: `rect` (JSON document x/y/width/height), `viewport` (JSON width/height),
  `styles` (JSON computed CSS, including font, colors, background, radius, shadow, and gap).

SQLite table `element_marks` stores the latest selection per session and site. Removing a mark
replaces that selection; unlike survey answers, marks do not currently retain a revision history.
