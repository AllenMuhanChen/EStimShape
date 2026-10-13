"""
Choice-period response, EStim ON vs OFF, across sessions.

Reads NafcChoicePeriodResponses (filled per session by
ChoicePeriodEStimAnalysis, src/analysis/nafc/neural/choice_period_response.py)
and asks whether EStim during the sample changes the response during the
later choice period.

Methods
-------
Unit of analysis is one channel in one session. For each channel we take the
mean choice-period firing rate on EStim OFF trials and on EStim ON trials
(each the mean of per-trial rates, spikes in [choices_on, choices_off] divided
by that trial's choice-period duration). Channels are kept if they have at
least min_trials_per_condition trials in both conditions and an average rate
((ON + OFF) / 2) of at least min_rate_hz, so silent channels don't contribute
undefined indices.

  - Per channel: Welch's t-test of ON vs OFF per-trial rates (computed per
    session and stored in the table). We count channels with a significant
    decrease / increase at p < alpha.
  - Population (channels): paired t-test of ON vs OFF mean rates across all
    kept channels, and a one-sample t-test of the modulation index
    MI = (ON - OFF) / (ON + OFF) against 0. MI is bounded in [-1, 1] and
    puts high- and low-rate channels on the same scale.
  - Population (sessions): channels recorded together are not independent,
    so as a conservative check we average MI within each session and run a
    one-sample t-test of the session means against 0.
  - MI to percent change: ON / OFF = (1 + MI) / (1 - MI), so MI = -0.076
    means ON = 0.859 x OFF, a 14% lower rate (not 7.6%).
  - Distance to EStim: each recorded channel's distance along the probe
    (65 um spacing, DBCChannelMapper) to the nearest channel stimulated
    (a1 > 0 in EStimParameters) in that session, over all EStim specs. MI vs
    distance is tested with a Pearson correlation across channels (channels
    from one session are not independent, so treat p as descriptive).
    Plotted as its own figure (plot_distance_to_estim), fitted with the
    falloff of current density from a point source (~ 1/r^2), with
    r = sqrt(d^2 + r0^2) (d = distance along the probe, r0 = fitted offset to
    the activated tissue, which keeps the curve finite at d = 0):
        MI(d) = A r0^2 / (d^2 + r0^2) + C.
    A is the MI at d = 0 above the far-field level C, and r0 is also the
    distance at which the effect is half its d = 0 value. Least squares on all
    channels; 95% CIs by resampling whole sessions (1000 bootstraps).
  - Current: each session's current_per_second (a1 x number of stimulated
    channels x pulse rate) and total_current (a1 x number of stimulated
    channels x number of pulses), from estim_hyperparameters; ON trials of all
    of a session's EStim specs are pooled here, so each is the ON-trial-weighted
    mean over its (spec, sample_length) combinations. For each, the distance
    plot is repeated with points colored by it, and per session the mean MI of
    channels within near_field_um of an EStim channel is plotted against it
    (Pearson correlation across sessions). With split_by_polarity, sessions
    are split by the polarity of their EStim specs (EStimParameters, active
    channels) into cathodic and anodic, each with its own correlation; a
    session whose ON trials mix both is drawn as "mixed" and left out of both.

Figure: population PSTHs aligned to choices_on (t = 0).
  1. EStim ON vs EStim OFF, all trials.
  2. EStim OFF trials split four ways: sample is hypothesized (the variant)
     or not (delta / removed) x the monkey chose hypothesized or not.
  3. EStim ON trials split the same way.
A channel enters a split curve only if it has at least min_trials_per_group
trials in that group.

Synchrony figure (artifact check, see choice_period_synchrony.py): rate of
events where many channels cross threshold within ~0.2 ms, aligned to
choices_on, ON vs OFF, mean +- SEM across sessions; and the same per 1000
pooled spikes, so a change in overall firing alone can't explain it; plus, when
the amplitude artifact detector was run, the % of time it flagged in each trial
(before any window is built, so ON vs OFF shows where artifact actually is).

spike_source selects which per-session results are read
(choice_period_artifact_mask.py):
  - "spike_dat_artwin" (default): one rejection window per session, built from
    where that session's ON trials have artifact (>= window_min_frac of ON
    trials flagged, relative to choices_on) and removed identically from ON
    and OFF trials, so both conditions lose the same time. Each session's
    window is printed and saved to rejection_windows.csv.
  - "spike_dat_artmask": each trial's own detected intervals removed.
  - "spike_dat": nothing removed.
Each channel's PSTH (mean across its trials) is optionally divided by that
channel's OFF choice-period rate (all OFF trials), so every channel
contributes on the same scale and all curves share one baseline. Shading is
SEM across channels.

Outputs (timestamped folder): figure (png + svg), channel table (csv),
stats.txt, config.json.
"""

from __future__ import annotations

import json
import os
import warnings
from datetime import datetime
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from src.analysis.nafc.neural.choice_period_response import (
    TABLE_NAME, GROUPS_TABLE_NAME, SPIKE_SOURCE_SPIKE_DAT, SPIKE_SOURCE_SPIKE_DAT_ARTMASK,
    SPIKE_SOURCE_SPIKE_DAT_ARTWIN,
    ESTIM_COLORS, ESTIM_LABELS,
    PSTH_GROUPS, decode_array,
)
from src.analysis.nafc.neural.choice_period_synchrony import SYNC_TABLE_NAME

# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------

def load_rows(session_ids, spike_source: str) -> pd.DataFrame:
    from clat.util.connection import Connection
    conn = Connection("allen_data_repository")
    cols = ["session_id", "channel", "is_estim_on", "n_trials", "mean_rate", "sem_rate",
            "p_value", "t_stat", "psth_start_s", "psth_bin_size_s", "psth_mean",
            "n_trials_hyp", "psth_mean_hyp", "n_trials_not_hyp", "psth_mean_not_hyp"]
    query = f"SELECT {', '.join(cols)} FROM {TABLE_NAME} WHERE spike_source = %s"
    params = [spike_source]
    if session_ids:
        query += f" AND session_id IN ({', '.join(['%s'] * len(session_ids))})"
        params += list(session_ids)
    conn.execute(query, params=tuple(params))
    return pd.DataFrame(conn.fetch_all(), columns=cols)


def _session_filter(session_ids):
    if not session_ids:
        return "", []
    return f" AND session_id IN ({', '.join(['%s'] * len(session_ids))})", list(session_ids)


def _group_key(estim_on: bool, sample_hyp: bool, chose_hyp: bool) -> str:
    return f"{'on' if estim_on else 'off'}_s{int(sample_hyp)}_c{int(chose_hyp)}"


def add_group_psths(table: pd.DataFrame, session_ids, spike_source: str) -> pd.DataFrame:
    """Join the four sample x choice PSTHs per condition onto the channel table as
    columns psth_mean_g_<key> / n_trials_g_<key>."""
    from clat.util.connection import Connection
    conn = Connection("allen_data_repository")
    cols = ["session_id", "channel", "is_estim_on", "sample_is_hyp", "chose_hyp",
            "n_trials", "psth_mean"]
    where, params = _session_filter(session_ids)
    conn.execute(f"SELECT {', '.join(cols)} FROM {GROUPS_TABLE_NAME} WHERE spike_source = %s"
                 + where, params=tuple([spike_source] + params))
    groups = pd.DataFrame(conn.fetch_all(), columns=cols)
    table = table.copy()
    if groups.empty:
        print(f"No rows in {GROUPS_TABLE_NAME}; rerun ChoicePeriodEStimAnalysis per session.")
        return table
    groups["key"] = [_group_key(bool(a), bool(b), bool(c)) for a, b, c in
                     zip(groups["is_estim_on"], groups["sample_is_hyp"], groups["chose_hyp"])]
    wide_psth = groups.pivot_table(index=["session_id", "channel"], columns="key",
                                   values="psth_mean", aggfunc="first")
    wide_n = groups.pivot_table(index=["session_id", "channel"], columns="key",
                                values="n_trials", aggfunc="first")
    wide = wide_psth.add_prefix("psth_mean_g_").join(wide_n.add_prefix("n_trials_g_"))
    return table.join(wide, on=["session_id", "channel"])


def load_synchrony(session_ids, spike_source: str) -> pd.DataFrame:
    from clat.util.connection import Connection
    conn = Connection("allen_data_repository")
    cols = ["session_id", "is_estim_on", "n_trials", "n_channels", "sync_window_s",
            "min_channels", "psth_start_s", "psth_bin_size_s", "sync_rate_mean",
            "spike_rate_mean", "artifact_frac_mean", "rejection_window"]
    where, params = _session_filter(session_ids)
    conn.execute(f"SELECT {', '.join(cols)} FROM {SYNC_TABLE_NAME} WHERE spike_source = %s"
                 + where, params=tuple([spike_source] + params))
    return pd.DataFrame(conn.fetch_all(), columns=cols)


def restrict_to_cluster_channels(rows: pd.DataFrame) -> pd.DataFrame:
    from src.repository.good_channels import read_cluster_channels
    keep = []
    for session_id, grp in rows.groupby("session_id"):
        cluster = set(read_cluster_channels(session_id))
        if not cluster:
            print(f"{session_id}: no cluster channels, skipped")
        keep.append(grp[grp["channel"].isin(cluster)])
    return pd.concat(keep, ignore_index=True) if keep else rows.iloc[0:0]


def to_channel_table(rows: pd.DataFrame) -> pd.DataFrame:
    """One row per (session, channel) with OFF and ON side by side."""
    rows = rows.copy()
    rows["is_estim_on"] = rows["is_estim_on"].astype(bool)
    off = rows[~rows["is_estim_on"]].set_index(["session_id", "channel"])
    on = rows[rows["is_estim_on"]].set_index(["session_id", "channel"])
    per_condition = ["n_trials", "mean_rate", "sem_rate", "psth_mean",
                     "n_trials_hyp", "psth_mean_hyp", "n_trials_not_hyp", "psth_mean_not_hyp"]
    table = off[per_condition + ["p_value", "t_stat", "psth_start_s", "psth_bin_size_s"]].join(
        on[per_condition],
        lsuffix="_off", rsuffix="_on", how="inner").reset_index()
    for c in ["mean_rate_off", "mean_rate_on", "p_value", "t_stat"]:
        table[c] = pd.to_numeric(table[c], errors="coerce")
    return table


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

