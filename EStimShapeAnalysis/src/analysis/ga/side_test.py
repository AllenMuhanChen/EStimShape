import pandas as pd
from matplotlib import pyplot as plt

from clat.compile.task.cached_task_fields import CachedTaskFieldList
from clat.compile.task.classic_database_task_fields import StimSpecIdField
from clat.compile.task.compile_task_id import TaskIdCollector
from clat.pipeline.pipeline_base_classes import create_pipeline, create_branch
from clat.util.connection import Connection
from src.analysis.cached_task_fields import StimTypeField, StimPathField, ThumbnailField, ClusterResponseField
from src.analysis.ga.cached_ga_fields import LineageField, GAResponseField, ParentIdField
from src.analysis.grouped_stims_by_response import create_grouped_stimuli_module
from src.analysis.isogabor.isogabor_analysis import WindowSortSpikesByUnitField, WindowSortSpikesForUnitField, \
    WindowSortSpikeRatesByUnitField, IntanSpikesByChannelField, EpochStartStopTimesField
from src.intan.MultiFileParser import MultiFileParser
from src.repository.export_to_repository import export_to_repository
from src.repository.import_from_repository import import_from_repository
from src.startup import context


def main():
    conn = Connection(context.ga_database)

    data_for_all_tasks = compile_data(conn)

    data_for_all_tasks = clean_data(data_for_all_tasks)

    # print(data_for_all_tasks.to_string())

    data_for_plotting = organize_data(data_for_all_tasks)

    print(data_for_plotting.to_string())
    export_to_repository(data_for_plotting,
                         context.ga_database,
                         "ga",
                            stim_info_table="2Dvs3DStimInfo",
                            stim_info_columns=['Lineage', 'StimType','StimPath','ThumbnailPath', 'GA Response', 'TestId', 'TestType'],
                         )

    data_for_plotting = import_from_repository(
        "250427_0",
        "ga",
        "2Dvs3DStimInfo",
        "RawSpikeResponses"
    )

    # unit = "Channel.A_031_Unit 2"
    visualize_module = create_grouped_stimuli_module(
        # response_col='Window Sort Spike Rates By Unit',
        response_col='Response Rate by channel',
        response_key="A-018",
        path_col='ThumbnailPath',
        # response_key=("%s" % unit),
        col_col='TestId',
        row_col='TestType',
        # title=f'2D vs 3D Test: {unit}',
        # save_path=f"{context.ga_plot_path}/2Dvs3D_Test_{unit}.png",
    )
    # Create and run pipeline with aggregated data
    plot_branch = create_branch().then(visualize_module)
    pipeline = create_pipeline().make_branch(
        plot_branch
    ).build()
    result = pipeline.run(data_for_plotting)

    # Show the figure
    plt.show()

    return result


def organize_data(data_for_stim_ids):
    data_for_side_test_stim = data_for_stim_ids[data_for_stim_ids['StimType'].str.contains("SIDETEST_2Dvs3D")]
    # print(data_for_side_tests.to_string())
    # Go through side test stimuli and add row for parent to dataframe if unique: add to a new dataframe with new column 'TestId'
    data_for_plotting = pd.DataFrame(columns=data_for_stim_ids.columns)
    for _, side_test_stim_row in data_for_side_test_stim.iterrows():
        parent_row = data_for_stim_ids[data_for_stim_ids['StimSpecId'] == side_test_stim_row['ParentId']]
        if not parent_row.empty:
            #

            # PARENT
            parent_row = parent_row.iloc[0]
            # check if parent already exists in data_for_side_tests
            parent_row['TestId'] = parent_row['StimSpecId']
            if "2D" in parent_row['StimType']:
                parent_row['TestType'] = "2D"
            else:
                parent_row['TestType'] = "3D"
            if not (data_for_plotting['StimSpecId'] == parent_row['StimSpecId']).any():
                data_for_plotting = pd.concat([data_for_plotting, parent_row.to_frame().T], ignore_index=True)

            new_row = side_test_stim_row.copy()
            new_row['TestId'] = parent_row['StimSpecId']
            if "2D" in parent_row['TestType']:
                new_row['TestType'] = "3D"
            else:
                new_row['TestType'] = "2D"
            data_for_plotting = pd.concat([data_for_plotting, new_row.to_frame().T], ignore_index=True)
    return data_for_plotting


def clean_data(data_for_all_tasks):
    # Remove trials with no response
    data_for_all_tasks = data_for_all_tasks[data_for_all_tasks['GA Response'].notna()]
    # Remove NaNs
    # data_for_all_tasks = data_for_all_tasks.dropna()
    # Remove Catch
    data_for_all_tasks = data_for_all_tasks[data_for_all_tasks['ThumbnailPath'].apply(lambda x: x != "None")]
    return data_for_all_tasks


def compile_data(conn: Connection) -> pd.DataFrame:
    collector = TaskIdCollector(conn)
    task_ids = collector.collect_task_ids()
    response_processor = context.ga_config.make_response_processor()
    cluster_combination_strategy = response_processor.cluster_combination_strategy
    # sort_dir = "/home/r2_allen/Documents/EStimShape/allen_sort_250421_0/sorted_spikes.pkl"
    parser = MultiFileParser(to_cache=True, cache_dir=context.ga_parsed_spikes_path)

    fields = CachedTaskFieldList()
    fields.append(StimSpecIdField(conn))
    fields.append(ParentIdField(conn))
    fields.append(LineageField(conn))
    fields.append(StimTypeField(conn))
    fields.append(StimPathField(conn))
    fields.append(ThumbnailField(conn))
    fields.append(IntanSpikesByChannelField(conn, parser, task_ids, context.ga_intan_path))
    fields.append(EpochStartStopTimesField(conn, parser, task_ids, context.ga_intan_path))
    fields.append(GAResponseField(conn))
    fields.append(ClusterResponseField(conn, cluster_combination_strategy),
    # fields.append(WindowSortSpikesByUnitField(conn, parser, task_ids, context.ga_intan_path,
    #                                           sort_dir))
    # fields.append(WindowSortSpikeRatesByUnitField(conn, parser, task_ids, context.ga_intan_path,
    #                                               sort_dir)
    )

    data = fields.to_data(task_ids)


    return data

if __name__ == "__main__":
    main()