from typing import Dict, List, Tuple
import numpy as np
import pandas as pd
from scipy import stats as statss
from clat.pipeline.pipeline_base_classes import (
    ComputationModule, InputT, OutputT, OutputHandler, AnalysisModuleFactory
)
from clat.util.connection import Connection


def create_channel_filter_module(session_id: str):
    """Factory function to create the channel filtering analysis module."""
    return AnalysisModuleFactory.create(
        computation=ChannelFilterCalculator(),
        output_handler=ChannelAnalysisDBSaver(session_id),
        name="channel_filter_analysis"
    )


class ChannelFilterCalculator(ComputationModule):
    """Computation module that analyzes channels for significance and magnitude criteria."""

    def __init__(self):
        self.slide_length = 0.5  # in seconds
        self.pre_stim_duration = 0.2
        self.post_stim_duration = 0.2

    def compute(self, prepared_data: pd.DataFrame) -> Dict:
        """
        Analyze channels and return structured results.

        Returns:
            Dict containing:
                - good_channels: List of channels passing criteria
                - all_channel_stats: Dict with statistics for ALL channels
                - significant_channels: List of statistically significant channels
        """
        print(prepared_data.head(5).to_string())

        def extract_before_during_after(spike_dict):
            before_for_channels = {}
            during_for_channels = {}
            after_for_channels = {}
            not_during_for_channels = {}

            for channel, spike_times in spike_dict.items():
                before_for_channels[channel] = len(
                    [spike for spike in spike_times if spike < 0]) / self.pre_stim_duration
                during_for_channels[channel] = len(
                    [spike for spike in spike_times if 0 <= spike <= self.slide_length]) / self.slide_length
                after_for_channels[channel] = len(
                    [spike for spike in spike_times if spike > self.slide_length]) / self.post_stim_duration
                not_during_for_channels[channel] = len(
                    [spike for spike in spike_times if spike < 0 or spike > self.slide_length]) / (
                                                           self.post_stim_duration + self.pre_stim_duration)

            return before_for_channels, during_for_channels, after_for_channels, not_during_for_channels

        # Extract spike rate data
        spike_data = prepared_data['Spikes by channel'].apply(extract_before_during_after)
        prepared_data['Spike Rates Before'] = spike_data.apply(lambda x: x[0])
        prepared_data['Spike Rates During'] = spike_data.apply(lambda x: x[1])
        prepared_data['Spike Rates After'] = spike_data.apply(lambda x: x[2])
        prepared_data['Spike Rates Not During'] = spike_data.apply(lambda x: x[3])

        # Aggregate data per channel
        during_stim_spike_rates_per_channel = {}
        not_during_stim_spike_rates_per_channel = {}

        for index, row in prepared_data.iterrows():
            for channel, spike_rate in row['Spike Rates During'].items():
                if channel not in during_stim_spike_rates_per_channel:
                    during_stim_spike_rates_per_channel[channel] = []
                during_stim_spike_rates_per_channel[channel].append(spike_rate)

            for channel, spike_rate in row['Spike Rates Not During'].items():
                if channel not in not_during_stim_spike_rates_per_channel:
                    not_during_stim_spike_rates_per_channel[channel] = []
                not_during_stim_spike_rates_per_channel[channel].append(spike_rate)

        # Calculate statistics for ALL channels
        all_channel_stats = {}
        for channel in during_stim_spike_rates_per_channel.keys():
            if channel in not_during_stim_spike_rates_per_channel:
                during_rates = during_stim_spike_rates_per_channel[channel]
                not_during_rates = not_during_stim_spike_rates_per_channel[channel]

                during_mean = np.mean(during_rates)
                not_during_mean = np.mean(not_during_rates)
                during_std = np.std(during_rates)
                not_during_std = np.std(not_during_rates)

                all_channel_stats[channel] = {
                    'during_mean': during_mean,
                    'not_during_mean': not_during_mean,
                    'during_std': during_std,
                    'not_during_std': not_during_std,
                    'during_rates': during_rates,
                    'not_during_rates': not_during_rates
                }

        # Find statistically significant channels
        significant_channels = []
        for channel, statistics in all_channel_stats.items():
            during_rates = statistics['during_rates']
            not_during_rates = statistics['not_during_rates']

            if len(during_rates) > 1 and len(not_during_rates) > 1:
                t_stat, p_value = statss.ttest_ind(during_rates, not_during_rates)
                if p_value < 0.001:
                    significant_channels.append(channel)

        # Apply magnitude criteria to determine good channels
        good_channels = []
        for channel, stats in all_channel_stats.items():
            during_mean = stats['during_mean']
            not_during_mean = stats['not_during_mean']
            during_std = stats['during_std']
            not_during_std = stats['not_during_std']

            if not_during_mean > 0:
                percentage_increase = ((during_mean - not_during_mean) / not_during_mean) * 100
                percentage_std_diff = (during_std - not_during_std) / not_during_std * 100

                if (percentage_increase >= 50 or percentage_std_diff >= 50) and channel in significant_channels:
                    good_channels.append(channel)

        print(f"All Significant Channels: {significant_channels}")
        print(f"Channels with 20%+ Magnitude Increase: {good_channels}")

        return {
            'good_channels': good_channels,
            'all_channel_stats': all_channel_stats,
            'significant_channels': significant_channels
        }


