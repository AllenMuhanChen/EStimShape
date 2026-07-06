"""
Analyze how EStim effect degradation relates to estim / behavioral conditions.

Reads EStimShapeTrials + EStimSessionCutoffs. For a given cutoff algorithm_label
(default ``first_drop_w50_s5_t0_n2_m10``), every condition that has a stored
cutoff is split at its cutoff trial into:

  - a BEFORE portion : trials with trial_start <= max_trial_start
  - an AFTER  portion : trials with trial_start >  max_trial_start

and two degradation metrics are computed per condition:

  1) Degradation Strength = mean estim effect AFTER cutoff / mean estim effect
     BEFORE cutoff.  ~1 means the effect held up; near 0 means it collapsed;
     negative means it reversed after the cutoff.
  2) Degradation Onset    = number of estim-on trials BEFORE the cutoff (how many
     estim-on presentations the effect survived before degrading).

Each condition's estim_spec_id is unfurled into its physical EStimParameters
(a1, polarity, shape, num_channels, pulse_rate_hz, ...), its derived
hyperparameters (total current per pulse / total current / current per second,
from estim_hyperparameters), and combined with its behavioral conditions
(trial_type, noise_chance, sample_length). For every parameter we plot each
metric against that parameter's value. Numeric
parameters (e.g. a1) are coerced to float and sorted ascending; categorical
parameters (e.g. polarity) are shown as ordered categories.

A second analysis asks whether the same parameters predict WHETHER a condition
degraded at all. Each condition is labelled 'degraded' (has a cutoff) or
'robust' (no cutoff and a full-data effect that clears an effect-size / n
threshold, default > 15 pp and n_on > 10). For every parameter we then plot the
fraction of conditions that degraded against that parameter's value.
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parents[3]))

from clat.util.connection import Connection
from src.analysis.nafc.group_analysis.estim_session_cutoffs import (
    _get_all_trials_ordered,
    _effect_and_ns_for_condition,
    _count_estim_on_for_condition,
    _parse_conditions_json,
)
from src.analysis.nafc.group_analysis.max_estim_per_experiment import (
    _expand_condition,
    _to_float,
    _clean_num,
)
from src.analysis.nafc.group_analysis.analyze_estim_by_condition import (
    METRIC_PCT_HYP_VS_DELTA,
    _normalize_cond_key,
)
from src.analysis.nafc.estim_hyperparameters import (
    get_estim_hyperparameters,
    HYPERPARAMETER_NAMES,
)

DEFAULT_ALGORITHM_LABEL = 'first_drop_w5_s1_t0_n3_m10_g5_xestim'

# Thresholds defining a "robust" (non-degraded) condition for the degraded-vs-robust
# comparison: a condition with NO cutoff whose full-data effect clears these bars.
DEFAULT_EFFECT_THRESHOLD = 5  # percentage points
DEFAULT_MIN_N = 10               # estim-on trials

# Columns of the degradation / classification tables that are bookkeeping / metrics,
# NOT parameters to plot against. Everything else is treated as a condition parameter.
_NON_PARAM_COLUMNS = {
    'session_id', 'estim_spec_id', 'max_trial_start',
    'degradation_strength', 'degradation_onset',
    'effect_before', 'effect_after',
    'n_on_before', 'n_on_after', 'n_off_before', 'n_off_after',
    'group', 'full_effect', 'n_on', 'n_off', 'enable_charge_recovery',
    'num_procedural_distractors', 'num_choices', 'num_rand_distractors'

}

# The metrics we plot, in display order: column name -> axis label.
_METRICS = {
    'degradation_strength': 'Degradation Strength\n(effect after / before cutoff)',
    'degradation_onset': 'Degradation Onset\n(# estim-on trials before cutoff)',
}

# Preferred left-to-right ordering of parameters in the plot grid. Any parameter
# not listed here is appended afterwards in alphabetical order. The derived
# hyperparameters (total current per pulse, total current, current per second)
# are included alongside the base estim parameters.
_PARAM_ORDER = [
    'a1', 'polarity', 'shape', 'num_channels', 'pulse_rate_hz',
    'post_trigger_delay', 'enable_charge_recovery',
    'total_current_per_pulse', 'total_current', 'current_per_second',
    'trial_type', 'noise_chance', 'sample_length',
]

# Formula shown in parentheses on the x-axis label for derived hyperparameters.
_PARAM_FORMULAS = {
    'total_current_per_pulse': 'a1 * num_channels',
    'total_current': 'a1 * num_channels * num_pulses',
    'current_per_second': 'a1 * num_channels * pulse_rate_hz',
}


def _param_xlabel(param):
    """X-axis label for a parameter, with the derivation formula in parentheses
    for hyperparameters (e.g. 'total_current\\n(a1 * num_channels * num_pulses)')."""
    formula = _PARAM_FORMULAS.get(param)
    return f"{param}\n({formula})" if formula else param


# Some parameters carry small jitter / spurious precision (e.g. a pulse rate that
# lands at 98 or 203 Hz, or post-trigger delays a few µs off a round value). Bin
# these to a sensible grid before grouping/plotting so near-identical conditions
# collapse onto the same x value. param name -> bin width (nearest multiple).
_PARAM_BIN_SIZES = {
    'pulse_rate_hz': 25,        # nearest 50 Hz (±25)
    'post_trigger_delay': 1000,  # nearest 1000 µs
    'total_current': 100,
    'current_per_second': 200
}


def _bin_value(value, bin_size):
    """Round a numeric value to the nearest multiple of bin_size; pass through
    None / non-numeric values unchanged. Integer-valued bins stay ints for clean
    axis labels."""
    f = _to_float(value)
    if f is None:
        return value
    binned = round(f / bin_size) * bin_size
    return int(binned) if binned == int(binned) else binned


def _expand_with_hyperparameters(session_id, cond_dict):
    """Unfurl a condition's estim_spec_id into its physical EStimParameters AND its
    derived hyperparameters (total current per pulse / total current / current per
    second), keeping behavioral keys unchanged, then bin the jittery parameters.
    Used by both build_* tables."""
    params = _expand_condition(session_id, cond_dict)
    spec_id = cond_dict.get('estim_spec_id')
    if spec_id is not None:
        # sample_length (ms) is the LEVEL trigger's hold window; needed to count
        # pulses for level-triggered specs (num_repetitions is a default there).
        params.update(get_estim_hyperparameters(
            session_id, spec_id, sample_duration_ms=cond_dict.get('sample_length')))
    for key, bin_size in _PARAM_BIN_SIZES.items():
        if params.get(key) is not None:
            params[key] = _bin_value(params[key], bin_size)
    return params


def get_cutoffs(algorithm_label, session_id=None):
    """Return list of (session_id, conditions_json, max_trial_start) for the label."""
    conn = Connection("allen_data_repository")
    if session_id:
        conn.execute(
            "SELECT session_id, conditions, max_trial_start FROM EStimSessionCutoffs "
            "WHERE algorithm_label = %s AND session_id = %s",
            (algorithm_label, session_id))
    else:
        conn.execute(
            "SELECT session_id, conditions, max_trial_start FROM EStimSessionCutoffs "
            "WHERE algorithm_label = %s",
            (algorithm_label,))
    return [(row[0], row[1], row[2]) for row in conn.fetch_all()]


def compute_degradation_metrics(trials_df, cond_dict, max_trial_start):
    """
    Split trials_df at max_trial_start and compute degradation metrics for cond_dict.

    Returns a dict with the two headline metrics plus the underlying effects and
    trial counts, or None if there is no positive before-cutoff effect to compare
    against (degradation strength would be undefined).
    """
    before = trials_df[trials_df['trial_start'] <= max_trial_start]
    after = trials_df[trials_df['trial_start'] > max_trial_start]

    eff_before, n_on_before, n_off_before = _effect_and_ns_for_condition(before, cond_dict)
    eff_after, n_on_after, n_off_after = _effect_and_ns_for_condition(after, cond_dict)

    # Degradation strength is the ratio of after-effect to before-effect. It is only
    # meaningful when the condition had a positive effect before the cutoff (which is
    # the premise of the cutoff procedure); otherwise the ratio is undefined.
    if eff_before is None or eff_before <= 0:
        strength = None
    elif eff_after is None:
        strength = None
    else:
        strength = eff_after / eff_before

    return {
        'degradation_strength': strength,
        'degradation_onset': _count_estim_on_for_condition(before, cond_dict),
        'effect_before': eff_before,
        'effect_after': eff_after,
        'n_on_before': n_on_before,
        'n_on_after': n_on_after,
        'n_off_before': n_off_before,
        'n_off_after': n_off_after,
    }


def build_degradation_table(algorithm_label=DEFAULT_ALGORITHM_LABEL, session_id=None):
    """
    Build a one-row-per-condition DataFrame of degradation metrics joined with the
    condition's estim parameters (estim_spec_id unfurled) and behavioral conditions.
    """
    cutoffs = get_cutoffs(algorithm_label, session_id)
    print(f"Found {len(cutoffs)} stored cutoffs for algorithm_label='{algorithm_label}'"
          + (f" (session {session_id})" if session_id else ""))

    trials_cache = {}
    records = []
    for sid, conditions_json, max_trial_start in cutoffs:
        try:
            cond_dict = _parse_conditions_json(conditions_json)
        except Exception as e:
            print(f"  WARNING: skipping unparseable conditions for {sid}: {e}")
            continue

        if sid not in trials_cache:
            trials_cache[sid] = _get_all_trials_ordered(sid)
        trials_df = trials_cache[sid]

        metrics = compute_degradation_metrics(trials_df, cond_dict, max_trial_start)

        # Unfurl estim_spec_id into the physical stimulation parameters + derived
        # hyperparameters, keeping the behavioral keys (trial_type, noise_chance,
        # sample_length) as-is.
        params = _expand_with_hyperparameters(sid, cond_dict)

        record = {'session_id': sid, 'max_trial_start': max_trial_start}
        record.update(params)
        record.update(metrics)
        records.append(record)

    df = pd.DataFrame(records)
    n_strength = int(df['degradation_strength'].notna().sum()) if not df.empty else 0
    print(f"Built degradation table: {len(df)} conditions "
          f"({n_strength} with a defined degradation strength)")
    return df


def _parameter_columns(df):
    """Parameter columns present in df, ordered by _PARAM_ORDER then alphabetically."""
    present = [c for c in df.columns if c not in _NON_PARAM_COLUMNS]
    ordered = [c for c in _PARAM_ORDER if c in present]
    ordered += sorted(c for c in present if c not in _PARAM_ORDER)
    return ordered


def _is_numeric_param(values):
    """True if every non-null value coerces to a float (e.g. a1, noise_chance)."""
    non_null = [v for v in values if v is not None and not (isinstance(v, float) and np.isnan(v))]
    if not non_null:
        return False
    return all(_to_float(v) is not None for v in non_null)


def _sem(vals):
    """Standard error of the mean of a list of values; 0 for a single sample."""
    n = len(vals)
    if n <= 1:
        return 0.0
    return float(np.std(vals, ddof=1) / np.sqrt(n))


def _prop_sem(vals):
    """Standard error of a proportion (list of 0/1 outcomes): sqrt(p*(1-p)/n)."""
    n = len(vals)
    if n == 0:
        return 0.0
    p = float(np.mean(vals))
    return float(np.sqrt(p * (1 - p) / n))


def _make_subset_colors(df, subset_by):
    """Stable color per subset value (sorted), so the same subset is drawn in the same
    color across every subplot. Returns {str(value): rgba} or None if subset_by is
    missing / has no non-null values."""
    if not subset_by or subset_by not in df.columns:
        return None
    vals = sorted({str(v) for v in df[subset_by].dropna().tolist()}, key=str)
    if not vals:
        return None
    cmap = plt.get_cmap('tab10')
    return {v: cmap(i % 10) for i, v in enumerate(vals)}


def _plot_numeric_param(ax, xs, ys, subsets=None, colors=None):
    """Scatter all (x, y) points and overlay a line connecting the per-value mean.

    If ``subsets`` (a subset label per point) is given, draw one mean line per subset
    value in its assigned color plus a bold black combined-total line; otherwise draw
    the single firebrick mean line (original behavior)."""
    def _mean_line(sel_xs, sel_ys, color, label, zorder=3):
        by_x = {}
        for x, y in zip(sel_xs, sel_ys):
            by_x.setdefault(x, []).append(y)
        uniq = sorted(by_x)
        means = [float(np.mean(by_x[x])) for x in uniq]
        sems = [_sem(by_x[x]) for x in uniq]
        ax.errorbar(uniq, means, yerr=sems, fmt='-o', color=color, markersize=5,
                    linewidth=1.5, capsize=3, elinewidth=1, label=label, zorder=zorder)
        for x, m in zip(uniq, means):
            ax.annotate(f"n={len(by_x[x])}", (x, m), textcoords='offset points',
                        xytext=(0, 6), fontsize=6, ha='center', color=color, zorder=zorder)

    if subsets is None:
        ax.scatter(xs, ys, alpha=0.4, s=25, color='steelblue', edgecolor='none')
        _mean_line(xs, ys, 'firebrick', 'mean')
    else:
        colors = colors or {}
        pt_colors = [colors.get(s, 'gray') for s in subsets]
        ax.scatter(xs, ys, alpha=0.3, s=25, c=pt_colors, edgecolor='none')
        for s in sorted(set(subsets), key=str):
            sx = [x for x, ss in zip(xs, subsets) if ss == s]
            sy = [y for y, ss in zip(ys, subsets) if ss == s]
            _mean_line(sx, sy, colors.get(s, 'gray'), str(s))
        _mean_line(xs, ys, 'black', 'total', zorder=4)
    ax.legend(fontsize=7)


def _plot_categorical_param(ax, cats, ys, subsets=None, colors=None):
    """Strip plot of categories (with jitter) and a diamond at each category mean.

    If ``subsets`` is given, draw one connected diamond mean-line per subset value in
    its color plus a bold black combined-total line; otherwise draw the single
    firebrick per-category mean diamonds (original behavior)."""
    labels = sorted(set(cats), key=str)
    pos = {c: i for i, c in enumerate(labels)}
    rng = np.random.default_rng(0)
    jitter = rng.uniform(-0.12, 0.12, size=len(cats))
    xpos = [pos[c] + j for c, j in zip(cats, jitter)]

    def _mean_diamonds(sel_cats, sel_ys, color, label, connect):
        by_cat = {}
        for c, y in zip(sel_cats, sel_ys):
            by_cat.setdefault(c, []).append(y)
        present = [c for c in labels if c in by_cat]
        px = [pos[c] for c in present]
        means = [float(np.mean(by_cat[c])) for c in present]
        sems = [_sem(by_cat[c]) for c in present]
        ax.errorbar(px, means, yerr=sems, fmt='-D' if connect else 'D', color=color,
                    markersize=7, capsize=3, elinewidth=1, label=label)
        for c, m in zip(present, means):
            ax.annotate(f"n={len(by_cat[c])}", (pos[c], m), textcoords='offset points',
                        xytext=(0, 8), fontsize=6, ha='center', color=color)

    if subsets is None:
        ax.scatter(xpos, ys, alpha=0.4, s=25, color='steelblue', edgecolor='none')
        _mean_diamonds(cats, ys, 'firebrick', 'mean', connect=False)
    else:
        colors = colors or {}
        pt_colors = [colors.get(s, 'gray') for s in subsets]
        ax.scatter(xpos, ys, alpha=0.3, s=25, c=pt_colors, edgecolor='none')
        for s in sorted(set(subsets), key=str):
            sc = [c for c, ss in zip(cats, subsets) if ss == s]
            sy = [y for y, ss in zip(ys, subsets) if ss == s]
            _mean_diamonds(sc, sy, colors.get(s, 'gray'), str(s), connect=True)
        _mean_diamonds(cats, ys, 'black', 'total', connect=True)

    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels([str(_clean_num(c)) for c in labels], rotation=30, ha='right',
                       fontsize=8)
    ax.legend(fontsize=7)


def plot_degradation_metric(df, metric_key, algorithm_label=DEFAULT_ALGORITHM_LABEL,
                            save_path=None, subset_by=None):
    """
    For one metric, plot it against every condition parameter (one subplot each).
    Numeric parameters are sorted ascending on a float axis; categorical parameters
    are shown as ordered categories.

    If ``subset_by`` names a parameter (e.g. 'polarity'), each subplot overlays one
    mean line per value of that parameter plus a combined-total line. The subplot for
    the subset parameter itself is drawn un-subsetted (subsetting it would be trivial).
    """
    if df.empty:
        print(f"No data to plot for metric '{metric_key}'.")
        return None

    params = _parameter_columns(df)
    valid = df[df[metric_key].notna()]
    if valid.empty:
        print(f"No conditions with a defined '{metric_key}'.")
        return None

    colors = _make_subset_colors(valid, subset_by)

    n = len(params)
    ncols = min(3, n)
    nrows = (n + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(5.5 * ncols, 4 * nrows),
                             squeeze=False)

    for i, param in enumerate(params):
        ax = axes[i // ncols][i % ncols]
        use_subset = colors is not None and subset_by != param
        cols = [param, metric_key] + ([subset_by] if use_subset else [])
        sub = valid[cols].copy()
        sub = sub[sub[param].notna()]
        if use_subset:
            sub = sub[sub[subset_by].notna()]
        if sub.empty:
            ax.text(0.5, 0.5, 'no data', ha='center', va='center', transform=ax.transAxes)
            ax.set_title(param, fontsize=10, fontweight='bold')
            continue

        ys = sub[metric_key].astype(float).tolist()
        raw_vals = sub[param].tolist()
        subsets = [str(v) for v in sub[subset_by].tolist()] if use_subset else None

        if _is_numeric_param(raw_vals):
            xs = [_to_float(v) for v in raw_vals]
            _plot_numeric_param(ax, xs, ys, subsets=subsets, colors=colors)
        else:
            _plot_categorical_param(ax, [str(v) for v in raw_vals], ys,
                                    subsets=subsets, colors=colors)

        if metric_key == 'degradation_strength':
            ax.axhline(1.0, color='gray', linestyle=':', linewidth=1, alpha=0.6)
            ax.axhline(0.0, color='gray', linestyle='--', linewidth=0.8, alpha=0.4)
        ax.set_title(param, fontsize=10, fontweight='bold')
        ax.set_xlabel(_param_xlabel(param), fontsize=9)
        ax.set_ylabel(_METRICS[metric_key], fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.set_axisbelow(True)

    for j in range(n, nrows * ncols):
        axes[j // ncols][j % ncols].axis('off')

    subset_note = f", by {subset_by}" if colors is not None else ""
    fig.suptitle(f"{_METRICS[metric_key].splitlines()[0]} vs condition parameters\n"
                 f"({len(valid)} conditions, algorithm='{algorithm_label}'{subset_note})",
                 fontsize=13, fontweight='bold')
    fig.tight_layout(rect=[0, 0, 1, 0.94])

    if save_path:
        import os
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        fig.savefig(save_path, bbox_inches='tight', dpi=150)
        print(f"Saved to {save_path}")

    plt.show()
    return fig


# ---------------------------------------------------------------------------
# Degraded vs robust comparison: do the same parameters predict WHETHER a
# condition degraded at all?  A condition is "degraded" if it has a stored
# cutoff under this algorithm_label; it is "robust" if it has NO cutoff and its
# full-data effect clears an effect-size and trial-count threshold (default
# > 15 pp, n_on > 10).  Conditions that neither degraded nor reached a strong
# stable effect are dropped (they tell us nothing about degradation).
# ---------------------------------------------------------------------------

def _get_condition_universe(metric, session_id=None):
    """All distinct (session_id, conditions_json) present in EStimEffects for a metric.

    EStimEffects is the same condition universe the cutoff search iterates, so this
    captures every condition that could have degraded — whether or not it did.
    """
    conn = Connection("allen_data_repository")
    if session_id:
        conn.execute(
            "SELECT DISTINCT session_id, conditions FROM EStimEffects "
            "WHERE metric = %s AND session_id = %s", (metric, session_id))
    else:
        conn.execute(
            "SELECT DISTINCT session_id, conditions FROM EStimEffects WHERE metric = %s",
            (metric,))
    return [(row[0], row[1]) for row in conn.fetch_all()]


def build_condition_classification_table(algorithm_label=DEFAULT_ALGORITHM_LABEL,
                                         metric=METRIC_PCT_HYP_VS_DELTA,
                                         effect_threshold=DEFAULT_EFFECT_THRESHOLD,
                                         min_n=DEFAULT_MIN_N, session_id=None):
    """
    Label every condition as 'degraded' (has a cutoff) or 'robust' (no cutoff and
    full-data effect > effect_threshold with n_on > min_n), and join each with its
    estim parameters (estim_spec_id unfurled) and behavioral conditions.

    Returns a one-row-per-condition DataFrame; conditions that are neither degraded
    nor robust are excluded.
    """
    # Degraded conditions: those with a stored cutoff under this algorithm_label.
    degraded_keys = set()
    for sid, conditions_json, _ in get_cutoffs(algorithm_label, session_id):
        try:
            cond = _parse_conditions_json(conditions_json)
        except Exception:
            continue
        degraded_keys.add((sid, _normalize_cond_key(cond)))

    trials_cache = {}
    seen = set()
    records = []
    for sid, conditions_json in _get_condition_universe(metric, session_id):
        try:
            cond_dict = _parse_conditions_json(conditions_json)
        except Exception:
            continue
        key = (sid, _normalize_cond_key(cond_dict))
        if key in seen:
            continue
        seen.add(key)

        if sid not in trials_cache:
            trials_cache[sid] = _get_all_trials_ordered(sid)
        full_eff, n_on, n_off = _effect_and_ns_for_condition(
            trials_cache[sid], cond_dict, metric=metric)

        if key in degraded_keys:
            group = 'degraded'
        elif full_eff is not None and full_eff > effect_threshold and n_on > min_n:
            group = 'robust'
        else:
            continue  # neither clearly degraded nor a strong stable effect

        record = {'session_id': sid, 'group': group,
                  'full_effect': full_eff, 'n_on': n_on, 'n_off': n_off}
        record.update(_expand_with_hyperparameters(sid, cond_dict))
        records.append(record)

    df = pd.DataFrame(records)
    if df.empty:
        print("No conditions classified as degraded or robust.")
        return df
    n_deg = int((df['group'] == 'degraded').sum())
    n_rob = int((df['group'] == 'robust').sum())
    print(f"Classified {len(df)} conditions: {n_deg} degraded, {n_rob} robust "
          f"(robust = no cutoff, effect > {effect_threshold}pp, n_on > {min_n})")
    return df


def _plot_likelihood_numeric(ax, xs, is_degraded, subsets=None, colors=None):
    """Plot fraction-degraded vs a numeric parameter, annotated with counts.

    If ``subsets`` is given, draw one fraction line per subset value plus a bold black
    combined-total line (only the total line is annotated with counts, to keep the
    subplot readable)."""
    def _frac_line(sx, sd, color, label):
        by_x = {}
        for x, d in zip(sx, sd):
            by_x.setdefault(x, []).append(d)
        uniq = sorted(by_x)
        fracs = [float(np.mean(by_x[x])) for x in uniq]
        sems = [_prop_sem(by_x[x]) for x in uniq]
        ax.errorbar(uniq, fracs, yerr=sems, fmt='-o', color=color, markersize=5,
                    linewidth=1.5, capsize=3, elinewidth=1, label=label)
        for x in uniq:
            lst = by_x[x]
            ax.annotate(f"{int(sum(lst))}/{len(lst)}", (x, float(np.mean(lst))),
                        textcoords='offset points', xytext=(0, 6), fontsize=6,
                        ha='center', color=color)

    if subsets is None:
        _frac_line(xs, is_degraded, 'purple', None)
    else:
        colors = colors or {}
        for s in sorted(set(subsets), key=str):
            sx = [x for x, ss in zip(xs, subsets) if ss == s]
            sd = [d for d, ss in zip(is_degraded, subsets) if ss == s]
            _frac_line(sx, sd, colors.get(s, 'gray'), str(s))
        _frac_line(xs, is_degraded, 'black', 'total')
        ax.legend(fontsize=7)


def _plot_likelihood_categorical(ax, cats, is_degraded, subsets=None, colors=None):
    """Bar chart of fraction-degraded per category, annotated with counts.

    If ``subsets`` is given, draw grouped bars — one bar per subset value per category
    plus a combined-total bar — instead of a single bar per category."""
    labels = sorted(set(cats), key=str)

    if subsets is None:
        by_cat = {}
        for c, d in zip(cats, is_degraded):
            by_cat.setdefault(c, []).append(d)
        fracs = [float(np.mean(by_cat[c])) for c in labels]
        sems = [_prop_sem(by_cat[c]) for c in labels]
        ax.bar(range(len(labels)), fracs, yerr=sems, capsize=3, color='mediumpurple',
               edgecolor='black')
        for i, c in enumerate(labels):
            lst = by_cat[c]
            ax.text(i, float(np.mean(lst)) + _prop_sem(lst), f"{int(sum(lst))}/{len(lst)}",
                    ha='center', va='bottom', fontsize=6)
    else:
        colors = colors or {}
        subs = sorted(set(subsets), key=str)
        by = {}
        for c, d, s in zip(cats, is_degraded, subsets):
            by.setdefault((c, s), []).append(d)
        by_cat = {}
        for c, d in zip(cats, is_degraded):
            by_cat.setdefault(c, []).append(d)
        # One slot per subset plus a trailing 'total' slot, centered on each category.
        n_slots = len(subs) + 1
        width = 0.8 / n_slots

        def _annotate_bars(positions, groups, color):
            for x, lst in zip(positions, groups):
                ax.text(x, float(np.mean(lst)) + _prop_sem(lst),
                        f"{int(sum(lst))}/{len(lst)}", ha='center', va='bottom',
                        fontsize=5, color=color, rotation=90)

        for j, s in enumerate(subs):
            fracs, sems, positions, groups = [], [], [], []
            for i, c in enumerate(labels):
                if (c, s) in by:
                    lst = by[(c, s)]
                    fracs.append(float(np.mean(lst)))
                    sems.append(_prop_sem(lst))
                    positions.append(i + (j - (n_slots - 1) / 2) * width)
                    groups.append(lst)
            color = colors.get(s, 'gray')
            ax.bar(positions, fracs, width=width, yerr=sems, capsize=2, color=color,
                   edgecolor='black', label=str(s))
            _annotate_bars(positions, groups, color)
        total_fracs = [float(np.mean(by_cat[c])) for c in labels]
        total_sems = [_prop_sem(by_cat[c]) for c in labels]
        total_pos = [i + (len(subs) - (n_slots - 1) / 2) * width for i in range(len(labels))]
        ax.bar(total_pos, total_fracs, width=width, yerr=total_sems, capsize=2,
               color='black', edgecolor='black', label='total')
        _annotate_bars(total_pos, [by_cat[c] for c in labels], 'black')
        ax.legend(fontsize=7)

    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels([str(_clean_num(c)) for c in labels], rotation=30, ha='right',
                       fontsize=8)


def plot_degradation_likelihood(df, algorithm_label=DEFAULT_ALGORITHM_LABEL,
                                effect_threshold=DEFAULT_EFFECT_THRESHOLD,
                                min_n=DEFAULT_MIN_N, save_path=None, subset_by=None):
    """
    For every condition parameter, plot the fraction of conditions that DEGRADED as a
    function of that parameter's value (degraded vs robust, one subplot per parameter).
    Numeric parameters are sorted ascending; categorical parameters are ordered
    categories. Each point/bar is annotated with (# degraded / # conditions).

    If ``subset_by`` names a parameter (e.g. 'polarity'), each subplot draws one
    fraction line / grouped bar per value of that parameter plus a combined-total.
    """
    if df.empty:
        print("No classified conditions to plot.")
        return None

    is_deg_col = (df['group'] == 'degraded').astype(int)
    colors = _make_subset_colors(df, subset_by)
    params = _parameter_columns(df)
    n = len(params)
    ncols = min(3, n)
    nrows = (n + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(5.5 * ncols, 4 * nrows),
                             squeeze=False)

    for i, param in enumerate(params):
        ax = axes[i // ncols][i % ncols]
        use_subset = colors is not None and subset_by != param
        mask = df[param].notna()
        if use_subset:
            mask &= df[subset_by].notna()
        if not mask.any():
            ax.text(0.5, 0.5, 'no data', ha='center', va='center', transform=ax.transAxes)
            ax.set_title(param, fontsize=10, fontweight='bold')
            continue

        raw_vals = df.loc[mask, param].tolist()
        is_deg = is_deg_col[mask].tolist()
        subsets = [str(v) for v in df.loc[mask, subset_by].tolist()] if use_subset else None

        if _is_numeric_param(raw_vals):
            _plot_likelihood_numeric(ax, [_to_float(v) for v in raw_vals], is_deg,
                                     subsets=subsets, colors=colors)
        else:
            _plot_likelihood_categorical(ax, [str(v) for v in raw_vals], is_deg,
                                         subsets=subsets, colors=colors)

        ax.axhline(0.5, color='gray', linestyle=':', linewidth=1, alpha=0.6)
        ax.set_ylim(-0.05, 1.1)
        ax.set_title(param, fontsize=10, fontweight='bold')
        ax.set_xlabel(_param_xlabel(param), fontsize=9)
        ax.set_ylabel('Fraction degraded', fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.set_axisbelow(True)

    for j in range(n, nrows * ncols):
        axes[j // ncols][j % ncols].axis('off')

    n_deg = int(is_deg_col.sum())
    n_rob = len(df) - n_deg
    subset_note = f", by {subset_by}" if colors is not None else ""
    fig.suptitle(f"Fraction of conditions that degraded vs condition parameters\n"
                 f"({n_deg} degraded vs {n_rob} robust [effect > {effect_threshold}pp, "
                 f"n_on > {min_n}], algorithm='{algorithm_label}'{subset_note})",
                 fontsize=13, fontweight='bold')
    fig.tight_layout(rect=[0, 0, 1, 0.93])

    if save_path:
        import os
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        fig.savefig(save_path, bbox_inches='tight', dpi=150)
        print(f"Saved to {save_path}")

    plt.show()
    return fig


# ---------------------------------------------------------------------------
# Effect-size-vs-parameter comparison: instead of asking WHETHER a condition
# degraded, plot the condition's actual full-data estim effect size (from
# pct_hyp_vs_delta) against every parameter. Uses the same parameter set,
# binning, and min_n trial-count gate as the degraded-vs-robust comparison, but
# applies NO effect-size threshold — weak and reversed effects are kept so the
# plotted mean is the true average effect at each parameter value.
# ---------------------------------------------------------------------------

# Axis label for the effect-size plots (metric is pct_hyp_vs_delta).
_EFFECT_SIZE_YLABEL = 'Estim effect size (pp)\n(%hyp_vs_delta, estim-on - estim-off)'


def build_effect_size_table(metric=METRIC_PCT_HYP_VS_DELTA, min_n=DEFAULT_MIN_N,
                            session_id=None):
    """
    Build a one-row-per-condition DataFrame of each condition's full-data estim effect
    size (measured with `metric`, default pct_hyp_vs_delta), joined with its estim
    parameters (estim_spec_id unfurled + derived hyperparameters) and behavioral
    conditions.

    Conditions are kept if they have enough estim-on trials (n_on > min_n). Unlike the
    degraded-vs-robust classification there is NO effect-size threshold, so weak,
    zero, and reversed effects are all included.
    """
    trials_cache = {}
    seen = set()
    records = []
    for sid, conditions_json in _get_condition_universe(metric, session_id):
        try:
            cond_dict = _parse_conditions_json(conditions_json)
        except Exception:
            continue
        key = (sid, _normalize_cond_key(cond_dict))
        if key in seen:
            continue
        seen.add(key)

        if sid not in trials_cache:
            trials_cache[sid] = _get_all_trials_ordered(sid)
        full_eff, n_on, n_off = _effect_and_ns_for_condition(
            trials_cache[sid], cond_dict, metric=metric)

        if full_eff is None or n_on <= min_n:
            continue

        record = {'session_id': sid,
                  'full_effect': full_eff, 'n_on': n_on, 'n_off': n_off}
        record.update(_expand_with_hyperparameters(sid, cond_dict))
        records.append(record)

    df = pd.DataFrame(records)
    print(f"Built effect-size table: {len(df)} conditions "
          f"(n_on > {min_n}, metric='{metric}', no effect threshold)")
    return df


def plot_effect_size_by_parameter(df, metric=METRIC_PCT_HYP_VS_DELTA,
                                  min_n=DEFAULT_MIN_N, save_path=None, subset_by=None):
    """
    For every condition parameter, plot each condition's estim effect size against that
    parameter's value (one subplot per parameter), overlaying the per-value mean effect.
    Numeric parameters are sorted ascending on a float axis; categorical parameters are
    shown as ordered categories.

    If ``subset_by`` names a parameter (e.g. 'polarity'), each subplot overlays one
    mean line per value of that parameter plus a combined-total line.
    """
    if df.empty:
        print("No conditions to plot effect size for.")
        return None

    colors = _make_subset_colors(df, subset_by)
    params = _parameter_columns(df)
    n = len(params)
    ncols = min(3, n)
    nrows = (n + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(5.5 * ncols, 4 * nrows),
                             squeeze=False)

    for i, param in enumerate(params):
        ax = axes[i // ncols][i % ncols]
        use_subset = colors is not None and subset_by != param
        cols = [param, 'full_effect'] + ([subset_by] if use_subset else [])
        sub = df[cols].copy()
        sub = sub[sub[param].notna() & sub['full_effect'].notna()]
        if use_subset:
            sub = sub[sub[subset_by].notna()]
        if sub.empty:
            ax.text(0.5, 0.5, 'no data', ha='center', va='center', transform=ax.transAxes)
            ax.set_title(param, fontsize=10, fontweight='bold')
            continue

        ys = sub['full_effect'].astype(float).tolist()
        raw_vals = sub[param].tolist()
        subsets = [str(v) for v in sub[subset_by].tolist()] if use_subset else None

        if _is_numeric_param(raw_vals):
            xs = [_to_float(v) for v in raw_vals]
            _plot_numeric_param(ax, xs, ys, subsets=subsets, colors=colors)
        else:
            _plot_categorical_param(ax, [str(v) for v in raw_vals], ys,
                                    subsets=subsets, colors=colors)

        ax.axhline(0.0, color='gray', linestyle='--', linewidth=0.8, alpha=0.4)
        ax.set_title(param, fontsize=10, fontweight='bold')
        ax.set_xlabel(_param_xlabel(param), fontsize=9)
        ax.set_ylabel(_EFFECT_SIZE_YLABEL, fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.set_axisbelow(True)

    for j in range(n, nrows * ncols):
        axes[j // ncols][j % ncols].axis('off')

    subset_note = f", by {subset_by}" if colors is not None else ""
    fig.suptitle(f"Estim effect size vs condition parameters\n"
                 f"({len(df)} conditions [n_on > {min_n}], metric='{metric}'{subset_note})",
                 fontsize=13, fontweight='bold')
    fig.tight_layout(rect=[0, 0, 1, 0.94])

    if save_path:
        import os
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        fig.savefig(save_path, bbox_inches='tight', dpi=150)
        print(f"Saved to {save_path}")

    plt.show()
    return fig


def run(algorithm_label=DEFAULT_ALGORITHM_LABEL, session_id=None, save_dir=None,
        metric=METRIC_PCT_HYP_VS_DELTA, effect_threshold=DEFAULT_EFFECT_THRESHOLD,
        min_n=DEFAULT_MIN_N, subset_by=None):
    """
    Build the degradation table and plot every metric against every parameter, then
    build the degraded-vs-robust classification table and plot, per parameter, the
    fraction of conditions that degraded. Finally, build the effect-size table and
    plot each condition's estim effect size against every parameter.

    ``subset_by`` (e.g. 'polarity') splits every subplot's overlay into one line per
    value of that parameter plus a combined-total line. Pass any parameter column name
    ('polarity', 'shape', 'trial_type', 'a1', ...); None (default) plots a single
    combined line as before. When set, the parameter name is appended to each saved
    filename so subsetted plots don't overwrite the combined ones.
    """
    subset_tag = f"_by_{subset_by}" if subset_by else ""
    df = build_degradation_table(algorithm_label, session_id)
    if not df.empty:
        for metric_key in _METRICS:
            save_path = (f"{save_dir}/estim_degradation_{metric_key}_{algorithm_label}{subset_tag}.png"
                         if save_dir else None)
            plot_degradation_metric(df, metric_key, algorithm_label=algorithm_label,
                                    save_path=save_path, subset_by=subset_by)
    else:
        print("No cutoffs found for this algorithm_label — skipping degradation-metric plots.")

    class_df = build_condition_classification_table(
        algorithm_label, metric=metric, effect_threshold=effect_threshold,
        min_n=min_n, session_id=session_id)
    if not class_df.empty:
        save_path = (f"{save_dir}/estim_degradation_likelihood_{algorithm_label}{subset_tag}.png"
                     if save_dir else None)
        plot_degradation_likelihood(class_df, algorithm_label=algorithm_label,
                                    effect_threshold=effect_threshold, min_n=min_n,
                                    save_path=save_path, subset_by=subset_by)

    # Effect size vs parameters: same parameters and min_n gate, but no effect
    # threshold — plots the actual average estim effect at each parameter value.
    effect_df = build_effect_size_table(metric=metric, min_n=min_n, session_id=session_id)
    if not effect_df.empty:
        save_path = (f"{save_dir}/estim_effect_size_by_parameter{subset_tag}.png"
                     if save_dir else None)
        plot_effect_size_by_parameter(effect_df, metric=metric, min_n=min_n,
                                      save_path=save_path, subset_by=subset_by)
    return df, class_df, effect_df


def main():
    run(
        algorithm_label=DEFAULT_ALGORITHM_LABEL,
        session_id=None,  # str = one session, None = all sessions with a cutoff
        save_dir="/home/connorlab/Documents/plots/group_analysis/estimshape",
        effect_threshold=DEFAULT_EFFECT_THRESHOLD,
        min_n=DEFAULT_MIN_N,
        # None = one combined line per subplot (original behavior). Set to a parameter
        # name (e.g. 'polarity', 'shape', 'trial_type') to split each subplot into one
        # line per value of that parameter, plus a combined-total line.
        subset_by='polarity',
    )


if __name__ == '__main__':
    main()
