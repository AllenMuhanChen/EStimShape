from math import prod
from typing import Any

from numpy import mean

from pga.spike_parsing import ResponseParser
from pga.response_processing import ResponseProcessor
from pga.lineage_selection import ClassicLineageDistributor
from pga.multi_ga_db_util import MultiGaDbUtil
from pga.regime_three import LeafingPhaseParentSelector, LeafingPhaseMutationAssigner, \
    LeafingPhaseMutationMagnitudeAssigner, LeafingPhaseTransitioner, HighEndSigmoid
from pga.regime_two import CanopyPhaseParentSelector, CanopyPhaseMutationAssigner, CanopyPhaseMutationMagnitudeAssigner, \
    CanopyPhaseTransitioner
from src.pga.ga_classes import Phase, ParentSelector, MutationAssigner, MutationMagnitudeAssigner, RegimeTransitioner
from src.pga.genetic_algorithm import GeneticAlgorithm
from src.pga.regime_one import GrowingPhaseParentSelector, GrowingPhaseMutationAssigner, GrowingPhaseMutationMagnitudeAssigner, \
    GrowingPhaseTransitioner, GetAllStimuliFunc
from src.pga.regime_zero import SeedingPhaseParentSelector, SeedingPhaseMutationAssigner, \
    SeedingPhaseMutationMagnitudeAssigner, SeedingPhaseTransitioner
from clat.util.connection import Connection


class GeneticAlgorithmConfig:
    ga_name = "New3D"
    num_trials_per_generation = 40


    def __init__(self,*,  database: str, base_intan_path: str):
        self.database = database
        self.base_intan_path = base_intan_path
        self.connection = self.make_connection()
        self.var_fetcher = GAVarParameterFetcher(self.connection)
        self.db_util = self.make_db_util()
        self.response_processor = self.make_response_processor()
        self.regimes = self.make_phases()

    def make_genetic_algorithm(self) -> GeneticAlgorithm:
        ga = GeneticAlgorithm(name=self.ga_name,
                              regimes=self.regimes,
                              db_util=self.db_util,
                              trials_per_generation=self.num_trials_per_generation,
                              lineage_distributor=self.make_lineage_distributor(),
                              response_parser=self.make_response_parser(),
                              response_processor=self.response_processor)
        return ga

    def make_phases(self):
        return [self.seeding_phase(),
                self.growing_phase(),
                self.canopy_phase(),
                self.leafing_phase()]

    def seeding_phase(self):
        return Phase(self.seeding_phase_parent_selector(),
                     self.seeding_phase_mutation_assigner(),
                     self.seeding_phase_mutation_magnitude_assigner(),
                     self.seeding_phase_transitioner())

    def seeding_phase_transitioner(self):
        return SeedingPhaseTransitioner(
            self.spontaneous_firing_rate(),
            self.seeding_phase_significance_threshold())

    def seeding_phase_mutation_magnitude_assigner(self):
        return SeedingPhaseMutationMagnitudeAssigner()

    def seeding_phase_mutation_assigner(self):
        return SeedingPhaseMutationAssigner()

    def seeding_phase_parent_selector(self):
        return SeedingPhaseParentSelector()

    def seeding_phase_significance_threshold(self):
        return self.var_fetcher.get("regime_zero_transition_significance_threshold", dtype=float)

    def spontaneous_firing_rate(self):
        # TODO: analyze real data to get this number
        return self.var_fetcher.get("regime_zero_transition_spontaneous_firing_rate", dtype=float)

    def growing_phase(self):
        return Phase(
            GrowingPhaseParentSelector(
                self.get_all_stimuli_func(),
                self.growing_phase_bin_proportions(),
                self.growing_phase_bin_sample_sizes()),
            self.growing_phase_mutation_assigner(),
            GrowingPhaseMutationMagnitudeAssigner(),
            GrowingPhaseTransitioner(
                self.convergence_threshold()
            ))

    def growing_phase_mutation_assigner(self):
        return GrowingPhaseMutationAssigner()

    def growing_phase_bin_proportions(self):
        return self.var_fetcher.get_array_parameter("regime_one_selection_bin_proportions", dtype=float)

    def growing_phase_bin_sample_sizes(self):
        return self.var_fetcher.get_array_parameter("regime_one_selection_bin_sample_size_proportions", dtype=float)

    def convergence_threshold(self):
        return self.var_fetcher.get("regime_one_transition_convergence_threshold", dtype=float)

    def get_all_stimuli_func(self):
        return GetAllStimuliFunc(db_util=self.db_util,
                                 ga_name=self.ga_name,
                                 response_processor=self.response_processor)

    def make_response_processor(self) -> ResponseProcessor:
        return ResponseProcessor(db_util=self.db_util,
                                 repetition_combination_strategy=mean,
                                 cluster_combination_strategy=sum)

    # should be (n-1)*pair_threshold_high where n is max number of components

    def canopy_phase(self):
        return Phase(
            CanopyPhaseParentSelector(
                self.percentage_of_max_threshold(),
                self.num_to_select()),
            CanopyPhaseMutationAssigner(),
            CanopyPhaseMutationMagnitudeAssigner(),
            CanopyPhaseTransitioner(self.pair_threshold_high(), self.pair_threshold_low()))

    def percentage_of_max_threshold(self):
        return self.var_fetcher.get("regime_two_selection_percentage_of_max_threshold", dtype=float)

    def num_to_select(self):
        return self.var_fetcher.get("regime_two_selection_num_to_select", dtype=int)

    def pair_threshold_high(self):
        return self.var_fetcher.get("regime_two_transition_pair_threshold_high", dtype=int)

    def pair_threshold_low(self):
        return self.var_fetcher.get("regime_two_transition_pair_threshold_low", dtype=int)

    def leafing_phase(self):
        return Phase(
            LeafingPhaseParentSelector(
                self.weight_func(),
                self.sampling_smoothing_bandwidth()),
            self.leafing_phase_mutation_assigner(),
            LeafingPhaseMutationMagnitudeAssigner(),
            LeafingPhaseTransitioner(self.get_under_sampling_threshold(), bandwidth=self.sampling_smoothing_bandwidth()))

    def leafing_phase_mutation_assigner(self):
        return LeafingPhaseMutationAssigner()

    def weight_func(self):
        return HighEndSigmoid(
            steepness=self.var_fetcher.get("regime_three_selection_weight_func_sigmoid_steepness", dtype=float),
            offset=self.var_fetcher.get("regime_three_selection_weight_func_sigmoid_offset", dtype=float))

    def sampling_smoothing_bandwidth(self):
        return self.var_fetcher.get("regime_three_selection_sampling_smoothing_bandwidth", dtype=float)

    def get_under_sampling_threshold(self):
        return self.var_fetcher.get("regime_three_transition_under_sampling_threshold", dtype=float)

    def make_response_parser(self):
        return ResponseParser(self.base_intan_path,
                              self.db_util)

    def make_lineage_distributor(self):
        return ClassicLineageDistributor(
            number_of_trials_per_generation=self.num_trials_per_generation,
            max_lineages_to_build=self.max_lineages_to_build(),
            number_of_new_lineages_per_generation=self.num_new_lineages_per_generation(),
            regimes=self.regimes,
            max_lineages_to_explore=self.max_lineages_to_explore())

    def max_lineages_to_explore(self):
        return self.var_fetcher.get("lineage_distribution_max_lineages_to_explore", dtype=int)

    def max_lineages_to_build(self):
        return self.var_fetcher.get("lineage_distribution_max_lineages_to_build", dtype=int)

    def num_new_lineages_per_generation(self):
        return self.var_fetcher.get("lineage_distribution_num_new_lineages_per_generation", dtype=int)

    def make_connection(self):
        return Connection(self.database)

    def make_db_util(self):
        return MultiGaDbUtil(self.connection)


