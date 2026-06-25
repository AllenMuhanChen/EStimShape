"""
upcoming_trials.py
------------------
Read trials that are queued in TaskToDo but have not yet run (no TaskDone row), and derive
their condition-grouping attributes so the live GUI can show "how many trials of each kind
are still coming".

Why this is a separate path from the completed-trial compile
------------------------------------------------------------
The completed-trial pipeline (nafc_database_fields / psychometric_compile_for_sessions) keys
every field off a per-trial *timestamp window* (a `When`), because it reads run-time messages
(BehMsg TrialMessage, choices, etc.) that only exist once a trial has actually been presented.
An upcoming trial has none of that — all we have is its row in TaskToDo (task_id, stim_id,
gen_id).

Fortunately every attribute we need to *group* upcoming trials is written at generation time
and is keyed by stim_id, so we can read it directly without a timestamp:

    - trial type            : StimSpec.spec -> stimType  (+ NafcSampleRole.is_sample_delta to
                              split EStimShapeVariantsDeltaNAFCStim into delta vs variant)
    - estim_spec_id         : StimSpec.spec -> eStimObjData/long
    - noise level           : StimSpec.data -> noiseChance
    - split-texture params  : NafcSplitTextureParams (split_render_is_sample, inverted_shading,
                              contrast_texture), keyed by stim_id

Note: for NAFC, TaskToDo.stim_id == StimSpec.id (the "stim spec id"); the same value the
completed-trial pipeline ends up calling task_id. We read everything by stim_id here.

This module only *reads*; deleting groups of upcoming trials (step 2) will live alongside it.
"""

import pandas as pd
import xmltodict

from clat.util.connection import Connection


# Coarse trial-type label per StimSpec.spec stimType. EStimShapeVariantsDeltaNAFCStim is
# refined into 'delta'/'variant' using NafcSampleRole; everything else maps directly.
SPLIT_TEXTURE_STIM_TYPE = 'EStimShapeSplitTextureNAFCStim'
_REMOVED_STIM_TYPE = 'EStimShapeVariantsDeletedNAFCStim'
_DELTA_STIM_TYPE = 'EStimShapeVariantsDeltaNAFCStim'
_VARIANT_STIM_TYPE = 'EStimShapeVariantsNAFCStim'
_BEHAVIORAL_STIM_TYPE = 'EStimShapeProceduralBehavioralStim'

# Columns of the DataFrame returned by read_upcoming_trials(), in display order.
UPCOMING_COLUMNS = [
    'task_id', 'stim_id', 'gen_id', 'trial_type', 'stim_type',
    'estim_spec_id', 'is_estim_on', 'noise_chance',
    'split_render_is_sample', 'inverted_shading', 'contrast_texture',
]

# Grouping dimensions the GUI can offer, as (column, human label). Kept here so the panel and
# any future delete-by-group logic agree on the available dimensions.
GROUP_DIMENSIONS = [
    ('trial_type', 'Trial type'),
    ('estim_spec_id', 'EStim spec id'),
    ('noise_chance', 'Noise'),
    ('inverted_shading', 'Inverted shading'),
    ('split_render_is_sample', 'Split on sample'),
    ('contrast_texture', 'Contrast texture'),
    ('gen_id', 'Generation'),
]

# Grouping dimensions checked by default in the GUI panel.
DEFAULT_GROUP_DIMENSIONS = ['trial_type', 'estim_spec_id', 'noise_chance']

_CHUNK = 1000  # max ids per IN (...) query


def _chunks(seq, n=_CHUNK):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def get_upcoming_tasks(conn: Connection):
    """Return [(task_id, stim_id, gen_id), ...] for tasks in TaskToDo with no TaskDone row,
    ordered by generation then task. These are the trials still waiting to run."""
    conn.execute(
        """
        SELECT t.task_id, t.stim_id, t.gen_id
        FROM TaskToDo t
        LEFT JOIN TaskDone d ON d.task_id = t.task_id
        WHERE d.task_id IS NULL
        ORDER BY t.gen_id, t.task_id
        """
    )
    return list(conn.fetch_all())


