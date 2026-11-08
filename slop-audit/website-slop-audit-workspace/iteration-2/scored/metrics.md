# Benchmark scores

Primary metric: **strict accepted-finding micro F1 on fully annotated assessable scopes**. Undefined values are shown as 'undefined', never as 0 or 1.

## multimodal runs

| system | sites | TP | FP | FN | precision | recall | F1 | contextual false alarms | presence F1 | unreviewed | abstention |
|---|---|---|---|---|---|---|---|---|---|---|---|
| frozen-skill/claude-opus-5-5 | 6 | 12.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.857 | 0.000 | 0.167 |

## Evidence validity (integrity error counts by code)


## Operational

- frozen-skill/claude-opus-5-5: 6 runs, schema-valid 1.000, integrity-valid 1.000, parse failures 0, median latency 269723 ms

No weighted 'best model' score is computed. Report the tradeoffs.
