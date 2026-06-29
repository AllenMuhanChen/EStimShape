"""
bias_analysis.py
----------------
Reusable, GUI-agnostic computation of *choice bias* in variant/delta NAFC behaviour.

"Behavioural" here means estim-OFF trials of the variant/delta experiment (is_estim_on = 0):
unstimulated behaviour, organised into lineage groups of {1 variant + N deltas}. For each group
we ask: when a given lineage stimulus was the SAMPLE, how often did the animal pick each lineage
member? A flat, sample-independent preference for one member is a bias.

This module deliberately depends only on the compiled repository (EStimShapeTrials, which now
carries both the sample's lineage id ``base_mstick_id`` and the picked shape's lineage id
``picked_base_mstick_id``) plus the IncludedDeltas grouping table — so it can be reused by batch
analyses, notebooks, or the live GUI alike. Nothing here imports Qt/pyqtgraph.

Typical use:
    from src.analysis.nafc import bias_analysis as bias
    result = bias.compute_session_bias("260626_0", start_gen_id=1)
    for group in result['groups']:
        group['member_ids']   # [variant_id, delta_id, ...]  (variant first)
        group['colors']       # {member_id: (r,g,b)}  stable per group
        group['bars']         # {sample_id: {'n', 'count': {m:n}, 'pct': {m:%}}}
        group['timeseries']   # {(sample_id, picked_id): (xs, ys)}
        group['thumbnails']   # {member_id: png_path_or_None}
"""

import os
from collections import defaultdict

import pandas as pd

from clat.util.connection import Connection
from src.startup import context

REPO_DB = "allen_data_repository"

# Sample trial types that make up a lineage group. 'Removed Trial' (a variant with its tuned-for
# component deleted) is a distinct paradigm and is intentionally left out of the bias view.
_LINEAGE_SAMPLE_TRIAL_TYPES = ('Hypothesized Shape', 'Delta Shape')

# Stable palette for lineage members within a group. The variant (member index 0) always gets the
# first colour, so the same group always looks the same across the bar chart, time series, and the
# thumbnail borders that act as the legend.
MEMBER_COLORS = [
    (31, 119, 180), (214, 39, 40), (44, 160, 44), (148, 103, 189), (255, 127, 14),
    (140, 86, 75), (227, 119, 194), (23, 190, 207), (188, 189, 34), (127, 127, 127),
]

# Default sliding-window geometry for the time-series view (trials).
WINDOW_SIZE = 50
WINDOW_STEP = 5


def _repo(conn):
    return conn if conn is not None else Connection(REPO_DB)


def _ga(conn):
    return conn if conn is not None else Connection(context.ga_database)


# ---------------------------------------------------------------------------
# Reading the behavioural (estim-off) trials
# ---------------------------------------------------------------------------

def read_bias_trials(session_id, start_gen_id=None, max_gen_id=None, repo_conn=None):
    """Estim-OFF variant/delta trials for a session, one row per trial.

    Returns a DataFrame with columns:
        task_id, gen_id, trial_start, trial_type, choice,
        noise_chance, sample_length, num_choices, num_procedural_distractors, num_rand_distractors,
        sample_id  (the sample's lineage id == base_mstick_id),
        picked_id  (the picked shape's lineage id == picked_base_mstick_id; may be NULL when the
                    animal picked a non-lineage shape such as a random distractor).

    The behavioural-parameter columns are returned as-is so callers (e.g. the live GUI's top-bar
    filters) can subset the trials before grouping/aggregating.

    Only estim-off trials that carry a sample lineage id are returned (this naturally excludes the
    procedural behavioural catch trials, which record no base_mstick_id, and split-texture trials,
    which have their own paradigm). ``start_gen_id`` / ``max_gen_id`` apply the same generation
    window as the rest of the live analysis; either may be None for no bound.
    """
    conn = _repo(repo_conn)
    placeholders = ', '.join(['%s'] * len(_LINEAGE_SAMPLE_TRIAL_TYPES))
    conn.execute(
        f"""
        SELECT task_id, gen_id, trial_start, trial_type, choice,
               noise_chance, sample_length,
               num_choices, num_procedural_distractors, num_rand_distractors,
               base_mstick_id, picked_base_mstick_id
        FROM EStimShapeTrials
        WHERE session_id = %s
          AND is_estim_on = 0
          AND base_mstick_id IS NOT NULL
          AND trial_type IN ({placeholders})
          AND COALESCE(is_texture_split, 0) = 0
        ORDER BY trial_start, task_id
        """,
        (session_id, *_LINEAGE_SAMPLE_TRIAL_TYPES))
    columns = [desc[0] for desc in conn.my_cursor.description]
    df = pd.DataFrame(conn.fetch_all(), columns=columns)
    df = df.rename(columns={'base_mstick_id': 'sample_id',
                            'picked_base_mstick_id': 'picked_id'})
    if len(df) == 0:
        return df

    # Lineage ids are integers; keep them nullable-int friendly (picked_id can be NULL). Coerce via
    # to_numeric first so Decimal/str values from the DB driver land as a clean nullable Int64.
    df['sample_id'] = pd.to_numeric(df['sample_id'], errors='coerce').astype('Int64')
    df['picked_id'] = pd.to_numeric(df['picked_id'], errors='coerce').astype('Int64')

    # A 'match' pick is, by definition, the sample itself (the match is a copy of the sample), so
    # its picked lineage id is the sample's. Fill it straight from the long-standing `choice`
    # column. This makes the self-pick (diagonal) bars correct even on sessions compiled before
    # picked_base_mstick_id existed; non-match picks still need the reconstructed column.
    if 'choice' in df.columns:
        match_mask = df['choice'].astype(str) == 'match'
        df.loc[match_mask, 'picked_id'] = df.loc[match_mask, 'sample_id']

    if start_gen_id is not None:
        df = df[df['gen_id'] >= start_gen_id]
    if max_gen_id is not None:
        df = df[df['gen_id'] <= max_gen_id]
    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Lineage grouping (triplets)
