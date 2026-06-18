"""
Compute and store per-condition adaptation cutoffs for EStim sessions.

Conservative policy:
  - Only apply a cutoff to conditions that were initially positive (first-window effect > 0).
  - If a condition was always negative, do nothing — cutting it would be arbitrary.
  - If a condition was initially positive but never degraded below the threshold, do nothing
    (no evidence of adaptation).
  - Only insert a row when a real cutoff is warranted.

Downstream usage:
  JOIN EStimSessionCutoffs ON (session_id, conditions, algorithm_label)
  AND gen_id <= max_gen_id
  If no row exists for a given algorithm_label, use all trials (no cutoff).
"""

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parents[3]))

import math

from clat.util.connection import Connection
from src.analysis.nafc.estim_parameter_classifier import EStimParameterClassifier


def _normalize_cond_key(cond_dict):
    """Canonical JSON key, robust to NaN vs None and numpy vs Python types."""
    def _v(v):
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
    """Parse conditions JSON that may contain bare NaN."""
    return json.loads(re.sub(r'\bNaN\b', 'null', conditions_json))


def create_cutoffs_table():
    conn = Connection("allen_data_repository")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS EStimSessionCutoffs
        (
            session_id       VARCHAR(10)  NOT NULL,
            conditions       LONGTEXT     NOT NULL,
            algorithm_label  VARCHAR(100) NOT NULL,
            max_trial_start  BIGINT       NOT NULL,
            created_at       TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,

            PRIMARY KEY (session_id, conditions(500), algorithm_label(100)),
            FOREIGN KEY (session_id) REFERENCES Sessions (session_id) ON DELETE CASCADE
        ) ENGINE = InnoDB DEFAULT CHARSET = latin1
    """)
    _migrate_cutoffs_table(conn)
    print("EStimSessionCutoffs table created/verified")


def _migrate_cutoffs_table(conn):
    """Replace legacy columns and fix max_trial_start type if it was created as DATETIME."""
    # Drop any old column names (max_gen_id, max_task_id)
    conn.execute("""
        SELECT COLUMN_NAME FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME   = 'EStimSessionCutoffs'
          AND COLUMN_NAME  IN ('max_gen_id', 'max_task_id')
    """)
    old_cols = [row[0] for row in conn.fetch_all()]
    if old_cols:
        print(f"Migrating EStimSessionCutoffs: replacing {old_cols} with max_trial_start BIGINT...")
        conn.execute("DELETE FROM EStimSessionCutoffs")
        for col in old_cols:
            conn.execute(f"ALTER TABLE EStimSessionCutoffs DROP COLUMN {col}")
        conn.execute("ALTER TABLE EStimSessionCutoffs ADD COLUMN max_trial_start BIGINT NOT NULL")
        print("Migration complete")
        return

    # Fix max_trial_start if it was previously created with the wrong type (DATETIME)
    conn.execute("""
        SELECT DATA_TYPE FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME   = 'EStimSessionCutoffs'
          AND COLUMN_NAME  = 'max_trial_start'
    """)
    rows = conn.fetch_all()
    if rows and rows[0][0].lower() != 'bigint':
        print(f"Migrating EStimSessionCutoffs: changing max_trial_start to BIGINT...")
        conn.execute("DELETE FROM EStimSessionCutoffs")
        conn.execute("ALTER TABLE EStimSessionCutoffs MODIFY max_trial_start BIGINT NOT NULL")
        print("Migration complete")


def _get_all_trials_ordered(session_id):
    """
    Fetch ALL trials for the session (all conditions), sorted by trial_start.
    The window slides over this full trial sequence, exactly as sliding_window_analysis does.
    """
    conn = Connection("allen_data_repository")
    query = f"""
        SELECT t.trial_start, t.is_estim_on, t.is_hypothesized_choice,
               t.trial_type, t.noise_chance, t.sample_length, t.estim_spec_id,
               ep.polarity, ep.shape, ep.num_channels, ep.a1,
               ep.post_stim_refractory_period, ep.enable_charge_recovery
        FROM EStimShapeTrials t
        LEFT JOIN ({EStimParameterClassifier.active_channel_sql_subquery()}) ep
          ON t.session_id = ep.session_id AND t.estim_spec_id = ep.estim_spec_id
        WHERE t.session_id = %s
        ORDER BY t.trial_start ASC
    """
    conn.execute(query, (session_id,))
    rows = conn.fetch_all()
    df = pd.DataFrame(rows, columns=[
        'trial_start', 'is_estim_on', 'is_hypothesized_choice',
        'trial_type', 'noise_chance', 'sample_length', 'estim_spec_id',
        'polarity', 'shape', 'num_channels', 'a1',
        'post_stim_refractory_period', 'enable_charge_recovery',
    ])
    df = df[df['is_hypothesized_choice'].notna()].copy()
    df['is_estim_on'] = df['is_estim_on'].astype(int)
    df['is_hypothesized_choice'] = df['is_hypothesized_choice'].astype(int)
    return df.reset_index(drop=True)


def _behavioral_mask(df, cond_dict):
    """Boolean mask of trials matching the behavioral filters (apply to on AND off)."""
    mask = pd.Series(True, index=df.index)
    if 'trial_type' in cond_dict:
        mask &= df['trial_type'] == cond_dict['trial_type']
    if 'noise_chance' in cond_dict:
        mask &= (df['noise_chance'] - cond_dict['noise_chance']).abs() < 0.001
    if 'sample_length' in cond_dict:
        if cond_dict['sample_length'] is None:
            mask &= df['sample_length'].isna()
        else:
            mask &= df['sample_length'] == cond_dict['sample_length']
    return mask


def _estim_on_subset(on_df, cond_dict):
    """Restrict estim-on trials to those matching the estim-param filters."""
    if 'estim_spec_id' in cond_dict:
        on_df = on_df[(on_df['estim_spec_id'] - cond_dict['estim_spec_id']).abs() < 0.5]
    if 'polarity' in cond_dict:
        on_df = on_df[on_df['polarity'] == cond_dict['polarity']]
    if 'shape' in cond_dict:
        on_df = on_df[on_df['shape'] == cond_dict['shape']]
    if 'num_channels' in cond_dict:
        on_df = on_df[on_df['num_channels'] == cond_dict['num_channels']]
    if 'a1' in cond_dict:
        on_df = on_df[(on_df['a1'] - cond_dict['a1']).abs() < 0.01]
    if 'post_stim_refractory_period' in cond_dict:
        on_df = on_df[(on_df['post_stim_refractory_period'] - cond_dict['post_stim_refractory_period']).abs() < 1.0]
    if 'enable_charge_recovery' in cond_dict:
        on_df = on_df[on_df['enable_charge_recovery'] == cond_dict['enable_charge_recovery']]
    return on_df


def _condition_groups(df, cond_dict):
    """
    Return (on_df, off) for a condition within df.
      off : is_hypothesized_choice of behavioral-matched estim-off trials
      on_df : behavioral-matched, param-matched estim-on trials
    Behavioral filters apply to both groups; estim-param filters apply only to estim-on.
    """
    behavioral_df = df[_behavioral_mask(df, cond_dict)]
    off = behavioral_df.loc[behavioral_df['is_estim_on'] == 0, 'is_hypothesized_choice']
    on_df = _estim_on_subset(behavioral_df[behavioral_df['is_estim_on'] == 1], cond_dict)
    return on_df, off


def _window_effect_for_condition(window_df, cond_dict):
    """
    Compute effect size (pp) for a specific condition within a window of ALL trials.
    Behavioral filters (trial_type, noise_chance, sample_length) apply to both groups.
    Estim-param filters (polarity, a1, …) apply only to estim-on trials.
    """
    on_df, off = _condition_groups(window_df, cond_dict)
    on = on_df['is_hypothesized_choice']
    if len(on) == 0 or len(off) == 0:
        return None
    return float((on.mean() - off.mean()) * 100.0)


def _count_estim_on_for_condition(df, cond_dict):
    """Count estim-on trials in df that match cond_dict (same filters as _window_effect_for_condition)."""
    behavioral_df = df[_behavioral_mask(df, cond_dict)]
    return len(_estim_on_subset(behavioral_df[behavioral_df['is_estim_on'] == 1], cond_dict))


def _effect_and_ns_for_condition(df, cond_dict):
    """
    Effect size (pp) and trial counts for a condition over an arbitrary df
    (e.g. the kept portion after a cutoff).
    Returns (effect_pct_or_None, n_estim_on, n_estim_off).
    """
    on_df, off = _condition_groups(df, cond_dict)
    on = on_df['is_hypothesized_choice']
    n_on, n_off = len(on), len(off)
    if n_on == 0 or n_off == 0:
        return None, n_on, n_off
    return float((on.mean() - off.mean()) * 100.0), n_on, n_off


def _format_cond_label(cond_dict):
    """Compact human-readable condition label for diagnostics."""
    abbrevs = {'estim_spec_id': 'spec', 'trial_type': 'type', 'noise_chance': 'noise',
               'sample_length': 'smpl', 'num_channels': 'ch', 'polarity': 'pol',
               'shape': 'shp', 'a1': 'amp', 'post_stim_refractory_period': 'refrac',
               'enable_charge_recovery': 'CR'}
    return ' '.join(f"{abbrevs.get(k, k)}={v}" for k, v in cond_dict.items() if v is not None)


def _sliding_window_effects(df, window_size, step_size, cond_dict):
    """
    Slide a window of window_size trials (step_size apart) over ALL session trials,
    computing the per-condition effect at each position.
    Returns list of (window_end_trial_idx, effect_pct).
    """
    n       = len(df)
    results = []
    for start in range(0, n - window_size + 1, step_size):
        effect = _window_effect_for_condition(df.iloc[start: start + window_size], cond_dict)
        results.append((start + window_size - 1, effect))
    return results


def compute_first_sustained_drop(session_id, cond_dict,
                                  window_size, step_size, threshold, n_steps_below,
                                  min_estim_trials=10):
    """
    Slides a window over ALL session trials (ordered by trial_start) and finds the
    FIRST time the effect drops below threshold and stays there for n_steps_below
    consecutive windows.  The cutoff is the window immediately before that drop.

    Conservative rules:
      - First window WITH DATA has effect <= 0  → condition started negative, skip.
        (Estim specs are introduced progressively, so the first window that
        actually contains trials for this condition is rarely window 0.)
      - Effect never drops below threshold → no adaptation, skip.
      - First drop is the condition's first data window → no positive period to
        keep, skip.

    Returns: trial_start of the last trial in the last good window, or None.
    """
    df = _get_all_trials_ordered(session_id)
    return _first_sustained_drop_from_df(
        df, cond_dict, window_size, step_size, threshold, n_steps_below, min_estim_trials)


def _first_sustained_drop_from_df(df, cond_dict,
                                  window_size, step_size, threshold, n_steps_below,
                                  min_estim_trials=10):
    """
    DataFrame-based core of compute_first_sustained_drop. Kept separate so the
    permutation test can re-run the identical cutoff procedure on relabeled data
    without re-querying the database.
    """
    if len(df) < window_size:
        return None

    windows = _sliding_window_effects(df, window_size, step_size, cond_dict)

    if not windows:
        return None

    # The condition's "first window" is the first one that actually has data for
    # it, not the literal window 0 (which usually predates this spec).
    first_idx = next((i for i, (_, e) in enumerate(windows) if e is not None), None)
    if first_idx is None:
        return None  # condition never had a computable window

    first_effect = windows[first_idx][1]
    if first_effect <= 0:
        return None

    for i in range(first_idx, len(windows)):
        effect = windows[i][1]
        if effect is None or effect >= threshold:
            continue
        # Check n_steps_below - 1 subsequent windows are also below threshold
        run = windows[i: i + n_steps_below]
        if len(run) < n_steps_below:
            break  # not enough windows left to confirm sustained drop
        if all(e is None or e < threshold for _, e in run):
            # The window to keep is the last one BEFORE the drop that had data.
            prev_idx = next((j for j in range(i - 1, first_idx - 1, -1)
                             if windows[j][1] is not None), None)
            if prev_idx is None:
                return None  # no good window to keep before the drop
            end_trial_idx = windows[prev_idx][0]
            kept_df = df.iloc[:end_trial_idx + 1]
            if _count_estim_on_for_condition(kept_df, cond_dict) < min_estim_trials:
                return None  # too few estim trials before the cutoff
            return int(df.iloc[end_trial_idx]['trial_start'])

    return None  # never had a sustained drop


# ---------------------------------------------------------------------------
# Permutation test (Option B): the cutoff is selected FROM the choice outcomes,
# so a valid null must apply the identical cutoff-selection procedure to relabeled
# data. We permute the estim-on / estim-off labels across the whole session
# (keeping trial times fixed), re-run the cutoff detection on the permuted series,
# and take the effect on the surviving trials as the null statistic. Comparing the
# observed cutoff-selected effect to this null cancels the selection bias.
# (Permuting only the surviving trials would be circular and inflate significance.)
# ---------------------------------------------------------------------------

def _cutoff_selected_effect(df, cond_dict, window_size, step_size, threshold,
                            n_steps_below, min_estim_trials):
    """
    Test statistic: the condition's effect size AFTER applying the cutoff procedure.
    If the procedure finds a cutoff, the effect is computed over the kept (<= cutoff)
    trials; otherwise over all trials. Returns effect in pp (0.0 if not computable).
    """
    max_ts = _first_sustained_drop_from_df(
        df, cond_dict, window_size, step_size, threshold, n_steps_below, min_estim_trials)
    kept = df if max_ts is None else df[df['trial_start'] <= max_ts]
    eff, _, _ = _effect_and_ns_for_condition(kept, cond_dict)
    return 0.0 if eff is None else eff


def _condition_on_off_index(df, cond_dict):
    """
    (on_idx, off_idx) index labels for the condition: behavioral+param-matched
    estim-on trials and behavioral-matched estim-off (baseline) trials. These are
    the exchangeable units under H0.
    """
    behavioral_df = df[_behavioral_mask(df, cond_dict)]
    off_idx = behavioral_df.index[behavioral_df['is_estim_on'] == 0]
    on_idx = _estim_on_subset(behavioral_df[behavioral_df['is_estim_on'] == 1], cond_dict).index
    return on_idx, off_idx


def _condition_pool_index(df, cond_dict):
    """Union of the condition's estim-on and estim-off index labels."""
    on_idx, off_idx = _condition_on_off_index(df, cond_dict)
    return on_idx.union(off_idx)


