import numpy as np
from matplotlib import cm, pyplot as plt

from analysis.nafc.nafc_database_fields import IsCorrectField, NoiseChanceField, NumRandDistractorsField
from analysis.nafc.psychometric_curves import collect_choice_trials, plot_psychometric_curve, unix_to_datetime
from clat.compile.trial.cached_fields import CachedFieldList
from clat.util import time_util
from clat.util.connection import Connection


def main():
    conn = Connection("allen_estimshape_train_231211")
    trial_tstamps = collect_choice_trials(conn, time_util.from_date_to_now(2024,
                                                                       1, 3,
                                                                           ))


    print (unix_to_datetime(time_util.now()))
    fields = CachedFieldList()
    fields.append(IsCorrectField(conn))
    fields.append(NoiseChanceField(conn))
    fields.append(NumRandDistractorsField(conn))

    data = fields.get_data(trial_tstamps)
    print(data.to_string())

    # FILTER DATA
    data = data[data['NumRandDistractors'] == 2]

    plot_psychometric_curves_by_day(data)
    plt.show()

def plot_psychometric_curves_by_day(df):
    show_n = True

    """
    Plots psychometric curves binned by the calendar date from 'TrialStartStop'.
    """
    # Extract dates from 'TrialStartStop' column
    df['Date'] = df['TrialStartStop'].apply(lambda x: unix_to_datetime(x.stop).date())

    # Group by Date and plot psychometric curves for each day
    grouped = df.groupby('Date')
    num_days = len(grouped)
    colors = cm.viridis(np.linspace(0, 1, num_days))

    fig, ax = plt.subplots(figsize=(12, 8))


    for (date, group), color in zip(grouped, colors):
        plot_psychometric_curve(group, title=f"Psychometric Curve for {date}", ax=ax, color=color, label=str(date), show_n=show_n)


    ax.legend(title="Date")
    ax.set_title('Psychometric Curves by Day')
    ax.set_xlabel('Noise Chance')
    ax.set_ylabel('Percent Correct (%)')
    ax.grid(True)
    ax.invert_xaxis()  # Invert x-axis to have higher NoiseChance first

    plt.show()


if __name__ == "__main__":
    main()