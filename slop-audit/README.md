# website-slop-audit: one-command version

This skill looks at a website and reports **which parts of it may make it feel
AI-generated, generic, or "sloppy", where they are, and on what evidence**. It
also answers the PhD study's per-website questions (for example "How much of
this site did AI build?" and the 0–10 feature grid) in the same format the PhD
participants use, so you can put the two side by side.

This branch (`slop-skill-command-questions`) is the **one-command version**.
Open the repository in Claude Code, Codex, or Gemini CLI and type one line with
a website address; the rest happens on its own. The step-by-step version (any
model, including chat apps, with a hand-written capture plan) is on the branch
`slop-skill-questions`, and every step-by-step command also works here
(see "Without an agent" below).

> The skill reports how a site *comes across*. It never decides who or what
> made a site, and its "AI" ratings are impressions, not facts about how the
> site was built.

---

## Quick start

```
/website-slop-audit https://someone.github.io/project/
```

Type that in **Claude Code** opened at the repository root, wait about 10 to 25
minutes, and open the `report.html` it points you to. In Codex type
`$website-slop-audit https://…`; in Gemini CLI the same `/website-slop-audit https://…`.

---

## What you get for each website

Everything goes into a new folder, `slop-audit/local-runs/<site>-<time>/`, which
git ignores (so captures of student sites are never committed by accident):

| File | What it is |
|---|---|
| `bundle/` | A frozen capture of the site: screenshots, the text of every page, the page structure, and what happened when each safe control was clicked. |
| `plan.json`, `site.json` | What the capture did: which pages it found, what it clicked, what it skipped and why. |
| `audit.json` | The full result: located findings, cues that were present but fine in context, quality issues, what could not be checked, and the answers to the study's questions. |
| `report.html` / `report.md` | The same result, readable. The study answers are at the top. |
| `responses_wide.csv` | The study answers as one row, using the **same column names and values as the PhD study's export** (`ai_appearance`, `feature_rating__charts`, `ai_extent`, …). |
| `marks.csv` | The spots the model "clicked" as feeling AI-generated, in the study's `marks.csv` columns. |
| `questionnaire_reasons.csv` | The reason behind every answer and the evidence it rests on. |

The agent also replies in the chat with a short summary: what was covered, the
main findings, the study answers, and these paths.

---

## Before you start (one time)

1. **Python 3.11 or newer** as `python3` (check with `python3 --version`).
   Nothing else to install for the skill itself.
2. **Get the code** on this branch:

   ```bash
   git clone https://github.com/dstl-lab/ai-or-not.git
   ```
   ```bash
   cd ai-or-not && git checkout slop-skill-command-questions
   ```

