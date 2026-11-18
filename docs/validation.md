# Validation

Run from the repository root:

    python -m unittest discover -s ion_trap_chip/verification/tests -v
    python -m tools.verify_results

The eight core tests cover missing and ambiguous matches, equal-voltage electrode swaps, incomplete acceptance checks, dependency invalidation, absolute geometric tolerance and consecutive-refinement criteria.

The result checker verifies the eight-table inventory, checksums, row structure, assignment counts, saved fault outcomes, dependency rules, numerical decisions and control summaries. A successful run reports the saved device precision as UNRESOLVED. Passing this checker establishes table consistency; it does not repeat the historical simulations.

For CAD, generate both designs and check STEP read-back with `ion_trap_chip.verification.cad.describe` and `read_step`. The optional COMSOL drivers require user-supplied inputs described in reproduction.md. Full solver experiments are not rerun as part of source-package validation.

Four additional tests cover model-free analytical-control setup, missing model/profile inputs, and prevention of run-directory overwrite.
