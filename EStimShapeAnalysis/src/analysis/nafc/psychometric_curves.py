import datetime

import numpy as np
import pandas as pd
import pytz
from clat.compile.trial.cached_fields import CachedFieldList
from clat.compile.trial.trial_collector import TrialCollector
from matplotlib import pyplot as plt, cm

from src.analysis.nafc.nafc_database_fields import IsCorrectField, NoiseChanceField, NumRandDistractorsField, \
    StimTypeField, ChoiceField, AnswerField, GenIdField
from clat.util import time_util
from clat.util.connection import Connection, since_nth_most_recent_experiment
from clat.util.time_util import When


def collect_choice_trials(conn: Connection, when: When = time_util.all()) -> list[When]:
    trial_collector = TrialCollector(conn, when)
    return trial_collector.collect_choice_trials()


def main():
    conn = Connection("allen_estimshape_train_240604")
    date_and_time = time_util.on_date_and_time(2024,
                                               6, 19,
                                               start_time=None,  # "16:49:00"
                                               end_time=None)
    since_date = time_util.from_date_to_now(2024, 7, 10)
    last_experiment = since_nth_most_recent_experiment(conn, n=1)
    start_gen_id = 436

    trial_tstamps = collect_choice_trials(conn, last_experiment)

    fields = CachedFieldList()
    fields.append(IsCorrectField(conn))
    fields.append(NoiseChanceField(conn))
    fields.append(NumRandDistractorsField(conn))
    fields.append(StimTypeField(conn))
    fields.append(ChoiceField(conn))
    fields.append(AnswerField(conn))
    fields.append(GenIdField(conn))

    data = fields.to_data(trial_tstamps)

    # Filter data by GenId
    data = data[data['GenId'] >= start_gen_id]

    data_psychometric = data[data['StimType'] == 'EStimShapePsychometricTwoByTwoStim']
    data_procedural = data[data['StimType'] == 'EStimShapeTwoByTwoBehavioralStim']
    data_psychometric_untouched = data_psychometric[data_psychometric['NumRandDistractors'] == 0]
    print(data_psychometric.to_string())
    # print number of each choice
    print(data_psychometric['Choice'].value_counts())
    print(data_psychometric_untouched['Choice'].value_counts())
    # FILTER DATA
    fig, axes = plt.subplots(2, 3, figsize=(8, 12))

    axes_psychometric = axes[0, :]
    axes_choices = axes[1, :]
    answer_types = ["I", "II", "III", "IV"]
    color_for_all = 'black'
    colors_for_answers = cm.get_cmap('tab10').colors
    #PROCEDURAL
    plot_psychometric_curve_on_ax(data_procedural, axes_psychometric[0], title='Procedural Trials', show_n=True,
                                  num_rep_min=0, color=color_for_all)

    #PSYCHOMETRIC-ALL
    plot_psychometric_curve_on_ax(data_psychometric, axes_psychometric[1], title='Pyschometric Trials', show_n=True,
                                  num_rep_min=0, label="All", color=color_for_all, linewidth=2)
    for answer in answer_types:
        plot_psychometric_curve_on_ax(filter_to_sample_type(data_psychometric, answer), axes_psychometric[1],
                                      show_n=True,
                                      num_rep_min=0,
                                      label=answer,
                                      color=colors_for_answers[answer_types.index(answer)],
                                      linestyle='--')
    plot_choices_per_sample(data_psychometric, axes_choices[1])

    #PSYCHOMETRIC-UNTOUCHED
    plot_psychometric_curve_on_ax(data_psychometric_untouched, axes_psychometric[2],
                                  title='Pyschometric Trials - Untouched', show_n=True,
                                  num_rep_min=0, label="All", color=color_for_all)
    for answer in answer_types:
        plot_psychometric_curve_on_ax(filter_to_sample_type(data_psychometric_untouched, answer), axes_psychometric[2],
                                      show_n=True,
                                      num_rep_min=0,
                                      label=answer,
                                      color=colors_for_answers[answer_types.index(answer)],
                                      linestyle='--')
    # New plot for choices per sample
    plot_choices_per_sample(data_psychometric_untouched, axes_choices[2])

    plot_incorrect_choices(data_psychometric, axes_choices[0])

    for ax in axes[0, :]:
        ax.invert_xaxis()
        ax.set_ylim([0, 110])
        ax.legend()

    plt.show()


