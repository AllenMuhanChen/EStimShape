"""
Per-estim-spec isolation score: how isolated each estim spec's active
channels are from channels in any other cluster, in microns on the probe.

Estim channels are identified by reading allen_data_repository.EStimParameters
and selecting channels with a1 > 0 (channels actually delivering current;
a1 = 0 are ground / charge-recovery pulses and are excluded). Matches the
convention in src/analysis/nafc/estim_parameter_classifier.py.

Different estim_spec_ids within a session may stimulate different
electrodes, so the score is computed *per estim_spec_id* and written to
allen_data_repository.EStimParameterData keyed by (session_id, estim_spec_id).

For each estim spec, for each active estim channel:
  - look up which cluster it's assigned to (from the GUI's clustering),
  - compute mean distance (microns) to every channel assigned to a
    *different* cluster.
Then average across that spec's estim channels.

Two penalties drop out of the same formula:
  - Split estim assignment: estim channels in different clusters become
    each other's "other cluster" — and since they're typically near each
    other physically, the distance shrinks and the score drops.
  - Boundary placement: an estim channel at the edge of its cluster has
    other-cluster channels nearby, dragging its mean distance down.
"""

import re

import numpy as np
from clat.intan.channels import Channel
from clat.util.connection import Connection

from src.cluster.cluster_app_classes import ChannelMapper

_CHANNEL_STR_RE = re.compile(r'^([A-Za-z])-?(\d+)$')


def _parse_channel(ch_str: str) -> Channel | None:
    """Parse the assortment of channel string formats we see in the DB
    ("A-012", "A012", "a-12", ...) into the canonical Channel enum
    (Channel.A_012). Returns None if unrecognizable.
    """
    match = _CHANNEL_STR_RE.match(ch_str.strip())
    if not match:
        return None
    letter = match.group(1).upper()
    num = int(match.group(2))
    enum_name = f"{letter}_{num:03d}"
    try:
        return Channel[enum_name]
    except KeyError:
        return None


def fetch_active_estim_channels_by_spec(session_id: str) -> dict[int, list[Channel]]:
    """Map estim_spec_id → list of Channel enums for channels actively
    delivering current under that spec (a1 > 0).

    Ground-pulse channels (a1 = 0) are excluded — they're not real estim
    sites, just charge-recovery pulses.
    """
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


def compute_estim_isolation_score(
    estim_channels: list[Channel],
    channels_for_clusters: dict[int, list[Channel]],
    channel_mapper: ChannelMapper,
) -> float | None:
    """Mean distance, in microns, from each estim channel to all channels
    assigned to a different cluster than that estim channel.

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


def compute_per_spec_isolation_scores(
    channels_for_clusters: dict[int, list[Channel]],
    channel_mapper: ChannelMapper,
    session_id: str,
) -> dict[int, float | None]:
    """Compute the isolation score for every estim_spec_id in the session.

    Returns {estim_spec_id: score or None}.
    """
    by_spec = fetch_active_estim_channels_by_spec(session_id)
    return {
        spec_id: compute_estim_isolation_score(
            estim_channels, channels_for_clusters, channel_mapper)
        for spec_id, estim_channels in by_spec.items()
    }


def save_per_spec_isolation_scores(
    repo_conn: Connection,
    session_id: str,
    scores_by_spec: dict[int, float | None],
) -> None:
    """Upsert per-spec isolation scores into EStimParameterData."""
    _ensure_estim_parameter_data_table(repo_conn)
    for spec_id, score in scores_by_spec.items():
        value = float(score) if score is not None else None
        repo_conn.execute(
            """
            INSERT INTO EStimParameterData (session_id, estim_spec_id, estim_isolation_um)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE estim_isolation_um = VALUES(estim_isolation_um)
            """,
            (session_id, int(spec_id), value),
        )
        print(f"Saved estim_isolation_um={value} for session {session_id}, "
              f"estim_spec_id={spec_id}")


def _ensure_estim_parameter_data_table(repo_conn: Connection) -> None:
    repo_conn.execute(
        """
        CREATE TABLE IF NOT EXISTS EStimParameterData (
            session_id          VARCHAR(10) NOT NULL,
            estim_spec_id       BIGINT      NOT NULL,
            estim_isolation_um  FLOAT       NULL,
            PRIMARY KEY (session_id, estim_spec_id),
            CONSTRAINT EStimParameterData_session_fk
                FOREIGN KEY (session_id) REFERENCES Sessions (session_id) ON DELETE CASCADE
        ) ENGINE = InnoDB DEFAULT CHARSET = latin1
        """
    )
