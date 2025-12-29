import sys
from pathlib import Path
import numpy as np

# Add the parent directory to the path to import from the original file
# Adjust this path based on where you save this file relative to the original
sys.path.insert(0, str(Path(__file__).parent))

from matplotlib import pyplot as plt
from clat.compile.tstamp.cached_tstamp_fields import CachedFieldList
from clat.util import time_util
from clat.util.connection import Connection

from src.analysis.nafc.nafc_database_fields import (
    IsCorrectField, NoiseChanceField, NumRandDistractorsField,
    StimTypeField, ChoiceField, AnswerField, GenIdField, EStimEnabledField,
    BaseMStickIdField
)
from src.analysis.nafc.psychometric_curves import collect_choice_trials, plot_psychometric_curve_on_ax


def main():
    # Database connection
    conn = Connection("allen_estimshape_exp_251226_0")

    # Time range
    since_date = time_util.from_date_to_now(2024, 7, 10)
    start_gen_id = 8  # Filter for all data (EStim OFF and general filtering)
    max_gen_id = 19  # Maximum GenId to include
    start_gen_id_estim_on = 0  # Additional filter for EStim ON trials only
    max_gen_id_estim_on = float('inf')  # Maximum GenId for EStim ON trials

    # Collect trial timestamps
    trial_tstamps = collect_choice_trials(conn, since_date)

    # Set up fields to collect
    fields = CachedFieldList()
    fields.append(IsCorrectField(conn))
    fields.append(NoiseChanceField(conn))
    fields.append(NumRandDistractorsField(conn))
    fields.append(StimTypeField(conn))
    fields.append(ChoiceField(conn))
    fields.append(GenIdField(conn))
    fields.append(EStimEnabledField(conn))
    fields.append(BaseMStickIdField(conn))  # Add the new field

    # Convert to dataframe
    data = fields.to_data(trial_tstamps)

    # Filter data by GenId (both min and max)
    data = data[(data['GenId'] >= start_gen_id) & (data['GenId'] <= max_gen_id)]

    # Filter for experimental trials only
    data_exp = data[data['StimType'] == 'EStimShapeVariantsNAFCStim']

    # Get unique BaseMStickId values (excluding None/NaN)
    base_mstick_ids = data_exp['BaseMStickId'].dropna().unique()
    base_mstick_ids = sorted([x for x in base_mstick_ids if x is not None])

    if len(base_mstick_ids) == 0:
        print("No BaseMStickId values found in the data!")
        return

    print(f"Found {len(base_mstick_ids)} unique BaseMStickId values: {base_mstick_ids}")

    # Determine subplot layout
    n_plots = len(base_mstick_ids)
    n_cols = min(3, n_plots)  # Max 3 columns
    n_rows = int(np.ceil(n_plots / n_cols))

    # Create figure with subplots for each BaseMStickId
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(6 * n_cols, 5 * n_rows))

    # Make sure axes is always a flat array
    if n_plots == 1:
        axes = np.array([axes])
    elif n_rows == 1:
        axes = axes.reshape(1, -1)
    axes_flat = axes.flatten()

    # Plot for each BaseMStickId
    for idx, base_mstick_id in enumerate(base_mstick_ids):
        ax = axes_flat[idx]

        # Filter data for this BaseMStickId
        data_base = data_exp[data_exp['BaseMStickId'] == base_mstick_id].copy()

        # Apply EStim filters
        data_base_estim_on = data_base[
            (data_base['EStimEnabled'] == True) &
            (data_base['GenId'] >= start_gen_id_estim_on) &
            (data_base['GenId'] <= max_gen_id_estim_on)
            ]
        data_base_estim_off = data_base[data_base['EStimEnabled'] == False]

        # Plot EStim ON if data available
        if len(data_base_estim_on) > 0:
            plot_psychometric_curve_on_ax(
                data_base_estim_on,
                ax,
                title=f'BaseMStickId: {base_mstick_id}',
                show_n=True,
                num_rep_min=0,
                color='red',
                linewidth=2.5,
                marker='s',
                markersize=6,
                linestyle='-',
                label=f'EStim ON (n={len(data_base_estim_on)})'
            )

        # Plot EStim OFF if data available
        if len(data_base_estim_off) > 0:
            plot_psychometric_curve_on_ax(
                data_base_estim_off,
                ax,
                title=f'BaseMStickId: {base_mstick_id}',
                show_n=True,
                num_rep_min=0,
                color='blue',
                linewidth=2.5,
                marker='o',
                markersize=6,
                linestyle='-',
                label=f'EStim OFF (n={len(data_base_estim_off)})'
            )

        # Format axis
        ax.invert_xaxis()
        ax.set_ylim([0, 110])
        ax.grid(True, alpha=0.3)
        ax.legend()

        # Print statistics for this BaseMStickId
        print(f"\nBaseMStickId {base_mstick_id}:")
        print(f"  EStim ON: {len(data_base_estim_on)} trials")
        print(f"  EStim OFF: {len(data_base_estim_off)} trials")
        if len(data_base_estim_on) > 0:
            data_base_estim_on_clean = data_base_estim_on.copy()
            data_base_estim_on_clean.loc[data_base_estim_on_clean['IsCorrect'] == "No Data", 'IsCorrect'] = False
            acc = (data_base_estim_on_clean['IsCorrect'] == True).mean() * 100
            print(f"    EStim ON accuracy: {acc:.2f}%")
        if len(data_base_estim_off) > 0:
            data_base_estim_off_clean = data_base_estim_off.copy()
            data_base_estim_off_clean.loc[data_base_estim_off_clean['IsCorrect'] == "No Data", 'IsCorrect'] = False
            acc = (data_base_estim_off_clean['IsCorrect'] == True).mean() * 100
            print(f"    EStim OFF accuracy: {acc:.2f}%")

    # Hide unused subplots
    for idx in range(n_plots, len(axes_flat)):
        axes_flat[idx].axis('off')

    plt.tight_layout()
    plt.suptitle('Psychometric Curves by BaseMStickId', fontsize=16, y=1.01)
    plt.show()


if __name__ == '__main__':
    main()