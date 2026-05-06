"""
Group-level (across-cell) plots for axis-coding outputs in
``allen_data_repository``.

Reads from AxisCodingFitMetrics + AxisCodingFitArrays (populated by
AxisCodingAnalysis with ``export_to_repository=True``). Three figures:

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

from typing import Optional

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

from clat.util.connection import Connection

from src.repository.export_axis_coding import (
    read_axis_coding_arrays,
    read_axis_coding_metrics,
)


def _model_color_map(models: list[str]) -> dict[str, tuple]:
    cmap = plt.get_cmap("tab10")
    return {name: cmap(i % 10) for i, name in enumerate(models)}


# ---------------------------------------------------------------------------
# Plot 1: population orth-tuning curves (one line per cell, panels per model)
# ---------------------------------------------------------------------------

def plot_population_orth_tuning_curves(
    repo_conn: Connection,
    component_type: str,
    strategy: str,
    title: Optional[str] = None,
) -> Optional[plt.Figure]:
    """One line per cell, one panel per model. Curves Tsao-normalized by a+c."""
    metrics = read_axis_coding_metrics(
        repo_conn, component_type=component_type, strategy=strategy,
    )
    if metrics.empty:
        print("  [group] no metrics rows match.")
        return None

    x_df = read_axis_coding_arrays(
        repo_conn, "orth_tuning_x",
        component_type=component_type, strategy=strategy,
    )
    y_df = read_axis_coding_arrays(
        repo_conn, "orth_tuning_mean",
        component_type=component_type, strategy=strategy,
    )
    if x_df.empty or y_df.empty:
        print("  [group] no orth_tuning arrays found.")
        return None

    keycols = ["session_id", "unit_name", "component_type", "strategy", "model_name"]
    merged = (
        metrics
        .merge(x_df.rename(columns={"array": "x"}), on=keycols)
        .merge(y_df.rename(columns={"array": "y"}), on=keycols)
    )

    models = sorted(merged["model_name"].unique())
    colors = _model_color_map(models)
    fig, axes = plt.subplots(
        1, len(models), figsize=(5.5 * len(models), 4.5), squeeze=False,
        sharey=True,
    )

    for col_idx, model in enumerate(models):
        ax = axes[0, col_idx]
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

        # Bold population mean (across cells with valid fits).
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
                ax.plot(np.asarray(valid.iloc[0]["x"], dtype=np.float64),
                        mean_curve, color="black", lw=2.5,
                        label=f"population mean (n={len(curves)})")

        ax.axhline(1.0, color="gray", lw=0.6, ls=":", alpha=0.7)
        ax.axhline(0.0, color="black", lw=0.5)
        ax.set_xlabel("Projection onto random orth axis (z)")
        if col_idx == 0:
            ax.set_ylabel("Normalized response  [ y / (a+c) ]")
        ax.set_title(f"{model}\n(n={n_cells} cells)")
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
    component_type: str,
    strategy: str,
    bins: int = 80,
    title: Optional[str] = None,
) -> Optional[plt.Figure]:
    """Histogram of orth_amplitude_norm = a / (a+c) across cells, by model."""
    metrics = read_axis_coding_metrics(
        repo_conn, component_type=component_type, strategy=strategy,
    )
    if metrics.empty:
        print("  [group] no metrics rows match.")
        return None

    valid = metrics[
        metrics["orth_gauss_fit_ok"].astype(bool)
        & metrics["orth_amplitude_norm"].notna()
    ]
    if valid.empty:
        print("  [group] no valid Gaussian fits to histogram.")
        return None

    models = sorted(valid["model_name"].unique())
    colors = _model_color_map(models)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    all_vals = valid["orth_amplitude_norm"].astype(float).values
    bin_edges = np.linspace(
        float(np.nanmin(all_vals)) - 1e-3,
        float(np.nanmax(all_vals)) + 1e-3,
        bins + 1,
    )
    for model in models:
        vals = valid[valid["model_name"] == model]["orth_amplitude_norm"].astype(float).values
        ax.hist(vals, bins=bin_edges, color=colors[model], alpha=0.55,
                edgecolor="black", linewidth=0.4,
                label=f"{model} (n={len(vals)}, med={np.median(vals):+.2f})")

    ax.axvline(0.0, color="black", lw=0.7, ls="--", label="flat (axis coding)")
    ax.axvline(1.0, color="gray", lw=0.7, ls=":", label="full bump (exemplar)")
    ax.set_xlim((-2, 2))
    ax.set_xlabel("Modulation depth  a / (a + c)")
    ax.set_ylabel("Cell count")
    ax.set_title(title or
                  f"Population orthogonal-tuning modulation depth  ({component_type}, {strategy})")
    ax.legend(fontsize=8, loc="best")
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Plot 3: population Spearman-p histogram (model goodness-of-fit)
# ---------------------------------------------------------------------------

def plot_population_spearman_p_histogram(
    repo_conn: Connection,
    component_type: str,
    strategy: str,
    bins: int = 80,
    title: Optional[str] = None,
) -> Optional[plt.Figure]:
    """
    Histogram of model goodness-of-fit p-values across cells, by model.
    Per-cell: spearmanr(predicted, actual) analytical p. Lower = better
    fit. Bonus: also reports the fraction of cells with p < 0.05 per model.
    """
    metrics = read_axis_coding_metrics(
        repo_conn, component_type=component_type, strategy=strategy,
    )
    if metrics.empty:
        print("  [group] no metrics rows match.")
        return None

    valid = metrics[metrics["spearman_p"].notna()]
    if valid.empty:
        print("  [group] no spearman_p values to histogram.")
        return None

    models = sorted(valid["model_name"].unique())
    colors = _model_color_map(models)
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5),
                              gridspec_kw={"width_ratios": [3, 2]})

    # Left: histogram of p (linear scale).
    ax = axes[0]
    bin_edges = np.linspace(0.0, 1.0, bins + 1)
    for model in models:
        vals = valid[valid["model_name"] == model]["spearman_p"].astype(float).values
        frac_sig = float((vals < 0.05).mean())
        ax.hist(vals, bins=bin_edges, color=colors[model], alpha=0.55,
                edgecolor="black", linewidth=0.4,
                label=f"{model} (n={len(vals)}, p<0.05: {frac_sig:.0%})")
    ax.axvline(0.05, color="black", lw=0.7, ls="--", label="p=0.05")
    ax.set_xlabel("Spearman p (predicted vs actual)")
    ax.set_ylabel("Cell count")
    ax.set_title("Goodness-of-fit p-values")
    ax.legend(fontsize=8, loc="best")

    # Right: companion |ρ| distribution to show effect size.
    ax2 = axes[1]
    rho_bin_edges = np.linspace(-1.0, 1.0, 21)
    for model in models:
        rhos = valid[valid["model_name"] == model]["spearman_rho"].astype(float).values
        ax2.hist(rhos, bins=rho_bin_edges, color=colors[model], alpha=0.55,
                 edgecolor="black", linewidth=0.4,
                 label=f"{model} (med ρ={np.median(rhos):+.2f})")
    ax2.axvline(0.0, color="black", lw=0.7, ls="--")
    ax2.set_xlabel("Spearman ρ (predicted vs actual)")
    ax2.set_ylabel("Cell count")
    ax2.set_xlim(0, 1.0)
    ax2.set_title("Goodness-of-fit effect size")
    ax2.legend(fontsize=8, loc="best")

    if title:
        fig.suptitle(title)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Convenience entry: build all three figures + save
# ---------------------------------------------------------------------------

def main(component_type: str = "Shaft", strategy: str = "multi_prototype_pca",
         save_dir: Optional[str] = None):
    repo_conn = Connection("allen_data_repository")
    base = f"{component_type} | {strategy}"

    fig1 = plot_population_orth_tuning_curves(
        repo_conn, component_type, strategy,
        title=f"{base}  —  population orthogonal-tuning curves",
    )
    fig2 = plot_population_modulation_depth_histogram(
        repo_conn, component_type, strategy,
        title=f"{base}  —  population modulation-depth histogram",
    )
    fig3 = plot_population_spearman_p_histogram(
        repo_conn, component_type, strategy,
        title=f"{base}  —  population goodness-of-fit",
    )

    if save_dir:
        import os
        os.makedirs(save_dir, exist_ok=True)
        for label, fig in (("orth_tuning", fig1),
                           ("modulation_hist", fig2),
                           ("spearman_p_hist", fig3)):
            if fig is not None:
                path = os.path.join(save_dir, f"population_{component_type}_{strategy}_{label}.png")
                fig.savefig(path, dpi=150, bbox_inches="tight")
                print(f"  saved: {path}")
    else:
        plt.show()


if __name__ == "__main__":
    main()
