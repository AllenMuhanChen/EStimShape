"""Session-resampling stability sweep.

Goal: eliminate 'which sessions were used' as a driver of the alignment answer.
Instead of many configs, we LOCK one config (mean aggregation beta=0, per-session
ON, rigid = daz/del/ddepth frozen) and vary only the SESSION SUBSET: each run
optimises on a random ~SUBSAMPLE_FRAC of sessions, starting from the NOMINAL ZERO
pose (the real start the pipeline uses). With a fixed start Nelder-Mead is
deterministic, so the only thing that moves between runs is the session
composition — that variation IS the session effect (see WARM_START).

Each run writes to its own dir OUT_BASE/<RUN_TAG>_<timestamp> (never overwrites a
previous run) and saves config.json (all parameters used) + summary.json (results).

Outputs (in the per-run dir):
  - config.json / summary.json : parameters used / results (consensus pose, spread,
      leverage, consensus-vs-full-data distance).
  - resamples.csv : ONE ROW PER RESAMPLE CORRECTION, in the SAME schema as the
      robustness sweep.csv (raw_after, shift_mm, inbrain_frac, the 9 global
      params, per_session_json, ...) PLUS resample columns (origin/normal,
      included_sessions, n_sessions, raw_after_subset, degenerate). So you can
      run recover_knee_correction.py on THIS file to build a frontier, pick
      candidates, and save/apply any individual correction — exactly like before.
  - consensus_correction : the MEDIAN chamber pose over non-degenerate resamples,
      saved as an opt_*.json (the session-composition-robust answer).
  - leverage.csv + plots : per-session leverage (which sessions swing the pose)
      and the pose-spread distributions.

All metrics for each resample correction are computed on the FULL session set, so
rows are directly comparable regardless of which subset produced them.

No CLI — edit CONFIG and run.
"""
import datetime
import json
import os

import numpy as np
import pandas as pd

from clat.util.connection import Connection

from src.analysis.penetrations.alignment_optimize import MRI_VIEWER_CONFIG_PATH
from src.analysis.penetrations.alignment_robustness import (
    _OPT_PARAM_NAMES,
    _row_from_result,
    chamber_pose,
    fixed_from_enabled,
    inbrain_fraction,
    optimize_subset,
    per_session_raw,
    pose_diff,
    prepare_data,
    save_correction_from_row,
    _silent_optimize,
)


# ═══════════════════════════════════════════════════════════════════════════
#  CONFIG
# ═══════════════════════════════════════════════════════════════════════════
# Every run writes to OUT_BASE/<RUN_TAG>_<timestamp> (timestamp always appended),
# so a new run NEVER overwrites a previous one. A config.json of all parameters
# and a summary.json of results are written into that per-run dir. Use RUN_TAG to
# label the run (e.g. the pipeline you're testing).
OUT_BASE = "/home/connorlab/Documents/penetration_optimization_plots/_session_resample"
RUN_TAG  = None                 # e.g. "PIPE_AA_K5" or "ica_v2"; None -> timestamp only

DB = dict(database="allen_data_repository", user="xper_rw", password="up2nite", host="172.30.6.61")
PIPELINE_NAME = "PIPE_AA_K7"
TABLE   = "PenetrationMetrics"
EXCLUDE = ["260327_0", "260331_0", "260402_0", "260520_0", "260423_0"]

MRI_CONFIG_PATH = MRI_VIEWER_CONFIG_PATH
NO_SKULL_MRI    = "/home/connorlab/Documents/MRI/45X_MRI/45X_110315_4_1_corrected_warper_native/rigid_aligned/subject_ns_rigid_aligned.nii.gz"          # REQUIRED brain-extracted volume (for inbrain_frac)

# Locked optimiser config (what dominated the knee).
BETA            = 0.0           # mean aggregation
PER_SESSION     = True
RIGID           = ['tx_mm', 'ty_mm', 'tz_mm', 'rx_deg', 'ry_deg', 'rz_deg']  # freeze daz/del/ddepth
MAXITER         = 100000          # warm-started, so it converges fast
CHAMBER_DIST_PENALTY = 0.000
CHAMBER_PARAM_PENALTY = 0.0001
SESSION_CORR_PENALTY = 0.1

# Resampling.
B              = 200            # number of session subsets
SUBSAMPLE_FRAC = 0.75           # fraction of sessions per subset
MIN_SESSIONS   = 8
MIN_INBRAIN    = 0.90           # resamples below this are degenerate -> excluded from consensus
SEED           = 0
# Start each subset from the NOMINAL ZERO pose (the real start the pipeline
# actually uses) so the result is 'what would the pipeline conclude from this
# subset'. With a fixed start Nelder-Mead is deterministic, so variation across
# subsets is PURELY the session effect — no random-start noise to remove.
# Set True only if you want to warm-start from the full-data optimum for speed;
# that ANCHORS every subset to the full-data answer and UNDER-reports the
# session-driven spread, so it is NOT recommended for this analysis.
WARM_START     = False
# ═══════════════════════════════════════════════════════════════════════════


