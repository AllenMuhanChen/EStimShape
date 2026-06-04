"""
Per-estim-spec isolation score: how isolated each estim spec's active
channels are, in microns, accounting for both boundary placement AND
splits across clusters.

Estim channels come from allen_data_repository.EStimParameters: channels
with a1 > 0 are actively delivering current (channels with a1 = 0 are
ground / charge-recovery pulses and are excluded). Matches the convention
in src/analysis/nafc/estim_parameter_classifier.py.

Scoring (per active estim channel e):
    nearest(e) = min distance to any channel in a cluster ≠ e's cluster
    splits(e)  = count of *other* estim channels assigned to a cluster ≠ e's cluster
    score(e)   = nearest(e) - SPLIT_PENALTY_UM * splits(e)

Aggregated per estim_spec:
    estim_min_isolation_um  = min over estim channels of score(e)   (worst channel)
    estim_mean_isolation_um = mean over estim channels of score(e)  (average)

The split penalty is what lets the score go arbitrarily negative when
estim channels land in different clusters. Pure distance maxes at the
probe length (~2015 µm for the DBC probe); any single split subtracts
SPLIT_PENALTY_UM µm regardless of physical layout, so multi-cluster
splits dominate boundary issues. With the default penalty of 2000 µm,
even one split partner per channel produces a score lower than any
attainable distance-only score, and the all-different-clusters scenario
the user called out scales as (N-1) × penalty in the negative direction.

Scores are saved per (session_id, estim_spec_id) into the
EStimParameterData table — different estim_spec_ids within a session
may stimulate different electrode sets.
"""

import re

import numpy as np
from clat.intan.channels import Channel
from clat.util.connection import Connection

from src.cluster.cluster_app_classes import ChannelMapper

# Microns subtracted from a channel's score for each *other* estim channel
# in a different cluster. Chosen larger than the DBC probe length (~2015 µm)
# so that even a single split partner guarantees a worse score than any
# attainable distance-only result.
SPLIT_PENALTY_UM = 2000.0

_CHANNEL_STR_RE = re.compile(r'^([A-Za-z])-?(\d+)$')


def _parse_channel(ch_str: str) -> Channel | None:
    """Parse channel strings like 'A012' or 'A-12' into Channel.A_012."""
    match = _CHANNEL_STR_RE.match(ch_str.strip())
    if not match:
        return None
    letter = match.group(1).upper()
    num = int(match.group(2))
    try:
        return Channel[f"{letter}_{num:03d}"]
    except KeyError:
        return None


def fetch_active_estim_channels_by_spec(session_id: str) -> dict[int, list[Channel]]:
    """Map estim_spec_id → list of Channel enums for channels actively
    delivering current under that spec (a1 > 0)."""
    repo_conn = Connection("allen_data_repository")
    repo_conn.execute(
        "SELECT estim_spec_id, channel FROM EStimParameters "
        "WHERE session_id = %s AND a1 > 0",
        (session_id,),
    )
    rows = repo_conn.fetch_all()
    by_spec: dict[int, list[Channel]] = {}
    for spec_id, ch_str in rows:
        ch = _parse_channel(ch_str)
        if ch is None:
            print(f"WARN: unparseable channel '{ch_str}' in EStimParameters; skipping")
            continue
        by_spec.setdefault(int(spec_id), []).append(ch)
    return by_spec


