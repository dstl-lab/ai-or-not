<!-- GENERATED from assets/codebook.json by scripts/build_codebook.py. Edit the JSON, then rebuild. -->


# Evidence sources ledger (rubric 0.1.1)

Each entry records what was read, at what access level, what it supports, and its limits. None of these sources validates an authorship detector. Practitioner guidance, empirical findings, and this project's own hypotheses are labeled separately (`kind`). Benchmark judgments must not do fresh web research; this ledger is fixed per rubric version.

## SRC-PROJECT-DEF

- **Citation.** Project team, UC San Diego data science lab. Provisional research definition and operational hypotheses for perceived AI-slop features (website-slop-audit rubric 0.1.0).
- **URL.** none (internal)
- **Kind.** `operational_choice` · **Access level.** `internal`
- **Section read.** definition; research_hypothesis entries
- **Version / date.** 2026-11
- **Supported proposition.** Defines the construct and the hypotheses (substance, integration, interaction, data-story families) this project will test.
- **Limitation.** An operational choice, not an empirical finding. Must be piloted with human raters.
- **Cited by features.** SUB-01, SUB-02, SUB-03, INT-01, INT-02, SRC-01, DAT-01, DAT-03

## SRC-AGENTSKILLS

- **Citation.** Agent Skills specification.
- **URL.** https://agentskills.io/specification
- **Kind.** `specification` · **Access level.** `full_text`
- **Section read.** Directory structure; Frontmatter; Progressive disclosure; File references; Validation
- **Version / date.** accessed 2026-11-07
- **Supported proposition.** A skill is a directory with SKILL.md; only name and description are required frontmatter; references use relative paths one level deep; SKILL.md should stay under 500 lines.
- **Limitation.** Optional fields (for example allowed-tools, marked experimental) are not supported uniformly across hosts.
- **Cited by features.** definition and protocol only

## SRC-CLAUDE-SKILLS

- **Citation.** Anthropic. Agent Skills overview (Claude Platform documentation).
- **URL.** https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview
- **Kind.** `specification` · **Access level.** `full_text`
- **Section read.** Where Skills work; Limitations and constraints
- **Version / date.** accessed 2026-11-07
- **Supported proposition.** Host loading differs: API skills run in a sandboxed container without network access or runtime package installation; custom skills do not sync across surfaces.
- **Limitation.** Vendor-specific; describes one host family only.
- **Cited by features.** definition and protocol only

## SRC-FRONTEND-DESIGN

- **Citation.** Anthropic. frontend-design skill (SKILL.md), anthropics/skills repository, commit 41bbe19d1a1a7eaab5e7bb9050a417e5c6cffc8f.
- **URL.** https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md
- **Kind.** `practitioner` · **Access level.** `full_text`
- **Section read.** Design principles; Process (calibration list of five clustered traits); More on writing in design
- **Version / date.** commit dated 2026-09-03; accessed 2026-11-07
- **Supported proposition.** Practitioner list of recurring generated-design defaults: cream/terracotta with serif display; near-black with one acid accent; broadsheet layout; the identical-rounded-card kit with gradient washes; template chrome (tracked all-caps eyebrows, middle-dot meta strings, spaced em-dash labels, monospace data labels, appended arrows); single-word headline accents; numbering only for real sequences; fade-and-slide entrances on every section; the big-number-plus-stats hero.
- **Limitation.** Generation guidance and design opinion, written by a model vendor about generated output. It states every trait is legitimate for some briefs. It provides no sensitivity, specificity, or perception data.
- **Cited by features.** VIS-01, VIS-02, LAY-01, LAY-02, VIS-03, MOT-01, TXT-01, SUB-03

## SRC-IMPECCABLE

- **Citation.** Bakaus, P. Impeccable (design skills and anti-pattern detector), pbakaus/impeccable, commit 687bc381bc9091bf252c0a05303640561014a425 (package 4.8.0, engine 0.1.18); detector documentation.
- **URL.** https://github.com/pbakaus/impeccable
- **Kind.** `practitioner` · **Access level.** `full_text`
- **Section read.** crates/foundation/src/registry.rs (rule registry); https://impeccable.style/docs/detector/
- **Version / date.** commit dated 2026-11-06; accessed 2026-11-07
- **Supported proposition.** A deterministic rule baseline: 62 registry rules (31 category 'slop', 31 category 'quality'); source scans and rendered-URL scans are distinct; intentional choices can be recorded as narrow ignores.
- **Limitation.** Rules are practitioner heuristics. Some rule ids name specific generators (gpt-thin-border-wide-shadow, codex-grid-background), which this rubric does not adopt as generator-identity cues. No validation of the rules as authorship or perception signals was found in the inspected scope.
- **Cited by features.** VIS-01, VIS-02, LAY-01, VIS-03, MOT-01, TXT-01, TXT-02, QLT-01

