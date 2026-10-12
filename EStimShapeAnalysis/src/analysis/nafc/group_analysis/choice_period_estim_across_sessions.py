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
        }, f, indent=2)
    with open(os.path.join(out_dir, "stats.txt"), "w") as f:
        f.write(text + "\n")
    all_channels.drop(columns=[c for c in all_channels.columns if c.startswith("psth_mean")]).assign(
        kept=lambda d: d.set_index(["session_id", "channel"]).index.isin(
            table.set_index(["session_id", "channel"]).index)
    ).to_csv(os.path.join(out_dir, "choice_period_channels.csv"), index=False)

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
    if show_plots:
        plt.show()


if __name__ == "__main__":
    main()
