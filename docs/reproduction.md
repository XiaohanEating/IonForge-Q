# Running the code

## Core checks and CAD

Python 3.10 and NumPy are sufficient for the twelve tests (eight core checks and four input-handling checks) and result-table checks listed in README.md. CAD generation additionally needs PythonOCC. The recorded environment uses Python 3.10.18, NumPy 1.26.4, mph 1.3.1 and COMSOL 6.3.0.290. Install optional Python dependencies from requirements-simulation.txt; COMSOL and its modules require a separate licensed installation.

## Standalone analytical control

The analytical control constructs a 1 mm cube programmatically and needs no external model file:

    python -m tools.prepare_run --output runs/control

Set IONFORGE_RUN_DIR to the absolute run-directory path. In PowerShell:

    $env:IONFORGE_RUN_DIR = (Resolve-Path runs/control).Path
    python -m experiments.integration.analytic_control

## Device-specific experiments with private inputs

Supply a compatible reference MPH and the three reference potential profiles yourself. This release supplies experiment code and result tables, not these inputs. The drivers retain the original device's geometry/physics tags, so a different model requires adapting those tags and electrode definitions.

    python -m tools.prepare_run --output runs/device --model PATH_TO_REFERENCE.mph --reference-profiles PATH_TO_PROFILES

Set IONFORGE_RUN_DIR to the resulting absolute path, then run:

    python -m experiments.integration.inspect_model
    python -m experiments.integration.prepare_edits
    python -m experiments.integration.reimport --order AB --solve
    python -m experiments.integration.reimport --order BA --solve
    python -m experiments.integration.numerics
    python -m experiments.integration.fault_tests

Inspection exports the two source electrodes from the user's model. Preparation increases each y span by 0.020 mm with the lower-y edge fixed, validates the STEP round trip, and records hashes. Reimport loads the configured source model for each order, restores selections and runs the DC solve. Fault replay consumes the locally generated reimport records.

Numerical checks preserve the recorded protocol: three privately supplied reference profiles are paired with three new modified-model solves. Expected reference filenames:

- comsol_profile_reference_tight.npz
- comsol_profile_reference_fine_tight.npz
- comsol_profile_reference_finer_tight.npz

Each file supplies `coords_mm` with shape `(3,381)` and `dc` whose first row contains 381 potentials in volts. Coordinates are x=1.3 mm, z=13.2 mm, and 381 evenly spaced y values from -1.65 to -0.70 mm. Inputs must use the same reference geometry, drive settings and refinement protocol; coordinates alone do not establish compatibility. Their hashes are recorded when consumed.

All generated models, field arrays and records stay in the local run directory, which is excluded from version control. Use a fresh directory for another experiment. See protocol.md for thresholds and the distinction between correspondence and numerical acceptance.
