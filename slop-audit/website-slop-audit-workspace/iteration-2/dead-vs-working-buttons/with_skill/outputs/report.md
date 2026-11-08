# Slop-feature audit fx-06-multimodal-core-r1

bundle `fx-06` · profile `multimodal-core` · rubric 0.1.1 · status **completed**

## Scope and limits

A short, plain neighborhood air-quality readout: title and data scope, two buttons and a download link, one reading panel, and a method note. The main observation is behavioral. In a completed recorded click (E02) the 'Compare with last year' button changed nothing: no text, no ARIA or input state, and its after-state screenshot is byte-identical to the before state. The comparison it advertises, which the panel prompt and the provided purpose also name, never appears in the captured page. The sibling 'Show PM2.5' button worked under the same procedure (E01), so this is a control-specific failure, not a capture-wide script failure. 'Download CSV' was not exercised and is not judged. Surface styling (Verdana, white background, outlined green buttons, one bordered panel) and the specific copy (place, sensor count, month, sensor model, correction formula) showed no codebook surface, layout, copy, or substance pattern. A loose averaging label on the ozone reading is recorded as a contextual exception, not a finding. Evidence covers one desktop viewport and one click per control; nothing here bears on who or what made the page.

- Assessed modalities: screenshot, text, dom, computed_style, interaction
- Not assessed: source (no source excerpts were supplied in the bundle)
- Limitation: Desktop viewport only (1280x800, one scroll position); no mobile or keyboard-focus evidence.
- Limitation: Each button was clicked once on a fresh load with an 800 or 1200 ms window; combinations such as comparing after selecting PM2.5 are untested.
- Limitation: Download CSV link was not exercised (it would leave the page); its behavior is unknown, not broken.
- Limitation: No source excerpts, so SRC-01 is unassessed and the cause of the E02 failure cannot be examined.
- Limitation: Profile multimodal-core was used as requested; the data-story module (DAT-01 to DAT-04) was not applied although the provided genre is a data dashboard.
- Limitation: Synthetic development fixture: the context was written by the fixture author.
- Counts: 1 finding, 1 contextual exception, 0 quality observations, 0 exploratory candidates, 1 unassessed feature

These findings identify features that may contribute to a perceived AI-slop impression; they do not establish who or what made the site.

## Findings

### F001 · INT-01 Decorative or nonfunctional affordance

- **What:** The 'Compare with last year' button was clicked in a completed recorded test (E02) and nothing changed: no text, no ARIA or input state, and the after-state screenshot A03 is byte-identical (same recorded sha256) to the before-state A01. The comparison the button, the panel prompt, and the provided purpose all advertise never appears in the captured page. The sibling 'Show PM2.5' button worked under the same procedure (E01).
- **Where (region):** R02 (toolbar) · state S03 · image A03 with box · selector #compare-last-year; R02 (toolbar) · state S01 · image A01 with box · selector #compare-last-year
- **Evidence:**
  - `interaction:E02` Click on #compare-last-year, execution_status completed, observed 1200 ms after the action on a fresh load: no visible text changed and no aria-pressed/expanded/selected or input value changed.
  - `text:T004` The button label advertises a year-over-year comparison. "Compare with last year"
  - `text:T008` Before the click, the reading panel's #comparison line invites the reader to choose a comparison. "Select a pollutant or a comparison above."
  - `text:T021` After E02, the same #comparison line still shows only the prompt; no comparison result appears. "Select a pollutant or a comparison above."
  - `text:T020` After E02, the reading is unchanged from the initial state. "Ozone: 41 ppb (8-hour average)"
  - `screenshot:A03` After-state screenshot of E02; the manifest records the same sha256 as the before-state screenshot A01, so the rendered viewport did not change.
  - `dom:D024` The button in S03 has the same computed style as the working Show PM2.5 button (opacity 1, same colors); no disabled styling was captured.
  - `interaction:E01` Contrast case: the sibling Show PM2.5 button, tested the same way, changed #metric to the PM2.5 value, so page scripts were running during capture.
  - `context:purpose` The provided purpose names comparison with the previous year as half of what the page is for.
