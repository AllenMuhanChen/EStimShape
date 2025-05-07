from matplotlib import pyplot as plt

from clat.pipeline.pipeline_base_classes import create_pipeline, create_branch
from src.analysis.ga.plot_top_n import get_top_n_lineages

from src.analysis.modules.grouped_rasters import create_grouped_raster_module
from src.analysis.modules.grouped_stims_by_response import create_grouped_stimuli_module
from src.repository.import_from_repository import import_from_repository
from src.sort.export_sort_to_repository import export_sorted_spikes
from src.startup import context


def main():
    # INPUTS #
    session_name = '250427_0'
    unit = 'A-018_Unit 3'
    label = None
    new_spikes = False
    ##########
    save_path = f"/home/r2_allen/Documents/EStimShape/allen_sort_{session_name}/plots"
    if label:
        unit = f"{label}_{unit}"

    if new_spikes:
        export_sorted_spikes(session_name, label)

    analyse_isogabor(session_name, unit,save_path)
    # analyse_plot_top_n(session_name, unit)
    analyse_2dvs3d(session_name, unit, save_path)
    plt.show()


def analyse_2dvs3d(session_name, unit, save_path):
    data_for_plotting = import_from_repository(
        session_name,
        "ga",
        "2Dvs3DStimInfo",
        "WindowSortedResponses"
    )
    # unit = "Channel.A_031_Unit 2"
    visualize_module = create_grouped_stimuli_module(
        # response_col='Window Sort Spike Rates By Unit',
        response_rate_col='Response Rate by unit',
        response_rate_key=unit,
        path_col='ThumbnailPath',
        # response_key=("%s" % unit),
        col_col='TestId',
        row_col='TestType',
        title=f'2D vs 3D Test: {unit}',
        save_path=f"{save_path}/2D vs 3D Test: {unit}.png",
    )
    # Create and run pipeline with aggregated data
    plot_branch = create_branch().then(visualize_module)
    pipeline = create_pipeline().make_branch(
        plot_branch
    ).build()
    result = pipeline.run(data_for_plotting)


def analyse_plot_top_n(session_name, unit, save_path):
    data = import_from_repository(
        session_name,
        "ga",
        "GAStimInfo",
        "WindowSortedResponses"
    )
    print(data.head())
    # Break apart the response rate by channel
    data['Response Rate'] = data['Response Rate by unit'].apply(lambda x: x[unit])
    # Calculate average response rate for each StimSpecId within each Lineage
    avg_response = data.groupby(['Lineage', 'StimSpecId'])['Response Rate'].mean().reset_index()
    avg_response.rename(columns={'Response Rate': 'Avg Response Rate'}, inplace=True)
    # Rank the averages within each Lineage
    avg_response['RankWithinLineage'] = avg_response.groupby('Lineage')['Avg Response Rate'].rank(ascending=False,
                                                                                                  method='first')
    # Merge the ranks back to the original dataframe
    data = data.merge(avg_response[['Lineage', 'StimSpecId', 'RankWithinLineage']], on=['Lineage', 'StimSpecId'],
                      how='left')
    visualize_module = create_grouped_stimuli_module(
        response_rate_col='Response Rate',
        # response_rate_key='A-018',
        path_col='ThumbnailPath',
        col_col='RankWithinLineage',
        row_col='Lineage',
        title='Top Stimuli Per Lineage',
        filter_values={"Lineage": get_top_n_lineages(data, 3),
                       "RankWithinLineage": range(1, 21)}, # only show top 20 per lineage
        save_path=f"{save_path}/top_n: {unit}.png",
    )
    # Create and run pipeline with aggregated data
    pipeline = create_pipeline().then(visualize_module).build()
    result = pipeline.run(data)


def analyse_isogabor(session_name, unit, save_path):
    imported_data = import_from_repository(
        session_name,
        'isogabor',
        'IsoGaborStimInfo',
        'WindowSortedResponses')

    grouped_raster_module = create_grouped_raster_module(
        primary_group_col='Type',
        secondary_group_col='Frequency',
        spike_data_col='Spikes by unit',
        # spike_data_col_key= "A-016",
        # spike_data_col='Window Sort Spikes By Unit',
        spike_data_col_key=unit,
        filter_values={
            'Type': ['Red', 'Green', 'Cyan', 'Orange', 'RedGreen', 'CyanOrange']
        },
        title=f"Color Experiment: {unit}",
        save_path=f"{save_path}/color_experiment_{unit}.png",
    )
    # Create a simple pipeline
    pipeline = create_pipeline().then(grouped_raster_module).build()
    # Run the pipeline
    result = pipeline.run(imported_data)


if __name__ == "__main__":
    main()