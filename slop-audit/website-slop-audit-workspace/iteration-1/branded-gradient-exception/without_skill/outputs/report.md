# Slop audit: Sunrise Fest 2027 (`fx-branded-gradient`)

**Verdict: low slop (0.1 on a 0–1 ordinal scale), medium confidence.**
The page does not read as AI-generated slop. Its one well-known AI tell is a headline filled with a gradient clipped to the text. A documented brand rule requires that gradient, and the page uses it only where the rule says, so it is exempted rather than counted. Nothing else on the page matches the usual template-style AI patterns. The real problems are craft and accessibility issues, listed separately below.

| | Count |
|---|---|
| Counted slop findings | 0 |
| Exempted signals | 1 (gradient headline) |
| Editorial observations (not counted) | 1 |
| Craft / accessibility notes (not slop) | 2 |

## What was audited
- **Bundle:** `fx-branded-gradient`, site `site-branded-gradient`, route `/index.html`, state S01, desktop viewport V1 (1280×800).
- **Evidence:** one viewport screenshot (A01), three regions (R01 headline, R02 lineup, R03 visitor details), nine DOM text spans (T001–T009), and twelve DOM elements with computed styles (D001–D012).
- **Integrity:** the SHA-256 of `assets/A01.png` matches the manifest and lock file. The bundle-level hash could not be reproduced because its recipe is not documented, so it is recorded as unverified. This is not suspicious, since the only file matched.
- **Context used:** purpose (announce a three-day festival: lineup, dates, travel), genre (event promotion), audience (local festival-goers), and one provided constraint: *the brand guide requires the orange-to-pink sunrise gradient on the wordmark and main headline.*
- **Blinding:** respected. No attempt was made to recover the withheld fields (award, course year, creator AI report, generator) or the target URL.

## The gradient headline: exempted
**Signal:** the `h1` "Sunrise Fest 2027" (D004) has `background-image: linear-gradient(90deg, rgb(255,138,0), rgb(255,45,111))`, `background-clip: text` and transparent text color, at 72px, weight 800, letter-spacing −1px. Gradient-clipped display text is one of the most common visual tells on generated landing pages.

**Why it is not counted:**
1. **A constraint requires it.** The capture plan states that the brand guide requires this gradient on the wordmark and main headline. That constraint is the basis for the exemption.
2. **It stays within what the constraint names.** Of the 12 captured elements, only the `h1` has a background image. Section headers, list items, the body text and the backgrounds use none. A generated page usually spreads gradients across buttons, badges, section titles and backgrounds.
3. **It uses the colors the constraint names.** The stops are warm orange and pink, as the brand describes, not the purple, indigo or blue gradient typical of generated templates.
4. **Supporting evidence only:** the page copy (T009) also says the gradient has been part of the festival's identity since 2019. I did not rely on this sentence alone, because a page can say anything about itself. It agrees with the provided constraint.

If the gradient had shown up anywhere the constraint doesn't cover, or in different colors, those uses would have been counted.

## Signals checked and not found
| ID | Signal | Result | Evidence |
|---|---|---|---|
| V02 | Default AI palette (purple, indigo or blue) | Absent | Text rgb(43,29,20) warm brown on cream rgb(255,250,243); orange accents only |
| V03 | Rounded cards, soft shadows, bento or feature grids | Absent | `border-radius: 0px`, `box-shadow: none` on all elements; single column |
| V04 | Decorative background gradients, glass effects, blobs | Absent | Sections transparent, `background-image: none`; flat cream background |
| V05 | Emoji or icon bullets, icon rows, stock illustration | Absent | Plain numbered list with bold day labels; no images |
| V06 | Template hero with a CTA button pair | Absent | Left-aligned headline and one factual subhead; no buttons |
| V07 | Scroll or entrance animations | Absent (limited evidence) | `animation-name: none` everywhere. `transition-property: all` is the CSS default, not a declared transition |
| V08 | Generic modern-startup type stack | Absent | Trebuchet MS throughout, a dated choice rather than a generated default |
| C01 | Hype or filler copy | Absent | Copy is concrete: genres, venue, dates, gate time, station and walk time, price, child policy |
| C02 | Formulaic rhetoric (tricolons, em-dash asides, "not just X") | Absent | "folk, soul, and brass" lists real programming; the only dash is a correct en dash in "June 11–13" |
| C03 | Placeholder or uniform specifics | Absent | Lineup entries vary in form and count (3/3/2). Not checked against reality because the fixture is synthetic |
| S01 | Boilerplate section sequence (Features, Testimonials, FAQ, CTA) | Absent | Three sections map onto the stated purpose |
| S02 | Polish without substance | Absent | Everything the purpose calls for is present; decoration is limited to the brand gradient |

