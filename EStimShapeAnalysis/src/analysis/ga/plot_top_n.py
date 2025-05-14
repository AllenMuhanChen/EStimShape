from __future__ import annotations

import pandas as pd
from matplotlib import pyplot as plt

from clat.compile.task.cached_task_fields import CachedTaskFieldList
from clat.compile.task.classic_database_task_fields import StimSpecIdField
from clat.compile.task.compile_task_id import TaskIdCollector
from clat.pipeline.pipeline_base_classes import create_pipeline
from clat.util.connection import Connection
from src.analysis import Analysis
from src.analysis.fields.cached_task_fields import StimTypeField, StimPathField, ThumbnailField, ClusterResponseField
from src.analysis.fields.matchstick_fields import ShaftField, TerminationField, JunctionField, StimSpecDataField
from src.analysis.ga.cached_ga_fields import LineageField, GAResponseField, RegimeScoreField, GenIdField
from src.analysis.isogabor.old_isogabor_analysis import IntanSpikesByChannelField, EpochStartStopTimesField, \
    IntanSpikeRateByChannelField
from src.analysis.modules.grouped_stims_by_response import create_grouped_stimuli_module
from src.intan.MultiFileParser import MultiFileParser
from src.pga.mock.mock_rwa_analysis import condition_spherical_angles, hemisphericalize_orientation
from src.repository.export_to_repository import export_to_repository, read_session_id_from_db_name
from src.repository.import_from_repository import import_from_repository
from src.startup import context


def main():
    channel = "A-011"

    # compiled_data = compile()
    analysis = PlotTopNAnalysis()

    compiled_data = None
    session_id, _ = read_session_id_from_db_name(context.ga_database)
    session_id = "250425_0"
    channel = "A-017"
    analysis.run(session_id, "raw", channel, compiled_data=compiled_data)


class PlotTopNAnalysis(Analysis):

    def analyze(self, channel, compiled_data: pd.DataFrame = None):
        if compiled_data is None:
            compiled_data = import_from_repository(
                self.session_id,
                "ga",
                "GAStimInfo",
                self.response_table
            )
        # Break apart the response rate by channel
        compiled_data = add_lineage_rank_to_df(compiled_data, self.spike_rates_col, channel)

        visualize_module = create_grouped_stimuli_module(
            response_rate_col=self.spike_rates_col,
            response_rate_key=channel,
            path_col='ThumbnailPath',
            col_col='RankWithinLineage',
            row_col='Lineage',
            title='Top Stimuli Per Lineage',
            filter_values={"Lineage": get_top_n_lineages(compiled_data, 3),
                           "RankWithinLineage": range(1, 21)},  # only show top 20 per lineage
            save_path=f"{self.save_path}/{channel}: plot_top_n.png",
            publish_mode=True,
            subplot_spacing=(20, 0),
        )

        # Create and run pipeline with aggregated data
        pipeline = create_pipeline().then(visualize_module).build()
        result = pipeline.run(compiled_data)

        plt.show()

    def compile_and_export(self):
        compile_and_export()

    def compile(self):
        compile()


def add_lineage_rank_to_df(compiled_data, spike_rates_col, channel):
    compiled_data['Spike Rate'] = compiled_data[spike_rates_col].apply(lambda x: x[channel] if channel in x else 0)
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


def compile_and_export():
    # Setting up connection and time frame to analyse in
    data = compile()
    export_to_repository(data, context.ga_database, "ga",
                         stim_info_table="GAStimInfo",
                         stim_info_columns=[
                             "Lineage",
                             "RegimeScore",
                             "StimType",
                             "StimPath",
                             "ThumbnailPath",
                             "GA Response",
                             "Cluster Response",
                             "Shaft",
                             "Termination",
                             "Junction"
                         ])
    return data


def compile():
    conn = Connection(context.ga_database)
    # Collect data and condition it
    data_for_all_tasks = compile_data(conn)
    data = clean_ga_data(data_for_all_tasks)
    data = condition_spherical_angles(data)
    data = hemisphericalize_orientation(data)
    return data


def compile_data(conn: Connection) -> pd.DataFrame:
    collector = TaskIdCollector(conn)
    task_ids = collector.collect_task_ids()
    response_processor = context.ga_config.make_response_processor()
    cluster_combination_strategy = response_processor.cluster_combination_strategy
    parser = MultiFileParser(to_cache=True, cache_dir=context.ga_parsed_spikes_path)
    mstick_spec_data_source = StimSpecDataField(conn)

    fields = CachedTaskFieldList()
    fields.append(StimSpecIdField(conn))
    fields.append(LineageField(conn))
    fields.append(GenIdField(conn))
    fields.append(RegimeScoreField(conn))
    fields.append(StimTypeField(conn))
    fields.append(StimPathField(conn))
    fields.append(ThumbnailField(conn))
    fields.append(GAResponseField(conn))
    fields.append(ClusterResponseField(conn, cluster_combination_strategy))
    fields.append(IntanSpikesByChannelField(conn, parser, task_ids, context.ga_intan_path))
    fields.append(IntanSpikeRateByChannelField(conn, parser, task_ids, context.ga_intan_path))
    fields.append(EpochStartStopTimesField(conn, parser, task_ids, context.ga_intan_path))
    fields.append(ShaftField(conn, mstick_spec_data_source))
    fields.append(TerminationField(conn, mstick_spec_data_source))
    fields.append(JunctionField(conn, mstick_spec_data_source))

    data = fields.to_data(task_ids)
    return data


def get_top_n_lineages(data, n):
    length_for_lineages = data.groupby("Lineage")["RegimeScore"].size()
    top_n_lineages = length_for_lineages.nlargest(n).index
    return list(top_n_lineages)


if __name__ == "__main__":
    main()


def clean_ga_data(data_for_all_tasks):
    # Remove trials with no response
    data_for_all_tasks = data_for_all_tasks[data_for_all_tasks['GA Response'].notna()]
    # Remove NaNs
    data_for_all_tasks = data_for_all_tasks[data_for_all_tasks['StimSpecId'].notna()]
    # Remove Catch
    data_for_all_tasks = data_for_all_tasks[data_for_all_tasks['ThumbnailPath'].apply(lambda x: x is not None)]
    return data_for_all_tasks
