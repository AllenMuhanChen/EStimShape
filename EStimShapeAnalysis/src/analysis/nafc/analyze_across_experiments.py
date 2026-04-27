"""
Compare % chose hypothesized shape across experiments.
x-axis: experiment label, y-axis: % chose hypothesized.
Two dots per x-position (or sub-position): EStim OFF (black) and EStim ON (colored).

Data is read from EStimShapeTrials in the central repository (allen_data_repository),
filtered by session_id derived from each experiment's DB name.
Each experiment is described by a config dict; see _DEFAULTS for all available keys.
"""

import os
import sys
from pathlib import Path

import matplotlib.cm as cm
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

sys.path.insert(0, str(Path(__file__).parent))

from clat.util.connection import Connection


# ===========================================================================
# Config defaults — every key below is optional in a per-experiment dict.
# ===========================================================================

_DEFAULTS = {
    # Gen-id range applied to ALL trials (ON and OFF)
    "start_gen_id":           0,
    "max_gen_id":             None,   # None = no upper limit

    # Additional gen-id range applied only to EStim ON trials
    # (useful when stimulation began mid-session)
    "start_gen_id_estim_on":  0,
    "max_gen_id_estim_on":    None,

    # trial_type column filter: None = include all
    "include_trial_types":    None,   # e.g. ['delta'] or ['variant', 'delta']

    # noise_chance column filter: None = include all
    "include_noise_chances":  None,   # e.g. [0.875, 0.85]
    # True  → pool all selected noise levels into one dot per ON/OFF
    # False → produce one dot per noise level per ON/OFF
    "combine_noise_chances":  True,

    # sample_length column filter: None = include all
    "include_sample_lengths": None,   # e.g. [400]

    # estim_spec_id filter applied only to ON trials: None = include all
    "include_spec_ids":       None,   # e.g. [3]
}


def _cfg(d: dict, key: str):
    return d.get(key, _DEFAULTS[key])


# ===========================================================================
# Data loading from EStimShapeTrials
# ===========================================================================

def _session_id_from_exp_db(exp_db: str) -> str:
    """Derive session_id from experiment DB name, e.g. 'allen_estimshape_exp_260426_0' → '260426_0'."""
    return exp_db.split("allen_estimshape_exp_")[-1]


_REPO_DB = "allen_data_repository"


def load_experiment_data(config: dict) -> pd.DataFrame:
    """Query EStimShapeTrials in the central repository for one experiment."""
    session_id = _session_id_from_exp_db(config["exp_db"])
    conn = Connection(_REPO_DB)

    start_gen = _cfg(config, "start_gen_id")
    max_gen   = _cfg(config, "max_gen_id")

    params = [session_id, start_gen]
    query = (
        "SELECT gen_id, noise_chance, sample_length, estim_spec_id, "
        "       is_estim_on, is_hypothesized_choice, trial_type "
        "FROM EStimShapeTrials "
        "WHERE session_id = %s AND gen_id >= %s"
    )
    if max_gen is not None:
        query += " AND gen_id <= %s"
        params.append(max_gen)

    conn.execute(query, tuple(params))
    rows = conn.fetch_all()

    df = pd.DataFrame(rows, columns=[
        "gen_id", "noise_chance", "sample_length", "estim_spec_id",
        "is_estim_on", "is_hypothesized_choice", "trial_type",
    ])

    if df.empty:
        return df

    df["is_estim_on"] = df["is_estim_on"].astype(int)
    df["is_hypothesized_choice"] = (
        pd.to_numeric(df["is_hypothesized_choice"], errors="coerce")
        .fillna(0).astype(int)
    )

    # Apply column-level filters shared between ON and OFF
    for cfg_key, col in [
        ("include_trial_types",    "trial_type"),
        ("include_noise_chances",  "noise_chance"),
        ("include_sample_lengths", "sample_length"),
    ]:
        vals = _cfg(config, cfg_key)
        if vals is not None:
            df = df[df[col].isin(set(vals))]

    return df.reset_index(drop=True)


