import datetime

import numpy as np
import pandas as pd
import pytz
from matplotlib import pyplot as plt, cm

from analysis.nafc.nafc_database_fields import IsCorrectField, NoiseChanceField, NumRandDistractorsField
from clat.compile.trial.trial_collector import TrialCollector
from clat.compile.trial.cached_fields import CachedFieldList, CachedDatabaseField
from clat.util import time_util
from clat.util.connection import Connection
from clat.util.time_util import When


def collect_choice_trials(conn: Connection, when: When = time_util.all()) -> list[When]:
    trial_collector = TrialCollector(conn, when)
    return trial_collector.collect_choice_trials()


def main():
    conn = Connection("allen_estimshape_train_231211")
    trial_tstamps = collect_choice_trials(conn, time_util.on_date_and_time(2024,
                                                                           1, 9,
                                                                           start_time=None,  # "16:49:00"
                                                                           end_time=None))

    fields = CachedFieldList()
    fields.append(IsCorrectField(conn))
    fields.append(NoiseChanceField(conn))
    fields.append(NumRandDistractorsField(conn))

    data = fields.get_data(trial_tstamps)
    print(data.to_string())

    # FILTER DATA
    data = data[data['NumRandDistractors'] == 2]

    # plot_binned_psychometric_curves(data, 2)
    plot_psychometric_curve(data, 'Percentage of Correct Responses by Noise Chance')
    plt.show()


def unix_to_datetime(unix_timestamp):
    """Convert Unix timestamp in microseconds to a datetime object in local timezone."""
    # Create a UTC datetime object from the Unix timestamp
    utc_dt = datetime.datetime.utcfromtimestamp(unix_timestamp / 1e6).replace(tzinfo=pytz.utc)

    # Convert the UTC datetime object to local timezone
    local_dt = utc_dt.astimezone(pytz.timezone('US/Eastern'))
    return local_dt



def plot_psychometric_curve(df, title=None, ax=None, color=None, label=None):
    """
    Plots a single line based on NoiseChance and IsCorrect values in the given DataFrame.
    If an ax (matplotlib Axes) is provided, it plots on that ax. Otherwise, it creates a new plot.
    """
    # Group by 'NoiseChance' and calculate the percentage of 'Correct' in 'IsCorrect'
    percent_correct = df.groupby('NoiseChance')['IsCorrect'].apply(lambda x: (x == True).sum() / len(x) * 100)

    # Sort the percent_correct Series in ascending order of 'NoiseChance'
    percent_correct = percent_correct.sort_index(ascending=True)

    # Check if an ax is provided
    if ax is None:
        plt.figure(figsize=(10, 6))
        ax = plt.gca()

        ax.set_title(title)
        ax.set_xlabel('Noise Chance')
        ax.set_ylabel('Percent Correct (%)')
        ax.grid(True)
        ax.invert_xaxis()  # Invert x-axis to have higher NoiseChance first

    # Setting the x-axis labels to where there are data points
    existing_ticks = set(ax.get_xticks())
    updated_ticks = existing_ticks.union(set(percent_correct.index))
    ax.set_xticks(sorted(updated_ticks))
    ax.set_xticklabels(sorted(updated_ticks), rotation=45)  # Rotate labels for better readability

    # Plotting as a line graph on the given ax
    ax.plot(percent_correct.index, percent_correct.values, color=color, marker='o', label=label)


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
