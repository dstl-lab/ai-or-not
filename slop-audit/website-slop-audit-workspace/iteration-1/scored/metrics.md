# Benchmark scores

Primary metric: **strict accepted-finding micro F1 on fully annotated assessable scopes**. Undefined values are shown as 'undefined', never as 0 or 1.

## multimodal runs

| system | sites | TP | FP | FN | precision | recall | F1 | contextual false alarms | presence F1 | unreviewed | abstention |
|---|---|---|---|---|---|---|---|---|---|---|---|
| frozen-skill/claude-opus-5-5 | 6 | 10.000 | 2.000 | 1.000 | 0.833 | 0.909 | 0.870 | 0.000 | 0.743 | 0.000 | 0.157 |
| no-skill-dev/claude-opus-5-5 | 6 | 0.000 | 0.000 | 11.000 | undefined | 0.000 | undefined | 0.000 | undefined | 0.000 | 0.000 |

## Evidence validity (integrity error counts by code)

- no-skill-dev/claude-opus-5-5: 2032 schema

## Operational

- frozen-skill/claude-opus-5-5: 6 runs, schema-valid 1.000, integrity-valid 1.000, parse failures 0, median latency 242356.500 ms
- no-skill-dev/claude-opus-5-5: 6 runs, schema-valid 0.000, integrity-valid 0.000, parse failures 6, median latency 193030.000 ms

No weighted 'best model' score is computed. Report the tradeoffs.