def split_on_off(df: pd.DataFrame, config: dict) -> tuple:
    """Split into (df_on, df_off), applying ON-only gen-id and spec-id filters."""
    df_off = df[df["is_estim_on"] == 0].copy()

    df_on = df[df["is_estim_on"] == 1].copy()

    start_on = _cfg(config, "start_gen_id_estim_on")
    max_on   = _cfg(config, "max_gen_id_estim_on")
    df_on = df_on[df_on["gen_id"] >= start_on]
    if max_on is not None:
        df_on = df_on[df_on["gen_id"] <= max_on]

    spec_ids = _cfg(config, "include_spec_ids")
    if spec_ids is not None:
        df_on = df_on[df_on["estim_spec_id"].isin(set(spec_ids))]

    return df_on, df_off


# ===========================================================================
# Dot-value computation
# ===========================================================================

def _pct_hyp(df: pd.DataFrame) -> tuple:
    """Return (pct_hypothesized, n) for a subset DataFrame."""
    if df.empty:
        return None, 0
    return 100.0 * df["is_hypothesized_choice"].mean(), len(df)


def compute_dots(df_on: pd.DataFrame, df_off: pd.DataFrame, config: dict) -> list:
    """
    Return a list of dot-dicts: {label, pct_off, n_off, pct_on, n_on}.

    One element  when combine_noise_chances=True  (the optimised single-dot case).
    One per noise level when combine_noise_chances=False.
    """
    if _cfg(config, "combine_noise_chances"):
        pct_off, n_off = _pct_hyp(df_off)
        pct_on,  n_on  = _pct_hyp(df_on)
        return [dict(label="", pct_off=pct_off, n_off=n_off, pct_on=pct_on, n_on=n_on)]

    noise_levels = sorted(
        set(df_off["noise_chance"].dropna()) | set(df_on["noise_chance"].dropna())
    )
    dots = []
    for noise in noise_levels:
        pct_off, n_off = _pct_hyp(df_off[df_off["noise_chance"] == noise])
        pct_on,  n_on  = _pct_hyp(df_on[df_on["noise_chance"] == noise])
        dots.append(dict(
            label=f"N={noise * 100:.0f}%",
            pct_off=pct_off, n_off=n_off,
            pct_on=pct_on,   n_on=n_on,
        ))
    return dots


# ===========================================================================
# Plot
# ===========================================================================

_MARKERS    = ['o', 's', '^', 'D', 'v', 'P', '*', 'X']
_DOT_SPREAD = 0.28   # half-width of sub-dot spread for multi-dot experiments
_PAIR_GAP   = 0.10   # x-separation between the OFF and ON dot of one pair


