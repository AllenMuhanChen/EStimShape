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

import re
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
from src.lfp.lfp_power_law import FOOOFPowerLaw
from src.lfp.mua_detection import detect_mua_spikes
from src.repository.export_to_repository import read_session_id_and_date_from_db_name
from src.startup import context

# Import context for Intan path and database name
from src.startup.context import ga_database

# Import session ID parser (reuse existing function, do not recreate)


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
POWER_LAW_PANELS = dict(
    show_exponent=True,
    show_amplitude=True,
    show_r_squared=False,
    show_gamma_ratio=False,
    show_residual_gamma=False,
    show_residual_alpha_beta=False
)

# ---- MUA detection config -----------------------------------------------
MUA_HIGHPASS_HZ    = 300.0   # classic HPF cutoff for spike detection
MUA_THRESHOLD_RMS  = 4.0     # threshold multiplier: -N × RMS
MUA_REFRACTORY_SEC = 0.001   # 1 ms refractory period
# -------------------------------------------------------------------------

# ---- Tissue-score / MRI plot config -------------------------------------
# Brain-extracted MRI used by the alignment optimiser in run_per_session.
# Setting volume_path to this avoids fitting tissue scores to skull/scalp.
NO_SKULL_MRI_PATH = (
    "/home/connorlab/Documents/MRI/45X_MRI/"
    "45X_110315_4_1_corrected_warper_native/rigid_aligned/"
    "subject_ns_rigid_aligned.nii.gz"
)
TISSUE_PLOT_N_PCS = 2
# -------------------------------------------------------------------------


class GetSampleRateFailure(Exception):
    pass


class InvalidMagicNumber(Exception):
    pass


def sftp_to_local_path(sftp_path: str) -> str:
    """Strip the SFTP mount prefix, returning the bare path on the Intan machine.

    Example:
        /run/user/1000/gvfs/sftp:host=172.30.9.78/mnt/data/EStimShape/allen_ga_exp_260115_0
        -> /mnt/data/EStimShape/allen_ga_exp_260115_0
    """
    match = re.search(r'sftp:host=[^/]+(/.*)', sftp_path)
    if match:
        return match.group(1)
    raise ValueError(f"Could not parse local path from: {sftp_path!r}")


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


# detect_mua_spikes is defined in src/lfp/mua_detection.py and imported above


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


def _load_pen_offsets(monkey_specific_path: str) -> dict:
    """Read the latest global az/el/depth offsets saved by the alignment optimiser.

    Returns an empty dict if the file does not exist, so callers can pass the
    result straight through to compute_mri_comparison.
    """
    import json
    import os
    path = os.path.splitext(monkey_specific_path)[0] + '_pen_offsets.json'
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)


