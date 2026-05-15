"""
For each session, pick the best condition (largest positive effect_size, n>=10 each group)
from EStimPermutationTests, plot EStim ON (red) and EStim OFF (black) as two dots —
same style as estim_examples_across_experiments.py — and annotate the max-stat
permutation p-value per session plus population statistics in a side panel.

Max-stat p-value per session (one-tailed, positive direction):
  observed_max = max_c(T_c)           — best positive effect across conditions
  null_max[k]  = max_c(null_c[k])     — element-wise max across conditions, iteration k
  p            = fraction of k where null_max[k] >= observed_max
"""

import json
import os
import sys
from pathlib import Path

import matplotlib.patches as mpatches
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.gridspec import GridSpec

sys.path.insert(0, str(Path(__file__).parents[3]))

from clat.util.connection import Connection
from src.analysis.nafc.estim_groups_permutation_test import get_trial_data_for_condition


def _get_sessions_with_permutation_data():
    conn = Connection("allen_data_repository")
    conn.execute("SELECT DISTINCT session_id FROM EStimPermutationTests ORDER BY session_id")
    return [row[0] for row in conn.fetch_all()]


def _build_max_stat_for_session(session_id):
    """
    Returns dict with:
        observed_signed : signed effect of the best positive condition
        max_stat_null   : array (n_perms,) — element-wise max across conditions per iteration
        p_value         : fraction of null_max >= observed_signed
        best_cond_dict  : condition filter dict for the best condition
    Returns None if no qualifying conditions (n>=10 each group).
    """
    conn = Connection("allen_data_repository")
    conn.execute("""
        SELECT conditions, observed_effect_size, null_distribution,
               n_trials_estim_on, n_trials_estim_off
        FROM EStimPermutationTests
        WHERE session_id = %s
    """, (session_id,))
    rows = conn.fetch_all()

    if not rows:
        return None

    entries = []
    for conditions_json, obs_effect, null_json, n_on, n_off in rows:
        if null_json is None or obs_effect is None:
            continue
        if n_on is None or n_off is None or n_on < 10 or n_off < 10:
            continue
        entries.append({
            'cond_dict':  json.loads(conditions_json),
            'obs_effect': obs_effect,
            'null':       np.array(json.loads(null_json)),
        })

    if not entries:
        return None

    # Best = largest positive effect (directional: stim should increase choice)
    best = max(entries, key=lambda e: e['obs_effect'])

    # Element-wise max across all conditions for each permutation iteration (signed, no abs)
    null_matrix   = np.stack([e['null'] for e in entries], axis=0)  # (n_conds, n_perms)
    max_stat_null = null_matrix.max(axis=0)                          # (n_perms,)

    observed_signed = best['obs_effect']
    p_value         = float(np.mean(max_stat_null >= observed_signed))

    return {
        'observed_signed': observed_signed,
        'max_stat_null':   max_stat_null,
        'p_value':         p_value,
        'best_cond_dict':  best['cond_dict'],
    }


def _get_pct_on_off(session_id, cond_dict):
    trial_data = get_trial_data_for_condition(session_id, cond_dict)
    on  = trial_data['estim_on']
    off = trial_data['estim_off']
    if not on or not off:
        return None, None, 0, 0
    return 100.0 * np.mean(on), 100.0 * np.mean(off), len(on), len(off)


def _fmt_p(p):
    if p < 0.001:
        return "p<0.001"
    if p < 0.01:
        return f"p={p:.3f}"
    return f"p={p:.2f}"


def compute_population_stats(rows):
    """
    Two convergent population tests on per-session max-stat results.

    Permutation test on mean max-stat:
        A_obs  = mean_i(observed_signed_i)  across sessions
        A*[k]  = mean_i(max_stat_null_i[k]) for each permutation iteration k
        p_perm = fraction of k where A*[k] >= A_obs

    Stouffer's combined p-value:
        Converts each session's one-tailed p_i into a standard normal z_i = Phi^{-1}(1 - p_i),
        sums them, and divides by sqrt(n).  The resulting p gives the probability of observing
        this level of consistent evidence across sessions if H0 were true in all of them.
        Unlike the permutation test (which tests the mean effect size), Stouffer's is sensitive
        to sessions with very small p-values even if their effect size is modest.

    n_sig: number of sessions individually significant at p<0.05 (descriptive only).

    Note: a sign test is not used here because we select the best *positive* condition per
    session — the max of C conditions from a symmetric null is positive >50% of the time,
    so a 50% baseline would be anticonservative.
    """
    from scipy import stats as sp_stats

    n = len(rows)
    if n == 0:
        return None

    observed = np.array([d['observed_signed'] for d in rows])
    A_obs    = float(np.mean(observed))

    null_matrix = np.stack([d['max_stat_null'] for d in rows], axis=0)  # (n_sessions, n_perms)
    pop_null    = null_matrix.mean(axis=0)                               # (n_perms,)
    p_perm      = float(np.mean(pop_null >= A_obs))
    null_95     = float(np.percentile(pop_null, 95))

    p_values   = np.clip([d['p_value'] for d in rows], 1e-6, 1 - 1e-6)
    z_scores   = sp_stats.norm.ppf(1 - np.array(p_values))
    stouffer_z = float(np.sum(z_scores) / np.sqrt(n))
    stouffer_p = float(1 - sp_stats.norm.cdf(stouffer_z))

    n_sig = int(np.sum(np.array([d['p_value'] for d in rows]) < 0.05))

    stats = {
        'n':          n,
        'A_obs':      A_obs,
        'null_95':    null_95,
        'p_perm':     p_perm,
        'stouffer_z': stouffer_z,
        'stouffer_p': stouffer_p,
        'n_sig':      n_sig,
    }

    print(f"\nPopulation stats (n={n} sessions):")
    print(f"  Observed mean best effect:  {A_obs:+.2f}%")
    print(f"  Null 95th percentile:       {null_95:+.2f}%")
    print(f"  Permutation test:           {_fmt_p(p_perm)}")
    print(f"  Stouffer combined:          {_fmt_p(stouffer_p)}  (Z={stouffer_z:.2f})")
    print(f"  Individually significant:   {n_sig}/{n} sessions (p<0.05)")

    return stats


