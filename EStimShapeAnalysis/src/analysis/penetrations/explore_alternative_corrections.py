"""
Sweep over a single global correction parameter (default: del_deg), holding it
fixed at each value while re-optimizing the remaining 8 globals + per-session
corrections. Reveals trade-offs and identifies alternative equivalent fits.

Usage: edit the configuration block at the bottom and run:
    python explore_alternative_corrections.py
"""
import os
import sys
import numpy as np
import pandas as pd

# Allow `from src.mri...` imports the same way penetrations_pca does
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from src.analysis.penetrations.penetrations_pca import (
    load_and_perform_pca,
    compute_tissue_confidence,
    optimize_trajectory_alignment,
    load_mri_pipeline,
    MRI_VIEWER_CONFIG_PATH,
    MODEL_PCA_V2,
    _OPT_PARAM_NAMES,
)
from clat.util.connection import Connection


def sweep_fixed_param(
        conn: Connection,
        param_to_fix: str,
        sweep_values: list,
        start_from_file: str,
        # PCA settings (must match the run that produced the start_from_file)
        within_session_normalize: bool = False,
        varimax_n_components: int = 2,
        pc_smooth_sigma: float = 2.0,
        tissue_model=MODEL_PCA_V2,
        exclude_sessions=None,
        # Optimizer settings (carry over from production run)
        maxiter: int = 20000,
        enable_per_session_corrections: bool = True,
        session_corr_penalty: float = 0.5,
        chamber_dist_penalty: float = 0.01,
        chamber_param_penalty: float = 0.001,
        softmin_beta: float = 20,
        optimizer: str = 'cma-es',
        use_confidence_weights: bool = False,
        top_downweight_mm: float = 0.0,
        top_downweight_factor: float = 0.25,
):
    if param_to_fix not in _OPT_PARAM_NAMES:
        raise ValueError(f"Unknown param {param_to_fix!r}. "
                         f"Choose from: {_OPT_PARAM_NAMES}")

    # 1. PCA + tissue scores
    df, pca, X_pca, feature_columns, scaler = load_and_perform_pca(
        conn, "PenetrationMetrics",
        exclude_sessions=exclude_sessions,
        within_session_normalize=within_session_normalize,
        pc_smooth_sigma=pc_smooth_sigma,
        varimax_n_components=varimax_n_components,
    )
    df_conf = compute_tissue_confidence(df, model=tissue_model)

    # 2. MRI pipeline
    print("\nLoading MRI pipeline ...")
    mri_pipeline = load_mri_pipeline(MRI_VIEWER_CONFIG_PATH)

    # 3. Sweep
    records = []
    for val in sweep_values:
        print("\n" + "=" * 70)
        print(f"  Sweep: {param_to_fix} = {val:+.4f}")
        print("=" * 70)
        opt = optimize_trajectory_alignment(
            df_conf, conn, mri_pipeline,
            maxiter=maxiter,
            start_from_file=start_from_file,
            enable_per_session_corrections=enable_per_session_corrections,
            session_corr_penalty=session_corr_penalty,
            chamber_dist_penalty=chamber_dist_penalty,
            chamber_param_penalty=chamber_param_penalty,
            softmin_beta=softmin_beta,
            optimizer=optimizer,
            use_confidence_weights=use_confidence_weights,
            top_downweight_mm=top_downweight_mm,
            top_downweight_factor=top_downweight_factor,
            fixed_globals={param_to_fix: float(val)},
        )
        rec = {'fixed_val': float(val),
               'score': float(opt['score_after']),
               'raw': float(opt['raw_after'])}
        for i, name in enumerate(_OPT_PARAM_NAMES):
            rec[name] = float(opt['params'][i])
        if opt.get('per_session_corrections'):
            per_dels = np.array([c['del_deg'] for c in opt['per_session_corrections'].values()])
            per_dazs = np.array([c['daz_deg'] for c in opt['per_session_corrections'].values()])
            per_deps = np.array([c['ddepth_mm'] for c in opt['per_session_corrections'].values()])
            rec['max|Δaz|']  = float(np.abs(per_dazs).max())
            rec['max|Δel|']  = float(np.abs(per_dels).max())
            rec['max|Δdep|'] = float(np.abs(per_deps).max())
        records.append(rec)

    # 4. Summary table
    table = pd.DataFrame(records)
    print("\n" + "=" * 70)
    print(f"  Sweep summary (fixing {param_to_fix})")
    print("=" * 70)
    # Round for readability
    fmt = table.copy()
    for c in fmt.columns:
        fmt[c] = fmt[c].map(lambda x: f"{x:+.4f}" if isinstance(x, float) else x)
    print(fmt.to_string(index=False))

    # Persist as CSV next to the start_from_file
    out_dir = os.path.dirname(start_from_file) or "."
    base = os.path.splitext(os.path.basename(start_from_file))[0]
    out_path = os.path.join(out_dir, f"sweep_{base}_fix_{param_to_fix}.csv")
    table.to_csv(out_path, index=False)
    print(f"\nSaved sweep to: {out_path}")

    return table


if __name__ == "__main__":
    conn = Connection(
        database="allen_data_repository",
        user="xper_rw",
        password="up2nite",
        host="172.30.6.61",
    )

    # ---------------------------------------------------------------------
    # Configure the sweep here
    # ---------------------------------------------------------------------
    START_FROM_FILE = "/home/connorlab/git/EStimShape/EStimShapeAnalysis/src/mri/opt_20260424_175651.json"
    PARAM_TO_FIX    = 'del_deg'
    SWEEP_VALUES    = [-12.0, -10.0, -8.0, -6.0, -4.0, -2.0, 0.0]
    # ---------------------------------------------------------------------

    sweep_fixed_param(
        conn,
        param_to_fix=PARAM_TO_FIX,
        sweep_values=SWEEP_VALUES,
        start_from_file=START_FROM_FILE,
    )
