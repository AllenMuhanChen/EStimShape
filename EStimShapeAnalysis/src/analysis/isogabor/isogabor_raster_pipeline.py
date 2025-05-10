import matplotlib.pyplot as plt
import pandas as pd

from clat.compile.task.cached_task_fields import CachedTaskFieldList
from clat.compile.task.classic_database_task_fields import StimSpecIdField
from clat.util.connection import Connection
from clat.compile.task.compile_task_id import TaskIdCollector
from src.analysis import Analysis
from src.analysis.isogabor.isogabor_psth import compute_and_plot_psth
from src.analysis.modules.grouped_rasters import create_grouped_raster_module
from src.intan.MultiFileParser import MultiFileParser
from src.repository.import_from_repository import import_from_repository
from src.startup import context
from src.analysis.isogabor.old_isogabor_analysis import TypeField, FrequencyField, IntanSpikesByChannelField, \
    EpochStartStopTimesField, IsoTypeField, IntanSpikeRateByChannelField
# Import our pipeline framework
from clat.pipeline.pipeline_base_classes import (
    create_pipeline, create_branch
)
from src.repository.export_to_repository import export_to_repository, read_session_id_from_db_name


def main():
    channel = "A-011"
    session_id, _ = read_session_id_from_db_name(context.isogabor_database)
    compiled_data = compile()

    analysis = IsogaborAnalysis()
    return analysis.run(session_id, "raw", channel, compiled_data=compiled_data)


class IsogaborAnalysis(Analysis):
    def analyze(self, channel, compiled_data: pd.DataFrame = None):
        if compiled_data is None:
            compiled_data = import_from_repository(
                self.session_id,
                'isogabor',
                'IsoGaborStimInfo',
                self.response_table,
            )
            print(compiled_data.columns)
            # ----------------
            # STEP 2: Create and run the analysis pipeline
            # ----------------
            # For the isochromatic/isoluminant example:

        grouped_raster_module = create_grouped_raster_module(
            primary_group_col='Type',
            secondary_group_col='Frequency',
            spike_data_col=self.spike_tstamps_col,
            spike_data_col_key=channel,
            filter_values={
                'Type': ['Red', 'Green', 'Cyan', 'Orange', 'RedGreen', 'CyanOrange']
            },
            title=f"Color Experiment: {channel}",
            save_path=f"{self.save_path}/{channel}: color_experiment.png",
        )
        grouped_raster_by_isotype_module = create_grouped_raster_module(
            primary_group_col='IsoType',
            secondary_group_col='Type',
            spike_data_col=self.spike_tstamps_col,
            spike_data_col_key=channel,
            filter_values={
                'Type': ['Red', 'Green', 'Cyan', 'Orange', 'RedGreen', 'CyanOrange']
            },
            title=f"Color Experiment: {channel}",
            save_path=f"{self.save_path}/{channel}: color_experiment_by_isotype{channel}.png",

        )
        # Create a simple pipeline
        raster_branch = create_branch().then(grouped_raster_module)
        raster_by_isotype_branch = create_branch().then(grouped_raster_by_isotype_module)
        pipeline = create_pipeline().make_branch(raster_branch, raster_by_isotype_branch).build()
        # Run the pipeline
        result = pipeline.run(compiled_data)
        # Show the figure

        # Calculate and plot PSTH
        psth_fig = compute_and_plot_psth(
            compiled_data=compiled_data,
            channel=channel,
            spike_tstamps_col=self.spike_tstamps_col,
            save_path=self.save_path.replace(".png", "_psth.png"),  # Add _psth suffix
            bin_size=0.025,  # 10ms bins
            time_window=(-0.2, 0.5),  # 0 to 500ms
            # frequency_to_include=frequencies
        )

        plt.show()
        return result

    def compile_and_export(self):
        compile_and_export()

    def compile(self):
        compile()



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
    fields.append(IntanSpikeRateByChannelField(conn, parser, task_ids, context.isogabor_intan_path))
    fields.append(EpochStartStopTimesField(conn, parser, task_ids, context.isogabor_intan_path))
    # fields.append(WindowSortSpikesByUnitField(conn, parser, task_ids, context.isogabor_intan_path, "/home/r2_allen/Documents/EStimShape/allen_sort_250421_0/sorted_spikes.pkl"))
    # Compile data
    data = fields.to_data(task_ids)

    # filter out trials where Spikes by Channel is empty
    data = data[data['Spikes by channel'].notnull()]
    return data


if __name__ == "__main__":
    main()
