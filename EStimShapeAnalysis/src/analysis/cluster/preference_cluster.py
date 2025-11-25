import json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from scipy.stats import spearmanr
from clat.intan.channels import Channel
from clat.util.connection import Connection
from src.cluster.cluster_app_classes import ChannelMapper
from src.repository.export_to_repository import read_session_id_from_db_name
from src.startup import context


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


def load_response_vectors(conn: Connection, session_id: str, vector_type: str = 'ga_mean_response'):
    """
    Load response vectors from the database.

    Returns:
        dict: {channel_name: {'id_vector': [...], 'response_vector': [...]}}
    """
    query = """
            SELECT unit_name, id_vector, response_vector
            FROM ChannelResponseVectors
            WHERE session_id = %s \
              AND vector_type = %s
            """

    conn.execute(query, (session_id, vector_type))
    results = conn.fetch_all()

    vectors = {}
    for unit_name, id_vector_json, response_vector_json in results:
        vectors[unit_name] = {
            'id_vector': json.loads(id_vector_json),
            'response_vector': json.loads(response_vector_json)
        }

    return vectors


def calculate_correlations(vectors: dict, cluster_channels: set):
    """
    Calculate Spearman correlations between each channel and each cluster channel.

    Returns:
        dict: {cluster_channel: {channel: correlation_value}}
    """
    correlations = {}

    for cluster_channel in cluster_channels:
        if cluster_channel not in vectors:
            print(f"Warning: Cluster channel {cluster_channel} has no response vector")
            continue

        cluster_data = vectors[cluster_channel]
        cluster_id_vector = cluster_data['id_vector']
        cluster_response = cluster_data['response_vector']

        correlations[cluster_channel] = {}

        for channel, data in vectors.items():
            # Find common stimuli
            channel_id_vector = data['id_vector']
            channel_response = data['response_vector']

            # Get intersection of stimulus IDs
            common_ids = sorted(set(cluster_id_vector) & set(channel_id_vector))

            if len(common_ids) < 3:
                # Need at least 3 points for correlation
                correlations[cluster_channel][channel] = np.nan
                continue

            # Align responses to common stimuli
            cluster_aligned = [cluster_response[cluster_id_vector.index(sid)] for sid in common_ids]
            channel_aligned = [channel_response[channel_id_vector.index(sid)] for sid in common_ids]

            # Calculate Spearman correlation
            rho, _ = spearmanr(cluster_aligned, channel_aligned)
            correlations[cluster_channel][channel] = rho

    return correlations


