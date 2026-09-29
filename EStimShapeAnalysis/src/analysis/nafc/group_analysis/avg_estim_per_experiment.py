"""
Analytic (permutation-free) test of the AVERAGE EStim effect per session, and across
sessions.

Unlike max_estim_per_experiment.py (which picks each session's best condition and
tests it against a max-stat permutation null), this pools every qualifying condition
in a session into one 2x2 table and asks whether EStim shifts choice on average.

Per session — one-sided Fisher's exact test on the pooled 2x2 table:

                      chose hypothesized   did not
        EStim ON            a                 b
        EStim OFF           c                 d

    ON  = every qualifying condition's EStim-ON trials (disjoint across conditions).
    OFF = the union of those conditions' EStim-OFF baselines. Conditions in the same
          behavioral group share one OFF baseline, so OFF trials are de-duplicated
          (each trial counted once) rather than stacked per condition.
    alternative='greater' tests ON > OFF; 'less' tests ON < OFF.

Population — Fisher's combined-probability test:
    X^2 = -2 * sum_i ln(p_i)  ~  chi^2 with 2S degrees of freedom (S sessions)
Sessions use disjoint trials, so the per-session p-values are independent.

Caveats:
  - Pooling across behavioral groups (trial_type, noise, ...) ignores differences in
    baseline between groups. If the ON:OFF ratio differs a lot between groups the
    pooled effect can be biased (Simpson's paradox).
  - Fisher's exact p-values are discrete and conservative, so the combined test is
    conservative too (it errs toward p being too large, not too small).
"""

import os
import sys
from pathlib import Path

import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.gridspec import GridSpec
from scipy import stats as sp_stats

sys.path.insert(0, str(Path(__file__).parents[3]))

from clat.util.connection import Connection
from src.analysis.nafc.group_analysis.analyze_estim_by_condition import (
    METRIC_PCT_HYPOTHESIZED, METRIC_PCT_HYP_VS_DELTA,
    _DEFAULT_BEHAVIORAL_CONDITIONS, _DEFAULT_ESTIM_CONDITIONS,
    _fetch_trial_start_cutoffs, _filter_for_metric, split_data_by_conditions)
from src.analysis.nafc.group_analysis.estim_groups_permutation_test import (
    _read_session_data_cached)

# Minimum trials required in EACH group (EStim ON / OFF) for a condition to be
# pooled into its session's table. Matches max_estim_per_experiment.
DEFAULT_MIN_TRIALS = 15

ALTERNATIVES = ('greater', 'less')


def _get_sessions_with_effects(algorithm_label='none', metric=METRIC_PCT_HYPOTHESIZED):
    conn = Connection("allen_data_repository")
    conn.execute(
        "SELECT DISTINCT session_id FROM EStimEffects "
        "WHERE algorithm_label = %s AND metric = %s ORDER BY session_id",
        (algorithm_label, metric))
    return [row[0] for row in conn.fetch_all()]


