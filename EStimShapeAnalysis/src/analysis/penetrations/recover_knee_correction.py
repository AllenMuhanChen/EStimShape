"""Recover chamber-correction files from an existing robustness sweep.csv.

No CLI — just edit the CONFIG block below and run the file. It rebuilds the
MRI-viewer chamber-correction JSON (the kind apply_pca_opt_result / the viewer
loads) from rows of sweep.csv, without re-running any optimisation.

  - By default it AUTOMATICALLY selects the best few NON-DEGENERATE candidates:
    the Pareto frontier (highest raw correlation per unit correction size) after
    dropping edge-grazing poses that score high r while sitting outside the brain
    (inbrain_frac < MIN_INBRAIN). It saves one correction file per candidate
    (opt_<ts>_c1..cN.json) and a plot with all of them ringed, so you can load
    each in the viewer and keep the one that looks right — no manual picking off
    a scatter plot.
  - Set SELECT_ROW to an integer to instead recover that one specific CSV row.

The 4x4 the viewer applies is built purely from the 9 global params + the
chamber centre (both available without a DB connection), so loading the MRI
pipeline here does NOT need the database. APPLYING a correction (APPLY=True)
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
    pareto_front,
    pareto_knee,
    save_candidates,
    save_correction_from_row,
    select_candidates,
)
from src.mri.correction import load_corrections


# ═══════════════════════════════════════════════════════════════════════════
#  CONFIG — edit these, then run the file
# ═══════════════════════════════════════════════════════════════════════════
SWEEP_CSV = "/home/connorlab/Documents/penetration_optimization_plots/_robustness/sweep.csv"

# MRI pipeline (needed only for the chamber centre / 4x4 geometry — no DB).
MRI_CONFIG_PATH = MRI_VIEWER_CONFIG_PATH
NO_SKULL_MRI    = None          # set to the brain-extracted volume path if you used one

# Candidate selection:
#   SELECT_ROW = None  -> auto-select N_CANDIDATES non-degenerate frontier points
#   SELECT_ROW = <int> -> recover just that one 0-based CSV row
SELECT_ROW   = None
N_CANDIDATES = 3                # how many frontier candidates to save when auto-selecting

# Degeneracy guards (a high Pearson r is fooled by edge-grazing poses that sit
# mostly OUTSIDE the brain). Requires the sweep.csv to have an 'inbrain_frac'
# column (produced by newer runs). MIN_INBRAIN drops rows whose trajectories are
# largely out of brain BEFORE selecting; RAW_MAX is a hard 'too good to be true'
# cap on raw_after.
MIN_INBRAIN = 0.90              # None to disable
RAW_MAX     = None              # e.g. 0.90 to exclude a spurious high cluster
KNEE_TOL    = 0.01              # used only by the diagnostic's knee line

# Where to drop copies of the saved JSONs (the canonical copies always go to the
# mri dir that apply_pca_opt_result reads). Defaults to the sweep.csv folder.
COPY_DIR = None

# Print a no-DB diagnostic table (raw_after / in-brain / correction size for the
# top rows) and compare against the chamber correction currently in the live
# file. Read this to sanity-check the candidates before applying.
DIAGNOSE = True

# Save a PNG of the Pareto scatter with ALL selected candidates ringed and
# numbered, every point coloured by in-brain fraction (edge-grazers show up
# dark). Lets you see exactly which corrections were picked.
PLOT      = True
PLOT_PATH = None                # None -> 'recovered_candidates.png' next to the CSV

# Set to a candidate number (1..N_CANDIDATES) to ALSO write that one into the
# live chamber-correction file (overwrites it). None = save files + plot only,
# touch nothing live (recommended until you've eyeballed them in the viewer).
APPLY_WHICH = None
# ═══════════════════════════════════════════════════════════════════════════


def plot_candidates(df, cands, out_path, front=None):
    """Scatter raw_after vs shift_mm, colour by in-brain fraction, draw the
    non-degenerate Pareto frontier, and ring + number every saved candidate."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    d = df.dropna(subset=['shift_mm', 'raw_after'])
    fig, ax = plt.subplots(figsize=(8, 5.5))
    has_ib = 'inbrain_frac' in d.columns and d['inbrain_frac'].notna().any()
    if has_ib:
        sc = ax.scatter(d['shift_mm'], d['raw_after'], c=d['inbrain_frac'].fillna(0.0),
                        cmap='viridis', vmin=0.0, vmax=1.0, s=36, alpha=0.8)
        fig.colorbar(sc, ax=ax, label='in-brain fraction (dark = edge-grazer, out of brain)')
    else:
        ax.scatter(d['shift_mm'], d['raw_after'], s=36, alpha=0.7, color='gray')
        ax.text(0.02, 0.02, "no inbrain_frac in CSV (older run)", transform=ax.transAxes,
                fontsize=8, color='gray')

    if front is not None and not front.empty:
        fsorted = front.sort_values('shift_mm')
        ax.plot(fsorted['shift_mm'], fsorted['raw_after'], '-', color='crimson',
                lw=1.2, alpha=0.7, zorder=4, label='non-degenerate frontier')

    for i, (_, r) in enumerate(cands.iterrows(), 1):
        ax.scatter([r['shift_mm']], [r['raw_after']], s=320, facecolors='none',
                   edgecolors='red', linewidths=2.4, zorder=6)
        ax.annotate(f"c{i}", (r['shift_mm'], r['raw_after']),
                    textcoords='offset points', xytext=(8, 6), fontsize=10,
                    color='red', fontweight='bold')

    ax.set_xlabel('correction magnitude  (RMS mm shift of sampled points from nominal)')
    ax.set_ylabel('raw correlation  (mean unweighted Pearson r)')
    ax.set_title(f'Recovered candidates (c1..c{len(cands)}) on the non-degenerate frontier')
    ax.legend(loc='lower right', fontsize=9)
    fig.tight_layout()
    fig.savefig(out_path, dpi=140)
    plt.close(fig)


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

    has_ib = 'inbrain_frac' in df.columns
    if not has_ib:
        print("  NOTE: this CSV has NO inbrain_frac column (older run) — the in-brain")
        print("        filter CANNOT work; every row (incl. degenerates) passes.")
        print("        Re-run the sweep (records inbrain_frac) or backfill the column.")
    else:
        ib = df['inbrain_frac'].dropna()
        below = int((ib < MIN_INBRAIN).sum())
        print(f"  inbrain_frac: min={ib.min():.2f}  median={ib.median():.2f}  max={ib.max():.2f}  "
              f"| {below}/{len(ib)} rows below MIN_INBRAIN={MIN_INBRAIN}")
        top = df.dropna(subset=['raw_after']).nlargest(10, 'raw_after')
        if len(top) and top['inbrain_frac'].min() > MIN_INBRAIN and below == 0:
            print("  *** WARNING: the filter will remove NOTHING — even the top-raw rows")
            print("      have high inbrain_frac. The metric is NOT discriminating. Almost")
            print("      certainly the sweep sampled a FULL-SKULL volume (NO_SKULL_MRI was")
            print("      not set), so skull/scalp counts as 'in brain'. Re-run the sweep")
            print("      with NO_SKULL_MRI pointing at your brain-extracted volume.")

    d = df.dropna(subset=['raw_after']).copy()
    knee = pareto_knee(d, tol=KNEE_TOL, min_inbrain=MIN_INBRAIN, raw_max=KNEE_RAW_MAX)
    best = d.loc[d['raw_after'].idxmax()]

    def _ib(r):
        return f"{r['inbrain_frac']:.2f}" if has_ib and pd.notna(r.get('inbrain_frac')) else " n/a"

    def describe(label, r):
        Mt, Ma = _mat_stats(row_M(r))
        print(f"  {label:<10s} raw_after={r['raw_after']:.4f}  inbrain={_ib(r)}  "
              f"shift_mm={r.get('shift_mm', float('nan')):.2f}  |t|={Mt:.2f}mm  rot={Ma:.2f}deg  "
              f"set={r.get('param_set')}  ps={r.get('per_session')}  beta={r.get('beta')}")

    if knee is not None:
        describe("KNEE", knee)
    describe("BEST-raw", best)

    print(f"\n  Top {top} rows by raw_after (raw, inbrain, shift, |t|, rot):")
    cols = d.sort_values('raw_after', ascending=False).head(top)
    for i, (_, r) in enumerate(cols.iterrows()):
        Mt, Ma = _mat_stats(row_M(r))
        flag = ""
        if has_ib and pd.notna(r.get('inbrain_frac')) and r['inbrain_frac'] < 0.8:
            flag = "  <-- LIKELY EDGE-GRAZER (mostly out of brain)"
        print(f"    #{i:<2d} idx={r.name:<4} raw={r['raw_after']:.4f}  inbrain={_ib(r)}  "
              f"shift={r.get('shift_mm', float('nan')):5.2f}mm  |t|={Mt:5.2f}mm  rot={Ma:5.2f}deg"
              f"{flag}")
    print("  A high raw_after with LOW inbrain is a degenerate edge-grazing pose —")
    print("  it scores well but sits outside the brain. Prefer the highest-raw row")
    print("  with inbrain ~1; set SELECT_ROW to its idx, or tune MIN_INBRAIN.")
    print("=" * 78)


