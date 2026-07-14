import os

import matplotlib.pyplot as plt
import pandas as pd

from clat.compile.task.cached_task_fields import CachedTaskFieldList
from clat.compile.task.classic_database_task_fields import StimSpecIdField
from clat.util.connection import Connection
from clat.compile.task.compile_task_id import TaskIdCollector
from src.analysis import Analysis
from src.analysis.modules.grouped_rsth import create_psth_module
from src.analysis.modules.matplotlib.grouped_rasters_matplotlib import create_grouped_raster_module
from src.analysis.isogabor.mixed_gabors_index import create_alignment_suppression_index_module
from src.intan.MultiFileParser import MultiFileParser
from src.repository.import_from_repository import import_from_repository
from src.startup import context
from src.analysis.isogabor.old_isogabor_analysis import TypeField, IntanSpikesByChannelField, \
    EpochStartStopTimesField, MixedFrequencyField, MixedPhaseField, AlignedFrequencyField, AlignedPhaseField, \
    IntanSpikeRateByChannelField, MuaSpikesByChannelField, MuaSpikeRateByChannelField, MuaEpochStartStopTimesField, \
    MuaDbCachedParser
# Import our pipeline framework
from clat.pipeline.pipeline_base_classes import (
    create_pipeline, create_branch
)
from src.repository.export_to_repository import export_to_repository, read_session_id_and_date_from_db_name


def main():
    channel = "A-027"
    # data_type "mua" -> MUASpikeResponses (see Analysis._configure_data_type).
    # Use "raw" for the old spike.dat behaviour.
    data_type = "mua"
    analysis = MixedGaborsAnalysis(data_type=data_type)
    compiled_data = analysis.compile_and_export()
    # session_id, _ = read_session_id_from_db_name(context.isogabor_database)
    session_id = "260624_0"
    analysis.run(session_id, data_type, channel, compiled_data=compiled_data)


class MixedGaborsAnalysis(Analysis):
    def analyze(self, channel, compiled_data: pd.DataFrame = None):
        if compiled_data is None:
            compiled_data = import_from_repository(
                self.session_id,
                'isogabor',
                'IsoGaborStimInfo',
                self.response_table,
                mua_method=self.mua_method if self._is_mua() else None,
            )

        # CALCULATE INDEX: Alignment Suppression Index, one per luminance frequency.
        index_module = create_alignment_suppression_index_module(
            channel=channel,
            session_id=self.session_id,
            spike_data_col=self.spike_rates_col,
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
            save_path=f"{self.save_path}/{channel}_mixed_gabors.png",
        )

        psth_module = create_psth_module(
            primary_group_col='Mixed Frequency',
            secondary_group_col='Aligned Frequency',
            spike_data_col=self.spike_tstamps_col,
            spike_data_col_key=channel,
            time_window=(-0.2, 0.5),
            bin_size=0.025,
            save_path=f"{self.save_path}/{channel}_mixed_gabors_psth.png",
            cell_size=(600, 300),
            include_row_labels=True
        )
        # Create a simple pipeline
        index_branch = create_branch().then(index_module)
        frequency_branch = create_branch().then(grouped_raster_module_frequency)
        psth_branch = create_branch().then(psth_module)

        # phase_branch = create_branch().then(grouped_raster_module_phase)
        pipeline = create_pipeline().make_branch(
            index_branch, frequency_branch, psth_branch).build()
        # Run the pipeline
        result = pipeline.run(compiled_data)
        # Show the figure
        plt.show()
        return result

    def _is_mua(self):
        return self.response_table == "MUASpikeResponses"

    def compile_and_export(self):
        return compile_and_export(
            data_type='mua' if self._is_mua() else 'raw',
            mua_method=self.mua_method if self._is_mua() else None,
            mua_k=self.mua_k or 4.0, mua_block=self.mua_block or 100)

    def compile(self):
        return compile(
            data_type='mua' if self._is_mua() else 'raw',
            mua_method=self.mua_method if self._is_mua() else None,
            mua_k=self.mua_k or 4.0, mua_block=self.mua_block or 100)