def add_derived(table: pd.DataFrame, alpha: float) -> pd.DataFrame:
    table = table.copy()
    on, off = table["mean_rate_on"], table["mean_rate_off"]
    table["diff_hz"] = on - off
    table["modulation_index"] = (on - off) / (on + off)
    table["percent_change"] = 100 * (on - off) / off
    sig = table["p_value"] < alpha
    table["significance"] = np.where(sig & (table["diff_hz"] < 0), "decrease",
                                     np.where(sig & (table["diff_hz"] > 0), "increase", "n.s."))
    return table


def filter_channels(table: pd.DataFrame, min_trials: int, min_rate_hz: float) -> pd.DataFrame:
    enough = (table["n_trials_off"] >= min_trials) & (table["n_trials_on"] >= min_trials)
    active = (table["mean_rate_on"] + table["mean_rate_off"]) / 2 >= min_rate_hz
    return table[enough & active].reset_index(drop=True)


def population_stats(table: pd.DataFrame) -> dict:
    out = {"n_channels": len(table), "n_sessions": table["session_id"].nunique()}
    if len(table) >= 2:
        t, p = stats.ttest_rel(table["mean_rate_on"], table["mean_rate_off"])
        out["paired_t"] = {"t": float(t), "p": float(p), "df": len(table) - 1,
                           "mean_diff_hz": float(table["diff_hz"].mean())}
        t, p = stats.ttest_1samp(table["modulation_index"], 0.0)
        out["mi_t"] = {"t": float(t), "p": float(p), "df": len(table) - 1,
                       "mean_mi": float(table["modulation_index"].mean())}
    session_mi = table.groupby("session_id")["modulation_index"].mean()
    out["session_mean_mi"] = session_mi.to_dict()
    if len(session_mi) >= 2:
        t, p = stats.ttest_1samp(session_mi, 0.0)
        out["session_mi_t"] = {"t": float(t), "p": float(p), "df": len(session_mi) - 1,
                               "mean_mi": float(session_mi.mean())}
    counts = table["significance"].value_counts()
    out["n_decrease"] = int(counts.get("decrease", 0))
    out["n_increase"] = int(counts.get("increase", 0))
    out["n_ns"] = int(counts.get("n.s.", 0))
    return out


def mi_to_percent_change(mi):
    """MI = (ON - OFF) / (ON + OFF)  ->  100 * (ON - OFF) / OFF."""
    return 100 * 2 * np.asarray(mi) / (1 - np.asarray(mi))


def _p_text(p: float) -> str:
    return "p < 0.001" if p < 0.001 else f"p = {p:.3f}"


def stats_text(pop: dict, alpha: float) -> str:
    lines = [f"{pop['n_channels']} channels, {pop['n_sessions']} sessions"]
    if "paired_t" in pop:
        s = pop["paired_t"]
        lines.append(f"Paired t-test, ON vs OFF rate: mean diff {s['mean_diff_hz']:+.2f} spikes/s, "
                     f"t({s['df']}) = {s['t']:.2f}, {_p_text(s['p'])}")
    if "mi_t" in pop:
        s = pop["mi_t"]
        lines.append(f"One-sample t-test, MI vs 0 (channels): mean {s['mean_mi']:+.3f} "
                     f"(ON {mi_to_percent_change(s['mean_mi']):+.1f}% vs OFF), "
                     f"t({s['df']}) = {s['t']:.2f}, {_p_text(s['p'])}")
    if "session_mi_t" in pop:
        s = pop["session_mi_t"]
        lines.append(f"One-sample t-test, MI vs 0 (session means): mean {s['mean_mi']:+.3f}, "
                     f"t({s['df']}) = {s['t']:.2f}, {_p_text(s['p'])}")
    lines.append(f"Per-channel Welch t-test (p < {alpha:g}): {pop['n_decrease']} decrease, "
                 f"{pop['n_increase']} increase, {pop['n_ns']} n.s.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Population PSTH
# ---------------------------------------------------------------------------

def population_psth(table: pd.DataFrame, normalize: bool, curve_specs: dict,
                    min_trials: int = 1):
    """Average channel PSTHs across channels.

    curve_specs: {label: (psth_column, n_trials_column)}. Returns
    (bin_centers, {label: (mean, sem, n_channels)}) using the PSTH layout shared
    by most channels; channels saved with other bins are skipped."""
    layouts = table.apply(lambda r: (round(float(r["psth_start_s"]), 6),
                                     round(float(r["psth_bin_size_s"]), 6),
                                     len(decode_array(r["psth_mean_off"]))), axis=1)
    layout = layouts.mode().iloc[0]
    n_skipped = int((layouts != layout).sum())
    if n_skipped:
        print(f"Population PSTH: skipped {n_skipped} channels saved with different PSTH bins")
    sub = table[layouts == layout]
    start, width, n_bins = layout
    centers = start + width * (np.arange(n_bins) + 0.5)

    out = {}
    for label, (psth_col, n_col) in curve_specs.items():
        curves = []
        for _, r in sub.iterrows():
            n_trials = r.get(n_col)
            if n_trials is None or pd.isna(n_trials) or n_trials < min_trials:
                continue
            curve = decode_array(r[psth_col])
            if len(curve) != n_bins:
                continue
            if normalize:
                if not r["mean_rate_off"] > 0:
                    continue
                curve = curve / r["mean_rate_off"]
            curves.append(curve)
        arr = np.vstack(curves) if curves else np.full((1, n_bins), np.nan)
        n = np.sum(~np.isnan(arr), axis=0)
        with np.errstate(invalid="ignore", divide="ignore"), warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)  # all-NaN pre-period bins
            mean = np.nanmean(arr, axis=0)
            sem = np.nanstd(arr, axis=0, ddof=1) / np.sqrt(n)
        out[label] = (mean, sem, len(curves))
    return centers, out


# ---------------------------------------------------------------------------
# Figure
# ---------------------------------------------------------------------------

# Sample type -> colour, choice -> line style.
GROUP_STYLES = {
    PSTH_GROUPS[(True, True)]: ("#2A9D8F", "-"),
    PSTH_GROUPS[(True, False)]: ("#2A9D8F", "--"),
    PSTH_GROUPS[(False, True)]: ("#E9A23B", "-"),
    PSTH_GROUPS[(False, False)]: ("#E9A23B", "--"),
}


def _draw_psths(ax, centers, curves: dict, styles: dict, title: str, ylabel: str,
                unit: str = "channels"):
    for label, (mean, sem, n) in curves.items():
        color, linestyle = styles[label]
        ax.plot(centers, mean, color=color, linestyle=linestyle, linewidth=2.4,
                label=f"{label} (n={n} {unit})")
        ax.fill_between(centers, mean - sem, mean + sem, color=color, alpha=0.15, linewidth=0)
    ax.axvline(0, color="black", linewidth=1)
    ax.set_xlabel("Time from choices on (s)", fontsize=14)
    ax.set_ylabel(ylabel, fontsize=14)
    ax.set_title(title, fontsize=15)
    ax.legend(fontsize=11, frameon=False)
    ax.tick_params(labelsize=12, labelleft=True)
    ax.spines[["top", "right"]].set_visible(False)


def plot_psths(table: pd.DataFrame, normalize: bool, min_trials_per_group: int):
    ylabel = "Rate / OFF choice-period rate" if normalize else "Firing rate (spikes/s)"
    fig, axes = plt.subplots(1, 3, figsize=(21, 7), sharey=True)

    centers, curves = population_psth(table, normalize, {
        ESTIM_LABELS[False]: ("psth_mean_off", "n_trials_off"),
        ESTIM_LABELS[True]: ("psth_mean_on", "n_trials_on"),
    })
    _draw_psths(axes[0], centers, curves,
                {ESTIM_LABELS[k]: (ESTIM_COLORS[k], "-") for k in (False, True)},
                "Population PSTH", ylabel)

    for ax, estim_on in ((axes[1], False), (axes[2], True)):
        specs = {}
        for (sample_hyp, chose_hyp), label in PSTH_GROUPS.items():
            key = _group_key(estim_on, sample_hyp, chose_hyp)
            if f"psth_mean_g_{key}" in table.columns:
                specs[label] = (f"psth_mean_g_{key}", f"n_trials_g_{key}")
        if specs:
            centers, curves = population_psth(table, normalize, specs,
                                              min_trials=min_trials_per_group)
            _draw_psths(ax, centers, curves, GROUP_STYLES,
                        f"{ESTIM_LABELS[estim_on]}: sample x choice", "")
    fig.tight_layout()
    return fig


def _session_curves(sync: pd.DataFrame, value):
    """Mean +- SEM across sessions of value(row) (an array per session row)."""
    out = {}
    for estim_on in (False, True):
        rows = sync[sync["is_estim_on"].astype(bool) == estim_on]
        arrs = [value(r) for _, r in rows.iterrows()]
        arrs = [a for a in arrs if len(a)]
        if not arrs:
            continue
        arr = np.vstack(arrs)
        with np.errstate(invalid="ignore", divide="ignore"), warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            mean = np.nanmean(arr, axis=0)
            sem = np.nanstd(arr, axis=0, ddof=1) / np.sqrt(np.sum(~np.isnan(arr), axis=0))
        out[ESTIM_LABELS[estim_on]] = (mean, sem, len(arrs))
    return out


def plot_synchrony(sync: pd.DataFrame):
    layouts = list(zip(sync["psth_start_s"].round(6), sync["psth_bin_size_s"].round(6),
                       sync["sync_rate_mean"].map(lambda t: len(decode_array(t)))))
    layout = pd.Series(layouts).mode().iloc[0]
    sync = sync[[l == layout for l in layouts]]
    start, width, n_bins = layout
    centers = start + width * (np.arange(n_bins) + 0.5)
    styles = {ESTIM_LABELS[k]: (ESTIM_COLORS[k], "-") for k in (False, True)}

    has_mask = sync["artifact_frac_mean"].map(lambda t: len(decode_array(t)) > 0).any()
    fig, axes = plt.subplots(1, 3 if has_mask else 2, figsize=(24 if has_mask else 16, 6.5))
    _draw_psths(axes[0], centers, _session_curves(sync, lambda r: decode_array(r["sync_rate_mean"])),
                styles, "Cross-channel synchrony", "Synchronous events / s", unit="sessions")

    def per_1000_spikes(r):
        ev, sp = decode_array(r["sync_rate_mean"]), decode_array(r["spike_rate_mean"])
        with np.errstate(invalid="ignore", divide="ignore"):
            return np.where(sp > 0, 1000 * ev / sp, np.nan)

    _draw_psths(axes[1], centers, _session_curves(sync, per_1000_spikes), styles,
                "Synchrony per spike", "Synchronous events / 1000 spikes", unit="sessions")
    if has_mask:
        _draw_psths(axes[2], centers,
                    _session_curves(sync, lambda r: 100 * decode_array(r["artifact_frac_mean"])),
                    styles, "Artifact detected (per trial)", "% of time flagged", unit="sessions")
    first = sync.iloc[0]
    fig.suptitle(f">= {int(first['min_channels'])} channels within "
                 f"{1000 * float(first['sync_window_s']):.1f} ms", fontsize=13)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Distance to the stimulated channel(s)
