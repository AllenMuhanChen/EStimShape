from __future__ import annotations

import dataclasses
import json
import os
from dataclasses import dataclass
from typing import Any, Callable, Optional, Union

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from PIL import Image
from scipy.optimize import curve_fit
from scipy.stats import spearmanr, theilslopes

from clat.pipeline.pipeline_base_classes import (
    InputHandler,
    ComputationModule,
    AnalysisModuleFactory,
)
from clat.util.dictionary_util import apply_function_to_subdictionaries_values_with_keys

from src.analysis.ga.axis_coding.axis_coding_dataset import (
    AxisCodingDataset,
    _extract_per_trial_response,
    remove_trial_outliers,
)
from src.analysis.ga.axis_coding.appearance_features import AppearanceFeatures
from src.analysis.ga.axis_coding.axis_models import (
    BuildResult,
    FitContext,
    ModelAxisFit,
    ModelSpec,
    appearance_model,
    default_axis_models,
    shape_model,
    shape_plus_appearance_model,
)
from src.analysis.ga.axis_coding.component_encoding import (
    ComponentEncoder,
    PCAPreprocessor,
    make_default_encoders,
)
from src.analysis.ga.axis_coding.component_selectors import (
    ComponentSelector,
    FixedCovarianceSelector,
    LearnedDiagonalCovarianceSelector,
    ClusterModeSelector,
    SoftAttentionAxisSelector,
    MultiPrototypeAttentionSelector,
    RWAPeakSelector,
)
from src.analysis.ga.axis_coding.ridge_regression_model import (
    RidgeRegressionAxisModel,
)
from src.analysis.ga.plot_top_n import PlotTopNAnalysis
from src.analysis.ga.receptive_field_filter import ReceptiveFieldFilter
from src.analysis.modules.figure_output import FigureSaverOutput
from src.analysis.modules.matplotlib.grouped_stims_by_response_matplotlib import (
    GroupedStimuliPlotter_matplotlib,
)
from src.pga.mock.mock_rwa_analysis import (
    condition_spherical_angles,
    hemisphericalize_orientation,
)
from src.repository.export_to_repository import read_session_id_and_date_from_db_name
from src.startup import context

# ---------------------------------------------------------------------------
# Strategy spec (selector factory + label) used by both direct and pipeline runs
# ---------------------------------------------------------------------------

SelectorFactory = Callable[[], ComponentSelector]
RidgeFactory = Callable[[], RidgeRegressionAxisModel]


@dataclass
class AxisCodingStrategy:
    """A named selector + ridge strategy.

    Both factories are called fresh per (channel, component_type) so each fit
    gets its own learned mu and alpha without cross-contamination.
    ``ridge_factory=None`` uses ``RidgeRegressionAxisModel()`` defaults.
    ``n_pcs=None`` skips PCA; ``n_pcs=k`` projects to the top-k PCs of the
    z-scored component matrix before running the selector and ridge.
    """

    label: str
    selector_factory: SelectorFactory
    ridge_factory: Optional[RidgeFactory] = None
    n_pcs: Optional[int] = None


def default_strategy() -> AxisCodingStrategy:
    return AxisCodingStrategy(
        label="fixed_cov_identity",
        selector_factory=lambda: FixedCovarianceSelector(),
    )


# ---------------------------------------------------------------------------
# Per-(strategy, type) result record
# ---------------------------------------------------------------------------

@dataclass
class AxisCodingResult:
    channel: Union[str, list[str]]
    component_type: str
    strategy_label: str
    n_stim: int
    n_features: int
    n_dropped_no_components: int
    n_dropped_no_response: int
    selector_summary: dict
    ridge_summary: dict
    selected_indices: list[int]
    stim_ids: list
    feature_names: list[str]
    actual_responses: list[float]
    predicted_responses: list[float]
    axis_projections: Optional[list[float]] = None
    orthogonal_projections: Optional[list[float]] = None
    orthogonal_axis: Optional[list[float]] = None
    all_orthogonal_axes: Optional[list[list[float]]] = None         # (d, n_orth)
    all_orthogonal_variances: Optional[list[float]] = None          # (n_orth,)
    all_orthogonal_projections: Optional[list[list[float]]] = None  # (n_stim, n_orth)
    noise_ceiling: Optional[float] = None
    # PCA back-projections (set when n_pcs was used; None otherwise)
    w_in_feature_space: Optional[list[float]] = None                # (d,) back-projected preferred axis
    orthogonal_axis_in_feature_space: Optional[list[float]] = None  # (d,) back-projected orth axis
    all_orthogonal_axes_in_feature_space: Optional[list[list[float]]] = None  # (d, n_orth)
    pca_explained_variance: Optional[list[float]] = None            # (k,) per-PC variance ratio
    # μ ("chosen mean") in three spaces, when the selector exposes one:
    #   mu_in_selector_space:    raw selector μ (PC space if PCA active, else feat)
    #   mu_in_feature_space:     z-scored, original-feature space (post back-projection)
    #   mu_in_unscaled_space:    raw feature units (post inverse_scale)
    #   mu_decoded:              interpretable params (linear, atan2 angles, sphere)
    # Same fields prefixed with ``mus_*`` carry every prototype for multi-prototype selectors.
    mu_in_selector_space: Optional[list[float]] = None
    mu_in_feature_space_zscored: Optional[list[float]] = None
    mu_in_unscaled_space: Optional[list[float]] = None
    mu_decoded: Optional[dict] = None
    mus_in_unscaled_space: Optional[list[list[float]]] = None
    mus_decoded: Optional[list[dict]] = None
    prototype_amplitudes: Optional[list[float]] = None
    # Thumbnail paths aligned with stim_ids (for axis-stimulus visualization)
    thumbnail_paths: Optional[list[Optional[str]]] = None

    # ---- Appearance comparison (texture + average RGB) ---------------------
    # All aligned with stim_ids. ``texture_per_stim`` holds the raw label per
    # stim; one-hot expansion lives in ``appearance_features``.
    appearance_features: Optional[list[list[float]]] = None
    appearance_feature_names: Optional[list[str]] = None
    texture_per_stim: Optional[list[Optional[str]]] = None
    # Ridge-comparison metrics, all using the same factory / CV folds as the
    # shape model. ``cv_r2`` here always refers to the held-out R² mean.
    appearance_only_summary: Optional[dict] = None        # ridge.summary() on appearance alone
    appearance_only_predictions: Optional[list[float]] = None
    joint_summary: Optional[dict] = None                  # ridge.summary() on [shape | appearance]
    joint_predictions: Optional[list[float]] = None
    joint_appearance_weights: Optional[list[float]] = None  # appearance-block weights from joint
    joint_shape_weights: Optional[list[float]] = None       # shape-block weights from joint
    residual_appearance_summary: Optional[dict] = None    # ridge on (actual - shape_pred)
    residual_appearance_predictions: Optional[list[float]] = None
    # Per-texture shape CV R² (how shape model behaves within each texture group).
    texture_stratified_cv_r2: Optional[dict[str, float]] = None
    texture_stratified_n: Optional[dict[str, int]] = None
    # Pluggable per-model axis fits. Each entry is a ModelAxisFit (see
    # axis_models.py). The shape model's fit also populates the flat
    # axis_projections/orthogonal_*/feature_names fields above for back-compat
    # with plot_axes_stimuli and any callers that read them directly.
    # Default models: shape, appearance, shape+appearance; users add more by
    # passing axis_models=[...] to AxisCodingAnalysis.
    model_fits: Optional[dict[str, dict]] = None  # dict[name, ModelAxisFit-as-dict]

    def to_json_dict(self) -> dict:
        d = self.__dict__.copy()
        # Channel may be a list -> already JSON-serializable.
        return d


# ---------------------------------------------------------------------------
# Noise ceiling
# ---------------------------------------------------------------------------

