import sys
from pathlib import Path

# Add the parent directory to the path to import from the original file
# Adjust this path based on where you save this file relative to the original
sys.path.insert(0, str(Path(__file__).parent))

from matplotlib import pyplot as plt, cm
from clat.compile.tstamp.cached_tstamp_fields import CachedFieldList
from clat.util import time_util
from clat.util.connection import Connection

from src.analysis.nafc.nafc_database_fields import (
    IsCorrectField, NoiseChanceField, NumRandDistractorsField,
    StimTypeField, ChoiceField, AnswerField, GenIdField, EStimEnabledField
)
from src.analysis.nafc.psychometric_curves import collect_choice_trials, plot_psychometric_curve_on_ax


def filter_by_num_distractors(data, num_distractors):
    """Filter data by NumRandDistractors value."""
    return data[data['NumRandDistractors'] == num_distractors]


def main():
    # Database connection
    conn = Connection("allen_estimshape_exp_251027_1")

    # Time range
    since_date = time_util.from_date_to_now(2024, 7, 10)
    start_gen_id = 0  # Filter for all data (EStim OFF and general filtering)
    start_gen_id_estim_on = 8  # Additional filter for EStim ON trials only (set higher to get only recent EStim ON data)

    # Collect trial timestamps
    trial_tstamps = collect_choice_trials(conn, since_date)

    # Set up fields to collect
    fields = CachedFieldList()
    fields.append(IsCorrectField(conn))
    fields.append(NoiseChanceField(conn))
    fields.append(NumRandDistractorsField(conn))
    fields.append(StimTypeField(conn))
    fields.append(ChoiceField(conn))
    fields.append(AnswerField(conn))
    fields.append(GenIdField(conn))
    fields.append(EStimEnabledField(conn))

    # Convert to dataframe
    data = fields.to_data(trial_tstamps)

    # Filter data by GenId
    data = data[data['GenId'] >= start_gen_id]

    # Split into the two datasets we care about
    data_procedural = data[data['StimType'] == 'EStimShapeProceduralBehavioralStim']
    data_exp = data[data['StimType'] == 'EStimShapeProceduralStim']

    # Create figure with 2x2 subplots
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    # Get colormap for multiple lines
    colors = cm.get_cmap('tab10').colors

    # TOP LEFT: Plot procedural data - overall and by NumRandDistractors
    plot_psychometric_curve_on_ax(
        data_procedural,
        axes[0, 0],
        title='Procedural Behavioral Trials',
        show_n=True,
        num_rep_min=0,
        color='black',
        linewidth=2.5,
        marker='o',
        markersize=6,
        label='All'
    )

    # Plot separate lines for each NumRandDistractors value
    distractor_values_proc = sorted(data_procedural['NumRandDistractors'].unique())
    for i, num_dist in enumerate(distractor_values_proc):
        filtered_data = filter_by_num_distractors(data_procedural, num_dist)
        plot_psychometric_curve_on_ax(
            filtered_data,
            axes[0, 0],
            show_n=True,
            num_rep_min=0,
            color=colors[i % len(colors)],
            linewidth=1.5,
            marker='o',
            markersize=4,
            linestyle='--',
            label=f'NumDist={num_dist}'
        )

    # TOP RIGHT: Experimental plot with NumRandDistractors breakdown AND EStim variants
    plot_psychometric_curve_on_ax(
        data_exp,
        axes[0, 1],
        title='Experimental Procedural Trials (with EStim variants)',
        show_n=True,
        num_rep_min=0,
        color='black',
        linewidth=2.5,
        marker='s',
        markersize=6,
        label='All'
    )

    # Plot separate lines for each NumRandDistractors value, split by EStim enabled/disabled
    distractor_values_exp = sorted(data_exp['NumRandDistractors'].unique())
    for i, num_dist in enumerate(distractor_values_exp):
        filtered_data = filter_by_num_distractors(data_exp, num_dist)

        # Plot with EStim enabled (solid line, smaller)
        filtered_data_estim_on = filtered_data[
            (filtered_data['EStimEnabled'] == True) & (filtered_data['GenId'] >= start_gen_id_estim_on)]
        if len(filtered_data_estim_on) > 0:
            plot_psychometric_curve_on_ax(
                filtered_data_estim_on,
                axes[0, 1],
                show_n=True,
                num_rep_min=0,
                color=colors[i % len(colors)],
                linewidth=1.5,
                marker='s',
                markersize=4,
                linestyle='-',
                label=f'NumDist={num_dist} (EStim ON)'
            )

        # Plot with EStim disabled (dashed line, smaller)
        filtered_data_estim_off = filtered_data[filtered_data['EStimEnabled'] == False]
        if len(filtered_data_estim_off) > 0:
            plot_psychometric_curve_on_ax(
                filtered_data_estim_off,
                axes[0, 1],
                show_n=True,
                num_rep_min=0,
                color=colors[i % len(colors)],
                linewidth=1.5,
                marker='o',
                markersize=4,
                linestyle='--',
                label=f'NumDist={num_dist} (EStim OFF)'
            )

    # BOTTOM RIGHT: Simple EStim ON vs OFF comparison (two solid lines only)
    data_exp_estim_on = data_exp[(data_exp['EStimEnabled'] == True) & (data_exp['GenId'] >= start_gen_id_estim_on)]
    data_exp_estim_off = data_exp[data_exp['EStimEnabled'] == False]

    if len(data_exp_estim_on) > 0:
        plot_psychometric_curve_on_ax(
            data_exp_estim_on,
            axes[1, 1],
            title='Experimental: EStim ON vs OFF',
            show_n=True,
            num_rep_min=0,
            color='red',
            linewidth=2.5,
            marker='s',
            markersize=6,
            linestyle='-',
            label='EStim ON'
        )

    if len(data_exp_estim_off) > 0:
        plot_psychometric_curve_on_ax(
            data_exp_estim_off,
            axes[1, 1],
            title='Experimental: EStim ON vs OFF',
            show_n=True,
            num_rep_min=0,
            color='blue',
            linewidth=2.5,
            marker='o',
            markersize=6,
            linestyle='-',
            label='EStim OFF'
        )

    # Hide bottom left plot (unused)
    axes[1, 0].axis('off')

    # Format all axes (except the hidden one)
    for i in range(2):
        for j in range(2):
            if i == 1 and j == 0:  # Skip bottom left (hidden)
                continue
            axes[i, j].invert_xaxis()
            axes[i, j].set_ylim([0, 110])
            axes[i, j].grid(True, alpha=0.3)
            axes[i, j].legend()

    plt.tight_layout()
    plt.show()


if __name__ == '__main__':
    main()