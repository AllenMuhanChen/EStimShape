from clat.util.connection import Connection
import pandas as pd
import json
import re
import math
import matplotlib.pyplot as plt
import numpy as np

from src.analysis.nafc.estim_parameter_classifier import EStimParameterClassifier
from src.startup import context


# Metric identifiers stored in EStimEffects.metric (and EStimPermutationTests.metric).
# pct_hypothesized: mean(is_hypothesized_choice) over all trials in the group.
# pct_hyp_vs_delta: mean(is_hypothesized_choice) restricted to trials where the
#   monkey committed to either the hypothesized or the delta alternative — drops
#   choice in {'rand', 'removed'}. Effectively a 2AFC collapse of the task.
METRIC_PCT_HYPOTHESIZED = 'pct_hypothesized'
METRIC_PCT_HYP_VS_DELTA = 'pct_hyp_vs_delta'
ALL_METRICS = (METRIC_PCT_HYPOTHESIZED, METRIC_PCT_HYP_VS_DELTA)
_EXCLUDED_CHOICES_FOR_HYP_VS_DELTA = {'rand', 'removed'}


class _NumpyEncoder(json.JSONEncoder):
    """Converts numpy scalar types to Python natives so json.dumps works on pandas groupby keys."""
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.bool_):
            return bool(obj)
        return super().default(obj)


def _groupkey_to_dict(condition_keys, group_values):
    """Map a pandas groupby key back to {column: value}.

    Robust to pandas >= 2.2 returning a length-1 tuple when grouping by a
    single-column list (older pandas returned a bare scalar). Without this,
    grouping by a single condition (e.g. ['estim_spec_id']) would store the value
    wrapped in a list — e.g. {'estim_spec_id': [10.0]} instead of 10.0.
    """
    if not isinstance(group_values, tuple):
        group_values = (group_values,)
    return dict(zip(condition_keys, group_values))


def _normalize_cond_key(cond_dict):
    """
    Canonical JSON key for a condition dict, robust to NaN vs None and numpy vs Python types.
    NaN is treated as None (null in JSON) so stored keys and freshly-generated keys compare equal.
    """
    def _v(v):
        # pandas single-column groupby used to store values list/tuple-wrapped
        # (e.g. [10.0] for estim_spec_id). Unwrap so a stored [10.0] compares
        # equal to a freshly-split scalar 10.0 (and old data still resolves).
        if isinstance(v, (list, tuple)) and len(v) == 1:
            v = v[0]
        if isinstance(v, float) and math.isnan(v):
            return None
        if isinstance(v, np.integer):
            return int(v)
        if isinstance(v, np.floating):
            f = float(v)
            return None if math.isnan(f) else f
        if isinstance(v, np.bool_):
            return bool(v)
        return v
    return json.dumps({k: _v(v) for k, v in cond_dict.items()}, sort_keys=True)


def _parse_conditions_json(conditions_json):
    """Parse a conditions JSON string that may contain bare NaN (not valid JSON)."""
    cleaned = re.sub(r'\bNaN\b', 'null', conditions_json)
    return json.loads(cleaned)


def _cond_val_equal(a, b):
    """Fuzzy equality for condition values: NaN==None, int==float if close, bool(False)==int(0)."""
    def _n(v):
        if v is None:
            return None
        if isinstance(v, float) and math.isnan(v):
            return None
        return v
    a, b = _n(a), _n(b)
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    if isinstance(a, (int, float, bool)) and isinstance(b, (int, float, bool)):
        return math.isclose(float(a), float(b), rel_tol=1e-6, abs_tol=1e-9)
    return a == b


def _cond_dicts_equal(a, b):
    """
    True if two condition dicts describe the same condition: identical key sets and
    fuzzily-equal values (NaN==None, int==float when close, bool(False)==int(0)).

    Use this instead of comparing _normalize_cond_key(a) == _normalize_cond_key(b): exact
    JSON-string equality is brittle to a value being an int in one dict and a float in the
    other (e.g. a newly added `coherence` stored as 0 vs grouped as 0.0), which silently
    fails to match. This comparison is robust to that, so adding a condition parameter does
    not break condition lookup.
    """
    if set(a.keys()) != set(b.keys()):
        return False
    return all(_cond_val_equal(a.get(k), b.get(k)) for k in a)


def _find_cutoff_for_condition(all_conds, trial_start_cutoffs):
    """
    Look up max_trial_start for all_conds in trial_start_cutoffs using fuzzy comparison.
    trial_start_cutoffs maps raw conditions_json strings → max_trial_start.
    Returns the max_trial_start or None if no match found.
    """
    for conditions_json, max_ts in trial_start_cutoffs.items():
        try:
            stored = _parse_conditions_json(conditions_json)
        except Exception:
            continue
        if _cond_dicts_equal(all_conds, stored):
            return max_ts
    return None


