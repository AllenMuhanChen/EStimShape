from unittest import TestCase

import matplotlib.pyplot as plt
import numpy as np

from clat.intan.one_file_spike_parsing import OneFileParser
from clat.intan.rhs.load_intan_rhs_format import read_data
from clat.intan.channels import Channel
from src.intan.one_file_lfp_parsing import OneFileLFPParser
from src.lfp.lfp_band_power_plotter import LFPBandPowerPlotter
from src.lfp.lfp_power_law import LFPPowerLaw, LFPPowerLawSpectrumPlotter, LFPSpikeRatePlotter
from src.lfp.lfp_spectrum import LFPSpectrum
from src.lfp.lfp_spectrum_plotter import LFPSpectrumPlotter
from src.lfp.relative_power_spectrum import RelativePowerSpectrum


class TestOneFileLFPParser(TestCase):
    # file_path = "/run/user/1000/gvfs/sftp:host=172.30.9.78/mnt/data/EStimShape/allen_ga_exp_260120_0/2026-01-20/1768934618287078_1_1768934754529063_260120_134558"
    # file_path = "/run/user/1000/gvfs/sftp:host=172.30.9.78/mnt/data/EStimShape/allen_ga_exp_260115_0/2026-01-15/1768500912926825_1_1768501037142197_260115_131719"
    # file_path = "/run/user/1000/gvfs/sftp:host=172.30.9.78/mnt/data/EStimShape/allen_ga_exp_260115_0/2026-01-15/1768500912926825_8_1768506582349129_260115_144943"
    file_path = "/run/user/1000/gvfs/sftp:host=172.30.9.78/mnt/data/EStimShape/allen_ga_exp_260113_0/2026-01-13/1768327745079370_1_1768327879721977_260113_131121"

    def test_parse(self):
        path_to_file = "/run/user/1000/gvfs/sftp:host=172.30.9.78/mnt/data/EStimShape/allen_ga_exp_260115_0/2026-01-15/1768500912926825_1_1768501037142197_260115_131719"
        path_to_rhd = f"{path_to_file}/info.rhs"
        data = read_data(path_to_rhd)
        amplifier_channels = data['amplifier_channels']
        sample_rate = data['frequency_parameters']['amplifier_sample_rate']

        parser = OneFileLFPParser(
            sample_rate,
            amplifier_channels,
            0.2,
            0.2
        )

        lfp_by_channel_by_task_id, epoch_start_stop_times_by_task_id, sample_rate = parser.parse(path_to_file)

        # Plot channel A-024 for the first 10 task_ids
        chan = "A-003"
        channel = Channel("%s" % chan)
        task_ids = [tid for tid, v in lfp_by_channel_by_task_id.items() if v is not None][:10]

        fig, axes = plt.subplots(len(task_ids), 1, figsize=(10, 2 * len(task_ids)), sharex=True)
        if len(task_ids) == 1:
            axes = [axes]

        for ax, task_id in zip(axes, task_ids):
            waveform = lfp_by_channel_by_task_id[task_id][channel]
            time_axis = np.arange(len(waveform)) / sample_rate - parser.seconds_before_epoch
            ax.plot(time_axis, waveform, linewidth=0.5)
            ax.set_ylabel(f"Task {task_id}\n(µV)")
            ax.axvline(0, color='r', linestyle='--', linewidth=0.5, label='epoch start')

        axes[-1].set_xlabel("Time (s)")
        fig.suptitle("Channel %s LFP by Task ID" % chan)
        plt.tight_layout()
        plt.show()

    def test_spectrum(self):
        path_to_file = "/run/user/1000/gvfs/sftp:host=172.30.9.78/mnt/data/EStimShape/allen_ga_exp_260113_0/2026-01-13/1768327745079370_1_1768327879721977_260113_131121"
        path_to_rhd = f"{path_to_file}/info.rhs"
        data = read_data(path_to_rhd)
        amplifier_channels = data['amplifier_channels']
        sample_rate = data['frequency_parameters']['amplifier_sample_rate']

        parser = OneFileLFPParser(
            sample_rate,
            amplifier_channels,
            0.0,
            0.0
        )

        lfp_by_channel_by_task_id, epoch_start_stop_times_by_task_id, sample_rate = parser.parse(path_to_file)

        # Compute spectra for all task_ids/channels
        spectrum_calculator = LFPSpectrum(sample_rate)
        spectra = spectrum_calculator.compute(lfp_by_channel_by_task_id)

        # Plot spectra for channel A-024, first 10 task_ids
        chan = "A-003"
        channel = Channel(chan)
        task_ids = [tid for tid, v in spectra.items() if v is not None][:10]

        fig, axes = plt.subplots(len(task_ids), 1, figsize=(10, 2 * len(task_ids)), sharex=True)
        if len(task_ids) == 1:
            axes = [axes]

        for ax, task_id in zip(axes, task_ids):
            freqs, power = spectra[task_id][channel]
            ax.semilogy(freqs, power, linewidth=0.5)
            ax.set_ylabel(f"Task {task_id}\n(µV²/Hz)")
            ax.set_xlim(0, 300)

        axes[-1].set_xlabel("Frequency (Hz)")
        fig.suptitle(f"Channel {chan} Power Spectrum by Task ID")
        plt.tight_layout()
        plt.show()

    def _compute_avg_spectra(self):
        """Helper to parse, compute spectra, and average across task_ids."""

        path_to_file = self.file_path
        path_to_rhd = f"{path_to_file}/info.rhs"
        data = read_data(path_to_rhd)
        amplifier_channels = data['amplifier_channels']
        sample_rate = data['frequency_parameters']['amplifier_sample_rate']

        parser = OneFileLFPParser(sample_rate, amplifier_channels, 0.5, 0.0)
        lfp_by_channel_by_task_id, _, sample_rate = parser.parse(path_to_file)

        spectrum_calculator = LFPSpectrum(sample_rate)
        spectra = spectrum_calculator.compute(lfp_by_channel_by_task_id)

        valid_task_ids = [tid for tid, v in spectra.items() if v is not None]
        channels = list(spectra[valid_task_ids[0]].keys())

        # Determine expected number of frequency bins from first valid spectrum
        expected_freqs, _ = spectra[valid_task_ids[0]][channels[0]]
        expected_len = len(expected_freqs)

        avg_spectrum_by_channel = {}
        for channel in channels:
            powers = []
            for tid in valid_task_ids:
                freqs, power = spectra[tid][channel]
                if len(power) == expected_len:
                    powers.append(power)
            avg_spectrum_by_channel[channel] = (expected_freqs, np.mean(powers, axis=0))

        return avg_spectrum_by_channel

    def test_spectrum_heatmap(self):
        avg_spectrum_by_channel = self._compute_avg_spectra()

        channel_order = [7, 8, 25, 22, 0, 15, 24, 23, 6, 9, 26, 21, 5, 10, 31, 16,
                         27, 20, 4, 11, 28, 19, 1, 14, 3, 12, 29, 18, 2, 13, 30, 17]
        # channel_order.reverse()
        plotter = LFPSpectrumPlotter(channel_order=channel_order)
        fig = plotter.plot(avg_spectrum_by_channel)
        fig.suptitle("Average LFP Power Spectrum Across All Trials")
        plt.tight_layout()
        plt.show()

    def test_relative_power_heatmap(self):
        avg_spectrum_by_channel = self._compute_avg_spectra()

        channel_order = [7, 8, 25, 22, 0, 15, 24, 23, 6, 9, 26, 21, 5, 10, 31, 16,
                         27, 20, 4, 11, 28, 19, 1, 14, 3, 12, 29, 18, 2, 13, 30, 17]
        # channel_order.reverse()

        rps = RelativePowerSpectrum(channel_order=channel_order)
        noisy = rps.get_noisy_channels(avg_spectrum_by_channel)
        print(f"Noisy channels: {[str(ch) for ch in noisy]}")

        normalized = rps.compute(avg_spectrum_by_channel)

        fig, (ax_heatmap, ax_band) = plt.subplots(1, 2, figsize=(16, 8),
                                                  gridspec_kw={'width_ratios': [2, 1]})

        heatmap_plotter = LFPSpectrumPlotter(channel_order=channel_order)
        heatmap_plotter.plot(normalized, ax=ax_heatmap)
        ax_heatmap.set_title("Relative Power Spectrum")

        band_plotter = LFPBandPowerPlotter(channel_order=channel_order)
        band_plotter.plot(normalized, ax=ax_band)
        ax_band.set_title("Band Power Profile")

        fig.suptitle("Relative LFP Power Spectrum (Normalized per Frequency)")
        plt.tight_layout()
        plt.show()

    def _compute_avg_spike_rates(self):
        """Compute average spike rate per channel across all task_ids."""

        parser = OneFileParser()
        spikes_by_channel_by_task_id, epoch_times, sample_rate = parser.parse(self.file_path)

        valid_task_ids = [tid for tid, v in spikes_by_channel_by_task_id.items() if v is not None]
        channels = list(spikes_by_channel_by_task_id[valid_task_ids[0]].keys())

        spike_rates = {}
        for channel in channels:
            rates = []
            for tid in valid_task_ids:
                spikes = spikes_by_channel_by_task_id[tid][channel]
                epoch_start, epoch_end = epoch_times[tid]
                duration = epoch_end - epoch_start
                if duration > 0:
                    rates.append(len(spikes) / duration)
            spike_rates[channel] = np.mean(rates) if rates else 0.0

        return spike_rates

    def test_power_law(self):
        avg_spectrum_by_channel = self._compute_avg_spectra()
        spike_rates = self._compute_avg_spike_rates()

        channel_order = [7, 8, 25, 22, 0, 15, 24, 23, 6, 9, 26, 21, 5, 10, 31, 16,
                         27, 20, 4, 11, 28, 19, 1, 14, 3, 12, 29, 18, 2, 13, 30, 17]

        fitter = LFPPowerLaw(freq_range=(20, 100))
        normalized = fitter.normalize_spectra_peak(avg_spectrum_by_channel)
        fits = fitter.fit_dict(normalized)

        spectrum_plotter = LFPPowerLawSpectrumPlotter(channel_order=channel_order)
        spike_plotter = LFPSpikeRatePlotter(channel_order=channel_order)

        n_cols = spectrum_plotter.n_axes + spike_plotter.n_axes
        width_ratios = [1] * spectrum_plotter.n_axes + [1] * spike_plotter.n_axes
        fig, axes = plt.subplots(1, n_cols, figsize=(4 * n_cols, 8), sharey=True,
                                 gridspec_kw={'width_ratios': width_ratios})

        spectrum_plotter.plot_onto_axes(
            fits, axes[:spectrum_plotter.n_axes],
            avg_spectrum_by_channel=avg_spectrum_by_channel,
            label_y_axis=True,
        )
        spike_plotter.plot_onto_axes(
            spike_rates, axes[spectrum_plotter.n_axes:],
            fits_by_channel=fits,
            label_y_axis=False,
        )

        fig.suptitle("Power Law & Spike Rate Parameters")
        plt.tight_layout()
        plt.show()

    def _compute_baseline_spectra(self, baseline_duration=0.25):
        """
        Compute spectra using only the pre-stimulus baseline window.
        This isolates spontaneous aperiodic activity, removing stimulus-driven contamination.
        """
        path_to_file = self.file_path
        path_to_rhd = f"{path_to_file}/info.rhs"
        data = read_data(path_to_rhd)
        amplifier_channels = data['amplifier_channels']
        sample_rate = data['frequency_parameters']['amplifier_sample_rate']

        # Parse with large pre-stimulus window, no post-stimulus
        parser = OneFileLFPParser(sample_rate, amplifier_channels,
                                  seconds_before_epoch=baseline_duration,
                                  seconds_after_epoch=0.0)
        lfp_by_channel_by_task_id, _, lfp_sample_rate = parser.parse(path_to_file)

        # Slice out only the pre-stimulus portion (before time 0)
        n_baseline_samples = int(baseline_duration * lfp_sample_rate)

        baseline_by_channel_by_task_id = {}
        for task_id, channels_dict in lfp_by_channel_by_task_id.items():
            if channels_dict is None:
                baseline_by_channel_by_task_id[task_id] = None
                continue
            baseline_channels = {}
            for channel, waveform in channels_dict.items():
                baseline_channels[channel] = waveform[:n_baseline_samples]
            baseline_by_channel_by_task_id[task_id] = baseline_channels

        # Compute spectra on baseline only
        spectrum_calculator = LFPSpectrum(lfp_sample_rate)
        spectra = spectrum_calculator.compute(baseline_by_channel_by_task_id)

        valid_task_ids = [tid for tid, v in spectra.items() if v is not None]
        channels = list(spectra[valid_task_ids[0]].keys())

        expected_freqs, _ = spectra[valid_task_ids[0]][channels[0]]
        expected_len = len(expected_freqs)

        avg_spectrum_by_channel = {}
        for channel in channels:
            powers = []
            for tid in valid_task_ids:
                freqs, power = spectra[tid][channel]
                if len(power) == expected_len:
                    powers.append(power)
            avg_spectrum_by_channel[channel] = (expected_freqs, np.mean(powers, axis=0))

        return avg_spectrum_by_channel

    def test_power_law_baseline(self):
        """Power law fit using only pre-stimulus baseline activity."""
        baseline_spectra = self._compute_baseline_spectra(baseline_duration=0.25)
        spike_rates = self._compute_avg_spike_rates()

        channel_order = [7, 8, 25, 22, 0, 15, 24, 23, 6, 9, 26, 21, 5, 10, 31, 16,
                         27, 20, 4, 11, 28, 19, 1, 14, 3, 12, 29, 18, 2, 13, 30, 17]

        fitter = LFPPowerLaw()
        normalized = fitter.normalize_spectra_peak(baseline_spectra)
        fits = fitter.fit_dict(normalized)

        spectrum_plotter = LFPPowerLawSpectrumPlotter(channel_order=channel_order)
        spike_plotter = LFPSpikeRatePlotter(channel_order=channel_order)

        n_cols = spectrum_plotter.n_axes + spike_plotter.n_axes
        fig, axes = plt.subplots(1, n_cols, figsize=(4 * n_cols, 8), sharey=True)

        spectrum_plotter.plot_onto_axes(
            fits, axes[:spectrum_plotter.n_axes],
            avg_spectrum_by_channel=baseline_spectra,
            label_y_axis=True,
        )
        spike_plotter.plot_onto_axes(
            spike_rates, axes[spectrum_plotter.n_axes:],
            fits_by_channel=fits,
            label_y_axis=False,
        )

        fig.suptitle("Baseline Power Law & Spike Rate Parameters (pre-stimulus only)")
        plt.tight_layout()
        plt.show()