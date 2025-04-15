import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

from clat.compile.task.cached_task_fields import CachedTaskFieldList
from clat.compile.task.classic_database_task_fields import StimSpecIdField
# Import pipeline framework
from clat.util.connection import Connection
from clat.util.time_util import When
from clat.compile.task.compile_task_id import TaskIdCollector
from clat.pipeline.pipeline_base_classes import (
    AnalysisModule, create_pipeline, create_branch, AnalysisModuleFactory
)
from src.analysis.cached_task_fields import StimPathField, ThumbnailField

# Import custom modules
from src.intan.MultiFileParser import MultiFileParser
from src.startup import context
from src.analysis.isogabor.isogabor_analysis import IntanSpikesByChannelField, SpikeRateByChannelField
from src.analysis.grouped_stims_by_response import create_grouped_stimuli_module

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


class GAClusterResponseField(SpikeRateByChannelField):
    """Field for calculating cluster responses."""

    def __init__(self, conn: Connection, parser: MultiFileParser, all_task_ids: list[int], intan_files_dir: str,
                 cluster_combination_method: callable = np.sum):
        super().__init__(conn, parser, all_task_ids, intan_files_dir)
        self.cluster_combination_method = cluster_combination_method

    def get(self, task_id: int) -> float:
        spike_rate_by_channel = self.get_cached_super(task_id, SpikeRateByChannelField, self.parser, self.all_task_ids,
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


def main():
    """Main function to run the 2D vs 3D analysis pipeline."""

    # Set up database connection and date
    date = '2025-04-15'
    conn = Connection(context.twodvsthreed_database)

    # Collect trials
    task_id_collector = TaskIdCollector(conn)
    task_ids = task_id_collector.collect_task_ids()

    # Set up parser for spike data
    parser = MultiFileParser(to_cache=True, cache_dir=context.twodvsthreed_parsed_spikes_path)
    intan_files_dir = context.twodvsthreed_intan_path + '/' + date

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
    fields.append(SpikeRateByChannelField(conn, parser, task_ids, intan_files_dir))
    fields.append(GAClusterResponseField(conn, parser, task_ids, intan_files_dir))

    # Compile data
    raw_data = fields.to_data(task_ids)
    print(raw_data.to_string())
    print("\nRaw data summary:")
    print(f"Total rows: {len(raw_data)}")
    print(f"Columns: {raw_data.columns.tolist()}")

    # Filter out trials with no response data
    data = raw_data[raw_data['Cluster Response'].notna()]



    # ---------------
    # Manual aggregation by StimId
    # ---------------
    # Group by StimId and calculate aggregated values
    aggregation_cols = ['StimSpecId', 'Texture', 'RGB', 'ThumbnailPath']
    if 'StimGaId' in data.columns:
        aggregation_cols.append('StimGaId')

    # Perform groupby aggregation
    print(f"\nAggregating by: {aggregation_cols}")
    agg_dict = {'Cluster Response': 'mean'}
    agg_data = data.groupby(aggregation_cols).agg(agg_dict).reset_index()

    print("\nAfter aggregation:")
    print(f"Total rows: {len(agg_data)}")
    print(f"Unique StimIds: {agg_data['StimSpecId'].nunique()}")

    # Create visualization module
    visualize_module = create_grouped_stimuli_module(
        response_col='Cluster Response',
        path_col='ThumbnailPath',
        col_col='RGB',
        row_col='Texture',
        subgroup_col='StimGaId',
        filter_values={
            'Texture': ['SHADE', 'SPECULAR', '2D']
        },
        title='2D vs 3D Texture Response Analysis',
        # save_path=f"{context.twodvsthreed_plots_dir}/texture_by_lightness.png"
    )

    # Create and run pipeline with aggregated data
    pipeline = create_pipeline().then(visualize_module).build()
    result = pipeline.run(agg_data)

    # Show the figure
    plt.show()

    return result

if __name__ == "__main__":
    main()