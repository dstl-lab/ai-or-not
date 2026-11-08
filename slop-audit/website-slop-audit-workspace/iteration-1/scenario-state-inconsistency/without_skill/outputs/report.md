# Audit report: sea-level-rise data story (fx-scenario-inconsistency)

**Profile:** multimodal-datastory
**Bundle:** `fx-scenario-inconsistency`, frozen 2026-11-07T22:45:19Z, one route (`/index.html`)
**Verdict:** needs fixes. There is 1 high-severity issue, 2 medium and 4 low.
**Machine-readable version:** `audit.json`, in the same folder.

## Bottom line

The page is a clean, well-sourced, one-chart data story. Its bars use a fixed linear scale, so bar lengths can be compared honestly across years. Its main interaction is only partly wired, though. Clicking **2050** updates the chart title and the bars, but the "What this means" summary directly below still describes **2020**. That conflicts with the page's stated purpose of comparing scenario years. A second likely defect is that the bars disappear entirely at phone width.

## Findings

### F01: The summary stays on 2020 after 2050 is selected (high severity, high confidence, confirmed)

After the recorded click E01 on `button[data-year="2050"]`, the after-click screenshot A04 shows this:

| Element | Before (S01 / A01) | After 2050 click (S03 / A04) |
|---|---|---|
| Chart title `#chart-title` | Parcels in the flood zone, **2020** | Parcels in the flood zone, **2050** |
| Mission Beach | 12% | **31%** |
| Imperial Beach | 9% | **27%** |
| La Jolla Shores | 4% | **11%** |
| Summary `#summary` | "In 2020, 4% … 12% … 9%." | **unchanged**: "In 2020, 4% … 12% … 9%." |

Three sources of evidence agree:
- **Interaction log:** E01's `observed_changes` lists the three values, the title and the button state. Nothing changed in `#summary`.
- **Text spans:** T015 (before) and T030 (after) are character-identical.
- **Pixels:** a full diff of A01 against A04 shows changes only in the button row, the year in the title and the bar/value rows. The summary and method panels are pixel-identical.

The sentence does say "In 2020", so it is stale rather than false. But it sits under a "What this means" heading directly below a chart that now shows 2050. A resident who follows the narrative sees numbers 2.5 to 3 times lower than the chart (12 vs 31, 9 vs 27, 4 vs 11), which understates the projected risk.

**Fix:** drive `#summary` from the same selected-year state as the title and bars. If the 2020 sentence is a deliberate baseline, label it "Baseline (2020)" and add a sentence that changes with the selected year.

### F02: Bars are missing at the mobile viewport (medium severity, medium confidence, likely defect)

In both mobile screenshots (A02 and A03, 390x844 at DPR 2), the chart is only labels and percentages. A pixel scan of the chart rows found zero pixels of the bar color (rgb(31,111,139)). The strip between the label column and the value column is pure white. On desktop, the same rows carry clear bars. So on a phone, which residents are likely to use, the page has no visual encoding and nothing to compare by bar length. The bundle has no mobile DOM or computed-style capture and does not include the bar elements, so it cannot show whether the bars were hidden on purpose or collapsed to zero width. Nothing on the page signals an intended table-only view, so I treat it as a likely defect.

### F03: "What this means" only restates the numbers (medium severity, medium confidence)

The paragraph repeats the three values printed beside the bars. It adds no change over time, no comparison and no takeaway for residents, even though the stated purpose is comparison across scenario years. The page also shows one year at a time with no delta or annotation, so readers have to remember the previous values while toggling. This combines with F01: the one place that could explain how flooding grows from 2020 to 2050 does neither.

### F04: The "scenario" wording does not match the controls or the source (low severity)

The headline says "under each sea-level scenario". The buttons are years, and the source note says all the numbers come from a single "intermediate-high scenario". Readers may take the years to be separate scenarios, or look for a scenario selector that does not exist.

### F05: Counts and shares are blurred (low severity)

The purpose, the method ("We counted parcels") and the chart title ("Parcels in the flood zone") all read as counts. The values are percentages with no denominator and no totals, so readers cannot judge scale across neighborhoods.

### F06: Desktop value labels sit far from their bars (low severity, high confidence)

The values are pinned near x≈1148 px, while the bars end between 286 and 526 px, leaving up to about 790 px of white gap in the 2020 view. No track or axis shows that the full width means 100%. Values at the bar ends, or a faint 0-100% track, would fix it.

### F07: Paragraph line-height is inconsistent on mobile (low severity, medium confidence)

Measured from line pitch, the summary is set at about 1.54 line-height, while the method paragraph is about 1.13, the subtitle about 1.18 and the source note about 1.15. Multi-line text outside the summary is cramped on phones.

## What works

- **Honest, stable scale.** Every bar starts at x=252. The bars measure 106, 80 and 35 px for 12, 9 and 4%, and 275, 239 and 97 px for 31, 27 and 11%. That is 8.75-8.89 px per percentage point in both states, so switching years does not rescale the axis.
- **Clear selected state.** The active button gets a filled style, its state attribute toggles, and the chart title follows the selection.
- **Sourcing and method are disclosed.** The page names the County Coastal Vulnerability Assessment (2024, intermediate-high scenario), the parcel-centroid method and the 2023 assessor roll.
- **Contrast passes WCAG AA.** The lowest measured pair is the 13px source note at 5.49:1. The bar fill against the panel is 5.67:1.
- **The data is internally plausible.** Every neighborhood's share rises from 2020 to 2050, and the ranking is the same in both years.
- **The styling is restrained.** There are no gradients, text effects or animations, and there is one accent color. The white-card, pill-button look is generic, but I did not count it as a defect.

## Coverage and limits

- The **2100** button was not exercised, so F01 is shown for 2050 only. The 2100 view very likely has the same problem, but that is not proven.
- No after-click state was captured on mobile.
- No source code was captured, so the causes of F01 and F02 are inferred from behavior.
- The bar elements are not in the DOM capture, so bar geometry comes from pixels. Line-height is not a captured style property, so F07 is estimated from pixels.
- Alt text, ARIA labels and hidden elements are not captured, so chart accessibility beyond contrast (for example, what a screen reader announces) was not assessed.
- The capture observes the page 800 ms after the click. A later asynchronous summary update would be missed, but nothing suggests one.

## Choices made for this run

1. **No skill and no external schema were used.** I read "multimodal-datastory" as cross-checking every captured modality (screenshots, text spans, computed styles and the interaction log) against each other. The 12 checks are listed in `audit.json` under `profile.checks`. The `audit.json` structure was designed for this run, not taken from a published schema.
2. **Severity scale.** *High* means a reader doing the page's core task would come away with wrong or contradictory information. *Medium* means a core part of the experience is degraded. *Low* means clarity or polish.
3. **Confidence** reflects how directly the bundle proves the issue. F02 is "medium" because the missing bars are certain from pixels, but whether they were removed on purpose cannot be determined.
4. **Blinding respected.** No authorship inference was made. The "slop signals" section of `audit.json` rates signs of unreviewed work, not who or what made the page.
5. **Integrity.** All four asset SHA-256 hashes match `bundle.lock.json` and the manifest. The lock's `bundle_hash` was not recomputed because the bundle does not say how it is derived.
6. **Measurements** (bar lengths, the before/after pixel diff, mobile bar-pixel scan, line pitch, contrast) were made with a small pure-Python PNG decoder, because no imaging library was installed. Those helper scripts were kept out of the outputs folder.
7. Only the input bundle was read. No other repository folder and no web resources were consulted.
8. **Harness note.** The harness blocked me from writing this file, so its text was returned to the caller to save as `report.md`.
