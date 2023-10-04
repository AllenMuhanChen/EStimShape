import os

import matplotlib
import pandas as pd
from matplotlib import pyplot as plt

from compile.task.task_field import TaskFieldList, TaskField
from intan.rhd import load_intan_rhd_format
from julie.compile.sorted_units_compilation import read_pickle, SortedSpikeTStampField

matplotlib.use("Qt5Agg")


def main():
    date = "2023-10-03"
    round = "231003_round3"
    sorted_spikes_filename = "sorted_spikes_include_smaller.pkl"

    cortana_path = "/run/user/1003/gvfs/smb-share:server=connorhome.local,share=connorhome/Julie/IntanData/Cortana"
    round_path = os.path.join(cortana_path, date, round)
    compiled_trials_filepath = os.path.join(round_path, "compiled.pk1")
    experiment_name = os.path.basename(os.path.dirname(compiled_trials_filepath))
    raw_trial_data = pd.read_pickle(compiled_trials_filepath).reset_index(drop=True)

    # TODO: specify which sorting pickle to use and which units to plot, then add them to dataframe
    rhd_file_path = os.path.join(round_path, "info.rhd")
    sorted_spikes_filepath = os.path.join(cortana_path, date, round, sorted_spikes_filename)
    sorted_spikes = read_pickle(sorted_spikes_filepath)
    sample_rate = load_intan_rhd_format.read_data(rhd_file_path)["frequency_parameters"]['amplifier_sample_rate']
    sorted_data = calculate_spike_timestamps(raw_trial_data, sorted_spikes, sample_rate)

    for unit, data in raw_trial_data['SpikeTimes'][0].items():
        plot_raster_for_monkeys(sorted_data, unit, experiment_name=experiment_name)
    # plt.show()


def calculate_spike_timestamps(df: pd.DataFrame, spike_indices_by_unit_by_channel: dict, sample_rate: int):
    """
    Calculates spike timestamps for each row in the DataFrame.

    Parameters:
    - df: Pandas DataFrame with a column 'EpochStartStop' containing tuples of (epoch_start, epoch_stop)
    - spike_indices_by_unit_by_channel: Dictionary of channels to a dict of Units to spike indices
    - sample_rate: The sample rate for the spike indices

    Returns:
    - new_df: A new DataFrame with an additional column containing the calculated spike timestamps
    """

    def single_row_calculation(epoch_start_stop):
        epoch_start, epoch_stop = epoch_start_stop
        spikes_tstamps_by_unit = {}

        for channel, spike_indices_by_unit in reversed(spike_indices_by_unit_by_channel.items()):
            for unit_name, spike_indices in spike_indices_by_unit.items():
                new_unit_name = f"{channel}_{unit_name}"

                # Filter and convert spike indices to timestamps
                spike_times = [spike_index / sample_rate for spike_index in spike_indices]
                valid_spike_times = []
                valid_spike_times = [
                    spike_time
                    for spike_time in spike_times
                    if epoch_start <= spike_time < epoch_stop
                ]

                spikes_tstamps_by_unit[new_unit_name] = valid_spike_times

        return spikes_tstamps_by_unit

    df['SpikeTimes'] = df['EpochStartStop'].apply(single_row_calculation)
    return df


def extract_target_unit_data(unit, data):
    # Get SpikeTimes for channel
    unit_data = data.copy()
    unit_data[f'SpikeTimes_{unit}'] = data['SpikeTimes'].apply(lambda x: x[unit] if unit in x else [])
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
            ax.set_xlim(0, 2.0)
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
    plt.show()
    ## SAVE PLOTS
    base_save_dir = "/home/r2_allen/git/EStimShape/EStimShapeAnalysis/plots/julie"
    if experiment_name is not None:
        save_dir = os.path.join(base_save_dir, experiment_name)
        os.makedirs(save_dir, exist_ok=True)

        # Save individual plot
        individual_save_path = os.path.join(save_dir, f"{experiment_name}_{unit}_sorted_raster.png")
        fig.savefig(individual_save_path)

    return fig


if __name__ == '__main__':
    main()