def _simple_label_shuffle_null(on_vals, off_vals, n_permutations, rng):
    """
    Plain two-sample label-shuffle null for the effect size (pp). Valid when no
    cutoff was applied (no selection to correct for), and much cheaper than
    re-running the cutoff detection on every permutation.
    """
    pooled = np.concatenate([on_vals, off_vals])
    n_on = len(on_vals)
    null = np.empty(n_permutations)
    for k in range(n_permutations):
        perm = rng.permutation(pooled)
        null[k] = perm[:n_on].mean() * 100.0 - perm[n_on:].mean() * 100.0
    return null


def permutation_test_for_condition(session_id, cond_dict,
                                   window_size, step_size, threshold, n_steps_below,
                                   min_estim_trials=10, n_permutations=1000, rng=None):
    """
    Option-B permutation test for a single condition. Returns a dict with the
    observed cutoff-selected effect, its cutoff, the null distribution and p-values,
    or None if the condition has no usable data.
    """
    if rng is None:
        rng = np.random.default_rng()

    df = _get_all_trials_ordered(session_id)

    max_ts = _first_sustained_drop_from_df(
        df, cond_dict, window_size, step_size, threshold, n_steps_below, min_estim_trials)
    kept = df if max_ts is None else df[df['trial_start'] <= max_ts]
    observed, n_on, n_off = _effect_and_ns_for_condition(kept, cond_dict)
    # Too few estim-on trials in the tested (kept) portion → not enough data to test.
    # (Cutoff conditions already pass this via _first_sustained_drop_from_df; this
    # mainly skips low-n no-cutoff conditions.)
    if observed is None or n_on < min_estim_trials or n_off == 0:
        return None

    on_idx, off_idx = _condition_on_off_index(df, cond_dict)
    if len(on_idx) == 0 or len(off_idx) == 0:
        return None

    if max_ts is None:
        # No cutoff was applied → the observed effect carries no selection bias, so a
        # plain label-shuffle null is valid and avoids re-running the sliding-window
        # cutoff detection on every permutation.
        method = 'simple'
        null = _simple_label_shuffle_null(
            df.loc[on_idx, 'is_hypothesized_choice'].to_numpy(),
            df.loc[off_idx, 'is_hypothesized_choice'].to_numpy(),
            n_permutations, rng)
    else:
        # A cutoff was selected from the data → the null must apply the same
        # cutoff-selection procedure to relabeled data. Mutate one working copy's
        # choice column in place each permutation instead of copying the frame.
        method = 'cutoff_resampled'
        pool_idx = on_idx.union(off_idx)
        pool_choices = df.loc[pool_idx, 'is_hypothesized_choice'].to_numpy()
        df_work = df.copy()
        null = np.empty(n_permutations)
        for k in range(n_permutations):
            df_work.loc[pool_idx, 'is_hypothesized_choice'] = rng.permutation(pool_choices)
            null[k] = _cutoff_selected_effect(
                df_work, cond_dict, window_size, step_size, threshold, n_steps_below, min_estim_trials)

    p_two     = float(np.mean(np.abs(null) >= abs(observed)))
    p_greater = float(np.mean(null >= observed))
    p_less    = float(np.mean(null <= observed))

    return {
        'observed': observed, 'max_trial_start': max_ts, 'method': method,
        'n_on': n_on, 'n_off': n_off,
        'p_two_tailed': p_two, 'p_greater': p_greater, 'p_less': p_less,
        'null_mean': float(np.mean(null)), 'null': null, 'n_permutations': n_permutations,
    }


