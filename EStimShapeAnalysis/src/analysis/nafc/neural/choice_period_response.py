"""
NAFC choice-period response, EStim ON vs OFF (one session).

For every channel, measures the response during the choice period
(choices_on -> choices_off, when the choice stimuli are on screen and no
EStim is delivered, so no stimulation artifact) and compares trials with
EStim ON against trials with EStim OFF.

Per channel and condition (ON / OFF) it saves one row to the data
repository table ``NafcChoicePeriodResponses``:
  - mean / std / SEM of the per-trial choice-period firing rate,
  - the per-trial rates themselves (so across-session scripts can redo stats),
  - a PSTH aligned to choices_on (mean and SEM across trials),
  - a Welch t-test of ON vs OFF trial rates (same value on both rows).

Methods
-------
Spike times come from the parser used by the rest of the NAFC neural code
(default: Intan spike.dat via NafcNeuralParser). For each trial the
choice-period rate is the number of spikes in
[choices_on + window_start_offset_s, choices_off] divided by that window's
duration (optionally capped at window_max_duration_s). Dividing by each
trial's own duration keeps the rate comparable when ON and OFF trials have
different reaction times. ON vs OFF is compared with Welch's two-sample
t-test on the per-trial rates (unequal variances, unequal n).

The PSTH counts spikes in bins of psth_bin_size_s from -psth_before_s to
+psth_after_s around choices_on and converts to spikes/s. With
psth_clip_to_choice_period=True, a trial only contributes to bins that lie
fully inside [sample_off, choices_off], so the PSTH never mixes in
sample-period (EStim) activity or post-choice activity, and each bin is
averaged over the trials still in the choice period at that time.

Run it per session from analyze_raw_data.py (add ChoicePeriodEStimAnalysis()
to its analyses list), or for one session with main() below.
"""

from __future__ import annotations

import os
from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats

from src.analysis import Analysis

TABLE_NAME = "NafcChoicePeriodResponses"
SPIKE_SOURCE_SPIKE_DAT = "spike_dat"


# ---------------------------------------------------------------------------
# Pure computation (no database) — used by the Analysis and by the tests
# ---------------------------------------------------------------------------

def choice_window(neural: dict, start_offset_s: float = 0.0,
                  max_duration_s: Optional[float] = None) -> Optional[tuple[float, float]]:
    """Return (start, stop) of the choice-period window in recording seconds,
    or None if the trial is missing choices_on / choices_off."""
    if not isinstance(neural, dict):
        return None
    c_on = neural.get("choices_on")
    c_off = neural.get("choices_off")
    if c_on is None or c_off is None:
        return None
    start = c_on + start_offset_s
    stop = c_off
    if max_duration_s is not None:
        stop = min(stop, start + max_duration_s)
    if stop <= start:
        return None
    return start, stop


def _channel_spikes(neural: dict, channel: str) -> np.ndarray:
    return np.asarray(neural.get("spikes_by_channel", {}).get(channel, []), dtype=float)


def trial_choice_rates(data: pd.DataFrame, channel: str,
                       start_offset_s: float = 0.0,
                       max_duration_s: Optional[float] = None) -> pd.DataFrame:
    """One row per usable trial: estim_on, rate_hz, duration_s."""
    rows = []
    for _, trial in data.iterrows():
        neural = trial.get("NeuralData")
        window = choice_window(neural, start_offset_s, max_duration_s)
        if window is None:
            continue
        start, stop = window
        spikes = _channel_spikes(neural, channel)
        n = int(np.count_nonzero((spikes >= start) & (spikes < stop)))
        rows.append({
            "estim_on": bool(trial.get("EStimEnabled")),
            "rate_hz": n / (stop - start),
            "duration_s": stop - start,
        })
    return pd.DataFrame(rows, columns=["estim_on", "rate_hz", "duration_s"])


def psth_bins(before_s: float, after_s: float, bin_size_s: float) -> np.ndarray:
    n_bins = int(round((before_s + after_s) / bin_size_s))
    return -before_s + bin_size_s * np.arange(n_bins + 1)


