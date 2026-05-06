"""
Population-level plots from AxisIndependenceMetrics and
AxisCompositionMetrics, joined where useful with AxisCodingFitMetrics.

Reads the data repository, writes one figure per analysis to a save dir.
Run after ``run_position_axis_batch`` has populated the tables.

Edit the variables in ``main()`` and run this file directly.

Plots produced:

  1. independence_summary
        2 panels:
          (A) histogram of interaction_gap (R^2_int - R^2_add) — how
              much shape × position interaction the population shows.
          (B) scatter of R^2_pos_only vs R^2_shape_only with diagonal —
              every neuron a dot, color by component_type.

  2. composition_summary
        2 panels:
          (A) histogram of preferred-axis PSI (R^2_pos - R^2_shape) with
              chance-baseline lines from the table.
          (B) preferred PSI vs orth-axes median PSI per cell — shows
              whether the preferred axis is more position-loaded than its
              own orthogonal complement.

  3. composition_by_component_type
        Box / strip plot of preferred-axis PSI grouped by component_type.

Each plot has its own ``plot_*`` function, callable individually if you
want a single figure.
"""

from __future__ import annotations

import os
from typing import Optional

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_independence(repo_conn, **filters) -> pd.DataFrame:
    from src.repository.export_axis_independence import (
        read_axis_independence_metrics,
    )
    return read_axis_independence_metrics(repo_conn, **filters)


def load_composition(repo_conn, **filters) -> pd.DataFrame:
    from src.repository.export_axis_independence import (
        read_axis_composition_metrics,
    )
    return read_axis_composition_metrics(repo_conn, **filters)


# ---------------------------------------------------------------------------
# Plot 1: independence summary
# ---------------------------------------------------------------------------

def plot_independence_summary(
    df: pd.DataFrame,
    *,
    save_path: Optional[str] = None,
) -> plt.Figure:
    if df.empty:
        raise ValueError("AxisIndependenceMetrics is empty.")

    fig, axes = plt.subplots(1, 2, figsize=(13, 5), constrained_layout=True)

    # (A) interaction_gap histogram.
    ax = axes[0]
    gap = df["interaction_gap"].astype(float).dropna().values
    ax.hist(gap, bins=30, color="tab:purple", alpha=0.85, edgecolor="black", lw=0.4)
    ax.axvline(0, color="grey", lw=0.8, ls="--")
    median = float(np.median(gap)) if gap.size else float("nan")
    pos_frac = float(np.mean(gap > 0)) if gap.size else float("nan")
    ax.set_xlabel("interaction gap = R²_int − R²_add  (CV)")
    ax.set_ylabel("# neurons")
    ax.set_title(
        f"Shape × position interaction  |  n={gap.size}  "
        f"median={median:+.3f}  P(gap>0)={pos_frac:.2f}"
    )
    ax.grid(alpha=0.25)

    # (B) RPI vs interaction_gap, colored by component_type.
    # RPI = R²_pos_only − R²_shape_only is the CV-based response position
    # index — positive means position alone explains more held-out variance
    # than shape alone. Pairing it against the interaction gap on the
    # y-axis answers "do certain groups / RPI values have certain
    # interaction effects".
    ax = axes[1]
    rpi = (
        df["r2_pos_only"].astype(float).values
        - df["r2_shape_only"].astype(float).values
    )
    gap = df["interaction_gap"].astype(float).values
    ctypes = df["component_type"].astype(str).values
    palette = {
        "Shaft": "tab:blue",
        "Termination": "tab:orange",
        "Junction": "tab:green",
    }
    for ctype in np.unique(ctypes):
        sel = ctypes == ctype
        ax.scatter(
            rpi[sel], gap[sel],
            s=20, alpha=0.7,
            color=palette.get(ctype, "tab:gray"),
            edgecolors="black", linewidths=0.3,
            label=f"{ctype} (n={int(sel.sum())})",
        )
    ax.axhline(0, color="grey", lw=0.8, ls="--")
    ax.axvline(0, color="grey", lw=0.8, ls="--")
    ax.set_xlabel("RPI = R²_pos_only − R²_shape_only  (CV)")
    ax.set_ylabel("interaction gap = R²_int − R²_add  (CV)")
    ax.set_title(
        "Per-cell interaction effect by RPI and component type"
    )
    ax.legend(fontsize=8, loc="best")
    ax.grid(alpha=0.25)

    fig.suptitle("Axis independence — population summary", fontsize=12)
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"  saved: {save_path}")
    return fig


# ---------------------------------------------------------------------------
# Plot 2: composition summary
# ---------------------------------------------------------------------------

