# Benchmark protocol (draft for pilot, rubric 0.1.0)

How to compare models (and baselines) on the same frozen skill fairly. The
scorer `scripts/score_benchmark.py` implements the matching and metrics in
sections 5 and 6 exactly. Items marked **pilot decision** are provisional
choices to revisit after the pilot, not established standards.

Contents: 1 what is measured · 2 conditions · 3 controls · 4 compatibility
levels · 5 reference annotation · 6 matching and metrics · 7 primary metric
and decision rule · 8 uncertainty · 9 sampling · 10 perturbation checks ·
11 what results do not show · 12 commands.

## 1. What "better at identifying features" means

Three validation questions stay separate:

1. **Observation validity** (main engineering metric): is the reported feature present and correctly located in the supplied evidence, and does an accepted finding meet the codebook's inclusion and exclusion criteria?
2. **Perception alignment** (substantive research outcome): do independent human evaluators associate that feature with AI slop, and how much do they vary? Individual ratings are kept.
3. **Provenance validity** (optional, separate study): does an attribution judgment match independently documented production? Not measured by 1 or 2, and not claimed unless separately designed and validated.

Locating a gradient is not evidence that calling it a slop feature was right.
A system that finds many real conventions but condemns appropriate uses
incurs contextual false alarms and cannot win on accepted findings by volume.

## 2. Conditions

| Id | Condition | Notes |
|---|---|---|
| `generic-prompt` | Short identification prompt, same task and evidence and output schema, no codebook definitions or rules (`integrations/baselines/expand_generic.py`) | Isolates the effect of the skill's content. |
| `frozen-skill` | The same model with this frozen skill (`scripts/expand_prompt.py`) | Repeat across model families. |
| `critique-baseline` | The existing MCPmarket critique skill, frozen by hash with its frontend-design dependency (`integrations/baselines/critique_baseline.py`) | Broader task and free-form output; scored only on the human-mapped relaxed path. The interactive teach-impeccable step cannot run and is replaced by the bundle context. |
| `deterministic-baseline` | Transparent local rules (`integrations/baselines/local_checks.py`); Impeccable mapped where comparable (`impeccable_import.py`) | Presence only; source scans and rendered checks kept apart; not an origin detector. |
| `native-workflow` | Optional: a host's own skill loading and format | Labeled a workflow comparison, not a controlled model comparison. |
| `live-agent` | Optional ecological track with browsing under a recorded common budget | Compares agent systems, not isolated models. |
| `no-skill-dev` | Development only: the Skill Creator baseline, same task with no skill and no schema | Not a protocol condition. Its low strict scores mostly reflect the missing output contract, not perception; never report it as the generic-prompt condition. |

## 3. Controls for directly compared conditions

- Fresh session per run; no unrelated skills, memory, or conversation history.
- Identical prompt bytes (`prompt_sha256`) and images in the same order (`package_sha256`) for every model in a condition. Host envelopes (system vs user message, file upload) may differ and are logged in the run record.
- The same neutral context and the same output and finding budget. Never truncate an unconstrained critic after seeing its output and call it a primary baseline.
- No independent navigation in the controlled benchmark; the bundle is frozen first.
- One judgment call per run. A verification pass, if used, has identical instructions and cost for all systems, and the initial output is kept. A failing model never gets silent extra attempts; retries are counted.
- Log model id as reported by the endpoint, provider, date, system instructions hash, prompt and bundle hashes, transformations, output limits, reasoning settings if exposed, retries, parse failures, and parameters that were unavailable. A shared temperature value does not make different models equally stochastic.
- Keep every raw output and every repeated run (`scripts/import_run.py` never overwrites).

## 4. Compatibility levels

| Level | How the model receives the skill | Reported in |
|---|---|---|
| Native skill loading | The host loads `website-slop-audit/` itself | Its own rows; envelope logged |
| Manual instruction package | `prompt.md` plus `attachments/` pasted or uploaded | Same table as native when the profile matches |
| Reduced capability | A text-only profile; visual checks unassessed | A separate table, never ranked with multimodal runs |

Check, do not assume, whether a model can read images, follow structured
output, and use files. Keep the package within the common context and image
limits of all compared models: `expand_prompt.py --max-chars` and the
profile's image budget fail loudly rather than truncating.

## 5. Reference annotation

**Form** (`schemas/annotation.schema.json`): per item, region and state ids,
feature code, observed evidence, confidence, slop association, contextual
exception note, consequence, uncertainty, and a disposition:
`accepted_slop_candidate`, `contextual_exception`, `quality_only`,
`feature_absent`, or `unassessed`. Scopes declare which regions, states, and
codes were fully annotated. Annotators record relevant design,
visualization, and web experience; a degree title alone is not expertise.

**Procedure** (initial reproducibility protocol):

- Two independent annotators per bundle in the main coded set; a third adjudicator or a documented resolution process. Keep the pre-adjudication sets and their disagreements (`--human-sets`).
- Blind annotators to generator, model identity, and cohort year where feasible.
- Rubric-guided labels (`condition: rubric_guided`) and spontaneous cue elicitation (`unprompted`) are separate sets, never mixed.
- Development examples and any feedback used to tune the skill stay out of the held-out test set.
- If labels are incomplete, unmatched model findings are **unreviewed**, not false positives. Plausible novel findings go to a blinded review step. Reference-update rules are frozen before any model comparison.
- If two annotators plus adjudication cannot be resourced, say so; do not call the reference an independent gold standard. The fixtures in this project are `synthetic_development` sets written by the developer and validate plumbing only.

## 6. Matching and metrics (implemented in `score_benchmark.py`)

