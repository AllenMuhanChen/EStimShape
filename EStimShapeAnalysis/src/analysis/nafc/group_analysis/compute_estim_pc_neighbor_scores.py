"""
Clustering-free per-estim-spec isolation metric: PC-space distance to physical
neighbors.

Motivation
----------
``cluster_isolation_score`` measures how cleanly a spec's estim channels sit
inside a *manually drawn* cluster. That requires the cluster app and a human.
This module computes a complementary metric that needs no manual clustering:

  1. Build the SAME response representation the cluster app uses — per-channel
     z-scored spikes/s, then PCA (default 2 components, exactly matching
     ``cluster_app.reduce_data`` / ``run_cluster_app_pc_figure``).
  2. For each actively-stimulating channel (a1 > 0), find its ``n_neighbors``
     physically-nearest channels on the probe (DBCChannelMapper coordinates).
  3. Average the PC-space distance from the estim channel to those physical
     neighbors.

If an estim channel sits in a functionally homogeneous patch, its physical
neighbors are close in PC space (small distance). If it sits at — or past — a
functional boundary, some physical neighbors are far in PC space (large
distance). So large distance flags poor isolation, with no boundary drawn by
hand.

Aggregated per estim_spec (across its estim channels):
    estim_max_pc_neighbor_dist  = max  per-channel neighbor distance (worst channel)
    estim_mean_pc_neighbor_dist = mean per-channel neighbor distance (average)

Note the sign is OPPOSITE to estim_*_isolation_um: there, higher = better
isolated; here, higher distance = worse (more boundary-like). The "worst" spec
is therefore the MAX distance, which is why the worst-channel aggregate is a max
rather than a min.

Design knobs (see run_for_sessions):
  - reducer       : 'pca' (default) | 'mds' | 'none'. 'none'/n_components=None
                    use the full z-scored response space (PCA with all components
                    is just a rotation, so its distances equal the full-space
                    distances anyway). 'mds' uses sklearn metric MDS — stochastic
                    and slow; included for completeness.
  - n_components  : PCA/MDS target dim. Default 2 to match the cluster app
                    exactly. None = full space.
  - distance      : 'euclidean' (in the embedding) or 'correlation'
                    (1 - Pearson r on the response vectors). Correlation is in
                    [0, 2] and dimension-independent, so it is comparable across
                    sessions with different stimulus counts; Euclidean is not.
  - n_neighbors   : how many physically-nearest channels to average over (3).
  - exclude_other_estim : skip a spec's other active estim channels when picking
                    neighbors (they are the stim site, not surrounding tissue).
  - within_session_norm : 'scale' (default) divides every distance by one
                    within-session scalar — the RMS of all pairwise channel
                    distances in the embedding — so a score reads as "multiples
                    of this probe's typical spread" and is comparable across
                    experiments regardless of each session's absolute PC scale.
                    'none' leaves raw distances. The divisor preserves the PCA
                    geometry (relative PC1/PC2 weighting), unlike per-PC
                    whitening.

Scores are upserted into EStimParameterData keyed by (session_id, estim_spec_id),
alongside the existing isolation columns.
"""

from __future__ import annotations

import traceback

import numpy as np
from sklearn.decomposition import PCA
from sklearn.manifold import MDS

from clat.intan.channels import Channel
from clat.util.connection import Connection

from src.cluster.cluster_isolation_score import fetch_active_estim_channels_by_spec
from src.cluster.probe_mapping import DBCChannelMapper
from src.startup import context
from src.startup.apply_session_context import apply_session_context


# ---------------------------------------------------------------------------
# Response loading + normalization (mirrors cluster_app / run_cluster_app)
# ---------------------------------------------------------------------------

def _channels_for_prefix(prefix: str) -> list[Channel]:
    return [channel for channel in Channel if channel.name.startswith(prefix)]