def _get_all_session_ids():
    """Return all session_ids present in EStimShapeTrials."""
    repo_conn = Connection("allen_data_repository")
    repo_conn.execute("SELECT DISTINCT session_id FROM EStimShapeTrials ORDER BY session_id")
    return [row[0] for row in repo_conn.fetch_all()]


_DEFAULT_BEHAVIORAL_CONDITIONS = ['trial_type', 'noise_chance', 'coherence', 'sample_length',
                                  'num_choices', 'num_procedural_distractors', 'num_rand_distractors']
# Key estim conditions by estim_spec_id so each spec is its own condition, matching
# analyze_estim_by_estim_id. Grouping on a parameter subset (e.g. amplitude/shape/
# polarity without channel) pools physically distinct specs — different electrode
# sites, frequencies, etc. — into one row, which dilutes the effect size and inflates
# n by drawing the gen-matched baseline from every pooled spec's generations.
_DEFAULT_ESTIM_CONDITIONS = ['estim_spec_id']


def run_pipeline(session_ids=None, algorithm_label='None', force_recompute=True,
                 behavioral_conditions=None, estim_conditions=None,
                 window_size=100, step_size=10,
                 show_sliding_window=True):
    """
    Compute and persist EStimEffects for one or more sessions.

    Args:
        session_ids   : list of session_ids, or None to use every session in
                        EStimShapeTrials.
        algorithm_label: cutoff label (must match an entry in EStimSessionCutoffs,
                        or 'None'/'none' for raw data).
        force_recompute: if False, sessions already present in EStimEffects for
                        this algorithm_label are skipped.
        show_sliding_window: when running across many sessions you usually want
                        this off — the sliding-window plot blocks on plt.show().
    """
    if behavioral_conditions is None:
        behavioral_conditions = _DEFAULT_BEHAVIORAL_CONDITIONS
    if estim_conditions is None:
        estim_conditions = _DEFAULT_ESTIM_CONDITIONS

    create_estim_effects_table()

    ids_to_run = _get_all_session_ids() if session_ids is None else list(session_ids)
    print(f"Sessions to process: {ids_to_run}")

    for session_id in ids_to_run:
        if not force_recompute and _session_has_effects_computed(session_id, algorithm_label):
            print(f"Skipping {session_id} (already in EStimEffects for '{algorithm_label}')")
            continue

        data = read_trial_data_from_repository(session_id)
        print(f"\n=== {session_id}: {len(data)} trials ===")

        # Only condition on columns actually present (e.g. 'coherence' is absent on repos compiled
        # before it was added), so a missing column never breaks the groupby.
        session_behavioral_conditions = [c for c in behavioral_conditions if c in data.columns]

        trial_start_cutoffs = _fetch_trial_start_cutoffs(session_id, algorithm_label)

        if show_sliding_window:
            sliding_window_analysis(
                data,
                session_behavioral_conditions,
                estim_conditions,
                window_size=window_size,
                step_size=step_size,
                session_id=session_id,
                cutoff_trial_starts=trial_start_cutoffs,
            )

        condition_groups_data = split_data_by_conditions(
            data, session_behavioral_conditions, estim_conditions,
            trial_start_cutoffs=trial_start_cutoffs,
        )
        results = calculate_estim_effects(condition_groups_data)
        save_estim_effects_to_repository(session_id, results, algorithm_label)
        print(f"Saved {len(results)} effects for {session_id} (algorithm='{algorithm_label}')")


def main():
    # Single-session interactive default; orchestrator scripts should call
    # run_pipeline() directly. session_ids=None runs every session.
    run_pipeline(
        session_ids=["260702_0"],
        algorithm_label='None',
        force_recompute=True,
        show_sliding_window=True,
    )


def _fetch_trial_start_cutoffs(session_id, algorithm_label):
    """
    Return {normalized_cond_key: max_trial_start} for all conditions in this session
    that have a cutoff stored under algorithm_label.
    Keys are normalized via _normalize_cond_key so NaN vs None and int vs float don't break lookup.
    Returns an empty dict if algorithm_label is 'none' or no cutoffs exist.
    """
    if algorithm_label == 'none':
        return {}
    conn = Connection("allen_data_repository")
    conn.execute("""
        SELECT conditions, max_trial_start FROM EStimSessionCutoffs
        WHERE session_id = %s AND algorithm_label = %s
    """, (session_id, algorithm_label))
    rows = conn.fetch_all()
    print(f"  [cutoffs] found {len(rows)} stored cutoffs for {session_id} / {algorithm_label}")
    return {row[0]: row[1] for row in rows}


