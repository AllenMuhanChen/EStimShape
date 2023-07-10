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
        return current_regime.generate_batch(self.stimuli, batch_size)

    def check_for_regime_transition(self):
        """
        Check if this lineage should transition to a new regime based on its performance.
        """
        current_regime = self.regimes[self.current_regime_index]
        if current_regime.should_transition(self.stimuli):
            self.current_regime_index += 1


class Regime:
    def __init__(self, parent_selector, mutation_assigner, mutation_magnitude_assigner, regime_transitioner):
        self.parent_selector = parent_selector
        self.mutation_assigner = mutation_assigner
        self.mutation_magnitude_assigner = mutation_magnitude_assigner
        self.regime_transitioner = regime_transitioner

    def generate_batch(self, stimuli, batch_size):
        """
        Generate a new batch of stimuli by selecting parents and assigning mutation types and magnitudes.
        """
        parents = self.parent_selector.select_parents(stimuli, batch_size)
        return [Stimulus(self.mutation_assigner.assign_mutation(), parent=parent,
                         mutation_magnitude=self.mutation_magnitude_assigner.assign_mutation_magnitude())
                for parent in parents]

    def should_transition(self, stimuli):
        """
        Check if a lineage should transition to a new regime based on its performance.
        """
        return self.regime_transitioner.should_transition(stimuli)


class ParentSelector(ABC):
    @abstractmethod
    def select_parents(self, stimuli, batch_size):
        pass


class MutationAssigner(ABC):
    @abstractmethod
    def assign_mutation(self):
        pass


class MutationMagnitudeAssigner(ABC):
    @abstractmethod
    def assign_mutation_magnitude(self):
        pass


class RegimeTransitioner(ABC):
    @abstractmethod
    def should_transition(self, stimuli):
        pass
