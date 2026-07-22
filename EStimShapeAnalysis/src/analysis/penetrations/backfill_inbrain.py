"""Backfill the 'inbrain_frac' column onto an existing robustness sweep.csv
WITHOUT re-running the optimisation.

Why this exists: older sweeps didn't record inbrain_frac, so the degeneracy
filter (which drops edge-grazing poses that score high r while sitting outside
the brain) has nothing to act on. inbrain_frac only needs the cheap MRI-sampling
step, not the expensive optimisation — so we rebuild the data once, then for
each stored row reconstruct its pose and sample the volume. Minutes, not a
whole sweep.

No CLI — edit the CONFIG block and run.

IMPORTANT: NO_SKULL_MRI must point at your BRAIN-EXTRACTED volume (0 outside the
brain). If you sampled a full-skull volume, skull/scalp counts as 'in brain' and
inbrain_frac won't discriminate. This is the single most common reason the
filter 'does nothing'.
"""
import os

import pandas as pd

from clat.util.connection import Connection

from src.analysis.penetrations.alignment_optimize import MRI_VIEWER_CONFIG_PATH
from src.analysis.penetrations.alignment_robustness import (
    backfill_inbrain,
    prepare_data,
)


# ═══════════════════════════════════════════════════════════════════════════
#  CONFIG — edit these, then run the file
# ═══════════════════════════════════════════════════════════════════════════
SWEEP_CSV = "/home/connorlab/Documents/penetration_optimization_plots/_robustness/sweep.csv"
OUT_CSV   = None            # None -> overwrite SWEEP_CSV in place; or a new path

# Must match the sweep's tissue recipe + session set so depths/sessions line up.
from src.analysis.penetrations.run_pooled import PIPE_AA_K5   # noqa: E402
PIPELINE = PIPE_AA_K5
TABLE    = "PenetrationMetrics"
EXCLUDE  = ["260327_0", "260331_0", "260402_0", "260520_0", "260423_0"]

MRI_CONFIG_PATH = MRI_VIEWER_CONFIG_PATH
# REQUIRED for a meaningful result: the brain-extracted (no-skull) volume.
NO_SKULL_MRI = None         # e.g. "/path/to/subject_ns_rigid_aligned.par"

# In-brain intensity threshold. 0.0 for a clean brain-extracted volume (exactly
# 0 outside). Raise slightly if the volume has a non-zero background.
INBRAIN_THRESH = 0.0

# DB connection (same as run_per_session).
DB = dict(database="allen_data_repository", user="xper_rw",
          password="up2nite", host="172.30.6.61")
# ═══════════════════════════════════════════════════════════════════════════


def main():
    if NO_SKULL_MRI is None:
        print("WARNING: NO_SKULL_MRI is None — inbrain_frac will be computed on the "
              "config's default volume. If that is NOT brain-extracted, the values "
              "will be ~1 everywhere and useless. Set NO_SKULL_MRI to your no-skull "
              "volume for a meaningful filter.\n")

    out_csv = OUT_CSV or SWEEP_CSV
    conn = Connection(**DB)

    print("Preparing data (PCA + tissue model + MRI pipeline; no optimisation) ...")
    df_conf, mri_pipeline = prepare_data(
        conn, PIPELINE, TABLE, EXCLUDE, MRI_CONFIG_PATH, NO_SKULL_MRI)

    print(f"Reading sweep: {SWEEP_CSV}")
    df = pd.read_csv(SWEEP_CSV)
    print(f"  {len(df)} rows; computing inbrain_frac ...")

    df = backfill_inbrain(df, mri_pipeline, conn, df_conf, thresh=INBRAIN_THRESH)

    ib = df['inbrain_frac'].dropna()
    print(f"\ninbrain_frac: min={ib.min():.2f}  median={ib.median():.2f}  max={ib.max():.2f}")
    top = df.dropna(subset=['raw_after']).nlargest(10, 'raw_after')
    print("  top-10 raw_after rows -> their inbrain_frac:")
    print("   ", [f"{r.raw_after:.2f}/{r.inbrain_frac:.2f}" for r in top.itertuples()])
    if len(top) and top['inbrain_frac'].min() > 0.9:
        print("  *** The highest-raw rows all have HIGH inbrain_frac — the metric is")
        print("      NOT discriminating. Almost certainly NO_SKULL_MRI is wrong / not")
        print("      brain-extracted. Fix that and re-run this backfill.")

    df.to_csv(out_csv, index=False)
    print(f"\nWrote → {out_csv}")
    print("Now run recover_knee_correction.py (MIN_INBRAIN will actually filter).")


if __name__ == "__main__":
    main()
