"""
pub_single_column.py
--------------------
Publication-quality single-column figure: all channels top → bottom,
coloured by one chosen metric.

Usage: edit the USER SETTINGS block, then run.
"""

import matplotlib.pyplot as plt
from clat.util.connection import Connection
from src.analysis.channel_data_loaders import (
    ChannelResponseVectorLoader,
    ClusterChannelLoader,
    DeltaVariantStimLoader,
    GAResponseLoader,
    IsochromaticPreferenceLoader,
    RawSpikeResponseLoader,
    SolidPreferenceLoader,
)
from src.analysis.channel_metric_plot import (
    LookupMetric,
    StimVectorCorrelation,
    build_channel_strings,
    cluster_marker_legend_handles,
    default_cmap_norm,
    format_single_column_axis,
    plot_metric_column,
)
from src.startup import context


# ─── USER SETTINGS ────────────────────────────────────────────────────────────

SESSION_ID  = "260426_0"
HEADSTAGE   = "A"
SAVE_PATH   = None   # e.g. "/home/connorlab/Documents/plots/pub_column.png"

# Open connections once so metric choices below can share them.
conn    = Connection("allen_data_repository")
ga_conn = Connection(context.ga_database)

# ── Pick ONE metric ──────────────────────────────────────────────────────────
# Assign the one you want to `metric` and leave the rest commented out.

# Solid preference index
metric = SolidPreferenceLoader(SESSION_ID, conn).as_metric(title='Solid Preference')

# Isochromatic preference at a specific frequency
# iso_data = IsochromaticPreferenceLoader(SESSION_ID, conn).load()
# metric = LookupMetric(iso_data[12.0], title='Iso Pref  12 Hz')

# Raw Spearman correlation vs a cluster channel (from pre-computed GA vectors)
# matrix = ChannelResponseVectorLoader(SESSION_ID, conn).load()
# metric = StimVectorCorrelation.vs_channel(matrix, "A-001", title='ρ vs A-001')

# Z-scored Spearman on delta/variant stims
# dv_ids = DeltaVariantStimLoader(ga_conn, included_only=True).load()
# matrix = RawSpikeResponseLoader(conn, dv_ids).load()
# metric = StimVectorCorrelation.vs_channel(matrix, "A-001", zscore=True, title='ρ vs A-001 (Δ/var)')

# Z-scored Spearman on top-N GA stims
# ga_resp = GAResponseLoader(SESSION_ID, conn).load()
# top_ids = set(sorted(ga_resp, key=ga_resp.get, reverse=True)[:20])
# matrix  = RawSpikeResponseLoader(conn, top_ids).load()
# metric  = StimVectorCorrelation.vs_channel(matrix, "A-001", zscore=True, title='ρ vs A-001 (top-N)')

# ─────────────────────────────────────────────────────────────────────────────


def main():
    channel_strings  = build_channel_strings(HEADSTAGE)
    cluster_channels = ClusterChannelLoader(SESSION_ID, conn).load()
    cmap, norm       = default_cmap_norm()

    fig, ax = plt.subplots(figsize=(2, 10))

    scatter = plot_metric_column(
        ax, metric.compute(), channel_strings, cluster_channels,
        cmap=cmap, norm=norm,
        self_channel=metric.self_channel,
        show_yticks=True,
    )
    format_single_column_axis(ax)

    if metric.title:
        ax.set_title(metric.title, fontsize=11, fontweight='bold', pad=8)

    if scatter:
        cbar = plt.colorbar(
            plt.cm.ScalarMappable(norm=norm, cmap=cmap),
            ax=ax, orientation='horizontal', pad=0.04, fraction=0.05,
        )
        cbar.set_label('Value', fontsize=9)

    ax.legend(handles=cluster_marker_legend_handles(), loc='upper right', fontsize=8,
              framealpha=0.8)

    plt.tight_layout()

    if SAVE_PATH:
        plt.savefig(SAVE_PATH, dpi=300, bbox_inches='tight')
        print(f"Saved to {SAVE_PATH}")

    plt.show()


if __name__ == "__main__":
    main()
