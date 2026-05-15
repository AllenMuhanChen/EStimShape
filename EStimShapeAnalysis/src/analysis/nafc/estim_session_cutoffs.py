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
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parents[3]))

from clat.util.connection import Connection
from src.analysis.nafc.estim_parameter_classifier import EStimParameterClassifier


def create_cutoffs_table():
    conn = Connection("allen_data_repository")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS EStimSessionCutoffs
        (
            session_id      VARCHAR(10)  NOT NULL,
            conditions      LONGTEXT     NOT NULL,
            algorithm_label VARCHAR(100) NOT NULL,
            max_gen_id      INT          NOT NULL,
            created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,

            PRIMARY KEY (session_id, conditions(500), algorithm_label(100)),
            FOREIGN KEY (session_id) REFERENCES Sessions (session_id) ON DELETE CASCADE
        ) ENGINE = InnoDB DEFAULT CHARSET = latin1
    """)
    print("EStimSessionCutoffs table created/verified")


def _get_trials_with_gen_id(session_id, cond_dict):
    """
    Returns a DataFrame with columns [gen_id, is_estim_on, is_hypothesized_choice]
    for the given session and condition, sorted by gen_id ascending.
    Applies the same condition filters as get_trial_data_for_condition.
    """
    conn = Connection("allen_data_repository")

    query = f"""
        SELECT t.gen_id, t.is_estim_on, t.is_hypothesized_choice, t.task_id
        FROM EStimShapeTrials t
        LEFT JOIN ({EStimParameterClassifier.active_channel_sql_subquery()}) ep
          ON t.session_id = ep.session_id AND t.estim_spec_id = ep.estim_spec_id
        WHERE t.session_id = %s
    """
    params = [session_id]

    if 'trial_type' in cond_dict:
        query += " AND t.trial_type = %s"
        params.append(cond_dict['trial_type'])
    if 'noise_chance' in cond_dict:
        query += " AND ABS(t.noise_chance - %s) < 0.001"
        params.append(cond_dict['noise_chance'])
    if 'sample_length' in cond_dict:
        if cond_dict['sample_length'] is None:
            query += " AND t.sample_length IS NULL"
        else:
            query += " AND t.sample_length = %s"
            params.append(cond_dict['sample_length'])

    estim_conds = []
    if 'polarity' in cond_dict:
        estim_conds.append("(t.is_estim_on = 0 OR ep.polarity = %s)")
        params.append(cond_dict['polarity'])
    if 'shape' in cond_dict:
        estim_conds.append("(t.is_estim_on = 0 OR ep.shape = %s)")
        params.append(cond_dict['shape'])
    if 'num_channels' in cond_dict:
        estim_conds.append("(t.is_estim_on = 0 OR ep.num_channels = %s)")
        params.append(cond_dict['num_channels'])
    if 'a1' in cond_dict:
        estim_conds.append("(t.is_estim_on = 0 OR ABS(ep.a1 - %s) < 0.01)")
        params.append(cond_dict['a1'])
    if 'post_stim_refractory_period' in cond_dict:
        estim_conds.append("(t.is_estim_on = 0 OR ABS(ep.post_stim_refractory_period - %s) < 1.0)")
        params.append(cond_dict['post_stim_refractory_period'])
    if 'enable_charge_recovery' in cond_dict:
        estim_conds.append("(t.is_estim_on = 0 OR ep.enable_charge_recovery = %s)")
        params.append(cond_dict['enable_charge_recovery'])

    if estim_conds:
        query += " AND " + " AND ".join(estim_conds)

    query += " ORDER BY t.task_id ASC"

    conn.execute(query, tuple(params))
    rows = conn.fetch_all()

    df = pd.DataFrame(rows, columns=['gen_id', 'is_estim_on', 'is_hypothesized_choice', 'task_id'])
    df = df[df['is_hypothesized_choice'].notna()].copy()
    df['is_estim_on'] = df['is_estim_on'].astype(int)
    df['is_hypothesized_choice'] = df['is_hypothesized_choice'].astype(int)
    return df.reset_index(drop=True)


def _window_effect(window_df):
    """Effect size (pp) for a DataFrame slice of trials."""
    on  = window_df[window_df['is_estim_on'] == 1]['is_hypothesized_choice']
    off = window_df[window_df['is_estim_on'] == 0]['is_hypothesized_choice']
    if len(on) == 0 or len(off) == 0:
        return None
    return (on.mean() - off.mean()) * 100.0


def compute_last_sustained_positive_window(session_id, cond_dict, k, threshold):
    """
    Algorithm: last_sustained_positive_window

    Slides a window of K *trials* (ordered by task_id) forward through the session.
    At each position the effect size = mean(estim_on choices) - mean(estim_off choices)
    in that window.  Finds the last trial index where the window effect >= threshold.
    Returns the gen_id of that trial so the cutoff can be applied as gen_id <= max_gen_id.

    Conservative rules:
      - First-window effect <= 0  → condition started negative, skip.
      - Effect never reaches threshold → never strong enough to call adaptation, skip.
      - Last qualifying window is the final window → never degraded, skip.

    Returns: max_gen_id (int) or None if no cutoff should be applied.
    """
    df = _get_trials_with_gen_id(session_id, cond_dict)
    n  = len(df)

    if n < k:
        return None

    # Check initial direction using the first K trials
    first_effect = _window_effect(df.iloc[:k])
    if first_effect is None or first_effect <= 0:
        return None

    # Slide over trials, track the last position where effect >= threshold
    last_above_threshold_idx = None
    for end in range(k - 1, n):
        effect = _window_effect(df.iloc[end - k + 1: end + 1])
        if effect is not None and effect >= threshold:
            last_above_threshold_idx = end

    if last_above_threshold_idx is None:
        return None

    if last_above_threshold_idx == n - 1:
        # Never degraded below threshold — no cutoff needed
        return None

    return int(df.iloc[last_above_threshold_idx]['gen_id'])


def save_cutoff(session_id, conditions_json, algorithm_label, max_gen_id):
    conn = Connection("allen_data_repository")
    conn.execute("""
        INSERT INTO EStimSessionCutoffs (session_id, conditions, algorithm_label, max_gen_id)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE max_gen_id = VALUES(max_gen_id),
                                created_at = CURRENT_TIMESTAMP
    """, (session_id, conditions_json, algorithm_label, max_gen_id))


def run_last_sustained_cutoffs(k=3, threshold=5.0, session_id=None, force_recompute=False):
    """
    Compute and store last-sustained-positive-window cutoffs for all conditions.

    Args:
        k          : rolling window size in gen_ids
        threshold  : minimum effect size (pp) to count as "still working"
        session_id : restrict to one session, or None for all
        force_recompute: overwrite existing rows
    """
    create_cutoffs_table()

    algorithm_label = f"last_sustained_k{k}_t{threshold}"

    conn = Connection("allen_data_repository")
    if session_id:
        conn.execute("SELECT session_id, conditions FROM EStimEffects WHERE session_id = %s",
                     (session_id,))
    else:
        conn.execute("SELECT session_id, conditions FROM EStimEffects")

    col_names = [d[0] for d in conn.my_cursor.description]
    all_rows = conn.fetch_all()
    print(f"Processing {len(all_rows)} conditions with algorithm '{algorithm_label}'")

    n_cutoffs = 0
    n_skipped = 0
    n_no_degradation = 0

    for row in tqdm(all_rows, desc="Computing cutoffs"):
        row_dict = dict(zip(col_names, row))
        sid             = row_dict['session_id']
        conditions_json = row_dict['conditions']
        cond_dict       = json.loads(conditions_json)

        if not force_recompute:
            conn.execute("""
                SELECT 1 FROM EStimSessionCutoffs
                WHERE session_id = %s AND conditions = %s AND algorithm_label = %s
            """, (sid, conditions_json, algorithm_label))
            if conn.fetch_all():
                continue

        max_gen_id = compute_last_sustained_positive_window(sid, cond_dict, k, threshold)

        if max_gen_id is None:
            n_no_degradation += 1
        else:
            save_cutoff(sid, conditions_json, algorithm_label, max_gen_id)
            n_cutoffs += 1

    print(f"\nDone. Cutoffs applied: {n_cutoffs}  |  No degradation / not applicable: {n_no_degradation}")
    return algorithm_label


def get_session_cutoffs(session_id, algorithm_label):
    """Return {conditions_json: max_gen_id} for this session+algorithm_label."""
    conn = Connection("allen_data_repository")
    conn.execute("""
        SELECT conditions, max_gen_id FROM EStimSessionCutoffs
        WHERE session_id = %s AND algorithm_label = %s
    """, (session_id, algorithm_label))
    return {row[0]: row[1] for row in conn.fetch_all()}


def plot_session_cutoffs(session_id, algorithm_label, window_size=100, step_size=10):
    """
    Re-run sliding window analysis for a session and overlay the cutoff lines
    so you can visually verify each cutoff is reasonable.
    Reuses plot_sliding_window_results from analyze_estim_by_condition.
    """
    from src.analysis.nafc.analyze_estim_by_condition import (
        read_trial_data_from_repository,
        sliding_window_analysis,
    )

    cutoffs = get_session_cutoffs(session_id, algorithm_label)
    if not cutoffs:
        print(f"No cutoffs found for session={session_id} algorithm={algorithm_label}")

    data = read_trial_data_from_repository(session_id)
    print(f"[{session_id}] {len(data)} trials, {len(cutoffs)} condition cutoffs to overlay")

    behavioral_conditions = ['trial_type', 'noise_chance', 'sample_length']
    estim_conditions      = ['num_channels', 'polarity', 'shape', 'a1',
                              'post_stim_refractory_period', 'enable_charge_recovery']

    sliding_window_analysis(
        data,
        behavioral_conditions,
        estim_conditions,
        window_size=window_size,
        step_size=step_size,
        session_id=f"{session_id}_cutoffs_{algorithm_label}",
        cutoff_gen_ids=cutoffs,
    )


def main():
    run_last_sustained_cutoffs(k=3, threshold=5.0)


if __name__ == "__main__":
    main()