def run_cutoff_permutation_tests(session_id=None, window_size=100, step_size=10,
                                 threshold=5.0, n_steps_below=3, min_estim_trials=10,
                                 n_permutations=1000, seed=None,
                                 session_level=True, studentize=True,
                                 exceedance_thresholds=None, plot=True,
                                 metric=METRIC_PCT_HYPOTHESIZED, save_results=True):
    """
    Run the permutation test for every condition in one or all sessions and print a
    per-condition summary. Conditions WITH a cutoff use the Option-B null (re-run the
    cutoff-selection procedure on relabeled data) so the selection bias is cancelled;
    conditions WITHOUT a cutoff use a plain label-shuffle null (no selection to
    correct, far cheaper).

    When save_results is True, each condition's observed effect, null distribution and
    p-values are written to EStimPermutationTests under the cutoff's algorithm_label,
    so downstream population analyses (e.g. max_estim_per_experiment) can use them.

    When session_level is True, also runs and (if plot) plots the per-session maxT
    and exceedance-count tests built from the per-condition nulls. studentize puts
    conditions on a common z scale before aggregating; exceedance_thresholds overrides
    the default threshold sweep.
    """
    rng = np.random.default_rng(seed)
    algorithm_label = _algorithm_label(window_size, step_size, threshold, n_steps_below, min_estim_trials)
    if save_results:
        create_permutation_test_table()
    conn = Connection("allen_data_repository")
    if session_id:
        conn.execute(
            "SELECT session_id, conditions FROM EStimEffects "
            "WHERE session_id = %s AND metric = %s", (session_id, metric))
    else:
        conn.execute(
            "SELECT session_id, conditions FROM EStimEffects WHERE metric = %s", (metric,))
    col_names = [d[0] for d in conn.my_cursor.description]
    all_rows = conn.fetch_all()

    print(f"\nPermutation test  |  algorithm='{algorithm_label}'  |  metric='{metric}'  |  "
          f"{len(all_rows)} conditions  |  {n_permutations} permutations each")
    print("(cutoff conditions: re-run cutoff procedure on relabeled data; "
          "no-cutoff conditions: plain label shuffle)")
    print(f"saving to EStimPermutationTests: {save_results}\n")

    seen_keys = set()
    results = []
    n_skipped = 0
    for row in tqdm(all_rows, desc="Permutation tests"):
        row_dict = dict(zip(col_names, row))
        sid = row_dict['session_id']
        try:
            cond_dict = _parse_conditions_json(row_dict['conditions'])
        except Exception:
            continue
        dedup_key = (sid, _normalize_cond_key(cond_dict))
        if dedup_key in seen_keys:
            continue
        seen_keys.add(dedup_key)

        res = permutation_test_for_condition(
            sid, cond_dict, window_size, step_size, threshold, n_steps_below,
            min_estim_trials, n_permutations=n_permutations, rng=rng)
        if res is None:
            n_skipped += 1
            continue
        results.append((sid, cond_dict, res))

        if save_results:
            save_permutation_results(
                sid, _normalize_cond_key(cond_dict), algorithm_label, metric,
                res['observed'], res['null'].tolist(),
                res['p_two_tailed'], res['p_greater'], res['p_less'],
                res['n_permutations'], res['n_on'], res['n_off'])

        cut_str = (f"cutoff@{res['max_trial_start']} [{res['method']}]"
                   if res['max_trial_start'] is not None
                   else f"no cutoff [{res['method']}]")
        sig = '*' if res['p_two_tailed'] < 0.05 else ' '
        tqdm.write(
            f"{sig} [{sid}] {_format_cond_label(cond_dict)}  |  {cut_str}\n"
            f"      observed={res['observed']:+.1f}pp  (n_on={res['n_on']}, n_off={res['n_off']})  "
            f"null_mean={res['null_mean']:+.1f}pp\n"
            f"      p(two)={res['p_two_tailed']:.4f}  p(greater)={res['p_greater']:.4f}  "
            f"p(less)={res['p_less']:.4f}")

    n_sig = sum(1 for _, _, r in results if r['p_two_tailed'] < 0.05)
    print(f"\nDone. {len(results)} conditions tested  |  {n_sig} significant at p<0.05 (two-tailed)"
          f"  |  {n_skipped} skipped (< {min_estim_trials} estim-on trials or no baseline)")

    if session_level and results:
        by_session = {}
        for sid, cond_dict, res in results:
            by_session.setdefault(sid, []).append(res)
        for sid, entries in by_session.items():
            max_res = session_max_stat_test(entries, studentize=studentize)
            exc_res = session_exceedance_test(entries, thresholds=exceedance_thresholds,
                                              studentize=studentize)
            _print_session_level_tests(sid, max_res, exc_res)
            if plot:
                plot_session_permutation_tests(sid, max_res, exc_res)

    return results