def load_responses_for_channels(conn: Connection, prefix: str = "A") -> dict[Channel, np.ndarray]:
    """Per-channel mean spikes/s vector (ordered by stim_id), exactly as
    DbDataLoader.get_spikes_per_channel builds it. Channels with no rows get an
    empty array."""
    data_for_channels = {}
    for channel in _channels_for_prefix(prefix):
        conn.execute(
            """
            SELECT stim_id, AVG(spikes_per_second) AS avg_spikes_per_second
            FROM ChannelResponses
            WHERE channel = %s
            GROUP BY stim_id
            ORDER BY stim_id
            """,
            (str(channel.value),),
        )
        rows = conn.fetch_all()
        if not rows:
            data_for_channels[channel] = np.array([])
        else:
            data_for_channels[channel] = np.array([float(r[1]) for r in rows])
    return data_for_channels


def normalize_per_channel(values: list[np.ndarray]) -> np.ndarray:
    """Per-channel z-score, identical to cluster_app.reduce_data /
    PcInterpretationFigureExporter._normalize_per_channel."""
    normalized = []
    for v in values:
        if len(v) > 1 and np.std(v) > 1e-10:
            normalized.append((v - np.mean(v)) / np.std(v))
        else:
            normalized.append(v)
    return np.vstack(normalized)


# ---------------------------------------------------------------------------
# Embedding + distance
# ---------------------------------------------------------------------------

def _embed(normalized: np.ndarray, reducer: str, n_components) -> np.ndarray:
    """Reduce the (n_channels, n_stim) z-scored matrix to (n_channels, k).

    PCA matches the cluster app. n_components=None or reducer='none' returns the
    full space unchanged (PCA-all-components is a rotation, so its Euclidean
    distances equal full-space distances)."""
    if n_components is None or reducer == 'none':
        return normalized
    k = min(n_components, normalized.shape[0], normalized.shape[1])
    if reducer == 'pca':
        return PCA(n_components=k).fit_transform(normalized)
    if reducer == 'mds':
        # Stochastic; seeded for reproducibility across reruns.
        return MDS(n_components=k, random_state=0).fit_transform(normalized)
    raise ValueError(f"unknown reducer {reducer!r}; choose 'pca', 'mds', or 'none'")


def _build_distance_fn(channels_with_data, normalized, reducer, n_components, distance):
    """Return dist(channel_a, channel_b) over channels_with_data."""
    idx = {ch: i for i, ch in enumerate(channels_with_data)}

    if distance == 'correlation':
        # 1 - Pearson r on the response vectors. Scale-invariant (z-scoring
        # doesn't change it), bounded in [0, 2], comparable across sessions.
        corr = np.corrcoef(normalized)

        def dist(a, b):
            return float(1.0 - corr[idx[a], idx[b]])
        return dist

    if distance != 'euclidean':
        raise ValueError(f"unknown distance {distance!r}; choose 'euclidean' or 'correlation'")

    embedding = _embed(normalized, reducer, n_components)

    def dist(a, b):
        return float(np.linalg.norm(embedding[idx[a]] - embedding[idx[b]]))
    return dist


def _within_session_scale(channels_with_data, dist_fn):
    """RMS of all pairwise channel distances under dist_fn — one scalar per
    session used to normalize distances for cross-session comparability.

    Returns 1.0 (a no-op divisor) when there aren't enough channels or every
    channel coincides."""
    n = len(channels_with_data)
    if n < 2:
        return 1.0
    squares = []
    for i in range(n):
        for j in range(i + 1, n):
            d = dist_fn(channels_with_data[i], channels_with_data[j])
            squares.append(d * d)
    rms = float(np.sqrt(np.mean(squares))) if squares else 0.0
    return rms if rms > 1e-12 else 1.0


# ---------------------------------------------------------------------------
# Per-channel + per-spec scoring
# ---------------------------------------------------------------------------

