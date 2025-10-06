from matplotlib import pyplot as plt

from clat.pipeline.pipeline_base_classes import create_pipeline

from clat.compile.task.cached_task_fields import CachedTaskFieldList
from clat.compile.task.classic_database_task_fields import StimSpecIdField
from clat.compile.task.compile_task_id import TaskIdCollector
from clat.util.connection import Connection
from src.analysis import Analysis
from src.analysis.fields.cached_task_fields import StimPathField
from src.analysis.isogabor.old_isogabor_analysis import IntanSpikesByChannelField, IntanSpikeRateByChannelField, \
    EpochStartStopTimesField
from src.analysis.lightness.lightness_analysis import StimGaIdField, TextureField, GAClusterResponseField
from src.analysis.modules.grouped_stims_by_response import create_grouped_stimuli_module
from src.analysis.modules.utils.sorting_utils import SpikeRateSortingUtils
from src.intan.MultiFileParser import MultiFileParser
from src.repository.export_to_repository import read_session_id_from_db_name, export_to_repository
from src.repository.import_from_repository import import_from_repository
from src.startup import context
from src.repository.export_to_repository_alchemy import export_to_repository_alchemy


def main():
    channel = 'A-013'
    session_id, _ = read_session_id_from_db_name(context.shuffle_database)
    analysis = ShuffleAnalysis()
    compiled_data = analysis.compile()
    # print(compiled_data.to_string())
    analysis.run(session_id, "raw", channel, compiled_data=compiled_data)


class ShuffleAnalysis(Analysis):
    def analyze(self, channel, compiled_data=None):
        if compiled_data is None:
            compiled_data = import_from_repository(
                self.session_id,
                'shuffle',
                'ShuffleStimInfo',
                self.response_table,
            )
        visualize_module = create_grouped_stimuli_module(
            response_rate_col=self.spike_rates_col,
            response_rate_key=channel,
            path_col='StimPath',
            col_col='ShuffleType',
            row_col='Texture',
            subgroup_col='StimGaId',
            title='Shuffle Analysis',
            filter_values={
                'ShuffleType': ['NONE', 'PIXEL', 'PHASE', 'MAGNITUDE']
            },
            sort_rules={
                "col": "StimGaId",
                "custom_func": SpikeRateSortingUtils.by_avg_value(
                    column=self.spike_rates_col,
                    comparison_col="StimSpecId"
                )
            },
            save_path=f"{self.save_path}/{channel}: shuffle_test.png",
            publish_mode=False,
            # include_labels_for={"col"}
        )
        pipeline = create_pipeline().then(visualize_module).build()
        result = pipeline.run(compiled_data)
        # Show the figure
        plt.show()
        return result

    def compile_and_export(self):
        data = self.compile()
        export_to_repository(data,
                             context.shuffle_database,
                             "shuffle",
                             stim_info_table="ShuffleStimInfo",
                             stim_info_columns=["StimSpecId",
                                                "StimGaId",
                                                "StimPath",
                                                "Texture",
                                                "ShuffleType",
                                                ]
                             )
        return data

    def compile(self):
        conn = Connection(context.shuffle_database)
        task_id_collector = TaskIdCollector(conn)
        task_ids = task_id_collector.collect_task_ids()
        if not task_ids:
            raise ValueError("No task IDs found in the database.")
        parser = MultiFileParser(to_cache=True, cache_dir=context.shuffle_parsed_spikes_path)
        intan_files_dir = context.shuffle_intan_path

        fields = CachedTaskFieldList()
        fields.append(StimSpecIdField(conn))
        fields.append(StimGaIdField(conn))
        fields.append(StimPathField(conn))
        fields.append(TextureField(conn))
        fields.append(ShuffleTypeField(conn))
        fields.append(IntanSpikesByChannelField(conn, parser, task_ids, intan_files_dir))
        fields.append(IntanSpikeRateByChannelField(conn, parser, task_ids, intan_files_dir))
        fields.append(EpochStartStopTimesField(conn, parser, task_ids, intan_files_dir))
        fields.append(IntanSpikeRateByChannelField(conn, parser, task_ids, intan_files_dir))
        fields.append(GAClusterResponseField(conn, parser, task_ids, intan_files_dir))

        raw_data = fields.to_data(task_ids)
        data = raw_data[raw_data['Spike Rate by channel'].notna()]
        data = data[data['StimSpecId'].notna()]
        return data


class ShuffleTypeField(StimSpecIdField):
    def get(self, task_id) -> str:
        stim_id = self.get_cached_super(task_id, StimSpecIdField)

        self.conn.execute("SELECT shuffle_type FROM StimShuffleType WHERE stim_id = %s",
                          params=(stim_id,))

        shuffle_type = self.conn.fetch_one()
        return shuffle_type

    def get_name(self):
        return "ShuffleType"


if __name__ == "__main__":
    main()
