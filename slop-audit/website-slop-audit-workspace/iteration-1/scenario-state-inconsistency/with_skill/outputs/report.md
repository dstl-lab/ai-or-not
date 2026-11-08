# Slop-feature audit audit-fx-scenario-inconsistency-with-skill-iter1

bundle `fx-scenario-inconsistency` · profile `multimodal-datastory` · rubric 0.1.0 · status **completed**

## Scope and limits

The page is a short, single-screen data story on the share of coastal parcels in three San Diego neighborhoods inside the projected flood zone for each scenario year. The recorded click on the 2050 button updated the chart title, the bar values, and the active button, but the 'What this means' summary kept its 2020 sentence and values, so after the change the interpretation describes a year the chart no longer shows. This is filed as an incomplete-state-integration finding with a narrative-chart secondary tag. Other cues were checked and not counted: the chart, summary, and method share one card style, and the summary restates the chart values; both are contextual exceptions. Bars are not drawn at the mobile viewport, recorded as a quality observation. Copy is specific and sourced, and no decorative chrome, stock skeleton, or configured animation appeared in the captured scope. Only the 2050 control was tested, the after state exists only at desktop width, mobile has screenshots only, and no source was supplied, so the cause of the stale summary is not established. None of this indicates who or what made the site.

- Assessed modalities: screenshot, text, dom, computed_style, interaction
- Not assessed: source (No source excerpts were supplied in the bundle.)
- Limitation: Only the 2050 scenario button was exercised (E01); the 2100 button and a return to 2020 are untested, so whether the summary ever updates is unknown.
- Limitation: The after-interaction state was captured only at the desktop viewport; the mobile after state is unknown.
- Limitation: Mobile state S02 has screenshots only (no text spans or DOM), so mobile observations cannot be quoted or tied to selectors.
- Limitation: No source excerpts were supplied; SRC-01 is unassessed and implementation causes are not established.
- Limitation: Animation playback was not recorded; motion was judged from computed styles only.
- Counts: 1 finding, 2 contextual exceptions, 1 quality observation, 0 exploratory candidates, 1 unassessed feature

These findings identify features that may contribute to a perceived AI-slop impression; they do not establish who or what made the site.

## Findings

### F001 · INT-02 Incomplete state integration

- **What:** After the recorded click on the 2050 scenario button (E01, completed), the chart panel switched to 2050: the title reads 'Parcels in the flood zone, 2050', the values became 31%, 27%, and 11%, and the 2050 button became the active one. The linked 'What this means' summary directly below did not change and still describes 2020 with the old values (12%, 9%, 4%), so in the after state the interpretive text describes a year the chart no longer shows.
- **Where (cross-region):** R02 (scenario chart panel) · state S03 · image A04 with box · selector #scenario-panel > div:nth-of-type(1) > button:nth-of-type(2); R02 (scenario chart panel) · state S03 · image A04 with box · selector #chart-title; R02 (scenario chart panel) · state S03 · image A04 with box; R03 (summary panel) · state S03 · image A04 with box · selector #summary
- **Evidence:**
  - `interaction:E01` Click on the 2050 scenario button, execution completed, observed 800 ms after the action. Recorded changes cover the chart title, the three bar values, and the button state; no change to #summary is recorded.
  - `text:T021` Chart title in the after state names 2050. "Parcels in the flood zone, 2050"
  - `text:T023` Mission Beach value in the after state. "31%"
  - `text:T025` Imperial Beach value in the after state. "27%"
  - `text:T027` La Jolla Shores value in the after state. "11%"
  - `text:T029` Heading that frames the summary as the interpretation of the chart, unchanged after E01. "What this means"
  - `text:T030` Summary text in the after state still names 2020 and the 2020 values. "In 2020, 4% of La Jolla Shores parcels and 12% of Mission Beach parcels sit in the flood zone. Imperial Beach is in between at 9%."
  - `text:T015` Summary text in the initial state, identical to T030, showing it did not update. "In 2020, 4% of La Jolla Shores parcels and 12% of Mission Beach parcels sit in the flood zone."
  - `dom:D025` In S03 the 2050 button has the filled active style (white text on teal background), confirming the selected scenario.
  - `screenshot:A04` Desktop after-state screenshot: 2050 chart with longer bars above an unchanged 2020 summary.
  - `context:purpose` Stated purpose is comparing flood-zone parcels across scenario years, which the summary is meant to interpret.