def plot_incorrect_choices(data, ax):
    choice_types = ["I", "II", "III", "IV"]
    incorrect_choices = {choice: 0 for choice in choice_types}
    no_choice = 0  # Counter for None or invalid choices

    for _, row in data.iterrows():
        if row['Choice'] != row['Answer']:
            if row['Choice'] in choice_types:
                incorrect_choices[row['Choice']] += 1
            else:
                no_choice += 1

    ax.bar(choice_types, [incorrect_choices[choice] for choice in choice_types])

    # Add a bar for 'None' or invalid choices if there are any
    if no_choice > 0:
        ax.bar(len(choice_types), no_choice)
        choice_types.append('None')

    ax.set_xlabel('Choice')
    ax.set_ylabel('Number of Incorrect Selections')
    ax.set_title('Incorrect Choices')
    ax.set_xticks(range(len(choice_types)))
    ax.set_xticklabels(choice_types)

    # Add value labels on top of each bar
    for i, v in enumerate(list(incorrect_choices.values()) + ([no_choice] if no_choice > 0 else [])):
        ax.text(i, v, str(v), ha='center', va='bottom')

    return no_choice  # Return the count of None/invalid choices for debugging
def plot_choices_per_sample(data, ax):
    answer_types = ["I", "II", "III", "IV"]
    choice_types = ["I", "II", "III", "IV"]

    choice_data = {choice: [] for choice in choice_types}

    for answer in answer_types:
        answer_data = data[data['Answer'] == answer]
        choice_counts = answer_data['Choice'].value_counts().reindex(choice_types).fillna(0)

        for choice in choice_types:
            choice_data[choice].append(choice_counts[choice])

    x = np.arange(len(answer_types))
    width = 0.2

    for i, choice in enumerate(choice_types):
        offset = (i - 1.5) * width
        ax.bar(x + offset, choice_data[choice], width, label=f'Choice {choice}')

    ax.set_xlabel('Sample')
    ax.set_ylabel('Count')
    ax.set_title('Choices per Sample Type')
    ax.set_xticks(x)
    ax.set_xticklabels(answer_types)
    ax.legend()

    # Add value labels on top of each bar
    for i, choice in enumerate(choice_types):
        offset = (i - 1.5) * width
        for j, v in enumerate(choice_data[choice]):
            ax.text(j + offset, v, str(int(v)), ha='center', va='bottom')


def filter_to_sample_type(data, sample_type):
    return data[data['Answer'] == sample_type]


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
    plot_psychometric_curve_on_ax(df, ax, title=title, color=color, label=label, show_n=show_n, num_rep_min=5)
    plt.show()


def plot_psychometric_curve_on_ax(df, ax, title=None, show_n=False, num_rep_min=10, **plot_kwargs):
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

    ax.set_title(title, fontsize=14)
    ax.set_xlabel('Noise Chance (%)', fontsize=14)
    ax.set_ylabel('Percent Correct', fontsize=14)
    ax.grid(True)

    # Setting the x-axis labels to where there are data points
    existing_ticks = set(ax.get_xticks())
    updated_ticks = existing_ticks.union(set(percent_correct.index))
    ax.set_xticks(sorted(updated_ticks))
    ticks = [f"{x * 100:.0f}" for x in sorted(updated_ticks)]
    ax.set_xticklabels(ticks, rotation=45, fontsize=14, color='black', fontweight='regular')
    ax.tick_params(axis='y', labelsize=14)

    # Plotting as a line graph on the given ax

    line = ax.plot(percent_correct.index, percent_correct.values, **plot_kwargs)

    # Adding text for num_reps above each data point
    if show_n:
        for noise_chance, y_val in percent_correct.items():
            reps = num_reps[noise_chance]
            ax.text(noise_chance, y_val, f'{reps}', color=line[0].get_color(), ha='center', va='bottom')


def plot_binned_psychometric_curves(df, num_bins):
    """
    Plots percent correct binned into num_bins bins, using a separate line for each bin.
    This is used to visualize psychometric shift across time.
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
