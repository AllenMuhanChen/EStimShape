from __future__ import annotations

"""Stimulus-as-point PCA over the channel response space.

This is the *flipped* counterpart to the cluster_app dimensionality reduction.

  cluster_app:  each **channel** is a point. Its high-dim coordinates are its
                responses to every stimulus. PCA reduces the stimulus axis.

  this module:  each **stimulus** is a point. Its high-dim coordinates are the
                responses it evoked on every channel. PCA reduces the channel
                axis.

Why flip it? Running PCA on the (n_stimuli x n_channels) matrix asks a
different question:

  * The scree plot tells us how many components are needed to explain the
    population's response to the stimulus set, i.e. the effective
    dimensionality of what V4 is encoding here.

  * The PCA **loadings** assign every channel a weight on each component.
    Channels that load similarly are responding to the same underlying
    stimulus dimension -- so clustering channels in *loading space* is a
    principled way to recover groups of channels that encode the same
    shape / information, which is exactly what the cluster_app GUI is trying
    to do by hand.

No GUI: this is a batch analysis class modeled on ``PlotTopNAnalysis``. It
reuses that class's GA compile / import / export pipeline, and overrides
``analyze`` to build the stimulus x channel matrix, run PCA, draw the scree
and loadings figures, and cluster the channels by their loadings.
"""

from dataclasses import dataclass, field
from typing import Optional, Sequence

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from scipy.cluster.hierarchy import dendrogram, fcluster, linkage
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from src.analysis.ga.plot_top_n import PlotTopNAnalysis
from src.analysis.ga.ga_raster_analysis import CHANNEL_ORDER
from src.repository.export_to_repository import read_session_id_and_date_from_db_name
from src.startup import context

# Channel names in probe order, A-000 .. A-031 arranged top-to-bottom on the
# probe. Used as the default feature set and to order the loadings heatmap.
PROBE_CHANNELS = [f"A-{i:03d}" for i in CHANNEL_ORDER]

# Variance-explained thresholds reported by the scree analysis ("how many PCs
# is enough").
VARIANCE_THRESHOLDS = (0.80, 0.90, 0.95)


@dataclass
class StimulusPCAResult:
    """Everything the flipped PCA produces, so callers can introspect / re-plot
    without re-running the analysis."""

    # (n_stimuli x n_channels) mean response matrix. Index = StimSpecId,
    # columns = channel names (probe order).
    response_matrix: pd.DataFrame
    # The fitted sklearn PCA (samples = stimuli, features = channels).
    pca: PCA
    # Per-component fraction of variance explained, and its cumulative sum.
    explained_variance_ratio: np.ndarray
    cumulative_variance: np.ndarray
    # {threshold -> #PCs needed to reach it}, plus a scree-elbow estimate.
    n_pcs_for_threshold: dict[float, int]
    elbow_n_pcs: int
    # Channel loadings: index = channel, columns = PC1..PCk. loading[j, k] is
    # channel j's correlation-scaled weight on component k.
    loadings: pd.DataFrame
    # Flat channel clustering derived from the loadings: {channel -> cluster id}.
    channel_clusters: dict[str, int]
    # SciPy linkage matrix over channels (for the dendrogram / custom cuts).
    linkage_matrix: np.ndarray
    # Paths of the figures written to disk.
    figure_paths: list[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"Stimuli (points): {self.response_matrix.shape[0]}",
            f"Channels (features): {self.response_matrix.shape[1]}",
            f"Scree elbow at ~{self.elbow_n_pcs} PC(s).",
        ]
        for thr, n in self.n_pcs_for_threshold.items():
            lines.append(f"  {int(thr * 100)}% variance reached at {n} PC(s).")
        n_clusters = len(set(self.channel_clusters.values()))
        lines.append(f"Channels grouped into {n_clusters} loading-based cluster(s):")
        by_cluster: dict[int, list[str]] = {}
        for ch, cl in self.channel_clusters.items():
            by_cluster.setdefault(cl, []).append(ch)
        for cl in sorted(by_cluster):
            members = ", ".join(sorted(by_cluster[cl]))
            lines.append(f"  Cluster {cl}: {members}")
        return "\n".join(lines)