def _read_stim_specs(conn: Connection, stim_ids):
    """Return {stim_id: (stim_type, estim_spec_id_or_None, noise_chance_or_None)} parsed from
    StimSpec.spec and StimSpec.data for the given stim_ids."""
    out = {}
    for chunk in _chunks(list(stim_ids)):
        placeholders = ','.join(['%s'] * len(chunk))
        conn.execute(
            "SELECT id, spec, data FROM StimSpec WHERE id IN (%s)" % placeholders,
            params=tuple(chunk))
        for stim_id, spec_xml, data_xml in conn.fetch_all():
            stim_type = _parse_stim_type(spec_xml)
            estim_spec_id = _parse_estim_spec_id(spec_xml)
            noise_chance = _parse_noise_chance(data_xml)
            out[stim_id] = (stim_type, estim_spec_id, noise_chance)
    return out


def _parse_stim_type(spec_xml):
    if not spec_xml:
        return None
    try:
        return xmltodict.parse(spec_xml)['StimSpec'].get('stimType')
    except Exception:
        return None


def _parse_estim_spec_id(spec_xml):
    """Pull the estim spec id out of StimSpec.spec eStimObjData/long. Returns None when the
    trial has no estim object (estim OFF)."""
    if not spec_xml:
        return None
    try:
        estim_obj_data = xmltodict.parse(spec_xml)['StimSpec'].get('eStimObjData')
    except Exception:
        return None
    if not estim_obj_data:
        return None
    longs = estim_obj_data.get('long') if isinstance(estim_obj_data, dict) else None
    if longs is None:
        return None
    if isinstance(longs, list):
        longs = longs[0] if longs else None
    try:
        return int(longs)
    except (TypeError, ValueError):
        return None


def _parse_noise_chance(data_xml):
    if not data_xml:
        return None
    try:
        data = xmltodict.parse(data_xml)
        noise = data[next(iter(data))].get('noiseChance')
        return None if noise is None else float(noise)
    except Exception:
        return None


def _read_sample_roles(conn: Connection, stim_ids):
    """Return {stim_id: is_sample_delta(bool)} from NafcSampleRole, or {} if the table is
    absent. Used to split EStimShapeVariantsDeltaNAFCStim into delta vs variant."""
    if not _table_exists(conn, 'NafcSampleRole'):
        return {}
    out = {}
    for chunk in _chunks(list(stim_ids)):
        placeholders = ','.join(['%s'] * len(chunk))
        conn.execute(
            "SELECT stim_id, is_sample_delta FROM NafcSampleRole WHERE stim_id IN (%s)"
            % placeholders, params=tuple(chunk))
        for stim_id, is_delta in conn.fetch_all():
            out[stim_id] = bool(is_delta)
    return out


def _read_split_params(conn: Connection, stim_ids):
    """Return {stim_id: (split_render_is_sample, inverted_shading, contrast_texture)} from
    NafcSplitTextureParams, or {} if the table is absent."""
    if not _table_exists(conn, 'NafcSplitTextureParams'):
        return {}
    out = {}
    for chunk in _chunks(list(stim_ids)):
        placeholders = ','.join(['%s'] * len(chunk))
        conn.execute(
            "SELECT stim_id, split_render_is_sample, inverted_shading, contrast_texture "
            "FROM NafcSplitTextureParams WHERE stim_id IN (%s)" % placeholders,
            params=tuple(chunk))
        for stim_id, split_is_sample, inverted, contrast in conn.fetch_all():
            out[stim_id] = (
                None if split_is_sample is None else bool(split_is_sample),
                None if inverted is None else bool(inverted),
                contrast,
            )
    return out


def _table_exists(conn: Connection, table):
    conn.execute("SHOW TABLES LIKE %s", params=(table,))
    return conn.fetch_one() is not None


def _trial_type(stim_type, is_sample_delta):
    if stim_type == SPLIT_TEXTURE_STIM_TYPE:
        return 'split_texture'
    if stim_type == _REMOVED_STIM_TYPE:
        return 'removed'
    if stim_type == _DELTA_STIM_TYPE:
        if is_sample_delta is None:
            return 'delta?'  # delta-capable trial whose role wasn't recorded
        return 'delta' if is_sample_delta else 'variant'
    if stim_type == _VARIANT_STIM_TYPE:
        return 'variant'
    if stim_type == _BEHAVIORAL_STIM_TYPE:
        return 'behavioral'
    return stim_type or 'unknown'


