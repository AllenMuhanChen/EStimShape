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
SAVE_PATH   = "/home/connorlab/Documents/plots/260426_0/probe_correlation"   # e.g. "/home/connorlab/Documents/plots/pub_column.png"

# Open connections once so metric choices below can share them.
conn    = Connection("allen_data_repository")
ga_conn = Connection(context.ga_database)

# ── Pick ONE metric ──────────────────────────────────────────────────────────
# Assign the one you want to `metric` and leave the rest commented out.

# Solid preference index
# metric = SolidPreferenceLoader(SESSION_ID, conn).as_metric(title='Solid Preference')

# Isochromatic preference at a specific frequency
# iso_data = IsochromaticPreferenceLoader(SESSION_ID, conn).load()
# metric = LookupMetric(iso_data[12.0], title='Iso Pref  12 Hz')

# Raw Spearman correlation vs a cluster channel (from pre-computed GA vectors)
matrix = ChannelResponseVectorLoader(SESSION_ID, conn).load()
metric = StimVectorCorrelation.vs_channel(matrix, "A-022", title='ρ vs A-022')

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

CHANNEL_SPACING_MM = 0.065  # 65 µm center-to-center
ESTIM_HATCH_COLOR  = '#8B8000'  # used for both hatch and "EStim" label


def main():
    """
    Args:
        estim_channels: Optional set of channel strings (e.g. {"A-007", "A-025"})
                        to mark with a hatched band so they are visually distinct
                        from cluster channels without obscuring the dot colour.
    """
    estim_channels = {"A-008", "A-022"}

    channel_strings  = build_channel_strings(HEADSTAGE)
    cluster_channels = ClusterChannelLoader(SESSION_ID, conn).load()
    cmap, norm       = default_cmap_norm()
    n                = len(channel_strings)

    fig, ax = plt.subplots(figsize=(4, 12), constrained_layout=True)

    scatter = plot_metric_column(
        ax, metric.compute(), channel_strings, cluster_channels,
        cmap=cmap, norm=norm,
        self_channel=metric.self_channel,
        show_yticks=True,
    )

    # Replace channel-name tick labels with depth in mm.
    # y=n → top channel (index 0, depth 0 mm); y=1 → bottom (depth (n-1)*spacing)
    depth_labels = [f'{(n - 1 - i) * CHANNEL_SPACING_MM:.2f}' for i in range(n)]
    ax.set_yticklabels(depth_labels, fontsize=8)
    ax.set_ylabel('Depth (mm)', fontsize=10)

    format_single_column_axis(ax)

    if metric.title:
        ax.set_title(metric.title, fontsize=11, fontweight='bold', pad=8)

    # Hatched bands for estim channels (drawn behind the dots).
    if estim_channels:
        for row_idx, ch in enumerate(channel_strings):
            if ch in estim_channels:
                y_pos = n - row_idx  # matches y positions in plot_metric_column
                ax.axhspan(
                    y_pos - 0.5, y_pos + 0.5,
                    facecolor='none', hatch='////',
                    edgecolor=ESTIM_HATCH_COLOR, linewidth=0.4,
                    zorder=0,
                )
                ax.text(
                    1.02, y_pos, 'EStim',
                    transform=ax.get_yaxis_transform(),
                    ha='left', va='center',
                    fontsize=7, color=ESTIM_HATCH_COLOR,
                    clip_on=False,
                )

    if scatter:
        cbar = fig.colorbar(
            plt.cm.ScalarMappable(norm=norm, cmap=cmap),
            ax=ax, orientation='vertical', pad=0.12, fraction=0.05,
        )
        cbar.set_label('Value', fontsize=9)

    ax.legend(
        handles=cluster_marker_legend_handles(),
        fontsize=8,
        bbox_to_anchor=(1.55, 1.0),
        loc='upper left',
        borderaxespad=0,
        framealpha=0.8,
    )

    if SAVE_PATH:
        fig.savefig(SAVE_PATH, dpi=300, bbox_inches='tight')
        print(f"Saved to {SAVE_PATH}")

    plt.show()


if __name__ == "__main__":
    main()