# ---------------------------------------------------------------------------
# Session-level tests built from the per-condition permutation nulls.
# maxT (family-wise): is the single best condition larger than the max chance
# produces across all of the session's conditions?
# Exceedance-count: are there more conditions above a threshold than chance?
# Per-condition nulls are combined by iteration index (treated as independent
# across conditions, matching max_estim_per_experiment's population test).
# ---------------------------------------------------------------------------

def _fmt_p(p):
    return "p<0.001" if p < 0.001 else f"p={p:.3f}"


def _stack_obs_null(entries, studentize=False):
    """
    Build (obs_vector, null_matrix (C, P), unit) from per-condition result dicts.
    studentize standardizes each condition by its own null so wide-null (small-n)
    conditions don't dominate; thresholds are then in z units.
    """
    n_perms = min(len(r['null']) for r in entries)
    obs_vals, null_rows = [], []
    for r in entries:
        null = np.asarray(r['null'][:n_perms], dtype=float)
        if studentize:
            mu, sd = float(np.mean(null)), float(np.std(null, ddof=1))
            if not np.isfinite(sd) or sd <= 0:
                continue
            obs_vals.append((r['observed'] - mu) / sd)
            null_rows.append((null - mu) / sd)
        else:
            obs_vals.append(r['observed'])
            null_rows.append(null)
    if not obs_vals:
        return None
    return np.array(obs_vals), np.stack(null_rows, axis=0), ('z' if studentize else 'pp'), n_perms


