from unittest import TestCase

from matplotlib import pyplot as plt

from intan.read_intan_spike_file import read_digitalin_file
from newga.responses import ResponseRetriever, fetch_spike_tstamps_from_file

import itertools


class TestResponseRetriever(TestCase):

    def test_retrieve_responses(self):
        responses = fetch_spike_tstamps_from_file(
            "/home/r2_allen/git/EStimShape/EStimShapeAnalysis/tests/newga/spike.dat")
        print(responses)

    def test_digitalin(self):
        digital_in = read_digitalin_file("/home/r2_allen/git/EStimShape/EStimShapeAnalysis/tests/newga/digitalin.dat")

        plot_bool_array(digital_in[0])
        plot_bool_array(digital_in[1], False)
        plt.show()


def plot_bool_array(arr, new_figure=True):
    if new_figure:
        plt.figure(figsize=(10, 6))

    plt.plot(arr, drawstyle='steps-pre')
    plt.ylim(-0.5, 1.5)  # to set proper y-limits
    plt.yticks([0, 1], ['False', 'True'])  # to set y-tick labels