def _row_for_correction(res, subset, mri_pipeline, conn, df_full, b):
    """Build one resamples.csv row: standard sweep schema (full-data metrics) +
    resample extras. raw_after here is the FULL-DATA mean so rows are comparable."""
    tags = dict(param_set='rigid', beta=BETA, chamber_param_penalty=CHAMBER_PARAM_PENALTY,
                per_session=PER_SESSION, resample=b, n_sessions=len(subset),
                start_kind='resample')
    row = _row_from_result(res, mri_pipeline, conn, df_full, tags)  # shift/inbrain/params over FULL data
    row['raw_after_subset'] = row['raw_after']                      # optimiser's in-subset mean
    full_rs = per_session_raw(mri_pipeline, res, conn, df_full)     # evaluate on ALL sessions
    row['raw_after'] = float(np.mean(full_rs))                      # override -> full-data mean (comparable)
    row['raw_std_full'] = float(np.std(full_rs))
    row['raw_min_full'] = float(np.min(full_rs))
    o, n = chamber_pose(mri_pipeline, np.asarray(res['params'])[:9])
    row['origin_x'], row['origin_y'], row['origin_z'] = map(float, o)
    row['normal_x'], row['normal_y'], row['normal_z'] = map(float, n)
    row['included_sessions'] = json.dumps(sorted(map(str, subset)))
    row['degenerate'] = bool(pd.notna(row.get('inbrain_frac')) and row['inbrain_frac'] < MIN_INBRAIN)
    return row


