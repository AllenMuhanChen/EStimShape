from unittest import TestCase

from clat.intan.livenotes import map_unique_task_id_to_epochs_with_livenotes
from clat.intan.marker_channels import read_digitalin_file, get_epochs_start_and_stop_indices


class TestLiveNoteMapToMarkerChannels(TestCase):
    def test_map_stim_id_on_file(self):
        digital_in = read_digitalin_file(
            "/pga/mock-trial/digitalin.dat")
        stim_tstamps = get_epochs_start_and_stop_indices(digital_in[1], digital_in[0])

        notes = "/home/r2_allen/git/EStimShape/EStimShapeAnalysis/tests/newga/mock-trial/notes.txt"

        stamps_for_stim_id = map_unique_task_id_to_epochs_with_livenotes(notes, stim_tstamps)
        print(stamps_for_stim_id)

        expected = {1: (3919, 18966), 2: (19424, 33927), 3: (34421, 48964)}
        self.assertEqual(expected, stamps_for_stim_id)

    def test_map_stim_id_to_tstamp(self):
        data = """
        1000, 00:00:00, 1\n\n
        2000, 00:00:01, 2\n\n
        3000, 00:00:02, 3\n\n
        4000, 00:00:03, 4\n\n
        """
        time_indices = [(1500, 2500), (2500, 3500), (3500, 4500), (4500, 5500)]
        expected_result = {1: (1500, 2500), 2: (2500, 3500), 3: (3500, 4500), 4: (4500, 5500)}
        self.assertEqual(map_unique_task_id_to_epochs_with_livenotes(data, time_indices), expected_result)

        # Test with time_indices for start being before expected
        time_indices = [(500, 1500), (1500, 2500), (2500, 3500), (3500, 4500)]
        expected_result = {1: (500, 1500), 2: (1500, 2500), 3: (2500, 3500), 4: (3500, 4500)}
        self.assertEqual(map_unique_task_id_to_epochs_with_livenotes(data, time_indices), expected_result)

        # Test with time_indices for start being after expected
        time_indices = [(1500, 2500), (2500, 3500), (3500, 4500), (5000, 6000)]
        expected_result = {1: (1500, 2500), 2: (2500, 3500), 3: (3500, 4500), 4: (5000, 6000)}
        self.assertEqual(map_unique_task_id_to_epochs_with_livenotes(data, time_indices), expected_result)

