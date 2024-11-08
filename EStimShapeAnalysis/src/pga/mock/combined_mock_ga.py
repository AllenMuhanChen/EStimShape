import os
import subprocess
import unittest
from time import sleep

import numpy as np

from clat.intan.channels import Channel

import src.tree_graph.ga_tree_graph
from src.pga.config.rf_config import RFGeneticAlgorithmConfig
from src.pga.spike_parsing import IntanResponseParser
from src.pga.mock import mock_ga_responses
from src.pga.multi_ga_db_util import MultiGaDbUtil


class TestCombinedMockWithFakeNeuronResponse(unittest.TestCase):
    """
    Instructions:
    1. Run Java PGA Console and Experiment
    2. Run test_ga_loop
    """
    def setUp(self) -> None:
        self.mock_config = FakeNeuronMockGeneticAlgorithmConfig()

    def test_ga_loop(self):
        generation = 1
        while generation < 15:
            sleep(20)
            ga = self.mock_config.make_genetic_algorithm()
            ga.run()
            run_trial_generator(generation)
            generation += 1

    def test_util_reset_db(self):
        src.tree_graph.ga_tree_graph.conn.truncate("StimGaInfo")
        src.tree_graph.ga_tree_graph.conn.truncate("LineageGaInfo")
        src.tree_graph.ga_tree_graph.conn.truncate("StimSpec")
        src.tree_graph.ga_tree_graph.conn.truncate("TaskToDo")
        src.tree_graph.ga_tree_graph.conn.truncate("TaskDone")
        src.tree_graph.ga_tree_graph.conn.truncate("BehMsg")
        self.mock_config.db_util.update_ready_gas_and_generations_info("New3D", 0)


class FakeNeuronMockGeneticAlgorithmConfig(RFGeneticAlgorithmConfig):
    def __init__(self):
        super().__init__()

    def make_response_parser(self):
        return FakeNeuronMockIntanResponseParser(db_util=self.db_util)

    def get_db_util(self) -> MultiGaDbUtil:
        return FakeNeuronMockMultiGaDbUtil(self.connection)


class FakeNeuronMockIntanResponseParser(IntanResponseParser):
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


def run_trial_generator(generation):
    output_dir = "/home/r2_allen/git/EStimShape/EStimShapeAnalysis/src/tree_graph"
    allen_dist = "/home/r2_allen/git/EStimShape/xper-train/dist/allen"

    output_file = os.path.join(output_dir, f"generation_{generation}.txt")
    trial_generator_path = os.path.join(allen_dist, "MockNewGATrialGenerator.jar")
    trial_generator_command = f"java -jar {trial_generator_path}"

    with open(output_file, "w") as file:
        result = subprocess.run(trial_generator_command, shell=True, stdout=file, stderr=subprocess.STDOUT, text=True)
    return result.returncode


if __name__ == '__main__':
    unittest.main()
