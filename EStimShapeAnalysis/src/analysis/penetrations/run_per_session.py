"""Master script: pooled PCA → tissue prediction → MRI alignment optimisation.

This is the file-3 entry point in the refactor — it runs the standard
end-to-end pipeline that `penetrations_pca.py:run_analysis` used to provide.
Despite the name, the PCA is fit on the pooled dataset across all sessions
(the "per_session" naming refers to per-session corrections in the alignment
step, not to per-session PCA).

For comparing multiple tissue-prediction methods against a single corrections
file, use run_pooled.py instead.
"""
from typing import Optional

from clat.util.connection import Connection

from src.analysis.penetrations.pca_predict import (
    DECOMPOSITION_METHOD,
    USE_VARIMAX,
    MODEL_PCA_V1,
    MODEL_PCA_V2,
    TissueModel,
    TissuePipeline,
    _TISSUE_CONF_FA_NO_VARIMAX,
    _TISSUE_CONF_FA_VARIMAX,
    compute_tissue_confidence,
    get_feature_correlations,
    get_loadings_df,
    load_and_perform_pca,
    print_feature_correlations,
    run_cortex_pca, MODEL_ICA_V1,
)
from src.analysis.penetrations.alignment_optimize import (
    CHAMBER_DIST_PENALTY,
    CHAMBER_IN_BRAIN_PENALTY,
    CHAMBER_PARAM_PENALTY,
    CHAMBER_RADIUS_MM,
    ENABLE_PER_SESSION_CORRECTIONS,
    MRI_VIEWER_CONFIG_PATH,
    N_CHAMBER_RING_SAMPLES,
    SESSION_CORRECTION_PENALTY,
    SOFTMIN_BETA,
    TOP_DOWNWEIGHT_FACTOR,
    TOP_DOWNWEIGHT_MM,
    VARIANCE_PENALTY,
    apply_optimized_pipeline,
    compute_mri_comparison,
    compute_trajectory_fit_scores,
    load_mri_pipeline,
    optimize_trajectory_alignment,
    save_optimized_params,
)
from src.analysis.penetrations.penetration_plots import (
    _make_run_dirs,
    _opt_run_tag,
    _pca_run_tag,
    _write_fit_log,
    plot_correlation_heatmap,
    plot_depth_profiles_overlaid,
    plot_loadings,
    plot_mri_comparison_by_session,
    plot_pca_scatter,
    plot_scree,
    plot_tissue_confidence_by_session,
)
from src.analysis.penetrations.run_pooled import EXCUDE_REL_LFP, PIPE_PCA_exclude_rel_lfp, PIPE_PCA_new