## SRC-BOUSSIOUX2026

- **Citation.** Boussioux, L., Zhao, Z., & Cho, K. (2026). One Tool, One Taste? How Vibe Coding Trades Collective Diversity for Individual Creativity. arXiv:2609.38183 (v1).
- **URL.** https://arxiv.org/abs/2609.38183
- **Kind.** `empirical_preprint` · **Access level.** `abstract_only`
- **Section read.** Abstract
- **Version / date.** v1 submitted 2026-08-05
- **Supported proposition.** Among 73 Lovable-built promotional sites by graduate students, embedding analysis found within-cohort visual concentration (88% of sites in six clusters under one specification; 3 to 12 clusters across sensitivity analyses), and perceived quality was not associated with atypicality. Motivates examining repeated layouts and production defaults.
- **Limitation.** Single platform and cohort; preprint; abstract only. Does not identify feature-level signatures and cannot separate model effects from platform scaffolding.
- **Cited by features.** VIS-01, LAY-02

## SRC-SHIN2026

- **Citation.** Shin, D., Gao, A., Pang, R. Y., Lee, J., Reinecke, K., & Tseng, E. (2026). Interrogating Design Homogenization in Web Vibe Coding. arXiv:2603.13036 (v1).
- **URL.** https://arxiv.org/abs/2603.13036
- **Kind.** `conceptual_preprint` · **Access level.** `abstract_only`
- **Section read.** Abstract
- **Version / date.** v1 submitted 2026-03-13
- **Supported proposition.** Conceptual framing: frictionless generation may homogenize web design; proposes productive friction as mitigation.
- **Limitation.** Conceptual risk analysis, not a feature classifier or ground truth; abstract only.
- **Cited by features.** SUB-02

## SRC-JAKESCH2023

