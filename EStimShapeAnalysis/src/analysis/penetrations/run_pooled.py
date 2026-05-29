"""Master script: pooled PCA + compare multiple tissue-prediction methods
against MRI using a single saved corrections file.

Two entry points:

  - visualize_pooled_pca(conn, ...)        — fit the pooled PCA and dump
    diagnostic plots (scree, loadings, depth-profile-overlaid). Use this
    when iterating on PC count / normalization choices before you have a
    TissueModel to compare. No corrections file or MRI sampling needed.

  - compare_predictors_on_corrections(conn, corrections_path, predictors, ...)
    — full flow: fit pooled PCA, sample MRI once under a fixed corrections
    file, evaluate every predictor's tissue_score against the MRI, render
    side-by-side per-session comparison plots. Also generates the PCA
    diagnostic plots into the comparison directory unless disabled.

To iterate on a new model:
  1. Run visualize_pooled_pca with the PC count you want to try.
  2. Look at loadings / depth profiles in PLOT_BASE_DIR/pca_viz/<tag>/.
  3. Define a TissueModel inline (see __main__ for an example).
  4. Run compare_predictors_on_corrections with the model in the list.
"""
import os
from typing import List, Optional

import pandas as pd

from clat.util.connection import Connection

from src.analysis.penetrations.pca_predict import (
    DECOMPOSITION_METHOD,
    Evidence,
    MODEL_PCA_V1,
    MODEL_PCA_V2,
    MODEL_PCA_V4,
    TissueClass,
    TissueModel,
    TissueModelPredictor,
    TissuePredictor,
    USE_VARIMAX,
    get_feature_correlations,
    get_loadings_df,
    load_and_perform_pca,
    print_feature_correlations,
)
from src.analysis.penetrations.alignment_optimize import (
    MRI_VIEWER_CONFIG_PATH,
    apply_corrections_to_pipeline,
    compute_mri_comparison,
    compute_trajectory_fit_scores,
    load_corrections_file,
    load_mri_pipeline,
)
from src.analysis.penetrations.penetration_plots import (
    PLOT_BASE_DIR,
    plot_correlation_heatmap,
    plot_depth_profiles_all_sessions,
    plot_depth_profiles_by_session,
    plot_depth_profiles_overlaid,
    plot_loadings,
    plot_predictor_comparison_by_session,
    plot_scree,
)


# ---------------------------------------------------------------------------
# PCA diagnostics — used by both visualize_pooled_pca and the comparison
# ---------------------------------------------------------------------------

def _load_and_sample_mri(
        conn: Connection,
        df: pd.DataFrame,
        corrections_path: str,
        mri_config_path: str,
):
    """Load MRI pipeline, apply a corrections file, sample MRI along each
    session's corrected trajectory. Returns (df_with_mri, corrected_pipeline).
    """
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

    print("\nSampling MRI along corrected trajectories ...")
    df_with_mri = compute_mri_comparison(
        df, conn, opt_pipeline,
        daz=daz, del_=del_, ddepth=ddepth,
        per_session_corrections=per_session,
    )
    return df_with_mri, opt_pipeline


