import pandas as pd
from matplotlib import pyplot as plt

from clat.compile.task.cached_task_fields import CachedTaskFieldList
from clat.compile.task.classic_database_task_fields import StimSpecIdField
from clat.compile.task.compile_task_id import TaskIdCollector
from clat.pipeline.pipeline_base_classes import create_pipeline, create_branch
from clat.util.connection import Connection
from src.analysis import Analysis
from src.analysis.fields.cached_task_fields import StimTypeField, StimPathField, ThumbnailField, ClusterResponseField
from src.analysis.ga.cached_ga_fields import LineageField, GAResponseField, ParentIdField
from src.analysis.ga.plot_top_n import clean_ga_data
from src.analysis.ga.solid_preference_index import create_sp_index_module
from src.analysis.isogabor.old_isogabor_analysis import IntanSpikesByChannelField, EpochStartStopTimesField, \
    IntanSpikeRateByChannelField
from src.analysis.lightness.lightness_analysis import TextureField
from src.analysis.modules.grouped_stims_by_response import create_grouped_stimuli_module
from src.analysis.modules.matplotlib.grouped_rasters_matplotlib import create_grouped_raster_module
from src.analysis.modules.grouped_rsth import create_psth_module
from src.analysis.modules.utils.sorting_utils import SpikeRateSortingUtils
from src.intan.MultiFileParser import MultiFileParser
from src.repository.export_to_repository import export_to_repository
from src.repository.import_from_repository import import_from_repository
from src.startup import context


def main():
    # channel = None
    compiled_data = compile()
    analysis = SideTestAnalysis()
    # session_id, _ = read_session_id_from_db_name(context.ga_database)
    # if channel is None:
        # channel = read_cluster_channels(session_id)[0]

    session_id = "250925_0"
    channel = "A-020"
    analysis.run(session_id, "raw", channel, compiled_data=compiled_data)


class SideTestAnalysis(Analysis):

    def analyze(self, channel, compiled_data: pd.DataFrame = None):
        if compiled_data is None:
            compiled_data = import_from_repository(
                self.session_id,
                "ga",
                "2Dvs3DStimInfo",
                self.response_table
            )
        # CLEAN UP DATA SOME
        compiled_data = compiled_data[compiled_data[self.spike_rates_col].notna()]

        # Index Computation Module
        index_module = create_sp_index_module(channel=channel, session_id=self.session_id, spike_data_col=self.spike_rates_col)
        index_branch = create_branch().then(index_module)

        # VISUALIZE MODULE
        limit = 10
        visualize_module = create_grouped_stimuli_module(
            response_rate_col=self.spike_rates_col,
            response_rate_key=channel,
            path_col='ThumbnailPath',
            col_col='TestId',
            row_col='TestType',
            sort_rules={
                "col": "TestId",
                "custom_func": SpikeRateSortingUtils.by_avg_value(
                    column=self.spike_rates_col,
                    comparison_col="TestType",
                    limit=limit
                )
            },
            title=f'2D vs 3D Test: {channel}',
            save_path=f"{self.save_path}/{channel}: 2dvs3d_more.png",
            include_labels_for={"row"},
            publish_mode=False,
            subplot_spacing=(20, 20),
            cell_size= (400, 400),
            border_width= 100,
            include_colorbar = True
        )

        plot_branch = create_branch().then(visualize_module)

        # RASTERS for SIDE TEST

        raster_module = create_grouped_raster_module(
            primary_group_col='TestType',
            secondary_group_col='TestId',
            spike_data_col=self.spike_tstamps_col,
            spike_data_col_key=channel,
            title=f'2D vs 3D Rasters: {channel}',
            save_path=f"{self.save_path}/{channel}: 2dvs3d_rasters.png",
        )
        raster_branch = create_branch().then(raster_module)

        # Create a PSTH module sorted by average firing rat
        psth_module = create_psth_module(
            primary_group_col='TestType',
            secondary_group_col='TestId',
            spike_data_col=self.spike_tstamps_col,
            spike_data_col_key=channel,
            bin_size=0.025,
            sort_rules={
                "col": "TestId",
                "custom_func": SpikeRateSortingUtils.by_avg_value(
                    column=self.spike_rates_col,
                    comparison_col="TestType",
                    limit=limit
                )
            },
            title=f'2D vs 3D PSTH: {channel}',
            save_path=f"{self.save_path}/{channel}: 2dvs3d_psth.png",
            cell_size=(600, 300),
            include_row_labels=False,
        )

        psth_branch = create_branch().then(psth_module)

        psth_examples = create_grouped_stimuli_module(
            response_rate_col=self.spike_rates_col,
            path_col='ThumbnailPath',
            response_rate_key=channel,
            row_col="TestId",
            col_col="TestType",
            sort_rules={
                "col": "TestId",
                "custom_func": SpikeRateSortingUtils.by_avg_value(
                    column=self.spike_rates_col,
                    comparison_col="TestType",
                    limit=limit)
            },
            title=f'2D vs 3D PSTH Examples: {channel}',
            save_path=f"{self.save_path}/{channel}: 2dvs3d_psth_examples.png",
            cols_in_info_box=[],
            cell_size=(300, 300),
            include_labels_for={"TestType"},
            publish_mode=True,
            subplot_spacing=(0, 0),
        )

        psth_examples_branch = create_branch().then(psth_examples)

        # pipeline = create_pipeline().make_branch(
        #     index_branch).build()

        pipeline = create_pipeline().make_branch(
            plot_branch, raster_branch, psth_branch, psth_examples_branch
        ).build()
        result = pipeline.run(compiled_data)
        # Show the figure
        plt.show()
        return result

    def compile_and_export(self):
        compile_and_export()

    def compile(self):
        compile()


