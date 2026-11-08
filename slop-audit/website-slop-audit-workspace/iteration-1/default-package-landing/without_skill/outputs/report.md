# Audit: fx-default-package-landing (multimodal-datastory profile)

**Verdict: your read is right.** Every one of the six captured sections follows a SaaS landing-page template. The data story itself is one unlabeled five-bar chart with a two-word caption. It sits fifth of six sections, two-thirds of the way down the page.

| Axis | Rating |
|---|---|
| SaaS-template resemblance | **High**: 12 markers (9 strong), present in 6 of 6 regions |
| Data-story fulfilment | **Low**: 1 chart, 0 labels, 0 mentions of Seattle, no source, no narrative |
| AI generation | **Not assessed**: provenance fields are blinded, and a template look is not evidence of AI authorship (see C03) |

Machine-readable results are in `audit.json`. Each finding there carries resolved boxes for every text span and region it cites.

## How to read the locations

- **Region** IDs and **selectors** come from the manifest (R01 `#hero` to R06 `#final-cta`).
- **Box** = `[x, y, w, h]` in image pixels of the named screenshot. A01–A04 are desktop at DPR 1, so pixels equal CSS px. A05 and A06 are mobile at DPR 2, so divide by 2 for CSS px.
- **Page y** = vertical position on the desktop page in CSS px. The full-page shot A04 is 1775px tall.
- A01 shows page y 0–800, A02 shows 800–1600, A03 shows 975–1775, and A04 is the whole page (overview only; read fine text from A01–A03).

## SaaS-template features and where they are

| ID | Feature | Where | Key evidence | Signal |
|---|---|---|---|---|
| F01 | Product-launch eyebrow "✨ INTRODUCING LIBRARYPULSE" | R01, `#hero > p:nth-of-type(1)` (T001/D007); A01 box [64,72,720,29], page y 72–101; also A05 top | uppercase, 19px, letter-spacing 4.18px (0.22em); invented product name | strong |
| F02 | Formula headline "Unlock the future of library insights" with **"future" in gradient text** | R01, `#hero > h1` (T002/D008); A01 [64,127,900,118]; gradient word at A01 [368,137,156,40] | 56px/700; glyph pixels run from rgb(166,139,250) to rgb(98,164,250), which matches Tailwind violet-400 → blue-400 (approximate, from pixels; the inner element is not in the DOM capture) | strong |
| F03 | Buzzword subhead ("Our platform empowers you… unlock powerful insights… Reimagine what's possible with next-generation analytics") | R01, `#hero > p:nth-of-type(2)` (T003/D009); A01 [64,263,720,46], page y 263–309 | names no dataset, place, period or finding | strong |
| F04 | Glowing gradient pill CTAs with arrows: "Get started →" at the top and "Start exploring →" at the bottom | `#hero > a` (T004/D010), A01 [64,335,145,43]; `#final-cta > a` (T033/D039), A03 [555,685,169,43], page y 1660–1703 | `linear-gradient(90deg, #7c3aed, #3b82f6)`, radius 12px, `box-shadow: 0 0 24px rgba(124,58,237,.6)`; link targets not captured | strong |
| F05 | Vanity stat strip: "10x Faster insights / 99% Accuracy / 24/7 Always-on analytics" | R02 `#stats`; A01 [0,434,1280,145], page y 434–579; numbers at A01 x 87 / 478 / 868, y 457 | marketing claims with no referent and nothing from the dataset; these are the only non-section numerals on the page | strong |
| F06 | "Everything you need, nothing you don't" over three feature cards with **the same ✨ icon** in gradient tiles ("Seamless Data", "Powerful Insights", "Team Credits") | R03 `#features`; heading T013 at A01 [64,659,1152,37]; icon tiles D020/D023/D026 at A01 y 736, x 87 / 477 / 867; card glow at A02 [64,86,1152,24] | tiles use `linear-gradient(135deg, #7c3aed, #3b82f6)` with radius 12px; one emoji used for all three suggests placeholders left in; the credit line is crammed into a feature slot | strong |
| F07 | Doubled section eyebrows: mono "01 / FEATURES", "02 / FAQ", "03 / DATA" over uppercase kickers "WHY IT MATTERS", "QUESTIONS", "THE DATA" | `#features > span`/`> p` (A01 y 618–647), `#faq > span`/`> p` (A02 y 160–190), `#chart-section > span`/`> p` (A02 y 422–451) | SF Mono 13px in #818cf8, then 12px uppercase 0.22em in #a5b4fc; the same three-line header repeats on every section | moderate |
| F08 | Product FAQ accordion: "Frequently asked questions" with "What is LibraryPulse?" and "Who is it for?" | R04 `#faq`; A02 [0,122,1280,261], page y 922–1183; summaries D032/D033 | `details > summary`; answers collapsed and not captured; the FAQ comes *before* the data | strong |
| F09 | Closing conversion band "Ready to transform your data journey?" + CTA | R06 `#final-cta`; T032 at A03 [64,636,1152,29], page y 1611–1640 | centered 24px/700 rhetorical question; ends on a sales pitch rather than a takeaway or sources | strong |
| F10 | Dark "AI startup" theme in framework-default colours | R01 background (D001), A01 [0,0,1280,434]; whole page | bg rgb(11,11,20); radial glows `rgba(124,58,237,.45)` at 30% 20% and `rgba(59,130,246,.35)` at 80% 0%; every accent is an exact Tailwind default (violet-600, blue-500, indigo-400, indigo-300, indigo-500 on the bars); Inter-first font stack | moderate |
| F11 | SaaS landing section order (hero → stats → features → FAQ → **data** → CTA) | all regions in A04; chart section R05 at page y 1183–1544 | chart section takes 20% of page height and 8.5% of visible words (9 of 106); no data in the first desktop viewport or in either mobile viewport | strong |
| F12 | Recycled benefit words | T002, T003, T006, T018, T019, T015/T016, T032 | in 106 visible words: "insights" ×5, "unlock" ×3, "powerful" ×3, "seamless" ×2, "transform" ×2 | moderate |