def plot_composition_summary(
    comp_df: pd.DataFrame,
    *,
    save_path: Optional[str] = None,
) -> plt.Figure:
    if comp_df.empty:
        raise ValueError("AxisCompositionMetrics is empty.")

    fig, axes = plt.subplots(1, 2, figsize=(13, 5), constrained_layout=True)

    # (A) Preferred-axis PSI histogram.
    ax = axes[0]
    pref = comp_df[comp_df["axis_label"] == "preferred"]
    psi = pref["psi"].astype(float).dropna().values
    chance = pref["chance_baseline_pos"].astype(float).dropna().values
    ax.hist(psi, bins=30, color="tab:blue", alpha=0.85, edgecolor="black", lw=0.4)
    ax.axvline(0, color="grey", lw=0.8, ls="--")
    if chance.size:
        # Convert chance R^2_pos -> PSI assuming a random axis would have
        # R^2_pos ≈ chance and R^2_shape ≈ 1 - chance, so PSI_chance =
        # 2*chance - 1. Plot the median across (component_type) baselines.
        chance_psi = 2.0 * float(np.median(chance)) - 1.0
        ax.axvline(
            chance_psi, color="tab:red", lw=1.0, ls=":",
            label=f"chance PSI ≈ {chance_psi:+.2f}",
        )
        ax.legend(fontsize=8, loc="best")
    median = float(np.median(psi)) if psi.size else float("nan")
    ax.set_xlabel("preferred-axis PSI = R²_pos − R²_shape")
    ax.set_ylabel("# neurons")
    ax.set_title(
        f"Preferred-axis composition  |  n={psi.size}  median={median:+.2f}"
    )
    ax.grid(alpha=0.25)

    # (B) preferred PSI vs median orth-axes PSI per cell.
    ax = axes[1]
    key = ["session_id", "unit_name", "component_type", "strategy"]
    pref_psi = (
        pref.set_index(key)["psi"].astype(float).rename("psi_pref")
    )
    orth = comp_df[comp_df["axis_label"] != "preferred"]
    orth_psi = (
        orth.groupby(key)["psi"].median().astype(float).rename("psi_orth_median")
    )
    joined = pd.concat([pref_psi, orth_psi], axis=1, join="inner").reset_index()
    if joined.empty:
        ax.text(0.5, 0.5, "no rows with both preferred + orth axes",
                ha="center", va="center")
        ax.axis("off")
    else:
        ctypes = joined["component_type"].values
        palette = {
            "Shaft": "tab:blue",
            "Termination": "tab:orange",
            "Junction": "tab:green",
        }
        for ctype in np.unique(ctypes):
            sel = ctypes == ctype
            ax.scatter(
                joined.loc[sel, "psi_orth_median"].values,
                joined.loc[sel, "psi_pref"].values,
                s=20, alpha=0.7,
                color=palette.get(ctype, "tab:gray"),
                edgecolors="black", linewidths=0.3,
                label=f"{ctype} (n={int(sel.sum())})",
            )
        lim = max(
            float(np.abs(joined[["psi_pref", "psi_orth_median"]].values).max()),
            0.5,
        )
        ax.plot([-lim, lim], [-lim, lim], color="grey", lw=0.8, ls="--",
                label="y = x")
        ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim)
        ax.set_xlabel("median PSI across orthogonal PCs")
        ax.set_ylabel("preferred-axis PSI")
        ax.set_title("Preferred axis vs its orthogonal complement (per cell)")
        ax.legend(fontsize=8, loc="best")
        ax.grid(alpha=0.25)

    fig.suptitle("Axis composition — population summary", fontsize=12)
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"  saved: {save_path}")
    return fig


# ---------------------------------------------------------------------------
# Plot 3: composition by component type
# ---------------------------------------------------------------------------

def plot_composition_by_component_type(
    comp_df: pd.DataFrame,
    *,
    save_path: Optional[str] = None,
) -> plt.Figure:
    if comp_df.empty:
        raise ValueError("AxisCompositionMetrics is empty.")

    pref = comp_df[comp_df["axis_label"] == "preferred"].copy()
    fig, ax = plt.subplots(1, 1, figsize=(8, 5), constrained_layout=True)

    types = sorted(pref["component_type"].dropna().unique())
    palette = {
        "Shaft": "tab:blue",
        "Termination": "tab:orange",
        "Junction": "tab:green",
    }
    data = [
        pref.loc[pref["component_type"] == t, "psi"].astype(float).dropna().values
        for t in types
    ]
    counts = [len(d) for d in data]

    bp = ax.boxplot(
        data, positions=range(len(types)), widths=0.5,
        patch_artist=True, showfliers=False,
    )
    for patch, t in zip(bp["boxes"], types):
        patch.set_facecolor(palette.get(t, "lightgray"))
        patch.set_alpha(0.6)

    rng = np.random.default_rng(0)
    for i, (t, d) in enumerate(zip(types, data)):
        if d.size == 0:
            continue
        jitter = rng.uniform(-0.12, 0.12, size=d.size)
        ax.scatter(
            np.full(d.size, i) + jitter, d,
            s=12, alpha=0.6,
            color=palette.get(t, "tab:gray"),
            edgecolors="black", linewidths=0.2,
        )

    ax.axhline(0, color="grey", lw=0.8, ls="--")
    ax.set_xticks(range(len(types)))
    ax.set_xticklabels([f"{t}\nn={n}" for t, n in zip(types, counts)])
    ax.set_ylabel("preferred-axis PSI = R²_pos − R²_shape")
    ax.set_title("Preferred-axis composition by component type")
    ax.grid(alpha=0.25, axis="y")

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"  saved: {save_path}")
    return fig


