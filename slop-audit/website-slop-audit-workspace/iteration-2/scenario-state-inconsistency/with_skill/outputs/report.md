# Slop-feature audit fx-04-multimodal-datastory-01

bundle `fx-04` · profile `multimodal-datastory` · rubric 0.1.1 · status **completed**

## Scope and limits

A compact, subject-specific scenario explorer. Styling is plain. Source, scenario, flood-zone definition, and counting method are stated on the page. The recorded 2050 click updates the chart's button state, title, values, and bar lengths. The accepted finding is an integration problem (INT-02, with DAT-01 as a secondary tag): after that click the 'What this means' panel still describes the 2020 values, so the interpretation and the chart describe different years and the selected scenario gets no interpretation. Uniform card treatment, the use of 'scenario' for year horizons of a single named scenario, and the summary's prose restatement of chart values were considered and recorded as contextual exceptions. Bars do not render at the mobile viewport; this is recorded as a rendering quality observation, not a slop claim. Only the 2050 click on desktop was tested, and no source was supplied, so the cause and extent of the stale summary are unknown. Nothing here speaks to how the page was produced.

- Assessed modalities: screenshot, text, dom, computed_style, interaction
- Not assessed: source (no source excerpts were supplied in the bundle)
- Limitation: Only one interaction (2050 on desktop) was recorded; 2100, returning to 2020, and mobile interaction are untested
- Limitation: No source excerpts, so SRC-01 is unassessed and the cause of the stale summary cannot be determined
- Limitation: DOM and computed styles were not captured for the mobile state or the bar elements
- Limitation: Synthetic fixture with provided context; a single short page fits in one desktop viewport
- Counts: 1 finding, 3 contextual exceptions, 1 quality observation, 0 exploratory candidates, 1 unassessed feature

These findings identify features that may contribute to a perceived AI-slop impression; they do not establish who or what made the site.

## Findings

### F001 · INT-02 Incomplete state integration

- **What:** After the recorded click on the 2050 button (E01), the chart panel updates: the 2050 button is selected, the title reads 'Parcels in the flood zone, 2050', the values become 31% / 27% / 11%, and the bars lengthen. The linked 'What this means' panel directly below keeps its 2020 text word for word (12%, 9%, 4%). In the after state the interpretation and the chart describe different years, and the selected scenario gets no interpretation.
- **Where (cross-region):** R02 (scenario chart panel) · state S03 · image A04 with box · selector #chart-title; R03 (summary panel) · state S03 · image A04 with box · selector #summary
- **Evidence:**
  - `interaction:E01` Click on the 2050 scenario button, execution_status completed, observed 800 ms after the action. Recorded changes cover the three value labels, #chart-title, and the button states; no change to #summary is recorded.
  - `text:T021` Chart title in the after state S03. "Parcels in the flood zone, 2050"
  - `text:T023` Mission Beach value in S03 (was 12% in S01). "31%"
  - `text:T027` La Jolla Shores value in S03 (was 4% in S01). "11%"
  - `text:T030` Summary text in S03, identical to the S01 summary T015 and still citing the 2020 values. "In 2020, 4% of La Jolla Shores parcels and 12% of Mission Beach parcels sit in the flood zone. Imperial Beach is in between at 9%."
  - `text:T029` Heading of the summary panel in S03, which presents the text as the interpretation of the chart. "What this means"
  - `screenshot:A04` Desktop after E01: 2050 selected, longer bars labeled 31% / 27% / 11%, and the unchanged 2020 summary directly below.
  - `screenshot:A01` Desktop before E01: in the initial 2020 state the summary matches the chart (12% / 9% / 4%).
  - `context:purpose` The provided purpose is comparing parcels in the flood zone across scenario years, so the interpretation panel is expected to follow the selected year or to mark itself as a fixed baseline.
