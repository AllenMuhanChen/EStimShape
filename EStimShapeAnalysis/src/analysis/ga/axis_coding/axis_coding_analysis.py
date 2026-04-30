from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Callable, Optional, Union

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from scipy.stats import linregress, spearmanr

from clat.pipeline.pipeline_base_classes import (
    InputHandler,
    ComputationModule,
    AnalysisModuleFactory,
)

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
)
from src.analysis.ga.axis_coding.ridge_regression_model import (
    RidgeRegressionAxisModel,
)
from src.analysis.ga.plot_top_n import PlotTopNAnalysis
from src.analysis.ga.receptive_field_filter import ReceptiveFieldFilter
from src.analysis.modules.figure_output import FigureSaverOutput
from src.pga.mock.mock_rwa_analysis import (
    condition_spherical_angles,
    hemisphericalize_orientation,
)
from src.repository.export_to_repository import read_session_id_and_date_from_db_name



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
    pca_explained_variance: Optional[list[float]] = None            # (k,) per-PC variance ratio

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
    pca_var: Optional[list[float]] = None
    if pca_pre is not None:
        w_feat = pca_pre.back_project(w)
        if np.linalg.norm(orth_axis) > 1e-12:
            orth_axis_feat = pca_pre.back_project(orth_axis)
        pca_var = pca_pre.explained_variance_ratio.tolist()

    noise_ceiling = compute_noise_ceiling(
        df=df,
        channel=channel,
        spike_rates_col=spike_rates_col,
        stim_ids=dataset.stim_ids,
    )

    result = AxisCodingResult(
        channel=channel,
        component_type=component_type,
        strategy_label=strategy_label,
        n_stim=dataset.n_stim,
        n_features=dataset.n_features,
        n_dropped_no_components=dataset.n_dropped_no_components,
        n_dropped_no_response=dataset.n_dropped_no_response,
        selector_summary=selector.summary(),
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
        pca_explained_variance=pca_var,
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

        # OLS line + stats
        reg = linregress(projections, actual)
        xs = np.array([projections.min(), projections.max()])
        ys = reg.intercept + reg.slope * xs
        ax.plot(xs, ys, color="crimson", lw=1.5, alpha=0.8, label="OLS fit")
        stats_str = (
            f"slope = {reg.slope:+.3g}\n"
            f"R²    = {reg.rvalue ** 2:.3f}\n"
            f"p     = {reg.pvalue:.2g}"
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
    n_top_curves: int = 3,
    n_bins: int = 10,
    title: Optional[str] = None,
) -> Optional[plt.Figure]:
    """
    Per-axis diagnostic for axis coding.

    Layout (2 × 3):
      Row 0:  tuning curves for the top-``n_top_curves`` orthogonal PCs
              (sorted by data variance), each annotated with OLS slope,
              Spearman ρ, p, and the variance fraction the PC captures.
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

    slopes = np.zeros(n_axes)
    rhos = np.zeros(n_axes)
    pvals = np.ones(n_axes)
    for k in range(n_axes):
        col = proj_all[:, k]
        if col.std() > 1e-12:
            reg = linregress(col, actual)
            slopes[k] = float(reg.slope)
            r, p = spearmanr(col, actual)
            rhos[k] = float(r)
            pvals[k] = float(p)

    # ------------------------------------------------------------------
    # Figure
    # ------------------------------------------------------------------
    fig, axes = plt.subplots(2, max(n_top_curves, 3), figsize=(6 * max(n_top_curves, 3), 9))

    # Row 0: tuning curves for the top-N orthogonal PCs.
    for k in range(min(n_top_curves, n_orth)):
        ax = axes[0, k]
        proj = proj_orth[:, k]
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
            reg = linregress(proj, actual)
            xs = np.array([proj.min(), proj.max()])
            ax.plot(xs, reg.intercept + reg.slope * xs,
                    color="crimson", lw=1.5, alpha=0.8, label="OLS")
            # k+1 maps to slopes[k+1] / rhos[k+1] (preferred is at index 0).
            ax.text(
                0.02, 0.98,
                f"orth PC{k+1}  var={variances_orth[k] / max(var_total, 1e-12):.1%}\n"
                f"slope = {slopes[k+1]:+.3g}\n"
                f"ρ     = {rhos[k+1]:+.3f}\n"
                f"p     = {pvals[k+1]:.2g}",
                transform=ax.transAxes, va="top", ha="left",
                fontsize=8, family="monospace",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                          alpha=0.85, edgecolor="lightgray"),
            )
        ax.set_xlabel(f"Projection onto orth PC{k+1}")
        ax.set_ylabel("Actual response")
        ax.set_title(f"Orth PC{k+1} tuning")
        ax.legend(fontsize=7, loc="lower right")

    for k in range(min(n_top_curves, n_orth), max(n_top_curves, 3)):
        axes[0, k].axis("off")

    # ------------------------------------------------------------------
    # Row 1: summaries across preferred axis + all orthogonal PCs.
    # ------------------------------------------------------------------
    labels = ["preferred"] + [f"orth {k+1}" for k in range(n_orth)]
    x = np.arange(n_axes)
    colors = ["forestgreen"] + ["steelblue"] * n_orth   # preferred stands out

    # Slope per axis
    ax = axes[1, 0]
    bars = ax.bar(x, slopes, color=colors)
    for k, b in enumerate(bars):
        if pvals[k] < 0.05 and k > 0:   # mark orth bars whose OLS p < 0.05
            b.set_edgecolor("crimson")
            b.set_linewidth(1.5)
    ax.axhline(0, color="black", lw=0.7)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("OLS slope (response per z-unit)")
    ax.set_title(
        "OLS slope per axis\n(preferred should dominate; orth bars ≈ 0)"
    )

    # |Spearman ρ| per axis
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
    ax.set_title("Rank correlation per axis\n(red edge: raw p<0.05)")
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

    # ------------------------------------------------------------------
    # Analysis API
    # ------------------------------------------------------------------

    def analyze(self, channel, compiled_data: pd.DataFrame = None):
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

        # Trial filter (matches plan):
        #   - drop Lineage == 0 (catch trials), per run_rwa.py:60
        #   - drop StimType == 'BASELINE',     per run_rwa.py:67
        #   - keep all RegimeScore values (regime-zero parents kept on purpose)
        if "Lineage" in df.columns:
            df = df[df["Lineage"] != 0]
        if "StimType" in df.columns:
            df = df[df["StimType"] != "BASELINE"]
        if "StimType" in df.columns:
            df = df[df["StimType"] != "SIDETEST_2Dvs3D"]

        # Conditioning. condition_spherical_angles / hemisphericalize_orientation
        # mutate component dicts in-place; they are idempotent for already-
        # conditioned dicts so it's safe to apply even if the repository copy
        # was already conditioned upstream.
        df = condition_spherical_angles(df)
        df = hemisphericalize_orientation(df)
        # df = remove_2d_trials(df)
        return df



# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def remove_2d_trials(data):
    return data[data["Texture"] != "2D"]

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
        AxisCodingStrategy(
            label="learned_diag",
            selector_factory=lambda: LearnedDiagonalCovarianceSelector(
                max_iter=50,
                tol=0.01,
                temperature=10,
                variance_floor=1e-3,
            ),
            ridge_factory=ridge,
        ),
        # PCA variant: decorrelate features before selector/ridge.
        # n_pcs controls dimensionality; None = no PCA.
        # Bar charts back-project to original feature space automatically.
        AxisCodingStrategy(
            label="learned_diag_pca",
            selector_factory=lambda: LearnedDiagonalCovarianceSelector(
                max_iter=50,
                tol=0.01,
                temperature=10,
                variance_floor=1e-3,
            ),
            ridge_factory=ridge,
            n_pcs=10,   # top-10 PCs; typically captures >90% variance
        ),
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
        AxisCodingStrategy(
            label="soft_attention",
            selector_factory=lambda: SoftAttentionAxisSelector(
                tau=1.0,                  # bandwidth of the softmax over distances; larger → softer pooling
                alpha=1.0,                # ridge α used inside the joint fit (downstream RidgeCV picks final α)
                max_iter=30,              # alternating (W-step / M-step) iterations
                tol=1e-3,                 # relative ‖Δμ‖ to declare convergence
                init="response_weighted_mean",
                mu_optimizer_max_iter=50, # L-BFGS-B iters per M-step
            ),
            ridge_factory=ridge,
        ),
        # Soft attention + PCA variant
        AxisCodingStrategy(
            label="soft_attention_pca",
            selector_factory=lambda: SoftAttentionAxisSelector(
                tau=1.0,
                alpha=1.0,
                max_iter=30,
                tol=1e-3,
                init="response_weighted_mean",
                mu_optimizer_max_iter=50,
            ),
            ridge_factory=ridge,
            n_pcs=10,
        ),
    ]

    analysis = AxisCodingAnalysis(
        strategies=strategies,
        outlier_sigma=2.0,       # 0.0 to disable; trials > n*std from stim mean are dropped
        outlier_min_trials=5,    # only attempt removal for stims with >= this many trials
        rf_filter=ReceptiveFieldFilter(plot=True, mahal_cutoff=3.5),  # None to disable
    )
    # session_id, _ = read_session_id_and_date_from_db_name(context.ga_database)
    session_id="260426_0"
    channel = "A-000"
    analysis.run(session_id, "raw", channel, compiled_data=None)


if __name__ == "__main__":
    main()
