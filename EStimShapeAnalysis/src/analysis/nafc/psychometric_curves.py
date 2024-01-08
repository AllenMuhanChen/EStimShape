import datetime

from matplotlib import pyplot as plt

from analysis.nafc.nafc_database_fields import IsCorrectField, NoiseChanceField
from clat.compile.trial.trial_collector import TrialCollector
from clat.compile.trial.trial_field import FieldList
from clat.compile.trial.cached_fields import CachedFieldList
from clat.util import time_util
from clat.util.connection import Connection
from clat.util.time_util import When


def collect_choice_trials(conn: Connection, when: When = time_util.all()) -> list[When]:
    trial_collector = TrialCollector(conn, when)
    return trial_collector.collect_choice_trials()


def main():
    conn = Connection("allen_estimshape_train_231211")
    trial_tstamps = collect_choice_trials(conn, time_util.on_date_and_time(2024,
                                                                           1, 3,
                                                                           start_time="16:49:00",  # "16:49:00"
                                                                           end_time=None))

    fields = CachedFieldList()
    fields.append(IsCorrectField(conn))
    fields.append(NoiseChanceField(conn))

    data = fields.get_data(trial_tstamps)
    print(data.to_string())

    plot_percent_correct(data)


def plot_percent_correct(df):
    # Group by 'NoiseChance' and calculate the percentage of 'Correct' in 'IsCorrect'
    percent_correct = df.groupby('NoiseChance')['IsCorrect'].apply(lambda x: (x == 'Correct').sum() / len(x) * 100)

    # Sort the percent_correct Series in descending order of 'NoiseChance'
    percent_correct = percent_correct.sort_index(ascending=True)

    # Plotting as a line graph
    plt.figure(figsize=(10, 6))
    percent_correct.plot(kind='line', color='skyblue', marker='o')  # Using line plot with markers for each point
    plt.title('Percentage of Correct Responses by Noise Chance')
    plt.xlabel('Noise Chance')
    plt.ylabel('Percent Correct (%)')
    plt.grid(True)
    plt.gca().invert_xaxis()  # Invert x-axis to have higher NoiseChance first
    plt.show()


if __name__ == '__main__':
    main()
