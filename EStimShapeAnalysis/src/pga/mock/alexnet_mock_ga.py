import os
import subprocess
import unittest
from time import sleep

import numpy as np

from clat.intan.channels import Channel
from src.pga.config.rf_config import RFGeneticAlgorithmConfig
from src.pga.config.twod_threed_config import TwoDThreeDGAConfig
from src.pga.ga_classes import RegimeTransitioner, Phase
from src.pga.mock import alexnet_ga_responses
from src.pga.multi_ga_db_util import MultiGaDbUtil
from src.pga.regime_zero import SeedingPhaseParentSelector, SeedingPhaseMutationAssigner, \
    SeedingPhaseMutationMagnitudeAssigner


class TestCombinedMockWithFakeNeuronResponse(unittest.TestCase):
    """
    Instructions:
    1. Run Java AcqServer, PGA Console and Experiment
    2. Run test_ga_loop
    """

    def setUp(self) -> None:
        self.mock_config = FullAutoAlexNetMockGeneticAlgorithmConfig()

    def test_ga_loop(self):
        generation = 1
        # while generation < 20:
        while generation < 20:
            sleep(8)  # time for the experiment to run all of the trials
            ga = self.mock_config.make_genetic_algorithm()
            ga.run()
            code = run_trial_generator(generation)
            if code != 0:
                print("Error in trial generator")
                continue
            generation += 1
        alexnet_ga_responses.main()

    def test_util_restart_ga(self):
        self.mock_config.db_util.update_ready_gas_and_generations_info("New3D", 0)

    def test_util_reset_db(self):
        self.mock_config.db_util.conn.truncate("StimGaInfo")
        self.mock_config.db_util.conn.truncate("LineageGaInfo")
        self.mock_config.db_util.conn.truncate("StimSpec")
        self.mock_config.db_util.conn.truncate("TaskToDo")
        self.mock_config.db_util.conn.truncate("TaskDone")
        self.mock_config.db_util.conn.truncate("BehMsg")
        self.mock_config.db_util.update_ready_gas_and_generations_info("New3D", 0)


class FullAutoAlexNetMockGeneticAlgorithmConfig(TwoDThreeDGAConfig):
    def __init__(self, *, database: str, base_intan_path: str):
        super().__init__(database=database, base_intan_path=base_intan_path)

    def make_response_parser(self):
        return AlexNetMockResponseParser(db_util=self.db_util)

    def seeding_phase_transitioner(self):
        return AlexNetSeedingPhaseTransitioner(0.0)

    def get_db_util(self):
        return AlexNetMultiGaDbUtil(self.connection())


class TrainingAlexNetMockGeneticAlgorithmConfig(TwoDThreeDGAConfig):
    def make_response_parser(self):
        return AlexNetMockResponseParser(db_util=self.db_util)


class AlexNetSeedingPhaseTransitioner(RegimeTransitioner):
    def __init__(self, spontaneous_firing_rate):
        self.spontaneous_firing_rate = spontaneous_firing_rate

    def should_transition(self, lineage):
        # checks if the firing rate is greater than the spontaneous firing rate
        firing_rates = lineage.stimuli[0].response_vector
        self.mean = np.mean(firing_rates)
        return self.mean > self.spontaneous_firing_rate

    def get_transition_data(self, lineage):
        data = {"response": self.mean}
        return str(data)


class AlexNetMockResponseParser:
    def __init__(self, db_util: MultiGaDbUtil = None):
        self.repetition_combination_strategy = np.mean
        self.db_util = db_util

    def parse_to_db(self, ga_name: str) -> None:
        alexnet_ga_responses.main()


class AlexNetMultiGaDbUtil(MultiGaDbUtil):
    """
    This class is a mock of MultiGaDbUtil that:
     1. Does not need a cluster to be defined. It mocks out a fake clusters.
    """

    def read_current_cluster(self, ga_name) -> list[Channel]:
        return [Channel.D_003]


def run_trial_generator(generation):
    output_dir = "/home/r2_allen/Documents/EStimShape/ga_dev_240207/java_output"
    allen_dist = "/home/r2_allen/git/EStimShape/xper-train/dist/allen"

    output_file = os.path.join(output_dir, f"generation_{generation}.txt")
    trial_generator_path = os.path.join(allen_dist, "MockNewGATrialGenerator.jar")
    trial_generator_command = f"java -jar {trial_generator_path}"

    with open(output_file, "w") as file:
        result = subprocess.run(trial_generator_command, shell=True, stdout=file, stderr=subprocess.STDOUT, text=True)
    return result.returncode