# ---------------------------------------------------------------------------

SIG_COLORS = {"decrease": "#D1495B", "n.s.": "#B0B0B0", "increase": "#2E86AB"}


def probe_coordinates() -> dict[str, np.ndarray]:
    """Channel name ('A-012') -> probe position (um), from DBCChannelMapper."""
    from src.cluster.probe_mapping import DBCChannelMapper
    mapper = DBCChannelMapper("A")
    return {ch.value: np.asarray(mapper.get_coordinates(ch), dtype=float)
            for ch in mapper.channels_top_to_bottom}


def estim_channels_for_session(session_id: str) -> list[str]:
    """Every channel that delivered current (a1 > 0) in any EStim spec."""
    from src.cluster.cluster_isolation_score import fetch_active_estim_channels_by_spec
    by_spec = fetch_active_estim_channels_by_spec(session_id)
    return sorted({ch.value for chs in by_spec.values() for ch in chs})


def add_estim_distance(table: pd.DataFrame, coords: dict, estim_channels_by_session: dict
                       ) -> pd.DataFrame:
    """Add distance_to_estim_um: distance from each channel to the nearest
    stimulated channel of its session (NaN if unknown)."""
    table = table.copy()

    def nearest(row):
        estim = [coords[c] for c in estim_channels_by_session.get(row["session_id"], [])
                 if c in coords]
        if not estim or row["channel"] not in coords:
            return np.nan
        return min(float(np.linalg.norm(coords[row["channel"]] - e)) for e in estim)

    table["distance_to_estim_um"] = table.apply(nearest, axis=1)
    table["is_estim_channel"] = table["distance_to_estim_um"] == 0
    return table


def falloff(d, a, c, r0):
    """Current density from a point source, MI(d) = A r0^2 / (d^2 + r0^2) + C."""
    d = np.asarray(d, dtype=float)
    return a * r0 ** 2 / (d ** 2 + r0 ** 2) + c


def fit_falloff(d: np.ndarray, mi: np.ndarray, **loss):
    """Least-squares fit; returns dict of a, c, r0 (None if it fails). loss: as
    FIT_LOSS, for a robust fit."""
    from scipy.optimize import curve_fit
    d, mi = np.asarray(d, dtype=float), np.asarray(mi, dtype=float)
    c0 = float(np.median(mi))
    a0 = float(np.mean(mi[d <= np.min(d) + 1e-9])) - c0
    try:
        (a, c, r0), _ = curve_fit(falloff, d, mi, p0=[a0, c0, 100.0],
                                  bounds=([-2, -1, 1], [2, 1, 2000]), maxfev=20000, **loss)
    except (RuntimeError, ValueError):
        return None
    return {"a": float(a), "c": float(c), "r0": float(r0)}


JOINT_I_REF = 1000.0  # reference current: k is the amplitude at this current


def falloff_joint(d, current, k, c, r0, beta=1.0):
    """1/r^2 falloff whose amplitude grows with the injected current:
    MI(d, I) = k (I / I_ref)^beta r0^2 / (d^2 + r0^2) + C.
    beta = 1 is plain proportionality (field ~ I); beta < 1 is a response that
    saturates with current."""
    amp = k * (np.asarray(current, dtype=float) / JOINT_I_REF) ** beta
    return falloff(d, amp, c, r0)


def _aic(rss: float, n: int, n_params: int) -> float:
    return float(n * np.log(rss / n) + 2 * n_params)


def fit_joint(d, current, mi):
    """Least-squares fit of falloff_joint with beta free. The constant-amplitude
    falloff and the beta = 1 version are fitted to the same channels so all
    three AICs are comparable."""
    from scipy.optimize import curve_fit
    d, current, mi = (np.asarray(x, dtype=float) for x in (d, current, mi))
    const = fit_falloff(d, mi)
    if const is None:
        return None
    x = np.vstack([d, current])
    try:
        (k1, c1, r01), _ = curve_fit(lambda x, k, c, r0: falloff_joint(x[0], x[1], k, c, r0),
                                     x, mi, p0=[const["a"], const["c"], const["r0"]],
                                     bounds=([-10, -1, 1], [10, 1, 2000]), maxfev=20000)
        (k, c, r0, beta), _ = curve_fit(
            lambda x, k, c, r0, beta: falloff_joint(x[0], x[1], k, c, r0, beta), x, mi,
            p0=[k1, c1, r01, 1.0], bounds=([-10, -1, 1, 0], [10, 1, 2000, 3]), maxfev=20000)
    except (RuntimeError, ValueError):
        return None
    n = len(mi)

    def rss(pred):
        return float(np.sum((mi - pred) ** 2))

    return {"k": float(k), "c": float(c), "r0": float(r0), "beta": float(beta), "n": n,
            "aic": _aic(rss(falloff_joint(d, current, k, c, r0, beta)), n, 4),
            "aic_linear": _aic(rss(falloff_joint(d, current, k1, c1, r01)), n, 3),
            "aic_const": _aic(rss(falloff(d, const["a"], const["c"], const["r0"])), n, 3)}


def bootstrap_joint(sub: pd.DataFrame, metric: str, n_boot: int, seed: int = 0) -> dict:
    """95% CIs for k, C, r0, beta and the AIC differences, resampling whole sessions."""
    rng = np.random.default_rng(seed)
    groups = {sid: g for sid, g in sub.groupby("session_id")}
    sids = list(groups)
    keys = ("k", "c", "r0", "beta")
    draws = {key: [] for key in keys + ("d_aic_const", "d_aic_linear")}
    for _ in range(n_boot):
        boot = pd.concat([groups[s] for s in rng.choice(sids, len(sids), replace=True)])
        fit = fit_joint(boot["distance_to_estim_um"], boot[metric], boot["modulation_index"])
        if fit is not None:
            for key in keys:
                draws[key].append(fit[key])
            draws["d_aic_const"].append(fit["aic"] - fit["aic_const"])
            draws["d_aic_linear"].append(fit["aic"] - fit["aic_linear"])
    return {key: tuple(np.percentile(v, [2.5, 97.5])) if v else (np.nan, np.nan)
            for key, v in draws.items()}


# ---------------------------------------------------------------------------
# Superposition: field at each recorded channel from every stimulated channel
# ---------------------------------------------------------------------------

# What each stimulated channel contributes to the summed field, and the
# reference level k is quoted at. Set by add_stim_sources from superposition_field.
# "separate": field from per-pulse a1, times (pulses / n_ref) with its own exponent.
FIELDS = {
    "amplitude": {"f_ref": 100.0, "unit": "uA", "label": "per-pulse current a1"},
    "charge": {"f_ref": 1000.0, "unit": "uA x pulses", "label": "charge a1 x pulses"},
    "separate": {"f_ref": 100.0, "unit": "uA", "separate": True, "n_ref": 1.0,
                 "label": "per-pulse current a1, pulse count with its own exponent"},
}
SUPERPOSITION_FIELD = dict(FIELDS["amplitude"], d_min=65.0)
# Loss for the weighted-total-current fits (and the constant-amplitude fit they are
# compared with). Empty = ordinary least squares. Set by main from robust_fit:
# {"loss": "soft_l1", "f_scale": s} keeps residuals below s quadratic and grows
# linearly beyond, so a few extreme channels pull the curve much less. AIC is still
# computed from squared residuals.
FIT_LOSS = {}


def session_stim_charges(session_id: str, per_pulse: bool = True) -> dict:
    """{stim channel: per-pulse current a1 (uA), or with per_pulse=False the
    charge a1 x pulses (uA x pulses)} for the session.

    per_pulse=True removes the number of pulses: each channel contributes its
    pulse amplitude only.

    Per (spec, sample_length) group of ON trials (EStimShapeTrials), each
    channel with a1 > 0 delivers a1 x n_pulses, n_pulses from estim_hyperparameters
    (total_current / (a1 x num_channels)). The field is linear in current, so the
    trial-averaged field equals the field of the ON-trial-weighted mean charge
    per channel, which is what is returned."""
    from clat.util.connection import Connection
    from src.analysis.nafc.estim_hyperparameters import get_base_params, get_estim_hyperparameters
    conn = Connection("allen_data_repository")
    conn.execute("SELECT estim_spec_id, sample_length, COUNT(*) FROM EStimShapeTrials "
                 "WHERE session_id = %s AND is_estim_on = 1 AND estim_spec_id IS NOT NULL "
                 "GROUP BY estim_spec_id, sample_length", params=(session_id,))
    groups = conn.fetch_all()
    totals, n_total = {}, 0
    for spec_id, sample_length, n in groups:
        base = get_base_params(session_id, int(spec_id)) or {}
        total = get_estim_hyperparameters(session_id, int(spec_id),
                                          sample_duration_ms=sample_length).get("total_current")
        a1, nch = base.get("a1"), base.get("num_channels")
        if per_pulse:
            n_pulses = 1.0
        elif total is None or not a1 or not nch:
            continue
        else:
            n_pulses = float(total) / (float(a1) * float(nch))
        conn.execute("SELECT channel, a1 FROM EStimParameters WHERE session_id = %s "
                     "AND estim_spec_id = %s AND a1 > 0", params=(session_id, int(spec_id)))
        from src.cluster.cluster_isolation_score import _parse_channel
        for channel, ch_a1 in conn.fetch_all():
            parsed = _parse_channel(str(channel))
            if parsed is None:
                continue
            name = parsed.value
            totals[name] = totals.get(name, 0.0) + int(n) * float(ch_a1) * n_pulses
        n_total += int(n)
    return {ch: q / n_total for ch, q in totals.items()} if n_total else {}