# ---------------------------------------------------------------------------
# Plot 4: independence (CV-based RPI) by component type
# ---------------------------------------------------------------------------

def plot_independence_by_component_type(
    indep_df: pd.DataFrame,
    *,
    save_path: Optional[str] = None,
) -> plt.Figure:
    """
    Box + strip plot of the CV-based response position index
    RPI = R²_pos_only − R²_shape_only grouped by component_type. Same
    layout as plot_composition_by_component_type, but the index comes
    from cross-validated response variance partitioning rather than
    OLS axis-projection partitioning.
    """
    if indep_df.empty:
        raise ValueError("AxisIndependenceMetrics is empty.")

    df = indep_df.copy()
    df["rpi"] = (
        df["r2_pos_only"].astype(float)
        - df["r2_shape_only"].astype(float)
    )

    fig, ax = plt.subplots(1, 1, figsize=(8, 5), constrained_layout=True)

    types = sorted(df["component_type"].dropna().unique())
    palette = {
        "Shaft": "tab:blue",
        "Termination": "tab:orange",
        "Junction": "tab:green",
    }
    data = [
        df.loc[df["component_type"] == t, "rpi"].dropna().values
        for t in types
    ]
    counts = [len(d) for d in data]

    bp = ax.boxplot(
        data, positions=range(len(types)), widths=0.5,
        patch_artist=True, showfliers=False,
    )
    for patch, t in zip(bp["boxes"], types):
        patch.set_facecolor(palette.get(t, "lightgray"))
        patch.set_alpha(0.6)

    rng = np.random.default_rng(0)
    for i, (t, d) in enumerate(zip(types, data)):
        if d.size == 0:
            continue
        jitter = rng.uniform(-0.12, 0.12, size=d.size)
        ax.scatter(
            np.full(d.size, i) + jitter, d,
            s=12, alpha=0.6,
            color=palette.get(t, "tab:gray"),
            edgecolors="black", linewidths=0.2,
        )

    ax.axhline(0, color="grey", lw=0.8, ls="--")
    ax.set_xticks(range(len(types)))
    ax.set_xticklabels([f"{t}\nn={n}" for t, n in zip(types, counts)])
    ax.set_ylabel("RPI = R²_pos_only − R²_shape_only  (CV)")
    ax.set_title("Response position index by component type")
    ax.grid(alpha=0.25, axis="y")

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"  saved: {save_path}")
    return fig


# ---------------------------------------------------------------------------
# Entry point — edit the variables below and run this file directly.
# ---------------------------------------------------------------------------

def main():
    # Where to save the figures.
    save_dir = "/home/connorlab/Documents/plots/axis_coding_group"

    # Optional filters when reading the tables. Leave None to read all rows.
    component_type = None
    strategy = "multi_prototype_pca"

    # ----------------------------------------------------------------------

    os.makedirs(save_dir, exist_ok=True)

    from clat.util.connection import Connection
    repo_conn = Connection("allen_data_repository")

    print("[group] reading AxisIndependenceMetrics …")
    indep_df = load_independence(
        repo_conn, component_type=component_type, strategy=strategy,
    )
    print(f"  {len(indep_df)} rows.")

    print("[group] reading AxisCompositionMetrics …")
    comp_df = load_composition(
        repo_conn, component_type=component_type, strategy=strategy,
    )
    print(f"  {len(comp_df)} rows.")

    if not indep_df.empty:
        plot_independence_summary(
            indep_df,
            save_path=os.path.join(save_dir, "independence_summary.png"),
        )
        plt.close("all")
        plot_independence_by_component_type(
            indep_df,
            save_path=os.path.join(
                save_dir, "independence_by_component_type.png",
            ),
        )
        plt.close("all")
    else:
        print("[group] no AxisIndependenceMetrics rows — skipping plots 1 & 4.")

    if not comp_df.empty:
        plot_composition_summary(
            comp_df,
            save_path=os.path.join(save_dir, "composition_summary.png"),
        )
        plt.close("all")
        plot_composition_by_component_type(
            comp_df,
            save_path=os.path.join(save_dir, "composition_by_component_type.png"),
        )
        plt.close("all")
    else:
        print("[group] no AxisCompositionMetrics rows — skipping plots 2 & 3.")


if __name__ == "__main__":
    main()