## Observation (not counted)
**C04. Meta copy explains the design.** Under "Getting there", T009 says the orange-to-pink gradient on the wordmark is part of the festival's identity and has been used on every poster since 2019. A visitor page rarely explains its own styling, and this line has nothing to do with directions. It reads a little like a design rationale aimed at a reviewer. But it is specific (2019, posters) and isn't one of the usual generated-copy patterns, so I recorded it as an editorial oddity with low confidence. If it's meant as brand heritage, it would sit better near the wordmark or in an "About" line than in the travel section.

## Craft and accessibility notes (not slop)
These don't affect the slop score, but they matter for the page.

**Q01. The pink end of the brand gradient never shows (low).** The gradient runs across the whole `h1` box, which is block-level and about 1184px wide, but the text covers only about 49% of it (ink from x=51 to x=628). In the screenshot, the headline goes from rgb(255,138,1) to about rgb(255,94,51), orange to red-orange. The pink stop rgb(255,45,111) falls in empty space to the right. So the page misses the "orange-to-pink" look its own brand guide asks for. *Fix:* size the `h1` to its text (`display: inline-block` or `width: fit-content`).

**Q02. The headline has low contrast (medium).** Against the cream background, the visible headline ranges from 2.28:1 (orange start) to about 2.93:1 (rightmost glyph). That is below the WCAG AA minimum of 3:1 for large text. Even the unseen pink stop would reach only 3.45:1. *Fix:* keep the hues but darken the stops, or put the wordmark on a darker field. Body text is fine at 15.69:1.

## Choices and assumptions
- **"multimodal-core" profile.** The bundle doesn't define this profile, and I was told not to open other folders or use skills. I took it to mean: judge the page on every modality the bundle captured (screenshot, DOM text, DOM elements, computed styles), check them against each other, and apply a core checklist of visual, copy and structural slop signals. Interaction and source evidence were not captured, so they weren't used.
- **Trust in the constraint.** The brand constraint has status "provided" in the manifest, so I treated it as reliable audit context. On-page text alone would not have been enough for an exemption.
- **Scope of the exemption.** It covers only the element the constraint names and only the colors it names.
- **Slop versus quality.** "Slop" here means generic, template-like, AI-default patterns. Contrast and brand-fidelity problems are real but reported separately and don't raise the score.
- **Pixel measurements.** Pillow isn't installed, so I decoded the PNG with a short standard-library Python script (zlib and struct) to sample colors and text extents. All coordinates are in screenshot pixels at DPR 1.
- **Output format.** No audit schema was supplied, so `audit.json` uses a structure I chose. It cites the bundle's own IDs (A, R, T, D) plus K1 for the constraint.

## Limitations
- There is one desktop viewport and no mobile capture, so responsive behavior is unknown.
- No interaction or animation playback was captured; motion was judged from computed styles only.
- HTML comments, alt text, hidden elements, `<title>` and meta tags were not captured.
- No page source was available, so markup or class-name fingerprints of a generator could not be checked.
- The captured page is short: content ends at y≈495 of 800, and the rest of the viewport is empty background. That leaves few signals to sample.
- The fixture is synthetic, so the acts, venue and station could not be checked against the real world.