def session_pulse_count(session_id: str) -> float:
    """ON-trial-weighted mean number of pulses per trial for the session:
    total_current / (a1 x num_channels) per (spec, sample_length) group of ON
    trials (EStimShapeTrials, estim_hyperparameters)."""
    from clat.util.connection import Connection
    from src.analysis.nafc.estim_hyperparameters import get_base_params, get_estim_hyperparameters
    conn = Connection("allen_data_repository")
    conn.execute("SELECT estim_spec_id, sample_length, COUNT(*) FROM EStimShapeTrials "
                 "WHERE session_id = %s AND is_estim_on = 1 AND estim_spec_id IS NOT NULL "
                 "GROUP BY estim_spec_id, sample_length", params=(session_id,))
    weighted, n_total = 0.0, 0
    for spec_id, sample_length, n in conn.fetch_all():
        base = get_base_params(session_id, int(spec_id)) or {}
        total = get_estim_hyperparameters(session_id, int(spec_id),
                                          sample_duration_ms=sample_length).get("total_current")
        a1, nch = base.get("a1"), base.get("num_channels")
        if total is None or not a1 or not nch:
            continue
        weighted += int(n) * float(total) / (float(a1) * float(nch))
        n_total += int(n)
    return weighted / n_total if n_total else np.nan


def add_stim_sources(table: pd.DataFrame, coords: dict, charges_by_session: dict,
                     field: str = "amplitude", pulses_by_session: dict = None,
                     min_distance_um: float = 65.0) -> pd.DataFrame:
    """stim_sources: per recorded channel, a list of (charge, distance um) for every
    stimulated channel of its session. field="separate" also adds n_pulses (per
    session, from pulses_by_session); n_ref is the median over sessions."""
    if field not in FIELDS:
        raise ValueError(f"superposition_field must be one of {list(FIELDS)}, got {field!r}")
    SUPERPOSITION_FIELD.clear()
    SUPERPOSITION_FIELD.update(FIELDS[field], d_min=float(min_distance_um))
    table = table.copy()
    if field == "separate":
        table["n_pulses"] = table["session_id"].map(pulses_by_session or {})
        per_session = table.drop_duplicates("session_id")["n_pulses"].dropna()
        if per_session.empty:
            raise ValueError("superposition_field = 'separate' needs pulse counts per session")
        SUPERPOSITION_FIELD["n_ref"] = float(np.median(per_session))

    def sources(row):
        charges = charges_by_session.get(row["session_id"]) or {}
        if row["channel"] not in coords:
            return None
        out = [(q, float(np.linalg.norm(coords[row["channel"]] - coords[ch])))
               for ch, q in charges.items() if ch in coords]
        return out or None

    table["stim_sources"] = table.apply(sources, axis=1)
    return table


def _source_arrays(sources_list):
    rows, q, d = [], [], []
    for i, srcs in enumerate(sources_list):
        for qi, di in srcs:
            rows.append(i)
            q.append(qi)
            d.append(di)
    return np.asarray(rows), np.asarray(q, dtype=float), np.asarray(d, dtype=float)


def effective_field(arrays, n_rows: int) -> np.ndarray:
    """Distance-weighted total current: sum over stimulated channels of
    charge x (d_min / d)^2, the 1/r^2 current-density falloff, with d floored at
    d_min (one channel spacing) so the stimulated channel itself isn't infinite.
    Fixed in advance, nothing fitted. Units: charge as if delivered d_min away."""
    rows, q, d = arrays
    d_min = SUPERPOSITION_FIELD["d_min"]
    return np.bincount(rows, weights=q * (d_min / np.maximum(d, d_min)) ** 2,
                       minlength=n_rows)


def superposition_model(arrays, n_rows, k, c, beta=1.0, pulse_ratio=None, beta_n=0.0):
    """k (F / f_ref)^beta (n / n_ref)^beta_n + C; pulse_ratio = n / n_ref per row."""
    drive = (effective_field(arrays, n_rows) / SUPERPOSITION_FIELD["f_ref"]) ** beta
    if pulse_ratio is not None:
        drive = drive * pulse_ratio ** beta_n
    return k * drive + c


def superposition_drive(sub: pd.DataFrame, fit: dict) -> np.ndarray:
    """(F / f_ref)^beta (n / n_ref)^beta_n per row: MI = k x drive + C."""
    drive = (effective_field(_source_arrays(sub["stim_sources"]), len(sub))
             / SUPERPOSITION_FIELD["f_ref"]) ** fit["beta"]
    if "beta_n" in fit:
        drive = drive * (sub["n_pulses"].to_numpy(dtype=float)
                         / SUPERPOSITION_FIELD["n_ref"]) ** fit["beta_n"]
    return drive


def fit_superposition(sub: pd.DataFrame):
    """MI = k (F / I_ref)^beta + C with F the summed field (effective_field);
    beta free, and beta = 1 plus the constant-amplitude falloff (nearest
    electrode) fitted to the same channels for AIC comparison.

    With SUPERPOSITION_FIELD "separate", F is from per-pulse a1 and the model is
    MI = k (F / f_ref)^beta (n / n_ref)^beta_n + C, compared by AIC against
    beta_n = beta (charge, one shared exponent), beta_n = 0 (amplitude only),
    beta = beta_n = 1 (proportional to charge) and constant amplitude."""
    from scipy.optimize import curve_fit
    sub = sub.dropna(subset=["stim_sources"])
    if SUPERPOSITION_FIELD.get("separate"):
        return _fit_superposition_separate(sub.dropna(subset=["n_pulses"]))
    if sub["session_id"].nunique() < 3:
        return None
    mi = sub["modulation_index"].to_numpy(dtype=float)
    n = len(mi)
    arrays = _source_arrays(sub["stim_sources"])
    idx = np.arange(n, dtype=float)
    const = fit_falloff(sub["distance_to_estim_um"], mi, **FIT_LOSS)
    if const is None:
        return None
    try:
        (k1, c1), _ = curve_fit(lambda _, k, c: superposition_model(arrays, n, k, c),
                                idx, mi, p0=[const["a"], const["c"]],
                                bounds=([-10, -1], [10, 1]), maxfev=20000, **FIT_LOSS)
        (k, c, beta), _ = curve_fit(
            lambda _, k, c, beta: superposition_model(arrays, n, k, c, beta), idx, mi,
            p0=[k1, c1, 1.0], bounds=([-10, -1, 0], [10, 1, 3]), maxfev=20000,
            **FIT_LOSS)
    except (RuntimeError, ValueError):
        return None

    def rss(pred):
        return float(np.sum((mi - pred) ** 2))

    return {"k": float(k), "c": float(c), "beta": float(beta), "n": n,
            "aic": _aic(rss(superposition_model(arrays, n, k, c, beta)), n, 3),
            "aic_linear": _aic(rss(superposition_model(arrays, n, k1, c1)), n, 2),
            "aic_const": _aic(rss(falloff(sub["distance_to_estim_um"].to_numpy(dtype=float),
                                          const["a"], const["c"], const["r0"])), n, 3)}


def _fit_superposition_separate(sub: pd.DataFrame):
    from scipy.optimize import curve_fit
    if sub["session_id"].nunique() < 3:
        return None
    mi = sub["modulation_index"].to_numpy(dtype=float)
    n = len(mi)
    arrays = _source_arrays(sub["stim_sources"])
    ratio = sub["n_pulses"].to_numpy(dtype=float) / SUPERPOSITION_FIELD["n_ref"]
    idx = np.arange(n, dtype=float)
    const = fit_falloff(sub["distance_to_estim_um"], mi, **FIT_LOSS)
    if const is None:
        return None

    def model(k, c, beta=1.0, beta_n=0.0):
        return superposition_model(arrays, n, k, c, beta, ratio, beta_n)

    lo, hi = [-10, -1], [10, 1]
    try:
        (k1, c1), _ = curve_fit(lambda _, k, c: model(k, c, 1.0, 1.0), idx, mi,
                                p0=[const["a"], const["c"]], bounds=(lo, hi), maxfev=20000,
                                **FIT_LOSS)
        p_amp, _ = curve_fit(lambda _, k, c, b: model(k, c, b, 0.0), idx, mi,
                             p0=[k1, c1, 1.0], bounds=(lo + [0], hi + [3]), maxfev=20000,
                             **FIT_LOSS)
        p_shared, _ = curve_fit(lambda _, k, c, b: model(k, c, b, b), idx, mi,
                                p0=[k1, c1, 1.0], bounds=(lo + [0], hi + [3]), maxfev=20000,
                             **FIT_LOSS)
        # Start from whichever nested fit is better so the free fit can't do worse.
        def rss(pred):
            return float(np.sum((mi - pred) ** 2))
        start = (list(p_amp) + [0.0]
                 if rss(model(*p_amp, 0.0)) < rss(model(*p_shared, p_shared[2]))
                 else list(p_shared) + [p_shared[2]])
        (k, c, beta, beta_n), _ = curve_fit(
            lambda _, k, c, b, bn: model(k, c, b, bn), idx, mi, p0=start,
            bounds=(lo + [0, -3], hi + [3, 3]), maxfev=20000, **FIT_LOSS)
    except (RuntimeError, ValueError):
        return None
    return {"k": float(k), "c": float(c), "beta": float(beta),
            "beta_n": float(beta_n), "n": n,
            "aic": _aic(rss(model(k, c, beta, beta_n)), n, 4),
            "aic_shared": _aic(rss(model(*p_shared, p_shared[2])), n, 3),
            "beta_shared": float(p_shared[2]),
            "aic_amp": _aic(rss(model(*p_amp, 0.0)), n, 3),
            "beta_amp": float(p_amp[2]),
            "aic_linear": _aic(rss(model(k1, c1, 1.0, 1.0)), n, 2),
            "aic_const": _aic(rss(falloff(sub["distance_to_estim_um"].to_numpy(dtype=float),
                                          const["a"], const["c"], const["r0"])), n, 3)}


def bootstrap_superposition(sub: pd.DataFrame, n_boot: int, seed: int = 0) -> dict:
    rng = np.random.default_rng(seed)
    groups = {sid: g for sid, g in sub.dropna(subset=["stim_sources"]).groupby("session_id")}
    sids = list(groups)
    separate = bool(SUPERPOSITION_FIELD.get("separate"))
    keys = ("k", "c", "beta") + (("beta_n",) if separate else ())
    aic_keys = ("const", "linear") + (("shared", "amp") if separate else ())
    draws = {key: [] for key in keys + tuple(f"d_aic_{a}" for a in aic_keys)}
    for _ in range(n_boot):
        boot = pd.concat([groups[s] for s in rng.choice(sids, len(sids), replace=True)])
        fit = fit_superposition(boot)
        if fit is not None:
            for key in keys:
                draws[key].append(fit[key])
            for a in aic_keys:
                draws[f"d_aic_{a}"].append(fit["aic"] - fit[f"aic_{a}"])
    return {key: tuple(np.percentile(v, [2.5, 97.5])) if v else (np.nan, np.nan)
            for key, v in draws.items()}


