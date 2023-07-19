import unittest
from unittest import TestCase
from unittest.mock import patch

from intan.responses import ResponseParser, fetch_spike_tstamps_from_file, find_folders_with_id
from intan.livenotes import map_stim_id_to_epochs_with_livenotes
from intan.marker_channels import get_epochs_start_and_stop_indices, read_digitalin_file


class TestResponseModuleFunctions(TestCase):

    def test_parse_spike_count(self):
        base_intan_path = "sftp://172.30.9.78/home/i2_allen/Documents/Test"
        response_parser = ResponseParser(base_intan_path)

    def test_retrieve_responses(self):
        responses = fetch_spike_tstamps_from_file(
            "/home/r2_allen/git/EStimShape/EStimShapeAnalysis/tests/newga/spike.dat")
        print(responses)



class TestFindFoldersWithID(unittest.TestCase):

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
