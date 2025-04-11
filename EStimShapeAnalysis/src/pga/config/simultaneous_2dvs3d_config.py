from __future__ import annotations
from enum import Enum

import time

from abc import abstractmethod

from typing import Protocol, List

from clat.util import time_util
from src.pga.config.twod_threed_config import TwoDThreeDGAConfig
from src.pga.ga_classes import Lineage, Stimulus
from src.pga.regime_type import RegimeType


class Simultaneous3Dvs2DConfig(TwoDThreeDGAConfig):
    """
    Configuration for a GA that takes top N 2D and top N 3D stimuli from previous generation
    and tests 2d vs 3d on them each generation. This ensures we have answers for 2D vs 3D
    no matter when we stop the GA.
    """
    pass


class SideTest(Protocol):
    @abstractmethod
    def run(self, experiment_id: int, lineages: List[Lineage], gen_id: int):
        pass


class DnessSideTest(SideTest):
    """
    A side test that runs the 3Dvs2D experiment on the given lineages.
    """

    def __init__(self, experiment_id: int, lineages: int, gen_id: int, n_top_3d=2, n_top_2d=2):
        self.experiment_id = experiment_id
        self.lineages = lineages
        self.gen_id = gen_id
        self.n_top_3d = n_top_3d
        self.n_top_2d = n_top_2d

        self.stimuli_from_this_gen_2d: List[Stimulus] = []
        self.stimuli_from_this_gen_3d: List[Stimulus] = []

    def run(self, experiment_id: int, lineages: List[Lineage], gen_id: int):
        top_2d, top_3d = self._collect_stims_to_test(gen_id, lineages)

        for stim_to_test in top_2d:
            self._generate_side_test_stim(stim_to_test, SIDETEST_2Dvs3D_Type.THREED_SHADE, gen_id)
            self._generate_side_test_stim(stim_to_test, SIDETEST_2Dvs3D_Type.THREED_SPECULAR, gen_id)

        for stim_to_test in top_3d:
            self._generate_side_test_stim(stim_to_test, SIDETEST_2Dvs3D_Type.TWOD_HIGH, gen_id)
            self._generate_side_test_stim(stim_to_test, SIDETEST_2Dvs3D_Type.TWOD_LOW, gen_id)

    def _collect_stims_to_test(self, gen_id, lineages):
        # Collect all stimuli from this generation
        self.stimuli_from_this_gen_2d = []
        self.stimuli_from_this_gen_3d = []
        for lineage in lineages:
            for stim_to_test in lineage.stimuli:
                if stim_to_test.gen_id == gen_id:
                    if not is_side_test_stimulus(stim_to_test):
                        self._assign_2d_or_3d(stim_to_test, lineage)
                        stim_to_test.lineage = lineage  # create new reference to containing lineage to use later

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

    @staticmethod
    def _generate_side_test_stim(stimulus, mutation_type: SIDETEST_2Dvs3D_Type, gen_id):
        """
        Generate a new stimulus from the given stimulus with the given mutation type.
        Then will add this stimulus to the Lineage's stimuli list and tree structure.
        """
        new_stimulus = Stimulus(time_util.now(),
                                mutation_type.value,
                                mutation_magnitude=0,
                                gen_id=gen_id,
                                parent_id=stimulus.id
                                )
        time.sleep(0.001)
        lineage = stimulus.lineage
        lineage.tree.add_child_to(lineage.get_parent_of(stimulus), new_stimulus)
        lineage.stimuli.extend(new_stimulus)

    def _assign_2d_or_3d(self, stimulus: Stimulus, lineage: Lineage):
        if "Zooming" in stimulus.mutation_type:
            self._assign_2d_or_3d(lineage.get_parent_of(stimulus), lineage)
        elif "2D" in stimulus.mutation_type:
            # Assign to 2D
            self.stimuli_from_this_gen_2d.append(stimulus)
        else:
            self.stimuli_from_this_gen_3d.append(stimulus)


def is_side_test_stimulus(stimulus):
    return "SIDETEST" in stimulus.mutation_type


class SIDETEST_2Dvs3D_Type(Enum):
    THREED_SHADE = "3D_SHADE"
    THREED_SPECULAR = "3D_SPECULAR"
    TWOD_HIGH = "2D_HIGH"
    TWOD_LOW = "2D_LOW"