def plot_channel_preferences(session_id: str, headstage_label: str = "A", save_path: str = None):
    """
    Plot raw channels ordered top-to-bottom, colored by isochromatic preference index.

    Args:
        session_id: The session identifier to query
        headstage_label: The headstage label (default "A")
        save_path: Optional path to save the figure as PNG (e.g., "output.png")
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
                    WHERE e.session_id = %s
                    """
    conn.execute(cluster_query, (session_id,))
    cluster_results = conn.fetch_all()
    cluster_channels = set(row[0] for row in cluster_results)

    print(f"Cluster channels for session {session_id}: {cluster_channels}")

    # Load response vectors and calculate correlations
    vectors = load_response_vectors(conn, session_id, vector_type='ga_mean_response')

    if vectors:
        print(f"Loaded response vectors for {len(vectors)} channels")
        correlations = calculate_correlations(vectors, cluster_channels)
        print(f"Calculated correlations for {len(correlations)} cluster channels")
    else:
        print("Warning: No response vectors found - correlation columns will be skipped")
        correlations = {}

    # Query isochromatic preference indices for raw channels (not sorted units)
    iso_query = """
                SELECT unit_name, frequency, isochromatic_preference_index
                FROM IsochromaticPreferenceIndices
                WHERE session_id = %s
                  AND unit_name NOT LIKE '%Unit%'
                ORDER BY frequency, unit_name
                """

    conn.execute(iso_query, (session_id,))
    iso_results = conn.fetch_all()

    # Query solid preference indices for raw channels
    solid_query = """
                  SELECT unit_name, solid_preference_index
                  FROM SolidPreferenceIndices
                  WHERE session_id = %s
                    AND unit_name NOT LIKE '%Unit%'
                  ORDER BY unit_name
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

    # Determine number of correlation columns
    n_corr_cols = len(correlations)
    cluster_channel_list = sorted(correlations.keys()) if correlations else []

    # Create subplots - adjust based on number of correlation columns
    # Layout: [isochromatic (4 cols), solid (1 col), correlation cols (n_corr_cols)]
    if n_corr_cols > 0:
        width_ratios = [4, 1] + [1] * n_corr_cols
        n_cols = 2 + n_corr_cols
        fig, axes = plt.subplots(1, n_cols, figsize=(14 + 2 * n_corr_cols, 12),
                                 sharey=True, gridspec_kw={'width_ratios': width_ratios, 'wspace': 0.15})
        ax_iso = axes[0]
        ax_solid = axes[1]
        ax_corr_list = axes[2:] if n_corr_cols > 0 else []
    else:
        fig, (ax_iso, ax_solid) = plt.subplots(1, 2, figsize=(14, 12),
                                               sharey=True, gridspec_kw={'width_ratios': [4, 1], 'wspace': 0.15})
        ax_corr_list = []

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
    ax_iso.set_xlim(-0.2, n_frequencies - 0.8)
    ax_iso.set_xticks(range(n_frequencies))
    ax_iso.set_xticklabels([f'{freq} Hz' for freq in frequencies], fontsize=10)
    ax_iso.set_yticks(range(1, len(channel_strings) + 1))
    ax_iso.set_yticklabels(channel_strings[::-1], fontsize=8)
    ax_iso.set_ylabel('Channel (Top → Bottom)', fontsize=10)
    ax_iso.set_title('Isochromatic Preference by Frequency', fontsize=12, fontweight='bold')
    ax_iso.grid(True, axis='y', alpha=0.3, linestyle='--')
    ax_iso.grid(True, axis='x', alpha=0.2, linestyle='--')
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

    # Plot correlation columns - one per cluster channel
    for col_idx, (ax_corr, cluster_channel) in enumerate(zip(ax_corr_list, cluster_channel_list)):
        corr_data = correlations[cluster_channel]

        for idx, channel_str in enumerate(channel_strings):
            y_pos = len(channel_strings) - idx  # Top to bottom
            is_cluster = channel_str in cluster_channels
            is_self = channel_str == cluster_channel

            if channel_str in corr_data and not np.isnan(corr_data[channel_str]):
                # Has correlation data
                color_val = corr_data[channel_str]
                size = 200 if is_cluster else 100
                marker = '*' if is_cluster else 'o'
                edge_color = 'black'
                line_width = 2.0 if is_self else (0.5 if is_cluster else 0.5)

                scatter = ax_corr.scatter(0, y_pos, c=color_val, s=size,
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

                ax_corr.scatter(0, y_pos, c='lightgray', s=size,
                                marker=marker, edgecolors=edge_color, linewidths=line_width,
                                alpha=0.7 if is_cluster else 0.5,
                                zorder=10 if is_cluster else 1)

        # Format correlation plot
        ax_corr.set_xlim(-0.5, 0.5)
        ax_corr.set_xticks([])
        ax_corr.set_title(f'ρ vs {cluster_channel}', fontsize=12, fontweight='bold')
        ax_corr.axvline(0, color='black', linewidth=0.5, alpha=0.3)
        ax_corr.grid(True, axis='y', alpha=0.3, linestyle='--')
        ax_corr.set_ylim(0.5, len(channel_strings) + 0.5)

    # Overall title
    title_text = f'Channel Preference Indices\nSession: {session_id}'
    if n_corr_cols > 0:
        title_text += f' | Correlations based on {len(vectors)} channels with response vectors'
    fig.suptitle(title_text, fontsize=14, fontweight='bold', y=0.95)

    # Adjust layout to make room for colorbar at bottom
    plt.tight_layout(rect=[0, 0.06, 1, 0.93])

    # Add colorbar at the bottom
    cbar_ax = fig.add_axes([0.15, 0.02, 0.7, 0.02])  # [left, bottom, width, height]
    cbar = plt.colorbar(scatter, cax=cbar_ax, orientation='horizontal')
    cbar.set_label('Preference Index / Correlation (Red = Positive, Blue = Negative)',
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

    # Save figure if path provided
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"\nFigure saved to: {save_path}")
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


def main():
    # Example usage - change session_id as needed
    (session_id, _) = read_session_id_from_db_name(context.ga_database)
    headstage_label = "A"

    # Optional: save figure as PNG
    save_path = f"/home/connorlab/Documents/plots/{session_id}/preference_clusters.png"

    plot_channel_preferences(session_id, headstage_label, save_path=save_path)


if __name__ == '__main__':
    main()