def session_max_stat_test(entries, studentize=False):
    """
    maxT test for one session. observed_max = largest observed effect across the
    session's conditions; null is the per-iteration max across conditions.
    Returns dict (or None if no usable conditions).
    """
    stacked = _stack_obs_null(entries, studentize)
    if stacked is None:
        return None
    obs, null_matrix, unit, n_perms = stacked
    max_null = null_matrix.max(axis=0)
    observed_max = float(np.max(obs))
    return {
        'observed_max': observed_max,
        'max_null': max_null,
        'p_value': float(np.mean(max_null >= observed_max)),
        'unit': unit, 'n_conditions': int(obs.shape[0]), 'n_perms': n_perms,
    }


def session_exceedance_test(entries, thresholds=None, studentize=False):
    """
    Exceedance-count test for one session. For each threshold x: observed count of
    conditions with effect >= x, vs the null distribution of that count.
    Returns dict (or None if no usable conditions).
    """
    stacked = _stack_obs_null(entries, studentize)
    if stacked is None:
        return None
    obs, null_matrix, unit, n_perms = stacked
    if thresholds is None:
        thresholds = (1.0, 1.5, 2.0, 2.5, 3.0) if studentize else (5.0, 10.0, 15.0, 20.0)
    rows = []
    for thr in thresholds:
        n_obs = int(np.sum(obs >= thr))
        null_counts = np.sum(null_matrix >= thr, axis=0)
        rows.append({
            'threshold': float(thr), 'n_obs': n_obs,
            'null_mean': float(np.mean(null_counts)),
            'null_95': float(np.percentile(null_counts, 95)),
            'p_value': float(np.mean(null_counts >= n_obs)),
        })
    return {'unit': unit, 'n_conditions': int(obs.shape[0]), 'n_perms': n_perms, 'rows': rows}