def _generate_pca_diagnostics(
        df, pca, feature_columns, n_pcs, save_dir,
        sessions_to_plot_individually=None,
):
    """Run the standard pooled-decomposition diagnostic plot set into save_dir.

    If df already has an 'mri_normalized' column (i.e. MRI was sampled), the
    per-session plot adds an MRI panel too. Raw input features are also
    added as panels in the per-session view.

    sessions_to_plot_individually : list of session_id strings. For each
        session in the list, save a single-session figure showing every PC,
        every raw input feature, and the MRI signal (when available) vs depth.
        None or [] = skip the per-session figures (the depth_profiles_all_sessions
        grid still covers all sessions).
    """
    print("\n" + "=" * 60)
    print("PCA LOADINGS")
    print("=" * 60)
    loadings_df = get_loadings_df(pca, feature_columns)
    print(loadings_df.round(3))

    corr_df = get_feature_correlations(df, feature_columns, n_pcs=n_pcs)
    print_feature_correlations(corr_df)

    plot_scree(pca, save_dir=save_dir)
    plot_loadings(pca, feature_columns, n_pcs=n_pcs, save_dir=save_dir)
    plot_correlation_heatmap(corr_df, feature_columns, save_dir=save_dir)
    plot_depth_profiles_overlaid(df, pca, n_pcs=n_pcs, save_dir=save_dir)
    # Grid of every session × every PC — one figure, easy side-by-side compare.
    plot_depth_profiles_all_sessions(df, pca, n_pcs=n_pcs, save_dir=save_dir)
    # One zoomed figure per requested session — includes raw features and
    # MRI signal (if df has 'mri_normalized') alongside the PC panels.
    if sessions_to_plot_individually:
        plot_depth_profiles_by_session(
            df, pca, n_pcs=n_pcs,
            sessions=sessions_to_plot_individually,
            feature_columns=feature_columns,
            save_dir=save_dir,
        )


def visualize_pooled_pca(
        conn: Connection,
        table_name: str = "PenetrationMetrics",
        exclude_sessions: Optional[list] = None,
        within_session_normalize: bool = False,
        pc_smooth_sigma: float = 2.0,
        n_components: Optional[int] = None,
        varimax_n_components: Optional[int] = None,
        decomp_method: str = DECOMPOSITION_METHOD,
        use_varimax: bool = USE_VARIMAX,
        exclude_features: Optional[list] = None,
        n_pcs_to_plot: Optional[int] = None,
        sessions_to_plot_individually: Optional[list] = None,
        corrections_path: Optional[str] = None,
        mri_config_path: str = MRI_VIEWER_CONFIG_PATH,
        save_dir: Optional[str] = None,
):
    """Fit the pooled decomposition and emit diagnostic plots.

    Useful when iterating on decomp_method, n_components, varimax, or
    normalisation choices before committing to a TissueModel.

    Parameters
    ----------
    decomp_method : 'pca' | 'fa' | 'ica'
    n_components  : total components to extract. If None, defaults to
        varimax_n_components for FA/ICA and to "all features" for PCA.
    varimax_n_components : how many components get varimax-rotated.
        Defaults to n_components when not given. Ignored for ICA.
    corrections_path : optional opt_*.json corrections file. When provided,
        MRI is sampled along each session's corrected trajectory and the
        per-session diagnostic plot adds an MRI panel next to the PCs and
        raw features. No optimisation — corrections are applied as-is.

    Returns the same tuple as load_and_perform_pca:
        (df, pca, X_pca, feature_columns, scaler)
    """
    if varimax_n_components is None and n_components is not None:
        varimax_n_components = n_components

    if save_dir is None:
        norm_tag = 'T' if within_session_normalize else 'F'
        vm_tag   = 'T' if use_varimax else 'F'
        ncomp_tag = (n_components if n_components is not None
                     else (varimax_n_components or 'all'))
        tag = (f"{decomp_method}_{ncomp_tag}pcs_vm{vm_tag}"
               f"_norm{norm_tag}_sig{pc_smooth_sigma:.1f}")
        if exclude_features:
            tag += f"_excl{len(exclude_features)}"
        save_dir = os.path.join(PLOT_BASE_DIR, 'pca_viz', tag)
    os.makedirs(save_dir, exist_ok=True)
    print(f"\nDecomposition visualisation output → {save_dir}")

    df, pca, X_pca, feature_columns, scaler = load_and_perform_pca(
        conn, table_name,
        exclude_sessions=exclude_sessions,
        within_session_normalize=within_session_normalize,
        pc_smooth_sigma=pc_smooth_sigma,
        n_components=n_components,
        varimax_n_components=varimax_n_components,
        decomp_method=decomp_method,
        use_varimax=use_varimax,
        exclude_features=exclude_features,
    )

    if n_pcs_to_plot is None:
        n_pcs_to_plot = max(varimax_n_components or X_pca.shape[1], 1)
    n_pcs_to_plot = min(n_pcs_to_plot, X_pca.shape[1])

    # Optionally sample MRI under a corrections file so the per-session
    # diagnostic plot can include an MRI panel alongside PCs and features.
    df_for_plots = df
    if corrections_path is not None:
        df_for_plots, _ = _load_and_sample_mri(conn, df, corrections_path, mri_config_path)

    _generate_pca_diagnostics(
        df_for_plots, pca, feature_columns, n_pcs_to_plot, save_dir,
        sessions_to_plot_individually=sessions_to_plot_individually,
    )

    return df_for_plots, pca, X_pca, feature_columns, scaler