def _draw_stats_panel(ax_text, pop, rows):
    """Render population statistics as descriptive text in a borderless axes."""
    ax_text.axis('off')
    if pop is None:
        return

    sig_color = "darkred" if pop['p_perm'] < 0.05 else "#444444"

    lines = [
        ("Population Statistics", 1.00, 11, "bold", sig_color),
        (f"n = {pop['n']} sessions", 0.92, 9, "normal", "black"),
        ("", 0.86, 9, "normal", "black"),

        ("Permutation test", 0.80, 9, "bold", "black"),
        ("H₀: stimulation has no effect on choice.", 0.73, 8, "normal", "#444444"),
        ("Null = mean of per-session max-stat", 0.67, 8, "normal", "#444444"),
        ("distributions, averaged across sessions.", 0.61, 8, "normal", "#444444"),
        (f"  Observed mean best effect: {pop['A_obs']:+.2f}%", 0.54, 9, "normal", sig_color),
        (f"  Null 95th percentile:      {pop['null_95']:+.2f}%", 0.47, 9, "normal", "#444444"),
        (f"  {_fmt_p(pop['p_perm'])}", 0.40, 10, "bold", sig_color),
        ("", 0.34, 9, "normal", "black"),

        ("Stouffer's combined test", 0.28, 9, "bold", "black"),
        ("Combines per-session p-values; sensitive", 0.21, 8, "normal", "#444444"),
        ("to consistent evidence even when individual", 0.15, 8, "normal", "#444444"),
        ("sessions are just sub-threshold.", 0.09, 8, "normal", "#444444"),
        (f"  {_fmt_p(pop['stouffer_p'])}", 0.02, 10, "bold",
         "darkred" if pop['stouffer_p'] < 0.05 else "#444444"),
    ]

    # Individually significant count — append below
    n_sig_line = f"Sessions individually significant (p<0.05): {pop['n_sig']}/{pop['n']}"

    for text, y, size, weight, color in lines:
        ax_text.text(0.05, y, text, transform=ax_text.transAxes,
                     fontsize=size, fontweight=weight, color=color,
                     va="top", ha="left", wrap=False)

    ax_text.text(0.05, -0.06, n_sig_line, transform=ax_text.transAxes,
                 fontsize=8, color="#444444", va="top", ha="left")

    ax_text.add_patch(plt.Rectangle((0, -0.08), 1.0, 1.12,
                                    transform=ax_text.transAxes,
                                    fill=True, facecolor="#f8f8f8",
                                    edgecolor="#cccccc", linewidth=0.8,
                                    zorder=-1, clip_on=False))


def plot_max_stat_per_experiment(session_ids=None, save_path=None, show_n=True,
                                 x_spacing=1.0, width_per_exp=1.5):
    if session_ids is None:
        session_ids = _get_sessions_with_permutation_data()

    rows = []
    for sid in session_ids:
        result = _build_max_stat_for_session(sid)
        if result is None:
            print(f"[{sid}] no permutation data or no conditions with n>=10, skipping")
            continue
        pct_on, pct_off, n_on, n_off = _get_pct_on_off(sid, result['best_cond_dict'])
        if pct_on is None:
            print(f"[{sid}] no trial data for best condition, skipping")
            continue
        rows.append({
            'session_id':      sid,
            'pct_on':          pct_on,
            'pct_off':         pct_off,
            'n_on':            n_on,
            'n_off':           n_off,
            'p_value':         result['p_value'],
            'observed_signed': result['observed_signed'],
            'max_stat_null':   result['max_stat_null'],
        })
        print(f"[{sid}] best effect={result['observed_signed']:+.1f}%  p={result['p_value']:.3f}  "
              f"ON={pct_on:.1f}% (n={n_on})  OFF={pct_off:.1f}% (n={n_off})")

    if not rows:
        print("No data to plot.")
        return None

    pop = compute_population_stats(rows)

    n_exp        = len(rows)
    plot_width   = width_per_exp * n_exp * x_spacing
    panel_width  = 3.2   # inches for the stats panel
    fig_w        = plot_width + panel_width

    fig = plt.figure(figsize=(fig_w, 6))
    gs  = GridSpec(1, 2, figure=fig,
                   width_ratios=[plot_width, panel_width],
                   wspace=0.05)
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
        if show_n:
            ax.text(x - 0.06, d['pct_off'], f"n={d['n_off']}",
                    ha="right", va="center", fontsize=7, color="dimgray")

        ax.scatter(x, d['pct_on'], color=_COLOR_ON, s=90, zorder=3,
                   edgecolors="black", linewidths=0.6)
        if show_n:
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
        mpatches.Patch(color=_COLOR_OFF, label="EStim OFF (best condition)"),
        mpatches.Patch(color=_COLOR_ON,  label="EStim ON (best condition)"),
    ]
    ax.legend(handles=legend_handles, fontsize=9, loc="lower right", framealpha=0.85)

    _draw_stats_panel(ax_panel, pop, rows)

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
    plot_max_stat_per_experiment(
        session_ids=None,
        save_path="/home/connorlab/Documents/plots/across_experiments/max_estim_per_experiment.png",
        show_n=True,
        x_spacing=0.5,
        width_per_exp=1.0,
    )


if __name__ == "__main__":
    main()