def main():
    copy_dir = COPY_DIR if COPY_DIR is not None else os.path.dirname(SWEEP_CSV)

    print(f"Loading MRI pipeline (config={MRI_CONFIG_PATH}) ...")
    mri_pipeline = load_mri_pipeline(MRI_CONFIG_PATH, volume_path=NO_SKULL_MRI)

    print(f"Reading sweep: {SWEEP_CSV}")
    df = pd.read_csv(SWEEP_CSV)

    if DIAGNOSE:
        diagnose(df, mri_pipeline)

    # Resolve candidates. Auto mode = the few best non-degenerate frontier points.
    if SELECT_ROW is None:
        front = pareto_front(df, min_inbrain=MIN_INBRAIN, raw_max=RAW_MAX)
        cands = select_candidates(df, n=N_CANDIDATES, min_inbrain=MIN_INBRAIN, raw_max=RAW_MAX)
        if cands is None or cands.empty:
            print("No non-degenerate candidates found — loosen MIN_INBRAIN / RAW_MAX, "
                  "or set SELECT_ROW. (If the CSV has no inbrain_frac column, re-run "
                  "the sweep so degenerate poses can be excluded.)")
            return
        print(f"\nAuto-selected {len(cands)} non-degenerate frontier candidate(s):")
    else:
        front = None
        cands = df.iloc[[SELECT_ROW]]
        print(f"\nExplicit single row idx={df.index[SELECT_ROW]} (SELECT_ROW={SELECT_ROW}):")

    for i, (_, r) in enumerate(cands.iterrows(), 1):
        ib = f"{r['inbrain_frac']:.2f}" if pd.notna(r.get('inbrain_frac')) else "n/a"
        print(f"  c{i}: raw={r.get('raw_after'):.4f}  inbrain={ib}  "
              f"shift={r.get('shift_mm'):.2f}mm  set={r.get('param_set')}  ps={r.get('per_session')}")

    if PLOT:
        plot_path = PLOT_PATH or os.path.join(copy_dir, 'recovered_candidates.png')
        plot_candidates(df, cands, plot_path, front=front)
        print(f"  Candidate plot → {plot_path}")

    print("\nSaving candidate correction files ...")
    saved = save_candidates(cands, mri_pipeline, copy_dir=copy_dir)
    for i, (_, p) in enumerate(saved, 1):
        print(f"  c{i} → {p}")

    if APPLY_WHICH is not None:
        if not (1 <= APPLY_WHICH <= len(saved)):
            print(f"\nAPPLY_WHICH={APPLY_WHICH} out of range 1..{len(saved)} — not applying.")
        else:
            _, p = saved[APPLY_WHICH - 1]
            print(f"\nAPPLY_WHICH={APPLY_WHICH} -> writing c{APPLY_WHICH} into the live "
                  f"chamber-correction file ...")
            apply_pca_opt_result(p, mri_pipeline)
            print("  Applied.")
    else:
        print("\nAPPLY_WHICH=None -> nothing live was modified. Load each opt_*_c*.json "
              "in the viewer, keep the best, or set APPLY_WHICH=<n> to apply one. Manual:")
        print("    apply_pca_opt_result('<path>', mri_pipeline)")


if __name__ == "__main__":
    main()