def plot_superposition(ax, sub: pd.DataFrame, fit: dict, binned_stat, fig):
    """MI vs the summed field at each channel (log x). If the model holds the
    points follow k (F / I_ref)^beta + C. With a pulse exponent (beta_n in fit)
    the x axis is the drive (F / f_ref)^beta (n / n_ref)^beta_n and the line is
    k x drive + C."""
    sub = sub.dropna(subset=["stim_sources"])
    separate = "beta_n" in fit
    if separate:
        sub = sub.dropna(subset=["n_pulses"])
        field = superposition_drive(sub, fit)
    else:
        field = effective_field(_source_arrays(sub["stim_sources"]), len(sub))
    mi = sub["modulation_index"].to_numpy(dtype=float)
    ok = field > 0
    sc = ax.scatter(field[ok], mi[ok], s=40, c=sub["distance_to_estim_um"].to_numpy()[ok],
                    cmap="viridis_r", alpha=0.35 if binned_stat else 0.85,
                    edgecolor="white", linewidth=0.5)
    cbar = fig.colorbar(sc, ax=ax, pad=0.02)
    cbar.solids.set_alpha(1)
    cbar.set_label("Distance to nearest EStim channel (um)", fontsize=13)
    cbar.ax.tick_params(labelsize=11)
    ax.set_xscale("log")
    xs = np.logspace(np.log10(field[ok].min()), np.log10(field[ok].max()), 300)
    if separate:
        handles = ax.plot(xs, fit["k"] * xs + fit["c"], color="black", linewidth=2.6, zorder=5,
                          label=f"k D + C (\u03b2 amplitude = {fit['beta']:.2f}, "
                                f"\u03b2 pulses = {fit['beta_n']:.2f})")
    else:
        handles = ax.plot(xs, fit["k"] * (xs / SUPERPOSITION_FIELD["f_ref"]) ** fit["beta"]
                          + fit["c"], color="black", linewidth=2.6, zorder=5,
                          label=f"k F^\u03b2 + C (\u03b2 = {fit['beta']:.2f})")
    if binned_stat:
        edges = np.logspace(np.log10(field[ok].min()), np.log10(field[ok].max()) + 1e-9, 13)
        which = np.digitize(field[ok], edges) - 1
        mids, centers, errs = [], [], []
        for b in range(len(edges) - 1):
            vals = mi[ok][which == b]
            if len(vals) < 3:
                continue
            centers.append(np.sqrt(edges[b] * edges[b + 1]))
            if binned_stat == "median":
                m = np.median(vals)
                errs.append((m - np.percentile(vals, 25), np.percentile(vals, 75) - m))
            else:
                m = vals.mean()
                e = vals.std(ddof=1) / np.sqrt(len(vals))
                errs.append((e, e))
            mids.append(m)
        if mids:
            errs = np.array(errs).T
            handles.append(ax.errorbar(centers, mids, yerr=errs, fmt="s", color="#1F1F1F",
                                       markerfacecolor="white", markeredgewidth=1.8,
                                       markersize=7, capsize=3, linewidth=1.4, zorder=6,
                                       label="Median (IQR)" if binned_stat == "median"
                                       else "Mean \u00b1 SEM"))
    ax.axhline(0, color="black", linewidth=1, linestyle="--")
    if separate:
        ax.set_xlabel(f"Drive D = (F / {SUPERPOSITION_FIELD['f_ref']:g} uA)^\u03b2a "
                      f"(pulses / {SUPERPOSITION_FIELD['n_ref']:g})^\u03b2n", fontsize=14)
        ax.set_title("Modulation vs field and pulse count", fontsize=15)
    else:
        ax.set_xlabel(f"Distance-weighted total current, F "
                      f"({SUPERPOSITION_FIELD['unit']} at {SUPERPOSITION_FIELD['d_min']:g} um)",
                      fontsize=14)
        ax.set_title("Modulation vs distance-weighted total current", fontsize=15)
    ax.set_ylabel("Modulation index (ON - OFF) / (ON + OFF)", fontsize=14)
    ax.legend(handles=handles, fontsize=11, frameon=False, loc="lower left")
    ax.tick_params(labelsize=12)
    ax.spines[["top", "right"]].set_visible(False)


def bootstrap_falloff(sub: pd.DataFrame, n_boot: int, seed: int = 0) -> dict:
    """95% CIs by resampling whole sessions (channels within a session are not
    independent)."""
    rng = np.random.default_rng(seed)
    groups = {sid: g for sid, g in sub.groupby("session_id")}
    sids = list(groups)
    draws = {k: [] for k in ("a", "c", "r0")}
    for _ in range(n_boot):
        boot = pd.concat([groups[s] for s in rng.choice(sids, len(sids), replace=True)])
        fit = fit_falloff(boot["distance_to_estim_um"], boot["modulation_index"])
        if fit is not None:
            for k in draws:
                draws[k].append(fit[k])
    return {k: tuple(np.percentile(v, [2.5, 97.5])) if v else (np.nan, np.nan)
            for k, v in draws.items()}


# Current measures compared against the modulation: column -> (label, unit).
CURRENT_METRICS = {
    "current_per_second": ("Current per second", "uA x Hz"),  # a1 x n channels x pulse rate
    "total_current": ("Total current", "uA x pulses"),        # a1 x n channels x n pulses
}


def session_current_metrics(session_id: str) -> dict:
    """{metric: value} for CURRENT_METRICS, from estim_hyperparameters.

    This analysis pools the ON trials of all of a session's EStim specs, so each
    measure is the mean over its (spec, sample_length) combinations weighted by
    their number of ON trials (EStimShapeTrials). sample_length matters for
    level-triggered specs, whose pulse count (and so total current) is set by
    how long the sample is shown. Sessions mixing several values are printed."""
    from clat.util.connection import Connection
    from src.analysis.nafc.estim_hyperparameters import get_estim_hyperparameters
    conn = Connection("allen_data_repository")
    conn.execute("SELECT estim_spec_id, sample_length, COUNT(*) FROM EStimShapeTrials "
                 "WHERE session_id = %s AND is_estim_on = 1 AND estim_spec_id IS NOT NULL "
                 "GROUP BY estim_spec_id, sample_length", params=(session_id,))
    groups = conn.fetch_all()
    out = {}
    for metric in CURRENT_METRICS:
        values, weights = [], []
        for spec_id, sample_length, n in groups:
            v = get_estim_hyperparameters(session_id, int(spec_id),
                                          sample_duration_ms=sample_length).get(metric)
            if v is not None:
                values.append(float(v))
                weights.append(int(n))
        if not values:
            out[metric] = np.nan
            continue
        if len(set(values)) > 1:
            print(f"{session_id}: {metric} differs across EStim specs / sample lengths "
                  f"{sorted(set(values))}, using the ON-trial-weighted mean")
        out[metric] = float(np.average(values, weights=weights))

    # Polarity of the specs used on ON trials (uniform within a spec).
    conn.execute("SELECT estim_spec_id, MIN(polarity) FROM EStimParameters "
                 "WHERE session_id = %s AND a1 > 0 GROUP BY estim_spec_id", params=(session_id,))
    by_spec = {int(spec): _polarity_label(pol) for spec, pol in conn.fetch_all()}
    used = {by_spec.get(int(spec_id)) for spec_id, _, _ in groups} - {None}
    out["polarity"] = used.pop() if len(used) == 1 else ("mixed" if used else None)
    if out["polarity"] == "mixed":
        print(f"{session_id}: ON trials mix cathodic and anodic specs, plotted as 'mixed'")
    return out


def _polarity_label(polarity) -> Optional[str]:
    """EStimParameters.polarity is NegativeFirst (cathodic-first) or
    PositiveFirst (anodic-first)."""
    text = str(polarity or "").lower()
    if text.startswith("negative") or "cath" in text:
        return "cathodic"
    if text.startswith("positive") or "anod" in text:
        return "anodic"
    if text:
        print(f"Unrecognized EStim polarity {polarity!r}, session not split")
    return None


POLARITY_COLORS = {"cathodic": "#3B6FB6", "anodic": "#E07A1F", "mixed": "#9A9A9A"}