# ---------------------------------------------------------------------------
# Predictor comparison against MRI
# ---------------------------------------------------------------------------

def compare_predictors_on_corrections(
        conn: Connection,
        corrections_path: str,
        predictors: List[TissuePredictor],
        table_name: str = "PenetrationMetrics",
        mri_config_path: str = MRI_VIEWER_CONFIG_PATH,
        exclude_sessions: Optional[list] = None,
        within_session_normalize: bool = False,
        pc_smooth_sigma: float = 2.0,
        n_components: Optional[int] = None,
        varimax_n_components: Optional[int] = None,
        decomp_method: str = DECOMPOSITION_METHOD,
        use_varimax: bool = USE_VARIMAX,
        exclude_features: Optional[list] = None,
        save_dir: Optional[str] = None,
        plot_pca_diagnostics: bool = True,
        n_pcs_to_plot: Optional[int] = None,
        sessions_to_plot_individually: Optional[list] = None,
) -> dict:
    """Fit pooled PCA once, sample MRI once under a fixed corrections file,
    then evaluate every predictor's tissue_score against the MRI.

    plot_pca_diagnostics : if True, also dumps scree / loadings / depth-profile-
        overlaid plots of the pooled PCA into save_dir before the comparison.
    n_pcs_to_plot : how many PCs to include in the diagnostic plots
        (default = varimax_n_components).

    Returns
    -------
    dict with keys:
        pca, X_pca, feature_columns, scaler   — pooled PCA outputs
        mri_pipeline                          — corrected pipeline
        df_with_mri                           — df with PC columns + MRI columns
        predictor_results : {name: {'df': df, 'fit_scores': DataFrame}}
        summary : DataFrame indexed by predictor name with per-session r and means
    """
    if not predictors:
        raise ValueError("No predictors supplied.")

    if varimax_n_components is None and n_components is not None:
        varimax_n_components = n_components

    if save_dir is None:
        corrections_tag = os.path.splitext(os.path.basename(corrections_path))[0]
        ncomp_tag = (n_components if n_components is not None
                     else (varimax_n_components or 'all'))
        run_tag = f"{corrections_tag}_{decomp_method}_{ncomp_tag}pcs"
        if exclude_features:
            run_tag += f"_excl{len(exclude_features)}"
        save_dir = os.path.join(
            PLOT_BASE_DIR, 'predictor_comparison', run_tag,
        )
    os.makedirs(save_dir, exist_ok=True)
    print(f"\nPredictor comparison output → {save_dir}")

    # ── 1) Pooled decomposition across all sessions ──────────────────────
    df, pca, X_pca, feature_columns, scaler = load_and_perform_pca(
        conn, table_name,
        exclude_sessions=exclude_sessions,
        within_session_normalize=within_session_normalize,
        pc_smooth_sigma=pc_smooth_sigma,
        n_components=n_components,
        varimax_n_components=varimax_n_components,
        decomp_method=decomp_method,
        use_varimax=use_varimax,
        exclude_features=exclude_features,
    )

    # ── 2) Load corrections, apply, and sample MRI ONCE ──────────────────
    df_with_mri, opt_pipeline = _load_and_sample_mri(
        conn, df, corrections_path, mri_config_path,
    )

    # ── 3) PCA diagnostics (incl. per-session PC + features + MRI panels) ──
    if plot_pca_diagnostics:
        if n_pcs_to_plot is None:
            n_pcs_to_plot = max(varimax_n_components or X_pca.shape[1], 1)
        n_pcs_to_plot = min(n_pcs_to_plot, X_pca.shape[1])
        _generate_pca_diagnostics(
            df_with_mri, pca, feature_columns, n_pcs_to_plot, save_dir,
            sessions_to_plot_individually=sessions_to_plot_individually,
        )

    # ── 4) For each predictor, compute tissue_score + per-session r ───────
    predictor_results: dict = {}
    summary_rows = []

    for predictor in predictors:
        print(f"\n── Predictor: {predictor.name} ──")
        df_pred = predictor.predict(df_with_mri)

        if 'tissue_score' not in df_pred.columns:
            raise RuntimeError(
                f"Predictor {predictor.name!r} did not add a 'tissue_score' column."
            )

        fit_scores = compute_trajectory_fit_scores(df_pred)
        predictor_results[predictor.name] = {
            'df': df_pred,
            'fit_scores': fit_scores,
        }

        row = {'predictor': predictor.name}
        for sid, fs in fit_scores.iterrows():
            row[f'r_{sid}'] = fs['fit_score']
        row['r_mean']   = fit_scores['fit_score'].mean()
        row['r_median'] = fit_scores['fit_score'].median()
        row['r_min']    = fit_scores['fit_score'].min()
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
        'df_with_mri': df_with_mri,
        'predictor_results': predictor_results,
        'summary': summary,
        'save_dir': save_dir,
    }