def run_analysis(conn: Connection, table_name: str = "PenetrationMetrics", n_pcs: int = 4,
                 mri_config_path: str = MRI_VIEWER_CONFIG_PATH, exclude_sessions=None,
                 pipeline: Optional[TissuePipeline] = None,
                 within_session_normalize: bool = False,
                 swap_tissue_pcs: bool = False,
                 pc_smooth_sigma: float = 2.0,
                 n_components: Optional[int] = None,
                 varimax_n_components: int = 6,
                 decomp_method: str = DECOMPOSITION_METHOD,
                 use_varimax: bool = USE_VARIMAX,
                 exclude_features: Optional[list] = None,
                 tissue_model: Optional[TissueModel] = None,
                 maxiter: int = 100000,
                 start_from_file: Optional[str] = None,
                 enable_per_session_corrections: bool = ENABLE_PER_SESSION_CORRECTIONS,
                 session_corr_bounds: dict = None,
                 session_corr_penalty: float = SESSION_CORRECTION_PENALTY,
                 chamber_dist_penalty: float = CHAMBER_DIST_PENALTY,
                 chamber_param_penalty: float = CHAMBER_PARAM_PENALTY,
                 chamber_param_tolerances: dict = None,
                 variance_penalty: float = VARIANCE_PENALTY,
                 softmin_beta: float = SOFTMIN_BETA,
                 optimizer: str = 'nelder-mead',
                 use_confidence_weights: bool = True,
                 top_downweight_mm: float = TOP_DOWNWEIGHT_MM,
                 top_downweight_factor: float = TOP_DOWNWEIGHT_FACTOR,
                 fixed_globals: Optional[dict] = None,
                 no_skull_mri_path: Optional[str] = None,
                 chamber_in_brain_penalty: float = CHAMBER_IN_BRAIN_PENALTY,
                 chamber_radius_mm: float = CHAMBER_RADIUS_MM,
                 n_chamber_ring_samples: int = N_CHAMBER_RING_SAMPLES):
    """Run complete PCA analysis with correlations, plots, and trajectory alignment.

    no_skull_mri_path : optional path to a brain-extracted MRI volume (e.g.
        subject_ns_rigid_aligned). When provided, the optimiser samples this
        volume instead of the config's `default_path`, so trajectory MRI
        signal is zero outside the brain. Required if you want the
        chamber-in-brain penalty to be meaningful.

    chamber_in_brain_penalty : λ on a penalty that samples the MRI at
        n_chamber_ring_samples points around the chamber circle (radius
        chamber_radius_mm) and adds the mean normalised intensity to the
        loss. Defaults to 0 (disabled). When >0, use with no_skull_mri_path —
        otherwise the penalty fires for any non-zero voxel (skull / scalp)
        too, which is wrong.

    pipeline : if provided, a TissuePipeline. Its decomp_method,
        n_components, varimax_n_components, use_varimax,
        within_session_normalize, pc_smooth_sigma, exclude_features, and
        model OVERRIDE the corresponding individual keyword arguments —
        so the same pipeline object you pass to run_pooled's
        compare_pipelines_on_corrections drops in here without restating
        the recipe. Set pipeline=None to use the individual kwargs
        (legacy behaviour).
    """
    # Unpack the pipeline (if given) into the legacy kwargs so the rest of
    # this function sees a uniform interface. Pipeline fields win.
    if pipeline is not None:
        print(f"\nUsing TissuePipeline: {pipeline.name}  ({pipeline.tag()})")
        decomp_method = pipeline.decomp_method
        n_components = pipeline.n_components
        varimax_n_components = pipeline.varimax_n_components
        use_varimax = pipeline.use_varimax
        within_session_normalize = pipeline.within_session_normalize
        pc_smooth_sigma = pipeline.pc_smooth_sigma
        exclude_features = list(pipeline.exclude_features)
        tissue_model = pipeline.model

    pca_tag = _pca_run_tag(
        decomp_method=decomp_method,
        varimax_n_components=varimax_n_components,
        use_varimax=use_varimax,
        within_session_normalize=within_session_normalize,
        pc_smooth_sigma=pc_smooth_sigma,
        exclude_sessions=exclude_sessions,
    )
    opt_tag = _opt_run_tag(
        softmin_beta=softmin_beta,
        variance_penalty=variance_penalty,
        enable_per_session_corrections=enable_per_session_corrections,
        chamber_dist_penalty=chamber_dist_penalty,
        chamber_param_penalty=chamber_param_penalty,
        session_corr_penalty=session_corr_penalty,
    )
    pca_dir, opt_dir = _make_run_dirs(pca_tag, opt_tag)
    print(f"\nPlots → {pca_dir}")
    print(f"Opt  → {opt_dir}")

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

    print("\n" + "=" * 60)
    print("PCA LOADINGS")
    print("=" * 60)
    loadings_df = get_loadings_df(pca, feature_columns)
    print(loadings_df.round(3))

    corr_df = get_feature_correlations(df, feature_columns, n_pcs=n_pcs)
    print_feature_correlations(corr_df)

    plot_scree(pca, save_dir=pca_dir)
    plot_loadings(pca, feature_columns, n_pcs=n_pcs, save_dir=pca_dir)
    plot_correlation_heatmap(corr_df, feature_columns, save_dir=pca_dir)
    plot_pca_scatter(df, pca, X_pca, plot_components=list(range(min(n_pcs, 3))), save_dir=pca_dir)

    plot_depth_profiles_overlaid(df, pca, n_pcs=n_pcs, save_dir=pca_dir)

    # Tissue confidence
    if tissue_model is not None:
        df_conf = compute_tissue_confidence(df, model=tissue_model)
    elif decomp_method == 'fa':
        tissue_conf = _TISSUE_CONF_FA_VARIMAX if use_varimax else _TISSUE_CONF_FA_NO_VARIMAX
        df_conf = compute_tissue_confidence(df, **tissue_conf)
    else:
        df_conf = compute_tissue_confidence(df, model=MODEL_PCA_V1)
    plot_tissue_confidence_by_session(df_conf, pca=pca, n_pcs=n_pcs, save_dir=pca_dir)

    cortex_pca_result = run_cortex_pca(df_conf, feature_columns, n_pcs=4, save_dir=pca_dir)

    fit_scores = None
    opt_result = None
    mri_pipeline = None
    try:
        print("\nLoading MRI pipeline ...")
        if no_skull_mri_path is not None:
            print(f"  Using brain-extracted MRI: {no_skull_mri_path}")
        mri_pipeline = load_mri_pipeline(mri_config_path, volume_path=no_skull_mri_path)

        print("\n── Initial MRI comparison ──")
        df_conf = compute_mri_comparison(df_conf, conn, mri_pipeline)
        fit_scores = compute_trajectory_fit_scores(df_conf)

        print("\n── Optimising transformation ──")
        opt_result = optimize_trajectory_alignment(df_conf, conn, mri_pipeline,
                                                   maxiter=maxiter,
                                                   start_from_file=start_from_file,
                                                   enable_per_session_corrections=enable_per_session_corrections,
                                                   session_corr_bounds=session_corr_bounds,
                                                   session_corr_penalty=session_corr_penalty,
                                                   chamber_dist_penalty=chamber_dist_penalty,
                                                   chamber_param_penalty=chamber_param_penalty,
                                                   chamber_param_tolerances=chamber_param_tolerances,
                                                   variance_penalty=variance_penalty,
                                                   softmin_beta=softmin_beta,
                                                   optimizer=optimizer,
                                                   use_confidence_weights=use_confidence_weights,
                                                   top_downweight_mm=top_downweight_mm,
                                                   top_downweight_factor=top_downweight_factor,
                                                   fixed_globals=fixed_globals,
                                                   chamber_in_brain_penalty=chamber_in_brain_penalty,
                                                   chamber_radius_mm=chamber_radius_mm,
                                                   n_chamber_ring_samples=n_chamber_ring_samples)

        print("\n── MRI comparison with optimised transformation ──")
        opt_pipeline, daz, del_, ddepth = apply_optimized_pipeline(mri_pipeline, opt_result)
        df_conf = compute_mri_comparison(df_conf, conn, opt_pipeline,
                                         daz=daz, del_=del_, ddepth=ddepth,
                                         per_session_corrections=opt_result.get('per_session_corrections'))
        fit_scores = compute_trajectory_fit_scores(df_conf)
        plot_mri_comparison_by_session(df_conf, fit_scores, save_dir=opt_dir)

        _write_fit_log(opt_dir, pca_tag, fit_scores=fit_scores, opt_params=dict(
            softmin_beta=softmin_beta,
            variance_penalty=variance_penalty,
            enable_per_session_corrections=enable_per_session_corrections,
            chamber_dist_penalty=chamber_dist_penalty,
            chamber_param_penalty=chamber_param_penalty,
            chamber_param_tolerances=chamber_param_tolerances,
            session_corr_penalty=session_corr_penalty,
            session_corr_bounds=session_corr_bounds,
            top_downweight_mm=top_downweight_mm,
            top_downweight_factor=top_downweight_factor,
            fixed_globals=fixed_globals,
            no_skull_mri_path=no_skull_mri_path,
            chamber_in_brain_penalty=chamber_in_brain_penalty,
            chamber_radius_mm=chamber_radius_mm,
            n_chamber_ring_samples=n_chamber_ring_samples,
            maxiter=maxiter,
            start_from_file=start_from_file,
        ), opt_result=opt_result)

        print("\n── Optimisation complete ──")
        print(f"  score: {opt_result['score_before']:.4f} → {opt_result['score_after']:.4f}")
        answer = input("Save this result? [y/N]: ").strip().lower()
        if answer == 'y':
            opt_result['result_path'] = save_optimized_params(opt_result, mri_pipeline, copy_dir=opt_dir)
        else:
            print("  Result not saved.")

    except Exception as exc:
        import traceback
        print(f"  MRI comparison / optimisation skipped: {exc}")
        traceback.print_exc()

    return {
        'df': df_conf,
        'pca': pca,
        'X_pca': X_pca,
        'feature_columns': feature_columns,
        'loadings': loadings_df,
        'correlations': corr_df,
        'fit_scores': fit_scores,
        'opt_result': opt_result,
        'mri_pipeline': mri_pipeline,
        'cortex_pca': cortex_pca_result,
    }


