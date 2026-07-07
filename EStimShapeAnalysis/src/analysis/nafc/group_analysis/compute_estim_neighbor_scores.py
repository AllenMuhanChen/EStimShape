"""
Per-estim-spec channel-isolation metrics: how similar is each estim channel to
its physical neighbours on the probe?

This generalises ``compute_estim_pc_neighbor_scores``. That script computed one
metric (PC-space *distance* to physical neighbours, higher = worse). Here we
compute a *family* of metrics, all expressed in the SAME direction —
**higher = more isolated / more similar to neighbours = "better"** — so they can
be compared head-to-head against the estim effect (see
``analyze_estim_isolation_effect.build_metric_comparison_table`` and the
leaderboard it feeds).

The shared skeleton (identical to the old PC-neighbour engine) is:

    for each actively-stimulating channel e of a spec (a1 > 0):
        neighbours(e) = the ``n_neighbors`` physically-nearest channels
                        (DBCChannelMapper coordinates), excluding e and
                        optionally the spec's other estim channels
        per_channel[e] = mean over neighbours of  similarity(e, neighbour)
    aggregate across the spec's estim channels:
        mean  = mean(per_channel)          (average channel)
        worst = min(per_channel)           (least-isolated channel)

The ONLY thing that varies between metrics is ``similarity(a, b)``. Each metric
is a small object exposing ``pair_similarity(a_str, b_str) -> float`` (higher =
more similar). Adding a new metric = adding one such object to
``build_metrics_for_session`` and it automatically joins the leaderboard.

Metrics computed (all higher = better):
  - ``pc_neighbor_sim``            exp(-normalised PC-space distance). The old
                                   ``estim_*_pc_neighbor_dist`` metric, flipped
                                   to a bounded (0, 1] similarity. PCA on
                                   channels x stimuli (each channel is a point),
                                   matching the cluster app.
  - ``channel_corr``              Spearman ρ of the full ga_mean_response
                                   vectors (same computation as
                                   ``preference_cluster``).
  - ``channel_corr_top{20,50,100}`` same, restricted to the top-N stimuli by GA
                                   response (same idea as
                                   ``delta_variant_correlation``'s top-N group).
  - ``channel_corr_delta_variant`` same, restricted to the included delta +
                                   variant stimuli (``IncludedDeltas``).
  - ``pc_loading_sim``            Pearson correlation between the two channels'
                                   PC-*loading* vectors (PCA on stimuli x
                                   channels, loadings per ``stimulus_pca_analysis``).

Data source: every metric reads one shared response matrix,
``ChannelResponseVectors`` (``vector_type='ga_mean_response'``) via
``ChannelResponseVectorLoader`` — the same source ``preference_cluster`` and
``delta_variant_correlation`` use. (The old PC script read ``ChannelResponses``
directly; unifying here keeps all metrics on one representation.)

Scores are upserted into a tidy table ``EStimNeighborScores`` keyed by
(session_id, estim_spec_id, metric_name, aggregation), so new metrics need no
schema change.
"""

from __future__ import annotations

import traceback

import numpy as np

from clat.intan.channels import Channel
from clat.util.connection import Connection

from src.analysis.channel_data_loaders import (
    ChannelResponseVectorLoader,
    DeltaVariantStimLoader,
    GAResponseLoader,
)
from src.analysis.channel_metric_plot import StimVectorCorrelation
from src.cluster.cluster_isolation_score import fetch_active_estim_channels_by_spec
from src.cluster.probe_mapping import DBCChannelMapper
from src.startup import context
from src.startup.apply_session_context import apply_session_context

# Reuse the PC-embedding primitives from the original single-metric script rather
# than duplicating them: these operate on a (channels x stimuli) z-scored matrix
# and a list of channel keys, independent of where the responses came from.
from src.analysis.nafc.group_analysis.compute_estim_pc_neighbor_scores import (
    normalize_per_channel,
    _build_distance_fn,
    _within_session_scale,
)


TOP_N_DEFAULTS = (20, 50, 100)
MIN_COMMON_STIMS = 3  # matches StimVectorCorrelation.min_common


