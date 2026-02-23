import pandas as pd

from clat.pipeline.pipeline_base_classes import InputHandler


class SpikeRateCombinerInputHandler(InputHandler):
    """
    If response_key is a list, sums spike rates across all specified keys into a
    new '_combined' entry in the spike rate dict. Passes through unchanged if
    response_key is a single key.

    use .effective_key property to get the key to use for downstream analysis
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
