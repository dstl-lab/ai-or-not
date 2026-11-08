# Slop-feature audit audit-fx-buttons-working-broken-mmcore-01

bundle `fx-buttons-working-broken` · profile `multimodal-core` · rubric 0.1.0 · status **completed**

## Scope and limits

A plain, specific single-view dashboard: Verdana text, one muted green accent on outlined buttons, a single bordered reading panel, and copy that names the neighborhood, sensor model, correction formula, and month. No surface, template, or copy pattern from the codebook was observed. The slop-associated feature is behavioral: the 'Compare with last year' button, which carries the comparison named in the stated purpose, was clicked on a fresh load and produced no visible text or DOM change within 1200 ms; the after screenshot is byte-identical to the initial one. The sibling 'Show PM2.5' button worked under the same capture method, so the failure is specific to one control. A dead control is an observed failure, explained equally well by an ordinary bug or an unfinished feature, and says nothing about who or what made the page. The time-aggregation labels ('averaged over September 2026', 'Current reading', '8-hour average') are loosely matched and were recorded as a non-counted exception. The Download CSV link was not tested and is unknown, not broken.

- Assessed modalities: screenshot, text, dom, computed_style, interaction
- Not assessed: source (the bundle contains no source excerpts (modalities.source is false))
- Limitation: One desktop viewport (1280x800) at scroll offset 0; no mobile viewport, full-page capture, or keyboard-focus states.
- Limitation: Each click was observed once on a fresh load within a fixed window (800 ms, 1200 ms); delayed results and combined interactions were not tested.
- Limitation: No source excerpts, so the cause of the dead control (SRC-01) cannot be examined.
- Limitation: The Download CSV link was not exercised; its behavior is unknown.
- Limitation: Synthetic fixture with provided context; creation history is withheld and not judged.
- Counts: 1 finding, 2 contextual exceptions, 0 quality observations, 0 exploratory candidates, 1 unassessed feature

These findings identify features that may contribute to a perceived AI-slop impression; they do not establish who or what made the site.

## Findings

### F001 · INT-01 Decorative or nonfunctional affordance

- **What:** The 'Compare with last year' button advertises the year-over-year comparison that the stated purpose names. In E02 it was clicked on a fresh load (completed) and, within 1200 ms, no visible text or DOM state changed: the after screenshot A03 is byte-identical to the initial A01, and the comparison status line still reads 'Select a pollutant or a comparison above.' No comparison appears in the captured view.
- **Where (region):** R02 (toolbar) · state S01 · image A01 with box · selector #compare-last-year; R02 (toolbar) · state S03 · image A03 with box · selector #compare-last-year; R03 (reading panel) · state S03 · image A03 with box · selector #comparison
- **Evidence:**
  - `interaction:E02` Click on #compare-last-year from S01 to S03, execution_status completed; observed changes: text_unchanged and dom_unchanged (no aria-pressed/expanded/selected or input value change) within 1200 ms.
  - `text:T004` The button label in the initial state, which advertises a comparison with the previous year. "Compare with last year"
  - `text:T021` The #comparison status line after the click, unchanged from the initial state (T008). "Select a pollutant or a comparison above."
  - `text:T020` The reading after the click, unchanged from the initial state (T007). "Ozone: 41 ppb (8-hour average)"
  - `screenshot:A03` After-click screenshot; its sha256 equals that of the initial screenshot A01, so nothing visible changed in the viewport.
  - `interaction:E01` Control comparison: the sibling 'Show PM2.5' button, clicked the same way on a fresh load, changed #metric text within 800 ms, so the capture method does detect changes on this page.
  - `context:purpose` The provided purpose includes comparing the readings with the previous year, so this control carries a stated main task.