# ---------------------------------------------------------------------------
# Channel <-> unit_name string bridge
# ---------------------------------------------------------------------------

def channel_to_str(channel: Channel) -> str:
    """Channel enum -> 'A-007' unit_name string (as stored in ChannelResponseVectors
    and used by DBCChannelMapper / preference_cluster). Deterministic from the enum
    name, so it does not depend on Channel.value formatting."""
    return channel.name.replace('_', '-')


# ---------------------------------------------------------------------------
# Similarity metrics — each exposes pair_similarity(a_str, b_str); higher = better
# ---------------------------------------------------------------------------

def _restrict_matrix(matrix, stim_ids):
    """Keep only the given stim_ids in every channel's response vector."""
    stim_ids = set(stim_ids)
    return {ch: {s: v for s, v in vec.items() if s in stim_ids}
            for ch, vec in matrix.items()}


class ResponseCorrelationSimilarity:
    """similarity(a, b) = correlation of a's and b's response vectors over their
    shared stimuli. Thin wrapper over StimVectorCorrelation (same alignment /
    min_common / NaN rules as preference_cluster & delta_variant_correlation).

    Correlation is already a "higher = more similar" quantity, so no sign flip."""

    def __init__(self, name, matrix, *, method='spearman', zscore=False,
                 min_common=MIN_COMMON_STIMS):
        self.name = name
        self._matrix = matrix
        self._method = method
        self._zscore = zscore
        self._min_common = min_common
        self._cache = {}  # target_channel -> {channel: rho}

    def _row(self, target):
        if target not in self._cache:
            self._cache[target] = StimVectorCorrelation.vs_channel(
                self._matrix, target, method=self._method, zscore=self._zscore,
                min_common=self._min_common).compute()
        return self._cache[target]

    def pair_similarity(self, a, b):
        return float(self._row(a).get(b, np.nan))


class PcNeighborSimilarity:
    """similarity(a, b) = exp(-normalised PC-space distance). This is the old
    ``estim_*_pc_neighbor_dist`` metric flipped to a bounded (0, 1] similarity:
    identical channels -> 1, distant (boundary-crossing) channels -> ~0.

    Reuses the original engine's PCA embedding + within-session RMS scaling, just
    fed from the shared ga_mean_response matrix instead of ChannelResponses."""

    def __init__(self, name, channel_strs, dist_fn, scale):
        self.name = name
        self._channels = set(channel_strs)
        self._dist_fn = dist_fn
        self._scale = scale

    @classmethod
    def from_aligned(cls, name, channel_strs, aligned_values, *,
                     reducer='pca', n_components=2, distance='euclidean'):
        """Build from a list of channel keys and their stim-aligned response
        vectors (channel-major, equal length). Returns None if there is nothing
        to embed."""
        if len(channel_strs) < 2:
            return None
        normalized = normalize_per_channel(aligned_values)
        dist_fn = _build_distance_fn(channel_strs, normalized, reducer,
                                     n_components, distance)
        scale = _within_session_scale(channel_strs, dist_fn)
        return cls(name, channel_strs, dist_fn, scale)

    def pair_similarity(self, a, b):
        if a not in self._channels or b not in self._channels:
            return np.nan
        return float(np.exp(-self._dist_fn(a, b) / self._scale))


