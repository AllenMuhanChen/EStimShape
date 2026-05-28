"""Master script: pooled PCA + compare multiple tissue-prediction methods
against a reference signal (raw MRI, segmentation labels, or both) using
a single saved corrections file.

Why a separate master from run_per_session.py:
  - The corrections file fixes the chamber + per-session alignment, so the
    sampled signals (raw MRI and/or segmentation labels) at each
    (trajectory, depth) point are identical across predictors. We sample
    once, then swap predictors.
  - Each predictor only computes a tissue_score / p_<class> columns from
    the PC values that are already in the dataframe — no re-optimisation
    needed.
  - Output: per-session weighted Pearson r vs raw MRI **and/or** 3-class
    classification accuracy vs segmentation, plus side-by-side per-session
    plots saved to a comparison directory.

Extend the predictors list at the bottom of this file to add new prediction
methods. Anything implementing the TissuePredictor protocol from
pca_predict.py (a `.name` and `.predict(df) -> df`) plugs in directly.
"""
import os
from typing import List, Optional

import pandas as pd

from clat.util.connection import Connection

from src.analysis.penetrations.pca_predict import (
    DECOMPOSITION_METHOD,
    MODEL_PCA_V1,
    MODEL_PCA_V2,
    MODEL_PCA_V4,
    TissueModelPredictor,
    TissuePredictor,
    USE_VARIMAX,
    load_and_perform_pca,
)
from src.analysis.penetrations.alignment_optimize import (
    MRI_VIEWER_CONFIG_PATH,
    apply_corrections_to_pipeline,
    compute_mri_comparison,
    compute_segmentation_accuracy,
    compute_segmentation_comparison,
    compute_trajectory_fit_scores,
    load_corrections_file,
    load_mri_pipeline,
    load_segmentation_volume,
)
from src.analysis.penetrations.penetration_plots import (
    PLOT_BASE_DIR,
    plot_predictor_comparison_by_session,
)


