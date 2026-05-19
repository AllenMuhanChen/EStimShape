from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class NafcTrialEvents:
    """
    Parsed neural data for a single NAFC recording.

    All timestamps are in seconds from the start of the recording.
    """
    task_id: int
    sample_on: Optional[float]
    sample_off: Optional[float]
    choices_on: Optional[float]
    choices_off: Optional[float]
    spikes_by_channel: Dict = field(default_factory=dict)
    sample_rate: float = 30000.0
