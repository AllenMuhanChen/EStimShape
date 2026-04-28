import json
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import spearmanr
from clat.intan.channels import Channel
from clat.util.connection import Connection
from src.analysis.channel_metric_plot import (
    build_channel_strings,
    cluster_marker_legend_handles,
    default_cmap_norm,
    format_single_column_axis,
    plot_metric_column,
)
from src.cluster.cluster_app_classes import ChannelMapper
from src.repository.export_to_repository import read_session_id_and_date_from_db_name
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
    # Get ordered channel names (as strings like "A-007")
    channel_strings = build_channel_strings(headstage_label)

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

    # Load response vectors and calculate correlations
    vectors = load_response_vectors(conn, session_id, vector_type='ga_mean_response')

    if vectors:
        print(f"Loaded response vectors for {len(vectors)} channels")
        correlations = calculate_correlations(vectors, cluster_channels)
        print(f"Calculated correlations for {len(correlations)} cluster channels")
    else:
        print("Warning: No response vectors found - correlation analysis will be skipped")
        correlations = {}

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
    cmap, norm = default_cmap_norm()

    # Plot isochromatic preferences - one column per frequency, all on ax_iso
    scatter = None
    for freq_idx, frequency in enumerate(frequencies):
        ref = plot_metric_column(
            ax_iso, frequency_data[frequency],
            channel_strings, cluster_channels,
            cmap=cmap, norm=norm,
            x_position=freq_idx,
            show_yticks=(freq_idx == 0),
        )
        scatter = ref or scatter

    # Format isochromatic plot (multi-column on a shared axis)
    ax_iso.set_xlim(-0.2, n_frequencies - 0.8)  # Tighter limits to reduce gaps
    ax_iso.set_xticks(range(n_frequencies))
    ax_iso.set_xticklabels([f'{freq} Hz' for freq in frequencies], fontsize=10)
    ax_iso.set_title('Isochromatic Preference by Frequency', fontsize=12, fontweight='bold')
    ax_iso.grid(True, axis='y', alpha=0.3, linestyle='--')
    ax_iso.grid(True, axis='x', alpha=0.2, linestyle='--')  # Add vertical grid lines

    # Plot solid preference - single column
    ref = plot_metric_column(
        ax_solid, solid_data,
        channel_strings, cluster_channels,
        cmap=cmap, norm=norm,
    )
    scatter = ref or scatter
    format_single_column_axis(ax_solid)
    ax_solid.set_title('Solid Preference', fontsize=12, fontweight='bold')

    # Plot correlation columns - one per cluster channel
    for ax_corr, cluster_channel in zip(ax_corr_list, cluster_channel_list):
        ref = plot_metric_column(
            ax_corr, correlations[cluster_channel],
            channel_strings, cluster_channels,
            cmap=cmap, norm=norm,
            self_channel=cluster_channel,
        )
        scatter = ref or scatter
        format_single_column_axis(ax_corr)
        ax_corr.set_title(f'ρ vs {cluster_channel}', fontsize=12, fontweight='bold')

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
    session_ids = ["260426_0"]
    # session_ids = ["260120_0", "260115_0", "260113_0", "260108_0", "260107_0", "251231_0", "251226_0"]
    headstage_label = "A"

    # Optional: save figure as PNG
    # save_path = f"channel_preferences_{session_id}.png"
    for session_id in session_ids:
        save_path = f"/home/connorlab/Documents/plots/{session_id}/preference_clusters.png"  # Set to None to skip saving
        plot_channel_preferences(session_id, headstage_label, save_path=save_path)


if __name__ == '__main__':
    main()