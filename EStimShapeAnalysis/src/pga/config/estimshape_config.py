from src.pga.config.simultaneous_2dvs3d_config import Simultaneous3Dvs2DConfig
from src.pga.ga_classes import Phase


class EStimPhaseParentSelector:
    pass


class EStimPhaseMutationAssigner:
    pass


class EStimPhaseMagnitudeAssigner:
    pass


class EStimPhaseTransitioner:
    pass


class EStimShapeConfig(Simultaneous3Dvs2DConfig):
    """
    Configuration to add a fourth phase to make variants of stimuli to test in EStimShape.
    """
    def make_phases(self):
        return [self.seeding_phase(),
                self.zooming_phase(),
                self.growing_phase(),
                self.estim_variant_phase()
                ]

    def estim_variant_phase(self):
        return Phase(
            EStimPhaseParentSelector(),
            EStimPhaseMutationAssigner(),
            EStimPhaseMagnitudeAssigner(),
            EStimPhaseTransitioner(),
        )
