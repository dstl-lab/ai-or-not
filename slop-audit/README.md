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
| B. Evidence acquisition | [`integrations/capture/`](integrations/capture/) | Adapters that produce frozen capture bundles through gstack browse: a whole site from one URL (`site_capture.py`), a page from a hand-written plan (`gstack_capture.py`), and a builder for supplied artifacts. |
| C. Evaluation | `website-slop-audit/scripts/` (validate, expand, import, score) and [`integrations/baselines/`](integrations/baselines/) | Model-free validation, canonical prompt packages, run import, offline scoring, and the comparison baselines. |

Claude-specific notes live in [`integrations/claude/`](integrations/claude/), outside the portable core.

## One command

Open the repository root in Claude Code and type:

```
/website-slop-audit https://someone.github.io/project/
```

In Codex type `$website-slop-audit URL`; in Gemini CLI, `/website-slop-audit URL`.
A script, not the model, captures the site: pages under the URL's folder (up
to 12), screenshots from one budget of 64, and each safe control clicked once
(up to 10 per page), frozen into one bundle. The agent then audits the bundle,
validates the result, and writes `audit.json`, `report.html`, and `report.md`
to `slop-audit/local-runs/<site>-<time>/` (git-ignored). Options go after the
URL: `--single-page`, `--max-pages 3`, `--budget 8`, `--withhold "Name"`.

It needs Python 3.11+ and gstack browse. Setup and per-agent steps are in
[`integrations/agents/README.md`](integrations/agents/README.md).

The command is for everyday use. For the controlled comparison with human
raters and for chat apps, use the step-by-step path below: the bundle the
command writes can be reused there, because the capture does not depend on
which model asked for it.

## Shortest commands (step by step)

From `slop-audit/website-slop-audit/` (Python 3.11+, standard library only):

```bash
# capture a site into a frozen bundle (prints RUN_DIR and BUNDLE); --budget 8 keeps it chat-app sized
python scripts/acquire_url.py https://someone.github.io/project/ --budget 8

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

In a host that loads skills natively, the one-line command above does all of
this; it follows the same `SKILL.md`.

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
| Schemas, bundle validator, audit validator, codebook generator | Working; 159 tests pass, 2 opt-in live tests skipped by default (both pass with `SLOP_LIVE_CAPTURE=1`) |
| Canonical prompt expansion with hashes, budgets, and freezing | Working; deterministic bytes verified |
| Report renderer (HTML and Markdown) | Working; escaping and local image paths tested |
| Run import (manual output path) and offline scorer | Working; known-answer tests for matching, undefined metrics, scope, repeats, bootstrap |
| gstack capture adapter (headless gstack browse) | Working on local fixture sites and three mirrored DSC 106 sites; one live re-capture test (opt-in) passes |
| One-line URL capture (`site_capture.py` via `scripts/acquire_url.py`) | Working on a local multi-page fixture (opt-in live test: pages, robots.txt, 404, refused and untested controls, scroll-revealed controls, masking) and on one public DSC 106 site |
| `/website-slop-audit URL` in Claude Code | Tested end to end once (2026-11-08, headless, one public DSC 106 site): capture, audit, validation, and both reports from one line; the audit validated and its quotes match the captured text. About 21 minutes, 72 turns, and $9.76 at API prices for a two-page site |
| `$website-slop-audit` in Codex, `/website-slop-audit` in Gemini CLI | Files in place (`.agents/skills/`, `.gemini/commands/`); untested, see `integrations/agents/README.md` |
| Supplied-artifact bundle builder | Working (source-only fixture) |
| Generic-prompt baseline package | Working (package builds; evidence identical to the skill condition) |
| Deterministic local-checks baseline | Working on all fixtures |
| Skill Creator development evals (6 cases in [`website-slop-audit-evals/`](website-slop-audit-evals/), with and without skill, one model family, 2 iterations) | Results, benchmark notes, and review pages in [`website-slop-audit-workspace/`](website-slop-audit-workspace/). Iteration 2: with skill 24/24 assertions, scorer F1 1.0 against the developer's own (revised) annotations; tuning-set smoke test only |

Not run or untested:

- **Real multi-model experiment**: not run. No model APIs were called and no comparative results exist. The adapter contract (`import_run.py`) is provider-neutral; no provider SDK adapters are included.
- **Capture of real public sites at scale**: the one-line capture has been run on one public DSC 106 site (two pages) and on local copies of three others; nothing beyond that. Sites behind sign-ins, heavy client-side routing (single-page apps with `#/` routes), or bot protection are untested.
- **Impeccable detector**: not executed (needs its compiled engine). `impeccable_import.py` is tested only against the finding format in Impeccable's own test code; the rule mapping is in `integrations/baselines/README.md`.
- **Critique baseline with a model**: the package builder and the human-mapping converter work; no model has produced a critique for scoring.
- **Human annotation**: all annotation files are `synthetic_development` sets written by the developer. There is no independent reference set yet.
- **Native skill loading in other hosts**: the skill folder passes Skill Creator's `quick_validate`, and Codex and Gemini CLI files are in place, but loading and running the command in those hosts is untested.
- **Official `skills-ref` validator**: not run (fetching it from PyPI was blocked in this session). Run `uvx skills-ref validate website-slop-audit` to check.

Fixtures validate the pipeline and the auditor's handling of edge cases. They
do not establish that any model recognizes perceived slop accurately, that any
cue indicates AI production, or that one model is better than another.

## Development

```bash
cd slop-audit
uv run pytest                                   # all tests (live capture test skipped)
SLOP_LIVE_CAPTURE=1 uv run pytest -k live       # also capture fixtures through gstack browse (single page and multi-page site)
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