class PcLoadingSimilarity:
    """similarity(a, b) = Pearson correlation between channels a and b of their
    PC-*loading* vectors (over the leading PCs).

    PCA is fit on the stimuli x channels matrix (stimuli are samples, channels are
    features), and loadings = components_.T * sqrt(explained_variance_) per
    ``stimulus_pca_analysis`` — one loading vector per channel across components.
    Two channels whose response profiles load onto the PCs the same way are
    functionally similar (correlation near 1); this mirrors the correlation-space
    channel comparison ``stimulus_pca_analysis._cluster_channels`` uses."""

    def __init__(self, name, loadings):
        self.name = name
        self._loadings = loadings  # {channel_str: np.ndarray over top-k PCs}

    @classmethod
    def from_aligned(cls, name, channel_strs, aligned_values, *, n_loading_pcs=10):
        """Fit PCA on stimuli x channels and keep each channel's leading-PC loading
        vector. Returns None if the matrix is too small to yield >= 2 components."""
        from sklearn.decomposition import PCA
        from sklearn.preprocessing import StandardScaler
        from src.analysis.ga.stimulus_pca_analysis import StimulusPCAAnalysis

        if len(channel_strs) < 2:
            return None
        # rows = channels, cols = stimuli -> transpose to stimuli x channels
        channel_major = np.vstack(aligned_values)              # (n_channels, n_stim)
        X = channel_major.T                                    # (n_stim, n_channels)
        if X.shape[0] < 2 or X.shape[1] < 2:
            return None
        X = StandardScaler().fit_transform(X)
        n_components = min(X.shape)
        pca = PCA(n_components=n_components).fit(X)
        loadings_df = StimulusPCAAnalysis._compute_loadings(pca, channel_strs)
        k = min(n_loading_pcs, loadings_df.shape[1])
        # Correlation over only 2 PCs is degenerate (always ±1); require >= 3.
        if k < 3:
            return None
        block = loadings_df.iloc[:, :k]
        loadings = {ch: block.loc[ch].to_numpy(dtype=float) for ch in channel_strs}
        return cls(name, loadings)

    def pair_similarity(self, a, b):
        va, vb = self._loadings.get(a), self._loadings.get(b)
        if va is None or vb is None or len(va) < 2:
            return np.nan
        if np.std(va) < 1e-12 or np.std(vb) < 1e-12:
            return np.nan
        return float(np.corrcoef(va, vb)[0, 1])


# ---------------------------------------------------------------------------
# Per-session metric construction
# ---------------------------------------------------------------------------

def _aligned_response_arrays(base_matrix, channel_strs):
    """Return (kept_channel_strs, [vector, ...]) aligned over the stimuli common
    to every kept channel. Channels contributing no data are dropped; if the
    common stimulus set is too small, returns ([], [])."""
    present = [ch for ch in channel_strs if base_matrix.get(ch)]
    if len(present) < 2:
        return [], []
    common = set.intersection(*(set(base_matrix[ch]) for ch in present))
    common = sorted(common)
    if len(common) < MIN_COMMON_STIMS:
        return [], []
    values = [np.array([base_matrix[ch][s] for s in common], dtype=float)
              for ch in present]
    return present, values


def build_metrics_for_session(session_id, base_matrix, repo_conn, ga_conn, *,
                              channel_strs, top_ns=TOP_N_DEFAULTS,
                              pca_components=2, n_loading_pcs=10,
                              corr_method='spearman'):
    """Construct the metric objects for one session. ``channel_strs`` is the list
    of probe channels that have response data (the universe over which neighbours
    and embeddings are computed)."""
    metrics = []

    # 2. Channel correlation over all ga_mean_response stimuli.
    metrics.append(ResponseCorrelationSimilarity(
        'channel_corr', base_matrix, method=corr_method))

    # 3. Channel correlation restricted to the top-N stimuli by GA response.
    try:
        ga_responses = GAResponseLoader(session_id, repo_conn).load()
    except Exception as exc:
        print(f"  {session_id}: GA response load failed ({exc}); skipping top-N metrics")
        ga_responses = {}
    if ga_responses:
        ranked = sorted(ga_responses, key=lambda s: ga_responses[s], reverse=True)
        for n in top_ns:
            top_ids = set(ranked[:n])
            metrics.append(ResponseCorrelationSimilarity(
                f'channel_corr_top{n}', _restrict_matrix(base_matrix, top_ids),
                method=corr_method))

    # 4. Channel correlation restricted to included deltas + variants.
    try:
        dv_ids = DeltaVariantStimLoader(ga_conn, included_only=True).load()
    except Exception as exc:
        print(f"  {session_id}: IncludedDeltas load failed ({exc}); skipping delta/variant metric")
        dv_ids = set()
    if dv_ids:
        metrics.append(ResponseCorrelationSimilarity(
            'channel_corr_delta_variant', _restrict_matrix(base_matrix, dv_ids),
            method=corr_method))

    # 1 & 5. PC-based metrics need a stim-aligned matrix over the probe channels.
    aligned_channels, aligned_values = _aligned_response_arrays(base_matrix, channel_strs)
    if aligned_channels:
        pc = PcNeighborSimilarity.from_aligned(
            'pc_neighbor_sim', aligned_channels, aligned_values,
            n_components=pca_components)
        if pc is not None:
            metrics.append(pc)
        loading = PcLoadingSimilarity.from_aligned(
            'pc_loading_sim', aligned_channels, aligned_values,
            n_loading_pcs=n_loading_pcs)
        if loading is not None:
            metrics.append(loading)
    else:
        print(f"  {session_id}: too few common stimuli for PC metrics; skipping them")

    return metrics


