"""
allen_data_repository tables for laminar position, and the data source the calling GUI reads.

    LaminarSessions   one row per session: final probe position + suggested markers
    LaminarProfiles   one row per (session, channel): evoked LFP, CSD, band profiles
    LaminarCalls      one row per (session, channel): the class you called in the GUI
    LaminarCallNotes  one row per session: notes + MRI slice angle used when calling

Channels are stored as channel numbers (A-007 -> 7). Waveforms are comma-separated
text, like LFPWaveforms.
"""

import json
import time
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from src.analysis.laminar.laminar_core import (
    CHANNEL_ORDER, channel_number,
)

REPO_DB = "allen_data_repository"

_CREATE = [
    """CREATE TABLE IF NOT EXISTS LaminarSessions (
        session_id            VARCHAR(32) NOT NULL PRIMARY KEY,
        final_pen_id          INT,
        final_tip_mm          DOUBLE,
        sample_rate           DOUBLE,
        pre_ms                DOUBLE,
        n_trials              INT,
        noisy_channels        TEXT,
        sink_channel          INT,
        sink_latency_ms       DOUBLE,
        sink_depth_mm         DOUBLE,
        crossover_depth_mm    DOUBLE,
        config                TEXT,
        computed_tstamp       BIGINT
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS LaminarProfiles (
        session_id     VARCHAR(32) NOT NULL,
        channel        INT NOT NULL,
        probe_pos      INT,
        depth_mm       DOUBLE,
        evoked_lfp     MEDIUMTEXT,
        csd            MEDIUMTEXT,
        alpha_beta_rel DOUBLE,
        gamma_rel      DOUBLE,
        PRIMARY KEY (session_id, channel)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS LaminarCalls (
        session_id    VARCHAR(32) NOT NULL,
        channel       INT NOT NULL,
        depth_mm      DOUBLE,
        laminar_class VARCHAR(16),
        tstamp        BIGINT,
        PRIMARY KEY (session_id, channel)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS LaminarCallNotes (
        session_id     VARCHAR(32) NOT NULL PRIMARY KEY,
        notes          TEXT,
        mri_phi_deg    DOUBLE,
        tstamp         BIGINT
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
]


def ensure_tables(conn) -> None:
    for sql in _CREATE:
        conn.execute(sql)


def _arr_to_text(x) -> str:
    return ','.join('nan' if not np.isfinite(v) else f'{v:.6g}' for v in np.asarray(x, float))


def _text_to_arr(s) -> np.ndarray:
    return np.fromstring(s, sep=',') if s else np.array([])


def save_session_profiles(conn, session_id: str, result: dict) -> None:
    """Write one laminar_profiles result (see laminar_profiles.compute_session)."""
    ensure_tables(conn)
    conn.execute(
        """INSERT INTO LaminarSessions (session_id, final_pen_id, final_tip_mm, sample_rate,
               pre_ms, n_trials, noisy_channels, sink_channel, sink_latency_ms, sink_depth_mm,
               crossover_depth_mm, config, computed_tstamp)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
           ON DUPLICATE KEY UPDATE final_pen_id=VALUES(final_pen_id),
               final_tip_mm=VALUES(final_tip_mm), sample_rate=VALUES(sample_rate),
               pre_ms=VALUES(pre_ms), n_trials=VALUES(n_trials), noisy_channels=VALUES(noisy_channels),
               sink_channel=VALUES(sink_channel), sink_latency_ms=VALUES(sink_latency_ms),
               sink_depth_mm=VALUES(sink_depth_mm), crossover_depth_mm=VALUES(crossover_depth_mm),
               config=VALUES(config), computed_tstamp=VALUES(computed_tstamp)""",
        (session_id, result['final_pen_id'], result['final_tip_mm'], result['sample_rate'],
         result['pre_ms'], result['n_trials'], ','.join(str(c) for c in result['noisy_channels']),
         result['sink_channel'], result['sink_latency_ms'], result['sink_depth_mm'],
         result['crossover_depth_mm'], json.dumps(result['config']), int(time.time() * 1000)))
    for pos, ch in enumerate(CHANNEL_ORDER):
        conn.execute(
            """INSERT INTO LaminarProfiles (session_id, channel, probe_pos, depth_mm, evoked_lfp, csd,
                   alpha_beta_rel, gamma_rel) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
               ON DUPLICATE KEY UPDATE probe_pos=VALUES(probe_pos), depth_mm=VALUES(depth_mm),
                   evoked_lfp=VALUES(evoked_lfp), csd=VALUES(csd),
                   alpha_beta_rel=VALUES(alpha_beta_rel), gamma_rel=VALUES(gamma_rel)""",
            (session_id, ch, pos, float(result['depths_mm'][pos]),
             _arr_to_text(result['evoked'][pos]), _arr_to_text(result['csd'][pos]),
             _nan_to_none(result['alpha_beta'][pos]), _nan_to_none(result['gamma'][pos])))


def _nan_to_none(v):
    return None if v is None or not np.isfinite(v) else float(v)


class LaminarDBSource:
    """Everything the calling GUI shows for a session, read from allen_data_repository.

    mri_config_path / corrections_file: as in recording_site_area_distances.py.
    tissue_pipeline: a TissuePipeline (analysis/penetrations/run_pooled.py), fitted once
        on PenetrationMetrics across sessions, or None to skip the ephys tissue strip.
    """

    def __init__(self, mri_config_path: str, corrections_file: Optional[str] = None,
                 tissue_pipeline=None):
        from clat.util.connection import Connection
        self.conn = Connection(REPO_DB)
        ensure_tables(self.conn)
        self.mri_config_path = mri_config_path
        self.corrections_file = corrections_file
        self.tissue_pipeline = tissue_pipeline
        self._tissue_df = None
        self._geom_cache = {}

    # ------------------------------------------------------------- sessions
    def sessions(self) -> List[str]:
        self.conn.execute("SELECT session_id FROM LaminarSessions ORDER BY session_id")
        return [r[0] for r in self.conn.fetch_all()]

    def session_info(self, session_id: str) -> dict:
        self.conn.execute(
            "SELECT final_pen_id, final_tip_mm, sample_rate, pre_ms, n_trials, noisy_channels, "
            "sink_channel, sink_latency_ms, sink_depth_mm, crossover_depth_mm FROM LaminarSessions "
            "WHERE session_id = %s", (session_id,))
        r = self.conn.fetch_all()[0]
        keys = ['final_pen_id', 'final_tip_mm', 'sample_rate', 'pre_ms', 'n_trials',
                'noisy_channels', 'sink_channel', 'sink_latency_ms', 'sink_depth_mm', 'crossover_depth_mm']
        info = dict(zip(keys, r))
        info['noisy_channels'] = [int(c) for c in (info['noisy_channels'] or '').split(',') if c]
        return info

    def profiles(self, session_id: str) -> pd.DataFrame:
        self.conn.execute(
            "SELECT channel, probe_pos, depth_mm, evoked_lfp, csd, alpha_beta_rel, gamma_rel "
            "FROM LaminarProfiles WHERE session_id = %s ORDER BY probe_pos", (session_id,))
        rows = self.conn.fetch_all()
        df = pd.DataFrame(rows, columns=['channel', 'probe_pos', 'depth_mm', 'evoked_lfp', 'csd',
                                         'alpha_beta_rel', 'gamma_rel'])
        df['evoked_lfp'] = df['evoked_lfp'].map(_text_to_arr)
        df['csd'] = df['csd'].map(_text_to_arr)
        return df

    # ---------------------------------------------------- whole-drive metrics
    def drive_metrics(self, session_id: str) -> pd.DataFrame:
        """PenetrationMetrics rows for the session (+ p_wm / p_gm / p_sulcus if a tissue pipeline is set)."""
        self.conn.execute("SELECT * FROM PenetrationMetrics WHERE session_id = %s "
                          "ORDER BY depth_under_chamber_mm", (session_id,))
        rows = self.conn.fetch_all()
        self.conn.execute("DESCRIBE PenetrationMetrics")
        cols = [r[0] for r in self.conn.fetch_all()]
        df = pd.DataFrame(rows, columns=cols)
        tissue = self._tissue()
        if tissue is not None:
            t = tissue[tissue['session_id'] == session_id]
            keep = ['depth_under_chamber_mm'] + [c for c in t.columns if c.startswith('p_')]
            df = df.merge(t[keep], on='depth_under_chamber_mm', how='left')
        return df

    def _tissue(self):
        if self.tissue_pipeline is None:
            return None
        if self._tissue_df is None:
            print(f"Fitting tissue pipeline {self.tissue_pipeline.name} on PenetrationMetrics ...")
            self._tissue_df = self.tissue_pipeline.fit_and_predict(self.conn)['df']
        return self._tissue_df

    # ---------------------------------------------------------------- estim
    def estim_channels(self, session_id: str) -> List[int]:
        self.conn.execute("SELECT DISTINCT channel FROM EStimParameters WHERE session_id = %s AND a1 > 0",
                          (session_id,))
        return sorted({c for (s,) in self.conn.fetch_all() if (c := channel_number(s)) is not None})

    # ------------------------------------------------------------------ MRI
    def mri(self, session_id: str):
        from src.analysis.laminar.laminar_mri import load_trajectory_mri
        pen_id = self.session_info(session_id)['final_pen_id']
        self.conn.execute("SELECT id, session_id, label, az_deg, el_deg, dist_mm FROM Penetrations WHERE id = %s",
                          (pen_id,))
        rows = self.conn.fetch_all()
        if not rows:
            raise RuntimeError(f"{session_id}: final-site Penetrations row id {pen_id} not found")
        pen = dict(zip(['id', 'session_id', 'label', 'az_deg', 'el_deg', 'dist_mm'], rows[0]))
        return load_trajectory_mri(self.conn, session_id, self.mri_config_path,
                                   self.corrections_file, self._geom_cache, pen=pen)

    # ---------------------------------------------------------------- calls
    def load_calls(self, session_id: str) -> dict:
        self.conn.execute("SELECT channel, laminar_class FROM LaminarCalls WHERE session_id = %s",
                          (session_id,))
        calls = {int(c): k for c, k in self.conn.fetch_all()}
        self.conn.execute("SELECT notes, mri_phi_deg FROM LaminarCallNotes WHERE session_id = %s",
                          (session_id,))
        r = self.conn.fetch_all()
        return dict(calls=calls, notes=r[0][0] if r else '', mri_phi_deg=r[0][1] if r else None)

    def save_calls(self, session_id: str, calls: Dict[int, str], depths_by_channel: Dict[int, float],
                   notes: str, mri_phi_deg: float) -> None:
        now = int(time.time() * 1000)
        for ch, cls in calls.items():
            self.conn.execute(
                "INSERT INTO LaminarCalls (session_id, channel, depth_mm, laminar_class, tstamp) "
                "VALUES (%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE depth_mm=VALUES(depth_mm), "
                "laminar_class=VALUES(laminar_class), tstamp=VALUES(tstamp)",
                (session_id, int(ch), float(depths_by_channel[ch]), cls, now))
        self.conn.execute(
            "INSERT INTO LaminarCallNotes (session_id, notes, mri_phi_deg, tstamp) VALUES (%s,%s,%s,%s) "
            "ON DUPLICATE KEY UPDATE notes=VALUES(notes), mri_phi_deg=VALUES(mri_phi_deg), tstamp=VALUES(tstamp)",
            (session_id, notes, float(mri_phi_deg), now))