# ---------------------------------------------------------------------------
# __main__
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # ════════════════════════════════════════════════════════════════════
    # CONFIGURATION — edit these to try different decomposition setups.
    # ════════════════════════════════════════════════════════════════════
    EXCLUDE_SESSIONS = ["260331_0", "260402_0", "260520_0", "260423_0"]

    # --- Decomposition method ---
    DECOMP_METHOD = 'pca'                 # 'pca' | 'fa' | 'ica'
    N_COMPONENTS = 2                      # how many components to extract
    USE_VARIMAX_ROTATION = True           # rotate for interpretability (ignored for ICA)
    VARIMAX_N_COMPONENTS = None           # None → rotate all N_COMPONENTS

    # --- Feature preprocessing ---
    WITHIN_SESSION_NORMALIZE = False      # z-score features per session before decomposition
    PC_SMOOTH_SIGMA = 2.0                 # gaussian smoothing of component scores vs depth
    # Drop these PenetrationMetrics columns from the feature matrix before
    # decomposition (in addition to session_id / depth_under_chamber_mm /
    # r_squared which are always excluded). Use this to test "what does
    # the PCA look like without metric X?". [] = use all numeric features.
    EXCLUDE_FEATURES: list = []

    # --- Plot scope ---
    N_PCS_TO_PLOT = None                  # None → matches N_COMPONENTS
    # Sessions to plot in their own dedicated per-session figures (one figure
    # per session, all PCs side by side). The depth_profiles_all_sessions
    # grid always covers every session regardless; this list adds zoomed
    # single-session views on top. [] = skip.
    SESSIONS_TO_PLOT_INDIVIDUALLY: list = []

    # --- Trajectory alignment ---
    CORRECTIONS_PATH = (
        "/home/connorlab/git/EStimShape/EStimShapeAnalysis/src/mri/"
        "opt_20260525_122040.json"
    )

    conn = Connection(
        database="allen_data_repository",
        user="xper_rw",
        password="up2nite",
        host="172.30.6.61",
    )

    # ════════════════════════════════════════════════════════════════════
    # TISSUE MODELS — add custom models inline, no need to edit pca_predict.py
    # while iterating.  Each Evidence references a PC column (PC1, PC2, ...).
    # Promote a stabilised model to pca_predict.py once you're happy with it.
    # ════════════════════════════════════════════════════════════════════

    # Example: 3-PC variant — uncomment after running visualize_pooled_pca
    # with VARIMAX_N_COMPONENTS=3 and inspecting the loadings:
    # MODEL_PCA_V5_3PC = TissueModel([
    #     TissueClass('wm', score=1.0, evidence=[
    #         Evidence('PC1', sign=+1),    # set sign based on loadings plot
    #         Evidence('PC2', sign=-1),
    #         Evidence('PC3', sign=+1),    # whatever PC3 captures
    #     ]),
    #     TissueClass('gm', score=0.5, evidence=[
    #         Evidence('PC1', sign=+1),
    #         Evidence('PC2', sign=+1),
    #     ]),
    #     TissueClass('sulcus', score=0.0, evidence=[
    #         Evidence('PC1', sign=-1),
    #     ]),
    # ])

    predictors: List[TissuePredictor] = [
        # TissueModelPredictor(name='MODEL_PCA_V1', model=MODEL_PCA_V1),
        TissueModelPredictor(name='MODEL_PCA_V2', model=MODEL_PCA_V2),
        # TissueModelPredictor(name='MODEL_PCA_V4', model=MODEL_PCA_V4),
        # TissueModelPredictor(name='MODEL_PCA_V5_3PC', model=MODEL_PCA_V5_3PC),
    ]

    # ════════════════════════════════════════════════════════════════════
    # WORKFLOW
    # ════════════════════════════════════════════════════════════════════
    # Step 1 (optional): just fit the PCA and look at loadings / depth profiles.
    # Use this when changing VARIMAX_N_COMPONENTS to design a new model.
    # Comment out the comparison call below while iterating.
    #
    # df, pca, X_pca, feature_columns, scaler = visualize_pooled_pca(
    #     conn,
    #     exclude_sessions=EXCLUDE_SESSIONS,
    #     within_session_normalize=WITHIN_SESSION_NORMALIZE,
    #     pc_smooth_sigma=PC_SMOOTH_SIGMA,
    #     decomp_method=DECOMP_METHOD,
    #     n_components=N_COMPONENTS,
    #     varimax_n_components=VARIMAX_N_COMPONENTS,
    #     use_varimax=USE_VARIMAX_ROTATION,
    #     n_pcs_to_plot=N_PCS_TO_PLOT,
    #     sessions_to_plot_individually=SESSIONS_TO_PLOT_INDIVIDUALLY,
    #     corrections_path=CORRECTIONS_PATH,   # optional — adds MRI panel to per-session plots
    # )

    # Step 2: compare predictors against MRI under a fixed corrections file.
    # plot_pca_diagnostics=True emits the same diagnostic plots into the
    # comparison directory, so step 1 is optional unless you don't have a
    # model ready yet.
    results = compare_predictors_on_corrections(
        conn,
        corrections_path=CORRECTIONS_PATH,
        predictors=predictors,
        exclude_sessions=EXCLUDE_SESSIONS,
        within_session_normalize=WITHIN_SESSION_NORMALIZE,
        pc_smooth_sigma=PC_SMOOTH_SIGMA,
        decomp_method=DECOMP_METHOD,
        n_components=N_COMPONENTS,
        varimax_n_components=VARIMAX_N_COMPONENTS,
        use_varimax=USE_VARIMAX_ROTATION,
        exclude_features=EXCLUDE_FEATURES,
        plot_pca_diagnostics=True,
        n_pcs_to_plot=N_PCS_TO_PLOT,
        sessions_to_plot_individually=SESSIONS_TO_PLOT_INDIVIDUALLY,
    )
