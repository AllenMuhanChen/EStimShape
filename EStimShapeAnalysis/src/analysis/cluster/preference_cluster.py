import numpy as np
import matplotlib.pyplot as plt
from clat.intan.channels import Channel
from clat.util.connection import Connection
from src.analysis.channel_data_loaders import (
    ChannelResponseVectorLoader,
    ClusterChannelLoader,
    IsochromaticPreferenceLoader,
    PreferredFrequencyLoader,
    SolidPreferenceLoader,
)
from src.analysis.channel_metric_plot import (
    StimVectorCorrelation,
    build_channel_strings,
    cluster_marker_legend_handles,
    default_cmap_norm,
    render_metric,
)
from src.cluster.cluster_app_classes import ChannelMapper
from src.startup import context


class DBCChannelMapper(ChannelMapper):
    def __init__(self, headstage_label: str):
        channel_strings_top_to_bottom = build_channel_strings(headstage_label)
        self.channels_top_to_bottom = [Channel[channel.replace("-", "_")] for channel in channel_strings_top_to_bottom]
        self.channel_map = {}

        height = 2015
        for channel in self.channels_top_to_bottom:
            self.channel_map[channel] = np.array([0, height])
            height -= 65

    def get_coordinates(self, channel: Channel) -> dict[any, np.ndarray]:
        return self.channel_map[channel]



def calculate_avg_distance_scaled_correlation(cluster_channels: set, channel_strings: list,
                                              correlations: dict):
    """
    Calculate average distance-scaled correlation metric for cluster channels.

    For each cluster channel:
    - Sum of (correlation / distance) for all other channels with valid correlations
    - Distance is the index difference between channels in the channel_strings list
    - Average by the number of channels with valid correlations

    If multiple cluster channels exist, return the mean of their individual metrics.

    Args:
        cluster_channels: Set of cluster channel names
        channel_strings: Ordered list of channel names (top to bottom)
        correlations: Dictionary of {cluster_channel: {channel: correlation_value}}

    Returns:
        float: Average distance-scaled correlation, or None if no valid data
    """
    if not correlations or not cluster_channels:
        return None

    # Build channel index map
    channel_index = {ch: idx for idx, ch in enumerate(channel_strings)}

    cluster_metrics = []

    for cluster_channel in cluster_channels:
        if cluster_channel not in correlations:
            continue

        if cluster_channel not in channel_index:
            print(f"Warning: Cluster channel {cluster_channel} not in channel list")
            continue

        cluster_idx = channel_index[cluster_channel]
        corr_data = correlations[cluster_channel]

        distance_scaled_sum = 0.0
        valid_count = 0

        for channel, correlation in corr_data.items():
            # Skip the cluster channel itself
            if channel == cluster_channel:
                continue

            # Skip NaN correlations
            if np.isnan(correlation):
                continue

            # Get channel index
            if channel not in channel_index:
                continue

            channel_idx = channel_index[channel]

            # Calculate distance (minimum of 1)
            distance = max(1, abs(cluster_idx - channel_idx))

            # Add to sum
            distance_scaled_sum += correlation / distance
            valid_count += 1

        # Calculate average for this cluster channel
        if valid_count > 0:
            cluster_metric = distance_scaled_sum
            cluster_metrics.append(cluster_metric)
            print(f"  {cluster_channel}: {cluster_metric:.4f} (based on {valid_count} channels)")

    # Return average across all cluster channels
    if cluster_metrics:
        avg_metric = np.mean(cluster_metrics)
        print(f"\nOverall average distance-scaled correlation: {avg_metric:.4f}")
        return avg_metric
    else:
        return None


def save_session_metric(conn: Connection, session_id: str, cluster_size: int,
                        avg_distance_scaled_correlation: float = None):
    """
    Save session-level metrics to EStimShapeSessionData table.

    Args:
        conn: Database connection
        session_id: Session identifier
        cluster_size: Number of cluster channels
        avg_distance_scaled_correlation: The calculated metric (or None)
    """
    # Ensure table exists
    create_table_sql = """
                       CREATE TABLE IF NOT EXISTS EStimShapeSessionData
                       (
                           session_id                      VARCHAR(10) NOT NULL PRIMARY KEY,
                           cluster_size                    INT         NOT NULL,
                           avg_distance_scaled_correlation FLOAT       NULL,
                           CONSTRAINT EStimShapeSessionData_ibfk_1
                               FOREIGN KEY (session_id) REFERENCES Sessions (session_id)
                                   ON DELETE CASCADE
                       ) CHARSET = latin1; \
                       """
    conn.execute(create_table_sql)

    # Insert or update
    upsert_sql = """
                 INSERT INTO EStimShapeSessionData
                     (session_id, avg_distance_scaled_correlation)
                 VALUES (%s, %s)
                 ON DUPLICATE KEY UPDATE 
                                         avg_distance_scaled_correlation = VALUES(avg_distance_scaled_correlation) \
                 """

    # Convert numpy types to native Python types for MySQL
    avg_dist_corr_value = float(
        avg_distance_scaled_correlation) if avg_distance_scaled_correlation is not None else None

    conn.execute(upsert_sql, (session_id, avg_dist_corr_value))
    print(f"\nSaved to EStimShapeSessionData: session_id={session_id}, "
          f"cluster_size={cluster_size}, avg_distance_scaled_correlation={avg_dist_corr_value}")


