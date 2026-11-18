# Verification result tables

These CSV files summarize recorded verification experiments. They contain no per-point fields, mesh geometry or laboratory measurements.

| File | Meaning |
|---|---|
| assignments.csv | Correct electrical boundary sets for two import orders and three assignment methods |
| fault_detection.csv | Four actual model mutations and four separate record-replay tests |
| dependencies.csv | Invalidated stages and field-reuse decisions after changing each input class |
| renumbering.csv | Saved domain-descriptor replay with a synthetic ID permutation; no additional solve |
| mesh_response.csv | Three response peaks and modified-mesh sizes |
| response_acceptance.csv | Two adjacent refinement differences, threshold and decisions |
| linearity.csv | Same-mesh doubled-drive consistency result |
| analytic_control.csv | Errors for two meshes of the parallel-plate analytical control |

Units are included in column names. AB and BA are the two import orders of electrodes A7 and B7. They are the seventh electrodes in DC banks A and B.

Run `python -m tools.verify_results` to check table integrity and consistency. It also executes dependency rules against the saved dependency table. The field-response and analytical-error values are historical summaries, not values recomputed from distributed fields.