- **Interpretation:** slop association moderate (An integration problem with concrete evidence: the visible control and chart respond, while the explanatory text beside them is not tied to state. That fits the 'surface works, linked substance does not follow' pattern. A single tested state and ordinary bug explanations keep it from being stronger.); fit questionable (The summary states its year ('In 2020'), so a fixed-baseline reading is possible. But nothing labels it as a baseline, and its 'What this means' heading under a 2050 chart presents it as the interpretation of what is shown. Its role for scenario comparison is unclear.); consequence moderate (A reader who selects 2050 sees 31% / 11% in the chart and 12% / 4% in the interpretation directly below. The selected scenario, the page's main comparison, gets no interpretation. The chart itself works, so the task is not blocked.)
- **Alternative explanations:** Ordinary state-management bug: the click handler updates the chart and title but not #summary; Summary deliberately fixed to the 2020 baseline but not labeled as a baseline; Unfinished prototype: per-scenario interpretation text not yet written
- **Observation confidence:** high (Completed recorded interaction, exact DOM text spans in both states, and legible before/after screenshots at the same viewport and scroll offset.) · evidence status `research_hypothesis`

## Contextual exceptions

- X001 LAY-01: The chart panel, the 'What this means' interpretation, and the method note get the same card treatment: white background, 10px radius, and the same soft shadow (computed styles D002-D004), stacked on a pale page background. The three panels play different roles (evidence, interpretation, method). (insufficient_evidence_for_finding: The inclusion rule needs the sameness to hide a hierarchy the content needs. Here hierarchy stays visible: the chart panel is the largest and comes first with its own controls and title, each panel has a distinct heading, and the order (evidence, interpretation, method) is conventional. Only three single-column panels; no flattening shown.)
- X002 SUB-02: The headline asks about 'each sea-level scenario' and the method speaks of 'each scenario's flood polygon', while the controls are years (2020, 2050, 2100) and the source note names a single 'intermediate-high scenario'. The page uses 'scenario' for the time horizons of one named scenario. (insufficient_evidence_for_finding: This is wording that needs a moment to reconcile, not a conflict of values, units, or entities. Reading the years as time horizons of the one named intermediate-high scenario makes all regions consistent, and '2050 scenario' is common usage in sea-level-rise planning communication. Too weak for a SUB-02 finding.)
- X003 TXT-02: The 'What this means' panel restates the chart's three values in prose, ordered lowest, highest, in between, without adding interpretation beyond the chart (for example parcel counts or implications for residents). (appropriate_in_context: A one-off prose restatement of a small chart helps skimming and non-visual readers, and the exclusion rule covers repetition that the page's purpose supports. It also adds a ranking. It is not a template repeated across sections.)

## Quality observations

- Q001 [rendering]: At the mobile viewport (V2, state S02) the chart shows neighborhood names and percentages but no bars. The space between label and value is blank white in A02 and A03, and the only teal pixels in either image are the year buttons. At desktop (A01) the bars render. Whether the bars are hidden on purpose or collapse to zero width cannot be told, because DOM and computed styles were not captured for S02 or for the bar elements.

## Exploratory candidates (not scored)

None recorded.

## Unassessed checks

- SRC-01: needs source excerpts, which this bundle does not contain

## Auditor notes on choices (appended by hand; not generated from the JSON)

- **Bundle and profile.** `scripts/validate_bundle.py` reported the bundle as valid and frozen, and its hash matches `bundle.lock.json`. I used the requested profile, `multimodal-datastory` (modules A-D). MED-01 is outside this profile and was not checked.
- **Primary code.** The chart/summary conflict exists only after the recorded 2050 click. In S01 the summary matches the chart. Following the codebook boundary rule, I coded it INT-02 (interaction-produced conflict) rather than DAT-01 or SUB-02, and added DAT-01 as a secondary tag because the "What this means" explanation is not supported by the chart's shown state in S03.
- **Fit rated questionable, not inappropriate.** The summary names its own year ("In 2020"), which leaves a fixed-baseline reading open. It is not labeled as a baseline, though, so its role is unclear rather than plainly contradictory.
- **Consequence rated moderate, not major.** The control works: title, values, button state, and bar lengths all update. The task is not blocked; the interpretation for the selected scenario is missing.
- **Bar checks.** PIL was unavailable, so I decoded the PNGs with the Python standard library (zlib) and counted pixels of the bar teal. Desktop bar widths are proportional in both states, about 8.8 px per percentage point (A01: 106/80/35 px for 12/9/4%; A04: 275/239/97 px for 31/27/11%). In the mobile images A02 and A03, the only teal pixels are in the year-button band, and the label-to-value gap is pure white. That supports Q001.
- **Finding limitations (in the JSON; the renderer does not print them).** Only the 2050 click at the desktop viewport was recorded. 2100, returning to 2020, and the mobile viewport are untested and not generalized. No source was supplied, so the cause is unknown. The capture observed the page 800 ms after the click. The finding says nothing about who or what produced the page.
- **No page-embedded instructions** addressed to the auditor were found in the text spans or screenshots.