class ChannelAnalysisDBSaver(OutputHandler):
    """Output handler that saves ALL channel analysis results to the ChannelFiltering table."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.conn = Connection("allen_data_repository")
        self._ensure_table_exists()

    def _ensure_table_exists(self):
        """Create the ChannelFiltering table with firing rate columns and is_good flag."""

        channel_filtering_sql = """
                                CREATE TABLE IF NOT EXISTS ChannelFiltering \
                                ( \
                                    session_id      VARCHAR(10)  NOT NULL, \
                                    channel         VARCHAR(255) NOT NULL, \
                                    during_mean     FLOAT        NOT NULL, \
                                    not_during_mean FLOAT        NOT NULL, \
                                    during_std      FLOAT        NOT NULL, \
                                    not_during_std  FLOAT        NOT NULL, \
                                    is_significant  BOOLEAN      NOT NULL DEFAULT FALSE, \
                                    is_good         BOOLEAN      NOT NULL DEFAULT FALSE, \
                                    PRIMARY KEY (session_id, channel), \
                                    CONSTRAINT ChannelFiltering_ibfk_1 \
                                        FOREIGN KEY (session_id) REFERENCES Sessions (session_id) \
                                            ON DELETE CASCADE
                                ) CHARSET = latin1; \
                                """

        self.conn.execute(channel_filtering_sql)

    def process(self, result: Dict) -> Dict:
        """Save ALL channel results to the database."""
        good_channels = result['good_channels']
        all_channel_stats = result['all_channel_stats']
        significant_channels = result['significant_channels']

        # Clear existing data for this session
        self.conn.execute("DELETE FROM ChannelFiltering WHERE session_id = %s", (self.session_id,))

        # Save ALL channels with their statistics
        for channel, statistics in all_channel_stats.items():
            is_significant = channel in significant_channels
            is_good = channel in good_channels

            insert_sql = """
                         INSERT INTO ChannelFiltering
                         (session_id, channel, during_mean, not_during_mean, during_std, not_during_std, is_significant, \
                          is_good)
                         VALUES (%s, %s, %s, %s, %s, %s, %s, %s) \
                         """

            # Convert numpy types to Python types
            self.conn.execute(insert_sql, (
                self.session_id,
                channel,
                float(statistics['during_mean']),
                float(statistics['not_during_mean']),
                float(statistics['during_std']),
                float(statistics['not_during_std']),
                bool(is_significant),
                bool(is_good)
            ))

        print(
            f"Saved statistics for {len(all_channel_stats)} channels ({len(good_channels)} good channels) for session {self.session_id}")

        return result


def extract_good_channels(session_id: str) -> List[str]:
    """
    Extract good channels by reading from the GoodChannels table.
    Returns list of channel names that are marked as good channels.
    """
    conn = Connection("allen_data_repository")

    query = """
            SELECT channel
            FROM GoodChannels
            WHERE session_id = %s
            ORDER BY channel \
            """

    conn.execute(query, (session_id,))
    results = conn.fetch_all()

    # Extract channel names from tuples
    good_channels = [row[0] for row in results]

    print(f"Found {len(good_channels)} good channels for session {session_id}")
    return good_channels