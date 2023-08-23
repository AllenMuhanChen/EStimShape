import random
import unittest
from typing import Dict, List

import numpy as np

from intan.channels import Channel
from intan.response_parsing import ResponseParser, get_current_date_as_YYYY_MM_DD
from mock import mock_ga_responses
from newga.config import GeneticAlgorithmConfig
from newga.multi_ga_db_util import MultiGaDbUtil


class TestPythonOnlyMockWithNonNeuralResponse(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_config = FakeNeuronMockGeneticAlgorithmConfig()

    def test_mock_ga(self):
        ga = self.mock_config.make_genetic_algorithm()
        ga.run()

    def test_util_reset_db(self):
        self.mock_config.db_util.conn.truncate("StimGaInfo")
        self.mock_config.db_util.conn.truncate("LineageGaInfo")
        self.mock_config.db_util.conn.truncate("StimSpec")
        self.mock_config.db_util.conn.truncate("TaskToDo")
        self.mock_config.db_util.conn.truncate("TaskDone")
        self.mock_config.db_util.conn.truncate("BehMsg")
        self.mock_config.db_util.update_ready_gas_and_generations_info("New3D", 0)


class MockResponseParser(ResponseParser):
    """
    This class is a mock of ResponseParser that:
    1. Does not need Intan to generate responses. It mocks out fake random responses.
    """

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
    """
    This class is a mock of MultiGaDbUtil that:
     1. Does not need a live running experiment generating task_done_ids. It mocks out fake task_done_ids.
     2. Does not need a cluster to be defined. It mocks out a fake clusters.
    """

    def read_current_cluster(self, ga_name) -> list[Channel]:
        return [Channel.A_000, Channel.A_001, Channel.A_002]

    def read_task_done_ids_for_stim_id(self, ga_name: str, stim_id: int):
        return [stim_id * scalar for scalar in [1, 2, 3, 4, 5]]


class MockGeneticAlgorithmConfig(GeneticAlgorithmConfig):
    """
    Overrides the normal ResponseParser and DbUtil with our mocks.
    """

    def __init__(self):
        super().__init__()

    def make_response_parser(self):
        return MockResponseParser(db_util=self.db_util)

    def make_db_util(self) -> MultiGaDbUtil:
        return MockMultiGaDbUtil(self.connection)


class TestCombinedMockWithFakeNeuronResponse(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_config = FakeNeuronMockGeneticAlgorithmConfig()

    # 1
    def test_mock_ga(self):
        ga = self.mock_config.make_genetic_algorithm()
        ga.run()

    def test_process_responses(self):
        ga = self.mock_config.make_genetic_algorithm()
        ga.process_responses()

    # 0
    def test_util_reset_db(self):
        self.mock_config.db_util.conn.truncate("StimGaInfo")
        self.mock_config.db_util.conn.truncate("LineageGaInfo")
        self.mock_config.db_util.conn.truncate("StimSpec")
        self.mock_config.db_util.conn.truncate("TaskToDo")
        self.mock_config.db_util.conn.truncate("TaskDone")
        self.mock_config.db_util.conn.truncate("BehMsg")
        self.mock_config.db_util.conn.truncate("ChannelResponses")
        self.mock_config.db_util.update_ready_gas_and_generations_info("New3D", 0)


class FakeNeuronMockGeneticAlgorithmConfig(GeneticAlgorithmConfig):
    def __init__(self):
        super().__init__()

    def make_response_parser(self):
        return FakeNeuronMockResponseParser(db_util=self.db_util)

    def make_db_util(self) -> MultiGaDbUtil:
        return FakeNeuronMockMultiGaDbUtil(self.connection)


class FakeNeuronMockResponseParser(ResponseParser):
    """
    This class is a mock of ResponseParser that:
    1. Does not generate responses, we'll let
    """

    def __init__(self, db_util: MultiGaDbUtil = None):
        self.repetition_combination_strategy = np.mean
        self.db_util = db_util

    def parse_to_db(self, ga_name: str) -> None:
        mock_ga_responses.main()


class FakeNeuronMockMultiGaDbUtil(MultiGaDbUtil):
    """
    This class is a mock of MultiGaDbUtil that:
     1. Does not need a cluster to be defined. It mocks out a fake clusters.
    """

    def read_current_cluster(self, ga_name) -> list[Channel]:
        return [Channel.A_000, Channel.A_001]


if __name__ == '__main__':
    unittest.main()
