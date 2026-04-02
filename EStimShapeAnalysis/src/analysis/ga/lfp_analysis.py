from typing import List, Optional

import numpy as np
import pandas as pd
from clat.compile.task.cached_task_fields import CachedTaskFieldList
from clat.compile.task.classic_database_task_fields import StimSpecIdField
from clat.compile.task.compile_task_id import TaskIdCollector
from clat.util.connection import Connection
from matplotlib import pyplot as plt

from src.analysis import Analysis
from src.analysis.fields.cached_task_fields import StimTypeField, StimPathField, ThumbnailField
from src.analysis.ga.cached_ga_fields import LineageField, GenIdField, GAResponseField
from src.analysis.ga.plot_top_n import PlotTopNAnalysis
from src.analysis.isogabor.old_isogabor_analysis import IntanSpikesByChannelField, IntanSpikeRateByChannelField
from src.intan.MultiFileLFPParser import MultiFileLFPParser
from src.intan.MultiFileParser import MultiFileParser
from src.lfp.lfp_band_power_plotter import LFPBandPowerPlotter
from src.lfp.lfp_power_law import FOOOFPowerLaw, LFPPowerLawSpectrumPlotter, LFPSpikeRatePlotter
from src.lfp.lfp_spectrum import LFPSpectrum
from src.lfp.lfp_spectrum_plotter import LFPSpectrumPlotter
from src.lfp.relative_power_spectrum import RelativePowerSpectrum
from src.repository.export_to_repository import (
    export_to_repository, write_lfp_waveforms_to_db, write_iti_to_db,
    write_raw_spike_responses, read_session_id_from_db_name,
)
from src.repository.import_from_repository import (
    import_from_repository, add_lfp_waveforms_to_df, import_iti_from_repository,
)
from src.startup import context

_lfp_cache_dir = context.ga_parsed_spikes_path.replace("parsed_spikes", "parsed_lfp")


def main():
    channel_order = [7, 8, 25, 22, 0, 15, 24, 23, 6, 9, 26, 21, 5, 10, 31, 16,
                 27, 20, 4, 11, 28, 19, 1, 14, 3, 12, 29, 18, 2, 13, 30, 17]
    analysis = LFPAnalysis(channel_order=channel_order,
                           mode='iti')
    data = None
    data = analysis.compile_and_export()
    analysis.run(session_id="260402_0", data_type="raw", channel=None, compiled_data=data)