- **Interpretation:** slop association moderate (A concrete integration problem: the control updates the chart but leaves its interpretive summary on the initial year, the pattern INT-02 describes. It is a single occurrence on one tested control, so it is not rated strong.); fit questionable (The page exists to compare scenario years, but after choosing 2050 the 'What this means' panel interprets 2020. The sentence is literally accurate for 2020, yet it is not labeled as a baseline, so its role in the after state is unclear.); consequence moderate (A reader viewing the 2050 chart gets an interpretation with different numbers (12% vs 31% for Mission Beach) and must notice the year to avoid misreading. The chart itself works, so the main task is not blocked.)
- **Alternative explanations:** The summary may be meant as a fixed 2020 baseline; it names its year but is not labeled as a baseline.; Ordinary state-management bug: the scenario handler updates the title and bars but not #summary (no source supplied to confirm).; Unfinished prototype in which per-scenario summary text was not yet written.; A summary update slower than the 800 ms observation window; unlikely since the chart updated within it, but not excluded.
- **Observation confidence:** high (Completed recorded interaction, exact DOM text spans in both states, and a legible after-state screenshot all show the same mismatch.) · evidence status `research_hypothesis`

## Contextual exceptions

- X001 LAY-01: The chart panel, the 'What this means' summary, and the method note have identical card styling: white background, 10px border radius, and the same soft shadow (computed styles of D002, D003, D004), although the three differ in role. (insufficient_evidence_for_finding: LAY-01 requires that the sameness hide a hierarchy the content needs. Here explicit headings, the chart panel's larger size and controls, and the top-to-bottom reading order carry the hierarchy, on a short single-screen page where sectioned panels are a common data-story layout.)
- X002 TXT-02: In the initial state, the 'What this means' summary restates the chart's three values in a sentence, adding only the ordering (Imperial Beach in between), rather than an interpretation beyond the numbers. (appropriate_in_context: A single, specific restatement with units, year, and place names, matching the chart; the codebook excludes intentional repetition for summary or accessibility, and nothing repeats across sections or follows a rigid template.)

## Quality observations

- Q001 [rendering]: At the mobile viewport (V2) the chart rows show the neighborhood names and percentages but no bar marks between them, whereas the desktop view (A01) draws a bar for each row. The values remain readable as numbers, but the bar-length comparison is not visible on mobile.

## Exploratory candidates (not scored)

None recorded.

## Unassessed checks

- SRC-01: No source excerpts were supplied, so no source/render comparison is possible.

## Run notes (auditor choices)

Everything above was generated from `audit.json` by `scripts/render_report.py`. This section only records the choices made during the run and adds no new judgments.

- **Profile.** `multimodal-datastory`, as requested. Its modules are core plus data-story, so MED-01 (media module) is not part of this audit.
- **Bundle.** `scripts/validate_bundle.py` reported it VALID with 0 errors. It was already frozen, so it was not re-frozen. `bundle_hash` was copied from `bundle.lock.json`, and the audit validator confirmed that it matches. Only the bundle and the skill folder were used: no live site, no web browsing, no other repository folders.
- **Status `completed`.** Every check the profile and the evidence allow was run. The untested 2100 button and the missing mobile after-state are gaps in the capture, not checks that were attempted and left unfinished, so they are listed as limitations.
- **One phenomenon, one code.** The stale summary is filed once, under INT-02, because the conflict appears only after a recorded interaction. DAT-01 is a secondary tag on that finding, not a second finding, and SUB-02 is not used because the initial state shows no conflict.
- **Ratings.**
  - Contextual fit is `questionable`, not `inappropriate`: the summary sentence is still literally true for 2020, and a fixed baseline is a plausible but unlabeled intent.
  - Consequence is `moderate`, not `major`: the chart itself updated correctly, so the main comparison task is not blocked.
  - Slop association is `moderate`, not `strong`: there is a single occurrence on one tested control.
- **The working 2050 button.** It produced its advertised change, so there is no INT-01 finding. The 2100 control is unknown, not broken.
- **Mobile bars.** The missing bars at 390 px are a quality observation (rendering), not a slop finding. That judgment rests on the screenshots alone, because the mobile state has no DOM or text spans. A closer crop confirmed that no bar marks appear.
- **Report format.** Only `report.md` was requested, so no HTML report was rendered.
