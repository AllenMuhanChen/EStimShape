from pathlib import Path

import pandas as pd
from PIL import Image
from clat.pipeline.pipeline_base_classes import create_pipeline
from matplotlib import pyplot as plt

from clat.compile.task.cached_task_fields import CachedTaskFieldList
from clat.compile.task.classic_database_task_fields import StimSpecIdField
from clat.compile.task.compile_task_id import TaskIdCollector

from clat.util import time_util
from clat.util.connection import Connection
from clat.util.time_util import When

from src.analysis.cached_task_fields import StimTypeField, StimPathField, ThumbnailField, ClusterResponseField
from src.analysis.ga.cached_ga_fields import LineageField, GAResponseField, RegimeScoreField
from src.analysis.grouped_stims_by_response import create_grouped_stimuli_module
from src.analysis.isogabor.isogabor_analysis import IntanSpikesByChannelField, EpochStartStopTimesField
from src.analysis.matchstick_fields import ShaftField, TerminationField, JunctionField, StimSpecDataField
from src.intan.MultiFileParser import MultiFileParser

from src.pga.alexnet.analysis.plot_top_n_alexnet import add_colored_border
from src.pga.app.run_rwa import remove_catch_trials
from src.pga.mock.mock_rwa_analysis import condition_spherical_angles, hemisphericalize_orientation
from src.repository.export_to_repository import export_to_repository
from src.repository.import_from_repository import import_from_repository
from src.startup import context


def get_top_n_lineages(data, n):
    length_for_lineages = data.groupby("Lineage")["RegimeScore"].size()
    top_n_lineages = length_for_lineages.nlargest(n).index
    return list(top_n_lineages)


def main():
    # Setting up connection and time frame to analyse in
    conn = Connection(context.ga_database)

    # Collect data and condition it
    data_for_all_tasks = compile_data(conn)
    data = data_for_all_tasks[data_for_all_tasks['Cluster Response'].notna()]
    data = data[data['StimSpecId'].notna()]
    data = data[data['ThumbnailPath'].apply(lambda x: x != "None")]
    data = remove_catch_trials(data)
    data = condition_spherical_angles(data)
    data = hemisphericalize_orientation(data)

    export_to_repository(data, context.ga_database, "ga",
                         stim_info_table="GAStimInfo",
                         stim_info_columns=[
                             "Lineage",
                             "RegimeScore",
                             "StimType",
                             "StimPath",
                             "ThumbnailPath",
                             "GA Response",
                             "Cluster Response",
                             "Shaft",
                             "Termination",
                             "Junction"
                         ])

    data = import_from_repository(
        "250427_0",
        "ga",
        "GAStimInfo",
        "RawSpikeResponses"
    )

    # Break apart the response rate by channel
    data['Response Rate'] = data['Response Rate by channel'].apply(lambda x: x['A-018'])

    # Calculate average response rate for each StimSpecId within each Lineage
    avg_response = data.groupby(['Lineage', 'StimSpecId'])['Response Rate'].mean().reset_index()
    avg_response.rename(columns={'Response Rate': 'Avg Response Rate'}, inplace=True)

    # Rank the averages within each Lineage
    avg_response['RankWithinLineage'] = avg_response.groupby('Lineage')['Avg Response Rate'].rank(ascending=False, method='first')

    # Merge the ranks back to the original dataframe
    data = data.merge(avg_response[['Lineage', 'StimSpecId', 'RankWithinLineage']], on=['Lineage', 'StimSpecId'], how='left')

    visualize_module = create_grouped_stimuli_module(
        response_rate_col='Response Rate',
        # response_rate_key='A-018',
        path_col='ThumbnailPath',
        col_col='RankWithinLineage',
        row_col='Lineage',
        title='Top Stimuli Per Lineage',
        filter_values={"Lineage": get_top_n_lineages(data, 3),
                       "RankWithinLineage": range(1, 21)}  # only show top 20 per lineage
        # save_path=f"{context.twodvsthreed_plots_dir}/texture_by_lightness.png"
    )

    # Create and run pipeline with aggregated data
    pipeline = create_pipeline().then(visualize_module).build()
    result = pipeline.run(data)

    # # Group by StimId and aggregate
    # data_for_stim_ids = data.groupby('StimSpecId').agg({
    #     'Lineage': 'first',
    #     'StimType': 'first',
    #     'ThumbnailPath': 'first',
    #     'GA_Response': 'mean',
    # }).reset_index()
    #
    # # Rename the response column
    # data_for_stim_ids = data_for_stim_ids.rename(columns={'Cluster Response': 'Average Response'})
    #
    # print(data_for_stim_ids.to_string())
    #
    # # Convert DataFrame to list of dicts for plotting
    # stimuli_list = []
    # for _, row in data_for_stim_ids.iterrows():
    #
    #     stim = {
    #         'stim_id': row['StimSpecId'],
    #         'response': row['GA_Response'],
    #         'lineage_id': row['Lineage'],
    #         'path': row['ThumbnailPath']
    #     }
    #
    #     if stim['path'] is not None:
    #         stimuli_list.append(stim)
    #
    # # Create and save plot
    # fig = plot_top_n_stimuli(stimuli_list, n=20)

    # plt.savefig(f"{context.plots_dir}/top_responses.png")
    plt.show()


def compile_data(conn: Connection) -> pd.DataFrame:
    collector = TaskIdCollector(conn)
    task_ids = collector.collect_task_ids()
    response_processor = context.ga_config.make_response_processor()
    cluster_combination_strategy = response_processor.cluster_combination_strategy
    parser = MultiFileParser(to_cache=True, cache_dir=context.ga_parsed_spikes_path)
    mstick_spec_data_source = StimSpecDataField(conn)

    fields = CachedTaskFieldList()
    fields.append(StimSpecIdField(conn))
    fields.append(LineageField(conn))
    fields.append(RegimeScoreField(conn))
    fields.append(StimTypeField(conn))
    fields.append(StimPathField(conn))
    fields.append(ThumbnailField(conn))
    fields.append(GAResponseField(conn))
    fields.append(ClusterResponseField(conn, cluster_combination_strategy))
    fields.append(IntanSpikesByChannelField(conn, parser, task_ids, context.ga_intan_path))
    fields.append(EpochStartStopTimesField(conn, parser, task_ids, context.ga_intan_path))
    fields.append(ShaftField(conn, mstick_spec_data_source))
    fields.append(TerminationField(conn, mstick_spec_data_source))
    fields.append(JunctionField(conn, mstick_spec_data_source))

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
                    fontsize=5, color='white',
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
