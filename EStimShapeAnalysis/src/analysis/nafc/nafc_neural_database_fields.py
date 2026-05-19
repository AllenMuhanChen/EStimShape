import os
from typing import Optional

import xmltodict
from clat.compile.tstamp.cached_tstamp_fields import CachedDatabaseField
from clat.util.connection import Connection
from clat.util.time_util import When

from src.analysis.nafc.neural.nafc_neural_parser import NafcNeuralParser, NafcTrialEvents


def _events_to_dict(events: NafcTrialEvents) -> dict:
    """Serialise NafcTrialEvents to a plain dict so CachedDatabaseField can cache it."""
    return {
        'task_id':    events.task_id,
        'sample_on':  events.sample_on,
        'sample_off': events.sample_off,
        'choices_on': events.choices_on,
        'choices_off': events.choices_off,
        'sample_rate': events.sample_rate,
        # Channel enum keys → string (e.g. "A-022")
        'spikes_by_channel': {
            getattr(ch, 'value', str(ch)): list(spikes)
            for ch, spikes in events.spikes_by_channel.items()
        },
    }


class NafcNeuralDataField(CachedDatabaseField):
    """
    Returns a plain dict (serializable) with keys:
        task_id, sample_on, sample_off, choices_on, choices_off,
        sample_rate, spikes_by_channel {channel_name -> [spike_times]}

    intan_base_path may contain trial directories directly:
        {base}/{stimSpecId}_{YYMMDD}_{HHMMSS}/
    or inside one level of date subdirectories:
        {base}/{YYYY-MM-DD}/{stimSpecId}_{YYMMDD}_{HHMMSS}/
    """

    def __init__(self, intan_base_path: str, conn: Connection, cache_dir: str = None):
        super().__init__(conn)
        self._base = intan_base_path
        self._parser = NafcNeuralParser(to_cache=cache_dir is not None, cache_dir=cache_dir)
        self._index: dict[str, str] = {}
        self._build_index()

    def get_name(self) -> str:
        return "NeuralData"

    def get(self, when: When) -> Optional[dict]:
        stim_spec_id = self._stim_spec_id_from_db(when)
        if stim_spec_id is None:
            return None
        recording_dir = self._index.get(str(stim_spec_id))
        if recording_dir is None:
            return None
        try:
            events = self._parser.parse(recording_dir)
            return _events_to_dict(events)
        except Exception as exc:
            print(f"NafcNeuralDataField: parse failed for stimSpecId={stim_spec_id}: {exc}")
            return None

    # ── stimSpecId lookup ────────────────────────────────────────────────────

    def _stim_spec_id_from_db(self, when: When) -> Optional[int]:
        """Read stimSpecId from the TrialMessage in BehMsg — this is the number
        that appears as the prefix of the Intan recording directory name."""
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
        id_str = trial_msg_dict.get('TrialMessage', {}).get('stimSpecId')
        if id_str is None:
            return None
        return int(id_str)

    # ── index builder ────────────────────────────────────────────────────────

    def _build_index(self) -> None:
        """Scan base_path and one level of subdirectories, indexing every
        directory whose name starts with a long numeric stimSpecId."""
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
        parts = name.split('_')
        return len(parts) >= 3 and len(parts[0]) > 10 and parts[0].isdigit()
