import datetime

import numpy as np
import pandas as pd
import pytz
from matplotlib import pyplot as plt, cm

from analysis.nafc.nafc_database_fields import IsCorrectField, NoiseChanceField, NumRandDistractorsField, StimTypeField
from clat.compile.trial.trial_collector import TrialCollector
from clat.compile.trial.cached_fields import CachedFieldList, CachedDatabaseField
from clat.util import time_util
from clat.util.connection import Connection, since_nth_most_recent_experiment
from clat.util.time_util import When


def collect_choice_trials(conn: Connection, when: When = time_util.all()) -> list[When]:
    trial_collector = TrialCollector(conn, when)
    return trial_collector.collect_choice_trials()


def main():
    conn = Connection("allen_estimshape_train_231211")
    date_and_time = time_util.on_date_and_time(2024,
                                               1, 25,
                                               start_time=None,  # "16:49:00"
                                               end_time=None)
    last_experiment = since_nth_most_recent_experiment(conn, n=3)

    trial_tstamps = collect_choice_trials(conn, date_and_time)

    fields = CachedFieldList()
    fields.append(IsCorrectField(conn))
    fields.append(NoiseChanceField(conn))
    fields.append(NumRandDistractorsField(conn))
    fields.append(StimTypeField(conn))

    data = fields.get_data(trial_tstamps)
    print(data.to_string())

    # FILTER DATA
    data_1_hard_distractor = data[data['NumRandDistractors'] == 2]
    data_2_hard_distractors = data[data['NumRandDistractors'] == 1]
    plot_psychometric_curves_side_by_side(data_1_hard_distractor, data_2_hard_distractors, '1 Hard Distractor',
                                          '2 Hard Distractors', show_n=True)

def plot_psycho_delta(data):
    data = data[data['NumRandDistractors'] == 2]
    data_psychometric = data[data['StimType'] == 'RandProcedural']
    data_delta = data[data['StimType'] == 'RandDeltaProcedural']
    # plot_binned_psychometric_curves(data, 2)
    plot_psychometric_curves_side_by_side(
        data_psychometric, data_delta, 'Psychometric', 'Delta', show_n=True)
    plt.show()


def unix_to_datetime(unix_timestamp):
    """Convert Unix timestamp in microseconds to a datetime object in local timezone."""
    # Create a UTC datetime object from the Unix timestamp
    utc_dt = datetime.datetime.utcfromtimestamp(unix_timestamp / 1e6).replace(tzinfo=pytz.utc)

    # Convert the UTC datetime object to local timezone
    local_dt = utc_dt.astimezone(pytz.timezone('US/Eastern'))
    return local_dt

def plot_psychometric_curve(df, title=None, color=None, label=None, show_n=False):
    """
    Plots a single line based on NoiseChance and IsCorrect values in the given DataFrame.
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    plot_psychometric_curve_on_ax(df, ax, title=title, color=color, label=label, show_n=show_n)
    plt.show()



def plot_psychometric_curves_side_by_side(df1, df2, title1=None, title2=None, color1=None, color2=None, label1=None, label2=None, show_n=False):
    """
    Plots two DataFrames side by side in a subplot.
    """
    fig, axs = plt.subplots(nrows=1, ncols=2, figsize=(20, 6))  # Create 1 row, 2 columns subplot

    # Plotting each DataFrame on its respective ax
    plot_psychometric_curve_on_ax(df1, axs[0], title=title1, color=color1, label=label1, show_n=show_n, num_rep_min=1)
    plot_psychometric_curve_on_ax(df2, axs[1], title=title2, color=color2, label=label2, show_n=show_n, num_rep_min=1)

    # Adjust subplot parameters for better layout
    plt.subplots_adjust(wspace=0.3)

    # Add an overall title if needed
    if title1 or title2:
        plt.suptitle(f'{title1} and {title2}')

    # scale both plots the same
    axs[0].set_ylim([20, 100])
    axs[1].set_ylim([20, 100])

    plt.show()


def plot_psychometric_curve_on_ax(df, ax, title=None, color=None, label=None, show_n=False, num_rep_min=10):
    """
    Plots a single line based on NoiseChance and IsCorrect values in the given DataFrame.
    Plots on the provided matplotlib Axes (ax).
    """
    # Group by 'NoiseChance' and calculate the percentage of 'Correct' in 'IsCorrect'
    percent_correct = df.groupby('NoiseChance')['IsCorrect'].apply(lambda x: (x == True).sum() / len(x) * 100)

    # Filter out NoiseChance values with too little data
    num_reps = df.groupby('NoiseChance')['IsCorrect'].count()
    percent_correct = percent_correct[num_reps > num_rep_min]

    # Sort the percent_correct Series in ascending order of 'NoiseChance'
    percent_correct = percent_correct.sort_index(ascending=True)

    ax.set_title(title)
    ax.set_xlabel('Noise Chance')
    ax.set_ylabel('Percent Correct (%)')
    ax.grid(True)
    ax.invert_xaxis()  # Invert x-axis to have higher NoiseChance first

    # Setting the x-axis labels to where there are data points
    existing_ticks = set(ax.get_xticks())
    updated_ticks = existing_ticks.union(set(percent_correct.index))
    ax.set_xticks(sorted(updated_ticks))
    ax.set_xticklabels([f"{x:.4f}" for x in sorted(updated_ticks)], rotation=45)

    # Plotting as a line graph on the given ax
    line = ax.plot(percent_correct.index, percent_correct.values, color=color, marker='o', label=label)

    if show_n:
        # Adding text for num_reps above each data point
        for noise_chance, y_val in percent_correct.items():
            reps = num_reps[noise_chance]
            ax.text(noise_chance, y_val, f'{reps}', color=line[0].get_color(), ha='center', va='bottom')

def plot_binned_psychometric_curves(df, num_bins):
    """
    Plots percent correct binned into num_bins bins, using a separate line for each bin.
    """
    # Convert 'NoiseChance' to numeric if it's not already
    if df['NoiseChance'].dtype == 'O':
        df['NoiseChance'] = pd.to_numeric(df['NoiseChance'], errors='coerce')

    # Determine the number of trials per bin
    trials_per_bin = len(df) // num_bins

    # Assign each trial to a bin
    df['Bin'] = np.ceil((df.index + 1) / trials_per_bin)
    df['Bin'] = df['Bin'].clip(upper=num_bins)

    # Create a colormap
    colors = cm.viridis(np.linspace(0, 1, num_bins))

    # Create a figure and axes for plotting
    fig, ax = plt.subplots(figsize=(10, 6))

    for bin_number in range(1, num_bins + 1):
        bin_data = df[df['Bin'] == bin_number]
        plot_psychometric_curve(bin_data, 'Percentage of Correct Responses by Noise Chance for Each Bin', ax,
                                colors[bin_number - 1], label=f'Bin {bin_number}')

    # Add legend and show plot
    ax.legend()
    ax.set_title('Percentage of Correct Responses by Noise Chance for Each %d-Trials' % trials_per_bin)
    ax.set_xlabel('Noise Chance')
    ax.set_ylabel('Percent Correct (%)')
    ax.grid(True)
    ax.invert_xaxis()  # Invert x-axis to have higher NoiseChance first


if __name__ == '__main__':
    main()
