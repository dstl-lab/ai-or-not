# Slop-feature audit default-package-landing-mm-datastory-01

bundle `fx-default-package-landing` · profile `multimodal-datastory` · rubric 0.1.0 · status **completed**

## Scope and limits

The captured page, given as a student data story about Seattle library visits, is laid out as a stock product landing page: a launch-style hero with a 'Get started' button, a strip of unitless performance figures, three icon cards, an FAQ, a single chart, and a closing call to action. Across that skeleton the evidence shows a recurring purple-to-blue glow-on-dark palette, numbered eyebrow labels on every section, one sparkle badge on unrelated cards, and broad 'unlock / transform / seamless' copy that never names Seattle, the data, the period, or a finding. The one chart has no axes, labels, values, or source, and its caption is two words. These are features that can make the page read as template scaffolding with little data story inside it; they say nothing about who or what made the site, and each has benign explanations such as pitch framing chosen for class, an unrevised starter template, or work in progress. Limits: no interactions were recorded, so the buttons and FAQ disclosures are untested rather than broken; FAQ answers, alt text, and hidden content were not captured; only one route was captured, and the mobile screenshots cover the upper part of the page.

- Assessed modalities: screenshot, text, dom, computed_style
- Not assessed: interaction (the bundle records no interactions (modalities.interaction is false; interactions list is empty))
- Not assessed: source (no source excerpts were supplied)
- Limitation: No recorded interactions: the two link buttons and both FAQ disclosures are untested, so INT-01, INT-02, and DAT-02 are unassessed.
- Limitation: No source excerpts were supplied, so SRC-01 is unassessed.
- Limitation: FAQ answers, alt text, and hidden elements were not captured; specifics or chart framing could exist there.
- Limitation: One route only; mobile screenshots cover R01 to R04, show a sliver of R05, and do not reach R06.
- Limitation: Context (purpose, genre, audience) was written by the fixture author; no course, brand, or template constraints were supplied.
- Counts: 8 findings, 2 contextual exceptions, 1 quality observation, 0 exploratory candidates, 4 unassessed features

These findings identify features that may contribute to a perceived AI-slop impression; they do not establish who or what made the site.

## Findings

### F001 · LAY-02 Interchangeable page skeleton

- **What:** The single captured route follows the stock product-landing sequence, in DOM order: #hero (launch eyebrow, headline, 'Get started' button), #stats (three figure tiles), #features (three icon cards), #faq (product questions), #chart-section (the only data display), #final-cta ('Start exploring' button). For a data story about library visits, the one chart sits fifth of six sections and takes about a fifth of the full-page height (A04), after four sections that say nothing about the data.
- **Where (page-pattern):** R01 (opening section) · state S01 · image A04 with box · selector #hero; R02 (statistic strip) · state S01 · image A04 with box · selector #stats; R03 (feature cards) · state S01 · image A04 with box · selector #features; R04 (question list) · state S01 · image A04 with box · selector #faq; R05 (chart section) · state S01 · image A04 with box · selector #chart-section; R06 (closing section) · state S01 · image A04 with box · selector #final-cta
- **Evidence:**
  - `screenshot:A04` Full-page overview: the six sections in order, with the chart near the bottom.
  - `dom:D003` Captured section ids name template roles: #hero, #stats, #features (D003), #faq (D004), #chart-section, #final-cta (D006).
  - `text:T001` Launch-style eyebrow naming a product. "INTRODUCING LIBRARYPULSE"
  - `text:T004` Hero call-to-action link. "Get started →"
  - `text:T025` FAQ section heading. "Frequently asked questions"
  - `text:T030` The only data heading, in the fifth section. "Visits over time"
  - `text:T032` Closing call-to-action headline. "Ready to transform your data journey?"
  - `context:genre` Provided genre is an interactive data story (explorable explanation), not a product page.
