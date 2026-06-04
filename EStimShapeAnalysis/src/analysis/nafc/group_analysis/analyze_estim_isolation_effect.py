"""
Relate per-estim-spec isolation scores to the raw estim effect on behavior.

Isolation scores (``estim_min_isolation_um`` / ``estim_mean_isolation_um``) are
computed per (session_id, estim_spec_id) in ``run_cluster_app_pc_figure`` and
stored in ``EStimParameterData`` (see ``cluster_isolation_score.py``). They
measure, in microns, how cleanly each estim spec's active channels sit inside a
single response cluster.

This module asks: does that isolation predict how strongly the spec moves
behavior? To answer it we need the estim effect *per estim_spec_id*, which the
existing ``EStimEffects`` table does NOT provide — that table aggregates by
condition combination, not by spec. So here we recompute the raw effect directly
from trial data, grouped by ``estim_spec_id``:

    effect_size(spec) = mean(metric | estim ON, this spec) * 100
                      - mean(metric | estim OFF, matched baseline) * 100

The estim-OFF baseline is matched on behavioral conditions: for each spec, the
baseline pools the no-estim trials from exactly the behavioral-condition groups
(trial_type / noise_chance / sample_length) in which that spec was actually
delivered. This mirrors ``split_data_by_conditions`` in
``analyze_estim_by_condition`` but groups the estim-ON side by spec id instead of
by estim parameter columns.

Two knobs match the rest of the group_analysis code:
  - ``metric``: any metric understood by ``_filter_for_metric``
    (``pct_hypothesized`` uses all trials; ``pct_hyp_vs_delta`` drops
    choice in {rand, removed} plus Removed-Trial/match rows).
  - ``required_conditions``: an optional global trial filter, e.g.
    ``{'noise_chance': 0.9, 'a1': 3.5, 'polarity': 'PositiveFirst'}``.
    Behavioral keys (trial_type / noise_chance / sample_length) filter ALL
    trials; estim keys (polarity / a1 / num_channels / shape / ...) filter only
    the estim-ON side, so the OFF baseline is never thrown away — same
    convention as ``estim_groups_permutation_test.get_trial_data_for_condition``.

Typical use:
    df = compute_isolation_effect_table(metric=METRIC_PCT_HYP_VS_DELTA,
                                        required_conditions={'noise_chance': 0.9})
    plot_isolation_vs_effect(metric=METRIC_PCT_HYP_VS_DELTA,
                             isolation_metric='min',
                             required_conditions={'noise_chance': 0.9},
                             output_path='.../isolation_vs_effect.png')
"""

import os
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parents[3]))

from clat.util.connection import Connection

from src.analysis.nafc.group_analysis.analyze_estim_by_condition import (
    METRIC_PCT_HYPOTHESIZED,
    METRIC_PCT_HYP_VS_DELTA,
    _filter_for_metric,
    read_trial_data_from_repository,
)

# Behavioral keys apply to every trial (estim on AND off). Everything else in a
# required_conditions dict is treated as an estim parameter and only constrains
# the estim-ON side, leaving the OFF baseline intact.
BEHAVIORAL_KEYS = ('trial_type', 'noise_chance', 'sample_length')

# Short aliases -> EStimParameterData column names.
ISOLATION_COLUMNS = {
    'min': 'estim_min_isolation_um',
    'mean': 'estim_mean_isolation_um',
    'estim_min_isolation_um': 'estim_min_isolation_um',
    'estim_mean_isolation_um': 'estim_mean_isolation_um',
}


# ---------------------------------------------------------------------------
# Trial filtering
# ---------------------------------------------------------------------------

def _fuzzy_eq(series: pd.Series, value) -> pd.Series:
    """Boolean mask of series == value, tolerant to float rounding and NaN.

    Numeric values use np.isclose (so noise_chance 0.9 and a1 3.5 match despite
    storage rounding); None matches NaN; everything else uses ==.
    """
    if value is None:
        return series.isna()
    if isinstance(value, (int, float, np.integer, np.floating)) and not isinstance(value, bool):
        numeric = pd.to_numeric(series, errors='coerce')
        return np.isclose(numeric.to_numpy(dtype=float), float(value),
                          rtol=1e-6, atol=1e-9, equal_nan=False)
    return series == value


def _apply_required_conditions(data: pd.DataFrame, required_conditions) -> pd.DataFrame:
    """Filter trials by required_conditions.

    Behavioral keys filter all rows; estim keys only constrain estim-ON rows
    (OFF rows pass automatically, preserving the baseline).
    """
    if not required_conditions:
        return data

    mask = pd.Series(True, index=data.index)
    is_on = data['is_estim_on'] == 1
    for key, value in required_conditions.items():
        if key not in data.columns:
            print(f"  WARN: required_condition '{key}' not a trial column; ignoring")
            continue
        eq = _fuzzy_eq(data[key], value)
        if key in BEHAVIORAL_KEYS:
            mask &= eq
        else:
            mask &= (~is_on) | eq
    return data[mask]


