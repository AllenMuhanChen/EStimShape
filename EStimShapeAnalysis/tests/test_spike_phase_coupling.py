"""
Test script for SpikePhaseCoupling analysis.

Follows the pattern of test_one_file_lfp_parsing.py:
- Loads one recording file using OneFileLFPParser and OneFileMUADetector
- Runs SpikePhaseCoupling to compute cross-channel LPC matrices
- Plots the SPI matrix, phase matrix, and phase profile

Usage:
    Run as a unittest: python -m pytest test_spike_phase_coupling.py
    Or run individual test methods.
"""

from unittest import TestCase

import matplotlib.pyplot as plt
import numpy as np

from clat.intan.amplifiers import read_amplifier_data_with_memmap
from clat.intan.one_file_spike_parsing import OneFileParser
from clat.intan.rhs.load_intan_rhs_format import read_data
from clat.intan.channels import Channel
from src.intan.one_file_lfp_parsing import OneFileLFPParser
from src.lfp.one_file_mua_detector import OneFileMUADetector
from src.lfp.spike_phase_coupling import SpikePhaseCoupling, GeneralizedPhase


class TestSpikePhaseCoupling(TestCase):
    """Test the full spike-phase coupling pipeline on a single recording file."""

    # Physical depth ordering of channels (superficial -> deep)
    # This mapping reflects the Intan 32-channel headstage wiring to the probe layout.
    # Adjust this to match your specific probe + headstage configuration.
    CHANNEL_ORDER_INTS = [7, 8, 25, 22, 0, 15, 24, 23, 6, 9, 26, 21, 5, 10, 31, 16,
                          27, 20, 4, 11, 28, 19, 1, 14, 3, 12, 29, 18, 2, 13, 30, 17]

    # Reverse so index 0 = most superficial (top of cortex)
    CHANNEL_ORDER_INTS_REVERSED = list(reversed(CHANNEL_ORDER_INTS))

    PATH_TO_FILE = ("/run/user/1000/gvfs/sftp:host=172.30.9.78/mnt/data/EStimShape/"
                    "allen_ga_exp_260115_0/2026-01-15/"
                    "1768500912926825_1_1768501037142197_260115_131719")

    def _load_raw_data(self):
        """Load raw data from the recording file."""
        path_to_rhd = f"{self.PATH_TO_FILE}/info.rhs"
        data = read_data(path_to_rhd)
        amplifier_channels = data['amplifier_channels']
        sample_rate = data['frequency_parameters']['amplifier_sample_rate']
        return data, amplifier_channels, sample_rate

    def _parse_data(self, seconds_before=0.2, seconds_after=0.2):
        """Parse both LFP and spike data from the recording file."""
        data, amplifier_channels, sample_rate = self._load_raw_data()

        # Parse LFP
        lfp_parser = OneFileLFPParser(
            sample_rate,
            amplifier_channels,
            seconds_before,
            seconds_after
        )
        lfp_by_channel_by_task_id, epoch_times, lfp_sample_rate = lfp_parser.parse(self.PATH_TO_FILE)

        # Parse spikes from Intan spike.dat
        spike_parser = OneFileParser()
        spike_parser.seconds_before_epoch = seconds_before
        spike_parser.seconds_after_epoch = seconds_after
        spikes_by_channel_by_task_id, spike_epoch_times, spike_sr = spike_parser.parse(self.PATH_TO_FILE)

        # # Detect MUA spikes from raw broadband data (paper's method)
        # mua_detector = OneFileMUADetector(
        #     sample_rate,
        #     amplifier_channels,
        #     seconds_before_epoch=seconds_before,
        #     seconds_after_epoch=seconds_after,
        #     highpass_freq=500.0,
        #     threshold_sd=4.0,
        #     sd_window_seconds=1.0,
        #     refractory_seconds=0.001,
        # )
        # spikes_by_channel_by_task_id, spike_epoch_times, spike_sr = mua_detector.parse(self.PATH_TO_FILE)

        return (lfp_by_channel_by_task_id, spikes_by_channel_by_task_id,
                epoch_times, lfp_sample_rate)

    def _get_channel_objects(self):
        """Convert integer channel indices to Channel objects matching the parser output."""
        return [Channel(f"A-{i:03d}") for i in self.CHANNEL_ORDER_INTS]

    # ---- Test: MUA detection alone ----

    def test_mua_detection(self):
        """Test MUA detection on a single channel and visualize threshold crossings."""
        data, amplifier_channels, sample_rate = self._load_raw_data()

        # Read amplifier data from amplifier.dat (same way as OneFileMUADetector)

        amplifier_dat_path = f"{self.PATH_TO_FILE}/amplifier.dat"
        channel_to_data = read_amplifier_data_with_memmap(amplifier_dat_path, amplifier_channels)

        # Pick a channel to visualize
        chan = Channel("A-003")
        raw = channel_to_data[chan]

        # High-pass filter
        from scipy.signal import butter, filtfilt
        nyq = sample_rate / 2.0
        b, a = butter(4, 500.0 / nyq, btype='high')
        filtered = filtfilt(b, a, raw)

        # Sliding SD
        window_samples = int(1.0 * sample_rate)
        detector = OneFileMUADetector(sample_rate, amplifier_channels)
        local_sd = detector._sliding_std(filtered, window_samples)
        threshold = 4.0 * local_sd

        # Show first 2 seconds
        n_show = int(2.0 * sample_rate)
        time_axis = np.arange(n_show) / sample_rate

        fig, axes = plt.subplots(2, 1, figsize=(14, 6), sharex=True)

        # Raw broadband
        axes[0].plot(time_axis, raw[:n_show], 'k', linewidth=0.3)
        axes[0].set_ylabel("Raw (µV)")
        axes[0].set_title(f"Channel {chan} — Raw Broadband")

        # Filtered + threshold
        axes[1].plot(time_axis, filtered[:n_show], 'k', linewidth=0.3)
        axes[1].plot(time_axis, threshold[:n_show], 'r--', linewidth=0.5, label='+4 SD')
        axes[1].plot(time_axis, -threshold[:n_show], 'r--', linewidth=0.5, label='-4 SD')
        axes[1].set_ylabel("500 Hz HP Filtered (µV)")
        axes[1].set_xlabel("Time (s)")
        axes[1].set_title("High-Pass Filtered + Threshold (±4 SD)")
        axes[1].legend(fontsize=8)

        # Mark detected spikes
        spike_samples = detector._detect_spikes(filtered[:n_show])
        if len(spike_samples) > 0:
            axes[1].plot(spike_samples / sample_rate, filtered[spike_samples],
                         'rv', markersize=4, label=f'{len(spike_samples)} spikes')
            axes[1].legend(fontsize=8)

        plt.tight_layout()
        plt.show()

    # ---- Test: Generalized Phase ----

    def test_generalized_phase(self):
        """Test GP computation on a single channel's LFP."""
        lfp_by_channel_by_task_id, _, _, lfp_sample_rate = self._parse_data()

        # Get first valid task_id
        task_ids = [tid for tid, v in lfp_by_channel_by_task_id.items() if v is not None]
        task_id = task_ids[0]

        chan = Channel("A-003")
        waveform = lfp_by_channel_by_task_id[task_id][chan]

        gp = GeneralizedPhase(low_freq=5.0, high_freq=50.0)
        phase = gp.compute(waveform, lfp_sample_rate)

        # Plot
        time_axis = np.arange(len(waveform)) / lfp_sample_rate
        fig, axes = plt.subplots(3, 1, figsize=(12, 8), sharex=True)

        axes[0].plot(time_axis, waveform, 'k', linewidth=0.5)
        axes[0].set_ylabel("Raw LFP (µV)")
        axes[0].set_title(f"Channel A-003, Task {task_id}")

        # Also show the bandpass filtered signal
        filtered = gp._bandpass_filter(waveform, lfp_sample_rate)
        axes[1].plot(time_axis, filtered, 'b', linewidth=0.5)
        axes[1].set_ylabel("5-50 Hz Filtered (µV)")

        # Phase colored by value
        scatter = axes[2].scatter(time_axis, phase, c=phase, cmap='hsv',
                                   s=1, vmin=-np.pi, vmax=np.pi)
        axes[2].set_ylabel("GP Phase (rad)")
        axes[2].set_xlabel("Time (s)")
        axes[2].set_ylim(-np.pi - 0.2, np.pi + 0.2)
        plt.colorbar(scatter, ax=axes[2], label='Phase (rad)')

        plt.tight_layout()
        plt.show()

    # ---- Test: Full LPC pipeline ----

    def test_spike_phase_coupling(self):
        """Run the full cross-channel LPC analysis and plot results."""
        (lfp_by_channel_by_task_id, spikes_by_channel_by_task_id,
         epoch_times, lfp_sample_rate) = self._parse_data(
            seconds_before=0.2, seconds_after=0.2
        )

        channel_order = self._get_channel_objects()

        spc = SpikePhaseCoupling(
            channel_order=channel_order,
            gp_params={'low_freq': 5.0, 'high_freq': 50.0, 'filter_order': 4},
            min_spikes=50
        )

        results = spc.compute(
            lfp_by_channel_by_task_id,
            spikes_by_channel_by_task_id,
            epoch_times,
            lfp_sample_rate
        )

        # Print summary
        print(f"\nSpike counts per channel:")
        for i, ch in enumerate(channel_order):
            print(f"  {ch}: {results['spike_counts'][i]}")

        # Plot
        fig, axes = plt.subplots(1, 3, figsize=(20, 7))

        SpikePhaseCoupling.plot_spi_matrix(results, ax=axes[0])
        SpikePhaseCoupling.plot_phase_matrix(results, ax=axes[1])
        SpikePhaseCoupling.plot_phase_profile(results, ax=axes[2])

        fig.suptitle("Cross-Channel Laminar Phase Coupling (LPC)", fontsize=14)
        plt.tight_layout()
        plt.show()

    def test_spike_phase_coupling_with_spike_counts(self):
        """
        Same as test_spike_phase_coupling but also show spike count bar plot
        to visualize which channels have enough spikes for reliable estimates.
        """
        (lfp_by_channel_by_task_id, spikes_by_channel_by_task_id,
         epoch_times, lfp_sample_rate) = self._parse_data(
            seconds_before=0.2, seconds_after=0.2
        )

        channel_order = self._get_channel_objects()

        spc = SpikePhaseCoupling(
            channel_order=channel_order,
            gp_params={'low_freq': 5.0, 'high_freq': 50.0},
            min_spikes=50
        )

        results = spc.compute(
            lfp_by_channel_by_task_id,
            spikes_by_channel_by_task_id,
            epoch_times,
            lfp_sample_rate
        )

        fig, axes = plt.subplots(1, 6, figsize=(32, 7),
                                 gridspec_kw={'width_ratios': [1, 3, 3, 1.5, 1, 1]})

        # Spike count profile
        depths = np.arange(len(channel_order))
        axes[0].barh(depths, results['spike_counts'], color='steelblue', height=0.8)
        axes[0].set_ylabel("Channel (by depth)")
        axes[0].set_xlabel("Spike Count")
        axes[0].set_title("Spike Counts")
        axes[0].invert_yaxis()
        tick_step = max(1, len(channel_order) // 8)
        tick_pos = list(range(0, len(channel_order), tick_step))
        axes[0].set_yticks(tick_pos)
        axes[0].set_yticklabels([str(channel_order[i]) for i in tick_pos], fontsize=7)

        # SPI matrix
        SpikePhaseCoupling.plot_spi_matrix(results, ax=axes[1])

        # Phase matrix
        SpikePhaseCoupling.plot_phase_matrix(results, ax=axes[2])

        # Phase profile (cross-channel mean)
        SpikePhaseCoupling.plot_phase_profile(results, ax=axes[3])

        # Within-channel (diagonal) SPI
        diag_spi = np.diag(results['spi_matrix'])
        axes[4].plot(diag_spi, depths, 'ko-', markersize=4)
        axes[4].set_xlabel("SPI")
        axes[4].set_title("Within-Channel SPI")
        axes[4].invert_yaxis()
        axes[4].set_yticks(tick_pos)
        axes[4].set_yticklabels([str(channel_order[i]) for i in tick_pos], fontsize=7)

        # Within-channel (diagonal) preferred phase
        diag_phase = np.diag(results['phase_matrix'])
        colors = plt.cm.hsv((diag_phase + np.pi) / (2 * np.pi))
        axes[5].scatter(diag_phase, depths, c=colors, s=40, edgecolors='k', linewidths=0.5)
        axes[5].plot(diag_phase, depths, 'k-', linewidth=0.5, alpha=0.3)
        axes[5].axvline(0, color='gray', linestyle='--', alpha=0.5)
        axes[5].axvline(np.pi, color='gray', linestyle=':', alpha=0.3)
        axes[5].axvline(-np.pi, color='gray', linestyle=':', alpha=0.3)
        axes[5].set_xlabel("Phase (rad)")
        axes[5].set_title("Within-Channel Phase")
        axes[5].set_xlim(-np.pi - 0.3, np.pi + 0.3)
        axes[5].invert_yaxis()
        axes[5].set_yticks(tick_pos)
        axes[5].set_yticklabels([str(channel_order[i]) for i in tick_pos], fontsize=7)

        fig.suptitle("Laminar Phase Coupling Analysis", fontsize=14)
        plt.tight_layout()
        plt.show()