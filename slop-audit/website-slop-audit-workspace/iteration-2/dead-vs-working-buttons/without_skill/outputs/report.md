# Slop audit: air-quality page (`fx-buttons-working-broken`)

**Profile:** multimodal-core (my interpretation is in "Choices and assumptions" below)
**Input:** `bundle/` only. It holds manifest.json, bundle.lock.json, and the screenshots A01–A03 (states S01–S03, desktop 1280x800).
**Overall slop signal:** **moderate**, medium confidence. All of the signal comes from **function and content integrity**. None comes from surface style.

## Bottom line

The page looks plain and hand-made, and the copy is specific. The problems are elsewhere. One of the two recorded buttons does what it says. The other does nothing, and it is the button that delivers half of the page's stated purpose (comparing with last year). The method note also does not support the page's default reading. These are AI-slop features, not proof of AI authorship. Dead buttons and loose labels are common in hand-built projects too.

## Button verdicts

| Control | Event | Verdict | Evidence |
|---|---|---|---|
| Show PM2.5 (`#show-pm25`, D007) | E01 | **Working** | `#metric` changes from "Ozone: 41 ppb (8-hour average)" to "PM2.5: 14.2 µg/m³ (monthly mean)" (T007 → T014). A02 differs from A01 only on that line (pixel diff: y 223–244 px). |
| Compare with last year (`#compare-last-year`, D008) | E02 | **Dead** | The click completed. The capture reports no text change and no DOM-state change (aria/input) within 1200 ms. **A03 is byte-identical to A01** (same SHA-256, zero pixel differences). The run started from a fresh load (S01), so E01 cannot explain it. |
| Download CSV (`#download-csv`, D009) | none | **Untested** | Links were not followed during capture. Its href was not captured. I did not count it as dead or as working. |

The dead button is styled exactly like the working one: same green text, white background, 4px radius, opacity 1. Nothing marks it as disabled, loading, or "coming soon". A user has no way to tell the two apart before clicking.

## Features found

**Present**

1. **MC-01 Dead control presented as functional.** High severity, high confidence. This is "Compare with last year" (see the table above).
2. **MC-02 Stated purpose not delivered.** High severity, high confidence. The purpose is to "...compare them with the previous year", and the helper text says "Select a pollutant or a comparison above." No prior-year value appears in any state. The page is called a dashboard but has one number and no chart or table. *This has the same root cause as MC-01. Treat the two as one problem, not two independent signals.*
3. **MC-03 Inconsistent data and method claims.** Medium severity, medium confidence.
   - The method note (T009) names PurpleAir PA-II sensors with the EPA 2021 correction. Both are about particulate matter. But the default reading is ozone in ppb (T007), and no ozone source is named. *(This relies on outside domain knowledge, not on anything in the bundle.)*
   - The panel heading "Current reading" (T006) sits over an "8-hour average" and a "monthly mean". The subtitle says the data is "averaged over September 2026", and the capture date is November 2026.
   - The two pollutants use different averaging periods, and nothing explains why.
4. **MC-04 Missing state feedback.** Low severity, medium confidence. After "Show PM2.5" works, the button shows no active style (D015 has the same style as D007). The helper line stays the same after a selection. The dead button gives no feedback at all.

**Absent (counter-evidence)**

- **MC-05 Generic or filler copy.** None found. The text is short, literal, and specific (twelve sensors, a named neighborhood, sensor model, correction formula, aggregation method, correct units).
- **MC-06 Template AI aesthetic.** None found. No gradients, shadows, gradient text, glassmorphism, purple/indigo palette, or emoji. Radii are 0–6px, the font is Verdana, and the palette is a muted green.
- **MC-07 Decorative motion.** None found in the computed styles (no animations, 0s transitions). Playback itself was not recorded.
- **MC-08 Boilerplate sections.** None found. There is no hero, feature grid, CTA, or testimonials. The page has four plain regions (R01–R04).

**Not assessable**

- **MC-09 Chart quality.** The page has no chart to judge.
- **MC-10 Download CSV.** The capture did not exercise it.

## Integrity checks

- The SHA-256 of A01, A02, and A03 matches both the manifest and bundle.lock.json.
- A01 and A03 are identical. That is the strongest evidence that the comparison button is dead.
- All rendered content sits in rows 38–335 of the 800 px viewport. Any visible change after E02 would have been on screen.
- I did not recompute `bundle_hash`, because the bundle does not say how it is computed.

## Choices and assumptions

- **No schema or profile definition was available** inside the bundle, and I was told not to open other folders. I designed the `audit.json` structure myself. I read "multimodal-core" as: core slop features judged from screenshots, DOM text, computed styles, and interactions together, with source code excluded. Each feature cites bundle IDs and is marked present, absent, or not_assessable.
- **What "dead" means here:** the click completed, and there was no text change, no DOM-state change, and no pixel change. I report untested controls as not_assessable, never as failures.
- **Other explanations for the dead button** that I could not rule out: the comparison loads after the 1200 ms window, or a JS error stops the handler (console logs were not captured). Either is possible, but the result for a visitor is the same.
- I used **outside domain knowledge** once, in MC-03 (PurpleAir PA-II sensors measure particulates, not ozone). It is flagged there.
- I made **no authorship claim**. Blinding withholds the generator and award fields, and the context fields are synthetic.
- The pixel diffs used a small pure-Python PNG decoder, because PIL was not installed. The diff ran in a scratch directory and wrote nothing to the bundle.

## Limitations

The capture covers one route, one desktop viewport, and scroll offset 0. It has no mobile view, console or network logs, source code, hidden elements, alt text, or pseudo-elements. Animation playback was not recorded.
