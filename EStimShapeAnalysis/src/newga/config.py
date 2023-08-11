from math import prod

from numpy import mean

from intan.response_parsing import ResponseParser
from intan.response_processing import ResponseProcessor
from newga.lineage_selection import ClassicLineageDistributor
from newga.multi_ga_db_util import MultiGaDbUtil
from newga.regime_three import RegimeThreeParentSelector, RegimeThreeMutationAssigner, \
    RegimeThreeMutationMagnitudeAssigner, RegimeThreeTransitioner, HighEndSigmoid
from newga.regime_two import RegimeTwoParentSelector, RegimeTwoMutationAssigner, RegimeTwoMutationMagnitudeAssigner, \
    RegimeTwoTransitioner
from src.newga.ga_classes import Regime, ParentSelector, MutationAssigner, MutationMagnitudeAssigner, RegimeTransitioner
from src.newga.genetic_algorithm import GeneticAlgorithm
from src.newga.regime_one import RegimeOneParentSelector, RegimeOneMutationAssigner, RegimeOneMutationMagnitudeAssigner, \
    RegimeOneTransitioner, GetAllStimuliFunc
from src.newga.regime_zero import RegimeZeroParentSelector, RegimeZeroMutationAssigner, \
    RegimeZeroMutationMagnitudeAssigner, RegimeZeroTransitioner
from util.connection import Connection


class GeneticAlgorithmConfig:
    ga_name = "New3D"
    database = "allen_estimshape_dev_230519"
    num_trials_per_generation = 40
    max_lineages_to_build = 3
    number_of_new_lineages_per_generation = 5
    base_intan_path = "/bleh"
    under_sampling_threshold = 3.0

    def __init__(self):
        self.connection = self.make_connection()
        self.db_util = self.make_db_util()
        self.response_processor = self.make_response_processor()
        self.regimes = self.make_regimes()

    def make_genetic_algorithm(self) -> GeneticAlgorithm:
        ga = GeneticAlgorithm(name=self.ga_name,
                              regimes=self.regimes,
                              db_util=self.db_util,
                              trials_per_generation=self.num_trials_per_generation,
                              lineage_distributor=self.make_lineage_distributor(),
                              response_parser=self.make_response_parser(),
                              response_processor=self.response_processor)
        return ga

    def make_regimes(self):
        return [self.regime_zero(),
                self.regime_one(),
                self.regime_two(),
                self.regime_three()]

    def regime_zero(self):
        return Regime(RegimeZeroParentSelector(),
                      RegimeZeroMutationAssigner(),
                      RegimeZeroMutationMagnitudeAssigner(),
                      RegimeZeroTransitioner(
                          self.spontaneous_firing_rate(),
                          self.regime_zero_significance_threshold()))

    def regime_zero_significance_threshold(self):
        return 0.05

    def spontaneous_firing_rate(self):
        # TODO: analyze real data to get this number
        return 10

    def regime_one(self):
        return Regime(
            RegimeOneParentSelector(
                self.get_all_stimuli_func(),
                regime_one_bin_proportions(),
                regime_one_bin_sample_sizes()),
            RegimeOneMutationAssigner(),
            RegimeOneMutationMagnitudeAssigner(),
            RegimeOneTransitioner(
                convergence_threshold()
            ))

    def get_all_stimuli_func(self):
        return GetAllStimuliFunc(db_util=self.db_util,
                                 ga_name=self.ga_name,
                                 response_processor=self.response_processor)

    def make_response_processor(self) -> ResponseProcessor:
        return ResponseProcessor(db_util=self.db_util,
                                 repetition_combination_strategy=mean,
                                 cluster_combination_strategy=sum)

    def regime_two(self):
        return Regime(
            RegimeTwoParentSelector(
                self.percentage_of_max_threshold(),
                self.x()),
            RegimeTwoMutationAssigner(),
            RegimeTwoMutationMagnitudeAssigner(),
            RegimeTwoTransitioner(self.pair_threshold_high(), self.pair_threshold_low()))

    def pair_threshold_high(self):
        return 10

    def pair_threshold_low(self):
        return 10

    def percentage_of_max_threshold(self):
        return 0.5

    def x(self):
        return 5

    def regime_three(self):
        return Regime(
            RegimeThreeParentSelector(
                self.weight_func(),
                self.bandwidth()),
            RegimeThreeMutationAssigner(),
            RegimeThreeMutationMagnitudeAssigner(),
            RegimeThreeTransitioner(self.get_under_sampling_threshold(), bandwidth=self.bandwidth()))

    def weight_func(self):
        return HighEndSigmoid(steepness=15.0, offset=0.5)

    def bandwidth(self):
        return 0.15

    def get_under_sampling_threshold(self):
        return self.under_sampling_threshold

    def make_response_parser(self):
        return ResponseParser(self.base_intan_path,
                              self.db_util)

    def make_lineage_distributor(self):
        return ClassicLineageDistributor(
            number_of_trials_per_generation=self.num_trials_per_generation,
            max_lineages_to_build=self.max_lineages_to_build,
            number_of_new_lineages_per_generation=self.number_of_new_lineages_per_generation,
            regimes=self.regimes)

    def make_connection(self):
        return Connection(self.database)

    def make_db_util(self):
        return MultiGaDbUtil(self.connection)


def regime_one_bin_proportions():
    return [0.4, 0.2, 0.2, 0.1, 0.1]


def regime_one_bin_sample_sizes():
    return [8, 8, 8, 8, 8]


def convergence_threshold():
    return 0.1


