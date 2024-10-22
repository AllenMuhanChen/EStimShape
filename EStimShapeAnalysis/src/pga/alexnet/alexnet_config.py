from src.pga.alexnet.AlexNetStimType import StimType
from src.pga.config.canopy_config import GeneticAlgorithmConfig
from src.pga.config.twod_threed_config import TwoDThreeDGAConfig
from src.pga.ga_classes import Phase, ParentSelector, Lineage, MutationAssigner, Stimulus, MutationMagnitudeAssigner, \
    RegimeTransitioner


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
            self.rf_loc_phase_transitioner()
        )


class RFLocPhaseParentSelector(ParentSelector):
    def select_parent(self, lineage: Lineage, batch_size: int):
        # We choose any parent with an above zero response?
        # We choose the parents with the highest response?
        # We should be able to do multiple generations of this if we need to
        pass


class RFLocPhaseMutationAssigner(MutationAssigner):
    def assign_mutation(self, lineage: Lineage, parent: Stimulus):
        # Assign a mutation to the stimulus
        return StimType.RF_LOCATE.value


class RFLocPhaseMutationMagnitudeAssigner(MutationMagnitudeAssigner):

    def assign_mutation_magnitude(self, lineage: Lineage, stimulus: Stimulus) -> float:
        return 1.0


class RFLocPhaseTransitioner(RegimeTransitioner):

    def should_transition(self, lineage: Lineage) -> bool:
        # check if we have enough stimuli with above zero response
        pass


