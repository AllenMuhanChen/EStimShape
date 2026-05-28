"""
For each session, pick the best condition (largest positive effect_size, n>=min_trials each group)
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
from src.analysis.nafc.group_analysis.analyze_estim_by_condition import METRIC_PCT_HYPOTHESIZED, METRIC_PCT_HYP_VS_DELTA
from src.analysis.nafc.group_analysis.estim_groups_permutation_test import (
    get_trial_data_for_condition, create_permutation_test_table)


def _get_sessions_with_permutation_data(algorithm_label='none', metric=METRIC_PCT_HYPOTHESIZED):
    conn = Connection("allen_data_repository")
    conn.execute(
        "SELECT DISTINCT session_id FROM EStimPermutationTests "
        "WHERE algorithm_label = %s AND metric = %s ORDER BY session_id",
        (algorithm_label, metric))
    return [row[0] for row in conn.fetch_all()]


# Minimum trials required in EACH group (EStim ON / OFF) for a condition to be
# included in either population test.
DEFAULT_MIN_TRIALS = 15


def _load_qualifying_conditions(session_id, algorithm_label='none', metric=METRIC_PCT_HYPOTHESIZED,
                                min_trials=DEFAULT_MIN_TRIALS):
    """Load all conditions for a session that pass the per-group min-trials filter.

    Shared by both population tests: the max-stat test reduces these to the best
    condition, the exceedance-count test counts how many exceed a threshold.

    ``min_trials`` is the minimum number of trials required in BOTH the EStim-ON
    and EStim-OFF groups for a condition to qualify.

    Returns a list of entries, each:
        {'session_id', 'cond_dict', 'obs_effect', 'null' (np.array, n_perms)}
    Empty list if the session has no qualifying conditions.
    """
    conn = Connection("allen_data_repository")
    conn.execute("""
        SELECT conditions, observed_effect_size, null_distribution,
               n_trials_estim_on, n_trials_estim_off
        FROM EStimPermutationTests
        WHERE session_id = %s AND algorithm_label = %s AND metric = %s
    """, (session_id, algorithm_label, metric))

    entries = []
    for conditions_json, obs_effect, null_json, n_on, n_off in conn.fetch_all():
        if null_json is None or obs_effect is None:
            continue
        if n_on is None or n_off is None or n_on < min_trials or n_off < min_trials:
            continue
        entries.append({
            'session_id': session_id,
            'cond_dict':  json.loads(conditions_json),
            'obs_effect': obs_effect,
            'null':       np.array(json.loads(null_json)),
        })
    return entries


def _build_max_stat_for_session(session_id, algorithm_label='none', metric=METRIC_PCT_HYPOTHESIZED,
                                min_trials=DEFAULT_MIN_TRIALS, studentize=False):
    """
    Returns dict with:
        observed_signed : signed statistic of the best positive condition
        max_stat_null   : array (n_perms,) — element-wise max across conditions per iteration
        p_value         : fraction of null_max >= observed_signed
        best_cond_dict  : condition filter dict for the best condition
    Returns None if no qualifying conditions (n>=min_trials each group).

    ``studentize``: if True, each condition's statistic is standardized by its own
    permutation null (T_c = (effect_c - mean(null_c)) / std(null_c)) before taking
    the max across conditions. This puts conditions with very different trial counts
    on a common scale so the noisiest (small-n, wide-null) conditions don't dominate
    the max. Observed/null are then in z units instead of percentage points.
    """
    entries = _load_qualifying_conditions(session_id, algorithm_label, metric, min_trials=min_trials)
    if not entries:
        return None

    # Build (cond_dict, observed_stat, null_array) per condition, tracking the
    # raw effect too. In studentized mode, standardize each by its own null;
    # drop degenerate (zero-spread) nulls.
    raw_list, obs_list, null_list, cond_list = [], [], [], []
    for e in entries:
        null = e['null']
        if studentize:
            mu = float(np.mean(null))
            sd = float(np.std(null, ddof=1))
            if not np.isfinite(sd) or sd <= 0:
                continue
            obs_list.append((e['obs_effect'] - mu) / sd)
            null_list.append((null - mu) / sd)
        else:
            obs_list.append(e['obs_effect'])
            null_list.append(null)
        raw_list.append(e['obs_effect'])
        cond_list.append(e['cond_dict'])

    if not obs_list:
        return None

    # Best = largest positive (studentized) effect (directional: stim should increase choice)
    best_idx = int(np.argmax(obs_list))

    # Element-wise max across all conditions for each permutation iteration (signed, no abs)
    null_matrix   = np.stack(null_list, axis=0)  # (n_conds, n_perms)
    max_stat_null = null_matrix.max(axis=0)       # (n_perms,)

    observed_signed = float(obs_list[best_idx])
    p_value         = float(np.mean(max_stat_null >= observed_signed))

    return {
        'observed_signed':      observed_signed,
        'observed_raw':         float(raw_list[best_idx]),
        'observed_studentized': float(obs_list[best_idx]) if studentize else None,
        'max_stat_null':        max_stat_null,
        'p_value':              p_value,
        'best_cond_dict':       cond_list[best_idx],
    }


def _get_pct_on_off(session_id, cond_dict, metric=METRIC_PCT_HYPOTHESIZED):
    trial_data = get_trial_data_for_condition(session_id, cond_dict, metric=metric)
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


# ---------------------------------------------------------------------------
# Population weighting strategies
# ---------------------------------------------------------------------------
#
# The cross-session combination (permutation mean + Stouffer's) is identical
# regardless of weighting — only the per-session weights change. Each strategy
# supplies those weights, letting the caller switch between the original
# equal-per-session test and trial-weighted variants without touching the
# statistics. ``best_cond_trials(row)`` = n_on + n_off of the session's selected
# best condition, i.e. the precision of the effect actually being tested.

from abc import ABC, abstractmethod


def _best_cond_trials(row):
    return float(row['n_on'] + row['n_off'])


class PopulationWeighting(ABC):
    """Per-session weights for combining max-stat results across sessions."""

    label: str = "unweighted"

    @abstractmethod
    def raw_weights(self, rows) -> np.ndarray:
        """Unnormalized per-session weights (one per row)."""

    def normalized_weights(self, rows) -> np.ndarray:
        """Weights summing to 1; used for the weighted-mean combinations."""
        w = self.raw_weights(rows).astype(float)
        total = w.sum()
        if total <= 0:
            return np.ones(len(rows)) / len(rows)
        return w / total


class UnweightedPopulation(PopulationWeighting):
    """Original behavior: every session counts equally."""

    label = "unweighted"

    def raw_weights(self, rows) -> np.ndarray:
        return np.ones(len(rows))


class TrialWeighting(PopulationWeighting):
    """Weight each session by its best condition's trial count (n_on + n_off).

    Inverse-variance-style weighting; gives the most power to large sessions
    but lets a single very large session dominate.
    """

    label = "best-cond trials"

    def raw_weights(self, rows) -> np.ndarray:
        return np.array([_best_cond_trials(d) for d in rows], dtype=float)


class SqrtTrialWeighting(PopulationWeighting):
    """Weight each session by sqrt(best-condition trials).

    The classic Stouffer weight: large sessions get more say, but the influence
    of any one session grows only with sqrt(n), so no single session dominates.
    Recommended default when session sizes are skewed.
    """

    label = "sqrt(best-cond trials)"

    def raw_weights(self, rows) -> np.ndarray:
        return np.sqrt([_best_cond_trials(d) for d in rows])


# Registry so callers can select a strategy by short name.
WEIGHTINGS = {
    'unweighted': UnweightedPopulation,
    'trials':     TrialWeighting,
    'sqrt':       SqrtTrialWeighting,
}


def make_weighting(weighting):
    """Coerce ``weighting`` (None / str key / instance) into a PopulationWeighting."""
    if weighting is None:
        return UnweightedPopulation()
    if isinstance(weighting, PopulationWeighting):
        return weighting
    if isinstance(weighting, str):
        try:
            return WEIGHTINGS[weighting]()
        except KeyError:
            raise ValueError(
                f"unknown weighting {weighting!r}; choose from {sorted(WEIGHTINGS)}")
    raise TypeError(f"weighting must be None, str, or PopulationWeighting, got {type(weighting)}")


def compute_population_stats(rows, weighting=None, value_label="%"):
    """
    Two convergent population tests on per-session max-stat results.

    Permutation test on (weighted) mean max-stat:
        A_obs  = Σ wᵢ·observed_signed_i      (weights normalized to sum to 1)
        A*[k]  = Σ wᵢ·max_stat_null_i[k]     for each permutation iteration k
        p_perm = fraction of k where A*[k] >= A_obs

    Stouffer's combined p-value (weighted form):
        Converts each session's one-tailed p_i into a standard normal
        z_i = Phi^{-1}(1 - p_i), then combines as Z = Σ Wᵢzᵢ / sqrt(Σ Wᵢ²).
        With equal weights this reduces to Σz_i / sqrt(n), the unweighted test.
        Unlike the permutation test (which tests the mean effect size), Stouffer's
        is sensitive to sessions with very small p-values even if their effect
        size is modest.

    ``weighting`` selects the per-session weighting strategy (None / str key /
    PopulationWeighting instance). Default ``None`` reproduces the original
    equal-per-session test exactly. The permutation null is still regenerated by
    the same permutations, so the weighted p-value remains valid.

    n_sig: number of sessions individually significant at p<0.05 (descriptive only).

    Note: a sign test is not used here because we select the best *positive* condition per
    session — the max of C conditions from a symmetric null is positive >50% of the time,
    so a 50% baseline would be anticonservative.
    """
    from scipy import stats as sp_stats

    n = len(rows)
    if n == 0:
        return None

    weighting = make_weighting(weighting)

    observed = np.array([d['observed_signed'] for d in rows])

    w_norm = weighting.normalized_weights(rows)                          # sums to 1
    A_obs  = float(np.dot(w_norm, observed))

    null_matrix = np.stack([d['max_stat_null'] for d in rows], axis=0)  # (n_sessions, n_perms)
    pop_null    = (null_matrix * w_norm[:, None]).sum(axis=0)            # (n_perms,)
    p_perm      = float(np.mean(pop_null >= A_obs))
    null_95     = float(np.percentile(pop_null, 95))

    p_values   = np.clip([d['p_value'] for d in rows], 1e-6, 1 - 1e-6)
    z_scores   = sp_stats.norm.ppf(1 - np.array(p_values))
    w_raw      = weighting.raw_weights(rows).astype(float)
    stouffer_z = float(np.sum(w_raw * z_scores) / np.sqrt(np.sum(w_raw ** 2)))
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
        'weighting':  weighting.label,
        'value_label': value_label,
    }

    print(f"\nPopulation stats (n={n} sessions, weighting={weighting.label}):")
    print(f"  Observed mean best effect:  {A_obs:+.2f}{value_label}")
    print(f"  Null 95th percentile:       {null_95:+.2f}{value_label}")
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

    weighted = pop.get('weighting', UnweightedPopulation.label) != UnweightedPopulation.label
    if weighted:
        null_desc = ["Null = trial-weighted mean of per-",
                     "session max-stat distributions."]
    else:
        null_desc = ["Null = mean of per-session max-stat",
                     "distributions, averaged across sessions."]

    stat_kind = "studentized max-stat" if pop.get('value_label', '%') == 'z' else "raw max-stat"

    lines = [
        ("Population Statistics", 1.00, 11, "bold", sig_color),
        (f"n = {pop['n']} sessions  ·  weighting: {pop.get('weighting', 'unweighted')}",
         0.92, 9, "normal", "black"),
        (f"statistic: {stat_kind}", 0.865, 8, "normal", "#444444"),
        ("", 0.84, 9, "normal", "black"),

        ("Permutation test", 0.80, 9, "bold", "black"),
        ("H₀: stimulation has no effect on choice.", 0.73, 8, "normal", "#444444"),
        (null_desc[0], 0.67, 8, "normal", "#444444"),
        (null_desc[1], 0.61, 8, "normal", "#444444"),
        (f"  Observed mean best effect: {pop['A_obs']:+.2f}{pop.get('value_label', '%')}",
         0.54, 9, "normal", sig_color),
        (f"  Null 95th percentile:      {pop['null_95']:+.2f}{pop.get('value_label', '%')}",
         0.47, 9, "normal", "#444444"),
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


def plot_max_stat_per_experiment(exclude_session_ids=None, start_session_id=None,
                                 algorithm_label='none', metric=METRIC_PCT_HYPOTHESIZED,
                                 save_path=None, show_n=True,
                                 x_spacing=1.0, width_per_exp=1.5,
                                 weighting=None, min_trials=DEFAULT_MIN_TRIALS,
                                 studentize=False):
    """
    exclude_session_ids : optional iterable of session_ids to drop; all other
                       sessions with permutation data are included.
    start_session_id : if given, only include sessions whose session_id >= this value
                       (lexicographic comparison works because session_id is YYMMDD_N).
    algorithm_label  : which cutoff variant to read from EStimPermutationTests.
    metric           : which EStimEffects metric row to plot (e.g. 'pct_hypothesized'
                       or 'pct_hyp_vs_delta'). Must match a metric previously stored
                       by run_permutation_tests for the same algorithm_label.
    weighting        : per-session weighting for the population tests. None (default)
                       reproduces the original equal-per-session test; pass a key from
                       WEIGHTINGS ('trials', 'sqrt') or a PopulationWeighting instance
                       to weight larger sessions more.
    min_trials       : minimum trials required in each group for a condition to qualify.
    studentize       : if True, standardize each condition by its own permutation null
                       before taking the max (fairer across conditions with very
                       different trial counts). p-values become studentized; the ON/OFF
                       dots stay in % as descriptive context.
    """
    create_permutation_test_table()  # ensures algorithm_label column exists
    session_ids = _get_sessions_with_permutation_data(algorithm_label, metric)
    if exclude_session_ids:
        excluded = set(exclude_session_ids)
        session_ids = [s for s in session_ids if s not in excluded]
    if start_session_id is not None:
        session_ids = [s for s in session_ids if s >= start_session_id]

    rows = []
    for sid in session_ids:
        result = _build_max_stat_for_session(sid, algorithm_label, metric,
                                             min_trials=min_trials, studentize=studentize)
        if result is None:
            print(f"[{sid}] no permutation data or no conditions with n>={min_trials}, skipping")
            continue
        pct_on, pct_off, n_on, n_off = _get_pct_on_off(sid, result['best_cond_dict'], metric=metric)
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
        stat_unit = "z" if studentize else "%"
        print(f"[{sid}] best stat={result['observed_signed']:+.2f}{stat_unit}  p={result['p_value']:.3f}  "
              f"ON={pct_on:.1f}% (n={n_on})  OFF={pct_off:.1f}% (n={n_off})")

    if not rows:
        print("No data to plot.")
        return None

    pop = compute_population_stats(rows, weighting=weighting,
                                   value_label=("z" if studentize else "%"))

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


# ===========================================================================
# Test 2: exceedance-count permutation test
# ===========================================================================
#
# Different question from the max-stat test. Instead of "is the single best
# condition larger than chance?", this asks "across all conditions pooled, are
# there more conditions with effect >= x% than chance produces?".
#
# Statistic (per threshold x):
#   N_obs        = #conditions with observed_effect >= x
#   null_count[k]= #conditions with null_c[k] >= x   (exceedances summed across
#                  all pooled conditions at permutation iteration k)
#   p            = fraction of k where null_count[k] >= N_obs
#
# Conditions are pooled across all sessions into one family. Within-session
# cross-condition correlation is preserved (those nulls share the shuffle);
# across sessions the nulls are independent, which is the true situation, so
# summing per-iteration exceedances is a valid joint null draw. Because the
# result depends on the (arbitrary) threshold, we sweep several thresholds.

def compute_exceedance_count_stats(exclude_session_ids=None, start_session_id=None,
                                   algorithm_label='none', metric=METRIC_PCT_HYPOTHESIZED,
                                   thresholds=None, min_trials=DEFAULT_MIN_TRIALS,
                                   studentize=False):
    """Pool all qualifying conditions across sessions and run the exceedance-count
    permutation test at each threshold.

    ``exclude_session_ids`` is an optional iterable of session_ids to drop; all
    other sessions with permutation data are pooled. ``min_trials`` is the minimum
    trials required in each group for a condition to be pooled.

    ``studentize``: if True, each condition's effect is standardized by its own
    permutation null (T = (effect - mean(null)) / std(null)) before counting
    exceedances, so thresholds are in z units ("how many conditions exceed z SDs
    above their own chance level") rather than raw percentage points. Conditions
    with degenerate (zero-spread) nulls are dropped.

    ``thresholds``: sweep of cutoffs. Defaults to (5,10,15,20) % in raw mode and
    (1.0,1.5,2.0,2.5,3.0) z in studentized mode.

    Returns a dict with the pooled condition/permutation counts, the threshold
    ``unit`` ('%' or 'z'), and a per-threshold list of {threshold, n_obs,
    null_mean, null_95, p_value}. Returns None if no qualifying conditions exist.
    """
    create_permutation_test_table()
    session_ids = _get_sessions_with_permutation_data(algorithm_label, metric)
    if exclude_session_ids:
        excluded = set(exclude_session_ids)
        session_ids = [s for s in session_ids if s not in excluded]
    if start_session_id is not None:
        session_ids = [s for s in session_ids if s >= start_session_id]

    entries = []
    for sid in session_ids:
        entries.extend(_load_qualifying_conditions(sid, algorithm_label, metric, min_trials=min_trials))

    if not entries:
        print(f"No qualifying conditions (n>={min_trials} each group) to test.")
        return None

    # Align null lengths across conditions, then pool into one (C, P) matrix.
    n_perms = min(len(e['null']) for e in entries)

    if studentize:
        obs_vals, null_rows = [], []
        for e in entries:
            null = e['null'][:n_perms]
            mu = float(np.mean(null))
            sd = float(np.std(null, ddof=1))
            if not np.isfinite(sd) or sd <= 0:
                continue
            obs_vals.append((e['obs_effect'] - mu) / sd)
            null_rows.append((null - mu) / sd)
        if not obs_vals:
            print("No conditions with usable (non-degenerate) nulls to studentize.")
            return None
        obs = np.array(obs_vals)
        null_matrix = np.stack(null_rows, axis=0)               # (C, P), in z units
        unit = "z"
        if thresholds is None:
            thresholds = (1.0, 1.5, 2.0, 2.5, 3.0)
    else:
        null_matrix = np.stack([e['null'][:n_perms] for e in entries], axis=0)  # (C, P)
        obs = np.array([e['obs_effect'] for e in entries])
        unit = "%"
        if thresholds is None:
            thresholds = (5.0, 10.0, 15.0, 20.0)

    n_conditions = int(obs.shape[0])

    results = []
    for thr in thresholds:
        n_obs       = int(np.sum(obs >= thr))
        null_counts = np.sum(null_matrix >= thr, axis=0)         # (P,)
        p_value     = float(np.mean(null_counts >= n_obs))
        results.append({
            'threshold':  float(thr),
            'n_obs':      n_obs,
            'null_mean':  float(np.mean(null_counts)),
            'null_95':    float(np.percentile(null_counts, 95)),
            'p_value':    p_value,
        })

    kind = "studentized " if studentize else ""
    print(f"\n{kind.capitalize()}exceedance-count test ({n_conditions} conditions pooled, {n_perms} perms):")
    for r in results:
        print(f"  effect >= {r['threshold']:.1f}{unit}:  observed={r['n_obs']:3d}  "
              f"null mean={r['null_mean']:5.1f}  null 95th={r['null_95']:5.1f}  "
              f"{_fmt_p(r['p_value'])}")

    return {
        'n_conditions': n_conditions,
        'n_perms':      n_perms,
        'thresholds':   [float(t) for t in thresholds],
        'unit':         unit,
        'studentize':   studentize,
        'results':      results,
    }


def plot_exceedance_count_test(exclude_session_ids=None, start_session_id=None,
                               algorithm_label='none', metric=METRIC_PCT_HYPOTHESIZED,
                               thresholds=None, save_path=None,
                               min_trials=DEFAULT_MIN_TRIALS, studentize=False):
    """Plot observed exceedance counts vs the permutation null across thresholds.

    ``studentize``: count exceedances of each condition's studentized effect
    (z = effect / own-null SD) instead of raw % — thresholds become z cutoffs.
    """
    stats = compute_exceedance_count_stats(
        exclude_session_ids=exclude_session_ids, start_session_id=start_session_id,
        algorithm_label=algorithm_label, metric=metric, thresholds=thresholds,
        min_trials=min_trials, studentize=studentize)
    if stats is None:
        print("No data to plot.")
        return None

    res       = stats['results']
    thr       = [r['threshold'] for r in res]
    n_obs     = [r['n_obs'] for r in res]
    null_mean = [r['null_mean'] for r in res]
    null_95   = [r['null_95'] for r in res]

    fig, ax = plt.subplots(figsize=(8, 6))

    ax.fill_between(thr, 0, null_95, color="gray", alpha=0.2,
                    label="Null (≤ 95th percentile)")
    ax.plot(thr, null_mean, color="gray", linestyle="--", marker="o",
            linewidth=1.5, label="Null mean count")
    ax.plot(thr, n_obs, color="red", marker="o", linewidth=2.0,
            markeredgecolor="black", markeredgewidth=0.6, label="Observed count")

    for r in res:
        is_sig = r['p_value'] < 0.05
        ax.annotate(_fmt_p(r['p_value']), (r['threshold'], r['n_obs']),
                    textcoords="offset points", xytext=(0, 9), ha="center",
                    fontsize=9, color="darkred" if is_sig else "gray",
                    fontweight="bold" if is_sig else "normal")

    unit = stats.get('unit', '%')
    unit_label = "studentized effect (z)" if unit == 'z' else "effect size (%)"
    kind = "Studentized exceedance-count" if stats.get('studentize') else "Exceedance-count"
    ax.set_xlabel(f"EStim {unit_label} threshold", fontsize=13)
    ax.set_ylabel("# conditions with effect ≥ threshold", fontsize=13)
    ax.set_title(f"{kind} permutation test\n"
                 f"{stats['n_conditions']} conditions pooled · {stats['n_perms']} perms",
                 fontsize=12, fontweight="bold")
    ax.set_xticks(thr)
    ax.set_ylim(bottom=0)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=9, loc="upper right", framealpha=0.85)

    fig.tight_layout()

    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        fig.savefig(save_path, bbox_inches="tight", dpi=150)
        svg_path = save_path.rsplit(".", 1)[0] + ".svg"
        fig.savefig(svg_path, bbox_inches="tight")
        print(f"Saved to {save_path}")

    plt.show()
    return fig


def plot_studentized_winners(exclude_session_ids=None, start_session_id=None,
                             algorithm_label='none', metric=METRIC_PCT_HYPOTHESIZED,
                             min_trials=DEFAULT_MIN_TRIALS, save_path=None):
    """Diagnostic for the studentized maxT winner per session.

    For each session, take the condition that wins the *studentized* max-stat and
    plot it in terms of BOTH its raw effect (percentage points) and its
    studentized effect (z = effect / null SD). A scatter of raw (x) vs studentized
    (y) makes the failure mode obvious: a point high on y but near zero on x is a
    winner that only looks strong because its null SD is tiny (small-n / degenerate
    null), whereas a point that is high on both is a genuinely strong, precisely
    measured effect.
    """
    create_permutation_test_table()
    session_ids = _get_sessions_with_permutation_data(algorithm_label, metric)
    if exclude_session_ids:
        excluded = set(exclude_session_ids)
        session_ids = [s for s in session_ids if s not in excluded]
    if start_session_id is not None:
        session_ids = [s for s in session_ids if s >= start_session_id]

    rows = []
    for sid in session_ids:
        result = _build_max_stat_for_session(sid, algorithm_label, metric,
                                             min_trials=min_trials, studentize=True)
        if result is None:
            print(f"[{sid}] no conditions with n>={min_trials}, skipping")
            continue
        pct_on, pct_off, n_on, n_off = _get_pct_on_off(sid, result['best_cond_dict'], metric=metric)
        rows.append({
            'session_id': sid,
            'raw':        result['observed_raw'],
            'z':          result['observed_studentized'],
            'p_value':    result['p_value'],
            'n_on':       n_on,
            'n_off':      n_off,
        })
        print(f"[{sid}] studentized winner: raw={result['observed_raw']:+.1f}%  "
              f"z={result['observed_studentized']:+.2f}  p={result['p_value']:.3f}  "
              f"(n_on={n_on}, n_off={n_off})")

    if not rows:
        print("No data to plot.")
        return None

    fig, ax = plt.subplots(figsize=(8, 7))
    ax.axvline(0, color="gray", linewidth=0.8, alpha=0.5)
    ax.axhline(0, color="gray", linewidth=0.8, alpha=0.5)

    for d in rows:
        is_sig = d['p_value'] < 0.05
        ax.scatter(d['raw'], d['z'],
                   s=90, color="red" if is_sig else "gray",
                   edgecolors="black", linewidths=0.6, zorder=3,
                   alpha=0.9 if is_sig else 0.7)
        ax.annotate(f"{d['session_id']}\n{_fmt_p(d['p_value'])}",
                    (d['raw'], d['z']), textcoords="offset points",
                    xytext=(6, 4), fontsize=7,
                    color="darkred" if is_sig else "dimgray")

    ax.set_xlabel("Studentized winner — raw effect size (percentage points)", fontsize=12)
    ax.set_ylabel("Studentized winner — studentized effect (z = effect / null SD)", fontsize=12)
    ax.set_title("Studentized maxT winners: raw vs studentized effect\n"
                 "(high-z + near-zero-raw ⇒ tiny-null artifact; high on both ⇒ genuine)",
                 fontsize=11, fontweight="bold")
    ax.grid(True, alpha=0.3)

    legend_handles = [
        mpatches.Patch(color="red",  label="studentized p < 0.05"),
        mpatches.Patch(color="gray", label="n.s."),
    ]
    ax.legend(handles=legend_handles, fontsize=9, loc="lower right", framealpha=0.85)

    fig.tight_layout()

    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        fig.savefig(save_path, bbox_inches="tight", dpi=150)
        svg_path = save_path.rsplit(".", 1)[0] + ".svg"
        fig.savefig(svg_path, bbox_inches="tight")
        print(f"Saved to {save_path}")

    plt.show()
    return fig


def plot_winning_conditions(exclude_session_ids=None, start_session_id=None,
                            algorithm_label='none', metric=METRIC_PCT_HYPOTHESIZED,
                            min_trials=DEFAULT_MIN_TRIALS, studentize=True,
                            save_path=None):
    """Across sessions, tally which condition parameters tend to win the max-stat.

    For each session the winning condition (studentized maxT winner by default;
    set studentize=False for the raw-effect winner) is recorded, then for every
    parameter key that appears in the winning condition dicts we bar-chart the
    frequency of each winning value. Shows which estim/behavioral parameter
    settings most often produce the best effect (polarity, shape, num_channels,
    a1, noise_chance, ...).

    Note: parameters are only counted for sessions whose winning condition
    actually specifies that key, so per-parameter totals can differ.
    """
    from collections import Counter, defaultdict

    create_permutation_test_table()
    session_ids = _get_sessions_with_permutation_data(algorithm_label, metric)
    if exclude_session_ids:
        excluded = set(exclude_session_ids)
        session_ids = [s for s in session_ids if s not in excluded]
    if start_session_id is not None:
        session_ids = [s for s in session_ids if s >= start_session_id]

    winners = []
    for sid in session_ids:
        result = _build_max_stat_for_session(sid, algorithm_label, metric,
                                             min_trials=min_trials, studentize=studentize)
        if result is None:
            continue
        winners.append((sid, result['best_cond_dict']))

    if not winners:
        print("No winning conditions found.")
        return None

    per_key = defaultdict(Counter)
    for _sid, cond in winners:
        for k, v in cond.items():
            per_key[k][str(v)] += 1

    print(f"\nWinning conditions across {len(winners)} sessions "
          f"({'studentized' if studentize else 'raw'} maxT):")
    for k in sorted(per_key):
        tally = ", ".join(f"{val}×{cnt}" for val, cnt in per_key[k].most_common())
        print(f"  {k}: {tally}")

    keys = sorted(per_key)
    n = len(keys)
    ncols = min(3, n)
    nrows = (n + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(5 * ncols, 3.5 * nrows), squeeze=False)

    for i, k in enumerate(keys):
        ax = axes[i // ncols][i % ncols]
        counter = per_key[k]
        labels = sorted(counter, key=lambda x: (-counter[x], x))
        counts = [counter[l] for l in labels]
        ax.bar(range(len(labels)), counts, color="steelblue", edgecolor="black")
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=8)
        ax.set_title(k, fontsize=10, fontweight="bold")
        ax.set_ylabel("# winning sessions", fontsize=8)
        ax.grid(True, axis="y", alpha=0.3)
        ax.set_axisbelow(True)

    for j in range(n, nrows * ncols):
        axes[j // ncols][j % ncols].axis("off")

    kind = "studentized" if studentize else "raw"
    fig.suptitle(f"Winning conditions across {len(winners)} sessions ({kind} maxT)",
                 fontsize=13, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.96])

    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        fig.savefig(save_path, bbox_inches="tight", dpi=150)
        svg_path = save_path.rsplit(".", 1)[0] + ".svg"
        fig.savefig(svg_path, bbox_inches="tight")
        print(f"Saved to {save_path}")

    plt.show()
    return fig


def main():
    # ---- Test 1: max-stat per experiment (is the BEST condition > chance?) ----
    plot_max_stat_per_experiment(
        exclude_session_ids=["260421_0", "260410_0"],   # e.g. ["260421_0", "260410_0"] to drop sessions
        # exclusion reasons: ["Incorrect GA Response behavior", "Weird clustering, too small"]
        # start_session_id="260423_0",
        start_session_id="260402_0", #first variant experiment
        algorithm_label='None',        # or e.g. 'last_sustained_k3_t5.0'
        metric=METRIC_PCT_HYP_VS_DELTA,  # switch to METRIC_PCT_HYP_VS_DELTA to test Hyp vs Delta only
        # algorithm_label='first_drop_w100_s10_t5.0_n3',
        save_path="/home/connorlab/Documents/plots/across_experiments/max_estim_per_experiment.png",
        show_n=True,
        x_spacing=0.5,
        width_per_exp=1.0,
        # weighting=None    #-> original equal-per-session test (default)
        weighting='sqrt',  #-> weight sessions by sqrt(best-condition trials)
        # weighting='trials'-> weight sessions by best-condition trial count
        # weighting=None,
        # studentize=False -> raw % effect (default); True -> standardize each
        #                     condition by its own null before taking the max
        #                     (fairer across conditions with very different n).
        studentize=True,
        min_trials=10
    )

    # ---- Test 2: exceedance-count (are there more conditions over x% than chance?) ----
    plot_exceedance_count_test(
        exclude_session_ids=None,   # e.g. ["260423_0"] to drop sessions
        # rejected for: ["Improper GA", "GA on cell not correlated with surrounding cells"]
        # start_session_id="260423_0",
        start_session_id="260325_0",
        algorithm_label='None',
        metric=METRIC_PCT_HYP_VS_DELTA,
        # thresholds=None -> (5,10,15,20)% in raw mode, (1.0..3.0) z when studentized
        thresholds=None,
        # studentize=True -> count exceedances of z = effect/own-null SD instead of raw %
        studentize=True,
        save_path="/home/connorlab/Documents/plots/across_experiments/exceedance_count_test.png",
    )

    # ---- Test 3: studentized winners — raw vs studentized effect (diagnostic) ----
    plot_studentized_winners(
        exclude_session_ids=["260421_0", "260410_0"],
        start_session_id="260402_0",
        algorithm_label='None',
        metric=METRIC_PCT_HYP_VS_DELTA,
        min_trials=10,
        save_path="/home/connorlab/Documents/plots/across_experiments/studentized_winners.png",
    )

    # ---- Test 4: which condition parameters tend to win the max ----
    plot_winning_conditions(
        exclude_session_ids=["260421_0", "260410_0"],
        start_session_id="260402_0",
        algorithm_label='None',
        metric=METRIC_PCT_HYP_VS_DELTA,
        min_trials=10,
        studentize=True,   # tally winners of the studentized maxT
        save_path="/home/connorlab/Documents/plots/across_experiments/winning_conditions.png",
    )


if __name__ == "__main__":
    main()
