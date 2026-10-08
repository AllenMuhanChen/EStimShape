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

Population — selected with ``stats_method`` (a parameter at the top of main()):

  'ttest' (default) — one-sample t-test on the distribution of EStim effects.
    Each unit's effect is e_i = %ON_i - %OFF_i (or its z-score when studentized).
    The units are the values in the plot being drawn: one per condition (or per
    spec with merge_behavioral) in the histograms, one per session in the dot plot.
    H0: mean(e) = 0.  t = mean(e) / (SD(e) / sqrt(n)), SD with ddof=1,
    df = n - 1, one-sided ('greater': H1 mean > 0; 'less': H1 mean < 0).
    Every unit counts equally (unweighted mean), as in a standard t-test.
    Caveat: conditions in the same behavioral group share one OFF baseline, so
    per-condition / per-spec effects are not strictly independent.

  'fisher_combined' — Fisher's combined-probability test over the per-session
    Fisher's exact p-values:
    X^2 = -2 * sum_i ln(p_i)  ~  chi^2 with 2S degrees of freedom (S sessions)
    Sessions use disjoint trials, so the per-session p-values are independent.

Caveats:
  - Pooling across behavioral groups (trial_type, noise, ...) ignores differences in
    baseline between groups. If the ON:OFF ratio differs a lot between groups the
    pooled effect can be biased (Simpson's paradox).
  - Fisher's exact p-values are discrete and conservative, so the Fisher combined
    test is conservative too (it errs toward p being too large, not too small).
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

# Population test (see module docstring).
STATS_TTEST  = 'ttest'             # one-sample t-test: mean effect vs 0
STATS_FISHER = 'fisher_combined'   # Fisher's combined probability over sessions
STATS_METHODS = (STATS_TTEST, STATS_FISHER)


def _get_sessions_with_effects(algorithm_label='none', metric=METRIC_PCT_HYPOTHESIZED):
    conn = Connection("allen_data_repository")
    conn.execute(
        "SELECT DISTINCT session_id FROM EStimEffects "
        "WHERE algorithm_label = %s AND metric = %s ORDER BY session_id",
        (algorithm_label, metric))
    return [row[0] for row in conn.fetch_all()]


def _qualifying_conditions(session_id, algorithm_label='none',
                           metric=METRIC_PCT_HYPOTHESIZED, min_trials=DEFAULT_MIN_TRIALS):
    """
    Every condition of a session whose ON and OFF groups both have >= ``min_trials``
    trials after the metric filter, as dicts with 'cond_dict', 'on_df', 'off_df'.

    Uses the same split (behavioral groups, estim_spec_id, gen window, cutoff) as the
    EStimEffects pipeline.
    """
    data = _read_session_data_cached(session_id)
    behavioral_keys = [c for c in _DEFAULT_BEHAVIORAL_CONDITIONS if c in data.columns]
    cutoffs = _fetch_trial_start_cutoffs(session_id, algorithm_label) or None

    comparisons = split_data_by_conditions(data, behavioral_keys, _DEFAULT_ESTIM_CONDITIONS,
                                           trial_start_cutoffs=cutoffs)
    out = []
    for comp in comparisons:
        on_df  = _filter_for_metric(comp['estim_on_data'], metric)
        off_df = _filter_for_metric(comp['estim_off_data'], metric)
        on_df  = on_df[on_df['is_hypothesized_choice'].notna()]
        off_df = off_df[off_df['is_hypothesized_choice'].notna()]
        if len(on_df) < min_trials or len(off_df) < min_trials:
            continue
        out.append({'cond_dict': {**comp['behavioral_conditions'], **comp['estim_conditions']},
                    'on_df': on_df, 'off_df': off_df})
    return out


def build_pooled_table_for_session(session_id, algorithm_label='none',
                                   metric=METRIC_PCT_HYPOTHESIZED,
                                   min_trials=DEFAULT_MIN_TRIALS, condition_filter=None):
    """
    Pool all qualifying conditions of a session into one ON/OFF 2x2 table.

    ``condition_filter(session_id, cond_dict) -> bool`` optionally restricts which
    qualifying conditions are pooled (e.g. the estim-rule split).

    Returns dict with the table counts, or None if nothing qualifies.
    """
    qualifying = _qualifying_conditions(session_id, algorithm_label, metric, min_trials)
    if condition_filter is not None:
        qualifying = [q for q in qualifying if condition_filter(session_id, q['cond_dict'])]
    return _pool_conditions(qualifying)


def _pool_conditions(qualifying):
    """One pooled 2x2 table from a list of _qualifying_conditions entries (or None)."""
    if not qualifying:
        return None

    on_frames  = [q['on_df'] for q in qualifying]
    off_frames = [q['off_df'] for q in qualifying]
    conditions = [{
        'cond_dict': q['cond_dict'],
        'on_yes':  int(q['on_df']['is_hypothesized_choice'].astype(bool).sum()),
        'off_yes': int(q['off_df']['is_hypothesized_choice'].astype(bool).sum()),
        'n_on':  len(q['on_df']),
        'n_off': len(q['off_df']),
    } for q in qualifying]

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
        # Per-condition counts (each condition vs its own OFF baseline), for the
        # effect-size histogram. Not independent: conditions share OFF trials.
        'conditions': conditions,
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


def one_sample_ttest(effects, alternative='greater'):
    """
    One-sample t-test of mean(effects) against 0 (SD with ddof=1, df = n - 1).
    alternative='greater' -> H1 mean > 0; 'less' -> H1 mean < 0.
    Returns (t, df, p); t and p are NaN when n < 2 or every effect is identical.
    """
    effects = np.asarray(effects, dtype=float)
    n = len(effects)
    if n < 2 or np.std(effects) == 0:
        return float('nan'), max(n - 1, 0), float('nan')
    res = sp_stats.ttest_1samp(effects, 0.0, alternative=alternative)
    return float(res.statistic), n - 1, float(res.pvalue)


def compute_population_stats(rows, alternative='greater', stats_method=STATS_TTEST,
                             effects=None, unit='%', noun='sessions'):
    """
    Population test across sessions, plus descriptive summaries.

    stats_method='ttest': one-sample t-test on ``effects`` (the distribution being
        plotted, e.g. per-condition effects from _condition_arrays). If ``effects`` is
        None, the per-session pooled effects (ON% - OFF%) are used, with noun='sessions'.
    stats_method='fisher_combined': Fisher's combined test on the per-session
        Fisher's exact p-values (``effects`` is then only used for the mean shown).

    The returned dict carries 'p' (the population p-value) for either method.
    """
    if stats_method not in STATS_METHODS:
        raise ValueError(f"stats_method must be one of {STATS_METHODS}, got {stats_method!r}")
    n_sessions = len(rows)
    if n_sessions == 0:
        return None

    if effects is None:
        effects, unit, noun = [d['pct_on'] - d['pct_off'] for d in rows], '%', 'sessions'
    effects = np.asarray(effects, dtype=float)
    n_sig   = int(np.sum(np.array([d['p_value'] for d in rows]) < 0.05))

    stats = {
        'method':      stats_method,
        'n_sessions':  n_sessions,
        'n':           len(effects),
        'noun':        noun,
        'unit':        unit,
        'mean_effect': float(np.mean(effects)),
        'sem':         float(sp_stats.sem(effects)) if len(effects) > 1 else float('nan'),
        'n_sig':       n_sig,
        'alternative': alternative,
    }

    print(f"\nPopulation stats ({n_sessions} sessions, alternative={alternative}):")
    print(f"  Individually significant sessions (Fisher's exact p<0.05): {n_sig}/{n_sessions}")
    if stats_method == STATS_TTEST:
        t, df, p = one_sample_ttest(effects, alternative)
        stats.update(t=t, df=df, p=p)
        print(f"  One-sample t-test on {len(effects)} {noun}: mean = "
              f"{stats['mean_effect']:+.2f}{unit} ± {stats['sem']:.2f} SEM, "
              f"t({df}) = {t:.2f}, {_fmt_p(p) if np.isfinite(p) else 'p=n/a'}")
    else:
        chi2, df, p = fishers_combined_probability([d['p_value'] for d in rows])
        stats.update(chi2=chi2, df=df, p=p)
        print(f"  Mean effect ({noun}): {stats['mean_effect']:+.2f}{unit}")
        print(f"  Fisher's combined: X²={chi2:.2f}, df={df}, {_fmt_p(p)}")
    return stats


def _h1_text(pop):
    return {'greater': ("ON > OFF", "mean > 0"),
            'less':    ("ON < OFF", "mean < 0")}[pop['alternative']]


def _pop_result_lines(pop):
    """(test name, statistic line, p text) describing the population test."""
    if pop['method'] == STATS_TTEST:
        p_txt = _fmt_p(pop['p']) if np.isfinite(pop['p']) else "p = n/a (n<2)"
        return (f"One-sample t-test ({_h1_text(pop)[1]})",
                f"t({pop['df']}) = {pop['t']:.2f}",
                p_txt)
    return (f"Fisher's combined ({_h1_text(pop)[0]})",
            f"X² = {pop['chi2']:.1f}, df = {pop['df']}",
            _fmt_p(pop['p']))


def _pop_is_sig(pop):
    return np.isfinite(pop['p']) and pop['p'] < 0.05


def _draw_stats_panel(ax_text, pop):
    ax_text.axis('off')
    if pop is None:
        return

    sig_color = "darkred" if _pop_is_sig(pop) else "#444444"
    h1 = _h1_text(pop)[0]
    name, stat_line, p_txt = _pop_result_lines(pop)
    formula = ("t = mean(eᵢ) / (SD / √n),  eᵢ = %ON − %OFF"
               if pop['method'] == STATS_TTEST else "X² = −2 Σ ln pᵢ  ~  χ²(2S)")

    lines = [
        ("Population Statistics", 1.00, 11, "bold", sig_color),
        (f"n = {pop['n_sessions']} sessions  ·  H₁: {h1}", 0.92, 9, "normal", "black"),
        ("", 0.86, 9, "normal", "black"),

        ("Per session: Fisher's exact test", 0.80, 9, "bold", "black"),
        ("All qualifying conditions pooled into", 0.73, 8, "normal", "#444444"),
        ("one ON/OFF × chose/didn't 2×2 table.", 0.67, 8, "normal", "#444444"),
        (f"  Mean pooled effect: {pop['mean_effect']:+.2f}%", 0.60, 9, "normal", "#444444"),
        ("", 0.54, 9, "normal", "black"),

        (name, 0.48, 9, "bold", "black"),
        (formula, 0.41, 8, "normal", "#444444"),
        (f"  {stat_line}", 0.34, 9, "normal", sig_color),
        (f"  {p_txt}", 0.26, 10, "bold", sig_color),
        ("", 0.20, 9, "normal", "black"),

        (f"Sessions individually significant (p<0.05): {pop['n_sig']}/{pop['n_sessions']}",
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


def _normalize_trial_types(trial_types):
    """None (all trial types) or a tuple of trial-type names; a bare string is one type."""
    if trial_types is None:
        return None
    if isinstance(trial_types, str):
        return (trial_types,)
    return tuple(trial_types)


def _normalize_ratio_ranges(ranges):
    """None or a tuple of (lo, hi) ratio ranges to exclude. Either end may be None for
    an open end, e.g. (8, None) = ratio >= 8. A single (lo, hi) pair is accepted too."""
    if ranges is None:
        return None
    ranges = list(ranges)
    if len(ranges) == 2 and all(v is None or np.isscalar(v) for v in ranges):
        ranges = [tuple(ranges)]   # a single (lo, hi) pair
    out = []
    for lo, hi in ranges:
        lo = -np.inf if lo is None else float(lo)
        hi = np.inf if hi is None else float(hi)
        if lo > hi:
            raise ValueError(f"exclude_ratio_ranges: lo > hi in ({lo}, {hi})")
        out.append((lo, hi))
    return tuple(out) or None


def _filter_label(trial_types):
    """Figure-title text naming the trial types shown. (Ratio exclusions are recorded
    in the filename only.)"""
    trial_types = _normalize_trial_types(trial_types)
    return "all trial types" if trial_types is None else " + ".join(trial_types)


def _with_filter_suffix(save_path, trial_types, exclude_ratio_ranges=None,
                        merge_behavioral=False):
    """Append the active filters to a filename, e.g.
    avg_estim.png -> avg_estim__HypothesizedShape+DeltaShape__xratio8-inf.png
    (unchanged when no filter is set)."""
    root, ext = os.path.splitext(save_path)
    trial_types = _normalize_trial_types(trial_types)
    if trial_types is not None:
        root += "__" + "+".join("".join(ch for ch in tt if ch.isalnum()) for tt in trial_types)
    ranges = _normalize_ratio_ranges(exclude_ratio_ranges)
    if ranges:
        def b(v):
            return ("inf" if v > 0 else "-inf") if np.isinf(v) else f"{v:g}"
        root += "__xratio" + "_".join(f"{b(lo)}-{b(hi)}" for lo, hi in ranges)
    if merge_behavioral:
        root += "__perspec"
    return root + ext


def _in_excluded_ratio(session_id, cond_dict, ranges):
    """True if the condition's spec ratio falls in any excluded range (inclusive).
    Conditions without a ratio (no spec, or missing current / half-distance) are kept."""
    spec = cond_dict.get('estim_spec_id')
    if spec is None or (isinstance(spec, float) and np.isnan(spec)):
        return False
    ratio = get_spec_ratios(session_id).get(int(spec))
    if ratio is None:
        return False
    return any(lo <= ratio <= hi for lo, hi in ranges)


def _save_figure(fig, save_path, trial_types=None, exclude_ratio_ranges=None,
                 merge_behavioral=False):
    """Save fig as PNG + SVG, with the active filters in the filename."""
    if not save_path:
        return
    save_path = _with_filter_suffix(save_path, trial_types, exclude_ratio_ranges,
                                    merge_behavioral)
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    fig.savefig(save_path, bbox_inches="tight", dpi=150)
    fig.savefig(os.path.splitext(save_path)[0] + ".svg", bbox_inches="tight")
    print(f"Saved to {save_path}")


def collect_session_rows(exclude_session_ids=None, start_session_id=None,
                         algorithm_label='none', metric=METRIC_PCT_HYPOTHESIZED,
                         alternative='greater', min_trials=DEFAULT_MIN_TRIALS,
                         condition_filter=None, trial_types=None,
                         exclude_ratio_ranges=None):
    """Build each session's pooled table and run its one-sided Fisher's exact test.

    ``condition_filter(session_id, cond_dict) -> bool`` restricts which conditions
    are pooled; sessions left with no conditions are skipped.
    ``trial_types``: None (all) or trial-type names to keep, e.g.
    ('Hypothesized Shape', 'Delta Shape').
    ``exclude_ratio_ranges``: None or [(lo, hi), ...] — drop conditions whose spec's
    current : half-distance ratio lies in any range (inclusive; None = open end).
    Both are applied on top of condition_filter."""
    if alternative not in ALTERNATIVES:
        raise ValueError(f"alternative must be one of {ALTERNATIVES}, got {alternative!r}")

    trial_types = _normalize_trial_types(trial_types)
    ranges      = _normalize_ratio_ranges(exclude_ratio_ranges)
    if trial_types is not None or ranges is not None:
        base_filter = condition_filter

        def condition_filter(sid, cond):
            if trial_types is not None and cond.get('trial_type') not in trial_types:
                return False
            if ranges is not None and _in_excluded_ratio(sid, cond, ranges):
                return False
            return base_filter is None or base_filter(sid, cond)

    session_ids = _get_sessions_with_effects(algorithm_label, metric)
    if exclude_session_ids:
        excluded = set(exclude_session_ids)
        session_ids = [s for s in session_ids if s not in excluded]
    if start_session_id is not None:
        session_ids = [s for s in session_ids if s >= start_session_id]

    rows = []
    for sid in session_ids:
        table = build_pooled_table_for_session(sid, algorithm_label, metric, min_trials=min_trials,
                                               condition_filter=condition_filter)
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
    return rows


# Default histogram bin width per x-axis unit.
DEFAULT_BIN_WIDTH_PCT = 5.0   # percentage points
DEFAULT_BIN_WIDTH_Z   = 0.5   # standard deviations


def _unit_noun(merge_behavioral):
    return "specs" if merge_behavioral else "conditions"


def _spec_unit_key(session_id, cond_dict):
    """One histogram unit per (session, trial type, estim spec) when merging."""
    return (session_id, cond_dict.get('trial_type'), cond_dict.get('estim_spec_id'))


def _condition_arrays(rows, studentize=False, merge_behavioral=False):
    """Per-unit effect and trial-count weights across rows.

    A unit is one condition, or with merge_behavioral=True one (session, trial type,
    estim spec): that spec's behavioral groups (noise, coherence, sample length, ...)
    are combined by a trial-weighted average of their per-group effects, each group
    still compared against its own OFF baseline:
        effect = sum(w_g * e_g) / W,   chance var = sum(w_g^2 * var_g) / W^2,
        w_g = n_on_g + n_off_g,        W = sum(w_g).

    studentize=False: effect in percentage points (ON% - OFF%).
    studentize=True : effect divided by its chance SD (per condition
                      sqrt(p(1-p)(1/n_on + 1/n_off)), p = pooled choice rate — a
                      two-proportion z-score). Units with a zero chance SD (all
                      choices identical) have no z-score and are dropped.
    """
    units = [(d['session_id'], c) for d in rows for c in d['conditions']]
    n_on  = np.array([c['n_on']  for _, c in units], dtype=float)
    n_off = np.array([c['n_off'] for _, c in units], dtype=float)
    effects = 100.0 * (np.array([c['on_yes'] for _, c in units]) / n_on
                       - np.array([c['off_yes'] for _, c in units]) / n_off)
    p_pool  = (np.array([c['on_yes'] + c['off_yes'] for _, c in units])) / (n_on + n_off)
    null_var = 1e4 * p_pool * (1 - p_pool) * (1 / n_on + 1 / n_off)
    weights = n_on + n_off

    if merge_behavioral:
        groups = {}
        for i, (sid, c) in enumerate(units):
            groups.setdefault(_spec_unit_key(sid, c['cond_dict']), []).append(i)
        idx = list(groups.values())
        W        = np.array([weights[g].sum() for g in idx])
        effects  = np.array([np.dot(weights[g], effects[g]) for g in idx]) / W
        null_var = np.array([np.dot(weights[g] ** 2, null_var[g]) for g in idx]) / W ** 2
        weights  = W

    noun = _unit_noun(merge_behavioral)
    if not studentize:
        return {'effects': effects, 'weights': weights, 'unit': '%', 'noun': noun}

    null_sd = np.sqrt(null_var)
    ok = null_sd > 0
    if (~ok).any():
        print(f"  studentize: dropping {int((~ok).sum())} {noun} with zero chance SD "
              f"(all choices identical)")
    return {'effects': effects[ok] / null_sd[ok], 'weights': weights[ok], 'unit': 'z',
            'noun': noun}


def _resolve_bin_width(bin_width, studentize):
    if bin_width is not None:
        return bin_width
    return DEFAULT_BIN_WIDTH_Z if studentize else DEFAULT_BIN_WIDTH_PCT


def _effect_axis_label(studentize, merge_behavioral=False):
    per = "per spec" if merge_behavioral else "per condition"
    if studentize:
        return f"Studentized EStim effect: (% ON − % OFF) / chance SD  (z, {per})"
    return f"EStim effect: % ON − % OFF ({per})"


def _histogram_edges(array_sets, bin_width):
    """Shared bin edges covering every set's effects (and 0), with 0 on an edge."""
    effects = np.concatenate([a['effects'] for a in array_sets])
    lo = np.floor(min(effects.min(), 0.0) / bin_width) * bin_width
    hi = np.ceil(max(effects.max(), 0.0) / bin_width) * bin_width
    if hi <= lo:
        hi = lo + bin_width
    return np.arange(lo, hi + bin_width, bin_width)


def _draw_condition_histogram(ax, rows, pop, arrays, edges, *, alternative='greater',
                              color="#d9534f", title=None):
    """Draw one per-condition effect histogram, a reference line at 0 and the
    population test result onto ``ax``."""
    effects, unit, noun = arrays['effects'], arrays['unit'], arrays['noun']
    trial_weighted = float(np.average(effects, weights=arrays['weights']))
    raw_mean       = float(effects.mean())

    ax.hist(effects, bins=edges, color=color, alpha=0.75, edgecolor="white",
            label=f"n={len(effects)} {noun}, {len(rows)} sessions")
    ax.axvline(0, color="gray", linestyle="--", linewidth=1)

    sig_color = "darkred" if _pop_is_sig(pop) else "#444444"
    name, stat_line, p_txt = _pop_result_lines(pop)
    if pop['method'] == STATS_TTEST:
        header = f"{name}, n = {pop['n']} {pop['noun']}"
        detail = f"mean = {pop['mean_effect']:+.2f}{unit}, {stat_line}, {p_txt}"
    else:
        header = f"{name}, {pop['n_sessions']} sessions"
        detail = f"{stat_line}, {p_txt}"
    ax.text(0.02, 0.97, f"{header}\n{detail}",
            transform=ax.transAxes, va="top", ha="left", fontsize=9, color=sig_color,
            bbox=dict(facecolor="#f8f8f8", edgecolor="#cccccc", boxstyle="round,pad=0.4"))

    if title:
        ax.set_title(title, fontsize=11, loc="left", fontweight="bold")
    ax.set_ylabel(f"Number of {noun}", fontsize=12)
    ax.legend(fontsize=9, loc="upper right", framealpha=0.9)
    ax.spines[['top', 'right']].set_visible(False)

    print(f"\nEffect histogram{' [' + title + ']' if title else ''}: {len(effects)} {noun}, "
          f"trial-weighted mean {trial_weighted:+.2f}{unit}, raw mean {raw_mean:+.2f}{unit}")


def plot_condition_effect_histogram(exclude_session_ids=None, start_session_id=None,
                                    algorithm_label='none', metric=METRIC_PCT_HYPOTHESIZED,
                                    alternative='greater', min_trials=DEFAULT_MIN_TRIALS,
                                    bin_width=None, studentize=False,
                                    trial_types=None, exclude_ratio_ranges=None,
                                    merge_behavioral=False, stats_method=STATS_TTEST,
                                    save_path=None):
    """
    Histogram of per-condition effect sizes (ON% - OFF%, one value per qualifying
    condition across all sessions).

    stats_method  : 'ttest' (default) -> one-sample t-test on the histogram's values
                    (mean effect > 0 for alternative='greater').
                    'fisher_combined' -> session-level Fisher's combined test
                    on each session's pooled Fisher's exact p (not a test on the
                    histogram: conditions share OFF trials, so they are not independent).

    studentize    : True puts each condition's effect in z units (effect / chance SD),
                    so small-n conditions no longer fill the tails. z measures strength
                    of evidence, not effect magnitude.
    bin_width     : None -> 5 percentage points, or 0.5 z when studentized.
    trial_types   : None (all) or trial-type names to keep; added to the filename.
    exclude_ratio_ranges : None or [(lo, hi), ...] — drop conditions whose spec's
                    current : half-distance ratio lies in any range (inclusive; None
                    for an open end). Added to the filename.
    merge_behavioral : True -> one histogram value per (session, trial type, spec),
                    averaging that spec's behavioral groups (see _condition_arrays)
                    instead of one per condition. Adds __perspec to the filename.
                    The t-test then runs on the per-spec values; the Fisher's
                    combined test is unaffected (same trials).
    """
    rows = collect_session_rows(exclude_session_ids, start_session_id, algorithm_label,
                                metric, alternative, min_trials, trial_types=trial_types,
                                exclude_ratio_ranges=exclude_ratio_ranges)
    if not rows:
        print("No data to plot.")
        return None
    arrays = _condition_arrays(rows, studentize=studentize, merge_behavioral=merge_behavioral)
    pop = compute_population_stats(rows, alternative=alternative, stats_method=stats_method,
                                   effects=arrays['effects'], unit=arrays['unit'],
                                   noun=arrays['noun'])
    edges = _histogram_edges([arrays], _resolve_bin_width(bin_width, studentize))

    fig, ax = plt.subplots(figsize=(8, 5))
    _draw_condition_histogram(ax, rows, pop, arrays, edges,
                              alternative=alternative)
    ax.set_xlabel(_effect_axis_label(studentize, merge_behavioral), fontsize=12)
    ax.set_title(_filter_label(trial_types), fontsize=11, loc="left",
                 fontweight="bold")
    fig.tight_layout()

    _save_figure(fig, save_path, trial_types, exclude_ratio_ranges, merge_behavioral)

    plt.show()
    return fig


# ---------------------------------------------------------------------------
# Estim rules from the current : half-distance regressions
# ---------------------------------------------------------------------------
#
# ratio = current_per_second / corr half-distance  ((µA·Hz)/µm), per estim spec,
# computed exactly as in plot_current_spread_vs_tuning (same half-distance defaults).
# A condition is "within the rules" when its trial type has a rule and its spec's
# ratio falls in that range (inclusive). Trial types without a rule (Removed Trial,
# Coherence, ...) are left out of BOTH histograms, as are conditions whose spec has
# no ratio (missing current or half-distance).
ESTIM_RULES = {
    'Hypothesized Shape': (2.0, 4.0),
    'Delta Shape':        (0.0, 4.0),
}

# Alternative, cutoff-free rule ('closest' mode): for each trial type, rank every
# qualifying condition (pooled across sessions, after all other filters) by its
# distance |ratio - center| and call the closest DISTANCE_RULE_FRACTION of them
# "within the rules". Trial types without a center are left out, as in 'range' mode.
ESTIM_DISTANCE_CENTERS = {
    'Hypothesized Shape': 4.0,
    'Delta Shape':        0.0,
}
DISTANCE_RULE_FRACTION = 0.5

RULE_MODE_RANGE   = 'range'     # ESTIM_RULES hard ranges
RULE_MODE_CLOSEST = 'closest'   # closest fraction to ESTIM_DISTANCE_CENTERS
RULE_MODES = (RULE_MODE_RANGE, RULE_MODE_CLOSEST)

RULE_IN  = 'in'
RULE_OUT = 'out'

_SPEC_RATIO_CACHE = {}


def get_spec_ratios(session_id):
    """{estim_spec_id: current_per_second / corr half-distance} for one session
    (None where either piece is missing). Cached per session."""
    if session_id in _SPEC_RATIO_CACHE:
        return _SPEC_RATIO_CACHE[session_id]

    # Heavy modules (probe geometry, tuning metrics) — import only when needed.
    from src.analysis.nafc.group_analysis.analyze_estim_isolation_effect import (
        _fetch_current_per_second)
    from src.analysis.nafc.group_analysis.plot_current_spread_vs_tuning import (
        compute_session_half_distance)

    half_dist = compute_session_half_distance(session_id)
    cps = _fetch_current_per_second([(session_id, spec) for spec in half_dist])
    ratios = {}
    for spec, hd in half_dist.items():
        c = cps.get((session_id, int(spec)))
        ok = (hd is not None and c is not None and np.isfinite(hd) and np.isfinite(c)
              and hd > 0)
        ratios[int(spec)] = float(c) / float(hd) if ok else None
    _SPEC_RATIO_CACHE[session_id] = ratios
    return ratios


def _condition_ratio(session_id, cond_dict):
    """The condition's spec ratio, or None (no spec, or missing current / half-distance)."""
    spec = cond_dict.get('estim_spec_id')
    if spec is None or (isinstance(spec, float) and np.isnan(spec)):
        return None
    return get_spec_ratios(session_id).get(int(spec))


def classify_estim_rule(session_id, cond_dict, rules=ESTIM_RULES):
    """RULE_IN / RULE_OUT for a condition, or None if it is excluded from both
    (trial type has no rule, or the spec has no ratio)."""
    rng = rules.get(cond_dict.get('trial_type'))
    if rng is None:
        return None
    ratio = _condition_ratio(session_id, cond_dict)
    if ratio is None:
        return None
    lo, hi = rng
    return RULE_IN if lo <= ratio <= hi else RULE_OUT


def compute_closest_thresholds(centers=ESTIM_DISTANCE_CENTERS, fraction=DISTANCE_RULE_FRACTION,
                               merge_behavioral=False, **collect_kwargs):
    """
    {trial_type: max |ratio - center| of the closest ``fraction`` of units}.

    Ranks every unit the plot would use (collect_kwargs = the same session /
    trial-type / ratio-exclusion / min_trials filters as collect_session_rows),
    pooled across sessions, per trial type. A unit is a condition, or with
    merge_behavioral=True one (session, trial type, spec) — the spec's behavioral
    groups share one ratio, so they are ranked once instead of as a tied block. The
    closest ceil(fraction * n) set the threshold; units tied at the threshold are
    all kept, so ties can push the group slightly above ``fraction``.
    """
    if not 0 < fraction <= 1:
        raise ValueError(f"fraction must be in (0, 1], got {fraction}")

    def has_center_and_ratio(sid, cond):
        return (cond.get('trial_type') in centers
                and _condition_ratio(sid, cond) is not None)

    print("\n===== Ranking conditions by distance from center =====")
    rows = collect_session_rows(condition_filter=has_center_and_ratio, **collect_kwargs)

    distances = {tt: [] for tt in centers}
    seen = set()
    for d in rows:
        for c in d['conditions']:
            if merge_behavioral:
                key = _spec_unit_key(d['session_id'], c['cond_dict'])
                if key in seen:
                    continue
                seen.add(key)
            tt = c['cond_dict']['trial_type']
            ratio = _condition_ratio(d['session_id'], c['cond_dict'])
            distances[tt].append(abs(ratio - centers[tt]))
    noun = _unit_noun(merge_behavioral)

    thresholds = {}
    for tt, dist in distances.items():
        if not dist:
            print(f"  {tt}: no {noun} with a ratio")
            continue
        dist = np.sort(dist)
        k = int(np.ceil(fraction * len(dist)))
        thresholds[tt] = float(dist[k - 1])
        n_in = int(np.sum(dist <= thresholds[tt]))
        print(f"  {tt}: center {centers[tt]:g}, {len(dist)} {noun} -> closest {n_in} "
              f"(target {k}) have |ratio - center| <= {thresholds[tt]:.3g}")
    return thresholds


def classify_closest(session_id, cond_dict, centers, thresholds):
    """RULE_IN if the condition is within its trial type's closest-fraction distance,
    RULE_OUT otherwise, None if it has no center / threshold / ratio."""
    tt = cond_dict.get('trial_type')
    if tt not in centers or tt not in thresholds:
        return None
    ratio = _condition_ratio(session_id, cond_dict)
    if ratio is None:
        return None
    return RULE_IN if abs(ratio - centers[tt]) <= thresholds[tt] else RULE_OUT


def _describe_rules(rules):
    return "; ".join(f"{tt}: ratio in [{lo:g}, {hi:g}]" for tt, (lo, hi) in rules.items())


def plot_estim_rule_histograms(exclude_session_ids=None, start_session_id=None,
                               algorithm_label='none', metric=METRIC_PCT_HYPOTHESIZED,
                               alternative='greater', min_trials=DEFAULT_MIN_TRIALS,
                               rules=ESTIM_RULES, bin_width=None,
                               studentize=False, trial_types=None,
                               exclude_ratio_ranges=None, rule_mode=RULE_MODE_RANGE,
                               centers=ESTIM_DISTANCE_CENTERS,
                               fraction=DISTANCE_RULE_FRACTION, merge_behavioral=False,
                               stats_method=STATS_TTEST, save_path=None):
    """
    Per-condition effect histograms split by the estim rules, stacked on a shared
    x-axis (and shared bins / y-axis) for direct comparison:
        top    = conditions within the rules
        bottom = conditions outside the rules (same trial types, ratio out of range)

    Each panel has its own population test (stats_method): 'ttest' (default) runs a
    one-sample t-test on that panel's histogram values; 'fisher_combined' runs a
    session-level Fisher's combined test (each session's within-rule / outside-rule
    conditions pooled into their own 2x2 table).

    rule_mode     : 'range' (default) — within = ratio inside ESTIM_RULES[trial_type].
                    'closest' — within = the closest ``fraction`` of conditions to
                    centers[trial_type] by |ratio - center|, ranked per trial type
                    across all sessions (no hard cutoff). Adds __closest<NN> to the
                    filename.

    studentize    : True puts the x-axis in z units (see plot_condition_effect_histogram).
    bin_width     : None -> 5 percentage points, or 0.5 z when studentized.
    trial_types   : None (all) or trial-type names to keep; added to the filename.
                    Trial types without a rule are excluded regardless.
    exclude_ratio_ranges : None or [(lo, hi), ...] ratio ranges to drop (inclusive;
                    None for an open end), applied before the rule split.
    merge_behavioral : True -> one value per (session, trial type, spec), averaging
                    the spec's behavioral groups; in 'closest' mode specs (not
                    conditions) are ranked. Adds __perspec to the filename.
    """
    if rule_mode not in RULE_MODES:
        raise ValueError(f"rule_mode must be one of {RULE_MODES}, got {rule_mode!r}")

    common = dict(exclude_session_ids=exclude_session_ids, start_session_id=start_session_id,
                  algorithm_label=algorithm_label, metric=metric, alternative=alternative,
                  min_trials=min_trials, trial_types=trial_types,
                  exclude_ratio_ranges=exclude_ratio_ranges)

    if rule_mode == RULE_MODE_CLOSEST:
        thresholds = compute_closest_thresholds(centers, fraction,
                                                merge_behavioral=merge_behavioral, **common)
        pct = f"{100 * fraction:g}%"

        def classify(sid, cond):
            return classify_closest(sid, cond, centers, thresholds)
        groups = [(RULE_IN,  f"Closest {pct} to center",        "#d9534f"),
                  (RULE_OUT, f"Farther from center (other {100 - 100 * fraction:g}%)", "#7f7f7f")]
        rule_text = (f"Closest {pct} by |ratio − center|: " + "; ".join(
            f"{tt}: center {c:g}" + (f" (≤ {thresholds[tt]:.2g})" if tt in thresholds else "")
            for tt, c in centers.items()))
        if save_path:
            root, ext = os.path.splitext(save_path)
            save_path = f"{root}__closest{100 * fraction:g}{ext}"
    else:
        def classify(sid, cond):
            return classify_estim_rule(sid, cond, rules)
        groups = [(RULE_IN,  "Within estim rules",  "#d9534f"),
                  (RULE_OUT, "Outside estim rules", "#7f7f7f")]
        rule_text = f"Rules: {_describe_rules(rules)}"

    results = {}
    for key, label, _ in groups:
        print(f"\n===== {label} =====")
        rows = collect_session_rows(
            condition_filter=lambda sid, cond, key=key: classify(sid, cond) == key, **common)
        arrays = (_condition_arrays(rows, studentize=studentize,
                                    merge_behavioral=merge_behavioral) if rows else None)
        pop = (compute_population_stats(rows, alternative=alternative,
                                        stats_method=stats_method,
                                        effects=arrays['effects'], unit=arrays['unit'],
                                        noun=arrays['noun']) if rows else None)
        results[key] = (rows, pop, arrays)

    present = [results[k][2] for k, _, _ in groups if results[k][2] is not None]
    if not present:
        print("No conditions in either group.")
        return None
    edges = _histogram_edges(present, _resolve_bin_width(bin_width, studentize))

    fig, axes = plt.subplots(2, 1, figsize=(8, 8), sharex=True, sharey=True)
    for ax, (key, label, color) in zip(axes, groups):
        rows, pop, arrays = results[key]
        if arrays is None:
            ax.text(0.5, 0.5, "no conditions", transform=ax.transAxes,
                    ha="center", va="center", color="gray")
            ax.set_title(label, fontsize=11, loc="left", fontweight="bold")
            continue
        _draw_condition_histogram(ax, rows, pop, arrays, edges, alternative=alternative,
                                  color=color, title=label)

    axes[-1].set_xlabel(_effect_axis_label(studentize, merge_behavioral), fontsize=12)
    fig.suptitle(f"{_filter_label(trial_types)}  ·  {rule_text}",
                 fontsize=10, color="#444444")
    fig.tight_layout()

    _save_figure(fig, save_path, trial_types, exclude_ratio_ranges, merge_behavioral)

    plt.show()
    return fig


def plot_avg_estim_per_experiment(exclude_session_ids=None, start_session_id=None,
                                  algorithm_label='none', metric=METRIC_PCT_HYPOTHESIZED,
                                  alternative='greater', min_trials=DEFAULT_MIN_TRIALS,
                                  save_path=None, show_n=True,
                                  x_spacing=1.0, width_per_exp=1.5, trial_types=None,
                                  exclude_ratio_ranges=None, stats_method=STATS_TTEST):
    """
    exclude_session_ids : optional iterable of session_ids to drop.
    start_session_id    : only include sessions with session_id >= this value.
    algorithm_label     : which cutoff variant to apply (matches EStimSessionCutoffs).
    metric              : 'pct_hypothesized' or 'pct_hyp_vs_delta' trial filtering.
    alternative         : 'greater' tests EStim ON > OFF; 'less' tests ON < OFF.
    min_trials          : minimum trials in each group for a condition to be pooled.
    trial_types         : None (all) or trial-type names to keep; added to the filename.
    exclude_ratio_ranges: None or [(lo, hi), ...] ratio ranges to drop (inclusive;
                          None for an open end); added to the filename.
    stats_method        : 'ttest' (default) -> one-sample t-test on the per-session
                          pooled effects; 'fisher_combined' -> Fisher's combined test.
    """
    rows = collect_session_rows(exclude_session_ids, start_session_id, algorithm_label,
                                metric, alternative, min_trials, trial_types=trial_types,
                                exclude_ratio_ranges=exclude_ratio_ranges)
    if not rows:
        print("No data to plot.")
        return None

    pop = compute_population_stats(rows, alternative=alternative, stats_method=stats_method)

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
    ax.set_title(_filter_label(trial_types), fontsize=11, loc="left",
                 fontweight="bold")

    legend_handles = [
        mpatches.Patch(color=_COLOR_OFF, label="EStim OFF (all conditions pooled)"),
        mpatches.Patch(color=_COLOR_ON,  label="EStim ON (all conditions pooled)"),
    ]
    ax.legend(handles=legend_handles, fontsize=9, loc="lower right", framealpha=0.85)

    _draw_stats_panel(ax_panel, pop)

    fig.tight_layout()

    _save_figure(fig, save_path, trial_types, exclude_ratio_ranges)

    plt.show()
    return fig


def main():
    metric = METRIC_PCT_HYP_VS_DELTA
    exclude_session_ids = ["260421_0", "260410_0"]
    start_session_id = "260402_0"
    algorithm_label = 'None'
    # Trial types to include in EVERY plot below; None = all. The filter is appended
    # to each saved filename, e.g. ..._histogram__HypothesizedShape.png
    trial_types = None
    # trial_types = ['Hypothesized Shape']
    trial_types = ['Hypothesized Shape', 'Delta Shape']
    # trial_types = ['Delta Shape']
    # current : half-distance ratio ranges to drop from EVERY plot (inclusive; None =
    # open end); also appended to each filename, e.g. ..._histogram__xratio8-inf.png
    exclude_ratio_ranges = [(8, None)]
    # exclude_ratio_ranges = [(8, None)]          # drop ratio >= 8
    # exclude_ratio_ranges = [(None, 0.5), (8, None)]
    # True -> one histogram value per (session, trial type, spec), averaging the spec's
    # behavioral groups (noise, coherence, ...); False -> one per condition. Adds
    # __perspec to the histogram filenames.
    merge_behavioral = True

    rule_mode = 'closest'
    # 'range'   -> hard ranges in ESTIM_RULES
    # 'closest' -> closest DISTANCE_RULE_FRACTION of conditions to
    #              ESTIM_DISTANCE_CENTERS (Hypothesized 4, Delta 0), no hard cutoff

    # Population test, used by every plot below:
    # 'ttest'           -> one-sample t-test on the plotted distribution of EStim
    #                      effects (one value per condition / spec / session),
    #                      H1: mean effect > 0 (alternative='greater')
    # 'fisher_combined' -> Fisher's combined test over per-session Fisher's exact p's
    stats_method = 'ttest'

    studentize = False
    min_trials = 10
    plot_condition_effect_histogram(
        exclude_session_ids=exclude_session_ids,
        start_session_id=start_session_id,
        algorithm_label=algorithm_label,
        metric=metric,
        alternative='greater',   # 'less' -> test whether the average effect is negative
        min_trials=min_trials,
        bin_width=None,          # None -> 5 %-points, or 0.5 z when studentized
        studentize=studentize,        # True -> x-axis in z = effect / chance SD
        trial_types=trial_types,
        exclude_ratio_ranges=exclude_ratio_ranges,
        merge_behavioral=merge_behavioral,
        stats_method=stats_method,
        save_path="/home/connorlab/Documents/plots/across_experiments/avg_estim_condition_histogram.png",
    )

    # Same histogram, split by the current : half-distance estim rules (ESTIM_RULES).

    plot_estim_rule_histograms(
        exclude_session_ids=exclude_session_ids,
        start_session_id=start_session_id,
        algorithm_label=algorithm_label,
        metric=metric,
        alternative='greater',
        min_trials=min_trials,
        bin_width=10,
        # False -> raw mean (every condition counts equally)
        studentize=studentize,        # True -> x-axis in z = effect / chance SD
        trial_types=trial_types,
        exclude_ratio_ranges=exclude_ratio_ranges,
        rule_mode=rule_mode,
        merge_behavioral=merge_behavioral,
        stats_method=stats_method,
        save_path="/home/connorlab/Documents/plots/across_experiments/avg_estim_rule_histograms.png",
    )

    # Per-session ON/OFF dot plot (same test, one pooled pair of dots per session):
    # plot_avg_estim_per_experiment(
    #     exclude_session_ids=exclude_session_ids,
    #     start_session_id=start_session_id,
    #     algorithm_label=algorithm_label,
    #     metric=metric,
    #     alternative='greater',
    #     min_trials=10,
    #     save_path="/home/connorlab/Documents/plots/across_experiments/avg_estim_per_experiment.png",
    #     show_n=False,
    #     x_spacing=0.75,
    #     width_per_exp=1.0,
    #     trial_types=trial_types,
    #     exclude_ratio_ranges=exclude_ratio_ranges,
    #     stats_method=stats_method,
    # )


if __name__ == "__main__":
    main()
