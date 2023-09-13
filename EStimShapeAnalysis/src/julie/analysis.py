import jsonpickle
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

from intan.channels import Channel


def main():
    pickle_to_read = "/home/r2_allen/git/EStimShape/EStimShapeAnalysis/compiled/julie/2023-09-12_16-00-00_to_23-59-59.pk1"
    data = pd.read_pickle(pickle_to_read)

    ## CHANNEL SPECIFIC ANALYSIS
    channel = Channel.C_021
    num_bins = 10

    channel_data = extract_target_channel_data(channel, data)

    channel_data = calculate_spikerates_per_bin(channel_data, channel, num_bins)

    print(channel_data['MonkeyName'])
    print(channel_data['MonkeyGroup'])

    ## PLOTTING
    plot_individual_monkeys(channel_data)
    plot_average_among_groups(channel_data)


def plot_individual_monkeys(channel_data):
    # Sample DataFrame 'channel_data' with 'MonkeyGroup', 'MonkeyName', and 'BinnedSpikeRates'

    # Count the number of unique MonkeyGroups and MonkeyNames
    num_groups = channel_data['MonkeyGroup'].nunique()
    max_monkeys_per_group = channel_data.groupby('MonkeyGroup')['MonkeyName'].nunique().max()

    # Create a figure with subplots
    fig, axes = plt.subplots(nrows=num_groups, ncols=max_monkeys_per_group, figsize=(15, 10))

    # Ensure axes is a 2D array for consistent indexing
    if num_groups == 1:
        axes = np.expand_dims(axes, axis=0)
    if max_monkeys_per_group == 1:
        axes = np.expand_dims(axes, axis=1)

    # Initialize subplot counter for each group
    subplot_counter = {}

    # Find the global maximum spike rate across all groups and monkeys
    global_max_spike_rate = channel_data['BinnedSpikeRates'].apply(lambda x: max(x) if x is not None else 0).max()

    # Find the number of bins (assuming you already have this from your previous calculations)
    num_bins = len(channel_data['BinnedSpikeRates'].iloc[0])

    # Create an array representing the proportion of the total time for each bin
    x_proportion = np.linspace(0, 1, num_bins)

    # Loop through each unique MonkeyGroup and MonkeyName
    for (group_name, monkey_name), group_data in channel_data.groupby(['MonkeyGroup', 'MonkeyName']):
        # Get the appropriate row index for the MonkeyGroup
        row_idx = channel_data['MonkeyGroup'].dropna().unique().tolist().index(group_name)

        # Initialize or update subplot counter for this group
        subplot_counter[group_name] = subplot_counter.get(group_name, 0)
        col_idx = subplot_counter[group_name]
        subplot_counter[group_name] += 1

        # Get the axis for this subplot
        ax = axes[row_idx, col_idx] if isinstance(axes, np.ndarray) else axes

        # Calculate mean and standard error for binned spike rates
        spike_rate_arrays = np.vstack(group_data['BinnedSpikeRates'])
        mean_spike_rates = np.mean(spike_rate_arrays, axis=0)
        std_spike_rates = np.std(spike_rate_arrays, axis=0)

        # Plot individual traces
        for spike_rates in spike_rate_arrays:
            ax.plot(x_proportion, spike_rates, color='gray', alpha=0.3)

            # Plot mean trace with error bars
            # Plot mean trace with error bars
        ax.errorbar(x_proportion, mean_spike_rates, yerr=std_spike_rates, color='blue', label='Mean')

        # Add title and labels
        ax.set_title(f'Monkey: {monkey_name}')
        ax.set_xlabel('Proportion of Total Time')
        ax.set_ylabel('Spike Rate')
        ax.legend()

        # Set the same y-range for all subplots
        ax.set_ylim(0, global_max_spike_rate)

    # Add a title for each MonkeyGroup
    for i, group_name in enumerate(channel_data['MonkeyGroup'].dropna().unique()):
        axes[i, 0].set_ylabel(f'MonkeyGroup: {group_name}', rotation=0, labelpad=60, verticalalignment='center',
                              fontsize=12)

    # # Remove empty subplots
    # for i in range(num_groups):
    #     for j in range(subplot_counter.get(group_name, 0), max_monkeys_per_group):
    #         fig.delaxes(axes[i, j])

    plt.tight_layout()
    plt.show()


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
        ax.errorbar(x_proportion, mean_spike_rates, yerr=std_err_spike_rates, label=f'Group: {group_name}')

    # Add labels, title, and legend
    ax.set_xlabel('Proportion of Total Time')
    ax.set_ylabel('Average Spike Rate')
    ax.set_title('Average Spike Rates Among Groups')
    ax.legend()

    # Show the plot
    plt.show()


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