def plot_mi_vs_distance(table: pd.DataFrame, alpha: float, show_point_labels: bool,
                        fit_curve: bool = True, n_boot: int = 1000,
                        current_metrics=(), near_field_um: float = 65.0,
                        current_ranges: dict = None, binned_stat: Optional[str] = "mean",
                        distance_bin_um: float = 65.0, joint_fit: bool = True,
                        joint_predictor: str = "superposition"):
    """Left: MI vs distance (with the 1/r^2 fit). For each metric in
    current_metrics with data, a row on the right: the same scatter colored by
    that metric, and per-session near-EStim MI vs the metric."""
    sub = table.dropna(subset=["distance_to_estim_um", "modulation_index"])
    current_metrics = [m for m in current_metrics
                       if m in sub.columns and sub[m].notna().any()]
    if current_metrics:
        n_rows = len(current_metrics)
        fig = plt.figure(figsize=(29, 7.5 * n_rows))
        grid = fig.add_gridspec(n_rows, 3, width_ratios=[1, 1.12, 0.85])
        ax = fig.add_subplot(grid[:, 0])
        current_axes = [(fig.add_subplot(grid[i, 1]), fig.add_subplot(grid[i, 2]))
                        for i in range(n_rows)]
    else:
        fig, ax = plt.subplots(figsize=(10, 7))
    for sig, color in SIG_COLORS.items():
        g = sub[sub["significance"] == sig]
        ax.scatter(g["distance_to_estim_um"], g["modulation_index"], s=50, color=color,
                   alpha=0.8, edgecolor="white", linewidth=0.5, label=f"{sig} (n={len(g)})")
    if show_point_labels:
        for _, r in sub.iterrows():
            ax.annotate(f"{r['session_id']} {r['channel']}",
                        (r["distance_to_estim_um"], r["modulation_index"]), fontsize=7)
    ax.axhline(0, color="black", linewidth=1, linestyle="--")
    sig_handles = ax.get_legend_handles_labels()[0]
    extra_handles = [_draw_binned(ax, sub, binned_stat, distance_bin_um)] \
        if binned_stat and len(sub) else []
    sig_legend = ax.legend(handles=sig_handles, fontsize=11, frameon=False, loc="lower right",
                           title=f"Welch p < {alpha:g}", title_fontsize=11)

    result = None
    if len(sub) >= 3:
        d, mi = sub["distance_to_estim_um"].to_numpy(), sub["modulation_index"].to_numpy()
        r, p = stats.pearsonr(d, mi)
        ax.text(0.02, 0.97, f"Pearson r = {r:.2f}, {_p_text(p)}", transform=ax.transAxes,
                fontsize=13, va="top")
        result = {"n": len(sub), "r": float(r), "p": float(p), "fit": None}
        fit = fit_falloff(d, mi) if fit_curve else None
        if fit_curve and fit is None:
            print("1/r^2 fit did not converge")
        if fit is not None:
            if n_boot:
                fit["ci"] = bootstrap_falloff(sub, n_boot)
            result["fit"] = fit
            xs = np.linspace(0, d.max(), 400)
            line = ax.plot(xs, falloff(xs, fit["a"], fit["c"], fit["r0"]), color="black",
                           linewidth=2.4, label=f"1/r\u00b2 fit (half at {fit['r0']:.0f} um)")
            extra_handles = line + extra_handles
    if extra_handles:
        ax.legend(handles=extra_handles, fontsize=11, frameon=False, loc="upper right")
        ax.add_artist(sig_legend)

    ax.set_xlabel("Distance to nearest EStim channel (um)", fontsize=14)
    ax.set_ylabel("Modulation index (ON - OFF) / (ON + OFF)", fontsize=14)
    ax.set_title("EStim modulation vs distance", fontsize=15)
    ax.tick_params(labelsize=12)
    ax.spines[["top", "right"]].set_visible(False)
    if current_metrics and result is not None:
        result["current"] = {
            m: _plot_current_panels(ax_c, ax_d, sub, m, near_field_um, fig, sharey_with=ax,
                                    current_range=(current_ranges or {}).get(m),
                                    joint_fit=joint_fit, n_boot=n_boot,
                                    binned_stat=binned_stat,
                                    distance_bin_um=distance_bin_um,
                                    joint_predictor=joint_predictor)
            for m, (ax_c, ax_d) in zip(current_metrics, current_axes)}
    fig.tight_layout()
    return fig, result


def _plot_current_panels(ax_scatter, ax_dose, sub: pd.DataFrame, metric: str,
                         near_field_um: float, fig, sharey_with=None, current_range=None,
                         joint_fit: bool = False, n_boot: int = 0,
                         binned_stat: Optional[str] = "mean",
                         distance_bin_um: float = 65.0,
                         joint_predictor: str = "superposition") -> dict:
    """Middle: the distance scatter colored by the session's value of metric.
    Right: per session, the mean MI of channels within near_field_um of an EStim
    channel vs metric (one point per session, sessions independent)."""
    label, unit = CURRENT_METRICS[metric]
    cur = sub.dropna(subset=[metric])
    lo, hi = current_range if current_range else (None, None)
    outside = ((cur[metric] < lo) if lo is not None else False) | \
              ((cur[metric] > hi) if hi is not None else False)
    outside = pd.Series(outside, index=cur.index, dtype=bool)
    excluded = sorted(cur.loc[outside, "session_id"].unique())
    if excluded:
        print(f"Left out of the {metric} panels (outside {current_range}): "
              + ", ".join(f"{sid} ({c:g})" for sid, c in cur.loc[outside].groupby("session_id")
                          [metric].first().items()))
        cur = cur[~outside]
    joint = None
    superposed = (joint_fit and joint_predictor == "superposition"
                  and "stim_sources" in cur.columns and cur["stim_sources"].notna().any())
    if superposed:
        joint = fit_superposition(cur)
        if joint is None:
            print("Superposition fit did not converge")
        else:
            joint["predictor"] = "superposition"
            if n_boot:
                joint["ci"] = bootstrap_superposition(cur, n_boot)
            plot_superposition(ax_scatter, cur, joint, binned_stat, fig)
    elif joint_fit and cur["session_id"].nunique() >= 3:
        joint = fit_joint(cur["distance_to_estim_um"], cur[metric], cur["modulation_index"])
        if joint is None:
            print(f"Joint fit with {metric} did not converge")
        else:
            joint["predictor"] = metric
            if n_boot:
                joint["ci"] = bootstrap_joint(cur, metric, n_boot)

    if not (superposed and joint is not None):
        if joint is not None:
            # Collapse: (MI - C) / (I / I_ref)^beta. If the joint fit holds, every
            # session falls on the same curve k r0^2/(d^2 + r0^2) whatever its current.
            # C (the far-field level) is subtracted first because it doesn't scale
            # with current. Low-current sessions are noisier here.
            shown = cur.assign(modulation_index=(cur["modulation_index"] - joint["c"])
                               / (cur[metric] / JOINT_I_REF) ** joint["beta"])
            ylabel = f"(MI - C) / (I / {JOINT_I_REF:g})^\u03b2"
            title = f"Modulation scaled by {label.lower()} (\u03b2 = {joint['beta']:.2f})"
        else:
            shown, ylabel, title = cur, "Modulation index (ON - OFF) / (ON + OFF)", \
                f"Colored by {label.lower()}"
        faded = joint is not None and bool(binned_stat)
        order = shown.sort_values(metric)  # high current drawn on top
        sc = ax_scatter.scatter(order["distance_to_estim_um"], order["modulation_index"], s=50,
                                c=order[metric], cmap="viridis", alpha=0.35 if faded else 0.85,
                                edgecolor="white", linewidth=0.5)
        cbar = fig.colorbar(sc, ax=ax_scatter, pad=0.02)
        cbar.solids.set_alpha(1)  # colorbar stays solid when points are faded
        cbar.set_label(f"{label} ({unit})", fontsize=13)
        cbar.ax.tick_params(labelsize=11)
        ax_scatter.axhline(0, color="black", linewidth=1, linestyle="--")
        ax_scatter.set_xlabel("Distance to nearest EStim channel (um)", fontsize=14)
        ax_scatter.set_ylabel(ylabel, fontsize=14)
        ax_scatter.set_title(title, fontsize=15)
        if joint is None and sharey_with is not None:
            ax_scatter.set_ylim(sharey_with.get_ylim())

        if joint is not None:
            xs = np.linspace(0, cur["distance_to_estim_um"].max(), 400)
            handles = ax_scatter.plot(xs, falloff(xs, joint["k"], 0.0, joint["r0"]),
                                      color="black", linewidth=2.6, zorder=5,
                                      label=f"k/r\u00b2 fit (half at {joint['r0']:.0f} um)")
            if binned_stat:
                handles.append(_draw_binned(ax_scatter, shown, binned_stat, distance_bin_um))
            ax_scatter.legend(handles=handles, fontsize=11, frameon=False, loc="lower right")
            # Low-current outliers can stretch the axis; keep it to the bulk of the data.
            lo, hi = np.nanpercentile(shown["modulation_index"], [1, 99])
            pad = 0.1 * (hi - lo)
            ax_scatter.set_ylim(lo - pad, hi + pad)

    near = cur[cur["distance_to_estim_um"] <= near_field_um]
    if "polarity" not in near.columns:
        near = near.assign(polarity=None)
    per_session = near.groupby("session_id").agg(
        current=(metric, "first"), polarity=("polarity", "first"),
        mi=("modulation_index", "mean"),
        sem=("modulation_index", lambda x: x.std(ddof=1) / np.sqrt(len(x)) if len(x) > 1
             else np.nan), n=("modulation_index", "size")).reset_index()
    ax_dose.axhline(0, color="black", linewidth=1, linestyle="--")
    out = {"near_field_um": near_field_um, "n_sessions": len(per_session),
           "excluded": excluded, "current_range": current_range, "by_polarity": {},
           "joint": joint}
    # Split only if some session used a single polarity; sessions whose ON trials
    # mix both can't be assigned to either.
    split = per_session["polarity"].isin(["cathodic", "anodic"]).any()
    groups = ([(pol, per_session[per_session["polarity"] == pol]) for pol in POLARITY_COLORS]
              if split else [(None, per_session)])
    if not split and per_session["polarity"].eq("mixed").any():
        print("Every session mixes cathodic and anodic ON trials; polarity split not drawn")
    for pol, g in groups:
        if g.empty:
            continue
        color = POLARITY_COLORS[pol] if pol else "#D1495B"
        leg = pol.capitalize() if pol else None
        if pol != "mixed" and len(g) >= 3:
            r, p = stats.pearsonr(g["current"], g["mi"])
            slope, intercept = np.polyfit(g["current"], g["mi"], 1)
            xs = np.array([g["current"].min(), g["current"].max()])
            ax_dose.plot(xs, intercept + slope * xs, color=color if pol else "black",
                         linewidth=2)
            stat = {"r": float(r), "p": float(p), "n": len(g)}
            if pol:
                out["by_polarity"][pol] = stat
                leg += f" (n={len(g)}, r = {r:.2f}, {_p_text(p)})"
            else:
                out.update(r=stat["r"], p=stat["p"])
                ax_dose.text(0.02, 0.97, f"Pearson r = {r:.2f}, {_p_text(p)}",
                             transform=ax_dose.transAxes, fontsize=13, va="top", zorder=5,
                             bbox=dict(facecolor="white", edgecolor="none", pad=2))
        elif pol:
            leg += f" (n={len(g)})"
        ax_dose.errorbar(g["current"], g["mi"], yerr=g["sem"], fmt="o", color=color,
                         markersize=9, capsize=4, linewidth=1.5, label=leg)
    if split:
        ax_dose.legend(fontsize=11, frameon=False, loc="lower left")
    ax_dose.set_xlabel(f"{label} ({unit})", fontsize=14)
    ax_dose.set_ylabel(f"Mean MI, channels <= {near_field_um:g} um", fontsize=14)
    ax_dose.set_title(f"Near-EStim modulation vs {label.lower()}", fontsize=15)
    for a in (ax_scatter, ax_dose):
        a.tick_params(labelsize=12)
        a.spines[["top", "right"]].set_visible(False)
    return out