- **Interpretation:** slop association moderate (A control the page itself advertises, carrying half the stated purpose, does nothing while its sibling works: a concrete integration gap of the 'surface present, behavior missing' kind. It is one control, and an ordinary bug or unfinished feature explains it equally well.); fit inappropriate (The provided purpose includes comparing readings with the previous year; a comparison control that produces nothing works against that purpose.); consequence major (Tested failure (E02): no year-over-year comparison can be obtained anywhere in the captured page, which blocks the comparison part of the main task. Reading and pollutant switching still work.)
- **Alternative explanations:** Ordinary bug: click handler missing or bound to the wrong element; Unfinished feature: last year's data or the comparison view not yet built; Comparison loads slower than the 1200 ms observation window on this server; Unstated prerequisite (for example selecting a pollutant first), though the prompt's 'or' and the button's normal styling do not suggest one
- **Observation confidence:** high (A completed recorded event with explicit no-change records for text and DOM state, plus a byte-identical after-state screenshot.) · evidence status `research_hypothesis`

## Contextual exceptions

- X001 SUB-02: Averaging labels differ across regions: the header says readings are averaged over September 2026 and the method note says hourly values are averaged per day then per month, while the reading panel heads the default value 'Current reading' and labels ozone as an 8-hour average. The PM2.5 state (S02) is labeled monthly mean, matching the header. (insufficient_evidence_for_finding: An 8-hour average is the conventional averaging time for reporting ozone, so a monthly mean of daily 8-hour values would reconcile all three texts, and 'current' is a common dashboard label for the latest period. The labels are loose rather than shown to conflict, so this is not counted as SUB-02.)

## Quality observations

None recorded.

## Exploratory candidates (not scored)

None recorded.

## Unassessed checks

- SRC-01: Needs source excerpts; none were supplied, so the cause of the failed control in E02 cannot be examined.

## Auditor notes on choices (added by hand, not part of the rendered audit)

Everything above was rendered from `audit.json` by `scripts/render_report.py` after `scripts/validate_audit.py` reported 0 errors and 0 warnings. The bundle validated and was already frozen (`bundle.lock.json`, hash matches). These notes record the choices made without asking:

- **Profile.** `multimodal-core` was used as requested, and all three screenshots were viewed. The provided genre (environmental data dashboard) would also fit `multimodal-datastory`, but the DAT-01 to DAT-04 checks were not run. Under that profile the dead button would still be coded INT-01, because a failing control is INT-01 and not DAT-02.
- **Working vs dead button.** E01 (Show PM2.5) changed `#metric` as advertised, so it is not a finding; it is cited only as a contrast case showing that page scripts were running. E02 (Compare with last year) is the only accepted finding.
- **Untested control.** The Download CSV link was not exercised during capture. It is recorded as untested and is not called broken.
- **Localization.** The finding is located on the control itself (toolbar R02, button box and `#compare-last-year`) in the before state S01 and after state S03. The unchanged reading panel (R03) is cited as text evidence, not as a second location, because INT-01 is a region-unit feature about the control.
- **Ratings.** Slop association is *moderate*, not strong: only one control fails, the sibling works, and an ordinary bug explains it equally well. Consequence is *major* because a completed test shows that the comparison, which is half of the provided purpose, cannot be obtained anywhere in the captured page. A reviewer could reasonably call it *moderate*, since reading and switching pollutants still work.
- **Averaging labels (X001).** The ozone "8-hour average" and the "Current reading" heading do not literally match the monthly averaging stated in the header and method note. This is recorded as a contextual exception, not a SUB-02 finding, because ozone is conventionally reported as an 8-hour average.
- **Outside knowledge not applied.** General domain knowledge suggests the sensor model named in the method note measures particulates, not ozone. The bundle does not establish this, so it was not used for any rating and is mentioned here only for a human reviewer.
- **Not included.** There is no authorship judgment, probability, or redesign advice, and no HTML report, since only `report.md` was requested.
