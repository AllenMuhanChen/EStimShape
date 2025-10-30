import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from clat.intan.channels import Channel
from clat.util.connection import Connection
from src.cluster.cluster_app_classes import ChannelMapper


class DBCChannelMapper(ChannelMapper):
    def __init__(self, headstage_label: str):
        channel_numbers_top_to_bottom = [7, 8, 25, 22, 0, 15, 24, 23, 6, 9, 26, 21, 5, 10, 31, 16, 27, 20, 4, 11, 28,
                                         19, 1, 14, 3, 12, 29, 18, 2, 13, 30, 17]
        channel_strings_top_to_bottom = [f"{headstage_label}-{num:03}" for num in channel_numbers_top_to_bottom]
        self.channels_top_to_bottom = [Channel[channel.replace("-", "_")] for channel in channel_strings_top_to_bottom]
        self.channel_map = {}

        height = 2015
        for channel in self.channels_top_to_bottom:
            self.channel_map[channel] = np.array([0, height])
            height -= 65

    def get_coordinates(self, channel: Channel) -> dict[any, np.ndarray]:
        return self.channel_map[channel]


def plot_channel_preferences(session_id: str, headstage_label: str = "A"):
    """
    Plot raw channels ordered top-to-bottom, colored by isochromatic preference index.

    Args:
        session_id: The session identifier to query
        headstage_label: The headstage label (default "A")
    """
    # Initialize channel mapper
    mapper = DBCChannelMapper(headstage_label)

    # Get ordered channel names (as strings like "A-007")
    channel_strings = [f"{headstage_label}-{str(ch).split('_')[1]}"
                       for ch in mapper.channels_top_to_bottom]

    # Connect to database
    conn = Connection("allen_data_repository")

    # Query cluster channels for this session
    cluster_query = """
                    SELECT DISTINCT c.channel
                    FROM ClusterInfo c
                             JOIN Experiments e ON c.experiment_id = e.experiment_id
                    WHERE e.session_id = %s \
                    """
    conn.execute(cluster_query, (session_id,))
    cluster_results = conn.fetch_all()
    cluster_channels = set(row[0] for row in cluster_results)

    print(f"Cluster channels for session {session_id}: {cluster_channels}")

    # Query isochromatic preference indices for raw channels (not sorted units)
    iso_query = """
                SELECT unit_name, frequency, isochromatic_preference_index
                FROM IsochromaticPreferenceIndices
                WHERE session_id = %s
                  AND unit_name NOT LIKE '%Unit%'
                ORDER BY frequency, unit_name \
                """

    conn.execute(iso_query, (session_id,))
    iso_results = conn.fetch_all()

    # Query solid preference indices for raw channels
    solid_query = """
                  SELECT unit_name, solid_preference_index
                  FROM SolidPreferenceIndices
                  WHERE session_id = %s
                    AND unit_name NOT LIKE '%Unit%'
                  ORDER BY unit_name \
                  """

    conn.execute(solid_query, (session_id,))
    solid_results = conn.fetch_all()

    if not iso_results and not solid_results:
        print(f"No data found for session {session_id}")
        return

    # Organize isochromatic data by frequency
    frequency_data = {}
    for unit_name, frequency, index_value in iso_results:
        if frequency not in frequency_data:
            frequency_data[frequency] = {}
        frequency_data[frequency][unit_name] = index_value

    # Organize solid preference data
    solid_data = {}
    for unit_name, index_value in solid_results:
        solid_data[unit_name] = index_value

    # Get sorted frequencies
    frequencies = sorted(frequency_data.keys())
    n_frequencies = len(frequencies)

    print(f"Found isochromatic data for {n_frequencies} frequencies: {frequencies}")
    print(f"Found solid preference data for {len(solid_data)} channels")
    print(f"Plotting {len(channel_strings)} channels")

    # Create subplots - 1 row, 2 columns (isochromatic with 4 freq columns, and solid)
    fig, (ax_iso, ax_solid) = plt.subplots(1, 2, figsize=(14, 12),
                                           sharey=True, gridspec_kw={'width_ratios': [4, 1], 'wspace': 0.15})

    # Set up colormap (diverging around 0)
    cmap = plt.cm.RdBu_r  # Red for positive (prefers isochromatic/3D), Blue for negative
    norm = TwoSlopeNorm(vmin=-1.0, vcenter=0.0, vmax=1.0)

    # Plot isochromatic preferences - 4 columns of dots (one per frequency)
    scatter = None
    for freq_idx, frequency in enumerate(frequencies):
        freq_data = frequency_data[frequency]
        x_position = freq_idx  # Horizontal position for this frequency

        # Prepare data for plotting
        for idx, channel_str in enumerate(channel_strings):
            y_pos = len(channel_strings) - idx  # Top to bottom
            is_cluster = channel_str in cluster_channels

            if channel_str in freq_data:
                # Has data - color by preference index
                color_val = freq_data[channel_str]
                size = 200 if is_cluster else 100
                marker = '*' if is_cluster else 'o'
                edge_color = 'black'
                line_width = 0.5 if is_cluster else 0.5

                scatter = ax_iso.scatter(x_position, y_pos, c=color_val, s=size,
                                         marker=marker, cmap=cmap, norm=norm,
                                         edgecolors=edge_color, linewidths=line_width,
                                         alpha=0.9 if is_cluster else 0.8,
                                         zorder=10 if is_cluster else 1)
            else:
                # No data - use gray
                size = 120 if is_cluster else 50
                marker = '*' if is_cluster else 'o'
                edge_color = 'black' if is_cluster else 'gray'
                line_width = 0.5 if is_cluster else 0.5

                ax_iso.scatter(x_position, y_pos, c='lightgray', s=size,
                               marker=marker, edgecolors=edge_color, linewidths=line_width,
                               alpha=0.7 if is_cluster else 0.5,
                               zorder=10 if is_cluster else 1)

    # Format isochromatic plot
    ax_iso.set_xlim(-0.2, n_frequencies - 0.8)  # Tighter limits to reduce gaps
    ax_iso.set_xticks(range(n_frequencies))
    ax_iso.set_xticklabels([f'{freq} Hz' for freq in frequencies], fontsize=10)
    ax_iso.set_yticks(range(1, len(channel_strings) + 1))
    ax_iso.set_yticklabels(channel_strings[::-1], fontsize=8)
    ax_iso.set_ylabel('Channel (Top → Bottom)', fontsize=10)
    ax_iso.set_title('Isochromatic Preference by Frequency', fontsize=12, fontweight='bold')
    ax_iso.grid(True, axis='y', alpha=0.3, linestyle='--')
    ax_iso.grid(True, axis='x', alpha=0.2, linestyle='--')  # Add vertical grid lines
    ax_iso.set_ylim(0.5, len(channel_strings) + 0.5)

    # Plot solid preference - single column
    for idx, channel_str in enumerate(channel_strings):
        y_pos = len(channel_strings) - idx  # Top to bottom
        is_cluster = channel_str in cluster_channels

        if channel_str in solid_data:
            # Has data - color by preference index
            color_val = solid_data[channel_str]
            size = 200 if is_cluster else 100
            marker = '*' if is_cluster else 'o'
            edge_color = 'black'
            line_width = 0.5 if is_cluster else 0.5

            scatter = ax_solid.scatter(0, y_pos, c=color_val, s=size,
                                       marker=marker, cmap=cmap, norm=norm,
                                       edgecolors=edge_color, linewidths=line_width,
                                       alpha=0.9 if is_cluster else 0.8,
                                       zorder=10 if is_cluster else 1)
        else:
            # No data - use gray
            size = 120 if is_cluster else 50
            marker = '*' if is_cluster else 'o'
            edge_color = 'black' if is_cluster else 'gray'
            line_width = 0.5 if is_cluster else 0.5

            ax_solid.scatter(0, y_pos, c='lightgray', s=size,
                             marker=marker, edgecolors=edge_color, linewidths=line_width,
                             alpha=0.7 if is_cluster else 0.5,
                             zorder=10 if is_cluster else 1)

    # Format solid preference plot
    ax_solid.set_xlim(-0.5, 0.5)
    ax_solid.set_xticks([])
    ax_solid.set_title('Solid Preference', fontsize=12, fontweight='bold')
    ax_solid.axvline(0, color='black', linewidth=0.5, alpha=0.3)
    ax_solid.grid(True, axis='y', alpha=0.3, linestyle='--')
    ax_solid.set_ylim(0.5, len(channel_strings) + 0.5)

    # Overall title
    fig.suptitle(f'Channel Preference Indices\nSession: {session_id}',
                 fontsize=14, fontweight='bold', y=0.95)

    # Adjust layout to make room for colorbar at bottom
    plt.tight_layout(rect=[0, 0.06, 1, 0.93])

    # Add colorbar at the bottom
    cbar_ax = fig.add_axes([0.15, 0.02, 0.7, 0.02])  # [left, bottom, width, height]
    cbar = plt.colorbar(scatter, cax=cbar_ax, orientation='horizontal')
    cbar.set_label('Preference Index (Red = Prefers Isochromatic/3D, Blue = Prefers Isoluminant/2D)',
                   fontsize=10)

    # Add legend for cluster channels
    if cluster_channels:
        from matplotlib.lines import Line2D
        legend_elements = [
            Line2D([0], [0], marker='*', color='w', markerfacecolor='lightcoral',
                   markeredgecolor='black', markersize=14, markeredgewidth=2,
                   label='Cluster Channel', linestyle='None')
        ]
        ax_iso.legend(handles=legend_elements, loc='upper left', fontsize=9)

    plt.show()

    # Print summary statistics
    print(f"\n=== Summary for session {session_id} ===")
    print(f"Cluster channels: {sorted(cluster_channels) if cluster_channels else 'None'}")

    print(f"\n--- Isochromatic Preference (by frequency) ---")
    for frequency in frequencies:
        freq_data = frequency_data[frequency]
        n_channels_with_data = len(freq_data)
        if n_channels_with_data > 0:
            values = list(freq_data.values())

            # Check cluster channel values
            cluster_values = [v for ch, v in freq_data.items() if ch in cluster_channels]

            print(f"\nFrequency {frequency} Hz:")
            print(f"  Channels with data: {n_channels_with_data}/{len(channel_strings)}")
            print(f"  Index range: [{min(values):.3f}, {max(values):.3f}]")
            print(f"  Mean index: {np.mean(values):.3f}")
            if cluster_values:
                print(f"  Cluster channel indices: {[f'{v:.3f}' for v in cluster_values]}")

    print(f"\n--- Solid Preference Index ---")
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


def main():
    # Example usage - change session_id as needed
    session_id = "251029_0"
    headstage_label = "A"

    plot_channel_preferences(session_id, headstage_label)


if __name__ == '__main__':
    main()