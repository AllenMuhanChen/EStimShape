"""
Group-level (across-cell) plots for axis-coding outputs in
``allen_data_repository``.

Reads from AxisCodingFitMetrics + AxisCodingFitArrays (populated by
AxisCodingAnalysis with ``export_to_repository=True``). Three figures, each
with one row per component_type (Shaft, Termination, Junction):

  1. plot_population_orth_tuning_curves
       One line per (session, unit) on a shared z-scored x-axis, with one
       panel per model. Each curve is normalized by its own Gaussian peak
       (a + c) so peaks land at 1 and curves are comparable across cells.
       Tsao Fig 4A at the population scale.

  2. plot_population_modulation_depth_histogram
       Histogram of orth_amplitude_norm = a / (a+c) across cells, one color
       per model. Axis coding predicts a tight distribution near 0.

  3. plot_population_spearman_p_histogram
       Histogram of model goodness-of-fit p-values (Spearman ρ between
       predicted and actual response, analytical p) across cells, one color
       per model. Tells you "what fraction of cells does this model fit
       significantly".
"""

from __future__ import annotations

from typing import Optional, Sequence

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

from clat.util.connection import Connection

from src.repository.export_axis_coding import (
    read_axis_coding_arrays,
    read_axis_coding_metrics,
)


DEFAULT_COMPONENT_TYPES: tuple[str, ...] = ("Shaft", "Termination", "Junction")


def _model_color_map(models: list[str]) -> dict[str, tuple]:
    cmap = plt.get_cmap("tab10")
    return {name: cmap(i % 10) for i, name in enumerate(models)}


def _empty_panel(ax, msg: str) -> None:
    ax.text(0.5, 0.5, msg, ha="center", va="center",
            transform=ax.transAxes, fontsize=10, color="gray")
    ax.set_xticks([])
    ax.set_yticks([])


def _collect_models(
    repo_conn: Connection,
    component_types: Sequence[str],
    strategy: str,
) -> tuple[dict[str, pd.DataFrame], list[str]]:
    """Pull metrics for every component_type once, plus the union of models."""
    per_ct: dict[str, pd.DataFrame] = {}
    models: set[str] = set()
    for ct in component_types:
        m = read_axis_coding_metrics(repo_conn, component_type=ct, strategy=strategy)
        per_ct[ct] = m
        if not m.empty:
            models.update(m["model_name"].unique().tolist())
    return per_ct, sorted(models)


# ---------------------------------------------------------------------------
# Plot 1: population orth-tuning curves (rows = component_type, cols = model)
# ---------------------------------------------------------------------------

