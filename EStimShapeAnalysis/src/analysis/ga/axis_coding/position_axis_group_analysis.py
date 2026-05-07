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
    # rpi = (
    #     df["r2_pos_only"].astype(float).values
    #     - df["r2_shape_only"].astype(float).values
    # )


    # formul a = pos_only - shape_only / max(pos_only, shape_only) to get a CV-based RPI that accounts for overall predictability; but for simplicity just do pos_only
    cols = ["r2_pos_only", "r2_shape_only"]
    df[cols] = df[cols].astype(float)

    rpi = (
            (df["r2_pos_only"] - df["r2_shape_only"])
            / df[cols].abs().max(axis=1)
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
    # formul a = pos_only - shape_only / max(pos_only, shape_only) to get a CV-based RPI that accounts for overall predictability; but for simplicity just do pos_only
    cols = ["r2_pos_only", "r2_shape_only"]
    df[cols] = df[cols].astype(float)

    df["rpi"] = (
            (df["r2_pos_only"] - df["r2_shape_only"])
            / df[cols].abs().max(axis=1)
    )




    # df["rpi"] = (
    #     df["r2_pos_only"].astype(float)
    #     - df["r2_shape_only"].astype(float)
    # )

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
# Variance partitioning (a.k.a. commonality analysis)
#
# Reference: de Heer, Huth, Griffiths, Gallant & Theunissen 2017, J Neurosci.
# Figs 4–5 use the same four-component decomposition for fMRI responses.
# Classical statistical source: Borcard, Legendre & Drapeau 1992, Ecology.
# ---------------------------------------------------------------------------

REGIME_ORDER: tuple[str, ...] = (
    "pos_only", "additive", "shape_only", "interaction", "redundant", "no_fit",
)
REGIME_PALETTE: dict[str, str] = {
    "pos_only":    "tab:blue",
    "shape_only":  "tab:orange",
    "additive":    "tab:green",
    "interaction": "tab:purple",
    "redundant":   "tab:gray",
    "no_fit":      "lightgray",
}


def _classify_regimes(
    df: pd.DataFrame,
    *,
    eps: float = 0.02,
    fit_threshold: float = 0.03,
) -> pd.DataFrame:
    """
    Decompose CV R² into the four variance shares and tag each row with a
    categorical regime label. Returns a copy with new columns:

      unique_pos        = R²_add − R²_shape   (position above-and-beyond shape)
      unique_shape      = R²_add − R²_pos     (shape above-and-beyond position)
      shared            = R²_pos + R²_shape − R²_add   (collinear contribution)
      interaction_extra = R²_int − R²_add     (cross-term beyond additive)

    Negative values are CV noise and are kept verbatim — the plots handle
    them.

    Regime rules (with epsilon ε for "indistinguishable from zero" and
    fit_threshold for "this cell is predictable at all"):

      no_fit       R²_int < fit_threshold
      interaction  interaction_extra > ε
      additive     unique_pos > ε  AND  unique_shape > ε
      pos_only     unique_pos > ε  AND  unique_shape ≤ ε
      shape_only   unique_shape > ε AND unique_pos ≤ ε
      redundant    fit but neither unique_* > ε (collinearity dominates)
    """
    df = df.copy()
    r2_p = df["r2_pos_only"].astype(float)
    r2_s = df["r2_shape_only"].astype(float)
    r2_a = df["r2_additive"].astype(float)
    r2_i = df["r2_interaction"].astype(float)

    df["unique_pos"] = r2_a - r2_s
    df["unique_shape"] = r2_a - r2_p
    df["shared"] = r2_p + r2_s - r2_a
    df["interaction_extra"] = r2_i - r2_a

    fit = r2_i.fillna(0.0) > fit_threshold
    has_int = df["interaction_extra"].fillna(0.0) > eps
    has_unique_pos = df["unique_pos"].fillna(0.0) > eps
    has_unique_shape = df["unique_shape"].fillna(0.0) > eps

    regime = pd.Series("no_fit", index=df.index, dtype=object)
    regime.loc[fit & has_int] = "interaction"
    regime.loc[fit & ~has_int & has_unique_pos & has_unique_shape] = "additive"
    regime.loc[fit & ~has_int & has_unique_pos & ~has_unique_shape] = "pos_only"
    regime.loc[fit & ~has_int & ~has_unique_pos & has_unique_shape] = "shape_only"
    regime.loc[fit & ~has_int & ~has_unique_pos & ~has_unique_shape] = "redundant"
    df["regime"] = regime
    return df


# ---------------------------------------------------------------------------
# Plot 5: regime pie chart (population + per-component-type)
# ---------------------------------------------------------------------------

def plot_regime_pie(
    indep_df: pd.DataFrame,
    *,
    eps: float = 0.02,
    fit_threshold: float = 0.03,
    save_path: Optional[str] = None,
) -> plt.Figure:
    """
    Pie of regime labels at the population scale plus one pie per
    component_type. Percentages are within-panel; counts are absolute.
    """
    if indep_df.empty:
        raise ValueError("AxisIndependenceMetrics is empty.")

    df = _classify_regimes(indep_df, eps=eps, fit_threshold=fit_threshold)
    types = sorted(df["component_type"].dropna().astype(str).unique())
    panels: list[tuple[str, pd.DataFrame]] = [("All", df)]
    for t in types:
        panels.append((t, df[df["component_type"] == t]))

    fig, axes = plt.subplots(
        1, len(panels), figsize=(4.0 * len(panels), 4.6),
        constrained_layout=True,
    )
    if len(panels) == 1:
        axes = [axes]

    for ax, (label, sub) in zip(axes, panels):
        counts = (
            sub["regime"].value_counts()
            .reindex(REGIME_ORDER, fill_value=0)
        )
        nz = counts[counts > 0]
        if len(nz) == 0:
            ax.text(0.5, 0.5, "no data", ha="center", va="center")
            ax.axis("off")
            ax.set_title(f"{label}  n=0")
            continue
        ax.pie(
            nz.values,
            labels=[f"{name}\n({n})" for name, n in nz.items()],
            colors=[REGIME_PALETTE[name] for name in nz.index],
            autopct="%1.0f%%",
            startangle=90,
            textprops={"fontsize": 8},
            wedgeprops={"edgecolor": "white", "linewidth": 0.6},
        )
        ax.set_title(f"{label}  n={len(sub)}", fontsize=10)

    fig.suptitle(
        f"Variance-partitioning regimes  |  ε={eps}  fit_threshold={fit_threshold}",
        fontsize=11,
    )
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"  saved: {save_path}")
    return fig


