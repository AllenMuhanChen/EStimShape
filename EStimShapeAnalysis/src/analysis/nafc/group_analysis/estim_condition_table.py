"""
One flat table of every EStimEffects condition, with everything you might want to
filter / group / compare on as its own column — the data layer behind
estim_condition_explorer_gui (and usable from scripts).

EStimEffects rows are keyed by a JSON condition dict that (since conditions were
keyed by estim_spec_id) only holds the behavioural conditions + estim_spec_id. This
expands that dict into columns and joins on, per (session, estim spec):
  - estim parameters from EStimParameters over the active channels (a1 > 0):
    num_channels plus every parameter column (waveform, pulse train incl.
    post_trigger_delay / refractory period, amp settle, charge recovery) — see
    SPEC_PARAM_COLUMNS. Uniform across a spec's active channels under the current
    paradigm; MIN is taken, and a1 is the MAX
  - current spread (optional, slower): current_per_second, the correlation
    half-distance and their ratio, computed exactly as in
    plot_current_spread_vs_tuning / avg_estim_per_experiment
  - session-level metrics from EStimShapeSessionData (lineage_score,
    avg_distance_scaled_correlation), if present
Keys already present in a row's condition dict (older rows) are kept as stored.

summarize_groups() reproduces average_estim_groups_by_condition's statistic for any
grouping: per group, the mean of per-session mean effects ± SEM across sessions,
and a p-value against the grand null built the same way from the stored
EStimPermutationTests null distributions (mean over a session's conditions, then
over sessions).
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parents[3]))

from clat.util.connection import Connection
from src.analysis.nafc.group_analysis.analyze_estim_by_condition import (
    METRIC_PCT_HYPOTHESIZED, METRIC_PCT_HYP_VS_DELTA)

METRICS = (METRIC_PCT_HYPOTHESIZED, METRIC_PCT_HYP_VS_DELTA)

# Core (non-condition) columns of the table.
EFFECT_COL = 'effect_size'
ON_COL, OFF_COL = 'on_pct', 'off_pct'
N_ON_COL, N_OFF_COL = 'n_on', 'n_off'
CORE_COLUMNS = ('session_id', 'conditions', EFFECT_COL, ON_COL, OFF_COL,
                N_ON_COL, N_OFF_COL)

# every EStimParameters column except a1 (taken as MAX) and the keys / channel
SPEC_PARAM_COLUMNS = ('shape', 'polarity', 'd1', 'd2', 'dp', 'a2',
                      'pulse_repetition', 'num_repetitions', 'pulse_train_period',
                      'post_stim_refractory_period', 'trigger_edge_or_level',
                      'post_trigger_delay',
                      'enable_amp_settle', 'pre_stim_amp_settle', 'post_stim_amp_settle',
                      'maintain_amp_settle_during_pulse_train',
                      'enable_charge_recovery', 'post_stim_charge_recovery_on',
                      'post_stim_charge_recovery_off')
SPREAD_COLUMNS = ('current_per_second', 'corr_half_distance_um', 'ratio')
SESSION_METRIC_COLUMNS = ('lineage_score', 'avg_distance_scaled_correlation')


def list_algorithm_labels():
    conn = Connection("allen_data_repository")
    conn.execute("SELECT DISTINCT algorithm_label FROM EStimEffects ORDER BY algorithm_label")
    return [r[0] for r in conn.fetch_all()]


def _fetch_effect_rows(algorithm_label, metric):
    conn = Connection("allen_data_repository")
    conn.execute(
        "SELECT session_id, conditions, effect_size, estim_on_pct_hypothesized, "
        "estim_off_pct_hypothesized, estim_on_n_trials, estim_off_n_trials "
        "FROM EStimEffects WHERE effect_size IS NOT NULL "
        "AND algorithm_label = %s AND metric = %s", (algorithm_label, metric))
    return pd.DataFrame(conn.fetch_all(), columns=list(CORE_COLUMNS))


def _expand_conditions(df):
    """One column per key of the condition JSON (missing keys -> NaN)."""
    conds = pd.DataFrame([json.loads(c) for c in df['conditions']], index=df.index)
    for col in conds.columns:
        if col in df.columns:
            raise ValueError(f"condition key {col!r} clashes with a core column")
    out = pd.concat([df, conds], axis=1)
    if 'estim_spec_id' in out.columns:
        out['estim_spec_id'] = pd.to_numeric(out['estim_spec_id'], errors='coerce')
    return out


def _fetch_spec_params(session_ids):
    """DataFrame keyed (session_id, estim_spec_id) of active-channel estim params."""
    if not session_ids:
        return pd.DataFrame(columns=['session_id', 'estim_spec_id'])
    conn = Connection("allen_data_repository")
    cols = ", ".join(f"MIN({c}) AS {c}" for c in SPEC_PARAM_COLUMNS)
    placeholders = ', '.join(['%s'] * len(session_ids))
    conn.execute(
        f"SELECT session_id, estim_spec_id, COUNT(DISTINCT channel) AS num_channels, "
        f"MAX(a1) AS a1, {cols} FROM EStimParameters "
        f"WHERE a1 > 0 AND session_id IN ({placeholders}) "
        "GROUP BY session_id, estim_spec_id", tuple(session_ids))
    names = ['session_id', 'estim_spec_id', 'num_channels', 'a1', *SPEC_PARAM_COLUMNS]
    out = pd.DataFrame(conn.fetch_all(), columns=names)
    out['estim_spec_id'] = pd.to_numeric(out['estim_spec_id'])
    return out


def _fetch_spread(session_ids):
    """DataFrame keyed (session_id, estim_spec_id) with current_per_second, the
    correlation half-distance and their ratio. Sessions that fail are skipped."""
    # heavy modules (probe geometry, tuning metrics): import only when asked for
    from src.analysis.nafc.group_analysis.analyze_estim_isolation_effect import (
        _fetch_current_per_second)
    from src.analysis.nafc.group_analysis.plot_current_spread_vs_tuning import (
        HALFDIST_COL, compute_session_half_distance)
    rows = []
    for sid in session_ids:
        try:
            half_dist = compute_session_half_distance(sid)
            cps = _fetch_current_per_second([(sid, spec) for spec in half_dist])
        except Exception as exc:
            print(f"  {sid}: current spread failed ({type(exc).__name__}: {exc}); skipped")
            continue
        for spec, hd in half_dist.items():
            c = cps.get((sid, int(spec)))
            ok = hd is not None and c is not None and hd > 0
            rows.append({'session_id': sid, 'estim_spec_id': int(spec),
                         'current_per_second': c, HALFDIST_COL: hd,
                         'ratio': float(c) / float(hd) if ok else None})
    return pd.DataFrame(rows, columns=['session_id', 'estim_spec_id', *SPREAD_COLUMNS])


def _fetch_session_metrics():
    conn = Connection("allen_data_repository")
    try:
        conn.execute(f"SELECT session_id, {', '.join(SESSION_METRIC_COLUMNS)} "
                     "FROM EStimShapeSessionData")
    except Exception as exc:
        print(f"  session metrics unavailable ({type(exc).__name__}: {exc})")
        return pd.DataFrame(columns=['session_id'])
    return pd.DataFrame(conn.fetch_all(), columns=['session_id', *SESSION_METRIC_COLUMNS])


def _join_fill(df, extra, keys):
    """Left-join extra on keys; columns already in df keep their stored values and
    only have their gaps filled from extra."""
    if extra is None or len(extra) == 0:
        return df
    merged = df.merge(extra, on=keys, how='left', suffixes=('', '__new'))
    for col in [c for c in merged.columns if c.endswith('__new')]:
        base = col[:-len('__new')]
        merged[base] = merged[base].where(merged[base].notna(), merged[col])
        merged = merged.drop(columns=col)
    return merged


def load_condition_table(algorithm_label='none', metric=METRIC_PCT_HYPOTHESIZED, *,
                         with_spread=True, session_ids=None):
    """Every EStimEffects condition for (algorithm_label, metric) as a DataFrame,
    one row per condition, with the condition keys, estim parameters, current
    spread (if with_spread) and session metrics as columns. session_ids optionally
    limits the sessions loaded."""
    df = _fetch_effect_rows(algorithm_label, metric)
    if session_ids is not None:
        df = df[df['session_id'].isin(set(session_ids))]
    df = df.reset_index(drop=True)
    print(f"EStimEffects ({algorithm_label!r}, {metric!r}): {len(df)} conditions in "
          f"{df['session_id'].nunique()} sessions")
    if len(df) == 0:
        return df
    for col in (EFFECT_COL, ON_COL, OFF_COL, N_ON_COL, N_OFF_COL):
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df = _expand_conditions(df)
    sessions = sorted(df['session_id'].unique().tolist())
    if 'estim_spec_id' in df.columns:
        df = _join_fill(df, _fetch_spec_params(sessions), ['session_id', 'estim_spec_id'])
        if with_spread:
            print("Computing current spread (half-distance) per session…")
            df = _join_fill(df, _fetch_spread(sessions), ['session_id', 'estim_spec_id'])
    df = _join_fill(df, _fetch_session_metrics(), ['session_id'])
    return df


def load_permutation_nulls(algorithm_label='none', metric=METRIC_PCT_HYPOTHESIZED,
                           session_ids=None):
    """{(session_id, conditions JSON): null distribution array} from
    EStimPermutationTests for this algorithm_label / metric."""
    conn = Connection("allen_data_repository")
    query = ("SELECT session_id, conditions, null_distribution FROM EStimPermutationTests "
             "WHERE algorithm_label = %s AND metric = %s AND null_distribution IS NOT NULL")
    params = [algorithm_label, metric]
    if session_ids:
        query += f" AND session_id IN ({', '.join(['%s'] * len(session_ids))})"
        params += list(session_ids)
    conn.execute(query, tuple(params))
    return {(sid, cond): np.asarray(json.loads(null), dtype=float)
            for sid, cond, null in conn.fetch_all() if null}


def _mean_of_arrays(arrays):
    """Element-wise mean, truncated to the shortest array (n_permutations may differ)."""
    n = min(len(a) for a in arrays)
    return np.mean([a[:n] for a in arrays], axis=0)


def grand_null(group_df, nulls):
    """Grand null of a group's mean-of-session-means: each session's condition nulls
    averaged, then averaged over sessions. None if no condition has a null."""
    session_nulls = []
    for _, sdf in group_df.groupby('session_id'):
        arrs = [nulls[k] for k in zip(sdf['session_id'], sdf['conditions']) if k in nulls]
        if arrs:
            session_nulls.append(_mean_of_arrays(arrs))
    return _mean_of_arrays(session_nulls) if session_nulls else None


def p_value(observed, null, alternative='two-sided'):
    if null is None or len(null) == 0 or not np.isfinite(observed):
        return None
    if alternative == 'greater':
        return float(np.mean(null >= observed))
    if alternative == 'less':
        return float(np.mean(null <= observed))
    return float(np.mean(np.abs(null) >= abs(observed)))


def _sem(values):
    values = np.asarray(values, dtype=float)
    return float(np.std(values) / np.sqrt(len(values))) if len(values) else np.nan


def summarize_groups(df, group_cols, nulls=None, alternative='two-sided'):
    """One row per combination of group_cols: n_conditions, n_sessions, effect
    (mean of per-session mean effects) ± effect_sem, the same for ON% / OFF%, trial
    totals, and the permutation p-value (None without nulls). group_cols may be []
    (one group of everything)."""
    group_cols = list(group_cols)
    groups = df.groupby(group_cols, dropna=False, sort=True, observed=True) if group_cols else [((), df)]
    rows = []
    for key, gdf in groups:
        key = key if isinstance(key, tuple) else (key,)
        per_session = gdf.groupby('session_id')[[EFFECT_COL, ON_COL, OFF_COL]].mean()
        effect = float(per_session[EFFECT_COL].mean())
        row = dict(zip(group_cols, key))
        row.update({
            'n_conditions': len(gdf), 'n_sessions': len(per_session),
            'effect': effect, 'effect_sem': _sem(per_session[EFFECT_COL]),
            'on': float(per_session[ON_COL].mean()), 'on_sem': _sem(per_session[ON_COL]),
            'off': float(per_session[OFF_COL].mean()), 'off_sem': _sem(per_session[OFF_COL]),
            'n_on_trials': int(gdf[N_ON_COL].sum()), 'n_off_trials': int(gdf[N_OFF_COL].sum()),
            'p': (p_value(effect, grand_null(gdf, nulls), alternative)
                  if nulls is not None and alternative else None),
        })
        rows.append(row)
    return pd.DataFrame(rows)


def significance_marker(p):
    if p is None or not np.isfinite(p):
        return ''
    return '***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else 'ns'


# ---------------------------------------------------------------------------
# Pairwise comparison of two groups
# ---------------------------------------------------------------------------

PAIRWISE_N_PERM = 5000


def pairwise_label_permutation(df, label_col, a, b, n_perm=PAIRWISE_N_PERM, seed=0):
    """Test whether group a's effect differs from group b's (rows of df with
    label_col == a / b), using the bars' own statistic: mean of per-session mean
    effects of a minus that of b.

    Null: within each session that has conditions in BOTH groups, the a / b labels
    are shuffled among that session's conditions (group sizes kept). Session-level
    differences in overall effect are therefore held fixed. Sessions with only one
    group still count toward the difference but are never shuffled, so the test
    needs sessions with both (n_shared); with none, p is None.

    Returns {'diff', 'p' (two-sided, (k+1)/(n_perm+1)), 'n_sessions_a',
    'n_sessions_b', 'n_shared'}."""
    rng = np.random.default_rng(seed)
    sub = df[df[label_col].isin([a, b])]
    obs_a, obs_b = [], []
    null_a = np.zeros(n_perm)
    null_b = np.zeros(n_perm)
    n_shared = 0
    for _, sdf in sub.groupby('session_id'):
        e = sdf[EFFECT_COL].to_numpy(dtype=float)
        is_a = (sdf[label_col] == a).to_numpy(dtype=bool)
        n_a = int(is_a.sum())
        n_b = len(e) - n_a
        if n_a:
            obs_a.append(e[is_a].mean())
        if n_b:
            obs_b.append(e[~is_a].mean())
        if n_a and n_b:
            n_shared += 1
            # a random a/b relabelling per permutation, keeping n_a conditions as a
            ranks = rng.random((n_perm, len(e))).argsort(axis=1).argsort(axis=1)
            mask = ranks < n_a
            null_a += (mask * e).sum(axis=1) / n_a
            null_b += (~mask * e).sum(axis=1) / n_b
        elif n_a:
            null_a += e.mean()
        else:
            null_b += e.mean()
    out = {'diff': np.nan, 'p': None, 'n_sessions_a': len(obs_a),
           'n_sessions_b': len(obs_b), 'n_shared': n_shared}
    if not obs_a or not obs_b:
        return out
    out['diff'] = float(np.mean(obs_a) - np.mean(obs_b))
    if n_shared:
        null = null_a / len(obs_a) - null_b / len(obs_b)
        k = int(np.sum(np.abs(null) >= abs(out['diff']) - 1e-12))
        out['p'] = (k + 1) / (n_perm + 1)
    return out


def holm(p_values):
    """Holm-Bonferroni adjusted p-values (same order; None stays None)."""
    idx = [i for i, p in enumerate(p_values) if p is not None]
    adjusted = [None] * len(p_values)
    m = len(idx)
    running = 0.0
    for rank, i in enumerate(sorted(idx, key=lambda i: p_values[i])):
        running = max(running, min(1.0, (m - rank) * p_values[i]))
        adjusted[i] = running
    return adjusted
