import unittest
from typing import List

from src.pga.ga_classes import Stimulus, Lineage, LineageFactory
from src.pga.shuffle_side_test import ShuffleSideTest, ShuffleType


class TestShuffleSideTest(unittest.TestCase):
    GEN_ID = 5
    PREV_GEN = GEN_ID - 1

    EXPECTED_SHUFFLES = ["SHUFFLE_PIXEL", "SHUFFLE_PHASE", "SHUFFLE_MAGNITUDE"]

    def _single_stim_lineage(self, stim: Stimulus) -> Lineage:
        return LineageFactory.create_lineage_from_stimuli([stim])

    def _shuffle_children(self, lineage: Lineage):
        founder = lineage.tree.data
        return [s for s in lineage.stimuli if s is not founder and "SHUFFLE" in s.mutation_type]

    def test_makes_three_shuffles_for_top_responder(self):
        side_test = ShuffleSideTest(n_top_responders=1)
        parent = self._single_stim_lineage(
            Stimulus(1, "REGIME_ONE", response_rate=50, gen_id=self.PREV_GEN))

        side_test.run([parent], self.GEN_ID)

        children = self._shuffle_children(parent)
        self.assertEqual([c.mutation_type for c in children], self.EXPECTED_SHUFFLES)
        for child in children:
            self.assertEqual(child.gen_id, self.GEN_ID)
            self.assertEqual(child.parent_id, 1)

    def test_only_top_n_selected_globally(self):
        side_test = ShuffleSideTest(n_top_responders=1)
        high = self._single_stim_lineage(
            Stimulus(1, "REGIME_ONE", response_rate=50, gen_id=self.PREV_GEN))
        low = self._single_stim_lineage(
            Stimulus(2, "REGIME_ONE", response_rate=10, gen_id=self.PREV_GEN))

        side_test.run([high, low], self.GEN_ID)

        self.assertEqual([c.mutation_type for c in self._shuffle_children(high)], self.EXPECTED_SHUFFLES)
        self.assertEqual(self._shuffle_children(low), [])

    def test_respects_n_top_responders(self):
        side_test = ShuffleSideTest(n_top_responders=2)
        high = self._single_stim_lineage(
            Stimulus(1, "REGIME_ONE", response_rate=50, gen_id=self.PREV_GEN))
        mid = self._single_stim_lineage(
            Stimulus(2, "REGIME_ONE", response_rate=30, gen_id=self.PREV_GEN))
        low = self._single_stim_lineage(
            Stimulus(3, "REGIME_ONE", response_rate=10, gen_id=self.PREV_GEN))

        side_test.run([high, mid, low], self.GEN_ID)

        self.assertEqual([c.mutation_type for c in self._shuffle_children(high)], self.EXPECTED_SHUFFLES)
        self.assertEqual([c.mutation_type for c in self._shuffle_children(mid)], self.EXPECTED_SHUFFLES)
        self.assertEqual(self._shuffle_children(low), [])

    def test_filters_ineligible_stimuli(self):
        side_test = ShuffleSideTest(n_top_responders=10)
        catch = self._single_stim_lineage(
            Stimulus(1, "CATCH", response_rate=90, gen_id=self.PREV_GEN))
        baseline = self._single_stim_lineage(
            Stimulus(2, "BASELINE", response_rate=90, gen_id=self.PREV_GEN))
        already_shuffled = self._single_stim_lineage(
            Stimulus(3, "SHUFFLE_PIXEL", response_rate=90, gen_id=self.PREV_GEN))
        no_response = self._single_stim_lineage(
            Stimulus(4, "REGIME_ONE", response_rate=None, gen_id=self.PREV_GEN))
        wrong_gen = self._single_stim_lineage(
            Stimulus(5, "REGIME_ONE", response_rate=90, gen_id=self.PREV_GEN - 1))
        eligible = self._single_stim_lineage(
            Stimulus(6, "REGIME_ONE", response_rate=20, gen_id=self.PREV_GEN))

        lineages = [catch, baseline, already_shuffled, no_response, wrong_gen, eligible]
        side_test.run(lineages, self.GEN_ID)

        for lineage in [catch, baseline, already_shuffled, no_response, wrong_gen]:
            self.assertEqual(self._shuffle_children(lineage), [])
        self.assertEqual([c.mutation_type for c in self._shuffle_children(eligible)], self.EXPECTED_SHUFFLES)

    def test_shuffle_type_values(self):
        self.assertEqual(ShuffleType.PIXEL.value, "SHUFFLE_PIXEL")
        self.assertEqual(ShuffleType.PHASE.value, "SHUFFLE_PHASE")
        self.assertEqual(ShuffleType.MAGNITUDE.value, "SHUFFLE_MAGNITUDE")


if __name__ == "__main__":
    unittest.main()
