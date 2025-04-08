from pathlib import Path

import pandas as pd
from PIL import Image
from matplotlib import pyplot as plt

from clat.compile.task.cached_task_fields import CachedTaskFieldList
from clat.compile.task.classic_database_task_fields import StimSpecIdField
from clat.compile.task.compile_task_id import TaskIdCollector

from clat.util import time_util
from clat.util.connection import Connection
from clat.util.time_util import When

from src.analysis.cached_task_fields import StimTypeField, StimPathField, ThumbnailField, GAResponseField, \
    ClusterResponseField, LineageField

from src.pga.alexnet.analysis.plot_top_n_alexnet import add_colored_border
from src.startup import context


def main():
    # Setting up connection and time frame to analyse in
    conn = Connection(context.ga_database)

    experiment_id = context.ga_config.db_util.read_current_experiment_id(context.ga_name)
    start = context.ga_config.db_util.read_current_experiment_id(context.ga_name)
    stop = time_util.now()

    # Collecting trials and compiling data


    data_for_all_tasks = compile_data(conn)

    # Removing empty trials (no stim_id)
    # Remove trials with no response
    data_for_all_tasks = data_for_all_tasks[data_for_all_tasks['Cluster Response'].apply(lambda x: x != 'nan')]

    # Group by StimId and aggregate
    data_for_stim_ids = data_for_all_tasks.groupby('StimSpecId').agg({
        'Lineage': 'first',
        'StimType': 'first',
        'ThumbnailPath': 'first',
        'Cluster Response': 'mean',
        'GA Response': 'first'
    }).reset_index()

    # Rename the response column
    data_for_stim_ids = data_for_stim_ids.rename(columns={'Cluster Response': 'Average Response'})

    print(data_for_stim_ids.to_string())

    # Convert DataFrame to list of dicts for plotting
    stimuli_list = []
    for _, row in data_for_stim_ids.iterrows():

        stim = {
            'stim_id': row['StimSpecId'],
            'response': row['GA Response'],
            'lineage_id': row['Lineage'],
            'path': row['ThumbnailPath']
        }

        if stim['path'] is not None:
            stimuli_list.append(stim)


    # Create and save plot
    fig = plot_top_n_stimuli(stimuli_list, n=20)
    # plt.savefig(f"{context.plots_dir}/top_responses.png")
    plt.show()


def compile_data(conn: Connection) -> pd.DataFrame:
    collector = TaskIdCollector(conn)
    task_ids = collector.collect_task_ids()
    response_processor = context.ga_config.make_response_processor()
    cluster_combination_strategy = response_processor.cluster_combination_strategy


    fields = CachedTaskFieldList()
    fields.append(StimSpecIdField(conn))
    fields.append(LineageField(conn))
    fields.append(StimTypeField(conn))
    fields.append(StimPathField(conn))
    fields.append(ThumbnailField(conn))
    fields.append(GAResponseField(conn))
    fields.append(ClusterResponseField(conn, cluster_combination_strategy))
    # fields.append(ShaftField(conn, mstick_spec_data_source))
    # fields.append(TerminationField(conn, mstick_spec_data_source))
    # fields.append(JunctionField(conn, mstick_spec_data_source))

    data = fields.to_data(task_ids)
    return data



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