# ---------------------------------------------------------------------------
# Plot 6: per-cell stacked variance shares
# ---------------------------------------------------------------------------

def plot_variance_share_stacked(
    indep_df: pd.DataFrame,
    *,
    sort_by: str = "unique_pos",
    save_path: Optional[str] = None,
) -> plt.Figure:
    """
    Stacked-bar profile of every cell. One bar per cell, decomposed into
    four variance-share components: unique_pos (blue), shared (gray),
    unique_shape (orange), interaction_extra (purple). Cells are sorted
    by ``sort_by`` descending so the population gradient is readable.

    Negative shares (CV noise) stack downward at reduced alpha so the
    eye doesn't double-count them as positive contributions.
    """
    if indep_df.empty:
        raise ValueError("AxisIndependenceMetrics is empty.")
    df = _classify_regimes(indep_df).copy()
    if sort_by not in df.columns:
        raise ValueError(f"sort_by={sort_by} not in {list(df.columns)}")

    df = df.sort_values(by=sort_by, ascending=False).reset_index(drop=True)
    n = len(df)

    components = [
        ("unique_pos",        "tab:blue",   "unique position"),
        ("shared",            "tab:gray",   "shared (collinear)"),
        ("unique_shape",      "tab:orange", "unique shape"),
        ("interaction_extra", "tab:purple", "interaction extra"),
    ]

    fig, ax = plt.subplots(
        1, 1,
        figsize=(max(8.0, min(n * 0.06, 22.0)), 5.0),
        constrained_layout=True,
    )
    x = np.arange(n)
    bottom_pos = np.zeros(n)
    bottom_neg = np.zeros(n)
    for col, color, label in components:
        vals = df[col].astype(float).fillna(0.0).values
        pos_part = np.where(vals > 0, vals, 0)
        neg_part = np.where(vals < 0, vals, 0)
        ax.bar(
            x, pos_part, bottom=bottom_pos,
            color=color, alpha=0.85, label=label,
            width=1.0, edgecolor="none",
        )
        # Negative parts (CV noise) drawn faintly so they're visible but
        # don't dominate the impression. No legend entry — same color.
        if (neg_part != 0).any():
            ax.bar(
                x, neg_part, bottom=bottom_neg,
                color=color, alpha=0.30,
                width=1.0, edgecolor="none",
            )
        bottom_pos += pos_part
        bottom_neg += neg_part

    ax.axhline(0, color="black", lw=0.5)
    ax.set_xlabel(f"cells (sorted by {sort_by} descending)")
    ax.set_ylabel("CV R² contribution")
    ax.set_title(
        f"Per-cell variance partitioning  |  n={n}  "
        f"(unique_pos + shared + unique_shape + interaction_extra ≈ R²_int)",
        fontsize=10,
    )
    ax.legend(fontsize=8, loc="upper right")
    ax.grid(alpha=0.25, axis="y")
    ax.set_xlim(-0.5, n - 0.5)

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

    # Variance-partitioning thresholds for the regime classifier.
    # Reference: de Heer et al. 2017 J Neurosci (Figs 4–5) for the four-way
    # partition; Borcard, Legendre & Drapeau 1992 Ecology for the math.
    regime_epsilon = 0.02       # noise floor for unique / interaction shares
    fit_threshold = 0.03        # below this, the cell is unfit at all

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
        plot_regime_pie(
            indep_df,
            eps=regime_epsilon,
            fit_threshold=fit_threshold,
            save_path=os.path.join(save_dir, "variance_regime_pie.png"),
        )
        plt.close("all")
        plot_variance_share_stacked(
            indep_df,
            save_path=os.path.join(save_dir, "variance_share_stacked.png"),
        )
        plt.close("all")
    else:
        print(
            "[group] no AxisIndependenceMetrics rows — "
            "skipping independence plots."
        )

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