def plot_population_orth_tuning_curves(
    repo_conn: Connection,
    component_types: Sequence[str],
    strategy: str,
    title: Optional[str] = None,
) -> Optional[plt.Figure]:
    """One row per component_type, one panel per model. Curves normalized by a+c."""
    per_ct_metrics, models = _collect_models(repo_conn, component_types, strategy)
    if not models:
        print("  [group] no metrics rows match for any component_type.")
        return None

    colors = _model_color_map(models)
    n_rows = len(component_types)
    n_cols = max(1, len(models))
    fig, axes = plt.subplots(
        n_rows, n_cols, figsize=(5.5 * n_cols, 4.5 * n_rows),
        squeeze=False, sharey="row",
    )

    for row_idx, ct in enumerate(component_types):
        metrics = per_ct_metrics[ct]
        if metrics.empty:
            for col_idx in range(n_cols):
                _empty_panel(axes[row_idx, col_idx], f"no data ({ct})")
            axes[row_idx, 0].set_ylabel(f"{ct}\nNormalized response  [ y / (a+c) ]")
            continue

        x_df = read_axis_coding_arrays(
            repo_conn, "orth_tuning_x",
            component_type=ct, strategy=strategy,
        )
        y_df = read_axis_coding_arrays(
            repo_conn, "orth_tuning_mean",
            component_type=ct, strategy=strategy,
        )
        if x_df.empty or y_df.empty:
            for col_idx in range(n_cols):
                _empty_panel(axes[row_idx, col_idx], f"no orth arrays ({ct})")
            axes[row_idx, 0].set_ylabel(f"{ct}\nNormalized response  [ y / (a+c) ]")
            continue

        keycols = ["session_id", "unit_name", "component_type", "strategy", "model_name"]
        merged = (
            metrics
            .merge(x_df.rename(columns={"array": "x"}), on=keycols)
            .merge(y_df.rename(columns={"array": "y"}), on=keycols)
        )

        for col_idx, model in enumerate(models):
            ax = axes[row_idx, col_idx]
            ax.set_ylim(0,2)
            sub = merged[merged["model_name"] == model]
            n_cells = len(sub)
            for _, row in sub.iterrows():
                x = np.asarray(row["x"], dtype=np.float64)
                y = np.asarray(row["y"], dtype=np.float64)
                a = row.get("orth_gauss_a")
                c = row.get("orth_gauss_c")
                ok = bool(row.get("orth_gauss_fit_ok"))
                if not ok or a is None or c is None:
                    continue
                denom = float(a) + float(c)
                if abs(denom) < 1e-9:
                    continue
                ax.plot(x, y / denom, color=colors[model], lw=0.8, alpha=0.35)

            valid = sub[(sub["orth_gauss_fit_ok"] == 1) &
                        sub["orth_gauss_a"].notna() & sub["orth_gauss_c"].notna()]
            if len(valid):
                curves = []
                for _, row in valid.iterrows():
                    denom = float(row["orth_gauss_a"]) + float(row["orth_gauss_c"])
                    if abs(denom) < 1e-9:
                        continue
                    curves.append(np.asarray(row["y"], dtype=np.float64) / denom)
                if curves:
                    stacked = np.vstack(curves)
                    mean_curve = np.nanmean(stacked, axis=0)
                    n_per_bin = np.sum(~np.isnan(stacked), axis=0)
                    sem_curve = np.nanstd(stacked, axis=0, ddof=1) / np.sqrt(
                        np.maximum(n_per_bin, 1)
                    )
                    x_axis = np.asarray(valid.iloc[0]["x"], dtype=np.float64)
                    ax.plot(x_axis, mean_curve, color="black", lw=2.5,
                            label=f"population mean (n={len(curves)})")
                    ax.errorbar(x_axis, mean_curve, yerr=sem_curve,
                                fmt="o", color="black", ecolor="black",
                                ms=4, elinewidth=1.0, capsize=2, zorder=5)

            ax.axhline(1.0, color="gray", lw=0.6, ls=":", alpha=0.7)
            ax.axhline(0.0, color="black", lw=0.5)
            if row_idx == n_rows - 1:
                ax.set_xlabel("Projection onto random orth axis (z)")
            if col_idx == 0:
                ax.set_ylabel(f"{ct}\nNormalized response  [ y / (a+c) ]")
            ax.set_title(f"{model}\n(n={n_cells} cells)" if row_idx == 0
                         else f"(n={n_cells} cells)")
            ax.legend(fontsize=8, loc="best")

    if title:
        fig.suptitle(title)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Plot 2: population modulation-depth histogram (a / (a+c))
# ---------------------------------------------------------------------------

def plot_population_modulation_depth_histogram(
    repo_conn: Connection,
    component_types: Sequence[str],
    strategy: str,
    bins: int = 80,
    title: Optional[str] = None,
) -> Optional[plt.Figure]:
    """Histogram of orth_amplitude_norm = a / (a+c) across cells, one row per component_type."""
    per_ct_metrics, models = _collect_models(repo_conn, component_types, strategy)
    if not models:
        print("  [group] no metrics rows match for any component_type.")
        return None

    colors = _model_color_map(models)
    n_rows = len(component_types)
    fig, axes = plt.subplots(n_rows, 1, figsize=(7, 4.5 * n_rows),
                              squeeze=False, sharex=True)

    for row_idx, ct in enumerate(component_types):
        ax = axes[row_idx, 0]
        metrics = per_ct_metrics[ct]
        if metrics.empty:
            _empty_panel(ax, f"no data ({ct})")
            continue

        valid = metrics[
            metrics["orth_gauss_fit_ok"].astype(bool)
            & metrics["orth_amplitude_norm"].notna()
        ]
        if valid.empty:
            _empty_panel(ax, f"no valid Gaussian fits ({ct})")
            continue

        all_vals = valid["orth_amplitude_norm"].astype(float).values
        bin_edges = np.linspace(
            float(np.nanmin(all_vals)) - 1e-3,
            float(np.nanmax(all_vals)) + 1e-3,
            bins + 1,
        )
        for model in models:
            vals = valid[valid["model_name"] == model]["orth_amplitude_norm"].astype(float).values
            if len(vals) == 0:
                continue
            ax.hist(vals, bins=bin_edges, color=colors[model], alpha=0.55,
                    edgecolor="black", linewidth=0.4,
                    label=f"{model} (n={len(vals)}, med={np.median(vals):+.2f})")

        ax.axvline(0.0, color="black", lw=0.7, ls="--", label="flat (axis coding)")
        ax.axvline(1.0, color="gray", lw=0.7, ls=":", label="full bump (exemplar)")
        ax.set_xlim((-2, 2))
        if row_idx == n_rows - 1:
            ax.set_xlabel("Modulation depth  a / (a + c)")
        ax.set_ylabel(f"{ct}\nCell count")
        ax.legend(fontsize=8, loc="best")

    if title:
        fig.suptitle(title)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Plot 3: population Spearman-p histogram (model goodness-of-fit)