def _print_session_level_tests(session_id, max_res, exc_res):
    print(f"\n=== Session-level tests for {session_id} ===")
    if max_res is not None:
        print(f"  Max-stat (maxT): observed max = {max_res['observed_max']:+.2f}{max_res['unit']}  "
              f"null mean = {float(np.mean(max_res['max_null'])):+.2f}{max_res['unit']}  "
              f"{_fmt_p(max_res['p_value'])}  ({max_res['n_conditions']} conditions)")
    if exc_res is not None:
        print(f"  Exceedance-count ({exc_res['n_conditions']} conditions):")
        for r in exc_res['rows']:
            print(f"    effect >= {r['threshold']:5.1f}{exc_res['unit']}:  observed={r['n_obs']:3d}  "
                  f"null mean={r['null_mean']:5.1f}  null 95th={r['null_95']:5.1f}  "
                  f"{_fmt_p(r['p_value'])}")


def plot_session_permutation_tests(session_id, max_res, exc_res, save_path=None):
    """Two-panel figure: maxT null vs observed max, and exceedance observed vs null."""
    import os
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

    if max_res is not None:
        ax1.hist(max_res['max_null'], bins=40, color='lightsteelblue', edgecolor='gray')
        ax1.axvline(max_res['observed_max'], color='red', linewidth=2,
                    label=f"observed max = {max_res['observed_max']:+.1f}{max_res['unit']}")
        ax1.set_title(f"Max-stat test  ({_fmt_p(max_res['p_value'])}, "
                      f"{max_res['n_conditions']} conds, {max_res['n_perms']} perms)")
        ax1.set_xlabel(f"max effect across conditions ({max_res['unit']})")
        ax1.set_ylabel("permutations")
        ax1.legend(fontsize=8)
    else:
        ax1.text(0.5, 0.5, "no usable conditions", ha='center', va='center', transform=ax1.transAxes)

    if exc_res is not None:
        thr       = [r['threshold'] for r in exc_res['rows']]
        n_obs     = [r['n_obs'] for r in exc_res['rows']]
        null_mean = [r['null_mean'] for r in exc_res['rows']]
        null_95   = [r['null_95'] for r in exc_res['rows']]
        ax2.plot(thr, n_obs, 'o-', color='red', label='observed')
        ax2.plot(thr, null_mean, 's--', color='gray', label='null mean')
        ax2.plot(thr, null_95, ':', color='darkgray', label='null 95th pct')
        for r in exc_res['rows']:
            ax2.annotate(_fmt_p(r['p_value']), (r['threshold'], r['n_obs']),
                         textcoords='offset points', xytext=(0, 7), fontsize=7, ha='center')
        ax2.set_title(f"Exceedance-count test ({exc_res['n_conditions']} conds)")
        ax2.set_xlabel(f"effect threshold ({exc_res['unit']})")
        ax2.set_ylabel("# conditions exceeding threshold")
        ax2.legend(fontsize=8)
    else:
        ax2.text(0.5, 0.5, "no usable conditions", ha='center', va='center', transform=ax2.transAxes)

    fig.suptitle(f"{session_id}  —  session-level permutation tests", fontsize=12)
    plt.tight_layout()

    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        fig.savefig(save_path, bbox_inches='tight', dpi=150)
        print(f"Saved to {save_path}")

    plt.show()
    return fig


def save_cutoff(session_id, conditions_json, algorithm_label, max_trial_start):
    conn = Connection("allen_data_repository")
    conn.execute("""
        INSERT INTO EStimSessionCutoffs (session_id, conditions, algorithm_label, max_trial_start)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE max_trial_start = VALUES(max_trial_start),
                                created_at = CURRENT_TIMESTAMP
    """, (session_id, conditions_json, algorithm_label, max_trial_start))


