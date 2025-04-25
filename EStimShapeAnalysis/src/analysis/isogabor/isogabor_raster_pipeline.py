import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.gridspec import GridSpec
from typing import Dict, List, Any

from clat.compile.task.cached_task_fields import CachedTaskFieldList
from clat.compile.task.classic_database_task_fields import StimSpecIdField
from clat.util.connection import Connection
from clat.compile.tstamp.trial_tstamp_collector import TrialCollector
from clat.compile.task.compile_task_id import TaskIdCollector
from src.analysis.grouped_rasters import GroupedRasterInputHandler, GroupedRasterPlotter, GroupedRasterOutput, \
    create_grouped_raster_module
from src.intan.MultiFileParser import MultiFileParser
from src.startup import context
from src.analysis.isogabor.isogabor_analysis import TypeField, FrequencyField, IntanSpikesByChannelField, \
    EpochStartStopTimesField, WindowSortSpikesByUnitField
# Import our pipeline framework
from clat.pipeline.pipeline_base_classes import (
    InputHandler, ComputationModule, OutputHandler, create_pipeline, AnalysisModuleFactory
)


def main():
    # ----------------
    # STEP 1: Compile data
    # ----------------
    conn = Connection(context.isogabor_database)
    compiled_data = compile_data(conn)
    #filter out trials where Spikes by Channel is empty
    compiled_data = compiled_data[compiled_data['Spikes by Channel'].notnull()]

    # ----------------
    # STEP 2: Create and run the analysis pipeline
    # ----------------
    # For the isochromatic/isoluminant example:
    unit = 'Channel.A_031_Unit 2'
    grouped_raster_module = create_grouped_raster_module(
        primary_group_col='Type',
        secondary_group_col='Frequency',
        # spike_data_col= 'Spikes by Channel',
        # spike_data_col_key= "A-016",
        spike_data_col='Window Sort Spikes By Unit',
        spike_data_col_key=('%s' % unit),
        filter_values={
            'Type': ['Red', 'Green', 'Cyan', 'Orange', 'RedGreen', 'CyanOrange']
        },
        title=f"Color Experiment: {unit}",
        save_path=f"{context.isogabor_plot_path}/color_experiment_{unit}.png",
    )

    # Create a simple pipeline
    pipeline = create_pipeline().then(grouped_raster_module).build()

    # Run the pipeline
    result = pipeline.run(compiled_data)

    # Show the figure
    plt.show()

    return result


def compile_data(conn):
    from clat.compile.tstamp.cached_tstamp_fields import CachedFieldList
    from clat.compile.tstamp.classic_database_tstamp_fields import StimIdField
    from clat.compile.tstamp.classic_database_tstamp_fields import TaskIdField

    # Import your field classes

    # Set up parser
    task_ids = TaskIdCollector(conn).collect_task_ids()
    parser = MultiFileParser(to_cache=True, cache_dir=context.isogabor_parsed_spikes_path)

    # Create fields list
    fields = CachedTaskFieldList()
    fields.append(StimSpecIdField(conn))
    fields.append(TypeField(conn))
    fields.append(FrequencyField(conn))
    fields.append(IntanSpikesByChannelField(conn, parser, task_ids, context.isogabor_intan_path))
    # fields.append(EpochStartStopTimesField(conn, parser, task_ids, context.isogabor_intan_path))
    fields.append(WindowSortSpikesByUnitField(conn, parser, task_ids, context.isogabor_intan_path, "/home/r2_allen/Documents/EStimShape/allen_sort_250421_0/sorted_spikes.pkl"))
    # Compile data
    data = fields.to_data(task_ids)
    print(data.to_string())
    return data


if __name__ == "__main__":
    main()
