# Slop-feature audit fx-02-multimodal-core-01

bundle `fx-02` · profile `multimodal-core` · rubric 0.1.1 · status **completed**

## Scope and limits

No accepted findings. The page's main surface cue, a gradient-filled headline (#hero > h1, computed orange rgb(255,138,0) to pink rgb(255,45,111)), is recorded as a contextual exception: the provided brand constraint requires that sunrise gradient on the wordmark and main headline, it is used only on the headline, and its colors fit the festival name. The copy is specific (named acts per day; June 11-13, which fall on Friday to Sunday in 2027 as the lineup says; Harbor Lawn; Pier Street station; $45 day passes), the section order fits an event announcement, and captured styles show no cards, decorative objects, or configured animation. Separately, as quality observations rather than slop claims: the gradient heading measures roughly 2.3:1 to 2.9:1 against the cream background, below the 3:1 large-text minimum, and because the gradient spans the full-width heading box, the glyphs show only its orange-to-red-orange half. Evidence is a single desktop viewport with no interactions or source.

- Assessed modalities: computed_style, dom, screenshot, text
- Not assessed: interaction (no interactions were recorded in the bundle)
- Not assessed: source (no source excerpts were supplied)
- Limitation: Single desktop viewport (1280x800) at scroll 0; no mobile viewport, scroll states, or full-page capture. Visible content ends near y=495px, but anything below the first viewport is unknown.
- Limitation: No interactions or source excerpts, so INT-01, INT-02, and SRC-01 are unassessed.
- Limitation: Page or body background styles were not captured; the background color and contrast ratios come from sampling screenshot pixels and are approximate.
- Limitation: The exception rests on the provided context constraint; the page's own statement (T009) is used only as corroboration.
- Limitation: Synthetic development fixture.
- Counts: 0 findings, 1 contextual exception, 2 quality observations, 0 exploratory candidates, 3 unassessed features

These findings identify features that may contribute to a perceived AI-slop impression; they do not establish who or what made the site.

## Findings

No accepted findings in the assessed scope.

## Contextual exceptions

- X001 VIS-02: The main heading 'Sunrise Fest 2027' (#hero > h1, 72px, weight 800) is filled with a horizontal gradient via background-clip: text, computed as linear-gradient(90deg, rgb(255, 138, 0), rgb(255, 45, 111)) with transparent text color. It is the only gradient or highlighted text on the captured page; the heading appears to serve as both wordmark and main headline. (documented_requirement: The provided context documents this gradient as a brand requirement for the wordmark and main headline, which is exactly where it appears. It also falls short of VIS-02 on its own terms: a single occurrence, not a device repeated across sections, and its sunrise colors relate to the festival's name.)

## Quality observations

- Q001 [accessibility]: The gradient heading has low contrast against the cream page background. Sampled glyph colors run from about rgb(255,137,0) at the left to rgb(255,93,52) at the right, against a background of rgb(255,250,243), giving roughly 2.3:1 to 2.9:1, below the WCAG 2.x AA 3:1 minimum for large text. This is an accessibility observation, not a slop claim, and it does not change X001.
- Q002 [rendering]: The gradient is sized to the full-width h1 box (about 1184px), but the glyphs occupy only its left half (about 579px). The rendered heading therefore shows orange shading only to red-orange; the pink end stop, rgb(255, 45, 111), falls in empty space to the right of the text. Whether this matches the brand guide's intent cannot be judged from the bundle.

## Exploratory candidates (not scored)

None recorded.

## Unassessed checks

- INT-01: needs a recorded interaction; the bundle contains none
- INT-02: needs a recorded interaction; the bundle contains none
- SRC-01: needs source excerpts; none were supplied

## Auditor notes (choices made; added after rendering, not derived from the JSON)

- **Profile.** `multimodal-core` as requested. I could view the screenshot, so this profile fits. The page is an event announcement, not a data story, so the data-story module was not needed.
- **Coding the gradient.** The gradient-filled headline is coded VIS-02, because the codebook boundary assigns gradient or highlighted headline text to VIS-02 and whole-palette packages to VIS-01. It is recorded as a contextual exception (`documented_requirement`), not a finding. The basis is the provided `context.constraints` entry. The page's own sentence about the gradient (T009) is page data. It is cited only as corroboration and was not treated as an instruction, since it does not address the auditor.
- **Wordmark and headline.** The bundle has no separate logo or image element, so I inferred that the h1 "Sunrise Fest 2027" serves as both the wordmark and the main headline the constraint names.
- **Measurements.** Body and page background styles were not captured. I read A01 with a small standard-library PNG decoder, kept in the session scratchpad and not part of the outputs. The background measured rgb(255,250,243). For each 40px strip of the heading I took the most saturated glyph pixel and computed WCAG relative-luminance contrast. Anti-aliasing and the sampling method make these figures approximate. The gradient's two computed stops alone give 2.28:1 (orange) and 3.45:1 (pink) against that background.
- **Date check.** June 11, 2027 is a Friday and June 13, 2027 is a Sunday, checked with Python's calendar. That matches the lineup's Friday/Saturday/Sunday labels, so SUB-02 found no conflict.
- **Considered and not recorded:**
  - The 1-3 numbering on the lineup list follows a real day sequence, so it is not gratuitous numbering under VIS-02.
  - "Used on every poster since 2019" is an ordinary first-party brand statement, not a statistic or a claim that needs a cited basis, so it is not SUB-01.
  - The brand note sits under the "Getting there" heading, which is mildly out of place. It is specific, though, and one sentence is too little for an exploratory candidate.
- **Status.** `completed`: every check the profile and evidence allow was run. INT-01, INT-02 and SRC-01 are unassessed because the bundle has no interactions or source, not because I abstained.
- **Scope.** I judged only the frozen bundle. There was no live browsing, and nothing outside the skill folder and the bundle was opened.
