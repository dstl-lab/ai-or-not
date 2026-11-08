# Comparison baselines

The four conditions in `website-slop-audit/references/benchmark-protocol.md`, section 2.

| Condition | File | Status |
|---|---|---|
| 1. Generic identification prompt | `expand_generic.py`, `generic-identification.md` | Working: builds a package with the same evidence, schema, and response block as the skill condition; only the instructions differ (feature names, no definitions or rules). |
| 2. Frozen skill | `../../website-slop-audit/scripts/expand_prompt.py` | Working |
| 3. MCPmarket critique skill | `critique_baseline.py` | Package builder and human-mapping converter working; not run with a model |
| 4. Deterministic rules | `local_checks.py` (implemented); `impeccable_import.py` (mapping only) | Local checks working on all fixtures; Impeccable not executed |

## Condition 3: critique skill

Frozen by content hash, not copied into this repository: the installed file
`~/.claude/plugins/mcpmarket-me/skills/critique/SKILL.md` (MCPmarket version
1.0.0, sha256 `9ccb14232c31467e5d89bbfb7794a3ff5ae08d0c103273998fc9b1e32d6a5e57`
on 2026-11-07). `critique_baseline.py package` copies it and its required
`frontend-design` skill into the run directory and records both hashes.

Mismatches to report with any result:

- It requires an interactive `teach-impeccable` context step, which cannot run in a frozen benchmark; the bundle's neutral context replaces it.
- Its task is broader (a UX critique) and it ends with a pass/fail "Does this look AI-generated?" verdict plus redesign commands, which this rubric does not produce.
- Its free-form output is scored only after a human maps each claim to a codebook code, region, and disposition (`critique_baseline.py template` / `to-audit`). That is the relaxed, human-reviewed path; it is never scored by an LLM matcher.

## Condition 4: deterministic rules

`local_checks.py` runs seven transparent rules over captured text, computed
styles, and recorded interactions (never pixels or source). It reports
presence only: association is always `unassessed` and context is never read,
so appropriate uses fire too (for example the required brand gradient in the
`branded-gradient` fixture). That makes it a useful floor, not an origin
detector.

| Rule | Code | Trigger |
|---|---|---|
| gradient-text | VIS-02 | computed `background-clip: text` with a gradient image |
| tracked-caps-label | VIS-02 | two or more small uppercase labels with letter-spacing ≥ 0.1em |
| literal-placeholder | SUB-01 | lorem ipsum, TODO, "replace with", "insert … here" |
| marketing-buzzwords | TXT-01 | two or more of a fixed buzzword list in one span |
| unitless-stat-tiles | SUB-03 | two or more short numeric spans (10x, 99%, 24/7) in one region |
| repeated-emoji | VIS-03 | the same emoji in three or more spans |
| no-change-control | INT-01 | a completed click with no text or state change |

### Impeccable (pinned, mapped, not executed)

Inspected at `pbakaus/impeccable` commit `687bc381bc9091bf252c0a05303640561014a425`
(package 4.8.0, engine 0.1.18). The rule registry
(`crates/foundation/src/registry.rs`) has **62 rules: 31 category "slop" and
31 category "quality"** (list in `impeccable-rules.json`). The detector is a
compiled engine; it was not built or run here, so this integration is
untested end to end. `impeccable_import.py` converts its documented JSON
findings into per-code counts. Source scans report files and lines, not
bundle regions, so they are kept separate from rendered-region scoring.

| Impeccable rules | Codebook |
|---|---|
| ai-color-palette, cream-palette, dark-glow | VIS-01 |
| gradient-text, kicker-above-heading, hero-eyebrow-chip, numbered-section-labels, italic-serif-display | VIS-02 |
| nested-cards | LAY-01 |
| icon-tile-stack, radial-halo, radial-spotlight-glow, repeating-stripes-gradient, shape-assembled-illustration | VIS-03 |
| bounce-easing, pulsing-dot, marquee, blinking-cursor | MOT-01 |
| marketing-buzzword, theater-slop-phrase | TXT-01 |
| aphoristic-cadence | TXT-02 |
| broken-image, low-contrast, text-overflow, tiny-text, content-hidden-at-rest, text-occlusion | QLT-01 |

Deliberately not mapped: `overused-font` and `em-dash-overuse` (a font or a
punctuation mark alone is excluded as a stand-alone cue), and
`gpt-thin-border-wide-shadow` and `codex-grid-background` (their names imply a
generator identity, which this rubric does not infer). All other rules are
reported as unmatched. Codebook capabilities with no Impeccable counterpart
include LAY-02, SUB-01 to SUB-03, INT-01, INT-02, SRC-01, MED-01, and DAT-01
to DAT-04.
