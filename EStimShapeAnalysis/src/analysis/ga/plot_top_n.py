from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import pandas as pd
from matplotlib import pyplot as plt

from clat.compile.task.cached_task_fields import CachedTaskFieldList
from clat.compile.task.classic_database_task_fields import StimSpecIdField, TaskIdField
from clat.compile.task.compile_task_id import TaskIdCollector
from clat.pipeline.pipeline_base_classes import create_pipeline, create_branch
from clat.util.connection import Connection
from src.analysis import Analysis, get_all_channels
from src.analysis.live_analysis import LiveCompilable

from src.analysis.fields.cached_task_fields import StimTypeField, StimPathField, ThumbnailField, ClusterResponseField, \
    HypothesizedCompField
from src.analysis.fields.matchstick_fields import ShaftField, TerminationField, JunctionField, StimSpecDataField, \
    MassCenterField
from src.analysis.ga.cached_ga_fields import LineageField, GAResponseField, RegimeScoreField, GenIdField, ParentIdField
from src.analysis.ga.response_spec import ResponseSpec
from src.analysis.isogabor.old_isogabor_analysis import IntanSpikesByChannelField, EpochStartStopTimesField, \
    IntanSpikeRateByChannelField, MuaSpikesByChannelField, MuaSpikeRateByChannelField, \
    MuaEpochStartStopTimesField, MuaDbCachedParser
from src.analysis.lightness.lightness_analysis import TextureField, ColorField, AverageRGBField
from src.analysis.modules.grouped_stims_by_response import create_grouped_stimuli_module
from src.intan.MultiFileParser import MultiFileParser
from src.pga.mock.mock_rwa_analysis import condition_spherical_angles, hemisphericalize_orientation
from src.repository.export_to_repository import export_to_repository, read_session_id_and_date_from_db_name
from src.repository.good_channels import read_cluster_channels
from src.repository.import_from_repository import import_from_repository
from src.startup import context


def main():



    compiled_data = None
    analysis = PlotTopNAnalysis(use_baseline_correction=False, data_type="mua")
    # compiled_data = analysis.compile_and_export()
    session_id, _ = read_session_id_and_date_from_db_name(context.ga_database)
    channel = "Cluster"
    # channel = read_cluster_channels(session_id)
    # channel = "A-013"
    analysis.run(session_id, "mua", channel, compiled_data=compiled_data)

    


