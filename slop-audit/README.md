# website-slop-audit: perceived AI-slop feature auditor

A research instrument for identifying **which parts of a website may trigger
perceived AI-slop judgments, on what evidence, with what uncertainty**, and for
comparing models on that task fairly. It identifies and localizes features. It
does not redesign sites, score quality, or decide who or what made a site.

Construct (a provisional operational definition chosen for this project): a
perceived AI-slop feature is a localized or cross-region pattern that can
contribute to an impression of default-driven, interchangeable, superficial,
or insufficiently integrated production. Neither the pattern nor the
impression establishes who or what produced the website.

## Three layers

| Layer | Where | What it is |
|---|---|---|
| A. Portable reasoning | [`website-slop-audit/`](website-slop-audit/) | The skill: `SKILL.md`, codebook (`assets/codebook.json` → `references/feature-codebook.md`), output contract, schemas, standard-library scripts, worked examples. No host tool names. |
| B. Evidence acquisition | [`integrations/capture/`](integrations/capture/) | Adapters that produce frozen capture bundles: live capture through gstack browse, and a builder for supplied artifacts. |
| C. Evaluation | `website-slop-audit/scripts/` (validate, expand, import, score) and [`integrations/baselines/`](integrations/baselines/) | Model-free validation, canonical prompt packages, run import, offline scoring, and the comparison baselines. |

Claude-specific notes live in [`integrations/claude/`](integrations/claude/), outside the portable core.

## Shortest commands

From `slop-audit/website-slop-audit/` (Python 3.11+, standard library only):

```bash
# audit a supplied bundle: freeze it, then build the canonical prompt for any model
python scripts/validate_bundle.py BUNDLE --freeze
python scripts/expand_prompt.py --bundle BUNDLE --profile multimodal-datastory --out pkg/

# export the canonical prompt for another model: send pkg/prompt.md plus pkg/attachments/* in order
cat pkg/prompt.lock.json          # prompt_sha256 and package_sha256 to log with the run

# validate a model's response (and keep the raw text as a run)
python scripts/import_run.py --raw reply.txt --package pkg/ --bundle BUNDLE --condition frozen-skill \
  --provider PROVIDER --model-id MODEL --access-path "manual chat" --out runs/
python scripts/validate_audit.py runs/RUN_ID/audit.json --bundle BUNDLE
python scripts/render_report.py runs/RUN_ID/audit.json --bundle BUNDLE --out report.html

# score saved responses against human annotations
python scripts/score_benchmark.py --runs runs/ --annotations annotations/ --bundles bundles/ --out scores/
```

In a host that loads skills natively, point it at `website-slop-audit/` and
give it the bundle path; it follows the same `SKILL.md`.

## Compatibility levels

| Level | How | Reported |
|---|---|---|
| Native skill loading | The host reads `website-slop-audit/` (Agent Skills format: only `name` and `description` frontmatter, relative references) | Envelope logged in the run record |
| Manual instruction package | `expand_prompt.py` writes identical prompt bytes and images for any model or chat interface | Same table as native for the same profile |
| Reduced capability | `text-only-*` profiles: no images; visual checks unassessed | Separate table; never ranked with multimodal runs |

## Status: what works and what is untested

Verified in this workspace (2026-11-08):

| Component | Status |
|---|---|
| Schemas, bundle validator, audit validator, codebook generator | Working; 144 tests pass, 1 opt-in live test skipped by default |
| Canonical prompt expansion with hashes, budgets, and freezing | Working; deterministic bytes verified |
| Report renderer (HTML and Markdown) | Working; escaping and local image paths tested |
| Run import (manual output path) and offline scorer | Working; known-answer tests for matching, undefined metrics, scope, repeats, bootstrap |
| gstack capture adapter (headless gstack browse) | Working on local fixture sites; one live re-capture test (opt-in) passes |
| Supplied-artifact bundle builder | Working (source-only fixture) |
| Generic-prompt baseline package | Working (package builds; evidence identical to the skill condition) |
| Deterministic local-checks baseline | Working on all fixtures |
| Skill Creator development evals (6 cases in [`website-slop-audit-evals/`](website-slop-audit-evals/), with and without skill, one model family, 2 iterations) | Results, benchmark notes, and review pages in [`website-slop-audit-workspace/`](website-slop-audit-workspace/). Iteration 2: with skill 24/24 assertions, scorer F1 1.0 against the developer's own (revised) annotations; tuning-set smoke test only |

Not run or untested:

- **Real multi-model experiment**: not run. No model APIs were called and no comparative results exist. The adapter contract (`import_run.py`) is provider-neutral; no provider SDK adapters are included.
- **Capture of real public sites**: the adapter has only captured local fixture pages. Public capture needs `--allow-public` and was not exercised; DSC 106 student sites were not captured or sent anywhere.
- **Impeccable detector**: not executed (needs its compiled engine). `impeccable_import.py` is tested only against the finding format in Impeccable's own test code; the rule mapping is in `integrations/baselines/README.md`.
- **Critique baseline with a model**: the package builder and the human-mapping converter work; no model has produced a critique for scoring.
- **Human annotation**: all annotation files are `synthetic_development` sets written by the developer. There is no independent reference set yet.
- **Native skill loading in other hosts**: only the instruction package format was verified with Skill Creator's `quick_validate`; loading in non-Claude hosts is untested.
- **Official `skills-ref` validator**: not run (fetching it from PyPI was blocked in this session). Run `uvx skills-ref validate website-slop-audit` to check.

Fixtures validate the pipeline and the auditor's handling of edge cases. They
do not establish that any model recognizes perceived slop accurately, that any
cue indicates AI production, or that one model is better than another.

## Development

```bash
cd slop-audit
uv run pytest                                   # all tests (live capture test skipped)
SLOP_LIVE_CAPTURE=1 uv run pytest -k live       # also re-capture a fixture through gstack browse
uv run python fixtures/build_fixtures.py        # re-capture every fixture site (needs gstack browse)
uv run python fixtures/references.py            # rewrite developer annotations and examples
uv run python fixtures/sync_evals.py            # rewrite website-slop-audit-evals/ from the fixtures
uv run python fixtures/grade_eval_runs.py website-slop-audit-workspace/iteration-2   # grade eval runs with code
uv run python website-slop-audit/scripts/build_codebook.py   # after editing assets/codebook.json
```

Dev dependencies are pinned in `pyproject.toml` (`jsonschema==4.26.0`,
`pytest==9.2.0`); the skill's own scripts need only the standard library.

## Where to read next

- Construct, features, anchors: [`references/feature-codebook.md`](website-slop-audit/references/feature-codebook.md)
- Sources and their limits: [`references/evidence-sources.md`](website-slop-audit/references/evidence-sources.md)
- Bundle contract and blinding: [`references/capture-protocol.md`](website-slop-audit/references/capture-protocol.md)
- Comparison design, annotation, metrics: [`references/benchmark-protocol.md`](website-slop-audit/references/benchmark-protocol.md)
- Fixtures and their expected invariants: [`fixtures/README.md`](fixtures/README.md)
