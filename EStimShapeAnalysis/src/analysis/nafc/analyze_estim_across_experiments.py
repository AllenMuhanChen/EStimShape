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
        if isinstance(vals, (list, set, tuple)):
            unique_before = sorted(df[col].dropna().unique())
            before = len(df)
            df = df[df[col].isin(set(vals))]
            if len(df) == 0:
                print(f"  WARNING: '{cfg_key}={vals}' filtered out all {before} rows. "
                      f"Values present in data: {unique_before}")

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


def plot_across_experiments(experiments: list, save_path: str = None,
                            show_n: bool = True,
                            show_effect_size: bool = True,
                            x_spacing: float = 1.0,
                            width_per_exp: float = 1.5):
    """
    Parameters
    ----------
    experiments : list of per-experiment config dicts.
                  Required key: "label", "exp_db".
                  Optional keys: see _DEFAULTS.
    save_path   : path to save the PNG; directory is created automatically.
    """
    # Load + compute all data first so the figure is drawn in one pass
    all_data = []
    for config in experiments:
        session_id = _session_id_from_exp_db(config["exp_db"])
        df = load_experiment_data(config)
        print(f"[{config['label']}] session_id={session_id}  rows loaded={len(df)}")
        df_on, df_off = split_on_off(df, config)
        print(f"  → ON={len(df_on)}  OFF={len(df_off)}")
        dots = compute_dots(df_on, df_off, config)
        all_data.append(dict(label=config["label"], dots=dots))

    n_exp      = len(all_data)
    max_ndots  = max(len(e["dots"]) for e in all_data)
    multi_dot  = max_ndots > 1

    _LEGEND_W = 1.5   # inches reserved for the right-side legend
    fig_w = width_per_exp * n_exp * x_spacing + (0.8 * max_ndots if multi_dot else 0) + _LEGEND_W
    fig, ax = plt.subplots(figsize=(fig_w, 6), constrained_layout=True)

    _COLOR_OFF = "black"
    _COLOR_ON  = "red"

    noise_markers = {}   # noise_label → dummy scatter handle (multi-dot legend)

    for exp_idx, exp in enumerate(all_data):
        x_base = float(exp_idx) * x_spacing
        dots   = exp["dots"]
        n_dots = len(dots)

        if n_dots == 1:
            sub_xs = [x_base]
        else:
            sub_xs = list(np.linspace(x_base - _DOT_SPREAD, x_base + _DOT_SPREAD, n_dots))

        for dot_idx, dot in enumerate(dots):
            marker = _MARKERS[dot_idx % len(_MARKERS)]
            x      = sub_xs[dot_idx]

            pct_off, n_off = dot["pct_off"], dot["n_off"]
            pct_on,  n_on  = dot["pct_on"],  dot["n_on"]

            # Vertical line
            if pct_off is not None and pct_on is not None:
                ax.plot([x, x], [pct_off, pct_on],
                        color="gray", alpha=0.6, linewidth=1.5, zorder=1)

            # Effect size annotation at midpoint of the line
            if show_effect_size and pct_off is not None and pct_on is not None:
                effect = pct_on - pct_off
                mid_y  = (pct_on + pct_off) / 2
                sign   = "+" if effect >= 0 else ""
                ax.text(x + 0.06, mid_y, f"{sign}{effect:.1f}%",
                        ha="left", va="center", fontsize=8,
                        color="red" if effect >= 0 else "black")

            # EStim OFF dot
            if pct_off is not None:
                ax.scatter(x, pct_off, color=_COLOR_OFF, marker=marker,
                           s=90, zorder=3, edgecolors="none")
                if show_n:
                    ax.text(x - 0.06, pct_off, f"n={n_off}",
                            ha="right", va="center", fontsize=7, color="dimgray")

            # EStim ON dot
            if pct_on is not None:
                ax.scatter(x, pct_on, color=_COLOR_ON, marker=marker,
                           s=90, zorder=3, edgecolors="black", linewidths=0.6)
                if show_n:
                    ax.text(x + 0.06, pct_on, f"n={n_on}",
                            ha="left", va="center", fontsize=7, color=_COLOR_ON)

            # Noise-level marker legend entry (multi-dot mode only)
            if multi_dot and dot["label"] and dot["label"] not in noise_markers:
                noise_markers[dot["label"]] = ax.scatter(
                    [], [], marker=marker, color="gray", s=60)

    # 50 % chance reference line
    x_margin = 0.5 * x_spacing
    ax.set_yticks(range(0, 101, 10))

    ax.set_xticks([i * x_spacing for i in range(n_exp)])
    ax.set_xticklabels([e["label"] for e in all_data], fontsize=11,
                       rotation=45, ha="center")
    ax.set_ylabel("% Chose Hypothesized Shape", fontsize=13)
    ax.set_xlabel("Experiment", fontsize=13)
    title_fontsize = max(7, fig_w * 14 / 7.5)
    # ax.set_title("EStim Effect Across Experiments: % Chose Hypothesized", fontsize=title_fontsize)
    ax.set_ylim([0, 100])
    ax.set_xlim([-x_margin, (n_exp - 1) * x_spacing + x_margin])
    ax.invert_xaxis()
    ax.grid(True, alpha=0.3, axis="y")

    # Legend: OFF (black) | ON (red) | noise-level markers if multi-dot
    legend_handles = [
        mpatches.Patch(color=_COLOR_OFF, label="EStim OFF"),
        mpatches.Patch(color=_COLOR_ON,  label="EStim ON"),
    ]
    legend_labels = ["EStim OFF", "EStim ON"]
    for lbl, h in noise_markers.items():
        legend_handles.append(h)
        legend_labels.append(lbl)
    ax.legend(legend_handles, legend_labels, fontsize=9,
              loc="upper left", bbox_to_anchor=(1.01, 1),
              framealpha=0.85, borderpad=0.7)

    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        fig.savefig(save_path, bbox_inches="tight", dpi=150)
        # also save SVG for vector graphics (same path but .svg extension)
        svg_path = save_path.rsplit(".", 1)[0] + ".svg"
        fig.savefig(svg_path, bbox_inches="tight")
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
            "max_gen_id":             5,

            # Extra gen-id range for ON trials only
            "start_gen_id_estim_on":  0,
            "max_gen_id_estim_on":    None,

            # Filters
            "include_trial_types":    ["Delta Shape"],
            "include_noise_chances":  [0.875, 0.85],
            "combine_noise_chances":  True,
            "include_sample_lengths": None,
            "include_spec_ids":       [3],
        },
        {
            "label":                  "260423",
            "exp_db":                 "allen_estimshape_exp_260423_0",
            "start_gen_id":           3,
            "max_gen_id":             6,
            "start_gen_id_estim_on":  0,
            "max_gen_id_estim_on":    None,
            "include_trial_types":    ['Hypothesized Shape'],
            "include_noise_chances":  [0.90],
            "combine_noise_chances":  True,
            "include_sample_lengths": True,
            "include_spec_ids":       [1],
        },
        {
            "label": "260414",
            "exp_db": "allen_estimshape_exp_260414_0",
            "start_gen_id": 3,
            "max_gen_id": 6,
            "start_gen_id_estim_on": 0,
            "max_gen_id_estim_on": None,
            "include_trial_types": ['Hypothesized Shape'],
            "include_noise_chances": [0.90],
            "combine_noise_chances": True,
            "include_sample_lengths": True,
            "include_spec_ids": [2],
        },
        {
            "label": "260407",
            "exp_db": "allen_estimshape_exp_260407_0",
            "start_gen_id": 3,
            "max_gen_id": None,
            "start_gen_id_estim_on": 0,
            "max_gen_id_estim_on": None,
            "include_trial_types": ['Delta Shape'],
            "include_noise_chances": [0.85],
            "combine_noise_chances": False,
            "include_sample_lengths": [500],
            "include_spec_ids": [3],
        },
        {
            "label": "260402",
            "exp_db": "allen_estimshape_exp_260402_0",
            "start_gen_id": 2,
            "max_gen_id": 9,
            "start_gen_id_estim_on": 0,
            "max_gen_id_estim_on": None,
            "include_trial_types": ['Delta Shape'],
            "include_noise_chances": [0.90],
            "combine_noise_chances": False,
            "include_sample_lengths": [1000],
            "include_spec_ids": [2,4],
        },
    ]

    plot_across_experiments(
        experiments,
        save_path="/home/connorlab/Documents/plots/across_experiments/pct_hypothesized.png",
        show_n=False,
        show_effect_size=False,
        x_spacing=0.5,       # reduce to compress experiments closer together (1.0 = default spacing)
        width_per_exp=1.0,   # inches per experiment slot
    )


if __name__ == "__main__":
    main()