def main():
    analysis = StimulusPCAAnalysis(
        standardize=True,
        n_loading_pcs=None,          # None -> use the elbow estimate
        n_channel_clusters=4,        # None -> cut the dendrogram by distance
    )
    session_id, _ = read_session_id_and_date_from_db_name(context.ga_database)
    compiled_data = None
    # compiled_data = analysis.compile_and_export()
    analysis.run(session_id, "raw", "ALL", compiled_data=compiled_data)


class StimulusPCAAnalysis(PlotTopNAnalysis):
    """PCA over stimuli (points) in channel-response space, plus channel
    clustering by PCA loadings.

    Reuses ``PlotTopNAnalysis``'s GA compile/import/export so the same raw
    Intan spike data flows in; only ``analyze`` is overridden.

    Args:
        standardize: z-score each channel (feature) before PCA so that
            high-firing channels don't dominate the components. Mirrors the
            per-channel normalization the cluster_app GUI applies.
        n_loading_pcs: how many leading PCs to use when describing/clustering
            channels in loading space. ``None`` uses the scree-elbow estimate.
        n_channel_clusters: number of channel clusters to cut the loading
            dendrogram into. ``None`` cuts by distance threshold instead.
        cluster_distance_threshold: fraction of the max merge distance used as
            the cut height when ``n_channel_clusters`` is ``None``.
        channels: explicit feature channel list; defaults to all probe
            channels that carry varying data. The ``channel`` argument passed to
            ``run``/``analyze`` overrides this when it is a list.
    """

    logging_path = context.logging_path

    def __init__(
        self,
        *,
        standardize: bool = True,
        n_loading_pcs: Optional[int] = None,
        n_channel_clusters: Optional[int] = 4,
        cluster_distance_threshold: float = 0.7,
        channels: Optional[Sequence[str]] = None,
        use_baseline_correction: bool = False,
    ):
        super().__init__(use_baseline_correction=use_baseline_correction)
        self.standardize = standardize
        self.n_loading_pcs = n_loading_pcs
        self.n_channel_clusters = n_channel_clusters
        self.cluster_distance_threshold = cluster_distance_threshold
        self.channels = list(channels) if channels is not None else None

    # ---- main entry point ------------------------------------------------
    def analyze(self, channel, compiled_data: pd.DataFrame = None) -> StimulusPCAResult:
        # A list passed as `channel` selects the feature channels; any scalar
        # (e.g. "ALL"/"GA") means "use the configured / all probe channels".
        feature_channels = channel if isinstance(channel, list) else self.channels

        response_matrix = self._build_response_matrix(compiled_data, feature_channels)
        if response_matrix.shape[0] < 2 or response_matrix.shape[1] < 2:
            raise ValueError(
                f"Need >=2 stimuli and >=2 channels for PCA; got "
                f"{response_matrix.shape[0]} stimuli x {response_matrix.shape[1]} channels."
            )

        pca, scores, X = self._fit_pca(response_matrix)
        evr = pca.explained_variance_ratio_
        cumulative = np.cumsum(evr)
        n_pcs_for_threshold = {
            thr: int(np.searchsorted(cumulative, thr) + 1) for thr in VARIANCE_THRESHOLDS
        }
        elbow = self._estimate_elbow(cumulative)

        loadings = self._compute_loadings(pca, response_matrix.columns)
        n_loading_pcs = self.n_loading_pcs or max(2, min(elbow, loadings.shape[1]))
        linkage_matrix, channel_clusters = self._cluster_channels(loadings, n_loading_pcs)

        result = StimulusPCAResult(
            response_matrix=response_matrix,
            pca=pca,
            explained_variance_ratio=evr,
            cumulative_variance=cumulative,
            n_pcs_for_threshold=n_pcs_for_threshold,
            elbow_n_pcs=elbow,
            loadings=loadings,
            channel_clusters=channel_clusters,
            linkage_matrix=linkage_matrix,
        )

        self._plot_all(result, scores, n_loading_pcs, compiled_data)
        print(result.summary())
        plt.show()
        return result

    # ---- matrix construction --------------------------------------------
    def _build_response_matrix(
        self, compiled_data: pd.DataFrame, feature_channels: Optional[Sequence[str]]
    ) -> pd.DataFrame:
        """Average the per-channel spike rates within each stimulus to get a
        (n_stimuli x n_channels) matrix."""
        data = compiled_data.copy()

        # Drop non-stimulus rows (baselines / catch trials) when typed.
        if 'StimType' in data.columns:
            data = data[~data['StimType'].isin(['BASELINE', 'CATCH'])]

        spike_rates_col = self.spike_rates_col  # 'Spike Rate by channel' for raw
        data = data[data[spike_rates_col].notna()]

        # Explode the per-trial {channel: rate} dicts into channel columns, then
        # average across trials of the same stimulus.
        rates = pd.json_normalize(data[spike_rates_col]).set_index(data.index)
        rates['StimSpecId'] = data['StimSpecId'].values
        matrix = rates.groupby('StimSpecId').mean().fillna(0.0)

        matrix = self._select_channels(matrix, feature_channels)
        return matrix

    def _select_channels(
        self, matrix: pd.DataFrame, feature_channels: Optional[Sequence[str]]
    ) -> pd.DataFrame:
        if feature_channels is not None:
            wanted = [ch for ch in feature_channels if ch in matrix.columns]
        else:
            # All probe channels that are actually present, in probe order.
            wanted = [ch for ch in PROBE_CHANNELS if ch in matrix.columns]
            # Include any stray channels not in the canonical order, too.
            wanted += [ch for ch in matrix.columns if ch not in wanted]

        matrix = matrix[wanted]

        # Drop dead channels (no variance) -- they break z-scoring and carry no
        # information for PCA / clustering.
        varying = matrix.columns[matrix.std(axis=0) > 1e-10]
        dropped = [ch for ch in matrix.columns if ch not in varying]
        if dropped:
            print(f"Dropping {len(dropped)} channel(s) with no variance: {dropped}")
        return matrix[varying]

    # ---- PCA -------------------------------------------------------------
    def _fit_pca(self, response_matrix: pd.DataFrame):
        X = response_matrix.to_numpy(dtype=float)
        if self.standardize:
            X = StandardScaler().fit_transform(X)
        n_components = min(X.shape)  # min(n_stimuli, n_channels)
        pca = PCA(n_components=n_components)
        scores = pca.fit_transform(X)
        return pca, scores, X

    @staticmethod
    def _estimate_elbow(cumulative: np.ndarray) -> int:
        """Kneedle-style elbow: the PC whose cumulative-variance point lies
        farthest from the straight line joining the first and last points."""
        n = len(cumulative)
        if n <= 2:
            return n
        xs = np.arange(n, dtype=float)
        x0, y0 = xs[0], cumulative[0]
        x1, y1 = xs[-1], cumulative[-1]
        # Perpendicular distance from each (x, cumulative[x]) to the end-to-end line.
        denom = np.hypot(x1 - x0, y1 - y0)
        if denom == 0:
            return 1
        distances = np.abs(
            (y1 - y0) * xs - (x1 - x0) * cumulative + x1 * y0 - y1 * x0
        ) / denom
        return int(np.argmax(distances) + 1)

    @staticmethod
    def _compute_loadings(pca: PCA, channels: Sequence[str]) -> pd.DataFrame:
        """Correlation-scaled loadings: components_.T * sqrt(eigenvalue).

        With standardized features these are the channel/PC correlations, which
        is the right space to cluster channels in -- two channels with similar
        loading vectors respond to the same stimulus dimensions.
        """
        loadings = pca.components_.T * np.sqrt(pca.explained_variance_)
        columns = [f"PC{i + 1}" for i in range(loadings.shape[1])]
        return pd.DataFrame(loadings, index=list(channels), columns=columns)

    # ---- channel clustering ---------------------------------------------
    def _cluster_channels(self, loadings: pd.DataFrame, n_loading_pcs: int):
        """Hierarchically cluster channels by their loading vectors over the
        leading ``n_loading_pcs`` PCs."""
        feature_block = loadings.iloc[:, :n_loading_pcs].to_numpy()
        # Correlation distance: groups channels whose loading *patterns* match,
        # regardless of overall magnitude. Falls back to euclidean if a channel
        # has a degenerate (constant) loading vector.
        try:
            linkage_matrix = linkage(feature_block, method='average', metric='correlation')
            if not np.all(np.isfinite(linkage_matrix[:, 2])):
                raise ValueError("non-finite correlation distances")
        except (ValueError, FloatingPointError):
            linkage_matrix = linkage(feature_block, method='ward', metric='euclidean')

        if self.n_channel_clusters is not None:
            labels = fcluster(linkage_matrix, t=self.n_channel_clusters, criterion='maxclust')
        else:
            max_d = self.cluster_distance_threshold * linkage_matrix[:, 2].max()
            labels = fcluster(linkage_matrix, t=max_d, criterion='distance')

        channel_clusters = {ch: int(lbl) for ch, lbl in zip(loadings.index, labels)}
        return linkage_matrix, channel_clusters

    # ---- plotting --------------------------------------------------------
    def _plot_all(self, result: StimulusPCAResult, scores: np.ndarray,
                  n_loading_pcs: int, compiled_data: pd.DataFrame) -> None:
        label = self._label()
        result.figure_paths = [
            self._plot_scree(result, label),
            self._plot_loadings_heatmap(result, label),
            self._plot_channel_dendrogram(result, n_loading_pcs, label),
            self._plot_channel_loading_space(result, n_loading_pcs, label),
            self._plot_stimulus_scatter(result, scores, compiled_data, label),
        ]

    def _label(self) -> str:
        suffix = "_std" if self.standardize else ""
        return f"stimulus_pca{suffix}"

    def _save(self, fig, name: str) -> str:
        path = f"{self.save_path}/{name}.png"
        fig.savefig(path, dpi=150, bbox_inches='tight')
        print(f"Saved {path}")
        return path

    def _plot_scree(self, result: StimulusPCAResult, label: str) -> str:
        evr = result.explained_variance_ratio
        cumulative = result.cumulative_variance
        xs = np.arange(1, len(evr) + 1)

        fig, ax1 = plt.subplots(figsize=(8, 5))
        ax1.bar(xs, evr, color='steelblue', edgecolor='black', linewidth=0.5,
                label='Per-PC variance')
        ax1.set_xlabel("Principal component")
        ax1.set_ylabel("Variance explained", color='steelblue')
        ax1.tick_params(axis='y', labelcolor='steelblue')

        ax2 = ax1.twinx()
        ax2.plot(xs, cumulative, color='darkorange', marker='o', label='Cumulative')
        ax2.set_ylabel("Cumulative variance", color='darkorange')
        ax2.tick_params(axis='y', labelcolor='darkorange')
        ax2.set_ylim(0, 1.02)

        for thr, n in result.n_pcs_for_threshold.items():
            ax2.axhline(thr, color='gray', linestyle=':', linewidth=0.8)
            ax2.annotate(f"{int(thr * 100)}% @ PC{n}", xy=(n, thr),
                         xytext=(3, 3), textcoords='offset points', fontsize=8,
                         color='gray')
        ax1.axvline(result.elbow_n_pcs, color='red', linestyle='--', linewidth=1,
                    label=f'Elbow (PC{result.elbow_n_pcs})')

        ax1.set_title("Scree: how many PCs explain the stimulus responses")
        ax1.set_xticks(xs)
        fig.legend(loc='upper right', bbox_to_anchor=(0.98, 0.92), fontsize=8)
        fig.tight_layout()
        return self._save(fig, f"{label}_scree")

    def _plot_loadings_heatmap(self, result: StimulusPCAResult, label: str) -> str:
        # Show loadings for the components up through the 90%-variance mark
        # (at least 5) so the heatmap stays legible.
        n_show = max(5, result.n_pcs_for_threshold[0.90])
        n_show = min(n_show, result.loadings.shape[1])
        block = result.loadings.iloc[:, :n_show]

        fig, ax = plt.subplots(figsize=(max(6, n_show * 0.6),
                                        max(5, len(block) * 0.22)))
        vmax = np.abs(block.to_numpy()).max()
        im = ax.imshow(block.to_numpy(), aspect='auto', cmap='RdBu_r',
                       vmin=-vmax, vmax=vmax)
        ax.set_xticks(range(n_show))
        ax.set_xticklabels(block.columns, rotation=45, ha='right')
        ax.set_yticks(range(len(block)))
        ax.set_yticklabels(block.index, fontsize=7)
        ax.set_xlabel("Principal component")
        ax.set_ylabel("Channel")
        ax.set_title("Channel loadings on each PC")
        fig.colorbar(im, ax=ax, label="Loading")
        fig.tight_layout()
        return self._save(fig, f"{label}_loadings_heatmap")

    def _plot_channel_dendrogram(self, result: StimulusPCAResult, n_loading_pcs: int,
                                 label: str) -> str:
        fig, ax = plt.subplots(figsize=(max(8, len(result.loadings) * 0.28), 5))
        dendrogram(
            result.linkage_matrix,
            labels=list(result.loadings.index),
            ax=ax,
            leaf_rotation=90,
            leaf_font_size=7,
        )
        ax.set_title(
            f"Channel clustering by loadings (first {n_loading_pcs} PCs)"
        )
        ax.set_ylabel("Distance")
        fig.tight_layout()
        return self._save(fig, f"{label}_channel_dendrogram")

    def _plot_channel_loading_space(self, result: StimulusPCAResult,
                                    n_loading_pcs: int, label: str) -> str:
        loadings = result.loadings
        x = loadings['PC1'].to_numpy()
        y = loadings['PC2'].to_numpy()
        clusters = np.array([result.channel_clusters[ch] for ch in loadings.index])

        fig, ax = plt.subplots(figsize=(7, 7))
        scatter = ax.scatter(x, y, c=clusters, cmap='tab10', s=60,
                             edgecolor='black', linewidth=0.5)
        for ch, xi, yi in zip(loadings.index, x, y):
            ax.annotate(ch.split('-')[-1], (xi, yi), fontsize=7,
                        xytext=(3, 3), textcoords='offset points')
        ax.axhline(0, color='gray', linewidth=0.5)
        ax.axvline(0, color='gray', linewidth=0.5)
        ax.set_xlabel("PC1 loading")
        ax.set_ylabel("PC2 loading")
        ax.set_title("Channels in loading space (colored by cluster)")
        legend = ax.legend(*scatter.legend_elements(), title="Cluster",
                           loc='best', fontsize=8)
        ax.add_artist(legend)
        fig.tight_layout()
        return self._save(fig, f"{label}_channel_loading_space")

    def _plot_stimulus_scatter(self, result: StimulusPCAResult, scores: np.ndarray,
                               compiled_data: pd.DataFrame, label: str) -> str:
        """Stimuli as points in PC1/PC2 score space, colored by lineage when
        available -- the direct analog of the cluster_app scatter, flipped."""
        fig, ax = plt.subplots(figsize=(7, 7))

        lineage_by_stim = self._lineage_lookup(compiled_data)
        if lineage_by_stim is not None:
            lineages = [lineage_by_stim.get(sid, -1) for sid in result.response_matrix.index]
            codes = pd.factorize(np.asarray(lineages))[0]
            sc = ax.scatter(scores[:, 0], scores[:, 1], c=codes, cmap='tab20',
                            s=25, alpha=0.8)
            ax.set_title("Stimuli in PC space (colored by lineage)")
        else:
            ax.scatter(scores[:, 0], scores[:, 1], s=25, alpha=0.8, color='steelblue')
            ax.set_title("Stimuli in PC space")

        evr = result.explained_variance_ratio
        ax.set_xlabel(f"PC1 ({evr[0] * 100:.1f}%)")
        ax.set_ylabel(f"PC2 ({evr[1] * 100:.1f}%)")
        fig.tight_layout()
        return self._save(fig, f"{label}_stimulus_scatter")

    @staticmethod
    def _lineage_lookup(compiled_data: pd.DataFrame) -> Optional[dict]:
        if compiled_data is None or 'Lineage' not in compiled_data.columns:
            return None
        sub = compiled_data[['StimSpecId', 'Lineage']].dropna().drop_duplicates('StimSpecId')
        return dict(zip(sub['StimSpecId'], sub['Lineage']))


if __name__ == "__main__":
    main()
