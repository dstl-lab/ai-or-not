# Claude-specific integration notes

Everything here is host-specific and deliberately kept out of the portable
skill. Nothing in this folder is required to use the skill with another model.

## Native loading in Claude Code (project-level, committed)

The repository root has `.claude/skills/website-slop-audit`, a relative
symlink to `slop-audit/website-slop-audit/`, so anyone who opens the
repository in Claude Code gets the command:

```
/website-slop-audit https://someone.github.io/project/
/website-slop-audit slop-audit/fixtures/bundles/injection
```

Claude Code passes the text after the command to the skill (it appends
`ARGUMENTS: …` because `SKILL.md` has no placeholder; the portable
frontmatter stays `name` and `description` only). Nothing was installed in
`~/.claude`. Setup, prerequisites (gstack browse, Python 3.11+), and the
Codex and Gemini equivalents are in `integrations/agents/README.md`.

Native loading changes the message envelope (the skill arrives through the
host's skill mechanism, not as one prompt) and lets the agent run the capture,
so record runs made this way as condition `native-workflow`, not as the
controlled `frozen-skill` condition. The frozen bundle the command writes can
still be reused for controlled runs.

## Claude API

Per the Claude Agent Skills overview (see `references/evidence-sources.md`,
SRC-CLAUDE-SKILLS), skills uploaded to the API run in a sandboxed container
without network access or runtime package installation, and custom skills do
not sync between claude.ai, Claude Code, and the API. The skill's scripts use
only the Python standard library for this reason. Live capture cannot run in
that sandbox; supply a frozen bundle.

## Development smoke tests with subagents

The development evals live in `slop-audit/website-slop-audit-evals/`, beside
the skill rather than inside it: their graders encode expected answers, and a
model loading the skill could otherwise list them. They were run with Claude
Code subagents following the Skill Creator workflow (with skill vs without
skill, same prompt, inputs copied to neutral paths). Results, grading,
benchmark notes, and review pages are in `website-slop-audit-workspace/`.
These runs use one model family on synthetic fixtures; they check that the
instructions are followable and that edge-case invariants hold. They are not a
benchmark and not a cross-model comparison.

To rerun the cases with the Claude Code CLI (real, billed model runs), link
the evals into the skill only for the duration of the run:

```bash
cd slop-audit && ln -s ../website-slop-audit-evals website-slop-audit/evals
(cd website-slop-audit && claude plugin eval . --allow-tools Write,Edit,Bash --scaffold)
rm website-slop-audit/evals
```

Subagents in this host cannot write report `.md` files; when a run returns its
report as text, save it verbatim to the run's `outputs/report.md`.

## Browsing in this workspace

The lab workspace requires gstack browse for web access. The capture adapter
(`integrations/capture/gstack_capture.py`) uses gstack's headless browser
(`$B`), which carries no personal cookies. Other hosts should write their own
adapter that produces the same bundle format.