def main():
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    run_name = f"{RUN_TAG}_{ts}" if RUN_TAG else ts
    out_dir = os.path.join(OUT_BASE, run_name)
    os.makedirs(out_dir, exist_ok=True)

    run_config = dict(
        timestamp=ts, run_tag=RUN_TAG,
        pipeline_name=PIPELINE_NAME, table=TABLE, exclude=list(EXCLUDE),
        mri_config_path=MRI_CONFIG_PATH, no_skull_mri=NO_SKULL_MRI,
        beta=BETA, per_session=PER_SESSION, rigid=list(RIGID), maxiter=MAXITER,
        chamber_dist_penalty=CHAMBER_DIST_PENALTY,
        chamber_param_penalty=CHAMBER_PARAM_PENALTY,
        session_corr_penalty=SESSION_CORR_PENALTY,
        B=B, subsample_frac=SUBSAMPLE_FRAC, min_sessions=MIN_SESSIONS,
        min_inbrain=MIN_INBRAIN, seed=SEED, warm_start=WARM_START,
        db=dict(host=DB.get('host'), user=DB.get('user'), database=DB.get('database')),  # password omitted
    )
    with open(os.path.join(out_dir, 'config.json'), 'w') as f:
        json.dump(run_config, f, indent=2)
    print(f"Run dir → {out_dir}")
    print(f"  config.json written ({run_config['pipeline_name']}, B={B}, "
          f"subsample={SUBSAMPLE_FRAC}, beta={BETA}, per_session={PER_SESSION})")

    conn = Connection(**DB)
    import src.analysis.penetrations.run_pooled as rp
    pipeline = getattr(rp, PIPELINE_NAME)

    print("Preparing data ...")
    df_conf, mri_pipeline = prepare_data(conn, pipeline, TABLE, EXCLUDE,
                                         MRI_CONFIG_PATH, NO_SKULL_MRI)
    sessions = list(df_conf['session_id'].unique())
    N = len(sessions)
    k = max(MIN_SESSIONS, int(round(SUBSAMPLE_FRAC * N)))
    print(f"  {N} sessions; drawing {k}/{N} per resample; B={B}")

    base_kw = dict(
        maxiter=MAXITER, optimizer='nelder-mead', use_confidence_weights=True,
        variance_penalty=0.0, softmin_beta=BETA,
        enable_per_session_corrections=PER_SESSION,
        chamber_dist_penalty=CHAMBER_DIST_PENALTY,
        chamber_param_penalty=CHAMBER_PARAM_PENALTY,
        session_corr_penalty=SESSION_CORR_PENALTY,
        fixed_globals=fixed_from_enabled(RIGID),
    )

    # Full-data reference solution (also the warm start).
    print("Full-data reference optimisation ...")
    res_full = _silent_optimize(df_conf, conn, mri_pipeline, **base_kw)
    x0_full = np.asarray(res_full['params'])[:9]
    o_full, n_full = chamber_pose(mri_pipeline, x0_full)
    print(f"  full-data pose: origin=({o_full[0]:.1f},{o_full[1]:.1f},{o_full[2]:.1f})mm")

    rng = np.random.default_rng(SEED)
    rows = []
    for b in range(B):
        idx = rng.choice(N, size=k, replace=False)
        subset = [sessions[i] for i in idx]
        try:
            res = optimize_subset(df_conf, conn, mri_pipeline, subset, base_kw,
                                  x0_global=(x0_full if WARM_START else None))
            row = _row_for_correction(res, subset, mri_pipeline, conn, df_conf, b)
        except Exception as exc:
            print(f"  [{b+1}/{B}] failed: {exc}")
            continue
        rows.append(row)
        print(f"  [{b+1}/{B}] raw={row['raw_after']:.4f}  inbrain={row['inbrain_frac']:.2f}  "
              f"shift={row['shift_mm']:.2f}mm  {'DEGEN' if row['degenerate'] else ''}")

    df_res = pd.DataFrame(rows)
    res_csv = os.path.join(out_dir, 'resamples.csv')
    df_res.to_csv(res_csv, index=False)
    print(f"\nresamples.csv → {res_csv}  ({len(df_res)} rows)")

    nd = df_res[~df_res['degenerate']].copy()
    print(f"  non-degenerate: {len(nd)}/{len(df_res)}")
    if nd.empty:
        print("  All resamples degenerate — check NO_SKULL_MRI / config. Stopping.")
        return

    # ---- Consensus = median global pose over non-degenerate resamples ----
    med = {name: float(nd[name].median()) for name in _OPT_PARAM_NAMES}
    consensus_row = pd.Series({**med, 'per_session_json': json.dumps({}),
                               'raw_after': float(nd['raw_after'].median()),
                               'beta': BETA, 'per_session': False, 'param_set': 'rigid'})
    o_c, n_c = chamber_pose(mri_pipeline, [med[n] for n in _OPT_PARAM_NAMES])
    cons_path = save_correction_from_row(consensus_row, mri_pipeline, copy_dir=out_dir,
                                         suffix='_consensus')
    print(f"\nConsensus correction (median pose) → {cons_path}")
    print(f"  consensus origin=({o_c[0]:.2f},{o_c[1]:.2f},{o_c[2]:.2f})mm")

    # ---- Spread of each resample pose around the consensus ----
    cons_params = [med[n] for n in _OPT_PARAM_NAMES]
    dpos, dang = [], []
    for _, r in nd.iterrows():
        dp, da = pose_diff(mri_pipeline, [r[n] for n in _OPT_PARAM_NAMES], cons_params)
        dpos.append(dp); dang.append(da)
    dpos, dang = np.array(dpos), np.array(dang)
    print(f"  pose spread vs consensus: origin {np.median(dpos):.2f}mm median / "
          f"{np.percentile(dpos,95):.2f}mm p95 | normal {np.median(dang):.2f}deg median / "
          f"{np.percentile(dang,95):.2f}deg p95")

    # ---- Per-session leverage: pose(included) vs pose(excluded) ----
    lev = []
    for sid in sessions:
        inc = nd[nd['included_sessions'].apply(lambda s: str(sid) in json.loads(s))]
        exc = nd[~nd['included_sessions'].apply(lambda s: str(sid) in json.loads(s))]
        if len(inc) < 3 or len(exc) < 3:
            continue
        pa = [inc[n].median() for n in _OPT_PARAM_NAMES]
        pb = [exc[n].median() for n in _OPT_PARAM_NAMES]
        dp, da = pose_diff(mri_pipeline, pa, pb)
        lev.append(dict(session=str(sid), leverage_mm=dp, leverage_deg=da,
                        n_incl=len(inc), n_excl=len(exc)))
    lev_df = pd.DataFrame(lev).sort_values('leverage_mm', ascending=False)
    lev_df.to_csv(os.path.join(out_dir, 'leverage.csv'), index=False)
    if not lev_df.empty:
        print("\nTop session leverage (pose shift when a session is in vs out):")
        for _, r in lev_df.head(8).iterrows():
            print(f"  {r['session']}: {r['leverage_mm']:.2f}mm  {r['leverage_deg']:.2f}deg")

    # ---- Results summary (alongside config.json) ----
    summary = dict(
        n_resamples=int(len(df_res)),
        n_non_degenerate=int((~df_res['degenerate']).sum()),
        consensus_params=med,
        consensus_origin=[float(v) for v in o_c],
        consensus_normal=[float(v) for v in n_c],
        full_data_params={n: float(x0_full[i]) for i, n in enumerate(_OPT_PARAM_NAMES)},
        full_data_origin=[float(v) for v in o_full],
        pose_spread_origin_mm=dict(median=float(np.median(dpos)), p95=float(np.percentile(dpos, 95))),
        pose_spread_normal_deg=dict(median=float(np.median(dang)), p95=float(np.percentile(dang, 95))),
        consensus_vs_full_data=dict(
            origin_mm=float(np.linalg.norm(np.array(o_c) - np.array(o_full)))),
        top_leverage=(lev_df.head(10).to_dict('records') if not lev_df.empty else []),
        resamples_csv=res_csv, consensus_correction=cons_path,
    )
    with open(os.path.join(out_dir, 'summary.json'), 'w') as f:
        json.dump(summary, f, indent=2)

    _plots(df_res, nd, dpos, dang, lev_df, cons_params, mri_pipeline, out_dir)
    print(f"\nOutputs → {out_dir}  (config.json, summary.json, resamples.csv, "
          f"leverage.csv, consensus correction, plots)")
    print("To pick alternate corrections: run recover_knee_correction.py with "
          f"SWEEP_CSV = '{res_csv}'.")