def plot_tissue_score_vs_mri(session_id: str) -> None:
    """Load PCA, predict tissue score for this session, sample MRI along the
    trajectory, and plot per-session tissue vs MRI with PC profiles.

    Mirrors the per-session figure produced by run_per_session, restricted to
    a single session and with an extra PC-profile panel so you can see what
    drove the prediction.
    """
    from clat.util.connection import Connection

    from src.analysis.penetrations.pca_predict import (
        MODEL_PCA_V2, TissuePipeline,
    )
    from src.analysis.penetrations.alignment_optimize import (
        MRI_VIEWER_CONFIG_PATH, compute_mri_comparison,
        compute_trajectory_fit_scores, load_mri_pipeline,
    )
    from src.analysis.penetrations.penetration_plots import (
        _draw_mri_tissue_line, _draw_pc_profiles, _draw_tissue_strip,
    )

    conn = Connection(
        database="allen_data_repository",
        user="xper_rw",
        password="up2nite",
        host="172.30.6.61",
    )

    pipeline = TissuePipeline(
        name='PCA_V2',
        model=MODEL_PCA_V2,
        decomp_method='pca',
        n_components=2,
        use_varimax=False,
        within_session_normalize=False,
        pc_smooth_sigma=2.0,
        exclude_features=[],
    )

    print(f"\nFitting PCA across all sessions and predicting tissue scores ...")
    fit = pipeline.fit_and_predict(conn)
    df_conf = fit['df']
    pca = fit['pca']

    if session_id not in df_conf['session_id'].unique():
        print(f"  No PenetrationMetrics rows for session {session_id} — "
              f"skipping tissue/MRI plot.")
        return

    print("\nLoading MRI pipeline (with saved chamber + pen corrections) ...")
    mri_pipeline = load_mri_pipeline(MRI_VIEWER_CONFIG_PATH,
                                     volume_path=NO_SKULL_MRI_PATH)
    pen_offsets = _load_pen_offsets(mri_pipeline['monkey_specific_path'])
    daz    = float(pen_offsets.get('daz_deg',    0.0))
    del_   = float(pen_offsets.get('del_deg',    0.0))
    ddepth = float(pen_offsets.get('ddepth_mm',  0.0))
    per_session_corrections = pen_offsets.get('per_session_corrections', {})
    if pen_offsets:
        print(f"  pen_offsets: daz={daz:+.3f}°  del={del_:+.3f}°  "
              f"ddepth={ddepth:+.3f} mm  "
              f"({len(per_session_corrections)}_ per-session entries)")

    df_conf = compute_mri_comparison(
        df_conf, conn, mri_pipeline,
        daz=daz, del_=del_, ddepth=ddepth,
        per_session_corrections=per_session_corrections,
    )
    fit_scores = compute_trajectory_fit_scores(df_conf)

    sdata = (df_conf[df_conf['session_id'] == session_id]
             .copy()
             .sort_values('depth_under_chamber_mm'))
    depths   = sdata['depth_under_chamber_mm'].values
    ts       = sdata['tissue_score'].values
    conf     = sdata['tissue_confidence'].values
    mri_norm = sdata['mri_normalized'].values
    mri_vmax = float(np.nanmax(mri_norm)) if np.any(np.isfinite(mri_norm)) else 1.0

    strip_w = 0.4
    fig, axes = plt.subplots(
        1, 5,
        figsize=(14, 10),
        gridspec_kw={'width_ratios': [strip_w, strip_w, strip_w, 1.0, 1.2]},
    )
    ax_mri, ax_ts, ax_conf, ax_line, ax_pc = axes
    _draw_tissue_strip(ax_mri,  depths, mri_norm, title='MRI',        vmax=mri_vmax)
    _draw_tissue_strip(ax_ts,   depths, ts,       title='Tissue',     vmax=1.0)
    _draw_tissue_strip(ax_conf, depths, conf,     title='Confidence', vmax=1.0)
    _draw_mri_tissue_line(ax_line, depths, ts, mri_norm, fit_scores, session_id, conf)
    _draw_pc_profiles(ax_pc, sdata, depths, pca, n_pcs=TISSUE_PLOT_N_PCS)

    fig.suptitle(
        f'Tissue score vs MRI — {session_id}\n'
        '(black=sulcus, gray=GM, white=WM)',
        fontsize=11,
    )
    plt.tight_layout()

    savepath = f"/home/connorlab/Documents/plots/{session_id}/tissue_score_vs_mri.png"
    try:
        import os
        os.makedirs(os.path.dirname(savepath), exist_ok=True)
        fig.savefig(savepath, dpi=300)
        print(f"  Saved → {savepath}")
    except Exception as exc:
        print(f"  Could not save figure: {exc}")

    plt.show()


