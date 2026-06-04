"""
Cluster app variant whose Export button generates a PC-interpretation figure
instead of writing cluster channels to the GA database.

The figure shows, for the currently-displayed PCA-family reducer:
  - the cluster scatter with centroids marked
  - thumbnails of stimuli at the +/- extremes of each PC axis loading
  - top-K thumbnails per cluster, reconstructed from the cluster centroid

Only PCA and SparsePCA reducers are supported (they expose linear loadings).
"""

import os
from datetime import datetime

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import cm
from matplotlib.gridspec import GridSpec

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

TOP_K_AXIS = 4
TOP_K_CENTROID = 5


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

        X = self._normalize_per_channel(list(data_for_channels.values()))

        if not hasattr(self.reducer, 'model'):
            self.reducer.fit_transform(X)

        model = self.reducer.model
        loadings = model.components_           # (2, n_stim_ids)
        mean = model.mean_                     # (n_stim_ids,)
        reduced = (X - mean) @ loadings.T      # (n_channels, 2) — matches GUI fit

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

        cluster_top = {}
        for cluster_id, centroid in centroids.items():
            recon = centroid @ loadings  # (n_stim_ids,)
            cluster_top[cluster_id] = np.argsort(recon)[-TOP_K_CENTROID:][::-1]

        save_path = self._build_save_path()
        self._render_figure(reduced, channels, channels_for_clusters,
                            centroids, cluster_top,
                            pc1_pos, pc1_neg, pc2_pos, pc2_neg,
                            stim_ids, thumbs, save_path)
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

    def _build_save_path(self) -> str:
        os.makedirs(self.save_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = self.reducer.get_name()
        return os.path.join(self.save_dir,
                            f"cluster_pc_interp_{name}_{ts}.png")

    def _render_figure(self, reduced, channels, channels_for_clusters,
                       centroids, cluster_top,
                       pc1_pos, pc1_neg, pc2_pos, pc2_neg,
                       stim_ids, thumbs, save_path):
        n_clusters = len(centroids)
        # Layout: top row = PC1 axis thumbs; main row = PC2 thumbs (left) + scatter + PC2 thumbs (right);
        # bottom = one row per cluster (top-K stimuli).
        n_rows = 2 + max(n_clusters, 1)
        n_cols = TOP_K_AXIS * 2 + 2  # PC2 col + scatter spans + PC2 col

        fig = plt.figure(figsize=(2.0 * n_cols, 2.2 * n_rows))
        gs = GridSpec(n_rows, n_cols, figure=fig, hspace=0.4, wspace=0.3)

        self._render_pc1_axis_row(fig, gs, pc1_neg, pc1_pos, stim_ids, thumbs, n_cols)
        scatter_ax = fig.add_subplot(gs[1, 1:n_cols - 1])
        self._render_pc2_extremes(fig, gs, pc2_neg, pc2_pos, stim_ids, thumbs, n_cols)
        self._render_scatter(scatter_ax, reduced, channels, channels_for_clusters, centroids)
        self._render_cluster_rows(fig, gs, cluster_top, stim_ids, thumbs, n_cols)

        fig.suptitle(f"PC interpretation — {self.reducer.get_name()} "
                     f"(session {self.session_id})", fontsize=14)
        fig.savefig(save_path, dpi=120, bbox_inches='tight')
        plt.close(fig)

    @staticmethod
    def _render_pc1_axis_row(fig, gs, pc1_neg, pc1_pos, stim_ids, thumbs, n_cols):
        # Top row: PC1 negative extremes (left half) then positive extremes (right half).
        for slot, stim_idx in enumerate(pc1_neg):
            ax = fig.add_subplot(gs[0, 1 + slot])
            _draw_thumb(ax, stim_idx, stim_ids, thumbs,
                        title=f"PC1−" if slot == 0 else None)
        # PC1+ runs from least-positive (col closest to scatter) to most-positive (rightmost).
        for slot, stim_idx in enumerate(pc1_pos):
            col = n_cols - 2 - slot
            ax = fig.add_subplot(gs[0, col])
            _draw_thumb(ax, stim_idx, stim_ids, thumbs,
                        title="PC1+" if slot == 0 else None)

    @staticmethod
    def _render_pc2_extremes(fig, gs, pc2_neg, pc2_pos, stim_ids, thumbs, n_cols):
        # PC2 extremes flank the scatter on left/right of the same row.
        # Show one representative thumb per end (the strongest loading).
        ax_neg = fig.add_subplot(gs[1, 0])
        _draw_thumb(ax_neg, pc2_neg[0], stim_ids, thumbs, title="PC2−")
        ax_pos = fig.add_subplot(gs[1, n_cols - 1])
        _draw_thumb(ax_pos, pc2_pos[0], stim_ids, thumbs, title="PC2+")

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
    def _render_cluster_rows(fig, gs, cluster_top, stim_ids, thumbs, n_cols):
        colormap = cm.get_cmap('tab10', MAX_GROUPS)
        # Each cluster gets its own row starting at row 2.
        for row_offset, (cid, top_idxs) in enumerate(sorted(cluster_top.items())):
            row = 2 + row_offset
            label_ax = fig.add_subplot(gs[row, 0])
            label_ax.text(0.5, 0.5, f"Cluster {cid}\ntop stimuli",
                          ha='center', va='center', fontsize=11, fontweight='bold',
                          color=colormap(cid / MAX_GROUPS))
            label_ax.axis('off')
            for slot, stim_idx in enumerate(top_idxs[:n_cols - 1]):
                ax = fig.add_subplot(gs[row, 1 + slot])
                _draw_thumb(ax, stim_idx, stim_ids, thumbs)


def _draw_thumb(ax, stim_idx: int, stim_ids: list, thumbs: dict, title: str = None):
    ax.axis('off')
    if title is not None:
        ax.set_title(title, fontsize=10)
    if stim_idx >= len(stim_ids):
        ax.text(0.5, 0.5, "n/a", ha='center', va='center', fontsize=8, color='gray')
        return
    sid = stim_ids[stim_idx]
    path = thumbs.get(sid)
    if not path or not os.path.exists(path):
        ax.text(0.5, 0.5, f"stim {sid}\n(no thumb)",
                ha='center', va='center', fontsize=7, color='gray')
        return
    try:
        img = mpimg.imread(path)
        ax.imshow(img)
    except Exception as e:
        ax.text(0.5, 0.5, f"stim {sid}\n(err)",
                ha='center', va='center', fontsize=7, color='red')


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