def _draw_binned(ax, sub: pd.DataFrame, stat: str, bin_um: float, color: str = "#1F1F1F",
                 label: str = None, offset_um: float = 0.0):
    """Mean +- SEM (or median with 25-75th percentile) of MI at each distance,
    distances rounded to the nearest bin_um (65 um = one probe channel)."""
    binned = sub.assign(_bin=(sub["distance_to_estim_um"] / bin_um).round() * bin_um)
    rows = []
    for d, g in binned.groupby("_bin"):
        mi = g["modulation_index"].to_numpy()
        if stat == "median":
            mid = np.median(mi)
            lo, hi = mid - np.percentile(mi, 25), np.percentile(mi, 75) - mid
        else:
            mid = mi.mean()
            lo = hi = mi.std(ddof=1) / np.sqrt(len(mi)) if len(mi) > 1 else 0.0
        rows.append((d, mid, lo, hi))
    d, mid, lo, hi = map(np.array, zip(*rows))
    if label is None:
        label = "Median (IQR)" if stat == "median" else "Mean \u00b1 SEM"
    return ax.errorbar(d + offset_um, mid, yerr=[lo, hi], fmt="s", color=color,
                       markerfacecolor="white",
                markeredgewidth=1.8, markersize=7, capsize=3, linewidth=1.4, zorder=4,
                label=label)


def joint_text(metric: str, j: dict) -> str:
    unit = CURRENT_METRICS[metric][1]
    ci = j.get("ci", {})

    def fmt(key, value, spec):
        lo, hi = ci.get(key, (np.nan, np.nan))
        return f"{value:{spec}}" + (f" [{lo:{spec}}, {hi:{spec}}]" if ci else "")

    def verdict(d_aic, other):
        return (f"beta fit better than {other}" if d_aic < -2 else
                f"{other} better" if d_aic > 2 else "no clear difference")

    d_const, d_lin = j["aic"] - j["aic_const"], j["aic"] - j["aic_linear"]
    if j.get("predictor") == "superposition" and "beta_n" in j:
        ref, n_ref = SUPERPOSITION_FIELD["f_ref"], SUPERPOSITION_FIELD["n_ref"]
        d_shared, d_amp = j["aic"] - j["aic_shared"], j["aic"] - j["aic_amp"]
        return (f"Superposition fit, MI = k (F / {ref:g})^beta_a (n / {n_ref:g})^beta_n + C, "
                f"F = sum over EStim channels of per-pulse current a1 x (d_min / d)^2, "
                f"d >= d_min = {SUPERPOSITION_FIELD['d_min']:g} um, "
                f"n = pulses per trial ({j['n']} channels; 95% CI: bootstrap over sessions):\n"
                f"  k (MI at F = {ref:g} uA and {n_ref:g} pulses, minus C) = "
                f"{fmt('k', j['k'], '+.3f')}, beta_a (amplitude) = {fmt('beta', j['beta'], '.2f')}, "
                f"beta_n (pulses) = {fmt('beta_n', j['beta_n'], '.2f')}, "
                f"C = {fmt('c', j['c'], '+.3f')}\n"
                f"  AIC - AIC shared exponent (charge, beta = {j['beta_shared']:.2f}) = "
                f"{fmt('d_aic_shared', d_shared, '+.1f')} ({verdict(d_shared, 'shared exponent')})\n"
                f"  AIC - AIC amplitude only (beta = {j['beta_amp']:.2f}) = "
                f"{fmt('d_aic_amp', d_amp, '+.1f')} ({verdict(d_amp, 'amplitude only')})\n"
                f"  AIC - AIC proportional to charge (both 1) = "
                f"{fmt('d_aic_linear', d_lin, '+.1f')} ({verdict(d_lin, 'proportional to charge')})\n"
                f"  AIC - AIC constant-amplitude falloff = {fmt('d_aic_const', d_const, '+.1f')} "
                f"({verdict(d_const, 'constant amplitude')}); negative favors the separate fit")
    if j.get("predictor") == "superposition":
        ref, funit = SUPERPOSITION_FIELD["f_ref"], SUPERPOSITION_FIELD["unit"]
        return (f"Superposition fit, MI = k (F / {ref:g})^beta + C, "
                f"F = sum over EStim channels of {SUPERPOSITION_FIELD['label']} "
                f"x (d_min / d)^2, d >= d_min = {SUPERPOSITION_FIELD['d_min']:g} um "
                f"({j['n']} channels; 95% CI: bootstrap over sessions):\n"
                f"  k (MI at F = {ref:g} {funit}, minus C) = {fmt('k', j['k'], '+.3f')}, "
                f"beta = {fmt('beta', j['beta'], '.2f')} (1 = proportional to field, "
                f"< 1 = saturating), C = {fmt('c', j['c'], '+.3f')}\n"
                f"  AIC - AIC constant-amplitude falloff = {fmt('d_aic_const', d_const, '+.1f')} "
                f"({verdict(d_const, 'constant amplitude')})\n"
                f"  AIC - AIC beta = 1 = {fmt('d_aic_linear', d_lin, '+.1f')} "
                f"({verdict(d_lin, 'beta = 1')}); negative favors the beta fit")
    return (f"Joint fit, MI(d, I) = k (I / {JOINT_I_REF:g})^beta r0^2 / (d^2 + r0^2) + C, "
            f"I = {metric} ({j['n']} channels; 95% CI: bootstrap over sessions):\n"
            f"  k (amplitude at {JOINT_I_REF:g} {unit}) = {fmt('k', j['k'], '+.3f')}, "
            f"beta = {fmt('beta', j['beta'], '.2f')} (1 = proportional to current, "
            f"< 1 = saturating), C = {fmt('c', j['c'], '+.3f')}, "
            f"r0 = {fmt('r0', j['r0'], '.0f')} um\n"
            f"  AIC beta fit - AIC constant amplitude = {fmt('d_aic_const', d_const, '+.1f')} "
            f"({verdict(d_const, 'constant amplitude')})\n"
            f"  AIC beta fit - AIC beta = 1 = {fmt('d_aic_linear', d_lin, '+.1f')} "
            f"({verdict(d_lin, 'beta = 1')}); negative favors the beta fit")


def joint_summary(j: dict) -> str:
    """Plain-language verdict on the current fit, printed at the end of a run."""
    ci = j.get("ci", {})
    b_lo, b_hi = ci.get("beta", (np.nan, np.nan))
    d_lin, d_const = j["aic"] - j["aic_linear"], j["aic"] - j["aic_const"]
    name = (f"Superposition fit (field summed over EStim channels, "
            f"{SUPERPOSITION_FIELD['label']})"
            if j.get("predictor") == "superposition" else f"Joint fit ({j.get('predictor')})")
    lines = ["", "=" * 70, name, "=" * 70]
    if j.get("predictor") == "superposition":
        lines.append(f"robust fit (soft L1, scale {FIT_LOSS['f_scale']:g} MI): outliers down-weighted"
                     if FIT_LOSS else "ordinary least squares")
    if "beta_n" in j:
        def exponent(key, what):
            lo, hi = ci.get(key, (np.nan, np.nan))
            line = f"{what:<22}{j[key]:.2f}"
            if ci:
                line += f"  (95% CI {lo:.2f} to {hi:.2f})"
                line += ("  -> excludes 0" if lo > 0 or hi < 0 else "  -> includes 0") + \
                        ("; excludes 1" if lo > 1 or hi < 1 else "; includes 1")
            return line

        def vs(key, what, better):
            d = j["aic"] - j[key]
            return (f"vs {what:<34}AIC difference {d:+.1f}  -> "
                    + (better if d < -2 else f"{what} better" if d > 2
                       else "no clear difference"))
        lines += [exponent("beta", "beta amplitude (a1):"),
                  exponent("beta_n", "beta pulses:"),
                  vs("aic_shared", f"shared exponent (charge, {j['beta_shared']:.2f}):",
                     "amplitude and pulses scale differently"),
                  vs("aic_amp", f"amplitude only ({j['beta_amp']:.2f}):",
                     "pulse count adds to the fit"),
                  vs("aic_linear", "proportional to charge (1, 1):", "exponents differ from 1"),
                  vs("aic_const", "constant amplitude:",
                     "current explains part of the session differences")]
        lines += [f"pulses reference n_ref = {SUPERPOSITION_FIELD['n_ref']:g} "
                      f"(median over sessions)", f"far-field level C = {j['c']:+.3f}", "=" * 70]
        return "\n".join(lines)
    beta = f"beta = {j['beta']:.2f}"
    if ci:
        beta += f"  (95% CI {b_lo:.2f} to {b_hi:.2f})"
        if b_hi < 1:
            beta += "  -> grows SLOWER than the field (saturating); CI excludes 1"
        elif b_lo > 1:
            beta += "  -> grows FASTER than the field; CI excludes 1"
        else:
            beta += "  -> consistent with proportional to the field (CI includes 1)"
    lines.append(beta)
    lines.append(f"vs beta = 1:            AIC difference {d_lin:+.1f}  -> "
                 + ("free beta clearly better" if d_lin < -2 else
                    "beta = 1 better" if d_lin > 2 else "no clear difference"))
    lines.append(f"vs constant amplitude:  AIC difference {d_const:+.1f}  -> "
                 + ("current explains part of the session differences" if d_const < -2 else
                    "constant amplitude better" if d_const > 2 else "no clear difference"))
    if "r0" in j:
        r0 = f"r0 = {j['r0']:.0f} um (half-effect distance from one electrode)"
        if "r0" in ci:
            r0 += f"  (95% CI {ci['r0'][0]:.0f} to {ci['r0'][1]:.0f})"
        lines.append(r0)
    lines.append(f"far-field level C = {j['c']:+.3f}")
    lines.append("=" * 70)
    return "\n".join(lines)


def falloff_text(fit: dict) -> str:
    ci = fit.get("ci", {})

    def fmt(k, spec):
        lo, hi = ci.get(k, (np.nan, np.nan))
        return f"{fit[k]:{spec}}" + (f" [{lo:{spec}}, {hi:{spec}}]" if ci else "")

    return (f"1/r^2 fit, MI(d) = A r0^2 / (d^2 + r0^2) + C (95% CI: bootstrap over sessions): "
            f"A = {fmt('a', '+.3f')}, C = {fmt('c', '+.3f')}, "
            f"r0 (half-effect distance) = {fmt('r0', '.0f')} um")


