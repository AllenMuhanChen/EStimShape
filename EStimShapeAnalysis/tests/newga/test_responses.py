from datetime import datetime
from unittest import TestCase
from unittest.mock import patch
import numpy as np

from matplotlib import pyplot as plt

from intan.channels import Channel
from intan.responses import ResponseParser, find_folders_with_id

from intan.spike_file import fetch_spike_tstamps_from_file
from intan.livenotes import map_stim_id_to_epochs_with_livenotes
from intan.marker_channels import get_epochs_start_and_stop_indices, read_digitalin_file
from tests.intan.test_marker_channels import plot_bool_array, plot_epochs_on_bool_array


class TestResponseModuleFunctions(TestCase):

    def test_parse_spike_count(self):
        base_intan_path = "/run/user/1003/gvfs/sftp:host=172.30.9.78/home/i2_allen/Documents/Test"
        response_parser = ResponseParser(base_intan_path, [Channel.B_025], "2023-07-19")
        print("Stim 1: ", response_parser.parse_spike_count_for_task(1))
        print("Stim 2: ", response_parser.parse_spike_count_for_task(2))
        print("Stim 3: ", response_parser.parse_spike_count_for_task(3))

        spike_tstamps_for_channels = fetch_spike_tstamps_from_file(response_parser.path_to_spike_file(1))
        # collapse values
        spike_tstamps = spike_tstamps_for_channels[Channel.B_025]
        spike_indices = [spike_tstamps * 30000 for spike_tstamps in spike_tstamps]

        digital_in = read_digitalin_file(
            response_parser.path_to_digital_in(1))
        epochs = get_epochs_start_and_stop_indices(digital_in[1], digital_in[0])
        plot_bool_array(digital_in[0])
        plot_bool_array(digital_in[1], False)
        plot_epochs_on_bool_array(digital_in[0], epochs, False)
        plot_timestamps_as_lines(spike_indices, False)

        plt.show()


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