def compile_and_export():
    data_for_plotting = compile()
    # print(data_for_plotting[["TestId", "UnderlingAvgRGB", "AvgRGBFromImage", "TestType"]].groupby(["TestId", "TestType"]).agg(
    #     {"UnderlingAvgRGB": "first",
    #      "AvgRGBFromImage": "first"}).reset_index().to_string(index=False))
    export_to_repository(data_for_plotting,
                         context.ga_database,
                         "ga",
                         stim_info_table="2Dvs3DStimInfo",
                         stim_info_columns=['Lineage', 'StimType', 'StimPath', 'ThumbnailPath', 'GA Response', 'TestId',
                                            'TestType'],
                         )


def compile():
    conn = Connection(context.ga_database)
    data_for_all_tasks = compile_data(conn)
    data_for_all_tasks = clean_ga_data(data_for_all_tasks)
    data_for_plotting = organize_data(data_for_all_tasks)
    return data_for_plotting


def compile_data(conn: Connection) -> pd.DataFrame:
    collector = TaskIdCollector(conn)
    task_ids = collector.collect_task_ids()
    response_processor = context.ga_config.make_response_processor()
    cluster_combination_strategy = response_processor.cluster_combination_strategy
    # sort_dir = "/home/r2_allen/Documents/EStimShape/allen_sort_250421_0/sorted_spikes.pkl"
    parser = MultiFileParser(to_cache=True, cache_dir=context.ga_parsed_spikes_path)

    fields = CachedTaskFieldList()
    fields.append(StimSpecIdField(conn))
    fields.append(ParentIdField(conn))
    fields.append(LineageField(conn))
    fields.append(StimTypeField(conn))
    fields.append(StimPathField(conn))
    fields.append(TextureField(conn))
    # fields.append(AverageRGBField(conn))
    fields.append(UnderlingAvgRGBField(conn))
    fields.append(ThumbnailField(conn))
    fields.append(IntanSpikesByChannelField(conn, parser, task_ids, context.ga_intan_path))
    fields.append(IntanSpikeRateByChannelField(conn, parser, task_ids, context.ga_intan_path))
    fields.append(EpochStartStopTimesField(conn, parser, task_ids, context.ga_intan_path))
    fields.append(GAResponseField(conn))
    fields.append(ClusterResponseField(conn, cluster_combination_strategy))

    data = fields.to_data(task_ids)

    return data