class PlotTopNAnalysis(Analysis, LiveCompilable):
    logging_path = context.logging_path
    # Repository experiment name this analysis exports under (experiment_id = f"{session_id}_{EXP_NAME}").
    EXP_NAME = "ga"

    def __init__(self, use_baseline_correction: bool = False, data_type: str = None):
        super().__init__(data_type=data_type)
        # Apply rank-based baseline correction to per-channel spike rates.
        # Silently a no-op in GA mode (the precomputed GA Response already
        # reflects whichever baseline policy the response processor used).
        # Subclasses just forward this through `super().__init__` to expose it.
        self.use_baseline_correction = use_baseline_correction

    def analyze(self, channel, compiled_data: pd.DataFrame = None):
        spec = ResponseSpec(channel, use_baseline_correction=self.use_baseline_correction)
        prepared = spec.apply(compiled_data, spike_rates_col=self.spike_rates_col)
        compiled_data = prepared.data

        if spec.use_ga_response:
            compiled_data = compiled_data.sort_values(
                by=['Lineage', prepared.response_col], ascending=[True, False]
            )
        # remove baseline
        compiled_data = compiled_data[compiled_data['StimType'] != 'BASELINE']

        compiled_data = rank_within_lineage(compiled_data, prepared.response_col)

        return self.analyze_one_channel(prepared, compiled_data)


    def import_data(self, compiled_data: pd.DataFrame) -> pd.DataFrame:
        # COMPILE DATA OR LOAD DATA
        if compiled_data is None:
            compiled_data = import_from_repository(
                self.session_id,
                "ga",
                "GAStimInfo",
                self.response_table,
                mua_method=self.mua_method if self.response_table == "MUASpikeResponses" else None,
            )

        return compiled_data

    def analyze_one_channel(self, prepared, compiled_data):
        visualize_module = create_grouped_stimuli_module(
            response_rate_col=prepared.response_col,
            response_rate_key=prepared.response_key,
            path_col='ThumbnailPath',
            col_col='RankWithinLineage',
            row_col='Lineage',
            title='Top Stimuli Per Lineage',
            filter_values={"Lineage": get_top_n_lineages(compiled_data, 4),
                           "RankWithinLineage": range(1, 21)},  # only show top 20 per lineage
            sort_rules={"RankWithinLineage": "ascending"},  # sort by rank within lineage
            save_path=f"{self.save_path}/{prepared.channel_label}{prepared.baseline_suffix}_plot_top_n.png",
            publish_mode=True,
            subplot_spacing=(20, 0),
            module_name="plot_top_n",
            border_width=50
        )
        pipeline = create_pipeline().then(visualize_module).build()
        result = pipeline.run(compiled_data)
        plt.show()
        return result

    def compile_and_export(self, task_ids: Optional[list] = None):
        data = self.compile(task_ids=task_ids)
        self.export(data)
        return data

    def export(self, data: pd.DataFrame) -> None:
        is_mua = self.response_table == "MUASpikeResponses"
        export_to_repository(data, context.ga_database, self.EXP_NAME,
                             stim_info_table="GAStimInfo",
                             response_table=self.response_table or "RawSpikeResponses",
                             mua_method=self.mua_method if is_mua else None,
                             stim_info_columns=[
                                 "Lineage",
                                 "RegimeScore",
                                 "GenId",
                                 "StimType",
                                 "StimPath",
                                 "ThumbnailPath",
                                 "GA Response",
                                 "Cluster Response",
                                 "Shaft",
                                 "Termination",
                                 "Junction",
                                 "ParentId",
                                 "MassCenter",
                                 "Texture",
                                 "AverageRGB"
                             ])

    def compile(self, task_ids: Optional[list] = None):
        conn = Connection(context.ga_database)
        data_for_all_tasks = self.compile_data(conn, task_ids=task_ids)
        data_for_all_tasks = self.clean_ga_data(data_for_all_tasks)
        return data_for_all_tasks

    # ---- LiveCompilable interface --------------------------------------
    def get_source_connection(self) -> Connection:
        return Connection(context.ga_database)

    def collect_task_ids(self, conn: Connection) -> list:
        return TaskIdCollector(conn).collect_task_ids()

    def get_exported_task_ids(self) -> set:
        """Task ids already exported to the repository for this session's GA experiment.

        Returns an empty set when the session/experiment isn't in the repository yet
        (e.g. the very first live poll of a brand-new session)."""
        session_id, _ = read_session_id_and_date_from_db_name(context.ga_database)
        experiment_id = f"{session_id}_{self.EXP_NAME}"
        repo_conn = Connection("allen_data_repository")
        repo_conn.execute(
            """
            SELECT tsm.task_id
            FROM TaskStimMapping tsm
            JOIN StimExperimentMapping sem ON tsm.stim_id = sem.stim_id
            WHERE sem.experiment_id = %s
            """,
            (experiment_id,),
        )
        return {int(row[0]) for row in repo_conn.fetch_all()}

    def compile_data(self, conn: Connection, task_ids: Optional[list] = None) -> pd.DataFrame:
        if task_ids is None:
            task_ids = self.collect_task_ids(conn)
        response_processor = context.ga_config.make_response_processor()
        cluster_combination_strategy = response_processor.cluster_combination_strategy
        mstick_spec_data_source = StimSpecDataField(conn)

        fields = CachedTaskFieldList()
        fields.append(TaskIdField(conn))
        fields.append(StimSpecIdField(conn))
        fields.append(ParentIdField(conn))
        fields.append(LineageField(conn))
        fields.append(GenIdField(conn))
        fields.append(RegimeScoreField(conn))
        fields.append(StimTypeField(conn))
        fields.append(StimPathField(conn))
        fields.append(ThumbnailField(conn))
        fields.append(GAResponseField(conn))
        fields.append(HypothesizedCompField(conn))
        fields.append(TextureField(conn))
        fields.append(AverageRGBField(conn))
        fields.append(ClusterResponseField(conn, cluster_combination_strategy))

        # Spike source: MUA (wideband, -k x MAD, block-of-N) vs spike.dat.
        is_mua = self.response_table == "MUASpikeResponses"
        if is_mua:
            from src.analysis.ga.baseline_spike_detection_comparison import (
                PeriodicBlockMUAParser, MadStrategy)
            wideband_parser = PeriodicBlockMUAParser(
                strategy=MadStrategy(threshold_mad=self.mua_k or 4.0),
                block_size=self.mua_block or 100,
                to_cache=True,
                cache_dir=os.path.join(context.ga_parsed_spikes_path, "mua_block_mad"),
            )
            # Reuse spikes the live GA parser already wrote to MUAChannelResponses;
            # only detect missing task_ids from wideband.
            mua_parser = MuaDbCachedParser(
                db_name=context.ga_database,
                mua_metric=self.mua_method or "mad_k4_block100",
                fallback_parser=wideband_parser,
            )
            fields.append(MuaSpikesByChannelField(conn, mua_parser, task_ids, context.ga_intan_path))
            fields.append(MuaSpikeRateByChannelField(conn, mua_parser, task_ids, context.ga_intan_path))
            fields.append(MuaEpochStartStopTimesField(conn, mua_parser, task_ids, context.ga_intan_path))
        else:
            parser = MultiFileParser(to_cache=True, cache_dir=context.ga_parsed_spikes_path)
            fields.append(IntanSpikesByChannelField(conn, parser, task_ids, context.ga_intan_path))
            fields.append(IntanSpikeRateByChannelField(conn, parser, task_ids, context.ga_intan_path))
            fields.append(EpochStartStopTimesField(conn, parser, task_ids, context.ga_intan_path))

        fields.append(ShaftField(conn, mstick_spec_data_source))
        fields.append(TerminationField(conn, mstick_spec_data_source))
        fields.append(JunctionField(conn, mstick_spec_data_source))
        fields.append(MassCenterField(conn, mstick_spec_data_source))

        data = fields.to_data(task_ids)
        if is_mua:
            # Rename the distinct MUA cache columns back to the standard names so
            # every downstream consumer (export, ResponseSpec, import) is uniform.
            data = data.rename(columns={
                "MUA Spikes by channel": "Spikes by channel",
                "MUA Spike Rate by channel": "Spike Rate by channel",
                "MUA Epoch": "Epoch",
            })
        return data
    @staticmethod
    def clean_ga_data(data_for_all_tasks):
        # Remove trials with no response
        data_for_all_tasks = data_for_all_tasks[data_for_all_tasks['GA Response'].notna()]
        # Remove NaNs
        data_for_all_tasks = data_for_all_tasks[data_for_all_tasks['StimSpecId'].notna()]
        # Remove Catch
        data_for_all_tasks = data_for_all_tasks[data_for_all_tasks['ThumbnailPath'].apply(lambda x: x is not None)]
        return data_for_all_tasks

