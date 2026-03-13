"""
Spike-Phase Coupling analysis implementing the Laminar Phase Coupling (LPC) method
from Davis et al. (2023) eLife 12:e84512.

Computes cross-channel spike-LFP phase coupling using Generalized Phase (GP)
to identify laminar boundaries in cortical recordings.

Key references:
    - Davis ZW et al. (2023) Spike-phase coupling patterns reveal laminar identity
      in primate cortex. eLife 12:e84512.
    - Davis ZW et al. (2020) Spontaneous travelling cortical waves gate perception
      in behaving primates. Nature 587:432-436.
"""

import numpy as np
from scipy.signal import butter, filtfilt, hilbert
from scipy.interpolate import PchipInterpolator


class GeneralizedPhase:
    """
    Computes Generalized Phase (GP) of an LFP signal.

    GP is an improved analytic signal representation that corrects two technical
    limitations of the standard Hilbert Transform when applied to broadband signals:

    1. Low-frequency intrusions shift the analytic signal off-center in the complex
       plane, distorting phase angles from the arctangent.
       -> Corrected by bandpass filtering (high-pass removes low-freq content).

    2. High-frequency intrusions appear as "complex riding cycles" that manifest
       as periods of negative instantaneous frequency.
       -> Corrected by detecting negative-frequency epochs and interpolating
          over them using shape-preserving piecewise cubic interpolation.

    Parameters
    ----------
    low_freq : float
        Low cutoff for bandpass filter (Hz). Default 5 Hz.
    high_freq : float
        High cutoff for bandpass filter (Hz). Default 50 Hz.
    filter_order : int
        Order of Butterworth filter. Default 4.
    """

    def __init__(self, low_freq=5.0, high_freq=50.0, filter_order=4):
        self.low_freq = low_freq
        self.high_freq = high_freq
        self.filter_order = filter_order

    def compute(self, signal: np.ndarray, sample_rate: float) -> np.ndarray:
        """
        Compute the generalized phase of a 1-D LFP signal.

        Parameters
        ----------
        signal : np.ndarray
            1-D LFP waveform (microvolts).
        sample_rate : float
            Sampling rate in Hz.

        Returns
        -------
        phase : np.ndarray
            Generalized phase in radians [-pi, pi], same length as signal.
        """
        # Step 1: Bandpass filter (forward-reverse for zero phase distortion)
        filtered = self._bandpass_filter(signal, sample_rate)

        # Step 2: Compute analytic signal via single-sided Fourier transform
        analytic = self._analytic_signal_fft(filtered)

        # Step 3: Extract raw phase
        raw_phase = np.angle(analytic)

        # Step 4: Compute instantaneous frequency as finite differences
        # in the complex plane (avoids phase unwrapping issues)
        inst_freq = self._instantaneous_frequency(analytic)

        # Step 5: Detect and correct negative frequency epochs
        phase = self._correct_negative_frequencies(raw_phase, inst_freq)

        return phase

    def _bandpass_filter(self, signal: np.ndarray, sample_rate: float) -> np.ndarray:
        """Apply zero-phase Butterworth bandpass filter."""
        nyq = sample_rate / 2.0
        low = self.low_freq / nyq
        high = self.high_freq / nyq

        # Clip to valid range
        low = max(low, 1e-5)
        high = min(high, 1.0 - 1e-5)

        b, a = butter(self.filter_order, [low, high], btype='band')
        return filtfilt(b, a, signal)

    @staticmethod
    def _analytic_signal_fft(signal: np.ndarray) -> np.ndarray:
        """
        Compute analytic signal using single-sided Fourier transform approach
        (Marple 1999). This zeroes out negative frequency components in the
        frequency domain, then inverse transforms.
        """
        n = len(signal)
        f_signal = np.fft.fft(signal)

        # Create the single-sided multiplier
        h = np.zeros(n)
        if n % 2 == 0:
            h[0] = 1        # DC
            h[1:n // 2] = 2  # Positive frequencies
            h[n // 2] = 1    # Nyquist
        else:
            h[0] = 1
            h[1:(n + 1) // 2] = 2

        return np.fft.ifft(f_signal * h)

    @staticmethod
    def _instantaneous_frequency(analytic: np.ndarray) -> np.ndarray:
        """
        Compute instantaneous frequency via complex multiplication of
        consecutive analytic signal samples (Feldman 2011, Muller et al. 2014).

        inst_freq[n] = angle( analytic[n+1] * conj(analytic[n]) )

        This gives the phase derivative as finite differences without unwrapping.
        """
        # Complex multiplication: z[n+1] * conj(z[n])
        phase_diff = analytic[1:] * np.conj(analytic[:-1])
        inst_freq = np.angle(phase_diff)

        # Pad to same length (repeat last value)
        inst_freq = np.append(inst_freq, inst_freq[-1])

        return inst_freq

    @staticmethod
    def _correct_negative_frequencies(phase: np.ndarray, inst_freq: np.ndarray) -> np.ndarray:
        """
        Detect negative-frequency epochs (complex riding cycles) and correct
        them using shape-preserving piecewise cubic interpolation (PCHIP).

        For each contiguous block of Nc negative-frequency points, we interpolate
        over the next 2*Nc points following the block using PCHIP on the unwrapped
        phase sequence.
        """
        corrected_phase = np.copy(phase)

        # Find indices where instantaneous frequency is negative
        neg_mask = inst_freq < 0

        if not np.any(neg_mask):
            return corrected_phase

        # Find contiguous blocks of negative frequency
        # Detect transitions: 0->1 (start) and 1->0 (end)
        diff = np.diff(neg_mask.astype(int))
        starts = np.where(diff == 1)[0] + 1
        ends = np.where(diff == -1)[0] + 1

        # Handle edge cases
        if neg_mask[0]:
            starts = np.insert(starts, 0, 0)
        if neg_mask[-1]:
            ends = np.append(ends, len(neg_mask))

        n = len(phase)

        # Unwrap phase for interpolation
        unwrapped = np.unwrap(corrected_phase)

        for start, end in zip(starts, ends):
            nc = end - start  # length of negative freq block

            # Region to interpolate over: the negative block + 2*Nc following points
            interp_end = min(end + 2 * nc, n)

            # We need valid (non-negative-freq) anchor points on either side
            # Left anchor: points before the block
            left_anchor = max(0, start - 1)
            right_anchor = interp_end

            if right_anchor >= n:
                right_anchor = n - 1

            # Indices that are NOT in the negative-freq block (anchor points)
            all_indices = np.arange(left_anchor, right_anchor + 1)
            block_indices = np.arange(start, min(interp_end, n))

            # Use points outside the block as anchors for interpolation
            anchor_mask = np.ones(len(all_indices), dtype=bool)
            for bi in block_indices:
                local_idx = bi - left_anchor
                if 0 <= local_idx < len(anchor_mask):
                    anchor_mask[local_idx] = False

            anchor_indices = all_indices[anchor_mask]

            if len(anchor_indices) < 2:
                continue

            # PCHIP interpolation on unwrapped phase
            interp_func = PchipInterpolator(anchor_indices, unwrapped[anchor_indices])
            unwrapped[block_indices] = interp_func(block_indices)

        # Re-wrap to [-pi, pi]
        corrected_phase = (unwrapped + np.pi) % (2 * np.pi) - np.pi

        return corrected_phase


class SpikePhaseCoupling:
    """
    Computes spike-phase coupling and cross-channel Laminar Phase Coupling (LPC)
    matrices from epoched LFP and spike data.

    The analysis:
    1. Concatenates LFP epochs across task_ids per channel into continuous signals
    2. Computes Generalized Phase (GP) of the wideband-filtered LFP
    3. For each (spike_channel, lfp_channel) pair, collects the LFP phase at
       each spike time and computes:
       - Spike-Phase Index (SPI): circular mean resultant length
       - Preferred phase angle: circular mean of the spike-phase distribution

    Parameters
    ----------
    channel_order : list
        List of channel identifiers in physical depth order (superficial -> deep).
        These should match the keys used in lfp_by_channel_by_task_id and
        spike_times_by_channel_by_task_id.
    gp_params : dict, optional
        Parameters for GeneralizedPhase: low_freq, high_freq, filter_order.
    min_spikes : int
        Minimum number of spikes required on a channel to include it. Default 100.
    """

    def __init__(self, channel_order: list, gp_params: dict = None, min_spikes: int = 100):
        self.channel_order = channel_order
        self.min_spikes = min_spikes

        gp_params = gp_params or {}
        self.gp = GeneralizedPhase(**gp_params)

    def compute(self,
                lfp_by_channel_by_task_id: dict,
                spike_times_by_channel_by_task_id: dict,
                epoch_start_stop_times_by_task_id: dict,
                lfp_sample_rate: float) -> dict:
        """
        Compute the cross-channel LPC matrices.

        Parameters
        ----------
        lfp_by_channel_by_task_id : dict
            {task_id: {channel: np.ndarray}} — epoched LFP waveforms.
        spike_times_by_channel_by_task_id : dict
            {task_id: {channel: list[float]}} — spike times in absolute seconds.
        epoch_start_stop_times_by_task_id : dict
            {task_id: (start_seconds, end_seconds)} — epoch boundaries.
        lfp_sample_rate : float
            Sample rate of the LFP data (after any downsampling).

        Returns
        -------
        results : dict with keys:
            'spi_matrix' : np.ndarray (n_channels x n_channels)
                Cross-channel SPI values. Row = spike channel, Col = LFP channel.
            'phase_matrix' : np.ndarray (n_channels x n_channels)
                Cross-channel preferred phase angles (radians).
            'spike_counts' : np.ndarray (n_channels,)
                Total spike count per channel after concatenation.
            'channel_order' : list
                The channel order used (for labeling axes).
            'phase_by_channel' : dict
                {channel: np.ndarray} — concatenated GP phase per channel.
            'spike_samples_by_channel' : dict
                {channel: np.ndarray} — concatenated spike sample indices per channel.
        """
        # Step 1: Concatenate LFP and spike data across task_ids
        concat_lfp, concat_spikes, total_samples = self._concatenate_data(
            lfp_by_channel_by_task_id,
            spike_times_by_channel_by_task_id,
            epoch_start_stop_times_by_task_id,
            lfp_sample_rate
        )

        # Step 2: Compute GP phase for each channel
        print("Computing Generalized Phase for each channel...")
        phase_by_channel = {}
        for ch in self.channel_order:
            if ch in concat_lfp and len(concat_lfp[ch]) > 0:
                print(f"  GP for channel {ch} ({len(concat_lfp[ch])} samples)")
                phase_by_channel[ch] = self.gp.compute(concat_lfp[ch], lfp_sample_rate)
            else:
                print(f"  Skipping channel {ch} — no LFP data")

        # Step 3: Convert spike times to sample indices in the concatenated signal
        spike_samples_by_channel = {}
        spike_counts = np.zeros(len(self.channel_order), dtype=int)
        for i, ch in enumerate(self.channel_order):
            if ch in concat_spikes:
                samples = concat_spikes[ch]
                # Filter to valid range
                valid = samples[(samples >= 0) & (samples < total_samples)]
                spike_samples_by_channel[ch] = valid.astype(int)
                spike_counts[i] = len(valid)
                print(f"  Channel {ch}: {len(valid)} spikes")
            else:
                spike_samples_by_channel[ch] = np.array([], dtype=int)

        # Step 4: Compute cross-channel SPI and preferred phase matrices
        n_ch = len(self.channel_order)
        spi_matrix = np.full((n_ch, n_ch), np.nan)
        phase_matrix = np.full((n_ch, n_ch), np.nan)

        print("Computing cross-channel spike-phase coupling...")
        for i, spike_ch in enumerate(self.channel_order):
            spike_idx = spike_samples_by_channel.get(spike_ch, np.array([]))
            if len(spike_idx) < self.min_spikes:
                continue

            for j, lfp_ch in enumerate(self.channel_order):
                if lfp_ch not in phase_by_channel:
                    continue

                phase_at_spikes = phase_by_channel[lfp_ch][spike_idx]

                # SPI = mean resultant length
                spi_matrix[i, j] = self._circular_resultant_length(phase_at_spikes)

                # Preferred phase = circular mean
                phase_matrix[i, j] = self._circular_mean(phase_at_spikes)

        return {
            'spi_matrix': spi_matrix,
            'phase_matrix': phase_matrix,
            'spike_counts': spike_counts,
            'channel_order': self.channel_order,
            'phase_by_channel': phase_by_channel,
            'spike_samples_by_channel': spike_samples_by_channel,
        }

    def _concatenate_data(self, lfp_by_channel_by_task_id, spike_times_by_channel_by_task_id,
                          epoch_start_stop_times_by_task_id, lfp_sample_rate):
        """
        Concatenate LFP waveforms and spike times across task_ids.

        For LFP: simply concatenate the waveform arrays.
        For spikes: convert absolute spike times to sample indices within
        the concatenated LFP signal.

        Returns
        -------
        concat_lfp : dict {channel: np.ndarray}
        concat_spikes : dict {channel: np.ndarray of sample indices}
        total_samples : int
        """
        # Get valid task_ids (where both LFP and spikes exist)
        valid_task_ids = []
        for tid in sorted(lfp_by_channel_by_task_id.keys()):
            if (lfp_by_channel_by_task_id.get(tid) is not None and
                    spike_times_by_channel_by_task_id.get(tid) is not None and
                    epoch_start_stop_times_by_task_id.get(tid) is not None):
                valid_task_ids.append(tid)

        print(f"Concatenating data from {len(valid_task_ids)} valid task_ids...")

        # Initialize containers
        concat_lfp = {ch: [] for ch in self.channel_order}
        concat_spikes = {ch: [] for ch in self.channel_order}

        cumulative_samples = 0

        for tid in valid_task_ids:
            lfp_data = lfp_by_channel_by_task_id[tid]
            spike_data = spike_times_by_channel_by_task_id[tid]
            epoch_start, epoch_end = epoch_start_stop_times_by_task_id[tid]

            # Determine the number of LFP samples for this epoch
            # Use the first available channel to get epoch length
            epoch_n_samples = None
            for ch in self.channel_order:
                if ch in lfp_data and lfp_data[ch] is not None:
                    epoch_n_samples = len(lfp_data[ch])
                    break

            if epoch_n_samples is None:
                continue

            # Concatenate LFP
            for ch in self.channel_order:
                if ch in lfp_data and lfp_data[ch] is not None:
                    concat_lfp[ch].append(lfp_data[ch])

            # Convert spike times to sample indices relative to concatenated signal
            # The LFP epoch starts at (epoch_start - seconds_before) in absolute time
            # and the waveform sample 0 corresponds to that time.
            # Spike times are in absolute seconds.
            # We need the absolute time of sample 0 of this LFP epoch.
            # From OneFileLFPParser: start_time = epoch_start - seconds_before_epoch
            # But we don't know seconds_before_epoch here. We can infer it:
            # The epoch in epoch_start_stop is (epoch_start, epoch_end) in absolute seconds.
            # The LFP waveform duration = epoch_n_samples / lfp_sample_rate
            # The waveform covers from (epoch_start - pre) to (epoch_end + post)
            # So waveform_start_time = epoch_start - (lfp_waveform_duration - (epoch_end - epoch_start)) / 2
            # Actually, simpler: the waveform starts at some time t0, and we know
            # its duration. We'll infer t0 from epoch info.

            # From the parser: waveform covers epoch_start - seconds_before to epoch_end + seconds_after
            # Total duration = seconds_before + (epoch_end - epoch_start) + seconds_after
            # = epoch_n_samples / lfp_sample_rate
            # waveform t0 = epoch_start - seconds_before
            # We can compute seconds_before as:
            # seconds_before = (epoch_n_samples / lfp_sample_rate - (epoch_end - epoch_start)) / 2
            # ... but that assumes seconds_before == seconds_after, which is the common case.
            # OR: we know the epoch occupies the middle, and pre/post are symmetric.

            # More robust: compute waveform_start using known duration
            waveform_duration = epoch_n_samples / lfp_sample_rate
            epoch_duration = epoch_end - epoch_start
            # seconds_before + seconds_after = waveform_duration - epoch_duration
            # For the parser, these are set at construction. We'll assume symmetric for now.
            # Actually, the parser stores them, but we don't have access here.
            # The safest approach: use the full waveform time span.
            # waveform covers some time window. The epoch_start is at sample index:
            #   seconds_before * lfp_sample_rate
            # We can compute seconds_before = (waveform_duration - epoch_duration) / 2
            # if symmetric, OR we just compute t0 from epoch_start:
            # We know the epoch_start corresponds to the sample at index (seconds_before * sr)
            # But we don't know seconds_before.
            #
            # SIMPLEST APPROACH: just use epoch_start and epoch_end to define the
            # time window. The LFP waveform sample i corresponds to time:
            #   t = waveform_start + i / lfp_sample_rate
            # where waveform_start is unknown. But if we assume the epoch boundaries
            # are aligned to the waveform, we can use:
            #
            # Actually: we CAN compute waveform_start because we know the LFP parser
            # uses: start_sample = epoch_start_sample - seconds_before * sample_rate
            # and the epoch_start in the output is epoch_start_sample / original_sample_rate.
            # After downsampling, the waveform still starts at that same absolute time.
            #
            # Let's just compute it: waveform_start = epoch_start - pre_seconds
            # where pre_seconds = (waveform_duration - epoch_duration) is approximately right
            # if post ~= 0, but in general we need both. Let's use a different approach:
            #
            # We'll parameterize this in the constructor.

            # For now, just use the first sample = epoch_start minus pre-buffer
            # We'll infer pre_seconds from the waveform length and epoch length:
            total_buffer = waveform_duration - epoch_duration
            # We'll assume symmetric (which matches the parser's 0.2, 0.2 defaults)
            pre_seconds = total_buffer / 2.0
            waveform_start_time = epoch_start - pre_seconds

            for ch in self.channel_order:
                if ch in spike_data and spike_data[ch] is not None:
                    spike_times = np.array(spike_data[ch], dtype=float)
                    # Convert absolute spike times to sample indices in concatenated signal
                    spike_samples = (spike_times - waveform_start_time) * lfp_sample_rate + cumulative_samples
                    # Only keep spikes that fall within this epoch's waveform
                    valid = spike_samples[(spike_samples >= cumulative_samples) &
                                          (spike_samples < cumulative_samples + epoch_n_samples)]
                    concat_spikes[ch].append(valid)

            cumulative_samples += epoch_n_samples

        # Finalize: concatenate lists into arrays
        for ch in self.channel_order:
            if concat_lfp[ch]:
                concat_lfp[ch] = np.concatenate(concat_lfp[ch])
            else:
                concat_lfp[ch] = np.array([])

            if concat_spikes[ch]:
                concat_spikes[ch] = np.concatenate(concat_spikes[ch])
            else:
                concat_spikes[ch] = np.array([])

        print(f"Total concatenated samples: {cumulative_samples} "
              f"({cumulative_samples / lfp_sample_rate:.1f} seconds)")

        return concat_lfp, concat_spikes, cumulative_samples

    @staticmethod
    def _circular_resultant_length(angles: np.ndarray) -> float:
        """Mean resultant length (SPI). Ranges from 0 (uniform) to 1 (all same phase)."""
        if len(angles) == 0:
            return np.nan
        return np.abs(np.mean(np.exp(1j * angles)))

    @staticmethod
    def _circular_mean(angles: np.ndarray) -> float:
        """Circular mean angle in radians [-pi, pi]."""
        if len(angles) == 0:
            return np.nan
        return np.angle(np.mean(np.exp(1j * angles)))

    # ---- Plotting utilities ----

    @staticmethod
    def plot_spi_matrix(results: dict, ax=None, **kwargs):
        """Plot the cross-channel SPI matrix as a heatmap."""
        import matplotlib.pyplot as plt

        if ax is None:
            fig, ax = plt.subplots(figsize=(8, 8))

        spi = results['spi_matrix']
        channel_order = results['channel_order']
        n = len(channel_order)

        im = ax.imshow(spi, cmap='hot', aspect='equal',
                        origin='upper', **kwargs)
        ax.set_xlabel("LFP Channel (by depth)")
        ax.set_ylabel("Spike Channel (by depth)")
        ax.set_title("Cross-Channel SPI")

        # Label every Nth tick to avoid clutter
        tick_step = max(1, n // 8)
        tick_pos = list(range(0, n, tick_step))
        ax.set_xticks(tick_pos)
        ax.set_xticklabels([str(channel_order[i]) for i in tick_pos], rotation=90, fontsize=7)
        ax.set_yticks(tick_pos)
        ax.set_yticklabels([str(channel_order[i]) for i in tick_pos], fontsize=7)

        plt.colorbar(im, ax=ax, label='SPI')
        return ax

    @staticmethod
    def plot_phase_matrix(results: dict, ax=None, **kwargs):
        """Plot the cross-channel preferred phase angle matrix."""
        import matplotlib.pyplot as plt

        if ax is None:
            fig, ax = plt.subplots(figsize=(8, 8))

        phase = results['phase_matrix']
        channel_order = results['channel_order']
        n = len(channel_order)

        im = ax.imshow(phase, cmap='hsv', aspect='equal',
                        origin='upper', vmin=-np.pi, vmax=np.pi, **kwargs)
        ax.set_xlabel("LFP Channel (by depth)")
        ax.set_ylabel("Spike Channel (by depth)")
        ax.set_title("Cross-Channel Preferred Phase")

        tick_step = max(1, n // 8)
        tick_pos = list(range(0, n, tick_step))
        ax.set_xticks(tick_pos)
        ax.set_xticklabels([str(channel_order[i]) for i in tick_pos], rotation=90, fontsize=7)
        ax.set_yticks(tick_pos)
        ax.set_yticklabels([str(channel_order[i]) for i in tick_pos], fontsize=7)

        cbar = plt.colorbar(im, ax=ax, label='Phase (rad)')
        cbar.set_ticks([-np.pi, -np.pi / 2, 0, np.pi / 2, np.pi])
        cbar.set_ticklabels(['-π', '-π/2', '0', 'π/2', 'π'])
        return ax

    @staticmethod
    def plot_phase_profile(results: dict, ax=None):
        """
        Plot the mean preferred phase across all spike channels as a function
        of LFP channel depth. This collapses the phase matrix across rows
        (spike channels) to show the characteristic phase reversal.
        """
        import matplotlib.pyplot as plt

        if ax is None:
            fig, ax = plt.subplots(figsize=(6, 8))

        phase = results['phase_matrix']
        channel_order = results['channel_order']

        # Compute circular mean across spike channels (rows) for each LFP channel (col)
        mean_phase_per_lfp_ch = np.full(phase.shape[1], np.nan)
        for j in range(phase.shape[1]):
            col = phase[:, j]
            valid = col[~np.isnan(col)]
            if len(valid) > 0:
                mean_phase_per_lfp_ch[j] = np.angle(np.mean(np.exp(1j * valid)))

        depths = np.arange(len(channel_order))

        ax.plot(mean_phase_per_lfp_ch, depths, 'ko-', markersize=4)
        ax.axvline(0, color='gray', linestyle='--', alpha=0.5)
        ax.axvline(np.pi, color='gray', linestyle=':', alpha=0.3)
        ax.axvline(-np.pi, color='gray', linestyle=':', alpha=0.3)
        ax.set_xlabel("Mean Preferred Phase (rad)")
        ax.set_ylabel("LFP Channel (by depth index)")
        ax.set_title("Phase Profile Across Depth")
        ax.set_xlim(-np.pi - 0.3, np.pi + 0.3)
        ax.invert_yaxis()

        # Label ticks
        tick_step = max(1, len(channel_order) // 8)
        tick_pos = list(range(0, len(channel_order), tick_step))
        ax.set_yticks(tick_pos)
        ax.set_yticklabels([str(channel_order[i]) for i in tick_pos], fontsize=7)

        return ax