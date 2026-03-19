#!/usr/bin/env python3
"""
Intan LFP Relative Power Analyzer
=================================
Standalone script that connects to Intan RHX via TCP, collects wideband data
from all 32 channels, computes LFP, and plots relative power spectrum together
with 1/f power-law parameter profiles.

Based on RHXReadWaveformData.py example.
Uses existing LFPSpectrum, RelativePowerSpectrum, LFPSpectrumPlotter,
LFPBandPowerPlotter, LFPPowerLaw, and LFPPowerLawSpectrumPlotter.
"""

import time
import socket
import struct
import threading

import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import butter, sosfilt, decimate

# Import existing classes
from lfp_spectrum import LFPSpectrum
from relative_power_spectrum import RelativePowerSpectrum
from lfp_spectrum_plotter import LFPSpectrumPlotter
from lfp_band_power_plotter import LFPBandPowerPlotter
from lfp_power_law import LFPPowerLaw, LFPPowerLawSpectrumPlotter, LFPSpikeRatePlotter

# ============================================================================
# CONFIGURATION
# ============================================================================

ACQUISITION_SECONDS = 30

CHANNEL_ORDER = [7, 8, 25, 22, 0, 15, 24, 23, 6, 9, 26, 21, 5, 10, 31, 16,
                 27, 20, 4, 11, 28, 19, 1, 14, 3, 12, 29, 18, 2, 13, 30, 17]

FREQ_RANGE = (0, 150)

LFP_LOWPASS = 250.0
LFP_TARGET_RATE = 1000

COMMAND_BUFFER_SIZE = 1024

MAGIC_NUMBER = 0x2ef07a08
FRAMES_PER_BLOCK = 128
MICROVOLTS_PER_BIT = 0.195
SAMPLE_OFFSET = 32768

# ---- Power-law plotter config -------------------------------------------
# Toggle individual parameter panels on/off here.
POWER_LAW_PANELS = dict(
    show_exponent=True,
    show_amplitude=False,
    show_r_squared=False,
    show_gamma_ratio=True,
    show_residual_gamma=False,
    show_residual_alpha_beta=False,
)

# ---- MUA detection config -----------------------------------------------
MUA_HIGHPASS_HZ    = 300.0   # classic HPF cutoff for spike detection
MUA_THRESHOLD_RMS  = 4.0     # threshold multiplier: -N × RMS
MUA_REFRACTORY_SEC = 0.001   # 1 ms refractory period
# -------------------------------------------------------------------------


class GetSampleRateFailure(Exception):
    pass


class InvalidMagicNumber(Exception):
    pass


def extract_lfp(wideband: np.ndarray, sample_rate: float,
                lowpass: float = 250.0, target_rate: float = 1000.0) -> tuple:
    nyq = sample_rate / 2
    sos = butter(3, lowpass / nyq, btype='low', output='sos')
    filtered = sosfilt(sos, wideband)

    decimate_factor = int(sample_rate / target_rate)
    if decimate_factor > 1:
        lfp = decimate(filtered, decimate_factor, ftype='fir', zero_phase=True)
        lfp_rate = sample_rate / decimate_factor
    else:
        lfp = filtered
        lfp_rate = sample_rate

    return lfp, lfp_rate


def detect_mua_spikes(wideband: np.ndarray, sample_rate: float,
                      highpass_hz: float = 300.0,
                      threshold_rms: float = 4.0,
                      refractory_sec: float = 0.001) -> np.ndarray:
    """
    Detect MUA spikes using the classic -N×RMS threshold method.

    Steps:
      1. High-pass filter at highpass_hz (4th-order Butterworth, zero-phase).
      2. Compute RMS over the entire recording as the noise estimate.
      3. Detect negative-going threshold crossings at -threshold_rms × RMS
         (extracellular APs are predominantly negative).
      4. Keep only the trough (minimum) within each refractory window so
         multi-sample crossings count as one spike.
      5. Enforce refractory period between successive spikes.

    Returns
    -------
    spike_samples : np.ndarray
        Sample indices of detected spikes.
    """
    nyq = sample_rate / 2.0
    sos = butter(4, highpass_hz / nyq, btype='high', output='sos')
    filtered = sosfilt(sos, wideband)

    rms = np.sqrt(np.mean(filtered ** 2))
    threshold = -threshold_rms * rms

    # Negative crossings: signal goes from above threshold to below
    below = filtered < threshold
    crossings = np.where(np.diff(below.astype(np.int8)) == 1)[0] + 1

    if len(crossings) == 0:
        return np.array([], dtype=int)

    # Snap each crossing to the trough within the refractory window
    refractory_samples = max(1, int(refractory_sec * sample_rate))
    n = len(filtered)
    spike_samples = []
    for c in crossings:
        window_end = min(c + refractory_samples, n)
        trough = c + int(np.argmin(filtered[c:window_end]))
        spike_samples.append(trough)

    spike_samples = np.array(spike_samples, dtype=int)

    # Enforce refractory period
    if len(spike_samples) > 1:
        kept = [spike_samples[0]]
        for s in spike_samples[1:]:
            if s - kept[-1] >= refractory_samples:
                kept.append(s)
        spike_samples = np.array(kept, dtype=int)

    return spike_samples


