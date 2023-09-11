from unittest import TestCase

from intan.spike_file import fetch_spike_tstamps_from_file


class Test(TestCase):
    def test_retrieve_responses(self):
        responses, sample_rate = fetch_spike_tstamps_from_file(
            "/home/r2_allen/git/EStimShape/EStimShapeAnalysis/tests/newga/spike.dat")
        print(responses)