**Assessable scope.** For each code, the union of region × state pairs in
fully annotated scopes that list that code. A prediction is in scope only if
all its locations fall inside that union; otherwise it is unreviewed.

**Strict matching.** One-to-one, greedy by location Jaccard with
deterministic tie-breaks. A pair is compatible only if the feature codes are
equal, the location sets overlap, and a page-pattern prediction is not being
matched to a region-scope reference (a generic whole-page complaint cannot
absorb local issues). Findings are deduplicated by the validator first.
Relaxed semantic matching, if needed, is a separate human-reviewed mapping
frozen on development data; an LLM is never the sole matcher.

**Counts.** TP: in-scope prediction matched to an `accepted_slop_candidate`.
FP: any other in-scope prediction, broken down as contextual false alarm
(matched a `contextual_exception`), quality-as-slop (matched `quality_only`),
absent false alarm (matched `feature_absent`), or unsupported in annotated
scope (no reference item). FN: unmatched `accepted_slop_candidate`.

**Metrics.**

- Precision, recall, F1: micro over all codes, per code, per site, and macro over codes and over sites (macro averages only defined values and reports how many were defined).
- **Undefined values**: precision with no in-scope predictions, or recall with no positives, is `undefined`, never 0 or 1. F1 is undefined if either is undefined, and 0 when both are defined and TP is 0.
- Presence recognition: findings and contextual exceptions both assert presence; matched against references whose disposition says the feature is present. Reported separately from accepted-finding performance.
- Localization on true positives: mean region/state Jaccard, exact-set rate, and box IoU only where a prediction box and a reference box exist on the same image (threshold 0.5, **pilot decision**). Null prediction boxes where the reference has a box are counted, not penalized as zero IoU, and no pixel-accuracy claim is made from region-only references.
- Evidence validity: counts of validator error codes per system (missing asset/span/event/element/excerpt refs, quote mismatches, unobserved actions, fabricated selectors, invalid source lines, out-of-bounds boxes, and others). Reported even when other metrics are high.
- Abstention: share of annotated-scope features the audit marked unassessed. Shown beside precision so withholding everything is visible.
- Ordinal agreement on slop association for matched pairs: exact, within one level, and Spearman when at least three pairs vary. Human pairwise agreement from pre-adjudication sets is reported beside it. Agreement is not provenance accuracy.
- Run-to-run stability: mean pairwise Jaccard of finding keys across repeated runs of the same system and bundle.
- Operational: schema-valid and integrity-valid rates, parse failures, retries, latency, provider-reported tokens, and cost from a dated, researcher-supplied price table (never estimated). Token units are not comparable effort.
- Parse failures and schema-invalid outputs score as empty outputs (all positives missed) and are also counted separately.
- Repeated runs average within a site before aggregation; findings, crops, and repeats are never treated as independent sites.
- No weighted "best model" score is computed.

## 7. Primary metric and decision rule (fill in before the test)

**Primary metric:** strict accepted-finding micro F1 on fully annotated
assessable scopes, multimodal table. **Template decision rule (pilot
decision):** report system A as better than B on identification only if the
paired site-level bootstrap 95% interval for F1(A) − F1(B) excludes zero and A's
evidence-validity error rate per audit is not higher than B's. Otherwise
report the precision, recall, grounding, and cost tradeoffs without a winner.
Record the final rule, sample, and repetitions in a dated preregistration
before running the held-out set.

## 8. Uncertainty

`--compare A B` runs a paired bootstrap over sites shared by both systems
(default 2,000 resamples, fixed seed): sites are resampled with replacement
and micro F1 is recomputed for both systems on each resample. It assumes
sites are exchangeable and ignores annotator variance; hierarchical models
(sites, annotators, repeated runs) are future work and must be documented if
used.

## 9. Sampling (planning envelope)

Use a small pilot to estimate runtime and annotation load, then plan the main
sample and repetitions. A few dozen varied sites is a useful initial
envelope, not a justified universal sample size. Split train/test by
project, team, or template family, never by screenshot; keep related versions
and controlled variants in the same split unless a declared
transformation-generalization experiment says otherwise. Include human-only,
AI-assisted, and unknown-provenance artifacts where documented and permitted,
different eras and genres, purposeful conventional designs, rough human work,
and polished AI-assisted work. Era, awards, polish, and repository badges are
not substitute provenance labels; creator or process evidence is used only in
the separate provenance analysis.

## 10. Perturbation checks (pilot decision)

Paired fixtures test expected invariances, not psychometric properties:

- `scenario-inconsistency` vs `scenario-inconsistency-restyled` (palette and font changed): the grounded INT-02 finding should persist.
- `buttons-working-broken` vs `buttons-fixed` (dead control fixed): the INT-01 finding should disappear while unrelated surface observations stay the same.

No invariance is expected for the feature that was deliberately changed.

## 11. What results do not show

Schema validity and fixture results show that the plumbing works. They do not
show that a model recognizes perceived slop accurately, that any cue
indicates AI production, or that one model is better in general. No learned
diagnostic weights exist in this rubric.

## 12. Commands

```bash
python scripts/expand_prompt.py --bundle B --profile multimodal-datastory --out pkg/      # frozen-skill package
python ../integrations/baselines/expand_generic.py --bundle B --profile multimodal-datastory --out pkg-generic/
python scripts/import_run.py --raw reply.txt --package pkg/ --bundle B --condition frozen-skill \
  --provider P --model-id M --access-path "manual chat" --out runs/
python scripts/score_benchmark.py --runs runs/ --annotations annotations/ --bundles bundles/ --out scores/ \
  --compare frozen-skill/M generic-prompt/M
```
