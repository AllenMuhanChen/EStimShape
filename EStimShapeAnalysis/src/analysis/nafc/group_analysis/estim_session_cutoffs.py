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

    on = on_df['is_hypothesized_choice']
    if len(on) == 0 or len(off) == 0:
        return None
    return float((on.mean() - off.mean()) * 100.0)


def _count_estim_on_for_condition(df, cond_dict):
    """Count estim-on trials in df that match cond_dict (same filters as _window_effect_for_condition)."""
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

    on_df = df[mask & (df['is_estim_on'] == 1)].copy()
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
    return len(on_df)


def _effect_and_ns_for_condition(df, cond_dict):
    """
    Effect size (pp) and trial counts for a condition over an arbitrary df
    (e.g. the kept portion after a cutoff).
    Returns (effect_pct_or_None, n_estim_on, n_estim_off).
    """
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

    behavioral_df = df[mask]
    off = behavioral_df.loc[behavioral_df['is_estim_on'] == 0, 'is_hypothesized_choice']

    on_df = behavioral_df[behavioral_df['is_estim_on'] == 1].copy()
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

    algorithm_label = f"first_drop_w{window_size}_s{step_size}_t{threshold}_n{n_steps_below}_m{min_estim_trials}"

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
    step_size        = 10
    threshold        = 0
    n_steps_below    = 3
    min_estim_trials = 10
    session_id       = "260617_0"  # None = all sessions

    algorithm_label = run_cutoffs(
        window_size=window_size, step_size=step_size,
        threshold=threshold, n_steps_below=n_steps_below,
        min_estim_trials=min_estim_trials,
        session_id=session_id,
        force_recompute=True,
        verbose=True,
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