# ---------------------------------------------------------------------------
# Per-spec effect computation
# ---------------------------------------------------------------------------

def compute_effect_by_spec_for_session(session_id, metric=METRIC_PCT_HYPOTHESIZED,
                                       required_conditions=None,
                                       behavioral_conditions=BEHAVIORAL_KEYS):
    """Raw estim effect per estim_spec_id for one session.

    Returns a list of dicts: session_id, estim_spec_id, n_on, n_off,
    on_pct, off_pct, effect_size. Specs with no estim-ON or no matched
    estim-OFF trials still appear, with None for the missing percentages.
    """
    data = read_trial_data_from_repository(session_id)
    if data is None or len(data) == 0:
        return []

    data = _apply_required_conditions(data, required_conditions)
    data = _filter_for_metric(data, metric)
    data = data[data['is_hypothesized_choice'].notna()]
    if len(data) == 0:
        return []

    present_behavioral = [c for c in behavioral_conditions if c in data.columns]
    if not present_behavioral:
        present_behavioral = ['trial_type'] if 'trial_type' in data.columns else []

    spec_on_vals = defaultdict(list)         # spec_id -> [outcomes]
    spec_behavioral_keys = defaultdict(set)  # spec_id -> {behavioral tuple, ...}
    off_by_bkey = {}                         # behavioral tuple -> np.array of outcomes

    grouped = data.groupby(present_behavioral, dropna=False) if present_behavioral \
        else [((), data)]
    for bvals, bgroup in grouped:
        bkey = bvals if isinstance(bvals, tuple) else (bvals,)
        off_by_bkey[bkey] = bgroup.loc[bgroup['is_estim_on'] == 0,
                                       'is_hypothesized_choice'].to_numpy(dtype=float)
        on_group = bgroup[bgroup['is_estim_on'] == 1]
        for spec_id, spec_rows in on_group.groupby('estim_spec_id', dropna=False):
            if pd.isna(spec_id):
                continue
            spec_id = int(spec_id)
            spec_on_vals[spec_id].extend(
                spec_rows['is_hypothesized_choice'].to_numpy(dtype=float).tolist())
            spec_behavioral_keys[spec_id].add(bkey)

    rows = []
    for spec_id, on_vals in spec_on_vals.items():
        off_arrays = [off_by_bkey[bkey] for bkey in spec_behavioral_keys[spec_id]
                      if len(off_by_bkey.get(bkey, [])) > 0]
        off_vals = np.concatenate(off_arrays) if off_arrays else np.array([])

        on_arr = np.asarray(on_vals, dtype=float)
        on_pct = float(on_arr.mean() * 100) if len(on_arr) > 0 else None
        off_pct = float(off_vals.mean() * 100) if len(off_vals) > 0 else None
        effect = (on_pct - off_pct) if (on_pct is not None and off_pct is not None) else None

        rows.append({
            'session_id': session_id,
            'estim_spec_id': spec_id,
            'n_on': int(len(on_arr)),
            'n_off': int(len(off_vals)),
            'on_pct': on_pct,
            'off_pct': off_pct,
            'effect_size': effect,
        })
    return rows


# ---------------------------------------------------------------------------
# Isolation scores
# ---------------------------------------------------------------------------

def _get_sessions_with_isolation():
    """Session ids that have at least one non-null isolation score in
    EStimParameterData. Used to skip sessions the cluster app never scored."""
    conn = Connection("allen_data_repository")
    conn.execute(
        "SELECT DISTINCT session_id FROM EStimParameterData "
        "WHERE estim_min_isolation_um IS NOT NULL "
        "   OR estim_mean_isolation_um IS NOT NULL "
        "ORDER BY session_id")
    return [row[0] for row in conn.fetch_all()]


def _fetch_isolation_scores(session_ids=None):
    """Return {(session_id, estim_spec_id): {'min': ..., 'mean': ...}} from
    EStimParameterData, optionally restricted to session_ids."""
    conn = Connection("allen_data_repository")
    base = ("SELECT session_id, estim_spec_id, "
            "estim_min_isolation_um, estim_mean_isolation_um FROM EStimParameterData")
    if session_ids:
        placeholders = ', '.join(['%s'] * len(session_ids))
        conn.execute(f"{base} WHERE session_id IN ({placeholders})", tuple(session_ids))
    else:
        conn.execute(base)

    scores = {}
    for sess_id, spec_id, min_um, mean_um in conn.fetch_all():
        scores[(sess_id, int(spec_id))] = {
            'estim_min_isolation_um': float(min_um) if min_um is not None else None,
            'estim_mean_isolation_um': float(mean_um) if mean_um is not None else None,
        }
    return scores


