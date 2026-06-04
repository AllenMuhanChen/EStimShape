"""
Estim isolation score: how isolated the session's active estim channels are
from channels in any other cluster, in microns on the probe.

Estim channels are identified by reading allen_data_repository.EStimParameters
and selecting channels with a1 > 0 (i.e. channels actually delivering
current; channels with a1 = 0 are ground / charge-recovery pulses and are
excluded). This matches the convention used by
src/analysis/nafc/estim_parameter_classifier.py.

For each active estim channel:
  - look up which cluster it's assigned to (from the GUI's clustering),
  - compute mean distance (microns) to every channel assigned to a
    *different* cluster.
Then average across estim channels.

Two penalties drop out of the same formula:
  - Split estim assignment: estim channels in different clusters become
    each other's "other cluster" — and since they're typically near each
    other physically, the distance shrinks and the score drops.
  - Boundary placement: an estim channel at the edge of its cluster has
    other-cluster channels nearby, dragging its mean distance down.

A large diffuse cluster's estim channels still score well — even at the
cluster edge, other clusters are physically far. A small cluster needs
to be well-isolated *and* the estim channels well-centered.
"""

import numpy as np
from clat.intan.channels import Channel
from clat.util.connection import Connection

from src.cluster.cluster_app_classes import ChannelMapper

ISOLATION_COLUMN = "estim_isolation_um"
LEGACY_ISOLATION_COLUMN = "estim_cluster_isolation_um"


def fetch_active_estim_channels(session_id: str) -> list[Channel]:
    """Return Channel enums for every channel actively delivering current
    in this session (DISTINCT channels with a1 > 0 in EStimParameters).

    Ground-pulse channels (a1 = 0) are excluded — they're not real estim
    sites, just charge-recovery pulses.
    """
    repo_conn = Connection("allen_data_repository")
    repo_conn.execute(
        "SELECT DISTINCT channel FROM EStimParameters "
        "WHERE session_id = %s AND a1 > 0",
        (session_id,),
    )
    rows = repo_conn.fetch_all()
    channels: list[Channel] = []
    for row in rows:
        ch_str = row[0]
        try:
            channels.append(Channel[ch_str.replace("-", "_")])
        except KeyError:
            print(f"WARN: unknown channel '{ch_str}' in EStimParameters; skipping")
    return channels


def compute_estim_isolation_score(
    estim_channels: list[Channel],
    channels_for_clusters: dict[int, list[Channel]],
    channel_mapper: ChannelMapper,
) -> float | None:
    """Mean distance, in microns, from each estim channel to all channels
    assigned to a different cluster than that estim channel.

    estim_channels can fall into any cluster(s) in `channels_for_clusters`;
    each estim channel uses its own assignment as the reference for
    "other cluster," so splits across clusters and boundary placement
    both get penalized naturally.

    Returns None if no estim channels can be scored (e.g. none are
    assigned to any cluster, or there are no other-cluster channels).
    """
    cluster_for_channel = {
        ch: cid for cid, chs in channels_for_clusters.items() for ch in chs
    }

    per_estim_means = []
    for estim_ch in estim_channels:
        own_cluster = cluster_for_channel.get(estim_ch)
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
        dists = np.linalg.norm(other_pos - e_pos, axis=1)
        per_estim_means.append(dists.mean())

    if not per_estim_means:
        return None
    return float(np.mean(per_estim_means))


def save_estim_isolation_score(
    repo_conn: Connection,
    session_id: str,
    score: float | None,
) -> None:
    """Upsert the score into allen_data_repository.EStimShapeSessionData."""
    _ensure_isolation_column(repo_conn)
    value = float(score) if score is not None else None
    repo_conn.execute(
        f"""
        INSERT INTO EStimShapeSessionData (session_id, cluster_size, {ISOLATION_COLUMN})
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE {ISOLATION_COLUMN} = VALUES({ISOLATION_COLUMN})
        """,
        (session_id, 0, value),
    )
    print(f"Saved {ISOLATION_COLUMN}={value} for session {session_id}")


def _ensure_isolation_column(repo_conn: Connection) -> None:
    """Make sure the score column exists under the current name, migrating
    from the legacy `estim_cluster_isolation_um` name if needed."""
    try:
        repo_conn.execute(
            f"ALTER TABLE EStimShapeSessionData "
            f"CHANGE COLUMN {LEGACY_ISOLATION_COLUMN} {ISOLATION_COLUMN} FLOAT NULL"
        )
        print(f"Renamed {LEGACY_ISOLATION_COLUMN} → {ISOLATION_COLUMN}")
    except Exception:
        pass  # legacy column didn't exist; that's fine
    try:
        repo_conn.execute(
            f"ALTER TABLE EStimShapeSessionData "
            f"ADD COLUMN {ISOLATION_COLUMN} FLOAT NULL"
        )
        print(f"Added {ISOLATION_COLUMN} column to EStimShapeSessionData")
    except Exception:
        pass  # column already exists
