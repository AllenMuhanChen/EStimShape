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
        SELECT t.gen_id, t.is_estim_on, t.is_hypothesized_choice
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

    query += " ORDER BY t.gen_id ASC"

    conn.execute(query, tuple(params))
    rows = conn.fetch_all()

    df = pd.DataFrame(rows, columns=['gen_id', 'is_estim_on', 'is_hypothesized_choice'])
    df = df[df['is_hypothesized_choice'].notna()].copy()
    df['is_estim_on'] = df['is_estim_on'].astype(int)
    df['is_hypothesized_choice'] = df['is_hypothesized_choice'].astype(int)
    return df


def _window_effect(df, gen_ids_in_window):
    """Effect size (pp) for trials whose gen_id is in gen_ids_in_window."""
    sub = df[df['gen_id'].isin(gen_ids_in_window)]
    on  = sub[sub['is_estim_on'] == 1]['is_hypothesized_choice']
    off = sub[sub['is_estim_on'] == 0]['is_hypothesized_choice']
    if len(on) == 0 or len(off) == 0:
        return None
    return (on.mean() - off.mean()) * 100.0


def compute_last_sustained_positive_window(session_id, cond_dict, k, threshold):
    """
    Algorithm: last_sustained_positive_window

    For each position i (from k-1 to end), compute the effect of the K gen_ids
    ending at position i.  Find the last gen_id where that rolling effect >= threshold.
    That gen_id becomes max_gen_id (all trials after it are excluded).

    Conservative rules:
      - If the first window effect is <= 0, the condition started negative — return None
        (no cutoff; caller should not insert a row).
      - If the condition never reaches threshold, return None (never strong enough to
        call degradation meaningful).
      - If the last rolling-window gen_id with effect >= threshold is the final gen_id
        in the session, the condition never degraded — return None (no cutoff needed).

    Returns: max_gen_id (int) to cut off at, or None if no cutoff should be applied.
    """
    df = _get_trials_with_gen_id(session_id, cond_dict)
    gen_ids = sorted(df['gen_id'].unique())

    if len(gen_ids) < k:
        return None

    # Check initial direction: first K gen_ids must show a positive effect
    first_effect = _window_effect(df, gen_ids[:k])
    if first_effect is None or first_effect <= 0:
        return None

    # Roll forward and track the last gen_id where effect >= threshold
    last_above_threshold_gen_id = None
    for i in range(k - 1, len(gen_ids)):
        window_gen_ids = gen_ids[i - k + 1: i + 1]
        effect = _window_effect(df, window_gen_ids)
        if effect is not None and effect >= threshold:
            last_above_threshold_gen_id = gen_ids[i]

    if last_above_threshold_gen_id is None:
        # Was initially positive but never hit threshold — not strong enough to call adaptation
        return None

    if last_above_threshold_gen_id == gen_ids[-1]:
        # Never degraded below threshold — no cutoff needed
        return None

    return int(last_above_threshold_gen_id)


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


def main():
    run_last_sustained_cutoffs(k=3, threshold=5.0)


if __name__ == "__main__":
    main()
