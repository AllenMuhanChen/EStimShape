import os
from typing import Optional

import xmltodict
from clat.compile.tstamp.cached_tstamp_fields import CachedDatabaseField
from clat.util.connection import Connection
from clat.util.time_util import When

from src.analysis.nafc.nafc_neural_parser import NafcNeuralParser, NafcTrialEvents


class NafcNeuralDataField(CachedDatabaseField):
    """
    CachedFieldList-compatible field that parses the Intan neural recording
    for each NAFC trial.

    intan_base_path may contain trial directories directly:
        {base}/{task_id}_{YYMMDD}_{HHMMSS}/
    or organised into one level of date subdirectories:
        {base}/{YYYY-MM-DD}/{task_id}_{YYMMDD}_{HHMMSS}/

    An index of all recording directories is built once on construction so
    that per-trial lookups are O(1).
    """

    def __init__(self, intan_base_path: str, conn: Connection):
        super().__init__(conn)
        self._base = intan_base_path
        self._parser = NafcNeuralParser()
        self._index: dict[str, str] = {}   # task_id_str -> full dir path
        self._results: dict[int, Optional[NafcTrialEvents]] = {}
        self._build_index()

    def get_name(self) -> str:
        return "NeuralData"

    def get(self, when: When) -> Optional[NafcTrialEvents]:
        task_id = self._task_id_from_db(when)
        if task_id is None:
            return None
        if task_id not in self._results:
            self._results[task_id] = self._load(task_id)
        return self._results[task_id]

    def _task_id_from_db(self, when: When) -> Optional[int]:
        """Read taskId from the TrialMessage in BehMsg — this is the number
        Xper sends to Intan and that appears in the recording directory name."""
        self.conn.execute(
            "SELECT msg FROM BehMsg WHERE "
            "msg LIKE '%TrialMessage%' AND "
            "tstamp >= %s AND tstamp <= %s",
            params=(int(when.start), int(when.stop))
        )
        trial_msg_xml = self.conn.fetch_one()
        if trial_msg_xml is None:
            return None
        trial_msg_dict = xmltodict.parse(trial_msg_xml)
        task_id_str = trial_msg_dict.get('TrialMessage', {}).get('taskId')
        if task_id_str is None:
            return None
        return int(task_id_str)

    # ── index builder ────────────────────────────────────────────────────────

    def _build_index(self) -> None:
        """
        Scan base_path and one level of subdirectories.  Any directory whose
        name begins with a long integer is treated as a recording directory
        and indexed by that integer (the task_id).
        """
        try:
            entries = list(os.scandir(self._base))
        except OSError as exc:
            print(f"NafcNeuralDataField: cannot scan {self._base}: {exc}")
            return

        for entry in entries:
            if not entry.is_dir():
                continue
            if self._is_recording_dir(entry.name):
                self._index[entry.name.split('_')[0]] = entry.path
            else:
                # Could be a date subdirectory (e.g. 2026-04-26)
                try:
                    for sub in os.scandir(entry.path):
                        if sub.is_dir() and self._is_recording_dir(sub.name):
                            self._index[sub.name.split('_')[0]] = sub.path
                except OSError:
                    pass

        if not self._index:
            print(f"NafcNeuralDataField: no recording directories found under {self._base}")

    @staticmethod
    def _is_recording_dir(name: str) -> bool:
        """True when the directory name starts with a long numeric task_id."""
        parts = name.split('_')
        if len(parts) < 3:
            return False
        return len(parts[0]) > 10 and parts[0].isdigit()

    # ── per-trial loader ─────────────────────────────────────────────────────

    def _load(self, task_id: int) -> Optional[NafcTrialEvents]:
        recording_dir = self._index.get(str(task_id))
        if recording_dir is None:
            return None
        try:
            return self._parser.parse(recording_dir)
        except Exception as exc:
            print(f"NafcNeuralDataField: parse failed for task_id={task_id}: {exc}")
            return None
