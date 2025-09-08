import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

from clat.compile.task.cached_task_fields import CachedTaskFieldList
from clat.compile.task.classic_database_task_fields import StimSpecIdField
# Import pipeline framework
from clat.util.connection import Connection
from clat.compile.task.compile_task_id import TaskIdCollector
from clat.pipeline.pipeline_base_classes import (
    create_pipeline
)
from src.analysis import Analysis
from src.analysis.fields.cached_task_fields import StimPathField, ThumbnailField
from src.analysis.modules.grouped_stims_by_response import create_grouped_stimuli_module

# Import custom modules
from src.intan.MultiFileParser import MultiFileParser
from src.repository.export_to_repository import export_to_repository, read_session_id_from_db_name
from src.repository.import_from_repository import import_from_repository
from src.startup import context
from src.analysis.isogabor.old_isogabor_analysis import IntanSpikesByChannelField, IntanSpikeRateByChannelField, \
    EpochStartStopTimesField
from src.analysis.modules.matplotlib.grouped_stims_by_response_matplotlib import create_grouped_stimuli_module_matplotlib


def main():
    """Main function to run the 2D vs 3D analysis pipeline."""

    channel = 'A-011'
    compiled_data = compile()
    analysis = LightnessAnalysis()
    session_id, _ = read_session_id_from_db_name(context.lightness_database)
    session_id = "250903_0"
    channel = "A-013"
    return analysis.run(session_id, "raw", channel, compiled_data=compiled_data)


class LightnessAnalysis(Analysis):

    def analyze(self, channel, compiled_data: pd.DataFrame = None):
        if compiled_data is None:
            compiled_data = import_from_repository(
                self.session_id,
                'lightness',
                'LightnessTestStimInfo',
                self.response_table
            )
        # Create Plotly visualization module
        visualize_module = create_grouped_stimuli_module(
            response_rate_col=self.spike_rates_col,
            response_rate_key=channel,
            path_col='ThumbnailPath',
            col_col='RGB',
            row_col='Texture',
            subgroup_col='StimGaId',
            filter_values={
                'Texture': ['SHADE', 'SPECULAR', '2D']
            },
            title='2D vs 3D Texture Response Analysis',
            save_path=f"{self.save_path}/{channel}: lightness_test.png",
            publish_mode=True,
            subplot_spacing=(20, 0),
        )

        # Create and run pipeline with aggregated data
        pipeline = create_pipeline().then(visualize_module).build()
        result = pipeline.run(compiled_data)
        # Show the figure
        plt.show()
        return result

    def compile_and_export(self):
        compile_and_export()

    def compile(self):
        compile()


def compile_and_export():
    data = compile()
    export_to_repository(data, context.lightness_database, "lightness",
                         stim_info_table="LightnessTestStimInfo",
                         stim_info_columns=[
                             'Type',
                             'RGB',
                             'Texture',
                             'StimGaId',
                             'StimPath',
                             'ThumbnailPath',
                             'GA Response',
                             'Cluster Response'
                         ])
    return data


def compile():
    conn = Connection(context.lightness_database)
    # Collect trials
    task_id_collector = TaskIdCollector(conn)
    task_ids = task_id_collector.collect_task_ids()
    if not task_ids:
        raise ValueError("No task IDs found in the database.")
    # Set up parser for spike data
    parser = MultiFileParser(to_cache=True, cache_dir=context.lightness_parsed_spikes_path)
    intan_files_dir = context.lightness_intan_path
    # Set up fields for data compilation
    fields = CachedTaskFieldList()
    fields.append(StimSpecIdField(conn))
    fields.append(StimGaIdField(conn))
    fields.append(StimPathField(conn))
    fields.append(ThumbnailField(conn))
    fields.append(TextureField(conn))
    fields.append(ColorField(conn))
    fields.append(TypeField(conn))
    fields.append(IntanSpikesByChannelField(conn, parser, task_ids, intan_files_dir))
    fields.append(IntanSpikeRateByChannelField(conn, parser, task_ids, intan_files_dir))
    fields.append(EpochStartStopTimesField(conn, parser, task_ids, intan_files_dir))
    fields.append(IntanSpikeRateByChannelField(conn, parser, task_ids, intan_files_dir))
    fields.append(GAClusterResponseField(conn, parser, task_ids, intan_files_dir))
    # Compile data
    raw_data = fields.to_data(task_ids)
    # Filter out trials with no response data
    data = raw_data[raw_data['Spike Rate by channel'].notna()]
    data = data[data['StimSpecId'].notna()]
    return data


