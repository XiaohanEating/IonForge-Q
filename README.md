# IonForge-Q

CAD design and electrode-correspondence verification for ion-trap design revisions.

This release contains the core design code, verification experiment code, unit tests, and eight verification result tables. Native simulation models, exported CAD models, field arrays, mesh data, laboratory measurements, and manuscript files are excluded.

## Quick start

Use Python 3.10 and run from the repository root:

    python -m pip install -r requirements.txt
    python -m unittest discover -s ion_trap_chip/verification/tests -v
    python -m tools.verify_results

These commands exercise core checks and verify the published tables using NumPy, without COMSOL. The table checker verifies checksums, decisions and dependency rules; it does not reconstruct fields from the summarized values.

## Contents

| Directory | Contents |
|---|---|
| ion_trap_chip/core, config, utils | Blade and segmented-trap geometry builders, design parameters and STEP export |
| ion_trap_chip/verification | Affine CAD edits, geometry/incidence correspondence, electrical assignment and dependency checks |
| experiments/integration | Model inspection, electrode editing, STEP reimport, numerical checks, analytical control and fault tests |
| results | Eight CSV tables and a file-integrity manifest |
| tools | CAD generation, isolated run preparation and result-table verification |
| docs | Experiment protocol, input requirements and provenance |

## CAD generation

Install PythonOCC in an appropriate conda environment. Then run:

    python -m tools.generate_cad blade --output outputs/blade.step
    python -m tools.generate_cad segmented --output outputs/segmented.step

Generated files remain local. The geometry and routing implementations are supplied as source code.

## Verification results

The recorded local revision has 40/40 correct assignments with checked mapping, 40/40 with static IDs, and 38/40 with native selection propagation. Actual model mutations and record replay are distinguished in the fault table. Adjacent mesh-response differences are approximately 0.770 and 0.815 mV against a 0.05 mV threshold; the recorded device-precision outcome remains UNRESOLVED. These are summaries of the recorded experiments.

See results/README.md for table definitions. To run simulation experiments with your own inputs, see docs/reproduction.md. COMSOL 6.3 and licensed modules are required for solver execution; no model-download service or simulation assets are provided by this release.

## License

Project-authored code, documentation and result tables use the MIT license. Third-party dependencies retain their own licenses.