3. **gstack browse**, the headless browser that captures the site (it uses no
   personal logins). Install gstack once (needs [Git](https://git-scm.com/)
   and [Bun](https://bun.sh/)):

   ```bash
   git clone --single-branch --depth 1 https://github.com/garrytan/gstack.git ~/.claude/skills/gstack && cd ~/.claude/skills/gstack && ./setup
   ```

   The capture looks for `~/.claude/skills/gstack/browse/dist/browse`. If yours
   is elsewhere, run `export GSTACK_BROWSE=/path/to/browse` before starting the
   agent.
4. **One agent**: Claude Code, Codex CLI, or Gemini CLI. The command is
   already wired into the repository (`.claude/skills/`, `.agents/skills/`,
   `.gemini/commands/`); you install nothing into your home folder.

**Check that capture works, with no model involved** (from the repository root):

```bash
python3 slop-audit/website-slop-audit/scripts/acquire_url.py https://jaredw022.github.io/drying-out-atlas/ --single-page --out /tmp/slop-check
```

It should end with `VALID: …` and then `RUN_DIR=`, `BUNDLE=`, and
`SUGGESTED_PROFILE=` lines.

---

## Audit a website, step by step (Claude Code)

1. Open a terminal **in the repository root** (`ai-or-not/`) and start Claude
   Code (`claude`).
2. Type `/website-slop-audit` and check that it autocompletes. If it does not,
   type `/skills` to see whether `website-slop-audit` is listed, then restart
   Claude Code.
3. Type the command with the site's address:

   ```
   /website-slop-audit https://someone.github.io/project/
   ```

4. Approve the `python3 …` commands when Claude asks (or allow
   `Bash(python3:*)` for the session). What happens:
   - **Capture (1–5 minutes).** A script, not the model, opens the URL, finds
     the site's pages (same site, under the URL's folder, at most 12), takes
     up to 64 screenshots (every page's top, the first page top to bottom,
     phone views), and clicks each safe control once (at most 10 per page).
     It never types, submits forms, downloads files, follows links to other
     sites, or clicks anything that looks like sign-in, purchase, send, or
     delete, and it respects `robots.txt`.
   - **Audit (5–20 minutes).** Claude reads the capture page by page and
     records findings with their locations and evidence.
   - **Study answers.** It answers the ten study questions from that audit,
     each with a short reason.
   - **Check and export.** It validates its own result, renders the report,
     and writes the CSV files.
5. Open `report.html` from the folder it names, in your browser.

Because the capture is done by a script with fixed rules, the same URL gives
the same kind of evidence whichever agent asked for it.

### Options

Put options after the URL, for example
`/website-slop-audit https://someone.github.io/project/ --single-page`:

| Option | Effect |
|---|---|
| `--single-page` | Only the page at the URL (fastest, cheapest) |
| `--max-pages 3` | At most 3 pages (default 12) |
| `--max-controls 5` | At most 5 clicks per page (default 10) |
| `--budget 8` | At most 8 screenshots (default and maximum 64); 8 also fits chat apps |
| `--withhold "Full Name"` | Masks a name (for example a team member) in the captured text; repeat for several names |
| `--no-mobile` | Skip the phone-width screenshots |

### Codex and Gemini CLI

- **Codex:** start `codex` in the repository root, check `/skills` lists
  `website-slop-audit`, and type `$website-slop-audit https://…`. Codex's
  default sandbox blocks the network the capture needs; either allow it for
  this run or capture first in a terminal (see "Without an agent") and give
  Codex the bundle path instead of the URL.
- **Gemini CLI:** start `gemini` in the repository root and type
  `/website-slop-audit https://…`. Approve the shell commands it proposes.
  Google has replaced Gemini CLI with Antigravity CLI for unpaid and Google One
  users; the same repository files are what to try there.

Both are wired up from the official documentation but have not been tested
here. Exact settings and a checklist for reporting a test are in
[`integrations/agents/README.md`](integrations/agents/README.md).

---

## Reading the results

- **`report.html`** starts with the study answers (each with its reason and
  evidence ids), then the findings: what was found, where, the evidence, how
  strongly it fits a slop pattern, and other explanations. Then come cues that
  were present but fine in context, quality issues that are not slop, and what
  could not be checked.
- **The study answers** are the PhD form's ten per-website questions (Steven's
  version `phd-reviewer-v1`, dstl-lab/ai-or-not PR #6), copied word for word
  into [`website-slop-audit/assets/study-questions.json`](website-slop-audit/assets/study-questions.json):

  | Question | Answer format (same as the PhD form) |
  |---|---|
  | `ai_appearance`: how strongly the website appears AI-generated | 1–5 (Not at all to Extremely) |
  | `ai_marks`: the parts that feel AI-generated | numbered elements (page, kind, text, selector), or "none" |
  | `feature_rating`: how AI-generated each feature looks | 0–10 for Colors, Gradients, Fonts, Emoji/icons, Buttons and hover effects, Layout and spacing, Animations, Charts, Writing, Navigation; `NA` if the site has none |
  | `top_ai_feature`: which feature looks most AI-generated | one feature, or None |
  | `ai_extent`: how much of the site AI built | None, A little, About half, Most, Nearly all |
  | `design_generic`, `writing_ai`, `polish`, `quality` | 1–5 with the study's end labels |
  | `technical_issue`: did a technical problem affect the review | No / Yes, but could still evaluate / Could not evaluate |

  Not answered: `ai_changes_view`, `seen_before`, and the follow-up
  `annotations` and `cues`.
- **The CSV files** use the study export's column names, so you can open them
  next to the PhD export. `participant_id` is `website-slop-audit:<model>`.

---

## Auditing many sites (for example the 10 study sites)

1. Run the command once per site. Each run gets its own folder under
   `slop-audit/local-runs/`.
2. Collect every site's answers into one table, using the **study's project id**
   for each site (the ids in `config/sites.json`, such as `breathing-smoke`),
   from the `slop-audit/` folder:

   ```bash
   python3 website-slop-audit/scripts/export_study_csv.py local-runs/<run-folder>/audit.json --bundle local-runs/<run-folder>/bundle --out local-runs/answers --site-id breathing-smoke --rater "anthropic/claude-opus-5-5" --append
   ```

   Repeat for each run folder with its own `--site-id`. Every site adds one
   row to `local-runs/answers/responses_wide.csv` and its marks to
   `local-runs/answers/marks.csv`.

---

## Without an agent (or with a chat app)

You can split the work: capture with a script, then give the capture to any
model, including ChatGPT or Gemini in a browser. From `slop-audit/`:

1. Capture, kept small enough for chat apps:

   ```bash
   python3 website-slop-audit/scripts/acquire_url.py https://someone.github.io/project/ --budget 8 --max-pages 1
   ```

   Note the `RUN_DIR` and `BUNDLE` it prints.
2. Build the prompt package:

   ```bash
   python3 website-slop-audit/scripts/expand_prompt.py --bundle BUNDLE --profile multimodal-datastory --out RUN_DIR/pkg
   ```

3. In a new chat, paste all of `RUN_DIR/pkg/prompt.md` and attach the images in
   `RUN_DIR/pkg/attachments/` in filename order. Save the whole reply as
   `RUN_DIR/reply.txt`.
4. Import, check, and export:

   ```bash
   python3 website-slop-audit/scripts/import_run.py --raw RUN_DIR/reply.txt --package RUN_DIR/pkg --bundle BUNDLE --condition frozen-skill --provider openai --model-id MODEL_NAME --access-path "ChatGPT web app" --out RUN_DIR/runs
   ```
   ```bash
   python3 website-slop-audit/scripts/render_report.py RUN_DIR/runs/<run>/audit.json --bundle BUNDLE --out RUN_DIR/report.html
   ```
   ```bash
   python3 website-slop-audit/scripts/export_study_csv.py RUN_DIR/runs/<run>/audit.json --bundle BUNDLE --out local-runs/answers --site-id SITE --rater "openai/MODEL_NAME" --append
   ```

Use `multimodal-datastory` for data stories and visualization projects and
`multimodal-core` for other sites (`SUGGESTED_PROFILE` tells you which the
capture recommends).

---

## Time and cost

A run uses your agent's normal usage. On a Claude subscription it counts
against your plan's usage limits; with an API key it is billed per token. As a
guide, full runs on a two-page DSC 106 site took about 20 minutes and cost
about $10 at API prices without the study questions and about $16 with them
(most of it is the conversation being re-read each turn). `--single-page`, a smaller `--max-pages`, or `--budget 8` make runs
faster and cheaper. If a run stops on a usage limit, resume the same session
after the limit resets; the capture is already saved, so ask it to continue
from the existing `bundle/` instead of capturing again.

---

## Troubleshooting

| What you see | What to do |
|---|---|
| `/website-slop-audit` does not autocomplete | Start the agent from the repository root; run `/skills`; restart the agent. On Windows, git must check out symlinks (`git config core.symlinks true`). |
| `gstack browse binary not found` | Install gstack (above) or `export GSTACK_BROWSE=/path/to/browse`. |
| `No acquisition adapter is available` | The skill folder was copied out of the repository; run it from this repository. |
| `robots.txt disallows …` | The site asks crawlers not to open that page; nothing was captured. |
| A page listed as `failed: HTTP 404` | A broken link on the site; the rest was captured and the report notes it. |
| `capture failed: give a full http(s) URL` | Include `https://`. |
| The agent reports validation errors it cannot fix | The model cited something that is not in the capture; keep the result as a failure or rerun. |
| `You've hit your … limit` | Resume the session after the limit resets (see "Time and cost"). |

---

## Privacy and safety

- The capture is read-only and stays on the site you named. It never signs in,
  types, submits, downloads, or follows links to other sites.
- Text on a page that addresses an AI ("ignore your instructions…") is treated
  as data and recorded, never followed.
- The agent sends the captured pages to its model provider. Do not audit
  unpublished student work unless you are allowed to share it that way.
- Results stay in `slop-audit/local-runs/`, which git ignores.

---

## Reference (for developers)

### Three layers

| Layer | Where | What it is |
|---|---|---|
| A. Portable reasoning | [`website-slop-audit/`](website-slop-audit/) | The skill: `SKILL.md`, codebook (`assets/codebook.json` → `references/feature-codebook.md`), the study questions, output contract, schemas, standard-library scripts, worked examples. No host tool names. |
| B. Evidence acquisition | [`integrations/capture/`](integrations/capture/) | Adapters that produce frozen capture bundles through gstack browse: a whole site from one URL (`site_capture.py`), a page from a hand-written plan (`gstack_capture.py`), and a builder for supplied artifacts. |
| C. Evaluation | `website-slop-audit/scripts/` (validate, expand, import, score, export) and [`integrations/baselines/`](integrations/baselines/) | Model-free validation, canonical prompt packages, run import, offline scoring, study CSV export, and the comparison baselines. |

The agent wiring lives at the repository root: `.claude/skills/website-slop-audit` and
`.agents/skills/website-slop-audit` (relative links to the skill) and
`.gemini/commands/website-slop-audit.toml`. Claude-specific notes are in
[`integrations/claude/`](integrations/claude/); per-agent setup in
[`integrations/agents/`](integrations/agents/).

### Compatibility levels

| Level | How | Reported |
|---|---|---|
| Native skill loading | The host reads `website-slop-audit/` (Agent Skills format: only `name` and `description` frontmatter, relative references) | Envelope logged in the run record |
| Manual instruction package | `expand_prompt.py` writes identical prompt bytes and images for any model or chat interface | Same table as native for the same profile |
| Reduced capability | `text-only-*` profiles: no images; visual checks unassessed | Separate table; never ranked with multimodal runs |

### Status: what works and what is untested

Verified in this workspace (2026-11-14):

| Component | Status |
|---|---|
| Schemas, bundle validator, audit validator, codebook generator | Working; 190 tests pass, 2 opt-in live tests skipped by default (both pass with `SLOP_LIVE_CAPTURE=1`) |
| Study questionnaire (10 per-website questions, `phd-reviewer-v1`): schema, checks, report section, prompt, CSV export | Working. Tested end to end with `/website-slop-audit` in Claude Code (headless, 2026-11-14, a live public DSC 106 site): it captured the site, audited it, answered all ten questions, validated with 0 errors and 0 warnings, and wrote the report and the CSV files. The run was cut off once by a usage limit and resumed from the saved capture; about 21 minutes and $16 at API prices in total |
| Canonical prompt expansion with hashes, budgets, and freezing | Working; deterministic bytes verified |
| Report renderer (HTML and Markdown) | Working; escaping and local image paths tested |
| Run import (manual output path) and offline scorer | Working; known-answer tests for matching, undefined metrics, scope, repeats, bootstrap |
| gstack capture adapter (headless gstack browse) | Working on local fixture sites and three mirrored DSC 106 sites; one live re-capture test (opt-in) passes |
| One-line URL capture (`site_capture.py` via `scripts/acquire_url.py`) | Working on a local multi-page fixture (opt-in live test: pages, robots.txt, 404, refused and untested controls, scroll-revealed controls, masking) and on one public DSC 106 site |
| `/website-slop-audit URL` in Claude Code | Tested end to end (headless, one public DSC 106 site, 2026-11-08): capture, audit, validation, and both reports from one line; the audit validated and its quotes match the captured text. About 21 minutes, 72 turns, and $9.76 at API prices for a two-page site |
| `$website-slop-audit` in Codex, `/website-slop-audit` in Gemini CLI | Files in place (`.agents/skills/`, `.gemini/commands/`); untested, see `integrations/agents/README.md` |
| Supplied-artifact bundle builder | Working (source-only fixture) |
| Generic-prompt baseline package | Working (package builds; evidence identical to the skill condition) |
| Deterministic local-checks baseline | Working on all fixtures |
| Skill Creator development evals (6 cases in [`website-slop-audit-evals/`](website-slop-audit-evals/), with and without skill, one model family, 2 iterations) | Results, benchmark notes, and review pages in [`website-slop-audit-workspace/`](website-slop-audit-workspace/). Iteration 2: with skill 24/24 assertions, scorer F1 1.0 against the developer's own (revised) annotations; tuning-set smoke test only |

Not run or untested:

- **Real multi-model experiment**: not run. The adapter contract (`import_run.py`) is provider-neutral; no provider SDK adapters are included.
- **Capture of real public sites at scale**: the one-line capture has been run on one public DSC 106 site (two pages) and on local copies of three others. Sites behind sign-ins, heavy client-side routing (single-page apps with `#/` routes), or bot protection are untested.
- **Impeccable detector**: not executed (needs its compiled engine). `impeccable_import.py` is tested only against the finding format in Impeccable's own test code; the rule mapping is in `integrations/baselines/README.md`.
- **Critique baseline with a model**: the package builder and the human-mapping converter work; no model has produced a critique for scoring.
- **Human annotation**: all annotation files are `synthetic_development` sets written by the developer. There is no independent reference set yet.
- **Native skill loading in other hosts**: the skill folder passes Skill Creator's `quick_validate`, and Codex and Gemini CLI files are in place, but loading and running the command in those hosts is untested.
- **Official `skills-ref` validator**: not run. Run `uvx skills-ref validate website-slop-audit` to check.

Fixtures validate the pipeline and the auditor's handling of edge cases. They
do not establish that any model recognizes perceived slop accurately, that any
cue indicates AI production, or that one model is better than another.

### Development

```bash
cd slop-audit
uv run pytest                                   # all tests (live capture tests skipped)
SLOP_LIVE_CAPTURE=1 uv run pytest -k live       # also capture fixtures through gstack browse (single page and multi-page site)
uv run python fixtures/build_fixtures.py        # re-capture every fixture site (needs gstack browse)
uv run python fixtures/references.py            # rewrite developer annotations and worked examples
uv run python fixtures/sync_evals.py            # rewrite website-slop-audit-evals/ from the fixtures
uv run python fixtures/grade_eval_runs.py website-slop-audit-workspace/iteration-2   # grade eval runs with code
uv run python website-slop-audit/scripts/build_codebook.py   # after editing assets/codebook.json
```

Dev dependencies are pinned in `pyproject.toml` (`jsonschema==4.26.0`,
`pytest==9.2.0`, `pyyaml==6.0.3`); the skill's own scripts need only the
standard library.

### Where to read next

- Per-agent setup and testing: [`integrations/agents/README.md`](integrations/agents/README.md)
- How the one-line capture works: [`integrations/capture/README.md`](integrations/capture/README.md)
- Construct, features, anchors: [`references/feature-codebook.md`](website-slop-audit/references/feature-codebook.md)
- Output format and the study-questionnaire rules: [`references/output-contract.md`](website-slop-audit/references/output-contract.md)
- Bundle contract and blinding: [`references/capture-protocol.md`](website-slop-audit/references/capture-protocol.md)
- Comparison design, annotation, metrics: [`references/benchmark-protocol.md`](website-slop-audit/references/benchmark-protocol.md)
- Fixtures and their expected invariants: [`fixtures/README.md`](fixtures/README.md)
