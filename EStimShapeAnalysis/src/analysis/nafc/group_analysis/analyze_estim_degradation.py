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
(a1, polarity, shape, num_channels, pulse_rate_hz, ...) and combined with its
behavioral conditions (trial_type, noise_chance, sample_length). For every
parameter we plot each metric against that parameter's value. Numeric
parameters (e.g. a1) are coerced to float and sorted ascending; categorical
parameters (e.g. polarity) are shown as ordered categories.
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

DEFAULT_ALGORITHM_LABEL = 'first_drop_w50_s5_t0_n2_m10'

# Columns of the degradation table that are bookkeeping / metrics, NOT parameters
# to plot against. Everything else in the table is treated as a condition parameter.
_NON_PARAM_COLUMNS = {
    'session_id', 'estim_spec_id', 'max_trial_start',
    'degradation_strength', 'degradation_onset',
    'effect_before', 'effect_after',
    'n_on_before', 'n_on_after', 'n_off_before', 'n_off_after',
}

# The metrics we plot, in display order: column name -> axis label.
_METRICS = {
    'degradation_strength': 'Degradation Strength\n(effect after / before cutoff)',
    'degradation_onset': 'Degradation Onset\n(# estim-on trials before cutoff)',
}

# Preferred left-to-right ordering of parameters in the plot grid. Any parameter
# not listed here is appended afterwards in alphabetical order.
_PARAM_ORDER = [
    'a1', 'polarity', 'shape', 'num_channels', 'pulse_rate_hz',
    'post_trigger_delay', 'enable_charge_recovery',
    'trial_type', 'noise_chance', 'sample_length',
]


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

        # Unfurl estim_spec_id into the physical stimulation parameters and keep the
        # behavioral keys (trial_type, noise_chance, sample_length) as-is.
        params = _expand_condition(sid, cond_dict)

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


def _plot_numeric_param(ax, xs, ys):
    """Scatter all (x, y) points and overlay a line connecting the per-value mean."""
    ax.scatter(xs, ys, alpha=0.4, s=25, color='steelblue', edgecolor='none')
    by_x = {}
    for x, y in zip(xs, ys):
        by_x.setdefault(x, []).append(y)
    uniq = sorted(by_x)
    means = [float(np.mean(by_x[x])) for x in uniq]
    ax.plot(uniq, means, '-o', color='firebrick', markersize=5, linewidth=1.5,
            label='mean')
    ax.legend(fontsize=7)


def _plot_categorical_param(ax, cats, ys):
    """Strip plot of categories (with jitter) and a diamond at each category mean."""
    labels = sorted(set(cats), key=str)
    pos = {c: i for i, c in enumerate(labels)}
    rng = np.random.default_rng(0)
    jitter = rng.uniform(-0.12, 0.12, size=len(cats))
    xpos = [pos[c] + j for c, j in zip(cats, jitter)]
    ax.scatter(xpos, ys, alpha=0.4, s=25, color='steelblue', edgecolor='none')

    by_cat = {}
    for c, y in zip(cats, ys):
        by_cat.setdefault(c, []).append(y)
    means = [float(np.mean(by_cat[c])) for c in labels]
    ax.plot(range(len(labels)), means, 'D', color='firebrick', markersize=7,
            label='mean')
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels([str(_clean_num(c)) for c in labels], rotation=30, ha='right',
                       fontsize=8)
    ax.legend(fontsize=7)


def plot_degradation_metric(df, metric_key, algorithm_label=DEFAULT_ALGORITHM_LABEL,
                            save_path=None):
    """
    For one metric, plot it against every condition parameter (one subplot each).
    Numeric parameters are sorted ascending on a float axis; categorical parameters
    are shown as ordered categories.
    """
    if df.empty:
        print(f"No data to plot for metric '{metric_key}'.")
        return None

    params = _parameter_columns(df)
    valid = df[df[metric_key].notna()]
    if valid.empty:
        print(f"No conditions with a defined '{metric_key}'.")
        return None

    n = len(params)
    ncols = min(3, n)
    nrows = (n + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(5.5 * ncols, 4 * nrows),
                             squeeze=False)

    for i, param in enumerate(params):
        ax = axes[i // ncols][i % ncols]
        sub = valid[[param, metric_key]].copy()
        sub = sub[sub[param].notna()]
        if sub.empty:
            ax.text(0.5, 0.5, 'no data', ha='center', va='center', transform=ax.transAxes)
            ax.set_title(param, fontsize=10, fontweight='bold')
            continue

        ys = sub[metric_key].astype(float).tolist()
        raw_vals = sub[param].tolist()

        if _is_numeric_param(raw_vals):
            xs = [_to_float(v) for v in raw_vals]
            _plot_numeric_param(ax, xs, ys)
        else:
            _plot_categorical_param(ax, [str(v) for v in raw_vals], ys)

        if metric_key == 'degradation_strength':
            ax.axhline(1.0, color='gray', linestyle=':', linewidth=1, alpha=0.6)
            ax.axhline(0.0, color='gray', linestyle='--', linewidth=0.8, alpha=0.4)
        ax.set_title(param, fontsize=10, fontweight='bold')
        ax.set_xlabel(param, fontsize=9)
        ax.set_ylabel(_METRICS[metric_key], fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.set_axisbelow(True)

    for j in range(n, nrows * ncols):
        axes[j // ncols][j % ncols].axis('off')

    fig.suptitle(f"{_METRICS[metric_key].splitlines()[0]} vs condition parameters\n"
                 f"({len(valid)} conditions, algorithm='{algorithm_label}')",
                 fontsize=13, fontweight='bold')
    fig.tight_layout(rect=[0, 0, 1, 0.94])

    if save_path:
        import os
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        fig.savefig(save_path, bbox_inches='tight', dpi=150)
        print(f"Saved to {save_path}")

    plt.show()
    return fig


def run(algorithm_label=DEFAULT_ALGORITHM_LABEL, session_id=None, save_dir=None):
    """Build the degradation table and plot every metric against every parameter."""
    df = build_degradation_table(algorithm_label, session_id)
    if df.empty:
        print("Nothing to analyze — no cutoffs found for this algorithm_label.")
        return df

    for metric_key in _METRICS:
        save_path = None
        if save_dir:
            save_path = f"{save_dir}/estim_degradation_{metric_key}_{algorithm_label}.png"
        plot_degradation_metric(df, metric_key, algorithm_label=algorithm_label,
                                save_path=save_path)
    return df


def main():
    run(
        algorithm_label=DEFAULT_ALGORITHM_LABEL,
        session_id=None,  # str = one session, None = all sessions with a cutoff
        save_dir="/home/connorlab/Documents/plots/group_analysis/estimshape",
    )


if __name__ == '__main__':
    main()
