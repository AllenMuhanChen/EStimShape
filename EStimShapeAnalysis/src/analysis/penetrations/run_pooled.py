"""Master script: pooled-decomposition tissue-prediction pipelines + MRI scoring.

The unit of configuration is `TissuePipeline` (in pca_predict.py). One
pipeline owns: decomp_method, n_components, varimax, normalisation,
feature exclusion, AND the TissueModel. Same object plugs into
run_per_session.run_analysis for full optimisation.

Two entry points:

  - visualize_pooled_pca(conn, pipeline, ...)
        Fit one pipeline's decomposition and dump diagnostic plots
        (scree, loadings, depth profiles). Optional corrections_path
        adds an MRI panel to the per-session plot. Use this when
        iterating on PC count / method / model.

  - compare_pipelines_on_corrections(conn, corrections_path, pipelines, ...)
        Run multiple pipelines side-by-side: each fits its own
        decomposition, samples MRI under a fixed corrections file,
        and scores tissue_score vs MRI. Each pipeline's diagnostic
        plots land in its own subdir; a single comparison figure
        and CSV summarise the result.

To iterate on a new pipeline:
  1. Define a TissuePipeline inline in __main__ (see PIPELINES below).
  2. Run visualize_pooled_pca on it to see loadings / depth profiles.
  3. Refine the TissueModel based on what you see.
  4. Add it to PIPELINES and run compare_pipelines_on_corrections to
     score it against alternatives.
  5. To run full optimisation: pass the same pipeline object to
     run_per_session.run_analysis(conn, pipeline=PIPE_X, ...).
"""
import os
from typing import List, Optional

import pandas as pd

from clat.util.connection import Connection