def compute_estim_isolation_scores(
    estim_channels: list[Channel],
    channels_for_clusters: dict[int, list[Channel]],
    channel_mapper: ChannelMapper,
    split_penalty_um: float = SPLIT_PENALTY_UM,
) -> dict[str, float | None]:
    """Per-estim-channel score combines boundary distance with a split
    penalty, then aggregates to {'min': worst-channel, 'mean': average}.

    score(e) = nearest_other_cluster_distance(e)
               - split_penalty_um * (# other estim channels in a different cluster)

    Returns {'min': None, 'mean': None} if nothing can be scored.
    """
    cluster_for_channel = {
        ch: cid for cid, chs in channels_for_clusters.items() for ch in chs
    }
    estim_cluster_for = {e: cluster_for_channel.get(e) for e in estim_channels}

    per_channel_scores: list[float] = []
    for estim_ch in estim_channels:
        own_cluster = estim_cluster_for[estim_ch]
        if own_cluster is None:
            continue
        other_channels = [
            ch
            for cid, chs in channels_for_clusters.items()
            if cid != own_cluster
            for ch in chs
        ]
        if not other_channels:
            continue
        e_pos = np.asarray(channel_mapper.get_coordinates(estim_ch))
        other_pos = np.array([channel_mapper.get_coordinates(c) for c in other_channels])
        nearest_dist = float(np.linalg.norm(other_pos - e_pos, axis=1).min())

        split_partners = sum(
            1
            for e2 in estim_channels
            if e2 is not estim_ch
            and estim_cluster_for[e2] is not None
            and estim_cluster_for[e2] != own_cluster
        )

        per_channel_scores.append(nearest_dist - split_penalty_um * split_partners)

    if not per_channel_scores:
        return {'min': None, 'mean': None}
    arr = np.asarray(per_channel_scores)
    return {'min': float(arr.min()), 'mean': float(arr.mean())}


def compute_per_spec_isolation_scores(
    channels_for_clusters: dict[int, list[Channel]],
    channel_mapper: ChannelMapper,
    session_id: str,
) -> dict[int, dict[str, float | None]]:
    """Compute {'min': ..., 'mean': ...} isolation scores for every
    estim_spec_id in the session."""
    by_spec = fetch_active_estim_channels_by_spec(session_id)
    return {
        spec_id: compute_estim_isolation_scores(
            estim_channels, channels_for_clusters, channel_mapper)
        for spec_id, estim_channels in by_spec.items()
    }


def save_per_spec_isolation_scores(
    repo_conn: Connection,
    session_id: str,
    scores_by_spec: dict[int, dict[str, float | None]],
) -> None:
    """Upsert per-spec isolation scores into EStimParameterData."""
    _ensure_estim_parameter_data_table(repo_conn)
    for spec_id, scores in scores_by_spec.items():
        min_value = scores.get('min')
        mean_value = scores.get('mean')
        repo_conn.execute(
            """
            INSERT INTO EStimParameterData
                (session_id, estim_spec_id, estim_min_isolation_um, estim_mean_isolation_um)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                estim_min_isolation_um  = VALUES(estim_min_isolation_um),
                estim_mean_isolation_um = VALUES(estim_mean_isolation_um)
            """,
            (session_id, int(spec_id),
             float(min_value) if min_value is not None else None,
             float(mean_value) if mean_value is not None else None),
        )
        print(f"Saved estim_min_isolation_um={min_value}, "
              f"estim_mean_isolation_um={mean_value} "
              f"for session {session_id}, estim_spec_id={spec_id}")


def _ensure_estim_parameter_data_table(repo_conn: Connection) -> None:
    """Create the table if missing, then make sure both score columns
    exist. Migrates the legacy single-column schema if present."""
    repo_conn.execute(
        """
        CREATE TABLE IF NOT EXISTS EStimParameterData (
            session_id              VARCHAR(10) NOT NULL,
            estim_spec_id           BIGINT      NOT NULL,
            estim_min_isolation_um  FLOAT       NULL,
            estim_mean_isolation_um FLOAT       NULL,
            PRIMARY KEY (session_id, estim_spec_id),
            CONSTRAINT EStimParameterData_session_fk
                FOREIGN KEY (session_id) REFERENCES Sessions (session_id) ON DELETE CASCADE
        ) ENGINE = InnoDB DEFAULT CHARSET = latin1
        """
    )
    # Migrate from the prior single-column schema (estim_isolation_um
    # held a mean-of-means score; the semantics changed when we moved to
    # nearest-other-cluster as the basis, so drop it rather than keep
    # ambiguous values around).
    for stmt in (
        "ALTER TABLE EStimParameterData ADD COLUMN estim_min_isolation_um FLOAT NULL",
        "ALTER TABLE EStimParameterData ADD COLUMN estim_mean_isolation_um FLOAT NULL",
        "ALTER TABLE EStimParameterData DROP COLUMN estim_isolation_um",
    ):
        try:
            repo_conn.execute(stmt)
        except Exception:
            pass
