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

import ast
import os
from dataclasses import dataclass, field
from typing import Optional, Sequence

import numpy as np
import pandas as pd
import matplotlib.colors as mcolors
from matplotlib import pyplot as plt
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
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


# Path to the AlexNet ONNX model exposing a conv3 output (same one the alexnet
# GA pipeline uses). Set to None to disable AlexNet coloring.
ALEXNET_ONNX_PATH = "/home/r2_allen/git/EStimShape/EStimShapeAnalysis/data/AlexNetONNX_with_conv3"


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
        # {role -> boolean mask over response_matrix.index}, set in _plot_all.
        self._highlight_roles = None

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
        # Stimuli to ring for special attention (included deltas + their variants),
        # split by role so deltas and variants get different ring colors.
        self._highlight_roles = self._compute_highlight_roles(result, compiled_data)

        paths = [
            self._plot_scree(result, label),
            self._plot_loadings_heatmap(result, label),
            # Each scatter is one figure with PC1/PC2 and PC3/PC4 side by side.
            self._plot_stimulus_scatter_categorical(
                result, scores, compiled_data, 'Lineage', label, cmap='tab20'),
            self._plot_stimulus_scatter_continuous(
                result, scores, compiled_data, 'GA Response', label),
            self._plot_stimulus_scatter_categorical(
                result, scores, compiled_data, 'Texture', label, cmap='Set1'),
            # Stim / mutation type: cmap=None -> large distinct palette so many
            # regime/mutation types stay visually separable.
            self._plot_stimulus_scatter_categorical(
                result, scores, compiled_data, 'StimType', label, cmap=None),
            # Center of mass: (x, y, z) mapped to RGB so similar colors == similar CoM.
            self._plot_stimulus_scatter_rgb(
                result, scores, compiled_data, 'MassCenter', label),
        ]
        # AlexNet conv3-PCA coloring (first two PCs -> a 2D color), if available.
        alexnet_pcs = self._resolve_alexnet_pcs(compiled_data)
        if alexnet_pcs:
            paths.append(self._plot_stimulus_scatter_alexnet(
                result, scores, alexnet_pcs, label))
        # Binned example thumbnails along each of PC1..PC4.
        for pc_idx in range(min(4, scores.shape[1])):
            paths.append(self._plot_pc_examples(result, scores, compiled_data, pc_idx, label))
        result.figure_paths = [p for p in paths if p is not None]

    def _resolve_alexnet_pcs(self, compiled_data: pd.DataFrame) -> Optional[dict]:
        """Per-stimulus AlexNet conv3-PCA coordinates: a precomputed dict if
        given, else computed by the injected embedder from stimulus images."""
        if self.alexnet_pcs is not None:
            return self.alexnet_pcs
        if self.alexnet_embedder is None:
            return None
        paths = (self._stim_value_lookup(compiled_data, 'StimPath')
                 or self._stim_value_lookup(compiled_data, 'ThumbnailPath'))
        if not paths:
            print("AlexNet coloring skipped: no StimPath/ThumbnailPath column.")
            return None
        return self.alexnet_embedder.embed(paths)

    def _compute_highlight_roles(self, result: StimulusPCAResult,
                                 compiled_data: pd.DataFrame) -> Optional[dict]:
        """``{role -> boolean mask}`` over response_matrix.index for the stimuli
        to ring, where role is 'delta' / 'variant' (or 'highlight' if unknown)."""
        roles_for_id = self._resolve_highlight_roles(compiled_data)
        if not roles_for_id:
            return None

        # Refine any unknown ('highlight') role from the StimType column.
        stim_types = self._stim_value_lookup(compiled_data, 'StimType') or {}
        role_per_index = []
        for sid in result.response_matrix.index:
            role = roles_for_id.get(sid)
            if role == 'highlight':
                st = stim_types.get(sid)
                if st == 'REGIME_ESTIM_VARIANTS':
                    role = 'variant'
                elif st == 'REGIME_ESTIM_DELTA':
                    role = 'delta'
            role_per_index.append(role)
        role_per_index = np.array(role_per_index, dtype=object)

        masks = {}
        for role in ('delta', 'variant', 'highlight'):
            mask = role_per_index == role
            if mask.any():
                masks[role] = mask
        if not masks:
            print("No highlighted (included delta/variant) stimuli are in this data.")
            return None
        summary = ", ".join(f"{int(m.sum())} {r}" for r, m in masks.items())
        print(f"Highlighting {summary}.")
        return masks

    def _resolve_highlight_roles(self, compiled_data: pd.DataFrame) -> dict:
        """``{stim_id -> role}``. Honors a dict override directly, treats a set
        override as role-unknown ('highlight'), else reads ``IncludedDeltas``."""
        override = self.highlighted_stim_ids
        if override is not None:
            if isinstance(override, dict):
                return {int(k): v for k, v in override.items()}
            return {int(k): 'highlight' for k in override}
        return self._load_included_delta_variant_roles()

    def _load_included_delta_variant_roles(self) -> dict:
        """``{stim_id -> 'delta'|'variant'}`` for included REGIME_ESTIM_DELTA
        stimuli and their paired REGIME_ESTIM_VARIANTS, from ``IncludedDeltas``.

        Returns an empty dict if the table is missing/empty or unreadable."""
        try:
            from clat.util.connection import Connection
            conn = Connection(context.ga_database)
            conn.execute(
                "SELECT delta_id, variant_id FROM IncludedDeltas WHERE included = 1"
            )
            roles: dict = {}
            for delta_id, variant_id in conn.fetch_all():
                if delta_id is not None:
                    roles[int(delta_id)] = 'delta'
                if variant_id is not None:
                    roles[int(variant_id)] = 'variant'
            return roles
        except Exception as exc:
            print(f"Could not read IncludedDeltas (highlight skipped): {exc}")
            return {}

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

    def _plot_coloring(self, result: StimulusPCAResult, scores: np.ndarray,
                       label: str, slug: str, suptitle: str, draw_fn) -> str:
        """One figure with PC1/PC2 (and PC3/PC4 when >=4 PCs exist) side by side.

        ``draw_fn(ax, fig, pc_x, pc_y, is_first)`` paints a single panel; the
        legend/colorbar/key should only be drawn on the first panel
        (``is_first``) to avoid duplication.
        """
        pc_pairs = [(0, 1)]
        if scores.shape[1] >= 4:
            pc_pairs.append((2, 3))
        fig, axes = plt.subplots(1, len(pc_pairs), figsize=(7.5 * len(pc_pairs), 7))
        axes = np.atleast_1d(axes)
        for i, (ax, (px, py)) in enumerate(zip(axes, pc_pairs)):
            draw_fn(ax, fig, px, py, i == 0)
            self._draw_highlights(ax, scores, px, py, annotate=(i == 0))
            self._axis_labels(ax, result, px, py)
            ax.set_title(self._pc_pair_label(px, py))
        fig.suptitle(suptitle)
        fig.tight_layout()
        return self._save(fig, f"{label}_stimulus_by_{slug}")

    # Ring color + label per highlight role.
    HIGHLIGHT_STYLE = {
        'variant': ('red', 'included variant'),
        'delta': ('black', 'included Δ (delta)'),
        'highlight': ('black', 'included Δ / variant'),
    }

    def _draw_highlights(self, ax, scores: np.ndarray, pc_x: int, pc_y: int,
                         annotate: bool) -> None:
        """Ring the highlighted stimuli on a panel, one ring color per role
        (variant vs delta)."""
        roles = self._highlight_roles
        if not roles:
            return
        y = 0.01
        for role, mask in roles.items():
            color, lbl = self.HIGHLIGHT_STYLE.get(role, ('black', role))
            ax.scatter(scores[mask, pc_x], scores[mask, pc_y], s=180,
                       facecolors='none', edgecolors=color, linewidths=1.8, zorder=6)
            if annotate:
                ax.text(0.01, y, f"○ {lbl} (n={int(mask.sum())})",
                        transform=ax.transAxes, ha='left', va='bottom',
                        fontsize=8, color=color,
                        bbox=dict(boxstyle='round', fc='white', ec='gray', alpha=0.75))
                y += 0.05

    def _plot_stimulus_scatter_categorical(
        self, result: StimulusPCAResult, scores: np.ndarray,
        compiled_data: pd.DataFrame, column: str, label: str,
        cmap: Optional[str] = 'tab20') -> Optional[str]:
        """Stimuli in PC space, one color per discrete `column` value
        (e.g. Lineage, Texture, StimType). ``cmap=None`` (or more categories
        than the named map holds) uses a large distinct palette."""
        values = self._stim_value_lookup(compiled_data, column)
        if values is None:
            print(f"Skipping '{column}' scatter: column not available.")
            return None

        per_stim = np.array([values.get(sid, None) for sid in result.response_matrix.index],
                            dtype=object)
        categories = [c for c in pd.unique(per_stim) if c is not None]
        colors = self._category_colors(len(categories), cmap)
        missing = per_stim == None  # noqa: E711  (elementwise on object array)

        def draw(ax, fig, px, py, is_first):
            if missing.any():
                ax.scatter(scores[missing, px], scores[missing, py], s=20,
                           color='lightgray', alpha=0.6,
                           label='(missing)' if is_first else None)
            for i, cat in enumerate(categories):
                mask = per_stim == cat
                ax.scatter(scores[mask, px], scores[mask, py], s=25, alpha=0.8,
                           color=colors[i],
                           label=str(cat) if is_first else None)
            if is_first and len(categories) <= 30:
                ax.legend(title=column, loc='best', fontsize=8, markerscale=1.2)

        return self._plot_coloring(
            result, scores, label, self._slug(column),
            f"Stimuli in PC space (colored by {column})", draw)

    def _plot_stimulus_scatter_continuous(
        self, result: StimulusPCAResult, scores: np.ndarray,
        compiled_data: pd.DataFrame, column: str, label: str) -> Optional[str]:
        """Stimuli in PC space, colored by a continuous `column`
        (e.g. GA Response) with a colorbar."""
        values = self._stim_value_lookup(compiled_data, column)
        if values is None:
            print(f"Skipping '{column}' scatter: column not available.")
            return None

        raw = [values.get(sid, np.nan) for sid in result.response_matrix.index]
        vals = pd.to_numeric(pd.Series(raw), errors='coerce').to_numpy()
        valid = ~np.isnan(vals)
        # Shared color scale across panels so colors are directly comparable.
        vmin = float(np.min(vals[valid])) if valid.any() else 0.0
        vmax = float(np.max(vals[valid])) if valid.any() else 1.0

        def draw(ax, fig, px, py, is_first):
            if (~valid).any():
                ax.scatter(scores[~valid, px], scores[~valid, py], s=20,
                           color='lightgray', alpha=0.6)
            sc = ax.scatter(scores[valid, px], scores[valid, py], c=vals[valid],
                            cmap='viridis', s=28, alpha=0.9, vmin=vmin, vmax=vmax)
            fig.colorbar(sc, ax=ax, label=column)

        return self._plot_coloring(
            result, scores, label, self._slug(column),
            f"Stimuli in PC space (colored by {column})", draw)

    def _plot_stimulus_scatter_rgb(
        self, result: StimulusPCAResult, scores: np.ndarray,
        compiled_data: pd.DataFrame, column: str, label: str) -> Optional[str]:
        """Stimuli in PC space, colored by a 3-vector `column` (e.g. MassCenter's
        x/y/z) mapped to RGB. Each component is min-max normalized across
        stimuli, so similar colors == similar centers of mass."""
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

        rgb = np.zeros((len(raw), 3))
        cmin = coords[valid].min(axis=0)
        cmax = coords[valid].max(axis=0)
        span = np.where((cmax - cmin) > 1e-12, cmax - cmin, 1.0)
        rgb[valid] = np.clip((coords[valid] - cmin) / span, 0.0, 1.0)

        def draw(ax, fig, px, py, is_first):
            if (~valid).any():
                ax.scatter(scores[~valid, px], scores[~valid, py], s=20,
                           color='lightgray', alpha=0.5)
            ax.scatter(scores[valid, px], scores[valid, py], c=rgb[valid],
                       s=32, alpha=0.95, edgecolor='none')
            if is_first:
                ax.text(0.99, 0.01, "R = x   G = y   B = z\n(each min–max normalized)",
                        transform=ax.transAxes, ha='right', va='bottom',
                        fontsize=8, color='dimgray')

        return self._plot_coloring(
            result, scores, label, self._slug(column),
            f"Stimuli in PC space (colored by {column} → RGB)", draw)

    def _plot_stimulus_scatter_alexnet(
        self, result: StimulusPCAResult, scores: np.ndarray,
        alexnet_pcs: dict, label: str) -> Optional[str]:
        """Stimuli in (neural) PC space, colored by the first two PCs of their
        AlexNet conv3 activations, mapped to a 2D color. Similar colors mean the
        stimuli look geometrically similar to AlexNet -- overlaying this on the
        neural PCA shows whether V4-clustered stimuli also look alike."""
        raw = [alexnet_pcs.get(sid) for sid in result.response_matrix.index]
        ab = np.full((len(raw), 2), np.nan)
        for i, v in enumerate(raw):
            if v is not None and len(v) >= 2:
                ab[i] = [float(v[0]), float(v[1])]
        valid = ~np.isnan(ab).any(axis=1)
        if not valid.any():
            print("Skipping AlexNet scatter: no usable coordinates.")
            return None

        colors = self._two_d_colors(ab, valid)

        def draw(ax, fig, px, py, is_first):
            if (~valid).any():
                ax.scatter(scores[~valid, px], scores[~valid, py], s=20,
                           color='lightgray', alpha=0.5)
            ax.scatter(scores[valid, px], scores[valid, py], c=colors[valid],
                       s=32, alpha=0.95, edgecolor='none')
            if is_first:
                self._add_2d_color_key(ax, "AlexNet PC1", "AlexNet PC2")

        return self._plot_coloring(
            result, scores, label, "alexnet_conv3_pca",
            "Stimuli in PC space (colored by AlexNet conv3 PCA: PC1→x, PC2→y)", draw)

    def _plot_pc_examples(self, result: StimulusPCAResult, scores: np.ndarray,
                          compiled_data: pd.DataFrame, pc_idx: int, label: str,
                          n_bins: int = 5, n_per_bin: int = 6) -> Optional[str]:
        """Grid of example thumbnails for one PC: rows are equal-width value
        ranges of the PC (high at top), each row showing several example stimuli
        drawn from that range."""
        thumbs = self._stim_value_lookup(compiled_data, 'ThumbnailPath')
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

    # ---- color helpers ---------------------------------------------------
    def _category_colors(self, n: int, cmap: Optional[str]) -> list:
        """A color per category. Uses the named qualitative `cmap` when it has
        enough discrete entries; otherwise a large distinct palette."""
        if cmap is not None:
            listed = getattr(plt.get_cmap(cmap), 'colors', None)
            if listed is not None and n <= len(listed):
                return [listed[i] for i in range(n)]
        return self._distinct_colors(n)

    @staticmethod
    def _distinct_colors(n: int) -> list:
        """`n` visually distinct colors: strong tab10 hues first, then tab20b/c
        (50 total), falling back to evenly-spaced HSV beyond that."""
        palette: list = []
        for name in ('tab10', 'tab20b', 'tab20c'):
            palette.extend(plt.get_cmap(name).colors)
        if n <= len(palette):
            return [tuple(palette[i]) for i in range(n)]
        hues = np.linspace(0, 1, n, endpoint=False)
        return [tuple(mcolors.hsv_to_rgb((h, 0.65, 0.9))) for h in hues]

    @staticmethod
    def _two_d_color_array(a_norm: np.ndarray, b_norm: np.ndarray) -> np.ndarray:
        """Map two [0,1] coordinates to RGB via HSV (hue<-a, saturation<-b) so
        nearby (a, b) get nearby colors."""
        a = np.asarray(a_norm, dtype=float)
        b = np.asarray(b_norm, dtype=float)
        h = 0.7 * a                      # hue sweeps red->blue across PC1
        s = 0.35 + 0.6 * b               # saturation grows with PC2
        v = np.full_like(h, 0.95)
        return mcolors.hsv_to_rgb(np.stack([h, s, v], axis=-1))

    def _two_d_colors(self, ab: np.ndarray, valid: np.ndarray) -> np.ndarray:
        """Per-point RGB for an (n, 2) array, min-max normalized over `valid`."""
        out = np.zeros((len(ab), 3))
        sub = ab[valid]
        mn, mx = sub.min(axis=0), sub.max(axis=0)
        span = np.where((mx - mn) > 1e-12, mx - mn, 1.0)
        norm = (sub - mn) / span
        out[valid] = self._two_d_color_array(norm[:, 0], norm[:, 1])
        return out

    def _add_2d_color_key(self, ax, xlabel: str, ylabel: str) -> None:
        """Inset showing the 2D color map, so the scatter colors are readable."""
        cax = inset_axes(ax, width="26%", height="26%", loc='lower right')
        n = 50
        aa, bb = np.meshgrid(np.linspace(0, 1, n), np.linspace(0, 1, n))
        grid = self._two_d_color_array(aa.ravel(), bb.ravel()).reshape(n, n, 3)
        cax.imshow(grid, origin='lower', extent=[0, 1, 0, 1], aspect='auto')
        cax.set_xticks([])
        cax.set_yticks([])
        cax.set_xlabel(xlabel, fontsize=6)
        cax.set_ylabel(ylabel, fontsize=6)

    @staticmethod
    def _slug(column: str) -> str:
        return column.strip().lower().replace(' ', '_')

    @staticmethod
    def _pc_pair_label(pc_x: int, pc_y: int) -> str:
        return f"PC{pc_x + 1} vs PC{pc_y + 1}"

    @staticmethod
    def _to_xyz(value) -> Optional[np.ndarray]:
        """Coerce a MassCenter-style value into a length-3 float array, or None.

        Handles tuples/lists of (x, y, z) and string reprs from the repository
        round-trip. MassCenter comes out of the matchstick XML as a tuple of
        *string* components, so ``str()`` on export yields e.g.
        ``"('0.1', '0.2', '0.3')"`` -- ``ast.literal_eval`` parses both that and
        the plain ``"(0.1, 0.2, 0.3)"`` form, where a naive split on commas
        would trip over the inner quotes.
        """
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return None
        try:
            parsed = ast.literal_eval(value) if isinstance(value, str) else value
            parts = list(parsed)
            if len(parts) != 3:
                return None
            return np.array([float(p) for p in parts], dtype=float)
        except (ValueError, TypeError, SyntaxError):
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
