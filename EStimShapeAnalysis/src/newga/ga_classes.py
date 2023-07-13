from __future__ import annotations
from abc import ABC, abstractmethod
import xml.etree.ElementTree as ET

from util import time_util


class Stimulus:
    def __init__(self, stim_id: int, mutation_type: str, parent: Stimulus = None, mutation_magnitude: float = None,
                 response_rate=None):
        self.id = stim_id
        self.parent = parent
        self.mutation_type = mutation_type
        self.mutation_magnitude = mutation_magnitude
        self.response_rate = response_rate
        self.mutation_magnitude = None

    def set_response_rate(self, response_rate):
        """
        Set the response rate of the stimulus. This should be called after the stimulus is tested.
        """
        self.response_rate = response_rate

    def set_mutation_magnitude(self, mutation_magnitude):
        """
        Set the mutation magnitude of the stimulus. This should be called after the stimulus is tested.
        """
        self.mutation_magnitude = mutation_magnitude

    def __eq__(self, o: object) -> bool:
        return self.__dict__ == o.__dict__


class Lineage:
    def __init__(self, founder: Stimulus, regimes: [Regime]):
        self.id = founder.id
        self.stimuli = [founder]
        self.tree = Node(founder)
        self.regimes = regimes
        self.current_regime_index = 0
        self.gen_id = 0

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

        self.gen_id += 1

    def regime_transition(self) -> None:
        """
        Check if this lineage should transition to a new regime based on its performance.
        """
        current_regime = self.regimes[self.current_regime_index]
        if current_regime.should_transition(self):
            self.current_regime_index += 1


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

    def find(self, parent_data):
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


class Regime:
    def __init__(self, parent_selector, mutation_assigner, mutation_magnitude_assigner, regime_transitioner):
        self.parent_selector = parent_selector
        self.mutation_assigner = mutation_assigner
        self.mutation_magnitude_assigner = mutation_magnitude_assigner
        self.regime_transitioner = regime_transitioner

    def generate_batch(self, lineage: Lineage, batch_size: int):
        """
        Generate a new batch of stimuli by selecting parents and assigning mutation types and magnitudes.
        """
        parents = self.parent_selector.select_parents(lineage.stimuli, batch_size)
        return [Stimulus(time_util.now(), self.mutation_assigner.assign_mutation(lineage), parent=parent,
                         mutation_magnitude=self.mutation_magnitude_assigner.assign_mutation_magnitude(lineage, parent))
                for parent in parents]

    def should_transition(self, lineage: Lineage):
        """
        Check if a lineage should transition to a new regime based on its performance.
        """
        return self.regime_transitioner.should_transition(lineage)


class ParentSelector(ABC):
    @abstractmethod
    def select_parents(self, lineage: Lineage, batch_size: int):
        pass


class MutationAssigner(ABC):
    @abstractmethod
    def assign_mutation(self, lineage: Lineage):
        pass


class MutationMagnitudeAssigner(ABC):
    @abstractmethod
    def assign_mutation_magnitude(self, lineage: Lineage, stimulus: Stimulus) -> float:
        pass


class RegimeTransitioner(ABC):
    @abstractmethod
    def should_transition(self, lineage):
        pass
