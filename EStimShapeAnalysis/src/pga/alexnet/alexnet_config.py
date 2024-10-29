from src.pga.alexnet.AlexNetStimType import StimType
from src.pga.alexnet.alexnet_genetic_algorithm import AlexNetGeneticAlgorithm
from src.pga.alexnet.alexnet_processor import AlexNetResponseProcessor
from src.pga.config.canopy_config import GeneticAlgorithmConfig
from src.pga.ga_classes import Phase, ParentSelector, Lineage, MutationAssigner, Stimulus, RegimeTransitioner
from src.pga.genetic_algorithm import GeneticAlgorithm
from src.pga.regime_one import GrowingPhaseMutationMagnitudeAssigner, GrowingPhaseParentSelector, \
    GrowingPhaseTransitioner, RankOrderedDistribution
from src.pga.response_processing import ResponseProcessor
from src.pga.alexnet.onnx_parser import AlexNetONNXResponseParser, UnitIdentifier
from src.pga.spike_parsing import ResponseParser
from src.pga.trial_generators import AlexNetGAJarTrialGenerator, TrialGenerator


class AlexNetExperimentGeneticAlgorithmConfig(GeneticAlgorithmConfig):
    unit_id = None

    def __init__(self, *, database: str, java_output_dir: str, allen_dist_dir: str, unit: UnitIdentifier):
        self.unit_id = unit
        super().__init__(database=database,
                         base_intan_path="None",
                         java_output_dir=java_output_dir,
                         allen_dist_dir=allen_dist_dir)

    def make_genetic_algorithm(self) -> GeneticAlgorithm:
        ga = AlexNetGeneticAlgorithm(
            name=self.ga_name,
            regimes=self.regimes,
            db_util=self.db_util,
            trials_per_generation=self.num_trials_per_generation,
            lineage_distributor=self.make_lineage_distributor(),
            response_parser=self.make_response_parser(),
            response_processor=self.response_processor,
            num_catch_trials=self.num_catch_trials,
            trial_generator=self.xper_trial_generator()
        )
        return ga

    def make_phases(self):
        return [self.seeding_phase(),
                self.rf_location_phase(),
                self.growing_phase]

    def seeding_phase_mutation_assigner(self):
        return AlexNetSeedingPhaseMutationAssigner()

    def seeding_phase_transitioner(self):
        return AlexNetSeedingPhaseTransitioner()

    def rf_location_phase(self):
        return Phase(
            RFLocPhaseParentSelector(),
            RFLocPhaseMutationAssigner(),
            RFLocPhaseMutationMagnitudeAssigner(),
            RFLocPhaseTransitioner()
        )

    @property
    def growing_phase(self):
        return Phase(
            AlexNetGrowingPhaseParentSelector(self.growing_phase_bin_proportions(),
                                              self.growing_phase_bin_sample_sizes()),
            AlexNetGrowingPhaseMutationAssigner(),
            GrowingPhaseMutationMagnitudeAssigner(),
            DontTransitioner()
        )

    def make_response_parser(self) -> ResponseParser:
        """
        This response parser will differ in that all it needs to do is read Stim paths
        and show those to AlexNet and save those activations into UnitActivations table.
        """
        return AlexNetONNXResponseParser(self.connection(),
                                          "/home/r2_allen/git/EStimShape/EStimShapeAnalysis/data/AlexNetONNX_with_conv3",
                                         self.unit_id)

    def make_response_processor(self) -> AlexNetResponseProcessor:
        """
        This one will be different in that it just needs to read the one Unit activation to
        StimGaInfo
        """
        return AlexNetResponseProcessor(self.connection(), self.unit_id)

    def xper_trial_generator(self) -> TrialGenerator:
        return AlexNetGAJarTrialGenerator(self.java_output_dir, self.allen_dist_dir)


class DontTransitioner(RegimeTransitioner):
    def should_transition(self, lineage: Lineage) -> bool:
        return False

    def get_transition_data(self, lineage: Lineage) -> str:
        return "None"


class AlexNetSeedingPhaseMutationAssigner(MutationAssigner):
    def assign_mutation(self, lineage, parent: Stimulus):
        # In Regime Zero, all stimuli are assigned the "RegimeZero" mutation.
        return StimType.SEEDING.value


