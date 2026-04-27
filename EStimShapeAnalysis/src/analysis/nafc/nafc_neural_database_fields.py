import os
from typing import Optional

from clat.compile.tstamp.cached_tstamp_fields import CachedDatabaseField
from clat.util.connection import Connection
from clat.util.time_util import When

from src.analysis.nafc.nafc_neural_parser import NafcNeuralParser, NafcTrialEvents


class NafcNeuralDataField(CachedDatabaseField):
    """
    CachedFieldList-compatible field that parses the Intan neural recording
    for each NAFC trial.

    Expects a flat directory at intan_base_path containing one subdirectory
    per trial, named {task_id}_{YYMMDD}_{HHMMSS}.

    Returns NafcTrialEvents on success, None if no matching directory is found
    or parsing fails.
    """

    def __init__(self, intan_base_path: str, conn: Connection):
        super().__init__(conn)
        self._base = intan_base_path
        self._parser = NafcNeuralParser()
        self._cache: dict[int, Optional[NafcTrialEvents]] = {}

    def get_name(self) -> str:
        return "NeuralData"

    def get(self, when: When) -> Optional[NafcTrialEvents]:
        task_id = int(when.start)
        if task_id not in self._cache:
            self._cache[task_id] = self._load(task_id)
        return self._cache[task_id]

    def _load(self, task_id: int) -> Optional[NafcTrialEvents]:
        recording_dir = self._find_dir(task_id)
        if recording_dir is None:
            print(f"NafcNeuralDataField: no recording dir for task_id={task_id}")
            return None
        try:
            return self._parser.parse(recording_dir)
        except Exception as exc:
            print(f"NafcNeuralDataField: parse failed for task_id={task_id}: {exc}")
            return None

    def _find_dir(self, task_id: int) -> Optional[str]:
        prefix = str(task_id)
        try:
            for entry in os.scandir(self._base):
                if entry.is_dir() and entry.name.startswith(prefix):
                    return entry.path
        except OSError as exc:
            print(f"NafcNeuralDataField: error scanning {self._base}: {exc}")
        return None