def organize_data(data_for_stim_ids):
    data_for_side_test_stim = data_for_stim_ids[data_for_stim_ids['StimType'].str.contains("SIDETEST_2Dvs3D")]
    # print(data_for_side_tests.to_string())
    # Go through side test stimuli and add row for parent to dataframe if unique: add to a new dataframe with new column 'TestId'
    data_for_plotting = pd.DataFrame(columns=data_for_stim_ids.columns)
    for _, side_test_stim_row in data_for_side_test_stim.iterrows():
        parent_rows = data_for_stim_ids[data_for_stim_ids['StimSpecId'] == side_test_stim_row['ParentId']]
        if not parent_rows.empty:
            #

            # PARENT
            for _, parent_row in parent_rows.iterrows():
                parent_row['TestId'] = parent_row['StimSpecId']
                if "2D" in parent_row['Texture']:
                    parent_row['TestType'] = "2D"
                else:
                    parent_row['TestType'] = "3D"

                if data_for_plotting[data_for_plotting['TaskId'] == parent_row[
                    'TaskId']].empty:  # if the parent row is not already in the dataframe
                    data_for_plotting = pd.concat([data_for_plotting, parent_row.to_frame().T], ignore_index=True)

            new_row = side_test_stim_row.copy()
            new_row['TestId'] = parent_row['StimSpecId']
            if "2D" in parent_row['TestType']:
                new_row['TestType'] = "3D"
            else:
                new_row['TestType'] = "2D"
            data_for_plotting = pd.concat([data_for_plotting, new_row.to_frame().T], ignore_index=True)
    return data_for_plotting


class UnderlingAvgRGBField(StimSpecIdField):
    def __init__(self, conn):
        super().__init__(conn)
        self.conn = conn

    def get(self, task_id):
        stim_spec_id = self.get_cached_super(task_id, StimSpecIdField)
        self.conn.execute("SELECT average_rgb FROM UnderlyingAverageRGB WHERE stim_id = %s", params=(stim_spec_id,))
        result = self.conn.fetch_one()
        return result;

    def get_name(self):
        return "UnderlingAvgRGB"


class AverageRGBField(StimPathField):
    def __init__(self, conn):
        super().__init__(conn)
        self.conn = conn

    def get(self, task_id):
        stim_path = self.get_cached_super(task_id, StimPathField)
        if stim_path is None or stim_path == "None":
            return None

        try:
            # Import necessary libraries
            import cv2
            import numpy as np
            from scipy import stats
            import os

            # Check if the file exists
            if not os.path.exists(stim_path):
                print(f"File not found: {stim_path}")
                return None

            # Read the image
            img = cv2.imread(stim_path)
            if img is None:
                print(f"Failed to read image: {stim_path}")
                return None

            # Convert to RGB if it's in BGR format (OpenCV default)
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            # Reshape the image to a 2D array of pixels
            pixels = img_rgb.reshape(-1, 3)

            # Find the mode pixel value (background)
            # We'll convert pixels to tuple strings to find the most common RGB combination
            pixel_tuples = [tuple(pixel) for pixel in pixels]
            mode_pixel = stats.mode(pixel_tuples, keepdims=False)[0]

            # Create a mask where pixels are not the background color
            # A small tolerance might be needed for slight variations in background color
            tolerance = 5
            mask = np.zeros(img_rgb.shape[:2], dtype=bool)  # Use boolean array

            for i in range(3):  # For each RGB channel
                channel_mask = np.abs(img_rgb[:, :, i] - mode_pixel[i]) > tolerance
                mask = mask | channel_mask  # Boolean OR operation

            # If mask is empty (all pixels considered background), return all pixels average
            if np.sum(mask) == 0:
                print(f"Warning: All pixels identified as background in {stim_path}")
                avg_rgb = np.mean(pixels, axis=0).astype(int)
                return {
                    'r': int(avg_rgb[0]),
                    'g': int(avg_rgb[1]),
                    'b': int(avg_rgb[2]),
                    'background_mode': tuple(int(v) for v in mode_pixel),
                    'foreground_pixels': len(pixels),
                    'note': 'All pixels considered background'
                }

            # Apply mask to get foreground pixels
            foreground_pixels = img_rgb[mask]

            # Calculate average RGB values of foreground
            avg_rgb = np.mean(foreground_pixels, axis=0).astype(int)

            # Return the result as a dictionary
            r = float(avg_rgb[0] / 255)
            g = float(avg_rgb[1] / 255)
            b = float(avg_rgb[2] / 255)
            return (r, g, b)

        except Exception as e:
            print(f"Error processing image {stim_path}: {e}")
            return None

    def get_name(self):
        return "AvgRGBFromImage"


if __name__ == "__main__":
    main()
