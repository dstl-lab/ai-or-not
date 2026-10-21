# AI or Not: study platform plan

**Goal.** A proof-of-concept platform for the DS teaching & learning lab study on how students
decide whether a website was AI-generated. Participants (students who took DSC 106) browse real
DSC 106 final-project websites and answer closed-ended questions about each one.

## Decisions

| Topic | Decision |
|---|---|
| Research framing | Perception only. No ground-truth "AI or not" labels are stored. |
| Participants | ~10 students, one session each, moderated in person |
| Sites per session | 10, about 4–5 minutes each, **same order for everyone** |
| Site source | DSC 106 Spring 2026 final projects ([showcase](https://dsc-courses.github.io/dsc106-2026-sp/showcase/)) |
| How sites are shown | Frozen local copies served by the app, so they behave like the real site |
| Questions | One shared set for every site; always visible; no timer |
| Answer rules | All questions for a site are required before **Next** unlocks |
| Going back | Allowed; answers stay editable |
| Screens | No consent, background, or closing screens. The researcher only enters a participant ID. |
| Site identity | Hidden. Students see "Website 3 of 10", not the project title or URL. |
| Activity logging | Not yet (survey answers only). Time on each site is kept as session metadata. |
| Storage | SQLite file (main store) + automatic sync of answers to a Google Sheet |
| Runs on | The researcher's laptop (`uv run aiornot serve`) |
| Stack | Python (FastAPI) backend; plain HTML/CSS/JS front end with no build step |

## The 10 study sites (in order)

1. Breathing Smoke (Best Project)
2. Five Minute Fire (Honorable Mention)
3. Strike or Ball? Could You Call the Zone? (Honorable Mention)
4. Climate Change is Global, Response is Not
5. Where Droughts Hide
6. From Rain to Ruins
7. The Greening Earth
8. Finding San Diego's Future Climate Twin
9. The World Is Getting Greener — But Momentum Is Uneven.
10. Human Climate Choices and Their Impact on the Storms of Our Future

Defined in `config/sites.json` (`study_sites`). Swapping a site = edit that list, run `uv run aiornot mirror`.

## Architecture

```
Browser (researcher laptop)                    FastAPI server (localhost:8000)
┌─────────────────────────────┬─────────┐      ┌──────────────────────────────────┐
│ iframe: /sites/<id>/        │ question│ ───▶ │ /sites/<id>/*  frozen site copies │
│ (frozen copy, same origin)  │ panel   │      │ /api/*         sessions, answers  │
└─────────────────────────────┴─────────┘      │ SQLite: data/study.db             │
                                               │ background worker ──▶ gws CLI ──▶ Google Sheet
                                               └──────────────────────────────────┘
```

- **Why copies, not live links.** Every project is a static GitHub Pages site built straight from
  its repo. Copying the repo at a pinned commit reproduces the site exactly. It also freezes it, so
  every participant sees the same version: 4 of 60 showcase links had already moved or died. And
  because the copies are served from the app's own origin, a future version can see in-site
  navigation and trigger follow-up questions.
- **Why SQLite first, then the Sheet.** The database write is synchronous and local, so an answer is
  never lost to a network problem. The Sheet is a convenience mirror, synced in the background with
  retries.

## Data model (SQLite)

- `sessions`: participant ID, start/finish times, site order, config versions, test flag
- `site_visits`: per session × site: first opened, completed, seconds on site, revision
- `responses`: latest answer per session × site × question
- `response_history`: append-only log of every saved answer (audit trail)
- `sheet_rows`: which Google Sheet row holds each session × site, plus sync status

Exports (CSV): long format (one row per answer) and wide format (one row per participant × site).
See `docs/data-dictionary.md`.

## Researcher workflow

1. `uv run aiornot serve`, then open http://localhost:8000
2. Enter participant ID → Start (tick "practice" for trial runs; those are flagged and kept out of exports)
3. Hand the laptop to the student
4. Afterwards: `/admin` shows progress, Sheet sync status, and CSV downloads

## Out of scope for this PoC (planned next)

- Logging in-site activity (pages visited, clicks, scroll depth)
- Questions triggered by what the student does on a site
- Remote / multi-laptop sessions (would move SQLite → hosted Postgres)
- Vendoring CDN scripts (D3, fonts) so sites work fully offline
