import matplotlib.pyplot as plt
import pandas as pd

from clat.compile.task.cached_task_fields import CachedTaskFieldList
from clat.compile.task.classic_database_task_fields import StimSpecIdField
from clat.util.connection import Connection
from clat.compile.task.compile_task_id import TaskIdCollector
from src.analysis import parse_data_type
from src.analysis.modules.grouped_rasters import create_grouped_raster_module
from src.intan.MultiFileParser import MultiFileParser
from src.repository.import_from_repository import import_from_repository
from src.startup import context
from src.analysis.isogabor.old_isogabor_analysis import TypeField, FrequencyField, IntanSpikesByChannelField, \
    EpochStartStopTimesField, IsoTypeField, SpikeRateByChannelField
# Import our pipeline framework
from clat.pipeline.pipeline_base_classes import (
    create_pipeline, create_branch
)
from src.repository.export_to_repository import export_to_repository


def main():
    # ----------------
    # STEP 1: Compile data
    # ----------------
    compile_and_export()

    session_id = '250509_0'
    channel = "A-011"
    return analyze(channel, session_id)


def analyze(channel, data_type: str, session_id: str = None, compiled_data: pd.DataFrame = None):
    raw_save_dir = f"{context.isogabor_plot_path}"
    filename = f"color_experiment_{channel}.png"
    response_table, save_path, spike_tstamps_col, spike_rates_col = parse_data_type(data_type, session_id, filename, raw_save_dir)

    if compiled_data is None:
        compiled_data = import_from_repository(
            session_id,
            'isogabor',
            'IsoGaborStimInfo',
            response_table,
        )
        print(compiled_data.columns)
    # ----------------
    # STEP 2: Create and run the analysis pipeline
    # ----------------
    # For the isochromatic/isoluminant example:

    grouped_raster_module = create_grouped_raster_module(
        primary_group_col='Type',
        secondary_group_col='Frequency',
        spike_data_col=spike_tstamps_col,
        spike_data_col_key=channel,
        filter_values={
            'Type': ['Red', 'Green', 'Cyan', 'Orange', 'RedGreen', 'CyanOrange']
        },
        title=f"Color Experiment: {channel}",
        save_path=save_path,
    )
    grouped_raster_by_isotype_module = create_grouped_raster_module(
        primary_group_col='IsoType',
        secondary_group_col='Type',
        spike_data_col=spike_tstamps_col,
        spike_data_col_key=channel,
        filter_values={
            'Type': ['Red', 'Green', 'Cyan', 'Orange', 'RedGreen', 'CyanOrange']
        },
        title=f"Color Experiment: {channel}",
        save_path=f"{context.isogabor_plot_path}/color_experiment_by_isotype{channel}.png",

    )
    # Create a simple pipeline
    raster_branch = create_branch().then(grouped_raster_module)
    raster_by_isotype_branch = create_branch().then(grouped_raster_by_isotype_module)
    pipeline = create_pipeline().make_branch(raster_branch, raster_by_isotype_branch).build()
    # Run the pipeline
    result = pipeline.run(compiled_data)
    # Show the figure
    plt.show()
    return result


def compile_and_export():
    compiled_data = compile()

    export_to_repository(compiled_data, context.isogabor_database, "isogabor",
                         stim_info_table="IsoGaborStimInfo",
                         stim_info_columns=['Type', 'Frequency', 'IsoType'])


def compile():
    conn = Connection(context.isogabor_database)
    # Set up parser
    task_ids = TaskIdCollector(conn).collect_task_ids()
    parser = MultiFileParser(to_cache=True, cache_dir=context.isogabor_parsed_spikes_path)

    # Create fields list
    fields = CachedTaskFieldList()
    fields.append(StimSpecIdField(conn))
    fields.append(TypeField(conn))
    fields.append(FrequencyField(conn))
    fields.append(IsoTypeField(conn))
    fields.append(IntanSpikesByChannelField(conn, parser, task_ids, context.isogabor_intan_path))
    fields.append(SpikeRateByChannelField(conn, parser, task_ids, context.isogabor_intan_path))
    fields.append(EpochStartStopTimesField(conn, parser, task_ids, context.isogabor_intan_path))
    # fields.append(WindowSortSpikesByUnitField(conn, parser, task_ids, context.isogabor_intan_path, "/home/r2_allen/Documents/EStimShape/allen_sort_250421_0/sorted_spikes.pkl"))
    # Compile data
    data = fields.to_data(task_ids)

    # filter out trials where Spikes by Channel is empty
    data = data[data['Spikes by channel'].notnull()]
    return data


if __name__ == "__main__":
    main()
