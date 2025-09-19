import matplotlib.pyplot as plt
import pandas as pd

from clat.compile.task.cached_task_fields import CachedTaskFieldList
from clat.compile.task.classic_database_task_fields import StimSpecIdField
from clat.util.connection import Connection
from clat.compile.task.compile_task_id import TaskIdCollector
from src.analysis import Analysis
from src.analysis.modules.grouped_rsth import create_psth_module
from src.analysis.modules.matplotlib.grouped_rasters_matplotlib import create_grouped_raster_module
from src.intan.MultiFileParser import MultiFileParser
from src.repository.import_from_repository import import_from_repository
from src.startup import context
from src.analysis.isogabor.old_isogabor_analysis import TypeField, IntanSpikesByChannelField, \
    EpochStartStopTimesField, MixedFrequencyField, MixedPhaseField, AlignedFrequencyField, AlignedPhaseField, \
    IntanSpikeRateByChannelField
# Import our pipeline framework
from clat.pipeline.pipeline_base_classes import (
    create_pipeline, create_branch
)
from src.repository.export_to_repository import export_to_repository, read_session_id_from_db_name


def main():
    channel = "A-029"
    compiled_data = compile_and_export()
    analysis = MixedGaborsAnalysis()
    # session_id, _ = read_session_id_from_db_name(context.isogabor_database)
    session_id = "250903_0"
    analysis.run(session_id, "raw", channel, compiled_data=compiled_data)


class MixedGaborsAnalysis(Analysis):
    def analyze(self, channel, compiled_data: pd.DataFrame = None):
        if compiled_data is None:
            compiled_data = import_from_repository(
                self.session_id,
                'isogabor',
                'IsoGaborStimInfo',
                self.response_table
            )

        grouped_raster_module_frequency = create_grouped_raster_module(
            primary_group_col='Aligned Frequency',
            secondary_group_col='Type',
            spike_data_col=self.spike_tstamps_col,
            spike_data_col_key=channel,
            filter_values={
                'Type': ['RedGreenMixed', 'CyanOrangeMixed']
            },
            title=f"Color Experiment: {channel}",
            save_path=f"{self.save_path}/{channel}: mixed_gabors.png",
        )

        psth_module = create_psth_module(
            primary_group_col='Mixed Frequency',
            secondary_group_col='Aligned Frequency',
            spike_data_col=self.spike_tstamps_col,
            spike_data_col_key=channel,
            time_window=(-0.2, 0.5),
            bin_size=0.025,
            save_path=f"{self.save_path}/{channel}: mixed_gabors_psth.png",
            cell_size=(600, 300),
            include_row_labels=True
        )
        # Create a simple pipeline
        frequency_branch = create_branch().then(grouped_raster_module_frequency)
        psth_branch = create_branch().then(psth_module)

        # phase_branch = create_branch().then(grouped_raster_module_phase)
        pipeline = create_pipeline().make_branch(frequency_branch, psth_branch).build()
        # Run the pipeline
        result = pipeline.run(compiled_data)
        # Show the figure
        plt.show()

    def compile_and_export(self):
        compile_and_export()

    def compile(self):
        compile()


def compile_and_export():
    compiled_data = compile()
    export_to_repository(compiled_data, context.isogabor_database, "isogabor",
                         stim_info_table="IsoGaborStimInfo",
                         stim_info_columns=['Type', 'Aligned Frequency', 'Mixed Frequency'])
    return compiled_data


def compile():
    conn = Connection(context.isogabor_database)
    compiled_data = collect_raw_data(conn)
    compiled_data = compiled_data[compiled_data['Spikes by channel'].notnull()]
    compiled_data = compiled_data[compiled_data['Mixed Frequency'].notnull()]
    return compiled_data


def collect_raw_data(conn):
    # Set up parser
    task_ids = TaskIdCollector(conn).collect_task_ids()
    parser = MultiFileParser(to_cache=True, cache_dir=context.isogabor_parsed_spikes_path)

    # Create fields list
    fields = CachedTaskFieldList()
    fields.append(StimSpecIdField(conn))
    fields.append(TypeField(conn))
    fields.append(MixedFrequencyField(conn))
    fields.append(MixedPhaseField(conn))
    fields.append(AlignedFrequencyField(conn))
    fields.append(AlignedPhaseField(conn))
    fields.append(IntanSpikesByChannelField(conn, parser, task_ids, context.isogabor_intan_path))
    fields.append(IntanSpikeRateByChannelField(conn, parser, task_ids, context.isogabor_intan_path))
    fields.append(EpochStartStopTimesField(conn, parser, task_ids, context.isogabor_intan_path))
    # fields.append(WindowSortSpikesByUnitField(conn, parser, task_ids, context.isogabor_intan_path, "/home/r2_allen/Documents/EStimShape/allen_sort_250421_0/sorted_spikes.pkl"))
    # Compile data
    data = fields.to_data(task_ids)
    print(data.to_string())
    return data


if __name__ == "__main__":
    main()