- **Citation.** Jakesch, M., Hancock, J. T., & Naaman, M. (2023). Human heuristics for AI-generated language are flawed. PNAS 120(11). doi:10.1073/pnas.2208839120; arXiv:2206.07271 (v4).
- **URL.** https://doi.org/10.1073/pnas.2208839120
- **Kind.** `empirical` · **Access level.** `abstract_only`
- **Section read.** Abstract (arXiv record https://arxiv.org/abs/2206.07271)
- **Version / date.** arXiv v4 2023-03-14
- **Supported proposition.** Across six experiments (N = 4,600), people could not detect AI-generated self-presentations; their judgments relied on intuitive but flawed heuristics (first-person pronouns, contractions, family topics) that make judgments predictable and manipulable.
- **Limitation.** Language self-presentations, not websites; does not establish website-specific effects.
- **Cited by features.** TXT-01, TXT-02

## SRC-YEUNG2026

- **Citation.** Yeung, C., Weld, G., Mink, J., & Roesner, F. (2026). Is This AI? Longitudinal Analysis of Strategies Used for AI Detection on Two Subreddits. arXiv:2606.22689 (v2).
- **URL.** https://arxiv.org/abs/2606.22689
- **Kind.** `empirical_preprint` · **Access level.** `abstract_only`
- **Section read.** Abstract
- **Version / date.** v2 2026-06-25
- **Supported proposition.** Catalogs 12 community AI-detection strategies over 2 years and 8 months (13,098 posts, 222,060 comments), including fine-grained physical details, and finds strategies shift with model capabilities and social trends.
- **Limitation.** Documented strategies, not demonstrated detection accuracy; mostly media, not websites; abstract only.
- **Cited by features.** MED-01

## SRC-LIBANKS2026

- **Citation.** Li, Z., & Banks, J. (2026). Defective, Amplified, Contested: Folk Conceptualizations of AI Slop. arXiv:2610.14231 (v1).
- **URL.** https://arxiv.org/abs/2610.14231
- **Kind.** `empirical_preprint` · **Access level.** `abstract_only`
- **Section read.** Abstract
- **Version / date.** v1 2026-10-09
- **Supported proposition.** Users conceptualize slop as audience-contested content with constitutional defects enabled by platform logics; supports eliciting audience judgments rather than imposing one taste standard.
- **Limitation.** Social-media content, descriptive thematic analysis; abstract only.
- **Cited by features.** definition and protocol only

## SRC-UICRIT2024

- **Citation.** Duan, P., Chen, C., Li, G., Hartmann, B., & Li, Y. (2024). UICrit: Enhancing Automated Design Evaluation with a UICritique Dataset. arXiv:2407.08850 (v3).
- **URL.** https://arxiv.org/abs/2407.08850
- **Kind.** `empirical` · **Access level.** `abstract_only`
- **Section read.** Abstract
- **Version / date.** v3 2024-08-13
- **Supported proposition.** 3,059 critiques and ratings of 983 mobile UIs from seven experienced designers; informs expert annotation design and critique specificity.
- **Limitation.** Mobile UI quality critique, not an AI-slop dataset; abstract only.
- **Cited by features.** definition and protocol only

## SRC-DUAN-CRITIQUE2024

- **Citation.** Duan, P., Cheng, C.-Y., Hartmann, B., & Li, Y. (2024). Visual Prompting with Iterative Refinement for Design Critique Generation. arXiv:2412.16829 (v2).
- **URL.** https://arxiv.org/abs/2412.16829
- **Kind.** `empirical` · **Access level.** `abstract_only`
- **Section read.** Abstract
- **Version / date.** v2 2025-05-22
- **Supported proposition.** Critique comments linked to bounding boxes are a precedent for spatial grounding; an iterative pipeline outperformed a baseline for expert raters.
- **Limitation.** Model-generated boxes require validation; an iterative pipeline has a different budget from a one-call baseline; abstract only.
- **Cited by features.** definition and protocol only

## SRC-ZHENG2023

- **Citation.** Zheng, L., et al. (2023). Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena. arXiv:2306.05685 (v4).
- **URL.** https://arxiv.org/abs/2306.05685
- **Kind.** `empirical` · **Access level.** `abstract_only`
- **Section read.** Abstract
- **Version / date.** v4 2023-12-24
- **Supported proposition.** Model judges show position, verbosity, and self-enhancement biases; motivates fixed protocols and non-LLM matching.
- **Limitation.** Agreement on conversational preferences does not validate this task; abstract only.
- **Cited by features.** definition and protocol only

## SRC-OREL2026

- **Citation.** Orel, D., Azizov, D., Paul, I., Wang, Y., Gurevych, I., & Nakov, P. (2026). AICD Bench: A Challenging Benchmark for AI-Generated Code Detection. arXiv:2602.02079 (v1).
- **URL.** https://arxiv.org/abs/2602.02079
- **Kind.** `empirical_preprint` · **Access level.** `abstract_only`
- **Section read.** Abstract
- **Version / date.** v1 2026-02-02
- **Supported proposition.** AI-generated code detection remains far below practical usability under distribution shift and for hybrid or adversarial code; supports keeping source observations separate from provenance claims.
- **Limitation.** Code detection, not rendered websites; abstract only.
- **Cited by features.** SRC-01

## SRC-SEGEL-HEER2010

- **Citation.** Segel, E., & Heer, J. (2010). Narrative Visualization: Telling Stories with Data. IEEE TVCG (Proc. InfoVis). doi:10.1109/TVCG.2010.179.
- **URL.** https://idl.uw.edu/papers/narrative
- **Kind.** `conceptual` · **Access level.** `abstract_only`
- **Section read.** Abstract (author page)
- **Version / date.** 2010
- **Supported proposition.** Vocabulary for narrative visualization genres and the balance between author-driven narrative flow and reader-driven exploration; used for the data-story module.
- **Limitation.** A 2010 design-space review; not about AI or slop; abstract only.
- **Cited by features.** DAT-01, DAT-02, DAT-03, DAT-04

## SRC-DSC106-SPEC

- **Citation.** UC San Diego DSC 106 final-project specification (Winter 2025) and Spring 2026 final-project showcase.
- **URL.** https://dsc-courses.github.io/dsc106-2026-sp/showcase/
- **Kind.** `corpus_context` · **Access level.** `full_text`
- **Section read.** Final project requirements (D3, hook, and-but-therefore storytelling, annotations, takeaway); showcase listing
- **Version / date.** read 2026-10-20 and 2026-10-21
- **Supported proposition.** A shared course rubric can explain repeated chapter structures (hook, body, takeaway), required interaction, and similar chart styles across student projects; an alternative explanation for skeleton and scaffolding cues.
- **Limitation.** Context for one corpus; does not describe any individual project's production.
- **Cited by features.** LAY-02, DAT-02, DAT-04
