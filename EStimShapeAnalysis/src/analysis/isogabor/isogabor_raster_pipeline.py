import matplotlib.pyplot as plt

from clat.compile.task.cached_task_fields import CachedTaskFieldList
from clat.compile.task.classic_database_task_fields import StimSpecIdField
from clat.util.connection import Connection
from clat.compile.task.compile_task_id import TaskIdCollector
from src.analysis.modules.grouped_rasters import create_grouped_raster_module
from src.intan.MultiFileParser import MultiFileParser
from src.repository.import_from_repository import import_from_repository
from src.startup import context
from src.analysis.isogabor.isogabor_analysis import TypeField, FrequencyField, IntanSpikesByChannelField, \
    EpochStartStopTimesField
# Import our pipeline framework
from clat.pipeline.pipeline_base_classes import (
    create_pipeline
)
from src.repository.export_to_repository import export_to_repository


def main():
    # ----------------
    # STEP 1: Compile data
    # ----------------
    conn = Connection(context.isogabor_database)
    compiled_data = compile_data(conn)
    #filter out trials where Spikes by Channel is empty
    compiled_data = compiled_data[compiled_data['Spikes by Channel'].notnull()]

    export_to_repository(compiled_data, context.isogabor_database, "isogabor",
                         stim_info_table="IsoGaborStimInfo",
                         stim_info_columns=['Type', 'Frequency'])


    imported_data = import_from_repository(
        '250506_0',
        'isogabor',
        'IsoGaborStimInfo',
        'RawSpikeResponses',
    )
    print(imported_data.head())

    # ----------------
    # STEP 2: Create and run the analysis pipeline
    # ----------------
    # For the isochromatic/isoluminant example:
    channel = "A-020"
    grouped_raster_module = create_grouped_raster_module(
        primary_group_col='Type',
        secondary_group_col='Frequency',
        spike_data_col= 'Spikes by channel',
        spike_data_col_key=channel,
        filter_values={
            'Type': ['Red', 'Green', 'Cyan', 'Orange', 'RedGreen', 'CyanOrange']
        },
        title=f"Color Experiment: {channel}",
        save_path=f"{context.isogabor_plot_path}/color_experiment_{channel}.png",
    )

    # Create a simple pipeline
    pipeline = create_pipeline().then(grouped_raster_module).build()

    # Run the pipeline
    result = pipeline.run(imported_data)

    # Show the figure
    plt.show()

    return result


def compile_data(conn):
    # Set up parser
    task_ids = TaskIdCollector(conn).collect_task_ids()
    parser = MultiFileParser(to_cache=True, cache_dir=context.isogabor_parsed_spikes_path)

    # Create fields list
    fields = CachedTaskFieldList()
    fields.append(StimSpecIdField(conn))
    fields.append(TypeField(conn))
    fields.append(FrequencyField(conn))
    fields.append(IntanSpikesByChannelField(conn, parser, task_ids, context.isogabor_intan_path))
    fields.append(EpochStartStopTimesField(conn, parser, task_ids, context.isogabor_intan_path))
    # fields.append(WindowSortSpikesByUnitField(conn, parser, task_ids, context.isogabor_intan_path, "/home/r2_allen/Documents/EStimShape/allen_sort_250421_0/sorted_spikes.pkl"))
    # Compile data
    data = fields.to_data(task_ids)
    print(data.to_string())
    return data


if __name__ == "__main__":
    main()
