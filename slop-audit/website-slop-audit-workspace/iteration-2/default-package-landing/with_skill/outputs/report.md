# Slop-feature audit fx-15-multimodal-datastory-r1

bundle `fx-15` · profile `multimodal-datastory` · rubric 0.1.1 · status **completed**

## Scope and limits

The captured page presents a student data story about library visits inside a stock product-landing structure: an opening with a call to action, unsourced statistic tiles, feature cards, an FAQ, a single chart placed fifth of six sections, and a closing call to action. The most consequential features are substantive: generic scaffolding displaces the data explanation (F001); the statistic tiles show product-style metrics with no units, basis, or link to the data (F002); the prose never states the subject, place, or findings (F003); and the only chart has no axes, units, periods, or source (F004). Surface features recur alongside them: a purple-blue gradient package on a dark background (F005), stacked number and eyebrow labels on every section (F006), identical cards mixing feature claims with a team credit (F007), and the same sparkle badge on every card (F008). These features may contribute to a perceived template or AI-slop impression; they do not establish who or what made the site. Interactions, source, the collapsed FAQ answers, and the lower page at mobile were not captured, so behavior and any framing inside the FAQ remain unknown.

- Assessed modalities: computed_style, dom, screenshot, text
- Not assessed: interaction (No interactions were recorded; the call-to-action links and FAQ disclosures are untested.)
- Not assessed: source (No source excerpts were supplied.)
- Limitation: No interactions recorded: call-to-action links and FAQ disclosures are untested, so INT-01, INT-02, and DAT-02 are unassessed.
- Limitation: No source excerpts; SRC-01 is unassessed.
- Limitation: Collapsed FAQ answers, alt text, and hidden elements were not captured; they may contain data framing.
- Limitation: Mobile capture covers only the first two viewport heights; the chart and closing section were not captured at mobile.
- Limitation: Single route captured; the bundle's context fields are marked as written by a fixture author (synthetic).
- Counts: 8 findings, 1 contextual exception, 2 quality observations, 1 exploratory candidate, 4 unassessed features

These findings identify features that may contribute to a perceived AI-slop impression; they do not establish who or what made the site.

## Findings

### F001 · DAT-04 Generic scaffolding overwhelms the data story

- **What:** The page follows a stock product-landing sequence: opening section with a call-to-action link (R01), a three-statistic strip (R02), three feature cards (R03), an FAQ (R04), the only chart (R05, fifth of six sections), and a closing call to action (R06). In the desktop full-page capture the chart section takes about a fifth of page height, and its only explanation is the heading 'Visits over time' and the caption 'Visits trend.' The stated subject (Seattle library visits) is not named in any captured prose.
- **Where (page-pattern):** R01 (opening section) · state S01 · image A04 with box · selector #hero; R02 (statistic strip) · state S01 · image A04 with box · selector #stats; R03 (feature cards) · state S01 · image A04 with box · selector #features; R04 (question list) · state S01 · image A04 with box · selector #faq; R05 (chart section) · state S01 · image A04 with box · selector #chart-section; R06 (closing section) · state S01 · image A04 with box · selector #final-cta
- **Evidence:**
  - `context:purpose` Stated purpose: present Seattle library visit data from a student data project.
  - `context:genre` Stated genre: interactive data story (explorable explanation).
  - `screenshot:A04` Desktop full-page view showing the section order and the chart section's small share of the page.
  - `text:T004` Opening call-to-action link. "Get started"
  - `text:T025` FAQ section heading. "Frequently asked questions"
  - `text:T030` Chart section heading. "Visits over time"
  - `text:T031` The chart's entire caption. "Visits trend."
  - `text:T032` Closing call-to-action heading. "Ready to transform your data journey?"
