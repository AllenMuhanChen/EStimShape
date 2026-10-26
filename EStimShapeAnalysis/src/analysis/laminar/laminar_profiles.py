"""
Per-session laminar profiles at the final probe position, from the GA recording.

For each session: trial-averaged LFP locked to GA stimulus onset (marker channels, via
MultiFileLFPParser), its CSD, and per-channel relative alpha-beta and gamma power
(see laminar_core.py for the methods). The suggested L4 markers are the strongest early
CSD sink and the gamma / alpha-beta crossover. Everything is saved to LaminarSessions +
LaminarProfiles in allen_data_repository, which laminar_calling_gui.py reads.

Final probe position: the session's final recording site, picked like
recording_site_area_distances.py (red Penetrations row with 'rec' or 'loc' in its label).
The tip distance comes from the notes the MRI viewer writes for an actual point
('ch<N> tip=<X>mm ...'); channel depths are tip - (600 + (31 - pos) * 65) µm. Sessions whose
row has no tip or channel in its notes fail loudly; give their tip in FINAL_TIP_MM.

Edit the settings at the top of main(), then run. One summary figure per session is shown
and saved into a new timestamped folder with a config.json of the settings.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict

sys.path.insert(0, str(Path(__file__).parents[3]))

import matplotlib.pyplot as plt
import numpy as np

from src.analysis.laminar.laminar_core import (
    CHANNEL_ORDER, channel_depth_mm, channel_name, channel_number, compute_csd,
    crossover_position, evoked_matrix, interpolate_channels, band_profile, strongest_sink,
)


def main():
    # ---------------------------------------------------------------- settings
    SESSIONS = None              # e.g. ["260702_0", "260708_0"]; None = every session with a final-site row
    SKIP_DONE = True             # skip sessions already in LaminarSessions
    PRE_S = 0.2                  # s of LFP before stim onset (MultiFileLFPParser default window)
    POST_S = 0.3                 # s after onset used for the evoked LFP / CSD
    BASELINE_S = 0.1             # baseline = last BASELINE_S before onset
    SINK_WINDOW_MS = (30, 90)    # strongest sink searched here = suggested L4
    HAMMING_SMOOTH = True        # 3-point spatial smoothing before the CSD
    ALPHA_BETA_HZ = (10, 19)     # same bands as penetration_lfp_analysis.BANDS
    GAMMA_HZ = (40, 150)
    NOISE_THRESHOLD_SD = 2.0     # RelativePowerSpectrum noisy-channel rule; noisy channels are interpolated
    EXCLUDE_CHANNELS = []        # channel numbers always treated as bad, e.g. [17]
    FINAL_SITE_LABEL_KEYWORDS = ['rec', 'loc']     # same as recording_site_area_distances.py
    FINAL_TIP_MM: Dict[str, float] = {}            # tip distance override, e.g. {"260702_0": 21.35}
    SAVE_ROOT = "/home/connorlab/Documents/plots/laminar_profiles"
    SHOW_PLOTS = True
    # -------------------------------------------------------------------------

    config = dict(PRE_S=PRE_S, POST_S=POST_S, BASELINE_S=BASELINE_S, SINK_WINDOW_MS=SINK_WINDOW_MS,
                  HAMMING_SMOOTH=HAMMING_SMOOTH, ALPHA_BETA_HZ=ALPHA_BETA_HZ, GAMMA_HZ=GAMMA_HZ,
                  NOISE_THRESHOLD_SD=NOISE_THRESHOLD_SD, EXCLUDE_CHANNELS=EXCLUDE_CHANNELS,
                  FINAL_SITE_LABEL_KEYWORDS=FINAL_SITE_LABEL_KEYWORDS, FINAL_TIP_MM=FINAL_TIP_MM)
    out_dir = os.path.join(SAVE_ROOT, datetime.now().strftime("%Y%m%d_%H%M%S"))
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "config.json"), "w") as f:
        json.dump(dict(config, SESSIONS=SESSIONS, SKIP_DONE=SKIP_DONE), f, indent=2)

    from clat.util.connection import Connection
    from src.analysis.laminar.laminar_db import REPO_DB, ensure_tables, save_session_profiles
    from src.analysis.laminar.laminar_mri import fetch_final_site
    repo = Connection(REPO_DB)
    ensure_tables(repo)

    if SESSIONS is None:
        from src.analysis.penetrations.recording_site_area_distances import (
            fetch_red_penetrations, filter_by_label_substring)
        SESSIONS = sorted({p['session_id'] for p in filter_by_label_substring(
            fetch_red_penetrations(repo, 'Penetrations'), FINAL_SITE_LABEL_KEYWORDS) if p['session_id']})
    done = set()
    if SKIP_DONE:
        repo.execute("SELECT session_id FROM LaminarSessions WHERE final_tip_mm IS NOT NULL")   # rows from the old deepest-idle version are redone
        done = {r[0] for r in repo.fetch_all()}

    failed = {}
    for sid in SESSIONS:
        if sid in done:
            print(f"{sid}: already in LaminarSessions, skipping (SKIP_DONE)")
            continue
        print(f"\n===== {sid} =====")
        try:
            site = fetch_final_site(repo, sid, label_keywords=FINAL_SITE_LABEL_KEYWORDS,
                                    tip_override_mm=FINAL_TIP_MM.get(sid))
            if site is None:
                raise RuntimeError(f"no red Penetrations row with {FINAL_SITE_LABEL_KEYWORDS} in its label")
            print(f"  final site: id {site['id']} {site['label']!r}, tip {site['tip_mm']:.2f} mm")
            trials, sr = load_ga_trials(sid, PRE_S)
            result = compute_session(trials, sr, site['tip_mm'], config)
            result['final_pen_id'] = int(site['id'])
            save_session_profiles(repo, sid, result)
            fig = plot_session(sid, result)
            fig.savefig(os.path.join(out_dir, f"{sid}_laminar_profile.png"), dpi=150)
            if SHOW_PLOTS:
                plt.show()
            plt.close(fig)
        except Exception as exc:
            failed[sid] = repr(exc)
            print(f"{sid}: FAILED: {exc!r}")
    if failed:
        print("\nFailed sessions:")
        for sid, err in failed.items():
            print(f"  {sid}: {err}")
        raise RuntimeError(f"{len(failed)} session(s) failed, see above")


# ─────────────────────────────────────────────────────────────────────────────
#  Loading
# ─────────────────────────────────────────────────────────────────────────────

def load_ga_trials(session_id: str, pre_s: float):
    """GA trials' LFP (channel number -> array starting pre_s before onset) and the LFP sample rate."""
    from clat.compile.task.compile_task_id import TaskIdCollector
    from clat.util.connection import Connection
    from src.intan.MultiFileLFPParser import MultiFileLFPParser
    from src.startup import context
    from src.startup.apply_session_context import apply_session_context

    apply_session_context(session_id)
    task_ids = TaskIdCollector(Connection(context.ga_database)).collect_task_ids()
    parser = MultiFileLFPParser(seconds_before_epoch=pre_s, to_cache=True,
                                cache_dir=context.ga_parsed_spikes_path.replace("parsed_spikes", "parsed_lfp"))
    lfp, epochs, sr = parser.parse(task_ids, context.ga_intan_path)
    trials = []
    for tid, by_ch in lfp.items():
        ep = epochs.get(tid)
        if not by_ch or ep is None or ep[0] < pre_s:   # window would be clipped at file start
            continue
        trials.append({channel_number(k): np.asarray(v) for k, v in by_ch.items()})
    print(f"  {len(trials)} GA trials with LFP ({len(task_ids)} task ids)")
    if not trials:
        raise RuntimeError("no GA trials with LFP")
    return trials, sr


