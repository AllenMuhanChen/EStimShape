from julie.single_channel_analysis import extract_target_channel_data
import os
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec


import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

import matplotlib.pyplot as plt

import matplotlib.pyplot as plt

import matplotlib.pyplot as plt

import matplotlib.pyplot as plt
from matplotlib import gridspec


def plot_raster_for_monkeys(raw_data, channel, experiment_name=None):
    channel_data = extract_target_channel_data(channel, raw_data)
    unique_monkey_groups = channel_data['MonkeyGroup'].dropna().unique().tolist()

    max_num_trials = 0

    for group_name in unique_monkey_groups:
        group_data = channel_data[channel_data['MonkeyGroup'] == group_name]
        unique_monkeys = group_data['MonkeyName'].dropna().unique().tolist()

        group_trials = 0
        for monkey_name in unique_monkeys:
            monkey_data = group_data[group_data['MonkeyName'] == monkey_name]
            num_trials = len(monkey_data)
            group_trials += num_trials

        max_num_trials = max(max_num_trials, group_trials)

    total_grid_rows = max_num_trials

    fig = plt.figure(figsize=(20, total_grid_rows))
    spec = gridspec.GridSpec(total_grid_rows, len(unique_monkey_groups), hspace=0.4)

    for col_idx, group_name in enumerate(unique_monkey_groups):
        current_row = 0  # Reset row for each new group
        group_data = channel_data[channel_data['MonkeyGroup'] == group_name]
        unique_monkeys = group_data['MonkeyName'].dropna().unique().tolist()

        for monkey_name in unique_monkeys:
            monkey_data = group_data[group_data['MonkeyName'] == monkey_name]
            num_trials = len(monkey_data)

            ax = fig.add_subplot(spec[current_row:current_row + num_trials, col_idx])

            filtered_spike_times_list = []
            for idx, row in monkey_data.iterrows():
                spike_times = row[f'SpikeTimes_{channel.value}']
                epoch_start, epoch_stop = row['EpochStartStop']
                filtered_spike_times = [spike - epoch_start for spike in spike_times if
                                        epoch_start <= spike <= epoch_stop]
                filtered_spike_times_list.append(filtered_spike_times)

            ax.eventplot(filtered_spike_times_list, color='black', linewidths=0.25)
            ax.set_xlim(0, 1.0)
            ax.set_ylim(0, num_trials)

            # Add labels for monkey group and monkey name
            ax.text(0.5, 1.05, f'Monkey Group: {group_name}', transform=ax.transAxes, ha='center', va='center',
                    fontsize=12)
            ax.text(0.5, -0.2, f'Monkey: {monkey_name}', transform=ax.transAxes, ha='center', va='center', fontsize=10)

            current_row += num_trials  # Move down the number of trials for this monkey

    # Add a legend and N count
    plt.figtext(0.95, 0.15, 'Spike Times', color='black', fontsize=10)
    plt.figtext(0.95, 0.12, f'N: {len(channel_data)}', color='black', fontsize=10)

    plt.subplots_adjust(hspace=2)
    plt.show()


# Replace 'extract_target_channel_data' and 'your_channel' with your actual functions and data
# Uncomment the below line to run the function
# plot_raster_for_monkeys(raw_data, your_channel)

def get_figure_dimensions(channel_data, unique_monkey_groups):
    max_rows = 0
    for group_name in unique_monkey_groups:
        group_data = channel_data[channel_data['MonkeyGroup'] == group_name]
        unique_monkeys = group_data['MonkeyName'].dropna().unique().tolist()
        max_rows = max(max_rows, len(unique_monkeys))
    return max_rows, (15 * len(unique_monkey_groups), 35 * max_rows)


def plot_single_monkey_raster(fig, spec, col_idx, row_idx, group_data, monkey_name, channel, unique_monkey_groups):
    monkey_data = group_data[group_data['MonkeyName'] == monkey_name]
    num_trials = len(monkey_data)

    ax = fig.add_subplot(spec.new_subplotspec((row_idx, col_idx), rowspan=num_trials))

    filtered_spike_times_list = []
    for idx, row in monkey_data.iterrows():
        spike_times = row[f'SpikeTimes_{channel.value}']
        epoch_start, epoch_stop = row['EpochStartStop']

        # Filter spikes based on EpochStartStop and subtract the epoch start time
        filtered_spike_times = [spike - epoch_start for spike in spike_times if epoch_start <= spike <= epoch_stop]
        filtered_spike_times_list.append(filtered_spike_times)

    ax.eventplot(filtered_spike_times_list, color='black', linewidths=0.25)
    ax.set_xlim(0, 1.0)
    ax.set_ylim(0, len(filtered_spike_times_list))  # Setting y-axis limits based on the number of trials

    return ax, filtered_spike_times_list

def set_subplot_title(ax, filtered_spike_times_list, monkey_name):
    ax.set_yticks([len(filtered_spike_times_list)])
    ax.text(1.05, 0.5, f"{monkey_name}", transform=ax.transAxes, ha='left', va='center', fontsize=14)


def set_group_title(fig, col_idx, group_name, unique_monkey_groups):
    fig.text(0.5 / len(unique_monkey_groups) + col_idx / len(unique_monkey_groups), 0.95, f'{group_name}',
             ha='center', va='center')


def set_figure_labels(fig, N, channel):
    fig.text(0.5, 0.05, 'Time (s)', ha='center', va='center', rotation='horizontal')
    fig.text(0.99, 0.95, f'N: {N}', ha='right', va='bottom')
    fig.suptitle(f'Raster Plots for Individual Monkeys: Channel: {channel.value}')
    plt.subplots_adjust(hspace=1.0, wspace=1.0)


def save_plot(fig, channel, experiment_name):
    if experiment_name is not None:
        base_save_dir = "/home/r2_allen/git/EStimShape/EStimShapeAnalysis/plots/julie"
        save_dir = os.path.join(base_save_dir, experiment_name)
        os.makedirs(save_dir, exist_ok=True)
        individual_save_path = os.path.join(save_dir, f"{channel.name}_raster.png")
        fig.savefig(individual_save_path)