class AlexNetSeedingPhaseTransitioner(RegimeTransitioner):
    def should_transition(self, lineage: Lineage) -> bool:
        for stimulus in lineage.stimuli:
            if stimulus.response_rate > 0:
                return True

    def get_transition_data(self, lineage: Lineage) -> str:
        return "None"


class RFLocPhaseParentSelector(ParentSelector):
    proportions = [0.5, 0.2, 0.2, 0.1]
    bin_sample_sizes_proportions = [0.0, 0.25, 0.25, 0.5]

    def select_parents(self, lineage: Lineage, batch_size: int) -> list[Stimulus]:
        stimuli = lineage.stimuli
        # filter out negative stimuli
        stimuli = [stimulus for stimulus in stimuli if stimulus.response_rate > 0]

        rank_ordered_distribution = RankOrderedDistribution(lineage.stimuli, self.proportions)
        if not stimuli:
            return []

        sampled_stimuli_from_lineage = rank_ordered_distribution.sample_total_amount_across_bins(
            bin_sample_probabilities=self.bin_sample_sizes_proportions, total=batch_size)

        return sampled_stimuli_from_lineage


class RFLocPhaseMutationAssigner(MutationAssigner):
    def assign_mutation(self, lineage: Lineage, parent: Stimulus):
        # Assign a mutation to the stimulus
        return StimType.RF_LOCATE.value


class RFLocPhaseMutationMagnitudeAssigner(GrowingPhaseMutationMagnitudeAssigner):
    min_magnitude = 0.1
    max_magnitude = 1.0
    overlap = 0.5


class RFLocPhaseTransitioner(RegimeTransitioner):
    def __init__(self):
        self.threshold_response = None
        self.threshold_percentage_of_max = 0.9  # percentage of max response to consider a stimulus passed the threshold
        self.num_pass_required = 5  # percentage of stimuli that must pass the threshold

        # data
        self.passed_threshold = None

    def should_transition(self, lineage: Lineage) -> bool:
        # check if we have enough stimuli in the top 90% of the highest response
        stimuli = [stimulus for stimulus in lineage.stimuli if stimulus.response_rate > 0]
        sorted_responses = sorted(stimuli, reverse=True, key=lambda x: x.response_rate)
        highest_response = sorted_responses[0].response_rate
        self.threshold_response = self.threshold_percentage_of_max * highest_response
        self.passed_threshold = [stimulus for stimulus in sorted_responses if
                                 stimulus.response_rate >= self.threshold_response]

        self.num_required_to_pass = self.num_pass_required
        return len(self.passed_threshold) >= self.num_required_to_pass

    def get_transition_data(self, lineage: Lineage) -> str:
        data = {"threshold": self.threshold_response, "num_passed": len(self.passed_threshold),
                "num_required": self.num_required_to_pass}
        return str(data)


class AlexNetGrowingPhaseMutationAssigner(MutationAssigner):
    def assign_mutation(self, lineage, parent: Stimulus) -> str:
        return StimType.GROWING.value


class AlexNetGrowingPhaseParentSelector(GrowingPhaseParentSelector):

    def select_parents(self, lineage: Lineage, batch_size: int) -> list[Stimulus]:
        # filter out negative stimuli
        stimuli = [stimulus for stimulus in lineage.stimuli if stimulus.response_rate > 0]

        stimuli = self._filter_to_best_rf(stimuli)

        rank_ordered_distribution = RankOrderedDistribution(lineage.stimuli, self.bin_proportions)
        if not stimuli:
            return []

        sampled_stimuli_from_lineage = rank_ordered_distribution.sample_total_amount_across_bins(
            bin_sample_probabilities=self.bin_sample_probabilities, total=batch_size)

        return sampled_stimuli_from_lineage

    def _filter_to_best_rf(self, stimuli):
        # filter out all RF_LOCATE/SEED that isn't the best in the lineage by response rate
        candidates = []
        for stimulus in stimuli:
            if self._is_rf_related(stimulus):
                candidates.append(stimulus)
        best_rf_candidate = max(candidates, key=lambda x: x.response_rate)
        # remove all rf_locate/seed stimuli that aren't the best candidate
        stimuli = [stimulus for stimulus in stimuli if
                   not self._is_rf_related(stimulus) or stimulus == best_rf_candidate]
        return stimuli

    def _is_rf_related(self, stimulus):
        return stimulus.mutation_type == StimType.RF_LOCATE.value or stimulus.mutation_type == StimType.SEEDING.value