def read_upcoming_trials(conn: Connection) -> pd.DataFrame:
    """Read every not-yet-run trial from TaskToDo and resolve its grouping attributes.

    Returns a DataFrame with UPCOMING_COLUMNS (empty if nothing is queued). All attribute
    lookups are by stim_id against generation-time tables, so this works before any trial in
    the batch has been presented."""
    tasks = get_upcoming_tasks(conn)
    if not tasks:
        return pd.DataFrame(columns=UPCOMING_COLUMNS)

    stim_ids = sorted({stim_id for _task, stim_id, _gen in tasks})
    specs = _read_stim_specs(conn, stim_ids)
    roles = _read_sample_roles(conn, stim_ids)
    split = _read_split_params(conn, stim_ids)

    rows = []
    for task_id, stim_id, gen_id in tasks:
        stim_type, estim_spec_id, noise_chance = specs.get(stim_id, (None, None, None))
        split_is_sample, inverted, contrast = split.get(stim_id, (None, None, None))
        rows.append({
            'task_id': task_id,
            'stim_id': stim_id,
            'gen_id': gen_id,
            'trial_type': _trial_type(stim_type, roles.get(stim_id)),
            'stim_type': stim_type,
            'estim_spec_id': estim_spec_id,
            'is_estim_on': estim_spec_id is not None,
            'noise_chance': noise_chance,
            'split_render_is_sample': split_is_sample,
            'inverted_shading': inverted,
            'contrast_texture': contrast,
        })
    return pd.DataFrame(rows, columns=UPCOMING_COLUMNS)


def task_ids_for_group(df: pd.DataFrame, group_key: dict):
    """Return the task_ids of rows in df matching group_key (a {column: value} dict, as produced
    per row by group_upcoming_counts). Matches NULL/NaN values correctly so an estim-OFF or
    no-noise group selects exactly its own trials."""
    if df is None or len(df) == 0:
        return []
    mask = pd.Series(True, index=df.index)
    for col, value in group_key.items():
        if value is None or (isinstance(value, float) and pd.isna(value)):
            mask &= df[col].isna()
        else:
            mask &= (df[col] == value)
    return df.loc[mask, 'task_id'].tolist()


def delete_upcoming_tasks(conn: Connection, task_ids) -> int:
    """Delete the given tasks from TaskToDo so the experiment will not run them. Only removes
    rows that are still upcoming (no TaskDone row) as a safety guard against deleting a task
    that completed between the read and the delete. Returns the number of rows deleted.

    Mirrors the existing clear_incomplete_tasks convention of operating on TaskToDo only;
    per-stim generation rows (StimSpec, NafcSampleRole, …) are left untouched and harmless."""
    task_ids = [t for t in task_ids if t is not None]
    if not task_ids:
        return 0
    deleted = 0
    for chunk in _chunks(task_ids):
        placeholders = ','.join(['%s'] * len(chunk))
        conn.execute(
            "DELETE FROM TaskToDo WHERE task_id IN (%s) "
            "AND task_id NOT IN (SELECT task_id FROM TaskDone)" % placeholders,
            params=tuple(chunk))
        # rowcount reflects rows actually removed (the TaskDone guard may exclude some).
        rowcount = getattr(getattr(conn, 'my_cursor', None), 'rowcount', None)
        deleted += rowcount if isinstance(rowcount, int) and rowcount >= 0 else len(chunk)
    return deleted


def group_upcoming_counts(df: pd.DataFrame, group_by) -> pd.DataFrame:
    """Aggregate upcoming trials to a count per group.

    group_by is a list of column names (a subset of UPCOMING_COLUMNS). Returns a DataFrame with
    those columns plus a 'count' column, sorted descending by count. With an empty group_by,
    returns a single total row."""
    if df is None or len(df) == 0:
        return pd.DataFrame(columns=list(group_by) + ['count'])
    if not group_by:
        return pd.DataFrame([{'count': len(df)}])
    # dropna=False so trials with NULL attributes (e.g. estim OFF -> no spec id) still form
    # their own visible group rather than vanishing from the totals.
    counts = (df.groupby(list(group_by), dropna=False)
                .size().reset_index(name='count')
                .sort_values('count', ascending=False, ignore_index=True))
    return counts
