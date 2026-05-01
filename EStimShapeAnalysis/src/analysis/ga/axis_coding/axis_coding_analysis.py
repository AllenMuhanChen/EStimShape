from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Callable, Optional, Union

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from PIL import Image
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

    selector.fit(components_for_selector, dataset.responses)
    X = selector.selected_vectors(components_for_selector)

    ridge = ridge_factory() if ridge_factory is not None else RidgeRegressionAxisModel()
    ridge.fit(X, dataset.responses, feature_names=feature_names_for_model)
    predicted = ridge.predict(X)

    # Preferred-axis projections and ALL orthogonal axes (sorted by variance).
    w = ridge.w_
    axis_projections = _project_onto_unit(X, w)
    all_orth_axes, all_orth_variances = compute_all_orthogonal_axes(X, w)
    if all_orth_axes.shape[1] > 0:
        orth_axis = all_orth_axes[:, 0]              # principal orthogonal (top variance)
        all_orth_projections = X @ all_orth_axes     # (n_stim, n_orth)
        orth_projections = all_orth_projections[:, 0]
    else:
        orth_axis = np.zeros_like(w)
        all_orth_projections = np.zeros((X.shape[0], 0))
        orth_projections = np.zeros(X.shape[0])

    # Back-project from PC space to original feature space for interpretability.
    w_feat: Optional[np.ndarray] = None
    orth_axis_feat: Optional[np.ndarray] = None
    all_orth_axes_feat: Optional[np.ndarray] = None
    pca_var: Optional[list[float]] = None
    if pca_pre is not None:
        w_feat = pca_pre.back_project(w)
        if np.linalg.norm(orth_axis) > 1e-12:
            orth_axis_feat = pca_pre.back_project(orth_axis)
        if all_orth_axes.shape[1] > 0:
            # back-project each column: (d_orig, k) @ (k, n_orth) = (d_orig, n_orth)
            all_orth_axes_feat = pca_pre._pca.components_.T @ all_orth_axes
        pca_var = pca_pre.explained_variance_ratio.tolist()

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
        ridge_summary=ridge.summary(),
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
    )

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

                fig = plot_axis_coding_result(
                    result,
                    title=(
                        f"{_channel_to_str(channel)} | "
                        f"{component_type} | {strategy.label}"
                    ),
                )
                if save_dir is not None:
                    channel_str = _channel_to_str(channel)
                    fig_path = os.path.join(
                        save_dir,
                        f"axis_coding_{channel_str}_{component_type}_"
                        f"{strategy.label}.png",
                    )
                    fig.savefig(fig_path, dpi=150, bbox_inches="tight")
                    print(f"  saved: {fig_path}")
                if self.show_plots:
                    plt.show()
                else:
                    plt.close(fig)

                # Companion diagnostic: flat-tuning across all orthogonal PCs.
                fig_orth = plot_orthogonal_axes_diagnostic(
                    result,
                    title=(
                        f"{_channel_to_str(channel)} | "
                        f"{component_type} | {strategy.label}  —  orthogonal axes"
                    ),
                )
                if fig_orth is not None:
                    if save_dir is not None:
                        orth_path = os.path.join(
                            save_dir,
                            f"axis_coding_{_channel_to_str(channel)}_"
                            f"{component_type}_{strategy.label}_orthogonal.png",
                        )
                        fig_orth.savefig(orth_path, dpi=150, bbox_inches="tight")
                        print(f"  saved: {orth_path}")
                    if self.show_plots:
                        plt.show()
                    else:
                        plt.close(fig_orth)

                # μ in interpretable parameter space (linear bars + sphere/circle plots).
                fig_mu = plot_mu_decoded(
                    result,
                    encoder=encoders_for_run[component_type],
                    title=(
                        f"{_channel_to_str(channel)} | "
                        f"{component_type} | {strategy.label}  —  μ in parameter space"
                    ),
                )
                if fig_mu is not None:
                    if save_dir is not None:
                        mu_path = os.path.join(
                            save_dir,
                            f"axis_coding_{_channel_to_str(channel)}_"
                            f"{component_type}_{strategy.label}_mu.png",
                        )
                        fig_mu.savefig(mu_path, dpi=150, bbox_inches="tight")
                        print(f"  saved: {mu_path}")
                    if self.show_plots:
                        plt.show()
                    else:
                        plt.close(fig_mu)

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
