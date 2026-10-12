"""
Cross-channel synchrony PSTH: an artifact check for the NAFC choice period.

A stimulation artifact is picked up by every electrode at the same instant,
so it produces threshold crossings on many channels within a fraction of a
millisecond. Real spikes on electrodes 65+ um apart almost never line up
that tightly across many channels. Counting these near-simultaneous
multi-channel events over time therefore tracks artifact contamination.

Methods
-------
For each trial, every channel's spike times are binned at sync_window_s
(default 0.2 ms = 6 samples at 30 kHz) from -before_s to +after_s around
choices_on. A bin is "synchronous" when at least min_channels distinct
channels have a spike in that bin or the next one (two adjacent bins, so
events straddling a bin edge are not missed). Runs of consecutive
synchronous bins count as one event, timed at the first bin. Events are then
histogrammed in bin_size_s bins and divided by the bin width, giving a
synchronous-event rate (events/s) per trial; mean and SEM are taken across
trials, separately for EStim ON and OFF. No choice-period clipping is
applied, and the default window reaches back into the sample period, so the
EStim artifact during the sample on ON trials serves as a positive control:
a working measure should be high there on ON trials and near zero on OFF
trials.

The pooled spike rate (all channels, spikes/s) is saved alongside so the
event rate can be compared with how many spikes there were to coincide.
When the amplitude artifact mask is on, the fraction of each bin covered by
artifact intervals (mean across trials) is saved too. Synchrony itself is
computed on the unmasked crossings, so it stays an independent check.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

SYNC_TABLE_NAME = "NafcChoicePeriodSynchrony"


def trial_sync_events(spikes_by_channel: dict, t0: float, before_s: float, after_s: float,
                      sync_window_s: float, min_channels: int) -> np.ndarray:
    """Times (relative to t0) of synchronous multi-channel events in one trial."""
    n_fine = int(np.ceil((before_s + after_s) / sync_window_s))
    edges = -before_s + sync_window_s * np.arange(n_fine + 1)
    presence = []
    for spikes in spikes_by_channel.values():
        rel = np.asarray(spikes, dtype=float) - t0
        rel = rel[(rel >= edges[0]) & (rel < edges[-1])]
        if len(rel) == 0:
            continue
        counts, _ = np.histogram(rel, bins=edges)
        presence.append(counts > 0)
    if len(presence) < min_channels:
        return np.array([])
    presence = np.vstack(presence)
    near = presence.copy()
    near[:, :-1] |= presence[:, 1:]
    sync = near.sum(axis=0) >= min_channels
    starts = np.flatnonzero(sync & ~np.concatenate([[False], sync[:-1]]))
    return edges[starts]


def summarize_synchrony(data: pd.DataFrame, *, before_s: float = 1.0, after_s: float = 1.0,
                        bin_size_s: float = 0.01, sync_window_s: float = 0.0002,
                        min_channels: int = 8, channels: Optional[list] = None) -> dict:
    """Synchrony PSTH (events/s) and pooled spike PSTH per EStim condition.

    channels: restrict to these channel names (default: every channel in the data)."""
    n_bins = int(round((before_s + after_s) / bin_size_s))
    bins = -before_s + bin_size_s * np.arange(n_bins + 1)
    from src.analysis.nafc.neural.choice_period_artifact_mask import bin_coverage
    per_trial = {k: {"sync": [], "spikes": [], "artifact": []} for k in (False, True)}
    n_channels_seen = set()
    for _, trial in data.iterrows():
        neural = trial.get("NeuralData")
        if not isinstance(neural, dict) or neural.get("choices_on") is None:
            continue
        spikes_by_channel = neural.get("spikes_by_channel", {})
        if channels is not None:
            spikes_by_channel = {c: v for c, v in spikes_by_channel.items() if c in channels}
        n_channels_seen.update(spikes_by_channel)
        t0 = neural["choices_on"]
        events = trial_sync_events(spikes_by_channel, t0, before_s, after_s,
                                   sync_window_s, min_channels)
        sync_counts, _ = np.histogram(events, bins=bins)
        all_spikes = np.concatenate([np.asarray(v, dtype=float) for v in spikes_by_channel.values()]
                                    ) - t0 if spikes_by_channel else np.array([])
        spike_counts, _ = np.histogram(all_spikes, bins=bins)
        estim_on = bool(trial.get("EStimEnabled"))
        per_trial[estim_on]["sync"].append(sync_counts / bin_size_s)
        per_trial[estim_on]["spikes"].append(spike_counts / bin_size_s)
        intervals = trial.get("ArtifactIntervals")
        if isinstance(intervals, list):
            per_trial[estim_on]["artifact"].append(bin_coverage(bins, t0, intervals))

    out = {"bins": bins, "sync_window_s": sync_window_s, "min_channels": min_channels,
           "n_channels": len(n_channels_seen), "conditions": {}}
    for estim_on, d in per_trial.items():
        c = {"n_trials": len(d["sync"])}
        for key in ("sync", "spikes", "artifact"):
            if d[key]:
                arr = np.vstack(d[key])
                mean = arr.mean(axis=0)
                sem = arr.std(axis=0, ddof=1) / np.sqrt(len(arr)) if len(arr) > 1 \
                    else np.full(n_bins, np.nan)
            else:
                mean = sem = np.full(n_bins, np.nan)
            c[f"{key}_rate_mean"], c[f"{key}_rate_sem"] = mean, sem
        out["conditions"][estim_on] = c
    return out


# ---------------------------------------------------------------------------
# Repository table
# ---------------------------------------------------------------------------

CREATE_SYNC_TABLE_SQL = f"""
    CREATE TABLE IF NOT EXISTS {SYNC_TABLE_NAME}
    (
        session_id        VARCHAR(10) NOT NULL,
        spike_source      VARCHAR(50) NOT NULL,
        is_estim_on       BOOLEAN     NOT NULL,
        n_trials          INT         NOT NULL,
        n_channels        INT,
        sync_window_s     DOUBLE,
        min_channels      INT,
        psth_align        VARCHAR(20),
        psth_start_s      DOUBLE,
        psth_bin_size_s   DOUBLE,
        sync_rate_mean    LONGTEXT,   -- synchronous events/s per bin
        sync_rate_sem     LONGTEXT,
        spike_rate_mean   LONGTEXT,   -- pooled spikes/s (all channels) per bin
        spike_rate_sem    LONGTEXT,
        artifact_frac_mean LONGTEXT,  -- fraction of each bin inside artifact intervals
        artifact_frac_sem  LONGTEXT,
        PRIMARY KEY (session_id, spike_source, is_estim_on),
        FOREIGN KEY (session_id) REFERENCES Sessions (session_id) ON DELETE CASCADE
    ) ENGINE = InnoDB
      DEFAULT CHARSET = latin1