def compute_pc_neighbor_score(estim_channels, channels_with_data, channel_mapper,
                              dist_fn, n_neighbors=3, exclude_other_estim=True):
    """Aggregate PC-neighbor distance over a spec's estim channels.

    Per estim channel: mean PC-space distance to its n_neighbors physically
    nearest channels (excluding itself, and optionally other estim channels).
    Returns {'mean': ..., 'max': ...} across estim channels, or {'mean': None,
    'max': None} if nothing could be scored (e.g. estim channels lack response
    data)."""
    coords = {ch: np.asarray(channel_mapper.get_coordinates(ch), dtype=float)
              for ch in channels_with_data}
    data_set = set(channels_with_data)
    estim_set = set(estim_channels)

    per_channel = []
    for e in estim_channels:
        if e not in data_set:
            continue  # estim channel has no response data; can't place in PC space
        candidates = [c for c in channels_with_data if c != e]
        if exclude_other_estim:
            candidates = [c for c in candidates if c not in estim_set]
        if not candidates:
            continue
        candidates.sort(key=lambda c: float(np.linalg.norm(coords[c] - coords[e])))
        neighbors = candidates[:n_neighbors]
        if not neighbors:
            continue
        per_channel.append(float(np.mean([dist_fn(e, c) for c in neighbors])))

    if not per_channel:
        return {'mean': None, 'max': None}
    arr = np.asarray(per_channel)
    return {'mean': float(arr.mean()), 'max': float(arr.max())}


def compute_session_pc_neighbor_scores(session_id, *, reducer='pca', n_components=2,
                                       distance='euclidean', n_neighbors=3,
                                       exclude_other_estim=True,
                                       within_session_norm='scale',
                                       channel_mapper=None):
    """Compute {estim_spec_id: {'mean': ..., 'max': ...}} for one session.

    Switches the global context to the session, loads ChannelResponses from its
    GA database, builds the cluster-app representation, and scores every estim
    spec found in EStimParameters (a1 > 0)."""
    apply_session_context(session_id)
    conn = context.ga_config.connection()

    responses = load_responses_for_channels(conn)
    responses = {ch: v for ch, v in responses.items() if v.size > 0}
    if not responses:
        print(f"  {session_id}: no ChannelResponses; skipping")
        return {}

    # vstack needs equal-length vectors; keep the most common stim count.
    lengths = [v.shape[0] for v in responses.values()]
    modal_len = max(set(lengths), key=lengths.count)
    dropped = [ch for ch, v in responses.items() if v.shape[0] != modal_len]
    if dropped:
        print(f"  {session_id}: dropping {len(dropped)} channels with off-length "
              f"response vectors (expected {modal_len})")
    responses = {ch: v for ch, v in responses.items() if v.shape[0] == modal_len}

    channels_with_data = list(responses.keys())
    normalized = normalize_per_channel(list(responses.values()))
    dist_fn = _build_distance_fn(channels_with_data, normalized, reducer,
                                 n_components, distance)

    # Cross-session comparability: divide every distance by the probe's RMS
    # pairwise distance so scores read as multiples of this session's spread.
    if within_session_norm == 'scale':
        scale = _within_session_scale(channels_with_data, dist_fn)
        print(f"  {session_id}: within-session scale (RMS pairwise dist) = {scale:.3f}")
        base_dist_fn = dist_fn
        dist_fn = lambda a, b: base_dist_fn(a, b) / scale
    elif within_session_norm not in (None, 'none'):
        raise ValueError(f"within_session_norm must be 'scale' or 'none'; "
                         f"got {within_session_norm!r}")

    if channel_mapper is None:
        channel_mapper = DBCChannelMapper("A")

    estim_by_spec = fetch_active_estim_channels_by_spec(session_id)
    if not estim_by_spec:
        print(f"  {session_id}: no estim specs (a1 > 0) in EStimParameters")
        return {}

    scores = {}
    for spec_id, estim_channels in estim_by_spec.items():
        scores[spec_id] = compute_pc_neighbor_score(
            estim_channels, channels_with_data, channel_mapper, dist_fn,
            n_neighbors=n_neighbors, exclude_other_estim=exclude_other_estim)
    return scores


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def _ensure_pc_neighbor_columns(repo_conn: Connection):
    """Create EStimParameterData if missing, then add the PC-neighbor columns."""
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
    for stmt in (
        "ALTER TABLE EStimParameterData ADD COLUMN estim_mean_pc_neighbor_dist FLOAT NULL",
        "ALTER TABLE EStimParameterData ADD COLUMN estim_max_pc_neighbor_dist FLOAT NULL",
    ):
        try:
            repo_conn.execute(stmt)
        except Exception:
            pass  # column already exists