def plot_channel_preferences(session_id: str, headstage_label: str = "A", save_path: str = None):
    """
    Plot raw channels ordered top-to-bottom, colored by isochromatic preference index.

    Args:
        session_id: The session identifier to query
        headstage_label: The headstage label (default "A")
        save_path: Optional path to save the figure as PNG (e.g., "output.png")
    """
    channel_strings = build_channel_strings(headstage_label)
    conn = Connection("allen_data_repository")

    # ---- load data via loader classes ----
    cluster_channels = ClusterChannelLoader(session_id, conn).load()
    print(f"Cluster channels for session {session_id}: {cluster_channels}")

    response_matrix = ChannelResponseVectorLoader(session_id, conn).load()
    if response_matrix:
        print(f"Loaded response vectors for {len(response_matrix)} channels")
    else:
        print("Warning: No response vectors found - correlation analysis will be skipped")

    iso_loader = IsochromaticPreferenceLoader(session_id, conn)
    iso_metrics = iso_loader.as_metrics()
    frequencies = iso_loader.frequencies
    n_frequencies = len(frequencies)

    solid_metric = SolidPreferenceLoader(session_id, conn).as_metric(title='Solid Preference')

    freq_metric = PreferredFrequencyLoader(session_id, conn).as_normalized_metric(
        frequencies, title='Preferred\nFrequency')

    if not iso_metrics and solid_metric.compute() == {}:
        print(f"No data found for session {session_id}")
        return

    print(f"Found isochromatic data for {n_frequencies} frequencies: {frequencies}")
    print(f"Found solid preference data for {len(solid_metric.compute())} channels")
    print(f"Plotting {len(channel_strings)} channels")

    cluster_channel_list = sorted(c for c in cluster_channels if c in response_matrix)
    corr_metrics = [
        StimVectorCorrelation.vs_channel(
            response_matrix, ch,
            method='spearman', zscore=False,
            title=f'ρ vs {ch}',
        )
        for ch in cluster_channel_list
    ]
    n_corr_cols = len(corr_metrics)

    # Create subplots - adjust based on number of correlation columns
    # Layout: [preferred freq (1 col), isochromatic (4 cols), solid (1 col),
    #          correlation cols (n_corr_cols)]
    if n_corr_cols > 0:
        width_ratios = [1, 4, 1] + [1] * n_corr_cols
        n_cols = 3 + n_corr_cols
        fig, axes = plt.subplots(1, n_cols, figsize=(16 + 2 * n_corr_cols, 12),
                                 sharey=True, gridspec_kw={'width_ratios': width_ratios, 'wspace': 0.15})
        ax_freq = axes[0]
        ax_iso = axes[1]
        ax_solid = axes[2]
        ax_corr_list = axes[3:]
    else:
        fig, (ax_freq, ax_iso, ax_solid) = plt.subplots(1, 3, figsize=(15, 12),
                                               sharey=True, gridspec_kw={'width_ratios': [1, 4, 1], 'wspace': 0.15})
        ax_corr_list = []

    # Set up colormap (diverging around 0)
    cmap, norm = default_cmap_norm()

    # Plot preferred frequency as the leftmost column (owns the y-tick labels)
    scatter = None
    _, ref = render_metric(
        ax_freq, freq_metric, channel_strings, cluster_channels,
        cmap=cmap, norm=norm,
        show_yticks=True,
    )
    scatter = ref or scatter

    # Plot isochromatic preferences - one metric per frequency, all on ax_iso
    for freq_idx, metric in enumerate(iso_metrics):
        _, ref = render_metric(
            ax_iso, metric, channel_strings, cluster_channels,
            cmap=cmap, norm=norm,
            x_position=freq_idx,
            show_yticks=False,
            format_axis=False, set_title=False,
        )
        scatter = ref or scatter

    # Multi-column axis formatting (frequency labels along x-axis)
    ax_iso.set_xlim(-0.2, n_frequencies - 0.8)  # Tighter limits to reduce gaps
    ax_iso.set_xticks(range(n_frequencies))
    ax_iso.set_xticklabels([f'{freq} Hz' for freq in frequencies], fontsize=10)
    ax_iso.set_title('Isochromatic Preference by Frequency', fontsize=12, fontweight='bold')
    ax_iso.grid(True, axis='y', alpha=0.3, linestyle='--')
    ax_iso.grid(True, axis='x', alpha=0.2, linestyle='--')

    # Plot solid preference and correlations through the same pipeline
    correlations: dict = {}  # {cluster_channel: {channel: rho}} for downstream stats
    for ax, metric in [(ax_solid, solid_metric), *zip(ax_corr_list, corr_metrics)]:
        data, ref = render_metric(
            ax, metric, channel_strings, cluster_channels,
            cmap=cmap, norm=norm,
        )
        scatter = ref or scatter
        if metric.self_channel is not None:
            correlations[metric.self_channel] = data

    # Overall title
    title_text = f'Channel Preference Indices\nSession: {session_id}'
    if n_corr_cols > 0:
        title_text += f' | Correlations based on {len(response_matrix)} channels with response vectors'
    fig.suptitle(title_text, fontsize=14, fontweight='bold', y=0.95)

    # Adjust layout to make room for colorbar at bottom
    plt.tight_layout(rect=[0, 0.06, 1, 0.93])

    # Add colorbar at the bottom
    cbar_ax = fig.add_axes([0.15, 0.02, 0.7, 0.02])  # [left, bottom, width, height]
    cbar = plt.colorbar(scatter, cax=cbar_ax, orientation='horizontal')
    cbar.set_label('Preference Index (Red = Prefers Isochromatic/3D, Blue = Prefers Isoluminant/2D)',
                   fontsize=10)

    # Add legend for cluster channels
    if cluster_channels:
        ax_iso.legend(
            handles=cluster_marker_legend_handles(),
            loc='upper left', fontsize=9,
        )

    # Save figure if path provided
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"\nFigure saved to: {save_path}")
    plt.show()

    # Print summary statistics
    print(f"\n=== Summary for session {session_id} ===")
    print(f"Cluster channels: {sorted(cluster_channels) if cluster_channels else 'None'}")

    print(f"\n--- Isochromatic Preference (by frequency) ---")
    for metric, frequency in zip(iso_metrics, frequencies):
        freq_data = metric.compute()
        if freq_data:
            values = list(freq_data.values())
            cluster_values = [v for ch, v in freq_data.items() if ch in cluster_channels]
            print(f"\nFrequency {frequency} Hz:")
            print(f"  Channels with data: {len(freq_data)}/{len(channel_strings)}")
            print(f"  Index range: [{min(values):.3f}, {max(values):.3f}]")
            print(f"  Mean index: {np.mean(values):.3f}")
            if cluster_values:
                print(f"  Cluster channel indices: {[f'{v:.3f}' for v in cluster_values]}")

    print(f"\n--- Solid Preference Index ---")
    solid_data = solid_metric.compute()
    if solid_data:
        values = list(solid_data.values())
        cluster_values = [v for ch, v in solid_data.items() if ch in cluster_channels]
        print(f"  Channels with data: {len(solid_data)}/{len(channel_strings)}")
        print(f"  Index range: [{min(values):.3f}, {max(values):.3f}]")
        print(f"  Mean index: {np.mean(values):.3f}")
        if cluster_values:
            print(f"  Cluster channel indices: {[f'{v:.3f}' for v in cluster_values]}")
    else:
        print("  No solid preference data available")

    # Print correlation statistics
    if correlations:
        print(f"\n--- Channel Correlations (Spearman's ρ) ---")
        for cluster_channel in cluster_channel_list:
            corr_data = correlations[cluster_channel]
            valid_corrs = [v for v in corr_data.values() if not np.isnan(v)]

            if valid_corrs:
                print(f"\nCorrelations with {cluster_channel}:")
                print(f"  Channels with data: {len(valid_corrs)}/{len(channel_strings)}")
                print(f"  Correlation range: [{min(valid_corrs):.3f}, {max(valid_corrs):.3f}]")
                print(f"  Mean correlation: {np.mean(valid_corrs):.3f}")

                # Top 5 most correlated channels (excluding self)
                sorted_corrs = sorted([(ch, v) for ch, v in corr_data.items()
                                       if not np.isnan(v) and ch != cluster_channel],
                                      key=lambda x: abs(x[1]), reverse=True)[:5]
                if sorted_corrs:
                    print(f"  Top 5 most correlated:")
                    for ch, corr in sorted_corrs:
                        print(f"    {ch}: ρ = {corr:.3f}")

    # Calculate and save session-level metric
    print(f"\n--- Average Distance-Scaled Correlation ---")
    avg_dist_scaled_corr = calculate_avg_distance_scaled_correlation(
        cluster_channels, channel_strings, correlations
    )

    # Save to database
    # cluster_size = len(cluster_channels)
    save_session_metric(conn, session_id, None, avg_dist_scaled_corr)


def main():
    # Example usage - change session_id as needed
    # (session_id, _) = read_session_id_from_db_name(context.ga_database)
    session_ids = ["260528_0"]
    # session_ids = ["260120_0", "260115_0", "260113_0", "260108_0", "260107_0", "251231_0", "251226_0"]
    headstage_label = "A"

    # Optional: save figure as PNG
    # save_path = f"channel_preferences_{session_id}.png"
    for session_id in session_ids:
        save_path = f"/home/connorlab/Documents/plots/{session_id}/preference_clusters.png"  # Set to None to skip saving
        plot_channel_preferences(session_id, headstage_label, save_path=save_path)


if __name__ == '__main__':
    main()