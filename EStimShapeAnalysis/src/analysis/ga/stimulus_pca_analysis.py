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

The stimulus scatter figures (colored by texture / lineage / GA response /
StimType / center-of-mass / AlexNet, with the included delta/variant stimuli
ringed) are drawn by the shared ``stimulus_scatter_figures`` engine, which the
cluster_app PC-interpretation exporter reuses to draw the same overlays in
loading space.
"""

import os
from dataclasses import dataclass, field
from typing import Optional, Sequence

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from scipy.cluster.hierarchy import fcluster, linkage
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from src.analysis.ga.plot_top_n import PlotTopNAnalysis
from src.analysis.ga.ga_raster_analysis import CHANNEL_ORDER
from src.cluster.stimulus_scatter_figures import (
    StimulusScatterFigures, build_highlight_spec, dataframe_value_lookup)
from src.repository.export_to_repository import read_session_id_and_date_from_db_name
from src.startup import context

# Channel names in probe order, A-000 .. A-031 arranged top-to-bottom on the
# probe. Used as the default feature set and to order the loadings heatmap.
PROBE_CHANNELS = [f"A-{i:03d}" for i in CHANNEL_ORDER]

# Variance-explained thresholds reported by the scree analysis ("how many PCs
# is enough").
VARIANCE_THRESHOLDS = (0.80, 0.90, 0.95)

# StimTypes always dropped from the analysis (and therefore every plot), on top
# of these defaults. Shuffle side-test stimuli are control conditions, not part
# of the encoding population we want to characterize.
DEFAULT_EXCLUDED_STIM_TYPES = ("SHUFFLE_PIXEL", "SHUFFLE_PHASE", "SHUFFLE_MAGNITUDE")

# Non-stimulus rows that are always dropped regardless of the exclusion list.
ALWAYS_EXCLUDED_STIM_TYPES = ("BASELINE", "CATCH")


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


# Path to the AlexNet ONNX model exposing a conv3 output (same one the alexnet
# GA pipeline uses). Set to None to disable AlexNet coloring.
ALEXNET_ONNX_PATH = "/home/connorlab/git/EStimShape/EStimShapeAnalysis/data/AlexNetONNX_with_conv3"


def make_alexnet_embedder(onnx_path: Optional[str]):
    """Build an AlexNet conv3-PCA embedder, or None if it can't be constructed
    (missing model file or the onnx/torch stack not installed)."""
    if not onnx_path or not os.path.exists(onnx_path):
        print(f"AlexNet coloring disabled: ONNX model not found at {onnx_path}.")
        return None
    try:
        from src.analysis.ga.alexnet_embedding import AlexNetLayer3PCAEmbedder
        return AlexNetLayer3PCAEmbedder(onnx_path)
    except Exception as exc:
        print(f"AlexNet coloring disabled: {exc}")
        return None


def main():
    analysis = StimulusPCAAnalysis(
        standardize=True,
        n_loading_pcs=None,          # None -> use the elbow estimate
        n_channel_clusters=4,        # None -> cut the dendrogram by distance
        # AlexNet coloring shows up only when an embedder (or precomputed
        # alexnet_pcs) is supplied; otherwise that one plot is simply skipped.
        alexnet_embedder=make_alexnet_embedder(ALEXNET_ONNX_PATH),
    )
    session_id, _ = read_session_id_and_date_from_db_name(context.ga_database)
    # session_id = "260626_0"
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
        alexnet_embedder: optional object with ``embed({stim_id: path}) ->
            {stim_id: pc_vector}`` (e.g. ``AlexNetLayer3PCAEmbedder``). When
            provided, stimuli are also colored by their first two AlexNet
            conv3-PCA coordinates.
        alexnet_pcs: optional precomputed ``{stim_id: (pc1, pc2)}`` mapping,
            used instead of running ``alexnet_embedder``.
        highlighted_stim_ids: optional StimSpecIds to ring on every scatter for
            special attention. Either a set (role inferred from StimType) or a
            dict ``{stim_id: 'delta' | 'variant'}`` to control ring color.
            ``None`` falls back to the ``IncludedDeltas`` table (the included
            REGIME_ESTIM_DELTA stimuli and their paired REGIME_ESTIM_VARIANTS),
            which already carry their roles.
        excluded_stim_types: StimTypes to drop from the whole analysis (PCA and
            every plot). Defaults to the shuffle side-test controls
            (``DEFAULT_EXCLUDED_STIM_TYPES``); pass a list/set to override, or
            ``[]`` to keep everything. BASELINE/CATCH are always dropped.
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
        alexnet_embedder=None,
        alexnet_pcs: Optional[dict] = None,
        highlighted_stim_ids: Optional[set] = None,
        excluded_stim_types: Optional[Sequence[str]] = None,
        use_baseline_correction: bool = False,
    ):
        super().__init__(use_baseline_correction=use_baseline_correction)
        self.standardize = standardize
        self.n_loading_pcs = n_loading_pcs
        self.n_channel_clusters = n_channel_clusters
        self.cluster_distance_threshold = cluster_distance_threshold
        self.channels = list(channels) if channels is not None else None
        self.alexnet_embedder = alexnet_embedder
        self.alexnet_pcs = alexnet_pcs
        self.highlighted_stim_ids = highlighted_stim_ids
        self.excluded_stim_types = (list(DEFAULT_EXCLUDED_STIM_TYPES)
                                    if excluded_stim_types is None
                                    else list(excluded_stim_types))

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

        # Drop non-stimulus rows (baseline/catch) and any user-excluded StimTypes.
        # Filtering here removes them from the PCA and, since every plot keys off
        # response_matrix.index, from all plots too.
        if 'StimType' in data.columns:
            dropped = list(ALWAYS_EXCLUDED_STIM_TYPES) + list(self.excluded_stim_types)
            before = data['StimSpecId'].nunique()
            data = data[~data['StimType'].isin(dropped)]
            after = data['StimSpecId'].nunique()
            if self.excluded_stim_types:
                print(f"Excluding StimTypes {sorted(set(self.excluded_stim_types))}: "
                      f"{before - after} stimulus(es) dropped, {after} remain.")
        elif self.excluded_stim_types:
            print("StimType column absent; cannot apply excluded_stim_types.")

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
        value_lookup = dataframe_value_lookup(compiled_data)
        stim_ids = list(result.response_matrix.index)

        # Stimuli to ring for special attention (included deltas + their variants),
        # split by role so deltas and variants get different ring colors.
        highlight = build_highlight_spec(
            stim_ids, context.ga_database,
            stim_type_for_id=value_lookup('StimType'),
            override=self.highlighted_stim_ids)

        # The shared engine draws the stimulus scatters; batch mode uses
        # pyplot-managed figures so the trailing plt.show() picks them up.
        scatter = StimulusScatterFigures(
            scores, stim_ids, value_lookup,
            variance_ratio=result.explained_variance_ratio,
            highlight=highlight, space="score",
            figure_factory=plt.figure)

        paths = [
            self._plot_scree(result, label),
            self._plot_loadings_heatmap(result, label),
        ]
        # AlexNet conv3-PCA coloring (first two PCs -> a 2D color), if available.
        alexnet_pcs = self._resolve_alexnet_pcs(value_lookup)
        for sf in scatter.build_standard(alexnet_pcs=alexnet_pcs):
            paths.append(self._save(sf.figure, f"{label}_stimulus_by_{sf.slug}"))
        # Binned example thumbnails along each of PC1..PC4.
        for pc_idx in range(min(4, scores.shape[1])):
            paths.append(self._plot_pc_examples(result, scores, compiled_data, pc_idx, label))
        result.figure_paths = [p for p in paths if p is not None]

    def _resolve_alexnet_pcs(self, value_lookup) -> Optional[dict]:
        """Per-stimulus AlexNet conv3-PCA coordinates: a precomputed dict if
        given, else computed by the injected embedder from stimulus images."""
        if self.alexnet_pcs is not None:
            return self.alexnet_pcs
        if self.alexnet_embedder is None:
            return None
        paths = value_lookup('StimPath') or value_lookup('ThumbnailPath')
        if not paths:
            print("AlexNet coloring skipped: no StimPath/ThumbnailPath column.")
            return None
        return self.alexnet_embedder.embed(paths)

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

    def _plot_pc_examples(self, result: StimulusPCAResult, scores: np.ndarray,
                          compiled_data: pd.DataFrame, pc_idx: int, label: str,
                          n_bins: int = 5, n_per_bin: int = 6) -> Optional[str]:
        """Grid of example thumbnails for one PC: rows are equal-width value
        ranges of the PC (high at top), each row showing several example stimuli
        drawn from that range."""
        thumbs = dataframe_value_lookup(compiled_data)('ThumbnailPath')
        if thumbs is None:
            print(f"Skipping PC{pc_idx + 1} examples: 'ThumbnailPath' not available.")
            return None

        stim_ids = list(result.response_matrix.index)
        pc = scores[:, pc_idx]
        lo, hi = float(np.min(pc)), float(np.max(pc))
        if hi - lo < 1e-12:
            print(f"Skipping PC{pc_idx + 1} examples: no spread along this PC.")
            return None
        edges = np.linspace(lo, hi, n_bins + 1)

        fig, axes = plt.subplots(n_bins, n_per_bin,
                                 figsize=(2.0 * n_per_bin, 2.3 * n_bins),
                                 squeeze=False)
        for row in range(n_bins):
            bin_idx = n_bins - 1 - row  # top row = highest range
            b_lo, b_hi = edges[bin_idx], edges[bin_idx + 1]
            if bin_idx == n_bins - 1:  # include the right edge in the top bin
                in_bin = np.where((pc >= b_lo) & (pc <= b_hi))[0]
            else:
                in_bin = np.where((pc >= b_lo) & (pc < b_hi))[0]
            in_bin = in_bin[np.argsort(pc[in_bin])]
            if len(in_bin) > n_per_bin:
                sel = in_bin[np.linspace(0, len(in_bin) - 1, n_per_bin).round().astype(int)]
            else:
                sel = in_bin

            for col in range(n_per_bin):
                ax = axes[row][col]
                if col < len(sel):
                    self._show_thumb(ax, thumbs.get(stim_ids[sel[col]]))
                else:
                    ax.axis('off')
            # Range label on the leftmost cell (frame off, keep the y-label).
            left = axes[row][0]
            left.set_xticks([])
            left.set_yticks([])
            for spine in left.spines.values():
                spine.set_visible(False)
            left.set_ylabel(f"[{b_lo:.1f}, {b_hi:.1f}]\nn={len(in_bin)}",
                            fontsize=8, rotation=0, ha='right', va='center', labelpad=28)

        evr = result.explained_variance_ratio
        fig.suptitle(f"Example stimuli by PC{pc_idx + 1} range "
                     f"({evr[pc_idx] * 100:.1f}% var; top = high)")
        fig.tight_layout()
        return self._save(fig, f"{label}_pc{pc_idx + 1}_examples")

    @staticmethod
    def _show_thumb(ax, path: Optional[str]) -> None:
        ax.set_xticks([])
        ax.set_yticks([])
        if path and os.path.exists(path):
            try:
                ax.imshow(plt.imread(path))
                return
            except Exception:  # unreadable image -> placeholder, keep going
                ax.text(0.5, 0.5, "(unreadable)", ha='center', va='center', fontsize=6)
        else:
            ax.text(0.5, 0.5, "(no thumb)", ha='center', va='center',
                    fontsize=7, color='gray')


if __name__ == "__main__":
    main()
