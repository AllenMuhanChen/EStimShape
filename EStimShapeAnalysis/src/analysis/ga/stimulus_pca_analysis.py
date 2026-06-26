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
        paths = [
            self._plot_scree(result, label),
            self._plot_loadings_heatmap(result, label),
        ]
        # Show stimuli in PC1/PC2 always, and PC3/PC4 when enough PCs exist.
        pc_pairs = [(0, 1)]
        if scores.shape[1] >= 4:
            pc_pairs.append((2, 3))
        for px, py in pc_pairs:
            paths.append(self._plot_stimulus_scatter_categorical(
                result, scores, compiled_data, 'Lineage', label, px, py, cmap='tab20'))
            paths.append(self._plot_stimulus_scatter_continuous(
                result, scores, compiled_data, 'GA Response', label, px, py))
            paths.append(self._plot_stimulus_scatter_categorical(
                result, scores, compiled_data, 'Texture', label, px, py, cmap='Set1'))
            # Center of mass: (x, y, z) mapped to RGB so similar colors == similar CoM.
            paths.append(self._plot_stimulus_scatter_rgb(
                result, scores, compiled_data, 'MassCenter', label, px, py))
        # Example thumbnails sampled along PC1.
        paths.append(self._plot_pc1_examples(result, scores, compiled_data, label))
        result.figure_paths = [p for p in paths if p is not None]

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

    def _axis_labels(self, ax, result: StimulusPCAResult, pc_x: int, pc_y: int) -> None:
        evr = result.explained_variance_ratio
        ax.set_xlabel(f"PC{pc_x + 1} ({evr[pc_x] * 100:.1f}%)")
        ax.set_ylabel(f"PC{pc_y + 1} ({evr[pc_y] * 100:.1f}%)")

    def _plot_stimulus_scatter_categorical(
        self, result: StimulusPCAResult, scores: np.ndarray,
        compiled_data: pd.DataFrame, column: str, label: str,
        pc_x: int, pc_y: int, cmap: str = 'tab20') -> Optional[str]:
        """Stimuli in PCx/PCy score space, one color per discrete `column`
        value (e.g. Lineage, Texture)."""
        values = self._stim_value_lookup(compiled_data, column)
        if values is None:
            print(f"Skipping '{column}' scatter: column not available.")
            return None

        per_stim = np.array([values.get(sid, None) for sid in result.response_matrix.index],
                            dtype=object)
        categories = [c for c in pd.unique(per_stim) if c is not None]
        color_map = plt.get_cmap(cmap)

        fig, ax = plt.subplots(figsize=(7, 7))
        # Missing values first, in light gray, so they don't crowd the legend.
        missing = per_stim == None  # noqa: E711  (elementwise on object array)
        if missing.any():
            ax.scatter(scores[missing, pc_x], scores[missing, pc_y], s=20,
                       color='lightgray', alpha=0.6, label='(missing)')
        for i, cat in enumerate(categories):
            mask = per_stim == cat
            ax.scatter(scores[mask, pc_x], scores[mask, pc_y], s=25, alpha=0.8,
                       color=color_map(i % color_map.N), label=str(cat))

        ax.set_title(f"Stimuli in PC space ({self._pc_pair_label(pc_x, pc_y)}, "
                     f"colored by {column})")
        self._axis_labels(ax, result, pc_x, pc_y)
        # A legend is only useful for a manageable number of categories.
        if len(categories) <= 20:
            ax.legend(title=column, loc='best', fontsize=8, markerscale=1.2)
        fig.tight_layout()
        return self._save(
            fig, f"{label}_stimulus_{self._pc_tag(pc_x, pc_y)}_by_{self._slug(column)}")

    def _plot_stimulus_scatter_continuous(
        self, result: StimulusPCAResult, scores: np.ndarray,
        compiled_data: pd.DataFrame, column: str, label: str,
        pc_x: int, pc_y: int) -> Optional[str]:
        """Stimuli in PCx/PCy score space, colored by a continuous `column`
        (e.g. GA Response) with a colorbar."""
        values = self._stim_value_lookup(compiled_data, column)
        if values is None:
            print(f"Skipping '{column}' scatter: column not available.")
            return None

        raw = [values.get(sid, np.nan) for sid in result.response_matrix.index]
        vals = pd.to_numeric(pd.Series(raw), errors='coerce').to_numpy()
        valid = ~np.isnan(vals)

        fig, ax = plt.subplots(figsize=(7.5, 7))
        if (~valid).any():
            ax.scatter(scores[~valid, pc_x], scores[~valid, pc_y], s=20,
                       color='lightgray', alpha=0.6, label='(missing)')
        sc = ax.scatter(scores[valid, pc_x], scores[valid, pc_y], c=vals[valid],
                        cmap='viridis', s=28, alpha=0.9)
        fig.colorbar(sc, ax=ax, label=column)
        ax.set_title(f"Stimuli in PC space ({self._pc_pair_label(pc_x, pc_y)}, "
                     f"colored by {column})")
        self._axis_labels(ax, result, pc_x, pc_y)
        fig.tight_layout()
        return self._save(
            fig, f"{label}_stimulus_{self._pc_tag(pc_x, pc_y)}_by_{self._slug(column)}")

    def _plot_stimulus_scatter_rgb(
        self, result: StimulusPCAResult, scores: np.ndarray,
        compiled_data: pd.DataFrame, column: str, label: str,
        pc_x: int, pc_y: int) -> Optional[str]:
        """Stimuli in PCx/PCy score space, colored by a 3-vector `column`
        (e.g. MassCenter's x/y/z) mapped to RGB. Each component is min-max
        normalized across stimuli, so two points with similar colors have
        similar centers of mass."""
        values = self._stim_value_lookup(compiled_data, column)
        if values is None:
            print(f"Skipping '{column}' RGB scatter: column not available.")
            return None

        raw = [values.get(sid) for sid in result.response_matrix.index]
        coords = np.full((len(raw), 3), np.nan)
        for i, v in enumerate(raw):
            vec = self._to_xyz(v)
            if vec is not None:
                coords[i] = vec
        valid = ~np.isnan(coords).any(axis=1)
        if not valid.any():
            print(f"Skipping '{column}' RGB scatter: no parseable (x, y, z) values.")
            return None

        # Min-max normalize each axis independently over the valid points.
        rgb = np.zeros((len(raw), 3))
        cmin = coords[valid].min(axis=0)
        cmax = coords[valid].max(axis=0)
        span = np.where((cmax - cmin) > 1e-12, cmax - cmin, 1.0)
        rgb[valid] = np.clip((coords[valid] - cmin) / span, 0.0, 1.0)

        fig, ax = plt.subplots(figsize=(7.5, 7))
        if (~valid).any():
            ax.scatter(scores[~valid, pc_x], scores[~valid, pc_y], s=20,
                       color='lightgray', alpha=0.5)
        ax.scatter(scores[valid, pc_x], scores[valid, pc_y], c=rgb[valid],
                   s=32, alpha=0.95, edgecolor='none')
        ax.set_title(f"Stimuli in PC space ({self._pc_pair_label(pc_x, pc_y)}, "
                     f"colored by {column} → RGB)")
        self._axis_labels(ax, result, pc_x, pc_y)
        ax.text(0.99, 0.01, "R = x   G = y   B = z\n(each min–max normalized)",
                transform=ax.transAxes, ha='right', va='bottom', fontsize=8,
                color='dimgray')
        fig.tight_layout()
        return self._save(
            fig, f"{label}_stimulus_{self._pc_tag(pc_x, pc_y)}_by_{self._slug(column)}")

    def _plot_pc1_examples(self, result: StimulusPCAResult, scores: np.ndarray,
                           compiled_data: pd.DataFrame, label: str,
                           n_examples: int = 7) -> Optional[str]:
        """Show example stimulus thumbnails sampled evenly (by rank) along PC1,
        from the lowest PC1 score to the highest."""
        thumbs = self._stim_value_lookup(compiled_data, 'ThumbnailPath')
        if thumbs is None:
            print("Skipping PC1 examples: 'ThumbnailPath' column not available.")
            return None

        stim_ids = list(result.response_matrix.index)
        pc1 = scores[:, 0]
        order = np.argsort(pc1)  # ascending PC1
        # Evenly spaced positions in rank space (robust to PC1 outliers).
        n = min(n_examples, len(order))
        picks = order[np.linspace(0, len(order) - 1, n).round().astype(int)]

        fig, axes = plt.subplots(1, n, figsize=(2.4 * n, 3.0))
        if n == 1:
            axes = [axes]
        for ax, idx in zip(axes, picks):
            sid = stim_ids[idx]
            path = thumbs.get(sid)
            ax.set_title(f"PC1={pc1[idx]:.2f}", fontsize=9)
            ax.axis('off')
            if path and os.path.exists(path):
                try:
                    ax.imshow(plt.imread(path))
                except Exception as exc:  # unreadable image -> note it, keep going
                    ax.text(0.5, 0.5, f"(unreadable)\n{exc}", ha='center',
                            va='center', fontsize=6)
            else:
                ax.text(0.5, 0.5, "(no thumbnail)", ha='center', va='center',
                        fontsize=8, color='gray')
        fig.suptitle("Example stimuli sampled along PC1 (low → high)")
        fig.tight_layout()
        return self._save(fig, f"{label}_pc1_examples")

    @staticmethod
    def _slug(column: str) -> str:
        return column.strip().lower().replace(' ', '_')

    @staticmethod
    def _pc_tag(pc_x: int, pc_y: int) -> str:
        return f"pc{pc_x + 1}_pc{pc_y + 1}"

    @staticmethod
    def _pc_pair_label(pc_x: int, pc_y: int) -> str:
        return f"PC{pc_x + 1} vs PC{pc_y + 1}"

    @staticmethod
    def _to_xyz(value) -> Optional[np.ndarray]:
        """Coerce a MassCenter-style value into a length-3 float array, or None.

        Handles tuples/lists of (x, y, z) (possibly string components from XML)
        and string reprs like "(0.1, 0.2, 0.3)" / "0.1, 0.2, 0.3".
        """
        if value is None:
            return None
        try:
            if isinstance(value, str):
                parts = value.strip().strip('()[]').split(',')
            else:
                parts = list(value)
            if len(parts) != 3:
                return None
            return np.array([float(p) for p in parts], dtype=float)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _stim_value_lookup(compiled_data: pd.DataFrame, column: str) -> Optional[dict]:
        """Map StimSpecId -> per-stimulus value for `column`, or None if the
        column is absent."""
        if compiled_data is None or column not in compiled_data.columns:
            return None
        sub = (compiled_data[['StimSpecId', column]]
               .dropna(subset=['StimSpecId'])
               .drop_duplicates('StimSpecId'))
        return dict(zip(sub['StimSpecId'], sub[column]))


if __name__ == "__main__":
    main()
