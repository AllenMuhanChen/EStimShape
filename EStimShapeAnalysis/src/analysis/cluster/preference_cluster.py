"""
Preference cluster: the probe's per-channel preference columns plus ρ vs each GA
channel, and the session's average distance-scaled correlation (saved to
EStimShapeSessionData).

The figure is now drawn by src/analysis/probe_analysis (also the explorer's "Probe
analysis" module, where every column can be toggled on and off).
"""

import numpy as np
from clat.intan.channels import Channel
from clat.util.connection import Connection
from src.analysis.channel_metric_plot import build_channel_strings
from src.cluster.cluster_app_classes import ChannelMapper
from src.repository.export_to_repository import read_session_id_and_date_from_db_name
from src.startup import context
from src.startup.apply_session_context import apply_session_context


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


def plot_channel_preferences(session_id: str, headstage_label: str = "A",
                             save_root: str = None):
    """
    Preference-cluster figure: the probe top -> bottom with the tuning columns
    (preferred frequency, orientation tuning frequency, preferred orientation,
    preferred colour, isochromatic preference per frequency, solid preference and its
    significance) and ρ vs each GA channel. Drawn by probe_analysis (the same figure
    as the explorer's "Probe analysis" module, which can toggle more columns).

    Then computes the average distance-scaled correlation of the GA channels and
    saves it to EStimShapeSessionData.
    """
    from src.analysis.probe_analysis.probe_analysis import run_probe_analysis
    from src.analysis.probe_analysis.probe_data import ProbeData

    columns = ['pref_freq', 'orient_freq', 'pref_orient', 'pref_color', 'iso',
               'solid', 'solid_sig', 'corr_each']
    data = ProbeData(session_id, headstage=headstage_label)
    _fig, blocks, _out_dir = run_probe_analysis(session_id, columns, save_root=save_root, data=data)

    # {GA channel: {channel: rho}} from the "ρ vs each GA channel" columns
    correlations = {sub.self_channel: sub.data
                    for b in blocks if b.key == 'corr_each' for sub in b.subs}
    cluster_channels = data.ga_channels()
    print(f"\n--- Average Distance-Scaled Correlation ---")
    avg_dist_scaled_corr = calculate_avg_distance_scaled_correlation(
        cluster_channels, data.channel_strs(), correlations
    )
    save_session_metric(data.repo_conn(), session_id, None, avg_dist_scaled_corr)


def main():
    # Example usage - change session_id as needed
    (session_id, _) = read_session_id_and_date_from_db_name(context.ga_database)
    session_ids = [session_id]
    # session_ids = ["260120_0", "260115_0", "260113_0", "260108_0", "260107_0", "251231_0", "251226_0"]
    headstage_label = "A"
    # Figures go in <save_root>/<session>/probe_analysis/<timestamp>/; None = don't save
    save_root = "/home/connorlab/Documents/plots"
    for session_id in session_ids:
        if len(session_ids) > 1:
            apply_session_context(session_id)
        plot_channel_preferences(session_id, headstage_label, save_root=save_root)


if __name__ == '__main__':
    main()