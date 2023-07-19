from unittest import TestCase

from matplotlib import pyplot as plt

from intan.marker_channels import get_epochs_start_and_stop_indices, read_digitalin_file


class TestEpoch(TestCase):
    def test_get_epochs(self):
        digital_in = read_digitalin_file(
            "/home/r2_allen/git/EStimShape/EStimShapeAnalysis/tests/newga/mock-trial/digitalin.dat")
        epochs = get_epochs_start_and_stop_indices(digital_in[1], digital_in[0])

        print(epochs)
        plot_bool_array(digital_in[0])
        plot_bool_array(digital_in[1], False)
        plot_epochs_on_bool_array(digital_in[0], epochs, False)

    def test_get_epochs_glitches(self):
        # Create some glitchless test data
        marker1_data = [False, False, True, True, True, False, False, False, False, False, True, True, True, False,
                        False]
        marker2_data = [False, False, False, False, False, True, True, True, False, False, False, False, False, False,
                        False]

        # Expected output
        expected_epochs = [(2, 4), (5, 7), (10, 12)]

        # Test the function on glitchless data
        epochs = get_epochs_start_and_stop_indices(marker1_data, marker2_data, false_data_correction_duration=3)
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
        epochs = get_epochs_start_and_stop_indices(marker1_data_false_negative, marker2_data_false_negative, false_data_correction_duration=3)
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
        epochs = get_epochs_start_and_stop_indices(marker1_data_false_positive, marker2_data_false_positive, false_data_correction_duration=3)
        self.assertEqual(expected_epochs, epochs)


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