def save_per_spec_pc_neighbor_scores(repo_conn, session_id, scores_by_spec):
    """Upsert PC-neighbor scores into EStimParameterData (leaves the isolation
    columns untouched)."""
    for spec_id, scores in sorted(scores_by_spec.items()):
        mean_v, max_v = scores.get('mean'), scores.get('max')
        repo_conn.execute(
            """
            INSERT INTO EStimParameterData
                (session_id, estim_spec_id, estim_mean_pc_neighbor_dist, estim_max_pc_neighbor_dist)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                estim_mean_pc_neighbor_dist = VALUES(estim_mean_pc_neighbor_dist),
                estim_max_pc_neighbor_dist  = VALUES(estim_max_pc_neighbor_dist)
            """,
            (session_id, int(spec_id),
             float(mean_v) if mean_v is not None else None,
             float(max_v) if max_v is not None else None),
        )
        if mean_v is None:
            print(f"  estim_spec_id={spec_id}: skipped (estim channels lack data "
                  f"or no neighbors)")
        else:
            print(f"  estim_spec_id={spec_id}: mean={mean_v:.3f}, max={max_v:.3f} "
                  f"(PC-neighbor distance; higher = more boundary-like)")


# ---------------------------------------------------------------------------
# Batch runner
# ---------------------------------------------------------------------------

def _sessions_with_estim():
    """Sessions that have at least one actively-stimulating channel."""
    conn = Connection("allen_data_repository")
    conn.execute("SELECT DISTINCT session_id FROM EStimParameters WHERE a1 > 0 "
                 "ORDER BY session_id")
    return [row[0] for row in conn.fetch_all()]


def run_for_sessions(start_session_id=None, exclude_session_ids=None, *,
                     reducer='pca', n_components=2,
                     distance='euclidean', n_neighbors=3, exclude_other_estim=True,
                     within_session_norm='scale'):
    """Compute and persist PC-neighbor scores across sessions.

    Operates on every session with estim data, then:
      - start_session_id    : if given, keep only sessions whose id >= this value
                              (lexicographic works because ids are YYMMDD_N).
      - exclude_session_ids : iterable of session ids to drop.

    Sessions that raise (missing GA DB, etc.) are reported but don't abort
    the run."""
    repo_conn = Connection("allen_data_repository")
    _ensure_pc_neighbor_columns(repo_conn)

    session_ids = _sessions_with_estim()
    if start_session_id is not None:
        session_ids = [s for s in session_ids if s >= start_session_id]
    if exclude_session_ids:
        excluded = set(exclude_session_ids)
        session_ids = [s for s in session_ids if s not in excluded]

    print(f"PC-neighbor scoring {len(session_ids)} sessions "
          f"(start={start_session_id}, excluded={sorted(exclude_session_ids) if exclude_session_ids else []}, "
          f"reducer={reducer}, n_components={n_components}, distance={distance}, "
          f"n_neighbors={n_neighbors}, exclude_other_estim={exclude_other_estim}, "
          f"within_session_norm={within_session_norm})")

    failed = []
    for sid in session_ids:
        print(f"\n=== {sid} ===")
        try:
            scores = compute_session_pc_neighbor_scores(
                sid, reducer=reducer, n_components=n_components, distance=distance,
                n_neighbors=n_neighbors, exclude_other_estim=exclude_other_estim,
                within_session_norm=within_session_norm)
        except Exception:
            traceback.print_exc()
            failed.append(sid)
            continue
        if scores:
            save_per_spec_pc_neighbor_scores(repo_conn, sid, scores)

    if failed:
        print(f"\nSessions that failed: {failed}")
    print("\nDone.")
    return failed


def main():
    run_for_sessions(
        start_session_id="260402_0",        # e.g. "260402_0" to start from the first
                                      # variant experiment; None = all sessions
        exclude_session_ids=None,     # e.g. ["260421_0", "260410_0"]
        reducer='pca',               # 'pca' (matches cluster app) | 'mds' | 'none'
        n_components=5,               # 2 matches the cluster app; None = full space
        distance='euclidean',        # 'euclidean' (in embedding) | 'correlation'
        n_neighbors=5,
        exclude_other_estim=False,
        within_session_norm='scale',  # 'scale' (RMS divisor, comparable across
                                      # experiments) | 'none' (raw distances)
    )


if __name__ == '__main__':
    main()
