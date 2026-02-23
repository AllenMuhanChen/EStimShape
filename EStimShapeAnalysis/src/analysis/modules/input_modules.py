from typing import Optional, Union, List

import pandas as pd

from clat.pipeline.pipeline_base_classes import InputHandler


class SpikeRateCombinerInputHandler(InputHandler):
    """
    If response_key is a list, sums spike rates across all specified keys into a
    new '_combined' entry in the spike rate dict. Passes through unchanged if
    response_key is a single key.

    use .effective_key property to get the key to use for downstream analysis

    Puts combined into a new key rather than replacing existing keys to preserve original data structure for analyses that may want individual keys.
    """
    COMBINED_KEY = "_combined"

    def __init__(self, response_key: str | list[str], spike_data_col: str):
        self.response_key = response_key
        self.spike_data_col = spike_data_col

    def prepare(self, compiled_data: pd.DataFrame) -> pd.DataFrame:
        if not isinstance(self.response_key, list):
            return compiled_data

        data = compiled_data.copy()

        def combine_rates(spike_dict):
            if not isinstance(spike_dict, dict):
                return spike_dict
            combined = sum(spike_dict.get(k, 0) for k in self.response_key)
            return {**spike_dict, self.COMBINED_KEY: combined}

        data[self.spike_data_col] = data[self.spike_data_col].apply(combine_rates)
        return data

    @property
    def effective_key(self):
        return self.COMBINED_KEY if isinstance(self.response_key, list) else self.response_key

class GroupedSpikeTStampInputHandler(InputHandler):
    """
    If spike_data_col_key is a list, creates a new '_combined' entry in the dict that contains a sorted list of all timestamps from the specified keys. Passes through unchanged if spike_data_col_key is a single key.

        use .effective_key property to get the key to use for downstream analysis

    Puts combined into a new key rather than replacing existing keys to preserve original data structure for analyses that may want individual keys.

    """
    COMBINED_KEY = "_combined"

    def __init__(self,
                 spike_data_col: str,
                 spike_data_col_key: Optional[Union[str, List[str]]] = None):
        self.spike_data_col = spike_data_col
        self.spike_data_col_key = spike_data_col_key

    def prepare(self, compiled_data: pd.DataFrame) -> pd.DataFrame:
        data = compiled_data.copy()

        if self.spike_data_col_key is None:
            return data
        if not isinstance(data[self.spike_data_col].iloc[0], dict):
            return data

        if isinstance(self.spike_data_col_key, list):
            # Add '_combined' key into the dict, leaving original keys intact
            data[self.spike_data_col] = data[self.spike_data_col].apply(
                lambda x: {**x, self.COMBINED_KEY: sorted([
                    t for k in self.spike_data_col_key
                    if k in x
                    for t in x[k]
                ])} if isinstance(x, dict) else x
            )
        # Single key: no transformation needed, dict already has the key
        return data

    @property
    def effective_key(self) -> Optional[str]:
        return self.COMBINED_KEY if isinstance(self.spike_data_col_key, list) else self.spike_data_col_key