def sliding_window_analysis(data, behavioral_conditions, estim_conditions,
                            window_size=100, step_size=5,
                            show_gen_boundaries=True, session_id=None,
                            cutoff_trial_starts=None):
    """
    Sliding window estim-effect analysis grouped by behavioral + estim conditions.

    For each window: effect_size = estim_on % hyp − estim_off % hyp.
    Plots effect-size lines per condition (top) and no-estim baseline % hyp (bottom).
    Dotted vertical lines mark generation boundaries (toggleable via show_gen_boundaries).
    """
    import os
    data_sorted = data.sort_values('trial_start').reset_index(drop=True)

    print(f"\nRunning sliding window analysis (by condition):")
    print(f"  Window size: {window_size} trials, Step: {step_size} trials, Total: {len(data_sorted)}")

    condition_groups = {}
    temp_groups = split_data_by_conditions(data, behavioral_conditions, estim_conditions)
    for group in temp_groups:
        condition_key = json.dumps(
            {**group['behavioral_conditions'], **group['estim_conditions']},
            sort_keys=True, cls=_NumpyEncoder)
        condition_groups[condition_key] = {
            'label': format_condition_label(group['behavioral_conditions'], group['estim_conditions']),
            'behavioral': group['behavioral_conditions'],
            'estim': group['estim_conditions'],
            'windows': []
        }

    print(f"  Tracking {len(condition_groups)} condition combinations")
    window_positions = range(0, len(data_sorted) - window_size + 1, step_size)

    for window_start in window_positions:
        window_data = data_sorted.iloc[window_start:window_start + window_size]
        window_groups = split_data_by_conditions(window_data, behavioral_conditions, estim_conditions)
        # Sliding-window plot only uses the raw metric; computing both would double rows.
        for result in calculate_estim_effects(window_groups, metrics=(METRIC_PCT_HYPOTHESIZED,)):
            condition_key = json.dumps(result['conditions'], sort_keys=True, cls=_NumpyEncoder)
            if condition_key in condition_groups:
                condition_groups[condition_key]['windows'].append({
                    'trial_number': window_start + window_size // 2,
                    'effect_size': result['effect_size'],
                    'estim_on_n': result['estim_on_n_trials'],
                    'estim_off_n': result['estim_off_n_trials']
                })

    # Convert trial_start cutoffs → trial-index positions for plotting
    cutoff_trial_numbers = {}
    if cutoff_trial_starts:
        for conditions_json, max_trial_start in cutoff_trial_starts.items():
            mask = data_sorted['trial_start'] <= max_trial_start
            if mask.any():
                cutoff_trial_numbers[conditions_json] = int(mask.values.nonzero()[0][-1])

    session_label = session_id or (data['session_id'].iloc[0] if 'session_id' in data.columns else 'unknown')
    save_dir = f"/home/connorlab/Documents/plots/{session_label}/estimshape/"
    os.makedirs(save_dir, exist_ok=True)
    output_path = os.path.join(save_dir, f'sliding_window_{session_label}_w{window_size}_s{step_size}.png')

    plot_sliding_window_results(
        condition_groups,
        baseline_windows=compute_baseline_windows(data_sorted, window_positions, window_size),
        gen_boundary_trial_numbers=compute_gen_boundaries(data_sorted),
        show_gen_boundaries=show_gen_boundaries,
        output_path=output_path,
        window_size=window_size,
        step_size=step_size,
        session_id=session_label,
        cutoff_trial_numbers=cutoff_trial_numbers,
    )


def compute_gen_boundaries(data_sorted):
    """Return list of (trial_index, new_gen_id) at each gen_id transition."""
    boundaries = []
    prev_gen = None
    for i, gen in enumerate(data_sorted['gen_id']):
        if pd.notna(gen):
            if prev_gen is not None and gen != prev_gen:
                boundaries.append((i, int(gen)))
            prev_gen = gen
    return boundaries


def compute_baseline_windows(data_sorted, window_positions, window_size):
    """
    % hypothesized choice for estim-off trials per window, split by trial_type + Combined.
    Returns dict: trial_type -> list of {trial_number, pct}.
    """
    trial_types = sorted(
        data_sorted.loc[data_sorted['is_estim_on'] == 0, 'trial_type'].dropna().unique()
    )
    result = {tt: [] for tt in trial_types}
    result['Combined'] = []

    for window_start in window_positions:
        trial_num = window_start + window_size // 2
        window_off = data_sorted.iloc[window_start:window_start + window_size]
        window_off = window_off[window_off['is_estim_on'] == 0]

        for tt in trial_types:
            choices = window_off.loc[window_off['trial_type'] == tt, 'is_correct_choice'].dropna()
            result[tt].append({'trial_number': trial_num,
                                'pct': float(choices.mean()) * 100 if len(choices) > 0 else None})

        all_choices = window_off['is_correct_choice'].dropna()
        result['Combined'].append({'trial_number': trial_num,
                                   'pct': float(all_choices.mean()) * 100 if len(all_choices) > 0 else None})

    return result