def compute_noise_ceiling(
    df: pd.DataFrame,
    channel: Union[str, list[str]],
    spike_rates_col: Optional[str],
    stim_ids=None,
    n_splits: int = 200,
    random_state: int = 0,
) -> Optional[float]:
    """
    Estimate the upper-bound R² achievable given trial-to-trial noise.

    For each stimulus with ≥2 trials, trials are randomly split in half and
    the Pearson r between the two half-means is Spearman-Brown corrected to
    full-N reliability, then squared to give a noise-ceiling R².  The result
    is averaged over ``n_splits`` random splits for stability.

    Returns None when no stimulus has ≥2 trials (e.g. single-trial sessions
    or when only GA Response is available as a pre-averaged scalar).
    """
    df = df.copy()
    df = df[df["StimSpecId"].notna()]
    df["_nc_resp"] = _extract_per_trial_response(df, channel, spike_rates_col)
    df = df[df["_nc_resp"].notna()]

    if stim_ids is not None:
        df = df[df["StimSpecId"].isin(stim_ids)]

    groups = {
        sid: grp["_nc_resp"].values
        for sid, grp in df.groupby("StimSpecId")
        if len(grp) >= 2
    }

    if len(groups) < 2:
        return None

    rng = np.random.default_rng(random_state)
    nc_values = []

    for _ in range(n_splits):
        h1, h2 = [], []
        for trials in groups.values():
            idx = rng.permutation(len(trials))
            mid = max(1, len(idx) // 2)
            h1.append(trials[idx[:mid]].mean())
            h2.append(trials[idx[mid:]].mean())

        h1, h2 = np.asarray(h1), np.asarray(h2)
        if h1.std() < 1e-12 or h2.std() < 1e-12:
            continue

        r = float(np.corrcoef(h1, h2)[0, 1])
        r = float(np.clip(r, 0.0, 1.0))   # negative = no signal; floor at 0
        r_sb = (2.0 * r) / (1.0 + r)      # Spearman-Brown to full-N reliability
        nc_values.append(r_sb ** 2)        # convert correlation → R²

    return float(np.mean(nc_values)) if nc_values else None


# ---------------------------------------------------------------------------
# Tsao Fig. 4A-style orthogonal-tuning summary
# ---------------------------------------------------------------------------

def _gauss_a_sigma_c(x: np.ndarray, a: float, sigma: float, c: float) -> np.ndarray:
    return a * np.exp(-(x ** 2) / (sigma ** 2)) + c


def compute_orthogonal_tuning_curve(
    design: np.ndarray,
    w: np.ndarray,
    responses: np.ndarray,
    n_draws: int = 2000,
    n_keep: int = 300,
    n_bins: int = 11,
    z_range: float = 1.0,
    fit_z_range: Optional[float] = None,
    rng: Optional[np.random.Generator] = None,
) -> dict:
    """
    Tsao et al. 2017 Fig 4A measure: average tuning along random axes
    orthogonal to the preferred axis ``w``, on a shared z-scored x-grid.

    Defaults match Tsao's display: ``z_range=1.0`` so bin centers span
    [-1, +1] z-units, which covers ~68% of stimuli for a roughly Gaussian
    projection distribution. Bins beyond that have too few stimuli per axis
    to be reliable. ``fit_z_range`` (defaults to ``z_range``) restricts the
    Gaussian fit to a possibly-narrower range.

    Procedure
    ---------
    1. Draw ``n_draws`` random unit vectors in design space.
    2. Orthogonalize each to ``w`` (Gram–Schmidt) and renormalize. Drop axes
       whose post-projection norm is too small (collinear with w).
    3. For each axis: project all stimuli onto it, z-score the projections,
       bin by ``n_bins`` evenly-spaced bin centers in [-z_range, +z_range],
       compute mean response per bin.
    4. Compute the variance of stimulus projections along each axis; keep
       the top ``n_keep`` highest-variance axes.
    5. Average those tuning curves bin-by-bin → ``mean``; SD across kept
       axes per bin → ``sd``.
    6. Fit ``a·exp(-x²/σ²) + c`` to ``mean`` (with reasonable bounds).

    Returns ``None`` if the design space has fewer than two dimensions.
    Otherwise returns a dict matching ModelAxisFit's orth_* fields plus
    the headline scalar ``orth_amplitude_norm = a / (a + c)``.
    """
    design = np.asarray(design, dtype=np.float64)
    w = np.asarray(w, dtype=np.float64)
    responses = np.asarray(responses, dtype=np.float64).ravel()

    n_stim, d = design.shape
    if d < 2 or n_stim < 5:
        return None

    rng = rng if rng is not None else np.random.default_rng(0)
    w_norm = float(np.linalg.norm(w))
    if w_norm < 1e-12:
        return None
    w_unit = w / w_norm

    # Draw random axes, orthogonalize to w_unit, renormalize, drop tiny-norm.
    raw = rng.standard_normal((n_draws, d))
    proj = raw @ w_unit                   # (n_draws,)
    raw = raw - np.outer(proj, w_unit)    # subtract w-component
    norms = np.linalg.norm(raw, axis=1, keepdims=True)
    keep_mask = norms.ravel() > 1e-9
    raw = raw[keep_mask]
    norms = norms[keep_mask]
    if raw.shape[0] == 0:
        return None
    axes = raw / norms                    # unit-norm rows

    # Project all stimuli onto every axis at once: (n_stim, d) @ (d, n_axes).
    projections = design @ axes.T          # (n_stim, n_axes)

    # Variance per axis; pick top-n_keep.
    variances = projections.var(axis=0, ddof=1)
    n_axes_drawn = projections.shape[1]
    top_k = min(n_keep, n_axes_drawn)
    if top_k < 1:
        return None
    top_idx = np.argpartition(-variances, top_k - 1)[:top_k]
    projections = projections[:, top_idx]
    n_axes_used = projections.shape[1]

    # Z-score per axis, then bin onto a shared grid in [-z_range, +z_range].
    proj_mean = projections.mean(axis=0, keepdims=True)
    proj_std = projections.std(axis=0, ddof=1, keepdims=True)
    proj_std = np.where(proj_std < 1e-12, 1.0, proj_std)
    z = (projections - proj_mean) / proj_std        # (n_stim, n_axes_used)

    edges = np.linspace(-z_range, z_range, n_bins + 1)
    centers = 0.5 * (edges[:-1] + edges[1:])

    # Bin index per stimulus per axis (-1 if outside range).
    bin_idx = np.digitize(z, edges) - 1              # values in [0, n_bins-1] or -1/n_bins
    valid = (bin_idx >= 0) & (bin_idx < n_bins)

    # Per-axis mean response per bin + bin count (for sanity / fit weights).
    per_axis_mean = np.full((n_axes_used, n_bins), np.nan)
    per_axis_count = np.zeros((n_axes_used, n_bins), dtype=np.int64)
    for k in range(n_axes_used):
        col_bin = bin_idx[:, k]
        col_valid = valid[:, k]
        if not col_valid.any():
            continue
        for b in range(n_bins):
            sel = col_valid & (col_bin == b)
            n_sel = int(sel.sum())
            per_axis_count[k, b] = n_sel
            if n_sel > 0:
                per_axis_mean[k, b] = responses[sel].mean()

    # Average across axes (NaN-aware) + average per-axis bin count.
    with np.errstate(invalid="ignore"):
        mean_curve = np.nanmean(per_axis_mean, axis=0)
        sd_curve = np.nanstd(per_axis_mean, axis=0, ddof=1)
    mean_count_per_bin = per_axis_count.mean(axis=0)

    # Per-axis modulation depth = (max - min) / |max| over the in-fit-range bins.
    # Cheap proxy for a/(a+c) without fitting a Gaussian per axis. Used to
    # surface any single bumpy axis the average might be hiding.
    fit_lim_for_mod = float(fit_z_range) if fit_z_range is not None else float(z_range)
    in_fit_mask = np.abs(centers) <= fit_lim_for_mod + 1e-9
    per_axis_in_fit = per_axis_mean[:, in_fit_mask]
    per_axis_mod = np.full(per_axis_mean.shape[0], np.nan)
    for k in range(per_axis_mean.shape[0]):
        row = per_axis_in_fit[k]
        finite_row = row[np.isfinite(row)]
        if finite_row.size < 2:
            continue
        mx = float(finite_row.max())
        mn = float(finite_row.min())
        if abs(mx) > 1e-12:
            per_axis_mod[k] = (mx - mn) / abs(mx)

    # Gaussian fit on bins inside fit_z_range where mean_curve is finite.
    fit_lim = float(fit_z_range) if fit_z_range is not None else float(z_range)
    fit_mask = np.isfinite(mean_curve) & (np.abs(centers) <= fit_lim + 1e-9)
    fit_ok = False
    a = sigma = c = float("nan")
    if fit_mask.sum() >= 4:
        x_fit = centers[fit_mask]
        y_fit = mean_curve[fit_mask]
        y_min, y_max = float(y_fit.min()), float(y_fit.max())
        y_range = max(y_max - y_min, 1e-9)
        # Heuristic init: a = y[center_bin] - mean(edges), c = mean(edges), σ = 1.
        center_bin = np.argmin(np.abs(x_fit))
        edge_mask = (np.abs(x_fit) >= z_range * 0.7)
        c_init = float(y_fit[edge_mask].mean()) if edge_mask.any() else float(y_fit.mean())
        a_init = float(y_fit[center_bin] - c_init)
        try:
            popt, _ = curve_fit(
                _gauss_a_sigma_c, x_fit, y_fit,
                p0=[a_init, 1.0, c_init],
                bounds=(
                    [-5.0 * y_range, 1e-3, y_min - 5.0 * y_range],
                    [ 5.0 * y_range, 10.0, y_max + 5.0 * y_range],
                ),
                maxfev=5000,
            )
            a, sigma, c = float(popt[0]), float(popt[1]), float(popt[2])
            fit_ok = True
        except Exception:
            fit_ok = False

    if fit_ok and abs(a + c) > 1e-9:
        amp_norm = float(a / (a + c))
    else:
        amp_norm = float("nan")

    return {
        "orth_tuning_x": centers.tolist(),
        "orth_tuning_mean": mean_curve.tolist(),
        "orth_tuning_sd": sd_curve.tolist(),
        "orth_tuning_count": mean_count_per_bin.tolist(),
        "orth_tuning_per_axis": per_axis_mean.tolist(),
        "orth_tuning_per_axis_modulation": per_axis_mod.tolist(),
        "orth_tuning_z_range": float(z_range),
        "orth_tuning_fit_z_range": fit_lim,
        "orth_tuning_n_axes_drawn": int(n_axes_drawn),
        "orth_tuning_n_axes_used": int(n_axes_used),
        "orth_gauss_a": a if fit_ok else float("nan"),
        "orth_gauss_sigma": sigma if fit_ok else float("nan"),
        "orth_gauss_c": c if fit_ok else float("nan"),
        "orth_amplitude_norm": amp_norm,
        "orth_gauss_fit_ok": bool(fit_ok),
    }


# ---------------------------------------------------------------------------
# Per-model axis fitting (ridge → preferred axis → orth basis → back-project)
# ---------------------------------------------------------------------------

def _fit_model_axes(
    spec: ModelSpec,
    ctx: FitContext,
    ridge_factory: Optional[RidgeFactory],
) -> ModelAxisFit:
    """
    Run the axis-coding pipeline on one model: build design → fit ridge → take
    the ridge weight as the preferred axis → compute the orthonormal basis on
    the orthogonal subspace → back-project the axis loadings to interpretable
    feature space (when the spec provides a back-projection).

    Same recipe regardless of model, so adding a new ``ModelSpec`` doesn't
    require any new code outside its builder.
    """
    br: BuildResult = spec.builder(ctx)
    design = np.asarray(br.design, dtype=np.float64)

    ridge = ridge_factory() if ridge_factory is not None else RidgeRegressionAxisModel()
    ridge.fit(design, ctx.responses, feature_names=br.feature_names_model)
    predictions = ridge.predict(design)
    w = ridge.w_

    axis_proj = _project_onto_unit(design, w)
    all_orth_axes, all_orth_vars = compute_all_orthogonal_axes(design, w)
    if all_orth_axes.shape[1] > 0:
        orth_axis = all_orth_axes[:, 0]
        all_orth_proj = design @ all_orth_axes
        orth_proj = all_orth_proj[:, 0]
    else:
        orth_axis = np.zeros_like(w)
        all_orth_proj = np.zeros((design.shape[0], 0))
        orth_proj = np.zeros(design.shape[0])

    w_in_feat: Optional[np.ndarray] = None
    orth_axis_in_feat: Optional[np.ndarray] = None
    all_orth_axes_in_feat: Optional[np.ndarray] = None
    if br.back_project is not None:
        w_in_feat = br.back_project(w)
        if np.linalg.norm(orth_axis) > 1e-12:
            orth_axis_in_feat = br.back_project(orth_axis)
        else:
            orth_axis_in_feat = np.zeros(len(br.feature_names_interp))
        if all_orth_axes.shape[1] > 0:
            all_orth_axes_in_feat = np.column_stack([
                br.back_project(all_orth_axes[:, j])
                for j in range(all_orth_axes.shape[1])
            ])
        else:
            all_orth_axes_in_feat = np.zeros((len(br.feature_names_interp), 0))

    # Tsao Fig 4A orthogonal-tuning summary (per model). Fixed seed so the
    # number is reproducible across reruns; a per-fit randomness would
    # complicate population pooling.
    orth_tune = compute_orthogonal_tuning_curve(
        design=design, w=w, responses=ctx.responses,
        rng=np.random.default_rng(0),
    ) or {}

    return ModelAxisFit(
        name=spec.name,
        feature_names_model=list(br.feature_names_model),
        feature_names_interp=list(br.feature_names_interp),
        has_shape_mu=spec.has_shape_mu,
        ridge_summary=ridge.summary(),
        predictions=predictions.tolist(),
        orth_tuning_x=orth_tune.get("orth_tuning_x"),
        orth_tuning_mean=orth_tune.get("orth_tuning_mean"),
        orth_tuning_sd=orth_tune.get("orth_tuning_sd"),
        orth_tuning_count=orth_tune.get("orth_tuning_count"),
        orth_tuning_per_axis=orth_tune.get("orth_tuning_per_axis"),
        orth_tuning_per_axis_modulation=orth_tune.get("orth_tuning_per_axis_modulation"),
        orth_tuning_z_range=orth_tune.get("orth_tuning_z_range"),
        orth_tuning_fit_z_range=orth_tune.get("orth_tuning_fit_z_range"),
        orth_tuning_n_axes_drawn=orth_tune.get("orth_tuning_n_axes_drawn"),
        orth_tuning_n_axes_used=orth_tune.get("orth_tuning_n_axes_used"),
        orth_gauss_a=orth_tune.get("orth_gauss_a"),
        orth_gauss_sigma=orth_tune.get("orth_gauss_sigma"),
        orth_gauss_c=orth_tune.get("orth_gauss_c"),
        orth_amplitude_norm=orth_tune.get("orth_amplitude_norm"),
        orth_gauss_fit_ok=bool(orth_tune.get("orth_gauss_fit_ok", False)),
        axis_projections=axis_proj.tolist(),
        orth_projections=orth_proj.tolist(),
        all_orth_projections=all_orth_proj.tolist(),
        orth_axis=orth_axis.tolist(),
        all_orth_axes=all_orth_axes.tolist(),
        all_orth_variances=all_orth_vars.tolist(),
        w_in_feature_space=w_in_feat.tolist() if w_in_feat is not None else None,
        orth_axis_in_feature_space=(
            orth_axis_in_feat.tolist() if orth_axis_in_feat is not None else None
        ),
        all_orth_axes_in_feature_space=(
            all_orth_axes_in_feat.tolist() if all_orth_axes_in_feat is not None else None
        ),
    )


# ---------------------------------------------------------------------------
# Core fit routine -- usable from pipeline or direct call
# ---------------------------------------------------------------------------

def fit_axis_coding(
    df: pd.DataFrame,
    component_type: str,
    encoder: ComponentEncoder,
    selector: ComponentSelector,
    channel: Union[str, list[str]],
    spike_rates_col: Optional[str],
    strategy_label: str,
    save_dir: Optional[str] = None,
    ridge_factory: Optional[RidgeFactory] = None,
    n_pcs: Optional[int] = None,
    axis_models: Optional[list[ModelSpec]] = None,
) -> AxisCodingResult:
    dataset = AxisCodingDataset.build(
        df=df,
        component_type=component_type,
        encoder=encoder,
        channel=channel,
        spike_rates_col=spike_rates_col,
    )

    # Optional PCA: fit on all encoded (z-scored) component vectors, then
    # transform each stimulus's component matrix from (m_i, d) to (m_i, k).
    pca_pre: Optional[PCAPreprocessor] = None
    if n_pcs is not None and n_pcs > 0:
        pca_pre = PCAPreprocessor(n_components=n_pcs)
        components_for_selector = pca_pre.fit_transform(dataset.components_per_stim)
        print(
            f"  [PCA] k={pca_pre.n_components_actual}  "
            f"cumulative var explained="
            f"{float(pca_pre.explained_variance_ratio.sum()):.1%}"
        )
    else:
        components_for_selector = dataset.components_per_stim

    # Feature names used by ridge (PC names when PCA is active).
    feature_names_for_model = (
        pca_pre.pc_feature_names() if pca_pre is not None else dataset.feature_names
    )

    # Selectors that need the encoder / PCA context (e.g. RWAPeakSelector
    # decoding a raw-space peak into selector space) declare a
    # ``set_encoding_context`` method. Other selectors don't have it and
    # are unaffected.
    if hasattr(selector, "set_encoding_context"):
        selector.set_encoding_context(
            encoder=encoder,
            pca_pre=pca_pre,
            component_type=component_type,
        )

    selector.fit(components_for_selector, dataset.responses)
    X = selector.selected_vectors(components_for_selector)

    pca_var: Optional[list[float]] = (
        pca_pre.explained_variance_ratio.tolist() if pca_pre is not None else None
    )

    # ------------------------------------------------------------------
    # Build appearance features early so model builders can use them.
    # Pluggable models (axis_models) each get a ModelAxisFit; the shape model
    # is the canonical "primary" and its fields are aliased to the flat
    # AxisCodingResult fields below for backward compatibility with callers
    # that don't know about model_fits yet.
    # ------------------------------------------------------------------
    appearance = AppearanceFeatures.build(df, dataset.stim_ids)
    A = appearance.features
    if appearance.n_missing_texture or appearance.n_missing_rgb:
        print(
            f"  [appearance] missing texture: {appearance.n_missing_texture}, "
            f"missing RGB: {appearance.n_missing_rgb} (of {appearance.n_stim})"
        )

    fit_ctx = FitContext(
        X_shape=X,
        A_appearance=A,
        shape_feature_names_model=list(feature_names_for_model),
        shape_feature_names_orig=list(dataset.feature_names),
        appearance_feature_names=list(appearance.feature_names),
        pca_pre=pca_pre,
        responses=dataset.responses,
    )

    models = list(axis_models) if axis_models is not None else default_axis_models()
    model_fits: dict[str, ModelAxisFit] = {}
    for spec in models:
        if spec.requires_appearance and A.shape[1] == 0:
            print(f"  [{spec.name}] skipped: requires appearance features")
            continue
        model_fits[spec.name] = _fit_model_axes(spec, fit_ctx, ridge_factory)
        ms = model_fits[spec.name].ridge_summary
        cv = ms.get("cv_r2_mean")
        cv_str = f"{cv:+.3f}" if cv is not None and not (isinstance(cv, float) and np.isnan(cv)) else "n/a"
        print(f"  [model:{spec.name}] cv_r2={cv_str}  d={len(ms.get('feature_names') or [])}")

    # Pull shape-model artifacts back out as locals for the rest of the
    # function (residual fit, μ decoding, result construction) — these still
    # operate on the shape model specifically.
    if "shape" not in model_fits:
        raise RuntimeError(
            "axis_models must include a 'shape' model; got: "
            f"{[s.name for s in models]}"
        )
    shape_fit = model_fits["shape"]
    predicted = np.asarray(shape_fit.predictions, dtype=np.float64)
    axis_projections = np.asarray(shape_fit.axis_projections, dtype=np.float64)
    orth_projections = np.asarray(shape_fit.orth_projections, dtype=np.float64)
    all_orth_projections = np.asarray(shape_fit.all_orth_projections, dtype=np.float64)
    orth_axis = np.asarray(shape_fit.orth_axis, dtype=np.float64)
    all_orth_axes = np.asarray(shape_fit.all_orth_axes, dtype=np.float64)
    all_orth_variances = np.asarray(shape_fit.all_orth_variances, dtype=np.float64)
    w_feat = (
        np.asarray(shape_fit.w_in_feature_space, dtype=np.float64)
        if shape_fit.w_in_feature_space is not None else None
    )
    orth_axis_feat = (
        np.asarray(shape_fit.orth_axis_in_feature_space, dtype=np.float64)
        if shape_fit.orth_axis_in_feature_space is not None else None
    )
    all_orth_axes_feat = (
        np.asarray(shape_fit.all_orth_axes_in_feature_space, dtype=np.float64)
        if shape_fit.all_orth_axes_in_feature_space is not None else None
    )

    # Decode μ into interpretable parameter space.
    # μ lives in selector-space: PC space if PCA was used, feature (z-scored) otherwise.
    # We back-project to z-scored features, inverse-scale to raw feature units, then
    # decode (cos,sin) → angle and (x,y,z) → (theta,phi).
    mu_sel = getattr(selector, "mu_", None)
    mus_sel = getattr(selector, "mus_", None)
    amps = getattr(selector, "amplitudes_", None)

    mu_in_selector_space: Optional[list[float]] = None
    mu_in_feat_z: Optional[list[float]] = None
    mu_in_unscaled: Optional[list[float]] = None
    mu_decoded: Optional[dict] = None
    mus_unscaled_list: Optional[list[list[float]]] = None
    mus_decoded_list: Optional[list[dict]] = None

    def _decode_one(mu_vec: np.ndarray) -> tuple[np.ndarray, np.ndarray, dict]:
        if pca_pre is not None:
            feat_z = pca_pre.back_project(mu_vec)
        else:
            feat_z = np.asarray(mu_vec, dtype=np.float64)
        unscaled = encoder.inverse_scale(feat_z)
        return feat_z, unscaled, encoder.decode_to_parameters(unscaled)

    if mu_sel is not None:
        mu_arr = np.asarray(mu_sel, dtype=np.float64)
        mu_in_selector_space = mu_arr.tolist()
        feat_z, unscaled, decoded = _decode_one(mu_arr)
        mu_in_feat_z = feat_z.tolist()
        mu_in_unscaled = unscaled.tolist()
        mu_decoded = decoded

    if mus_sel is not None:
        mus_arr = np.asarray(mus_sel, dtype=np.float64)
        mus_unscaled_list = []
        mus_decoded_list = []
        for k in range(mus_arr.shape[0]):
            _, unscaled_k, decoded_k = _decode_one(mus_arr[k])
            mus_unscaled_list.append(unscaled_k.tolist())
            mus_decoded_list.append(decoded_k)

    noise_ceiling = compute_noise_ceiling(
        df=df,
        channel=channel,
        spike_rates_col=spike_rates_col,
        stim_ids=dataset.stim_ids,
    )

    # ------------------------------------------------------------------
    # Appearance summaries (for plot_shape_vs_appearance) pulled from the
    # built-in models. Plus the residual-on-appearance fit (a metric, not a
    # per-model axis fit, so it lives outside model_fits).
    # ------------------------------------------------------------------
    appearance_only_summary = (
        model_fits["appearance"].ridge_summary if "appearance" in model_fits else None
    )
    appearance_only_predictions = (
        model_fits["appearance"].predictions if "appearance" in model_fits else None
    )
    joint_summary = (
        model_fits["shape+appearance"].ridge_summary
        if "shape+appearance" in model_fits else None
    )
    joint_predictions = (
        model_fits["shape+appearance"].predictions
        if "shape+appearance" in model_fits else None
    )
    if "shape+appearance" in model_fits:
        n_shape_feats = X.shape[1]
        sa_w = np.asarray(
            model_fits["shape+appearance"].ridge_summary.get("weights") or [],
            dtype=np.float64,
        )
        joint_shape_w = sa_w[:n_shape_feats].tolist() if sa_w.size else None
        joint_app_w = sa_w[n_shape_feats:].tolist() if sa_w.size else None
    else:
        joint_shape_w = None
        joint_app_w = None

    # Appearance ridge fit on shape-model residuals (separate from the model
    # loop because it predicts residuals, not responses).
    residual_appearance_summary = None
    residual_appearance_predictions = None
    if A.shape[1] > 0:
        residuals = dataset.responses - predicted
        ridge_resid = (
            ridge_factory() if ridge_factory is not None else RidgeRegressionAxisModel()
        )
        ridge_resid.fit(A, residuals, feature_names=appearance.feature_names)
        residual_appearance_summary = ridge_resid.summary()
        residual_appearance_predictions = ridge_resid.predict(A).tolist()

    # 4) Texture-stratified shape CV R²: refit shape ridge within each
    # texture group (need enough samples; skip groups with <5).
    texture_strat_cv_r2: dict[str, float] = {}
    texture_strat_n: dict[str, int] = {}
    if appearance.texture_per_stim and any(t is not None for t in appearance.texture_per_stim):
        tex_arr = np.array(appearance.texture_per_stim)
        for tex in np.unique(tex_arr):
            if tex is None or (isinstance(tex, float) and np.isnan(tex)):
                continue
            mask = tex_arr == tex
            n_in = int(mask.sum())
            texture_strat_n[str(tex)] = n_in
            if n_in < 5:
                texture_strat_cv_r2[str(tex)] = float("nan")
                continue
            try:
                ridge_tex = (
                    ridge_factory() if ridge_factory is not None
                    else RidgeRegressionAxisModel()
                )
                ridge_tex.fit(X[mask], dataset.responses[mask])
                texture_strat_cv_r2[str(tex)] = (
                    ridge_tex.cv_r2_mean_ if ridge_tex.cv_r2_mean_ is not None else float("nan")
                )
            except Exception as e:
                print(f"  [texture-strat] {tex}: fit failed ({e})")
                texture_strat_cv_r2[str(tex)] = float("nan")

    # Thumbnail paths aligned with dataset.stim_ids (one path per stimulus).
    # Used by plot_axes_stimuli to render evenly-spaced exemplars per axis.
    thumbnail_paths: Optional[list[Optional[str]]] = None
    if "ThumbnailPath" in df.columns:
        path_map = (
            df.dropna(subset=["StimSpecId"])
              .drop_duplicates(subset=["StimSpecId"])
              .set_index("StimSpecId")["ThumbnailPath"]
              .to_dict()
        )
        thumbnail_paths = [path_map.get(sid) for sid in dataset.stim_ids]

    result = AxisCodingResult(
        channel=channel,
        component_type=component_type,
        strategy_label=strategy_label,
        n_stim=dataset.n_stim,
        n_features=dataset.n_features,
        n_dropped_no_components=dataset.n_dropped_no_components,
        n_dropped_no_response=dataset.n_dropped_no_response,
        selector_summary=(
            selector.summary(components_for_selector)
            if isinstance(selector, MultiPrototypeAttentionSelector)
            else selector.summary()
        ),
        ridge_summary=shape_fit.ridge_summary,
        selected_indices=[int(i) for i in selector.selected_indices_],
        stim_ids=[_jsonable(s) for s in dataset.stim_ids.tolist()],
        feature_names=dataset.feature_names,   # always original d-dim names
        actual_responses=dataset.responses.tolist(),
        predicted_responses=predicted.tolist(),
        axis_projections=axis_projections.tolist(),
        orthogonal_projections=orth_projections.tolist(),
        orthogonal_axis=orth_axis.tolist(),
        all_orthogonal_axes=all_orth_axes.tolist(),
        all_orthogonal_variances=all_orth_variances.tolist(),
        all_orthogonal_projections=all_orth_projections.tolist(),
        noise_ceiling=noise_ceiling,
        w_in_feature_space=w_feat.tolist() if w_feat is not None else None,
        orthogonal_axis_in_feature_space=(
            orth_axis_feat.tolist() if orth_axis_feat is not None else None
        ),
        all_orthogonal_axes_in_feature_space=(
            all_orth_axes_feat.tolist() if all_orth_axes_feat is not None else None
        ),
        pca_explained_variance=pca_var,
        mu_in_selector_space=mu_in_selector_space,
        mu_in_feature_space_zscored=mu_in_feat_z,
        mu_in_unscaled_space=mu_in_unscaled,
        mu_decoded=mu_decoded,
        mus_in_unscaled_space=mus_unscaled_list,
        mus_decoded=mus_decoded_list,
        prototype_amplitudes=(amps.tolist() if amps is not None else None),
        thumbnail_paths=thumbnail_paths,
        appearance_features=A.tolist() if A.size else None,
        appearance_feature_names=list(appearance.feature_names) or None,
        texture_per_stim=list(appearance.texture_per_stim) or None,
        appearance_only_summary=appearance_only_summary,
        appearance_only_predictions=appearance_only_predictions,
        joint_summary=joint_summary,
        joint_predictions=joint_predictions,
        joint_shape_weights=joint_shape_w,
        joint_appearance_weights=joint_app_w,
        residual_appearance_summary=residual_appearance_summary,
        residual_appearance_predictions=residual_appearance_predictions,
        texture_stratified_cv_r2=texture_strat_cv_r2 or None,
        texture_stratified_n=texture_strat_n or None,
        model_fits=(
            {name: dataclasses.asdict(fit) for name, fit in model_fits.items()}
        ),
    )

    # Console summary for the appearance comparison.
    def _r2_str(s):
        if s is None:
            return "n/a"
        m = s.get("cv_r2_mean")
        sd = s.get("cv_r2_std")
        if m is None or (isinstance(m, float) and np.isnan(m)):
            return "n/a"
        return f"{m:+.3f} ± {sd:.3f}" if sd is not None else f"{m:+.3f}"

    if appearance_only_summary is not None:
        print(
            "  [shape-vs-appearance CV R²]"
            f"  shape={_r2_str(result.ridge_summary)}"
            f"  appearance={_r2_str(appearance_only_summary)}"
            f"  joint={_r2_str(joint_summary)}"
            f"  appearance|residuals={_r2_str(residual_appearance_summary)}"
        )
    if texture_strat_cv_r2:
        parts = [
            f"{tex}: cv_r2={texture_strat_cv_r2[tex]:+.3f} (n={texture_strat_n[tex]})"
            for tex in texture_strat_cv_r2
        ]
        print("  [texture-stratified shape CV R²]  " + ",  ".join(parts))

    if save_dir is not None:
        os.makedirs(save_dir, exist_ok=True)
        channel_str = _channel_to_str(channel)
        path = os.path.join(
            save_dir,
            f"axis_coding_{channel_str}_{component_type}_{strategy_label}.json",
        )
        with open(path, "w") as f:
            json.dump(result.to_json_dict(), f, indent=2, default=_jsonable)
        print(f"  saved: {path}")

    return result


# ---------------------------------------------------------------------------
# Pipeline integration
# ---------------------------------------------------------------------------

class AxisCodingInputHandler(InputHandler):
    """Pipeline input handler: runs fit for one (component_type, strategy)."""

    def __init__(
        self,
        component_type: str,
        encoder: ComponentEncoder,
        strategy: AxisCodingStrategy,
        channel: Union[str, list[str]],
        spike_rates_col: Optional[str],
        save_dir: Optional[str],
    ):
        self.component_type = component_type
        self.encoder = encoder
        self.strategy = strategy
        self.channel = channel
        self.spike_rates_col = spike_rates_col
        self.save_dir = save_dir

    def prepare(self, compiled_data: pd.DataFrame) -> dict[str, Any]:
        result = fit_axis_coding(
            df=compiled_data,
            component_type=self.component_type,
            encoder=self.encoder,
            selector=self.strategy.selector_factory(),
            channel=self.channel,
            spike_rates_col=self.spike_rates_col,
            strategy_label=self.strategy.label,
            save_dir=self.save_dir,
            ridge_factory=self.strategy.ridge_factory,
            n_pcs=self.strategy.n_pcs,
        )
        return {"result": result}


class AxisCodingPlotter(ComputationModule):
    """Pipeline computation module: produces a diagnostic figure."""

    def __init__(self, title: Optional[str] = None):
        self.title = title

    def compute(self, prepared: dict[str, Any]) -> plt.Figure:
        result: AxisCodingResult = prepared["result"]
        return plot_axis_coding_result(result, title=self.title)


def make_axis_coding_module(
    component_type: str,
    encoder: ComponentEncoder,
    strategy: AxisCodingStrategy,
    channel: Union[str, list[str]],
    spike_rates_col: Optional[str],
    save_dir: Optional[str],
    title: Optional[str] = None,
    fig_save_path: Optional[str] = None,
):
    if fig_save_path is None and save_dir is not None:
        fig_save_path = os.path.join(
            save_dir,
            f"axis_coding_{_channel_to_str(channel)}_{component_type}_"
            f"{strategy.label}.png",
        )
    return AnalysisModuleFactory.create(
        input_handler=AxisCodingInputHandler(
            component_type=component_type,
            encoder=encoder,
            strategy=strategy,
            channel=channel,
            spike_rates_col=spike_rates_col,
            save_dir=save_dir,
        ),
        computation=AxisCodingPlotter(title=title),
        output_handler=FigureSaverOutput(save_path=fig_save_path),
        name=f"axis_coding_{component_type}_{strategy.label}",
    )


# ---------------------------------------------------------------------------
# Plot helper
# ---------------------------------------------------------------------------

def _project_onto_unit(X: np.ndarray, w: np.ndarray) -> np.ndarray:
    """Project rows of X onto the unit-normalized direction of w."""
    w_norm = float(np.linalg.norm(w))
    if w_norm < 1e-12:
        return np.zeros(X.shape[0])
    return X @ (w / w_norm)


def compute_all_orthogonal_axes(
    X: np.ndarray, w: np.ndarray, min_variance_ratio: float = 1e-8,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Full orthonormal basis of the null-space of the preferred axis ``w``,
    sorted by descending data variance.  PCA on residuals X - (X·ŵ)ŵ; the
    near-zero eigenvalue (the w-parallel direction, annihilated by the
    projection) is dropped.

    Returns
    -------
    axes : (d, n_orth) array
        Each column is a unit-norm direction orthogonal to w and to all earlier
        columns (by symmetry of the eigendecomposition).
    variances : (n_orth,) array
        Variance of the data projected onto each axis (eigenvalues in
        descending order).
    """
    w_norm = float(np.linalg.norm(w))
    if w_norm < 1e-12 or X.shape[0] < 2:
        return np.zeros((X.shape[1], 0)), np.array([])
    w_unit = w / w_norm
    X_orth = X - np.outer(X @ w_unit, w_unit)
    centered = X_orth - X_orth.mean(axis=0)
    cov = centered.T @ centered / max(1, len(centered) - 1)
    vals, vecs = np.linalg.eigh(cov)
    order = np.argsort(-vals)
    vals = vals[order]
    vecs = vecs[:, order]
    if vals.size > 0:
        threshold = max(float(vals[0]) * min_variance_ratio, 1e-12)
        keep = vals > threshold
        vals = vals[keep]
        vecs = vecs[:, keep]
    return vecs, vals


def compute_principal_orthogonal_axis(X: np.ndarray, w: np.ndarray) -> np.ndarray:
    """
    The highest-variance unit direction in the null-space of the preferred
    axis ``w``. Found by PCA on residuals X - (X·ŵ)ŵ.

    Returns a unit vector orthogonal to w. If w ≈ 0 or the orthogonal subspace
    has no variance, returns a zero vector.
    """
    w_norm = float(np.linalg.norm(w))
    if w_norm < 1e-12 or X.shape[0] < 2:
        return np.zeros_like(w)
    w_unit = w / w_norm
    X_orth = X - np.outer(X @ w_unit, w_unit)
    centered = X_orth - X_orth.mean(axis=0)
    cov = centered.T @ centered / max(1, len(centered) - 1)
    vals, vecs = np.linalg.eigh(cov)
    pc = vecs[:, -1]
    pc_norm = float(np.linalg.norm(pc))
    if pc_norm < 1e-12 or float(vals[-1]) < 1e-12:
        return np.zeros_like(w)
    return pc / pc_norm


def compute_axis_projections(result: AxisCodingResult) -> np.ndarray:
    """
    Projections onto the preferred ridge axis.  Uses the stored
    ``axis_projections`` if present; otherwise reconstructs them from
    predictions: x_i · ŵ = (predicted_i - intercept) / ||w||.
    """
    if result.axis_projections is not None:
        return np.asarray(result.axis_projections, dtype=np.float64)
    weights = result.ridge_summary.get("weights")
    intercept = result.ridge_summary.get("intercept")
    if weights is None or intercept is None:
        return np.full(len(result.predicted_responses), np.nan)
    w = np.asarray(weights, dtype=np.float64)
    w_norm = float(np.linalg.norm(w))
    if w_norm < 1e-12:
        return np.zeros(len(result.predicted_responses))
    pred = np.asarray(result.predicted_responses, dtype=np.float64)
    return (pred - float(intercept)) / w_norm


# Default permutation count for axis significance tests.  1000 is enough for
# p ≈ 0.001 resolution; bump if extreme tails matter.
_PERMUTATION_N = 1000


def _theilsen_fit(x: np.ndarray, y: np.ndarray) -> tuple[float, float, float, float]:
    """
    Theil–Sen median-of-slopes regression.

    Returns (slope, intercept, lo_slope, hi_slope) where lo/hi are the 95% CI
    on the slope (Lehmann's method via scipy.stats.theilslopes).  Robust to the
    high-leverage tails that bias OLS when projection samples are sparse at the
    ends of an axis.
    """
    res = theilslopes(y, x, alpha=0.95)
    return float(res[0]), float(res[1]), float(res[2]), float(res[3])


def _permutation_pvalue_spearman(
    x: np.ndarray,
    y: np.ndarray,
    n_perm: int = _PERMUTATION_N,
    random_state: int = 0,
) -> tuple[float, float]:
    """
    Two-sided permutation p-value for the Spearman rank correlation between
    x and y.  Returns ``(rho_observed, p_value)``.

    Permutation builds the null from the actual sample, so the p-value does
    NOT inflate with n the way an asymptotic Spearman p-value does.
    Spearman ρ is rank-based, so it is robust to high-leverage tail points.
    """
    obs_rho, _ = spearmanr(x, y)
    obs_rho = float(obs_rho) if obs_rho is not None and not np.isnan(obs_rho) else 0.0
    if x.size < 3:
        return obs_rho, 1.0
    rng = np.random.default_rng(random_state)
    null_rhos = np.empty(n_perm, dtype=np.float64)
    for i in range(n_perm):
        rho_i, _ = spearmanr(x, rng.permutation(y))
        null_rhos[i] = float(rho_i) if rho_i is not None and not np.isnan(rho_i) else 0.0
    # +1 numerator/denominator: Phipson & Smyth (2010) — never report p=0.
    p = float((np.sum(np.abs(null_rhos) >= abs(obs_rho)) + 1) / (n_perm + 1))
    return obs_rho, p


def _binned_mean_sem(x: np.ndarray, y: np.ndarray, n_bins: int):
    """Return (centers, means, sems) for y binned along x. NaN bins kept."""
    bin_edges = np.linspace(x.min(), x.max(), n_bins + 1)
    centers = 0.5 * (bin_edges[:-1] + bin_edges[1:])
    means, sems = [], []
    for lo, hi in zip(bin_edges[:-1], bin_edges[1:]):
        mask = (x >= lo) & (x < hi)
        if mask.sum() > 0:
            vals = y[mask]
            means.append(vals.mean())
            sems.append(vals.std(ddof=0) / np.sqrt(len(vals)))
        else:
            means.append(np.nan)
            sems.append(np.nan)
    return centers, np.asarray(means), np.asarray(sems)


def _draw_tuning_curve(ax, projections, actual, n_bins, xlabel, title):
    ax.scatter(projections, actual, s=12, alpha=0.5, label="stimuli")

    has_variance = (
        projections.size > 1
        and not np.all(np.isnan(projections))
        and projections.std() > 1e-12
    )

    if has_variance:
        centers, means, sems = _binned_mean_sem(projections, actual, n_bins)
        valid = ~np.isnan(means)
        ax.plot(centers[valid], means[valid], "k-", lw=2, label="binned mean")
        ax.fill_between(
            centers[valid],
            (means - sems)[valid],
            (means + sems)[valid],
            alpha=0.25,
            color="k",
        )

        # Theil–Sen line (robust to high-leverage tails) + permutation p-value
        # on Spearman ρ (does not inflate with n; rank-based, robust to outliers).
        slope, intercept, lo_slope, hi_slope = _theilsen_fit(projections, actual)
        xs = np.array([projections.min(), projections.max()])
        ys = intercept + slope * xs
        ax.plot(xs, ys, color="crimson", lw=1.5, alpha=0.8, label="Theil–Sen")
        rho, p_perm = _permutation_pvalue_spearman(projections, actual)
        stats_str = (
            f"slope (T-S) = {slope:+.3g}\n"
            f"  95% CI    = [{lo_slope:+.3g}, {hi_slope:+.3g}]\n"
            f"ρ (Spearman) = {rho:+.3f}\n"
            f"p (permute) = {p_perm:.2g}"
        )
        ax.text(
            0.02, 0.98, stats_str,
            transform=ax.transAxes, va="top", ha="left",
            fontsize=8, family="monospace",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.85, edgecolor="lightgray"),
        )

    ax.set_xlabel(xlabel)
    ax.set_ylabel("Actual response")
    ax.set_title(title)
    ax.legend(fontsize=8, loc="lower right")


def plot_shape_vs_appearance(
    result: AxisCodingResult,
    title: Optional[str] = None,
) -> Optional[plt.Figure]:
    """
    Compare how much variance shape vs appearance (texture + average RGB)
    accounts for in the firing rate.

    Layout (2 × 3):
      Row 0:
        (0,0) shape predicted vs actual              (in-sample, with CV R²)
        (0,1) appearance-only predicted vs actual    (in-sample, with CV R²)
        (0,2) shape residuals vs appearance prediction
      Row 1:
        (1,0) CV R² bars: shape / appearance / joint / appearance|residuals
              (with noise-ceiling reference if available)
        (1,1) appearance-only ridge weights
        (1,2) texture-stratified shape CV R² (if texture column present)
    """
    if result.appearance_only_summary is None:
        return None

    actual = np.asarray(result.actual_responses, dtype=np.float64)
    pred_shape = np.asarray(result.predicted_responses, dtype=np.float64)
    pred_app = (
        np.asarray(result.appearance_only_predictions, dtype=np.float64)
        if result.appearance_only_predictions is not None
        else None
    )
    pred_resid = (
        np.asarray(result.residual_appearance_predictions, dtype=np.float64)
        if result.residual_appearance_predictions is not None
        else None
    )
    residuals = actual - pred_shape

    texture_per_stim = result.texture_per_stim or [None] * len(actual)
    # Color by texture for the residual scatter.
    tex_palette = {
        "SHADE": "#4c72b0",
        "SPECULAR": "#dd8452",
        "2D": "#55a868",
        None: "lightgray",
    }
    point_colors = [tex_palette.get(t, "lightgray") for t in texture_per_stim]

    fig, axes = plt.subplots(2, 3, figsize=(18, 10))

    nc = result.noise_ceiling
    nc_str = f"  NC={nc:.3f}" if nc is not None else ""

    def _r2(s):
        if s is None:
            return float("nan")
        v = s.get("cv_r2_mean")
        return float(v) if v is not None else float("nan")

    r2_shape = _r2(result.ridge_summary)
    r2_app = _r2(result.appearance_only_summary)
    r2_joint = _r2(result.joint_summary)
    r2_resid_app = _r2(result.residual_appearance_summary)

    # (0,0) shape predicted vs actual.
    ax = axes[0, 0]
    ax.scatter(actual, pred_shape, s=14, c=point_colors, alpha=0.7, edgecolors="none")
    lims = [
        float(min(actual.min(), pred_shape.min())),
        float(max(actual.max(), pred_shape.max())),
    ]
    ax.plot(lims, lims, "k--", lw=1)
    ax.set_xlabel("Actual response")
    ax.set_ylabel("Predicted (shape)")
    ax.set_title(f"Shape model\nCV R² = {r2_shape:+.3f}{nc_str}")

    # (0,1) appearance predicted vs actual.
    ax = axes[0, 1]
    if pred_app is not None:
        ax.scatter(actual, pred_app, s=14, c=point_colors, alpha=0.7, edgecolors="none")
        lims2 = [
            float(min(actual.min(), pred_app.min())),
            float(max(actual.max(), pred_app.max())),
        ]
        ax.plot(lims2, lims2, "k--", lw=1)
        ax.set_xlabel("Actual response")
        ax.set_ylabel("Predicted (appearance only)")
        ax.set_title(f"Appearance-only model\nCV R² = {r2_app:+.3f}")
    else:
        ax.axis("off")

    # (0,2) residuals vs appearance prediction. Headline panel.
    ax = axes[0, 2]
    if pred_resid is not None:
        ax.scatter(pred_resid, residuals, s=14, c=point_colors, alpha=0.7, edgecolors="none")
        lo = min(float(pred_resid.min()), float(residuals.min()))
        hi = max(float(pred_resid.max()), float(residuals.max()))
        ax.plot([lo, hi], [lo, hi], "k--", lw=1, alpha=0.5)
        ax.axhline(0, color="gray", lw=0.6)
        ax.set_xlabel("Appearance prediction (fit on shape residuals)")
        ax.set_ylabel("Shape residual (actual − shape pred)")
        ax.set_title(
            f"Residuals vs appearance\nCV R² (appearance | residuals) = {r2_resid_app:+.3f}"
        )
        # legend by texture.
        seen = []
        for t in texture_per_stim:
            if t in seen:
                continue
            seen.append(t)
            ax.scatter([], [], color=tex_palette.get(t, "lightgray"),
                       label=str(t) if t is not None else "unknown",
                       s=20, edgecolors="none")
        if seen:
            ax.legend(fontsize=7, loc="best", title="texture")
    else:
        ax.axis("off")

    # (1,0) CV R² bars.
    ax = axes[1, 0]
    bar_labels = ["shape", "appearance", "joint", "appearance|resid"]
    bar_vals = [r2_shape, r2_app, r2_joint, r2_resid_app]
    bar_colors = ["#4c72b0", "#dd8452", "#8172b3", "#937860"]
    x = np.arange(len(bar_labels))
    bars = ax.bar(x, bar_vals, color=bar_colors)
    for b, v in zip(bars, bar_vals):
        ax.text(b.get_x() + b.get_width() / 2, v,
                f"{v:+.3f}", ha="center",
                va="bottom" if v >= 0 else "top", fontsize=8)
    if nc is not None:
        ax.axhline(nc, color="black", lw=1, ls=":", label=f"NC = {nc:.3f}")
        ax.legend(fontsize=8, loc="best")
    ax.axhline(0, color="black", lw=0.7)
    ax.set_xticks(x)
    ax.set_xticklabels(bar_labels, rotation=20, ha="right", fontsize=9)
    ax.set_ylabel("Held-out CV R²")
    ax.set_title("Variance explained")

    # (1,1) appearance-only ridge weights.
    ax = axes[1, 1]
    app_summary = result.appearance_only_summary
    app_w = np.asarray(app_summary.get("weights") or [], dtype=np.float64)
    app_names = list(result.appearance_feature_names or [])
    if app_w.size and len(app_names) == app_w.size:
        order = np.argsort(-np.abs(app_w))
        names = [app_names[i] for i in order]
        vals = app_w[order]
        y = np.arange(len(names))
        ax.barh(y, vals, color="darkorange")
        ax.set_yticks(y)
        ax.set_yticklabels(names, fontsize=8)
        ax.invert_yaxis()
        ax.axvline(0, color="black", lw=0.8)
        ax.set_xlabel("Ridge weight (appearance-only model)")
        ax.set_title("Appearance feature weights")
    else:
        ax.axis("off")

    # (1,2) texture-stratified shape CV R².
    ax = axes[1, 2]
    strat = result.texture_stratified_cv_r2 or {}
    n_per = result.texture_stratified_n or {}
    if strat:
        keys = list(strat.keys())
        vals = [strat[k] for k in keys]
        x_t = np.arange(len(keys))
        colors_t = [tex_palette.get(k, "lightgray") for k in keys]
        bars = ax.bar(x_t, vals, color=colors_t)
        ax.axhline(r2_shape, color="black", lw=1, ls="--",
                   label=f"all stim: {r2_shape:+.3f}")
        for b, v, k in zip(bars, vals, keys):
            n = n_per.get(k, 0)
            ax.text(b.get_x() + b.get_width() / 2, v,
                    f"n={n}", ha="center",
                    va="bottom" if v >= 0 else "top", fontsize=7)
        ax.set_xticks(x_t)
        ax.set_xticklabels(keys, fontsize=9)
        ax.axhline(0, color="black", lw=0.7)
        ax.set_ylabel("Held-out CV R² (shape)")
        ax.set_title("Shape model: texture-stratified")
        ax.legend(fontsize=8, loc="best")
    else:
        ax.axis("off")

    if title:
        fig.suptitle(title)
    fig.tight_layout()
    return fig


def plot_axis_coding_result(
    result: AxisCodingResult, title: Optional[str] = None, n_bins: int = 10
) -> plt.Figure:
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))

    actual = np.asarray(result.actual_responses)
    pred = np.asarray(result.predicted_responses)
    axis_proj = compute_axis_projections(result)
    orth_proj = (
        np.asarray(result.orthogonal_projections, dtype=np.float64)
        if result.orthogonal_projections is not None
        else np.zeros_like(axis_proj)
    )

    cv_r2 = result.ridge_summary.get("cv_r2_mean")
    cv_r2_std = result.ridge_summary.get("cv_r2_std")
    nc = result.noise_ceiling

    r2_str = (
        f"CV R² = {cv_r2:.3f} ± {cv_r2_std:.3f}"
        if cv_r2 is not None and not np.isnan(cv_r2)
        else "CV R² = n/a"
    )
    if nc is not None:
        frac = cv_r2 / nc if (cv_r2 is not None and not np.isnan(cv_r2) and nc > 0) else float("nan")
        nc_str = f"NC = {nc:.3f}  ({frac:.0%} of ceiling)" if np.isfinite(frac) else f"NC = {nc:.3f}"
    else:
        nc_str = "NC = n/a (single-trial or pre-averaged data)"

    # Panel (0,0): Predicted vs actual
    ax = axes[0, 0]
    ax.scatter(actual, pred, s=12, alpha=0.6)
    lims = [
        float(min(actual.min(), pred.min())),
        float(max(actual.max(), pred.max())),
    ]
    ax.plot(lims, lims, "k--", lw=1)
    ax.set_xlabel("Actual response")
    ax.set_ylabel("Predicted response")
    ax.set_title(
        f"{result.component_type} | {result.strategy_label}\n{r2_str}\n{nc_str}"
    )

    # Panel (0,1): Tuning curve along preferred axis
    _draw_tuning_curve(
        axes[0, 1], axis_proj, actual, n_bins,
        xlabel="Projection onto preferred axis (z-scored units)",
        title="Axis tuning curve (preferred)",
    )

    # Panel (0,2): Top |w| bars — back-projected to original feature space when
    # PCA was used, so bar names are always the raw encoder features.
    ax = axes[0, 2]
    if result.w_in_feature_space is not None:
        weights_full = np.asarray(result.w_in_feature_space, dtype=np.float64)
        w_label = "Ridge weight (back-projected from PC space)"
        w_title = "Top features by |w|  (preferred axis, back-projected)"
    else:
        weights_full = np.asarray(
            result.ridge_summary.get("weights") or [], dtype=np.float64
        )
        w_label = "Ridge weight w"
        w_title = "Top features by |w|  (preferred axis)"
    feature_names = result.feature_names or []
    if weights_full.size and feature_names and len(feature_names) == weights_full.size:
        order = np.argsort(-np.abs(weights_full))[:10]
        names = [feature_names[i] for i in order]
        vals = weights_full[order]
        y = np.arange(len(names))
        ax.barh(y, vals, color="steelblue")
        ax.set_yticks(y)
        ax.set_yticklabels(names, fontsize=8)
        ax.invert_yaxis()
        ax.axvline(0, color="black", lw=0.8)
        ax.set_xlabel(w_label)
        ax.set_title(w_title)

    # Panel (1,0): Tuning along principal orthogonal axis
    _draw_tuning_curve(
        axes[1, 0], orth_proj, actual, n_bins,
        xlabel="Projection onto principal orthogonal axis (z-scored units)",
        title="Tuning along principal orthogonal axis",
    )

    # Panel (1,1): 2D scatter (preferred axis, orth axis) colored by response
    ax = axes[1, 1]
    sc = ax.scatter(
        axis_proj, orth_proj, c=actual,
        cmap="viridis", s=22, alpha=0.85,
        edgecolors="none",
    )
    ax.axhline(0, color="gray", lw=0.6, ls="--")
    ax.axvline(0, color="gray", lw=0.6, ls="--")
    ax.set_xlabel("Preferred axis projection")
    ax.set_ylabel("Principal orthogonal axis projection")
    ax.set_title("Axis vs orthogonal (color = response)")
    plt.colorbar(sc, ax=ax, label="Response")

    # Panel (1,2): Top |orth_axis| bars — back-projected when PCA was used.
    ax = axes[1, 2]
    if result.orthogonal_axis_in_feature_space is not None:
        orth = np.asarray(result.orthogonal_axis_in_feature_space, dtype=np.float64)
        orth_label = "Orthogonal-axis loading (back-projected)"
        orth_title = "Top features by |orth|  (principal orth axis, back-projected)"
    else:
        orth = (
            np.asarray(result.orthogonal_axis, dtype=np.float64)
            if result.orthogonal_axis is not None
            else np.array([])
        )
        orth_label = "Orthogonal-axis loading"
        orth_title = "Top features by |orth|  (principal orthogonal axis)"
    if orth.size and feature_names and len(feature_names) == orth.size:
        order = np.argsort(-np.abs(orth))[:10]
        names = [feature_names[i] for i in order]
        vals = orth[order]
        y = np.arange(len(names))
        ax.barh(y, vals, color="darkorange")
        ax.set_yticks(y)
        ax.set_yticklabels(names, fontsize=8)
        ax.invert_yaxis()
        ax.axvline(0, color="black", lw=0.8)
        ax.set_xlabel(orth_label)
        ax.set_title(orth_title)
    else:
        ax.axis("off")

    if title:
        fig.suptitle(title)
    fig.tight_layout()
    return fig


def plot_orthogonal_axes_diagnostic(
    result: AxisCodingResult,
    n_bins: int = 10,
    title: Optional[str] = None,
) -> Optional[plt.Figure]:
    """
    Per-axis diagnostic for axis coding.

    Layout (2 × 3):
      Row 0:  (0, 0) principal orthogonal axis tuning curve (binned mean ± SEM,
                     OLS line, slope/ρ/p annotation)
              (0, 1) overlay of binned mean-response curves for every axis
                     (preferred + all orthogonal), each in its own color so
                     flat orthogonal curves vs a steep preferred curve are
                     readable at a glance
              (0, 2) blank
      Row 1:  three summary panels across the preferred axis + all orthogonal
              PCs (preferred axis first, then orth PCs sorted by variance):
                (1, 0) OLS slope per axis                    ← main test
                (1, 1) |Spearman ρ| per axis
                (1, 2) variance fraction per axis (for context)

    For axis coding to hold, the preferred-axis bar should dominate row 1
    columns 0 and 1, and every orthogonal bar should be near zero — *regardless
    of how much variance that orthogonal direction captures*.
    """
    if result.all_orthogonal_projections is None or result.all_orthogonal_variances is None:
        return None

    proj_orth = np.asarray(result.all_orthogonal_projections, dtype=np.float64)
    variances_orth = np.asarray(result.all_orthogonal_variances, dtype=np.float64)
    actual = np.asarray(result.actual_responses, dtype=np.float64)

    if proj_orth.size == 0 or variances_orth.size == 0:
        return None

    n_orth = proj_orth.shape[1]

    # Preferred-axis projection + its data variance, prepended to the orth set.
    proj_pref = compute_axis_projections(result)
    var_pref = float(np.var(proj_pref, ddof=1)) if proj_pref.size > 1 else 0.0
    var_total = var_pref + float(variances_orth.sum())

    # All axes: index 0 = preferred, 1..n_orth = orth PCs (sorted by variance).
    n_axes = 1 + n_orth
    proj_all = np.column_stack([proj_pref, proj_orth])
    variances_all = np.concatenate([[var_pref], variances_orth])
    var_frac_all = (
        variances_all / var_total if var_total > 1e-12 else np.zeros_like(variances_all)
    )

    # Theil–Sen slope per axis (robust to tail leverage); permutation p-value on
    # Spearman ρ per axis (controls for n inflation; robust to outliers).
    slopes = np.zeros(n_axes)
    slope_lo = np.zeros(n_axes)
    slope_hi = np.zeros(n_axes)
    rhos = np.zeros(n_axes)
    pvals = np.ones(n_axes)
    for k in range(n_axes):
        col = proj_all[:, k]
        if col.std() > 1e-12:
            s, _, lo, hi = _theilsen_fit(col, actual)
            slopes[k] = s
            slope_lo[k] = lo
            slope_hi[k] = hi
            rho, p = _permutation_pvalue_spearman(col, actual)
            rhos[k] = rho
            pvals[k] = p

    # ------------------------------------------------------------------
    # Figure
    # ------------------------------------------------------------------
    fig, axes = plt.subplots(2, 3, figsize=(18, 9))

    # Row 0, col 0: principal orthogonal axis tuning curve.
    ax = axes[0, 0]
    proj = proj_orth[:, 0]
    ax.scatter(proj, actual, s=10, alpha=0.5, label="stimuli")
    if proj.std() > 1e-12:
        centers, means, sems = _binned_mean_sem(proj, actual, n_bins)
        valid = ~np.isnan(means)
        ax.plot(centers[valid], means[valid], "k-", lw=2, label="binned mean")
        ax.fill_between(
            centers[valid],
            (means - sems)[valid],
            (means + sems)[valid],
            alpha=0.25, color="k",
        )
        slope_p, intercept_p, _, _ = _theilsen_fit(proj, actual)
        xs = np.array([proj.min(), proj.max()])
        ax.plot(xs, intercept_p + slope_p * xs,
                color="crimson", lw=1.5, alpha=0.8, label="Theil–Sen")
        ax.text(
            0.02, 0.98,
            f"orth PC1  var={variances_orth[0] / max(var_total, 1e-12):.1%}\n"
            f"slope (T-S) = {slopes[1]:+.3g}\n"
            f"  95% CI    = [{slope_lo[1]:+.3g}, {slope_hi[1]:+.3g}]\n"
            f"ρ (Spearman) = {rhos[1]:+.3f}\n"
            f"p (permute) = {pvals[1]:.2g}",
            transform=ax.transAxes, va="top", ha="left",
            fontsize=8, family="monospace",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                      alpha=0.85, edgecolor="lightgray"),
        )
    ax.set_xlabel("Projection onto principal orth axis")
    ax.set_ylabel("Actual response")
    ax.set_title("Principal orthogonal axis tuning")
    ax.legend(fontsize=7, loc="lower right")

    # Row 0, col 1: overlay binned mean-response curves for all axes.
    # Preferred = forestgreen (bold); orth = sequential viridis colors.
    ax = axes[0, 1]
    cmap = plt.get_cmap("viridis")
    colors_overlay = ["forestgreen"] + [
        cmap(i / max(n_orth - 1, 1)) for i in range(n_orth)
    ]
    labels_overlay = ["preferred"] + [f"orth {k+1}" for k in range(n_orth)]
    for k in range(n_axes):
        col = proj_all[:, k]
        if col.std() < 1e-12:
            continue
        centers, means, sems = _binned_mean_sem(col, actual, n_bins)
        valid = ~np.isnan(means)
        if not valid.any():
            continue
        lw = 2.5 if k == 0 else 1.2
        alpha = 1.0 if k == 0 else 0.85
        ax.plot(
            centers[valid], means[valid],
            color=colors_overlay[k], lw=lw, alpha=alpha,
            label=labels_overlay[k],
        )
    ax.axhline(actual.mean(), color="gray", lw=0.7, ls="--", alpha=0.6)
    ax.set_xlabel("Projection onto axis (z-scored units)")
    ax.set_ylabel("Mean response")
    ax.set_title(
        "All axes overlay\n(preferred should be steep; orth should be flat)"
    )
    ax.legend(fontsize=7, loc="best", ncol=2)

    # Row 0, col 2: feature loadings for all axes (heatmap).
    # Rows = original features; cols = preferred + each orth axis.
    # Each column is unit-normalized so colors are comparable across axes.
    ax = axes[0, 2]
    feature_names = result.feature_names or []
    # Preferred-axis loading: prefer back-projected w (matches PCA case);
    # falls back to ridge weights for non-PCA case. Same column the |w| bar
    # chart in the main figure uses.
    if result.w_in_feature_space is not None:
        w_feat = np.asarray(result.w_in_feature_space, dtype=np.float64)
    else:
        w_feat = np.asarray(
            result.ridge_summary.get("weights") or [], dtype=np.float64
        )
    # Orthogonal loadings: use back-projected when PCA was used so the row
    # labels are original feature names; otherwise use the PC-space axes
    # which already live in original-feature space.
    if result.all_orthogonal_axes_in_feature_space is not None:
        orth_loadings = np.asarray(
            result.all_orthogonal_axes_in_feature_space, dtype=np.float64
        )
    elif result.all_orthogonal_axes is not None:
        orth_loadings = np.asarray(result.all_orthogonal_axes, dtype=np.float64)
    else:
        orth_loadings = np.zeros((len(feature_names), 0))

    if w_feat.size and feature_names and len(feature_names) == w_feat.size:
        # Build (d, n_axes) matrix; unit-normalize each column so colors are
        # comparable across axes (the absolute scale of w doesn't matter).
        cols = [w_feat / max(float(np.linalg.norm(w_feat)), 1e-12)]
        for j in range(orth_loadings.shape[1]):
            v = orth_loadings[:, j]
            cols.append(v / max(float(np.linalg.norm(v)), 1e-12))
        M = np.column_stack(cols)
        col_labels = ["preferred"] + [
            f"orth {k+1}" for k in range(orth_loadings.shape[1])
        ]

        vmax = max(float(np.max(np.abs(M))), 1e-12) if M.size else 1.0
        im = ax.imshow(
            M, aspect="auto", cmap="RdBu_r",
            vmin=-vmax, vmax=vmax, interpolation="nearest",
        )
        ax.set_xticks(np.arange(len(col_labels)))
        ax.set_xticklabels(col_labels, rotation=45, ha="right", fontsize=7)
        ax.set_yticks(np.arange(len(feature_names)))
        ax.set_yticklabels(feature_names, fontsize=7)
        ax.set_title("Loadings per axis (unit-norm)\nrows = features, cols = axes")
        plt.colorbar(im, ax=ax, fraction=0.04, pad=0.02, label="loading")
    else:
        ax.axis("off")

    # ------------------------------------------------------------------
    # Row 1: summaries across preferred axis + all orthogonal PCs.
    # ------------------------------------------------------------------
    labels = ["preferred"] + [f"orth {k+1}" for k in range(n_orth)]
    x = np.arange(n_axes)
    colors = ["forestgreen"] + ["steelblue"] * n_orth   # preferred stands out

    # Theil–Sen slope per axis with 95% CI error bars.
    ax = axes[1, 0]
    yerr_lo = np.maximum(slopes - slope_lo, 0.0)
    yerr_hi = np.maximum(slope_hi - slopes, 0.0)
    bars = ax.bar(
        x, slopes, color=colors,
        yerr=[yerr_lo, yerr_hi], capsize=3, ecolor="black",
        error_kw={"lw": 0.7},
    )
    for k, b in enumerate(bars):
        # Red edge: orth bar whose permutation p < 0.05.
        if pvals[k] < 0.05 and k > 0:
            b.set_edgecolor("crimson")
            b.set_linewidth(1.5)
    # Per-bar permutation p-value label, placed just outside the CI bar tip.
    for k, b in enumerate(bars):
        if slopes[k] >= 0:
            label_y = slopes[k] + yerr_hi[k]
            va = "bottom"
        else:
            label_y = slopes[k] - yerr_lo[k]
            va = "top"
        ax.text(
            b.get_x() + b.get_width() / 2, label_y,
            f"p={pvals[k]:.2g}",
            ha="center", va=va, fontsize=7, color="black",
        )
    ax.axhline(0, color="black", lw=0.7)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Slope (response per z-unit)")
    ax.set_title(
        "Slope per axis (95% CI; Theil–Sen)\n"
        "preferred should dominate; orth bars ≈ 0"
    )

    # |Spearman ρ| per axis with permutation p-value gating.
    ax = axes[1, 1]
    bars = ax.bar(x, np.abs(rhos), color=colors)
    for k, b in enumerate(bars):
        if pvals[k] < 0.05 and k > 0:
            b.set_edgecolor("crimson")
            b.set_linewidth(1.5)
    ax.axhline(0.1, color="gray", lw=1, ls="--", label="|ρ|=0.1")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("|Spearman ρ|")
    ax.set_title("Rank correlation per axis\n(red edge: permutation p<0.05)")
    ax.legend(fontsize=8)

    # Variance fraction per axis (small panel for context)
    ax = axes[1, 2]
    ax.bar(x, var_frac_all * 100.0, color=colors)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Variance fraction (%)")
    ax.set_title("Data variance per axis")

    if title:
        fig.suptitle(title)
    fig.tight_layout()
    return fig


@dataclass
class PlotPanelConfig:
    """
    Per-panel enable/disable flags for the consolidated axis-coding figure
    and the shape-vs-appearance figure. Defaults match the layout you asked
    for: 3 × 4 axis-coding figure with tuning, axes overlay, loadings, signed
    Spearman r per axis, variance per axis, and μ panels enabled. Old panels
    (top-features bars, |ρ| bar, slope-with-CI bar, in-axis pred-vs-actual,
    PC-space pred-vs-actual) stay in code but default-off; flip the flag to
    bring them back without touching the plot function.
    """

    # ----- Figure 2: consolidated axis coding -----
    show_preferred_tuning: bool = True
    show_orth_tuning: bool = True
    show_2d_scatter: bool = True
    show_all_axes_overlay: bool = True
    show_loadings_heatmap: bool = True
    show_signed_r_per_axis: bool = True
    show_variance_per_axis: bool = True
    show_mu_panels: bool = True
    # Default-off (legacy panels from plot_axis_coding_result + orth diagnostic).
    show_pred_vs_actual_in_axis_fig: bool = False
    show_top_features_w_bar: bool = False
    show_top_features_orth_bar: bool = False
    show_slope_per_axis_bar: bool = False
    show_abs_spearman_per_axis_bar: bool = False

    # ----- Figure 1: shape vs appearance (currently always all-on) -----
    show_appearance_residuals: bool = True
    show_texture_stratified: bool = True


def _signed_spearman(x: np.ndarray, y: np.ndarray) -> float:
    """Signed Spearman ρ. Returns NaN if the input has no variance."""
    if x.size < 2 or x.std() < 1e-12 or y.std() < 1e-12:
        return float("nan")
    rho, _ = spearmanr(x, y)
    return float(rho) if rho is not None else float("nan")


@dataclass
class _AxisView:
    """Lightweight view object — one set of axis-coding fields the plot reads."""
    axis_projections: np.ndarray
    orthogonal_projections: np.ndarray
    all_orthogonal_projections: np.ndarray
    all_orthogonal_variances: np.ndarray
    feature_names: list[str]
    w_in_feature_space: Optional[np.ndarray]
    all_orthogonal_axes_in_feature_space: Optional[np.ndarray]
    all_orthogonal_axes: Optional[np.ndarray]
    orthogonal_axis: Optional[np.ndarray]
    orthogonal_axis_in_feature_space: Optional[np.ndarray]
    ridge_summary: dict
    predicted_responses: np.ndarray


def _make_axis_view(result: AxisCodingResult, model_name: str) -> _AxisView:
    """
    Build a view of one model's axis-coding fit. Looks up the model fit in
    ``result.model_fits`` and assembles a uniform _AxisView regardless of
    which model produced it. Falls back to the flat shape fields for
    ``model_name="shape"`` if model_fits hasn't been populated (legacy json).
    """
    def _np(x, default_shape=None):
        if x is None:
            return None if default_shape is None else np.zeros(default_shape)
        return np.asarray(x, dtype=np.float64)

    fits = result.model_fits or {}
    if model_name in fits:
        f = fits[model_name]
        axis_proj = _np(f.get("axis_projections"))
        orth_proj = _np(f.get("orth_projections"), (axis_proj.size,))
        all_orth_proj = _np(f.get("all_orth_projections"), (axis_proj.size, 0))
        variances = _np(f.get("all_orth_variances"), (0,))
        feature_names = list(f.get("feature_names_interp") or [])
        w_feat = _np(f.get("w_in_feature_space"))
        all_orth_axes_feat = _np(f.get("all_orth_axes_in_feature_space"))
        all_orth_axes = _np(f.get("all_orth_axes"))
        orth_axis = _np(f.get("orth_axis"))
        orth_axis_feat = _np(f.get("orth_axis_in_feature_space"))
        ridge_summary = f.get("ridge_summary") or {}
        pred = _np(f.get("predictions"), (axis_proj.size,))
    elif model_name == "shape":
        axis_proj = _np(result.axis_projections)
        orth_proj = _np(result.orthogonal_projections, (axis_proj.size,))
        all_orth_proj = _np(result.all_orthogonal_projections,
                             (axis_proj.size, 0))
        variances = _np(result.all_orthogonal_variances, (0,))
        feature_names = list(result.feature_names or [])
        w_feat = _np(result.w_in_feature_space)
        all_orth_axes_feat = _np(result.all_orthogonal_axes_in_feature_space)
        all_orth_axes = _np(result.all_orthogonal_axes)
        orth_axis = _np(result.orthogonal_axis)
        orth_axis_feat = _np(result.orthogonal_axis_in_feature_space)
        ridge_summary = result.ridge_summary
        pred = _np(result.predicted_responses, (axis_proj.size,))
    else:
        raise KeyError(
            f"Model '{model_name}' not found in result.model_fits "
            f"(have: {list(fits.keys())})"
        )

    return _AxisView(
        axis_projections=axis_proj,
        orthogonal_projections=orth_proj,
        all_orthogonal_projections=all_orth_proj,
        all_orthogonal_variances=variances,
        feature_names=feature_names,
        w_in_feature_space=w_feat,
        all_orthogonal_axes_in_feature_space=all_orth_axes_feat,
        all_orthogonal_axes=all_orth_axes,
        orthogonal_axis=orth_axis,
        orthogonal_axis_in_feature_space=orth_axis_feat,
        ridge_summary=ridge_summary,
        predicted_responses=pred,
    )


def plot_orthogonal_tuning_curves(
    result: AxisCodingResult,
    title: Optional[str] = None,
) -> Optional[plt.Figure]:
    """
    Tsao Fig. 4A-style summary, one panel showing every model overlaid plus
    a side bar of the headline scalar.

    Left panel
    ----------
    Average tuning along random axes orthogonal to each model's preferred
    axis, on a shared z-scored x-grid. Each model is one line; shaded band
    is ± SD across kept axes (so it's the per-cell within-axis spread, not
    a population SD). Gaussian fit ``a·exp(-x²/σ²) + c`` is overlaid as a
    thin curve in the same color. Legend annotates each model with
    ``a/(a+c)`` and σ.

    Right panel
    -----------
    Bar chart of the headline scalar ``a/(a+c)`` per model. Axis-coding
    predicts ≈ 0; exemplar coding predicts ≫ 0.
    """
    fits = result.model_fits or {}
    models = [name for name, f in fits.items() if f.get("orth_tuning_x")]
    if not models:
        return None

    fig, axes = plt.subplots(1, 2, figsize=(14, 5),
                              gridspec_kw={"width_ratios": [3, 1]})
    # Density panel inset on the curves panel.
    ax_density = axes[0].twinx()
    ax_density.set_ylabel("Mean stim per bin per axis", color="gray", fontsize=8)
    ax_density.tick_params(axis="y", colors="gray", labelsize=7)
    ax_density.spines["right"].set_color("gray")
    cmap = plt.get_cmap("tab10")

    ax = axes[0]
    amp_norms: list[float] = []
    line_labels: list[str] = []
    for i, name in enumerate(models):
        f = fits[name]
        x = np.asarray(f["orth_tuning_x"], dtype=np.float64)
        y = np.asarray(f["orth_tuning_mean"], dtype=np.float64)
        sd = np.asarray(f.get("orth_tuning_sd") or [], dtype=np.float64)
        color = cmap(i % 10)

        fit_ok = f.get("orth_gauss_fit_ok")
        if fit_ok:
            a = float(f["orth_gauss_a"])
            sigma = float(f["orth_gauss_sigma"])
            c = float(f["orth_gauss_c"])
            denom = a + c
        else:
            a = sigma = c = float("nan")
            denom = 1.0

        # Normalize by Gaussian peak (a + c), Tsao's convention.
        if fit_ok and abs(denom) > 1e-9:
            y_n = y / denom
            sd_n = sd / abs(denom) if sd.size == y.size else sd
            xx = np.linspace(x.min(), x.max(), 200)
            yy = (a * np.exp(-(xx ** 2) / (sigma ** 2)) + c) / denom
            amp = a / denom
            baseline = c / denom
            label = (f"{name}: a/(a+c)={amp:+.2f}, σ={sigma:.2g}, "
                     f"baseline={baseline:.2f} (n={f.get('orth_tuning_n_axes_used')})")
        else:
            # Fallback: show raw response so user sees something.
            y_n = y
            sd_n = sd
            xx = None
            yy = None
            amp = float("nan")
            label = f"{name}: (Gaussian fit failed, showing raw)"

        ax.plot(x, y_n, color=color, lw=2, label=label)
        line_labels.append(label)
        if sd_n.size == y_n.size:
            ax.fill_between(x, y_n - sd_n, y_n + sd_n, color=color, alpha=0.15)
        if xx is not None and yy is not None:
            ax.plot(xx, yy, color=color, lw=1.0, ls="--", alpha=0.9)

        amp_norms.append(amp)

    # Density panel (gray bars): mean stim per bin per axis, averaged across
    # the kept axes. Sparse tails get squashed bars → take the apparent
    # "dip" out there with a grain of salt.
    first = next(iter(fits.values()))
    counts = np.asarray(first.get("orth_tuning_count") or [], dtype=np.float64)
    if counts.size:
        x_centers = np.asarray(first["orth_tuning_x"], dtype=np.float64)
        ax_density.bar(x_centers, counts, width=0.7 * (x_centers[1] - x_centers[0])
                       if x_centers.size > 1 else 0.5,
                       color="lightgray", alpha=0.5, zorder=0)
        ax_density.set_ylim(0, max(1.0, float(counts.max()) * 4))

    # Reference lines: peak = 1 and the implied "flat" baseline = 0 modulation.
    ax.axhline(1.0, color="gray", lw=0.7, ls=":", alpha=0.7)
    ax.axhline(0.0, color="black", lw=0.5)
    ax.set_xlabel("Projection onto random orthogonal axis (z-scored)")
    ax.set_ylabel("Normalized response  [ y / (a+c) ]")
    fit_lim = first.get("orth_tuning_fit_z_range")
    if fit_lim is not None:
        ax.axvspan(-fit_lim, fit_lim, color="khaki", alpha=0.10, zorder=0,
                    label=f"Gaussian fit range  ±{fit_lim:.1f}")
    ax.legend(fontsize=8, loc="best")
    ax.set_title("Average tuning along orthogonal axes\n(Tsao-normalized: peak at x=0 → 1)")

    # Right panel: modulation depth a/(a+c) per model.
    # Read it as: how much of the normalized peak is "bump" vs flat baseline.
    #   0 → curve is flat; orth axes carry no information (axis coding).
    #   1 → baseline is 0; orth axes are as informative as the preferred axis
    #       (exemplar-like).
    ax2 = axes[1]
    x_b = np.arange(len(models))
    bar_colors = [cmap(i % 10) for i in range(len(models))]
    ax2.bar(x_b, amp_norms, color=bar_colors)
    for i, v in enumerate(amp_norms):
        if np.isfinite(v):
            ax2.text(i, v, f"{v:+.2f}", ha="center",
                     va="bottom" if v >= 0 else "top", fontsize=8)
    ax2.axhline(0, color="black", lw=0.7, ls="--", alpha=0.7,
                label="flat (axis coding)")
    ax2.axhline(1, color="gray", lw=0.7, ls=":", alpha=0.7,
                label="full bump (exemplar)")
    ax2.set_xticks(x_b)
    ax2.set_xticklabels(models, rotation=20, ha="right", fontsize=8)
    ax2.set_ylabel("Modulation depth  a / (a + c)")
    ax2.set_title("Bump-vs-flat per model\n0 = flat (axis), 1 = full bump (exemplar)")
    ax2.legend(fontsize=7, loc="best")

    if title:
        fig.suptitle(title)
    fig.tight_layout()
    return fig


def plot_orthogonal_tuning_per_axis_detail(
    result: AxisCodingResult,
    title: Optional[str] = None,
    n_highlight: int = 1,
) -> Optional[plt.Figure]:
    """
    Per-model detail of the orthogonal-tuning summary: every kept random
    orthogonal axis plotted individually so a single bumpy axis can't be
    hidden by the average.

    Layout: one column per model. For each model:
      - Top panel: every kept axis as a faint thin line (Tsao-normalized
        when the Gaussian fit succeeded), the mean curve in bold, and the
        ``n_highlight`` most-modulated individual axes overlaid in red.
      - Bottom panel: histogram of per-axis modulation depth
        ``(max − min) / |max|`` of each axis's binned mean curve. A long
        right tail = some axes are highly modulated even though the
        average looks flat.
    """
    fits = result.model_fits or {}
    models = [
        name for name, f in fits.items()
        if f.get("orth_tuning_per_axis")
    ]
    if not models:
        return None

    fig, axes = plt.subplots(
        2, len(models),
        figsize=(5.0 * len(models), 8.0),
        squeeze=False,
        gridspec_kw={"height_ratios": [3, 1]},
    )
    cmap = plt.get_cmap("tab10")

    for col, name in enumerate(models):
        f = fits[name]
        color = cmap(col % 10)
        x = np.asarray(f["orth_tuning_x"], dtype=np.float64)
        per_axis = np.asarray(f["orth_tuning_per_axis"], dtype=np.float64)  # (n_axes, n_bins)
        mean_curve = np.asarray(f["orth_tuning_mean"], dtype=np.float64)
        per_axis_mod = np.asarray(f.get("orth_tuning_per_axis_modulation") or [],
                                   dtype=np.float64)

        fit_ok = f.get("orth_gauss_fit_ok")
        if fit_ok:
            denom = float(f["orth_gauss_a"]) + float(f["orth_gauss_c"])
        else:
            denom = 1.0
        if abs(denom) < 1e-9:
            denom = 1.0
        per_axis_n = per_axis / denom
        mean_n = mean_curve / denom

        # ---- Top: per-axis curves + mean + worst-modulated ------------
        ax = axes[0, col]
        # Faint per-axis lines.
        for k in range(per_axis_n.shape[0]):
            ax.plot(x, per_axis_n[k], color=color, alpha=0.06, lw=0.5)
        # Mean curve, bold.
        ax.plot(x, mean_n, color=color, lw=2.5, label=f"mean (n={per_axis.shape[0]})")
        # Top-N most modulated axes in red.
        if per_axis_mod.size:
            finite = np.where(np.isfinite(per_axis_mod))[0]
            if finite.size:
                order = finite[np.argsort(-per_axis_mod[finite])[:n_highlight]]
                for rank, k in enumerate(order):
                    lbl = f"worst axis (mod={per_axis_mod[k]:+.2f})" if rank == 0 else None
                    ax.plot(x, per_axis_n[k], color="crimson", lw=1.8,
                            alpha=0.9, label=lbl)

        ax.axhline(1.0, color="gray", lw=0.6, ls=":", alpha=0.6)
        ax.axhline(0.0, color="black", lw=0.5)
        fit_lim = f.get("orth_tuning_fit_z_range")
        if fit_lim is not None:
            ax.axvspan(-fit_lim, fit_lim, color="khaki", alpha=0.10, zorder=0)
        ax.set_xlabel("Projection (z)")
        ax.set_ylabel("Normalized response  [ y / (a+c) ]")
        ax.set_title(f"{name}", fontsize=11)
        ax.legend(fontsize=8, loc="best")

        # ---- Bottom: histogram of per-axis modulation depth ----------
        ax2 = axes[1, col]
        if per_axis_mod.size:
            finite_mod = per_axis_mod[np.isfinite(per_axis_mod)]
            if finite_mod.size:
                ax2.hist(finite_mod, bins=30, color=color, alpha=0.8,
                         edgecolor="black", linewidth=0.4)
                ax2.axvline(0.0, color="black", lw=0.7, ls="--",
                            label="flat (axis coding)")
                ax2.axvline(float(np.median(finite_mod)),
                            color="crimson", lw=1.0, ls="-",
                            label=f"median={np.median(finite_mod):.2f}")
                worst = float(np.max(finite_mod))
                ax2.axvline(worst, color="darkorange", lw=1.0, ls="-",
                            label=f"max={worst:.2f}")
        ax2.set_xlabel("Per-axis modulation depth  (max − min) / |max|")
        ax2.set_ylabel("axis count")
        ax2.legend(fontsize=7, loc="best")

    if title:
        fig.suptitle(title)
    fig.tight_layout()
    return fig


def plot_axis_coding_consolidated(
    result: AxisCodingResult,
    encoder: Optional[ComponentEncoder] = None,
    config: Optional[PlotPanelConfig] = None,
    title: Optional[str] = None,
    n_bins: int = 10,
    model_name: str = "shape",
    view: Optional[str] = None,   # deprecated alias for model_name
) -> plt.Figure:
    """
    All axis-coding panels in one figure (3 × 4 by default), driven by
    ``PlotPanelConfig``. Disabled panels become blank slots; the layout
    isn't rebuilt so panel positions stay consistent across runs.

    Slot layout (row, col):
      (0,0) preferred-axis tuning
      (0,1) principal-orth-axis tuning
      (0,2) 2D scatter (preferred vs orth1, color = response)
      (0,3) all-axes overlay (preferred + every orth, binned-mean curves)
      (1,0) loadings-per-axis heatmap
      (1,1) signed Spearman ρ per axis
      (1,2) variance fraction per axis
      (1,3) μ linear params (if any)
      (2,0..3) μ spherical (3D) and circular (dial) panels in order

    Legacy panels (top-|w| bars, slope-with-CI bar, |ρ| bar, in-axis
    pred-vs-actual) are off by default; flip ``show_*`` flags on the
    config to put them in place of one of the default panels.
    """
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401  (registers 3d projection)
    from matplotlib.gridspec import GridSpec

    cfg = config or PlotPanelConfig()
    name = view if view is not None else model_name
    av = _make_axis_view(result, name)
    has_shape_mu = bool(
        (result.model_fits or {}).get(name, {}).get("has_shape_mu", True)
    )

    actual = np.asarray(result.actual_responses, dtype=np.float64)
    axis_proj = av.axis_projections
    orth_proj = av.orthogonal_projections
    proj_orth_all = av.all_orthogonal_projections
    variances_orth = av.all_orthogonal_variances

    n_orth = proj_orth_all.shape[1] if proj_orth_all.ndim == 2 else 0
    n_axes = 1 + n_orth
    var_pref = float(np.var(axis_proj, ddof=1)) if axis_proj.size > 1 else 0.0
    var_total = var_pref + float(variances_orth.sum())
    proj_all = (
        np.column_stack([axis_proj, proj_orth_all])
        if n_orth > 0 else axis_proj.reshape(-1, 1)
    )
    variances_all = np.concatenate([[var_pref], variances_orth])
    var_frac_all = (
        variances_all / var_total if var_total > 1e-12
        else np.zeros_like(variances_all)
    )

    # Signed Spearman ρ per axis.
    rhos_signed = np.array([_signed_spearman(proj_all[:, k], actual)
                             for k in range(n_axes)])

    # μ panels: gather counts from encoder, if provided. Skipped when the
    # current model isn't shape-based (e.g. appearance-only).
    mu_panels: list[tuple[str, str]] = []  # (kind, name) where kind in {'linear', 'spherical', 'circular'}
    if (cfg.show_mu_panels and has_shape_mu
            and result.mu_decoded is not None and encoder is not None):
        if list(encoder.linear_params):
            mu_panels.append(("linear", "linear"))
        for sp in encoder.spherical_params:
            mu_panels.append(("spherical", sp))
        for cp in encoder.circular_params:
            mu_panels.append(("circular", cp))

    # Layout: 4 columns, default 3 rows. Anchored slots: rows 0 and 1 hold
    # the eight default tuning/loading/correlation/variance panels (column
    # (1,3) is reserved for the first μ panel — linear if present, else the
    # first spherical/circular). μ panels overflow into row 2+ as needed.
    n_cols = 4
    base_rows = 3
    n_mu_slots = len(mu_panels)
    n_legacy = sum(int(b) for b in [
        cfg.show_pred_vs_actual_in_axis_fig,
        cfg.show_top_features_w_bar,
        cfg.show_top_features_orth_bar,
        cfg.show_slope_per_axis_bar,
        cfg.show_abs_spearman_per_axis_bar,
    ])
    # 7 anchored default panels in rows 0–1 (cols 0..3 row 0 + cols 0..2 row 1)
    # leave (1,3) for first μ; remaining μ + legacy slots flow row 2 onwards.
    overflow_slots = max(0, n_mu_slots - 1) + n_legacy
    n_rows = max(base_rows, base_rows + (overflow_slots + n_cols - 1) // n_cols - 1)

    fig = plt.figure(figsize=(5.0 * n_cols, 4.2 * n_rows))
    gs = GridSpec(n_rows, n_cols, figure=fig)

    def _add(row, col, projection=None):
        return fig.add_subplot(gs[row, col], projection=projection)

    # ---------- Row 0 ----------
    if cfg.show_preferred_tuning:
        ax = _add(0, 0)
        _draw_tuning_curve(
            ax, axis_proj, actual, n_bins,
            xlabel="Projection onto preferred axis (z)",
            title="Preferred axis tuning",
        )
    if cfg.show_orth_tuning and n_orth > 0:
        ax = _add(0, 1)
        _draw_tuning_curve(
            ax, orth_proj, actual, n_bins,
            xlabel="Projection onto principal orth axis (z)",
            title="Principal orth axis tuning",
        )
    if cfg.show_2d_scatter and n_orth > 0:
        ax = _add(0, 2)
        sc = ax.scatter(
            axis_proj, orth_proj, c=actual,
            cmap="viridis", s=22, alpha=0.85, edgecolors="none",
        )
        ax.axhline(0, color="gray", lw=0.6, ls="--")
        ax.axvline(0, color="gray", lw=0.6, ls="--")
        ax.set_xlabel("Preferred axis projection")
        ax.set_ylabel("Principal orth projection")
        ax.set_title("Axis vs orth (color = response)")
        plt.colorbar(sc, ax=ax, label="Response")
    if cfg.show_all_axes_overlay:
        ax = _add(0, 3)
        cmap = plt.get_cmap("viridis")
        colors_overlay = ["forestgreen"] + [
            cmap(i / max(n_orth - 1, 1)) for i in range(n_orth)
        ]
        labels_overlay = ["preferred"] + [f"orth {k+1}" for k in range(n_orth)]
        for k in range(n_axes):
            col = proj_all[:, k]
            if col.std() < 1e-12:
                continue
            centers, means, sems = _binned_mean_sem(col, actual, n_bins)
            valid = ~np.isnan(means)
            if not valid.any():
                continue
            lw = 2.5 if k == 0 else 1.2
            alpha = 1.0 if k == 0 else 0.85
            ax.plot(centers[valid], means[valid],
                    color=colors_overlay[k], lw=lw, alpha=alpha,
                    label=labels_overlay[k])
        ax.axhline(actual.mean(), color="gray", lw=0.7, ls="--", alpha=0.6)
        ax.set_xlabel("Projection (z)")
        ax.set_ylabel("Mean response")
        ax.set_title("All axes overlay")
        ax.legend(fontsize=7, ncol=2, loc="best")

    # ---------- Row 1 ----------
    if cfg.show_loadings_heatmap:
        ax = _add(1, 0)
        feature_names = av.feature_names
        if av.w_in_feature_space is not None and av.w_in_feature_space.size:
            w_feat = av.w_in_feature_space
        else:
            w_feat = np.asarray(
                av.ridge_summary.get("weights") or [], dtype=np.float64
            )
        if (av.all_orthogonal_axes_in_feature_space is not None
                and av.all_orthogonal_axes_in_feature_space.size):
            orth_loadings = av.all_orthogonal_axes_in_feature_space
        elif av.all_orthogonal_axes is not None and av.all_orthogonal_axes.size:
            orth_loadings = av.all_orthogonal_axes
        else:
            orth_loadings = np.zeros((len(feature_names), 0))
        if w_feat.size and feature_names and len(feature_names) == w_feat.size:
            cols = [w_feat / max(float(np.linalg.norm(w_feat)), 1e-12)]
            for j in range(orth_loadings.shape[1]):
                v = orth_loadings[:, j]
                cols.append(v / max(float(np.linalg.norm(v)), 1e-12))
            M = np.column_stack(cols)
            col_labels = ["preferred"] + [
                f"orth {k+1}" for k in range(orth_loadings.shape[1])
            ]
            vmax = max(float(np.max(np.abs(M))), 1e-12) if M.size else 1.0
            im = ax.imshow(M, aspect="auto", cmap="RdBu_r",
                           vmin=-vmax, vmax=vmax, interpolation="nearest")
            ax.set_xticks(np.arange(len(col_labels)))
            ax.set_xticklabels(col_labels, rotation=45, ha="right", fontsize=7)
            ax.set_yticks(np.arange(len(feature_names)))
            ax.set_yticklabels(feature_names, fontsize=7)
            ax.set_title("Loadings per axis (unit-norm)")
            plt.colorbar(im, ax=ax, fraction=0.04, pad=0.02)
        else:
            ax.axis("off")

    if cfg.show_signed_r_per_axis:
        ax = _add(1, 1)
        x = np.arange(n_axes)
        labels_axes = ["pref"] + [f"o{k+1}" for k in range(n_orth)]
        bar_colors = ["forestgreen"] + ["steelblue"] * n_orth
        bars = ax.bar(x, rhos_signed, color=bar_colors)
        for b, v in zip(bars, rhos_signed):
            if not np.isnan(v):
                ax.text(b.get_x() + b.get_width() / 2, v,
                        f"{v:+.2f}", ha="center",
                        va="bottom" if v >= 0 else "top", fontsize=7)
        ax.axhline(0, color="black", lw=0.7)
        ax.set_xticks(x)
        ax.set_xticklabels(labels_axes, fontsize=8, rotation=45, ha="right")
        ax.set_ylabel("signed Spearman ρ")
        ax.set_title("Rank correlation per axis")

    if cfg.show_variance_per_axis:
        ax = _add(1, 2)
        x = np.arange(n_axes)
        labels_axes = ["pref"] + [f"o{k+1}" for k in range(n_orth)]
        bar_colors = ["forestgreen"] + ["steelblue"] * n_orth
        ax.bar(x, var_frac_all * 100.0, color=bar_colors)
        ax.set_xticks(x)
        ax.set_xticklabels(labels_axes, fontsize=8, rotation=45, ha="right")
        ax.set_ylabel("Variance fraction (%)")
        ax.set_title("Data variance per axis")

    # ---------- Row 1 col 3 + Row 2+: μ panels ----------
    # Walk slots in (row, col) order from (1,3) onwards.
    slot_order: list[tuple[int, int]] = [(1, 3)]
    for r in range(2, n_rows):
        for c in range(n_cols):
            slot_order.append((r, c))

    for i, (kind, name) in enumerate(mu_panels):
        if i >= len(slot_order):
            break
        r, c = slot_order[i]
        if kind == "linear":
            _draw_mu_linear(fig.add_subplot(gs[r, c]), result, encoder)
        elif kind == "spherical":
            _draw_mu_spherical(
                fig.add_subplot(gs[r, c], projection="3d"),
                result, encoder, name,
            )
        elif kind == "circular":
            _draw_mu_circular(fig.add_subplot(gs[r, c]), result, encoder, name)

    # ---------- Legacy / opt-in panels: place them on whichever default
    # slot they map to, only if the matching default panel is disabled.
    # Top-|w| bar replaces preferred tuning slot, etc. Simple approach:
    # add to any unused slot at the end (row 2+ tail).
    legacy_added: list[tuple[str, callable]] = []
    if cfg.show_pred_vs_actual_in_axis_fig:
        legacy_added.append(("pred_vs_actual", lambda ax: _draw_pred_vs_actual(ax, result)))
    if cfg.show_top_features_w_bar:
        legacy_added.append(("top_w", lambda ax: _draw_top_w_bar(ax, result)))
    if cfg.show_top_features_orth_bar:
        legacy_added.append(("top_orth", lambda ax: _draw_top_orth_bar(ax, result)))
    if cfg.show_slope_per_axis_bar:
        legacy_added.append(("slope", lambda ax: _draw_slope_per_axis(ax, result, n_axes)))
    if cfg.show_abs_spearman_per_axis_bar:
        legacy_added.append(("abs_rho", lambda ax: _draw_abs_rho_per_axis(ax, result, n_axes)))

    if legacy_added:
        # Place legacy panels in any slots after the μ panels.
        next_slot = 1 + len(mu_panels)
        for j, (_, drawer) in enumerate(legacy_added):
            slot_idx = next_slot + j
            if slot_idx >= len(slot_order):
                # Add a new row if we run out.
                break
            r, c = slot_order[slot_idx]
            drawer(fig.add_subplot(gs[r, c]))

    if title:
        fig.suptitle(title)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Helpers used by the consolidated plot
# ---------------------------------------------------------------------------

def _draw_mu_linear(ax, result: AxisCodingResult, encoder: ComponentEncoder):
    """Linear-params bar chart (one bar per prototype per param)."""
    linear = list(encoder.linear_params)
    if not linear or result.mu_decoded is None:
        ax.axis("off")
        return
    if result.mus_decoded is not None and result.mus_in_unscaled_space is not None:
        all_decoded = list(result.mus_decoded)
        amps = list(result.prototype_amplitudes or [1.0] * len(all_decoded))
    else:
        all_decoded = [result.mu_decoded]
        amps = [1.0]
    n_proto = len(all_decoded)
    cmap = plt.get_cmap("tab10")
    proto_colors = [cmap(k % 10) for k in range(n_proto)]
    amp_total = float(sum(amps)) or 1.0
    n = len(linear)
    bar_w = 0.8 / max(n_proto, 1)
    for k in range(n_proto):
        vals = [all_decoded[k].get(p, np.nan) for p in linear]
        x = np.arange(n) + (k - (n_proto - 1) / 2) * bar_w
        ax.bar(x, vals, width=bar_w * 0.95, color=proto_colors[k],
               label=f"μ{k+1} ({amps[k]/amp_total:.0%})")
    ax.set_xticks(np.arange(n))
    ax.set_xticklabels(linear, rotation=30, ha="right", fontsize=7)
    ax.axhline(0, color="black", lw=0.7)
    ax.set_ylabel("Value (raw units)", fontsize=8)
    ax.set_title("μ — linear params", fontsize=9)
    if n_proto > 1:
        ax.legend(fontsize=6, loc="best")


def _draw_mu_spherical(ax3d, result: AxisCodingResult, encoder: ComponentEncoder, sp: str):
    """3D arrow on a small sphere for a single spherical (θ,φ) param."""
    if result.mu_decoded is None:
        ax3d.axis("off")
        return
    if result.mus_decoded is not None:
        all_decoded = list(result.mus_decoded)
        amps = list(result.prototype_amplitudes or [1.0] * len(all_decoded))
    else:
        all_decoded = [result.mu_decoded]
        amps = [1.0]
    cmap = plt.get_cmap("tab10")
    n_proto = len(all_decoded)
    amps_arr = np.asarray(amps, dtype=np.float64)
    amp_max = float(amps_arr.max()) if amps_arr.size else 1.0
    amp_rel = amps_arr / max(amp_max, 1e-12)
    arrow_lws = 1.5 + 3.0 * amp_rel

    # Sphere wireframe (remapped: mpl_y = depth = real_z = cos φ).
    sph_u = np.linspace(0, 2 * np.pi, 24)
    sph_v = np.linspace(0, np.pi, 12)
    sph_rx = np.outer(np.cos(sph_u), np.sin(sph_v))
    sph_ry = np.outer(np.sin(sph_u), np.sin(sph_v))
    sph_rz = np.outer(np.ones_like(sph_u), np.cos(sph_v))
    ax3d.plot_wireframe(sph_rx, sph_rz, sph_ry,
                        color="lightgray", lw=0.3, alpha=0.4)
    # Reference axes in mpl coords (mpl_x=real_x, mpl_y=depth, mpl_z=real_y).
    ax3d.plot([-1.1, 1.1], [0, 0], [0, 0], color="gray", lw=0.6, alpha=0.5)   # X
    ax3d.plot([0, 0], [0, 0], [-1.1, 1.1], color="gray", lw=0.6, alpha=0.5)   # Y (up)
    # Depth axis: short dashes into/out of screen.
    ax3d.plot([0, 0], [-0.5, 0.5], [0, 0], color="gray", lw=0.6, alpha=0.4, ls=":")
    ax3d.text( 1.2,  0.0,  0.0, "+X (θ=0)",   fontsize=6, color="dimgray")
    ax3d.text(-1.5,  0.0,  0.0, "−X (θ=π)",  fontsize=6, color="dimgray")
    ax3d.text( 0.0,  0.0,  1.2, "+Y (θ=π/2)",fontsize=6, color="dimgray")
    ax3d.text( 0.0,  0.0, -1.35,"−Y",         fontsize=6, color="dimgray")
    # Depth tip markers (dot=away/+Z, ring=toward/-Z) on the depth axis.
    ax3d.scatter([0], [ 0.55], [0], color="#3b4cc0", s=30, edgecolors="black",
                 linewidths=0.5, zorder=4)
    ax3d.scatter([0], [-0.55], [0], facecolors="none", edgecolors="#b40426",
                 s=40, linewidths=1.0, zorder=4)
    ax3d.text(0,  0.65, 0, "+Z away (φ=0)",  fontsize=6, color="#3b4cc0")
    ax3d.text(0, -0.65, 0, "−Z toward (φ=π)", fontsize=6, color="#b40426")
    depth_cmap = plt.cm.coolwarm
    for k in range(n_proto):
        d = all_decoded[k]
        theta = d.get(f"{sp}.theta")
        phi_val = d.get(f"{sp}.phi")
        if theta is None or phi_val is None:
            continue
        sin_phi = float(np.sin(phi_val))
        rx = sin_phi * float(np.cos(theta))
        ry = sin_phi * float(np.sin(theta))
        rz = float(np.cos(phi_val))
        # mpl(x,y,z) = (real_x, real_z, real_y)
        mx, my_d, mz = rx, rz, ry
        n_seg = 18
        ts = np.linspace(0, 1, n_seg + 1)
        for i in range(n_seg):
            t0, t1 = ts[i], ts[i + 1]
            depth_mid = (t0 + t1) / 2 * my_d
            seg_color = depth_cmap((depth_mid + 1.0) / 2.0)
            ax3d.plot([t0 * mx, t1 * mx], [t0 * my_d, t1 * my_d],
                      [t0 * mz, t1 * mz], color=seg_color, lw=arrow_lws[k])
        tip_color = depth_cmap((my_d + 1.0) / 2.0)
        ax3d.scatter([mx], [my_d], [mz], color=tip_color,
                     s=60, edgecolors="black", linewidths=0.7, zorder=5)
        ax3d.text(mx * 1.15, my_d * 1.15, mz * 1.15,
                  f"μ{k+1}", fontsize=6, ha="center", va="center")
    ax3d.set_xlim(-1.1, 1.1)
    ax3d.set_ylim(-1.1, 1.1)
    ax3d.set_zlim(-1.1, 1.1)
    ax3d.set_xticks([-1, 0, 1])
    ax3d.set_yticks([-1, 0, 1])
    ax3d.set_zticks([-1, 0, 1])
    ax3d.set_xlabel("X →right", fontsize=6, labelpad=1)
    ax3d.set_zlabel("Y →up", fontsize=6, labelpad=1)
    ax3d.set_ylabel("Z depth\n(· away / ○ toward)", fontsize=5, labelpad=2)
    ax3d.set_title(
        f"μ — {sp}\n"
        r"$\bf{blue}$=away (φ=0)  $\bf{red}$=toward (φ=π)",
        fontsize=8,
    )
    ax3d.view_init(elev=0, azim=-90)
    try:
        ax3d.set_box_aspect((1, 1, 1))
    except AttributeError:
        pass


def _draw_mu_circular(ax, result: AxisCodingResult, encoder: ComponentEncoder, cp: str):
    """Dial showing the μ angle on the unit circle."""
    if result.mu_decoded is None:
        ax.axis("off")
        return
    if result.mus_decoded is not None:
        all_decoded = list(result.mus_decoded)
        amps = list(result.prototype_amplitudes or [1.0] * len(all_decoded))
    else:
        all_decoded = [result.mu_decoded]
        amps = [1.0]
    cmap = plt.get_cmap("tab10")
    amps_arr = np.asarray(amps, dtype=np.float64)
    amp_max = float(amps_arr.max()) if amps_arr.size else 1.0
    amp_rel = amps_arr / max(amp_max, 1e-12)
    lws = 1.5 + 3.0 * amp_rel

    ax.set_xlim(-1.3, 1.3)
    ax.set_ylim(-1.3, 1.3)
    ax.set_aspect("equal")
    circ_t = np.linspace(0, 2 * np.pi, 100)
    ax.plot(np.cos(circ_t), np.sin(circ_t), color="lightgray", lw=0.6)
    ax.axhline(0, color="gray", lw=0.4)
    ax.axvline(0, color="gray", lw=0.4)
    for k, d in enumerate(all_decoded):
        ang = d.get(cp)
        if ang is None:
            continue
        x = np.cos(ang)
        y = np.sin(ang)
        ax.annotate("", xy=(x, y), xytext=(0, 0),
                    arrowprops=dict(arrowstyle="->",
                                    color=cmap(k % 10), lw=lws[k]))
        ax.scatter([x], [y], color=cmap(k % 10), s=40,
                   edgecolors="black", linewidths=0.6, zorder=5,
                   label=f"μ{k+1}: {np.degrees(ang):+.0f}°")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(f"μ — {cp}", fontsize=9)
    ax.legend(fontsize=6, loc="lower right")


def _draw_pred_vs_actual(ax, result: AxisCodingResult):
    actual = np.asarray(result.actual_responses)
    pred = np.asarray(result.predicted_responses)
    ax.scatter(actual, pred, s=12, alpha=0.6)
    lims = [float(min(actual.min(), pred.min())),
            float(max(actual.max(), pred.max()))]
    ax.plot(lims, lims, "k--", lw=1)
    ax.set_xlabel("Actual")
    ax.set_ylabel("Predicted")
    cv = result.ridge_summary.get("cv_r2_mean")
    ax.set_title(f"Pred vs actual\nCV R² = {cv if cv is None else f'{cv:+.3f}'}")


def _draw_top_w_bar(ax, result: AxisCodingResult):
    if result.w_in_feature_space is not None:
        w = np.asarray(result.w_in_feature_space, dtype=np.float64)
    else:
        w = np.asarray(result.ridge_summary.get("weights") or [], dtype=np.float64)
    names = result.feature_names or []
    if not (w.size and names and len(names) == w.size):
        ax.axis("off")
        return
    order = np.argsort(-np.abs(w))[:10]
    y = np.arange(len(order))
    ax.barh(y, w[order], color="steelblue")
    ax.set_yticks(y)
    ax.set_yticklabels([names[i] for i in order], fontsize=7)
    ax.invert_yaxis()
    ax.axvline(0, color="black", lw=0.8)
    ax.set_title("Top |w|  (preferred axis)")


def _draw_top_orth_bar(ax, result: AxisCodingResult):
    if result.orthogonal_axis_in_feature_space is not None:
        orth = np.asarray(result.orthogonal_axis_in_feature_space, dtype=np.float64)
    elif result.orthogonal_axis is not None:
        orth = np.asarray(result.orthogonal_axis, dtype=np.float64)
    else:
        orth = np.array([])
    names = result.feature_names or []
    if not (orth.size and names and len(names) == orth.size):
        ax.axis("off")
        return
    order = np.argsort(-np.abs(orth))[:10]
    y = np.arange(len(order))
    ax.barh(y, orth[order], color="darkorange")
    ax.set_yticks(y)
    ax.set_yticklabels([names[i] for i in order], fontsize=7)
    ax.invert_yaxis()
    ax.axvline(0, color="black", lw=0.8)
    ax.set_title("Top |orth|  (principal orth axis)")


def _draw_slope_per_axis(ax, result: AxisCodingResult, n_axes: int):
    actual = np.asarray(result.actual_responses, dtype=np.float64)
    axis_proj = compute_axis_projections(result)
    proj_orth = (
        np.asarray(result.all_orthogonal_projections, dtype=np.float64)
        if result.all_orthogonal_projections is not None
        else np.zeros((axis_proj.size, 0))
    )
    proj_all = np.column_stack([axis_proj, proj_orth]) if proj_orth.size else axis_proj.reshape(-1, 1)
    slopes = np.zeros(n_axes); lo = np.zeros(n_axes); hi = np.zeros(n_axes)
    for k in range(n_axes):
        col = proj_all[:, k]
        if col.std() > 1e-12:
            s, _, l, h = _theilsen_fit(col, actual)
            slopes[k], lo[k], hi[k] = s, l, h
    x = np.arange(n_axes)
    labels = ["pref"] + [f"o{k+1}" for k in range(n_axes - 1)]
    colors = ["forestgreen"] + ["steelblue"] * (n_axes - 1)
    yerr = np.vstack([np.maximum(slopes - lo, 0), np.maximum(hi - slopes, 0)])
    ax.bar(x, slopes, color=colors, yerr=yerr, capsize=3, ecolor="black",
           error_kw={"lw": 0.7})
    ax.axhline(0, color="black", lw=0.7)
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=7, rotation=45, ha="right")
    ax.set_ylabel("Slope (Theil–Sen)"); ax.set_title("Slope per axis (95% CI)")


def _draw_abs_rho_per_axis(ax, result: AxisCodingResult, n_axes: int):
    actual = np.asarray(result.actual_responses, dtype=np.float64)
    axis_proj = compute_axis_projections(result)
    proj_orth = (
        np.asarray(result.all_orthogonal_projections, dtype=np.float64)
        if result.all_orthogonal_projections is not None
        else np.zeros((axis_proj.size, 0))
    )
    proj_all = np.column_stack([axis_proj, proj_orth]) if proj_orth.size else axis_proj.reshape(-1, 1)
    rhos = np.zeros(n_axes)
    for k in range(n_axes):
        col = proj_all[:, k]
        if col.std() > 1e-12:
            r, _ = spearmanr(col, actual)
            rhos[k] = abs(r) if r is not None else 0.0
    x = np.arange(n_axes)
    labels = ["pref"] + [f"o{k+1}" for k in range(n_axes - 1)]
    colors = ["forestgreen"] + ["steelblue"] * (n_axes - 1)
    ax.bar(x, rhos, color=colors)
    ax.axhline(0.1, color="gray", lw=1, ls="--")
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=7, rotation=45, ha="right")
    ax.set_ylabel("|Spearman ρ|"); ax.set_title("|ρ| per axis")


def plot_axes_stimuli(
    result: AxisCodingResult,
    n_per_axis: int = 7,
    border_width: int = 50,
    color_mode: str = "intensity",
    title: Optional[str] = None,
) -> Optional[plt.Figure]:
    """
    Show stimuli sampled uniformly along each axis (preferred + all orthogonal).

    For each axis, draw ``n_per_axis`` evenly-spaced bin centers from the most
    negative to the most positive projection value; for each bin center, render
    the thumbnail of the stimulus whose projection is closest to that center.
    Each thumbnail gets a response-colored border via the same helper used by
    plot_top_n (``GroupedStimuliPlotter_matplotlib._add_colored_border``):
    border intensity = response, normalized over the dataset's [min, max].

    One row per axis (preferred first, then orthogonal axes by data variance).
    Requires ``result.thumbnail_paths`` to be populated.
    """
    if not result.thumbnail_paths or all(p is None for p in result.thumbnail_paths):
        return None

    proj_pref = compute_axis_projections(result)
    proj_orth = (
        np.asarray(result.all_orthogonal_projections, dtype=np.float64)
        if result.all_orthogonal_projections is not None
        else np.zeros((len(proj_pref), 0))
    )

    n_orth = proj_orth.shape[1] if proj_orth.ndim == 2 else 0
    n_axes = 1 + n_orth
    paths = result.thumbnail_paths

    proj_all = [proj_pref] + [proj_orth[:, k] for k in range(n_orth)]
    labels = ["preferred"] + [f"orth {k+1}" for k in range(n_orth)]

    actual = np.asarray(result.actual_responses, dtype=np.float64)
    min_val = float(np.nanmin(actual)) if actual.size else 0.0
    max_val = float(np.nanmax(actual)) if actual.size else 1.0
    # Reuse plot_top_n's border code by instantiating the helper with our
    # border_width / color_mode and calling its _add_colored_border method.
    border_helper = GroupedStimuliPlotter_matplotlib(
        border_width=border_width,
        color_mode=color_mode,
    )

    fig, axes = plt.subplots(
        n_axes, n_per_axis,
        figsize=(1.8 * n_per_axis, 2.0 * n_axes),
        squeeze=False,
    )

    for row, (proj, label) in enumerate(zip(proj_all, labels)):
        proj = np.asarray(proj, dtype=np.float64)
        if proj.size == 0 or proj.std() < 1e-12:
            for col in range(n_per_axis):
                axes[row, col].axis("off")
            axes[row, 0].set_ylabel(label, fontsize=10, rotation=0,
                                     ha="right", va="center", labelpad=20)
            continue

        bin_centers = np.linspace(proj.min(), proj.max(), n_per_axis)
        for col, bc in enumerate(bin_centers):
            ax = axes[row, col]
            ax.set_xticks([])
            ax.set_yticks([])
            for spine in ax.spines.values():
                spine.set_visible(False)

            idx = int(np.argmin(np.abs(proj - bc)))
            path = paths[idx] if idx < len(paths) else None
            shown = False
            if path and isinstance(path, str) and os.path.exists(path):
                try:
                    img = Image.open(path)
                    img_with_border = border_helper._add_colored_border(
                        img, float(actual[idx]), min_val, max_val,
                    )
                    ax.imshow(np.asarray(img_with_border))
                    shown = True
                except Exception:
                    pass
            if not shown:
                ax.text(0.5, 0.5, "?", ha="center", va="center",
                        transform=ax.transAxes, fontsize=14, color="gray")
            ax.set_xlabel(f"{proj[idx]:+.2g}", fontsize=7)

        axes[row, 0].set_ylabel(label, fontsize=10, rotation=0,
                                 ha="right", va="center", labelpad=20)

    if title:
        fig.suptitle(title, fontsize=11)
    fig.tight_layout()
    return fig


def plot_mu_decoded(
    result: AxisCodingResult,
    encoder: ComponentEncoder,
    title: Optional[str] = None,
) -> Optional[plt.Figure]:
    """
    Visualize the selector's chosen μ ("the preferred component template") in
    interpretable parameter space.

    Layout (one panel each, in this order):
      - Linear params: grouped bar chart in raw units.
      - Spherical pairs (θ, φ): 3D arrow from origin to the unit-vector pose,
        on a faint reference sphere.  Convention:
            x = sin φ cos θ   (θ=0 along +X,  θ=π/2 along +Y)
            y = sin φ sin θ
            z = cos φ         (φ=0 → +Z, away from viewer; φ=π → -Z, towards)
        +X / +Y / +Z reference axes are drawn so direction is unambiguous.
      - Circular params: angle on a 2D dial at unit radius.

    For multi-prototype selectors (``mus_decoded`` populated), every prototype
    is overlaid in a distinct color with marker / arrow line-width scaled by
    amplitude α_k.
    """
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401  (registers 3d projection)

    if result.mu_decoded is None:
        return None

    # Collect all prototypes to plot (single-prototype selectors → one entry).
    all_decoded: list[dict] = []
    amplitudes: list[float] = []
    if result.mus_decoded is not None and result.mus_in_unscaled_space is not None:
        for k in range(len(result.mus_decoded)):
            all_decoded.append(result.mus_decoded[k])
        if result.prototype_amplitudes is not None:
            amplitudes = list(result.prototype_amplitudes)
        else:
            amplitudes = [1.0] * len(all_decoded)
    else:
        all_decoded.append(result.mu_decoded)
        amplitudes = [1.0]

    n_proto = len(all_decoded)
    cmap = plt.get_cmap("tab10")
    proto_colors = [cmap(k % 10) for k in range(n_proto)]

    linear = list(encoder.linear_params)
    circular = list(encoder.circular_params)
    spherical = list(encoder.spherical_params)

    n_lin_panels = 1 if linear else 0
    n_panels = n_lin_panels + len(spherical) + len(circular)
    if n_panels == 0:
        return None

    # Mixed 2D/3D panels — must use add_subplot per panel rather than plt.subplots.
    fig = plt.figure(figsize=(4.5 * n_panels, 4.2))
    panel = 1  # 1-indexed for add_subplot

    # Normalize amplitudes for display (sum-to-1 so legend shows % share)
    amps_arr = np.asarray(amplitudes, dtype=np.float64)
    amp_total = float(amps_arr.sum()) if amps_arr.size else 1.0
    amp_norm = amps_arr / max(amp_total, 1e-12)  # fraction of total (sums to 1)
    amp_max = float(amps_arr.max()) if amps_arr.size else 1.0
    amp_rel = amps_arr / max(amp_max, 1e-12)     # relative to largest (for sizing)
    sizes = 60.0 + 200.0 * amp_rel
    arrow_lws = 1.5 + 3.5 * amp_rel

    # Linear params: grouped bar chart, one bar per prototype per param.
    if linear:
        ax = fig.add_subplot(1, n_panels, panel)
        n = len(linear)
        bar_w = 0.8 / max(n_proto, 1)
        for k in range(n_proto):
            vals = [all_decoded[k].get(p, np.nan) for p in linear]
            x = np.arange(n) + (k - (n_proto - 1) / 2) * bar_w
            ax.bar(
                x, vals, width=bar_w * 0.95,
                color=proto_colors[k],
                label=f"μ{k+1} ({amp_norm[k]:.0%})",
            )
        ax.set_xticks(np.arange(n))
        ax.set_xticklabels(linear, rotation=30, ha="right", fontsize=8)
        ax.axhline(0, color="black", lw=0.7)
        ax.set_ylabel("Value (raw units)")
        ax.set_title("Linear params")
        if n_proto > 1:
            ax.legend(fontsize=7, loc="best")
        panel += 1

    # Spherical params: 3D arrow on a front-on view.
    #
    # Coordinate remapping so the plot matches intuition:
    #   mpl_x  = real_x = sin φ cos θ   →  left/right on screen
    #   mpl_z  = real_y = sin φ sin θ   →  up/down on screen  (mpl treats Z as "up")
    #   mpl_y  = real_z = cos φ         →  depth (in/out of screen) at azim=-90
    #
    # With view_init(elev=0, azim=-90) we look from the -Y direction, so:
    #   +mpl_y (= real_z, φ=0) goes INTO the screen  → "away from viewer"  → blue
    #   -mpl_y (= real_z, φ=π) comes OUT of the screen → "toward viewer"   → red
    #
    # Arrow color encodes depth via coolwarm gradient (origin=neutral, tip=depth color).
    # For multiple prototypes the linestyle varies (solid / dashed) and tips are labeled.

    depth_cmap = plt.cm.coolwarm

    def _gradient_arrow_3d(ax3d, tx, ty_depth, tz, lw, n_seg=30, lstyle="-"):
        """
        Draw a depth-gradient 3D arrow from origin to (tx, ty_depth, tz).

        ty_depth is the "into-the-screen" mpl_y axis = real_z = cos φ ∈ [-1, 1].
        Color transitions from neutral gray at origin to the tip's depth color.
        """
        ts = np.linspace(0, 1, n_seg + 1)
        for i in range(n_seg):
            t0, t1 = ts[i], ts[i + 1]
            depth_mid = (t0 + t1) / 2 * ty_depth  # interpolated depth at segment midpoint
            seg_color = depth_cmap((depth_mid + 1.0) / 2.0)
            ax3d.plot(
                [t0 * tx, t1 * tx],
                [t0 * ty_depth, t1 * ty_depth],
                [t0 * tz, t1 * tz],
                lstyle, color=seg_color, lw=lw, solid_capstyle="round",
            )
        # Arrowhead: large dot at tip, colored by full tip depth.
        tip_color = depth_cmap((ty_depth + 1.0) / 2.0)
        ax3d.scatter(
            [tx], [ty_depth], [tz],
            color=tip_color, s=80,
            edgecolors="black", linewidths=0.8, zorder=6,
        )

    # Build remapped sphere wireframe: mpl(x, y, z) = real(x, z, y)
    sph_u = np.linspace(0, 2 * np.pi, 28)
    sph_v = np.linspace(0, np.pi, 14)
    sph_rx = np.outer(np.cos(sph_u), np.sin(sph_v))   # real_x
    sph_ry = np.outer(np.sin(sph_u), np.sin(sph_v))   # real_y
    sph_rz = np.outer(np.ones_like(sph_u), np.cos(sph_v))  # real_z (depth)
    # mpl: x=real_x, y=real_z(depth), z=real_y(up)
    sph_mx, sph_my, sph_mz = sph_rx, sph_rz, sph_ry

    lstyles = ["-", "--", ":", "-."]

    for sp in spherical:
        ax = fig.add_subplot(1, n_panels, panel, projection="3d")

        ax.plot_wireframe(
            sph_mx, sph_my, sph_mz,
            color="lightgray", lw=0.3, alpha=0.40,
        )

        # Reference axes in mpl coords (mpl_x=real_x, mpl_y=depth, mpl_z=real_y).
        ax.plot([-1.1, 1.1], [0, 0], [0, 0], color="gray", lw=0.7, alpha=0.5)  # X
        ax.plot([0, 0], [0, 0], [-1.1, 1.1], color="gray", lw=0.7, alpha=0.5)  # Y (up)
        # Depth axis: short dashes into/out of screen.
        ax.plot([0, 0], [-0.5, 0.5], [0, 0], color="gray", lw=0.7, alpha=0.4, ls=":")
        ax.text( 1.2,  0.0, 0.0, "+X (θ=0)",    fontsize=7, color="dimgray")
        ax.text(-1.5,  0.0, 0.0, "−X (θ=π)",   fontsize=7, color="dimgray")
        ax.text( 0.0,  0.0, 1.2, "+Y (θ=π/2)", fontsize=7, color="dimgray")
        ax.text( 0.0,  0.0,-1.35,"−Y",          fontsize=7, color="dimgray")

        for k in range(n_proto):
            d = all_decoded[k]
            theta = d.get(f"{sp}.theta")
            phi_val = d.get(f"{sp}.phi")
            if theta is None or phi_val is None:
                continue
            sin_phi = float(np.sin(phi_val))
            real_x = sin_phi * float(np.cos(theta))
            real_y = sin_phi * float(np.sin(theta))
            real_z = float(np.cos(phi_val))           # depth: +1=away(blue), -1=toward(red)

            # Remap to mpl axes.
            mx, my_depth, mz = real_x, real_z, real_y

            _gradient_arrow_3d(
                ax, mx, my_depth, mz,
                lw=arrow_lws[k],
                lstyle=lstyles[k % len(lstyles)],
            )

            # Tip label (μ index + angles).
            ax.text(
                mx * 1.12, my_depth * 1.12, mz * 1.12,
                f"μ{k+1}\nθ={np.degrees(theta):+.0f}°\nφ={np.degrees(phi_val):.0f}°",
                fontsize=7, color="black",
                ha="center", va="center",
            )

        ax.set_xlim(-1.1, 1.1)
        ax.set_ylim(-1.1, 1.1)
        ax.set_zlim(-1.1, 1.1)
        ax.set_xticks([-1, 0, 1])
        ax.set_yticks([-1, 0, 1])
        ax.set_zticks([-1, 0, 1])
        ax.set_xlabel("X →right", fontsize=7, labelpad=2)
        ax.set_zlabel("Y →up", fontsize=7, labelpad=2)
        ax.set_ylabel("Z depth\n(· away / ○ toward)", fontsize=6, labelpad=4)
        ax.set_title(
            f"{sp}\n"
            r"$\bf{blue}$=away (φ=0)  $\bf{red}$=toward (φ=π)",
            fontsize=8,
        )
        ax.view_init(elev=0, azim=-90)
        try:
            ax.set_box_aspect((1, 1, 1))
        except AttributeError:
            pass
        panel += 1

    # Depth colorbar: small separate axes to show the blue→red scale.
    # Only added once, after the last spherical panel, if there were any.
    if spherical:
        sm = plt.cm.ScalarMappable(cmap=depth_cmap, norm=plt.Normalize(-1, 1))
        sm.set_array([])
        cbar_ax = fig.add_axes([0.92, 0.15, 0.015, 0.7])
        cb = fig.colorbar(sm, cax=cbar_ax)
        cb.set_label("Z depth  (cos φ)", fontsize=8)
        cb.set_ticks([-1, 0, 1])
        cb.set_ticklabels(["−1\n(φ=π\ntoward)", "0\n(φ=π/2)", "+1\n(φ=0\naway)"],
                          fontsize=7)

    # Circular params: dial.
    for cp in circular:
        ax = fig.add_subplot(1, n_panels, panel)
        ax.set_xlim(-1.3, 1.3)
        ax.set_ylim(-1.3, 1.3)
        ax.set_aspect("equal")
        # Reference circle.
        circ_t = np.linspace(0, 2 * np.pi, 100)
        ax.plot(np.cos(circ_t), np.sin(circ_t), color="lightgray", lw=0.6)
        ax.axhline(0, color="gray", lw=0.4)
        ax.axvline(0, color="gray", lw=0.4)
        ax.text(1.15, 0, "0°", fontsize=7, color="gray", va="center")
        ax.text(0, 1.15, "90°", fontsize=7, color="gray", ha="center")
        for k in range(n_proto):
            d = all_decoded[k]
            ang = d.get(cp)
            if ang is None:
                continue
            x = np.cos(ang)
            y = np.sin(ang)
            ax.annotate(
                "", xy=(x, y), xytext=(0, 0),
                arrowprops=dict(
                    arrowstyle="->",
                    color=proto_colors[k],
                    lw=arrow_lws[k],
                ),
            )
            ax.scatter([x], [y], s=sizes[k] * 0.5, color=proto_colors[k],
                       edgecolors="black", linewidths=0.8, zorder=5,
                       label=f"μ{k+1}: {np.degrees(ang):+.0f}°")
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title(cp)
        if n_proto >= 1:
            ax.legend(fontsize=7, loc="lower right")
        panel += 1

    if title:
        fig.suptitle(title)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class AxisCodingAnalysis(PlotTopNAnalysis):
    """
    Orchestrates per-component-type axis coding analysis for one channel
    (or list of channels, or the GA scalar).

    Implementation notes:
      - Reuses PlotTopNAnalysis for compile / compile_and_export / import_data.
      - Trial filter mirrors run_rwa.py except RegimeScore is preserved (regime
        zero parents kept on purpose for stimulus diversity).
      - Each (component_type, strategy) pair becomes a pipeline branch so
        adding a new selector = adding one branch, no orchestrator edits.
    """

    # logging_path = context.logging_path

    def __init__(
        self,
        component_types: Optional[list[str]] = None,
        strategies: Optional[list[AxisCodingStrategy]] = None,
        encoders: Optional[dict[str, ComponentEncoder]] = None,
        show_plots: bool = True,
        outlier_sigma: float = 0.0,
        outlier_min_trials: int = 3,
        rf_filter: Optional[ReceptiveFieldFilter] = None,
        n_stimuli_per_axis: int = 12,
        panel_config: Optional["PlotPanelConfig"] = None,
        axis_models: Optional[list[ModelSpec]] = None,
    ):
        super().__init__()
        self.component_types = component_types or [
            "Shaft", "Termination", "Junction"
        ]
        self.strategies = strategies or [default_strategy()]
        self.encoders = encoders if encoders is not None else make_default_encoders()
        self.show_plots = show_plots
        self.outlier_sigma = outlier_sigma
        self.outlier_min_trials = outlier_min_trials
        self.rf_filter = rf_filter
        self.n_stimuli_per_axis = n_stimuli_per_axis
        self.panel_config = panel_config or PlotPanelConfig()
        # Models drive both fit_axis_coding and the per-model figures emitted
        # in analyze(). Defaults to [shape, appearance, shape+appearance].
        self.axis_models = (
            list(axis_models) if axis_models is not None else default_axis_models()
        )

    # ------------------------------------------------------------------
    # Analysis API
    # ------------------------------------------------------------------

    def analyze(self, channel, compiled_data: pd.DataFrame = None):
        self.save_path = f"{self.save_path}/axis_coding"
        os.makedirs(f"{self.save_path}", exist_ok=True)
        compiled_data = self._prepare_dataframe(compiled_data)
        if self.rf_filter is not None:
            if self.rf_filter.save_dir is None:
                self.rf_filter.save_dir = self.save_path
            compiled_data = self.rf_filter.fit_and_filter(
                compiled_data,
                channel=channel,
                spike_rates_col=self.spike_rates_col,
            )
        if self.outlier_sigma > 0:
            compiled_data = remove_trial_outliers(
                compiled_data,
                channel=channel,
                spike_rates_col=self.spike_rates_col,
                n_sigma=self.outlier_sigma,
                min_trials=self.outlier_min_trials,
            )
        save_dir = self.save_path

        # Re-instantiate encoders per analyze call so the StandardScaler is fit
        # fresh on the data we are about to process.
        encoders_for_run = {
            t: ComponentEncoder(
                linear_params=list(self.encoders[t].linear_params),
                circular_params=list(self.encoders[t].circular_params),
                spherical_params=list(self.encoders[t].spherical_params),
            )
            for t in self.component_types
        }

        results: dict[str, dict[str, AxisCodingResult]] = {}

        for component_type in self.component_types:
            results[component_type] = {}
            for strategy in self.strategies:
                print(
                    f"\n[axis_coding] channel={channel} "
                    f"type={component_type} strategy={strategy.label}"
                )
                result = fit_axis_coding(
                    df=compiled_data,
                    component_type=component_type,
                    encoder=encoders_for_run[component_type],
                    selector=strategy.selector_factory(),
                    channel=channel,
                    spike_rates_col=self.spike_rates_col,
                    strategy_label=strategy.label,
                    save_dir=save_dir,
                    ridge_factory=strategy.ridge_factory,
                    n_pcs=strategy.n_pcs,
                    axis_models=self.axis_models,
                )
                results[component_type][strategy.label] = result

                # Prototype amplitudes for multi-prototype selectors.
                if result.prototype_amplitudes is not None:
                    norm_amps = result.selector_summary.get("amplitudes_normalized")
                    gate_usage = result.selector_summary.get("mean_gate_usage")
                    collapse = result.selector_summary.get("collapse_ratio")
                    if norm_amps is not None:
                        amps_str = ", ".join(
                            f"μ{k+1}: {a:.1%}" for k, a in enumerate(norm_amps)
                        )
                    else:
                        amps_str = ", ".join(
                            f"α{k+1}={a:.3g}"
                            for k, a in enumerate(result.prototype_amplitudes)
                        )
                    n_active = result.selector_summary.get("n_active_prototypes")
                    sep = result.selector_summary.get("prototype_separation")
                    sep_str = f"  sep={sep:.3g}" if sep is not None else ""
                    collapse_str = f"  collapse={collapse:.2g}" if collapse is not None else ""
                    gate_str = ""
                    if gate_usage is not None:
                        gate_str = "  gates=[" + ", ".join(f"{g:.2f}" for g in gate_usage) + "]"
                    print(
                        f"  prototypes ({n_active} active): {amps_str}"
                        f"{collapse_str}{sep_str}{gate_str}"
                    )

                cv_r2 = result.ridge_summary.get("cv_r2_mean")
                cv_r2_std = result.ridge_summary.get("cv_r2_std")
                alpha = result.ridge_summary.get("alpha")
                nc = result.noise_ceiling
                frac_str = ""
                if nc is not None and cv_r2 is not None and not np.isnan(cv_r2) and nc > 0:
                    frac_str = f"  ({cv_r2/nc:.0%} of NC={_fmt(nc)})"
                elif nc is not None:
                    frac_str = f"  NC={_fmt(nc)}"
                print(
                    f"  n_stim={result.n_stim}  n_features={result.n_features}  "
                    f"alpha={alpha if alpha is None else f'{alpha:.4g}'}  "
                    f"cv_r2={_fmt(cv_r2)} ± {_fmt(cv_r2_std)}{frac_str}"
                )

                # Top-10 features by |orthogonal-axis loading|.
                if (
                    result.orthogonal_axis is not None
                    and result.feature_names
                ):
                    orth_arr = np.asarray(result.orthogonal_axis)
                    if np.any(orth_arr):
                        top_orth = np.argsort(-np.abs(orth_arr))[:10]
                        print("  principal orthogonal axis loadings:")
                        for i in top_orth:
                            print(
                                f"    {result.feature_names[i]:35s}  "
                                f"{orth_arr[i]:+.3f}"
                            )

                # Top-10 worst-predicted stimuli (largest |actual - predicted|).
                actual_arr = np.asarray(result.actual_responses)
                pred_arr = np.asarray(result.predicted_responses)
                residuals = actual_arr - pred_arr
                worst = np.argsort(-np.abs(residuals))[:10]
                print("  worst predictions (stim_id  actual  predicted  residual):")
                for i in worst:
                    print(
                        f"    {result.stim_ids[i]}  "
                        f"{actual_arr[i]:8.2f}  {pred_arr[i]:8.2f}  "
                        f"{residuals[i]:+8.2f}"
                    )

                channel_str = _channel_to_str(channel)
                base_title = (
                    f"{channel_str} | {component_type} | {strategy.label}"
                )

                # Figure 1: shape vs appearance.
                fig_app = plot_shape_vs_appearance(
                    result,
                    title=f"{base_title}  —  shape vs appearance",
                )
                if fig_app is not None:
                    if save_dir is not None:
                        app_path = os.path.join(
                            save_dir,
                            f"axis_coding_{channel_str}_{component_type}_"
                            f"{strategy.label}_appearance.png",
                        )
                        fig_app.savefig(app_path, dpi=150, bbox_inches="tight")
                        print(f"  saved: {app_path}")
                    if self.show_plots:
                        plt.show()
                    else:
                        plt.close(fig_app)

                # Figure 2: one consolidated axis-coding figure per fitted
                # model. Filenames suffixed by model name (the shape model
                # keeps the unsuffixed filename for back-compat).
                for spec in self.axis_models:
                    if spec.name not in (result.model_fits or {}):
                        continue
                    suffix = "" if spec.name == "shape" else f"_{spec.name.replace('+', 'plus')}"
                    fig_m = plot_axis_coding_consolidated(
                        result,
                        encoder=encoders_for_run[component_type],
                        config=self.panel_config,
                        title=f"{base_title}  —  {spec.name} axes",
                        model_name=spec.name,
                    )
                    if save_dir is not None:
                        fig_path = os.path.join(
                            save_dir,
                            f"axis_coding_{channel_str}_{component_type}_"
                            f"{strategy.label}{suffix}.png",
                        )
                        fig_m.savefig(fig_path, dpi=150, bbox_inches="tight")
                        print(f"  saved: {fig_path}")
                    if self.show_plots:
                        plt.show()
                    else:
                        plt.close(fig_m)

                # Tsao Fig 4A-style orth-tuning summary, all models overlaid.
                fig_orth = plot_orthogonal_tuning_curves(
                    result,
                    title=f"{base_title}  —  orthogonal-tuning summary",
                )
                if fig_orth is not None:
                    if save_dir is not None:
                        orth_path = os.path.join(
                            save_dir,
                            f"axis_coding_{channel_str}_{component_type}_"
                            f"{strategy.label}_orth_tuning.png",
                        )
                        fig_orth.savefig(orth_path, dpi=150, bbox_inches="tight")
                        print(f"  saved: {orth_path}")
                    if self.show_plots:
                        plt.show()
                    else:
                        plt.close(fig_orth)

                # Per-axis detail: every kept random orth axis plotted
                # individually so a single bumpy axis can't hide behind
                # the mean.
                fig_orth_detail = plot_orthogonal_tuning_per_axis_detail(
                    result,
                    title=f"{base_title}  —  orthogonal-tuning per-axis detail",
                )
                if fig_orth_detail is not None:
                    if save_dir is not None:
                        detail_path = os.path.join(
                            save_dir,
                            f"axis_coding_{channel_str}_{component_type}_"
                            f"{strategy.label}_orth_tuning_per_axis.png",
                        )
                        fig_orth_detail.savefig(detail_path, dpi=150,
                                                 bbox_inches="tight")
                        print(f"  saved: {detail_path}")
                    if self.show_plots:
                        plt.show()
                    else:
                        plt.close(fig_orth_detail)

                # Stimuli sampled uniformly along each axis (one row per axis).
                fig_stim = plot_axes_stimuli(
                    result,
                    n_per_axis=self.n_stimuli_per_axis,
                    title=(
                        f"{_channel_to_str(channel)} | "
                        f"{component_type} | {strategy.label}  —  axis stimuli"
                    ),
                )
                if fig_stim is not None:
                    if save_dir is not None:
                        stim_path = os.path.join(
                            save_dir,
                            f"axis_coding_{_channel_to_str(channel)}_"
                            f"{component_type}_{strategy.label}_stimuli.png",
                        )
                        fig_stim.savefig(stim_path, dpi=150, bbox_inches="tight")
                        print(f"  saved: {stim_path}")
                    if self.show_plots:
                        plt.show()
                    else:
                        plt.close(fig_stim)

        return results

    # ------------------------------------------------------------------
    # Cleaning helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        if df is None:
            raise ValueError(
                "AxisCodingAnalysis.analyze received compiled_data=None. "
                "Run with `compiled_data=analysis.compile_and_export()` or with "
                "the repository import path enabled."
            )
        df = df.copy()
        df = convert_str(df)
        # Trial filter (matches plan):
        #   - drop Lineage == 0 (catch trials), per run_rwa.py:60
        #   - drop StimType == 'BASELINE',     per run_rwa.py:67
        #   - keep all RegimeScore values (regime-zero parents kept on purpose)
        if "Lineage" in df.columns:
            df = df[df["Lineage"] != 0]
        if "StimType" in df.columns:
            df = df[df["StimType"] != "BASELINE"]
        # if "StimType" in df.columns:
        #     df = df[df["StimType"] != "SIDETEST_2Dvs3D"]

        # Conditioning. condition_spherical_angles / hemisphericalize_orientation
        df = condition_spherical_angles(df)
        df = hemisphericalize_orientation(df)
        df = flatten_2d_trials(df)
        # df = remove_2d_trials(df)
        return df



# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def remove_2d_trials(data):
    return data[data["Texture"] != "2D"]

def convert_str(data):
    for column in data:
        column_data = data[column]
        # print(column_data)
        if column in ["Shaft", "Termination", "Junction"]:
            #get first non-null value
            first_non_null = column_data.dropna().iloc[0] if not column_data.dropna().empty else None
            if isinstance(first_non_null, str):
                data[column] = column_data.apply(lambda x: eval(x) if isinstance(x, str) else x)




    return data

def flatten_2d_trials(data):
    #twod only
    twod_df = data[data["Texture"] == "2D"]
    for column in twod_df:
        column_data = twod_df[column]
        # print(column_data)
        if column in ["Shaft", "Termination", "Junction"]:
            for stim_data in column_data.array:
                apply_function_to_subdictionaries_values_with_keys(stim_data, ["theta", "phi"],

                                                                       flatten)

    # replace the original columns with the modified columns in the DataFrame.
    data.update(twod_df.set_index("TaskId"))
    data.reset_index(inplace=True)


    return data

def flatten(dictionary:dict):
    output = dictionary
    # orientation = output['orientation']
    phi = np.pi / 2 #phi = 0 is facing away the viewer, phi=pi is facing the viewer
    output['phi'] = phi
    return output

def _channel_to_str(channel: Union[str, list[str]]) -> str:
    if isinstance(channel, list):
        return f"{len(channel)}channels"
    return str(channel)


def _fmt(x) -> str:
    if x is None:
        return "None"
    if isinstance(x, float) and np.isnan(x):
        return "nan"
    return f"{x:.3f}"


def _jsonable(x):
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating,)):
        return float(x)
    if isinstance(x, (np.ndarray,)):
        return x.tolist()
    return str(x)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    # --- Selector hyperparameters ---
    # max_iter:              EM iterations before forced stop
    # tol:                   relative change in mu to declare convergence
    # temperature:           0 = hard argmin (strict proximity enforcement)
    #                        >0 = soft assignment; higher = less enforcement
    # response_weight_floor: clip low responses before weighting mu updates
    # variance_floor:        (LearnedDiagonal only) prevents any feature from
    #                        collapsing to infinite precision

    # --- Ridge hyperparameters ---
    # alphas:         log-spaced alpha search grid
    # cv:             folds for alpha selection via RidgeCV
    # n_splits_cv_r2: held-out R² estimate splits
    # test_size:      fraction held out per split

    ridge = lambda: RidgeRegressionAxisModel(
        alphas=np.logspace(-3, 4, 20),
        cv=5,
        n_splits_cv_r2=20,
        test_size=0.2,
    )

    strategies = [
        # AxisCodingStrategy(
        #     label="fixed_hard",
        #     selector_factory=lambda: FixedCovarianceSelector(
        #         max_iter=5000,
        #         tol=0.01,
        #         temperature=10.0,
        #         response_weight_floor=0.0,
        #     ),
        #     ridge_factory=ridge,
        # ),
        # AxisCodingStrategy(
        #     label="learned_diag",
        #     selector_factory=lambda: LearnedDiagonalCovarianceSelector(
        #         max_iter=50,
        #         tol=0.01,
        #         temperature=10,
        #         variance_floor=1e-3,
        #     ),
        #     ridge_factory=ridge,
        # ),
        # PCA variant: decorrelate features before selector/ridge.
        # n_pcs controls dimensionality; None = no PCA.
        # Bar charts back-project to original feature space automatically.
        # AxisCodingStrategy(
        #     label="learned_diag_pca",
        #     selector_factory=lambda: LearnedDiagonalCovarianceSelector(
        #         max_iter=50,
        #         tol=0.01,
        #         temperature=10,
        #         variance_floor=1e-3,
        #     ),
        #     ridge_factory=ridge,
        #     n_pcs=10,   # top-10 PCs; typically captures >90% variance
        # ),
        # AxisCodingStrategy(
        #     label="cluster_mode",
        #     selector_factory=lambda: ClusterModeSelector(
        #         bandwidth=None,       # None = median pairwise distance (data-driven)
        #         n_random_inits=100,
        #         max_iter=5000,
        #         tol=0.01,
        #         temperature=10.0,
        #         response_weight_floor=0.0,
        #     ),
        #     ridge_factory=ridge,
        # ),
        # Soft attention disentangles selector quality (folded into π) from
        # shape-at-location (folded into w).  All components — selected and
        # not — appear in the design matrix; non-selected ones contribute
        # negative-evidence constraints on w.
        # AxisCodingStrategy(
        #     label="soft_attention",
        #     selector_factory=lambda: SoftAttentionAxisSelector(
        #         tau=1.0,                  # bandwidth of the softmax over distances; larger → softer pooling
        #         alpha=1.0,                # ridge α used inside the joint fit (downstream RidgeCV picks final α)
        #         max_iter=30,              # alternating (W-step / M-step) iterations
        #         tol=1e-3,                 # relative ‖Δμ‖ to declare convergence
        #         init="response_weighted_mean",
        #         mu_optimizer_max_iter=50, # L-BFGS-B iters per M-step
        #     ),
        #     ridge_factory=ridge,
        # ),
        # Soft attention + PCA variant
        # AxisCodingStrategy(
        #     label="soft_attention_pca",
        #     selector_factory=lambda: SoftAttentionAxisSelector(
        #         tau=1.0,
        #         alpha=1.0,
        #         max_iter=1000,
        #         tol=1e-4,
        #         init="response_weighted_mean",
        #         mu_optimizer_max_iter=200,
        #     ),
        #     ridge_factory=ridge,
        #     n_pcs=6,
        # ),
        # Multi-prototype attention: K=2 prototypes with sparsity penalty on
        # amplitudes.  Collapses to a single prototype when one is enough; reports
        # n_active_prototypes in the selector summary.  lambda_amp controls how
        # aggressive the collapse is — raise to penalize the second prototype
        # more, lower if you want it to stay around longer.
        AxisCodingStrategy(
            label="multi_prototype_pca",
            selector_factory=lambda: MultiPrototypeAttentionSelector(
                n_prototypes=2,
                tau=1.0,
                alpha=1.0,
                lambda_amp=0.1,
                max_iter=30,
                tol=1e-3,
                init_jitter=0.5,
                amplitude_floor=1e-3,
                mu_optimizer_max_iter=100,
            ),
            ridge_factory=ridge,
            n_pcs=6,
        ),
        # RWA-peak strategy: μ comes from the argmax of an RWA pkl on disk
        # (one per component_type, written by run_rwa.py). Drop-in: same
        # plotting, axis-coding, and orth-tuning analysis as every other
        # strategy. Uncomment to enable; pass experiment_id matching the
        # one used when run_rwa.py wrote the pkl files.
        # AxisCodingStrategy(
        #     label="rwa_peak",
        #     selector_factory=lambda: RWAPeakSelector(
        #         rwa_dir=context.rwa_output_dir,
        #         experiment_id=context.ga_config.db_util.read_current_experiment_id(
        #             context.ga_name,
        #         ),
        #     ),
        #     ridge_factory=ridge,
        #     n_pcs=6,
        # ),
    ]

    analysis = AxisCodingAnalysis(
        strategies=strategies,
        outlier_sigma=2.0,       # 0.0 to disable; trials > n*std from stim mean are dropped
        outlier_min_trials=5,    # only attempt removal for stims with >= this many trials
        rf_filter=ReceptiveFieldFilter(plot=True, mahal_cutoff=3.5),  # None to disable
        n_stimuli_per_axis=15,  # for plot_axes_stimuli; set to 0 to disable that plot
    )
    session_id, _ = read_session_id_and_date_from_db_name(context.ga_database)
    compiled_data = None
    compiled_data = analysis.compile_and_export()
    # session_id="260426_0"
    channel = "A-028"
    analysis.run(session_id, "raw", channel, compiled_data=compiled_data)


if __name__ == "__main__":
    main()
