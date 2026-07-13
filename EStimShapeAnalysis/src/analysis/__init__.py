import os
from abc import abstractmethod, ABC
from typing import Optional, List

import pandas as pd

def get_all_channels() -> List[str]:
    """Generate list of all possible channels A-000 through A-031."""
    return [f"A-{i:03d}" for i in range(32)]


class Analysis(ABC):
    """Meant to streamline the process of fetching data from either manually compilation"""
    " the data repository for analyzing it."
    def __init__(self):
        self.session_id = None
        self.spike_rates_col = None
        self.spike_tstamps_col = None
        self.save_path = None
        self.response_table = None
        # Set for MUA data types (see parse_data_type). Selects the detection
        # method row in MUASpikeResponses and drives which fields compile builds.
        self.mua_method = None
        self.mua_k = None
        self.mua_block = None


    def parse_data_type(self, data_type, session_id, save_dir=None):
        if save_dir is None:
            save_dir = f"/home/connorlab/Documents/plots"
        self.save_path = f"{save_dir}/{session_id}"
        if not os.path.exists(self.save_path):
            os.makedirs(self.save_path)
        if data_type == 'raw':
            self.response_table = 'RawSpikeResponses'
            self.spike_tstamps_col = 'Spikes by channel'
            self.spike_rates_col = 'Spike Rate by channel'
        elif data_type == 'sorted':
            self.response_table = 'WindowSortedResponses'
            self.spike_tstamps_col = 'Spikes by unit'
            self.spike_rates_col = 'Spike Rate by unit'
        elif data_type == 'GA':
            self.response_table = None
            self.spike_rates_col = None
        elif data_type == 'mua' or data_type == 'mua_mad_k4_block100':
            # Multi-unit activity re-detected from wideband with -4x MAD, threshold
            # refreshed every 100 task_ids (matches the GA MUA pipeline).
            self.response_table = 'MUASpikeResponses'
            self.spike_tstamps_col = 'Spikes by channel'
            self.spike_rates_col = 'Spike Rate by channel'
            self.mua_k = 4.0
            self.mua_block = 100
            self.mua_method = f"mad_k{self.mua_k:g}_block{self.mua_block}"

        else:
            raise ValueError(f"Unknown data type: {data_type}")

    def run(self, session_id, data_type: str, channel: str, compiled_data: pd.DataFrame = None):
        self.session_id = session_id
        self.parse_data_type(data_type, session_id=session_id)
        compiled_data = self.import_data(compiled_data)
        return self.analyze(channel, compiled_data=compiled_data)

    def run_on_channels(self, session_id, data_type: str, channels: list[str], compiled_data: pd.DataFrame = None):
        self.session_id = session_id
        self.parse_data_type(data_type, session_id=session_id)
        compiled_data = self.import_data(compiled_data)
        results = {}
        for channel in channels:
             result = self.analyze(channel, compiled_data=compiled_data)
             results[channel] = result

        return results

    def import_data(self, compiled_data: pd.DataFrame) -> pd.DataFrame:
        return compiled_data

    @abstractmethod
    def analyze(self, channel: list[str] | str, compiled_data: pd.DataFrame = None):
        pass

    @abstractmethod
    def compile_and_export(self):
        pass

    @abstractmethod
    def compile(self):
        pass