def compile_and_export(data_type: str = 'raw', mua_method: str = None,
                       mua_k: float = 4.0, mua_block: int = 100):
    is_mua = data_type == 'mua' or mua_method is not None
    method = mua_method or (f"mad_k{mua_k:g}_block{mua_block}" if is_mua else None)
    compiled_data = compile(data_type=data_type, mua_method=method,
                            mua_k=mua_k, mua_block=mua_block)

    export_to_repository(compiled_data, context.isogabor_database, "isogabor",
                         stim_info_table="IsoGaborStimInfo",
                         stim_info_columns=['Type', 'Aligned Frequency', 'Mixed Frequency'],
                         response_table='MUASpikeResponses' if is_mua else 'RawSpikeResponses',
                         mua_method=method)
    return compiled_data


def compile(data_type: str = 'raw', mua_method: str = None,
            mua_k: float = 4.0, mua_block: int = 100):
    conn = Connection(context.isogabor_database)
    compiled_data = collect_raw_data(conn, data_type=data_type, mua_method=mua_method,
                                     mua_k=mua_k, mua_block=mua_block)
    compiled_data = compiled_data[compiled_data['Spikes by channel'].notnull()]
    compiled_data = compiled_data[compiled_data['Mixed Frequency'].notnull()]
    return compiled_data


def collect_raw_data(conn, data_type: str = 'raw', mua_method: str = None,
                     mua_k: float = 4.0, mua_block: int = 100):
    # Set up parser
    task_ids = TaskIdCollector(conn).collect_task_ids()

    # Create fields list
    fields = CachedTaskFieldList()
    fields.append(StimSpecIdField(conn))
    fields.append(TypeField(conn))
    fields.append(MixedFrequencyField(conn))
    fields.append(MixedPhaseField(conn))
    fields.append(AlignedFrequencyField(conn))
    fields.append(AlignedPhaseField(conn))

    # Spike source: MUA (wideband, -k x MAD, block-of-N) vs spike.dat.
    is_mua = data_type == 'mua' or mua_method is not None
    if is_mua:
        from src.analysis.ga.baseline_spike_detection_comparison import (
            PeriodicBlockMUAParser, MadStrategy)
        wideband_parser = PeriodicBlockMUAParser(
            strategy=MadStrategy(threshold_mad=mua_k), block_size=mua_block,
            to_cache=True,
            cache_dir=os.path.join(context.isogabor_parsed_spikes_path, "mua_block_mad"))
        # Reuse any spikes already stored in MUAChannelResponses; detect the rest.
        parser = MuaDbCachedParser(
            db_name=context.isogabor_database,
            mua_metric=mua_method or f"mad_k{mua_k:g}_block{mua_block}",
            fallback_parser=wideband_parser)
        fields.append(MuaSpikesByChannelField(conn, parser, task_ids, context.isogabor_intan_path))
        fields.append(MuaSpikeRateByChannelField(conn, parser, task_ids, context.isogabor_intan_path))
        fields.append(MuaEpochStartStopTimesField(conn, parser, task_ids, context.isogabor_intan_path))
    else:
        parser = MultiFileParser(to_cache=True, cache_dir=context.isogabor_parsed_spikes_path)
        fields.append(IntanSpikesByChannelField(conn, parser, task_ids, context.isogabor_intan_path))
        fields.append(IntanSpikeRateByChannelField(conn, parser, task_ids, context.isogabor_intan_path))
        fields.append(EpochStartStopTimesField(conn, parser, task_ids, context.isogabor_intan_path))

    # Compile data
    data = fields.to_data(task_ids)
    if is_mua:
        data = data.rename(columns={
            "MUA Spikes by channel": "Spikes by channel",
            "MUA Spike Rate by channel": "Spike Rate by channel",
            "MUA Epoch": "Epoch",
        })
    print(data.to_string())
    return data


if __name__ == "__main__":
    main()