def rank_within_lineage(compiled_data: pd.DataFrame, response_col: str) -> pd.DataFrame:
    """Add RankWithinLineage column based on the mean of `response_col` per (Lineage, StimSpecId).

    Assumes `response_col` is already a scalar column (e.g. produced by
    `ResponseSpec.apply`). Use this instead of `add_lineage_rank_to_df` when
    you've prepared a scalar response column upstream.
    """
    avg_response = (
        compiled_data.groupby(['Lineage', 'StimSpecId'])[response_col].mean().reset_index()
    )
    avg_response.rename(columns={response_col: 'Avg Response Rate'}, inplace=True)
    avg_response['RankWithinLineage'] = avg_response.groupby('Lineage')['Avg Response Rate'].rank(
        ascending=False, method='first'
    )
    return compiled_data.merge(
        avg_response[['Lineage', 'StimSpecId', 'RankWithinLineage']],
        on=['Lineage', 'StimSpecId'],
        how='left',
    )


def add_lineage_rank_to_df(compiled_data, spike_rates_col, channel):
    """
    Add ranking information based on spike rates within each lineage.

    Args:
        compiled_data: DataFrame with spike rate data
        spike_rates_col: Column name containing spike rate dictionaries
        channel: Either a single channel name (str) or list of channel names (List[str]).
                If list is provided, responses are summed across all specified channels.
    """
    # Handle single channel vs multiple channels
    if channel == "GA":
        pass
    elif isinstance(channel, list):
        # Sum responses from multiple channels
        def sum_channels(x):
            if not isinstance(x, dict):
                return 0
            total = 0
            for ch in channel:
                total += x.get(ch, 0)
            return total

        compiled_data['Spike Rate'] = compiled_data[spike_rates_col].apply(sum_channels)
    else:
        # Single channel extraction (original behavior)
        compiled_data['Spike Rate'] = compiled_data[spike_rates_col].apply(
            lambda x: x[channel] if isinstance(x, dict) and channel in x else 0
        )

    # Calculate average response rate for each StimSpecId within each Lineage
    avg_response = compiled_data.groupby(['Lineage', 'StimSpecId'])['Spike Rate'].mean().reset_index()
    avg_response.rename(columns={'Spike Rate': 'Avg Response Rate'}, inplace=True)
    # Rank the averages within each Lineage
    avg_response['RankWithinLineage'] = avg_response.groupby('Lineage')['Avg Response Rate'].rank(ascending=False,
                                                                                                  method='first')
    # Merge the ranks back to the original dataframe
    compiled_data = compiled_data.merge(avg_response[['Lineage', 'StimSpecId', 'RankWithinLineage']],
                                        on=['Lineage', 'StimSpecId'],
                                        how='left')
    return compiled_data


def get_top_n_lineages(data, n):
    length_for_lineages = data.groupby("Lineage")["RegimeScore"].size()
    top_n_lineages = length_for_lineages.nlargest(n).index
    return list(top_n_lineages)



if __name__ == "__main__":
    main()
