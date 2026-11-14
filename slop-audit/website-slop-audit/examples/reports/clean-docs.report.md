# Slop-feature audit example-clean-docs

bundle `fx-13` · profile `multimodal-core` · rubric 0.1.1 · status **completed**

## Scope and limits

No accepted findings and no candidate cues worth recording as exceptions. The page is specific (real flags, defaults, file formats, and exit codes) and its conventional documentation layout matches its job.

- Assessed modalities: computed_style, dom, screenshot, text
- Not assessed: interaction (no interactions were recorded)
- Not assessed: source (no source excerpts supplied)
- Limitation: Interaction and source checks were not possible
- Limitation: Synthetic development fixture
- Counts: 0 findings, 0 contextual exceptions, 0 quality observations, 0 exploratory candidates, 3 unassessed features

These findings identify features that may contribute to a perceived AI-slop impression; they do not establish who or what made the site.

## Study questionnaire

Questionnaire phd-reviewer-v1, the participants' per-website questions in their answer formats. Formed from this audit: zero findings or exceptions, specific technical content in the text, and one desktop screenshot of a conventional documentation layout; no interactions or source. A perceived impression, not knowledge of how the page was made.

| Question | Answer | Reason | Rests on |
|---|---|---|---|
| Based on your overall impression, how strongly does this website appear AI-generated? | 1 (of 1–5: 1 = Not at all, 5 = Extremely) | Nothing in the assessed scope fits a slop pattern; the content is specific and the layout matches its job. | screenshot:A01, text:T006 |
| Click the parts of the website that feel AI-generated. | none | The audit located no slop-associated cue to point to. | none |
| Rate how AI-generated each feature looks. | see the feature table below | Every present feature is conventional for documentation and specific to the tool. | screenshot:A01 |
| Which feature looks most AI-generated? | None | No feature looks AI-generated; the highest rating is 2 of 10. | screenshot:A01 |
| How much of this site did AI build? | None | Nothing on the page reads as generated; it is specific throughout. | text:T006 |
| The design looks template-like. | 2 (of 1–5: 1 = Disagree, 5 = Agree) | A conventional documentation layout, but chosen for its job rather than as filler. | region:R01, region:R03 |
| The text sounds AI-written. | 1 (of 1–5: 1 = Disagree, 5 = Agree) | The text is specific and technical. | text:T016 |
| How polished is this site? | 3 (of 1–5: 1 = Rough, 5 = Polished) | Tidy and functional, without visual refinement. | screenshot:A01 |
| How good is this project overall? | 4 (of 1–5: 1 = Poor, 5 = Excellent) | Clear, complete reference content for its audience. | text:T006, region:R03 |
| Did a technical problem affect your review? | No | The page loaded completely and nothing failed during capture. | route:/index.html |

Feature ratings (0 = Human-made, 10 = AI-generated; NA = not on the site):

| Feature | Rating | Reason | Rests on |
|---|---|---|---|
| Colors | 1 | Plain documentation colors. | screenshot:A01 |
| Gradients | NA | No gradients. | screenshot:A01 |
| Fonts | 1 | Standard body and monospace type for code. | screenshot:A01 |
| Emoji/icons | NA | No emoji or icons. | screenshot:A01 |
| Buttons and hover effects | NA | No buttons. | screenshot:A01 |
| Layout and spacing | 1 | Sidebar, body, and options table: the expected shape of reference documentation. | region:R01, region:R03 |
| Animations | NA | No animation. | screenshot:A01 |
| Charts | NA | No charts. | screenshot:A01 |
| Writing | 1 | Real flags, defaults, file formats, and exit codes. | text:T016 |
| Navigation | 2 | A standard documentation sidebar; conventional, and it fits. | region:R01 |

## Findings

No accepted findings in the assessed scope.

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