"""

_SYNC_COLUMNS = ["session_id", "spike_source", "is_estim_on", "n_trials", "n_channels",
                 "sync_window_s", "min_channels", "psth_align", "psth_start_s",
                 "psth_bin_size_s", "sync_rate_mean", "sync_rate_sem", "spike_rate_mean",
                 "spike_rate_sem", "artifact_frac_mean", "artifact_frac_sem"]


def ensure_synchrony_table(conn) -> None:
    conn.execute(CREATE_SYNC_TABLE_SQL)
    for col in ("artifact_frac_mean", "artifact_frac_sem"):
        try:
            conn.execute(f"ALTER TABLE {SYNC_TABLE_NAME} ADD COLUMN {col} LONGTEXT")
        except Exception:
            pass  # column already exists


def synchrony_rows(session_id: str, sync: dict, *, spike_source: str) -> list[tuple]:
    from src.analysis.nafc.neural.choice_period_response import encode_array
    bins = sync["bins"]
    rows = []
    for estim_on, c in sync["conditions"].items():
        rows.append((session_id, spike_source, bool(estim_on), c["n_trials"], sync["n_channels"],
                     sync["sync_window_s"], sync["min_channels"], "choices_on", float(bins[0]),
                     float(bins[1] - bins[0]), encode_array(c["sync_rate_mean"]),
                     encode_array(c["sync_rate_sem"]), encode_array(c["spikes_rate_mean"]),
                     encode_array(c["spikes_rate_sem"]), encode_array(c["artifact_rate_mean"]),
                     encode_array(c["artifact_rate_sem"])))
    return rows


def insert_synchrony_rows(conn, rows: list[tuple]) -> None:
    placeholders = ", ".join(["%s"] * len(_SYNC_COLUMNS))
    updates = ", ".join(f"{c} = VALUES({c})" for c in _SYNC_COLUMNS[3:])
    sql = (f"INSERT INTO {SYNC_TABLE_NAME} ({', '.join(_SYNC_COLUMNS)}) "
           f"VALUES ({placeholders}) ON DUPLICATE KEY UPDATE {updates}")
    for row in rows:
        conn.execute(sql, row)
