# Mirrored-site validation for PR #4

Validated on October 25, 2026 (America/Los_Angeles), using desktop Chrome
155.0.8059.85, the actual frozen websites, and disposable practice sessions in a
separate SQLite database. All ten mirror directories match the active site list and
their pinned commit markers. No participant records or frozen website files changed.

## Common checks: 10 of 10 passed

Every website rendered and passed real pointer selection, overlapping-layer changes
without losing the draft note, saving all ten CSS properties, API readback, full-page
reload of the saved note, and ordinary website click delivery beneath passive highlights.
Additional checks below exercised actual controls and navigation where applicable.

| Website | Additional checks after fixes |
|---|---|
| Breathing Smoke | Canvas-area selection, save, and restored pointer interaction |
| Five Minute Fire | Enlarged-photo selection excludes the covered thumbnail; map canvas-area selection and restored gestures |
| Strike or Ball | Common checks above; supplementary Safari save/reload check |
| Climate Response | Canvas area; thin quadrant-chart SVG axis selected and saved with its visible stroke bounds |
| Where Droughts Hide | Canvas area; carousel hides a saved target, clears the highlight and shows guidance; returning to its slide restores the highlight |
| From Rain to Ruins | Explore → visualization 1; chart canvas-area note; month slider 0 → 11; Next to visualization 2; recalling the note returns to visualization 1 with unchanged saved data |
| Greening Earth | Start Exploring and Skip Tour; rendered WebGL map area selected and saved; map gestures restored |
| SD Climate Twin | Visible fingerprint-panel SVG whisker selected and saved with positive-width bounds |
| Greening Momentum | Rendered heatmap area; game page navigation, working answer reveal, return home, and saved game-note recovery |
| Storm Futures | All five chapters select their titled embedded frames by default, save frame metadata, and restore child-frame interaction; anomaly-map canvases painted after loading |

The seven sites with tested top-level canvases include From Rain to Ruins' internal
visualization page. Storm Futures' charts are selected as whole embedded frames;
their internal chart state is not recorded.

## Regressions fixed

1. Nested-frame chart clicks never reached the annotation tool. Frames now temporarily
   pass pointer input to the outer page while selecting, and remain available as titled
   layer choices. Removing the temporary selection rules restores normal interaction.
2. The lightbox picker could select an obscured thumbnail behind the dialog. Choices
   are now confined to the active dialog's contents.
3. Carousel notes could retain an offscreen highlight without explaining why the target
   disappeared. Highlight tracking and selection now respect hidden/clipped ancestors.
4. Horizontal and vertical SVG lines had zero geometric width or height and were
   rejected despite their visible strokes. Selection, capture, and highlights now use
   stroke-aware bounds, including SVG scaling and non-scaling strokes.

Each case has a regression test. The full suite passes **221 tests**, with one existing
Starlette/httpx deprecation warning. All JavaScript syntax checks and `git diff --check`
pass. Independent review found no blocking issue in these fixes.

## Existing source-site warnings

These warnings are present in the pinned originals. The study copies retain them so
the project versions recorded with participants' answers remain accurate.

- **From Rain to Ruins:** the [pinned stylesheet](https://github.com/iskabell/From-Rain-To-Ruins/blob/6d342824021fd24d87c0a68d1542db99dd2587e7/style.css#L133)
  requests `images/c3.svg`, but that revision contains `images/c3.png` instead. One
  decorative cloud layer is missing; the tested visualizations and navigation work.
- **Greening Momentum:** the [pinned HTML](https://github.com/JaredW022/drying-out-atlas/blob/85b4fb5becf4b6520516b2b85daa2e0a3bff2e7d/index.html)
  references absent `css/homepage-interactives.css` and `js/homepage-interactives.js`.
  The existing `main.js` still renders the heatmap after loading its monthly data;
  initial loading can be slow because it preloads roughly 802 MB. The game also emits
  an SVG `height="auto"` warning; its map, answer reveal, and navigation worked.
- Some video requests were aborted during page navigation. These were distinguished
  from missing resources and JavaScript exceptions.

## Repeating the smoke check

Use a separate data directory and practice sessions. Complete the initial ratings,
then test notes on each site during its final-question stage. Save a note, switch
layers before saving a second note, reload the study, and use the original website's
controls. For the cases above, also exercise the lightbox, carousel, thin SVG line,
embedded chart, and internal-page note recovery. Wait for data-heavy charts to render
before testing them. Run `uv run pytest` after changing shared annotation code.

This is representative integration coverage, not an audit of every visualization or
external video. Native Safari checks covered four sites, but the full ten-site sweep
used Chrome. Live Google Sheet writes and physical touch devices were not tested.
