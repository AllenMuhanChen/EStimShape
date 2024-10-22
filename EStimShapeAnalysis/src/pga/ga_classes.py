from __future__ import annotations

import time
import xml.etree.ElementTree as ET
from abc import abstractmethod
from typing import Protocol, Any

from clat.util import time_util


class Stimulus:
    stim_id: int
    mutation_type: str
    mutation_magnitude: float
    response_rate: float
    response_vector: [float]
    parent_id: int
    gen_id: int

    def __init__(self, stim_id: int, mutation_type: str, mutation_magnitude: float = None, response_vector=None,
                 response_rate=None, parent_id=None, gen_id=None):
        self.id = stim_id
        self.mutation_type = mutation_type
        self.mutation_magnitude = mutation_magnitude
        self.response_vector = response_vector
        self.response_rate = response_rate
        self.parent_id = parent_id
        self.gen_id = gen_id

    def set_parent(self, parent_id: int) -> None:
        self.parent_id = parent_id

    def __eq__(self, o: object) -> bool:
        return self.__dict__ == o.__dict__


class Lineage:
    def __init__(self, founder: Stimulus, regimes: [Phase], current_regime_index=0, tree=None, gen_id=1):
        self.id = founder.id
        if tree is None:
            self.stimuli = [founder]
            self.tree = Node(founder)
        else:
            self.tree = tree
            self.stimuli = tree.to_list()
        self.lineage_data = None
        self.regimes = regimes
        self.current_regime_index = current_regime_index
        self.gen_id = gen_id

    def generate_new_batch(self, batch_size: int) -> None:
        """
        Generate a new batch of stimuli by selecting parents and assigning mutation types
        using the current regime.
        """
        current_regime = self.regimes[self.current_regime_index]

        # Select parents from the current
        parents, children = current_regime.generate_batch(self, batch_size, self.gen_id)

        for parent, child in zip(parents, children):
            child.parent_id = parent.id
            self.tree.add_child_to(parent, child=Node(child))
        self.stimuli.extend(children)

    def transition_regimes_if_needed(self) -> None:
        """
        Check if this lineage should transition to a new regime based on its performance.
        """
        current_regime = self.regimes[self.current_regime_index]
        should_transition = current_regime.should_transition(self)
        self.lineage_data = current_regime.get_lineage_data(self)
        if should_transition:
            self.current_regime_index += 1

    def get_parent_of(self, child: Stimulus) -> Stimulus:
        return self.tree.find_node_that_satisfies(lambda node: node.data.id == child.parent_id).data


class Node:
    def __init__(self, data):
        self.data = data
        self.children = []

    def add_child(self, node: Node | Any):
        if not isinstance(node, Node):
            node = Node(node)
        self.children.append(node)

    def add_child_to(self, parent_data, child: Node):
        parent = self.find(parent_data)
        parent.add_child(child)

    def apply_to_children(self, function):
        for child in self.children:
            function(child)
            child.apply_to_children(function)

    def new_tree_from_function(self, function: callable[[Any], None]) -> Node:
        new_tree = Node(function(self.data))
        for child in self.children:
            new_tree.add_child(child.new_tree_from_function(function))
        return new_tree

    def have_parent_apply_to_children(self, function: callable[[Node, Node], None]):
        for child in self.children:
            function(child, self)
            child.have_parent_apply_to_children(function)

    def find(self, parent_data: Any) -> Node:
        if self.data == parent_data:
            return self
        for child in self.children:
            found = child.find(parent_data)
            if found:
                return found

    def find_node_that_satisfies(self, function: callable[[Node], bool]) -> Node:
        if function(self):
            return self
        for child in self.children:
            found = child.find_node_that_satisfies(function)
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
        result = [self.data]
        for child in self.children:
            result.extend(child.to_list())
        return result


class Phase:
    def __init__(self, parent_selector: ParentSelector, mutation_assigner: MutationAssigner,
                 mutation_magnitude_assigner: MutationMagnitudeAssigner, regime_transitioner: RegimeTransitioner):
        self.parent_selector = parent_selector
        self.mutation_assigner = mutation_assigner
        self.mutation_magnitude_assigner = mutation_magnitude_assigner
        self.regime_transitioner = regime_transitioner

    def generate_batch(self, lineage: Lineage, batch_size: int, gen_id: int) -> tuple[list[Stimulus], list[Stimulus]]:
        """
        Generate a new batch of stimuli by selecting parents and assigning mutation types and magnitudes.
        returns a dict with keys of children and value of their parents.
        """
        parents = self.parent_selector.select_parents(lineage, batch_size)
        new_children = []
        for parent in parents:
            new_children.append(Stimulus(time_util.now(),
                                         self.mutation_assigner.assign_mutation(lineage, parent),
                                         mutation_magnitude=self.mutation_magnitude_assigner.assign_mutation_magnitude(
                                             lineage,
                                             parent),
                                         gen_id=gen_id,
                                         parent_id=parent.id))
            time.sleep(0.001)
        return parents, new_children

    def should_transition(self, lineage: Lineage):
        """
        Check if a lineage should transition to a new regime based on its performance.
        """
        return self.regime_transitioner.should_transition(lineage)

    def get_lineage_data(self, lineage: Lineage):
        return self.regime_transitioner.get_transition_data(lineage)


class ParentSelector(Protocol):
    @abstractmethod
    def select_parents(self, lineage: Lineage, batch_size: int) -> list[Stimulus]:
        pass


class MutationAssigner(Protocol):
    @abstractmethod
    def assign_mutation(self, lineage: Lineage, parent: Stimulus):
        pass


class MutationMagnitudeAssigner(Protocol):
    @abstractmethod
    def assign_mutation_magnitude(self, lineage: Lineage, stimulus: Stimulus) -> float:
        pass


class RegimeTransitioner(Protocol):
    @abstractmethod
    def should_transition(self, lineage: Lineage) -> bool:
        pass

    def get_transition_data(self, lineage: Lineage) -> str:
        return "Test"


class LineageDistributor(Protocol):
    @abstractmethod
    def get_num_trials_for_lineage_ids(self, experiment_id: int) -> dict[int: int]:
        pass


class LineageFactory:
    @staticmethod
    def create_lineage_from_stimuli(stimuli: [Stimulus], regimes: [Phase] = None) -> Lineage:
        tree = Node(stimuli[0])
        for stimulus in stimuli[1:]:
            if stimulus.parent_id is not None:
                tree.add_child_to(stimulus.parent_id, Node(stimulus))
            else:
                print("Warning: stimulus with no parent. This should only happen in unit tests")
                tree.add_child(Node(stimulus))

        return Lineage(stimuli[0], regimes, 0, tree)

    @staticmethod
    def create_lineage_from_tree(tree: Node, current_regime_index=0, regimes: [Phase] = None,
                                 gen_id: int = None) -> Lineage:
        return Lineage(tree.data, regimes, tree=tree, current_regime_index=current_regime_index, gen_id=gen_id)

    @staticmethod
    def create_new_lineage_from_founder(founder: Stimulus, regimes=None) -> Lineage:
        return Lineage(founder, regimes)

    @staticmethod
    def create_new_lineage(*, regimes: [Phase]) -> Lineage:
        # founder = Stimulus(founder_id, mutation_type=regimes[0., parent_id=0, mutation_magnitude=None, gen_id=1)
        _, founders = regimes[0].generate_batch(None, 1, 1)
        founder = founders[0]
        return LineageFactory.create_new_lineage_from_founder(founder, regimes)