class LFPAnalysis(Analysis):

    def __init__(
        self,
        channel_order: List[int],
        channel_prefix: str = "A",
        exclude_channels: Optional[List[int]] = None,
        target_sample_rate: int = 1000,
        mode: str = 'task',
    ):
        super().__init__()
        self.channel_order = channel_order
        self.channel_prefix = channel_prefix
        self.exclude_channels = exclude_channels or []
        self.target_sample_rate = target_sample_rate
        self.mode = mode  # 'task' | 'iti'

    def analyze(self, channel, compiled_data: pd.DataFrame = None):
        if compiled_data is None:
            repo_conn = Connection("allen_data_repository")
            if self.mode == 'iti':
                compiled_data = import_iti_from_repository(
                    self.session_id, f"{self.session_id}_ga", repo_conn
                )
            else:
                compiled_data = import_from_repository(
                    self.session_id, "ga", "GAStimInfo", "RawSpikeResponses"
                )
                add_lfp_waveforms_to_df(compiled_data, repo_conn)

        # LFP
        lfp_data = {row['TaskId']: row['LFP by channel_id']
                    for _, row in compiled_data.iterrows()}
        sr = int(compiled_data['LFP Sample Rate'].iloc[0])

        spike_rates_by_channel = _compute_mean_spike_rates(compiled_data)

        # Spectra
        spectra = LFPSpectrum(sample_rate=sr).compute(lfp_data)
        avg_spectrum = _average_spectra(spectra)

        # Relative power (for heatmap + band power panels)
        rel_power = RelativePowerSpectrum(
            channel_order=self.channel_order,
            channel_prefix=self.channel_prefix,
            exclude_channels=self.exclude_channels,
        ).compute(avg_spectrum)

        # Power-law fits
        fits = FOOOFPowerLaw().fit_dict(avg_spectrum)

        # Build combined figure — mirrors intan_lfp.py
        pl_plotter = LFPPowerLawSpectrumPlotter(
            channel_order=self.channel_order,
            channel_prefix=self.channel_prefix,
            show_r_squared=False,

        )
        sp_plotter = LFPSpikeRatePlotter(
            channel_order=self.channel_order,
            channel_prefix=self.channel_prefix,
        )
        n_pl = pl_plotter.n_axes
        n_sp = sp_plotter.n_axes
        width_ratios = [2, 1] + [1] * n_pl + [1] * n_sp
        fig, axes = plt.subplots(
            1, 2 + n_pl + n_sp,
            figsize=(4 * (2 + n_pl + n_sp), 8),
            gridspec_kw={'width_ratios': width_ratios},
        )

        LFPSpectrumPlotter(
            channel_order=self.channel_order,
            channel_prefix=self.channel_prefix,
        ).plot(rel_power, ax=axes[0])
        axes[0].set_title("Relative Power Spectrum")

        LFPBandPowerPlotter(
            channel_order=self.channel_order,
            channel_prefix=self.channel_prefix,
        ).plot(rel_power, ax=axes[1])
        axes[1].set_title("Band Power")

        pl_plotter.plot_onto_axes(
            fits, axes[2: 2 + n_pl],
            avg_spectrum_by_channel=avg_spectrum,
            label_y_axis=False,
        )

        sp_plotter.plot_onto_axes(
            spike_rates_by_channel, axes[2 + n_pl:],
            fits_by_channel=fits,
            label_y_axis=False,
        )

        fig.suptitle(f"LFP Analysis — {self.session_id}")
        plt.tight_layout()
        fig.savefig(f"{self.save_path}/lfp_combined_analysis.png", dpi=150)
        plt.show()
        return rel_power

    def compile(self):
        if self.mode == 'iti':
            return self._compile_iti()
        conn = Connection(context.ga_database)
        task_ids = TaskIdCollector(conn).collect_task_ids()

        spike_parser = MultiFileParser(to_cache=True, cache_dir=context.ga_parsed_spikes_path)

        fields = CachedTaskFieldList()
        fields.append(StimSpecIdField(conn))
        fields.append(LineageField(conn))
        fields.append(GenIdField(conn))
        fields.append(GAResponseField(conn))
        fields.append(StimTypeField(conn))
        fields.append(StimPathField(conn))
        fields.append(ThumbnailField(conn))
        fields.append(IntanSpikesByChannelField(conn, spike_parser, task_ids, context.ga_intan_path))
        fields.append(IntanSpikeRateByChannelField(conn, spike_parser, task_ids, context.ga_intan_path))

        df = fields.to_data(task_ids)

        lfp_parser = MultiFileLFPParser(
            to_cache=True,
            cache_dir=_lfp_cache_dir,
            target_sample_rate=self.target_sample_rate,
        )
        lfp_data, _epochs, sr = lfp_parser.parse(task_ids, context.ga_intan_path)
        df['LFP by channel_id'] = df['TaskId'].map(lambda tid: lfp_data.get(tid) or {})
        df['LFP Sample Rate'] = sr
        return df

    def compile_and_export(self):
        if self.mode == 'iti':
            return self._compile_and_export_iti()
        df = self.compile()
        # export_to_repository(
        #     df,
        #     context.ga_database,
        #     "ga",
        #     stim_info_table="GAStimInfo",
        #     stim_info_columns=['Lineage', 'GenId', 'StimType', 'StimPath', 'ThumbnailPath', 'GA Response'],
        # )
        df = PlotTopNAnalysis.clean_ga_data(df)
        lfp_dict = {row['TaskId']: row['LFP by channel_id'] for _, row in df.iterrows()}
        sr = int(df['LFP Sample Rate'].iloc[0])
        repo_conn = Connection("allen_data_repository")
        write_lfp_waveforms_to_db(lfp_dict, sr, repo_conn)


    def _compile_iti(self) -> pd.DataFrame:
        """Parse ITI LFP + MUA across all recording files and return a DataFrame."""
        lfp_parser = MultiFileLFPParser(
            to_cache=True,
            cache_dir=_lfp_cache_dir,
            target_sample_rate=self.target_sample_rate,
        )
        iti_lfp, iti_spike_rates, _iti_windows, sr = lfp_parser.parse_iti(
            context.ga_intan_path,
        )
        records = []
        for iti_idx in sorted(iti_lfp.keys()):
            records.append({
                'TaskId': iti_idx,
                'LFP by channel_id': iti_lfp.get(iti_idx, {}),
                'LFP Sample Rate': sr,
                'Spike Rate by channel': iti_spike_rates.get(iti_idx, {}),
            })
        return pd.DataFrame(records)

    def _compile_and_export_iti(self) -> pd.DataFrame:
        """Compile ITI data, write to DB, and return the compiled DataFrame."""
        lfp_parser = MultiFileLFPParser(
            to_cache=True,
            cache_dir=_lfp_cache_dir,
            target_sample_rate=self.target_sample_rate,
        )
        iti_lfp, iti_spike_rates, iti_windows, sr = lfp_parser.parse_iti(
            context.ga_intan_path,
        )

        session_id, _ = read_session_id_from_db_name(context.ga_database)
        experiment_id = f"{session_id}_ga"
        repo_conn = Connection("allen_data_repository")

        # Write ITI windows → get iti_idx → iti_id mapping
        idx_to_id = write_iti_to_db(iti_windows, session_id, experiment_id, repo_conn)

        # Write LFP waveforms (keyed by iti_id)
        lfp_by_iti_id = {
            idx_to_id[idx]: iti_lfp[idx]
            for idx in iti_lfp
            if idx in idx_to_id
        }
        write_lfp_waveforms_to_db(lfp_by_iti_id, sr, repo_conn)

        # Write MUA spike rates into RawSpikeResponses (keyed by iti_id, empty tstamps)
        spike_rows = []
        for idx, rates in iti_spike_rates.items():
            iti_id = idx_to_id.get(idx)
            if iti_id is None:
                continue
            for ch, rate in rates.items():
                spike_rows.append((int(iti_id), str(ch), repr([]), float(rate)))
        write_raw_spike_responses(repo_conn, spike_rows)

        # Build and return the DataFrame
        records = []
        for idx in sorted(iti_lfp.keys()):
            records.append({
                'TaskId': idx_to_id.get(idx, idx),
                'LFP by channel_id': iti_lfp.get(idx, {}),
                'LFP Sample Rate': sr,
                'Spike Rate by channel': iti_spike_rates.get(idx, {}),
            })
        return pd.DataFrame(records)


