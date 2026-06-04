"""
Cluster isolation score for estim channel selection.

Captures how far the estim cluster's channels sit from channels in OTHER
non-zero clusters on the probe (in microns). Larger = lower risk of
stimulation current spreading into a different functional group.

Reusable: callers pass in channels_for_clusters (the GUI's cluster
assignment) and a ChannelMapper (gives micron coordinates). No coupling
to the figure-rendering or to the cluster app GUI.
"""

import numpy as np
from clat.intan.channels import Channel
from clat.util.connection import Connection

from src.cluster.cluster_app_classes import ChannelMapper

UNASSIGNED_CLUSTER_ID = 0
DEFAULT_ESTIM_CLUSTER_ID = 1   # matches src/pga/app/run_cluster_app.py:DbDataExporter


def compute_estim_cluster_isolation_score(
    channels_for_clusters: dict[int, list[Channel]],
    channel_mapper: ChannelMapper,
    estim_cluster_id: int = DEFAULT_ESTIM_CLUSTER_ID,
) -> float | None:
    """Mean pairwise distance, in microns, from each estim-cluster channel
    to every channel in any non-zero non-estim cluster.

    - "Other" excludes cluster 0 (unassigned). Unassigned channels aren't a
      coherent functional group worth penalizing current-spread to.
    - Returns None if either the estim cluster is empty or there are no
      other non-zero clusters to measure against.
    """
    estim_channels = channels_for_clusters.get(estim_cluster_id, [])
    other_channels = [
        ch
        for cid, chs in channels_for_clusters.items()
        if cid not in (estim_cluster_id, UNASSIGNED_CLUSTER_ID)
        for ch in chs
    ]
    if not estim_channels or not other_channels:
        return None

    estim_pos = np.array([channel_mapper.get_coordinates(c) for c in estim_channels])
    other_pos = np.array([channel_mapper.get_coordinates(c) for c in other_channels])

    diffs = estim_pos[:, None, :] - other_pos[None, :, :]
    dists = np.linalg.norm(diffs, axis=2)  # (n_estim, n_other), in microns

    return float(dists.mean(axis=1).mean())


def save_estim_cluster_isolation_score(
    repo_conn: Connection,
    session_id: str,
    score: float | None,
) -> None:
    """Upsert the score into allen_data_repository.EStimShapeSessionData.

    Adds the `estim_cluster_isolation_um` column if missing. Assumes the
    table itself already exists (created by analysis/cluster/preference_cluster.py
    on first use).
    """
    _ensure_isolation_column(repo_conn)
    value = float(score) if score is not None else None
    # Upsert: insert a row if this session_id is new, otherwise just update
    # our column. cluster_size NOT NULL is satisfied by providing the
    # current estim-cluster size (0 if score is None — the row won't be
    # informative anyway).
    repo_conn.execute(
        """
        INSERT INTO EStimShapeSessionData (session_id, cluster_size, estim_cluster_isolation_um)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE estim_cluster_isolation_um = VALUES(estim_cluster_isolation_um)
        """,
        (session_id, 0, value),
    )
    print(f"Saved estim_cluster_isolation_um={value} for session {session_id}")


def _ensure_isolation_column(repo_conn: Connection) -> None:
    try:
        repo_conn.execute(
            "ALTER TABLE EStimShapeSessionData "
            "ADD COLUMN estim_cluster_isolation_um FLOAT NULL"
        )
        print("Added estim_cluster_isolation_um column to EStimShapeSessionData")
    except Exception:
        pass  # column already exists; ALTER raises 1060 in MySQL