_KEY_ABBREVS = {
    'estim_spec_id': 'spec',
    'trial_type': 'type',
    'noise_chance': 'noise',
    'sample_length': 'smpl',
    'num_choices': 'nCh',
    'num_procedural_distractors': 'nProc',
    'num_rand_distractors': 'nRand',
    'num_channels': 'ch',
    'polarity': 'pol',
    'shape': 'shp',
    'a1': 'amp',
    'post_stim_refractory_period': 'refrac',
    'enable_charge_recovery': 'CR',
}

_VALUE_FORMATTERS = {
    'trial_type': lambda v: {'Delta Shape': 'Del', 'Hypothesized Shape': 'Hyp',
                             'Removed Trial': 'Rmv', 'Combined': 'Cmb'}.get(str(v), str(v)[:4]),
    'polarity': lambda v: 'Pos' if str(v) == 'PositiveFirst' else 'Neg',
    'noise_chance': lambda v: f"{int(float(v) * 100)}%",
    'a1': lambda v: f"{float(v):.1f}µA",
    'post_stim_refractory_period': lambda v: f"{int(float(v))}µs",
    'enable_charge_recovery': lambda v: 'CR+' if v else 'CR-',
    'sample_length': lambda v: f"{v}ms",
    'num_choices': lambda v: _fmt_int(v),
    'num_procedural_distractors': lambda v: _fmt_int(v),
    'num_rand_distractors': lambda v: _fmt_int(v),
}


