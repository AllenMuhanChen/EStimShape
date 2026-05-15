"""
For each session, pick the best condition (max |effect_size|) from EStimPermutationTests,
plot EStim ON (red) and EStim OFF (black) as two dots — same style as
estim_examples_across_experiments.py — and annotate the max-stat permutation p-value.

Max-stat p-value per session:
  observed_max = max_c |effect_c|
  null_max[k]  = max_c |null_c[k]|  (element-wise max across all conditions for iteration k)
  p            = fraction of k where null_max[k] >= observed_max
"""

import json
import os
import sys
from pathlib import Path

import matplotlib.patches as mpatches
import numpy as np
from matplotlib import pyplot as plt

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
        observed_signed : signed effect of the best condition (retains direction)
        observed_max    : |effect| of the best condition
        max_stat_null   : array (n_perms,) — element-wise max of |null_c[k]| across conditions
        p_value         : fraction of null_max >= observed_max
        best_cond_dict  : condition filter dict for the best condition
    Returns None if no data.
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

    observed_max = best['obs_effect']
    p_value      = float(np.mean(max_stat_null >= observed_max))

    return {
        'observed_signed': best['obs_effect'],
        'observed_max':    observed_max,
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
    Three convergent population tests on per-session max-stat results.

    Permutation test on mean max-stat:
        A_obs  = mean_i(observed_signed_i)
        A*[k]  = mean_i(max_stat_null_i[k])   — average the per-session nulls element-wise
        p_perm = fraction of k where A*[k] >= A_obs

    Stouffer's Z:  combine per-session p-values into a single Z (one-tailed positive).

    Sign test:     binomial test — how many sessions have positive best effects.
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

    p_values  = np.clip([d['p_value'] for d in rows], 1e-6, 1 - 1e-6)
    stouffer_z = float(np.sum(sp_stats.norm.ppf(1 - p_values)) / np.sqrt(n))
    stouffer_p = float(1 - sp_stats.norm.cdf(stouffer_z))

    n_positive = int(np.sum(observed > 0))
    sign_p     = float(sp_stats.binomtest(n_positive, n, p=0.5, alternative='greater').pvalue)

    stats = {
        'n':          n,
        'A_obs':      A_obs,
        'p_perm':     p_perm,
        'stouffer_z': stouffer_z,
        'stouffer_p': stouffer_p,
        'n_positive': n_positive,
        'sign_p':     sign_p,
    }

    print(f"\nPopulation stats (n={n} sessions):")
    print(f"  Mean best effect:  {A_obs:+.2f}%")
    print(f"  Permutation test:  {_fmt_p(p_perm)}")
    print(f"  Stouffer Z={stouffer_z:.2f}   {_fmt_p(stouffer_p)}")
    print(f"  Sign test:  {n_positive}/{n} positive  {_fmt_p(sign_p)}")

    return stats


def plot_max_stat_per_experiment(session_ids=None, save_path=None, show_n=True,
                                 x_spacing=1.0, width_per_exp=1.5):
    if session_ids is None:
        session_ids = _get_sessions_with_permutation_data()

    rows = []
    for sid in session_ids:
        result = _build_max_stat_for_session(sid)
        if result is None:
            print(f"[{sid}] no permutation data, skipping")
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

    n_exp     = len(rows)
    _LEGEND_W = 1.5
    fig_w     = width_per_exp * n_exp * x_spacing + _LEGEND_W
    fig, ax   = plt.subplots(figsize=(fig_w, 6), constrained_layout=True)

    _COLOR_OFF = "black"
    _COLOR_ON  = "red"

    for i, d in enumerate(rows):
        x = float(i) * x_spacing

        # Connecting line
        ax.plot([x, x], [d['pct_off'], d['pct_on']],
                color="gray", alpha=0.6, linewidth=1.5, zorder=1)

        # Effect size at midpoint
        effect = d['pct_on'] - d['pct_off']
        mid_y  = (d['pct_on'] + d['pct_off']) / 2
        sign   = "+" if effect >= 0 else ""
        ax.text(x + 0.06, mid_y, f"{sign}{effect:.1f}%",
                ha="left", va="center", fontsize=8,
                color="red" if effect >= 0 else "black")

        # EStim OFF dot
        ax.scatter(x, d['pct_off'], color=_COLOR_OFF, s=90, zorder=3, edgecolors="none")
        if show_n:
            ax.text(x - 0.06, d['pct_off'], f"n={d['n_off']}",
                    ha="right", va="center", fontsize=7, color="dimgray")

        # EStim ON dot
        ax.scatter(x, d['pct_on'], color=_COLOR_ON, s=90, zorder=3,
                   edgecolors="black", linewidths=0.6)
        if show_n:
            ax.text(x + 0.06, d['pct_on'], f"n={d['n_on']}",
                    ha="left", va="center", fontsize=7, color=_COLOR_ON)

        # Max-stat p-value at top
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
    ax.legend(handles=legend_handles, fontsize=9,
              loc="upper left", bbox_to_anchor=(1.01, 1),
              framealpha=0.85, borderpad=0.7)

    if pop is not None:
        summary = (f"n={pop['n']}  mean best={pop['A_obs']:+.1f}%  "
                   f"perm {_fmt_p(pop['p_perm'])}  "
                   f"Stouffer Z={pop['stouffer_z']:.2f} ({_fmt_p(pop['stouffer_p'])})  "
                   f"sign {pop['n_positive']}/{pop['n']} ({_fmt_p(pop['sign_p'])})")
        fig.suptitle(summary, fontsize=9, color="darkred" if pop['p_perm'] < 0.05 else "gray")

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
