import unittest
from unittest import TestCase

from matplotlib import pyplot as plt

from intan.read_intan_spike_file import read_digitalin_file
from newga.responses import ResponseParser, fetch_spike_tstamps_from_file, get_epochs, map_stim_id_to_tstamps

import itertools


class TestResponseRetriever(TestCase):

    def test_parse_spike_count(self):
        base_intan_path = "sftp://172.30.9.78/home/i2_allen/Documents/Test"
        response_parser = ResponseParser(base_intan_path)

    def test_retrieve_responses(self):
        responses = fetch_spike_tstamps_from_file(
            "/home/r2_allen/git/EStimShape/EStimShapeAnalysis/tests/newga/spike.dat")
        print(responses)

    def test_get_epochs(self):
        digital_in = read_digitalin_file(
            "/home/r2_allen/git/EStimShape/EStimShapeAnalysis/tests/newga/mock-trial/digitalin.dat")
        epochs = get_epochs(digital_in[1], digital_in[0])

        print(epochs)
        plot_bool_array(digital_in[0])
        plot_bool_array(digital_in[1], False)
        plot_epochs_on_bool_array(digital_in[0], epochs, False)

    def test_map_stim_id_on_file(self):
        digital_in = read_digitalin_file(
            "/home/r2_allen/git/EStimShape/EStimShapeAnalysis/tests/newga/mock-trial/digitalin.dat")
        stim_tstamps = get_epochs(digital_in[1], digital_in[0])

        notes = "/home/r2_allen/git/EStimShape/EStimShapeAnalysis/tests/newga/mock-trial/notes.txt"

        stamps_for_stim_id = map_stim_id_to_tstamps(notes, stim_tstamps)
        print(stamps_for_stim_id)

        expected = {1: 3919, 2: 19424, 3: 34421}
        self.assertEqual(expected, stamps_for_stim_id)

    def test_get_epochs_glitches(self):
        # Create some glitchless test data
        marker1_data = [False, False, True, True, True, False, False, False, False, False, True, True, True, False,
                        False]
        marker2_data = [False, False, False, False, False, True, True, True, False, False, False, False, False, False,
                        False]

        # Expected output
        expected_epochs = [(2, 4), (5, 7), (10, 12)]

        # Test the function on glitchless data
        epochs = get_epochs(marker1_data, marker2_data, false_data_correction_duration=3)
        self.assertEqual(expected_epochs, epochs)

        # Create some glitchy test data with false negatives in the middle of pulses
        marker1_data_false_negative = [True, True, True, False, True, False, False, False, False, False, True, True,
                                       True, False,
                                       False]

        marker2_data_false_negative = [False, False, False, False, False, True, True, True, False, True, False, False,
                                       False, False,
                                       False]

        # Expected output
        expected_epochs = [(0, 4), (5, 9), (10, 12)]

        # Test the function on glitchy data
        epochs = get_epochs(marker1_data_false_negative, marker2_data_false_negative, false_data_correction_duration=3)
        self.assertEqual(expected_epochs, epochs)

        # Create some glitchy test data with false positives
        marker1_data_false_positive = [True, False, True, True, True, False, False, False, False, False, True, True,
                                       True, False,
                                       False]
        marker2_data_false_positive = [False, False, False, False, False, True, True, True, False, False, False, False,
                                       True, False,
                                       False]

        # Expected output
        expected_epochs = [(2, 4), (5, 7), (10, 12)]

        # Test the function on glitchy data
        epochs = get_epochs(marker1_data_false_positive, marker2_data_false_positive, false_data_correction_duration=3)
        self.assertEqual(expected_epochs, epochs)

    def test_map_stim_id_to_tstamp(self):
        data = """
        1000, 00:00:00, 1\n\n
        2000, 00:00:01, 2\n\n
        3000, 00:00:02, 3\n\n
        4000, 00:00:03, 4\n\n
        """
        time_indices = [(1500, 2500), (2500, 3500), (3500, 4500), (4500, 5500)]
        expected_result = {1: 1500, 2: 2500, 3: 3500, 4: 4500}
        self.assertEqual(map_stim_id_to_tstamps(data, time_indices), expected_result)

        # Test with time_indices for start being before expected
        time_indices = [(500, 1500), (1500, 2500), (2500, 3500), (3500, 4500)]
        expected_result = {1: 500, 2: 1500, 3: 2500, 4: 3500}
        self.assertEqual(map_stim_id_to_tstamps(data, time_indices), expected_result)

        # Test with time_indices for start being after expected
        time_indices = [(1500, 2500), (2500, 3500), (3500, 4500), (5000, 6000)]
        expected_result = {1: 1500, 2: 2500, 3: 3500, 4: 5000}
        self.assertEqual(map_stim_id_to_tstamps(data, time_indices), expected_result)


def plot_bool_array(arr, new_figure=True):
    if new_figure:
        plt.figure(figsize=(10, 6))

    plt.plot(arr, drawstyle='steps-pre')
    plt.ylim(-0.5, 1.5)  # to set proper y-limits
    plt.yticks([0, 1], ['False', 'True'])  # to set y-tick labels


def plot_epochs_on_bool_array(arr, epochs, new_figure=True):
    if new_figure:
        plt.figure(figsize=(10, 6))

    plt.plot(arr, drawstyle='steps-pre')
    plt.ylim(-0.5, 1.5)  # to set proper y-limits
    plt.yticks([0, 1], ['False', 'True'])  # to set y-tick labels

    # Plot each epoch as a shaded region
    for start, end in epochs:
        plt.axvspan(start, end, alpha=0.2, color='red')  # change color and transparency as needed

    plt.show()
