from unittest import TestCase

from clat.intan.spike_file import fetch_spike_tstamps_from_file


class Test(TestCase):
    def test_retrieve_responses(self):
        responses, sample_rate = fetch_spike_tstamps_from_file(
            "/pga/spike.dat")
        print(responses)