# ---------------------------------------------------------------------------

def plot_population_spearman_p_histogram(
    repo_conn: Connection,
    component_types: Sequence[str],
    strategy: str,
    bins: int = 80,
    title: Optional[str] = None,
) -> Optional[plt.Figure]:
    """
    Histogram of model goodness-of-fit p-values across cells, one row per
    component_type. Per-cell: spearmanr(predicted, actual) analytical p.
    Companion column: |ρ| distribution to show effect size.
    """
    per_ct_metrics, models = _collect_models(repo_conn, component_types, strategy)
    if not models:
        print("  [group] no metrics rows match for any component_type.")
        return None

    colors = _model_color_map(models)
    n_rows = len(component_types)
    fig, axes = plt.subplots(n_rows, 2, figsize=(13, 4.5 * n_rows),
                              squeeze=False,
                              gridspec_kw={"width_ratios": [3, 2]})

    for row_idx, ct in enumerate(component_types):
        ax_p = axes[row_idx, 0]
        ax_rho = axes[row_idx, 1]
        metrics = per_ct_metrics[ct]
        if metrics.empty:
            _empty_panel(ax_p, f"no data ({ct})")
            _empty_panel(ax_rho, f"no data ({ct})")
            continue

        valid = metrics[metrics["spearman_p"].notna()]
        if valid.empty:
            _empty_panel(ax_p, f"no spearman_p ({ct})")
            _empty_panel(ax_rho, f"no spearman_rho ({ct})")
            continue

        bin_edges = np.linspace(0.0, 1.0, bins + 1)
        for model in models:
            vals = valid[valid["model_name"] == model]["spearman_p"].astype(float).values
            if len(vals) == 0:
                continue
            frac_sig = float((vals < 0.05).mean())
            ax_p.hist(vals, bins=bin_edges, color=colors[model], alpha=0.55,
                      edgecolor="black", linewidth=0.4,
                      label=f"{model} (n={len(vals)}, p<0.05: {frac_sig:.0%})")
        ax_p.axvline(0.05, color="black", lw=0.7, ls="--", label="p=0.05")
        if row_idx == n_rows - 1:
            ax_p.set_xlabel("Spearman p (predicted vs actual)")
        ax_p.set_ylabel(f"{ct}\nCell count")
        if row_idx == 0:
            ax_p.set_title("Goodness-of-fit p-values")
        ax_p.legend(fontsize=8, loc="best")

        rho_bin_edges = np.linspace(-1.0, 1.0, 21)
        for model in models:
            rhos = valid[valid["model_name"] == model]["spearman_rho"].astype(float).values
            if len(rhos) == 0:
                continue
            ax_rho.hist(rhos, bins=rho_bin_edges, color=colors[model], alpha=0.55,
                        edgecolor="black", linewidth=0.4,
                        label=f"{model} (med ρ={np.median(rhos):+.2f})")
        ax_rho.axvline(0.0, color="black", lw=0.7, ls="--")
        if row_idx == n_rows - 1:
            ax_rho.set_xlabel("Spearman ρ (predicted vs actual)")
        ax_rho.set_ylabel("Cell count")
        ax_rho.set_xlim(0, 1.0)
        if row_idx == 0:
            ax_rho.set_title("Goodness-of-fit effect size")
        ax_rho.legend(fontsize=8, loc="best")

    if title:
        fig.suptitle(title)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Convenience entry: build all three figures + save
# ---------------------------------------------------------------------------

def main(component_types: Sequence[str] = DEFAULT_COMPONENT_TYPES,
         strategy: str = "multi_prototype_pca",
         save_dir: Optional[str] = None):
    repo_conn = Connection("allen_data_repository")
    ct_label = "+".join(component_types)
    base = f"{ct_label} | {strategy}"

    fig1 = plot_population_orth_tuning_curves(
        repo_conn, component_types, strategy,
        title=f"{base}  —  population orthogonal-tuning curves",
    )
    fig2 = plot_population_modulation_depth_histogram(
        repo_conn, component_types, strategy,
        title=f"{base}  —  population modulation-depth histogram",
    )
    fig3 = plot_population_spearman_p_histogram(
        repo_conn, component_types, strategy,
        title=f"{base}  —  population goodness-of-fit",
    )

    if save_dir:
        import os
        os.makedirs(save_dir, exist_ok=True)
        for label, fig in (("orth_tuning", fig1),
                           ("modulation_hist", fig2),
                           ("spearman_p_hist", fig3)):
            if fig is not None:
                path = os.path.join(save_dir, f"population_{ct_label}_{strategy}_{label}.png")
                fig.savefig(path, dpi=150, bbox_inches="tight")
                print(f"  saved: {path}")
    else:
        plt.show()


if __name__ == "__main__":
    main()
