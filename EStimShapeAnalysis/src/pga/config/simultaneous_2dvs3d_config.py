from __future__ import annotations
from enum import Enum

import time

from abc import abstractmethod
from numpy.ma import mean

from typing import Protocol, List

from clat.util import time_util
from src.pga.config.twod_threed_config import TwoDThreeDGAConfig
from src.pga.ga_classes import Lineage, Stimulus, SideTest
from src.pga.mock.alexnet_mock_ga import AlexNetMockResponseParser
from src.pga.response_processing import GAResponseProcessor


class Simultaneous3Dvs2DConfig(TwoDThreeDGAConfig):
    """
    Configuration for a GA that runs a side test which takes top N 2D and top N 3D stimuli from previous generation
    and tests 2d vs 3d on them each generation. This ensures we have answers for 2D vs 3D
    no matter when we stop the GA.

    @param is_alexnet_mock: If True, use the AlexNet mock response parser. Should also
    set to use MockPGA java config class in xper.properties.
    """

    def __init__(self, *, is_alexnet_mock, database: str, base_intan_path: str, java_output_dir: str,
                 allen_dist_dir: str):
        super().__init__(database=database, base_intan_path=base_intan_path, java_output_dir=java_output_dir,
                         allen_dist_dir=allen_dist_dir)
        self.is_alexnet_mock = is_alexnet_mock

    def side_tests(self):
        """
        Returns a list of side tests to run.
        """
        return [
            DnessSideTest(n_top_3d=2, n_top_2d=2)
        ]

    def make_response_parser(self):
        if self.is_alexnet_mock:
            return AlexNetMockResponseParser(db_util=self.db_util)
        else:
            return super().make_response_parser()


class DnessSideTest(SideTest):
    """
    A side test that runs the 3Dvs2D experiment on the given lineages.
    """

    def __init__(self, n_top_3d=2, n_top_2d=2):
        self.n_top_3d = n_top_3d
        self.n_top_2d = n_top_2d

        self.stimuli_from_this_gen_2d: List[Stimulus] = []
        self.stimuli_from_this_gen_3d: List[Stimulus] = []

        self.lineages_for_stim = {}

    def run(self, lineages: List[Lineage], gen_id: int):
        top_2d, top_3d = self._collect_stims_to_test(gen_id, lineages)

        for stim_to_test in top_2d:
            self._generate_side_test_stim(stim_to_test, SIDETEST_2Dvs3D_Type.SIDETEST_2Dvs3D_Type, gen_id)
            # self._generate_side_test_stim(stim_to_test, SIDETEST_2Dvs3D_Type.THREED_SHADE, gen_id)
            # self._generate_side_test_stim(stim_to_test, SIDETEST_2Dvs3D_Type.THREED_SPECULAR, gen_id)

        for stim_to_test in top_3d:
            self._generate_side_test_stim(stim_to_test, SIDETEST_2Dvs3D_Type.SIDETEST_2Dvs3D_Type, gen_id)
            # self._generate_side_test_stim(stim_to_test, SIDETEST_2Dvs3D_Type.TWOD_HIGH, gen_id)
            # self._generate_side_test_stim(stim_to_test, SIDETEST_2Dvs3D_Type.TWOD_LOW, gen_id)

    def _collect_stims_to_test(self, gen_id, lineages):
        # Collect all stimuli from this generation
        self.stimuli_from_this_gen_2d = []
        self.stimuli_from_this_gen_3d = []
        for lineage in lineages:
            for stim_to_test in lineage.stimuli:
                if stim_to_test.gen_id == gen_id - 1:
                    if not is_side_test_stimulus(stim_to_test):
                        if stim_to_test.response_rate is not None:
                            self._assign_2d_or_3d(stim_to_test, lineage)
                            self.lineages_for_stim[stim_to_test.id] = lineage


        # Now we have all stimuli from this generation, we can extract top N
        # 2D and top N 3D stimuli
        top_2d = sorted(
            self.stimuli_from_this_gen_2d,
            key=lambda x: x.response_rate,
            reverse=True,
        )[:self.n_top_2d]
        top_3d = sorted(
            self.stimuli_from_this_gen_3d,
            key=lambda x: x.response_rate,
            reverse=True,
        )[:self.n_top_3d]
        return top_2d, top_3d


    def _generate_side_test_stim(self, stim_to_test, mutation_type: SIDETEST_2Dvs3D_Type, gen_id):
        """
        Generate a new stimulus from the given stimulus with the given mutation type.
        Then will add this stimulus to the Lineage's stimuli list and tree structure.
        """
        new_stimulus = Stimulus(time_util.now(),
                                mutation_type.value,
                                mutation_magnitude=0,
                                gen_id=gen_id,
                                parent_id=stim_to_test.id
                                )
        time.sleep(0.001)
        lineage = self.lineages_for_stim[stim_to_test.id]
        lineage.tree.add_child_to(stim_to_test, new_stimulus)
        lineage.stimuli.append(new_stimulus)

    def _assign_2d_or_3d(self, stimulus: Stimulus, lineage: Lineage):
        if "CATCH" in stimulus.mutation_type:
            pass
        if "Zooming" in stimulus.mutation_type:
            parent = lineage.get_parent_of(stimulus)
            if "2D" in parent.mutation_type:
                self.stimuli_from_this_gen_2d.append(stimulus)
            else:
                self.stimuli_from_this_gen_3d.append(stimulus)
        elif "2D" in stimulus.mutation_type:
            # Assign to 2D
            self.stimuli_from_this_gen_2d.append(stimulus)
        else:
            self.stimuli_from_this_gen_3d.append(stimulus)


def is_side_test_stimulus(stimulus):
    return "SIDETEST" in stimulus.mutation_type




class SIDETEST_2Dvs3D_Type(Enum):
    SIDETEST_2Dvs3D_Type = "SIDETEST_2Dvs3D"
    THREED_SHADE = "SIDETEST_2Dvs3D_3D_SHADE"
    THREED_SPECULAR = "SIDETEST_2Dvs3D_3D_SPECULAR"
    TWOD_HIGH = "SIDETEST_2Dvs3D_2D_HIGH"
    TWOD_LOW = "SIDETEST_2Dvs3D_2D_LOW"
