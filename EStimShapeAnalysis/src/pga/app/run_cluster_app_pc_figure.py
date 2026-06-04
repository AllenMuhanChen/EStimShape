"""
Cluster app variant whose Export button generates a PC-interpretation figure
instead of writing cluster channels to the GA database.

The figure shows, for the currently-displayed PCA-family reducer:
  - a scree plot of explained variance (full PCA, not just 2 components)
  - the cluster scatter with centroids marked
  - thumbnails of stimuli at the +/- extremes of PC1 and PC2, positioned
    above / to the right of the scatter at their actual loading values
    (rescaled to the scatter's score range, biplot-style)
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
from matplotlib.patches import ConnectionPatch
from matplotlib.transforms import blended_transform_factory
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

TOP_K_AXIS = 4         # thumbs per PC end (PC1 has TOP_K_AXIS on each side, PC2 same)
TOP_K_CLUSTER = 8      # top stimuli per cluster
BORDER_WIDTH = 30      # pixels of colored border around each cluster thumb
SCREE_MAX_COMPONENTS = 20
AXIS_FILL_RATIO = 0.92  # scale loadings so the max-shown loading reaches this fraction of axis extent
LEADER_COLOR = 'darkgray'
LEADER_LW = 0.8


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

        pc1_pos = np.argsort(loadings[0])[-TOP_K_AXIS:][::-1]
        pc1_neg = np.argsort(loadings[0])[:TOP_K_AXIS]
        pc2_pos = np.argsort(loadings[1])[-TOP_K_AXIS:][::-1]
        pc2_neg = np.argsort(loadings[1])[:TOP_K_AXIS]

        cluster_data = self._compute_cluster_top_by_mean_response(
            channels, raw_responses, channels_for_clusters)

        save_path = self._build_save_path()
        self._render_figure(reduced, channels, channels_for_clusters,
                            centroids, cluster_data, loadings,
                            pc1_pos, pc1_neg, pc2_pos, pc2_neg,
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
                       pc1_pos, pc1_neg, pc2_pos, pc2_neg,
                       stim_ids, thumbs,
                       explained_variance_ratio,
                       save_path):
        n_clusters = len(cluster_data)
        # Layout:
        #   col 0                      : label column (scree at top, cluster labels below)
        #   cols 1..TOP_K_CLUSTER      : PC1 axis rail (row 0), scatter (middle rows),
        #                                cluster thumbs (bottom rows)
        #   col TOP_K_CLUSTER + 1      : PC2 axis rail (vertical, beside scatter)
        n_cols = 2 + TOP_K_CLUSTER
        scatter_rowspan = 2 * TOP_K_AXIS  # match PC2 rail height
        n_rows = 1 + scatter_rowspan + max(n_clusters, 1)

        fig = plt.figure(figsize=(1.6 * n_cols + 2, 1.6 * n_rows + 2))
        gs = GridSpec(
            n_rows, n_cols, figure=fig, hspace=0.55, wspace=0.3,
            width_ratios=[1.2] + [1.0] * TOP_K_CLUSTER + [1.0],
        )

        scree_ax = fig.add_subplot(gs[0:2, 0])
        self._render_scree(scree_ax, explained_variance_ratio)

        scatter_ax = fig.add_subplot(gs[1:1 + scatter_rowspan, 1:1 + TOP_K_CLUSTER])
        self._render_scatter(scatter_ax, reduced, channels,
                             channels_for_clusters, centroids)

        # PC axis rails — rank-ordered, evenly spaced thumbs with leader lines
        # going to each thumb's actual loading position on the scatter edge.
        pc1_axes = self._render_pc1_rail(fig, gs, pc1_neg, pc1_pos, loadings,
                                         stim_ids, thumbs)
        pc2_axes = self._render_pc2_rail(fig, gs, pc2_neg, pc2_pos, loadings,
                                         stim_ids, thumbs, scatter_rowspan,
                                         n_cols)
        self._draw_leader_lines(fig, scatter_ax, pc1_axes, pc2_axes,
                                loadings, reduced)

        self._render_cluster_rows(fig, gs, cluster_data, stim_ids, thumbs,
                                  scatter_rowspan)

        fig.suptitle(f"PC interpretation — {self.reducer.get_name()} "
                     f"(session {self.session_id})", fontsize=14, y=1.0)
        fig.savefig(save_path, dpi=120, bbox_inches='tight')
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
    def _render_pc1_rail(fig, gs, pc1_neg, pc1_pos, loadings, stim_ids, thumbs):
        """Top row, evenly-spaced rank-ordered thumbs spanning the cluster-thumb columns.

        Returns a list of (thumb_ax, stim_idx) for leader-line connection.
        """
        ordered = list(pc1_neg) + list(pc1_pos)
        # If we're showing fewer thumbs than TOP_K_CLUSTER columns, center them.
        offset = (TOP_K_CLUSTER - len(ordered)) // 2
        out = []
        for slot, stim_idx in enumerate(ordered):
            col = 1 + offset + slot
            ax = fig.add_subplot(gs[0, col])
            _draw_simple_thumb(ax, stim_idx, stim_ids, thumbs,
                               subtitle=f"PC1: {loadings[0, stim_idx]:+.2f}")
            out.append((ax, stim_idx))
        return out

    @staticmethod
    def _render_pc2_rail(fig, gs, pc2_neg, pc2_pos, loadings, stim_ids, thumbs,
                        scatter_rowspan, n_cols):
        """Right column, evenly-spaced rank-ordered thumbs.

        Most-positive on top, most-negative on bottom.
        """
        ordered_top_to_bottom = list(pc2_pos) + list(pc2_neg)
        col = n_cols - 1
        out = []
        for slot, stim_idx in enumerate(ordered_top_to_bottom):
            row = 1 + slot
            ax = fig.add_subplot(gs[row, col])
            _draw_simple_thumb(ax, stim_idx, stim_ids, thumbs,
                               subtitle=f"PC2: {loadings[1, stim_idx]:+.2f}")
            out.append((ax, stim_idx))
        return out

    @staticmethod
    def _draw_leader_lines(fig, scatter_ax, pc1_axes, pc2_axes, loadings, reduced):
        """Draw a thin line from each PC rail thumb to its actual loading
        position on the corresponding scatter axis edge.

        Loading values are scaled so the most-extreme shown loading lands at
        AXIS_FILL_RATIO of the scatter's score range — same as the
        biplot-style positioning we'd use without the rail.
        """
        pc1_indices = [idx for _, idx in pc1_axes]
        pc2_indices = [idx for _, idx in pc2_axes]
        pc1_scale = _loading_to_score_scale(loadings[0], reduced[:, 0], pc1_indices)
        pc2_scale = _loading_to_score_scale(loadings[1], reduced[:, 1], pc2_indices)

        # x in scatter data coords, y in scatter axes-fraction
        bt_xdata_yaxes = blended_transform_factory(scatter_ax.transData,
                                                   scatter_ax.transAxes)
        # x in scatter axes-fraction, y in scatter data coords
        bt_xaxes_ydata = blended_transform_factory(scatter_ax.transAxes,
                                                   scatter_ax.transData)

        for thumb_ax, stim_idx in pc1_axes:
            x_data = float(loadings[0, stim_idx]) * pc1_scale
            con = ConnectionPatch(
                xyA=(0.5, 0.0), coordsA=thumb_ax.transAxes,
                xyB=(x_data, 1.0), coordsB=bt_xdata_yaxes,
                color=LEADER_COLOR, linewidth=LEADER_LW, zorder=0,
            )
            fig.add_artist(con)

        for thumb_ax, stim_idx in pc2_axes:
            y_data = float(loadings[1, stim_idx]) * pc2_scale
            con = ConnectionPatch(
                xyA=(0.0, 0.5), coordsA=thumb_ax.transAxes,
                xyB=(1.0, y_data), coordsB=bt_xaxes_ydata,
                color=LEADER_COLOR, linewidth=LEADER_LW, zorder=0,
            )
            fig.add_artist(con)

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
        for row_offset, (cid, info) in enumerate(sorted(cluster_data.items())):
            row = scatter_rowspan + row_offset
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
                       subtitle: str = None):
    ax.axis('off')
    img = _load_thumb_image(stim_idx, stim_ids, thumbs)
    if img is None:
        sid = stim_ids[stim_idx] if stim_idx < len(stim_ids) else None
        ax.text(0.5, 0.5, f"stim {sid}\n(no thumb)" if sid is not None else "n/a",
                ha='center', va='center', fontsize=7, color='gray')
    else:
        ax.imshow(img)
    if subtitle is not None:
        ax.set_title(subtitle, fontsize=7, pad=1, color='dimgray')


def _loading_to_score_scale(loading_vec, score_vec, shown_idxs) -> float:
    """Scale factor that maps the most-extreme shown loading onto
    AXIS_FILL_RATIO of the score range, so thumbs land inside the axes."""
    if len(shown_idxs) == 0:
        return 1.0
    max_loading = max(abs(float(loading_vec[i])) for i in shown_idxs)
    max_score = float(np.max(np.abs(score_vec))) if len(score_vec) else 1.0
    if max_loading == 0 or max_score == 0:
        return 1.0
    return (max_score * AXIS_FILL_RATIO) / max_loading


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
