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


def _sliding_window_effects(df, window_size, step_size):
    """
    Compute sliding window effect estimates using the same logic as sliding_window_analysis.
    Returns list of (window_end_trial_idx, effect_pct).
    window_end_trial_idx is the index of the last trial in each window.
    """
    n       = len(df)
    results = []
    for start in range(0, n - window_size + 1, step_size):
        effect = _window_effect(df.iloc[start: start + window_size])
        results.append((start + window_size - 1, effect))
    return results


def compute_last_sustained_positive_window(session_id, cond_dict,
                                           window_size, step_size, threshold):
    """
    Uses the same sliding window as sliding_window_analysis (window_size trials,
    step_size step) to compute reliable effect estimates, then finds the last
    window position where effect >= threshold.

    Conservative rules:
      - First window effect <= 0  → condition started negative, skip.
      - Effect never reaches threshold → not strong enough, skip.
      - Last qualifying window is the final one → never degraded, skip.

    Returns: max_gen_id (int) of the last trial in the last qualifying window,
             or None if no cutoff should be applied.
    """
    df = _get_trials_with_gen_id(session_id, cond_dict)

    if len(df) < window_size:
        return None

    windows = _sliding_window_effects(df, window_size, step_size)

    if not windows:
        return None

    first_effect = windows[0][1]
    if first_effect is None or first_effect <= 0:
        return None

    # A window only qualifies if: (1) it is above threshold, and (2) the mean of
    # all subsequent window effects is below threshold. This handles late spikes —
    # a brief recovery at the very end has no subsequent windows so cannot qualify,
    # preventing the "never degraded" false negative.
    last_above_idx = None
    for i, (_, effect) in enumerate(windows):
        if effect is not None and effect >= threshold:
            subsequent = [e for _, e in windows[i + 1:] if e is not None]
            if subsequent and np.mean(subsequent) < threshold:
                last_above_idx = i

    if last_above_idx is None:
        return None

    end_trial_idx = windows[last_above_idx][0]
    return int(df.iloc[end_trial_idx]['gen_id'])


def save_cutoff(session_id, conditions_json, algorithm_label, max_gen_id):
    conn = Connection("allen_data_repository")
    conn.execute("""
        INSERT INTO EStimSessionCutoffs (session_id, conditions, algorithm_label, max_gen_id)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE max_gen_id = VALUES(max_gen_id),
                                created_at = CURRENT_TIMESTAMP
    """, (session_id, conditions_json, algorithm_label, max_gen_id))


def run_last_sustained_cutoffs(window_size=100, step_size=10, threshold=5.0,
                               session_id=None, force_recompute=False):
    """
    Compute and store last-sustained-positive-window cutoffs for all conditions.
    Uses the same sliding window (window_size, step_size) as sliding_window_analysis
    so the validation plot is directly comparable to the analysis plot.

    Args:
        window_size : trials per window (should match sliding_window_analysis, default 100)
        step_size   : trials between window positions (default 10)
        threshold   : minimum effect size (pp) to count as "still working"
        session_id  : restrict to one session, or None for all
        force_recompute: overwrite existing rows
    """
    create_cutoffs_table()

    algorithm_label = f"last_sustained_w{window_size}_s{step_size}_t{threshold}"

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

        max_gen_id = compute_last_sustained_positive_window(
            sid, cond_dict, window_size, step_size, threshold
        )

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


def plot_session_cutoffs(session_id, algorithm_label, window_size, step_size, threshold,
                         save_path=None):
    """
    For each condition with a stored cutoff, show the same sliding window effect series
    (window_size, step_size) used to compute the cutoff, with:
      - Horizontal orange dashed line at the threshold
      - Vertical red dashed line at the cutoff window position
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

    for ax_idx, (conditions_json, max_gen_id) in enumerate(cutoffs.items()):
        ax        = axes_flat[ax_idx]
        cond_dict = json.loads(conditions_json)
        df        = _get_trials_with_gen_id(session_id, cond_dict)

        windows = _sliding_window_effects(df, window_size, step_size)
        xs      = [end - window_size // 2 for end, _ in windows]
        effects = [eff for _, eff in windows]

        ax.plot(xs, effects, color='steelblue', linewidth=1.5, marker='o', markersize=3)
        ax.axhline(y=threshold, color='orange', linestyle='--', linewidth=1.5,
                   label=f'threshold ({threshold}%)')
        ax.axhline(y=0, color='gray', linestyle=':', linewidth=1, alpha=0.5)

        # Find the window whose last trial has gen_id == max_gen_id and mark it
        for (end_idx, _), x in zip(windows, xs):
            if int(df.iloc[end_idx]['gen_id']) == max_gen_id:
                ax.axvline(x=x, color='red', linestyle='--', linewidth=2,
                           label=f'cutoff (gen_id={max_gen_id})')
                break

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
    window_size = 100
    step_size   = 10
    threshold   = 5.0
    session_id  = None  # None = all sessions

    algorithm_label = run_last_sustained_cutoffs(
        window_size=window_size, step_size=step_size, threshold=threshold,
        session_id=session_id,
    )

    conn = Connection("allen_data_repository")
    if session_id:
        sessions_with_cutoffs = [session_id]
    else:
        conn.execute("SELECT DISTINCT session_id FROM EStimSessionCutoffs WHERE algorithm_label = %s",
                     (algorithm_label,))
        sessions_with_cutoffs = [row[0] for row in conn.fetch_all()]

    for sid in sessions_with_cutoffs:
        plot_session_cutoffs(sid, algorithm_label,
                             window_size=window_size, step_size=step_size,
                             threshold=threshold)


if __name__ == "__main__":
    main()