def build_pooled_table_for_session(session_id, algorithm_label='none',
                                   metric=METRIC_PCT_HYPOTHESIZED,
                                   min_trials=DEFAULT_MIN_TRIALS):
    """
    Pool all qualifying conditions of a session into one ON/OFF 2x2 table.

    Uses the same split (behavioral groups, estim_spec_id, gen window, cutoff) as the
    EStimEffects pipeline. A condition qualifies when both its ON and OFF groups have
    at least ``min_trials`` trials after the metric filter.

    Returns dict with the table counts, or None if nothing qualifies.
    """
    data = _read_session_data_cached(session_id)
    behavioral_keys = [c for c in _DEFAULT_BEHAVIORAL_CONDITIONS if c in data.columns]
    cutoffs = _fetch_trial_start_cutoffs(session_id, algorithm_label) or None

    comparisons = split_data_by_conditions(data, behavioral_keys, _DEFAULT_ESTIM_CONDITIONS,
                                           trial_start_cutoffs=cutoffs)

    on_frames, off_frames = [], []
    for comp in comparisons:
        on_df  = _filter_for_metric(comp['estim_on_data'], metric)
        off_df = _filter_for_metric(comp['estim_off_data'], metric)
        on_df  = on_df[on_df['is_hypothesized_choice'].notna()]
        off_df = off_df[off_df['is_hypothesized_choice'].notna()]
        if len(on_df) < min_trials or len(off_df) < min_trials:
            continue
        on_frames.append(on_df)
        off_frames.append(off_df)

    if not on_frames:
        return None

    # Trial frames keep the session frame's row index, so duplicated index = same trial.
    on  = pd.concat(on_frames)
    off = pd.concat(off_frames)
    on  = on[~on.index.duplicated()]
    off = off[~off.index.duplicated()]

    on_yes  = int(on['is_hypothesized_choice'].astype(bool).sum())
    off_yes = int(off['is_hypothesized_choice'].astype(bool).sum())
    return {
        'n_conditions': len(on_frames),
        'on_yes':  on_yes,  'on_no':  len(on) - on_yes,
        'off_yes': off_yes, 'off_no': len(off) - off_yes,
        'n_on':  len(on),
        'n_off': len(off),
    }


def fisher_exact_for_table(table, alternative='greater'):
    """One-sided Fisher's exact test on a pooled table from build_pooled_table_for_session."""
    if alternative not in ALTERNATIVES:
        raise ValueError(f"alternative must be one of {ALTERNATIVES}, got {alternative!r}")
    contingency = [[table['on_yes'],  table['on_no']],
                   [table['off_yes'], table['off_no']]]
    odds_ratio, p = sp_stats.fisher_exact(contingency, alternative=alternative)
    return float(odds_ratio), float(p)


def fishers_combined_probability(p_values):
    """
    Fisher's method: X^2 = -2 * sum(ln p_i) ~ chi^2(2k) under H0 (independent p_i).
    Returns (X^2, degrees of freedom, combined p).
    """
    p = np.clip(np.asarray(p_values, dtype=float), 1e-300, 1.0)
    chi2 = float(-2.0 * np.sum(np.log(p)))
    df   = 2 * len(p)
    return chi2, df, float(sp_stats.chi2.sf(chi2, df))


def _fmt_p(p):
    if p < 0.001:
        return "p<0.001"
    if p < 0.01:
        return f"p={p:.3f}"
    return f"p={p:.2f}"


def compute_population_stats(rows, alternative='greater'):
    """Fisher's combined-probability test across sessions, plus descriptive summaries."""
    n = len(rows)
    if n == 0:
        return None

    chi2, df, p_comb = fishers_combined_probability([d['p_value'] for d in rows])
    effects = np.array([d['pct_on'] - d['pct_off'] for d in rows])
    n_sig   = int(np.sum(np.array([d['p_value'] for d in rows]) < 0.05))

    stats = {
        'n':           n,
        'chi2':        chi2,
        'df':          df,
        'p_combined':  p_comb,
        'mean_effect': float(np.mean(effects)),
        'n_sig':       n_sig,
        'alternative': alternative,
    }

    print(f"\nPopulation stats (n={n} sessions, alternative={alternative}):")
    print(f"  Mean pooled effect (ON-OFF): {stats['mean_effect']:+.2f}%")
    print(f"  Fisher's combined:           X²={chi2:.2f}, df={df}, {_fmt_p(p_comb)}")
    print(f"  Individually significant:    {n_sig}/{n} sessions (p<0.05)")
    return stats