if __name__ == "__main__":
    from src.analysis.penetrations.pca_predict import Evidence, TissueClass

    conn = Connection(
        database="allen_data_repository",
        user="xper_rw",
        password="up2nite",
        host="172.30.6.61",
    )

    exclude_sessions = ["260331_0", "260402_0", "260520_0", "260423_0", "260611_0"]
    start_from_file = None
    # start_from_file = "/home/connorlab/git/EStimShape/EStimShapeAnalysis/src/mri/opt_20260525_121133_best.json"
    # start_from_file = "/home/connorlab/git/EStimShape/EStimShapeAnalysis/src/mri/opt_20260529_132317_best_bottom.json"
    # start_from_file = "/home/connorlab/git/EStimShape/EStimShapeAnalysis/src/mri/opt_20260529_144758.json"
    # start_from_file = "/home/connorlab/git/EStimShape/EStimShapeAnalysis/src/mri/opt_20260601_152133.json"

    # ════════════════════════════════════════════════════════════════════
    # PIPELINE — the same object you'd drop into run_pooled's
    # compare_pipelines_on_corrections. Owns the full recipe
    # (decomposition + tissue model). Build inline here while
    # experimenting; once stable, promote MODEL_*** and the pipeline to
    # pca_predict.py so both scripts can import the same name.
    #
    # Swap which PIPELINE = ... line is active to switch recipes. The
    # alternative is kept above as a commented-out template.
    # ════════════════════════════════════════════════════════════════════

    # --- Legacy PCA-V2 pipeline (was the previous default) ---
    PIPE_PCA_V2 = TissuePipeline(
        name='PCA_V2',
        model=MODEL_PCA_V2,
        decomp_method='pca',
        n_components=2,
        use_varimax=False,
        within_session_normalize=True,
        pc_smooth_sigma=2.0,
        exclude_features=[],
    )
    PIPELINE = PIPE_PCA_V2
    # PIPELINE = PIPE_PCA_new

    # PIPELINE = PIPE_PCA_exclude_rel_lfp

    # ════════════════════════════════════════════════════════════════════
    # Run — pipeline supplies the decomp + model; everything else here is
    # alignment / regularisation / MRI / penalty configuration.
    # ════════════════════════════════════════════════════════════════════
    results = run_analysis(
        conn,
        pipeline=PIPELINE,
        exclude_sessions=exclude_sessions,
        maxiter=100000,
        start_from_file=start_from_file,
        enable_per_session_corrections=True,
        session_corr_bounds=None,
        varimax_n_components=0,
        n_pcs=2,
        session_corr_penalty=1.0,
        chamber_dist_penalty=0.000,
        chamber_param_penalty=0.0001,
        # chamber_param_tolerances=dict(t_mm=2, r_deg=2.5, daz_deg=0.5, del_deg=0.5, ddepth_mm=1.0),
        chamber_param_tolerances=dict(t_mm=2, r_deg=2.5, daz_deg=0.01, del_deg=0.01, ddepth_mm=0.1),
        variance_penalty=0.0,
        softmin_beta=20,
        optimizer='cma-es',
        use_confidence_weights=False,
        top_downweight_mm=5,
        top_downweight_factor=0.25,
        # Brain-extracted MRI: zero outside brain so the optimiser doesn't fit
        # to skull/scalp signal. Set to None to fall back to the config default.
        no_skull_mri_path="/home/connorlab/Documents/MRI/45X_MRI/45X_110315_4_1_corrected_warper_native/rigid_aligned/subject_ns_rigid_aligned.nii.gz",
        # no_skull_mri_path="/home/connorlab/Documents/MRI/45X_MRI/45X_110315_4_1_corrected_warper_native/rigid_aligned/NMT_v2.0_asym_SS_rigid_aligned.nii.gz",
        # Heavy penalty (λ) for any part of the chamber ring landing inside
        # brain tissue. Samples 32 points around the chamber circle (radius
        # 7 mm by default). Only meaningful with no_skull_mri_path set;
        # 0 = disabled, 10 = heavy (≈ 1.0 swing in mean fit r per unit penalty).
        chamber_in_brain_penalty=10.0,
        chamber_radius_mm=7.0,
        n_chamber_ring_samples=32,
    )