def compare_predictors_on_corrections(
        conn: Connection,
        corrections_path: str,
        predictors: List[TissuePredictor],
        table_name: str = "PenetrationMetrics",
        mri_config_path: str = MRI_VIEWER_CONFIG_PATH,
        exclude_sessions: Optional[list] = None,
        within_session_normalize: bool = False,
        pc_smooth_sigma: float = 2.0,
        varimax_n_components: int = 6,
        decomp_method: str = DECOMPOSITION_METHOD,
        use_varimax: bool = USE_VARIMAX,
        save_dir: Optional[str] = None,
        target: str = 'both',
        segmentation_path: Optional[str] = None,
) -> dict:
    """Fit pooled PCA once, sample reference signal(s) once under a fixed
    corrections file, then evaluate every predictor against the reference.

    Parameters
    ----------
    target : {'mri', 'segmentation', 'both'}
        - 'mri'          : score = weighted Pearson r between predicted
                           tissue_score and raw MRI intensity.
        - 'segmentation' : score = 3-class accuracy of argmax(p_sulcus, p_gm,
                           p_wm) vs the segmentation-derived class label.
        - 'both'         : compute both; summary table has columns for each.
    segmentation_path : str
        Required when target includes 'segmentation'. Path to the segmentation
        NIfTI (e.g. NMT_v2.0_asym_segmentation_rigid_aligned.nii). Values
        0/1 -> sulcus, 2/3 -> GM, 4 -> WM.

    Returns
    -------
    dict with keys:
        pca, X_pca, feature_columns, scaler   — pooled PCA outputs
        mri_pipeline                          — corrected pipeline
        seg_volume                            — segmentation volume (or None)
        df_with_data                          — df with PC columns + sampled
                                                reference columns
        predictor_results : {name: {'df': df, 'fit_scores': DataFrame or None,
                                    'seg_scores': DataFrame or None}}
        summary : DataFrame indexed by predictor name with per-session r
                  and/or accuracy and aggregated means
    """
    if not predictors:
        raise ValueError("No predictors supplied.")

    if target not in ('mri', 'segmentation', 'both'):
        raise ValueError(f"target must be 'mri'|'segmentation'|'both', got {target!r}")

    do_mri = target in ('mri', 'both')
    do_seg = target in ('segmentation', 'both')

    if do_seg and segmentation_path is None:
        raise ValueError("target includes 'segmentation' but no segmentation_path provided.")

    if save_dir is None:
        corrections_tag = os.path.splitext(os.path.basename(corrections_path))[0]
        save_dir = os.path.join(
            PLOT_BASE_DIR, 'predictor_comparison',
            f"{corrections_tag}_{target}",
        )
    os.makedirs(save_dir, exist_ok=True)
    print(f"\nPredictor comparison output → {save_dir}")
    print(f"  target = {target}")

    # ── 1) Pooled PCA across all sessions ─────────────────────────────────
    df, pca, X_pca, feature_columns, scaler = load_and_perform_pca(
        conn, table_name,
        exclude_sessions=exclude_sessions,
        within_session_normalize=within_session_normalize,
        pc_smooth_sigma=pc_smooth_sigma,
        varimax_n_components=varimax_n_components,
        decomp_method=decomp_method,
        use_varimax=use_varimax,
    )

    # ── 2) Load corrections + apply to MRI pipeline ───────────────────────
    print("\nLoading MRI pipeline ...")
    mri_pipeline = load_mri_pipeline(mri_config_path)

    print(f"\nLoading corrections from {corrections_path}")
    corrections = load_corrections_file(corrections_path)
    print(f"  score_before={corrections.get('score_before', 'NA')}  "
          f"score_after={corrections.get('score_after', 'NA')}")
    print(f"  global: daz={corrections.get('daz_deg', 0):+.3f}°  "
          f"del={corrections.get('del_deg', 0):+.3f}°  "
          f"ddepth={corrections.get('ddepth_mm', 0):+.3f}mm")

    opt_pipeline, daz, del_, ddepth, per_session = apply_corrections_to_pipeline(
        mri_pipeline, corrections,
    )

    # ── 3) Sample reference signal(s) ONCE ────────────────────────────────
    df_with_data = df
    if do_mri:
        print("\nSampling raw MRI along corrected trajectories ...")
        df_with_data = compute_mri_comparison(
            df_with_data, conn, opt_pipeline,
            daz=daz, del_=del_, ddepth=ddepth,
            per_session_corrections=per_session,
        )

    seg_volume = None
    if do_seg:
        print(f"\nLoading segmentation volume: {segmentation_path}")
        seg_volume = load_segmentation_volume(segmentation_path)
        print("Sampling segmentation along corrected trajectories ...")
        df_with_data = compute_segmentation_comparison(
            df_with_data, conn, opt_pipeline, seg_volume,
            daz=daz, del_=del_, ddepth=ddepth,
            per_session_corrections=per_session,
        )

    # ── 4) For each predictor, compute tissue_score + per-session metrics ──
    predictor_results: dict = {}
    summary_rows = []

    for predictor in predictors:
        print(f"\n── Predictor: {predictor.name} ──")
        df_pred = predictor.predict(df_with_data)

        if 'tissue_score' not in df_pred.columns:
            raise RuntimeError(
                f"Predictor {predictor.name!r} did not add a 'tissue_score' column."
            )

        row = {'predictor': predictor.name}
        fit_scores = None
        seg_scores = None

        if do_mri:
            fit_scores = compute_trajectory_fit_scores(df_pred)
            for sid, fs in fit_scores.iterrows():
                row[f'r_{sid}'] = fs['fit_score']
            row['r_mean']   = fit_scores['fit_score'].mean()
            row['r_median'] = fit_scores['fit_score'].median()
            row['r_min']    = fit_scores['fit_score'].min()

        if do_seg:
            seg_scores = compute_segmentation_accuracy(df_pred)
            for sid, fs in seg_scores.iterrows():
                row[f'acc_{sid}'] = fs['accuracy']
            row['acc_mean']   = seg_scores['accuracy'].mean()
            row['acc_median'] = seg_scores['accuracy'].median()
            row['acc_min']    = seg_scores['accuracy'].min()

        predictor_results[predictor.name] = {
            'df': df_pred,
            'fit_scores': fit_scores,
            'seg_scores': seg_scores,
        }
        summary_rows.append(row)

    summary = pd.DataFrame(summary_rows).set_index('predictor')
    print("\n=== Predictor comparison summary ===")
    print(summary.round(4).to_string())

    # ── 5) Side-by-side per-session plots ─────────────────────────────────
    plot_predictor_comparison_by_session(predictor_results, save_dir=save_dir)

    summary_path = os.path.join(save_dir, 'predictor_comparison_summary.csv')
    summary.to_csv(summary_path)
    print(f"\n  Summary CSV → {summary_path}")

    return {
        'pca': pca,
        'X_pca': X_pca,
        'feature_columns': feature_columns,
        'scaler': scaler,
        'mri_pipeline': opt_pipeline,
        'seg_volume': seg_volume,
        'df_with_data': df_with_data,
        'predictor_results': predictor_results,
        'summary': summary,
        'save_dir': save_dir,
    }


if __name__ == "__main__":
    conn = Connection(
        database="allen_data_repository",
        user="xper_rw",
        password="up2nite",
        host="172.30.6.61",
    )

    exclude_sessions = ["260331_0", "260402_0", "260520_0", "260423_0"]

    # Single corrections file used for all predictors so the MRI samples are identical.
    corrections_path = (
        "/home/connorlab/git/EStimShape/EStimShapeAnalysis/src/mri/"
        "opt_20260525_122040.json"
    )

    # Path to the rigid-aligned NMT segmentation. Values 0=out-of-brain, 1=sulcus,
    # 2=GM, 3=sub-brain, 4=WM (mapped internally to sulcus/GM/WM).
    segmentation_path = (
        "/home/connorlab/Documents/MRI/45X_MRI/45X_110315_4_1_corrected_warper_native/rigid_aligned/"
        "NMT_v2.0_asym_segmentation_rigid_aligned.nii.gz"
    )

    # Add / remove TissuePredictor instances here to evaluate different methods.
    predictors: List[TissuePredictor] = [
        # TissueModelPredictor(name='MODEL_PCA_V1', model=MODEL_PCA_V1),
        TissueModelPredictor(name='MODEL_PCA_V2', model=MODEL_PCA_V2),
        # TissueModelPredictor(name='MODEL_PCA_V4', model=MODEL_PCA_V4),
    ]

    results = compare_predictors_on_corrections(
        conn,
        corrections_path=corrections_path,
        predictors=predictors,
        exclude_sessions=exclude_sessions,
        within_session_normalize=False,
        varimax_n_components=2,
        target='both',
        segmentation_path=segmentation_path,
    )
