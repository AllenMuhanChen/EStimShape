import random
import unittest
from typing import Dict, List

from intan.channels import Channel
from intan.response_parsing import ResponseParser, get_current_date_as_YYYY_MM_DD
from newga.config import GeneticAlgorithmConfig
from newga.multi_ga_db_util import MultiGaDbUtil


class MockResponseParser(ResponseParser):
    def __init__(self, db_util: MultiGaDbUtil = None):
        # self.channels = get_channels()
        self.db_util = db_util

    def _parse_spike_rate_per_channel_for_task(self, task_id) -> dict[Channel, float]:
        rand = random.Random()
        spike_rates_per_channel = {}
        for channel in Channel:
            spike_rates_per_channel[channel] = rand.random() * 100
        return spike_rates_per_channel


class MockMultiGaDbUtil(MultiGaDbUtil):
    def read_current_cluster(self, ga_name) -> list[Channel]:
        return [Channel.A_000, Channel.A_001]

    def read_task_done_ids_for_stim_id(self, ga_name: str, stim_id: int):
        return [stim_id * scalar for scalar in [1, 2, 3, 4, 5]]

class MockGeneticAlgorithmConfig(GeneticAlgorithmConfig):
    def __init__(self):
        super().__init__()

    def response_parser(self):
        return MockResponseParser(db_util=self.db_util)

    def db_util(self):
        return MockMultiGaDbUtil(self.connection)


class TestPythonOnlyMockWithNonNeuralResponse(unittest.TestCase):

    def test_mock_ga(self):
        mock_config = MockGeneticAlgorithmConfig()
        ga = mock_config.genetic_algorithm()
        ga.run()

    def test_mock_respose_parser(self):
        mock_response_parser = MockResponseParser()
        print(mock_response_parser._parse_spike_rate_per_channel_for_task(1))


if __name__ == '__main__':
    unittest.main()
