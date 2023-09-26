import os

import matplotlib
import pandas as pd
from matplotlib import pyplot as plt

matplotlib.use("Qt5Agg")


def main():
    file_path = "/run/user/1003/gvfs/smb-share:server=connorhome.local,share=connorhome/Julie/IntanData/Cortana/2023-09-21/230921_round5/compiled.pk1"
    experiment_name = os.path.basename(os.path.dirname(file_path))
    raw_data = pd.read_pickle(file_path).reset_index(drop=True)
    for unit, data in raw_data['SpikeTimes'][0].items():
        plot_raster_for_monkeys(raw_data, unit, experiment_name=experiment_name)
    plt.show()


def extract_target_unit_data(unit, data):
    # Get SpikeTimes for channel
    unit_data = data.copy()
    unit_data[f'SpikeTimes_{unit}'] = data['SpikeTimes'].apply(lambda x: x[unit])
    return unit_data


def plot_raster_for_monkeys(raw_data, unit, experiment_name=None):
    unit_data = extract_target_unit_data(unit, raw_data)
    unique_monkey_groups = unit_data['MonkeyGroup'].dropna().unique().tolist()
    N = len(unit_data)

    max_rows = 0
    for group_name in unique_monkey_groups:
        group_data = unit_data[unit_data['MonkeyGroup'] == group_name]
        unique_monkeys = group_data['MonkeyName'].dropna().unique().tolist()
        max_rows = max(max_rows, len(unique_monkeys))

    fig = plt.figure(figsize=(15 * len(unique_monkey_groups), 45 * max_rows))

    for col_idx, group_name in enumerate(unique_monkey_groups):
        group_data = unit_data[unit_data['MonkeyGroup'] == group_name]
        unique_monkeys = group_data['MonkeyName'].dropna().unique().tolist()

        for row_idx, monkey_name in enumerate(unique_monkeys):
            monkey_data = group_data[group_data['MonkeyName'] == monkey_name]

            ax = fig.add_subplot(max_rows, len(unique_monkey_groups), row_idx * len(unique_monkey_groups) + col_idx + 1)

            filtered_spike_times_list = []
            for idx, row in monkey_data.iterrows():
                spike_times = row[f'SpikeTimes_{unit}']
                epoch_start, epoch_stop = row['EpochStartStop']

                # Filter spikes based on EpochStartStop and subtract the epoch start time
                filtered_spike_times = [spike - epoch_start for spike in spike_times if
                                        epoch_start <= spike <= epoch_stop]
                filtered_spike_times_list.append(filtered_spike_times)

            ax.eventplot(filtered_spike_times_list, color='black', linewidths=0.5)
            ax.set_xlim(0, 1.0)
            ax.set_yticks([len(filtered_spike_times_list)])
            # Place the title text to the right of the subplot
            ax.text(1.05, 0.5, f"{monkey_name}", transform=ax.transAxes, ha='left', va='center', fontsize=14)

        fig.text(0.5 / len(unique_monkey_groups) + col_idx / len(unique_monkey_groups), 0.95, f'{group_name}',
                 ha='center', va='center')

    # fig.text(0.5, 0.01, 'Monkey Groups', ha='center', va='center')
    fig.text(0.5, 0.05, 'Time (s)', ha='center', va='center', rotation='horizontal')
    fig.text(0.99, 0.95, f'N: {N}', ha='right', va='bottom')
    fig.suptitle(f'Raster Plots for Individual Monkeys: Channel: {unit}')

    plt.subplots_adjust(hspace=1.0, wspace=1.0)

    ## SAVE PLOTS
    base_save_dir = "/home/r2_allen/git/EStimShape/EStimShapeAnalysis/plots/julie"
    if experiment_name is not None:
        save_dir = os.path.join(base_save_dir, experiment_name)
        os.makedirs(save_dir, exist_ok=True)

        # Save individual plot
        individual_save_path = os.path.join(save_dir, f"{unit}_raster.png")
        fig.savefig(individual_save_path)

    return fig


if __name__ == '__main__':
    main()
