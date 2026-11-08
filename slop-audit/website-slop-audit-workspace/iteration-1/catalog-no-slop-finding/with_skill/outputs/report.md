# Slop-feature audit audit-fx-catalog-conventional-01

bundle `fx-catalog-conventional` · profile `multimodal-core` · rubric 0.1.0 · status **completed**

## Scope and limits

No accepted slop findings in the assessed scope. The page is a plain, specific municipal catalog: a solid header, a concrete introduction naming the collection, publisher, listed fields, and license, a grid of parallel dataset listings with real formats, sizes, and dates, and a footer. The uniform card grid is present but recorded as a contextual exception, because the listings are genuinely parallel records and the card component is a documented style-guide requirement. The reserved example-domain contact address is recorded as an exception, not a placeholder finding. A quality observation, not a slop claim, notes that no download path was located in the captured scope. Interaction and source checks were not possible, and only one desktop viewport was captured.

- Assessed modalities: screenshot, text, dom, computed_style
- Not assessed: interaction (No interactions were recorded in the bundle (interactions list is empty; modality flag false).)
- Not assessed: source (No source excerpts were supplied (source_excerpts list is empty; modality flag false).)
- Limitation: Single desktop screenshot (1280x800, scroll 0) of one route; no mobile viewport, so responsive and small-screen checks were not possible.
- Limitation: No recorded interactions: INT-01 and INT-02 are unassessed; whether titles, the contact address, or any download path work is unknown.
- Limitation: No source excerpts: SRC-01 is unassessed.
- Limitation: Card containers and the page background have no captured computed styles; card borders and corners are described from the screenshot only.
- Limitation: Context provenance marks the capture plan as synthetic (development fixture).
- Counts: 0 findings, 2 contextual exceptions, 1 quality observation, 0 exploratory candidates, 3 unassessed features

These findings identify features that may contribute to a perceived AI-slop impression; they do not establish who or what made the site.

## Findings

No accepted findings in the assessed scope.

## Contextual exceptions

- X001 LAY-01: The dataset listing (R03) renders nine identical bordered cards in a three-column grid, each with a bold title and the same three-row Format / Size / Updated list. The uniform card treatment is clearly present. (appropriate_in_context: The LAY-01 inclusion rule is not met: the nine items are genuinely parallel dataset records (same role, same fields), so uniform cards hide no hierarchy. This matches the codebook's own legitimate counterexample (an open-data portal listing datasets as equal cards). The card component is also a documented requirement in the provided constraints and the footer.)
- X002 SUB-01: The footer's contact address uses the reserved '.example' top-level domain, which is set aside for documentation and does not resolve on the public internet. Read literally, it resembles placeholder contact data. (insufficient_evidence_for_finding: The address is consistent with the site's own naming (Riverton) and is not template text such as lorem ipsum or a bracketed fill-in; the bundle is labeled synthetic, so a reserved domain is the expected de-identification choice; no mail or link test was recorded. A single address does not support a placeholder finding.)

## Quality observations

- Q001 [usability]: The stated purpose ends in downloading, but no download link, button, or per-dataset link was located in the inspected scope: titles are captured as h2 elements with no anchor, and no control is visible in A01. The download path may live on detail pages or other routes that were not captured, and no click was recorded, so this is not called missing or broken.

## Exploratory candidates (not scored)

None recorded.

## Unassessed checks

- INT-01: Requires a completed recorded interaction; the bundle records none. No control is called broken.
- INT-02: Requires a completed recorded interaction; the bundle records none.
- SRC-01: Requires supplied source excerpts; the bundle has none.

## Run notes (process choices, not audit claims)

Everything above this section was generated from `audit.json` by `scripts/render_report.py`. This section only records how the run was done.

- **Profile.** `multimodal-core`, as requested. It fits: the screenshot was viewable, and the page is a dataset catalog, not a data story, so the data-story module (DAT-01 to DAT-04) would not apply.
- **Bundle.** `scripts/validate_bundle.py` reported VALID with 0 errors and 0 warnings. The bundle was already frozen (`bundle.lock.json` present, hash `63e65e4b…`), so I did not re-run `--freeze` and left the input unchanged.
- **Evidence used.** Only the frozen bundle: one desktop screenshot (A01), 67 DOM text spans, and 71 DOM elements with computed styles. No live site, no web access, a single judgment pass, and no verification pass.
- **Card grid.** I recorded it as a contextual exception (X001) rather than leaving it out, because the skill treats "present but appropriate" as a separate result from "absent". I picked `appropriate_in_context` over `documented_requirement` because the LAY-01 inclusion rule already fails on parallel content. The style-guide requirement is cited as supporting evidence.
- **Contact address.** The `.example` domain is recorded as a SUB-01 exception (X002), not a finding. The bundle is labeled synthetic, and reserved domains are the normal way to avoid real addresses.
- **Download path.** Q001 is a usability note scoped to the captured route. It makes no slop claim and does not say anything is broken.
- **Validation.** `scripts/validate_audit.py` reported VALID with 0 errors and 0 warnings.
- **Disclosure.** At the start I ran a recursive listing of the skill folder to find SKILL.md. That printed the *file names* under `evals/`, including grader file names for this case and others. I did not open any of those files, or any other folder outside the skill's instructions, references, schemas, scripts, assets, examples, and this bundle.
