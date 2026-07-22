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

import numpy as np
import pandas as pd

from src.analysis.penetrations.alignment_optimize import (
    MRI_VIEWER_CONFIG_PATH,
    _OPT_PARAM_NAMES,
    _chamber_correction_matrix,
    apply_pca_opt_result,
    load_mri_pipeline,
)
from src.analysis.penetrations.alignment_robustness import (
    pareto_knee,
    save_correction_from_row,
    save_knee_correction,
)
from src.mri.correction import load_corrections


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

# Print a no-DB diagnostic table (raw_after vs correction size for the top
# rows, the knee, and the best-raw row) and compare against the chamber
# correction currently in the live file. Read this BEFORE applying — if the
# knee's correction is tiny next to the best-raw row / your current file, the
# knee is under-correcting (raw-r is a weak constraint on absolute position).
DIAGNOSE = True

# Set True to ACTUALLY write the correction into the live chamber-correction
# file (overwrites it). Leave False to only produce the opt_*.json and print
# the command you'd run to apply it.
APPLY = False
# ═══════════════════════════════════════════════════════════════════════════


def _mat_stats(M):
    """(translation norm mm, net rotation angle deg) of a 4x4 correction."""
    t = float(np.linalg.norm(M[:3, 3]))
    R = M[:3, :3]
    ang = float(np.degrees(np.arccos(np.clip((np.trace(R) - 1.0) / 2.0, -1.0, 1.0))))
    return t, ang


def diagnose(df, mri_pipeline, top=12):
    center = mri_pipeline.get('chamber_center_base', np.zeros(3))

    def row_M(r):
        g = np.array([float(r[n]) for n in _OPT_PARAM_NAMES])
        return _chamber_correction_matrix(g, center)

    print("\n" + "=" * 78)
    print("DIAGNOSTIC — is the selected correction actually correcting? (no DB needed)")
    print("=" * 78)

    # current live chamber correction (the pose you have now)
    try:
        cur, _ = load_corrections(mri_pipeline['ch_corr_path'])
        ct, ca = _mat_stats(np.asarray(cur))
        is_id = np.allclose(cur, np.eye(4))
        print(f"  CURRENT live chamber correction: |t|={ct:.2f}mm  rot={ca:.2f}deg"
              + ("   (identity — nothing applied yet)" if is_id else ""))
    except Exception as exc:
        print(f"  (could not read current chamber correction: {exc})")

    d = df.dropna(subset=['raw_after']).copy()
    knee = pareto_knee(d)
    best = d.loc[d['raw_after'].idxmax()]

    def describe(label, r):
        Mt, Ma = _mat_stats(row_M(r))
        print(f"  {label:<10s} raw_after={r['raw_after']:.4f}  shift_mm={r.get('shift_mm', float('nan')):.2f}"
              f"  |t|={Mt:.2f}mm  rot={Ma:.2f}deg  set={r.get('param_set')}  "
              f"ps={r.get('per_session')}  beta={r.get('beta')}  pen={r.get('chamber_param_penalty')}")

    if knee is not None:
        describe("KNEE", knee)
    describe("BEST-raw", best)

    print(f"\n  Top {top} rows by raw_after (raw_after, shift_mm, |t|, rot):")
    cols = d.sort_values('raw_after', ascending=False).head(top)
    for i, (_, r) in enumerate(cols.iterrows()):
        Mt, Ma = _mat_stats(row_M(r))
        print(f"    #{i:<2d} idx={r.name:<4} raw={r['raw_after']:.4f}  "
              f"shift={r.get('shift_mm', float('nan')):5.2f}mm  |t|={Mt:5.2f}mm  rot={Ma:5.2f}deg  "
              f"set={r.get('param_set')}  ps={r.get('per_session')}")
    print("  If KNEE's |t|/shift is tiny next to BEST-raw or your CURRENT file, the")
    print("  knee is under-correcting — set SELECT_ROW to a high-raw / adequately-")
    print("  corrected idx above instead, or re-run the sweep on a no-skull MRI.")
    print("=" * 78)


def main():
    copy_dir = COPY_DIR if COPY_DIR is not None else os.path.dirname(SWEEP_CSV)

    print(f"Loading MRI pipeline (config={MRI_CONFIG_PATH}) ...")
    mri_pipeline = load_mri_pipeline(MRI_CONFIG_PATH, volume_path=NO_SKULL_MRI)

    print(f"Reading sweep: {SWEEP_CSV}")
    df = pd.read_csv(SWEEP_CSV)

    if DIAGNOSE:
        diagnose(df, mri_pipeline)

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