def run_cutoffs(window_size=100, step_size=10, threshold=5.0, n_steps_below=3,
                min_estim_trials=10, session_id=None, force_recompute=False,
                verbose=False):
    """
    Compute and store first-sustained-drop cutoffs for all conditions.

    Args:
        window_size      : trials per window (match sliding_window_analysis, default 100)
        step_size        : trials between window positions (default 10)
        threshold        : effect must drop below this (pp) to count as degraded
        n_steps_below    : number of consecutive windows below threshold required
        min_estim_trials : minimum estim-on trials in the kept portion; if fewer exist
                           before the detected cutoff, no cutoff is applied
        session_id       : restrict to one session, or None for all
        force_recompute  : overwrite existing rows
        verbose          : print per-condition effect size and trial counts
                           (n_on / n_off) for the full data and the kept
                           (after-cutoff) portion
    """
    create_cutoffs_table()

    algorithm_label = _algorithm_label(window_size, step_size, threshold, n_steps_below, min_estim_trials)

    conn = Connection("allen_data_repository")
    # Limit to one metric so cutoff search iterates each (session, conditions) once;
    # cutoffs are metric-agnostic — they apply via trial_start, not the EStimEffects rows.
    if session_id:
        conn.execute(
            "SELECT session_id, conditions FROM EStimEffects "
            "WHERE session_id = %s AND metric = 'pct_hyp_vs_delta'",
            (session_id,))
    else:
        conn.execute(
            "SELECT session_id, conditions FROM EStimEffects WHERE metric = 'pct_hyp_vs_delta'")

    col_names = [d[0] for d in conn.my_cursor.description]
    all_rows = conn.fetch_all()
    print(f"Processing {len(all_rows)} conditions with algorithm '{algorithm_label}'")

    n_cutoffs = 0
    n_no_degradation = 0

    seen_keys = set()  # deduplicate (session_id, normalized_key) across algorithm_label rows

    for row in tqdm(all_rows, desc="Computing cutoffs"):
        row_dict = dict(zip(col_names, row))
        sid             = row_dict['session_id']
        conditions_json = row_dict['conditions']
        try:
            cond_dict = _parse_conditions_json(conditions_json)
        except Exception as e:
            print(f"  WARNING: skipping unparseable conditions for {sid}: {e}")
            continue
        # Normalize so the stored key matches what analyze_estim_by_condition looks up
        normalized_json = _normalize_cond_key(cond_dict)

        dedup_key = (sid, normalized_json)
        if dedup_key in seen_keys:
            continue
        seen_keys.add(dedup_key)

        if not force_recompute:
            conn.execute("""
                SELECT 1 FROM EStimSessionCutoffs
                WHERE session_id = %s AND conditions = %s AND algorithm_label = %s
            """, (sid, normalized_json, algorithm_label))
            if conn.fetch_all():
                continue

        max_trial_start = compute_first_sustained_drop(
            sid, cond_dict, window_size, step_size, threshold, n_steps_below, min_estim_trials
        )

        if max_trial_start is None:
            n_no_degradation += 1
        else:
            save_cutoff(sid, normalized_json, algorithm_label, max_trial_start)
            n_cutoffs += 1

        if verbose:
            df = _get_all_trials_ordered(sid)
            eff_full, on_full, off_full = _effect_and_ns_for_condition(df, cond_dict)
            if max_trial_start is None:
                cut_str = "no cutoff (kept all trials)"
                eff_cut, on_cut, off_cut = eff_full, on_full, off_full
            else:
                kept = df[df['trial_start'] <= max_trial_start]
                eff_cut, on_cut, off_cut = _effect_and_ns_for_condition(kept, cond_dict)
                cut_str = f"cutoff@trial_start={max_trial_start}"
            eff_full_s = f"{eff_full:+.1f}pp" if eff_full is not None else "n/a"
            eff_cut_s  = f"{eff_cut:+.1f}pp"  if eff_cut  is not None else "n/a"
            tqdm.write(
                f"  [{sid}] {_format_cond_label(cond_dict)}  |  {cut_str}\n"
                f"        full:       effect={eff_full_s}  n_on={on_full}  n_off={off_full}\n"
                f"        after-cut:  effect={eff_cut_s}  n_on={on_cut}  n_off={off_cut}"
            )

    print(f"\nDone. Cutoffs applied: {n_cutoffs}  |  No degradation / not applicable: {n_no_degradation}")
    return algorithm_label


def get_session_cutoffs(session_id, algorithm_label):
    """Return {conditions_json: max_trial_start} for this session+algorithm_label."""
    conn = Connection("allen_data_repository")
    conn.execute("""
        SELECT conditions, max_trial_start FROM EStimSessionCutoffs
        WHERE session_id = %s AND algorithm_label = %s
    """, (session_id, algorithm_label))
    return {row[0]: row[1] for row in conn.fetch_all()}


