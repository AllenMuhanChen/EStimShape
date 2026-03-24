from typing import List, Optional

import numpy as np
import pandas as pd
from clat.compile.task.compile_task_id import TaskIdCollector
from clat.util.connection import Connection
from matplotlib import pyplot as plt

from src.analysis import Analysis
from src.intan.MultiFileLFPParser import MultiFileLFPParser
from src.lfp.lfp_band_power_plotter import LFPBandPowerPlotter
from src.lfp.lfp_spectrum import LFPSpectrum
from src.lfp.lfp_spectrum_plotter import LFPSpectrumPlotter
from src.lfp.relative_power_spectrum import RelativePowerSpectrum
from src.repository.import_from_repository import import_from_repository
from src.startup import context

_lfp_cache_dir = context.ga_parsed_spikes_path.replace("parsed_spikes", "parsed_lfp")


def main():
    channel_order = [7, 8, 25, 22, 0, 15, 24, 23, 6, 9, 26, 21, 5, 10, 31, 16,
                 27, 20, 4, 11, 28, 19, 1, 14, 3, 12, 29, 18, 2, 13, 30, 17]
    analysis = LFPAnalysis(channel_order=channel_order)
    analysis.run(session_id="260115_0", data_type="GA", channel=None)


class LFPAnalysis(Analysis):

    def __init__(
        self,
        channel_order: List[int],
        channel_prefix: str = "A",
        exclude_channels: Optional[List[int]] = None,
    ):
        super().__init__()
        self.channel_order = channel_order
        self.channel_prefix = channel_prefix
        self.exclude_channels = exclude_channels or []

    def analyze(self, channel, compiled_data: pd.DataFrame = None):
        # 1. Fetch compiled data if not provided
        if compiled_data is None:
            compiled_data = import_from_repository(
                self.session_id, "ga", "GAStimInfo", self.response_table
            )

        # 2. Extract task IDs
        task_ids = compiled_data['TaskId'].tolist()

        # 3. Parse LFP with caching
        parser = MultiFileLFPParser(to_cache=True, cache_dir=_lfp_cache_dir)
        lfp_data, _epochs, sr = parser.parse(task_ids, context.ga_intan_path)

        # 4. Compute power spectra and average across task IDs
        spectra = LFPSpectrum(sample_rate=sr).compute(lfp_data)
        avg_spectrum = _average_spectra(spectra)

        # 5. Relative power normalization
        rel_power = RelativePowerSpectrum(
            channel_order=self.channel_order,
            channel_prefix=self.channel_prefix,
            exclude_channels=self.exclude_channels,
        ).compute(avg_spectrum)

        # 6. Heatmap
        heatmap_fig = LFPSpectrumPlotter(
            channel_order=self.channel_order,
            channel_prefix=self.channel_prefix,
        ).plot(rel_power)
        heatmap_fig.savefig(f"{self.save_path}/lfp_relative_power_heatmap.png", dpi=150)

        # 7. Band power profile
        band_fig = LFPBandPowerPlotter(
            channel_order=self.channel_order,
            channel_prefix=self.channel_prefix,
        ).plot(rel_power)
        band_fig.savefig(f"{self.save_path}/lfp_band_power_profile.png", dpi=150)

        plt.show()
        return rel_power

    def compile(self):
        conn = Connection(context.ga_database)
        return TaskIdCollector(conn).collect_task_ids()

    def compile_and_export(self):
        pass  # LFP results are not exported to the repository


def _average_spectra(spectra_by_task_id):
    """Average power across all task IDs per channel.

    Returns Dict[Channel, (freqs, avg_power)].
    """
    channel_accumulators = {}
    freqs_ref = {}
    for ch_dict in spectra_by_task_id.values():
        if ch_dict is None:
            continue
        for ch, (freqs, power) in ch_dict.items():
            channel_accumulators.setdefault(ch, []).append(power)
            freqs_ref[ch] = freqs
    return {
        ch: (freqs_ref[ch], np.mean(powers, axis=0))
        for ch, powers in channel_accumulators.items()
    }


if __name__ == "__main__":
    main()