def trial_psths(data: pd.DataFrame, channel: str, bins: np.ndarray,
                clip_to_choice_period: bool = True) -> pd.DataFrame:
    """One row per trial with a choices_on time: estim_on and a rate array
    (spikes/s per bin, NaN where the bin is outside the trial's usable span)."""
    bin_size = bins[1] - bins[0]
    rows = []
    for _, trial in data.iterrows():
        neural = trial.get("NeuralData")
        if not isinstance(neural, dict) or neural.get("choices_on") is None:
            continue
        c_on = neural["choices_on"]
        spikes = _channel_spikes(neural, channel) - c_on
        counts, _ = np.histogram(spikes, bins=bins)
        rate = counts / bin_size
        if clip_to_choice_period:
            lo = -np.inf if neural.get("sample_off") is None else neural["sample_off"] - c_on
            hi = np.inf if neural.get("choices_off") is None else neural["choices_off"] - c_on
            outside = (bins[:-1] < lo - 1e-9) | (bins[1:] > hi + 1e-9)
            rate = rate.astype(float)
            rate[outside] = np.nan
        rows.append({"estim_on": bool(trial.get("EStimEnabled")), "rate": rate})
    return pd.DataFrame(rows, columns=["estim_on", "rate"])


def _nan_mean_sem(rates: list[np.ndarray], n_bins: int) -> tuple[np.ndarray, np.ndarray]:
    if not rates:
        return np.full(n_bins, np.nan), np.full(n_bins, np.nan)
    arr = np.vstack(rates)
    n = np.sum(~np.isnan(arr), axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = np.where(n > 0, np.nansum(arr, axis=0) / np.maximum(n, 1), np.nan)
        sd = np.array([np.nanstd(col, ddof=1) if k > 1 else np.nan
                       for col, k in zip(arr.T, n)])
        sem = sd / np.sqrt(n)
    return mean, sem


def summarize_channel(data: pd.DataFrame, channel: str, *,
                      start_offset_s: float = 0.0,
                      max_duration_s: Optional[float] = None,
                      psth_before_s: float = 0.2,
                      psth_after_s: float = 1.0,
                      psth_bin_size_s: float = 0.05,
                      clip_to_choice_period: bool = True) -> dict:
    """Everything saved for one channel: per-condition stats + PSTH + t-test."""
    rates = trial_choice_rates(data, channel, start_offset_s, max_duration_s)
    bins = psth_bins(psth_before_s, psth_after_s, psth_bin_size_s)
    psths = trial_psths(data, channel, bins, clip_to_choice_period)

    on = rates.loc[rates["estim_on"], "rate_hz"].to_numpy()
    off = rates.loc[~rates["estim_on"], "rate_hz"].to_numpy()
    if len(on) >= 2 and len(off) >= 2 and (np.std(on) > 0 or np.std(off) > 0):
        t_stat, p_value = stats.ttest_ind(on, off, equal_var=False)
        t_stat, p_value = float(t_stat), float(p_value)
    else:
        t_stat, p_value = None, None

    out = {"channel": channel, "bins": bins, "t_stat": t_stat, "p_value": p_value,
           "conditions": {}}
    for estim_on in (False, True):
        r = rates.loc[rates["estim_on"] == estim_on]
        trial_rates = r["rate_hz"].to_numpy()
        psth_mean, psth_sem = _nan_mean_sem(
            list(psths.loc[psths["estim_on"] == estim_on, "rate"]), len(bins) - 1)
        n = len(trial_rates)
        out["conditions"][estim_on] = {
            "n_trials": n,
            "mean_rate": float(np.mean(trial_rates)) if n else None,
            "std_rate": float(np.std(trial_rates, ddof=1)) if n > 1 else None,
            "sem_rate": float(np.std(trial_rates, ddof=1) / np.sqrt(n)) if n > 1 else None,
            "mean_duration_s": float(r["duration_s"].mean()) if n else None,
            "trial_rates": trial_rates,
            "psth_mean": psth_mean,
            "psth_sem": psth_sem,
        }
    return out


# ---------------------------------------------------------------------------
# Repository table
# ---------------------------------------------------------------------------

def encode_array(values) -> str:
    """Comma-separated text, NaN written as 'nan' (matches how the repository
    stores spike tstamps as comma-separated TEXT)."""
    return ",".join("nan" if v is None or np.isnan(v) else f"{v:.6g}" for v in values)


def decode_array(text: Optional[str]) -> np.ndarray:
    if not text:
        return np.array([], dtype=float)
    return np.array([float(v) for v in text.split(",")], dtype=float)


CREATE_TABLE_SQL = f"""
    CREATE TABLE IF NOT EXISTS {TABLE_NAME}
    (
        session_id            VARCHAR(10)  NOT NULL,
        channel               VARCHAR(255) NOT NULL,
        spike_source          VARCHAR(50)  NOT NULL,
        is_estim_on           BOOLEAN      NOT NULL,

        n_trials              INT          NOT NULL,
        mean_rate             DOUBLE,
        std_rate              DOUBLE,
        sem_rate              DOUBLE,
        mean_duration_s       DOUBLE,
        trial_rates           LONGTEXT,   -- comma-separated per-trial rates (spikes/s)

        t_stat                DOUBLE,     -- Welch t-test ON vs OFF (same on both rows)
        p_value               DOUBLE,

        window_start_offset_s DOUBLE,
        window_max_duration_s DOUBLE,

        psth_align            VARCHAR(20),
        psth_start_s          DOUBLE,
        psth_bin_size_s       DOUBLE,
        psth_clipped          BOOLEAN,
        psth_mean             LONGTEXT,   -- comma-separated spikes/s per bin
        psth_sem              LONGTEXT,

        PRIMARY KEY (session_id, channel, spike_source, is_estim_on),
        FOREIGN KEY (session_id) REFERENCES Sessions (session_id) ON DELETE CASCADE
    ) ENGINE = InnoDB
      DEFAULT CHARSET = latin1
"""

_COLUMNS = [
    "session_id", "channel", "spike_source", "is_estim_on",
    "n_trials", "mean_rate", "std_rate", "sem_rate", "mean_duration_s", "trial_rates",
    "t_stat", "p_value", "window_start_offset_s", "window_max_duration_s",
    "psth_align", "psth_start_s", "psth_bin_size_s", "psth_clipped", "psth_mean", "psth_sem",
]


def summary_to_rows(session_id: str, summary: dict, *, spike_source: str,
                    start_offset_s: float, max_duration_s: Optional[float],
                    clip_to_choice_period: bool) -> list[tuple]:
    bins = summary["bins"]
    rows = []
    for estim_on, c in summary["conditions"].items():
        row = {
            "session_id": session_id,
            "channel": summary["channel"],
            "spike_source": spike_source,
            "is_estim_on": bool(estim_on),
            "n_trials": c["n_trials"],
            "mean_rate": c["mean_rate"],
            "std_rate": c["std_rate"],
            "sem_rate": c["sem_rate"],
            "mean_duration_s": c["mean_duration_s"],
            "trial_rates": encode_array(c["trial_rates"]),
            "t_stat": summary["t_stat"],
            "p_value": summary["p_value"],
            "window_start_offset_s": start_offset_s,
            "window_max_duration_s": max_duration_s,
            "psth_align": "choices_on",
            "psth_start_s": float(bins[0]),
            "psth_bin_size_s": float(bins[1] - bins[0]),
            "psth_clipped": bool(clip_to_choice_period),
            "psth_mean": encode_array(c["psth_mean"]),
            "psth_sem": encode_array(c["psth_sem"]),
        }
        rows.append(tuple(row[col] for col in _COLUMNS))
    return rows


def ensure_table(conn) -> None:
    conn.execute(CREATE_TABLE_SQL)


def clear_session(conn, session_id: str, spike_source: str) -> None:
    conn.execute(f"DELETE FROM {TABLE_NAME} WHERE session_id = %s AND spike_source = %s",
                 (session_id, spike_source))


def insert_rows(conn, rows: list[tuple]) -> None:
    placeholders = ", ".join(["%s"] * len(_COLUMNS))
    updates = ", ".join(f"{c} = VALUES({c})" for c in _COLUMNS[4:])
    sql = (f"INSERT INTO {TABLE_NAME} ({', '.join(_COLUMNS)}) VALUES ({placeholders}) "
           f"ON DUPLICATE KEY UPDATE {updates}")
    for row in rows:
        conn.execute(sql, row)


# ---------------------------------------------------------------------------
# Per-channel figure
# ---------------------------------------------------------------------------

ESTIM_COLORS = {False: "#4D4D4D", True: "#D1495B"}
ESTIM_LABELS = {False: "EStim OFF", True: "EStim ON"}


def plot_channel(summary: dict, title: str):
    import matplotlib.pyplot as plt

    fig, (ax_psth, ax_bar) = plt.subplots(
        1, 2, figsize=(13, 5), gridspec_kw={"width_ratios": [2.4, 1]})
    bins = summary["bins"]
    centers = bins[:-1] + (bins[1] - bins[0]) / 2
    for estim_on in (False, True):
        c = summary["conditions"][estim_on]
        color = ESTIM_COLORS[estim_on]
        ax_psth.plot(centers, c["psth_mean"], color=color, linewidth=2.2,
                     label=f"{ESTIM_LABELS[estim_on]} (n={c['n_trials']})")
        ax_psth.fill_between(centers, c["psth_mean"] - c["psth_sem"],
                             c["psth_mean"] + c["psth_sem"], color=color, alpha=0.2,
                             linewidth=0)
    ax_psth.axvline(0, color="black", linewidth=1)
    ax_psth.set_xlabel("Time from choices on (s)", fontsize=13)
    ax_psth.set_ylabel("Firing rate (spikes/s)", fontsize=13)
    ax_psth.legend(fontsize=11, frameon=False)
    ax_psth.tick_params(labelsize=11)
    ax_psth.spines[["top", "right"]].set_visible(False)

    rng = np.random.default_rng(0)
    for x, estim_on in enumerate((False, True)):
        c = summary["conditions"][estim_on]
        color = ESTIM_COLORS[estim_on]
        r = c["trial_rates"]
        if len(r):
            ax_bar.scatter(x + rng.uniform(-0.15, 0.15, len(r)), r, s=14, color=color,
                           alpha=0.35, linewidth=0)
            ax_bar.errorbar(x, c["mean_rate"], yerr=c["sem_rate"] or 0, fmt="o",
                            color=color, markersize=9, capsize=6, linewidth=2)
    ax_bar.set_xticks([0, 1], [ESTIM_LABELS[False], ESTIM_LABELS[True]], fontsize=12)
    ax_bar.set_xlim(-0.6, 1.6)
    ax_bar.set_ylabel("Choice-period rate (spikes/s)", fontsize=13)
    ax_bar.tick_params(labelsize=11)
    ax_bar.spines[["top", "right"]].set_visible(False)
    p = summary["p_value"]
    ax_bar.set_title("Welch t-test: " + ("n/a" if p is None else f"p = {p:.3g}"),
                     fontsize=12)

    fig.suptitle(title, fontsize=15)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Analysis hooked into analyze_raw_data.py
# ---------------------------------------------------------------------------

class ChoicePeriodEStimAnalysis(Analysis):
    """Per-session choice-period ON vs OFF analysis.

    compile_and_export() loads the session's NAFC trials + neural data once
    (session = whatever context.nafc_database currently points at; call
    apply_session_context first, as analyze_raw_data does) and clears this
    session's old rows. run(session_id, channel=...) then summarises one
    channel and writes its two rows (ON, OFF).
    """

    def __init__(self, *,
                 window_start_offset_s: float = 0.0,
                 window_max_duration_s: Optional[float] = None,
                 psth_before_s: float = 0.2,
                 psth_after_s: float = 1.0,
                 psth_bin_size_s: float = 0.05,
                 psth_clip_to_choice_period: bool = True,
                 parser=None,
                 spike_source: str = SPIKE_SOURCE_SPIKE_DAT,
                 export: bool = True,
                 save_plots: bool = True,
                 show_plots: bool = False):
        # 'raw' = Intan spike.dat threshold crossings, the NAFC parser default.
        super().__init__(data_type="raw")
        self.window_start_offset_s = window_start_offset_s
        self.window_max_duration_s = window_max_duration_s
        self.psth_before_s = psth_before_s
        self.psth_after_s = psth_after_s
        self.psth_bin_size_s = psth_bin_size_s
        self.psth_clip_to_choice_period = psth_clip_to_choice_period
        self.parser = parser
        self.spike_source = spike_source
        self.export = export
        self.save_plots = save_plots
        self.show_plots = show_plots
        self._data: Optional[pd.DataFrame] = None
        self._data_session_id: Optional[str] = None
        self.summaries: dict[str, dict] = {}

    # -- compile ------------------------------------------------------------

    @staticmethod
    def _current_session_id() -> str:
        from src.repository.export_to_repository import read_session_id_and_date_from_db_name
        from src.startup import context
        session_id, _ = read_session_id_and_date_from_db_name(context.nafc_database)
        return session_id

    @staticmethod
    def nafc_intan_path() -> str:
        """Intan folder for the current NAFC session. NafcNeuralDataField
        indexes recording dirs here and one level of date subfolders below."""
        from src.startup import context
        return os.path.join(os.path.dirname(context.ga_intan_path), context.nafc_database)

    def compile(self) -> pd.DataFrame:
        from clat.compile.tstamp.cached_tstamp_fields import CachedFieldList
        from clat.util.connection import Connection
        from src.analysis.nafc.nafc_database_fields import EStimEnabledField
        from src.analysis.nafc.nafc_neural_database_fields import NafcNeuralDataField
        from src.analysis.nafc.psychometric_curves import collect_choice_trials
        from src.startup import context

        exp_conn = Connection(context.nafc_database)
        trial_tstamps = collect_choice_trials(exp_conn)
        if not trial_tstamps:
            raise RuntimeError(f"No NAFC choice trials in {context.nafc_database}")

        fields = CachedFieldList()
        fields.append(EStimEnabledField(exp_conn))
        fields.append(NafcNeuralDataField(self.nafc_intan_path(), exp_conn, parser=self.parser))
        data = fields.to_data(trial_tstamps)

        has_neural = data["NeuralData"].apply(lambda d: isinstance(d, dict))
        print(f"{context.nafc_database}: {len(data)} choice trials, "
              f"{int(has_neural.sum())} with neural data")
        if not has_neural.any():
            raise RuntimeError(f"No neural recordings matched under {self.nafc_intan_path()}")
        return data[has_neural].reset_index(drop=True)

    def compile_and_export(self):
        session_id = self._current_session_id()
        self._data = self.compile()
        self._data_session_id = session_id
        self.summaries = {}
        if self.export:
            from clat.util.connection import Connection
            repo_conn = Connection("allen_data_repository")
            ensure_table(repo_conn)
            clear_session(repo_conn, session_id, self.spike_source)
            print(f"Cleared {TABLE_NAME} rows for session {session_id} ({self.spike_source})")

    # -- analyze ------------------------------------------------------------

    def analyze(self, channel, compiled_data: pd.DataFrame = None):
        if compiled_data is None:
            if self._data is None or self._data_session_id != self.session_id:
                self.compile_and_export()
            compiled_data = self._data

        summary = summarize_channel(
            compiled_data, channel,
            start_offset_s=self.window_start_offset_s,
            max_duration_s=self.window_max_duration_s,
            psth_before_s=self.psth_before_s,
            psth_after_s=self.psth_after_s,
            psth_bin_size_s=self.psth_bin_size_s,
            clip_to_choice_period=self.psth_clip_to_choice_period,
        )
        self.summaries[channel] = summary
        off, on = summary["conditions"][False], summary["conditions"][True]
        print(f"{self.session_id} {channel}: OFF {off['mean_rate']} Hz (n={off['n_trials']}), "
              f"ON {on['mean_rate']} Hz (n={on['n_trials']}), p={summary['p_value']}")

        if self.export:
            from clat.util.connection import Connection
            rows = summary_to_rows(
                self.session_id, summary, spike_source=self.spike_source,
                start_offset_s=self.window_start_offset_s,
                max_duration_s=self.window_max_duration_s,
                clip_to_choice_period=self.psth_clip_to_choice_period)
            insert_rows(Connection("allen_data_repository"), rows)

        if self.save_plots or self.show_plots:
            import matplotlib.pyplot as plt
            fig = plot_channel(summary, f"{self.session_id} {channel}")
            if self.save_plots:
                from src.startup import context
                out_dir = os.path.join(context.nafc_plot_path, "choice_period_estim")
                os.makedirs(out_dir, exist_ok=True)
                fig.savefig(os.path.join(out_dir, f"{channel}.png"), dpi=150,
                            bbox_inches="tight")
            if self.show_plots:
                plt.show()
            else:
                plt.close(fig)
        return summary


def main():
    # ---- parameters ----
    session_id = "260518_0"
    channels = None            # None = all 32 channels; or e.g. ["A-026"]
    show_plots = True          # one figure per channel
    export = True              # write rows to NafcChoicePeriodResponses
    # --------------------

    from src.analysis import get_all_channels
    from src.startup.apply_session_context import apply_session_context

    apply_session_context(session_id)
    analysis = ChoicePeriodEStimAnalysis(export=export, show_plots=show_plots)
    analysis.compile_and_export()
    for channel in channels or get_all_channels():
        analysis.run(session_id=session_id, channel=channel)


if __name__ == "__main__":
    main()
