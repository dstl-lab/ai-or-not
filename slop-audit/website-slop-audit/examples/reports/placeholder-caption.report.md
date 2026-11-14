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

## Study questionnaire

Questionnaire phd-reviewer-v1, the participants' per-website questions in their answer formats. Formed from this audit: two findings (F001 placeholder caption, F002 unsupported headline statistic), the plain palette and type seen in A01, and coverage limited to one desktop screenshot with text and DOM, no interactions or source. A perceived impression; the page alone cannot show who or what made it.

| Question | Answer | Reason | Rests on |
|---|---|---|---|
| Based on your overall impression, how strongly does this website appear AI-generated? | 3 (of 1–5: 1 = Not at all, 5 = Extremely) | The placeholder caption and the unsupported 42% read as unattended scaffolding, but the plain, specific rest of the page pulls the impression down to moderate. | finding:F001, finding:F002, screenshot:A01 |
| Click the parts of the website that feel AI-generated. | 2 mark(s), listed below | The two places the audit located a slop-associated cue. | finding:F001, finding:F002 |
| Rate how AI-generated each feature looks. | see the feature table below | Writing and the chart carry the two findings; the visual design is plain. | finding:F001, finding:F002 |
| Which feature looks most AI-generated? | Writing | Writing has the highest rating, because of the placeholder caption. | finding:F001 |
| How much of this site did AI build? | A little | Most of the page reads as specific and hand-assembled; two parts look left on autopilot. | finding:F001, finding:F002 |
| The design looks template-like. | 2 (of 1–5: 1 = Disagree, 5 = Agree) | The visual design is plain rather than template-like. | screenshot:A01 |
| The text sounds AI-written. | 3 (of 1–5: 1 = Disagree, 5 = Agree) | The caption is template text, but the introduction is specific to Oakland's lanes and years. | finding:F001, text:T018 |
| How polished is this site? | 3 (of 1–5: 1 = Rough, 5 = Polished) | Clean visual presentation, undercut by an unfinished caption. | screenshot:A01, finding:F001 |
| How good is this project overall? | 2 (of 1–5: 1 = Poor, 5 = Excellent) | The story's takeaway is missing and its headline number is unsupported by its own chart. | finding:F001, finding:F002 |
| Did a technical problem affect your review? | No | The page loaded completely and nothing failed during capture. | route:/index.html |

Feature ratings (0 = Human-made, 10 = AI-generated; NA = not on the site):

| Feature | Rating | Reason | Rests on |
|---|---|---|---|
| Colors | 2 | Plain, muted palette with no default-package pattern. | screenshot:A01 |
| Gradients | NA | No gradients in the screenshot or captured styles. | screenshot:A01 |
| Fonts | 2 | Ordinary type, used consistently; nothing template-like. | screenshot:A01 |
| Emoji/icons | NA | The page has no emoji or icons. | screenshot:A01 |
| Buttons and hover effects | NA | The page has no buttons. | screenshot:A01 |
| Layout and spacing | 3 | A stock title, stat strip, and chart sequence; serviceable but familiar. | region:R02, region:R03 |
| Animations | NA | No animation was captured or configured. | screenshot:A01 |
| Charts | 5 | The chart is specific, but its caption is a placeholder and the headline number does not match it. | finding:F002, region:R03 |
| Writing | 6 | A lorem-ipsum caption asking to be replaced is template text left in place. | finding:F001 |
| Navigation | NA | A single page with no navigation. | screenshot:A01 |

Marked spots:

1. Text on `/index.html` (`#chart-caption`): "Lorem ipsum dolor sit amet — replace with key insight before publishing.". Literal template text where the chart's takeaway belongs.
2. Text on `/index.html` (`#stat-strip > div:nth-of-type(2) > b`): "42%". A headline number the chart's own values do not support.

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