- **Interpretation:** slop association moderate (A control that advertises the page's headline comparison but does nothing fits the surface-without-integration pattern, with concrete tested evidence. Not strong: it is a single control, the sibling control works, the rest of the page is specific, and an ordinary bug explains it equally well.); fit inappropriate (The stated purpose is to compare readings with the previous year; a visible control for that comparison that produces nothing works against the purpose.); consequence major (Tested failure (E02): the year-over-year comparison, half of the stated purpose, does not appear, and no other route to it is visible in the captured page.)
- **Alternative explanations:** Ordinary implementation bug, such as a click handler that is not attached or a failed request for last year's data; Unfinished feature: previous-year data or the comparison view not yet built when the page was captured; The comparison takes longer than the 1200 ms observation window to appear; The comparison depends on a prerequisite the page does not state, although the status line suggests it can be chosen directly
- **Observation confidence:** high (A completed recorded click, explicit unchanged-text and unchanged-DOM records, byte-identical before and after screenshots, and a working sibling control tested the same way.) · evidence status `research_hypothesis`

## Contextual exceptions

- X001 SUB-02: The time-aggregation labels do not line up cleanly across regions: the header says readings are averaged over September 2026 and the method note says hourly values are averaged per day, then per month, while the panel is headed 'Current reading' and its default value is labeled '8-hour average'. After E01 the PM2.5 value is labeled 'monthly mean', which matches the header. (insufficient_evidence_for_finding: Not a clear conflict: pollutant-specific conventions (ozone is commonly reported as an 8-hour average) allow a September mean of 8-hour values, so the labels may be terse rather than contradictory, and 'Current reading' can mean the selected reading. The tension is real but too ambiguous to count as incoherence.)
- X002 INT-02: After E01 (Show PM2.5) the reading updates to PM2.5, but the status line under it still says 'Select a pollutant or a comparison above.' even though a pollutant has just been selected, and the button shows no selected styling (computed style of D015 equals D007). (insufficient_evidence_for_finding: The working control did what it advertised. The leftover line sits in the #comparison slot, which belongs to the untriggered comparison, so it reads as that slot's empty state rather than a linked summary contradicting the result; the stale pair (#metric and #comparison) sits within one region, short of INT-02's two-region minimum, and the missing selected styling is not a content conflict.)

## Quality observations

None recorded.

## Exploratory candidates (not scored)

None recorded.

## Unassessed checks

- SRC-01: needs source excerpts, which this bundle does not contain; the cause of the E02 result cannot be examined

## Auditor notes on choices

These notes record judgment calls made without asking questions. They add no findings and do not change the JSON; the sections above are rendered from `audit.json` by `scripts/render_report.py`.

- **Profile.** `multimodal-core` (modules A–C), as the task specified. The page is a small data dashboard, but the data-story module (DAT-01 to DAT-04) is not in this profile, so those checks were not run or listed.
- **Bundle.** `scripts/validate_bundle.py` reported the bundle valid and frozen (0 errors, 0 warnings). All states loaded with fonts. The audit validates with 0 errors and 0 warnings.
- **Working vs dead button.** E01 ("Show PM2.5") changed the reading text, so it is not a finding. E02 ("Compare with last year") is the single INT-01 finding: a completed click, unchanged text and DOM, and an after screenshot (A03) whose sha256 matches the initial A01. E01 is cited as a control showing that the capture method does detect changes on this page.
- **Consequence rated major.** The provided purpose names the previous-year comparison, and this button is the only visible route to it, so the tested failure blocks a stated main task. The finding's limitations list the caveats: one 1200 ms observation, no repeated or combined clicks, no source.
- **Slop association rated moderate, not strong.** It is one control, its sibling works, and the copy is specific. An ordinary bug explains it equally well. Nothing here is a judgment about authorship.
- **Download CSV.** The bundle lists it as untested (it would leave the page), so it is unknown, not broken, and was not judged under INT-01.
- **Not counted (contextual exceptions).** X001 is the loose time-aggregation labels: "averaged over September 2026", "Current reading", "8-hour average", and "monthly mean". X002 is the leftover status prompt after the working PM2.5 click. Both are weak cues that do not meet their features' inclusion rules.
- **Background knowledge not used as evidence.** Outside the bundle, PurpleAir PA-II units are generally described as particulate sensors, and the EPA 2021 correction as a PM2.5 correction. If so, the method note gives no instrument for the default ozone reading. This can't be checked from the bundle, so it was not used to support any finding or exception. A reviewer with domain knowledge may want to look at it.
- **Quality checks.** Text contrast was computed from the captured colors against the white ground seen in the screenshots (the body background was not captured as a computed style). The lowest ratio, the 13px method note, is about 4.8:1, which meets WCAG AA. Mobile layout and keyboard focus were not captured, so no quality observations were recorded.
- **Report format.** The task asked for `report.md`, so the renderer's Markdown output was used instead of HTML.
