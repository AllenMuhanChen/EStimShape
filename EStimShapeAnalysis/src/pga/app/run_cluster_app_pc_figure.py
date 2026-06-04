"""
Cluster app variant whose Export button generates a PC-interpretation figure
instead of writing cluster channels to the GA database.

The figure shows, for the currently-displayed PCA-family reducer:
  - a scree plot of explained variance (full PCA, not just 2 components)
  - the cluster scatter with centroids marked
  - N thumbnails along each PC axis, sampled at evenly-spaced quantiles
    of the loading distribution (not just the extremes). PC1 thumbs run
    left-to-right above the scatter, ordered by ascending loading;
    PC2 thumbs run top-to-bottom to the right, ordered by descending
    loading. Each thumb's loading value is printed beneath it.
  - top-K thumbnails per cluster ranked by mean response across the cluster's
    channels, with cluster-colored borders whose intensity scales with each
    cluster's own min..max response range.

Only PCA and SparsePCA reducers are supported (they expose linear loadings).
"""

import os
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageOps
from matplotlib import cm
from matplotlib.gridspec import GridSpec
from sklearn.decomposition import PCA

from clat.intan.channels import Channel
from clat.util.connection import Connection
from src.cluster.cluster_app import ClusterApplicationWindow
from src.cluster.cluster_app_classes import DataExporter, MAX_GROUPS
from src.cluster.dimensionality_reduction import (DimensionalityReducer,
                                                  PCAReducer, SparsePCAReducer)
from src.cluster.mock_cluster_app import get_qapplication_instance
from src.cluster.probe_mapping import DBCChannelMapper
from src.pga.app.run_cluster_app import DbClusterLoader, DbDataLoader
from src.repository.export_to_repository import \
    read_session_id_and_date_from_db_name
from src.startup import context

K_AXIS_PER_END = 4      # thumbs per PC end (so PC1 rail shows 2*K_AXIS_PER_END thumbs total)
TOP_K_CLUSTER = 8       # top stimuli per cluster
BORDER_WIDTH = 30       # pixels of colored border around each cluster thumb
SCREE_MAX_COMPONENTS = 20
LOADING_CMAP = 'coolwarm'  # diverging colormap for PC loading subtitle text


