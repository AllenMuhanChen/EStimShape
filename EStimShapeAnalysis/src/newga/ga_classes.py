from __future__ import annotations
from abc import ABC, abstractmethod
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Protocol, Any

from util import time_util


class Stimulus:

    def __init__(self, stim_id: int, mutation_type: str, mutation_magnitude: float = None, response_vector=None,
                 driving_response=None):
        self.id = stim_id
        self.mutation_type = mutation_type
        self.mutation_magnitude = mutation_magnitude
        self.response_vector = response_vector
        self.response_rate = driving_response

    def set_parent_id(self, parent_id: int) -> None:
        self.parent = parent_id
    def __eq__(self, o: object) -> bool:
        return self.__dict__ == o.__dict__


class Lineage:
    def __init__(self, founder: Stimulus, regimes: [Regime]):
        self.id = founder.id
        self.stimuli = [founder]
        self.tree = Node(founder)
        self.regimes = regimes
        self.current_regime_index = 0
        self.age_in_generations = 0

    # def __init__(self, lineage_id: int, regimes: [Regime], tree: Node):
    #     self.id = lineage_id
    #     self.regimes = regimes
    #     self.tree = tree
    #     self.stimuli = tree.to_list()
    #     self.current_regime_index = 0
    #     self.age_in_generations = 0

    def generate_new_batch(self, batch_size: int) -> None:
        """
        Generate a new batch of stimuli by selecting parents and assigning mutation types
        using the current regime.
        """
        current_regime = self.regimes[self.current_regime_index]

        # Select parents from the current
        new_children = current_regime.generate_batch(self, batch_size)
        self.stimuli.append(new_children)
        for child in new_children:
            self.tree.add_child_to(child.parent, child)

        self.age_in_generations += 1

    def transition_regimes_if_needed(self) -> None:
        """
        Check if this lineage should transition to a new regime based on its performance.
        """
        current_regime = self.regimes[self.current_regime_index]
        if current_regime.should_transition(self):
            self.current_regime_index += 1

    def get_parent_of(self, child: Stimulus) -> Stimulus:
        return self.tree.find(child.parent).data


class Node:
    def __init__(self, data):
        self.data = data
        self.children = []

    def add_child(self, node):
        self.children.append(node)

    def add_child_to(self, parent_data, child_data):
        parent = self.find(parent_data)
        parent.add_child(child_data)

    def apply_to_children(self, function):
        for child in self.children:
            function(child)
            child.apply_to_children(function)

    def new_tree_from_function(self, function: callable[[Any], None]):
        new_tree = Node(function(self.data))
        for child in self.children:
            new_tree.add_child(child.new_tree_from_function(function))
        return new_tree

    def have_parent_apply_to_children(self, function: callable[[Node, Node], None]):
        for child in self.children:
            function(child, self)
            child.have_parent_apply_to_children(function)

    def find(self, parent_data) -> Node:
        if self.data == parent_data:
            return self
        for child in self.children:
            found = child.find(parent_data)
            if found:
                return found

    def to_xml(self):
        root = ET.Element("Node")
        root.text = str(self.data)
        for child in self.children:
            root.append(ET.fromstring(child.to_xml()))
        return ET.tostring(root, encoding='unicode')

    @classmethod
    def from_xml(cls, xml_str):
        root = ET.fromstring(xml_str)
        node = cls(root.text)
        for child_xml in root.findall('Node'):
            child_node = cls.from_xml(ET.tostring(child_xml, encoding='unicode'))
            node.add_child(child_node)
        return node

    def to_list(self):
        return [self.data] + [child.to_list() for child in self.children]


class Regime:
    def __init__(self, parent_selector: ParentSelector, mutation_assigner: MutationAssigner,
                 mutation_magnitude_assigner: MutationMagnitudeAssigner, regime_transitioner: RegimeTransitioner):
        self.parent_selector = parent_selector
        self.mutation_assigner = mutation_assigner
        self.mutation_magnitude_assigner = mutation_magnitude_assigner
        self.regime_transitioner = regime_transitioner

    def generate_batch(self, lineage: Lineage, batch_size: int):
        """
        Generate a new batch of stimuli by selecting parents and assigning mutation types and magnitudes.
        """
        parents = self.parent_selector.select_parents(lineage, batch_size)
        return [Stimulus(time_util.now(), self.mutation_assigner.assign_mutation(lineage),
                         mutation_magnitude=self.mutation_magnitude_assigner.assign_mutation_magnitude(lineage, parent))
                for parent in parents]

    def should_transition(self, lineage: Lineage):
        """
        Check if a lineage should transition to a new regime based on its performance.
        """
        return self.regime_transitioner.should_transition(lineage)


class ParentSelector(Protocol):
    @abstractmethod
    def select_parents(self, lineage: Lineage, batch_size: int) -> list[Stimulus]:
        pass


class MutationAssigner(Protocol):
    @abstractmethod
    def assign_mutation(self, lineage: Lineage):
        pass


class MutationMagnitudeAssigner(Protocol):
    @abstractmethod
    def assign_mutation_magnitude(self, lineage: Lineage, stimulus: Stimulus) -> float:
        pass


class RegimeTransitioner(Protocol):
    @abstractmethod
    def should_transition(self, lineage):
        pass


class LineageDistributor(Protocol):
    @abstractmethod
    def get_num_trials_for_lineage_ids(self, experiment_id: int) -> dict[int: int]:
        pass
