from src.pga.alexnet.AlexNetStimType import StimType
from src.pga.alexnet.alexnet_genetic_algorithm import AlexNetGeneticAlgorithm
from src.pga.alexnet.alexnet_processor import AlexNetResponseProcessor
from src.pga.config.canopy_config import GeneticAlgorithmConfig
from src.pga.ga_classes import Phase, ParentSelector, Lineage, MutationAssigner, Stimulus, RegimeTransitioner
from src.pga.genetic_algorithm import GeneticAlgorithm
from src.pga.regime_one import GrowingPhaseMutationMagnitudeAssigner, GrowingPhaseParentSelector, \
    GrowingPhaseTransitioner
from src.pga.response_processing import ResponseProcessor
from src.pga.alexnet.onnx_parser import AlexNetIntanResponseParser, UnitIdentifier
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
                self.growing_phase()]

    def seeding_phase_mutation_assigner(self):
        return AlexNetSeedingPhaseMutationAssigner()

    def rf_location_phase(self):
        return Phase(
            RFLocPhaseParentSelector(),
            RFLocPhaseMutationAssigner(),
            RFLocPhaseMutationMagnitudeAssigner(),
            RFLocPhaseTransitioner()
        )

    def growing_phase(self):
        return Phase(
            GrowingPhaseParentSelector(self.growing_phase_bin_proportions(), self.growing_phase_bin_sample_sizes()),
            AlexNetGrowingPhaseMutationAssigner(),
            GrowingPhaseMutationMagnitudeAssigner(),
            GrowingPhaseTransitioner(
                self.convergence_threshold()
            )
        )

    def make_response_parser(self) -> ResponseParser:
        """
        This response parser will differ in that all it needs to do is read Stim paths
        and show those to AlexNet and save those activations into UnitActivations table.
        """
        return AlexNetIntanResponseParser(self.connection(),
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



class AlexNetSeedingPhaseMutationAssigner(MutationAssigner):
    def assign_mutation(self, lineage, parent: Stimulus):
        # In Regime Zero, all stimuli are assigned the "RegimeZero" mutation.
        return StimType.SEEDING.value


class AlexNetGrowingPhaseMutationAssigner(MutationAssigner):
    def assign_mutation(self, lineage, parent: Stimulus) -> str:
        return StimType.GROWING.value


class RFLocPhaseParentSelector(ParentSelector):
    def select_parents(self, lineage: Lineage, batch_size: int) -> list[Stimulus]:
        sorted_responses = sorted(lineage.stimuli, reverse=True, key=lambda x: x.response_rate)
        return [stimulus for stimulus in sorted_responses[:batch_size]]


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
        self.percent_pass_required = 0.33  # percentage of stimuli that must pass the threshold

        # data
        self.passed_threshold = None

    def should_transition(self, lineage: Lineage) -> bool:
        # check if we have enough stimuli in the top 90% of the highest response
        sorted_responses = sorted(lineage.stimuli, reverse=True, key=lambda x: x.response_rate)
        highest_response = sorted_responses[0].response_rate
        self.threshold_response = self.threshold_percentage_of_max * highest_response
        self.passed_threshold = [stimulus for stimulus in sorted_responses if
                                 stimulus.response_rate >= self.threshold_response]

        return len(self.passed_threshold) >= self.percent_pass_required * len(sorted_responses)

    def get_transition_data(self, lineage: Lineage) -> str:
        data = {"threshold": self.threshold_response, "num_passed": len(self.passed_threshold)}
        return str(data)
