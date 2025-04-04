from pathlib import Path

import pandas as pd
from PIL import Image
from matplotlib import pyplot as plt

from clat.compile.tstamp.cached_tstamp_fields import CachedFieldList
from clat.compile.tstamp.classic_database_tstamp_fields import StimSpecDataField, TaskIdField, StimIdField
from clat.compile.tstamp.trial_tstamp_collector import TrialCollector
from clat.util import time_util
from clat.util.connection import Connection
from clat.util.time_util import When
from src.analysis.cached_fields import LineageField, StimTypeField, StimPathField, \
    ClusterResponseField
from src.pga.alexnet.analysis.plot_top_n_alexnet import add_colored_border
from src.startup import context


def main():
    # Setting up connection and time frame to analye in
    conn = Connection(context.ga_database)

    experiment_id = context.ga_config.db_util.read_current_experiment_id(context.ga_name)
    start = context.ga_config.db_util.read_current_experiment_id(context.ga_name)
    stop = time_util.now()

    # Collecting trials and compiling data
    trial_tstamps = collect_trials(conn, When(start, stop))
    data_for_all_tasks = compile_data(conn, trial_tstamps)

    # Removing empty trials (no stim_id)
    # Remove trials with no response
    data_for_all_tasks = data_for_all_tasks[data_for_all_tasks['Cluster Response'].apply(lambda x: x != 'nan')]

    # Group by StimId and aggregate
    data_for_stim_ids = data_for_all_tasks.groupby('StimId').agg({
        'Lineage': 'first',
        'StimType': 'first',
        'StimPath': 'first',
        'Cluster Response': 'mean'
    }).reset_index()

    # Rename the response column
    data_for_stim_ids = data_for_stim_ids.rename(columns={'Cluster Response': 'Average Response'})

    print(data_for_stim_ids.to_string())

    # Convert DataFrame to list of dicts for plotting
    stimuli_list = []
    for _, row in data_for_stim_ids.iterrows():
        stim = {
            'stim_id': row['StimId'],
            'response': row['Average Response'],
            'lineage_id': row['Lineage'],
            'path': row['StimPath']
        }
        stimuli_list.append(stim)

    # Create and save plot
    fig = plot_top_n_stimuli(stimuli_list, n=20)
    # plt.savefig(f"{context.plots_dir}/top_responses.png")
    plt.show()


def compile_data(conn: Connection, trial_tstamps: list[When]) -> pd.DataFrame:
    response_processor = context.ga_config.make_response_processor()
    cluster_combination_strategy = response_processor.cluster_combination_strategy
    mstick_spec_data_source = StimSpecDataField(conn)

    fields = CachedFieldList()
    fields.append(TaskIdField(conn))
    fields.append(StimIdField(conn))
    fields.append(LineageField(conn))
    fields.append(StimTypeField(conn))
    fields.append(StimPathField(conn))
    fields.append(ClusterResponseField(conn, cluster_combination_strategy))
    # fields.append(ShaftField(conn, mstick_spec_data_source))
    # fields.append(TerminationField(conn, mstick_spec_data_source))
    # fields.append(JunctionField(conn, mstick_spec_data_source))

    data = fields.to_data(trial_tstamps)
    return data


def collect_trials(conn: Connection, when: When = time_util.all()) -> list[When]:
    trial_collector = TrialCollector(conn, when)
    return trial_collector.collect_trials()


def plot_top_n_stimuli(stimuli: list[dict], n: int = 10, fig_size=(20, 4), min_response=None, max_response=None):
    """
    Plot top N stimuli with borders colored by response intensity.

    Parameters:
    stimuli (list[dict]): List of stimulus dictionaries. Each must have:
        - 'stim_id': Stimulus identifier
        - 'response': Numeric response value
        - 'path': Path to stimulus image
        Optional:
        - 'lineage_id': Lineage identifier (will be displayed if present)
    n (int): Number of top stimuli to show
    fig_size (tuple): Figure size as (width, height)
    min_response, max_response (float): Optional response range for normalization.
                                      If None, will use min/max from provided stimuli.

    Returns:
    matplotlib.figure.Figure: The created figure
    """
    # Sort stimuli by response and take top N
    sorted_stimuli = sorted(stimuli, key=lambda x: x['response'], reverse=True)[:n]

    # Normalize responses
    if min_response is None:
        min_response = min(x['response'] for x in sorted_stimuli)
    if max_response is None:
        max_response = max(x['response'] for x in sorted_stimuli)

    response_range = max_response - min_response
    for stim in sorted_stimuli:
        if response_range == 0:
            stim['normalized_response'] = 1.0
        else:
            stim['normalized_response'] = (stim['response'] - min_response) / response_range

    # Calculate grid dimensions
    ncols = min(10, n)  # 10 images per row maximum
    nrows = (n - 1) // ncols + 1

    # Create figure
    fig, axes = plt.subplots(nrows, ncols, figsize=fig_size)
    if nrows == 1:
        axes = axes.reshape(1, -1)

    # Plot each stimulus
    for idx, stim in enumerate(sorted_stimuli):
        row, col = idx // ncols, idx % ncols
        ax = axes[row, col]

        img_path = Path(stim['path'])
        if img_path.exists():
            img = Image.open(img_path)
            img_with_border = add_colored_border(img, stim['normalized_response'])
            ax.imshow(img_with_border)

            # Create label text
            label_parts = [f"Response: {stim['response']:.2f}",
                           f"ID: {stim['stim_id']}"]
            if 'lineage_id' in stim:
                label_parts.append(f"Lineage: {stim['lineage_id']}")

            ax.text(img_with_border.size[0] - 5, 5,
                    '\n'.join(label_parts),
                    fontsize=5, color='black',
                    transform=ax.transData,
                    ha='right', va='top')
        else:
            ax.text(0.5, 0.5, f"Image not found\nID: {stim['stim_id']}",
                    ha='center', va='center')
        ax.axis('off')

    # Turn off any unused subplots
    for ax in axes.flat[len(sorted_stimuli):]:
        ax.axis('off')

    plt.tight_layout()
    return fig




if __name__ == "__main__":
    main()
