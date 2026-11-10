# AI or Not: current tool plan

The next step is an internal trial of the survey sidebar using the existing ten DSC106
projects. This repository runs reviewer sessions; creator submission surveys remain external.
The internal trial should establish whether the flow, saving, timing, and exports work
comfortably before finalizing a research protocol.

## Current decisions

| Topic | Implemented behavior |
|---|---|
| Construct | Perceived AI-generated appearance, rated 1–5; no authorship ground truth |
| Initial sidebar | Appearance, previous familiarity, and technical-problem questions |
| Technical failure | `unable` permits a blank appearance rating and blank final cue selection |
| Final questions | Cue checklist and optional element annotations for two randomly selected projects, after all initial reviews |
| Annotations | Select a webpage element, write a note, then Save; up to three notes per page and 500 characters per note |
| Editing | Initial reviews can be revisited; starting final questions locks initial ratings; finish locks the session |
| Background | Researcher records one of three groups; internship participants can have either DSC106 background |
| Assignment | Up to ten distinct projects, using local per-group assignment and position counts |
| Practice | Flagged, omitted from ordinary exports and balancing; available when explicitly included |
| Timing | Visible-tab time, stored separately for initial reviews and final questions; no forced five-minute cutoff |
| Stimuli | Existing ten projects, served from pinned local mirrors |
| Saving | Ratings/choices autosave; annotation drafts require Save note; SQLite answer history and optional background Sheet mirror |
| Historical definitions | Per-session question and project snapshots, version IDs, order, and final-question subset |
| Creator linkage | External survey joins reviewer exports using stable `site_id` + `site_commit` |

Group labels record the researcher's classification; the tool does not screen internship
experience, manage recruitment or consent, or determine research approval. Researcher-supplied
exclusions block own/familiar projects when enough eligible projects remain to fill a session.

## Internal trial checklist

1. Run locally and start a practice session from the Codex browser/sidebar.
2. Check that the webpage remains usable beside the questions; exercise scrolling, links,
   keyboard navigation, reload, and dashboard resume.
3. Try both a normal review and an `unable` technical-problem report. Check the saved state
   and distinguish a missing rating from a low rating in exported data.
4. Complete the initial reviews and confirm cue questions appear only at the end for the
   selected subset. Confirm initial ratings are then locked. Select an element, check the
   hover outline and selected target, save a note, then exercise Edit note, Remove, and
   showing the saved target. Check that an unsaved draft requires Save or Cancel before
   navigating and warns before closing the tab.
5. Download exports including practice data. Check project IDs/commits, presentation order,
   cohort/background, separate stage timing, and saved answers against the session.

Allow roughly five minutes per webpage including answers, then time the full flow. The
hour-long session target and final questionnaire wording still need a practical trial.
No additional project collection is required for this internal test.

The pilot has five configured fields: three during initial review, then annotations and
cues on the final two webpages. New sessions use annotations instead of the former
`cue_example` field; historical sessions retain their saved questions and exports.

## Architecture and limits

FastAPI serves the plain HTML/CSS/JS interface, the API, and mirrored project files from one
local origin. SQLite is the primary store. CSV and pandas outputs are generated from that
database; Google Sheets is an optional convenience copy rather than an assignment service.

Each computer balances against its own database. Sharing a Sheet does not create global
counterbalancing or cross-computer duplicate checks. Keep unique participant IDs across
computers and retain each database if using several machines.

Question JSON changes require a restart. New sessions save their definitions; older sessions
continue using their saved questionnaire. Legacy sessions without snapshots require their
original questionnaire configuration to resume after a version change. Export fallbacks for
those sessions cannot reliably recover old project commits or removed question definitions.

Do not replace mirrors during an active collection round: saved metadata does not preserve
an additional copy of the website. A changed or missing mirror blocks resuming a session
until the original copy is restored. Some projects depend on external fonts/scripts, so the
local mirrors do not guarantee fully offline or permanently identical external resources.
The wrapper obscures project titles, while project content itself can reveal identity.

Annotations retain an ID, project page path, selector, short element quote, geometry,
viewport size, and note as JSON. The API restricts saved paths to the assigned project.
This is location-based evidence, not a screenshot or replay of interactive state; some
elements need the reviewer to recreate an interaction before showing the target again.

The current server is intended for local, moderated testing. Recruitment/consent flows,
remote deployment, full offline packaging, in-page click/scroll tracking, and causal analysis
are outside this change. A live external Google Sheet synchronization still needs testing;
column changes require linking a new compatible Sheet before writes can resume.

See [README.md](../README.md) for setup and [data-dictionary.md](data-dictionary.md) for outputs.
