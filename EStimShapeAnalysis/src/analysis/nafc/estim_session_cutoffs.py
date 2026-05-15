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
            max_task_id     BIGINT       NOT NULL,
            created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,

            PRIMARY KEY (session_id, conditions(500), algorithm_label(100)),
            FOREIGN KEY (session_id) REFERENCES Sessions (session_id) ON DELETE CASCADE
        ) ENGINE = InnoDB DEFAULT CHARSET = latin1
    """)
    _migrate_cutoffs_table(conn)
    _widen_task_id_column(conn)
    print("EStimSessionCutoffs table created/verified")


def _migrate_cutoffs_table(conn):
    """Rename max_gen_id → max_task_id if the table was created with the old column name."""
    conn.execute("""
        SELECT COUNT(*) FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME   = 'EStimSessionCutoffs'
          AND COLUMN_NAME  = 'max_gen_id'
    """)
    if conn.fetch_all()[0][0] == 0:
        return
    print("Migrating EStimSessionCutoffs: renaming max_gen_id to max_task_id...")
    conn.execute("ALTER TABLE EStimSessionCutoffs CHANGE max_gen_id max_task_id BIGINT NOT NULL")
    print("Migration complete")
    _widen_task_id_column(conn)


def _widen_task_id_column(conn):
    """Widen max_task_id from INT to BIGINT if needed (task_ids are timestamp-based)."""
    conn.execute("""
        SELECT DATA_TYPE FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME   = 'EStimSessionCutoffs'
          AND COLUMN_NAME  = 'max_task_id'
    """)
    rows = conn.fetch_all()
    if not rows or rows[0][0].lower() == 'bigint':
        return
    print("Migrating EStimSessionCutoffs: widening max_task_id to BIGINT...")
    conn.execute("ALTER TABLE EStimSessionCutoffs MODIFY max_task_id BIGINT NOT NULL")
    print("Migration complete")


def _get_all_trials_ordered(session_id):
    """
    Fetch ALL trials for the session (all conditions), sorted by task_id.
    The window slides over this full trial sequence, exactly as sliding_window_analysis does.
    """
    conn = Connection("allen_data_repository")
    query = f"""
        SELECT t.task_id, t.is_estim_on, t.is_hypothesized_choice,
               t.trial_type, t.noise_chance, t.sample_length,
               ep.polarity, ep.shape, ep.num_channels, ep.a1,
               ep.post_stim_refractory_period, ep.enable_charge_recovery
        FROM EStimShapeTrials t
        LEFT JOIN ({EStimParameterClassifier.active_channel_sql_subquery()}) ep
          ON t.session_id = ep.session_id AND t.estim_spec_id = ep.estim_spec_id
        WHERE t.session_id = %s
        ORDER BY t.task_id ASC
    """
    conn.execute(query, (session_id,))
    rows = conn.fetch_all()
    df = pd.DataFrame(rows, columns=[
        'task_id', 'is_estim_on', 'is_hypothesized_choice',
        'trial_type', 'noise_chance', 'sample_length',
        'polarity', 'shape', 'num_channels', 'a1',
        'post_stim_refractory_period', 'enable_charge_recovery',
    ])
    df = df[df['is_hypothesized_choice'].notna()].copy()
    df['is_estim_on'] = df['is_estim_on'].astype(int)
    df['is_hypothesized_choice'] = df['is_hypothesized_choice'].astype(int)
    return df.reset_index(drop=True)


def _window_effect_for_condition(window_df, cond_dict):
    """
    Compute effect size (pp) for a specific condition within a window of ALL trials.
    Behavioral filters (trial_type, noise_chance, sample_length) apply to both groups.
    Estim-param filters (polarity, a1, …) apply only to estim-on trials.
    """
    mask = pd.Series(True, index=window_df.index)
    if 'trial_type' in cond_dict:
        mask &= window_df['trial_type'] == cond_dict['trial_type']
    if 'noise_chance' in cond_dict:
        mask &= (window_df['noise_chance'] - cond_dict['noise_chance']).abs() < 0.001
    if 'sample_length' in cond_dict:
        if cond_dict['sample_length'] is None:
            mask &= window_df['sample_length'].isna()
        else:
            mask &= window_df['sample_length'] == cond_dict['sample_length']

    behavioral_df = window_df[mask]
    off = behavioral_df.loc[behavioral_df['is_estim_on'] == 0, 'is_hypothesized_choice']

    on_df = behavioral_df[behavioral_df['is_estim_on'] == 1].copy()
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

    on = on_df['is_hypothesized_choice']
    if len(on) == 0 or len(off) == 0:
        return None
    return float((on.mean() - off.mean()) * 100.0)


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
    df = _get_all_trials_ordered(session_id)

    if len(df) < window_size:
        return None

    windows = _sliding_window_effects(df, window_size, step_size, cond_dict)

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
    return int(df.iloc[end_trial_idx]['task_id'])


def save_cutoff(session_id, conditions_json, algorithm_label, max_task_id):
    conn = Connection("allen_data_repository")
    conn.execute("""
        INSERT INTO EStimSessionCutoffs (session_id, conditions, algorithm_label, max_task_id)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE max_task_id = VALUES(max_task_id),
                                created_at = CURRENT_TIMESTAMP
    """, (session_id, conditions_json, algorithm_label, max_task_id))


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

        max_task_id = compute_last_sustained_positive_window(
            sid, cond_dict, window_size, step_size, threshold
        )

        if max_task_id is None:
            n_no_degradation += 1
        else:
            save_cutoff(sid, conditions_json, algorithm_label, max_task_id)
            n_cutoffs += 1

    print(f"\nDone. Cutoffs applied: {n_cutoffs}  |  No degradation / not applicable: {n_no_degradation}")
    return algorithm_label


def get_session_cutoffs(session_id, algorithm_label):
    """Return {conditions_json: max_task_id} for this session+algorithm_label."""
    conn = Connection("allen_data_repository")
    conn.execute("""
        SELECT conditions, max_task_id FROM EStimSessionCutoffs
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

    for ax_idx, (conditions_json, max_task_id) in enumerate(cutoffs.items()):
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

        # Find the window whose last trial has task_id == max_task_id and mark it
        for (end_idx, _), x in zip(windows, xs):
            if int(df.iloc[end_idx]['task_id']) == max_task_id:
                ax.axvline(x=x, color='red', linestyle='--', linewidth=2,
                           label=f'cutoff (task_id={max_task_id})')
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
