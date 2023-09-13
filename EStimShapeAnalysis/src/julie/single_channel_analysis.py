import jsonpickle
import matplotlib
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
matplotlib.use("Qt5Agg")

from intan.channels import Channel


def main():
    plot_channel("/home/r2_allen/git/EStimShape/EStimShapeAnalysis/compiled/julie/2023-09-13_14-00-00_to_16-00-00.pk1",
                 channel=Channel.C_010)


def plot_channel(path_to_data_pickle_file, channel):
    data = pd.read_pickle(path_to_data_pickle_file)
    ## CHANNEL SPECIFIC ANALYSIS
    num_bins = 10
    channel_data = extract_target_channel_data(channel, data)
    channel_data = calculate_spikerates_per_bin(channel_data, channel, num_bins)

    ## PLOTTING
    plot_individual_monkeys(channel_data)
    plot_average_among_groups(channel_data)

    plt.show()


def plot_individual_monkeys(channel_data):
    num_groups = channel_data['MonkeyGroup'].nunique()
    unique_monkey_groups = channel_data['MonkeyGroup'].dropna().unique().tolist()

    # Create a new figure
    fig = plt.figure(figsize=(15, 10))

    row_idx = 0
    global_max_spike_rate = channel_data['BinnedSpikeRates'].apply(lambda x: max(x) if x is not None else 0).max()
    num_bins = len(channel_data['BinnedSpikeRates'].iloc[0])
    x_proportion = np.linspace(0, 1, num_bins)

    legend_handles_labels = None
    for group_name in unique_monkey_groups:
        group_data = channel_data[channel_data['MonkeyGroup'] == group_name]
        unique_monkeys = group_data['MonkeyName'].dropna().unique().tolist()

        for col_idx, monkey_name in enumerate(unique_monkeys):
            monkey_data = group_data[group_data['MonkeyName'] == monkey_name]

            ax = fig.add_subplot(num_groups, len(unique_monkeys), row_idx * len(unique_monkeys) + col_idx + 1)

            spike_rate_arrays = np.vstack(monkey_data['BinnedSpikeRates'])
            mean_spike_rates = np.mean(spike_rate_arrays, axis=0)
            std_spike_rates = np.std(spike_rate_arrays, axis=0)

            for spike_rates in spike_rate_arrays:
                ax.plot(x_proportion, spike_rates, color='black', alpha=1.0)

            err_bar = ax.errorbar(x_proportion, mean_spike_rates, yerr=std_spike_rates, color='blue', alpha=0.75,
                                  label='Mean')

            ax.set_ylim(0, global_max_spike_rate)
            ax.set_title(f"{monkey_name}")

            # Collect legend handles and labels from one of the axes
            if legend_handles_labels is None:
                legend_handles_labels = ([err_bar], ["Mean"])
                # Add a label for the MonkeyGroup on the left side

                # Correctly position the label for the MonkeyGroup on the left side
        subplot_height = 1 / num_groups
        vertical_position = 1 - (row_idx * subplot_height + subplot_height / 2)
        fig.text(0.08, vertical_position, f'{group_name}', ha='center', va='center',
                 rotation='vertical')
        row_idx += 1

    # Add a single x-axis label at the bottom
    fig.text(0.5, 0.04, 'Proportion of Total Time', ha='center', va='center')
    # Add a single y-axis label on the left
    fig.text(0.04, 0.5, 'Spike Rate', ha='center', va='center', rotation='vertical')

    # Add a single legend at the top-right corner
    fig.legend(*legend_handles_labels, loc='upper right')

    plt.subplots_adjust(hspace=0.5, wspace=1.0)
    # plt.show()


def plot_average_among_groups(channel_data):
    # Group the data by MonkeyGroup
    grouped_data = channel_data.groupby('MonkeyGroup')['BinnedSpikeRates'].apply(
        lambda x: np.vstack(x)
    ).reset_index()

    # Find the number of bins (assuming you already have this from your previous calculations)
    num_bins = len(channel_data['BinnedSpikeRates'].iloc[0])

    # Create a figure and axis for the plot
    fig, ax = plt.subplots(figsize=(10, 6))

    # Loop through each unique MonkeyGroup to plot the average and error bars
    for index, row in grouped_data.iterrows():
        group_name = row['MonkeyGroup']
        spike_rates_matrix = row['BinnedSpikeRates']

        # Calculate the mean and standard error for each bin
        mean_spike_rates = np.mean(spike_rates_matrix, axis=0)
        std_err_spike_rates = np.std(spike_rates_matrix, axis=0) / np.sqrt(spike_rates_matrix.shape[0])

        # Calculate the proportion of total time for each bin
        x_proportion = np.linspace(0, 1, num_bins)

        # Plot the mean trace with error bars
        ax.errorbar(x_proportion, mean_spike_rates, yerr=std_err_spike_rates, label=f'Group: {group_name}', alpha=0.75)

    # Add labels, title, and legend
    ax.set_xlabel('Proportion of Total Time')
    ax.set_ylabel('Average Spike Rate')
    ax.set_title('Average Spike Rates Among Groups')
    ax.legend()

    # Show the plot



def calculate_binned_spike_rate(spikes, epoch, num_bins):
    if spikes is None or epoch is None:
        return [0.0] * num_bins

    start_time, end_time = epoch
    total_duration = end_time - start_time
    bin_duration = total_duration / num_bins
    binned_spike_rates = []

    for i in range(num_bins):
        bin_start = start_time + i * bin_duration
        bin_end = bin_start + bin_duration
        spike_rate = calculate_spike_rate(spikes, (bin_start, bin_end))
        binned_spike_rates.append(spike_rate)

    return np.array(binned_spike_rates)


def calculate_spike_rate(spikes: list, time_range: tuple) -> float:
    """
    Calculate the spike rate between two timestamps.

    Parameters:
        spikes (list): List of spike timestamps.
        time_range (tuple): Tuple containing start_time and end_time.

    Returns:
        float: Spike rate.
    """
    if not spikes or time_range[0] >= time_range[1]:
        return 0.0

    start_time, end_time = time_range
    spikes_in_range = [spike for spike in spikes if start_time <= spike < end_time]
    spike_count = len(spikes_in_range)
    duration = end_time - start_time

    if duration == 0:
        return 0.0

    return spike_count / duration


def extract_target_channel_data(channel, data):
    # Get SpikeTimes for channel
    channel_data = data.copy()
    channel_data[f'SpikeTimes_{channel.value}'] = data['SpikeTimes'].apply(lambda x: x[channel])
    return channel_data


def calculate_spikerates_per_bin(channel_data, channel, num_bins):
    # Calculate binned spike rates
    channel_data['BinnedSpikeRates'] = channel_data.apply(
        lambda row: calculate_binned_spike_rate(row[f'SpikeTimes_{channel.value}'], row['EpochStartStop'], num_bins),
        axis=1
    )
    return channel_data


if __name__ == '__main__':
    main()
