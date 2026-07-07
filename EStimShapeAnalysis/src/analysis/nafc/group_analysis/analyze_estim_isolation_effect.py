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
from src.analysis.nafc.estim_hyperparameters import get_estim_hyperparameters

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
    # Clustering-free PC-neighbor distance (compute_estim_pc_neighbor_scores).
    # NOTE: higher = WORSE (more boundary-like), opposite of the isolation cols.
    'pc_mean': 'estim_mean_pc_neighbor_dist',
    'pc_max': 'estim_max_pc_neighbor_dist',
    'estim_mean_pc_neighbor_dist': 'estim_mean_pc_neighbor_dist',
    'estim_max_pc_neighbor_dist': 'estim_max_pc_neighbor_dist',
}

# Columns where higher means worse isolation (so the x-axis hint flips).
HIGHER_IS_WORSE_COLUMNS = {'estim_mean_pc_neighbor_dist', 'estim_max_pc_neighbor_dist'}


def _isolation_axis_hint(iso_col):
    """Human-readable direction hint for an isolation/distance column."""
    if iso_col in HIGHER_IS_WORSE_COLUMNS:
        return "higher = more boundary-like (worse)"
    return "higher = better isolated"

# Polarity-first ordering maps to the leading phase of the biphasic pulse:
# PositiveFirst = anodic-first, NegativeFirst = cathodic-first. Plotted as
# separate series since we don't yet know how to fold polarity into the metric.
POLARITY_LABELS = {
    'PositiveFirst': 'Anodic (PositiveFirst)',
    'NegativeFirst': 'Cathodic (NegativeFirst)',
}
POLARITY_COLORS = {
    'PositiveFirst': '#D32F2F',   # red — anodic
    'NegativeFirst': '#1976D2',   # blue — cathodic
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
    """Session ids that have any row in EStimParameterData — i.e. were scored by
    the cluster app (isolation) and/or compute_estim_pc_neighbor_scores. The
    final per-spec join still drops specs missing the specific metric used."""
    conn = Connection("allen_data_repository")
    conn.execute(
        "SELECT DISTINCT session_id FROM EStimParameterData ORDER BY session_id")
    return [row[0] for row in conn.fetch_all()]


# Score columns we surface from EStimParameterData. Kept as a list so a missing
# (not-yet-migrated) column is simply skipped rather than raising.
_SCORE_COLUMNS = (
    'estim_min_isolation_um', 'estim_mean_isolation_um',
    'estim_mean_pc_neighbor_dist', 'estim_max_pc_neighbor_dist',
)


def _fetch_isolation_scores(session_ids=None):
    """Return {(session_id, estim_spec_id): {col: value or None}} from
    EStimParameterData, reading columns by name so PC-neighbor columns that
    haven't been added yet are simply absent rather than an error."""
    conn = Connection("allen_data_repository")
    base = "SELECT * FROM EStimParameterData"
    if session_ids:
        placeholders = ', '.join(['%s'] * len(session_ids))
        conn.execute(f"{base} WHERE session_id IN ({placeholders})", tuple(session_ids))
    else:
        conn.execute(base)

    columns = [desc[0] for desc in conn.my_cursor.description]
    scores = {}
    for row in conn.fetch_all():
        row_dict = dict(zip(columns, row))
        key = (row_dict['session_id'], int(row_dict['estim_spec_id']))
        scores[key] = {
            col: (float(row_dict[col]) if row_dict.get(col) is not None else None)
            for col in _SCORE_COLUMNS if col in row_dict
        }
    return scores


def _fetch_estim_power_and_polarity(session_ids=None):
    """Return {(session_id, estim_spec_id): {'total_current_uA': ..., 'polarity': ...,
    'n_active': ...}} from EStimParameters.

    Total current is the sum of a1 across all actively-stimulating channels
    (a1 > 0), matching the active-channel convention everywhere else. Polarity is
    read off the active channels (uniform per spec under the current paradigm)."""
    conn = Connection("allen_data_repository")
    base = ("SELECT session_id, estim_spec_id, SUM(a1) AS total_current, "
            "MIN(polarity) AS polarity, COUNT(*) AS n_active "
            "FROM EStimParameters WHERE a1 > 0")
    if session_ids:
        placeholders = ', '.join(['%s'] * len(session_ids))
        conn.execute(f"{base} AND session_id IN ({placeholders}) "
                     "GROUP BY session_id, estim_spec_id", tuple(session_ids))
    else:
        conn.execute(f"{base} GROUP BY session_id, estim_spec_id")

    out = {}
    for sess_id, spec_id, total_current, polarity, n_active in conn.fetch_all():
        out[(sess_id, int(spec_id))] = {
            'total_current_uA': float(total_current) if total_current is not None else None,
            'polarity': polarity,
            'n_active': int(n_active) if n_active is not None else None,
        }
    return out


# ---------------------------------------------------------------------------
# Combined table
# ---------------------------------------------------------------------------

def compute_isolation_effect_table(start_session_id=None, exclude_session_ids=None,
                                   *, metric=METRIC_PCT_HYPOTHESIZED,
                                   required_conditions=None,
                                   behavioral_conditions=BEHAVIORAL_KEYS):
    """Build a per-(session, estim_spec) DataFrame of raw estim effect joined with
    isolation scores.

    Operates on every session scored in EStimParameterData, then:
      - start_session_id    : keep only sessions whose id >= this value
                              (lexicographic works because ids are YYMMDD_N).
      - exclude_session_ids : iterable of session ids to drop.

    Args:
        metric:      any metric understood by _filter_for_metric.
        required_conditions: optional global trial filter (see module docstring).
        behavioral_conditions: keys used to match the estim-OFF baseline.

    Returns:
        DataFrame with columns: session_id, estim_spec_id, n_on, n_off,
        on_pct, off_pct, effect_size, estim_min_isolation_um,
        estim_mean_isolation_um, total_current_uA, polarity,
        n_active_channels. Empty DataFrame if nothing matched.
    """
    # Only sessions scored in EStimParameterData are worth processing — specs
    # without any isolation/PC score can't enter the plots.
    session_ids = _get_sessions_with_isolation()
    if start_session_id is not None:
        session_ids = [s for s in session_ids if s >= start_session_id]
    if exclude_session_ids:
        excluded = set(exclude_session_ids)
        session_ids = [s for s in session_ids if s not in excluded]
    print(f"Sessions scored in EStimParameterData (after start/exclude filters): "
          f"{len(session_ids)}")

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
            'effect_size', 'estim_min_isolation_um', 'estim_mean_isolation_um',
            'estim_mean_pc_neighbor_dist', 'estim_max_pc_neighbor_dist',
            'total_current_uA', 'polarity', 'n_active_channels'])

    df = pd.DataFrame(all_rows)

    isolation = _fetch_isolation_scores(sorted(df['session_id'].unique().tolist()))
    df['estim_min_isolation_um'] = [
        (isolation.get((s, int(spec)), {}) or {}).get('estim_min_isolation_um')
        for s, spec in zip(df['session_id'], df['estim_spec_id'])]
    df['estim_mean_isolation_um'] = [
        (isolation.get((s, int(spec)), {}) or {}).get('estim_mean_isolation_um')
        for s, spec in zip(df['session_id'], df['estim_spec_id'])]
    # Clustering-free PC-neighbor distance (compute_estim_pc_neighbor_scores);
    # absent (all-None) until that script has been run.
    df['estim_mean_pc_neighbor_dist'] = [
        (isolation.get((s, int(spec)), {}) or {}).get('estim_mean_pc_neighbor_dist')
        for s, spec in zip(df['session_id'], df['estim_spec_id'])]
    df['estim_max_pc_neighbor_dist'] = [
        (isolation.get((s, int(spec)), {}) or {}).get('estim_max_pc_neighbor_dist')
        for s, spec in zip(df['session_id'], df['estim_spec_id'])]

    power = _fetch_estim_power_and_polarity(sorted(df['session_id'].unique().tolist()))
    df['total_current_uA'] = [
        (power.get((s, int(spec)), {}) or {}).get('total_current_uA')
        for s, spec in zip(df['session_id'], df['estim_spec_id'])]
    df['polarity'] = [
        (power.get((s, int(spec)), {}) or {}).get('polarity')
        for s, spec in zip(df['session_id'], df['estim_spec_id'])]
    df['n_active_channels'] = [
        (power.get((s, int(spec)), {}) or {}).get('n_active')
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


def plot_isolation_vs_effect(start_session_id=None, exclude_session_ids=None,
                             *, metric=METRIC_PCT_HYPOTHESIZED,
                             isolation_metric='min', required_conditions=None,
                             behavioral_conditions=BEHAVIORAL_KEYS,
                             min_on_trials=15, min_off_trials=15,
                             abs_effect=False, color_by_session=True,
                             output_path=None, df=None):
    """Scatter raw estim effect vs isolation score, one point per estim spec.

    Args:
        start_session_id / exclude_session_ids: session selection (see
            compute_isolation_effect_table).
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
            start_session_id=start_session_id, exclude_session_ids=exclude_session_ids,
            metric=metric,
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
        cmap = plt.get_cmap('tab20', max(len(sessions), 1))
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

    ax.set_xlabel(f"{iso_col}  ({_isolation_axis_hint(iso_col)})", fontsize=12)
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


def plot_power_over_isolation_vs_effect(start_session_id=None, exclude_session_ids=None,
                                        *, metric=METRIC_PCT_HYPOTHESIZED,
                                        isolation_metric='min', required_conditions=None,
                                        behavioral_conditions=BEHAVIORAL_KEYS,
                                        min_on_trials=15, min_off_trials=15,
                                        require_positive_isolation=True,
                                        combine_op='auto',
                                        abs_effect=False, output_path=None, df=None):
    """Scatter a combined power/isolation metric vs estim effect, one point per
    estim spec, split into anodic vs cathodic series.

    The x metric combines stimulation power with isolation. How they combine
    depends on the isolation column's polarity (``combine_op``):

      - 'divide'   x = total_current_uA / isolation   — for estim_*_isolation_um,
                   where higher isolation = BETTER. A lot of current into
                   poorly-isolated tissue (small isolation) gives a large ratio.
      - 'multiply' x = total_current_uA * isolation    — for the PC-neighbor
                   distance columns, where higher distance = WORSE. A lot of
                   current at a functional boundary (large distance) gives a
                   large product.
      - 'auto'     multiply for higher-is-worse columns (PC-neighbor), divide
                   otherwise (isolation). Default.

    Either way a LARGE x means "lots of current delivered where it shouldn't be",
    so the effect-vs-x relationship is expected to be hump-shaped: too-low x
    (weak / well-targeted) and too-high x (overdriven / spilling across a
    boundary) both bad. Anodic (PositiveFirst) and cathodic (NegativeFirst) specs
    are plotted as separate series because we don't yet know how polarity should
    enter the metric.

    Args:
        isolation_metric: 'min'/'mean' (isolation µm) or 'pc_mean'/'pc_max'
            (PC-neighbor distance). See ISOLATION_COLUMNS.
        combine_op: 'auto' (default), 'divide', or 'multiply'.
        require_positive_isolation: when dividing, drop specs whose isolation
            <= 0 (isolation goes negative when channels split across clusters;
            dividing by it is uninterpretable). Ignored when multiplying.
        abs_effect: plot |effect| instead of signed effect.
        df: precomputed table (skips recompute).

    Returns the filtered DataFrame actually plotted.
    """
    iso_col = ISOLATION_COLUMNS.get(isolation_metric)
    if iso_col is None:
        raise ValueError(f"isolation_metric must be one of {sorted(ISOLATION_COLUMNS)}; "
                         f"got {isolation_metric!r}")

    if combine_op == 'auto':
        combine_op = 'multiply' if iso_col in HIGHER_IS_WORSE_COLUMNS else 'divide'
    if combine_op not in ('divide', 'multiply'):
        raise ValueError(f"combine_op must be 'auto', 'divide', or 'multiply'; got {combine_op!r}")

    if df is None:
        df = compute_isolation_effect_table(
            start_session_id=start_session_id, exclude_session_ids=exclude_session_ids,
            metric=metric,
            required_conditions=required_conditions,
            behavioral_conditions=behavioral_conditions)
    if len(df) == 0:
        print("Nothing to plot.")
        return df

    plot_df = df[
        df['effect_size'].notna()
        & df[iso_col].notna()
        & df['total_current_uA'].notna()
        & (df['n_on'] >= min_on_trials)
        & (df['n_off'] >= min_off_trials)
    ].copy()

    # Dividing by a non-positive isolation is uninterpretable; only relevant for
    # the divide path (PC distances are >= 0 and used multiplicatively).
    if combine_op == 'divide' and require_positive_isolation:
        n_before = len(plot_df)
        plot_df = plot_df[plot_df[iso_col] > 0]
        dropped = n_before - len(plot_df)
        if dropped:
            print(f"Dropped {dropped} specs with {iso_col} <= 0 "
                  f"(set require_positive_isolation=False to keep them)")

    if len(plot_df) == 0:
        print("No specs pass filters.")
        return plot_df

    if combine_op == 'divide':
        plot_df['power_over_isolation'] = plot_df['total_current_uA'] / plot_df[iso_col]
    else:
        plot_df['power_over_isolation'] = plot_df['total_current_uA'] * plot_df[iso_col]
    plot_df['y'] = plot_df['effect_size'].abs() if abs_effect else plot_df['effect_size']

    fig, ax = plt.subplots(figsize=(9, 7))

    # One series per polarity; unknown/other polarities collapse into a gray series.
    series_order = ['PositiveFirst', 'NegativeFirst']
    present = [p for p in series_order if (plot_df['polarity'] == p).any()]
    other = [p for p in plot_df['polarity'].dropna().unique() if p not in series_order]
    for pol in present + other:
        sub = plot_df[plot_df['polarity'] == pol]
        if len(sub) == 0:
            continue
        color = POLARITY_COLORS.get(pol, '#757575')
        label = POLARITY_LABELS.get(pol, str(pol))
        corr = _correlation(sub['power_over_isolation'].to_numpy(), sub['y'].to_numpy())
        if corr:
            label += f"  (n={corr['n']}, r={corr['pearson_r']:.2f}"
            if corr['pearson_p'] is not None:
                label += f", p={corr['pearson_p']:.3g}"
            label += ")"
        ax.scatter(sub['power_over_isolation'], sub['y'], s=60, alpha=0.8,
                   color=color, edgecolors='black', linewidths=0.5, label=label)
        # Per-series trend line
        if len(sub) >= 2:
            xs = sub['power_over_isolation'].to_numpy(dtype=float)
            ys = sub['y'].to_numpy(dtype=float)
            slope, intercept = np.polyfit(xs, ys, 1)
            x_line = np.array([xs.min(), xs.max()])
            ax.plot(x_line, slope * x_line + intercept, color=color,
                    linewidth=2, alpha=0.7)

    if not abs_effect:
        ax.axhline(0, color='black', linestyle='--', linewidth=1, alpha=0.5)

    op_symbol = '/' if combine_op == 'divide' else '×'
    ax.set_xlabel(f"total current (µA) {op_symbol} {iso_col}  "
                  f"(combined stimulation power & isolation; larger = worse)",
                  fontsize=12)
    ax.set_ylabel(f"{'|effect|' if abs_effect else 'effect'} "
                  f"(EStim ON − OFF %, metric={metric})", fontsize=12)

    title = f"Stimulation power {op_symbol} isolation vs raw effect (per estim spec)"
    if required_conditions:
        req = ', '.join(f"{k}={v}" for k, v in required_conditions.items())
        title += f"\nrequired: {req}"
    ax.set_title(title, fontsize=12)
    ax.legend(fontsize=9, framealpha=0.9)
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


# ===========================================================================
# Metric comparison: which neighbour-similarity metric best explains the effect?
#
# The metrics themselves are computed by compute_estim_neighbor_scores.py and
# stored (higher = more isolated) in the tidy table EStimNeighborScores. Here we
# join every metric to the per-spec raw effect and rank them by how well they
# predict it — including a partial correlation controlling for current dose, so a
# metric that merely tracks stimulation power is separated from one that adds real
# isolation information.
# ===========================================================================

# Human-friendly ordering / labels for known metrics (unknown ones still appear,
# appended in alphabetical order).
_METRIC_LABELS = {
    'pc_neighbor_sim': 'PC-neighbour similarity',
    'channel_corr': 'Channel corr (all stims)',
    'channel_corr_top20': 'Channel corr (top 20)',
    'channel_corr_top50': 'Channel corr (top 50)',
    'channel_corr_top100': 'Channel corr (top 100)',
    'channel_corr_delta_variant': 'Channel corr (delta+variant)',
    'pc_loading_sim': 'PC-loading similarity',
}
_METRIC_ORDER = list(_METRIC_LABELS)


# Single shared config for BOTH comparison entry points (main_metric_comparison and
# main_neighbor_sweep). Edit here once — keeping them in one place makes it impossible
# for the leaderboard and the sweep to silently drift onto different effect
# definitions (which makes every correlation disagree even though the code is the
# same). GUI users: change these constants, then Run the file.
COMPARISON_METRIC = METRIC_PCT_HYP_VS_DELTA
COMPARISON_REQUIRED_CONDITIONS = {'trial_type': 'Hypothesized Shape'}
COMPARISON_START_SESSION_ID = "260402_0"
COMPARISON_EXCLUDE_SESSION_IDS = ["260421_0", "260410_0"]
COMPARISON_MIN_ON_TRIALS = 10
COMPARISON_MIN_OFF_TRIALS = 10
COMPARISON_ABS_EFFECT = True          # relate metrics to |effect| (effect strength)
COMPARISON_SAVE_DIR = "/home/connorlab/Documents/plots/across_experiments/"
# Split the whole analysis by trial_type. None = single pass using
# COMPARISON_REQUIRED_CONDITIONS as-is; [] = auto-discover the trial types present;
# or an explicit list, e.g. ['Hypothesized Shape', 'Random Shape'].
COMPARISON_TRIAL_TYPES = None


def _slug(text):
    """Filesystem-safe lowercase slug for tags in filenames (e.g. a trial_type)."""
    return ''.join(c if c.isalnum() else '_' for c in str(text)).strip('_').lower()


def _get_sessions_with_neighbor_scores():
    """Session ids that have any row in EStimNeighborScores."""
    conn = Connection("allen_data_repository")
    conn.execute("SELECT DISTINCT session_id FROM EStimNeighborScores ORDER BY session_id")
    return [row[0] for row in conn.fetch_all()]


def _available_n_neighbors(exclude_other_estim=True):
    """Sorted list of n_neighbors values present in EStimNeighborScores for the
    given exclude_other_estim setting (the neighbourhood sizes available to sweep)."""
    conn = Connection("allen_data_repository")
    conn.execute(
        "SELECT DISTINCT n_neighbors FROM EStimNeighborScores "
        "WHERE exclude_other_estim = %s ORDER BY n_neighbors",
        (1 if exclude_other_estim else 0,))
    return [int(row[0]) for row in conn.fetch_all()]


def _fetch_neighbor_scores(session_ids=None, *, n_neighbors=3,
                           exclude_other_estim=True):
    """Return {(session_id, estim_spec_id): {metric_name: {aggregation: value}}}
    plus the sorted list of metric names present, from EStimNeighborScores, for one
    (n_neighbors, exclude_other_estim) configuration."""
    conn = Connection("allen_data_repository")
    where = ["n_neighbors = %s", "exclude_other_estim = %s"]
    params = [int(n_neighbors), 1 if exclude_other_estim else 0]
    if session_ids:
        where.append(f"session_id IN ({', '.join(['%s'] * len(session_ids))})")
        params.extend(session_ids)
    conn.execute(
        "SELECT session_id, estim_spec_id, metric_name, aggregation, value "
        "FROM EStimNeighborScores WHERE " + " AND ".join(where), tuple(params))

    scores = {}
    metric_names = set()
    for session_id, spec_id, metric_name, aggregation, value in conn.fetch_all():
        key = (session_id, int(spec_id))
        metric_names.add(metric_name)
        scores.setdefault(key, {}).setdefault(metric_name, {})[aggregation] = (
            float(value) if value is not None else None)
    ordered = [m for m in _METRIC_ORDER if m in metric_names]
    ordered += sorted(m for m in metric_names if m not in _METRIC_ORDER)
    return scores, ordered


def _fetch_current_per_second(session_spec_pairs):
    """Return {(session_id, estim_spec_id): current_per_second} for the given
    pairs, via get_estim_hyperparameters (a1 * num_channels * pulse_rate_hz)."""
    out = {}
    for session_id, spec_id in session_spec_pairs:
        try:
            hp = get_estim_hyperparameters(session_id, int(spec_id))
        except Exception as exc:
            print(f"  WARN: current lookup failed for {session_id}/{spec_id}: {exc}")
            hp = {}
        out[(session_id, int(spec_id))] = hp.get('current_per_second')
    return out


def _effect_and_current_table(start_session_id=None, exclude_session_ids=None, *,
                              metric=METRIC_PCT_HYPOTHESIZED, required_conditions=None,
                              behavioral_conditions=BEHAVIORAL_KEYS):
    """Per-(session, estim_spec) DataFrame of the raw estim effect + current_per_second,
    over sessions that have neighbour scores. Independent of neighbourhood config, so
    a sweep can compute it once and re-join different metric configs."""
    session_ids = _get_sessions_with_neighbor_scores()
    if start_session_id is not None:
        session_ids = [s for s in session_ids if s >= start_session_id]
    if exclude_session_ids:
        excluded = set(exclude_session_ids)
        session_ids = [s for s in session_ids if s not in excluded]
    print(f"Sessions with neighbour scores (after start/exclude filters): {len(session_ids)}")

    all_rows = []
    for session_id in session_ids:
        rows = compute_effect_by_spec_for_session(
            session_id, metric=metric, required_conditions=required_conditions,
            behavioral_conditions=behavioral_conditions)
        all_rows.extend(rows)
        print(f"  {session_id}: {len(rows)} estim specs")

    if not all_rows:
        print("No per-spec effects computed.")
        return pd.DataFrame()

    df = pd.DataFrame(all_rows)
    pairs = sorted({(s, int(spec)) for s, spec in zip(df['session_id'], df['estim_spec_id'])})
    cps = _fetch_current_per_second(pairs)
    df['current_per_second'] = [
        cps.get((s, int(spec))) for s, spec in zip(df['session_id'], df['estim_spec_id'])]
    # n_active_channels is the direct source of the "worst"=min selection bias
    # (more estim channels -> more chances for a low minimum), so it's available as
    # an alternative covariate to partial out.
    power = _fetch_estim_power_and_polarity(sorted(df['session_id'].unique().tolist()))
    df['n_active_channels'] = [
        (power.get((s, int(spec)), {}) or {}).get('n_active')
        for s, spec in zip(df['session_id'], df['estim_spec_id'])]
    return df


def _join_neighbor_scores(df, scores, metric_names, aggregations=('mean', 'worst')):
    """Add one ``<metric>__<aggregation>`` column per (metric, aggregation) to df
    from a _fetch_neighbor_scores result. Returns the list of columns added."""
    metric_cols = []
    for name in metric_names:
        for agg in aggregations:
            col = f"{name}__{agg}"
            df[col] = [
                (scores.get((s, int(spec)), {}).get(name, {}) or {}).get(agg)
                for s, spec in zip(df['session_id'], df['estim_spec_id'])]
            metric_cols.append(col)
    return metric_cols


def build_metric_comparison_table(start_session_id=None, exclude_session_ids=None,
                                  *, metric=METRIC_PCT_HYPOTHESIZED,
                                  required_conditions=None,
                                  behavioral_conditions=BEHAVIORAL_KEYS,
                                  n_neighbors=3, exclude_other_estim=True):
    """Per-(session, estim_spec) DataFrame joining the raw estim effect with every
    neighbour-similarity metric (all aggregations) and current_per_second, for one
    (n_neighbors, exclude_other_estim) configuration.

    Returns (df, metric_names). Metric columns are named ``<metric>__<aggregation>``
    (e.g. ``channel_corr__mean``, ``pc_neighbor_sim__worst``)."""
    df = _effect_and_current_table(
        start_session_id=start_session_id, exclude_session_ids=exclude_session_ids,
        metric=metric, required_conditions=required_conditions,
        behavioral_conditions=behavioral_conditions)
    if len(df) == 0:
        return df, []

    scores, metric_names = _fetch_neighbor_scores(
        sorted(df['session_id'].unique().tolist()),
        n_neighbors=n_neighbors, exclude_other_estim=exclude_other_estim)
    metric_cols = _join_neighbor_scores(df, scores, metric_names)

    n_with = sum(df[c].notna().any() for c in metric_cols)
    print(f"\nBuilt comparison table (n_neighbors={n_neighbors}, "
          f"exclude_other_estim={exclude_other_estim}): {len(df)} specs across "
          f"{df['session_id'].nunique()} sessions; {len(metric_names)} metrics "
          f"({n_with} metric columns populated)")
    return df, metric_names


# ---------------------------------------------------------------------------
# Splitting the whole analysis by trial_type
#
# trial_type is a behavioural condition, so it changes the estim EFFECT (Y) but NOT
# the neighbour-metric scores (X, which come from GA responses). So we compute the
# effect table once per trial_type, tag it, stack into one long table, and re-join
# the same scores. Everything downstream (leaderboard, grid, sweep) then just filters
# the long table by trial_type.
# ---------------------------------------------------------------------------

def _rc_for_trial_type(base_required_conditions, trial_type):
    """required_conditions with trial_type overridden to `trial_type` (None -> keep
    base as-is)."""
    rc = {k: v for k, v in (base_required_conditions or {}).items() if k != 'trial_type'}
    if trial_type is not None:
        rc['trial_type'] = trial_type
    return rc or None


def _discover_trial_types(start_session_id=None, exclude_session_ids=None):
    """Distinct trial_type values across the sessions that have neighbour scores.
    Reads trial data once per session (same source the effect uses)."""
    session_ids = _get_sessions_with_neighbor_scores()
    if start_session_id is not None:
        session_ids = [s for s in session_ids if s >= start_session_id]
    if exclude_session_ids:
        excluded = set(exclude_session_ids)
        session_ids = [s for s in session_ids if s not in excluded]
    types = set()
    for sid in session_ids:
        data = read_trial_data_from_repository(sid)
        if data is not None and len(data) and 'trial_type' in data.columns:
            types.update(t for t in data['trial_type'].dropna().unique().tolist())
    return sorted(types)


def build_metric_comparison_long(trial_types, start_session_id=None,
                                 exclude_session_ids=None, *,
                                 metric=METRIC_PCT_HYPOTHESIZED,
                                 base_required_conditions=None,
                                 behavioral_conditions=BEHAVIORAL_KEYS,
                                 n_neighbors=3, exclude_other_estim=True):
    """Long per-(session, estim_spec, trial_type) table: the effect computed
    separately for each trial_type, tagged with a ``trial_type`` column, with the
    (trial-type-independent) neighbour-metric scores + current joined on.

    Returns (long_df, metric_names). Each spec contributes one row per trial_type
    (same metric X, trial-type-specific effect Y)."""
    frames = []
    for tt in trial_types:
        rc = _rc_for_trial_type(base_required_conditions, tt)
        print(f"\n--- effect table for trial_type={tt!r} ---")
        df_tt = _effect_and_current_table(
            start_session_id=start_session_id, exclude_session_ids=exclude_session_ids,
            metric=metric, required_conditions=rc,
            behavioral_conditions=behavioral_conditions)
        if len(df_tt) == 0:
            print(f"  (no specs for trial_type={tt!r})")
            continue
        df_tt['trial_type'] = tt
        frames.append(df_tt)

    if not frames:
        return pd.DataFrame(), []

    long_df = pd.concat(frames, ignore_index=True)
    scores, metric_names = _fetch_neighbor_scores(
        sorted(long_df['session_id'].unique().tolist()),
        n_neighbors=n_neighbors, exclude_other_estim=exclude_other_estim)
    _join_neighbor_scores(long_df, scores, metric_names)
    print(f"\nBuilt long comparison table: {len(long_df)} rows across "
          f"{len(frames)} trial types (n_neighbors={n_neighbors})")
    return long_df, metric_names


def _partial_correlation(x, y, z):
    """Partial Pearson correlation of x and y controlling for z: correlate the
    residuals of x and y after linearly regressing each on z. Returns a dict with
    n, r, p (p None if scipy unavailable), or None if too few finite points."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    z = np.asarray(z, dtype=float)
    mask = np.isfinite(x) & np.isfinite(y) & np.isfinite(z)
    x, y, z = x[mask], y[mask], z[mask]
    n = len(x)
    if n < 4 or np.std(z) < 1e-12:
        return None
    design = np.vstack([z, np.ones_like(z)]).T
    bx, _, _, _ = np.linalg.lstsq(design, x, rcond=None)
    by, _, _, _ = np.linalg.lstsq(design, y, rcond=None)
    rx = x - design @ bx
    ry = y - design @ by
    if np.std(rx) < 1e-12 or np.std(ry) < 1e-12:
        return None
    r = float(np.corrcoef(rx, ry)[0, 1])
    p = None
    try:
        from scipy import stats as sp_stats
        # one covariate controlled -> dof = n - 3
        dof = n - 3
        if dof > 0 and abs(r) < 1.0:
            t = r * np.sqrt(dof / (1.0 - r * r))
            p = float(2.0 * sp_stats.t.sf(abs(t), dof))
    except Exception:
        pass
    return {'n': n, 'r': r, 'p': p}


def build_metric_leaderboard(df, metric_names, *, aggregation='mean',
                             min_on_trials=15, min_off_trials=15,
                             control_for_current=True, abs_effect=False):
    """Rank metrics by how well they explain effect_size.

    For each metric (at the given aggregation) computes, over the specs passing the
    trial-count filters: n, Pearson r/p, Spearman ρ/p, R² (= Pearson r²), and — if
    control_for_current — the partial correlation with effect controlling for
    current_per_second. Sorted by |partial r| when available, else |Pearson r|.

    Returns a DataFrame, one row per metric."""
    base = df[
        df['effect_size'].notna()
        & (df['n_on'] >= min_on_trials)
        & (df['n_off'] >= min_off_trials)
    ]

    rows = []
    for name in metric_names:
        col = f"{name}__{aggregation}"
        if col not in df.columns:
            continue
        sub = base[base[col].notna()]
        y = sub['effect_size'].abs() if abs_effect else sub['effect_size']
        corr = _correlation(sub[col].to_numpy(), y.to_numpy())
        row = {
            'metric': name,
            'label': _METRIC_LABELS.get(name, name),
            'aggregation': aggregation,
            'n': (corr['n'] if corr else int(len(sub))),
            'pearson_r': corr['pearson_r'] if corr else None,
            'pearson_p': corr['pearson_p'] if corr else None,
            'spearman_r': corr['spearman_r'] if corr else None,
            'spearman_p': corr['spearman_p'] if corr else None,
            'r2': (corr['pearson_r'] ** 2 if corr and corr['pearson_r'] is not None else None),
            'partial_r': None,
            'partial_p': None,
            'partial_n': None,
        }
        if control_for_current and 'current_per_second' in df.columns:
            pc = _partial_correlation(sub[col].to_numpy(), y.to_numpy(),
                                      sub['current_per_second'].to_numpy())
            if pc:
                row.update(partial_r=pc['r'], partial_p=pc['p'], partial_n=pc['n'])
        rows.append(row)

    board = pd.DataFrame(rows)
    if len(board) == 0:
        return board
    rank_key = board['partial_r'].abs().where(board['partial_r'].notna(),
                                              board['pearson_r'].abs())
    board = board.assign(_rank=rank_key).sort_values(
        '_rank', ascending=False, na_position='last').drop(columns='_rank')
    return board.reset_index(drop=True)


def plot_metric_grid(df, metric_names, *, aggregation='mean',
                     min_on_trials=15, min_off_trials=15, abs_effect=False,
                     current_bins=None, group_by=None, nb_by_metric=None,
                     output_path=None):
    """Small-multiples scatter: effect vs each metric (at one aggregation), one
    panel per metric. The visual companion to build_metric_leaderboard.

    abs_effect=True plots |effect| — the direct test of "does isolation predict
    effect STRENGTH" (regardless of sign), which the signed view hides as spread.

    Grouping (each draws one colour + one trend line + a per-group n/r legend entry
    per group, so you can see whether the relationship holds within a subset):
      - group_by: a categorical column, e.g. 'trial_type'. Takes precedence.
      - current_bins: a list of current_per_second edges (e.g. [0,1000,2000,3000]).
    With neither, points are coloured by raw current (viridis) with one trend line."""
    from matplotlib.lines import Line2D
    y_label = '|effect| (|ON − OFF| %)' if abs_effect else 'effect (ON − OFF %)'
    name_col_pairs = [(name, f"{name}__{aggregation}") for name in metric_names
                      if f"{name}__{aggregation}" in df.columns]
    if not name_col_pairs:
        print("No metric columns to plot.")
        return

    base = df[
        df['effect_size'].notna()
        & (df['n_on'] >= min_on_trials)
        & (df['n_off'] >= min_off_trials)
    ]

    # Decide grouping: an explicit categorical column, or current bins, or none.
    group_col = group_labels = group_color = group_title = None
    if group_by is not None and group_by in base.columns:
        vals = list(pd.unique(base[group_by].dropna()))
        try:
            vals = sorted(vals)
        except Exception:
            pass
        group_col, group_labels, group_title = group_by, vals, group_by
        cmap = plt.get_cmap('tab10', max(len(group_labels), 1))
        group_color = {lab: cmap(i) for i, lab in enumerate(group_labels)}
    elif current_bins is not None and len(current_bins) >= 2:
        edges = sorted(float(e) for e in current_bins)
        group_labels = [f"{edges[i]:g}–{edges[i + 1]:g}" for i in range(len(edges) - 1)]
        base = base.assign(_cbin=pd.cut(base['current_per_second'], bins=edges,
                                        labels=group_labels, include_lowest=True))
        group_col, group_title = '_cbin', 'current bin'
        cmap = plt.get_cmap('viridis', len(group_labels))
        group_color = {lab: cmap(i) for i, lab in enumerate(group_labels)}
    grouped = group_col is not None

    def _panel_y(frame):
        return frame['effect_size'].abs() if abs_effect else frame['effect_size']

    def _draw_trend(ax, xarr, yarr, color):
        good = np.isfinite(xarr) & np.isfinite(yarr)
        if good.sum() >= 2:
            slope, intercept = np.polyfit(xarr[good], yarr[good], 1)
            xl = np.array([xarr[good].min(), xarr[good].max()])
            ax.plot(xl, slope * xl + intercept, color=color, linewidth=1.8, alpha=0.85)

    n = len(name_col_pairs)
    ncols = min(3, n)
    nrows = int(np.ceil(n / ncols))
    # constrained_layout auto-spaces the multi-line subplot titles, the suptitle,
    # and the colorbar so nothing collides (tight_layout can't handle all three).
    fig, axes = plt.subplots(nrows, ncols, figsize=(5.5 * ncols, 4.8 * nrows),
                             squeeze=False, constrained_layout=True)

    cur = base['current_per_second']
    cur_valid = cur[cur.notna()]
    vmin = float(cur_valid.min()) if len(cur_valid) else None
    vmax = float(cur_valid.max()) if len(cur_valid) else None

    scatter_ref = None
    for i, (name, col) in enumerate(name_col_pairs):
        ax = axes[i // ncols][i % ncols]
        sub = base[base[col].notna()]
        if len(sub) == 0:
            ax.set_title(f"{_METRIC_LABELS.get(name, name)}\n(no data)")
            ax.axis('off')
            continue

        if grouped:
            handles = []
            for lab in group_labels:
                subb = sub[sub[group_col] == lab]
                if len(subb) == 0:
                    continue
                yv = _panel_y(subb)
                ax.scatter(subb[col], yv, color=group_color[lab], s=55, alpha=0.85,
                           edgecolors='black', linewidths=0.4)
                _draw_trend(ax, subb[col].to_numpy(dtype=float),
                            yv.to_numpy(dtype=float), group_color[lab])
                bcorr = _correlation(subb[col].to_numpy(), yv.to_numpy())
                lbl = f"{lab}: n={len(subb)}"
                if bcorr:
                    lbl += f", r={bcorr['pearson_r']:.2f}"
                handles.append(Line2D([0], [0], marker='o', color=group_color[lab],
                                      markerfacecolor=group_color[lab],
                                      markeredgecolor='black', label=lbl))
            unmatched = sub[sub[group_col].isna()]
            if len(unmatched):
                ax.scatter(unmatched[col], _panel_y(unmatched), color='lightgray',
                           s=38, alpha=0.6, edgecolors='gray', linewidths=0.3)
            if handles:
                ax.legend(handles=handles, fontsize=7, loc='best', framealpha=0.85,
                          title=group_title)
        else:
            c = sub['current_per_second']
            yv = _panel_y(sub)
            sc = ax.scatter(sub[col], yv, c=c, cmap='viridis',
                            vmin=vmin, vmax=vmax, s=55, alpha=0.85,
                            edgecolors='black', linewidths=0.4)
            if c.notna().any():
                scatter_ref = sc
            _draw_trend(ax, sub[col].to_numpy(dtype=float), yv.to_numpy(dtype=float),
                        'red')

        if not abs_effect:
            ax.axhline(0, color='black', linestyle='--', linewidth=1, alpha=0.5)
        sub_t = _METRIC_LABELS.get(name, name)
        if nb_by_metric and name in nb_by_metric:
            sub_t += f"  (nb={nb_by_metric[name]})"
        if not grouped:
            # Pooled correlation is only meaningful when not grouping (pooling across
            # groups can hide/flip within-group trends).
            corr = _correlation(sub[col].to_numpy(), _panel_y(sub).to_numpy())
            if corr:
                sub_t += f"\nn={corr['n']}  r={corr['pearson_r']:.2f}"
                if corr['pearson_p'] is not None:
                    sub_t += f" (p={corr['pearson_p']:.2g})"
        ax.set_title(sub_t, fontsize=10)
        ax.set_xlabel(col, fontsize=9)
        ax.set_ylabel(y_label, fontsize=9)
        ax.grid(True, alpha=0.3)

    for j in range(n, nrows * ncols):
        axes[j // ncols][j % ncols].axis('off')

    if not grouped and scatter_ref is not None:
        cbar = fig.colorbar(scatter_ref, ax=axes.ravel().tolist(), shrink=0.6,
                            pad=0.02)
        cbar.set_label('current_per_second (µA·Hz)', fontsize=10)

    colour_desc = f'colour = {group_title}' if grouped else 'colour = current'
    fig.suptitle(f"Estim {'|effect|' if abs_effect else 'effect'} vs "
                 f"neighbour-similarity metrics — '{aggregation}' aggregation "
                 f"({colour_desc})", fontsize=13)
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        fig.savefig(output_path, dpi=150, bbox_inches='tight')
        fig.savefig(output_path.rsplit('.', 1)[0] + '.svg', bbox_inches='tight')
        print(f"Saved grid to {output_path}")
    plt.show()


def plot_metric_leaderboard(board, *, output_path=None, title=None):
    """Horizontal bar chart of each metric's correlation with effect: raw Pearson r
    and (where available) the partial r controlling for current. This is the
    'which metric wins' summary."""
    if len(board) == 0:
        print("Empty leaderboard; nothing to plot.")
        return
    board = board.iloc[::-1]  # highest-ranked at top after barh
    labels = board['label'].tolist()
    y = np.arange(len(board))
    height = 0.4

    fig, ax = plt.subplots(figsize=(9, max(3, 0.7 * len(board))))
    ax.barh(y + height / 2, board['pearson_r'].fillna(0), height=height,
            color='#5B8DEF', label='Pearson r (raw)')
    if board['partial_r'].notna().any():
        ax.barh(y - height / 2, board['partial_r'].fillna(0), height=height,
                color='#E8734A', label='partial r | current')
    ax.axvline(0, color='black', linewidth=0.8)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=10)
    ax.set_xlabel('correlation with estim effect', fontsize=11)
    ax.set_title(title or "Which metric best explains estim effect?", fontsize=13)
    ax.legend(fontsize=9)
    ax.grid(True, axis='x', alpha=0.3)
    fig.tight_layout()
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        fig.savefig(output_path, dpi=150, bbox_inches='tight')
        fig.savefig(output_path.rsplit('.', 1)[0] + '.svg', bbox_inches='tight')
        print(f"Saved leaderboard to {output_path}")
    plt.show()


def run_metric_comparison(start_session_id=None, exclude_session_ids=None, *,
                          metric=METRIC_PCT_HYP_VS_DELTA, required_conditions=None,
                          min_on_trials=10, min_off_trials=10,
                          control_for_current=True, abs_effect=False,
                          current_bins=None, n_neighbors=3, exclude_other_estim=True,
                          save_dir=None):
    """End-to-end: build the comparison table, print + plot the leaderboard for
    both aggregations, and draw the per-metric scatter grids. Returns
    (df, {'mean': board_mean, 'worst': board_worst}).

    abs_effect=True relates each metric to |effect| (effect STRENGTH regardless of
    sign) instead of signed effect — the direct test of the isolation hypothesis.
    n_neighbors / exclude_other_estim pick which stored neighbourhood configuration
    to use (see plot_neighbor_sweep to compare across n_neighbors)."""
    print(f"[config] LEADERBOARD  metric={metric}  required_conditions={required_conditions}  "
          f"abs_effect={abs_effect}  min_on/off={min_on_trials}/{min_off_trials}  "
          f"start={start_session_id}  exclude={exclude_session_ids}")
    df, metric_names = build_metric_comparison_table(
        start_session_id=start_session_id, exclude_session_ids=exclude_session_ids,
        metric=metric, required_conditions=required_conditions,
        n_neighbors=n_neighbors, exclude_other_estim=exclude_other_estim)
    if len(df) == 0:
        print("Nothing to compare — run compute_estim_neighbor_scores first.")
        return df, {}

    suffix = (f"_nb{n_neighbors}{'' if exclude_other_estim else '_incl'}"
              f"{'_abs' if abs_effect else ''}")
    y_desc = '|effect|' if abs_effect else 'signed effect'
    boards = {}
    for aggregation in ('mean', 'worst'):
        board = build_metric_leaderboard(
            df, metric_names, aggregation=aggregation,
            min_on_trials=min_on_trials, min_off_trials=min_off_trials,
            control_for_current=control_for_current, abs_effect=abs_effect)
        boards[aggregation] = board
        print(f"\n=== Leaderboard ({aggregation} aggregation, {y_desc}) — "
              f"ranked by |partial r| controlling for current ===")
        cols = ['label', 'n', 'pearson_r', 'pearson_p', 'spearman_r', 'r2',
                'partial_r', 'partial_p']
        with pd.option_context('display.width', 160, 'display.max_columns', None):
            print(board[cols].to_string(index=False))

        if save_dir:
            plot_metric_leaderboard(
                board, title=f"Which metric best explains estim {y_desc}? "
                             f"({aggregation}, metric={metric})",
                output_path=os.path.join(save_dir, f"metric_leaderboard_{aggregation}{suffix}.png"))
            plot_metric_grid(
                df, metric_names, aggregation=aggregation,
                min_on_trials=min_on_trials, min_off_trials=min_off_trials,
                abs_effect=abs_effect, current_bins=current_bins,
                output_path=os.path.join(save_dir, f"metric_grid_{aggregation}{suffix}.png"))

    return df, boards


def plot_leaderboard_grouped(boards_by_group, *, group_title='trial_type',
                             use_partial=True, aggregation='mean', abs_effect=False,
                             output_path=None):
    """Grouped horizontal bar chart: one row per metric, one bar per group (e.g.
    trial_type), so you can read how each metric's link to effect differs across
    groups. Bars show the partial r (controlling for current) by default, else raw
    Pearson r. boards_by_group maps group_label -> leaderboard DataFrame."""
    groups = [g for g in boards_by_group if len(boards_by_group[g])]
    if not groups:
        print("No non-empty boards to plot.")
        return
    key = 'partial_r' if use_partial else 'pearson_r'

    # Metric order taken from the known order, restricted to what's present.
    present = set()
    for g in groups:
        present.update(boards_by_group[g]['metric'].tolist())
    metrics = [m for m in _METRIC_ORDER if m in present]
    metrics += sorted(m for m in present if m not in _METRIC_ORDER)
    labels = [_METRIC_LABELS.get(m, m) for m in metrics]

    y = np.arange(len(metrics))
    ng = len(groups)
    bar_h = 0.8 / ng
    cmap = plt.get_cmap('tab10', max(ng, 1))

    fig, ax = plt.subplots(figsize=(9, max(3.5, 0.9 * len(metrics))))
    for gi, g in enumerate(groups):
        board = boards_by_group[g].set_index('metric')
        vals = [board[key].get(m, np.nan) if m in board.index else np.nan for m in metrics]
        offset = (gi - (ng - 1) / 2) * bar_h
        ax.barh(y + offset, np.nan_to_num(vals), height=bar_h, color=cmap(gi),
                label=str(g))
    ax.axvline(0, color='black', linewidth=0.8)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=10)
    ax.invert_yaxis()  # first metric on top
    r_desc = 'partial r | current' if use_partial else 'Pearson r'
    y_desc = '|effect|' if abs_effect else 'effect'
    ax.set_xlabel(f"correlation with {y_desc}  ({r_desc})", fontsize=11)
    ax.set_title(f"Metric–{y_desc} correlation by {group_title} "
                 f"({aggregation} aggregation)", fontsize=13)
    ax.legend(fontsize=9, title=group_title)
    ax.grid(True, axis='x', alpha=0.3)
    fig.tight_layout()
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        fig.savefig(output_path, dpi=150, bbox_inches='tight')
        fig.savefig(output_path.rsplit('.', 1)[0] + '.svg', bbox_inches='tight')
        print(f"Saved grouped leaderboard to {output_path}")
    plt.show()


def run_metric_comparison_by_trial_type(trial_types=None, start_session_id=None,
                                        exclude_session_ids=None, *,
                                        metric=METRIC_PCT_HYP_VS_DELTA,
                                        base_required_conditions=None,
                                        min_on_trials=10, min_off_trials=10,
                                        control_for_current=True, abs_effect=False,
                                        n_neighbors=3, exclude_other_estim=True,
                                        save_dir=None):
    """Leaderboard + scatter grid split by trial_type. Builds one long table (effect
    per trial_type, shared metric scores), then per aggregation: a per-trial-type
    leaderboard (printed), a grouped-bar leaderboard, and a grid with one trend line
    per trial_type. Returns (long_df, {aggregation: {trial_type: board}})."""
    if trial_types is None:
        trial_types = _discover_trial_types(start_session_id, exclude_session_ids)
    print(f"[config] LEADERBOARD split across trial types: {trial_types}  "
          f"metric={metric}  abs_effect={abs_effect}  n_neighbors={n_neighbors}")

    long_df, metric_names = build_metric_comparison_long(
        trial_types, start_session_id=start_session_id,
        exclude_session_ids=exclude_session_ids, metric=metric,
        base_required_conditions=base_required_conditions,
        n_neighbors=n_neighbors, exclude_other_estim=exclude_other_estim)
    if len(long_df) == 0:
        print("Nothing to compare — run compute_estim_neighbor_scores first.")
        return long_df, {}

    present_types = [tt for tt in trial_types if (long_df['trial_type'] == tt).any()]
    suffix = f"_nb{n_neighbors}{'_abs' if abs_effect else ''}"
    out = {}
    for aggregation in ('mean', 'worst'):
        boards = {}
        for tt in present_types:
            sub = long_df[long_df['trial_type'] == tt]
            board = build_metric_leaderboard(
                sub, metric_names, aggregation=aggregation,
                min_on_trials=min_on_trials, min_off_trials=min_off_trials,
                control_for_current=control_for_current, abs_effect=abs_effect)
            boards[tt] = board
            print(f"\n=== Leaderboard [{tt}] ({aggregation} agg, "
                  f"{'|effect|' if abs_effect else 'signed'}) ===")
            cols = ['label', 'n', 'pearson_r', 'pearson_p', 'r2', 'partial_r', 'partial_p']
            with pd.option_context('display.width', 160, 'display.max_columns', None):
                print(board[cols].to_string(index=False))
        out[aggregation] = boards
        if save_dir:
            plot_leaderboard_grouped(
                boards, group_title='trial_type', use_partial=control_for_current,
                aggregation=aggregation, abs_effect=abs_effect,
                output_path=os.path.join(save_dir, f"leaderboard_by_trialtype_{aggregation}{suffix}.png"))
            plot_metric_grid(
                long_df, metric_names, aggregation=aggregation,
                min_on_trials=min_on_trials, min_off_trials=min_off_trials,
                abs_effect=abs_effect, group_by='trial_type',
                output_path=os.path.join(save_dir, f"metric_grid_by_trialtype_{aggregation}{suffix}.png"))
    return long_df, out


# ---------------------------------------------------------------------------
# "Best neighbourhood per metric" comparison
#
# WARNING: picking each metric's best n_neighbors from the same data you then report
# is a winner's-curse — maximising over n_neighbors inflates the correlations (you'd
# get non-zero "best" values even from noise). Treat the per-metric-best leaderboard
# as an EXPLORATORY UPPER BOUND. The single shared-best n_neighbors (best on average
# across metrics) is the honest, non-cherry-picked number.
# ---------------------------------------------------------------------------

def _best_nb_per_metric(sweep, select_by='partial_r'):
    """{metric: n_neighbors that maximises |select_by|} from a sweep dict.
    Falls back to pearson_r when the chosen key is missing for a metric."""
    best = {}
    for name, entries in sweep.items():
        valid = [e for e in entries if e.get(select_by) is not None]
        if not valid:
            valid = [e for e in entries if e.get('pearson_r') is not None]
            key = 'pearson_r'
        else:
            key = select_by
        if not valid:
            continue
        best[name] = max(valid, key=lambda e: abs(e[key]))['n_neighbors']
    return best


def _best_shared_nb(sweep, select_by='partial_r'):
    """The single n_neighbors maximising the mean |select_by| across all metrics —
    the honest 'best condition' that isn't cherry-picked per metric."""
    nbs = sorted({e['n_neighbors'] for entries in sweep.values() for e in entries})
    best_nb, best_score = None, -1.0
    for nb in nbs:
        vals = []
        for entries in sweep.values():
            e = next((x for x in entries if x['n_neighbors'] == nb), None)
            if e is None:
                continue
            v = e.get(select_by)
            if v is None:
                v = e.get('pearson_r')
            if v is not None:
                vals.append(abs(v))
        score = float(np.mean(vals)) if vals else -1.0
        if score > best_score:
            best_nb, best_score = nb, score
    return best_nb, best_score


def _join_scores_per_metric_nb(df, metric_to_nb, aggregation, *, exclude_other_estim,
                               session_ids):
    """Add each metric's ``<metric>__<aggregation>`` column sourced from that metric's
    own n_neighbors. Fetches each needed n_neighbors once."""
    by_nb = {}
    for nb in sorted(set(metric_to_nb.values())):
        by_nb[nb] = _fetch_neighbor_scores(
            session_ids, n_neighbors=nb, exclude_other_estim=exclude_other_estim)[0]
    for name, nb in metric_to_nb.items():
        scores = by_nb[nb]
        col = f"{name}__{aggregation}"
        df[col] = [
            (scores.get((s, int(spec)), {}).get(name, {}) or {}).get(aggregation)
            for s, spec in zip(df['session_id'], df['estim_spec_id'])]


def run_best_nb_comparison(start_session_id=None, exclude_session_ids=None, *,
                           metric=METRIC_PCT_HYP_VS_DELTA, required_conditions=None,
                           min_on_trials=10, min_off_trials=10,
                           control_for_current=True, abs_effect=False,
                           exclude_other_estim=True, select_by='partial_r',
                           save_dir=None):
    """Leaderboard + grid where each metric uses its OWN best n_neighbors (chosen by
    |select_by|, 'partial_r' or 'pearson_r', from the sweep). Also reports the single
    shared-best n_neighbors as the honest alternative. Returns
    {aggregation: (board, best_nb_per_metric, shared_nb)}."""
    df_effect = _effect_and_current_table(
        start_session_id=start_session_id, exclude_session_ids=exclude_session_ids,
        metric=metric, required_conditions=required_conditions)
    if len(df_effect) == 0:
        print("Nothing to compare — run compute_estim_neighbor_scores first.")
        return {}
    session_ids = sorted(df_effect['session_id'].unique().tolist())
    suffix = f"_bestnb{'_abs' if abs_effect else ''}"

    out = {}
    for aggregation in ('mean', 'worst'):
        sweep, nb_values = build_neighbor_sweep(
            start_session_id=start_session_id, exclude_session_ids=exclude_session_ids,
            metric=metric, required_conditions=required_conditions,
            aggregation=aggregation, abs_effect=abs_effect,
            exclude_other_estim=exclude_other_estim,
            control_for_current=control_for_current, min_on_trials=min_on_trials,
            min_off_trials=min_off_trials)
        if not sweep:
            continue

        best = _best_nb_per_metric(sweep, select_by=select_by)
        shared_nb, shared_score = _best_shared_nb(sweep, select_by=select_by)

        df = df_effect.copy()
        _join_scores_per_metric_nb(df, best, aggregation,
                                   exclude_other_estim=exclude_other_estim,
                                   session_ids=session_ids)
        metric_names = list(best.keys())
        board = build_metric_leaderboard(
            df, metric_names, aggregation=aggregation, min_on_trials=min_on_trials,
            min_off_trials=min_off_trials, control_for_current=control_for_current,
            abs_effect=abs_effect)
        board['best_nb'] = board['metric'].map(best)

        print(f"\n=== BEST-nb-per-metric leaderboard ({aggregation} agg, "
              f"{'|effect|' if abs_effect else 'signed'}; selected by |{select_by}|) ===")
        print("    *** EXPLORATORY: per-metric nb selection inflates these r's "
              "(winner's curse) ***")
        print(f"    Honest single shared best nb = {shared_nb} "
              f"(mean |{select_by}| across metrics = {shared_score:.3f}) — "
              f"use this in main_metric_comparison for an unbiased leaderboard.")
        cols = ['label', 'best_nb', 'n', 'pearson_r', 'pearson_p', 'r2',
                'partial_r', 'partial_p']
        with pd.option_context('display.width', 170, 'display.max_columns', None):
            print(board[cols].to_string(index=False))

        if save_dir:
            plot_metric_grid(
                df, metric_names, aggregation=aggregation,
                min_on_trials=min_on_trials, min_off_trials=min_off_trials,
                abs_effect=abs_effect, nb_by_metric=best,
                output_path=os.path.join(save_dir, f"metric_grid_{aggregation}{suffix}.png"))
        out[aggregation] = (board, best, shared_nb)
    return out


def main_best_nb_comparison():
    """Leaderboard/grid using each metric's best n_neighbors (exploratory), plus the
    honest single shared-best n_neighbors. Uses the shared COMPARISON_* config."""
    run_best_nb_comparison(
        start_session_id=COMPARISON_START_SESSION_ID,
        exclude_session_ids=COMPARISON_EXCLUDE_SESSION_IDS,
        metric=COMPARISON_METRIC,
        required_conditions=COMPARISON_REQUIRED_CONDITIONS or None,
        min_on_trials=COMPARISON_MIN_ON_TRIALS,
        min_off_trials=COMPARISON_MIN_OFF_TRIALS,
        control_for_current=True,
        abs_effect=COMPARISON_ABS_EFFECT,
        exclude_other_estim=True,
        select_by='partial_r',   # or 'pearson_r'
        save_dir=COMPARISON_SAVE_DIR,
    )


# ---------------------------------------------------------------------------
# Neighbourhood-size sweep: how does each metric's link to effect change with
# n_neighbors?
# ---------------------------------------------------------------------------

def build_neighbor_sweep(start_session_id=None, exclude_session_ids=None, *,
                         metric=METRIC_PCT_HYP_VS_DELTA, required_conditions=None,
                         behavioral_conditions=BEHAVIORAL_KEYS,
                         aggregation='mean', abs_effect=False,
                         exclude_other_estim=True, control_for_current=True,
                         covariate='current_per_second',
                         min_on_trials=10, min_off_trials=10,
                         n_neighbors_values=None):
    """For each stored n_neighbors, correlate every metric (at one aggregation) with
    the effect. The effect + current table is built ONCE and re-joined per
    n_neighbors, so this is cheap.

    covariate: which column to partial out when control_for_current is True —
    'current_per_second' (dose) or 'n_active_channels' (the direct source of the
    'worst'=min selection bias).

    Returns {metric_name: [{'n_neighbors', 'n', 'pearson_r', 'partial_r'}, ...]}
    (sorted by n_neighbors) plus the sorted list of n_neighbors values used."""
    df_effect = _effect_and_current_table(
        start_session_id=start_session_id, exclude_session_ids=exclude_session_ids,
        metric=metric, required_conditions=required_conditions,
        behavioral_conditions=behavioral_conditions)
    if len(df_effect) == 0:
        return {}, []

    if n_neighbors_values is None:
        n_neighbors_values = _available_n_neighbors(exclude_other_estim)
    if not n_neighbors_values:
        print("No n_neighbors values stored for this exclude_other_estim setting.")
        return {}, []

    session_ids = sorted(df_effect['session_id'].unique().tolist())
    sweep = {}
    for nb in n_neighbors_values:
        scores, metric_names = _fetch_neighbor_scores(
            session_ids, n_neighbors=nb, exclude_other_estim=exclude_other_estim)
        df = df_effect.copy()
        _join_neighbor_scores(df, scores, metric_names, aggregations=(aggregation,))
        base = df[
            df['effect_size'].notna()
            & (df['n_on'] >= min_on_trials)
            & (df['n_off'] >= min_off_trials)
        ]
        for name in metric_names:
            col = f"{name}__{aggregation}"
            sub = base[base[col].notna()]
            y = sub['effect_size'].abs() if abs_effect else sub['effect_size']
            corr = _correlation(sub[col].to_numpy(), y.to_numpy())
            entry = {'n_neighbors': nb,
                     'n': corr['n'] if corr else int(len(sub)),
                     'pearson_r': corr['pearson_r'] if corr else None,
                     'partial_r': None}
            if control_for_current and covariate in df.columns:
                pc = _partial_correlation(sub[col].to_numpy(), y.to_numpy(),
                                          pd.to_numeric(sub[covariate], errors='coerce').to_numpy())
                if pc:
                    entry['partial_r'] = pc['r']
            sweep.setdefault(name, []).append(entry)

    for name in sweep:
        sweep[name].sort(key=lambda e: e['n_neighbors'])
    return sweep, sorted(n_neighbors_values)


def plot_neighbor_sweep(sweep, *, use_partial=False, aggregation='mean',
                        abs_effect=False, exclude_other_estim=True, metric='',
                        covariate='current_per_second', tag='', output_path=None):
    """Line plot: x = n_neighbors, y = each metric's correlation with the effect
    (raw Pearson r, or partial r controlling for current when use_partial=True),
    one line per metric. Shows whether a metric's signal strengthens or washes out
    as the neighbourhood grows."""
    if not sweep:
        print("Empty sweep; nothing to plot.")
        return
    ordered = [m for m in _METRIC_ORDER if m in sweep]
    ordered += sorted(m for m in sweep if m not in _METRIC_ORDER)
    key = 'partial_r' if use_partial else 'pearson_r'

    cmap = plt.get_cmap('tab10', max(len(ordered), 1))
    fig, ax = plt.subplots(figsize=(9, 6))
    for i, name in enumerate(ordered):
        entries = sweep[name]
        xs = [e['n_neighbors'] for e in entries if e[key] is not None]
        ys = [e[key] for e in entries if e[key] is not None]
        if not xs:
            continue
        ax.plot(xs, ys, marker='o', color=cmap(i),
                label=_METRIC_LABELS.get(name, name))
    ax.axhline(0, color='black', linestyle='--', linewidth=1, alpha=0.5)
    ax.set_xlabel('n_neighbors (physical neighbours averaged per estim channel)',
                  fontsize=11)
    r_desc = f'partial r | {covariate}' if use_partial else 'Pearson r'
    y_desc = '|effect|' if abs_effect else 'effect'
    ax.set_ylabel(f"correlation with {y_desc}  ({r_desc})", fontsize=11)
    ax.set_title(f"Metric–{y_desc} correlation vs neighbourhood size "
                 f"{('[' + tag + '] ') if tag else ''}"
                 f"({aggregation} agg, exclude_other_estim={exclude_other_estim}"
                 f"{', metric=' + metric if metric else ''})", fontsize=12)
    ax.legend(fontsize=8, loc='best', framealpha=0.9)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        fig.savefig(output_path, dpi=150, bbox_inches='tight')
        fig.savefig(output_path.rsplit('.', 1)[0] + '.svg', bbox_inches='tight')
        print(f"Saved neighbour sweep to {output_path}")
    plt.show()


def run_neighbor_sweep(start_session_id=None, exclude_session_ids=None, *,
                       metric=METRIC_PCT_HYP_VS_DELTA, required_conditions=None,
                       abs_effect=False, exclude_other_estim=True,
                       control_for_current=True, covariate='current_per_second',
                       min_on_trials=10, min_off_trials=10, tag='', save_dir=None):
    """Build and plot the neighbourhood-size sweep for both aggregations, printing
    raw r AND the partial r controlling for `covariate` ('current_per_second' or
    'n_active_channels'). tag labels the run (e.g. a trial_type) in titles/filenames.
    Returns {aggregation: sweep_dict}."""
    print(f"[config] SWEEP{(' [' + tag + ']') if tag else ''}  metric={metric}  "
          f"required_conditions={required_conditions}  abs_effect={abs_effect}  "
          f"min_on/off={min_on_trials}/{min_off_trials}  start={start_session_id}  "
          f"exclude={exclude_session_ids}")
    tag_slug = ('_' + _slug(tag)) if tag else ''
    suffix = (f"{tag_slug}_{'incl' if not exclude_other_estim else 'excl'}"
              f"{'_abs' if abs_effect else ''}"
              f"{'_ctrlN' if covariate == 'n_active_channels' else ''}")
    out = {}
    for aggregation in ('mean', 'worst'):
        sweep, nb_values = build_neighbor_sweep(
            start_session_id=start_session_id, exclude_session_ids=exclude_session_ids,
            metric=metric, required_conditions=required_conditions,
            aggregation=aggregation, abs_effect=abs_effect,
            exclude_other_estim=exclude_other_estim,
            control_for_current=control_for_current, covariate=covariate,
            min_on_trials=min_on_trials, min_off_trials=min_off_trials)
        out[aggregation] = sweep
        if not sweep:
            continue
        print(f"\n=== Neighbour sweep{(' [' + tag + ']') if tag else ''} "
              f"({aggregation} aggregation, "
              f"{'|effect|' if abs_effect else 'effect'}) over n_neighbors={nb_values} "
              f"[cell = raw r / partial r | {covariate}] ===")
        for name in ([m for m in _METRIC_ORDER if m in sweep]
                     + sorted(m for m in sweep if m not in _METRIC_ORDER)):
            def _cell(e):
                raw = f"{e['pearson_r']:+.2f}" if e['pearson_r'] is not None else "  na"
                par = f"{e['partial_r']:+.2f}" if e['partial_r'] is not None else "  na"
                return f"nb{e['n_neighbors']}: {raw}/{par}"
            print(f"  {_METRIC_LABELS.get(name, name):28s} "
                  + "  ".join(_cell(e) for e in sweep[name]))
        if save_dir:
            plot_neighbor_sweep(
                sweep, use_partial=False, aggregation=aggregation,
                abs_effect=abs_effect, exclude_other_estim=exclude_other_estim,
                metric=metric, tag=tag,
                output_path=os.path.join(save_dir, f"neighbor_sweep_{aggregation}{suffix}.png"))
            if control_for_current:
                plot_neighbor_sweep(
                    sweep, use_partial=True, aggregation=aggregation,
                    abs_effect=abs_effect, exclude_other_estim=exclude_other_estim,
                    metric=metric, covariate=covariate, tag=tag,
                    output_path=os.path.join(save_dir, f"neighbor_sweep_{aggregation}{suffix}_partial.png"))
    return out


def run_neighbor_sweep_by_trial_type(trial_types=None, start_session_id=None,
                                     exclude_session_ids=None, *,
                                     metric=METRIC_PCT_HYP_VS_DELTA,
                                     base_required_conditions=None, abs_effect=False,
                                     exclude_other_estim=True, control_for_current=True,
                                     covariate='current_per_second',
                                     min_on_trials=10, min_off_trials=10, save_dir=None):
    """Run the neighbourhood-size sweep separately for each trial_type (one set of
    figures/printouts per type). trial_types=None auto-discovers them."""
    if trial_types is None:
        trial_types = _discover_trial_types(start_session_id, exclude_session_ids)
    print(f"Neighbour sweep split across trial types: {trial_types}")
    out = {}
    for tt in trial_types:
        out[tt] = run_neighbor_sweep(
            start_session_id=start_session_id, exclude_session_ids=exclude_session_ids,
            metric=metric, required_conditions=_rc_for_trial_type(base_required_conditions, tt),
            abs_effect=abs_effect, exclude_other_estim=exclude_other_estim,
            control_for_current=control_for_current, covariate=covariate,
            min_on_trials=min_on_trials, min_off_trials=min_off_trials,
            tag=str(tt), save_dir=save_dir)
    return out


def main_neighbor_sweep():
    """Show how each metric's correlation with the estim effect changes with
    neighbourhood size (n_neighbors). Requires compute_estim_neighbor_scores to have
    been run with a multi-value n_neighbors_list first.

    Uses the shared COMPARISON_* config so it can never drift from
    main_metric_comparison."""
    # Covariate to partial out: 'current_per_second' (dose) or 'n_active_channels'
    # (the direct source of the 'worst'=min selection bias). Try both — if the
    # top-20 worst signal survives BOTH, it's not just a channel-count artefact.
    covariate = 'current_per_second'

    if COMPARISON_TRIAL_TYPES is not None:
        # One sweep (both aggregations) per trial type.
        run_neighbor_sweep_by_trial_type(
            trial_types=(COMPARISON_TRIAL_TYPES or None),  # [] -> auto-discover
            start_session_id=COMPARISON_START_SESSION_ID,
            exclude_session_ids=COMPARISON_EXCLUDE_SESSION_IDS,
            metric=COMPARISON_METRIC,
            base_required_conditions=COMPARISON_REQUIRED_CONDITIONS,
            abs_effect=COMPARISON_ABS_EFFECT,
            exclude_other_estim=True,
            control_for_current=True,
            covariate=covariate,
            min_on_trials=COMPARISON_MIN_ON_TRIALS,
            min_off_trials=COMPARISON_MIN_OFF_TRIALS,
            save_dir=COMPARISON_SAVE_DIR,
        )
        return

    run_neighbor_sweep(
        start_session_id=COMPARISON_START_SESSION_ID,
        exclude_session_ids=COMPARISON_EXCLUDE_SESSION_IDS,
        metric=COMPARISON_METRIC,
        required_conditions=COMPARISON_REQUIRED_CONDITIONS or None,
        abs_effect=COMPARISON_ABS_EFFECT,
        exclude_other_estim=True,      # flip to False if you also swept inclusion
        control_for_current=True,
        covariate=covariate,
        min_on_trials=COMPARISON_MIN_ON_TRIALS,
        min_off_trials=COMPARISON_MIN_OFF_TRIALS,
        save_dir=COMPARISON_SAVE_DIR,
    )


def main_metric_comparison():
    """Compare all neighbour-similarity metrics against the estim effect and rank
    them. Requires compute_estim_neighbor_scores.run_for_sessions() to have populated
    EStimNeighborScores first.

    Uses the shared COMPARISON_* config so it can never drift from
    main_neighbor_sweep (which is what makes the leaderboard and sweep agree at the
    same n_neighbors)."""
    # Optional current binning: set to a list of current_per_second edges to colour
    # points by dose bin and draw one trend line per bin (per-bin n/r in legend), so
    # you can see whether the relationship holds within a dose level. None = colour
    # by raw current with a single trend line.
    #   e.g. current_bins = [0, 1000, 2000, 3000, 5000]
    current_bins = None

    # Which stored neighbourhood configuration to use for the leaderboard/grid.
    # (compute_estim_neighbor_scores stores several n_neighbors — use
    # main_neighbor_sweep / run_neighbor_sweep to compare across them.)
    n_neighbors = 3
    exclude_other_estim = True

    if COMPARISON_TRIAL_TYPES is not None:
        # Split the leaderboard + grid by trial_type (grouped bars + a trend line per
        # trial type in each grid panel).
        run_metric_comparison_by_trial_type(
            trial_types=(COMPARISON_TRIAL_TYPES or None),  # [] -> auto-discover
            start_session_id=COMPARISON_START_SESSION_ID,
            exclude_session_ids=COMPARISON_EXCLUDE_SESSION_IDS,
            metric=COMPARISON_METRIC,
            base_required_conditions=COMPARISON_REQUIRED_CONDITIONS,
            min_on_trials=COMPARISON_MIN_ON_TRIALS,
            min_off_trials=COMPARISON_MIN_OFF_TRIALS,
            control_for_current=True,
            abs_effect=COMPARISON_ABS_EFFECT,
            n_neighbors=n_neighbors,
            exclude_other_estim=exclude_other_estim,
            save_dir=COMPARISON_SAVE_DIR,
        )
        return

    run_metric_comparison(
        start_session_id=COMPARISON_START_SESSION_ID,
        exclude_session_ids=COMPARISON_EXCLUDE_SESSION_IDS,
        metric=COMPARISON_METRIC,
        required_conditions=COMPARISON_REQUIRED_CONDITIONS or None,
        min_on_trials=COMPARISON_MIN_ON_TRIALS,
        min_off_trials=COMPARISON_MIN_OFF_TRIALS,
        control_for_current=True,
        abs_effect=COMPARISON_ABS_EFFECT,
        current_bins=current_bins,
        n_neighbors=n_neighbors,
        exclude_other_estim=exclude_other_estim,
        save_dir=COMPARISON_SAVE_DIR,
    )


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
        'trial_type': 'Hypothesized Shape',
    }

    # Session selection (same convention as max_estim_per_experiment):
    #   start_session_id    -> e.g. "260402_0" to start from the first variant
    #                          experiment; None = all scored sessions.
    #   exclude_session_ids -> e.g. ["260421_0", "260410_0"].
    start_session_id = "260402_0"
    exclude_session_ids = ["260421_0", "260410_0"]

    save_dir = "/home/connorlab/Documents/plots/across_experiments/"

    # Which isolation metric to relate to effect:
    #   'min'     -> estim_min_isolation_um      (manual-cluster, worst channel)
    #   'mean'    -> estim_mean_isolation_um     (manual-cluster, average)
    #   'pc_max'  -> estim_max_pc_neighbor_dist  (clustering-free, worst channel;
    #                                             HIGHER = worse / more boundary-like)
    #   'pc_mean' -> estim_mean_pc_neighbor_dist (clustering-free, average)
    # The pc_* columns require compute_estim_pc_neighbor_scores.main() to have
    # been run first.
    isolation_metric = 'pc_mean'

    # Plot 1: raw isolation/distance vs effect.
    plot_isolation_vs_effect(
        start_session_id=start_session_id,
        exclude_session_ids=exclude_session_ids,
        metric=metric,
        isolation_metric=isolation_metric,
        required_conditions=required_conditions or None,
        min_on_trials=10,
        min_off_trials=10,
        abs_effect=False,            # True -> relate isolation to effect MAGNITUDE
        color_by_session=True,
        output_path=os.path.join(save_dir, f"isolation_vs_effect_{isolation_metric}.png"),
    )

    # Plot 2: combined metric — stimulation power combined with isolation, split
    # by polarity (anodic vs cathodic). combine_op='auto' divides by the
    # isolation columns (higher=better) and multiplies by the PC-neighbor columns
    # (higher=worse), so a LARGE x always means "lots of current where it
    # shouldn't be". NOTE: don't pin polarity in required_conditions here, or one
    # of the two series will be empty.
    plot_power_over_isolation_vs_effect(
        start_session_id=start_session_id,
        exclude_session_ids=exclude_session_ids,
        metric=metric,
        isolation_metric=isolation_metric,
        required_conditions=required_conditions or None,
        min_on_trials=10,
        min_off_trials=10,
        require_positive_isolation=False,  # (divide path only) drop isolation <= 0
        combine_op='auto',
        abs_effect=False,
        output_path=os.path.join(save_dir, f"power_x_isolation_vs_effect_{isolation_metric}.png"),
    )


if __name__ == '__main__':
    # Running this file compares all neighbour-similarity metrics against the estim
    # effect and ranks them (needs compute_estim_neighbor_scores to have run first).
    #   - main_neighbor_sweep()     -> how each metric's link to effect changes with
    #                                  neighbourhood size (n_neighbors)
    #   - main_best_nb_comparison() -> leaderboard with each metric at its own best
    #                                  n_neighbors (exploratory) + the honest shared nb
    #   - main()                    -> legacy single-isolation-metric plots
    main_metric_comparison()