# ---------------------------------------------------------------------------
# Neighbour aggregation engine (metric-agnostic)
# ---------------------------------------------------------------------------

def _physical_neighbors(estim_channel, channels_with_data, coords, n_neighbors,
                        exclude):
    """The n_neighbors physically-nearest channels to estim_channel (excluding
    itself and any channel in ``exclude``)."""
    candidates = [c for c in channels_with_data
                  if c != estim_channel and c not in exclude]
    candidates.sort(key=lambda c: float(np.linalg.norm(coords[c] - coords[estim_channel])))
    return candidates[:n_neighbors]


def score_spec_for_metric(metric, estim_channels, channels_with_data, coords,
                          *, n_neighbors=3, exclude_other_estim=True):
    """Aggregate one metric over a spec's estim channels.

    Per estim channel: mean similarity to its physical neighbours. Across the
    spec's estim channels: mean (average) and worst (min, least isolated).
    Returns {'mean': ..., 'worst': ...}, values None if nothing scorable."""
    estim_set = set(estim_channels)
    exclude = estim_set if exclude_other_estim else set()

    per_channel = []
    for e in estim_channels:
        e_str = channel_to_str(e)
        if e not in channels_with_data:
            continue  # estim channel has no response data
        neighbors = _physical_neighbors(e, channels_with_data, coords,
                                        n_neighbors, exclude)
        sims = [metric.pair_similarity(e_str, channel_to_str(nb)) for nb in neighbors]
        sims = [s for s in sims if s is not None and np.isfinite(s)]
        if sims:
            per_channel.append(float(np.mean(sims)))

    if not per_channel:
        return {'mean': None, 'worst': None}
    arr = np.asarray(per_channel, dtype=float)
    return {'mean': float(arr.mean()), 'worst': float(arr.min())}


def compute_session_neighbor_scores(session_id, *, n_neighbors_list=(3,),
                                    exclude_other_estim_list=(True,),
                                    top_ns=TOP_N_DEFAULTS, pca_components=2,
                                    n_loading_pcs=10, corr_method='spearman',
                                    channel_mapper=None, repo_conn=None):
    """Compute scores for one session across all metrics and every
    (n_neighbors, exclude_other_estim) combination.

    Returns {(n_neighbors, exclude_other_estim): {estim_spec_id:
    {metric_name: {'mean': .., 'worst': ..}}}}. The response matrix, PCA, and
    correlation matrices are built ONCE and reused across the sweep — only
    neighbour selection + aggregation re-run per combination, so the sweep is
    cheap."""
    apply_session_context(session_id)
    ga_conn = context.ga_config.connection()
    if repo_conn is None:
        repo_conn = Connection("allen_data_repository")

    base_matrix = ChannelResponseVectorLoader(session_id, repo_conn).load()
    if not base_matrix:
        print(f"  {session_id}: no ChannelResponseVectors; skipping")
        return {}

    if channel_mapper is None:
        channel_mapper = DBCChannelMapper("A")

    # Probe channels (in DBC order) that have response data — the universe for
    # neighbour selection and embeddings.
    channels_with_data = [ch for ch in channel_mapper.channels_top_to_bottom
                          if channel_to_str(ch) in base_matrix]
    if len(channels_with_data) < 2:
        print(f"  {session_id}: <2 probe channels with data; skipping")
        return {}
    coords = {ch: np.asarray(channel_mapper.get_coordinates(ch), dtype=float)
              for ch in channels_with_data}
    channel_strs = [channel_to_str(ch) for ch in channels_with_data]

    metrics = build_metrics_for_session(
        session_id, base_matrix, repo_conn, ga_conn, channel_strs=channel_strs,
        top_ns=top_ns, pca_components=pca_components, n_loading_pcs=n_loading_pcs,
        corr_method=corr_method)
    print(f"  {session_id}: {len(metrics)} metrics: {[m.name for m in metrics]}")

    estim_by_spec = fetch_active_estim_channels_by_spec(session_id)
    if not estim_by_spec:
        print(f"  {session_id}: no estim specs (a1 > 0) in EStimParameters")
        return {}

    results = {}
    for n_neighbors in n_neighbors_list:
        for exclude_other_estim in exclude_other_estim_list:
            per_spec = {}
            for spec_id, estim_channels in estim_by_spec.items():
                per_spec[spec_id] = {
                    metric.name: score_spec_for_metric(
                        metric, estim_channels, channels_with_data, coords,
                        n_neighbors=n_neighbors,
                        exclude_other_estim=exclude_other_estim)
                    for metric in metrics
                }
            results[(int(n_neighbors), bool(exclude_other_estim))] = per_spec
    return results