def main():
    # ---- parameters ----
    session_ids = None                # None = every session in the table; or ["260518_0", ...]
    spike_source = SPIKE_SOURCE_SPIKE_DAT_ARTWIN  # one window per session, same for ON and OFF
    # alternatives: SPIKE_SOURCE_SPIKE_DAT_ARTMASK (per-trial mask), SPIKE_SOURCE_SPIKE_DAT (none)
    channel_mode = "all"              # "all" or "cluster" (ClusterInfo channels of each session)
    min_trials_per_condition = 5      # channel needs this many ON and OFF trials
    min_rate_hz = 1.0                 # drop channels whose (ON + OFF) / 2 rate is below this
    alpha = 0.05                      # per-channel Welch t-test threshold
    normalize_psth = True             # divide each channel's PSTH by its OFF choice-period rate
    plot_distance_to_estim = True     # MI vs distance to the nearest stimulated channel
    show_point_labels = False         # session/channel label on each distance-plot point
    fit_distance_falloff = True       # fit current-density falloff (1/r^2) to MI vs distance
    distance_fit_bootstraps = 1000    # session-resampling bootstraps for CIs (0 = no CIs)
    current_metrics = ["total_current"]  # panels added to the distance figure, one row each;
                                      # also "current_per_second"; [] = none
    near_field_um = 250.0             # "near EStim" = within this distance (65 um = 1 channel)
    split_by_polarity = True          # near-EStim panel: cathodic / anodic sessions, own fits
    binned_stat = "mean"              # distance plot: "mean" (+- SEM), "median" (IQR) or None,
    distance_bin_um = 65.0            # per distance bin of this width (65 um = one channel)
    joint_current_fit = True          # fit modulation as a power of the stimulating current
    joint_predictor = "superposition"  # "superposition": field summed over each EStim channel
                                      # with its own distance (physics of several electrodes);
                                      # "total_current": session total x 1/r^2 to nearest
    superposition_field = "charge"    # what each EStim channel contributes to the field:
                                      # "amplitude" = per-pulse a1 only (pulses ignored),
                                      # "charge" = a1 x pulses (one exponent, default),
                                      # "separate" = a1 field and pulse count, own exponents
    robust_fit = True                 # weighted-current fit down-weights outlier channels
    robust_scale = 0.1                # (soft L1): residuals beyond this MI count linearly
    field_min_distance_um = 65.0      # field weight = (this / d)^2, d floored here (65 um =
                                      # one channel spacing; stim channel and neighbours = 1)
    current_ranges = {                # (min, max) per metric, e.g. (0, 3000); sessions outside
        "current_per_second": (0, 5000),  # are left out of that metric's two panels and their
        "total_current": None,        # correlation only. None = all; either end may be None
    }
    min_trials_per_group = 3          # channel needs this many trials in a sample x choice group
    output_root = "/home/connorlab/Documents/plots/across_experiments/choice_period_estim"
    show_plots = True
    # --------------------

    rows = load_rows(session_ids, spike_source)
    if rows.empty:
        print(f"No rows in {TABLE_NAME}. Run ChoicePeriodEStimAnalysis per session first.")
        return
    if channel_mode == "cluster":
        rows = restrict_to_cluster_channels(rows)
    elif channel_mode != "all":
        raise ValueError(f"channel_mode must be 'all' or 'cluster', got {channel_mode!r}")

    all_channels = add_derived(to_channel_table(rows), alpha)
    table = filter_channels(all_channels, min_trials_per_condition, min_rate_hz)
    print(f"Kept {len(table)} of {len(all_channels)} channels "
          f"(>= {min_trials_per_condition} trials per condition, >= {min_rate_hz} spikes/s)")
    if table.empty:
        return

    pop = population_stats(table)
    text = stats_text(pop, alpha)

    distance_result = None
    if plot_distance_to_estim:
        estim_by_session = {sid: estim_channels_for_session(sid)
                            for sid in table["session_id"].unique()}
        for sid, chs in estim_by_session.items():
            if not chs:
                print(f"{sid}: no EStimParameters channels with a1 > 0, no distance")
        coords = probe_coordinates()
        table = add_estim_distance(table, coords, estim_by_session)
        all_channels = add_estim_distance(all_channels, coords, estim_by_session)
        if current_metrics:
            current = {sid: session_current_metrics(sid) for sid in estim_by_session}
            for m in current_metrics:
                values = {sid: c.get(m, np.nan) for sid, c in current.items()}
                table[m] = table["session_id"].map(values)
                all_channels[m] = all_channels["session_id"].map(values)
            if joint_current_fit and joint_predictor == "superposition":
                charges = {sid: session_stim_charges(
                    sid, per_pulse=superposition_field != "charge") for sid in estim_by_session}
                pulses = ({sid: session_pulse_count(sid) for sid in estim_by_session}
                          if superposition_field == "separate" else None)
                if pulses:
                    print("Pulses per ON trial: " + ", ".join(
                        f"{sid} {n:.1f}" for sid, n in sorted(pulses.items())))
                FIT_LOSS.clear()
                if robust_fit:
                    FIT_LOSS.update(loss="soft_l1", f_scale=robust_scale)
                table = add_stim_sources(table, coords, charges, field=superposition_field,
                                         pulses_by_session=pulses,
                                         min_distance_um=field_min_distance_um)
            if split_by_polarity:
                polarity = {sid: c.get("polarity") for sid, c in current.items()}
                table["polarity"] = table["session_id"].map(polarity)
                all_channels["polarity"] = all_channels["session_id"].map(polarity)
        distance_fig, distance_result = plot_mi_vs_distance(
            table, alpha, show_point_labels, fit_distance_falloff, distance_fit_bootstraps,
            current_metrics=current_metrics, near_field_um=near_field_um,
            current_ranges=current_ranges, binned_stat=binned_stat,
            distance_bin_um=distance_bin_um, joint_fit=joint_current_fit,
            joint_predictor=joint_predictor)
        if distance_result:
            text += (f"\nPearson correlation, MI vs distance to EStim (channels): "
                     f"r = {distance_result['r']:.2f}, {_p_text(distance_result['p'])}, "
                     f"n = {distance_result['n']}")
            if distance_result["fit"]:
                text += "\n" + falloff_text(distance_result["fit"])
            for m, cur in (distance_result.get("current") or {}).items():
                head = (f"\nPearson correlation, session mean MI of channels <= "
                        f"{cur['near_field_um']:g} um vs {m} (sessions)")
                if "r" in cur:
                    text += (f"{head}: r = {cur['r']:.2f}, {_p_text(cur['p'])}, "
                             f"n = {cur['n_sessions']}")
                if cur.get("joint"):
                    text += "\n" + joint_text(m, cur["joint"])
                for pol, st in cur["by_polarity"].items():
                    text += (f"{head}, {pol}: r = {st['r']:.2f}, {_p_text(st['p'])}, "
                             f"n = {st['n']}")
                if cur["excluded"]:
                    text += (f"\n  ({m} range {cur['current_range']}; left out: "
                             f"{', '.join(cur['excluded'])})")
    print(text)

    out_dir = os.path.join(output_root, datetime.now().strftime("%Y%m%d_%H%M%S"))
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "config.json"), "w") as f:
        json.dump({
            "session_ids": session_ids,
            "sessions_used": sorted(table["session_id"].unique()),
            "spike_source": spike_source,
            "channel_mode": channel_mode,
            "min_trials_per_condition": min_trials_per_condition,
            "min_rate_hz": min_rate_hz,
            "alpha": alpha,
            "normalize_psth": normalize_psth,
            "min_trials_per_group": min_trials_per_group,
            "plot_distance_to_estim": plot_distance_to_estim,
            "fit_distance_falloff": fit_distance_falloff,
            "current_metrics": current_metrics,
            "near_field_um": near_field_um,
            "current_ranges": current_ranges,
            "split_by_polarity": split_by_polarity,
            "binned_stat": binned_stat,
            "joint_current_fit": joint_current_fit,
            "joint_predictor": joint_predictor,
            "superposition_field": superposition_field,
            "field_min_distance_um": field_min_distance_um,
            "robust_fit": robust_fit,
            "robust_scale": robust_scale,
            "distance_bin_um": distance_bin_um,
            "distance_fit_bootstraps": distance_fit_bootstraps,
        }, f, indent=2)
    with open(os.path.join(out_dir, "stats.txt"), "w") as f:
        f.write(text + "\n")
    all_channels.drop(columns=[c for c in all_channels.columns if c.startswith("psth_mean")]).assign(
        kept=lambda d: d.set_index(["session_id", "channel"]).index.isin(
            table.set_index(["session_id", "channel"]).index)
    ).to_csv(os.path.join(out_dir, "choice_period_channels.csv"), index=False)

    if distance_result is not None:
        distance_fig.savefig(os.path.join(out_dir, "mi_vs_estim_distance.png"), dpi=150,
                             bbox_inches="tight")
        distance_fig.savefig(os.path.join(out_dir, "mi_vs_estim_distance.svg"),
                             bbox_inches="tight")

    table = add_group_psths(table, session_ids, spike_source)
    fig = plot_psths(table, normalize_psth, min_trials_per_group)
    fig.savefig(os.path.join(out_dir, "choice_period_psth.png"), dpi=150, bbox_inches="tight")
    fig.savefig(os.path.join(out_dir, "choice_period_psth.svg"), bbox_inches="tight")

    sync = load_synchrony(session_ids, spike_source)
    sync = sync[sync["session_id"].isin(table["session_id"].unique())]
    if sync.empty:
        print(f"No rows in {SYNC_TABLE_NAME}; rerun ChoicePeriodEStimAnalysis per session.")
    else:
        windows = (sync.drop_duplicates("session_id")[["session_id", "rejection_window"]]
                   .sort_values("session_id").fillna(""))
        windows.to_csv(os.path.join(out_dir, "rejection_windows.csv"), index=False)
        print("Rejection windows (s from choices_on, same for ON and OFF):")
        for _, w in windows.iterrows():
            print(f"  {w['session_id']}: {w['rejection_window'] or 'none'}")
        fig = plot_synchrony(sync)
        fig.savefig(os.path.join(out_dir, "choice_period_synchrony.png"), dpi=150,
                    bbox_inches="tight")
        fig.savefig(os.path.join(out_dir, "choice_period_synchrony.svg"), bbox_inches="tight")
    print(f"Saved to {out_dir}")
    for m, cur in ((distance_result or {}).get("current") or {}).items():
        if cur.get("joint"):
            print(joint_summary(cur["joint"]))
    if show_plots:
        plt.show()


if __name__ == "__main__":
    main()
