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
    _TISSUE_CONF_FA_NO_VARIMAX,
    _TISSUE_CONF_FA_VARIMAX,
    compute_tissue_confidence,
    get_feature_correlations,
    get_loadings_df,
    load_and_perform_pca,
    print_feature_correlations,
    run_cortex_pca,
)
from src.analysis.penetrations.alignment_optimize import (
    CHAMBER_DIST_PENALTY,
    CHAMBER_PARAM_PENALTY,
    ENABLE_PER_SESSION_CORRECTIONS,
    MRI_VIEWER_CONFIG_PATH,
    SESSION_CORRECTION_PENALTY,
    SOFTMIN_BETA,
    TOP_DOWNWEIGHT_FACTOR,
    TOP_DOWNWEIGHT_MM,
    VARIANCE_PENALTY,
    apply_optimized_pipeline,
    compute_mri_comparison,
    compute_segmentation_accuracy,
    compute_segmentation_comparison,
    compute_trajectory_fit_scores,
    load_mri_pipeline,
    load_segmentation_volume,
    optimize_trajectory_alignment,
    optimize_trajectory_alignment_seg,
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


def run_analysis(conn: Connection, table_name: str = "PenetrationMetrics", n_pcs: int = 4,
                 mri_config_path: str = MRI_VIEWER_CONFIG_PATH, exclude_sessions=None,
                 within_session_normalize: bool = False,
                 swap_tissue_pcs: bool = False,
                 pc_smooth_sigma: float = 2.0,
                 varimax_n_components: int = 6,
                 decomp_method: str = DECOMPOSITION_METHOD,
                 use_varimax: bool = USE_VARIMAX,
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
                 optimize_target: str = 'mri',
                 segmentation_path: Optional[str] = None):
    """Run complete PCA analysis with correlations, plots, and trajectory alignment.

    optimize_target : {'mri', 'segmentation'}
        - 'mri'         : optimise weighted Pearson r between tissue_score
                          and raw MRI intensity (default; original behaviour).
        - 'segmentation': optimise 3-class classification accuracy of
                          argmax(p_*) against the NMT-style segmentation
                          label. Requires segmentation_path.
    """
    if optimize_target not in ('mri', 'segmentation'):
        raise ValueError(f"optimize_target must be 'mri' or 'segmentation', "
                         f"got {optimize_target!r}")
    if optimize_target == 'segmentation' and segmentation_path is None:
        raise ValueError("optimize_target='segmentation' requires segmentation_path")

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
        varimax_n_components=varimax_n_components,
        decomp_method=decomp_method,
        use_varimax=use_varimax,
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
    seg_scores = None
    opt_result = None
    mri_pipeline = None
    seg_volume = None
    try:
        print("\nLoading MRI pipeline ...")
        mri_pipeline = load_mri_pipeline(mri_config_path)

        if optimize_target == 'segmentation':
            print(f"\nLoading segmentation volume: {segmentation_path}")
            seg_volume = load_segmentation_volume(segmentation_path)

            print("\n── Initial segmentation comparison ──")
            df_conf = compute_segmentation_comparison(df_conf, conn, mri_pipeline, seg_volume)
            seg_scores = compute_segmentation_accuracy(df_conf)

            print("\n── Optimising transformation (segmentation accuracy) ──")
            opt_result = optimize_trajectory_alignment_seg(
                df_conf, conn, mri_pipeline, seg_volume,
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
            )

            print("\n── Comparisons with optimised transformation ──")
            opt_pipeline, daz, del_, ddepth = apply_optimized_pipeline(mri_pipeline, opt_result)
            per_sess = opt_result.get('per_session_corrections')
            df_conf = compute_mri_comparison(df_conf, conn, opt_pipeline,
                                             daz=daz, del_=del_, ddepth=ddepth,
                                             per_session_corrections=per_sess)
            df_conf = compute_segmentation_comparison(df_conf, conn, opt_pipeline, seg_volume,
                                                      daz=daz, del_=del_, ddepth=ddepth,
                                                      per_session_corrections=per_sess)
            fit_scores = compute_trajectory_fit_scores(df_conf)
            seg_scores = compute_segmentation_accuracy(df_conf)
            plot_mri_comparison_by_session(df_conf, fit_scores, save_dir=opt_dir)
        else:
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
                                                       fixed_globals=fixed_globals)

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
        'seg_scores': seg_scores,
        'opt_result': opt_result,
        'mri_pipeline': mri_pipeline,
        'seg_volume': seg_volume,
        'cortex_pca': cortex_pca_result,
    }


if __name__ == "__main__":
    conn = Connection(
        database="allen_data_repository",
        user="xper_rw",
        password="up2nite",
        host="172.30.6.61",
    )

    exclude_sessions = ["260331_0", "260402_0", "260520_0", "260423_0"]

    start_from_file = "/home/connorlab/git/EStimShape/EStimShapeAnalysis/src/mri/opt_20260525_121133_best.json"
    results = run_analysis(
        conn,
        n_pcs=2,
        exclude_sessions=exclude_sessions,
        within_session_normalize=False,
        tissue_model=MODEL_PCA_V2,
        varimax_n_components=2,
        maxiter=100000,
        start_from_file=start_from_file,
        enable_per_session_corrections=True,
        session_corr_bounds=None,
        session_corr_penalty=0.5,
        chamber_dist_penalty=0.000,
        chamber_param_penalty=0.0005,
        chamber_param_tolerances=dict(t_mm=4, r_deg=2.5, daz_deg=0.5, del_deg=0.5, ddepth_mm=4.0),
        variance_penalty=0.0,
        softmin_beta=0,
        optimizer='cma-es',
        use_confidence_weights=False,
        top_downweight_mm=0,
        top_downweight_factor=0.25,
        # optimize_target='segmentation',
        # segmentation_path="/home/connorlab/Documents/MRI/45X_MRI/45X_110315_4_1_corrected_warper_native/rigid_aligned/NMT_v2.0_asym_segmentation_rigid_aligned.nii.gz",
    )
