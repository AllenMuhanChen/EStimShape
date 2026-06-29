"""
live_estim_compile.py
---------------------
Incremental compilation of newly-completed choice trials into the EStimShapeTrials
table, for the live analysis GUI (live_analyze_estim_by_estim_id.py).

The batch path (estim_compile.export_to_repo) deletes a session's rows and rewrites
them wholesale. That is wrong for a live setting: we want to compile *just the trials
that have appeared since the last poll* and upsert them, leaving everything else intact.

Flow per poll:
    1. collect_choice_trials() on the experiment DB  -> list[When]
    2. keep only timestamps we haven't compiled yet (tracked by .start in memory)
    3. compile_latest(exp_conn, new_tstamps)          -> DataFrame in DB column format
    4. upsert_trials() into EStimShapeTrials (INSERT ... ON DUPLICATE KEY UPDATE)
"""

import pandas as pd

from clat.util import time_util
from clat.util.connection import Connection

from src.analysis.nafc.estim_compile import create_estimshape_trials_table
from src.analysis.nafc.psychometric_compile_for_sessions import compile_latest
from src.analysis.nafc.psychometric_curves import collect_choice_trials

# EStimShapeTrials lives in the central results repository.
REPO_DB = "allen_data_repository"

# Trials older than this are never considered (matches compile_latest / the batch script).
_SINCE = (2024, 7, 10)

# Columns we attempt to write — intersected with what the compiled DataFrame actually has.
# task_id is the primary key; the rest are updated on conflict.
_TABLE_COLUMNS = [
    'session_id', 'task_id', 'estim_spec_id', 'is_estim_on',
    'is_hypothesized_choice', 'is_correct_choice', 'trial_type',
    'noise_chance', 'base_mstick_id', 'gen_id', 'trial_start', 'trial_end',
    'sample_length', 'trial_class', 'choice',
    'is_texture_split', 'split_render_is_sample', 'inverted_shading',
    'contrast_texture', 'is_3d_choice',
    'num_choices', 'num_procedural_distractors', 'num_rand_distractors',
]


def ensure_estimshape_trials_table():
    """Create EStimShapeTrials (and EStimParameters) if missing, and make sure the
    sample_length column exists — the base CREATE in estim_compile.py predates it."""
    create_estimshape_trials_table()
    conn = Connection(REPO_DB)
    try:
        conn.execute("ALTER TABLE EStimShapeTrials ADD COLUMN sample_length DOUBLE")
    except Exception:
        pass  # column already present


def get_existing_trial_starts(session_id):
    """Return the set of trial_start timestamps already compiled for this session, so a
    restart of the GUI doesn't recompile trials that are already in the repository."""
    conn = Connection(REPO_DB)
    conn.execute(
        "SELECT trial_start FROM EStimShapeTrials WHERE session_id = %s AND trial_start IS NOT NULL",
        (session_id,))
    return {row[0] for row in conn.fetch_all()}


def upsert_trials(session_id, data):
    """Insert/update compiled trials in EStimShapeTrials keyed on task_id. Unlike the batch
    export, this never deletes existing rows. Returns the number of rows written."""
    if data is None or len(data) == 0:
        return 0

    data = data.copy()
    data['session_id'] = session_id

    # Compile pipelines leave the Choice column capitalized; the table column is `choice`.
    if 'Choice' in data.columns and 'choice' not in data.columns:
        data = data.rename(columns={'Choice': 'choice'})

    columns = [col for col in _TABLE_COLUMNS if col in data.columns]
    if 'task_id' not in columns:
        print("[live-compile] Error: task_id column missing from compiled data")
        return 0

    placeholders = ', '.join(['%s'] * len(columns))
    column_names = ', '.join(columns)
    # Update every non-key column on conflict so a re-compiled trial reflects the latest data.
    updates = ', '.join(f"{c} = VALUES({c})" for c in columns if c != 'task_id')
    insert_query = (
        f"INSERT INTO EStimShapeTrials ({column_names}) VALUES ({placeholders}) "
        f"ON DUPLICATE KEY UPDATE {updates}"
    )

    conn = Connection(REPO_DB)
    written = 0
    for _, row in data.iterrows():
        values = tuple(_clean(row[col]) if col in row.index else None for col in columns)
        conn.execute(insert_query, values)
        written += 1
    return written


def _clean(value):
    """Convert pandas NaN/NA to None so it lands as SQL NULL rather than a literal 'nan'."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def compile_new_trials(exp_conn, session_id, seen_starts):
    """Compile and upsert any choice trials not yet seen in this run.

    seen_starts is a set of trial-start timestamps mutated in place. Returns the number of
    newly-compiled trials (0 if nothing new)."""
    since_date = time_util.from_date_to_now(*_SINCE)
    tstamps = collect_choice_trials(exp_conn, since_date)

    new_tstamps = [t for t in tstamps if t.start not in seen_starts]
    if not new_tstamps:
        return 0

    data = compile_latest(exp_conn, new_tstamps)
    upsert_trials(session_id, data)
    seen_starts.update(t.start for t in new_tstamps)
    return len(new_tstamps)
