"""Recover a chamber-correction file from an existing robustness sweep.csv.

No CLI — just edit the CONFIG block below and run the file. It rebuilds the
MRI-viewer chamber-correction JSON (the kind apply_pca_opt_result / the viewer
loads) from a row of sweep.csv, without re-running any optimisation.

  - By default it recovers the PARSIMONY KNEE (smallest correction within
    KNEE_TOL of the best raw correlation).
  - Set SELECT_ROW to an integer to instead recover that specific CSV row
    (use this to pick a point you eyeballed off the Pareto plot).

The 4x4 the viewer applies is built purely from the 9 global params + the
chamber centre (both available without a DB connection), so loading the MRI
pipeline here does NOT need the database. APPLYING the correction (APPLY=True)
DOES overwrite the real chamber-correction file, so it defaults to False.
"""
import os

import pandas as pd

from src.analysis.penetrations.alignment_optimize import (
    MRI_VIEWER_CONFIG_PATH,
    apply_pca_opt_result,
    load_mri_pipeline,
)
from src.analysis.penetrations.alignment_robustness import (
    save_correction_from_row,
    save_knee_correction,
)


# ═══════════════════════════════════════════════════════════════════════════
#  CONFIG — edit these, then run the file
# ═══════════════════════════════════════════════════════════════════════════
SWEEP_CSV = "/home/connorlab/Documents/penetration_optimization_plots/_robustness/sweep.csv"

# MRI pipeline (needed only for the chamber centre / 4x4 geometry — no DB).
MRI_CONFIG_PATH = MRI_VIEWER_CONFIG_PATH
NO_SKULL_MRI    = None          # set to the brain-extracted volume path if you used one

# Which row to recover:
#   SELECT_ROW = None  -> the parsimony knee (recommended)
#   SELECT_ROW = <int> -> that 0-based row index of the CSV
SELECT_ROW = None
KNEE_TOL   = 0.01               # knee = smallest shift within this of the best raw_after

# Where to drop a copy of the saved JSON (the canonical copy always goes to the
# mri dir that apply_pca_opt_result reads). Defaults to the sweep.csv folder.
COPY_DIR = None

# Set True to ACTUALLY write the correction into the live chamber-correction
# file (overwrites it). Leave False to only produce the opt_*.json and print
# the command you'd run to apply it.
APPLY = False
# ═══════════════════════════════════════════════════════════════════════════


def main():
    copy_dir = COPY_DIR if COPY_DIR is not None else os.path.dirname(SWEEP_CSV)

    print(f"Loading MRI pipeline (config={MRI_CONFIG_PATH}) ...")
    mri_pipeline = load_mri_pipeline(MRI_CONFIG_PATH, volume_path=NO_SKULL_MRI)

    print(f"Reading sweep: {SWEEP_CSV}")
    df = pd.read_csv(SWEEP_CSV)

    if SELECT_ROW is None:
        print("Recovering parsimony knee ...")
        path = save_knee_correction(df, mri_pipeline, copy_dir=copy_dir, tol=KNEE_TOL)
    else:
        row = df.iloc[SELECT_ROW]
        print(f"Recovering explicit row {SELECT_ROW}:  raw_after={row.get('raw_after')}  "
              f"shift_mm={row.get('shift_mm')}  param_set={row.get('param_set')}")
        path = save_correction_from_row(row, mri_pipeline, copy_dir=copy_dir)

    if not path:
        print("Nothing recovered.")
        return

    print(f"\nCorrection file written: {path}")
    if APPLY:
        print("APPLY=True -> writing into the live chamber-correction file ...")
        apply_pca_opt_result(path, mri_pipeline)
        print("  Applied.")
    else:
        print("APPLY=False -> not modifying live files. To apply, either set "
              "APPLY=True and re-run, or call:")
        print(f"    apply_pca_opt_result('{path}', mri_pipeline)")


if __name__ == "__main__":
    main()