def _draw_stats_panel(ax_text, pop):
    ax_text.axis('off')
    if pop is None:
        return

    sig_color = "darkred" if pop['p_combined'] < 0.05 else "#444444"
    h1 = "ON > OFF" if pop['alternative'] == 'greater' else "ON < OFF"

    lines = [
        ("Population Statistics", 1.00, 11, "bold", sig_color),
        (f"n = {pop['n']} sessions  ·  H₁: {h1}", 0.92, 9, "normal", "black"),
        ("", 0.86, 9, "normal", "black"),

        ("Per session: Fisher's exact test", 0.80, 9, "bold", "black"),
        ("All qualifying conditions pooled into", 0.73, 8, "normal", "#444444"),
        ("one ON/OFF × chose/didn't 2×2 table.", 0.67, 8, "normal", "#444444"),
        (f"  Mean pooled effect: {pop['mean_effect']:+.2f}%", 0.60, 9, "normal", "#444444"),
        ("", 0.54, 9, "normal", "black"),

        ("Fisher's combined-probability test", 0.48, 9, "bold", "black"),
        ("X² = −2 Σ ln pᵢ  ~  χ²(2S)", 0.41, 8, "normal", "#444444"),
        (f"  X² = {pop['chi2']:.2f},  df = {pop['df']}", 0.34, 9, "normal", sig_color),
        (f"  {_fmt_p(pop['p_combined'])}", 0.26, 10, "bold", sig_color),
        ("", 0.20, 9, "normal", "black"),

        (f"Sessions individually significant (p<0.05): {pop['n_sig']}/{pop['n']}",
         0.12, 8, "normal", "#444444"),
    ]
    for text, y, size, weight, color in lines:
        ax_text.text(0.05, y, text, transform=ax_text.transAxes,
                     fontsize=size, fontweight=weight, color=color,
                     va="top", ha="left", wrap=False)

    ax_text.add_patch(plt.Rectangle((0, 0.04), 1.0, 1.0,
                                    transform=ax_text.transAxes,
                                    fill=True, facecolor="#f8f8f8",
                                    edgecolor="#cccccc", linewidth=0.8,
                                    zorder=-1, clip_on=False))