# ---------------------------------------------------------------------------
# Persistence (tidy long table)
# ---------------------------------------------------------------------------

def _ensure_neighbor_scores_table(repo_conn: Connection):
    """Create the tidy EStimNeighborScores table if missing. One row per
    (session, spec, metric, aggregation, n_neighbors, exclude_other_estim) so a
    neighbourhood-size sweep coexists in one table and new metrics never need a
    schema change.

    If a pre-existing table uses the older 4-column key (no config columns), it is a
    derived cache that this run fully regenerates, so it is dropped and recreated
    with the new key (a warning is printed). Rebuilding the PRIMARY KEY in place is
    avoided because it can conflict with the session FK's index and silently leave
    the old key, which would collapse rows across n_neighbors."""
    # Does a table with the new schema already exist? (SELECT of the new column
    # succeeds only if the table exists AND has been created/migrated.)
    try:
        repo_conn.execute("SELECT n_neighbors FROM EStimNeighborScores LIMIT 1")
        return  # already the new schema
    except Exception:
        pass

    # New column absent: either no table at all, or an old-schema table to replace.
    try:
        repo_conn.execute("SELECT 1 FROM EStimNeighborScores LIMIT 1")
        table_exists = True
    except Exception:
        table_exists = False
    if table_exists:
        print("Migrating EStimNeighborScores: dropping the old-schema table "
              "(a derived cache, regenerated by this run) and recreating it with "
              "the (n_neighbors, exclude_other_estim) key.")
        repo_conn.execute("DROP TABLE EStimNeighborScores")

    repo_conn.execute(
        """
        CREATE TABLE IF NOT EXISTS EStimNeighborScores (
            session_id           VARCHAR(10) NOT NULL,
            estim_spec_id        BIGINT      NOT NULL,
            metric_name          VARCHAR(64) NOT NULL,
            aggregation          VARCHAR(16) NOT NULL,
            n_neighbors          INT         NOT NULL DEFAULT 3,
            exclude_other_estim  TINYINT     NOT NULL DEFAULT 1,
            value                FLOAT       NULL,
            PRIMARY KEY (session_id, estim_spec_id, metric_name, aggregation,
                         n_neighbors, exclude_other_estim),
            CONSTRAINT EStimNeighborScores_session_fk
                FOREIGN KEY (session_id) REFERENCES Sessions (session_id) ON DELETE CASCADE
        ) ENGINE = InnoDB DEFAULT CHARSET = latin1
        """
    )


def save_session_neighbor_scores(repo_conn, session_id, results_by_config):
    """Upsert all scores for a session. results_by_config maps
    (n_neighbors, exclude_other_estim) -> {spec_id: {metric_name: {agg: value}}}."""
    n_rows = 0
    for (n_neighbors, exclude_other_estim), scores_by_spec in sorted(results_by_config.items()):
        for spec_id, per_metric in sorted(scores_by_spec.items()):
            for metric_name, aggs in per_metric.items():
                for aggregation, value in aggs.items():
                    repo_conn.execute(
                        """
                        INSERT INTO EStimNeighborScores
                            (session_id, estim_spec_id, metric_name, aggregation,
                             n_neighbors, exclude_other_estim, value)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE value = VALUES(value)
                        """,
                        (session_id, int(spec_id), metric_name, aggregation,
                         int(n_neighbors), 1 if exclude_other_estim else 0,
                         float(value) if value is not None else None),
                    )
                    n_rows += 1
    print(f"  {session_id}: upserted {n_rows} metric rows "
          f"({len(results_by_config)} neighbourhood configs)")


