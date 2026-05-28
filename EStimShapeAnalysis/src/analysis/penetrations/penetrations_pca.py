"""Backwards-compatibility shim.

The original penetrations_pca module was split into four files for sustainability:

  - pca_predict.py          : PCA / FA + TissueModel + tissue prediction
  - alignment_optimize.py   : MRI sampling + chamber/per-session optimisation
  - penetration_plots.py    : all plotting + run-tag/log helpers
  - run_per_session.py      : standard end-to-end pipeline (the old run_analysis)
  - run_pooled.py           : pooled-PCA + multi-predictor comparison harness

This module re-exports the public names the rest of the codebase still imports
from `penetrations_pca` (eval_corrections.py, explore_alternative_corrections.py)
so those keep working without changes. New code should import directly from the
target modules above.
"""
from src.analysis.penetrations.pca_predict import (  # noqa: F401
    DECOMPOSITION_METHOD,
    Evidence,
    MODEL_PCA_V1,
    MODEL_PCA_V2,
    MODEL_PCA_V3,
    MODEL_PCA_V4,
    TissueClass,
    TissueModel,
    TissueModelPredictor,
    TissuePredictor,
    USE_VARIMAX,
    WM_THRESHOLD,
    _FactorAnalysisAdapter,
    _TISSUE_CONF_FA_NO_VARIMAX,
    _TISSUE_CONF_FA_VARIMAX,
    _TISSUE_CONF_PCA,
    _gmm_brain_threshold,
    _varimax,
    _within_session_zscore,
    compute_tissue_confidence,
    get_feature_correlations,
    get_loadings_df,
    load_and_perform_pca,
    print_feature_correlations,
    run_cortex_pca,
)

from src.analysis.penetrations.alignment_optimize import (  # noqa: F401
    CHAMBER_DIST_PENALTY,
    CHAMBER_PARAM_PENALTY,
    CHAMBER_PARAM_TOLERANCES,
    ENABLE_PER_SESSION_CORRECTIONS,
    MRI_VIEWER_CONFIG_PATH,
    OPTIMIZATIONS_path,
    CHAMBER_IN_BRAIN_PENALTY,
    CHAMBER_RADIUS_MM,
    N_CHAMBER_RING_SAMPLES,
    SESSION_CORRECTION_BOUNDS,
    SESSION_CORRECTION_PENALTY,
    SOFTMIN_BETA,
    TOP_DOWNWEIGHT_FACTOR,
    TOP_DOWNWEIGHT_MM,
    VARIANCE_PENALTY,
    _OPT_PARAM_NAMES,
    _OPT_X0,
    _apply_chamber_params,
    _tanh_bound,
    _weighted_pearson_r,
    apply_optimized_pipeline,
    apply_pca_opt_result,
    compute_mri_comparison,
    compute_trajectory_fit_scores,
    get_penetration_for_session,
    load_mri_pipeline,
    optimize_trajectory_alignment,
    sample_mri_along_trajectory,
    save_optimized_params,
)

from src.analysis.penetrations.penetration_plots import (  # noqa: F401
    PLOT_BASE_DIR,
    _make_run_dirs,
    _opt_run_tag,
    _pca_run_tag,
    _save_fig,
    _setup_depth_yaxis,
    _write_fit_log,
    plot_correlation_heatmap,
    plot_cortex_pc_scatter,
    plot_depth_profiles_all_sessions,
    plot_depth_profiles_by_session,
    plot_depth_profiles_overlaid,
    plot_loadings,
    plot_mri_comparison_by_session,
    plot_pca_scatter,
    plot_scree,
    plot_tissue_confidence_by_session,
)

from src.analysis.penetrations.run_per_session import run_analysis  # noqa: F401