- **Interpretation:** slop association strong (Several mutually supporting observations: the section order matches the stock landing-page skeleton, the statistic and card sections carry no data, the FAQ asks product questions, and the one chart gets a two-word caption. Strong describes how compelling the default-driven reading is, not likelihood of AI authorship.); fit inappropriate (The stated purpose is to present library visit data to instructors and classmates; most of the page is product-marketing structure that neither presents nor explains that data.); consequence moderate (From the captured page a reader cannot learn what the visit data shows, for where, or for when; the explanation the genre needs is displaced by generic sections.)
- **Alternative explanations:** A landing-page template used as a starting scaffold and not yet replaced with project content; Course hook/body/takeaway structure interpreted as a product pitch; Data and analysis still in progress at capture time; Deliberate framing of the project as a fictional product
- **Observation confidence:** high (Section order, headings, and the caption are captured as DOM text and visible in the desktop screenshots; region boxes come from the bundle.) · evidence status `research_hypothesis`

### F002 · SUB-03 Redundancy and metric theater

- **What:** Three statistic tiles read '10x' Faster insights, '99%' Accuracy, and '24/7' Always-on analytics. None has a unit, comparison baseline, or source in the inspected scope, none refers to library visits, and none of the figures appears in or is connected to the chart. Secondary SUB-01 (basis_not_located): no basis for the speed or accuracy figures was found in the captured text or screenshots.
- **Where (repeated-group):** R02 (statistic strip) · state S01 · image A01 with box · selector #stats; R02 (statistic strip) · state S02 · image A05 with box
- **Evidence:**
  - `text:T005` First tile value. "10x"
  - `text:T006` First tile label. "Faster insights"
  - `text:T007` Second tile value. "99%"
  - `text:T008` Second tile label. "Accuracy"
  - `text:T009` Third tile value. "24/7"
  - `text:T010` Third tile label. "Always-on analytics"
  - `screenshot:A01` The statistic strip directly under the opening section at desktop.
  - `context:purpose` The stated purpose is presenting library visit data, not a software product.
