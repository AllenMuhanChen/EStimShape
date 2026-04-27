import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import matplotlib.lines as mlines
import matplotlib.pyplot as plt
import numpy as np

from clat.intan.marker_channels import read_digitalin_file
from clat.intan.rhs.load_intan_rhs_format import read_data
from clat.intan.spike_file import fetch_spike_tstamps_from_file


@dataclass
class NafcTrialEvents:
    """
    Parsed neural data for a single NAFC recording.

    All timestamps are in seconds from the start of the recording.
    """
    task_id: int
    sample_on: Optional[float]
    sample_off: Optional[float]
    choices_on: Optional[float]
    choices_off: Optional[float]
    spikes_by_channel: Dict = field(default_factory=dict)
    sample_rate: float = 30000.0


def _task_id_from_dir(recording_dir: str) -> int:
    """Extract task_id from directory name: {task_id}_{date}_{time}."""
    basename = os.path.basename(recording_dir.rstrip('/\\'))
    return int(basename.split('_')[0])


def _rising_edges(channel_data: np.ndarray) -> np.ndarray:
    return np.where(np.diff(channel_data.astype(np.int8)) == 1)[0] + 1


def _falling_edges(channel_data: np.ndarray) -> np.ndarray:
    return np.where(np.diff(channel_data.astype(np.int8)) == -1)[0] + 1


def _first_as_seconds(indices: np.ndarray, sample_rate: float) -> Optional[float]:
    if len(indices) == 0:
        return None
    return float(indices[0]) / sample_rate


class NafcNeuralParser:
    """
    Parse a single-trial NAFC Intan recording directory.

    Directory naming convention:  {task_id}_{YYMMDD}_{HHMMSS}
    e.g.  1777238072918508_260426_171633

    Digital channel mapping:
        digital-in-01 (index 0): sample on / off
        digital-in-02 (index 1): choices on / off
    """

    def parse(self, recording_dir: str) -> NafcTrialEvents:
        task_id = _task_id_from_dir(recording_dir)
        sample_rate = self._read_sample_rate(recording_dir)
        spikes_by_channel = self._read_spikes(recording_dir)
        events = self._read_events(recording_dir, sample_rate)
        return NafcTrialEvents(
            task_id=task_id,
            sample_rate=sample_rate,
            spikes_by_channel=spikes_by_channel,
            **events,
        )

    @staticmethod
    def _read_sample_rate(recording_dir: str) -> float:
        rhs_path = os.path.join(recording_dir, "info.rhs")
        data = read_data(rhs_path)
        return float(data['frequency_parameters']['amplifier_sample_rate'])

    @staticmethod
    def _read_spikes(recording_dir: str) -> dict:
        spike_path = os.path.join(recording_dir, "spike.dat")
        spikes_by_channel, _ = fetch_spike_tstamps_from_file(spike_path)
        return spikes_by_channel

    @staticmethod
    def _read_events(recording_dir: str, sample_rate: float) -> dict:
        digital_in_path = os.path.join(recording_dir, "digitalin.dat")
        digital_in = read_digitalin_file(digital_in_path)

        sample_ch = np.array(digital_in[0])
        choices_ch = np.array(digital_in[1])

        return {
            'sample_on':   _first_as_seconds(_rising_edges(sample_ch),  sample_rate),
            'sample_off':  _first_as_seconds(_falling_edges(sample_ch), sample_rate),
            'choices_on':  _first_as_seconds(_rising_edges(choices_ch),  sample_rate),
            'choices_off': _first_as_seconds(_falling_edges(choices_ch), sample_rate),
        }


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

_EVENT_STYLES: List[Tuple[str, str, str, str]] = [
    ('sample_on',   'green',  '--', 'Sample On'),
    ('sample_off',  'red',    '--', 'Sample Off'),
    ('choices_on',  'blue',   ':',  'Choices On'),
    ('choices_off', 'orange', ':',  'Choices Off'),
]


def plot_nafc_raster(events: NafcTrialEvents) -> None:
    channels = sorted(events.spikes_by_channel.keys(), key=str)
    n_channels = len(channels)

    if n_channels == 0:
        print("No spike data to plot.")
        return

    fig, ax = plt.subplots(figsize=(14, max(4, n_channels * 0.4)))

    colors = plt.cm.tab20(np.linspace(0, 1, n_channels))
    for row, channel in enumerate(channels):
        spikes = events.spikes_by_channel[channel]
        if spikes:
            ax.vlines(spikes, row + 0.1, row + 0.9, color=colors[row], linewidth=0.8)

    legend_handles = []
    for attr, color, linestyle, label in _EVENT_STYLES:
        t = getattr(events, attr)
        if t is not None:
            ax.axvline(t, color=color, linestyle=linestyle, linewidth=1.5, alpha=0.85)
            legend_handles.append(
                mlines.Line2D([], [], color=color, linestyle=linestyle,
                              label=f'{label}  ({t:.3f} s)')
            )

    ax.set_yticks(np.arange(n_channels) + 0.5)
    ax.set_yticklabels([str(ch) for ch in channels], fontsize=7)
    ax.set_ylim(0, n_channels)
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Channel')
    ax.set_title(f'NAFC Raster — task_id: {events.task_id}')
    if legend_handles:
        ax.legend(handles=legend_handles, loc='upper right', fontsize=9)
    plt.tight_layout()
    plt.show()


# ---------------------------------------------------------------------------
# Main — set RECORDING_DIR to test against a real recording
# ---------------------------------------------------------------------------

def main():
    # ── Set this to the path of a real NAFC recording directory ────────────
    RECORDING_DIR = "/run/user/1000/gvfs/sftp:host=172.30.9.78/mnt/data/EStimShape/allen_estimshape_exp_260426_0/2026-04-26/1777238072918508_260426_171633"
    # ───────────────────────────────────────────────────────────────────────

    parser = NafcNeuralParser()
    events = parser.parse(RECORDING_DIR)

    print(f"task_id     : {events.task_id}")
    print(f"sample_rate : {events.sample_rate:.0f} Hz")
    print(f"sample_on   : {events.sample_on}")
    print(f"sample_off  : {events.sample_off}")
    print(f"choices_on  : {events.choices_on}")
    print(f"choices_off : {events.choices_off}")
    total = sum(len(v) for v in events.spikes_by_channel.values())
    print(f"total spikes: {total} across {len(events.spikes_by_channel)} channels")

    plot_nafc_raster(events)


if __name__ == "__main__":
    main()