## Where it falls short as a data story

| ID | Gap | Where | Evidence |
|---|---|---|---|
| G01 | **The one chart has no axes, labels, values, units, time periods or source**, and about 84% of its box is empty | R05 `#chart-section`; container A02 [64,518,1152,146] (page y 1318–1464); bars A02 [77,543,180,108] | 5 bars, 28px wide with 10px gaps, heights 108/102/30/72/96px, all #6366f1; no text spans inside the box; no svg or canvas in the DOM capture; caption "Visits trend." (T031) states no finding |
| G02 | No narrative and no numbers from the data | whole page | "Seattle" appears 0 times and "library" once (H1). The only digits are F05's stats and the section numbers |
| G03 | No source, method or named authors | R03 third card (T021/T022) | credit reads "Built by four passionate students who love data." No names, course, dataset or link |
| G04 | "Interactive" (from the stated genre) cannot be observed | R05 | interaction modality is false and the interactions list is empty; no controls are visible on the chart. Recorded as *not observable*, not as absent |
| G05 | Copy addresses a buyer, not instructors and classmates | T003, T027, T032 | "Our platform empowers you", "Who is it for?", "Ready to transform your data journey?" |

## Craft defect (weak counter-signal)

**Q01: mobile card rows don't reflow.** At 390px the stat strip and the feature grid stay three-across, and the third card is cut off at the right edge:

- Stats: A05 [648,1332,132,245], CSS x 324→390+.
- Features: A06 [702,388,78,570], CSS x 351→390+.

The text column ends at CSS x 326, and feature-card text wraps to 1–3 words per line. A single screenshot can't show whether this is overflow or an unmarked horizontal scroller. Commercial templates usually stack these rows on mobile, so this points to a desktop-only or partly adapted build rather than a stock template used untouched.

## Counter-evidence and caveats

- **C01:** "Built by four passionate students" is a real course trace, consistent with the stated context.
- **C02:** The bars are uneven, with a sharp dip at bar 3, so the chart probably encodes real values. It just can't be read.
- **C03:** Template look ≠ AI. Every marker above is just as typical of hand-picked landing kits (Tailwind UI or shadcn-style starters, site builders) as of generated pages. `generator` and `creator_ai_report` are withheld, and this audit makes no provenance claim.
- **C04:** `transition-property: all` on every element is the CSS initial value, and `animation-name` is `none` everywhere. Neither was scored. Motion was not assessed.

## Capture coverage and limitations

- **Integrity:** all six PNGs match the SHA-256 values in both the manifest and the lock file. `bundle_hash` was not recomputed because its algorithm isn't specified, and `manifest.json` isn't listed in the lock.
- **No interaction pair:** 6 of a possible 8 images were captured. FAQ answers and any chart interactivity are therefore unseen, so G02/G03 cover only visible captured text (alt text, comments and hidden elements are outside the capture).
- **Mobile findings rest on pixels:** text spans and DOM styles exist only for the desktop state, so mobile observations come from region boxes plus pixel measurement.
- **Some styles rest on pixels:** card wrappers, the chart container and the bars are not in `dom_elements`, so their fill, border, glow and size were measured from the PNGs. The same goes for the gradient on "future".
- **Fonts:** the declared stack is Inter first. Computed style can't confirm whether Inter or a fallback rendered.
- **Possible label leakage:** `bundle_id` and `site_id` contain "default-package-landing", which hints at the expected answer, yet `blinding.known_leakage` is empty. I did not use the name as evidence. You may want to rename the fixture before giving it to blinded raters.
- **Synthetic context:** the context fields say "capture plan written by the fixture author (synthetic)". The page may be a constructed test fixture rather than a submitted student project.

## Choices I made (no questions asked)

1. **Profile definition:** the "multimodal-datastory" profile wasn't in the bundle, and I was not to use skills or open other folders. I interpreted it as two rules:
   - Every finding cites captured evidence and names the modalities it used (text spans, DOM/computed style, screenshot pixels).
   - Features are judged against what a data story needs: a question, labelled data, narrative, sourcing and audience fit. A SaaS marker counts most where it pushes out data-story content.
2. **Schema:** no official `audit.json` schema was available, so the file uses its own structure, described in its `schema_note`.
3. **Ratings:** each finding is rated on three separate axes: signal strength, confidence in the observation, and impact on the data story. I computed no single score, because there is no calibrated rubric.
4. **Scope:** I scoped the audit to template resemblance, as you asked, not to whether AI built the page.
5. **Colour matches:** Tailwind matches are stated as exact only for CSS values from the capture. Matches derived from pixels are marked approximate.
6. **Pixel measurement:** I decoded the PNGs with a small pure-Python reader (no image library was installed) to measure the chart, the gradient word, the card glow and the mobile clipping.