class StimGaIdField(StimSpecIdField):
    def get(self, task_id) -> int:
        stim_id = self.get_cached_super(task_id, StimSpecIdField)
        self.conn.execute("SELECT ga_stim_id FROM StimGaId WHERE stim_id = %s",
                          params=(stim_id,))
        result = self.conn.fetch_one()
        return result if result is not None else stim_id  # Return original stim_id if no GA mapping exists

    def get_name(self):
        return "StimGaId"


class TextureField(StimSpecIdField):
    """Field for extracting texture type information."""

    def get(self, task_id) -> str:
        id = self.get_cached_super(task_id, StimSpecIdField)
        self.conn.execute("SELECT texture_type FROM StimTexture WHERE stim_id = %s",
                          params=(id,))
        texture = self.conn.fetch_one()
        return texture

    def get_name(self):
        return "Texture"


class ContrastField(StimSpecIdField):
    """Field for extracting contrast information."""

    def get(self, task_id) -> float:
        id = self.get_cached_super(task_id, StimSpecIdField)
        self.conn.execute("SELECT contrast FROM StimContrast WHERE stim_id = %s",
                          params=(id,))
        contrast = self.conn.fetch_one()
        return contrast

    def get_name(self):
        return "Contrast"


class ColorField(StimSpecIdField):
    """Field for extracting color information."""

    def get(self, task_id) -> tuple:
        id = self.get_cached_super(task_id, StimSpecIdField)
        self.conn.execute("SELECT red, green, blue FROM StimColor WHERE stim_id = %s",
                          params=(id,))
        color = self.conn.fetch_all()
        return color[0]

    def get_name(self):
        return "RGB"


class TypeField(ColorField):
    """Field for calculating lightness from RGB values."""

    def get(self, task_id) -> str:
        rgb = self.get_cached_super(task_id, ColorField)
        contrast = self.get_cached_super(task_id, ContrastField)
        texture = self.get_cached_super(task_id, TextureField)
        if texture == "SHADE" or texture == "SPECULAR":
            return texture
        elif texture == "2D":
            if contrast == 0.4:
                return "2D_LOW"
            elif contrast == 1.0:
                return "2D_HIGH"
            else:
                raise ValueError(f"Unknown contrast value: {contrast}")
        else:
            raise ValueError(f"Unknown texture type: {texture}")

    def get_name(self):
        return "Type"


class GAClusterResponseField(IntanSpikeRateByChannelField):
    """Field for calculating cluster responses."""

    def __init__(self, conn: Connection, parser: MultiFileParser, all_task_ids: list[int], intan_files_dir: str,
                 cluster_combination_method: callable = np.sum):
        super().__init__(conn, parser, all_task_ids, intan_files_dir)
        self.cluster_combination_method = cluster_combination_method

    def get(self, task_id: int) -> float:
        spike_rate_by_channel = self.get_cached_super(task_id, IntanSpikeRateByChannelField, self.parser,
                                                      self.all_task_ids,
                                                      self.intan_files_dir)

        channels = self._fetch_cluster_channels()

        # Get response per channel in the cluster
        cluster_response_vector = []
        for channel in channels:
            if channel in spike_rate_by_channel:
                cluster_response_vector.append(spike_rate_by_channel[channel])

        if not cluster_response_vector:
            return 0.0

        return self.cluster_combination_method(cluster_response_vector)

    def _fetch_cluster_channels(self):
        self.conn.execute("SELECT channel FROM ClusterInfo ORDER BY experiment_id DESC, gen_id")
        channels = self.conn.fetch_all()
        # Remove duplicate channels
        channels = list(dict.fromkeys(channels))
        # Unpack tuples
        channels = [channel[0] for channel in channels]
        return channels

    def get_name(self):
        return "Cluster Response"


if __name__ == "__main__":
    main()
