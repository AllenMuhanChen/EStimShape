import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.gridspec import GridSpec
from typing import Dict, List, Any
from clat.util.connection import Connection
from clat.compile.tstamp.trial_tstamp_collector import TrialCollector
from clat.compile.task.compile_task_id import TaskIdCollector
from src.analysis.grouped_rasters import GroupedRasterInputHandler, GroupedRasterPlotter, GroupedRasterOutput, \
    create_grouped_raster_module
from src.intan.MultiFileParser import MultiFileParser
from src.startup import context
from src.analysis.isogabor.isogabor_analysis import TypeField, FrequencyField, IntanSpikesByChannelField
# Import our pipeline framework
from clat.pipeline.pipeline_base_classes import (
    InputHandler, ComputationModule, OutputHandler, create_pipeline, AnalysisModuleFactory
)


def main():
    # ----------------
    # STEP 1: Compile data
    # ----------------
    conn = Connection(context.isogabor_database)
    trial_collector = TrialCollector(conn)
    trial_tstamps = trial_collector.collect_trials()
    compiled_data = compile_data(conn, trial_tstamps)
    #filter out trials where Spikes by Channel is empty
    compiled_data = compiled_data[compiled_data['Spikes by Channel'].notnull()]

    # ----------------
    # STEP 2: Create and run the analysis pipeline
    # ----------------
    # For the isochromatic/isoluminant example:
    grouped_raster_module = create_grouped_raster_module(
        primary_group_col='Type',
        secondary_group_col='Frequency',
        spike_data_col='Spikes by Channel',
        filter_values={
            'Type': ['Red', 'Green', 'Cyan', 'Blue', 'RedGreen', 'CyanOrange']
        },
        save_path=None
    )

    # Create a simple pipeline
    pipeline = create_pipeline().then(grouped_raster_module).build()

    # Run the pipeline
    result = pipeline.run(compiled_data)

    # Show the figure
    plt.show()

    return result


def compile_data(conn, trial_tstamps):
    from clat.compile.tstamp.cached_tstamp_fields import CachedFieldList
    from clat.compile.tstamp.classic_database_tstamp_fields import StimIdField
    from clat.compile.tstamp.classic_database_tstamp_fields import TaskIdField

    # Import your field classes

    # Set up parser
    task_ids = TaskIdCollector(conn).collect_task_ids()
    parser = MultiFileParser(to_cache=True, cache_dir=context.isogabor_parsed_spikes_path)

    # Create fields list
    fields = CachedFieldList()
    fields.append(TaskIdField(conn))
    fields.append(StimIdField(conn))
    fields.append(TypeField(conn))
    fields.append(FrequencyField(conn))
    fields.append(IntanSpikesByChannelField(conn, parser, task_ids, context.isogabor_intan_path))

    # Compile data
    data = fields.to_data(trial_tstamps)
    return data


if __name__ == "__main__":
    main()
