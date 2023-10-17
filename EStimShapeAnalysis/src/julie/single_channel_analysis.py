import os

import matplotlib
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from clat.intan.channels import Channel

matplotlib.use("Qt5Agg")


def main():
    experiment_data_filename = "1697052348461980_231011_152549_round1.pk1"
    experiment_name = experiment_data_filename.split(".")[0]
    file_path = "/home/r2_allen/git/EStimShape/EStimShapeAnalysis/compiled/julie/%s" % experiment_data_filename
    raw_data = read_pickle(file_path)
    #   plot_channel_histograms(raw_data, channel=Channel.C_013)

    channels = [
                # Channel.C_017,
                Channel.C_002,
                # Channel.C_002,
                # Channel.C_029,
                # Channel.C_007,
                # Channel.C_013,
                # Channel.C_018,
                # Channel.C_024,
                # Channel.C_003,
                # Channel.C_028,
                # Channel.C_012,
                # Channel.C_022,
                # Channel.C_011,
                # Channel.C_020,
                # Channel.C_010,
                # Channel.C_021,
                # Channel.C_006,
                # Channel.C_010,
                # Channel.C_025,
                # Channel.C_026,
                # Channel.C_023,
                # Channel.C_006,
                # Channel.C_025,
                # Channel.C_006
                ]
    for channel in channels:
        print("Working on channel %s" % channel)
        plot_raster_for_monkeys(raw_data, channel=channel,
                                experiment_name=experiment_name)


def read_pickle(file_path):
    unpacked_pickle = pd.read_pickle(file_path).reset_index(drop=True)
    return unpacked_pickle


def plot_raster_for_monkeys(raw_data, channel, experiment_name=None):
    channel_data = extract_target_channel_data(channel, raw_data)
    unique_monkey_groups = channel_data['MonkeyGroup'].dropna().unique().tolist()
    N = len(channel_data)

    max_rows = 0
    for group_name in unique_monkey_groups:
        group_data = channel_data[channel_data['MonkeyGroup'] == group_name]
        unique_monkeys = group_data['MonkeyName'].dropna().unique().tolist()
        max_rows = max(max_rows, len(unique_monkeys))

    fig = plt.figure(figsize=(15 * len(unique_monkey_groups), 45 * max_rows))

    for col_idx, group_name in enumerate(unique_monkey_groups):
        group_data = channel_data[channel_data['MonkeyGroup'] == group_name]
        unique_monkeys = group_data['MonkeyName'].dropna().unique().tolist()

        for row_idx, monkey_name in enumerate(unique_monkeys):
            monkey_data = group_data[group_data['MonkeyName'] == monkey_name]

            ax = fig.add_subplot(max_rows, len(unique_monkey_groups), row_idx * len(unique_monkey_groups) + col_idx + 1)

            filtered_spike_times_list = []
            for idx, row in monkey_data.iterrows():
                spike_times = row[f'SpikeTimes_{channel.value}']
                epoch_start, epoch_stop = row['EpochStartStop']

                # Filter spikes based on EpochStartStop and subtract the epoch start time
                filtered_spike_times = [spike - epoch_start for spike in spike_times if
                                        epoch_start <= spike <= epoch_stop]
                filtered_spike_times_list.append(filtered_spike_times)

            ax.eventplot(filtered_spike_times_list, color='black', linewidths=0.5)
            ax.set_xlim(0, 2.0)
            ax.set_yticks([len(filtered_spike_times_list)])
            # Place the title text to the right of the subplot
            ax.text(1.05, 0.5, f"{monkey_name}", transform=ax.transAxes, ha='left', va='center', fontsize=14)

        fig.text(0.5 / len(unique_monkey_groups) + col_idx / len(unique_monkey_groups), 0.95, f'{group_name}',
                 ha='center', va='center')

    # fig.text(0.5, 0.01, 'Monkey Groups', ha='center', va='center')
    fig.text(0.5, 0.05, 'Time (s)', ha='center', va='center', rotation='horizontal')
    fig.text(0.99, 0.95, f'N: {N}', ha='right', va='bottom')
    fig.suptitle(f'Raster Plots for Individual Monkeys: Channel: {channel.value}')

    plt.subplots_adjust(hspace=1.0, wspace=1.0)
    plt.show()

    ## SAVE PLOTS
    base_save_dir = "/home/r2_allen/git/EStimShape/EStimShapeAnalysis/plots/julie"
    if experiment_name is not None:
        save_dir = os.path.join(base_save_dir, experiment_name)
        os.makedirs(save_dir, exist_ok=True)

        # Save individual plot
        individual_save_path_png = os.path.join(save_dir, f"{channel.name}_raster.png")
        individual_save_path_svg = os.path.join(save_dir, f"{channel.name}_raster.svg")
        # fig.savefig(individual_save_path_png)
        fig.savefig(individual_save_path_svg)

    return fig


def plot_channel_histograms(data, channel):
    ## NOISE FILTERING
    # data = remove_noisy_data(data, 10, 100)

    ## CHANNEL SPECIFIC ANALYSIS
    num_bins = 10
    channel_data = extract_target_channel_data(channel, data)
    channel_data = calculate_spikerates_per_bin(channel_data, channel, num_bins)

    ## PLOTTING
    individual_plot = plot_histograms_for_individual_monkeys(channel_data, channel)
    group_plot = plot_average_among_groups(channel_data, channel)

    ## SAVE PLOTS
    # base_save_dir = "/home/r2_allen/git/EStimShape/EStimShapeAnalysis/plots/julie"
    # experiment_name = path_to_data_pickle_file.split("/")[-1].split(".")[0]
    # save_dir = os.path.join(base_save_dir, experiment_name)
    # os.makedirs(save_dir, exist_ok=True)
    #
    # Save individual plot
    # individual_save_path = os.path.join(save_dir, f"{channel.name}_individual.png")
    # individual_plot.savefig(individual_save_path)
    #
    # Save group plot
    # group_save_path = os.path.join(save_dir, f"{channel.name}_group.png")
    # group_plot.savefig(group_save_path)

    plt.show()