# ---------------------------------------------------------------------------

def get_variant_delta_map(ga_conn=None):
    """{variant_id: [delta_id, ...]} for all included deltas, in the DB's natural order
    (matching how the generator enumerates them)."""
    conn = _ga(ga_conn)
    conn.execute("SELECT variant_id, delta_id FROM IncludedDeltas WHERE included = 1")
    out = defaultdict(list)
    for variant_id, delta_id in conn.fetch_all():
        out[int(variant_id)].append(int(delta_id))
    return dict(out)


def _variant_of(lineage_id, vd_map, delta_to_variant):
    """The variant id for any lineage id (a variant maps to itself; a delta to its variant)."""
    if lineage_id in vd_map:
        return lineage_id
    return delta_to_variant.get(lineage_id)


def assign_member_colors(member_ids):
    """Stable {member_id: (r,g,b)} for a group's members (variant first)."""
    return {int(m): MEMBER_COLORS[i % len(MEMBER_COLORS)] for i, m in enumerate(member_ids)}


def build_groups(trials_df, ga_conn=None, vd_map=None):
    """Group the session's lineage stimuli into triplets.

    A group is created for every variant that appears as a SAMPLE in ``trials_df``. Members are
    ordered [variant_id, then the variant's included deltas]. Returns a list of dicts:
        {'variant_id', 'member_ids', 'colors'}
    ordered by variant_id. Empty if the grouping table or data is empty.
    """
    if vd_map is None:
        vd_map = get_variant_delta_map(ga_conn)
    delta_to_variant = {d: v for v, deltas in vd_map.items() for d in deltas}

    if 'sample_id' not in trials_df.columns or len(trials_df) == 0:
        return []

    variants_present = []
    seen = set()
    for sid in trials_df['sample_id'].dropna().astype(int):
        variant = _variant_of(int(sid), vd_map, delta_to_variant)
        if variant is not None and variant not in seen:
            seen.add(variant)
            variants_present.append(variant)

    groups = []
    for variant in sorted(variants_present):
        members = [variant] + list(vd_map.get(variant, []))
        groups.append({
            'variant_id': variant,
            'member_ids': members,
            'colors': assign_member_colors(members),
        })
    return groups


# ---------------------------------------------------------------------------
# Bias statistics
# ---------------------------------------------------------------------------

def bias_bar_data(trials_df, member_ids):
    """Per-sample pick distribution for one group.

    Returns {sample_id: {'n': int, 'count': {member_id: int}, 'pct': {member_id: float}}}, with an
    entry only for sample members that actually occurred. The denominator for each sample is ALL of
    that sample's trials, so picks of a non-member shape (e.g. a random distractor) leave the bars
    summing to < 100%. Samples not in ``member_ids`` are ignored (every sample in a group is a
    member by construction).
    """
    members = [int(m) for m in member_ids]
    mset = set(members)
    if 'sample_id' not in trials_df.columns or len(trials_df) == 0:
        return {}
    sub = trials_df[trials_df['sample_id'].isin(mset)]

    out = {}
    for sample in members:
        ssub = sub[sub['sample_id'] == sample]
        n = len(ssub)
        if n == 0:
            continue
        counts = {m: int((ssub['picked_id'] == m).sum()) for m in members}
        pct = {m: 100.0 * counts[m] / n for m in members}
        out[sample] = {'n': n, 'count': counts, 'pct': pct}
    return out