def plot_session_cutoffs(session_id, algorithm_label, window_size, step_size, threshold,
                         save_path=None):
    """
    For each condition with a stored cutoff, show the sliding window effect series with:
      - Orange dashed threshold line
      - Red dashed vertical line at the cutoff window position
    x-axis is window center trial index, identical to sliding_window_analysis.
    """
    import os
    import matplotlib.pyplot as plt

    cutoffs = get_session_cutoffs(session_id, algorithm_label)
    if not cutoffs:
        print(f"No cutoffs found for session={session_id} algorithm={algorithm_label}")
        return None

    n     = len(cutoffs)
    cols  = min(3, n)
    rows  = (n + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(6 * cols, 4 * rows), squeeze=False)
    axes_flat = axes.flatten()

    abbrevs = {'trial_type': 'type', 'noise_chance': 'noise', 'sample_length': 'smpl',
               'num_channels': 'ch', 'polarity': 'pol', 'shape': 'shp',
               'a1': 'amp', 'post_stim_refractory_period': 'refrac',
               'enable_charge_recovery': 'CR'}

    for ax_idx, (conditions_json, max_trial_start) in enumerate(cutoffs.items()):
        ax        = axes_flat[ax_idx]
        cond_dict = json.loads(conditions_json)
        df        = _get_all_trials_ordered(session_id)

        windows = _sliding_window_effects(df, window_size, step_size, cond_dict)
        xs      = [end - window_size // 2 for end, _ in windows]
        effects = [eff for _, eff in windows]

        ax.plot(xs, effects, color='steelblue', linewidth=1.5, marker='o', markersize=3)
        ax.axhline(y=threshold, color='orange', linestyle='--', linewidth=1.5,
                   label=f'threshold ({threshold}%)')
        ax.axhline(y=0, color='gray', linestyle=':', linewidth=1, alpha=0.5)

        for (end_idx, _), x in zip(windows, xs):
            if df.iloc[end_idx]['trial_start'] == max_trial_start:
                ax.axvline(x=x, color='red', linestyle='--', linewidth=2, label='cutoff')
                break

        # Resulting effect size and trial counts: full data vs after-cutoff kept data
        eff_full, on_full, off_full = _effect_and_ns_for_condition(df, cond_dict)
        kept = df[df['trial_start'] <= max_trial_start]
        eff_cut, on_cut, off_cut = _effect_and_ns_for_condition(kept, cond_dict)
        eff_full_s = f"{eff_full:+.1f}pp" if eff_full is not None else "n/a"
        eff_cut_s  = f"{eff_cut:+.1f}pp"  if eff_cut  is not None else "n/a"
        ax.text(
            0.02, 0.02,
            f"full:  {eff_full_s}  (n_on={on_full}, n_off={off_full})\n"
            f"after: {eff_cut_s}  (n_on={on_cut}, n_off={off_cut})",
            transform=ax.transAxes, fontsize=6.5, va='bottom', ha='left',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.7, edgecolor='gray'),
        )

        label_parts = [f"{abbrevs.get(k, k)}={v}" for k, v in cond_dict.items() if v is not None]
        ax.set_title(' | '.join(label_parts), fontsize=7)
        ax.set_xlabel('Trial index (window center)')
        ax.set_ylabel('Effect size (%)')
        ax.legend(fontsize=7)
        ax.grid(True, alpha=0.3)

    for ax in axes_flat[n:]:
        ax.set_visible(False)

    fig.suptitle(f'{session_id}  —  cutoff validation  ({algorithm_label})', fontsize=12)
    plt.tight_layout()

    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        fig.savefig(save_path, bbox_inches='tight', dpi=150)
        print(f"Saved to {save_path}")

    plt.show()
    return fig


def main():
    window_size      = 50
    step_size        = 5
    threshold        = 0
    n_steps_below    = 2
    min_estim_trials = 10
    n_permutations   = 1000
    session_id       = None  # str = one session, list = several, None = all

    # Normalize the selection to a list of run_cutoffs arguments (None means "all").
    if session_id is None or isinstance(session_id, str):
        session_args = [session_id]
    else:
        session_args = list(session_id)

    algorithm_label = None
    for s in session_args:
        algorithm_label = run_cutoffs(
            window_size=window_size, step_size=step_size,
            threshold=threshold, n_steps_below=n_steps_below,
            min_estim_trials=min_estim_trials,
            session_id=s,
            force_recompute=False,
            verbose=True,
        )

    # Resolve which sessions to plot.
    if isinstance(session_id, str):
        sessions_with_cutoffs = [session_id]
    elif session_id is None:
        conn = Connection("allen_data_repository")
        conn.execute("SELECT DISTINCT session_id FROM EStimSessionCutoffs WHERE algorithm_label = %s",
                     (algorithm_label,))
        sessions_with_cutoffs = [row[0] for row in conn.fetch_all()]
    else:
        sessions_with_cutoffs = list(session_id)

    for sid in sessions_with_cutoffs:
        plot_session_cutoffs(sid, algorithm_label,
                             window_size=window_size, step_size=step_size,
                             threshold=threshold)

    # Permutation test. Prompt only when a single session was requested;
    # for a list or all sessions, proceed automatically.
    if isinstance(session_id, str):
        resp = input("\nMove on to the permutation test for this session? [y/N]: ")
        if resp.strip().lower() not in ('y', 'yes'):
            print("Skipping permutation test.")
            return
        perm_sessions = [session_id]
    else:
        print("\nMultiple/all sessions selected — running permutation test automatically.")
        perm_sessions = sessions_with_cutoffs if session_id is None else list(session_id)

    for sid in perm_sessions:
        run_cutoff_permutation_tests(
            session_id=sid, window_size=window_size, step_size=step_size,
            threshold=threshold, n_steps_below=n_steps_below,
            min_estim_trials=min_estim_trials, n_permutations=n_permutations,
            studentize=True
        )


if __name__ == "__main__":
    main()
