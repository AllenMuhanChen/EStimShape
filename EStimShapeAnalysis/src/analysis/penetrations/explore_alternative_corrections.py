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
import matplotlib.pyplot as plt

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


def plot_sweep(table, param_to_fix: str, save_path: str = None):
    """Plot a sweep summary: fit quality + how each global param compensates.

    Accepts either a DataFrame or a path to a sweep CSV.
    """
    if isinstance(table, str):
        table = pd.read_csv(table)

    x = table['fixed_val'].values
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # --- Top-left: fit quality vs sweep ---
    ax = axes[0, 0]
    ax.plot(x, table['score'], 'o-', label='score (softmin, with penalties)',
            color='C0', linewidth=2, markersize=8)
    ax.plot(x, table['raw'], 's-', label='raw (unweighted mean r)',
            color='C1', linewidth=2, markersize=8)
    ax.set_xlabel(f'fixed {param_to_fix}')
    ax.set_ylabel('correlation')
    ax.set_title('Fit quality vs constrained value')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # --- Top-right: chamber translation ---
    ax = axes[0, 1]
    for col, c in zip(['tx_mm', 'ty_mm', 'tz_mm'], ['C0', 'C1', 'C2']):
        ax.plot(x, table[col], 'o-', label=col, color=c, linewidth=2, markersize=6)
    ax.axhline(0, color='gray', linewidth=0.5)
    ax.set_xlabel(f'fixed {param_to_fix}')
    ax.set_ylabel('mm')
    ax.set_title('Chamber translation (absorbs constraint?)')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # --- Bottom-left: chamber rotation ---
    ax = axes[1, 0]
    for col, c in zip(['rx_deg', 'ry_deg', 'rz_deg'], ['C0', 'C1', 'C2']):
        ax.plot(x, table[col], 'o-', label=col, color=c, linewidth=2, markersize=6)
    ax.axhline(0, color='gray', linewidth=0.5)
    ax.set_xlabel(f'fixed {param_to_fix}')
    ax.set_ylabel('deg')
    ax.set_title('Chamber rotation (absorbs constraint?)')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # --- Bottom-right: other global angle/depth offsets ---
    ax = axes[1, 1]
    other_globals = [n for n in ['daz_deg', 'del_deg', 'ddepth_mm'] if n != param_to_fix]
    for col, c in zip(other_globals, ['C0', 'C1', 'C2']):
        unit = 'deg' if col.endswith('_deg') else 'mm'
        ax.plot(x, table[col], 'o-', label=f'{col} ({unit})', color=c, linewidth=2, markersize=6)
    ax.axhline(0, color='gray', linewidth=0.5)
    ax.set_xlabel(f'fixed {param_to_fix}')
    ax.set_ylabel('deg or mm')
    ax.set_title('Other global offsets')
    ax.legend()
    ax.grid(True, alpha=0.3)

    fig.suptitle(f'Sweep: holding {param_to_fix} fixed at each value, re-optimizing the rest',
                 fontsize=13, y=1.00)
    plt.tight_layout()
    if save_path is not None:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Saved plot to: {save_path}")
    plt.show()


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

    # Persist as CSV and PNG next to the start_from_file
    out_dir = os.path.dirname(start_from_file) or "."
    base = os.path.splitext(os.path.basename(start_from_file))[0]
    csv_path = os.path.join(out_dir, f"sweep_{base}_fix_{param_to_fix}.csv")
    png_path = os.path.join(out_dir, f"sweep_{base}_fix_{param_to_fix}.png")
    table.to_csv(csv_path, index=False)
    print(f"\nSaved sweep to: {csv_path}")
    plot_sweep(table, param_to_fix, save_path=png_path)

    return table


if __name__ == "__main__":
    # If a CSV path is given on the command line, just plot it and exit.
    # This lets you re-plot a previous sweep without re-running optimization.
    if len(sys.argv) > 1 and sys.argv[1].endswith('.csv'):
        csv_path = sys.argv[1]
        param = sys.argv[2] if len(sys.argv) > 2 else 'del_deg'
        png_path = csv_path.replace('.csv', '.png')
        plot_sweep(csv_path, param, save_path=png_path)
        sys.exit(0)

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
