<!-- GENERATED from assets/codebook.json by scripts/build_codebook.py. Edit the JSON, then rebuild. -->


# Feature codebook (rubric 0.1.1)

Status: provisional; development version, not validated against human annotations.

Contents: definition, dimensions, prohibited inferences, ordinal anchors, evidence-status levels, modules, then one entry per feature:

- [VIS-01: Default aesthetic package](#vis-01-default-aesthetic-package)
- [VIS-02: Mechanical typographic and section chrome](#vis-02-mechanical-typographic-and-section-chrome)
- [LAY-01: Indiscriminate cardization](#lay-01-indiscriminate-cardization)
- [LAY-02: Interchangeable page skeleton](#lay-02-interchangeable-page-skeleton)
- [VIS-03: Decoration without semantic differentiation](#vis-03-decoration-without-semantic-differentiation)
- [MOT-01: Templated motion](#mot-01-templated-motion)
- [TXT-01: Interchangeable copy](#txt-01-interchangeable-copy)
- [TXT-02: Repetitive or mechanically balanced prose](#txt-02-repetitive-or-mechanically-balanced-prose)
- [SUB-01: Placeholder or unverifiable substance](#sub-01-placeholder-or-unverifiable-substance)
- [SUB-02: Local polish with global incoherence](#sub-02-local-polish-with-global-incoherence)
- [SUB-03: Redundancy and metric theater](#sub-03-redundancy-and-metric-theater)
- [INT-01: Decorative or nonfunctional affordance](#int-01-decorative-or-nonfunctional-affordance)
- [INT-02: Incomplete state integration](#int-02-incomplete-state-integration)
- [QLT-01: General usability or accessibility defect](#qlt-01-general-usability-or-accessibility-defect)
- [SRC-01: Source/render mismatch](#src-01-sourcerender-mismatch)
- [MED-01: Media inconsistency or synthetic-looking artifact](#med-01-media-inconsistency-or-synthetic-looking-artifact)
- [DAT-01: Narrative–chart disconnect](#dat-01-narrativechart-disconnect)
- [DAT-02: Interaction without explanatory role](#dat-02-interaction-without-explanatory-role)
- [DAT-03: Missing or unclear data framing](#dat-03-missing-or-unclear-data-framing)
- [DAT-04: Generic scaffolding overwhelms the data story](#dat-04-generic-scaffolding-overwhelms-the-data-story)

## Definition

> A perceived AI-slop feature is a localized or cross-region pattern that can contribute to an impression of default-driven, interchangeable, superficial, or insufficiently integrated production. The impression may arise from style conventions, content–design mismatch, incomplete behavior, or surface polish unsupported by coherent substance. Neither the pattern nor the impression establishes who or what produced the website.

*Operational research definition chosen by the project team (UC San Diego data science lab, 2026). It is a working construct to pilot with human raters, not an established or externally validated definition.*

## Four dimensions, kept separate

1. **observable feature**: What is actually present in the supplied evidence. Recorded as the observation, its locations, and evidence references.
2. **slop association**: How strongly the observed feature, in this context, fits a candidate AI-slop pattern. An ordinal interpretation, not a probability of production history.
3. **contextual fit and consequence**: Whether the feature serves the website's purpose, and whether there is an observable communication or interaction problem. Recorded separately from slop association.
4. **production provenance**: Independently documented creation history. Withheld from the auditor; stored outside capture bundles for optional secondary research. The auditor never outputs a provenance judgment.

## Never infer

- No global probability that a site is AI-generated, and no percentage-AI score.
- No authorship inference from fluency, grammatical correctness, language proficiency, or punctuation (including em dashes).
- No authorship inference from Inter or any other font, gradients, rounded corners, Tailwind, React, D3, shadcn, or any component library alone.
- No inference of a specific generator's identity from a palette, font, or style.
- No requirement to report a minimum number of findings; an empty findings list with stated coverage is a valid result.
- Not every design defect is a slop finding; usability and accessibility defects are quality observations unless an explicit additional rationale is recorded.

## Ordinal anchors

Provisional research operationalizations to pilot with human raters. They are not an externally validated scale.

**slop_association**

- `none`: No supported association in this context.
- `weak`: An isolated or conventional cue with substantial benign explanations.
- `moderate`: A contextually questionable recurring pattern or integration problem, with concrete evidence.
- `strong`: Several mutually supporting observations make the superficial or default-driven interpretation especially compelling to the evaluator. Strong does not mean AI authorship is likely. Do not promote a rating merely because several correlated style checks fired.
- `unassessed`: The evidence or contextual basis is insufficient to rate the association.

**observation_confidence**

- `high`: The feature is clearly present in the cited evidence (readable text span, legible screenshot region, completed recorded event).
- `medium`: The feature appears present but is partly visible, depends on reading small or stylized text, or rests on a single state.
- `low`: Presence is uncertain; the evidence is ambiguous, low resolution, or possibly a transient capture artifact.

**contextual_fit**

- `appropriate`: The feature serves the site's stated or inferable purpose, genre, or constraints.
- `questionable`: The feature's role is unclear or only weakly connected to the purpose.
- `inappropriate`: The feature works against the stated purpose or conflicts with the site's own content.
- `unknown`: Purpose or constraints are not available, so fit cannot be judged.

**consequence**

- `none_identified`: No communication or interaction problem identified in the evidence.
- `minor`: A cosmetic concern that does not impede understanding or use.
- `moderate`: Makes a claim harder to interpret, or makes a feature harder to use, as shown by cited evidence.
- `major`: A tested failure that blocks the main task, as shown by a recorded interaction.
- `unknown`: The evidence does not show whether there is a consequence.

## Evidence-status levels

The auditor copies a feature's status from this codebook and never changes it.

- `corpus_specific_empirical`: Supported by empirical analysis of the target corpus. No v0.1 entry has this status; it can only be assigned after corpus studies exist.
- `practitioner_heuristic`: Proposed by practitioner design guidance or rule-based tools. Not validated as a detection signal or as a predictor of perception.
- `research_hypothesis`: An operational hypothesis of this project, motivated by sources or conceptual reasoning, to be tested with human raters.
- `quality_only`: Tracks a usability, accessibility, or implementation problem. Not a slop-association claim by default.

## Modules

- `core`: Families A (surface), B (substance), and C (interaction and implementation). Applies to any website genre.
- `data-story`: Family D. Applies to interactive data stories, explorable explanations, and visualization-heavy pages.
- `media`: MED-01. Optional inspection of images and other media inside the page.

## Features

## Family A: Surface and template-associated candidates

### VIS-01: Default aesthetic package

*Module:* `core` · *Unit:* page-pattern · *Judgment:* qualitative · *Evidence status:* `practitioner_heuristic` · *Consequence required:* no

- **Definition.** A recurring bundle of palette, type, and layout choices that matches a commonly reproduced aesthetic package (for example purple or blue gradients over glowing dark backgrounds; cream with terracotta and high-contrast serif headlines; a generic dark dashboard with one bright accent; a broadsheet treatment) applied without visible subject-specific decisions.
- **Include when.** Several co-occurring choices form a recognizable package AND the evidence shows little relationship between those choices and the subject, audience, or brand context.
- **Exclude.** A single color, gradient, font, or theme. A package that the supplied context documents as brand, client, or course requirement. Exact color values unless they were measured (computed_style); otherwise describe colors qualitatively.
- **Minimum evidence.** Two or more regions showing the same bundle of choices, plus a stated reason the bundle is not tied to the subject. (at least 2 regions)
- **Modalities.** screenshot
- **Positive example.** A municipal water-quality data story uses a glowing purple-to-blue gradient hero, dark glassy panels, and neon accents in every section, with nothing in the palette relating to water, the city, or the data.
- **Legitimate counterexample.** A music festival site whose supplied brand guide specifies a neon-on-dark palette; the package is a brand decision.
- **Alternative explanations.** Brand or client requirement; Course or organization template; Deliberate genre convention (e.g., developer tools, nightlife); Designer preference
- **Boundary.** Palette and background packages are VIS-01. Typographic treatment of specific text (gradient or highlighted headline words, eyebrows) is VIS-02. Non-text decorative objects are VIS-03.
- **Sources.** SRC-FRONTEND-DESIGN, SRC-IMPECCABLE, SRC-BOUSSIOUX2026

### VIS-02: Mechanical typographic and section chrome

*Module:* `core` · *Unit:* repeated-group · *Judgment:* qualitative · *Evidence status:* `practitioner_heuristic` · *Consequence required:* no

- **Definition.** Repeated typographic devices that do not clarify structure: eyebrow labels above every heading, a single highlighted or gradient headline word, gratuitous section numbering, label strings, or monospaced metadata used as decoration.
- **Include when.** The device repeats across sections AND carries no structural information (the numbering is not a sequence, the label repeats the heading, the metadata is not data).
- **Exclude.** Real sequences (steps, chapters a reader follows in order), editorial hierarchy, useful scientific or data metadata. A font family or a punctuation mark (including an em dash or middle dot) as a stand-alone cue.
- **Minimum evidence.** At least two occurrences of the device, with text spans or legible screenshot regions, and a statement of why it does not encode structure.
- **Modalities.** screenshot+text or text+computed_style
- **Positive example.** Every section heading has a tracked uppercase eyebrow ('INSIGHT', 'OVERVIEW', 'DEEP DIVE') whose words repeat the heading, plus '01 / 02 / 03' numbers on sections a reader can visit in any order.
- **Legitimate counterexample.** A tutorial numbers its steps 1 to 5 because each step depends on the previous one.
- **Alternative explanations.** Editorial style guide; Course template; Screen-reader or skimming support; Designer preference
- **Boundary.** Typographic devices on text are VIS-02; overall palette packages are VIS-01; decorative non-text objects are VIS-03.
- **Sources.** SRC-FRONTEND-DESIGN, SRC-IMPECCABLE

### LAY-01: Indiscriminate cardization

*Module:* `core` · *Unit:* repeated-group · *Judgment:* qualitative · *Evidence status:* `practitioner_heuristic` · *Consequence required:* no

- **Definition.** Conceptually different material forced into identical rounded tiles or repeated card grids, flattening meaningful hierarchy.
- **Include when.** Content with different roles or importance (a key claim, a caveat, a method note, a data source) receives the same card treatment, AND that sameness hides a hierarchy the content needs.
- **Exclude.** Uniform cards for items that are genuinely parallel: a catalog, product or dataset listings, comparable options, dashboard tiles. Repeated component presence alone is not a supported claim of poor fit.
- **Minimum evidence.** The repeated group, plus evidence that its items differ in role or importance.
- **Modalities.** screenshot or dom+computed_style
- **Positive example.** A data story puts its central finding, a methodology caveat, and a team credit into three identical cards with the same icon, size, and weight.
- **Legitimate counterexample.** An open-data portal lists 24 datasets as equal cards with title, size, and update date.
- **Alternative explanations.** Component library default; Genuinely parallel content; Responsive-layout convenience; Course template
- **Boundary.** Component-level uniformity inside a region or group is LAY-01; the page-level sequence of sections is LAY-02.
- **Sources.** SRC-FRONTEND-DESIGN, SRC-IMPECCABLE

### LAY-02: Interchangeable page skeleton

*Module:* `core` · *Unit:* page-pattern · *Judgment:* qualitative · *Evidence status:* `practitioner_heuristic` · *Consequence required:* no

- **Definition.** A stock succession of sections (hero, statistic strip, feature cards, testimonials, FAQ, final call to action) appearing without a clear relationship to the actual purpose.
- **Include when.** Multiple recorded regions follow the stock sequence AND the sequence does not fit what the page is for (for example a data story structured like a product landing page).
- **Exclude.** A marketing or product page that needs exactly this sequence. A single hero section. A sequence required by a course rubric or organization template documented in context.
- **Minimum evidence.** At least three recorded regions in sequence, and a statement of the purpose mismatch. (at least 3 regions)
- **Modalities.** screenshot or text+dom
- **Positive example.** An explorable explanation of drought data opens with a hero and call-to-action button, then a three-statistic strip, three feature cards, and an FAQ, with the actual chart placed last.
- **Legitimate counterexample.** A startup landing page with hero, features, testimonials, and pricing; the skeleton matches the job.
- **Alternative explanations.** Genre convention for marketing pages; Site builder or theme default; Course rubric (hook, body, takeaway); Organization template
- **Boundary.** Page-level section order is LAY-02. Card treatment inside a section is LAY-01. Excess decorative summaries are SUB-03. Primary-code rule: when the data-story module applies and the stock sequence's problem is that generic sections displace the data explanation, DAT-04 is the primary code and LAY-02 a secondary tag. LAY-02 is primary when the data-story module is not in the profile, or the page is not a data story.
- **Sources.** SRC-FRONTEND-DESIGN, SRC-BOUSSIOUX2026, SRC-DSC106-SPEC

### VIS-03: Decoration without semantic differentiation

*Module:* `core` · *Unit:* repeated-group · *Judgment:* qualitative · *Evidence status:* `practitioner_heuristic` · *Consequence required:* no

- **Definition.** Repeated icon badges, decorative blobs, glass panels, glows, gradients, emoji, or visual effects that appear to substitute for content-specific structure.
- **Include when.** The decorative element repeats AND does not differentiate content (the same badge or emoji on unrelated items, effects that carry no meaning).
- **Exclude.** Decoration that encodes meaning (status icons, category colors with a legend), brand illustration, or a single decorative moment. Effect presence alone is not an interpretation of its role.
- **Minimum evidence.** At least two occurrences, plus a statement of why the decoration does not differentiate the content it is attached to.
- **Modalities.** screenshot
- **Positive example.** Every paragraph block in a climate story starts with a glowing sparkle icon in a gradient circle, regardless of topic.
- **Legitimate counterexample.** Map layers use distinct icons that are explained in a legend.
- **Alternative explanations.** Brand illustration system; Accessibility support (icons aiding scanning); Template or icon-pack default; Playful tone chosen for the audience
- **Boundary.** Non-text decorative objects are VIS-03. Palette packages are VIS-01. Typographic devices are VIS-02.
- **Sources.** SRC-FRONTEND-DESIGN, SRC-IMPECCABLE

### MOT-01: Templated motion

*Module:* `core` · *Unit:* repeated-group · *Judgment:* mixed · *Evidence status:* `practitioner_heuristic` · *Consequence required:* no

- **Definition.** Repeated fade-and-slide entrances, floating effects, or animated counters that are independent of meaningful change.
- **Include when.** Recorded states or captured animation styles show the same entrance or ambient motion applied across unrelated sections, with no explanatory role.
- **Exclude.** Animation that explains a transition, communicates state, responds to a user action, or serves the genre (for example scroll-driven chart updates in a data story). Anything inferred from a single static screenshot.
- **Minimum evidence.** Recorded before and after states (for example scroll states) or captured animation or transition properties on two or more elements. Screenshots alone cannot establish motion; qualify any statement based on style properties as 'configured', not 'observed playing'.
- **Modalities.** interaction or computed_style or source
- **Positive example.** Captured styles show every section, footer, and caption with the same 'fade-up' animation and 0.6s duration, including static legal text.
- **Legitimate counterexample.** A chart animates between two years when the reader moves a slider, showing what changed.
- **Alternative explanations.** Animation library or template default; Deliberate brand motion system; Scrollytelling convention
- **Boundary.** Motion is MOT-01. Interaction controls with no explanatory role are DAT-02.
- **Sources.** SRC-FRONTEND-DESIGN, SRC-IMPECCABLE

## Family B: Substance, specificity, and integration candidates

### TXT-01: Interchangeable copy

*Module:* `core` · *Unit:* region · *Judgment:* qualitative · *Evidence status:* `practitioner_heuristic` · *Consequence required:* no

- **Definition.** Broad claims that give little subject-specific information, generic 'unlock / elevate / reimagine' language, or an introduction that could fit unrelated topics with noun substitutions.
- **Include when.** A quoted excerpt makes claims that would fit unrelated subjects AND the excerpt omits the specifics its role requires (what the data is, what was found, for whom).
- **Exclude.** A single suspect word. Plain or accessible language chosen for the audience. Short copy in a deliberately minimal interface.
- **Minimum evidence.** A short exact quotation from a text span, plus an explanation of what specific information is missing.
- **Modalities.** text
- **Positive example.** 'Our platform empowers you to unlock powerful insights and transform the way you see data' opens a story about one county's eviction filings, naming neither the county nor the data.
- **Legitimate counterexample.** 'This page shows how many people lived in each neighborhood in 2020' is plain but specific.
- **Alternative explanations.** Marketing-copy convention; Placeholder copy awaiting revision; Writing for a general audience; Non-native writing conventions
- **Boundary.** Lack of specificity is TXT-01. Structural repetition and mechanical balance are TXT-02. Literal placeholders are SUB-01.
- **Sources.** SRC-IMPECCABLE, SRC-FRONTEND-DESIGN, SRC-JAKESCH2023

### TXT-02: Repetitive or mechanically balanced prose

*Module:* `core` · *Unit:* repeated-group · *Judgment:* qualitative · *Evidence status:* `practitioner_heuristic` · *Consequence required:* no

- **Definition.** Multiple sections repeating the same claim, rigid parallel headings, rhetorical questions without explanatory payoff, or empty concluding summaries.
- **Include when.** Two or more text spans repeat a claim or a rigid template without adding information.
- **Exclude.** Fluent or grammatical writing as such. A single em dash or any punctuation. Intentional repetition for summary, accessibility, or emphasis that the page's purpose supports.
- **Minimum evidence.** At least two text spans showing the repetition or template, with short exact quotations.
- **Modalities.** text
- **Positive example.** Three sections end with near-identical sentences: 'The data tells a powerful story.' / 'The numbers tell a powerful story.' / 'The trends tell a powerful story.'
- **Legitimate counterexample.** A long explainer ends with a three-point recap of its own specific findings.
- **Alternative explanations.** Template copy; Editing by multiple people; Course rubric phrasing; Second-language writing conventions
- **Boundary.** Classify the repetition, not a presumed origin. Specificity problems are TXT-01.
- **Sources.** SRC-IMPECCABLE, SRC-JAKESCH2023

### SUB-01: Placeholder or unverifiable substance

*Module:* `core` · *Unit:* region · *Judgment:* mixed · *Evidence status:* `research_hypothesis` · *Consequence required:* no

- **Definition.** Literal placeholders, template testimonials, unconnected statistic tiles, unfinished labels, or claims presented without a locatable basis in the inspected material.
- **Include when.** One of three distinct sub-types, which must be named in the observation: (a) literal_placeholder: template text such as lorem ipsum or '[insert caption]'; (b) basis_not_located: a claim or statistic whose basis cannot be located in the inspected scope; (c) contradicted: the supplied evidence contradicts it.
- **Exclude.** Calling a testimonial, statistic, person, or citation fabricated because it seems generic or was not externally verified. 'Not located in inspected scope' is not 'absent everywhere'.
- **Minimum evidence.** A text span or legible screenshot region with the placeholder or claim; for basis_not_located, a statement of which scope was inspected.
- **Modalities.** text or screenshot
- **Positive example.** A chart caption reads 'Lorem ipsum dolor sit amet — replace with insight.'
- **Legitimate counterexample.** A statistic tile cites 'U.S. Census ACS 2022, table B01003' in a footnote within the inspected scope.
- **Alternative explanations.** Unfinished human draft; Template not cleaned up; Source shown outside the captured scope
- **Boundary.** Literal placeholders and unlocatable claims are SUB-01. Redundant quantitative displays are SUB-03. Missing data framing on charts is DAT-03.
- **Sources.** SRC-PROJECT-DEF

### SUB-02: Local polish with global incoherence

*Module:* `core` · *Unit:* cross-region · *Judgment:* mixed · *Evidence status:* `research_hypothesis` · *Consequence required:* no

- **Definition.** Individually polished sections whose labels, entities, terminology, color meanings, implied audience, or explanatory claims conflict with each other.
- **Include when.** At least two linked evidence items from different regions conflict (a year, a unit, an entity name, a color meaning, a claim).
- **Exclude.** A conflict seen only within an interaction (use INT-02). Deliberate contrast the page explains. A single region.
- **Minimum evidence.** At least two evidence items from at least two regions, each with a short exact quotation or legible screenshot region. (at least 2 regions)
- **Modalities.** text or screenshot
- **Positive example.** The header says the story covers 2010–2020 while a summary panel says 'since 1990', and the legend colors 'high risk' red in one chart and blue in the next.
- **Legitimate counterexample.** A page explicitly contrasts two definitions of 'drought' and labels each.
- **Alternative explanations.** Ordinary editing error; Sections written by different team members; Data updated in one place only
- **Boundary.** Static cross-region conflicts are SUB-02. Conflicts produced by a recorded interaction are INT-02 (SUB-02 may be a secondary tag). Chart–claim conflicts in a data story are DAT-01.
- **Sources.** SRC-PROJECT-DEF, SRC-SHIN2026

### SUB-03: Redundancy and metric theater

*Module:* `core` · *Unit:* repeated-group · *Judgment:* qualitative · *Evidence status:* `research_hypothesis` · *Consequence required:* no

- **Definition.** Multiple decorative summaries or quantitative-looking displays that add no distinct explanatory role, or numbers presented without units or a meaningful comparison.
- **Include when.** Quantitative displays repeat or lack units or comparison, AND the site's purpose does not explain the redundancy.
- **Exclude.** Useful repetition for accessibility, summary, or navigation. A dashboard whose job is to show tiles.
- **Minimum evidence.** The displays with their text spans or legible screenshot regions, plus the purpose-based justification.
- **Modalities.** text or screenshot
- **Positive example.** A story shows '98% Accuracy', '10x Faster', and '24/7 Insights' tiles with no units, source, or connection to its dataset.
- **Legitimate counterexample.** A data story's key-number summary repeats three figures from its charts, each with units and a link to the chart.
- **Alternative explanations.** Landing-page template; Course hook requirement; Summary for skimming readers
- **Boundary.** Quantitative-looking redundancy is SUB-03. Literal placeholders are SUB-01. Generic structure overwhelming data explanation is DAT-04.
- **Sources.** SRC-FRONTEND-DESIGN, SRC-PROJECT-DEF

## Family C: Interaction and implementation observations

### INT-01: Decorative or nonfunctional affordance

*Module:* `core` · *Unit:* region · *Judgment:* observational · *Evidence status:* `research_hypothesis` · *Consequence required:* yes

- **Definition.** A control advertises a meaningful action, but a recorded test fails to produce the advertised change.
- **Include when.** A recorded interaction with execution_status 'completed' shows no advertised change between its before and after states.
- **Exclude.** A control with no recorded test (that is 'unassessed', never 'broken'). Loading delays, disabled prerequisites, navigation outside the captured scope, or an element that is intentionally informational.
- **Minimum evidence.** The interaction record (action, target, before and after states) and evidence of what was advertised and what did not change. (requires a completed recorded interaction)
- **Modalities.** interaction
- **Positive example.** A 'Compare scenarios' button was clicked (event completed); the before and after states are identical and no comparison appears.
- **Legitimate counterexample.** A 'Download data' link that leaves the captured scope was not followed; it is unassessed.
- **Alternative explanations.** Ordinary bug; Unfinished prototype; Feature disabled intentionally; Timing too short for slow loading
- **Boundary.** A failing control is INT-01. A working control with no explanatory role is DAT-02. A control whose working result conflicts with other content is INT-02.
- **Sources.** SRC-PROJECT-DEF

### INT-02: Incomplete state integration

*Module:* `core` · *Unit:* cross-region · *Judgment:* observational · *Evidence status:* `research_hypothesis` · *Consequence required:* yes

- **Definition.** An interaction updates part of the page but leaves linked content inconsistent: a filter updates one view but not its linked summary, a reset fails to restore the recorded initial state, or a result conflicts with its own labels.
- **Include when.** A completed recorded interaction produces an after state in which two linked elements conflict.
- **Exclude.** Untested states (do not generalize from one tested state). Conflicts present before any interaction (use SUB-02).
- **Minimum evidence.** The interaction record plus at least two evidence items in the after state showing the conflict. (requires a completed recorded interaction; at least 2 regions)
- **Modalities.** interaction
- **Positive example.** After the recorded change to the 2050 scenario, the chart title says 2050 but the linked summary still describes 2020.
- **Legitimate counterexample.** A summary deliberately keeps a baseline year and labels it 'baseline'.
- **Alternative explanations.** Conventional state-management bug; Unfinished human prototype; Summary intentionally fixed to a baseline
- **Boundary.** Interaction-produced conflicts are INT-02 (SUB-02 or DAT-01 may be secondary tags). State precisely what was tested.
- **Sources.** SRC-PROJECT-DEF

### QLT-01: General usability or accessibility defect

*Module:* `core` · *Unit:* region · *Judgment:* observational · *Evidence status:* `quality_only` · *Consequence required:* no

- **Definition.** Overflow, low contrast, focus failures, unreadable labels, reduced-motion problems, and similar defects, tracked as quality observations.
- **Include when.** The defect is visible in the evidence. Record it in quality_observations. It enters findings only with an explicit additional rationale connecting it to the slop construct (quality_to_slop_rationale).
- **Exclude.** Presenting a defect as distinctive evidence of AI production. Transient loading artifacts.
- **Minimum evidence.** The defect in a screenshot region, computed style, or DOM record.
- **Modalities.** screenshot or computed_style or dom
- **Positive example.** Axis labels overflow their container at the mobile viewport.
- **Legitimate counterexample.** A loading skeleton captured before fonts loaded.
- **Alternative explanations.** Ordinary implementation defect; Untested viewport
- **Boundary.** Defects are quality observations by default; never the sole basis for a slop finding.
- **Sources.** SRC-IMPECCABLE

### SRC-01: Source/render mismatch

*Module:* `core` · *Unit:* region · *Judgment:* observational · *Evidence status:* `research_hypothesis` · *Consequence required:* no

- **Definition.** Supplied source contains unused scaffolding, disconnected handlers, or contradictory implementation details that explain a visible or tested phenomenon.
- **Include when.** An inspected source excerpt (exact path and lines) explains an observed or tested phenomenon, such as a handler attached to the wrong element explaining a dead button.
- **Exclude.** Generic naming, verbose comments, component reuse, or framework choice. Any source that was not supplied. Source-only observations must stay source-only and must not raise a visual finding's confidence.
- **Minimum evidence.** A source excerpt reference with path and line range, and the phenomenon it explains.
- **Modalities.** source
- **Positive example.** Lines 40–52 of app.js attach the 'Compare' handler to an element id that does not exist in the captured DOM, explaining the dead button in E02.
- **Legitimate counterexample.** A file has long explanatory comments; that is not a mismatch.
- **Alternative explanations.** Refactoring leftover; Merge error; Unfinished feature
- **Boundary.** Source evidence explains other observations; it is not authorship evidence.
- **Sources.** SRC-OREL2026, SRC-PROJECT-DEF

### MED-01: Media inconsistency or synthetic-looking artifact

*Module:* `media` · *Unit:* region · *Judgment:* observational · *Evidence status:* `research_hypothesis` · *Consequence required:* no

- **Definition.** A local image shows observable distortions, nonsensical rendered text, or visual inconsistency relevant to the site's presentation.
- **Include when.** The distortion or nonsensical text is visible in a legible screenshot region or crop.
- **Exclude.** Declaring the image synthetic or the site AI-produced. Compression or scaling artifacts of the capture itself.
- **Minimum evidence.** A legible screenshot region of the image, with a box when it can be localized.
- **Modalities.** screenshot
- **Positive example.** A hero photo shows a street sign with unreadable, letter-like glyphs and a hand with six fingers.
- **Legitimate counterexample.** A stylized illustration with intentionally simplified hands.
- **Alternative explanations.** Stock-image editing; Intentional illustration style; Capture compression
- **Boundary.** Report the local observation only.
- **Sources.** SRC-YEUNG2026

## Family D: Interactive data-story module

### DAT-01: Narrative–chart disconnect

*Module:* `data-story` · *Unit:* cross-region · *Judgment:* mixed · *Evidence status:* `research_hypothesis` · *Consequence required:* no

- **Definition.** A headline or explanation is not supported by the chart's shown state, confuses a projection with an observation, or uses an inconsistent comparison.
- **Include when.** Readable chart evidence (legible values, labels, or supplied data) contradicts or fails to support the adjacent claim.
- **Exclude.** Charts too small or illegible to read; abstain instead. Claims about data outside the shown state.
- **Minimum evidence.** The claim's text span plus legible chart evidence or a supplied data excerpt.
- **Modalities.** screenshot or source
- **Positive example.** A caption says rainfall 'doubled since 2000' while the chart's own labeled values rise from 410 mm to 455 mm.
- **Legitimate counterexample.** A caption says 'projected' and the chart marks the projected range with a dashed line.
- **Alternative explanations.** Caption written before final data; Misreading by the author; Different data version
- **Boundary.** Chart–claim conflicts are DAT-01; general cross-region conflicts are SUB-02.
- **Sources.** SRC-SEGEL-HEER2010, SRC-PROJECT-DEF

### DAT-02: Interaction without explanatory role

*Module:* `data-story` · *Unit:* region · *Judgment:* qualitative · *Evidence status:* `research_hypothesis` · *Consequence required:* no

- **Definition.** Controls or animations offer surface activity but do not demonstrably support exploration or explanation for the stated purpose.
- **Include when.** A recorded working interaction changes something that does not help the reader explore or understand the stated question. State the task and the observed behavior.
- **Exclude.** Exploratory, playful, or engagement uses the context supports. Untested controls.
- **Minimum evidence.** The interaction record and the stated purpose it fails to serve. (requires a completed recorded interaction)
- **Modalities.** interaction
- **Positive example.** A 'shuffle colors' button recolors the chart randomly in a story about income inequality.
- **Legitimate counterexample.** A playful 'guess the trend' interaction before the reveal, which the narrative uses.
- **Alternative explanations.** Course requirement to include interaction; Experimentation; Engagement goal
- **Boundary.** Working controls without explanatory role are DAT-02; failing controls are INT-01.
- **Sources.** SRC-SEGEL-HEER2010, SRC-DSC106-SPEC

### DAT-03: Missing or unclear data framing

*Module:* `data-story` · *Unit:* region · *Judgment:* mixed · *Evidence status:* `research_hypothesis` · *Consequence required:* no

- **Definition.** In the inspected scope, units, population, time range, source, uncertainty, or assumptions needed for the claim cannot be located.
- **Include when.** A specific chart or claim needs a framing element that cannot be located in the inspected scope. Name which element is missing.
- **Exclude.** Framing that is irrelevant to the actual chart and claim. Framing shown outside the captured scope (say the scope). 'Missing in the inspected view' is not 'absent everywhere'.
- **Minimum evidence.** The chart or claim region, the missing framing element, and the inspected scope.
- **Modalities.** text or screenshot
- **Positive example.** A line chart of 'risk' has no unit, no source, and no time-axis label in any captured state.
- **Legitimate counterexample.** A small sparkline in a table whose column header gives the unit and years.
- **Alternative explanations.** Framing provided on another page; Space constraints; Course template omitting sources
- **Boundary.** Missing chart framing is DAT-03; unlocatable claims outside charts are SUB-01.
- **Sources.** SRC-SEGEL-HEER2010, SRC-PROJECT-DEF

### DAT-04: Generic scaffolding overwhelms the data story

*Module:* `data-story` · *Unit:* page-pattern · *Judgment:* qualitative · *Evidence status:* `research_hypothesis` · *Consequence required:* no

- **Definition.** The page devotes substantial repeated structure to broad claims or decorative summaries while the actual evidence receives little explanation.
- **Include when.** Recorded regions show more space or structure for generic framing than for explaining the data, AND the data shown gets little explanation.
- **Exclude.** Short copy, a minimal interface, or a familiar story arc as such.
- **Minimum evidence.** At least two recorded regions of generic scaffolding and the data region(s) they surround. (at least 2 regions)
- **Modalities.** screenshot or text+dom
- **Positive example.** Four sections of mission statements and feature cards precede one unlabeled chart with a one-line caption.
- **Legitimate counterexample.** A short story with a hook, one well-annotated chart, and a takeaway.
- **Alternative explanations.** Course structure (hook, takeaway); Time constraints; Data still being prepared
- **Boundary.** Page-level scaffolding imbalance in data stories is DAT-04. It is the primary code over LAY-02 in data-story profiles; add LAY-02 as a secondary tag when the scaffolding follows the stock landing-page sequence.
- **Sources.** SRC-SEGEL-HEER2010, SRC-DSC106-SPEC

## OTHER-CANDIDATE: Exploratory candidate outside the codebook

A specific observable pattern outside the codebook that may contribute to a perceived-slop impression. Record it in exploratory_candidates with a free-text label, its observation, locations, and evidence. It is reported separately from closed-codebook results and is never silently added to the scored rubric; adding it requires a new rubric version.

## Changelog

- **0.1.0** (2026-11-07): Initial codebook from the seed taxonomy (families A–D, OTHER-CANDIDATE). Boundary rules added: palette packages VIS-01, typographic devices VIS-02, decorative objects VIS-03; interaction-produced conflicts INT-02 with SUB-02 as secondary tag; chart–claim conflicts DAT-01; SUB-01 split into three named sub-types. No feature has corpus_specific_empirical status.
- **0.1.1** (2026-11-08): Primary-code rule between LAY-02 and DAT-04 made explicit (DAT-04 primary in data-story profiles). Motivated by a development eval where a stock skeleton displacing a data story was coded LAY-02 by the auditor and DAT-04 by the developer reference; both were defensible under 0.1.0. No feature added or removed.