def ReadWaveformDataDemo():
    n_channels = len(CHANNEL_ORDER)

    # Channels arrive from TCP in ascending numeric order regardless of enable order
    sorted_channels = sorted(CHANNEL_ORDER)

    # ========================================================================
    # PROMPT FOR DEPTH BEFORE CONNECTING — no timing pressure yet
    # ========================================================================
    depth = input("Enter electrode depth (integer): ").strip()
    session_id, _ = read_session_id_and_date_from_db_name(ga_database)
    base_filename = f"idle_{session_id}_{depth}"
    local_intan_path = sftp_to_local_path(context.ga_intan_path)
    print(f'Intan save path : {local_intan_path}')
    print(f'Intan base name : {base_filename}')

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

    # ========================================================================
    # SET FILENAME AND PATH ON INTAN MACHINE BEFORE RECORDING
    # ========================================================================
    print('Configuring Intan save filename...')
    scommand.sendall(b'set filename.basefilename ' + base_filename.encode('utf-8'))
    time.sleep(0.1)
    scommand.sendall(b'set filename.path ' + local_intan_path.encode('utf-8'))
    time.sleep(0.1)

    scommand.sendall(b'set impedancefilename.basefilename ' + base_filename.encode('utf-8'))
    time.sleep(0.1)
    scommand.sendall(b'set impedancefilename.path ' + local_intan_path.encode('utf-8'))
    time.sleep(0.1)


    # IMPEDANCE CHECK
    scommand.sendall(b'execute measureimpedance')
    time.sleep(3)  # wait 3 seconds for impedance measurement to complete
    scommand.sendall(b'execute saveimpedance')

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
    scommand.sendall(b'set runmode record')

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

    print('Starting acquisition for experimenter convenience...')
    scommand.sendall(b'set runmode run')

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

    # TCP stream delivers channels in ascending numeric order (sorted_channels),
    # regardless of the order they were enabled.
    for i, ch_num in enumerate(sorted_channels):
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
    power_law = FOOOFPowerLaw()
    fits = power_law.fit_dict(spectra)

    # ========================================================================
    # MUA SPIKE DETECTION  (-4 × RMS, 300 Hz HPF, negative crossings only)
    # ========================================================================

    print('\nDetecting MUA spikes...')
    spike_rates_by_channel = {}
    for i, ch_num in enumerate(sorted_channels):
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

    db_name = f"allen_ga_exp_{session_id}"
    from src.lfp.penetration_lfp_analysis import INTAN_SFTP_PREFIX
    intan_path = f"{INTAN_SFTP_PREFIX}/{db_name}"
    # Tip start is read from PenetrationTipStart in allen_data_repository, never
    # defaulted. If this session has no tip start yet, prompt for it and save it
    # before analyzing so the value lives in the database.
    from src.lfp.penetration_lfp_analysis import (
        PenetrationLFPAnalysis, get_tip_start, save_tip_start,
    )
    if get_tip_start(session_id) is None:
        entered = input(
            f"No tip start found for session {session_id}. "
            f"Enter tip start depth (mm): ").strip()
        save_tip_start(session_id, float(entered))
        print(f"Saved tip start {entered} mm for session {session_id}.")
    PenetrationLFPAnalysis(session_id=session_id, intan_path=intan_path).run()

    try:
        plot_tissue_score_vs_mri(session_id)
    except Exception as exc:
        import traceback
        print(f"  Tissue/MRI plot skipped: {exc}")
        traceback.print_exc()

    print('Plotting...')
    #
    pl_plotter = LFPPowerLawSpectrumPlotter(
        channel_order=CHANNEL_ORDER,
        **POWER_LAW_PANELS,
    )
    sp_plotter = LFPSpikeRatePlotter(channel_order=CHANNEL_ORDER)

    n_pl = pl_plotter.n_axes
    n_sp = sp_plotter.n_axes

    width_ratios = [2, 1] + [1] * n_pl + [1] * n_sp
    fig, axes = plt.subplots(
        1, 2 + n_pl + n_sp,
        figsize=(4 * (2 + n_pl + n_sp), 8),
        gridspec_kw={'width_ratios': width_ratios},
    )

    heatmap_plotter = LFPSpectrumPlotter(
        channel_order=CHANNEL_ORDER, freq_range=FREQ_RANGE)
    heatmap_plotter.plot(normalized, ax=axes[0])
    axes[0].set_title("Relative Power Spectrum")

    band_plotter = LFPBandPowerPlotter(channel_order=CHANNEL_ORDER)
    band_plotter.plot(normalized, ax=axes[1])
    axes[1].set_title("Band Power Profile")

    pl_plotter.plot_onto_axes(
        fits,
        axes[2: 2 + n_pl],
        avg_spectrum_by_channel=spectra,
        label_y_axis=False,
    )

    sp_plotter.plot_onto_axes(
        spike_rates_by_channel,
        axes[2 + n_pl:],
        fits_by_channel=fits,
        label_y_axis=False,
    )

    fig.suptitle(f"LFP Analysis — {ACQUISITION_SECONDS}s acquisition  |  {base_filename}")
    plt.tight_layout()

    fig_fits = pl_plotter.plot_spectrum_fits(fits, avg_spectrum_by_channel=spectra)
    fig_fits.suptitle(f"FOOOF Spectral Fits — {ACQUISITION_SECONDS}s acquisition  |  {base_filename}")

    plt.show()

    print('\nDone!')


if __name__ == '__main__':
    ReadWaveformDataDemo()