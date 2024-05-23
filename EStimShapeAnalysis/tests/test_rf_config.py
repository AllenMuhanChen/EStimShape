import random
import unittest

from src.pga.config.rf_config import ZoomingPhaseParentSelector, ZoomSetHandler
from src.pga.ga_classes import Stimulus, LineageFactory


class TestZoomingPhase(unittest.TestCase):

    def setUp(self):
        self.selector = ZoomingPhaseParentSelector(
            spontaneous_firing_rate=15,
            significance_level=0.05,
            zoom_set_handler=MockZoomSetHandler()
        )

        stimuli = [Stimulus(i, "Test", response_rate=i, response_vector=[i for _ in range(10)]) for i in
                   [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]]
        # shuffle stimuli randomly
        random.shuffle(stimuli)


        self.lineage = LineageFactory.create_lineage_from_stimuli(stimuli)

    def test_select_parents(self):
        self.selector.select_parents(self.lineage, 10)


class MockZoomSetHandler(ZoomSetHandler):
    def is_no_set(self, stimulus: Stimulus) -> bool:
        if stimulus.response_rate == 20 or stimulus.response_rate == 30:
            return True

    def is_partial_set(self, stimulus):
        if stimulus.response_rate == 40 or stimulus.response_rate == 50:
            return True

    def is_full_set(self, stimulus):
        if stimulus.response_rate > 50:
            return True

    def get_how_many_stimuli_needed_to_make_full_set(self, stimulus):
        if self.is_partial_set(stimulus):
            return 1
        elif self.is_no_set(stimulus):
            return 2
