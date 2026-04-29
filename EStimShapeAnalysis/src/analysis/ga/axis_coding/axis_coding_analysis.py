from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Callable, Optional, Union

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

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
    make_default_encoders,
)
from src.analysis.ga.axis_coding.component_selectors import (
    ComponentSelector,
    FixedCovarianceSelector,
    LearnedDiagonalCovarianceSelector,
    ClusterModeSelector,
)
from src.analysis.ga.axis_coding.ridge_regression_model import (
    RidgeRegressionAxisModel,
)
from src.analysis.ga.plot_top_n import PlotTopNAnalysis
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
    """

    label: str
    selector_factory: SelectorFactory
    ridge_factory: Optional[RidgeFactory] = None


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
    noise_ceiling: Optional[float] = None

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
) -> AxisCodingResult:
    dataset = AxisCodingDataset.build(
        df=df,
        component_type=component_type,
        encoder=encoder,
        channel=channel,
        spike_rates_col=spike_rates_col,
    )

    selector.fit(dataset.components_per_stim, dataset.responses)
    X = selector.selected_vectors(dataset.components_per_stim)

    ridge = ridge_factory() if ridge_factory is not None else RidgeRegressionAxisModel()
    ridge.fit(X, dataset.responses, feature_names=dataset.feature_names)
    predicted = ridge.predict(X)

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
        feature_names=dataset.feature_names,
        actual_responses=dataset.responses.tolist(),
        predicted_responses=predicted.tolist(),
        noise_ceiling=noise_ceiling,
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

def compute_axis_projections(result: AxisCodingResult) -> np.ndarray:
    """
    Project each stimulus's selected component vector onto the preferred axis.

    The ridge axis direction is w/||w||.  Since predicted = X @ w + b, the
    projection x_i · (w/||w||) = (predicted_i - b) / ||w||, so we can recover
    it from already-stored predictions without re-running the selector.

    Returns a 1-D array of length n_stim (axis coordinates, in z-scored units).
    """
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


def plot_axis_coding_result(
    result: AxisCodingResult, title: Optional[str] = None, n_bins: int = 10
) -> plt.Figure:
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    actual = np.asarray(result.actual_responses)
    pred = np.asarray(result.predicted_responses)
    projections = compute_axis_projections(result)

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

    # Panel 1: Predicted vs actual
    ax = axes[0]
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

    # Panel 2: Tuning curve — response vs projection onto preferred axis
    ax = axes[1]
    ax.scatter(projections, actual, s=12, alpha=0.5, label="stimuli")
    # Binned mean ± SEM overlay
    if not np.all(np.isnan(projections)):
        bin_edges = np.linspace(projections.min(), projections.max(), n_bins + 1)
        bin_centers = 0.5 * (bin_edges[:-1] + bin_edges[1:])
        bin_means, bin_sems = [], []
        for lo, hi in zip(bin_edges[:-1], bin_edges[1:]):
            mask = (projections >= lo) & (projections < hi)
            if mask.sum() > 0:
                vals = actual[mask]
                bin_means.append(vals.mean())
                bin_sems.append(vals.std(ddof=0) / np.sqrt(len(vals)))
            else:
                bin_means.append(np.nan)
                bin_sems.append(np.nan)
        bin_means = np.asarray(bin_means)
        bin_sems = np.asarray(bin_sems)
        valid = ~np.isnan(bin_means)
        ax.plot(bin_centers[valid], bin_means[valid], "k-", lw=2, label="binned mean")
        ax.fill_between(
            bin_centers[valid],
            (bin_means - bin_sems)[valid],
            (bin_means + bin_sems)[valid],
            alpha=0.25,
            color="k",
        )
    ax.set_xlabel("Projection onto preferred axis (z-scored units)")
    ax.set_ylabel("Actual response")
    ax.set_title("Axis tuning curve")
    ax.legend(fontsize=8)

    # Panel 3: Top |w| bars
    ax = axes[2]
    top = result.ridge_summary.get("top_features") or []
    if top:
        names = [n for n, _ in top]
        weights = [w for _, w in top]
        y = np.arange(len(names))
        ax.barh(y, weights)
        ax.set_yticks(y)
        ax.set_yticklabels(names, fontsize=8)
        ax.invert_yaxis()
        ax.axvline(0, color="black", lw=0.8)
        ax.set_xlabel("Ridge weight")
        ax.set_title("Top features by |w|")

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

    # ------------------------------------------------------------------
    # Analysis API
    # ------------------------------------------------------------------

    def analyze(self, channel, compiled_data: pd.DataFrame = None):
        compiled_data = self._prepare_dataframe(compiled_data)
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
        AxisCodingStrategy(
            label="cluster_mode",
            selector_factory=lambda: ClusterModeSelector(
                bandwidth=None,       # None = median pairwise distance (data-driven)
                n_random_inits=100,
                max_iter=5000,
                tol=0.01,
                temperature=10.0,
                response_weight_floor=0.0,
            ),
            ridge_factory=ridge,
        ),
    ]

    analysis = AxisCodingAnalysis(
        strategies=strategies,
        outlier_sigma=2.0,       # 0.0 to disable; trials > n*std from stim mean are dropped
        outlier_min_trials=5,    # only attempt removal for stims with >= this many trials
    )
    # session_id, _ = read_session_id_and_date_from_db_name(context.ga_database)
    session_id="260426_0"
    channel = "GA"
    analysis.run(session_id, "raw", channel, compiled_data=None)


if __name__ == "__main__":
    main()