class GAVarParameterFetcher:
    def __init__(self, connection: Connection):
        self.connection = connection

    def get_most_recent_experiment_and_gen_id(self):
        # Get the maximum experiment_id first
        self.connection.execute("SELECT MAX(experiment_id) FROM GAVar")
        max_experiment_id = self.connection.fetch_one()

        # Then get the maximum gen_id for that experiment_id
        query = "SELECT MAX(gen_id) FROM GAVar WHERE experiment_id=%s"
        self.connection.execute(query, (max_experiment_id,))
        max_gen_id = self.connection.fetch_one()

        return max_experiment_id, max_gen_id

    def get(self, name, dtype=str) -> Any:
        experiment_id, gen_id = self.get_most_recent_experiment_and_gen_id()
        query = "SELECT value FROM GAVar WHERE name=%s AND experiment_id=%s AND gen_id=%s AND arr_ind = 0"
        self.connection.execute(query, (name, experiment_id, gen_id))
        result = self.connection.fetch_one()
        return dtype(result)

    def get_array_parameter(self, name, dtype=str) -> list:
        experiment_id, gen_id = self.get_most_recent_experiment_and_gen_id()
        query = f"SELECT arr_ind, value FROM GAVar WHERE name = '{name}' AND experiment_id = {experiment_id} AND gen_id = {gen_id} ORDER BY arr_ind"
        self.connection.execute(query)
        result = self.connection.fetch_all()
        return [dtype(value) for _, value in result]