class DataReader:
    """Reads waveform data from TCP socket in a background thread."""

    def __init__(self, socket, bytes_per_block):
        self.socket = socket
        self.bytes_per_block = bytes_per_block
        self.chunks = []
        self.total_received = 0
        self.running = False
        self.thread = None

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._read_loop)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=5.0)

    def _read_loop(self):
        self.socket.settimeout(1.0)
        while self.running:
            try:
                chunk = self.socket.recv(65536)
                if chunk:
                    self.chunks.append(chunk)
                    self.total_received += len(chunk)
            except socket.timeout:
                continue
            except Exception as e:
                print(f'Read error: {e}')
                break

    def get_data(self):
        return b''.join(self.chunks)


def ReadWaveformDataDemo():
    n_channels = len(CHANNEL_ORDER)

    print('Connecting to TCP command server...')
    scommand = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    scommand.connect(('172.30.9.78', 5000))

    print('Connecting to TCP waveform server...')
    swaveform = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    swaveform.connect(('172.30.9.78', 5001))

    scommand.sendall(b'get runmode')
    commandReturn = str(scommand.recv(COMMAND_BUFFER_SIZE), "utf-8")

    if commandReturn != "Return: RunMode Stop":
        scommand.sendall(b'set runmode stop')
        time.sleep(0.1)

    scommand.sendall(b'get sampleratehertz')
    commandReturn = str(scommand.recv(COMMAND_BUFFER_SIZE), "utf-8")
    expectedReturnString = "Return: SampleRateHertz "
    if commandReturn.find(expectedReturnString) == -1:
        raise GetSampleRateFailure('Unable to get sample rate from server.')

    sample_rate = float(commandReturn[len(expectedReturnString):])
    print(f'Sample rate: {sample_rate} Hz')

    scommand.sendall(b'execute clearalldataoutputs')
    time.sleep(0.1)

    print(f'Enabling TCP output for {n_channels} channels...')
    for ch_num in CHANNEL_ORDER:
        cmd = f'set a-{ch_num:03d}.tcpdataoutputenabled true'.encode('utf-8')
        scommand.sendall(cmd)
        time.sleep(0.1)

    waveformBytesPerFrame = 4 + (2 * n_channels)
    waveformBytesPerBlock = FRAMES_PER_BLOCK * waveformBytesPerFrame + 4

    expected_samples = int(ACQUISITION_SECONDS * sample_rate)
    expected_blocks = (expected_samples // FRAMES_PER_BLOCK) + 1
    expected_bytes = expected_blocks * waveformBytesPerBlock
    print(f'Expecting ~{expected_bytes} bytes ({expected_blocks} blocks)')

    reader = DataReader(swaveform, waveformBytesPerBlock)

    print('Starting data reader...')
    reader.start()

    print(f'Acquiring {ACQUISITION_SECONDS} seconds of data...')
    scommand.sendall(b'set runmode run')

    start_time = time.time()
    while time.time() - start_time < ACQUISITION_SECONDS:
        elapsed = time.time() - start_time
        pct = 100 * reader.total_received / expected_bytes
        print(f'  {elapsed:.1f}s / {ACQUISITION_SECONDS}s - '
              f'Received {reader.total_received} bytes ({pct:.1f}%)')
        time.sleep(0.5)

    print('Stopping acquisition...')
    scommand.sendall(b'set runmode stop')

    print('Draining remaining data...')
    time.sleep(1.0)
    reader.stop()

    rawData = reader.get_data()
    print(f'Received {len(rawData)} bytes total')

    numBlocks = len(rawData) // waveformBytesPerBlock
    rawData = rawData[:numBlocks * waveformBytesPerBlock]
    print(f'Processing {numBlocks} complete blocks')

    if numBlocks == 0:
        print("ERROR: No complete data blocks received!")
        scommand.close()
        swaveform.close()
        return

    rawIndex = 0
    amplifierTimestamps = []
    amplifierData = [[] for _ in range(n_channels)]

    for block in range(numBlocks):
        magicNumber = struct.unpack('<I', rawData[rawIndex:rawIndex + 4])[0]
        rawIndex += 4
        if magicNumber != MAGIC_NUMBER:
            raise InvalidMagicNumber(
                f'Expected 0x{MAGIC_NUMBER:08x}, got 0x{magicNumber:08x}')

        for frame in range(FRAMES_PER_BLOCK):
            timestamp = struct.unpack('<i', rawData[rawIndex:rawIndex + 4])[0]
            rawIndex += 4
            amplifierTimestamps.append(timestamp)

            for ch in range(n_channels):
                rawSample = struct.unpack('<H', rawData[rawIndex:rawIndex + 2])[0]
                rawIndex += 2
                amplifierData[ch].append(
                    MICROVOLTS_PER_BIT * (rawSample - SAMPLE_OFFSET))

    amplifierTimestamps = np.array(amplifierTimestamps) / sample_rate
    amplifierData = [np.array(ch_data) for ch_data in amplifierData]

    actual_duration = len(amplifierTimestamps) / sample_rate
    print(f'Parsed {len(amplifierTimestamps)} samples ({actual_duration:.2f} seconds)')

    scommand.close()
    swaveform.close()

    # ========================================================================
    # LFP PROCESSING
    # ========================================================================

    print('\nExtracting LFP...')
    lfp_by_channel = {}
    lfp_rate = None

    for i, ch_num in enumerate(CHANNEL_ORDER):
        ch_name = f"A_{ch_num:03d}"
        wideband = amplifierData[i]
        lfp, lfp_rate = extract_lfp(wideband, sample_rate, LFP_LOWPASS, LFP_TARGET_RATE)
        lfp_by_channel[ch_name] = lfp

    print(f'LFP rate: {lfp_rate} Hz, samples per channel: {len(lfp)}')

    print('Computing spectra...')
    spectrum_calculator = LFPSpectrum(sample_rate=lfp_rate, nperseg=1000)
    spectra = {ch: spectrum_calculator.compute(lfp)
               for ch, lfp in lfp_by_channel.items()}

    print('Normalizing spectra...')
    rps = RelativePowerSpectrum(channel_order=CHANNEL_ORDER)
    normalized = rps.compute(spectra)

    print('Fitting 1/f power laws...')
    power_law = LFPPowerLaw(freq_range=(20, 100))
    fits = power_law.fit_dict(spectra)

    # ========================================================================
    # MUA SPIKE DETECTION  (-4 × RMS, 300 Hz HPF, negative crossings only)
    # ========================================================================

    print('\nDetecting MUA spikes...')
    spike_rates_by_channel = {}
    for i, ch_num in enumerate(CHANNEL_ORDER):
        ch_name = f"A_{ch_num:03d}"
        spike_samples = detect_mua_spikes(
            amplifierData[i], sample_rate,
            highpass_hz=MUA_HIGHPASS_HZ,
            threshold_rms=MUA_THRESHOLD_RMS,
            refractory_sec=MUA_REFRACTORY_SEC,
        )
        rate = len(spike_samples) / actual_duration
        spike_rates_by_channel[ch_name] = rate
        print(f'  {ch_name}: {len(spike_samples)} spikes  ({rate:.2f} Hz)')

    # ========================================================================
    # PLOTTING  — single figure with heatmap | band power | power-law panels
    # ========================================================================
    print('Plotting...')

    pl_plotter = LFPPowerLawSpectrumPlotter(
        channel_order=CHANNEL_ORDER,
        **POWER_LAW_PANELS,
    )
    sp_plotter = LFPSpikeRatePlotter(channel_order=CHANNEL_ORDER)

    n_pl = pl_plotter.n_axes
    n_sp = sp_plotter.n_axes

    # Width ratios: heatmap=2, band power=1, each param panel=1
    width_ratios = [2, 1] + [1] * n_pl + [1] * n_sp
    fig, axes = plt.subplots(
        1, 2 + n_pl + n_sp,
        figsize=(4 * (2 + n_pl + n_sp), 8),
        gridspec_kw={'width_ratios': width_ratios},
    )

    # --- Heatmap + band power ---
    heatmap_plotter = LFPSpectrumPlotter(
        channel_order=CHANNEL_ORDER, freq_range=FREQ_RANGE)
    heatmap_plotter.plot(normalized, ax=axes[0])
    axes[0].set_title("Relative Power Spectrum")

    band_plotter = LFPBandPowerPlotter(channel_order=CHANNEL_ORDER)
    band_plotter.plot(normalized, ax=axes[1])
    axes[1].set_title("Band Power Profile")

    # --- Power-law panels ---
    pl_plotter.plot_onto_axes(
        fits,
        axes[2 : 2 + n_pl],
        avg_spectrum_by_channel=spectra,
        label_y_axis=False,
    )

    # --- Spike rate panels ---
    sp_plotter.plot_onto_axes(
        spike_rates_by_channel,
        axes[2 + n_pl :],
        fits_by_channel=fits,
        label_y_axis=False,
    )

    fig.suptitle(f"LFP Analysis — {ACQUISITION_SECONDS}s acquisition")
    plt.tight_layout()
    plt.show()

    print('\nDone!')


if __name__ == '__main__':
    ReadWaveformDataDemo()