from src.analysis.penetrations.pca_predict import (
    Evidence,
    MODEL_PCA_V1,
    MODEL_PCA_V2,
    MODEL_PCA_V4,
    MODEL_AA_K5,
    MODEL_AA_K6,
    CompositionalTissueModel,
    TissueClass,
    TissueModel,
    TissuePipeline,
    get_feature_correlations,
    get_loadings_df,
    print_feature_correlations, MODEL_PCA_V5, MODEL_PCA_V6, MODEL_AA_K3, MODEL_AA_K4,
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


EXCUDE_REL_LFP = [
    "band_power_delta_theta", "band_power_alpha_beta", "band_power_gamma",
]
MODEL_PCA_EXCL_REL_LFP = TissueModel([
    TissueClass('wm', score=1.0, evidence=[
        Evidence('PC1', sign=-1),
        Evidence('PC2', sign=+1),
    ]),
    TissueClass('gm', score=0.5, evidence=[
        Evidence('PC1', sign=+1),
        Evidence('PC2', sign=+1),
    ]),
    TissueClass('sulcus', score=0.0, evidence=[
        Evidence('PC2', sign=-1),
    ])
])

PIPE_PCA_exclude_rel_lfp = TissuePipeline(
    name='PCA_V2_excl_rel_lfp',
    model=MODEL_PCA_EXCL_REL_LFP,
    decomp_method='pca',
    n_components=2,
    use_varimax=False,
    within_session_normalize=False,
    pc_smooth_sigma=2.0,
    exclude_features=EXCUDE_REL_LFP,
)

# ---------------------------------------------------------------------------
# Archetypal-analysis pipelines with hand-assigned compositional tissue models.
# The decomposition recipe here MUST match the one the archetypes were labelled
# under in explore_decompositions (within_session_normalize=True,
# pc_smooth_sigma=2.0, no excluded features) — otherwise the archetype order
# shifts and MODEL_AA_K* map to the wrong prototypes.
# ---------------------------------------------------------------------------
PIPE_AA_K4 = TissuePipeline(
    name='AA_K4',
    model=MODEL_AA_K4,
    decomp_method='aa',
    n_components=4,
    use_varimax=False,
    within_session_normalize=True,
    pc_smooth_sigma=2.0,
    exclude_features=[],
)

PIPE_AA_K5 = TissuePipeline(
    name='AA_K5',
    model=MODEL_AA_K5,
    decomp_method='aa',
    n_components=5,
    use_varimax=False,
    within_session_normalize=True,
    pc_smooth_sigma=2.0,
    exclude_features=[],
)

PIPE_AA_K6 = TissuePipeline(
    name='AA_K6',
    model=MODEL_AA_K6,
    decomp_method='aa',
    n_components=6,
    use_varimax=False,
    within_session_normalize=True,
    pc_smooth_sigma=2.0,
    exclude_features=[],
)

PIPE_AA_K3 = TissuePipeline(
    name='AA_K3',
    model=MODEL_AA_K3,
    decomp_method='aa',
    n_components=3,
    use_varimax=False,
    within_session_normalize=True,
    pc_smooth_sigma=2.0,
    exclude_features=[],
)
# ---------------------------------------------------------------------------
# Shared helpers
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

    Picks up an 'mri_normalized' column automatically (per-session plot adds
    an MRI panel when present). Raw input features become extra per-session
    panels alongside the PCs.
    """
    print("\n" + "=" * 60)
    print("LOADINGS")
    print("=" * 60)
    loadings_df = get_loadings_df(pca, feature_columns)
    print(loadings_df.round(3))

    corr_df = get_feature_correlations(df, feature_columns, n_pcs=n_pcs)
    print_feature_correlations(corr_df)

    plot_scree(pca, save_dir=save_dir)
    plot_loadings(pca, feature_columns, n_pcs=n_pcs, save_dir=save_dir)
    plot_correlation_heatmap(corr_df, feature_columns, save_dir=save_dir)
    plot_depth_profiles_overlaid(df, pca, n_pcs=n_pcs, save_dir=save_dir)
    plot_depth_profiles_all_sessions(df, pca, n_pcs=n_pcs, save_dir=save_dir)
    if sessions_to_plot_individually:
        plot_depth_profiles_by_session(
            df, pca, n_pcs=n_pcs,
            sessions=sessions_to_plot_individually,
            feature_columns=feature_columns,
            save_dir=save_dir,
        )


# ---------------------------------------------------------------------------
# Step 1: visualise a single pipeline's decomposition
# ---------------------------------------------------------------------------

def visualize_pooled_pca(
        conn: Connection,
        pipeline: TissuePipeline,
        table_name: str = "PenetrationMetrics",
        exclude_sessions: Optional[list] = None,
        n_pcs_to_plot: Optional[int] = None,
        sessions_to_plot_individually: Optional[list] = None,
        corrections_path: Optional[str] = None,
        mri_config_path: str = MRI_VIEWER_CONFIG_PATH,
        save_dir: Optional[str] = None,
):
    """Fit one pipeline's decomposition and emit diagnostic plots.

    If corrections_path is given, also sample MRI under that corrections
    file so the per-session plot includes an MRI panel. No optimisation
    is performed — corrections are applied as-is, which is what you want
    for "look before designing a model" iteration.

    Returns (df, pca, X_pca, feature_columns, scaler).
    """
    if save_dir is None:
        save_dir = os.path.join(PLOT_BASE_DIR, 'pca_viz',
                                f"{pipeline.name}_{pipeline.tag()}")
    os.makedirs(save_dir, exist_ok=True)
    print(f"\nDecomposition visualisation output → {save_dir}")
    print(f"  Pipeline: {pipeline.name}  ({pipeline.tag()})")

    df, pca, X_pca, feature_columns, scaler = pipeline.fit_decomposition(
        conn, table_name, exclude_sessions,
    )

    if pipeline.model is not None:
        df = pipeline.predict(df)

    if corrections_path is not None:
        df, _ = _load_and_sample_mri(conn, df, corrections_path, mri_config_path)

    if n_pcs_to_plot is None:
        n_pcs_to_plot = max(
            pipeline.varimax_n_components or pipeline.n_components or X_pca.shape[1],
            1,
        )
    n_pcs_to_plot = min(n_pcs_to_plot, X_pca.shape[1])

    _generate_pca_diagnostics(
        df, pca, feature_columns, n_pcs_to_plot, save_dir,
        sessions_to_plot_individually=sessions_to_plot_individually,
    )

    return df, pca, X_pca, feature_columns, scaler


# ---------------------------------------------------------------------------
# Step 2: side-by-side pipeline comparison
# ---------------------------------------------------------------------------

def compare_pipelines_on_corrections(
        conn: Connection,
        corrections_path: str,
        pipelines: List[TissuePipeline],
        table_name: str = "PenetrationMetrics",
        mri_config_path: str = MRI_VIEWER_CONFIG_PATH,
        exclude_sessions: Optional[list] = None,
        save_dir: Optional[str] = None,
        plot_pca_diagnostics: bool = True,
        n_pcs_to_plot: Optional[int] = None,
        sessions_to_plot_individually: Optional[list] = None,
) -> dict:
    """Run multiple TissuePipelines side-by-side against the same MRI samples.

    Each pipeline fits its OWN decomposition (so you can compare PCA vs ICA
    vs FA with different component counts in one call), then is scored
    against MRI sampled under the fixed corrections_path.

    Each pipeline's per-decomposition diagnostic plots land in
    save_dir/pipeline_<name>/; the side-by-side comparison figure and
    CSV summary land at save_dir/.

    Every pipeline must have model != None.

    Returns a dict with keys:
        pipeline_results : {name: {df, fit_scores, pca, X_pca, feature_columns,
                                   save_dir}}
        summary          : DataFrame indexed by pipeline name with per-session r
                           and aggregated means / median / min.
        save_dir         : top-level output directory.
        mri_pipeline     : corrected pipeline (shared across pipelines).
    """
    if not pipelines:
        raise ValueError("No pipelines supplied.")
    missing_models = [p.name for p in pipelines if p.model is None]
    if missing_models:
        raise ValueError(
            f"Pipelines without a TissueModel cannot be compared against MRI: "
            f"{missing_models}. Set .model on each pipeline."
        )
    names = [p.name for p in pipelines]
    if len(set(names)) != len(names):
        raise ValueError(f"Duplicate pipeline names: {names}")

    if save_dir is None:
        corrections_tag = os.path.splitext(os.path.basename(corrections_path))[0]
        run_tag = corrections_tag + "_" + "_".join(p.name for p in pipelines)
        save_dir = os.path.join(PLOT_BASE_DIR, 'pipeline_comparison', run_tag)
    os.makedirs(save_dir, exist_ok=True)
    print(f"\nPipeline comparison output → {save_dir}")
    print(f"  Pipelines: {[p.name for p in pipelines]}")

    # Load MRI pipeline + corrections ONCE — independent of pipelines.
    print("\nLoading MRI pipeline (shared across pipelines) ...")
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

    pipeline_results: dict = {}
    summary_rows = []

    for pipe in pipelines:
        print(f"\n══════════════════════════════════════════════════════")
        print(f"  Pipeline: {pipe.name}  ({pipe.tag()})")
        print(f"══════════════════════════════════════════════════════")

        pipe_dir = os.path.join(save_dir, f"pipeline_{pipe.name}")
        os.makedirs(pipe_dir, exist_ok=True)

        # 1. Pipeline's own decomposition.
        df_decomp, pca, X_pca, feature_columns, scaler = pipe.fit_decomposition(
            conn, table_name, exclude_sessions,
        )

        # 2. Sample MRI on this pipeline's df (same corrections, same trajectories).
        df_with_mri = compute_mri_comparison(
            df_decomp, conn, opt_pipeline,
            daz=daz, del_=del_, ddepth=ddepth,
            per_session_corrections=per_session,
        )

        # 3. Apply the tissue model.
        df_pred = pipe.predict(df_with_mri)

        # 4. Diagnostic plots (per-pipeline subdir).
        if plot_pca_diagnostics:
            n_pcs = n_pcs_to_plot
            if n_pcs is None:
                n_pcs = max(pipe.varimax_n_components or pipe.n_components
                            or X_pca.shape[1], 1)
            n_pcs = min(n_pcs, X_pca.shape[1])
            _generate_pca_diagnostics(
                df_pred, pca, feature_columns, n_pcs, pipe_dir,
                sessions_to_plot_individually=sessions_to_plot_individually,
            )

        # 5. Score against MRI.
        fit_scores = compute_trajectory_fit_scores(df_pred)

        pipeline_results[pipe.name] = {
            'df': df_pred,
            'fit_scores': fit_scores,
            'pca': pca,
            'X_pca': X_pca,
            'feature_columns': feature_columns,
            'save_dir': pipe_dir,
        }

        row = {'pipeline': pipe.name}
        for sid, fs in fit_scores.iterrows():
            row[f'r_{sid}'] = fs['fit_score']
        row['r_mean']   = fit_scores['fit_score'].mean()
        row['r_median'] = fit_scores['fit_score'].median()
        row['r_min']    = fit_scores['fit_score'].min()
        summary_rows.append(row)

    summary = pd.DataFrame(summary_rows).set_index('pipeline')
    print("\n=== Pipeline comparison summary ===")
    print(summary.round(4).to_string())

    # Side-by-side per-session comparison figure (top-level save_dir).
    plot_predictor_comparison_by_session(pipeline_results, save_dir=save_dir)

    summary_path = os.path.join(save_dir, 'pipeline_comparison_summary.csv')
    summary.to_csv(summary_path)
    print(f"\n  Summary CSV → {summary_path}")

    return {
        'pipeline_results': pipeline_results,
        'summary': summary,
        'save_dir': save_dir,
        'mri_pipeline': opt_pipeline,
    }


# ---------------------------------------------------------------------------
# Backwards-compat: legacy compare_predictors_on_corrections
# ---------------------------------------------------------------------------
# The old API took shared decomp args + a list of TissueModelPredictor. It's
# kept as a shim that builds one TissuePipeline per predictor with shared
# decomp settings and dispatches to compare_pipelines_on_corrections.

def compare_predictors_on_corrections(
        conn: Connection,
        corrections_path: str,
        predictors,
        table_name: str = "PenetrationMetrics",
        mri_config_path: str = MRI_VIEWER_CONFIG_PATH,
        exclude_sessions: Optional[list] = None,
        within_session_normalize: bool = False,
        pc_smooth_sigma: float = 2.0,
        n_components: Optional[int] = None,
        varimax_n_components: Optional[int] = None,
        decomp_method: str = 'pca',
        use_varimax: bool = True,
        exclude_features: Optional[list] = None,
        save_dir: Optional[str] = None,
        plot_pca_diagnostics: bool = True,
        n_pcs_to_plot: Optional[int] = None,
        sessions_to_plot_individually: Optional[list] = None,
) -> dict:
    """Legacy shim — builds a TissuePipeline per predictor using the shared
    decomp settings, then calls compare_pipelines_on_corrections."""
    pipelines = [
        TissuePipeline(
            name=p.name,
            model=p.model,
            decomp_method=decomp_method,
            n_components=n_components,
            varimax_n_components=varimax_n_components,
            use_varimax=use_varimax,
            within_session_normalize=within_session_normalize,
            pc_smooth_sigma=pc_smooth_sigma,
            exclude_features=list(exclude_features or []),
        )
        for p in predictors
    ]
    return compare_pipelines_on_corrections(
        conn,
        corrections_path=corrections_path,
        pipelines=pipelines,
        table_name=table_name,
        mri_config_path=mri_config_path,
        exclude_sessions=exclude_sessions,
        save_dir=save_dir,
        plot_pca_diagnostics=plot_pca_diagnostics,
        n_pcs_to_plot=n_pcs_to_plot,
        sessions_to_plot_individually=sessions_to_plot_individually,
    )
PIPE_PCA_V4 = TissuePipeline(
    name='PCA_V4',
    model=MODEL_PCA_V4,
    decomp_method='pca',
    n_components=4,
    use_varimax=False,
    within_session_normalize=False,
    pc_smooth_sigma=2.0,
)
PIPE_PCA_new = TissuePipeline(
    name='PCA_V5',
    model=MODEL_PCA_V5,
    decomp_method='pca',
    n_components=4,
    use_varimax=False,
    within_session_normalize=False,
    pc_smooth_sigma=2.0,
)

PIPE_PCA_V6 = TissuePipeline(
    name='PCA_V6',
    model=MODEL_PCA_V6,
    decomp_method='pca',
    n_components=2,
    use_varimax=False,
    within_session_normalize=False,
    pc_smooth_sigma=1.5
)

PIPE_PCA_V7 = TissuePipeline(
    name='PCA_V6',
    model=MODEL_PCA_V6,
    decomp_method='pca',
    n_components=4,
    use_varimax=False,
    within_session_normalize=False,
    pc_smooth_sigma=1.5
)
# ---------------------------------------------------------------------------
# __main__
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # ════════════════════════════════════════════════════════════════════
    # CONFIGURATION
    # ════════════════════════════════════════════════════════════════════
    EXCLUDE_SESSIONS = ["260331_0", "260402_0", "260520_0", "260423_0"]

    SESSIONS_TO_PLOT_INDIVIDUALLY: list = ["260609_0", "260605_0"]

    CORRECTIONS_PATH = (
        "/home/connorlab/git/EStimShape/EStimShapeAnalysis/src/mri/"
        "opt_20260602_170728_best.json"
    )


    # ════════════════════════════════════════════════════════════════════
    # TISSUE MODELS — define inline; promote stable ones to pca_predict.py.
    # ════════════════════════════════════════════════════════════════════

    MODEL_ICA_V1 = TissueModel([
        TissueClass('wm', score=1.0, evidence=[
            Evidence('PC1', sign=+1),
            Evidence('PC2', sign=+1),
        ]),
        TissueClass('gm', score=0.5, evidence=[
            Evidence('PC1', sign=-1),
            Evidence('PC2', sign=+1),
        ]),
        TissueClass('sulcus', score=0.0, evidence=[
            Evidence('PC2', sign=-1),
        ]),
    ])


    # ════════════════════════════════════════════════════════════════════
    # PIPELINES — each owns its own decomp recipe + tissue model. Drop one
    # of these into run_per_session.run_analysis(pipeline=...) to optimise.
    # ════════════════════════════════════════════════════════════════════

    PIPE_PCA = TissuePipeline(
        name='PCA_V2',
        model=MODEL_PCA_V2,
        decomp_method='pca',
        n_components=2,
        use_varimax=False,
        within_session_normalize=False,
        pc_smooth_sigma=1.0,
    )



    PIPE_PCA_exclude_rel_lfp = TissuePipeline(
        name='PCA_V2_excl_rel_lfp',
        model=MODEL_PCA_EXCL_REL_LFP,
        decomp_method='pca',
        n_components=2,
        use_varimax=False,
        within_session_normalize=False,
        pc_smooth_sigma=2.0,
        exclude_features=EXCUDE_REL_LFP,
    )

    PIPE_ICA_V1 = TissuePipeline(
        name='ICA_V1',
        model=MODEL_ICA_V1,
        decomp_method='ica',
        n_components=2,
        use_varimax=False,
        within_session_normalize=False,
        pc_smooth_sigma=2.0,
        exclude_features=EXCUDE_REL_LFP,
    )

    PIPELINES: List[TissuePipeline] = [
        PIPE_PCA_V4,
        PIPE_PCA_new
    ]

    conn = Connection(
        database="allen_data_repository",
        user="xper_rw",
        password="up2nite",
        host="172.30.6.61",
    )

    # ════════════════════════════════════════════════════════════════════
    # WORKFLOW
    # ════════════════════════════════════════════════════════════════════
    # Step 1 (optional): visualise a single pipeline's decomposition.
    # Use this when designing a new TissueModel — fits decomp, dumps
    # loadings / depth profiles, optionally adds an MRI panel.
    #
    visualize_pooled_pca(
        conn,
        pipeline=PIPE_PCA_V7,
        exclude_sessions=EXCLUDE_SESSIONS,
        sessions_to_plot_individually=SESSIONS_TO_PLOT_INDIVIDUALLY,
        corrections_path=CORRECTIONS_PATH,   # optional → adds MRI panel
    )

    # # Step 2: compare every pipeline in PIPELINES side-by-side against MRI.
    # # Each pipeline fits its OWN decomposition; per-pipeline diagnostic
    # # plots land in <save_dir>/pipeline_<name>/.
    # results = compare_pipelines_on_corrections(
    #     conn,
    #     corrections_path=CORRECTIONS_PATH,
    #     pipelines=PIPELINES,
    #     exclude_sessions=EXCLUDE_SESSIONS,
    #     plot_pca_diagnostics=True,
    #     sessions_to_plot_individually=SESSIONS_TO_PLOT_INDIVIDUALLY,
    # )
