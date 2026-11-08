# Perceived AI-slop audit: fx-catalog-conventional

**Page:** municipal open-data catalog, `/index.html`, desktop 1280x800 (one screenshot, A01)
**Profile:** multimodal-core (screenshot + text + DOM + computed style)
**Result:** no perceived AI-slop findings. Confidence is moderate.

## What the page is

The page is the City of Riverton open-data catalog for climate and environment datasets. It has a solid dark-blue header, a two-sentence intro, a 3x3 grid of dataset cards (Format / Size / Updated), and a one-line footer. The stated purpose is to let residents and researchers check each dataset's format, size, and update date before downloading.

## Verdict

The page shows none of the common perceived-AI-slop cues:

- **Typography and styling:** All 71 captured elements use Arial. None has a gradient, box shadow, gradient text, letter-spaced uppercase label, or animation. The palette is greys plus one muted accent, rgb(29,79,110).
- **Copy:** The text is plain and checkable. "Nine" datasets matches the nine cards, and the intro names the issuing office and the license version. There is no hype, filler, or emoji. The intro's one three-item list names the three card fields; it is not decoration.
- **Data:** The values vary and fit their datasets. Sizes run from 41 KB to 140 MB. Spatial layers use GeoJSON or Shapefile, sensor data uses Parquet, and tables use CSV or XLSX. Dates are ISO and spread over five months.

## The one candidate worth discussing: the identical card grid

A grid of nine identical cards is a common "templated" cue, so it was examined closely. **I discounted it rather than reporting it** for three reasons:

1. Every record has the same three fields, so identical cards are the clearest way to compare them, and comparison is the page's stated purpose.
2. A provided constraint says City Web Style Guide section 4.2 *requires* the standard catalog card component. The visible footer says the same thing.
3. The cards are bare. They have no icons, badges, CTA buttons, taglines, or imagery, which are the extras that usually make a card grid read as generated.

The cards have small (about 4px) rounded corners and a hairline border with no shadow. That is restrained and was not reported either.

The other candidates that were checked and not reported (placeholder-looking `.example` email domain, empty space below a short page, data plausibility) are listed with evidence in `audit.json` under `candidates_considered`.

## Note for the study

The footer email uses the reserved `.example` domain (`opendata@riverton.example`). This is most likely an artifact of the synthetic fixture. Human judges might still read it as "unfinished template," so consider whether fixtures like this need realistic-looking placeholder details to avoid biasing ratings.

## Limits

- One route, one desktop viewport, one screenshot. There is no mobile layout, no hover or focus states, and no motion playback.
- Alt text, hidden elements, HTML comments, and source were not captured.
- The card containers (`article` elements) and `body` have no computed-style records. Card radius, border, and page background were read from the screenshot only.
- Elements in uncaptured states or routes could change the result. Within the captured state, the no-finding result is well supported.

## Choices I made (no questions were asked)

- **Profile meaning:** The bundle does not define "multimodal-core." I read it as: judge from screenshot, text, DOM, and computed styles together, and require a visible cue for any finding. Interaction and source evidence are out of scope, and they were not captured anyway.
- **Perception, not provenance:** The audit rates what a viewer might perceive as AI slop. It makes no claim about whether AI built the page. The blinded fields (award, course_year, creator_ai_report, generator) were not consulted, and I made no attempt to recover the withheld locator.
- **Context trusted:** I took the context fields marked "provided" as true, including the style-guide constraint.
- **Discounting rule:** A pattern that the content or an explicit constraint explains was discounted, not reported.
- **Schema:** No audit schema was supplied, so `audit.json` uses a structure defined for this audit (`ad-hoc/perceived-slop-audit/0.1`).
- **Integrity:** The screenshot's sha256 matches the lock file. The declared `bundle_hash` could not be reproduced because its recipe is not documented, so it is recorded as declared.
