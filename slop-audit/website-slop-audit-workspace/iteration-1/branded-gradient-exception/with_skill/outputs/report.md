# Slop-feature audit fx-branded-gradient-multimodal-core-01

bundle `fx-branded-gradient` · profile `multimodal-core` · rubric 0.1.0 · status **completed**

## Scope and limits

No accepted findings. The one candidate cue, the orange-to-pink gradient on the main headline and wordmark, is recorded as a contextual exception under VIS-02: the supplied context documents it as a brand-guide requirement, it appears once rather than as a repeated device, and its sunrise colours fit the festival's name. The rest of the captured page is plain and specific: named acts for each of three days that agree with the stated June dates, a named venue and station, a gate time, and prices, with no cards, icons, eyebrow labels, statistic tiles, stock section sequence, or configured animation. Separately, quality notes concern the headline only: its gradient colours fall below the 3:1 large-text contrast guideline against the light background, and the gradient spans the full heading width so its pink end never reaches the letters. These are quality observations, not slop claims. Coverage is one desktop screenshot at scroll 0 with DOM text and computed styles; mobile layout, interactions, and source were not available.

- Assessed modalities: computed_style, dom, screenshot, text
- Not assessed: interaction (no interactions were recorded in the bundle)
- Not assessed: source (no source excerpts were supplied)
- Limitation: One desktop screenshot at scroll offset 0; no mobile viewport, and content below the first viewport, if any, was not captured (the screenshot shows blank space below the visitor details).
- Limitation: No recorded interactions or source excerpts, so INT-01, INT-02, and SRC-01 are unassessed.
- Limitation: Motion judged only from captured computed styles (animation-name none); transition durations and playback were not recorded.
- Limitation: Contrast ratios use a background colour sampled from screenshot pixels because the page body's computed style was not captured.
- Limitation: The brand requirement comes from the supplied capture-plan context (a synthetic fixture), not from an inspected brand guide.
- Counts: 0 findings, 1 contextual exception, 2 quality observations, 0 exploratory candidates, 3 unassessed features

These findings identify features that may contribute to a perceived AI-slop impression; they do not establish who or what made the site.

## Findings

No accepted findings in the assessed scope.

## Contextual exceptions

- X001 VIS-02: The main headline and wordmark 'Sunrise Fest 2027' is 72px, weight 800, with transparent text colour and a computed linear-gradient from rgb(255, 138, 0) to rgb(255, 45, 111) clipped to the text. It is the only gradient or highlighted text in the captured page; the other headings and all body text are solid dark brown. (documented_requirement: The supplied context documents this gradient as a brand-guide requirement for the wordmark and main headline, and it appears once rather than repeating across sections, so VIS-02's repetition rule is not met either. The sunrise colours also fit the festival's name. Also checked under VIS-01: one gradient is excluded there and no palette package recurs across regions.)

## Quality observations

- Q001 [accessibility]: The gradient headline has low contrast against the light page background. Rendered text runs from about rgb(255, 137, 0) at the left to about rgb(255, 93, 54) at the right end of the letters; against the background sampled from the screenshot, about rgb(255, 250, 243), that is roughly 2.3:1 to 2.9:1, below the WCAG 2.x AA minimum of 3:1 for large text. The headline is still legible in the screenshot.
- Q002 [rendering]: The gradient is sized to the full width of the h1 block (about 92% of the image width) while the letters cover roughly the left half, so the visible wordmark runs from orange only to a red-orange near rgb(255, 93, 54). The pink end stop, rgb(255, 45, 111), falls in empty space to the right of the text and does not appear on the letters.

## Exploratory candidates (not scored)

None recorded.

## Unassessed checks

- INT-01: Needs a completed recorded interaction; the bundle has none. No controls are visible in the captured screenshot either.
- INT-02: Needs a completed recorded interaction; the bundle has none.
- SRC-01: Needs supplied source excerpts; the bundle has none.

## Auditor notes (choices made)

Everything above this section was generated from `audit.json` by `scripts/render_report.py`. These notes add nothing new; they explain choices made during the audit.

- **Profile.** I used `multimodal-core`, as requested. I could view the screenshot, and the page is an event promotion page rather than a data story, so the data-story module does not apply.
- **Bundle checks.** `scripts/validate_bundle.py` passed with 0 errors and 0 warnings. The bundle was already frozen, and the `bundle_hash` matches `bundle.lock.json`. I did not re-freeze it, so the evidence was not modified. `scripts/validate_audit.py` passed with 0 errors and 0 warnings.
- **Code for the gradient headline: VIS-02, not VIS-01.** The codebook's boundary rule puts typographic treatment of headline text (gradient or highlighted words) under VIS-02, and palette packages under VIS-01. I therefore recorded the gradient as a VIS-02 contextual exception and checked VIS-01 separately. VIS-01 excludes a single gradient, and no palette package recurs across regions, so I added no second VIS-01 entry. Either way, the gradient is not counted as a finding.
- **What the exception rests on.** The exception is based on the supplied context constraint, which has status `provided`: the brand guide requires the gradient. The page's own sentence about the gradient (T009) is cited only as supporting evidence. Page text alone would not establish a brand requirement. That sentence does not address the auditor, so it is not listed under untrusted instructions.
- **Contrast figures (Q001).** The body element's style was not captured, so I decoded `assets/A01.png` with a standard-library script. From it I sampled the page background (rgb(255, 250, 243)) and the rendered colours of the headline letters. I then computed WCAG relative-luminance contrast:
  - gradient start: about 2.29:1
  - rightmost visible letters: about 2.94:1
  - body text: about 15.7:1

  These figures are approximate because they come from screenshot pixels.
- **Gradient extent (Q002).** The letters end at about x = 628 px of the 1280 px image, and the h1 block spans about 48 to 1232 px. The colour expected at that point in the gradient, about rgb(255, 92, 54), matches the sampled pixels. This is how I concluded that the pink end stop falls beyond the text.
- **Considered and not recorded:**
  - The numbered list of days is a real chronological sequence. June 11 to 13, 2027 fall on Friday to Sunday, which matches the lineup labels.
  - The "since 2019" poster claim is an ordinary organizer statement, not a statistic that needs a source.
  - The brand-note sentence sits under the "Getting there" heading. That placement is a minor content-organization choice with no slop or quality consequence shown.
- **Scope.** I judged only the frozen bundle: one desktop state, no browsing, and no other repository folders opened. Status is `completed` because every check that this profile and evidence permit was run. INT-01, INT-02, and SRC-01 are unassessed because the bundle has no interaction or source data.