# ---------------------------------------------------------------------------
# Combined table
# ---------------------------------------------------------------------------

def compute_isolation_effect_table(session_ids=None, metric=METRIC_PCT_HYPOTHESIZED,
                                   required_conditions=None,
                                   behavioral_conditions=BEHAVIORAL_KEYS):
    """Build a per-(session, estim_spec) DataFrame of raw estim effect joined with
    isolation scores.

    Args:
        session_ids: list of session_ids, single id string, or None for every
                     session in EStimShapeTrials.
        metric:      any metric understood by _filter_for_metric.
        required_conditions: optional global trial filter (see module docstring).
        behavioral_conditions: keys used to match the estim-OFF baseline.

    Returns:
        DataFrame with columns: session_id, estim_spec_id, n_on, n_off,
        on_pct, off_pct, effect_size, estim_min_isolation_um,
        estim_mean_isolation_um. Empty DataFrame if nothing matched.
    """
    if session_ids is None:
        # Only sessions actually scored by the cluster app are worth processing —
        # specs without isolation scores can't enter the isolation-vs-effect plot.
        session_ids = _get_sessions_with_isolation()
        print(f"Sessions with isolation scores in EStimParameterData: {len(session_ids)}")
    elif isinstance(session_ids, str):
        session_ids = [session_ids]

    all_rows = []
    for session_id in session_ids:
        rows = compute_effect_by_spec_for_session(
            session_id, metric=metric,
            required_conditions=required_conditions,
            behavioral_conditions=behavioral_conditions)
        all_rows.extend(rows)
        print(f"  {session_id}: {len(rows)} estim specs")

    if not all_rows:
        print("No per-spec effects computed.")
        return pd.DataFrame(columns=[
            'session_id', 'estim_spec_id', 'n_on', 'n_off', 'on_pct', 'off_pct',
            'effect_size', 'estim_min_isolation_um', 'estim_mean_isolation_um'])

    df = pd.DataFrame(all_rows)

    isolation = _fetch_isolation_scores(sorted(df['session_id'].unique().tolist()))
    df['estim_min_isolation_um'] = [
        (isolation.get((s, int(spec)), {}) or {}).get('estim_min_isolation_um')
        for s, spec in zip(df['session_id'], df['estim_spec_id'])]
    df['estim_mean_isolation_um'] = [
        (isolation.get((s, int(spec)), {}) or {}).get('estim_mean_isolation_um')
        for s, spec in zip(df['session_id'], df['estim_spec_id'])]

    n_with_iso = df['estim_min_isolation_um'].notna().sum()
    print(f"\nBuilt table: {len(df)} specs across {df['session_id'].nunique()} sessions; "
          f"{n_with_iso} have isolation scores in EStimParameterData")
    return df


# ---------------------------------------------------------------------------
# Correlation + plotting
# ---------------------------------------------------------------------------

