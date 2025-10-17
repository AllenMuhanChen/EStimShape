import matplotlib.pyplot as plt
import pandas as pd

from clat.compile.task.cached_task_fields import CachedTaskFieldList
from clat.compile.task.classic_database_task_fields import StimSpecIdField
from clat.util.connection import Connection
from clat.compile.task.compile_task_id import TaskIdCollector
from src.analysis import Analysis
from src.analysis.isogabor.frequency_response import create_frequency_response_module
from src.analysis.isogabor.isogabor_index import create_isochromatic_index_module
from src.analysis.isogabor.preferred_frequency import create_preferred_frequency_module
from src.analysis.modules.matplotlib.grouped_rasters_matplotlib import create_grouped_raster_module
from src.analysis.modules.grouped_rsth import create_psth_module

from src.intan.MultiFileParser import MultiFileParser
from src.repository.import_from_repository import import_from_repository
from src.startup import context
from src.analysis.isogabor.old_isogabor_analysis import TypeField, FrequencyField, IntanSpikesByChannelField, \
    EpochStartStopTimesField, IsoTypeField, IntanSpikeRateByChannelField

# Import our pipeline framework
from clat.pipeline.pipeline_base_classes import (
    create_pipeline, create_branch, AnalysisModuleFactory
)
from src.repository.export_to_repository import export_to_repository


def main():
    # channel = "A-011"
    # session_id, _ = read_session_id_from_db_name(context.isogabor_database)
    compiled_data = compile()

    session_id = "251016_0"
    channel = "A-004"
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

        # CALCULATE INDEX
        index_module = create_isochromatic_index_module(channel=channel, session_id=self.session_id, spike_data_col=self.spike_rates_col)

        # ----------------
        # STEP 1: Create raster plot modules
        # ----------------
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
            title=f"Color Experiment by Type: {channel}",
            save_path=f"{self.save_path}/{channel}: color_experiment_by_isotype.png",
        )

        # ----------------
        # STEP 2: Create PSTH module
        # ----------------
        # Define color scheme for PSTH plots
        color_map = {
            'Red': 'red',
            'Green': 'green',
            'RedGreen': 'darkred',
            'Cyan': 'cyan',
            'Orange': 'orange',
            'CyanOrange': 'teal'
        }

        # Explicitly group the color types into two columns
        column_groups = {
            0: ['Red', 'Green', 'RedGreen'],  # Left column: warm colors
            1: ['Cyan', 'Orange', 'CyanOrange']  # Right column: cool colors
        }

        # Define column titles
        column_titles = [
            "Red / Green",
            "Cyan / Orange"
        ]

        # Create the PSTH module with explicit column grouping

        psth_module = create_psth_module(
            primary_group_col='Type',
            secondary_group_col='Frequency',
            filter_values={
                'Type': ['Red', 'Green', 'Cyan', 'Orange', 'RedGreen', 'CyanOrange']
            },
            spike_data_col=self.spike_tstamps_col,
            spike_data_col_key=channel,
            time_window=(-0.2, 0.5),
            bin_size=0.025,
            column_groups=column_groups,  # Specify explicit column grouping
            colors=color_map,
            show_std=False,  # Set to True if you want to show standard deviation
            title=f"Luminance vs Chromatic Contrast",
            col_titles=column_titles,
            row_suffix="(cycles/°)",
            save_path=f"{self.save_path}/{channel}: color_experiment_psth.png",
            include_row_labels=True,
            cell_size=(600, 300),
        )

        freq_response_module = create_frequency_response_module(
            channel=channel,
            spike_data_col=self.spike_rates_col,
            filter_values={
                'Type': ['Red', 'Green', 'Cyan', 'Orange', 'RedGreen', 'CyanOrange']
            },
            title="Frequency Tuning Curves",
            save_path=f"{self.save_path}/{channel}: frequency_response.png",
            colors=color_map
        )


        # ----------------
        # STEP 3: Create and run the pipeline
        # ----------------

        raster_branch = create_branch().then(grouped_raster_module)
        raster_by_isotype_branch = create_branch().then(grouped_raster_by_isotype_module)
        psth_branch = create_branch().then(psth_module)
        freq_response_branch = create_branch().then(freq_response_module)
        index_branch = create_branch().then(index_module)

        pipeline = create_pipeline().make_branch(
            raster_branch,
            raster_by_isotype_branch,
            psth_branch,
            freq_response_branch,
            index_branch
        ).build()

        # Run the pipeline
        result = pipeline.run(compiled_data)

        plt.show()
        return result

    def compile_and_export(self):
        compile_and_export()

    def compile(self):
        compile()


class IsochromaticIndexAnalysis(IsogaborAnalysis):

    def analyze(self, channel, compiled_data: pd.DataFrame = None):
        if compiled_data is None:
            compiled_data = import_from_repository(
                self.session_id,
                'isogabor',
                'IsoGaborStimInfo',
                self.response_table,
            )

        # CALCULATE INDEX
        index_module = create_isochromatic_index_module(channel=channel, session_id=self.session_id,
                                                        spike_data_col=self.spike_rates_col)

        pref_freq_module = create_preferred_frequency_module(
            channel=channel,
            session_id=self.session_id,
            spike_data_col=self.spike_rates_col,
            filter_values={
                'Type': ['Red', 'Green', 'Cyan', 'Orange', 'RedGreen', 'CyanOrange']
            }
        )
        index_branch = create_branch().then(index_module)
        pref_freq_branch = create_branch().then(pref_freq_module)

        pipeline = create_pipeline().make_branch(index_branch, pref_freq_branch).build()

        result = pipeline.run(compiled_data)
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