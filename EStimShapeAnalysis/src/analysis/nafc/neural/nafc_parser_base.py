from abc import ABC, abstractmethod

from src.analysis.nafc.neural.nafc_trial_events import NafcTrialEvents


class NafcParserBase(ABC):
    """
    Interface for parsers that convert a single NAFC Intan recording
    directory into a :class:`NafcTrialEvents`.

    Implementations are interchangeable wherever a NAFC neural parser
    is consumed (e.g. ``NafcNeuralDataField``).
    """

    @abstractmethod
    def parse(self, recording_dir: str) -> NafcTrialEvents:
        ...
