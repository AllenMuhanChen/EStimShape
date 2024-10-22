import numpy as np

from src.pga.alexnet.AlexNetStimType import StimType
from src.pga.config.canopy_config import GeneticAlgorithmConfig
from src.pga.ga_classes import Phase, ParentSelector, Lineage, MutationAssigner, Stimulus, MutationMagnitudeAssigner, \
    RegimeTransitioner
from src.pga.regime_one import GrowingPhaseMutationMagnitudeAssigner


class AlexNetExperimentGeneticAlgorithmConfig(GeneticAlgorithmConfig):

    def make_phases(self):
        return [self.seeding_phase(),
                self.rf_location_phase(),
                self.growing_phase()]

    def rf_location_phase(self):
        return Phase(
            RFLocPhaseParentSelector(),
            RFLocPhaseMutationAssigner(),
            RFLocPhaseMutationMagnitudeAssigner(),
            RFLocPhaseTransitioner()
        )


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
        return data