def plot_avg_estim_per_experiment(exclude_session_ids=None, start_session_id=None,
                                  algorithm_label='none', metric=METRIC_PCT_HYPOTHESIZED,
                                  alternative='greater', min_trials=DEFAULT_MIN_TRIALS,
                                  save_path=None, show_n=True,
                                  x_spacing=1.0, width_per_exp=1.5):
    """
    exclude_session_ids : optional iterable of session_ids to drop.
    start_session_id    : only include sessions with session_id >= this value.
    algorithm_label     : which cutoff variant to apply (matches EStimSessionCutoffs).
    metric              : 'pct_hypothesized' or 'pct_hyp_vs_delta' trial filtering.
    alternative         : 'greater' tests EStim ON > OFF; 'less' tests ON < OFF.
    min_trials          : minimum trials in each group for a condition to be pooled.
    """
    if alternative not in ALTERNATIVES:
        raise ValueError(f"alternative must be one of {ALTERNATIVES}, got {alternative!r}")

    session_ids = _get_sessions_with_effects(algorithm_label, metric)
    if exclude_session_ids:
        excluded = set(exclude_session_ids)
        session_ids = [s for s in session_ids if s not in excluded]
    if start_session_id is not None:
        session_ids = [s for s in session_ids if s >= start_session_id]

    rows = []
    for sid in session_ids:
        table = build_pooled_table_for_session(sid, algorithm_label, metric, min_trials=min_trials)
        if table is None:
            print(f"[{sid}] no conditions with n>={min_trials} in each group, skipping")
            continue
        odds_ratio, p = fisher_exact_for_table(table, alternative=alternative)
        pct_on  = 100.0 * table['on_yes']  / table['n_on']
        pct_off = 100.0 * table['off_yes'] / table['n_off']
        rows.append({'session_id': sid, 'pct_on': pct_on, 'pct_off': pct_off,
                     'odds_ratio': odds_ratio, 'p_value': p, **table})
        print(f"[{sid}] {table['n_conditions']} conds  ON={pct_on:.1f}% (n={table['n_on']})  "
              f"OFF={pct_off:.1f}% (n={table['n_off']})  OR={odds_ratio:.2f}  p={p:.3f}")

    if not rows:
        print("No data to plot.")
        return None

    pop = compute_population_stats(rows, alternative=alternative)

    n_exp       = len(rows)
    plot_width  = width_per_exp * n_exp * x_spacing
    panel_width = 3.2
    fig = plt.figure(figsize=(plot_width + panel_width, 6))
    gs  = GridSpec(1, 2, figure=fig, width_ratios=[plot_width, panel_width], wspace=0.05)
    ax       = fig.add_subplot(gs[0])
    ax_panel = fig.add_subplot(gs[1])

    _COLOR_OFF = "black"
    _COLOR_ON  = "red"

    for i, d in enumerate(rows):
        x = float(i) * x_spacing

        ax.plot([x, x], [d['pct_off'], d['pct_on']],
                color="gray", alpha=0.6, linewidth=1.5, zorder=1)

        effect = d['pct_on'] - d['pct_off']
        mid_y  = (d['pct_on'] + d['pct_off']) / 2
        sign   = "+" if effect >= 0 else ""
        ax.text(x + 0.06, mid_y, f"{sign}{effect:.1f}%",
                ha="left", va="center", fontsize=8,
                color="red" if effect >= 0 else "black")

        ax.scatter(x, d['pct_off'], color=_COLOR_OFF, s=90, zorder=3, edgecolors="none")
        ax.scatter(x, d['pct_on'], color=_COLOR_ON, s=90, zorder=3,
                   edgecolors="black", linewidths=0.6)
        if show_n:
            ax.text(x - 0.06, d['pct_off'], f"n={d['n_off']}",
                    ha="right", va="center", fontsize=7, color="dimgray")
            ax.text(x + 0.06, d['pct_on'], f"n={d['n_on']}",
                    ha="left", va="center", fontsize=7, color=_COLOR_ON)

        is_sig = d['p_value'] < 0.05
        ax.text(x, 97, _fmt_p(d['p_value']),
                ha="center", va="bottom", fontsize=8,
                color="darkred" if is_sig else "gray",
                fontweight="bold" if is_sig else "normal")

    x_margin = 0.5 * x_spacing
    ax.axhline(50, color="gray", linestyle="--", linewidth=1, alpha=0.5)
    ax.set_yticks(range(0, 101, 10))
    ax.set_xticks([i * x_spacing for i in range(n_exp)])
    ax.set_xticklabels([d['session_id'] for d in rows], rotation=45, ha="center", fontsize=9)
    ax.set_ylabel("% Chose Object with Response-Driving Part", fontsize=13)
    ax.set_xlabel("Session", fontsize=13)
    ax.set_ylim([0, 105])
    ax.set_xlim([-x_margin, (n_exp - 1) * x_spacing + x_margin])
    ax.invert_xaxis()
    ax.grid(True, alpha=0.3, axis="y")

    legend_handles = [
        mpatches.Patch(color=_COLOR_OFF, label="EStim OFF (all conditions pooled)"),
        mpatches.Patch(color=_COLOR_ON,  label="EStim ON (all conditions pooled)"),
    ]
    ax.legend(handles=legend_handles, fontsize=9, loc="lower right", framealpha=0.85)

    _draw_stats_panel(ax_panel, pop)

    fig.tight_layout()

    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        fig.savefig(save_path, bbox_inches="tight", dpi=150)
        svg_path = save_path.rsplit(".", 1)[0] + ".svg"
        fig.savefig(svg_path, bbox_inches="tight")
        print(f"Saved to {save_path}")

    plt.show()
    return fig


def main():
    metric = METRIC_PCT_HYP_VS_DELTA
    exclude_session_ids = ["260421_0", "260410_0"]
    start_session_id = "260402_0"
    algorithm_label = 'None'

    plot_avg_estim_per_experiment(
        exclude_session_ids=exclude_session_ids,
        start_session_id=start_session_id,
        algorithm_label=algorithm_label,
        metric=metric,
        alternative='greater',   # 'less' -> test whether the average effect is negative
        min_trials=10,
        save_path="/home/connorlab/Documents/plots/across_experiments/avg_estim_per_experiment.png",
        show_n=False,
        x_spacing=0.75,
        width_per_exp=1.0,
    )


if __name__ == "__main__":
    main()