class PcInterpretationFigureExporter(DataExporter):
    def __init__(self, data_loader: DbDataLoader, reducer: DimensionalityReducer,
                 session_id: str, save_dir: str):
        self.data_loader = data_loader
        self.reducer = reducer
        self.session_id = session_id
        self.save_dir = save_dir

    def export_channels_for_clusters(self, channels_for_clusters: dict[int, list[Channel]]):
        data_for_channels = self.data_loader.load_data_for_channels()
        data_for_channels = {ch: v for ch, v in data_for_channels.items() if len(v) > 0}
        channels = list(data_for_channels.keys())

        raw_responses = np.vstack(list(data_for_channels.values()))  # (n_channels, n_stim_ids), raw spikes/s
        X = self._normalize_per_channel(list(data_for_channels.values()))

        if not hasattr(self.reducer, 'model'):
            self.reducer.fit_transform(X)

        model = self.reducer.model
        loadings = model.components_           # (2, n_stim_ids)
        mean = model.mean_                     # (n_stim_ids,)
        reduced = (X - mean) @ loadings.T      # (n_channels, 2) — matches GUI fit

        explained_variance_ratio = self._fit_full_pca_for_scree(X)

        stim_ids = self._fetch_stim_id_order()
        if len(stim_ids) != loadings.shape[1]:
            print(f"WARN: stim_id count ({len(stim_ids)}) != loadings dim ({loadings.shape[1]}); "
                  "thumbnails may not align with PC components.")
        thumbs = self._fetch_thumbnails(stim_ids)

        centroids = self._compute_centroids(channels, reduced, channels_for_clusters)

        # PC axis thumbs: top-K most-negative + top-K most-positive loadings.
        # Returned indices are sorted by loading value ascending so the rails
        # read monotonically (PC1 neg→pos left-to-right; PC2 reversed for
        # pos→neg top-to-bottom in _render_pc2_rail).
        pc1_axis_idxs = _signed_extreme_thumbs(loadings[0], K_AXIS_PER_END)
        pc2_axis_idxs = _signed_extreme_thumbs(loadings[1], K_AXIS_PER_END)

        cluster_data = self._compute_cluster_top_by_mean_response(
            channels, raw_responses, channels_for_clusters)

        save_path = self._build_save_path()
        self._render_figure(reduced, channels, channels_for_clusters,
                            centroids, cluster_data, loadings,
                            pc1_axis_idxs, pc2_axis_idxs,
                            stim_ids, thumbs,
                            explained_variance_ratio,
                            save_path)
        print(f"Saved PC interpretation figure to {save_path}")

    @staticmethod
    def _normalize_per_channel(values: list[np.ndarray]) -> np.ndarray:
        normalized = []
        for v in values:
            if len(v) > 1 and np.std(v) > 1e-10:
                normalized.append((v - np.mean(v)) / np.std(v))
            else:
                normalized.append(v)
        return np.vstack(normalized)

    @staticmethod
    def _fit_full_pca_for_scree(X: np.ndarray) -> np.ndarray:
        n_components = min(SCREE_MAX_COMPONENTS, X.shape[0], X.shape[1])
        return PCA(n_components=n_components).fit(X).explained_variance_ratio_

    def _fetch_stim_id_order(self) -> list:
        conn = self.data_loader.conn
        conn.execute(
            "SELECT DISTINCT stim_id FROM ChannelResponses ORDER BY stim_id"
        )
        return [row[0] for row in conn.fetch_all()]

    def _fetch_thumbnails(self, stim_ids: list) -> dict:
        if not stim_ids:
            return {}
        repo_conn = Connection("allen_data_repository")
        placeholders = ', '.join(['%s'] * len(stim_ids))
        repo_conn.execute(
            f"SELECT stim_id, ThumbnailPath FROM GAStimInfo "
            f"WHERE stim_id IN ({placeholders})",
            params=stim_ids,
        )
        thumbs = {}
        for row in repo_conn.fetch_all():
            sid, path = row[0], row[1]
            if path:
                thumbs[sid] = path
        return thumbs

    @staticmethod
    def _compute_centroids(channels: list[Channel], reduced: np.ndarray,
                           channels_for_clusters: dict[int, list[Channel]]) -> dict:
        channel_to_idx = {ch: i for i, ch in enumerate(channels)}
        centroids = {}
        for cluster_id, ch_list in channels_for_clusters.items():
            if cluster_id == 0:
                continue
            idxs = [channel_to_idx[ch] for ch in ch_list if ch in channel_to_idx]
            if not idxs:
                continue
            centroids[cluster_id] = reduced[idxs].mean(axis=0)
        return centroids

    @staticmethod
    def _compute_cluster_top_by_mean_response(channels, raw_responses,
                                              channels_for_clusters):
        """Return {cluster_id: {'top_idxs': ..., 'mean_response': ..., 'min': ..., 'max': ...}}.

        Mean response is averaged across the cluster's channels using raw
        (un-normalized) spike rates, so the per-cluster min/max used for
        border-intensity normalization are interpretable as actual response
        rates in that cluster.
        """
        channel_to_idx = {ch: i for i, ch in enumerate(channels)}
        result = {}
        for cluster_id, ch_list in channels_for_clusters.items():
            if cluster_id == 0:
                continue
            idxs = [channel_to_idx[ch] for ch in ch_list if ch in channel_to_idx]
            if not idxs:
                continue
            mean_response = raw_responses[idxs].mean(axis=0)
            top_idxs = np.argsort(mean_response)[-TOP_K_CLUSTER:][::-1]
            result[cluster_id] = {
                'top_idxs': top_idxs,
                'mean_response': mean_response,
                'min': float(mean_response.min()),
                'max': float(mean_response.max()),
            }
        return result

    def _build_save_path(self) -> str:
        os.makedirs(self.save_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = self.reducer.get_name()
        return os.path.join(self.save_dir,
                            f"cluster_pc_interp_{name}_{ts}.png")

    def _render_figure(self, reduced, channels, channels_for_clusters,
                       centroids, cluster_data, loadings,
                       pc1_axis_idxs, pc2_axis_idxs,
                       stim_ids, thumbs,
                       explained_variance_ratio,
                       save_path):
        n_clusters = len(cluster_data)
        # Layout:
        #   col 0                              : label column (scree at top, cluster labels below)
        #   cols 1..(2*K_AXIS_PER_END)         : PC1 axis rail (row 0), scatter (middle rows),
        #                                         cluster thumbs (bottom rows; up to TOP_K_CLUSTER)
        #   col (2*K_AXIS_PER_END) + 1         : PC2 axis rail (vertical, beside scatter)
        n_axis_thumbs = 2 * K_AXIS_PER_END
        main_cols = max(n_axis_thumbs, TOP_K_CLUSTER)
        n_cols = 2 + main_cols
        scatter_rowspan = n_axis_thumbs  # one gridspec row per PC2 thumb
        n_rows = 1 + scatter_rowspan + max(n_clusters, 1)

        fig = plt.figure(figsize=(1.6 * n_cols + 2, 1.4 * n_rows + 2),
                         constrained_layout=True)
        gs = GridSpec(
            n_rows, n_cols, figure=fig,
            width_ratios=[1.2] + [1.0] * main_cols + [1.0],
        )

        scree_ax = fig.add_subplot(gs[0:2, 0])
        self._render_scree(scree_ax, explained_variance_ratio)

        scatter_ax = fig.add_subplot(gs[1:1 + scatter_rowspan, 1:1 + main_cols])
        self._render_scatter(scatter_ax, reduced, channels,
                             channels_for_clusters, centroids)

        self._render_pc1_rail(fig, gs, pc1_axis_idxs, loadings, stim_ids, thumbs,
                              main_cols)
        self._render_pc2_rail(fig, gs, pc2_axis_idxs, loadings, stim_ids, thumbs,
                              scatter_rowspan, n_cols)

        self._render_cluster_rows(fig, gs, cluster_data, stim_ids, thumbs,
                                  scatter_rowspan)

        fig.suptitle(f"PC interpretation — {self.reducer.get_name()} "
                     f"(session {self.session_id})", fontsize=14)
        fig.savefig(save_path, dpi=120)
        plt.close(fig)

    @staticmethod
    def _render_scree(ax, explained_variance_ratio):
        n = len(explained_variance_ratio)
        xs = np.arange(1, n + 1)
        ax.bar(xs, explained_variance_ratio, color='steelblue',
               edgecolor='black', linewidth=0.5)
        ax.set_xlabel("PC", fontsize=8)
        ax.set_ylabel("Var. expl.", fontsize=8)
        ax.set_title("Scree", fontsize=9)
        ax.tick_params(axis='both', labelsize=7)
        ax.set_xticks(xs[::max(1, n // 6)])

    @staticmethod
    def _render_pc1_rail(fig, gs, pc1_axis_idxs, loadings, stim_ids, thumbs,
                         main_cols):
        """Top row, thumbs ordered left-to-right by ascending PC1 loading."""
        n = len(pc1_axis_idxs)
        offset = (main_cols - n) // 2
        max_abs_load = max(abs(float(loadings[0, i])) for i in pc1_axis_idxs) \
            if n else 0.0
        for slot, stim_idx in enumerate(pc1_axis_idxs):
            col = 1 + offset + slot
            ax = fig.add_subplot(gs[0, col])
            load = float(loadings[0, stim_idx])
            _draw_simple_thumb(ax, int(stim_idx), stim_ids, thumbs,
                               subtitle=f"PC1: {load:+.2f}",
                               subtitle_color=_loading_text_color(load, max_abs_load))

    @staticmethod
    def _render_pc2_rail(fig, gs, pc2_axis_idxs, loadings, stim_ids, thumbs,
                         scatter_rowspan, n_cols):
        """Right column, thumbs ordered top-to-bottom by descending PC2 loading."""
        top_to_bottom = list(reversed(list(pc2_axis_idxs)))
        col = n_cols - 1
        n = len(top_to_bottom)
        offset = (scatter_rowspan - n) // 2
        max_abs_load = max(abs(float(loadings[1, i])) for i in top_to_bottom) \
            if n else 0.0
        for slot, stim_idx in enumerate(top_to_bottom):
            row = 1 + offset + slot
            ax = fig.add_subplot(gs[row, col])
            load = float(loadings[1, stim_idx])
            _draw_simple_thumb(ax, int(stim_idx), stim_ids, thumbs,
                               subtitle=f"PC2: {load:+.2f}",
                               subtitle_color=_loading_text_color(load, max_abs_load))

    @staticmethod
    def _render_scatter(ax, reduced, channels, channels_for_clusters, centroids):
        cluster_for_channel = {}
        for cid, chs in channels_for_clusters.items():
            for ch in chs:
                cluster_for_channel[ch] = cid
        colormap = cm.get_cmap('tab10', MAX_GROUPS)
        colors = [colormap(cluster_for_channel.get(ch, 0) / MAX_GROUPS) for ch in channels]
        ax.scatter(reduced[:, 0], reduced[:, 1], c=colors, s=30, alpha=0.7)
        for cid, centroid in centroids.items():
            color = colormap(cid / MAX_GROUPS)
            ax.scatter([centroid[0]], [centroid[1]],
                       marker='X', s=200, c=[color], edgecolors='black', linewidths=1.5,
                       zorder=5)
            ax.annotate(f"C{cid}", xy=centroid, xytext=(6, 6),
                        textcoords='offset points', fontsize=11, fontweight='bold')
        ax.set_xlabel("PC1")
        ax.set_ylabel("PC2")
        ax.axhline(0, color='gray', lw=0.5, alpha=0.5)
        ax.axvline(0, color='gray', lw=0.5, alpha=0.5)

    @staticmethod
    def _render_cluster_rows(fig, gs, cluster_data, stim_ids, thumbs,
                             scatter_rowspan):
        colormap = cm.get_cmap('tab10', MAX_GROUPS)
        first_cluster_row = 1 + scatter_rowspan  # row 0 = PC1 rail, rows 1..scatter_rowspan = scatter
        for row_offset, (cid, info) in enumerate(sorted(cluster_data.items())):
            row = first_cluster_row + row_offset
            base_color = colormap(cid / MAX_GROUPS)[:3]  # RGB 0-1
            label_ax = fig.add_subplot(gs[row, 0])
            label_ax.text(0.5, 0.5,
                          f"C{cid}\n[{info['min']:.1f},\n {info['max']:.1f}] sp/s",
                          ha='center', va='center', fontsize=9, fontweight='bold',
                          color=base_color)
            label_ax.axis('off')
            for slot, stim_idx in enumerate(info['top_idxs'][:TOP_K_CLUSTER]):
                ax = fig.add_subplot(gs[row, 1 + slot])
                response = float(info['mean_response'][stim_idx])
                _draw_thumb_with_border(ax, stim_idx, stim_ids, thumbs,
                                        response=response,
                                        min_val=info['min'],
                                        max_val=info['max'],
                                        base_color_rgb=base_color)


def _draw_thumb_with_border(ax, stim_idx: int, stim_ids: list, thumbs: dict,
                            response: float, min_val: float, max_val: float,
                            base_color_rgb):
    ax.axis('off')
    img = _load_thumb_image(stim_idx, stim_ids, thumbs)
    if img is None:
        sid = stim_ids[stim_idx] if stim_idx < len(stim_ids) else None
        ax.text(0.5, 0.5, f"stim {sid}\n(no thumb)" if sid is not None else "n/a",
                ha='center', va='center', fontsize=7, color='gray')
        return
    pil = Image.fromarray(_to_uint8_rgb(img))
    border_color = _scaled_border_color(response, min_val, max_val, base_color_rgb)
    bordered = ImageOps.expand(pil, border=BORDER_WIDTH, fill=border_color)
    ax.imshow(np.asarray(bordered))
    ax.set_title(f"{response:.1f}", fontsize=7, pad=1)


def _draw_simple_thumb(ax, stim_idx: int, stim_ids: list, thumbs: dict,
                       subtitle: str = None, subtitle_color='dimgray'):
    ax.axis('off')
    img = _load_thumb_image(stim_idx, stim_ids, thumbs)
    if img is None:
        sid = stim_ids[stim_idx] if stim_idx < len(stim_ids) else None
        ax.text(0.5, 0.5, f"stim {sid}\n(no thumb)" if sid is not None else "n/a",
                ha='center', va='center', fontsize=7, color='gray')
    else:
        ax.imshow(img)
    if subtitle is not None:
        ax.set_title(subtitle, fontsize=8, pad=1, color=subtitle_color,
                     fontweight='bold')


def _signed_extreme_thumbs(loading_vec, k_per_end: int) -> np.ndarray:
    """Return the k most-negative + k most-positive loading indices, sorted by
    loading value ascending. Near-zero loadings are skipped — they carry no
    information about what the PC represents.
    """
    loading_vec = np.asarray(loading_vec)
    n_stims = len(loading_vec)
    if n_stims == 0:
        return np.array([], dtype=int)
    sorted_idxs = np.argsort(loading_vec)
    k = min(k_per_end, n_stims // 2)
    negs = sorted_idxs[:k]
    poss = sorted_idxs[-k:]
    return np.concatenate([negs, poss])  # ascending by loading


def _loading_text_color(loading_val: float, max_abs_load: float):
    """Map a loading value to a diverging-colormap color (blue↔gray↔red).

    Used to color the small 'PC1: +0.34' subtitle under each axis thumb so
    the sign and magnitude of the loading are visible at a glance.
    """
    if max_abs_load <= 0:
        return 'gray'
    normalized = (loading_val / max_abs_load + 1.0) / 2.0
    normalized = max(0.0, min(1.0, normalized))
    return cm.get_cmap(LOADING_CMAP)(normalized)


def _load_thumb_image(stim_idx: int, stim_ids: list, thumbs: dict):
    if stim_idx >= len(stim_ids):
        return None
    sid = stim_ids[stim_idx]
    path = thumbs.get(sid)
    if not path or not os.path.exists(path):
        return None
    try:
        return np.asarray(Image.open(path).convert('RGB'))
    except Exception:
        return None


def _to_uint8_rgb(img: np.ndarray) -> np.ndarray:
    if img.dtype != np.uint8:
        img = (np.clip(img, 0, 1) * 255).astype(np.uint8) if img.max() <= 1.0 \
              else img.astype(np.uint8)
    if img.ndim == 2:
        img = np.stack([img] * 3, axis=-1)
    elif img.shape[-1] == 4:
        img = img[..., :3]
    return img


def _scaled_border_color(response: float, min_val: float, max_val: float,
                         base_color_rgb) -> tuple:
    if max_val <= min_val:
        normalized = 1.0
    else:
        normalized = (response - min_val) / (max_val - min_val)
        normalized = max(0.0, min(1.0, normalized))
    return tuple(int(255 * normalized * c) for c in base_color_rgb)


def main():
    session_id, _ = read_session_id_and_date_from_db_name(context.ga_database)
    save_dir = context.pc_maps_path

    data_loader = DbDataLoader(context.ga_config.connection())
    pca_reducer = PCAReducer()
    sparse_pca_reducer = SparsePCAReducer()
    exporter = PcInterpretationFigureExporter(
        data_loader=data_loader,
        reducer=pca_reducer,
        session_id=session_id,
        save_dir=save_dir,
    )

    app = get_qapplication_instance()
    window = ClusterApplicationWindow(
        data_loader,
        exporter,
        [pca_reducer, sparse_pca_reducer],
        DBCChannelMapper("A"),
        DbClusterLoader(context.ga_config.db_util),
    )
    window.show()
    app.exec_()


if __name__ == '__main__':
    main()