# ─────────────────────────────────────────────────────────────────────────────
#  Computation
# ─────────────────────────────────────────────────────────────────────────────

def compute_session(trials, sr: float, tip_mm: float, config: dict) -> dict:
    from src.lfp.lfp_spectrum import LFPSpectrum
    from src.lfp.relative_power_spectrum import RelativePowerSpectrum

    pre_s, post_s = config['PRE_S'], config['POST_S']
    evoked = evoked_matrix(trials, sr, pre_s, post_s, config['BASELINE_S'])
    times_ms = (np.arange(evoked.shape[1]) / sr - pre_s) * 1000.0

    # Trial-averaged spectra per channel, relative power per frequency across channels
    spec = LFPSpectrum(sample_rate=sr)
    sums, counts = {}, {}
    for trial in trials:
        for ch, x in trial.items():
            if ch not in CHANNEL_ORDER:
                continue
            freqs, p = spec.compute(np.asarray(x, float))
            if ch in sums and len(p) != len(sums[ch]):
                continue
            sums[ch] = sums.get(ch, 0) + p
            counts[ch] = counts.get(ch, 0) + 1
    avg = {channel_name(ch): (freqs, sums[ch] / counts[ch]) for ch in sums}
    rps = RelativePowerSpectrum(channel_order=CHANNEL_ORDER, noise_threshold_sd=config['NOISE_THRESHOLD_SD'],
                                exclude_channels=list(config['EXCLUDE_CHANNELS']))
    rel = rps.compute(avg)
    noisy = sorted({channel_number(k) for k in rps.get_noisy_channels(avg)} | set(config['EXCLUDE_CHANNELS']))
    rel_mat = np.full((len(CHANNEL_ORDER), len(freqs)), np.nan)
    for k, (_, p) in rel.items():
        rel_mat[CHANNEL_ORDER.index(channel_number(k))] = p
    rel_mat = interpolate_channels(rel_mat, [CHANNEL_ORDER.index(c) for c in config['EXCLUDE_CHANNELS']])
    alpha_beta = band_profile(rel_mat, freqs, config['ALPHA_BETA_HZ'])
    gamma = band_profile(rel_mat, freqs, config['GAMMA_HZ'])

    phi = interpolate_channels(evoked, [CHANNEL_ORDER.index(c) for c in noisy])
    csd = compute_csd(phi, hamming=config['HAMMING_SMOOTH'])
    sink = strongest_sink(csd, times_ms, config['SINK_WINDOW_MS'])

    positions = np.arange(len(CHANNEL_ORDER))
    depths = channel_depth_mm(positions, tip_mm)
    cross = crossover_position(gamma, alpha_beta)
    print(f"  noisy/excluded channels: {noisy}")
    print(f"  strongest sink: pos {sink['pos']} at {sink['latency_ms']} ms; crossover pos {cross}")
    return dict(
        final_pen_id=None, final_tip_mm=float(tip_mm), sample_rate=float(sr),
        pre_ms=pre_s * 1000.0, n_trials=len(trials), noisy_channels=noisy,
        evoked=evoked, csd=csd, times_ms=times_ms, alpha_beta=alpha_beta, gamma=gamma, depths_mm=depths,
        sink_channel=CHANNEL_ORDER[sink['pos']] if sink['pos'] is not None else None,
        sink_latency_ms=sink['latency_ms'],
        sink_depth_mm=float(depths[sink['pos']]) if sink['pos'] is not None else None,
        crossover_depth_mm=float(np.interp(cross, positions, depths)) if cross is not None else None,
        config=config,
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Summary figure
# ─────────────────────────────────────────────────────────────────────────────

def plot_session(session_id: str, r: dict, font_size: int = 13):
    plt.rcParams.update({'font.size': font_size})
    fig, (ax_csd, ax_lfp, ax_band) = plt.subplots(1, 3, figsize=(15, 8), sharey=True,
                                                  gridspec_kw={'width_ratios': [2, 1.4, 1]})
    d = r['depths_mm']
    step = d[1] - d[0]
    extent = (r['times_ms'][0], r['times_ms'][-1], d[-1] + step / 2, d[0] - step / 2)
    lim = np.nanpercentile(np.abs(r['csd']), 99) or 1.0
    im = ax_csd.imshow(-r['csd'], aspect='auto', cmap='RdBu_r', vmin=-lim, vmax=lim, extent=extent,
                       interpolation='bilinear')   # sinks red, sources blue
    cb = fig.colorbar(im, ax=ax_csd, pad=0.01)
    cb.set_ticks([-lim, 0, lim])
    cb.set_ticklabels(['source', '0', 'sink'])
    ax_csd.axvline(0, color='k', lw=1)
    ax_csd.set_xlabel('Time from stim onset (ms)')
    ax_csd.set_ylabel('Depth under chamber (mm)')
    ax_csd.set_title('CSD')

    lfp = r['evoked']
    scale = 0.8 * step / (np.nanmax(np.abs(lfp)) or 1.0)
    for i in range(len(d)):
        ax_lfp.plot(r['times_ms'], d[i] - lfp[i] * scale, color='k', lw=0.8)
    ax_lfp.axvline(0, color='k', lw=1)
    ax_lfp.set_xlabel('Time from stim onset (ms)')
    ax_lfp.set_title('Evoked LFP')

    ax_band.plot(r['alpha_beta'], d, color='tab:blue', lw=2, label='alpha-beta')
    ax_band.plot(r['gamma'], d, color='tab:red', lw=2, label='gamma')
    ax_band.set_xlabel('Relative power')
    ax_band.set_title('Band power')

    for ax in (ax_csd, ax_lfp, ax_band):
        if r['sink_depth_mm'] is not None:
            ax.axhline(r['sink_depth_mm'], color='tab:red', ls='--', lw=1.2, label='strongest sink')
        if r['crossover_depth_mm'] is not None:
            ax.axhline(r['crossover_depth_mm'], color='tab:purple', ls=':', lw=1.5, label='crossover')
    ax_band.legend(loc='lower right', frameon=False)
    ax_csd.set_ylim(extent[2], extent[3])
    fig.suptitle(f'{session_id} laminar profile')
    fig.tight_layout()
    return fig


if __name__ == '__main__':
    main()