def _fmt_int(v):
    """Format an integer-valued condition value, tolerating NaN/None (legacy trials that
    didn't record the parameter) by showing 'NA' instead of crashing."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    if math.isnan(f):
        return 'NA'
    return f"{int(f)}"


def format_condition_label(behavioral_dict, estim_dict, varying_keys=None):
    """Build a label from condition dicts, showing only keys in varying_keys (or all if None)."""
    all_conditions = {**behavioral_dict, **estim_dict}
    keys_to_show = varying_keys if varying_keys is not None else list(all_conditions.keys())
    parts = []
    for key in keys_to_show:
        val = all_conditions.get(key)
        if val is None:
            continue
        fmt = _VALUE_FORMATTERS.get(key, str)
        abbrev = _KEY_ABBREVS.get(key, key)
        parts.append(f"{abbrev}={fmt(val)}")
    return ' | '.join(parts) if parts else 'baseline'


def plot_sliding_window_results(condition_groups,
                                baseline_windows=None,
                                gen_boundary_trial_numbers=None,
                                show_gen_boundaries=True,
                                output_path=None,
                                window_size=None,
                                step_size=None,
                                session_id=None,
                                cutoff_trial_numbers=None):
    """
    Plot sliding window effect sizes, with optional extras:
      - baseline_windows: adds a second subplot (% hyp for no-estim trials by trial_type)
      - gen_boundary_trial_numbers + show_gen_boundaries: dotted vertical lines at gen transitions
    Each condition gets a unique color; legend shows only varying dimensions.
    """
    all_values_by_key = {}
    for cond_data in condition_groups.values():
        for k, v in {**cond_data['behavioral'], **cond_data['estim']}.items():
            all_values_by_key.setdefault(k, set()).add(str(v))
    varying_keys = [k for k, vs in all_values_by_key.items() if len(vs) > 1]

    active = [
        cond_data for cond_data in condition_groups.values()
        if cond_data['windows'] and not all(w['effect_size'] is None for w in cond_data['windows'])
    ]
    n = len(active)
    if n <= 10:
        palette = [plt.cm.tab10(i / 10) for i in range(n)]
    elif n <= 20:
        palette = [plt.cm.tab20(i / 20) for i in range(n)]
    else:
        palette = [plt.cm.hsv(i / n) for i in range(n)]

    has_baseline = baseline_windows is not None
    if has_baseline:
        fig, (ax_effect, ax_baseline) = plt.subplots(
            2, 1, figsize=(16, 10), sharex=True,
            gridspec_kw={'height_ratios': [2, 1]})
    else:
        fig, ax_effect = plt.subplots(figsize=(16, 8))
        ax_baseline = None

    cutoff_drawn = False
    for cond_data, color in zip(active, palette):
        trial_numbers = [w['trial_number'] for w in cond_data['windows']]
        effect_sizes = [w['effect_size'] for w in cond_data['windows']]
        label = format_condition_label(cond_data['behavioral'], cond_data['estim'], varying_keys)
        ax_effect.plot(trial_numbers, effect_sizes,
                       color=color, marker='o', markersize=3, linewidth=1.5, label=label)

        # Draw cutoff line for this condition if one exists
        if cutoff_trial_numbers:
            cond_key = json.dumps(
                {**cond_data['behavioral'], **cond_data['estim']},
                sort_keys=True, cls=_NumpyEncoder)
            if cond_key in cutoff_trial_numbers:
                cutoff_x = cutoff_trial_numbers[cond_key]
                ax_effect.axvline(x=cutoff_x, color=color, linestyle='--',
                                  linewidth=2, alpha=0.8,
                                  label='cutoff' if not cutoff_drawn else '_nolegend_')
                cutoff_drawn = True

    ax_effect.axhline(y=0, color='black', linestyle='--', linewidth=1, alpha=0.5)
    ax_effect.set_ylabel('Effect Size (EStim ON − EStim OFF %)', fontsize=12)
    title = f'{session_id} − Sliding Window Analysis' if session_id else 'Sliding Window Analysis'
    ax_effect.set_title(title, fontsize=14)
    ax_effect.legend(bbox_to_anchor=(1.02, 1), loc='upper left', fontsize=8, framealpha=0.9)
    ax_effect.grid(True, alpha=0.3)

    if window_size is not None and step_size is not None:
        textstr = f'Window: {window_size} trials  |  Step: {step_size} trials'
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
        ax_effect.text(0.02, 0.98, textstr, transform=ax_effect.transAxes, fontsize=9,
                       verticalalignment='top', bbox=props)

    if has_baseline:
        _BASELINE_COLORS = {
            'Delta Shape': '#d62728', 'Delta': '#d62728',
            'Hypothesized Shape': '#1f77b4', 'Variant': '#1f77b4',
            'Removed Trial': '#8c564b', 'Removed': '#8c564b',
            'Combined': 'black',
        }
        for tt, windows in baseline_windows.items():
            trial_nums = [w['trial_number'] for w in windows]
            pcts = [w['pct'] for w in windows]
            if all(p is None for p in pcts):
                continue
            color = _BASELINE_COLORS.get(tt, 'gray')
            ls = '--' if tt == 'Combined' else '-'
            ax_baseline.plot(trial_nums, pcts, color=color, linestyle=ls,
                             linewidth=1.5, label=tt)
        ax_baseline.axhline(y=50, color='black', linestyle=':', linewidth=0.8, alpha=0.5)
        ax_baseline.set_ylabel('% Correct\n(No EStim)', fontsize=10)
        ax_baseline.set_xlabel('Trial Number (Window Center)', fontsize=12)
        ax_baseline.legend(fontsize=8, framealpha=0.9)
        ax_baseline.grid(True, alpha=0.3)
    else:
        ax_effect.set_xlabel('Trial Number (Window Center)', fontsize=12)

    if show_gen_boundaries and gen_boundary_trial_numbers:
        axes_to_mark = [ax_effect] + ([ax_baseline] if ax_baseline is not None else [])
        for trial_num, gen_id in gen_boundary_trial_numbers:
            for ax in axes_to_mark:
                ax.axvline(x=trial_num, color='gray', linestyle=':', linewidth=1, alpha=0.6)
            ax_effect.text(trial_num, 1.0, f' G{gen_id}',
                           transform=ax_effect.get_xaxis_transform(),
                           rotation=90, va='top', ha='left',
                           fontsize=7, color='gray', alpha=0.85)

    plt.tight_layout()
    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"\nSaved sliding window plot to {output_path}")
    plt.show()

def combine_trial_types_at_max_noise(data):
    """
    Combine Delta Shape and Hypothesized Shape trial types at 100% noise.
    At maximum noise, these trial types are functionally equivalent.

    Args:
        data: DataFrame with trial data

    Returns:
        DataFrame with combined trial types
    """
    data = data.copy()

    # Find trials at 100% noise with Delta Shape or Hypothesized Shape trial types
    max_noise_mask = data['noise_chance'] == 1.0
    delta_or_hyp_mask = data['trial_type'].isin(['Delta Shape', 'Hypothesized Shape'])

    # Combine the masks
    combine_mask = max_noise_mask & delta_or_hyp_mask

    # Rename to 'Combined'
    data.loc[combine_mask, 'trial_type'] = 'Combined'

    num_combined = combine_mask.sum()
    print(f"Combined {num_combined} trials at 100% noise into 'Combined' trial type")

    return data


def _filter_for_metric(df, metric):
    """Apply per-metric row filtering before computing % hypothesized."""
    if metric == METRIC_PCT_HYP_VS_DELTA and 'choice' in df.columns:
        df = df[~df['choice'].isin(_EXCLUDED_CHOICES_FOR_HYP_VS_DELTA)]
        # filter out where trial type is "Removed Trial" and choice is "match"
        df = df[~((df['trial_type'] == 'Removed Trial') & (df['choice'] == 'match'))]
    return df


def calculate_estim_effects(condition_groups, metrics=ALL_METRICS):
    """
    Calculate % hypothesized for estim vs no-estim, one row per (condition, metric).

    Args:
        condition_groups: List of dicts with estim_on_data and estim_off_data
        metrics: Iterable of metric identifiers (see METRIC_* constants).
                 Default computes both pct_hypothesized and pct_hyp_vs_delta.

    Returns:
        List of dicts with calculated effects (length = len(condition_groups) * len(metrics)).
    """
    results = []

    for group in condition_groups:
        estim_on_full = group['estim_on_data']
        estim_off_full = group['estim_off_data']
        all_conditions = {**group['behavioral_conditions'], **group['estim_conditions']}

        for metric in metrics:
            estim_on = _filter_for_metric(estim_on_full, metric)
            estim_off = _filter_for_metric(estim_off_full, metric)

            estim_on_pct = estim_on['is_hypothesized_choice'].mean() * 100 if len(estim_on) > 0 else None
            estim_off_pct = estim_off['is_hypothesized_choice'].mean() * 100 if len(estim_off) > 0 else None

            results.append({
                'conditions': all_conditions,
                'metric': metric,
                'estim_on_pct_hypothesized': estim_on_pct,
                'estim_off_pct_hypothesized': estim_off_pct,
                'estim_on_n_trials': len(estim_on),
                'estim_off_n_trials': len(estim_off),
                'effect_size': estim_on_pct - estim_off_pct if estim_on_pct is not None and estim_off_pct is not None else None
            })

    return results


def create_estim_effects_table():
    """Create EStimEffects table if it doesn't exist, and run any pending migrations."""
    conn = Connection("allen_data_repository")

    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS EStimEffects
        (
            session_id                 VARCHAR(10)  NOT NULL,
            conditions                 LONGTEXT     NOT NULL,
            algorithm_label            VARCHAR(100) NOT NULL DEFAULT 'none',
            metric                     VARCHAR(50)  NOT NULL DEFAULT '{METRIC_PCT_HYPOTHESIZED}',
            estim_on_pct_hypothesized  FLOAT,
            estim_off_pct_hypothesized FLOAT,
            estim_on_n_trials          INT,
            estim_off_n_trials         INT,
            effect_size                FLOAT,

            PRIMARY KEY (session_id, conditions(500), algorithm_label(100), metric(50)),
            FOREIGN KEY (session_id) REFERENCES Sessions (session_id) ON DELETE CASCADE
        ) ENGINE = InnoDB DEFAULT CHARSET = latin1
    """)

    _migrate_estim_effects_table(conn)
    print("EStimEffects table ready")


def _migrate_estim_effects_table(conn):
    """Add algorithm_label column and ensure PK includes it. Checks each step independently
    so a partial migration (column added, PK not updated) is correctly retried."""
    # Step 1: add column if missing
    conn.execute("""
        SELECT COUNT(*) FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME   = 'EStimEffects'
          AND COLUMN_NAME  = 'algorithm_label'
    """)
    if conn.fetch_all()[0][0] == 0:
        print("Migrating EStimEffects: adding algorithm_label column...")
        conn.execute("ALTER TABLE EStimEffects ADD COLUMN algorithm_label VARCHAR(100) NOT NULL DEFAULT 'none'")
        print("Column added")

    # Step 2: ensure algorithm_label is actually part of the PRIMARY KEY
    conn.execute("""
        SELECT COUNT(*) FROM information_schema.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA    = DATABASE()
          AND TABLE_NAME      = 'EStimEffects'
          AND CONSTRAINT_NAME = 'PRIMARY'
          AND COLUMN_NAME     = 'algorithm_label'
    """)
    if conn.fetch_all()[0][0] == 0:
        print("Migrating EStimEffects: updating PRIMARY KEY to include algorithm_label...")
        # Single ALTER TABLE applies DROP + ADD atomically, so FK checks see the
        # completed PK (session_id is still present) rather than an intermediate state.
        conn.execute("""
            ALTER TABLE EStimEffects
              DROP PRIMARY KEY,
              ADD PRIMARY KEY (session_id, conditions(500), algorithm_label(100))
        """)
        print("Migration complete")

    # Step 3: add metric column if missing
    conn.execute("""
        SELECT COUNT(*) FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME   = 'EStimEffects'
          AND COLUMN_NAME  = 'metric'
    """)
    if conn.fetch_all()[0][0] == 0:
        print("Migrating EStimEffects: adding metric column...")
        conn.execute(
            f"ALTER TABLE EStimEffects ADD COLUMN metric VARCHAR(50) NOT NULL DEFAULT '{METRIC_PCT_HYPOTHESIZED}'"
        )
        print("Column added (existing rows default to pct_hypothesized)")

    # Step 4: ensure metric is in PRIMARY KEY
    conn.execute("""
        SELECT COUNT(*) FROM information_schema.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA    = DATABASE()
          AND TABLE_NAME      = 'EStimEffects'
          AND CONSTRAINT_NAME = 'PRIMARY'
          AND COLUMN_NAME     = 'metric'
    """)
    if conn.fetch_all()[0][0] == 0:
        print("Migrating EStimEffects: updating PRIMARY KEY to include metric...")
        conn.execute("""
            ALTER TABLE EStimEffects
              DROP PRIMARY KEY,
              ADD PRIMARY KEY (session_id, conditions(500), algorithm_label(100), metric(50))
        """)
        print("Migration complete")


def save_estim_effects_to_repository(session_id, results, algorithm_label='none'):
    conn = Connection("allen_data_repository")

    # Replace this session's effects rather than accumulate. The conditions string
    # is the primary key, so when the condition scheme changes (e.g. a 6-parameter
    # grouping -> estim_spec_id, or [2.0] -> 2.0) ON DUPLICATE KEY UPDATE would
    # leave the old-format rows behind as orphans, double-counting the same physical
    # condition in the downstream population tests. Clear the metrics being written
    # first so only current-format rows survive.
    metrics_present = {result.get('metric', METRIC_PCT_HYPOTHESIZED) for result in results}
    for metric in metrics_present:
        conn.execute(
            "DELETE FROM EStimEffects WHERE session_id = %s AND algorithm_label = %s AND metric = %s",
            (session_id, algorithm_label, metric))

    for result in results:
        conditions_str = _normalize_cond_key(result['conditions'])
        metric        = result.get('metric', METRIC_PCT_HYPOTHESIZED)
        estim_on_pct  = float(result['estim_on_pct_hypothesized'])  if result['estim_on_pct_hypothesized']  is not None else None
        estim_off_pct = float(result['estim_off_pct_hypothesized']) if result['estim_off_pct_hypothesized'] is not None else None
        estim_on_n    = int(result['estim_on_n_trials'])             if result['estim_on_n_trials']          is not None else None
        estim_off_n   = int(result['estim_off_n_trials'])            if result['estim_off_n_trials']         is not None else None
        effect        = float(result['effect_size'])                  if result['effect_size']                is not None else None

        conn.execute("""
            INSERT INTO EStimEffects
                (session_id, conditions, algorithm_label, metric,
                 estim_on_pct_hypothesized, estim_off_pct_hypothesized,
                 estim_on_n_trials, estim_off_n_trials, effect_size)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                estim_on_pct_hypothesized  = VALUES(estim_on_pct_hypothesized),
                estim_off_pct_hypothesized = VALUES(estim_off_pct_hypothesized),
                estim_on_n_trials          = VALUES(estim_on_n_trials),
                estim_off_n_trials         = VALUES(estim_off_n_trials),
                effect_size                = VALUES(effect_size)
        """, (session_id, conditions_str, algorithm_label, metric,
              estim_on_pct, estim_off_pct, estim_on_n, estim_off_n, effect))


def split_data_by_conditions(data, behavioral_conditions, estim_conditions,
                             trial_start_cutoffs=None):
    """
    Split data for estim vs no-estim comparisons.

    Strategy:
    1. Group by behavioral conditions (applies to all trials)
    2. Within each behavioral group, the estim_off trials are the baseline
    3. Find all unique estim parameter combinations in estim_on trials
    4. Create comparison pairs: each estim parameter combo vs the shared baseline

    Args:
        data: DataFrame with trial data
        behavioral_conditions: Conditions that apply to both estim and no-estim trials
        estim_conditions: Conditions that only apply to estim trials

    Returns:
        List of dicts, each containing:
            - 'behavioral_conditions': dict of behavioral condition values
            - 'estim_conditions': dict of estim parameter values
            - 'estim_on_data': DataFrame of estim trials with these parameters
            - 'estim_off_data': DataFrame of no-estim baseline trials
    """
    comparisons = []

    # First group by behavioral conditions
    behavioral_groups = data.groupby(behavioral_conditions, dropna=False)

    for behavioral_values, behavioral_group in behavioral_groups:
        # Create behavioral condition dict
        behavioral_dict = _groupkey_to_dict(behavioral_conditions, behavioral_values)

        # Split into estim on/off within this behavioral group
        estim_off_data = behavioral_group.loc[behavioral_group['is_estim_on'] == 0].copy()
        estim_on_data = behavioral_group.loc[behavioral_group['is_estim_on'] == 1].copy()

        # Skip if we don't have estim_off baseline
        if len(estim_off_data) == 0:
            continue

        # If no estim_on trials, we can't do comparisons
        if len(estim_on_data) == 0:
            continue

        # Now find all unique estim parameter combinations within estim_on trials
        estim_groups = estim_on_data.groupby(estim_conditions, dropna=False)

        for estim_values, estim_group in estim_groups:
            # Create estim condition dict
            estim_dict = _groupkey_to_dict(estim_conditions, estim_values)

            estim_on_trimmed  = estim_group.copy()
            estim_off_trimmed = estim_off_data.copy()

            # Restrict the estim_off baseline to the gen_ids this estim condition
            # actually ran in. An estim condition is often only presented during a
            # subset of generations; comparing it against estim_off trials drawn from
            # every generation mixes in unrelated baselines from other gen_ids.
            if 'gen_id' in estim_on_trimmed.columns:
                cond_gen_ids = estim_on_trimmed['gen_id'].dropna().unique()
                estim_off_trimmed = estim_off_trimmed[estim_off_trimmed['gen_id'].isin(cond_gen_ids)]

            # Apply adaptation cutoff for this condition if one exists
            if trial_start_cutoffs and 'trial_start' in data.columns:
                all_conds = {**behavioral_dict, **estim_dict}
                max_ts = _find_cutoff_for_condition(all_conds, trial_start_cutoffs)
                if max_ts is not None:
                    estim_on_trimmed  = estim_on_trimmed[estim_on_trimmed['trial_start']  <= max_ts]
                    estim_off_trimmed = estim_off_trimmed[estim_off_trimmed['trial_start'] <= max_ts]

            comparisons.append({
                'behavioral_conditions': behavioral_dict,
                'estim_conditions': estim_dict,
                'estim_on_data': estim_on_trimmed,
                'estim_off_data': estim_off_trimmed,
            })

    return comparisons


def _session_has_effects_computed(session_id, algorithm_label='none'):
    """Return True if EStimEffects already has rows for this session+algorithm_label."""
    conn = Connection("allen_data_repository")
    conn.execute("SELECT COUNT(*) FROM EStimEffects WHERE session_id = %s AND algorithm_label = %s",
                 (session_id, algorithm_label))
    return conn.fetch_all()[0][0] > 0


def read_trial_data_from_repository(session_id):
    """
    Read trial data from EStimShapeTrials table and join with EStim parameters

    Args:
        session_id: Session identifier

    Returns:
        pandas.DataFrame with trial data and estim parameters
    """
    repo_conn = Connection("allen_data_repository")

    # Join trials with estim parameters; active_channel_sql_subquery counts only
    # non-zero-amplitude channels so num_channels excludes ground-pulse channels.
    query = f"""
            SELECT t.*,
                   ep.channel,
                   ep.num_channels,
                   ep.shape,
                   ep.polarity,
                   ep.d1,
                   ep.d2,
                   ep.dp,
                   ep.a1,
                   ep.a2,
                   ep.pulse_repetition,
                   ep.num_repetitions,
                   ep.pulse_train_period,
                   ep.post_stim_refractory_period,
                   ep.trigger_edge_or_level,
                   ep.post_trigger_delay,
                   ep.enable_amp_settle,
                   ep.pre_stim_amp_settle,
                   ep.post_stim_amp_settle,
                   ep.maintain_amp_settle_during_pulse_train,
                   ep.enable_charge_recovery,
                   ep.post_stim_charge_recovery_on,
                   ep.post_stim_charge_recovery_off
            FROM EStimShapeTrials t
            LEFT JOIN ({EStimParameterClassifier.active_channel_sql_subquery()}) ep
              ON t.session_id = ep.session_id AND t.estim_spec_id = ep.estim_spec_id
            WHERE t.session_id = %s
              -- Split-texture trials (EStimShapeSplitTextureNAFCStim) have their own
              -- dedicated analysis; exclude them here so they aren't pooled into the
              -- by-condition delta/variant effects (they share trial_type/noise/etc.).
              AND COALESCE(t.is_texture_split, 0) = 0
            ORDER BY t.task_id
            """

    repo_conn.execute(query, (session_id,))

    # Get column names BEFORE fetch_all (which closes the cursor)
    column_names = [desc[0] for desc in repo_conn.my_cursor.description]

    # Now fetch the results
    result = repo_conn.fetch_all()

    # Convert to DataFrame
    df = pd.DataFrame(result, columns=column_names)

    return df


if __name__ == '__main__':
    main()