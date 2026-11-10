# Reviewer study implementation plan

**Goal:** Prepare an internal trial of the reviewer sidebar on the existing projects, including ratings, final reflections, and element annotations.

**Architecture:** Extend the existing FastAPI, SQLite, and plain JavaScript app. Keep saved assignments and survey/site snapshots with each session. Preserve old records through additive migrations.

**Scope:** Creator surveys remain external. Project identity is `site_id` plus the frozen `site_commit`; recruitment and consent remain researcher procedures.

- [x] Add tested group-aware allocation, exclusions, and coverage in `config.py` and `db.py`.
- [x] Add tested primary/follow-up survey phases and saved configuration snapshots in `questions.py` and `app.py`. Primary answers lock before cue questions appear.
- [x] Adapt researcher setup, participant navigation, and dashboard to groups and variable assignments.
- [x] Extend all exports, project manifest, and analysis summary; protect existing Google Sheet data against incompatible headers.
- [x] Refine the sidebar layout and add optional saved element-and-note annotations during final reflections.
- [x] Update the operational instructions and data dictionary, run the full test suite, and exercise real browser sessions, including annotation selection, saving, reloading, and target recovery.

Review focus: old databases remain readable; groups cannot silently mix; exclusions cannot exceed the available pool; restarting after a config edit does not change an existing survey; follow-up questions cannot overwrite primary ratings; existing Sheet columns cannot be silently relabeled.
