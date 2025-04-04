import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# Import pipeline framework
from clat.util.connection import Connection
from clat.util.time_util import When
from clat.compile.tstamp.trial_tstamp_collector import TrialCollector
from clat.compile.task.compile_task_id import TaskIdCollector
from clat.compile.tstamp.cached_tstamp_fields import CachedFieldList
from clat.compile.tstamp.classic_database_tstamp_fields import TaskIdField, StimIdField
from clat.pipeline.pipeline_base_classes import (
    AnalysisModule, create_pipeline, create_branch, AnalysisModuleFactory
)
from src.analysis.cached_fields import StimPathField, ThumbnailField

# Import custom modules
from src.intan.MultiFileParser import MultiFileParser
from src.startup import context
from src.analysis.isogabor.isogabor_analysis import IntanSpikesByChannelField, SpikeRateByChannelField
from src.analysis.grouped_stims_by_response import create_grouped_stimuli_module

class StimGaIdField(StimIdField):
    def get(self, when: When) -> int:
        stim_id = self.get_cached_super(when, StimIdField)
        self.conn.execute("SELECT ga_stim_id FROM StimGaId WHERE stim_id = %s",
                          params=(stim_id,))
        result = self.conn.fetch_one()
        return result if result is not None else stim_id  # Return original stim_id if no GA mapping exists

    def get_name(self):
        return "StimGaId"

class TextureField(StimIdField):
    """Field for extracting texture type information."""

    def get(self, when: When) -> str:
        id = self.get_cached_super(when, StimIdField)
        self.conn.execute("SELECT texture_type FROM StimTexture WHERE stim_id = %s",
                          params=(id,))
        texture = self.conn.fetch_one()
        return texture

    def get_name(self):
        return "Texture"


class ColorField(StimIdField):
    """Field for extracting color information."""

    def get(self, when: When) -> tuple:
        id = self.get_cached_super(when, StimIdField)
        self.conn.execute("SELECT red, green, blue FROM StimColor WHERE stim_id = %s",
                          params=(id,))
        color = self.conn.fetch_all()
        return color[0]

    def get_name(self):
        return "RGB"


class LightnessField(ColorField):
    """Field for calculating lightness from RGB values."""

    def get(self, when: When) -> float:
        rgb = self.get_cached_super(when, ColorField)
        # Calculate lightness using luminosity formula (0.299*R + 0.587*G + 0.114*B)
        lightness = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]

        return lightness

    def get_name(self):
        return "Lightness"


class GAClusterResponseField(SpikeRateByChannelField):
    """Field for calculating cluster responses."""

    def __init__(self, conn: Connection, parser: MultiFileParser, all_task_ids: list[int], intan_files_dir: str,
                 cluster_combination_method: callable = np.sum):
        super().__init__(conn, parser, all_task_ids, intan_files_dir)
        self.cluster_combination_method = cluster_combination_method

    def get(self, when: When) -> float:
        spike_rate_by_channel = self.get_cached_super(when, SpikeRateByChannelField, self.parser, self.all_task_ids,
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
    date = '2025-04-03'
    conn = Connection(context.twodvsthreed_database)

    # Collect trials
    trial_tstamps = TrialCollector(conn).collect_trials()
    task_ids = TaskIdCollector(conn).collect_task_ids()

    # Set up parser for spike data
    parser = MultiFileParser(to_cache=True, cache_dir=context.twodvsthreed_parsed_spikes_path)
    intan_files_dir = context.twodvsthreed_intan_path + '/' + date

    # Set up fields for data compilation
    fields = CachedFieldList()
    fields.append(TaskIdField(conn))
    fields.append(StimIdField(conn))
    fields.append(StimGaIdField(conn))
    fields.append(StimPathField(conn))
    fields.append(ThumbnailField(conn))
    fields.append(TextureField(conn))
    fields.append(ColorField(conn))
    fields.append(LightnessField(conn))
    fields.append(IntanSpikesByChannelField(conn, parser, task_ids, intan_files_dir))
    fields.append(SpikeRateByChannelField(conn, parser, task_ids, intan_files_dir))
    fields.append(GAClusterResponseField(conn, parser, task_ids, intan_files_dir))

    # Compile data
    raw_data = fields.to_data(trial_tstamps)
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
    aggregation_cols = ['StimId', 'Texture', 'Lightness', 'ThumbnailPath']
    if 'StimGaId' in data.columns:
        aggregation_cols.append('StimGaId')

    # Perform groupby aggregation
    print(f"\nAggregating by: {aggregation_cols}")
    agg_dict = {'Cluster Response': 'mean'}
    agg_data = data.groupby(aggregation_cols).agg(agg_dict).reset_index()

    print("\nAfter aggregation:")
    print(f"Total rows: {len(agg_data)}")
    print(f"Unique StimIds: {agg_data['StimId'].nunique()}")

    # Create visualization module
    visualize_module = create_grouped_stimuli_module(
        response_col='Cluster Response',
        path_col='ThumbnailPath',
        row_col='Texture',
        col_col='Lightness',
        subgroup_col='StimGaId',  # No subgrouping needed, we've already aggregated
        filter_values={
            'Texture': ['SHADE', 'SPECULAR', 'TWOD']  # Include UNKNOWN as well
        },
        figsize=(12, 9),
        cell_size=(2, 2),
        border_width=5,
        normalize_method='global',
        color_mode='intensity',
        title='2D vs 3D Texture Response Analysis',
        # save_path=f"{context.twodvsthreed_plots_dir}/texture_by_lightness.png"
    )

    # Print data summary before visualization
    print("\nData Summary before visualization:")
    print(f"Unique textures: {agg_data['Texture'].unique()}")
    print(f"Unique lightness values: {agg_data['Lightness'].unique()}")

    # Count values in each group
    print("\nTexture value counts:")
    print(agg_data['Texture'].value_counts())
    print("\nLightness value counts:")
    print(agg_data['Lightness'].value_counts())

    # Create data grid showing count of items in each row/col combination
    print("\nData grid (counts in each cell):")
    counts = pd.crosstab(agg_data['Texture'], agg_data['Lightness'])
    print(counts)

    # Create and run pipeline with aggregated data
    pipeline = create_pipeline().then(visualize_module).build()
    result = pipeline.run(agg_data)

    # Show the figure
    plt.show()

    return result

if __name__ == "__main__":
    main()