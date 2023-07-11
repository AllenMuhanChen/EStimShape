from abc import ABC, abstractmethod


class Stimulus:
    def __init__(self, mutation_type, parent=None, mutation_magnitude=None, response_rate=None):
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
    def __init__(self, founder, regimes):
        self.stimuli = [founder]
        self.regimes = regimes
        self.current_regime_index = 0

    def generate_new_batch(self, batch_size):
        """
        Generate a new batch of stimuli by selecting parents and assigning mutation types
        using the current regime.
        """
        current_regime = self.regimes[self.current_regime_index]
        self.stimuli.append(current_regime.generate_batch(self, batch_size))

    def check_for_regime_trasnsition(self):
        """
        Check if this lineage should transition to a new regime based on its performance.
        """
        current_regime = self.regimes[self.current_regime_index]
        if current_regime.should_transition(self):
            self.current_regime_index += 1


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
        return [Stimulus(self.mutation_assigner.assign_mutation(lineage),
                         parent=parent,
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