- **Interpretation:** slop association strong (Six consecutive recorded regions match the stock hero, stats, features, FAQ, call-to-action sequence almost one to one, and the data display is placed late and small. Together these make the default-template reading especially compelling to an evaluator. The rating describes the pattern, not authorship.); fit inappropriate (The provided purpose is presenting Seattle library visit data to instructors and classmates; this structure is built to convert product visitors and pushes the data behind product framing.); consequence moderate (The reader reaches the only data display after four sections of product framing that never mention the data (cited spans), which makes the page's actual subject harder to find.)
- **Alternative explanations:** The team chose to pitch the project as a fictional product for class (not documented in the supplied context); A landing-page theme or starter template was reused as a starting point; A course rubric asking for a hook and a takeaway, interpreted as a hero and a call to action; Data sections still being built when the capture was made
- **Observation confidence:** high (All six sections are captured in DOM order with selectors and are visible in the full-page screenshot.) · evidence status `practitioner_heuristic`

### F002 · VIS-01 Default aesthetic package

- **What:** One palette package recurs across sections: a near-black page; purple and blue radial glows behind the hero (computed: rgba(124,58,237,0.45) and rgba(59,130,246,0.35)); both call-to-action buttons filled with a 90deg gradient from rgb(124,58,237) to rgb(59,130,246) plus a purple glow shadow; the same gradient on the card icon tiles; and dark rounded bordered panels for the stats, cards, and chart. No part of it refers to Seattle, libraries, or the visit data.
- **Where (page-pattern):** R01 (opening section) · state S01 · image A01 with box · selector #hero; R01 (opening section) · state S01 · image A01 with box · selector #hero > a; R02 (statistic strip) · state S01 · image A01 with box · selector #stats; R05 (chart section) · state S01 · image A02 with box · selector #chart-section; R06 (closing section) · state S01 · image A03 with box · selector #final-cta > a; R01 (opening section) · state S02 · image A05 with box
- **Evidence:**
  - `dom:D001` Hero background: two radial gradients, purple rgba(124,58,237,0.45) at 30% 20% and blue rgba(59,130,246,0.35) at 80% 0%.
  - `dom:D010` 'Get started' button: linear-gradient(90deg, rgb(124,58,237), rgb(59,130,246)), 12px radius, 24px purple glow shadow.
  - `dom:D039` 'Start exploring' button: the same gradient, radius, and glow.
  - `dom:D020` Card icon tile: linear-gradient(135deg) of the same two colors.
  - `screenshot:A04` Full-page overview: purple-blue glow at the top, then dark bordered panels in every later section.
  - `screenshot:A05` Mobile viewport shows the same glow, gradient button, and dark tiles.
  - `context:purpose` Provided purpose is Seattle library visit data from a student project; the constraints list is empty, so no brand or course palette is documented.
- **Interpretation:** slop association moderate (A recognizable purple-blue-glow-on-dark package recurs in at least four regions with no subject-specific choice. It is still a style package with many benign explanations, so it is not rated higher on its own.); fit questionable (No palette decision relates to the library data or the audience; with no documented requirement its role is unclear rather than demonstrably harmful.); consequence none_identified (Text and chart remain legible against the dark ground in the captured screenshots.)
- **Alternative explanations:** Designer or team preference for a dark theme; A course or team template with this palette (not documented in the supplied context); Theme default carried over from a starter kit or component library; Dark theme chosen for projecting in class
- **Observation confidence:** high (Colors come from measured computed styles, and the package is visible in desktop and mobile screenshots.) · evidence status `practitioner_heuristic`

### F003 · TXT-01 Interchangeable copy

- **What:** The opening, the feature cards, and the close use broad product-marketing copy that would fit any analytics product: the hero promises to 'unlock powerful insights' with 'next-generation analytics', the cards promise a 'seamless, intuitive experience' and 'meaningful outcomes', and the close asks about a 'data journey'. None of these spans names Seattle, a library, what a visit counts, the period, or a finding; 'library' in the headline is the only subject word. 'Unlock ... insights' recurs in three spans (TXT-02).
- **Where (repeated-group):** R01 (opening section) · state S01 · image A01 with box · selector #hero > h1; R01 (opening section) · state S01 · image A01 with box · selector #hero > p:nth-of-type(2); R03 (feature cards) · state S01 · image A01 with box · selector #features > h2; R03 (feature cards) · state S01 · image A02 with box · selector #features > div > div:nth-of-type(1) > p; R03 (feature cards) · state S01 · image A02 with box · selector #features > div > div:nth-of-type(2) > p; R06 (closing section) · state S01 · image A03 with box · selector #final-cta > h2
- **Evidence:**
  - `text:T003` Hero tagline; names no dataset, place, period, or finding. "Our platform empowers you to unlock powerful insights and transform the way you see data"
  - `text:T003` Second sentence of the tagline. "Reimagine what's possible with next-generation analytics."
  - `text:T002` Headline; 'library' is the only subject-specific word. "Unlock the future of library insights"
  - `text:T019` Card body repeating the hero's claim. "Unlock powerful insights that drive meaningful outcomes."
  - `text:T016` Card body with no content-specific information. "Effortlessly explore data with a seamless, intuitive experience."
  - `text:T013` Section heading that names no content. "Everything you need, nothing you don't"
  - `text:T032` Closing question with no data-specific payoff. "Ready to transform your data journey?"
  - `context:purpose` Provided purpose names Seattle library visit data; no captured text span names Seattle.
- **Interpretation:** slop association strong (Six spans across three regions use interchangeable unlock/transform/seamless claims, repeat one claim, and leave out every specific an introduction to this dataset needs. Several mutually supporting text observations make the template-copy reading especially compelling. The rating describes the copy, not authorship.); fit inappropriate (The page's job is to introduce library visit data to instructors and classmates; the copy describes a generic analytics 'platform' and works against saying what the project is about.); consequence moderate (From the opening and closing text a reader cannot learn the place, data, period, or finding (cited spans), and that information is not located elsewhere in the captured text.)
- **Alternative explanations:** Placeholder marketing copy written early and never revised; Deliberate pitch or parody framing for a class presentation (not documented); Writing in a product-style voice for a general audience; Specifics may sit in the collapsed FAQ answers, which were not captured
- **Observation confidence:** high (Exact text spans captured from the DOM and legible in the desktop screenshots.) · evidence status `practitioner_heuristic`

### F004 · SUB-03 Redundancy and metric theater

- **What:** The statistic strip shows three large figures, '10x' (Faster insights), '99%' (Accuracy), and '24/7' (Always-on analytics), with no unit, baseline, source, or link to the library visit data; they describe a product's performance, not anything in the dataset. SUB-01 sub-type: basis_not_located. Inspected scope: all captured text spans and screenshots of /index.html (FAQ answers, alt text, and hidden elements not captured).
- **Where (region):** R02 (statistic strip) · state S01 · image A01 with box · selector #stats > div:nth-of-type(1) > b; R02 (statistic strip) · state S01 · image A01 with box · selector #stats > div:nth-of-type(2) > b; R02 (statistic strip) · state S01 · image A01 with box · selector #stats > div:nth-of-type(3) > b; R02 (statistic strip) · state S02 · image A05 with box
- **Evidence:**
  - `text:T005` First figure. "10x"
  - `text:T006` Its label; faster than what is not stated. "Faster insights"
  - `text:T007` Second figure. "99%"
  - `text:T008` Its label; accuracy of what is not stated. "Accuracy"
  - `text:T009` Third figure. "24/7"
  - `text:T010` Its label; describes service availability, not data. "Always-on analytics"
  - `screenshot:A01` The three tiles directly under the hero, the most prominent numbers on the page.
  - `context:purpose` Provided purpose is presenting library visit data; none of the figures is a visit count, rate, or change.
- **Interpretation:** slop association moderate (Three unitless, unsourced performance figures in a data story fit the metric-theater pattern; a basis could still exist in uncaptured content, so the rating stays moderate.); fit inappropriate (Speed, accuracy, and availability figures for an analytics product do not summarize library visits and work against the provided purpose.); consequence moderate (The most prominent numbers cannot be interpreted: '10x' faster than what, '99%' accuracy of what (cited spans).)
- **Alternative explanations:** Landing-page template figures left in as filler; Intended as a joke or pitch framing for class; A course hook requirement met with placeholder figures; A basis outside the captured page, for example in the collapsed FAQ or another route
- **Observation confidence:** high (All six text spans are captured from the DOM and legible in A01.) · evidence status `research_hypothesis`

### F005 · VIS-02 Mechanical typographic and section chrome

- **What:** Each content section carries the same two-line chrome above its heading: a monospaced indigo number label ('01 / FEATURES', '02 / FAQ', '03 / DATA') and a tracked uppercase eyebrow ('WHY IT MATTERS', 'QUESTIONS', 'THE DATA'). The numbers mark no sequence a reader must follow (the FAQ precedes the data; hero and close are unnumbered), and the eyebrows restate the heading or the number label. The hero adds a tracked uppercase 'INTRODUCING' eyebrow and one gradient headline word, 'future'.
- **Where (repeated-group):** R03 (feature cards) · state S01 · image A01 with box · selector #features > span; R04 (question list) · state S01 · image A02 with box · selector #faq > span; R05 (chart section) · state S01 · image A02 with box · selector #chart-section > span; R01 (opening section) · state S01 · image A01 with box · selector #hero > p:nth-of-type(1); R01 (opening section) · state S01 · image A01 with box · selector #hero > h1; R03 (feature cards) · state S02 · image A06 with box; R04 (question list) · state S02 · image A06 with box
- **Evidence:**
  - `text:T011` Number label over the features section. "01 / FEATURES"
  - `text:T023` Number label over the FAQ section. "02 / FAQ"
  - `text:T028` Number label over the data section. "03 / DATA"
  - `dom:D017` Number label style: 'SF Mono', Menlo, monospace, 13px, rgb(129,140,248); D029 and D034 are identical.
  - `text:T024` Eyebrow restating its heading 'Frequently asked questions' (T025). "QUESTIONS"
  - `text:T029` Eyebrow repeating its own number label '03 / DATA'. "THE DATA"
  - `dom:D018` Eyebrow style: 12px, uppercase, 2.64px letter-spacing, rgb(165,180,252); D030 and D035 are identical.
  - `text:T001` Hero eyebrow, uppercase with 4.18px letter-spacing (D007). "INTRODUCING LIBRARYPULSE"
  - `screenshot:A01` The headline word 'future' is rendered in a purple-to-blue gradient; the other headline words are plain light text.
- **Interpretation:** slop association moderate (A recurring decorative label system carrying no structural information fits the pattern; numbered, eyebrowed sections are also a common editorial style, so it is not rated strong.); fit questionable (No captured navigation uses the numbers, and the eyebrows repeat the headings, so the labels' role is unclear rather than harmful.); consequence minor (Redundant labels add noise above each heading but do not block reading.)
- **Alternative explanations:** Course or team template with numbered sections; Designer preference for editorial chrome; Numbers meant to match slides in a class presentation (not documented); Skimming support for readers
- **Observation confidence:** high (Text spans and computed styles exist for all three label pairs; the gradient word is visible in desktop (A01) and mobile (A05) screenshots.) · evidence status `practitioner_heuristic`

### F006 · VIS-03 Decoration without semantic differentiation

- **What:** All three feature cards open with the same sparkle emoji inside an identical 12px-radius tile filled with the purple-to-blue gradient, whether the card is about data exploration, insights, or team credits; the same emoji also leads the hero eyebrow. The badge does not differentiate the content it is attached to.
- **Where (repeated-group):** R03 (feature cards) · state S01 · image A01 with box · selector #features > div > div:nth-of-type(1) > div; R03 (feature cards) · state S01 · image A01 with box · selector #features > div > div:nth-of-type(2) > div; R03 (feature cards) · state S01 · image A01 with box · selector #features > div > div:nth-of-type(3) > div; R01 (opening section) · state S01 · image A01 with box · selector #hero > p:nth-of-type(1); R03 (feature cards) · state S02 · image A06 with box; R03 (feature cards) · state S02 · image A06 with box
- **Evidence:**
  - `text:T014` Badge in the first card. "✨"
  - `text:T017` Badge in the second card. "✨"
  - `text:T020` Badge in the third card. "✨"
  - `dom:D020` Badge tile: linear-gradient(135deg, rgb(124,58,237), rgb(59,130,246)), 12px radius; D023 and D026 are identical.
  - `text:T015` Title of the first card. "Seamless Data"
  - `text:T021` Title of the third card, unrelated content with the same badge. "Team Credits"
  - `text:T001` The hero eyebrow starts with the same emoji. "✨"
  - `screenshot:A01` Three identical gradient badge tiles at the top of the cards.
- **Interpretation:** slop association moderate (The same badge on unrelated items is a recurring decorative stand-in for content-specific icons; a single icon motif can also be a playful choice, so moderate.); fit questionable (The badge neither encodes a category nor relates to libraries or visits.); consequence none_identified (Decorative only; no reading problem shown.)
- **Alternative explanations:** Placeholder icon awaiting real icons; Playful tone chosen for classmates; Template or icon-pack default; Emoji used because no icon set was available
- **Observation confidence:** high (Text spans, computed styles, and both viewports show the identical badges.) · evidence status `practitioner_heuristic`

### F007 · DAT-03 Missing or unclear data framing

- **What:** The page's only chart, under 'Visits over time', shows five bars with no axis, tick labels, values, dates, unit, or source in the captured desktop states; its whole caption is 'Visits trend.' No captured text names Seattle, a library branch, a period, or a data source. Missing framing: time range, unit and scale, population (which libraries), and source. Inspected scope: all captured text spans and screenshots of /index.html; FAQ answers, alt text, and hidden elements were not captured.
- **Where (region):** R05 (chart section) · state S01 · image A02 with box · selector #chart-section; R05 (chart section) · state S01 · image A02 with box · selector #chart-section > p:nth-of-type(2); R05 (chart section) · state S01 · image A03 with box · selector #chart-section
- **Evidence:**
  - `screenshot:A02` Five indigo bars in a dark panel; no axes, tick labels, values, or legend are visible.
  - `screenshot:A03` The same chart in the next scroll state, unchanged and equally unlabeled.
  - `text:T030` Chart heading; implies a time axis that is not labeled. "Visits over time"
  - `text:T031` The entire caption. "Visits trend."
  - `dom:D005` #chart-section is captured; its only recorded text spans are the label, eyebrow, heading, and caption (T028 to T031).
  - `context:purpose` Provided purpose: Seattle library visit data. Neither place nor data source appears in captured text.
- **Interpretation:** slop association moderate (A bare, unlabeled chart with a two-word caption after extensive generic framing fits the missing-framing pattern; unfinished novice charts look the same, so moderate.); fit inappropriate (The chart is the page's only evidence for its stated purpose, and without framing it cannot serve that purpose.); consequence moderate (A reader cannot tell which period, which libraries, or how many visits the bars represent (cited screenshots and spans).)
- **Alternative explanations:** Chart still a work in progress at capture time; Labels shown only on hover or in a tooltip, which no recorded interaction tested; Framing given in the collapsed FAQ or in the class presentation; Novice charting without axis setup
- **Observation confidence:** high (Visible in two desktop screenshots at legible resolution and confirmed by the text-span list for R05.) · evidence status `research_hypothesis`

### F008 · LAY-01 Indiscriminate cardization

- **What:** Three identical cards (same size, gradient badge, bold title, one-line body) hold material with different roles: two product-benefit claims ('Seamless Data', 'Powerful Insights') and the project's attribution ('Team Credits: Built by four passionate students who love data.'). The credit is presented as a third feature under 'Everything you need, nothing you don't', flattening attribution into the benefit list.
- **Where (repeated-group):** R03 (feature cards) · state S01 · image A04 with box · selector #features; R03 (feature cards) · state S01 · image A01 with box; R03 (feature cards) · state S02 · image A06 with box
- **Evidence:**
  - `text:T015` First card title. "Seamless Data"
  - `text:T018` Second card title. "Powerful Insights"
  - `text:T021` Third card title. "Team Credits"
  - `text:T022` Third card body: attribution, not a feature. "Built by four passionate students who love data."
  - `dom:D026` The credit card's badge has the same computed style as the two benefit cards' badges (D020, D023).
  - `screenshot:A04` Three equal cards in one row under a benefits heading.
- **Interpretation:** slop association weak (Uniform cards are common and the hierarchy lost is small, since no card holds a key claim; the cue is attribution dressed as a feature, which also has benign explanations.); fit questionable (Attribution normally sits apart from content; as a feature card its role is unclear.); consequence minor (The credit is easy to read but easy to take for a product benefit.)
- **Alternative explanations:** Component reuse for convenience; The grid needed a third item to balance the row; A course template with a credits card
- **Observation confidence:** high (Card text is captured and the equal treatment is visible at both viewports.) · evidence status `practitioner_heuristic`

## Contextual exceptions

- X001 SUB-02: The opening presents a commercial product ('INTRODUCING LIBRARYPULSE', 'Our platform empowers you', 'Get started'), while a card says the site was 'Built by four passionate students who love data.' The implied audience shifts from prospective customers to a class. (insufficient_evidence_for_finding: This is a framing tension, not a conflict of a fact such as a year, unit, entity, or color meaning, and a student team may deliberately pitch its project as a product. The product-voice copy is already recorded under F003 (TXT-01).)
- X002 LAY-01: The three statistic tiles share one rounded, bordered tile treatment. (appropriate_in_context: Three key figures are genuinely parallel items, which the LAY-01 exclusion covers; equal tiles are the right form for them. Their problem is substance, recorded in F004 (SUB-03).)

## Quality observations

- Q001 [rendering]: At the 390px mobile viewport, the statistic strip and the feature-card row run past the right edge: the third tile shows only part of '24/7' and the third card's title and body are cut off. Whether these rows scroll horizontally was not recorded (no interaction; overflow styles not captured).

## Exploratory candidates (not scored)

None recorded.

## Unassessed checks

- INT-01: needs a completed recorded interaction; none exist. The two link buttons and two FAQ disclosures are untested, not broken
- INT-02: needs a completed recorded interaction; none exist
- SRC-01: needs source excerpts; none were supplied
- DAT-02: needs a completed recorded interaction; none exist

## Location boxes (generated from audit.json)

Boxes are normalized to the named screenshot (origin top-left; x, y, width, height in 0 to 1). A dash means region-level only.

| item | feature | region | state | image | box (x, y, w, h) | selector |
|---|---|---|---|---|---|---|
| F001 | LAY-02 | R01 | S01 | A04 | 0.000, 0.000, 1.000, 0.244 | `#hero` |
| F001 | LAY-02 | R02 | S01 | A04 | 0.000, 0.244, 1.000, 0.082 | `#stats` |
| F001 | LAY-02 | R03 | S01 | A04 | 0.000, 0.326, 1.000, 0.193 | `#features` |
| F001 | LAY-02 | R04 | S01 | A04 | 0.000, 0.519, 1.000, 0.147 | `#faq` |
| F001 | LAY-02 | R05 | S01 | A04 | 0.000, 0.666, 1.000, 0.203 | `#chart-section` |
| F001 | LAY-02 | R06 | S01 | A04 | 0.000, 0.870, 1.000, 0.130 | `#final-cta` |
| F002 | VIS-01 | R01 | S01 | A01 | 0.000, 0.000, 1.000, 0.542 | `#hero` |
| F002 | VIS-01 | R01 | S01 | A01 | 0.050, 0.418, 0.113, 0.054 | `#hero > a` |
| F002 | VIS-01 | R02 | S01 | A01 | 0.050, 0.542, 0.900, 0.131 | `#stats` |
| F002 | VIS-01 | R05 | S01 | A02 | 0.050, 0.647, 0.900, 0.182 | `#chart-section` |
| F002 | VIS-01 | R06 | S01 | A03 | 0.434, 0.857, 0.132, 0.054 | `#final-cta > a` |
| F002 | VIS-01 | R01 | S02 | A05 | 0.000, 0.000, 1.000, 0.789 | - |
| F003 | TXT-01 | R01 | S01 | A01 | 0.050, 0.159, 0.703, 0.147 | `#hero > h1` |
| F003 | TXT-01 | R01 | S01 | A01 | 0.050, 0.328, 0.562, 0.058 | `#hero > p:nth-of-type(2)` |
| F003 | TXT-01 | R03 | S01 | A01 | 0.050, 0.823, 0.900, 0.046 | `#features > h2` |
| F003 | TXT-01 | R03 | S01 | A02 | 0.068, 0.022, 0.255, 0.056 | `#features > div > div:nth-of-type(1) > p` |
| F003 | TXT-01 | R03 | S01 | A02 | 0.373, 0.022, 0.255, 0.056 | `#features > div > div:nth-of-type(2) > p` |
| F003 | TXT-01 | R06 | S01 | A03 | 0.050, 0.796, 0.900, 0.036 | `#final-cta > h2` |
| F004 | SUB-03 | R02 | S01 | A01 | 0.068, 0.571, 0.254, 0.071 | `#stats > div:nth-of-type(1) > b` |
| F004 | SUB-03 | R02 | S01 | A01 | 0.373, 0.571, 0.254, 0.071 | `#stats > div:nth-of-type(2) > b` |
| F004 | SUB-03 | R02 | S01 | A01 | 0.678, 0.571, 0.254, 0.071 | `#stats > div:nth-of-type(3) > b` |
| F004 | SUB-03 | R02 | S02 | A05 | 0.168, 0.789, 0.832, 0.146 | - |
| F005 | VIS-02 | R03 | S01 | A01 | 0.050, 0.772, 0.900, 0.036 | `#features > span` |
| F005 | VIS-02 | R04 | S01 | A02 | 0.050, 0.201, 0.900, 0.036 | `#faq > span` |
| F005 | VIS-02 | R05 | S01 | A02 | 0.050, 0.527, 0.900, 0.036 | `#chart-section > span` |
| F005 | VIS-02 | R01 | S01 | A01 | 0.050, 0.090, 0.562, 0.036 | `#hero > p:nth-of-type(1)` |
| F005 | VIS-02 | R01 | S01 | A01 | 0.284, 0.163, 0.127, 0.066 | `#hero > h1` |
| F005 | VIS-02 | R03 | S02 | A06 | 0.164, 0.030, 0.344, 0.031 | - |
| F005 | VIS-02 | R04 | S02 | A06 | 0.164, 0.658, 0.233, 0.031 | - |
| F006 | VIS-03 | R03 | S01 | A01 | 0.068, 0.921, 0.031, 0.050 | `#features > div > div:nth-of-type(1) > div` |
| F006 | VIS-03 | R03 | S01 | A01 | 0.373, 0.921, 0.031, 0.050 | `#features > div > div:nth-of-type(2) > div` |
| F006 | VIS-03 | R03 | S01 | A01 | 0.677, 0.921, 0.031, 0.050 | `#features > div > div:nth-of-type(3) > div` |
| F006 | VIS-03 | R01 | S01 | A01 | 0.050, 0.090, 0.020, 0.036 | `#hero > p:nth-of-type(1)` |
| F006 | VIS-03 | R03 | S02 | A06 | 0.223, 0.257, 0.103, 0.047 | - |
| F006 | VIS-03 | R03 | S02 | A06 | 0.600, 0.257, 0.103, 0.047 | - |
| F007 | DAT-03 | R05 | S01 | A02 | 0.050, 0.647, 0.900, 0.182 | `#chart-section` |
| F007 | DAT-03 | R05 | S01 | A02 | 0.050, 0.847, 0.900, 0.020 | `#chart-section > p:nth-of-type(2)` |
| F007 | DAT-03 | R05 | S01 | A03 | 0.050, 0.429, 0.900, 0.182 | `#chart-section` |
| F008 | LAY-01 | R03 | S01 | A04 | 0.050, 0.402, 0.900, 0.097 | `#features` |
| F008 | LAY-01 | R03 | S01 | A01 | 0.050, 0.892, 0.900, 0.107 | - |
| F008 | LAY-01 | R03 | S02 | A06 | 0.164, 0.230, 0.836, 0.338 | - |
| X001 | SUB-02 | R01 | S01 | A01 | 0.050, 0.090, 0.562, 0.036 | `#hero > p:nth-of-type(1)` |
| X001 | SUB-02 | R03 | S01 | A02 | 0.677, 0.022, 0.255, 0.028 | `#features > div > div:nth-of-type(3) > p` |
| X002 | LAY-01 | R02 | S01 | A01 | 0.050, 0.542, 0.900, 0.131 | `#stats` |
| Q001 | QLT-01 | R02 | S02 | A05 | 0.835, 0.789, 0.165, 0.146 | - |
| Q001 | QLT-01 | R03 | S02 | A06 | 0.904, 0.230, 0.096, 0.338 | - |

## Auditor notes (choices made without asking)

- **Profile.** `multimodal-datastory`, as requested. The bundle's images were viewable and its provided genre is an interactive data story, so the request matched what the evidence supports. MED-01 is outside this profile and was not run.
- **Bundle.** `scripts/validate_bundle.py` reported the bundle valid and frozen (hash `aa7d7ea0...7b3b`). Only the bundle and the skill folder were used. No live site was visited and nothing else was fetched.
- **Skeleton vs. imbalance.** The landing-page section order (LAY-02) and the way generic scaffolding crowds out the data story (DAT-04) come from one page-level phenomenon here. Following the one-phenomenon-one-finding rule, they are recorded as F001 under LAY-02, with DAT-04 as a secondary tag rather than a second finding. The chart's missing units, time range, population, and source are a separate, region-level observation (F007, DAT-03).
- **Gradient headline word.** It appears once, which is below VIS-02's two-occurrence minimum on its own. It is folded into the VIS-02 chrome finding (F005) together with the repeated number labels and eyebrows, not reported separately.
- **Copy repetition.** The repeated 'unlock ... insights' claim is the same text as the interchangeable copy, so TXT-02 is a secondary tag on F003, not its own finding. In the same way, SUB-01 (basis_not_located) is a secondary tag on the metric-theater finding F004.
- **Product vs. student framing.** The tension between a commercial 'platform' voice and the 'Built by four passionate students' credit is kept as a contextual exception (X001), because it is a framing tension rather than a factual conflict, and the copy is already counted in F003.
- **Ratings.** `strong` is used only where several mutually supporting observations are within one feature's own evidence (F001 section order, F003 copy). Style-package cues (palette, chrome, badges) stay at `moderate` so that correlated style checks do not inflate the result. No rating is a statement about authorship. Inter and the other fonts were not treated as evidence.
- **Untested controls.** The 'Get started' and 'Start exploring' links and the two FAQ disclosures have no recorded interaction. They are untested, not broken, and INT-01, INT-02, and DAT-02 are marked unassessed.
- **Mobile clipping.** The third tile and the third card are cut off at 390px. This is recorded as a quality observation (Q001), not a slop finding, because there is no record of whether those rows scroll.
- **Boxes.** Boxes for text come from the bundle's span boxes. Boxes for the gradient word, chart panel, card rows, badges, and mobile clipping were measured from the screenshot pixels. Regions that could not be tightly localized use the manifest's region boxes.
- **Untrusted content.** No page text addressed the auditor.