def _plots(df_res, nd, dpos, dang, lev_df, cons_params, mri_pipeline, out_dir):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    # 1. rigid param distributions with consensus markers
    try:
        rigid = ['tx_mm', 'ty_mm', 'tz_mm', 'rx_deg', 'ry_deg', 'rz_deg']
        fig, ax = plt.subplots(figsize=(9, 5))
        ax.violinplot([nd[p].values for p in rigid], showmeans=False, showmedians=True)
        for i, p in enumerate(rigid, 1):
            ax.scatter([i], [cons_params[_OPT_PARAM_NAMES.index(p)]], color='red', zorder=5,
                       label=('consensus' if i == 1 else None))
        ax.set_xticks(range(1, len(rigid) + 1)); ax.set_xticklabels(rigid, rotation=30)
        ax.set_ylabel('value (mm / deg)')
        ax.set_title('Rigid-param distribution across session subsets (red = consensus)')
        ax.legend(); fig.tight_layout()
        fig.savefig(os.path.join(out_dir, 'param_distributions.png'), dpi=140); plt.close(fig)
    except Exception as exc:
        print(f"  param plot skipped: {exc}")

    # 2. pose spread histograms
    try:
        fig, axs = plt.subplots(1, 2, figsize=(11, 4))
        axs[0].hist(dpos, bins=25, color='slategray'); axs[0].set_title('origin shift vs consensus (mm)')
        axs[0].set_xlabel('mm')
        axs[1].hist(dang, bins=25, color='darkkhaki'); axs[1].set_title('normal tilt vs consensus (deg)')
        axs[1].set_xlabel('deg')
        fig.tight_layout(); fig.savefig(os.path.join(out_dir, 'pose_spread.png'), dpi=140); plt.close(fig)
    except Exception as exc:
        print(f"  spread plot skipped: {exc}")

    # 3. per-session leverage bar
    try:
        if not lev_df.empty:
            top = lev_df.head(20)
            fig, ax = plt.subplots(figsize=(10, max(3, 0.35 * len(top) + 1)))
            ax.barh(range(len(top)), top['leverage_mm'], color='indianred')
            ax.set_yticks(range(len(top))); ax.set_yticklabels(top['session'], fontsize=7)
            ax.invert_yaxis(); ax.set_xlabel('pose shift when session in vs out (mm)')
            ax.set_title('Per-session leverage (which sessions swing the correction)')
            fig.tight_layout(); fig.savefig(os.path.join(out_dir, 'session_leverage.png'), dpi=140)
            plt.close(fig)
    except Exception as exc:
        print(f"  leverage plot skipped: {exc}")

    # 4. raw vs shift coloured by inbrain (same view as the main sweep)
    try:
        d = df_res.dropna(subset=['shift_mm', 'raw_after'])
        fig, ax = plt.subplots(figsize=(7.5, 5.5))
        sc = ax.scatter(d['shift_mm'], d['raw_after'], c=d['inbrain_frac'].fillna(0.0),
                        cmap='viridis', vmin=0, vmax=1, s=36, alpha=0.85)
        fig.colorbar(sc, ax=ax, label='in-brain fraction')
        ax.set_xlabel('shift_mm (vs nominal)'); ax.set_ylabel('raw_after (full-data mean r)')
        ax.set_title('Resample corrections: fit vs correction size')
        fig.tight_layout(); fig.savefig(os.path.join(out_dir, 'resample_fit_vs_shift.png'), dpi=140)
        plt.close(fig)
    except Exception as exc:
        print(f"  fit/shift plot skipped: {exc}")


if __name__ == "__main__":
    main()
