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

    def should_transition(self, lineage: Lineage) -> bool:
        # check if we have enough stimuli with above zero response
        pass