def bias_timeseries(trials_df, member_ids, window=WINDOW_SIZE, step=WINDOW_STEP):
    """Sliding-window version of bias_bar_data for one group.

    Slides a window of ``window`` trials (in chronological order) with stride ``step`` over the
    group's trials. For each window and each sample member s, computes the % of that sample's
    trials in the window on which each member p was picked.

    Returns {(sample_id, picked_id): (xs, ys)} where xs is the window-center trial index within the
    group's trial sequence and ys is the percentage. A (s, p) trace only gets a point at windows
    where sample s occurs.
    """
    members = [int(m) for m in member_ids]
    mset = set(members)
    out = {}
    if 'sample_id' not in trials_df.columns or len(trials_df) == 0:
        return out
    sub = trials_df[trials_df['sample_id'].isin(mset)].reset_index(drop=True)
    n = len(sub)
    if n == 0:
        return out

    for start in range(0, max(n - window, 0) + 1, step):
        w = sub.iloc[start:start + window]
        center = start + window // 2
        for sample in members:
            ws = w[w['sample_id'] == sample]
            denom = len(ws)
            if denom == 0:
                continue
            for picked in members:
                pct = 100.0 * int((ws['picked_id'] == picked).sum()) / denom
                xs, ys = out.setdefault((sample, picked), ([], []))
                xs.append(center)
                ys.append(pct)
    return out


# ---------------------------------------------------------------------------
# Thumbnails
# ---------------------------------------------------------------------------

def resolve_thumbnail(stim_spec_id, image_dir=None):
    """Best-effort filesystem path to a thumbnail PNG for a lineage stimulus, or None.

    Searches ``image_dir`` (default: context.image_path, the GA pngs directory) for a PNG whose
    name starts with the stimulus id, preferring a ``*_thumbnail.png`` render. Returns None when
    the directory or a matching file isn't available, so callers can fall back to a plain coloured
    swatch.
    """
    if image_dir is None:
        image_dir = getattr(context, 'image_path', None)
    if not image_dir or not os.path.isdir(image_dir):
        return None
    prefix = str(int(stim_spec_id))
    try:
        candidates = [f for f in os.listdir(image_dir)
                      if f.startswith(prefix) and f.endswith('.png')]
    except OSError:
        return None
    if not candidates:
        return None
    # Prefer the plain shape thumbnail ('<id>..._thumbnail.png'); never a derived map render
    # (e.g. '_thumbnail_compmap.png' / '_thumbnail_noisemap.png').
    plain_thumbs = [f for f in candidates if f.endswith('_thumbnail.png')]
    if plain_thumbs:
        chosen = sorted(plain_thumbs)[0]
    else:
        non_map = [f for f in candidates if 'compmap' not in f and 'noisemap' not in f]
        chosen = sorted(non_map or candidates)[0]
    return os.path.join(image_dir, chosen)


# ---------------------------------------------------------------------------
# Convenience: everything a UI needs in one call
# ---------------------------------------------------------------------------

def compute_session_bias(session_id, start_gen_id=None, max_gen_id=None,
                         window=WINDOW_SIZE, step=WINDOW_STEP,
                         repo_conn=None, ga_conn=None, with_thumbnails=True,
                         trials_df=None):
    """One-call bias computation for a session.

    Returns {'trials': DataFrame, 'groups': [group_dict, ...]} where each group dict carries
    'variant_id', 'member_ids', 'colors', 'bars', 'timeseries', and (when with_thumbnails)
    'thumbnails'. Pass ``trials_df`` to reuse an already-read frame (the live GUI reuses its cached
    read instead of hitting the DB again).
    """
    if trials_df is None:
        trials_df = read_bias_trials(session_id, start_gen_id, max_gen_id, repo_conn)
    groups = build_groups(trials_df, ga_conn)
    for group in groups:
        members = group['member_ids']
        group['bars'] = bias_bar_data(trials_df, members)
        group['timeseries'] = bias_timeseries(trials_df, members, window, step)
        if with_thumbnails:
            group['thumbnails'] = {int(m): resolve_thumbnail(m) for m in members}
    return {'trials': trials_df, 'groups': groups}