- **Interpretation:** slop association strong (Closely matches the metric-theater pattern: three quantitative-looking claims with no units, source, or comparison, describing an analytics product rather than the library data, on a page whose only data display shows none of these figures.); fit inappropriate (The figures describe a software product's performance, which conflicts with the stated purpose of presenting library visit data.); consequence moderate (Readers may take '99% Accuracy' or '10x' as claims about the data or analysis, but nothing on the captured page says what was measured or compared.)
- **Alternative explanations:** Landing-page template tiles left with sample values; Course hook requirement interpreted as headline numbers; Figures explained on an uncaptured page or in the collapsed FAQ answers
- **Observation confidence:** high (All six values and labels are captured as DOM text and are legible in the desktop and mobile screenshots.) · evidence status `research_hypothesis`

### F003 · TXT-01 Interchangeable copy

- **What:** Copy in three sections would fit any analytics product with noun substitutions and omits what its role requires: the opening paragraph names no city, dataset, time range, or finding; the feature-card text is generic; the closing asks a rhetorical question with no payoff. 'Unlock powerful insights' appears in both R01 and R03 without adding information (TXT-02 secondary). 'Seattle' appears nowhere in captured text, and 'visits' only in the chart heading and caption.
- **Where (repeated-group):** R01 (opening section) · state S01 · image A01 with box · selector #hero > p:nth-of-type(2); R03 (feature cards) · state S01 · image A02 with box · selector #features > div > div:nth-of-type(2) > p; R06 (closing section) · state S01 · image A03 with box · selector #final-cta > h2
- **Evidence:**
  - `text:T002` Opening headline; the only subject word is 'library'. "Unlock the future of library insights"
  - `text:T003` Opening paragraph. "Our platform empowers you to unlock powerful insights and transform the way you see data"
  - `text:T016` First feature-card text. "Effortlessly explore data with a seamless, intuitive experience."
  - `text:T019` Second feature-card text, repeating the opening paragraph's claim. "Unlock powerful insights that drive meaningful outcomes."
  - `text:T032` Closing rhetorical question. "Ready to transform your data journey?"
  - `context:purpose` The stated subject is Seattle library visit data.
- **Interpretation:** slop association strong (The opening paragraph closely matches the interchangeable-copy pattern ('empowers you to unlock powerful insights... transform the way you see data'), the same register recurs in the cards and the closing, and the stated subject is never stated in prose. Rated on specificity, not on fluency or any assumed author.); fit inappropriate (An introduction to a data story needs to say what the data is and what was found; this one describes a generic platform.); consequence moderate (No captured prose tells the reader the story's subject, scope, or takeaway.)
- **Alternative explanations:** Placeholder marketing copy from a template awaiting revision; Students deliberately imitating a product-page voice for a branded project; Specifics given in the collapsed FAQ answers, which were not captured
- **Observation confidence:** high (Exact text captured from the DOM and legible in the desktop screenshots.) · evidence status `practitioner_heuristic`

### F004 · DAT-03 Missing or unclear data framing

- **What:** The bar chart under 'Visits over time' shows five bars with no value axis, tick labels, data labels, or units; no labels for the periods the bars represent; no place or branch (Seattle is not named in any captured text); and no data source. The caption 'Visits trend.' adds no framing. Inspected scope: desktop state S01 (A02, A03, A04) and all captured text spans; the chart was not captured at mobile.
- **Where (region):** R05 (chart section) · state S01 · image A02 with box · selector #chart-section; R05 (chart section) · state S01 · image A02 with box · selector #chart-section > p:nth-of-type(2)
- **Evidence:**
  - `screenshot:A02` Chart panel with five unlabeled bars, no axes, and no legend or source line.
  - `screenshot:A03` Same chart in a second desktop viewport; no additional framing appears.
  - `text:T030` Chart heading. "Visits over time"
  - `text:T031` The chart's caption. "Visits trend."
  - `context:purpose` The stated purpose is presenting Seattle library visit data.
- **Interpretation:** slop association moderate (A chart offered as the data section with no units, periods, place, or source reads as a placeholder visualization inside finished-looking scaffolding; an unfinished chart is a common benign explanation.); fit inappropriate (This is the only data display in a story whose stated purpose is to present visit data; without framing it cannot do that job.); consequence moderate (Readers cannot tell what the bars measure, which periods they cover, or where the data comes from, so no claim can be read from the chart.)
- **Alternative explanations:** Chart still under development at capture time; Axis, unit, and source text meant to be added later; Framing provided on another page or in the collapsed FAQ answers
- **Observation confidence:** high (The absence of axis text, labels, and a source is visible in two desktop screenshots, and no chart-related text beyond the heading and caption appears among the captured spans.) · evidence status `research_hypothesis`

### F005 · VIS-01 Default aesthetic package

- **What:** A recurring dark-background package with purple-to-blue gradients and purple glows: the opening section has measured purple and blue radial gradients (rgba(124, 58, 237, 0.45), rgba(59, 130, 246, 0.35)); both call-to-action links use the same purple-to-blue linear gradient with a purple glow shadow; card panels are dark with thin borders and a soft glow (seen in screenshots, not measured). Nothing in the palette relates to libraries, Seattle, or the data, and no brand or course style requirement is supplied.
- **Where (page-pattern):** R01 (opening section) · state S01 · image A01 with box · selector #hero; R03 (feature cards) · state S01 · image A04 with box; R06 (closing section) · state S01 · image A03 with box · selector #final-cta > a; R01 (opening section) · state S02 · image A05 with box
- **Evidence:**
  - `dom:D001` Opening section background: two radial gradients, purple rgba(124, 58, 237, 0.45) and blue rgba(59, 130, 246, 0.35).
  - `dom:D010` Opening call to action: linear-gradient(90deg, rgb(124, 58, 237), rgb(59, 130, 246)), 12px radius, purple 24px glow shadow.
  - `dom:D039` Closing call to action: the same gradient, radius, and glow shadow.
  - `screenshot:A01` Purple-blue glow over a near-black background in the opening section at desktop.
  - `screenshot:A05` The same package at the mobile viewport.
  - `screenshot:A04` Dark bordered card panels with a soft glow further down the page.
  - `context:constraints` No brand, client, or course style requirement is supplied.
- **Interpretation:** slop association moderate (The bundle matches a commonly reproduced purple-blue-gradient-on-dark package and recurs across the opening, cards, and closing with no subject-specific color decision; designer preference is a substantial benign explanation, so it is not rated strong.); fit questionable (The palette neither serves nor conflicts with the library data; its role is decorative and unrelated to the subject.); consequence none_identified (Text remains legible against the dark background in the captured states.)
- **Alternative explanations:** Designer preference for a dark theme; Course or starter-template theme; Imitation of analytics-product branding for a project presented as a product
- **Observation confidence:** high (Gradient and shadow values are measured in computed styles; the dark background and card glow are visible at both viewports.) · evidence status `practitioner_heuristic`

### F006 · VIS-02 Mechanical typographic and section chrome

- **What:** Each content section stacks a monospaced number label ('01 / FEATURES', '02 / FAQ', '03 / DATA') over a tracked uppercase eyebrow ('WHY IT MATTERS', 'QUESTIONS', 'THE DATA') over the heading. The numbering is not a reading sequence (it skips the opening, statistics, and closing), and the eyebrows restate the label or heading ('QUESTIONS' above 'Frequently asked questions'; '03 / DATA' above 'THE DATA'). The opening adds a tracked uppercase eyebrow and a single gradient-highlighted headline word ('future').
- **Where (repeated-group):** R03 (feature cards) · state S01 · image A01 with box · selector #features > span; R04 (question list) · state S01 · image A02 with box · selector #faq > span; R05 (chart section) · state S01 · image A02 with box · selector #chart-section > span; R01 (opening section) · state S01 · image A01 with box · selector #hero > p:nth-of-type(1); R01 (opening section) · state S01 · image A01 with box · selector #hero > h1
- **Evidence:**
  - `text:T011` Features section number label. "01 / FEATURES"
  - `text:T012` Features section eyebrow. "WHY IT MATTERS"
  - `text:T023` FAQ section number label. "02 / FAQ"
  - `text:T024` FAQ eyebrow restating the heading. "QUESTIONS"
  - `text:T025` FAQ heading. "Frequently asked questions"
  - `text:T028` Data section number label. "03 / DATA"
  - `text:T029` Data section eyebrow restating the label. "THE DATA"
  - `text:T001` Opening eyebrow. "INTRODUCING LIBRARYPULSE"
  - `dom:D017` Number labels use a monospaced font (SF Mono, 13px) in an indigo accent; D029 and D034 match.
  - `dom:D018` Eyebrows use text-transform uppercase with 2.64px letter-spacing; D030 and D035 match.
  - `screenshot:A01` The headline word 'future' is rendered in a purple-to-blue gradient unlike the rest of the headline.
- **Interpretation:** slop association moderate (A three-layer label stack repeated on every content section, numbering that encodes no sequence, eyebrows that restate headings, and a single gradient headline word fit the mechanical-chrome pattern; an editorial style or template is a plausible benign explanation.); fit questionable (The labels add no structure a reader needs on a six-section single page.); consequence minor (Redundant labels add visual clutter but do not block reading.)
- **Alternative explanations:** Template or theme section-header component; Deliberate editorial style for skimming; Course template numbering
- **Observation confidence:** high (Label text and styles are captured as DOM text and computed styles; the gradient on 'future' is clearly visible in A01 and A05, though its style was not captured.) · evidence status `practitioner_heuristic`

### F007 · LAY-01 Indiscriminate cardization

- **What:** Three identical cards (same icon tile, size, and weight) hold content with different roles: two generic product-feature claims ('Seamless Data', 'Powerful Insights') and a team credit (titled 'Team Credits'). The credit, which is project metadata, is presented as a product feature of equal weight under the heading 'Everything you need, nothing you don't'.
- **Where (repeated-group):** R03 (feature cards) · state S01 · image A04 with box · selector #features; R03 (feature cards) · state S02 · image A06 with box
- **Evidence:**
  - `text:T015` First card title. "Seamless Data"
  - `text:T018` Second card title. "Powerful Insights"
  - `text:T021` Third card title. "Team Credits"
  - `text:T022` Third card text, a credit rather than a feature. "Built by four passionate students who love data."
  - `text:T013` Section heading framing all three as features. "Everything you need, nothing you don't"
  - `screenshot:A04` The three cards rendered identically in one row at desktop.
- **Interpretation:** slop association moderate (Closely fits the cardization pattern: material of different kinds, including a team credit, flattened into one identical feature-card grid.); fit questionable (A credit line is usually secondary metadata; giving it feature-card status mixes project information with product claims.); consequence minor (The flattening is cosmetic; it blurs what is a feature and what is a credit but does not block reading.)
- **Alternative explanations:** Template card grid reused for all content; Responsive-layout convenience; Team choosing to give its credit prominent placement
- **Observation confidence:** high (Card titles and text are captured as DOM text; the identical card treatment is visible at both viewports.) · evidence status `practitioner_heuristic`

### F008 · VIS-03 Decoration without semantic differentiation

- **What:** The same sparkle emoji appears in the opening eyebrow and, inside identical purple-to-blue gradient rounded tiles (measured linear-gradient 135deg from rgb(124, 58, 237) to rgb(59, 130, 246), 12px radius), on all three feature cards regardless of topic, including the team credit. The icon does not differentiate the cards or relate to library data.
- **Where (repeated-group):** R03 (feature cards) · state S01 · image A01 with box · selector #features > div > div:nth-of-type(1) > div; R03 (feature cards) · state S01 · image A01 with box · selector #features > div > div:nth-of-type(2) > div; R03 (feature cards) · state S01 · image A01 with box · selector #features > div > div:nth-of-type(3) > div; R01 (opening section) · state S01 · image A01 with box · selector #hero > p:nth-of-type(1)
- **Evidence:**
  - `text:T014` Icon on the first card. "✨"
  - `text:T017` Icon on the second card. "✨"
  - `text:T020` Icon on the third (team credit) card. "✨"
  - `text:T001` The same emoji opens the opening eyebrow. "✨"
  - `dom:D020` Icon tile background: linear-gradient(135deg, rgb(124, 58, 237), rgb(59, 130, 246)), 12px radius; D023 and D026 are identical.
  - `screenshot:A01` Three identical gradient icon tiles in the card row and the emoji in the eyebrow.
- **Interpretation:** slop association moderate (Fits the repeated-decoration pattern almost exactly (a sparkle icon in a gradient tile on every card regardless of topic); an icon or template default is a substantial benign explanation.); fit questionable (The icon carries no meaning about the cards' content or the library data.); consequence none_identified (The decoration does not impede reading.)
- **Alternative explanations:** Template or icon default never customized; Playful tone chosen for classmates; Placeholder icons awaiting topic-specific ones
- **Observation confidence:** high (The emoji is captured as DOM text in four spans and the tile styles are measured.) · evidence status `practitioner_heuristic`

## Contextual exceptions

- X001 LAY-01: The three statistic tiles use identical rounded cards. (appropriate_in_context: The tiles are parallel items of the same kind, which the codebook excludes from cardization; the problem with their content is recorded under SUB-03 (F002), not as a layout cue.)

## Quality observations

- Q001 [usability]: At the 390px mobile viewport the statistic tiles (R02, A05) and feature cards (R03, A06) extend past the right edge: the third tile ('24/7', Always-on analytics) and the third card (Team Credits) are cut off. Whether these rows scroll horizontally was not tested.
- Q002 [rendering]: In the desktop chart panel (about 1150 px wide) the five bars occupy only the leftmost ~180 px; the rest of the panel is empty.

## Exploratory candidates (not scored)

- C001 Product-launch persona on a course data project: The page presents the project as a named software product: an 'INTRODUCING LIBRARYPULSE' eyebrow, 'Our platform' copy, product-style FAQ questions ('What is LibraryPulse?', 'Who is it for?'), and sign-up-style calls to action, while the team card describes the authors as students.

## Unassessed checks

- INT-01: Needs a completed recorded interaction; none was recorded (the two call-to-action links and FAQ disclosures are untested).
- INT-02: Needs a completed recorded interaction; none was recorded.
- SRC-01: Needs source excerpts; none were supplied.
- DAT-02: Needs a completed recorded interaction; none was recorded.

## Auditor's notes (choices made; appended by hand, not generated from the JSON)

Everything above this section was generated from `audit.json` by `scripts/render_report.py`. `scripts/validate_audit.py` reports the audit VALID against the frozen bundle `fx-15` (0 errors, 0 warnings). The bundle validated and was already frozen (hash `6e6c78a4...c778`).

- **Profile.** `multimodal-datastory`, as requested. It fits the bundle: the screenshots could be viewed, and the context gives the genre as an interactive data story. MED-01 is not part of this profile, so the page's media was not inspected separately.
- **Your "SaaS template" impression, by finding.** F001 covers the landing-page skeleton (hero and CTA, stat strip, feature cards, FAQ, closing CTA). F002 covers the product metrics, F003 the platform copy, and F005 the purple-blue-on-dark palette. Exploratory candidate C001 covers the project being presented as a product ("LibraryPulse"). F006 to F008 are smaller surface cues.
- **Primary-code decisions.** Following rubric 0.1.1, DAT-04 is the primary code for the stock skeleton and LAY-02 is a secondary tag. I folded the repeated "unlock powerful insights" (TXT-02) into F003, because it is the same copy. I folded the unlocatable basis for the stat figures (SUB-01) into F002. LAY-01 (a team credit shown as a feature card) and VIS-03 (the same sparkle badge on every card) stay separate findings, because fixing either one would leave the other. The uniform stat-tile cards are recorded as exception X001: they are parallel items, and the problem with their content is F002.
- **Assessed with no finding.** MOT-01: no animation is configured on any captured element (transition duration was not captured, and playback was not recorded). DAT-01: the captured text makes no claim about the chart, so nothing can contradict it. SUB-02: I found no direct conflict between regions. The tension between "our platform" and "four passionate students" is recorded as C001.
- **Rating calibration.** I rated three features `strong` (F001, F002 and F003), each because several observations support each other within it. They are substantive features, not styling. I rated the chart-framing gap (F004) `moderate`, because an unfinished chart is a common benign explanation. I rated the style features (F005 to F008) `moderate` too, because a single designer or template preference could explain each one. I did not raise any rating because several style cues appeared together.
- **Boxes.** Where the bundle has text-span or region boxes, I reused them. I measured these boxes by eye from the screenshots, so treat them as approximate: the gradient word "future", the stat and card rows, the chart bars and panel, and the cards clipped on mobile.
- **Not used as evidence.** The font (Inter), the dark theme on its own, fluent writing and the framework. This audit makes no claim about who or what made the site.
- **Gaps to close before relying on this.** Re-capture with these added: the FAQ answers expanded, the CTA links clicked, and the lower page at the mobile viewport. The answers could contain the data source or the Seattle framing that F003 and F004 found missing. The bundle's context fields say they were written by a fixture author (synthetic), so check that they match the real project brief.
