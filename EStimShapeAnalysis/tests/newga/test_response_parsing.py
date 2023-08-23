from datetime import datetime
from unittest import TestCase
from unittest.mock import patch
import numpy as np

from matplotlib import pyplot as plt

from intan.channels import Channel
from intan.response_parsing import ResponseParser, find_folders_with_id

from intan.spike_file import fetch_spike_tstamps_from_file
from intan.livenotes import map_task_id_to_epochs_with_livenotes
from intan.marker_channels import get_epochs_start_and_stop_indices, read_digitalin_file
from tests.intan.test_marker_channels import plot_bool_array, plot_epochs_on_bool_array

import unittest
from unittest.mock import Mock, call
from src.intan.response_parsing import ResponseParser, Channel


class TestResponseParser(unittest.TestCase):
    base_intan_path = "/run/user/1003/gvfs/sftp:host=172.30.9.78/home/i2_allen/Documents/Test"
    test_date = "2023-07-19"

    def test_plot_spikes(self):
        response_parser = ResponseParser(self.base_intan_path, None, "2023-07-19")

        spike_tstamps_for_channels = fetch_spike_tstamps_from_file(response_parser._path_to_spike_file(1))
        # collapse values
        spike_tstamps = spike_tstamps_for_channels[Channel.B_025]
        spike_indices = [spike_tstamps * 30000 for spike_tstamps in spike_tstamps]

        digital_in = read_digitalin_file(
            response_parser._path_to_digital_in(1))
        epochs = get_epochs_start_and_stop_indices(digital_in[1], digital_in[0])
        plot_bool_array(digital_in[0])
        plot_bool_array(digital_in[1], False)
        plot_epochs_on_bool_array(digital_in[0], epochs, False)
        plot_timestamps_as_lines(spike_indices, False)

        plt.show()

    def test_parse_to_db(self):
        # Create a dictionary to store the values written to the database
        self.db_values = {}

        # Create a mock db_util
        mock_db_util = Mock()

        # Replace add_stim_response with a function that stores its inputs
        def add_stim_response(stim_id, task_id, channel, spikes_per_second):
            self.db_values[(stim_id, task_id, channel)] = spikes_per_second

        mock_db_util.add_stim_response = add_stim_response

        # Set return values for the other db_util methods

        mock_db_util.read_stims_with_no_responses = lambda name: [1, 2, 3]
        mock_db_util.read_task_done_ids_for_stim_id = lambda name, x: {x: [x]}
        # Create a ResponseParser instance with the mock db_util

        rp = ResponseParser(self.base_intan_path, mock_db_util, self.test_date)

        # Call the method to test
        rp.parse_to_db('ga_name')

        # Check the values written to the mock database
        for key, value in self.db_values.items():
            stim_id, task_id, channel = key
            # Here you can add checks for the values, depending on what you expect them to be
            # For example, if you expect the value for all channels to be 1.0, you could do:
            if channel == Channel.B_025.value:
                if stim_id == 1:
                    self.assertEqual(value, 18.568186507117808)
                elif stim_id == 2:
                    self.assertEqual(value, 6.189395502372602)
                elif stim_id == 3:
                    self.assertEqual(value, 10.315659170621005)


if __name__ == '__main__':
    unittest.main()


def plot_timestamps_as_lines(timestamps, new_figure=True, line_height=0.1, line_width=0.5):
    if new_figure:
        plt.figure(figsize=(10, 6))

    # Create a boolean array with same length as timestamps
    # All elements are False (represented by 0 in the plot)
    bool_arr = np.zeros(len(timestamps))

    # Plot the boolean array
    plt.plot(bool_arr, drawstyle='steps-pre')
    plt.ylim(-0.5, 1.5)  # to set proper y-limits
    plt.yticks([0, 1], ['False', 'True'])  # to set y-tick labels

    # For each timestamp, plot a shorter and thinner vertical line
    for ts in timestamps:
        plt.vlines(x=ts, ymin=0, ymax=line_height, color='red', linewidth=line_width)


class TestFindFoldersWithID(TestCase):

    @patch('os.walk')
    def test_find_folders_with_id(self, mock_os_walk):
        # Set up mock os.walk to return a predefined list of directories
        mock_os_walk.return_value = [
            ('/root', ['1_2_3__20230719_1200', '3_4_5_6__20230719_1300'], []),
            ('/root/1_2_3__20230719_1200', [], []),
            ('/root/3_4_5_6__20230719_1300', [], []),
        ]

        # Test that the function correctly finds directories with the id '2'
        self.assertEqual(
            find_folders_with_id('/root', 2),
            ['/root/1_2_3__20230719_1200']
        )

        # Test that the function correctly finds directories with the id '4'
        self.assertEqual(
            find_folders_with_id('/root', 4),
            ['/root/3_4_5_6__20230719_1300']
        )

        # Test that the function returns an empty list when the id is not found
        self.assertEqual(
            find_folders_with_id('/root', 7),
            []
        )

        # Test that the function returns a list with two elements when a file contains two
        # instances of the id
        self.assertEqual(
            find_folders_with_id('/root', 3),
            ['/root/1_2_3__20230719_1200', '/root/3_4_5_6__20230719_1300']
        )


import unittest
