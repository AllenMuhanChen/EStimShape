import unittest

from src.pga.ga_classes import Stimulus, Lineage, LineageFactory
from src.pga.lighting_side_test import LightingSideTest, LIGHTING_MUTATION_TYPE, DEFAULT_LIGHTING_ANGLES


class FakeTextureConn:
    """Minimal stand-in for a clat Connection that answers StimTexture lookups."""

    def __init__(self, texture_for_id=None, default="SHADE"):
        self.texture_for_id = texture_for_id or {}
        self.default = default
        self._pending = None

    def execute(self, query, params=None):
        self._pending = self.texture_for_id.get(params[0], self.default) if params else None

    def fetch_one(self):
        return self._pending


class TestLightingSideTest(unittest.TestCase):
    GEN_ID = 5
    PREV_GEN = GEN_ID - 1

    def _side_test(self, n, textures=None, light_angles=DEFAULT_LIGHTING_ANGLES) -> LightingSideTest:
        return LightingSideTest(conn=FakeTextureConn(textures), n_top_responders=n, light_angles=light_angles)

    def _single_stim_lineage(self, stim: Stimulus) -> Lineage:
        return LineageFactory.create_lineage_from_stimuli([stim])

    def _lighting_children(self, lineage: Lineage):
        founder = lineage.tree.data
        return [s for s in lineage.stimuli if s is not founder and s.mutation_type == LIGHTING_MUTATION_TYPE]

    def _angles(self, lineage: Lineage):
        return [s.mutation_magnitude for s in self._lighting_children(lineage)]

    def test_makes_a_variant_per_angle_for_top_3d(self):
        side_test = self._side_test(1)
        parent = self._single_stim_lineage(
            Stimulus(1, "REGIME_ONE", response_rate=50, gen_id=self.PREV_GEN))

        side_test.run([parent], self.GEN_ID)

        children = self._lighting_children(parent)
        # One "LIGHTING" stimulus per angle, with the angle carried in mutation_magnitude.
        self.assertEqual([c.mutation_type for c in children],
                         [LIGHTING_MUTATION_TYPE] * len(DEFAULT_LIGHTING_ANGLES))
        self.assertEqual(self._angles(parent), list(DEFAULT_LIGHTING_ANGLES))
        for child in children:
            self.assertEqual(child.gen_id, self.GEN_ID)
            self.assertEqual(child.parent_id, 1)

    def test_custom_angles(self):
        side_test = self._side_test(1, light_angles=(-30.0, 0.0, 30.0))
        parent = self._single_stim_lineage(
            Stimulus(1, "REGIME_ONE", response_rate=50, gen_id=self.PREV_GEN))

        side_test.run([parent], self.GEN_ID)

        self.assertEqual(self._angles(parent), [-30.0, 0.0, 30.0])

    def test_only_top_n_selected_globally(self):
        side_test = self._side_test(1)
        high = self._single_stim_lineage(
            Stimulus(1, "REGIME_ONE", response_rate=50, gen_id=self.PREV_GEN))
        low = self._single_stim_lineage(
            Stimulus(2, "REGIME_ONE", response_rate=10, gen_id=self.PREV_GEN))

        side_test.run([high, low], self.GEN_ID)

        self.assertEqual(self._angles(high), list(DEFAULT_LIGHTING_ANGLES))
        self.assertEqual(self._lighting_children(low), [])

    def test_skips_2d_stimuli(self):
        # The 2D stimulus is the higher responder, but only the 3D one gets lighting variants.
        side_test = self._side_test(1, textures={1: "2D", 2: "SPECULAR"})
        two_d = self._single_stim_lineage(
            Stimulus(1, "REGIME_ONE", response_rate=90, gen_id=self.PREV_GEN))
        three_d = self._single_stim_lineage(
            Stimulus(2, "REGIME_ONE", response_rate=30, gen_id=self.PREV_GEN))

        side_test.run([two_d, three_d], self.GEN_ID)

        self.assertEqual(self._lighting_children(two_d), [])
        self.assertEqual(self._angles(three_d), list(DEFAULT_LIGHTING_ANGLES))

    def test_filters_ineligible_stimuli(self):
        side_test = self._side_test(10)
        catch = self._single_stim_lineage(
            Stimulus(1, "CATCH", response_rate=90, gen_id=self.PREV_GEN))
        baseline = self._single_stim_lineage(
            Stimulus(2, "BASELINE", response_rate=90, gen_id=self.PREV_GEN))
        shuffled = self._single_stim_lineage(
            Stimulus(3, "SHUFFLE_PIXEL", response_rate=90, gen_id=self.PREV_GEN))
        already_lit = self._single_stim_lineage(
            Stimulus(4, LIGHTING_MUTATION_TYPE, mutation_magnitude=45.0, response_rate=90, gen_id=self.PREV_GEN))
        no_response = self._single_stim_lineage(
            Stimulus(5, "REGIME_ONE", response_rate=None, gen_id=self.PREV_GEN))
        wrong_gen = self._single_stim_lineage(
            Stimulus(6, "REGIME_ONE", response_rate=90, gen_id=self.PREV_GEN - 1))
        eligible = self._single_stim_lineage(
            Stimulus(7, "REGIME_ONE", response_rate=20, gen_id=self.PREV_GEN))

        lineages = [catch, baseline, shuffled, already_lit, no_response, wrong_gen, eligible]
        side_test.run(lineages, self.GEN_ID)

        for lineage in [catch, baseline, shuffled, already_lit, no_response, wrong_gen]:
            self.assertEqual(self._lighting_children(lineage), [])
        self.assertEqual(self._angles(eligible), list(DEFAULT_LIGHTING_ANGLES))


if __name__ == "__main__":
    unittest.main()