def compile_data(conn: Connection) -> pd.DataFrame:
    collector = TaskIdCollector(conn)
    task_ids = collector.collect_task_ids()

    fields = CachedTaskFieldList()
    fields.append(StimSpecIdField(conn))
    fields.append(LineageField(conn))
    fields.append(GenIdField(conn))
    fields.append(GAResponseField(conn))
    fields.append(StimTypeField(conn))
    fields.append(StimPathField(conn))
    fields.append(ThumbnailField(conn))

    return fields.to_data(task_ids)


def compile():
    conn = Connection(context.ga_database)
    return compile_data(conn)


def _compute_mean_spike_rates(df: pd.DataFrame) -> dict:
    """Average spike rate per channel across all task rows."""
    accum = {}
    for _, row in df.iterrows():
        rates = row.get('Spike Rate by channel') or {}
        for ch, rate in rates.items():
            accum.setdefault(ch, []).append(rate)
    return {ch: float(np.mean(vals)) for ch, vals in accum.items()}


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
    result = {}
    for ch, powers in channel_accumulators.items():
        min_len = min(len(p) for p in powers)
        stacked = np.stack([p[:min_len] for p in powers], axis=0)
        result[ch] = (freqs_ref[ch][:min_len], np.mean(stacked, axis=0))
    return result


if __name__ == "__main__":
    main()
