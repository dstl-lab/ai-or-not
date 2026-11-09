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
| `feature_rating__<feature>` | The 0–10 grid, one column per feature; `NA` = participant chose N/A |
| `ai_marks` | Short list of the spots clicked on the site (`1. Heading: … \| 2. Chart or graphic`), or `none` |
| `ai_marks__count` | Number of spots clicked (0 if they ticked "Nothing feels AI-generated") |
| `<question>__<option>` | 1/0 indicator for each multi-select option (1 = ticked), blank if unanswered |

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
`total_seconds`, `questions_version`, `sites_version`, `user_agent` (browser), `screen` (resolution),
then one column per background and closing question (see below).

`questions_version` / `sites_version` change whenever `config/questions.json` or the study sites
change, so you can tell which sessions saw which version.

### `marks.csv`: one row per spot a participant clicked on a website

`participant_id`, `session_id`, `practice`, `site_position`, `site_id`, `site_title`, plus:

| Column | Meaning |
|---|---|
| `question_id`, `mark_number` | Which question (`ai_marks`) and the mark's number as shown to the participant (1, 2, …) |
| `page` | Page within the site (blank = the site's first page) |
| `kind` | Plain-language type: Heading, Text, Chart or graphic, Button, Link, Image, Navigation, Section, Whole page |
| `tag` | HTML/SVG element name (`h2`, `p`, `rect`, `canvas`, …) |
| `text` | First 120 characters of the element's text, if any |
| `selector` | CSS path to the element. The sites are frozen copies, so `document.querySelector(selector)` finds the same element for every participant |
| `x`, `y` | Where they clicked, in pixels from the top-left of the whole page |
| `box_x`, `box_y`, `box_w`, `box_h` | The clicked element's position and size on the page |
| `scroll_y`, `viewport_w`, `viewport_h` | How far down they had scrolled and the size of the website area at the time |
| `created_at` | When the spot was marked (browser clock) |

Exact pixel positions depend on screen size, so compare marks across
participants by `selector` (or by which section contains it) rather than by pixels.

### `site_visits.csv`: one row per participant × website (timing only)

`participant_id`, `session_id`, `practice`, `site_position`, `site_id`, `site_title`,
`site_award`, `first_opened_at`, `completed_at`, `seconds_on_site`, `revision` (number of answer
changes saved for this site).

## Questions (`config/questions.json`, version `phd-v1`)

The feature list is defined once (`option_lists.features`) and shared by `feature_rating`,
`top_ai_feature` and `reliable_signs`, so the same list can be given to the AI
rater: `color_scheme` (Colors), `gradients`, `typography` (Fonts), `emoji_icons`, `buttons`
(Buttons and hover effects), `layout` (Layout and spacing), `animations`, `charts`, `writing`,
`navigation`.

### Background: once, before the first website (in `sessions.csv`)

| id | Type | Prompt | Stored values |
|---|---|---|---|
| `field` | single | What is your field or PhD program? | `cs`, `data_science`, `cogsci`, `design_hci`, `other` |
| `phd_year` | single | What year of your PhD are you in? | `y1`, `y2`, `y3`, `y4`, `y5plus` |
| `build_experience` | single | How much experience do you have building websites or data visualizations? | `none`, `a_little`, `moderate`, `a_lot` |
| `taught_course` | boolean | Have you taught or TA'd a course like DSC 106? | true / false |
| `ai_use_code` | single | How often do you use AI tools … to write code? | `never`, `monthly`, `weekly`, `daily` |
| `ai_use_design` | single | How often do you use AI tools for design or writing? | `never`, `monthly`, `weekly`, `daily` |
| `can_tell_pre` | scale 1–5 | I can reliably tell whether a website was made with AI. | 1 strongly disagree – 5 strongly agree |
| `ai_acceptable` | scale 1–5 | Using AI to build a course project is acceptable. | 1–5 |
| `ai_less_valuable` | scale 1–5 | Work made with AI help is less valuable than work made without it. | 1–5 |

### Per website (in `responses_wide.csv` / `responses_long.csv`)

| id | Type | Prompt | Stored values |
|---|---|---|---|
| `ai_marks` | marks (click on the site) | Click the parts of the website that feel AI-generated. | list of marks (any number; see `marks.csv`), or `"none"` |
| `feature_rating` | grid 0–10 + N/A | Rate how AI-generated each feature looks. | `{feature: 0–10 or "na"}`; 0 human-made – 10 AI-generated |
| `top_ai_feature` | single | Which feature looks most AI-generated? | a feature, or `none` |
| `ai_extent` | single | How much of this site did AI build? | `none`, `a_little`, `about_half`, `most`, `nearly_all` |
| `design_generic` | scale 1–5 | The design looks template-like. | 1 disagree – 5 agree |
| `writing_ai` | scale 1–5 | The text sounds AI-written. | 1 disagree – 5 agree |
| `polish` | scale 1–5 | How polished is this site? | 1 rough – 5 polished |
| `quality` | scale 1–5 | How good is this project overall? | 1 poor – 5 excellent |
| `ai_changes_view` | single | Would AI use change your view of its quality? | `lower`, `no_change`, `higher` |
| `seen_before` | single | Have you seen this site before? | `no`, `yes_seen`, `yes_made` |

Consider excluding (or analyzing separately) judgments where `seen_before` is `yes_made`.

### Closing: once, after the last website (in `sessions.csv`)

| id | Type | Prompt | Stored values |
|---|---|---|---|
| `can_tell_post` | scale 1–5 | I can reliably tell whether a website was made with AI. (repeat of `can_tell_pre`) | 1–5 |
| `reliable_signs` | multi (1–3) | Overall, which features were the most reliable signs of AI? | up to 3 features |
| `difficulty` | scale 1–5 | How hard was it to judge these websites? | 1 very easy – 5 very hard |
| `ai_vs_human` | single | Do you think an AI could judge "AI-ness" better than a person? | `worse`, `same`, `better`, `not_sure` |

## SQLite tables (`data/study.db`)

| Table | Contents |
|---|---|
| `sessions` | One row per session (as in `sessions.csv`; `site_order` is a JSON list) |
| `site_visits` | One row per session × site, created at session start; `revision` bumps on each answer change |
| `responses` | Latest answer per session × site × question (`value` is JSON). Background and closing answers use the site ids `_background` and `_closing` |
| `response_history` | Append-only log of every answer save; `value` NULL means the answer was cleared |
| `sheet_rows` | Which Google Sheet row holds each session × site, and its sync status |

## Google Sheet (`responses` tab)

The same columns as `responses_wide.csv` without the 0/1 indicator columns, plus `synced_at`
(first column) and `revision` (last column). Practice sessions are included and marked
`practice = TRUE`; filter them out in the Sheet.