# ---------------------------------------------------------------------------
# Batch runner
# ---------------------------------------------------------------------------

def _sessions_with_estim():
    """Sessions with at least one actively-stimulating channel."""
    conn = Connection("allen_data_repository")
    conn.execute("SELECT DISTINCT session_id FROM EStimParameters WHERE a1 > 0 "
                 "ORDER BY session_id")
    return [row[0] for row in conn.fetch_all()]


def run_for_sessions(start_session_id=None, exclude_session_ids=None, *,
                     n_neighbors_list=(3,), exclude_other_estim_list=(True,),
                     top_ns=TOP_N_DEFAULTS, pca_components=2, n_loading_pcs=10,
                     corr_method='spearman'):
    """Compute and persist all neighbour-similarity metrics across sessions, for
    every (n_neighbors, exclude_other_estim) combination in the given lists.

    Sweeping n_neighbors lets analyze_estim_isolation_effect.plot_neighbor_sweep
    show how each metric's correlation with the effect changes with neighbourhood
    size. Sessions that raise (missing GA DB, missing vectors, etc.) are reported
    but don't abort the run."""
    repo_conn = Connection("allen_data_repository")
    _ensure_neighbor_scores_table(repo_conn)

    session_ids = _sessions_with_estim()
    if start_session_id is not None:
        session_ids = [s for s in session_ids if s >= start_session_id]
    if exclude_session_ids:
        excluded = set(exclude_session_ids)
        session_ids = [s for s in session_ids if s not in excluded]

    print(f"Neighbour-metric scoring {len(session_ids)} sessions "
          f"(start={start_session_id}, "
          f"excluded={sorted(exclude_session_ids) if exclude_session_ids else []}, "
          f"n_neighbors_list={tuple(n_neighbors_list)}, "
          f"exclude_other_estim_list={tuple(exclude_other_estim_list)}, "
          f"top_ns={top_ns}, pca_components={pca_components}, "
          f"n_loading_pcs={n_loading_pcs}, corr_method={corr_method})")

    failed = []
    for sid in session_ids:
        print(f"\n=== {sid} ===")
        try:
            results = compute_session_neighbor_scores(
                sid, n_neighbors_list=n_neighbors_list,
                exclude_other_estim_list=exclude_other_estim_list,
                top_ns=top_ns, pca_components=pca_components,
                n_loading_pcs=n_loading_pcs, corr_method=corr_method,
                repo_conn=repo_conn)
        except Exception:
            traceback.print_exc()
            failed.append(sid)
            continue
        if results:
            save_session_neighbor_scores(repo_conn, sid, results)

    if failed:
        print(f"\nSessions that failed: {failed}")
    print("\nDone.")
    return failed


def main():
    run_for_sessions(
        start_session_id="260402_0",        # e.g. "260402_0"; None = all sessions
        exclude_session_ids=None,     # e.g. ["260421_0", "260410_0"]
        # Neighbourhood-size sweep: every value is computed and stored, so
        # plot_neighbor_sweep can show correlation-with-effect vs n_neighbors.
        n_neighbors_list=(1, 2, 3,4, 5, 8),
        # Add False to also sweep including the spec's other estim channels as
        # neighbours, e.g. exclude_other_estim_list=(True, False).
        exclude_other_estim_list=(True,False),
        top_ns=TOP_N_DEFAULTS,        # (20, 50, 100)
        pca_components=2,             # 2 matches the cluster app
        n_loading_pcs=4,             # PCs compared for pc_loading_sim
        corr_method='spearman',       # 'spearman' (preference_cluster) | 'pearson'
    )


if __name__ == '__main__':
    main()
