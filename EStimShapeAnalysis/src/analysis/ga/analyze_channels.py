import numpy as np
import pandas as pd
from scipy import stats
from src.analysis import Analysis
from src.analysis.ga.optimize_ga.analyze_magnitudes import AnalyzeMagnitudesAnalysis
from src.repository.export_to_repository import read_session_id_from_db_name
from src.repository.import_from_repository import import_from_repository
from src.startup import context


def main():
    analysis = FilterChannelsAnalysis()
    session_id, _ = read_session_id_from_db_name(context.ga_database)
    session_id = "250425_0"
    channel = None
    analysis.run(session_id, "raw", channel, compiled_data=None)


class FilterChannelsAnalysis(Analysis):
    slide_length = 0.5  # in seconds
    pre_stim_duration = 0.2
    post_stim_duration = 0.2

    def analyze(self, channel, compiled_data: pd.DataFrame = None):
        if compiled_data is None:
            compiled_data = import_from_repository(
                self.session_id,
                "ga",
                "GAStimInfo",
                self.response_table
            )

        print(compiled_data.head(5).to_string())

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

        spike_data = compiled_data['Spikes by channel'].apply(extract_before_during_after)

        # Extract the results
        compiled_data['Spike Rates Before'] = spike_data.apply(lambda x: x[0])
        compiled_data['Spike Rates During'] = spike_data.apply(lambda x: x[1])
        compiled_data['Spike Rates After'] = spike_data.apply(lambda x: x[2])
        compiled_data['Spike Rates Not During'] = spike_data.apply(lambda x: x[3])

        pre_stim_spike_rates_per_channel = {}
        during_stim_spike_rates_per_channel = {}
        post_stim_spike_rates_per_channel = {}
        not_during_stim_spike_rates_per_channel = {}

        for index, row in compiled_data.iterrows():
            for channel, spike_rates in row['Spike Rates Before'].items():
                if channel not in pre_stim_spike_rates_per_channel:
                    pre_stim_spike_rates_per_channel[channel] = []
                pre_stim_spike_rates_per_channel[channel].extend(
                    spike_rates if type(spike_rates) is list else [spike_rates])

            for channel, spike_rates in row['Spike Rates During'].items():
                if channel not in during_stim_spike_rates_per_channel:
                    during_stim_spike_rates_per_channel[channel] = []
                during_stim_spike_rates_per_channel[channel].extend(
                    spike_rates if type(spike_rates) is list else [spike_rates])

            for channel, spike_rates in row['Spike Rates After'].items():
                if channel not in post_stim_spike_rates_per_channel:
                    post_stim_spike_rates_per_channel[channel] = []
                post_stim_spike_rates_per_channel[channel].extend(
                    spike_rates if type(spike_rates) is list else [spike_rates])

            for channel, spike_rates in row['Spike Rates Not During'].items():
                if channel not in not_during_stim_spike_rates_per_channel:
                    not_during_stim_spike_rates_per_channel[channel] = []
                not_during_stim_spike_rates_per_channel[channel].extend(
                    spike_rates if type(spike_rates) is list else [spike_rates])

        # Calculate averages
        average_during_stim_spike_rates_per_channel = {}
        for channel, spike_rates in during_stim_spike_rates_per_channel.items():
            average_during_stim_spike_rates_per_channel[channel] = np.mean(spike_rates)

        average_not_during_stim_spike_rates_per_channel = {}
        for channel, spike_rates in not_during_stim_spike_rates_per_channel.items():
            average_not_during_stim_spike_rates_per_channel[channel] = np.mean(spike_rates)

        # Calculate t-test
        significant_channels = []

        for channel in during_stim_spike_rates_per_channel.keys():
            if channel in not_during_stim_spike_rates_per_channel:
                during_rates = during_stim_spike_rates_per_channel[channel]
                not_during_rates = not_during_stim_spike_rates_per_channel[channel]

                # Check if we have enough data for t-test
                if len(during_rates) > 1 and len(not_during_rates) > 1:
                    # Perform independent samples t-test
                    t_stat, p_value = stats.ttest_ind(during_rates, not_during_rates)

                    # Check for significance (p < 0.001)
                    if p_value < 0.001:
                        significant_channels.append(channel)

        # Criteria for Magnitude Difference
        magnitude_channels = []
        for channel in during_stim_spike_rates_per_channel.keys():
            if channel in not_during_stim_spike_rates_per_channel:
                during_mean = average_during_stim_spike_rates_per_channel[channel]
                not_during_mean = average_not_during_stim_spike_rates_per_channel[channel]

                # Calculate percentage increase (avoid division by zero)
                if not_during_mean > 0:
                    percentage_increase = ((during_mean - not_during_mean) / not_during_mean) * 100

                    # Filter channels with 20% or more increase
                    if percentage_increase >= 20:
                        magnitude_channels.append(channel)
                elif during_mean > 0 and not_during_mean == 0:
                    magnitude_channels.append(channel)

        print("All Significant Channels: " + str(significant_channels))
        print("Channels with 20%+ Magnitude Increase: " + str(magnitude_channels))

        return magnitude_channels

    def compile(self):
        pass

    def compile_and_export(self):
        pass


if __name__ == "__main__":
    main()