def plot_across_experiments(experiments: list, save_path: str = None):
    """
    Parameters
    ----------
    experiments : list of per-experiment config dicts.
                  Required key: "label", "exp_db".
                  Optional keys: see _DEFAULTS.
    save_path   : path to save the PNG; directory is created automatically.
    """
    colors = cm.tab10(np.linspace(0, 1, max(len(experiments), 1)))

    # Load + compute all data first so the figure is drawn in one pass
    all_data = []
    for config, color in zip(experiments, colors):
        df = load_experiment_data(config)
        df_on, df_off = split_on_off(df, config)
        dots = compute_dots(df_on, df_off, config)
        all_data.append(dict(label=config["label"], dots=dots, color=color))

    n_exp      = len(all_data)
    max_ndots  = max(len(e["dots"]) for e in all_data)
    multi_dot  = max_ndots > 1

    fig_w = max(7, 2.4 * n_exp + (1.0 * max_ndots if multi_dot else 0))
    fig, ax = plt.subplots(figsize=(fig_w, 6))

    # legend bookkeeping
    off_patch_added = False
    exp_patches     = []           # one colored patch per experiment (for ON)
    noise_markers   = {}           # noise_label → dummy scatter handle

    for exp_idx, exp in enumerate(all_data):
        x_base = float(exp_idx)
        dots   = exp["dots"]
        color  = exp["color"]
        n_dots = len(dots)

        if n_dots == 1:
            sub_xs = [x_base]
        else:
            sub_xs = list(np.linspace(x_base - _DOT_SPREAD, x_base + _DOT_SPREAD, n_dots))

        for dot_idx, dot in enumerate(dots):
            marker = _MARKERS[dot_idx % len(_MARKERS)]
            x      = sub_xs[dot_idx]
            x_off  = x - _PAIR_GAP
            x_on   = x + _PAIR_GAP

            pct_off, n_off = dot["pct_off"], dot["n_off"]
            pct_on,  n_on  = dot["pct_on"],  dot["n_on"]

            # Line connecting OFF → ON for this dot pair
            if pct_off is not None and pct_on is not None:
                ax.plot([x_off, x_on], [pct_off, pct_on],
                        color=color, alpha=0.45, linewidth=1.5, zorder=1)

            # EStim OFF dot (black)
            if pct_off is not None:
                ax.scatter(x_off, pct_off, color="black", marker=marker,
                           s=90, zorder=3, edgecolors="none")
                ax.text(x_off, pct_off - 3.0, f"n={n_off}",
                        ha="center", va="top", fontsize=7, color="dimgray")
                if not off_patch_added:
                    off_patch_added = True

            # EStim ON dot (experiment color)
            if pct_on is not None:
                ax.scatter(x_on, pct_on, color=color, marker=marker,
                           s=90, zorder=3, edgecolors="black", linewidths=0.6)
                ax.text(x_on, pct_on + 1.5, f"n={n_on}",
                        ha="center", va="bottom", fontsize=7, color=color)

            # Collect noise-level marker for legend (multi-dot mode only)
            if multi_dot and dot["label"] and dot["label"] not in noise_markers:
                h = ax.scatter([], [], marker=marker, color="gray", s=60,
                               label=dot["label"])
                noise_markers[dot["label"]] = h

        # Per-experiment color patch for ON legend
        exp_patches.append(mpatches.Patch(color=color, label=exp["label"]))

    # 50 % chance reference line
    ax.axhline(50, color="gray", linestyle="--", linewidth=1, alpha=0.5)
    ax.text(n_exp - 0.5, 51.5, "50% chance",
            va="bottom", ha="right", fontsize=8, color="gray")

    ax.set_xticks(range(n_exp))
    ax.set_xticklabels([e["label"] for e in all_data], fontsize=11,
                       rotation=20, ha="right")
    ax.set_ylabel("% Chose Hypothesized Shape", fontsize=13)
    ax.set_xlabel("Experiment", fontsize=13)
    ax.set_title("EStim Effect Across Experiments: % Chose Hypothesized", fontsize=14)
    ax.set_ylim([0, 110])
    ax.set_xlim([-0.6, n_exp - 0.4])
    ax.grid(True, alpha=0.3, axis="y")

    # Legend: OFF swatch | per-experiment ON swatches | noise-level markers (if multi-dot)
    legend_handles = []
    legend_labels  = []
    if off_patch_added:
        legend_handles.append(mpatches.Patch(color="black", label="EStim OFF"))
        legend_labels.append("EStim OFF")
    for p in exp_patches:
        legend_handles.append(p)
        legend_labels.append(p.get_label() + " (ON)")
    for lbl, h in noise_markers.items():
        legend_handles.append(h)
        legend_labels.append(lbl)
    if legend_handles:
        ax.legend(legend_handles, legend_labels, fontsize=9,
                  loc="upper right", framealpha=0.85, borderpad=0.7)

    plt.tight_layout()

    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        fig.savefig(save_path, bbox_inches="tight", dpi=150)
        print(f"Saved to {save_path}")

    plt.show()
    return fig


# ===========================================================================
# Main — edit experiments list here
# ===========================================================================

def main():
    experiments = [
        {
            "label":   "260426",
            "exp_db":  "allen_estimshape_exp_260426_0",

            # Gen-id range (ON and OFF)
            "start_gen_id":           2,
            "max_gen_id":             None,

            # Extra gen-id range for ON trials only
            "start_gen_id_estim_on":  0,
            "max_gen_id_estim_on":    None,

            # Filters
            "include_trial_types":    None,           # e.g. ['delta']
            "include_noise_chances":  [0.875, 0.85],
            "combine_noise_chances":  True,
            "include_sample_lengths": None,
            "include_spec_ids":       [3],
        },
        # Add more experiments here, e.g.:
        # {
        #     "label":                  "250301",
        #     "exp_db":                 "allen_estimshape_exp_250301_0",
        #     "start_gen_id":           1,
        #     "max_gen_id":             None,
        #     "start_gen_id_estim_on":  0,
        #     "max_gen_id_estim_on":    None,
        #     "include_trial_types":    None,
        #     "include_noise_chances":  [0.875],
        #     "combine_noise_chances":  True,
        #     "include_sample_lengths": None,
        #     "include_spec_ids":       None,
        # },
    ]

    plot_across_experiments(
        experiments,
        save_path="/home/connorlab/Documents/plots/across_experiments/pct_hypothesized.png",
    )


if __name__ == "__main__":
    main()
