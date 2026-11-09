# One-line command in Claude Code, Codex, and Gemini CLI

Anyone who opens this repository with one of these agents can audit a site
with a single line:

| Agent | Type this | Where it comes from | Status |
|---|---|---|---|
| Claude Code | `/website-slop-audit https://site.example/` | `.claude/skills/website-slop-audit` (link to the skill) | Tested end to end once (headless, 2026-11-08) |
| Codex CLI / IDE | `$website-slop-audit https://site.example/` (or pick it from `/skills`) | `.agents/skills/website-slop-audit` (same link) | Written from the official docs; untested |
| Gemini CLI | `/website-slop-audit https://site.example/` | `.gemini/commands/website-slop-audit.toml`, plus the skill in `.agents/skills/` | Written from the official docs; untested |

All three point at the same folder, `slop-audit/website-slop-audit/`. The
links are relative symlinks committed to the repository, so a clone works
without installing anything into your home folder. A bundle path works in
place of the URL.

## What happens when you run it

1. The agent reads the skill's `SKILL.md`.
2. It runs `python3 scripts/acquire_url.py URL`, which hands the URL to
   `integrations/capture/site_capture.py`. That script (not the model)
   finds the site's pages under the URL's folder (12 at most), screenshots
   them, clicks each safe control once (10 per page at most), and freezes a
   bundle. Expect 1 to 5 minutes. Nothing is typed, submitted, downloaded, or
   followed off-site.
3. The agent audits the frozen bundle with the codebook, validates its JSON,
   and renders the report.
4. It replies with a short summary and the paths.

Everything lands in `slop-audit/local-runs/<site>-<time>/`, which git
ignores: `bundle/` (frozen evidence), `plan.json`, `site.json`,
`audit.json`, `report.html`, `report.md`.

Options go after the URL, for example
`/website-slop-audit https://site.example/ --single-page` or
`--max-pages 3`, `--budget 8` (small enough to paste into chat apps), or
`--withhold "Team Member Name"` (masks names in captured text and blinds the
bundle).

## Prerequisites (every agent)

- Python 3.11 or newer as `python3`. No packages: the skill and the capture
  adapter use only the standard library.
- **gstack browse**, the headless browser the capture drives. Install gstack
  (needs Git and [Bun](https://bun.sh/)):

  ```bash
  git clone --single-branch --depth 1 https://github.com/garrytan/gstack.git ~/.claude/skills/gstack && cd ~/.claude/skills/gstack && ./setup
  ```

  The capture looks for `~/.claude/skills/gstack/browse/dist/browse`. If your
  gstack lives elsewhere (for example a setup for another agent), point to it:
  `export GSTACK_BROWSE=/path/to/browse/dist/browse`.
- Start the agent **from the repository root** (`ai-or-not/`).
- On Windows, git must check out symlinks (`git config core.symlinks true`
  with Developer Mode on) or the skill folders will be plain text files. If
  they are, copy `slop-audit/website-slop-audit` into `.claude/skills/` and
  `.agents/skills/` instead.

Quick check that capture works on your machine, with no model involved:

```bash
python3 slop-audit/website-slop-audit/scripts/acquire_url.py https://jaredw022.github.io/drying-out-atlas/ --single-page --out /tmp/slop-check
```

It should end with `VALID: …`, then `RUN_DIR=`, `BUNDLE=`, and
`SUGGESTED_PROFILE=` lines.

## Claude Code

1. Open Claude Code in the repository root and type `/website-slop-audit`;
   it should autocomplete. If it does not, run `/skills` and check that
   `website-slop-audit` is listed, then restart the session.
2. Run `/website-slop-audit https://jaredw022.github.io/drying-out-atlas/`.
3. Approve the `python3 …` commands when asked (or allow `Bash(python3:*)`
   for the session).

Headless, the way it was tested here:

```bash
claude -p "/website-slop-audit https://jaredw022.github.io/drying-out-atlas/" --allowedTools "Bash(python3:*)" "Bash(cd:*)" "Bash(ls:*)" "Read" "Write" "Edit" "Glob" "Grep"
```

That run (2026-11-08, a two-page DSC 106 site) captured 2 pages and 21
screenshots, wrote an audit that validated with 3 findings, 4 contextual
exceptions, 8 quality observations, and 2 exploratory candidates, and
rendered both reports. It took about 21 minutes and 72 turns and cost $9.76
at API prices (most of it cached input: the conversation is re-read on every
turn). Four commands outside that allow-list were refused (an `ls ~/…`,
compound `cd … && …` lines, and a Python heredoc that patched `audit.json`);
the agent worked around them. In an interactive session you would approve
those instead. Use `--single-page` or a smaller `--max-pages` to cut time and
cost on big sites.

## Codex (CLI, IDE extension, or app)

Codex reads skills from `.agents/skills/` in every folder from where you
start it up to the repository root, and you call one by mentioning it.

1. Start `codex` in the repository root. Run `/skills` and check that
   `website-slop-audit` is listed.
2. Type `$website-slop-audit https://jaredw022.github.io/drying-out-atlas/`.
3. Network: Codex's default `workspace-write` sandbox blocks outbound
   network, and gstack keeps its browser state in `~/.gstack`, outside the
   workspace. The capture step therefore needs a looser sandbox for this
   run, for example in `~/.codex/config.toml`:

   ```toml
   sandbox_mode = "workspace-write"
   [sandbox_workspace_write]
   network_access = true
   writable_roots = ["~/.gstack"]
   ```

   Or keep the sandbox and run the capture yourself in a terminal, then hand
   Codex the bundle: `python3 slop-audit/website-slop-audit/scripts/acquire_url.py URL`,
   then `$website-slop-audit slop-audit/local-runs/<run>/bundle`.

What to check: a `slop-audit/local-runs/<site>-<time>/` folder with
`audit.json` that passes
`python3 slop-audit/website-slop-audit/scripts/validate_audit.py <run>/audit.json --bundle <run>/bundle`,
and `report.html`.

## Gemini CLI

Gemini CLI reads custom commands from `.gemini/commands/` and Agent Skills
from `.agents/skills/` (and `.gemini/skills/`). Google's docs note that for
unpaid and Google One users Gemini CLI was replaced by Antigravity CLI on
2026-06-18; the same files are what to try there.

1. Start `gemini` in the repository root (the command injects
   `@{slop-audit/website-slop-audit/SKILL.md}`, a path relative to the
   workspace). If you added the file while Gemini was running, run
   `/commands reload`.
2. Type `/website-slop-audit https://jaredw022.github.io/drying-out-atlas/`.
3. Approve the shell commands it proposes (`cd slop-audit/website-slop-audit && python3 scripts/…`).
   If Gemini asks to activate the `website-slop-audit` skill as well, allow it.
4. If you run Gemini with its sandbox on, the capture needs network access
   and write access to `~/.gstack`; otherwise run the capture step yourself
   as described for Codex and give Gemini the bundle path.

What to check: the same files as for Codex.

## Reporting a test result

When you try Codex or Gemini, note the agent and version, the exact line you
typed, whether the capture step ran inside the agent, whether `audit.json`
validated on the first try, and anything you had to change. Then update the
status table above and the one in `slop-audit/README.md`.
