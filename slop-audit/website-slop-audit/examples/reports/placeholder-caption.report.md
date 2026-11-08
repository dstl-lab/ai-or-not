# Slop-feature audit example-placeholder-caption

bundle `fx-03` · profile `multimodal-datastory` · rubric 0.1.1 · status **completed**

## Scope and limits

Two substance problems: a literal placeholder caption under the main chart, and a headline statistic (42% faster) that the chart's own values do not support. Typography and palette are plain and showed no default-package pattern. The byline was masked for blinding.

- Assessed modalities: computed_style, dom, screenshot, text
- Not assessed: interaction (no interactions were recorded)
- Not assessed: source (no source excerpts supplied)
- Limitation: Single desktop screenshot
- Limitation: No interactions or source
- Limitation: Synthetic development fixture
- Counts: 2 findings, 0 contextual exceptions, 0 quality observations, 0 exploratory candidates, 4 unassessed features

These findings identify features that may contribute to a perceived AI-slop impression; they do not establish who or what made the site.

## Findings

### F001 · SUB-01 Placeholder or unverifiable substance

- **What:** literal_placeholder: the chart caption is template text asking to be replaced, so the chart has no stated takeaway.
- **Where (region):** R04 (chart caption) · state S01 · image A01 with box
- **Evidence:**
  - `text:T018` The caption text. "Lorem ipsum dolor sit amet — replace with key insight before publishing."
  - `screenshot:A01` The caption under the chart.
- **Interpretation:** slop association moderate (A placeholder left in a finished-looking story reads as unattended scaffolding; it is equally typical of a hurried human draft.); fit inappropriate (The caption is where the story's takeaway belongs.); consequence moderate (Readers get no interpretation of the chart.)
- **Alternative explanations:** Unfinished draft published early; Template caption never replaced
- **Observation confidence:** high (Exact text captured from the DOM and visible in the screenshot.) · evidence status `research_hypothesis`

### F002 · DAT-01 Narrative–chart disconnect

- **What:** The statistic strip claims '42% faster commutes', but the chart's own labeled medians fall by 14% to 24% (for example 25 to 19 minutes), and no basis for 42% appears in the inspected scope.
- **Where (cross-region):** R02 (statistic strip) · state S01 · image A01 with box; R03 (chart) · state S01 · image A01 with box
- **Evidence:**
  - `text:T006` The headline statistic. "42%"
  - `text:T007` Its label. "faster commutes"
  - `text:T012` Telegraph Ave before. "25 min"
  - `text:T013` Telegraph Ave after. "19 min"
- **Interpretation:** slop association weak (An unsupported headline number is a candidate metric-theater cue, but a different calculation (for example speed rather than time) could exist outside the captured page.); fit questionable (The number frames the story but is not tied to the shown data.); consequence moderate (The headline overstates what the chart shows.)
- **Alternative explanations:** Computed on a different measure or corridor set; Left over from an earlier draft; Arithmetic error
- **Observation confidence:** high (All values are captured as text spans.) · evidence status `research_hypothesis`

## Contextual exceptions

None recorded.

## Quality observations

None recorded.

## Exploratory candidates (not scored)

None recorded.

## Unassessed checks

- INT-01: needs interaction, which this bundle does not contain
- INT-02: needs interaction, which this bundle does not contain
- SRC-01: needs source, which this bundle does not contain
- DAT-02: needs interaction, which this bundle does not contain
