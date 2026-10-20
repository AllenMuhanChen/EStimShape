"""
EStim effect vs EStim parameter fitness, every qualifying condition across sessions.

Conditions, effects and filters are exactly those of avg_estim_per_experiment
(same parameters at the top of main()): every condition with >= min_trials EStim ON
and OFF trials, effect = % ON − % OFF against its own OFF baseline (or the
two-proportion z with studentize), optional trial-type filter, current : half-distance
ratio exclusions, and merge_behavioral (one value per session × trial type × spec).

Parameter fitness, per condition:
    ratio   = current_per_second / corr half-distance of its estim spec
              (avg_estim_per_experiment.get_spec_ratios)
    fitness = 1 / (1 + |ratio − center|),  center from ESTIM_DISTANCE_CENTERS
              (Hypothesized Shape 4, Delta Shape 0)
so 1 = at the center and it falls toward 0 with distance. Conditions whose trial type
has no center, or whose spec has no ratio, have no fitness and are left out (counted
in the printout).

Optional least-squares line of effect on fitness, with slope, r², p and n in a box
beside the plot. Spearman ρ is printed.

Outputs go to a timestamped folder: config.json, points.csv (one row per dot),
estim_fitness_scatter.png/.svg.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from scipy import stats as sp_stats

sys.path.insert(0, str(Path(__file__).parents[3]))

from src.analysis.nafc.group_analysis.analyze_estim_by_condition import (
    METRIC_PCT_HYP_VS_DELTA)
from src.analysis.nafc.group_analysis.avg_estim_per_experiment import (
    ESTIM_DISTANCE_CENTERS, _condition_arrays, _condition_ratio, _effect_axis_label,
    collect_session_rows)

FITNESS_LABEL = "EStim parameter fitness"
TRIAL_TYPE_COLORS = {"Hypothesized Shape": "#c0392b", "Delta Shape": "#2c7fb8"}
SINGLE_COLOR = "#2c7fb8"   # color_by='none'
COLOR_BY = ("trial type", "none")


def condition_fitness(session_id, cond_dict, centers=ESTIM_DISTANCE_CENTERS):
    """1 / (1 + |ratio − center|), or None (no center for the trial type, or no ratio)."""
    center = centers.get(cond_dict.get('trial_type'))
    if center is None:
        return None
    ratio = _condition_ratio(session_id, cond_dict)
    if ratio is None:
        return None
    return 1.0 / (1.0 + abs(ratio - center))


def build_points(rows, studentize=False, merge_behavioral=False):
    """One row per condition (or per spec with merge_behavioral) with a fitness:
    session_id, trial_type, estim_spec_id, ratio, fitness, effect. Also returns how many
    units had no fitness."""
    arrays = _condition_arrays(rows, studentize=studentize, merge_behavioral=merge_behavioral)
    points, n_missing = [], 0
    for (sid, cond), effect in zip(arrays['keys'], arrays['effects']):
        fitness = condition_fitness(sid, cond)
        if fitness is None:
            n_missing += 1
            continue
        points.append({'session_id': sid, 'trial_type': cond.get('trial_type'),
                       'estim_spec_id': cond.get('estim_spec_id'),
                       'ratio': _condition_ratio(sid, cond), 'fitness': fitness,
                       'effect': float(effect),
                       'conditions': json.dumps(cond, default=str)})
    return pd.DataFrame(points), n_missing


def plot_fitness_scatter(points, studentize=False, merge_behavioral=False,
                         color_by="trial type", fit_line=True):
    x, y = points['fitness'].to_numpy(), points['effect'].to_numpy()
    fit = (sp_stats.linregress(x, y)
           if fit_line and len(x) >= 3 and np.ptp(x) > 0 else None)

    if fit is not None:
        fig, (ax, ax_box) = plt.subplots(1, 2, figsize=(9.5, 6),
                                         gridspec_kw={'width_ratios': [6.5, 2]})
    else:
        fig, ax = plt.subplots(figsize=(7.5, 6))
    ax.axhline(0, color="black", linewidth=1, zorder=1)
    if color_by == "none":
        ax.scatter(x, y, color=SINGLE_COLOR, s=50, alpha=0.75, zorder=3)
    else:
        fallback = iter(["#27ae60", "#8e44ad", "#e67e22", "#555555"] * 4)
        types = points['trial_type'].to_numpy()
        for tt in [t for t in ESTIM_DISTANCE_CENTERS if t in set(types)]:
            on = types == tt
            ax.scatter(x[on], y[on], color=TRIAL_TYPE_COLORS.get(tt) or next(fallback),
                       s=50, alpha=0.75, zorder=3, label=tt)
    if fit is not None:
        xs = np.linspace(0, 1.03, 100)
        ax.plot(xs, fit.slope * xs + fit.intercept, color="black", linewidth=1.8,
                zorder=2, label="Linear fit")
        ax_box.axis("off")
        p_txt = "p < 0.001" if fit.pvalue < 0.001 else f"p = {fit.pvalue:.3f}"
        ax_box.text(0.0, 0.5, f"Linear fit\nslope = {fit.slope:+.2f}\n"
                              f"r² = {fit.rvalue ** 2:.2f}\n{p_txt}\nn = {len(x)}",
                    transform=ax_box.transAxes, ha="left", va="center", fontsize=14,
                    linespacing=1.5,
                    bbox=dict(boxstyle="round,pad=0.5", facecolor="white",
                              edgecolor="#cccccc"))
    if ax.get_legend_handles_labels()[0]:
        ax.legend(fontsize=13, frameon=False, loc="lower right")
    ax.set_xlim(0, 1.03)   # fitness is in (0, 1]
    ax.set_xlabel(FITNESS_LABEL, fontsize=16)
    ax.set_ylabel(_effect_axis_label(studentize, merge_behavioral), fontsize=14)
    ax.set_title("EStim effect vs parameter fitness", fontsize=17)
    ax.tick_params(labelsize=13)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    fig.tight_layout()
    return fig, fit


def main():
    # --- Same filtering options as avg_estim_per_experiment.main() ---
    metric = METRIC_PCT_HYP_VS_DELTA
    exclude_session_ids = ["260421_0", "260410_0"]
    start_session_id = "260402_0"
    algorithm_label = 'None'
    trial_types = None                    # None = all, e.g. ['Hypothesized Shape', 'Delta Shape']
    exclude_ratio_ranges = [(8, None)]    # drop ratio >= 8; None = keep all
    merge_behavioral = True               # one dot per (session, trial type, spec)
    studentize = False                    # True -> effect in z (two-proportion z-score)
    min_trials = 10

    # --- This plot ---
    color_by = "trial type"   # "trial type" or "none" (all dots one color)
    fit_line = True           # least-squares line + stats box beside the plot
    show_plots = True
    output_root = "/home/connorlab/Documents/plots/across_experiments/estim_fitness_scatter"

    if color_by not in COLOR_BY:
        raise ValueError(f"color_by must be one of {COLOR_BY}, got {color_by!r}")
    rows = collect_session_rows(exclude_session_ids, start_session_id, algorithm_label,
                                metric, min_trials=min_trials, trial_types=trial_types,
                                exclude_ratio_ranges=exclude_ratio_ranges)
    if not rows:
        raise RuntimeError("No sessions with qualifying conditions.")
    points, n_missing = build_points(rows, studentize=studentize,
                                     merge_behavioral=merge_behavioral)
    if points.empty:
        raise RuntimeError(f"None of the {n_missing} conditions has a parameter fitness "
                           "(needs a trial type in ESTIM_DISTANCE_CENTERS and a ratio).")
    print(f"\n{len(points)} dots from {points['session_id'].nunique()} sessions; "
          f"{n_missing} without a fitness left out")
    if len(points) >= 3 and np.ptp(points['fitness']) > 0:
        rho, p = sp_stats.spearmanr(points['fitness'], points['effect'])
        print(f"Spearman rho = {rho:+.3f}, p = {p:.3g}")

    fig, fit = plot_fitness_scatter(points, studentize=studentize,
                                    merge_behavioral=merge_behavioral,
                                    color_by=color_by, fit_line=fit_line)
    if fit is not None:
        print(f"Linear fit: slope = {fit.slope:+.3f}, r² = {fit.rvalue ** 2:.3f}, "
              f"p = {fit.pvalue:.3g}, n = {len(points)}")

    out_dir = os.path.join(output_root, datetime.now().strftime("%Y%m%d_%H%M%S"))
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "config.json"), "w") as f:
        json.dump({'metric': metric, 'exclude_session_ids': exclude_session_ids,
                   'start_session_id': start_session_id, 'algorithm_label': algorithm_label,
                   'trial_types': trial_types, 'exclude_ratio_ranges': exclude_ratio_ranges,
                   'merge_behavioral': merge_behavioral, 'studentize': studentize,
                   'min_trials': min_trials, 'color_by': color_by, 'fit_line': fit_line,
                   'centers': ESTIM_DISTANCE_CENTERS, 'n_points': len(points),
                   'n_without_fitness': n_missing,
                   'sessions': sorted(points['session_id'].unique().tolist())},
                  f, indent=2)
    points.to_csv(os.path.join(out_dir, "points.csv"), index=False)
    for ext in ('png', 'svg'):
        fig.savefig(os.path.join(out_dir, f"estim_fitness_scatter.{ext}"), dpi=200,
                    bbox_inches='tight')
    print(f"Saved to {out_dir}")
    if show_plots:
        plt.show()


if __name__ == "__main__":
    main()