def plot_histograms_for_individual_monkeys(channel_data, channel):
    num_groups = channel_data['MonkeyGroup'].nunique()
    unique_monkey_groups = channel_data['MonkeyGroup'].dropna().unique().tolist()
    N = len(channel_data)

    # Create a new figure
    fig = plt.figure(figsize=(15, 10))

    row_idx = 0
    global_max_spike_rate = channel_data['BinnedSpikeRates'].apply(lambda x: max(x) if x is not None else 0).max()
    ymax = 50
    num_bins = len(channel_data['BinnedSpikeRates'].iloc[0])
    x_proportion = np.linspace(0, 1, num_bins)

    legend_handles_labels = None
    for group_name in unique_monkey_groups:
        group_data = channel_data[channel_data['MonkeyGroup'] == group_name]
        unique_monkeys = group_data['MonkeyName'].dropna().unique().tolist()

        for col_idx, monkey_name in enumerate(unique_monkeys):
            monkey_data = group_data[group_data['MonkeyName'] == monkey_name]

            ax = fig.add_subplot(num_groups, len(unique_monkeys), row_idx * len(unique_monkeys) + col_idx + 1)

            err_bar = plot_histogram_for_single_monkey(ax, monkey_data, monkey_name, x_proportion, ymax)

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
    # Add total number of traces under the legend
    fig.text(0.99, 0.95, f'N: {N}', ha='right', va='bottom')
    # Add a super title
    fig.suptitle(f'Individual Monkey Spike Rates: Channel: {channel.value}')

    # Add a single legend at the top-right corner
    fig.legend(*legend_handles_labels, loc='upper right')

    plt.subplots_adjust(hspace=0.5, wspace=1.0)

    fig.canvas.mpl_connect('button_press_event', on_click_histo)
    return fig


def plot_histogram_for_single_monkey(ax, monkey_data, monkey_name, x_proportion, ymax):
    spike_rate_arrays = np.vstack(monkey_data['BinnedSpikeRates'])
    num_traces = spike_rate_arrays.shape[0]  # Number of rows in spike_rate_arrays is the number of traces
    mean_spike_rates = np.mean(spike_rate_arrays, axis=0)
    std_spike_rates = np.std(spike_rate_arrays, axis=0)
    for spike_rates in spike_rate_arrays:
        ax.plot(x_proportion, spike_rates, color='black', alpha=0.3, linewidth=0.75)
    err_bar = ax.errorbar(x_proportion, mean_spike_rates, yerr=std_spike_rates, color='orange', alpha=0.75,
                          label='Mean', elinewidth=0.8)
    ax.set_ylim(0, ymax)
    ax.set_title(f"{monkey_name}")
    # Add the number of traces to the top middle of each subplot
    ax.text(0.5, 0.85, f'n={num_traces}', transform=ax.transAxes, ha='center', va='bottom')
    return err_bar


def on_click_histo(event):
    ax = event.inaxes
    if ax is not None:
        fig, new_ax = plt.subplots()
        all_xdata = [line.get_xdata() for line in ax.lines[:-1]]  # Exclude the last line which is mean
        all_ydata = [line.get_ydata() for line in ax.lines[:-1]]  # Exclude the last line which is mean

        for xdata, ydata in zip(all_xdata, all_ydata):
            new_ax.plot(xdata, ydata, color='gray', alpha=0.3)

        mean_xdata = ax.lines[-1].get_xdata()
        mean_ydata = ax.lines[-1].get_ydata()
        # err_lines = ax.collections[0].get_paths()  # Assuming the error bars are the first collection

        # upper_err = err_lines[1].vertices[:, 1]  # The second path in the collection is the upper error bar
        # lower_err = err_lines[0].vertices[:, 1]  # The first path in the collection is the lower error bar
        # std_err = (upper_err - lower_err) / 2

        # print("Shapes:", std_err.shape, mean_ydata.shape)  # Debugging line

        new_ax.errorbar(mean_xdata, mean_ydata, color='orange', alpha=0.75, label='Mean')

        new_ax.set_title(ax.get_title())
        new_ax.set_ylim(ax.get_ylim())
        plt.show()


def plot_average_among_groups(channel_data, channel):
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
    ax.set_title(f'Average Spike Rates Among Groups: Channel: {channel.value}')
    ax.legend()

    return fig


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


def extract_target_channel_data(channel: Channel, data):
    # Get SpikeTimes for channel
    channel_data = data.copy()
    channel_data[f'SpikeTimes_{channel.value}'] = data['SpikeTimes'].apply(lambda x: x[next(filter(lambda key: key.value == channel.value, x.keys()), None)])


    return channel_data


def calculate_spikerates_per_bin(channel_data, channel, num_bins):
    # Calculate binned spike rates
    channel_data['BinnedSpikeRates'] = channel_data.apply(
        lambda row: calculate_binned_spike_rate(row[f'SpikeTimes_{channel.value}'], row['EpochStartStop'], num_bins),
        axis=1
    )
    return channel_data


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


if __name__ == '__main__':
    main()