def _correlation(x, y):
    """Pearson + Spearman correlation. scipy is imported lazily (it's optional);
    without it only Pearson r is returned, with p-values None."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if len(x) < 3:
        return None
    result = {'n': int(len(x)), 'pearson_r': float(np.corrcoef(x, y)[0, 1]),
              'pearson_p': None, 'spearman_r': None, 'spearman_p': None}
    try:
        from scipy import stats as sp_stats
        pr = sp_stats.pearsonr(x, y)
        sr = sp_stats.spearmanr(x, y)
        result.update(pearson_r=float(pr[0]), pearson_p=float(pr[1]),
                      spearman_r=float(sr.correlation), spearman_p=float(sr.pvalue))
    except Exception as e:  # scipy missing or degenerate input
        print(f"  (scipy unavailable for p-values: {e})")
    return result


def plot_isolation_vs_effect(session_ids=None, metric=METRIC_PCT_HYPOTHESIZED,
                             isolation_metric='min', required_conditions=None,
                             behavioral_conditions=BEHAVIORAL_KEYS,
                             min_on_trials=15, min_off_trials=15,
                             abs_effect=False, color_by_session=True,
                             output_path=None, df=None):
    """Scatter raw estim effect vs isolation score, one point per estim spec.

    Args:
        isolation_metric: 'min' / 'mean' (or the full column name).
        min_on_trials / min_off_trials: drop specs with too few trials.
        abs_effect: plot |effect| instead of signed effect — useful when you
                    only care about how *large* the effect is, regardless of sign.
        color_by_session: color points by session id.
        df: precomputed table from compute_isolation_effect_table (skips recompute).

    Returns the filtered DataFrame actually plotted.
    """
    iso_col = ISOLATION_COLUMNS.get(isolation_metric)
    if iso_col is None:
        raise ValueError(f"isolation_metric must be one of {sorted(ISOLATION_COLUMNS)}; "
                         f"got {isolation_metric!r}")

    if df is None:
        df = compute_isolation_effect_table(
            session_ids=session_ids, metric=metric,
            required_conditions=required_conditions,
            behavioral_conditions=behavioral_conditions)
    if len(df) == 0:
        print("Nothing to plot.")
        return df

    plot_df = df[
        df['effect_size'].notna()
        & df[iso_col].notna()
        & (df['n_on'] >= min_on_trials)
        & (df['n_off'] >= min_off_trials)
    ].copy()

    if len(plot_df) == 0:
        print(f"No specs pass filters (n_on>={min_on_trials}, n_off>={min_off_trials}, "
              f"isolation + effect present).")
        return plot_df

    plot_df['y'] = plot_df['effect_size'].abs() if abs_effect else plot_df['effect_size']

    corr = _correlation(plot_df[iso_col].to_numpy(), plot_df['y'].to_numpy())

    fig, ax = plt.subplots(figsize=(9, 7))

    if color_by_session:
        sessions = sorted(plot_df['session_id'].unique())
        cmap = plt.cm.get_cmap('tab20', max(len(sessions), 1))
        color_for = {s: cmap(i) for i, s in enumerate(sessions)}
        for s in sessions:
            sub = plot_df[plot_df['session_id'] == s]
            ax.scatter(sub[iso_col], sub['y'], s=60, alpha=0.8,
                       color=color_for[s], edgecolors='black', linewidths=0.5,
                       label=s)
        if len(sessions) <= 20:
            ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', fontsize=8,
                      title='session', framealpha=0.9)
    else:
        ax.scatter(plot_df[iso_col], plot_df['y'], s=60, alpha=0.8,
                   color='steelblue', edgecolors='black', linewidths=0.5)

    # Least-squares trend line
    if len(plot_df) >= 2:
        xs = plot_df[iso_col].to_numpy(dtype=float)
        ys = plot_df['y'].to_numpy(dtype=float)
        slope, intercept = np.polyfit(xs, ys, 1)
        x_line = np.array([xs.min(), xs.max()])
        ax.plot(x_line, slope * x_line + intercept, color='red', linewidth=2,
                alpha=0.8, label='_nolegend_')

    if not abs_effect:
        ax.axhline(0, color='black', linestyle='--', linewidth=1, alpha=0.5)

    ax.set_xlabel(f"{iso_col}  (µm; higher = better isolated)", fontsize=12)
    ax.set_ylabel(f"{'|effect|' if abs_effect else 'effect'} "
                  f"(EStim ON − OFF %, metric={metric})", fontsize=12)

    title = "Estim isolation vs raw effect (per estim spec)"
    if required_conditions:
        req = ', '.join(f"{k}={v}" for k, v in required_conditions.items())
        title += f"\nrequired: {req}"
    if corr:
        sub = f"n={corr['n']}  Pearson r={corr['pearson_r']:.3f}"
        if corr['pearson_p'] is not None:
            sub += f" (p={corr['pearson_p']:.3g})"
        if corr['spearman_r'] is not None:
            sub += f"   Spearman ρ={corr['spearman_r']:.3f}"
            if corr['spearman_p'] is not None:
                sub += f" (p={corr['spearman_p']:.3g})"
        title += f"\n{sub}"
    ax.set_title(title, fontsize=12)
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        fig.savefig(output_path, dpi=150, bbox_inches='tight')
        svg_path = output_path.rsplit('.', 1)[0] + '.svg'
        fig.savefig(svg_path, bbox_inches='tight')
        print(f"Saved plot to {output_path}")
    plt.show()
    return plot_df


def main():
    # Any metric understood by the rest of the group_analysis code works here.
    metric = METRIC_PCT_HYP_VS_DELTA

    # Optional global trial filter — same semantics as analyze_estim_by_condition:
    # behavioral keys (trial_type/noise_chance/sample_length) filter all trials;
    # estim keys (polarity/a1/num_channels/shape/...) filter only the ON side.
    required_conditions = {
        # 'noise_chance': 0.9,
        # 'a1': 3.5,
        # 'polarity': 'PositiveFirst',
        # 'trial_type': 'Hypothesized Shape',
    }

    save_dir = "/home/connorlab/Documents/plots/across_experiments/"
    output_path = os.path.join(save_dir, "isolation_vs_effect_min.png")

    # 'min'  -> estim_min_isolation_um (worst channel)
    # 'mean' -> estim_mean_isolation_um (average per channel)
    plot_isolation_vs_effect(
        session_ids=None,            # None = all sessions
        metric=metric,
        isolation_metric='min',
        required_conditions=required_conditions or None,
        min_on_trials=15,
        min_off_trials=15,
        abs_effect=False,            # True -> relate isolation to effect MAGNITUDE
        color_by_session=True,
        output_path=output_path,
    )


if __name__ == '__main__':
    main()
