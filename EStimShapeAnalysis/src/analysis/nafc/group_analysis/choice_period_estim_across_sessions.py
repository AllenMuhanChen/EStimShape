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

The population PSTH averages each channel's choices_on-aligned PSTH (mean
across trials), optionally after dividing by that channel's OFF choice-period
rate, so every channel contributes on the same scale. Shading is SEM across
channels.

Outputs (timestamped folder): figure (png + svg), channel table (csv),
stats.txt, config.json.
"""

from __future__ import annotations

import json
import os
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from src.analysis.nafc.neural.choice_period_response import (
    TABLE_NAME, SPIKE_SOURCE_SPIKE_DAT, ESTIM_COLORS, ESTIM_LABELS, decode_array,
)

SIG_COLORS = {"decrease": "#D1495B", "n.s.": "#B0B0B0", "increase": "#2E86AB"}


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------

def load_rows(session_ids, spike_source: str) -> pd.DataFrame:
    from clat.util.connection import Connection
    conn = Connection("allen_data_repository")
    cols = ["session_id", "channel", "is_estim_on", "n_trials", "mean_rate", "sem_rate",
            "p_value", "t_stat", "psth_start_s", "psth_bin_size_s", "psth_mean"]
    query = f"SELECT {', '.join(cols)} FROM {TABLE_NAME} WHERE spike_source = %s"
    params = [spike_source]
    if session_ids:
        query += f" AND session_id IN ({', '.join(['%s'] * len(session_ids))})"
        params += list(session_ids)
    conn.execute(query, params=tuple(params))
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
    table = off[["n_trials", "mean_rate", "sem_rate", "p_value", "t_stat",
                 "psth_start_s", "psth_bin_size_s", "psth_mean"]].join(
        on[["n_trials", "mean_rate", "sem_rate", "psth_mean"]],
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
        lines.append(f"One-sample t-test, MI vs 0 (channels): mean {s['mean_mi']:+.3f}, "
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

def population_psth(table: pd.DataFrame, normalize: bool):
    """Return (bin_centers, {estim_on: (mean, sem, n)}) using the PSTH layout
    shared by most channels; channels saved with other bins are skipped."""
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
    for estim_on, col in ((False, "psth_mean_off"), (True, "psth_mean_on")):
        curves = []
        for _, r in sub.iterrows():
            curve = decode_array(r[col])
            if normalize:
                if not r["mean_rate_off"] > 0:
                    continue
                curve = curve / r["mean_rate_off"]
            curves.append(curve)
        arr = np.vstack(curves) if curves else np.full((1, n_bins), np.nan)
        n = np.sum(~np.isnan(arr), axis=0)
        with np.errstate(invalid="ignore", divide="ignore"):
            mean = np.nanmean(arr, axis=0)
            sem = np.nanstd(arr, axis=0, ddof=1) / np.sqrt(n)
        out[estim_on] = (mean, sem, len(curves))
    return centers, out


# ---------------------------------------------------------------------------
# Figure
# ---------------------------------------------------------------------------

def plot_summary(table: pd.DataFrame, pop: dict, alpha: float, normalize_psth: bool,
                 n_hist_bins: int, show_point_labels: bool):
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    ax_sc, ax_hist, ax_psth, ax_sess = axes.ravel()
    label_size, tick_size, title_size = 14, 12, 15

    # A: OFF vs ON scatter
    for sig, color in SIG_COLORS.items():
        sub = table[table["significance"] == sig]
        ax_sc.scatter(sub["mean_rate_off"], sub["mean_rate_on"], s=45, color=color,
                      alpha=0.8, edgecolor="white", linewidth=0.5,
                      label=f"{sig} (n={len(sub)})")
    hi = float(np.nanmax(table[["mean_rate_off", "mean_rate_on"]].to_numpy())) * 1.05
    ax_sc.plot([0, hi], [0, hi], color="black", linewidth=1, linestyle="--")
    ax_sc.set_xlim(0, hi)
    ax_sc.set_ylim(0, hi)
    ax_sc.set_aspect("equal")
    if show_point_labels:
        for _, r in table.iterrows():
            ax_sc.annotate(f"{r['session_id']} {r['channel']}",
                           (r["mean_rate_off"], r["mean_rate_on"]), fontsize=7)
    ax_sc.set_xlabel("EStim OFF rate (spikes/s)", fontsize=label_size)
    ax_sc.set_ylabel("EStim ON rate (spikes/s)", fontsize=label_size)
    ax_sc.set_title("Choice-period rate per channel", fontsize=title_size)
    ax_sc.legend(fontsize=11, frameon=False, title=f"Welch p < {alpha:g}", title_fontsize=11)

    # B: modulation index histogram
    edges = np.linspace(-1, 1, n_hist_bins + 1)
    data = [table.loc[table["significance"] == s, "modulation_index"] for s in SIG_COLORS]
    ax_hist.hist(data, bins=edges, stacked=True, color=list(SIG_COLORS.values()),
                 label=list(SIG_COLORS), edgecolor="white", linewidth=0.5)
    ax_hist.axvline(0, color="black", linewidth=1)
    if "mi_t" in pop:
        ax_hist.axvline(pop["mi_t"]["mean_mi"], color="black", linewidth=2, linestyle="--",
                        label=f"mean {pop['mi_t']['mean_mi']:+.3f}")
        ax_hist.text(0.02, 0.97, f"t-test vs 0: {_p_text(pop['mi_t']['p'])}",
                     transform=ax_hist.transAxes, fontsize=12, va="top")
    ax_hist.set_xlabel("Modulation index (ON - OFF) / (ON + OFF)", fontsize=label_size)
    ax_hist.set_ylabel("Channels", fontsize=label_size)
    ax_hist.set_title("EStim modulation of choice-period rate", fontsize=title_size)
    ax_hist.legend(fontsize=11, frameon=False, loc="upper right")

    # C: population PSTH
    centers, curves = population_psth(table, normalize_psth)
    for estim_on in (False, True):
        mean, sem, n = curves[estim_on]
        color = ESTIM_COLORS[estim_on]
        ax_psth.plot(centers, mean, color=color, linewidth=2.4,
                     label=f"{ESTIM_LABELS[estim_on]} (n={n} channels)")
        ax_psth.fill_between(centers, mean - sem, mean + sem, color=color, alpha=0.2, linewidth=0)
    ax_psth.axvline(0, color="black", linewidth=1)
    ax_psth.set_xlabel("Time from choices on (s)", fontsize=label_size)
    ax_psth.set_ylabel("Rate / OFF choice-period rate" if normalize_psth
                       else "Firing rate (spikes/s)", fontsize=label_size)
    ax_psth.set_title("Population PSTH", fontsize=title_size)
    ax_psth.legend(fontsize=11, frameon=False)

    # D: per-session modulation index
    sessions = sorted(table["session_id"].unique())
    rng = np.random.default_rng(0)
    for x, sid in enumerate(sessions):
        mi = table.loc[table["session_id"] == sid, "modulation_index"].to_numpy()
        colors = [SIG_COLORS[s] for s in table.loc[table["session_id"] == sid, "significance"]]
        ax_sess.scatter(x + rng.uniform(-0.18, 0.18, len(mi)), mi, s=22, color=colors, alpha=0.7,
                        linewidth=0)
        sem = np.std(mi, ddof=1) / np.sqrt(len(mi)) if len(mi) > 1 else 0
        ax_sess.errorbar(x, mi.mean(), yerr=sem, fmt="s", color="black", markersize=8,
                         capsize=5, linewidth=2)
    ax_sess.axhline(0, color="black", linewidth=1, linestyle="--")
    ax_sess.set_xticks(range(len(sessions)), sessions, rotation=45, ha="right")
    ax_sess.set_xlim(-0.6, len(sessions) - 0.4)
    ax_sess.set_ylabel("Modulation index", fontsize=label_size)
    ax_sess.set_title("Per session (mean ± SEM)", fontsize=title_size)
    if "session_mi_t" in pop:
        ax_sess.text(0.02, 0.97, f"session means vs 0: {_p_text(pop['session_mi_t']['p'])}",
                     transform=ax_sess.transAxes, fontsize=12, va="top")

    for ax in axes.ravel():
        ax.tick_params(labelsize=tick_size)
        ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    return fig


def main():
    # ---- parameters ----
    session_ids = None                # None = every session in the table; or ["260518_0", ...]
    spike_source = SPIKE_SOURCE_SPIKE_DAT
    channel_mode = "all"              # "all" or "cluster" (ClusterInfo channels of each session)
    min_trials_per_condition = 5      # channel needs this many ON and OFF trials
    min_rate_hz = 1.0                 # drop channels whose (ON + OFF) / 2 rate is below this
    alpha = 0.05                      # per-channel Welch t-test threshold
    normalize_psth = True             # divide each channel's PSTH by its OFF choice-period rate
    n_hist_bins = 30
    show_point_labels = False
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
            "n_hist_bins": n_hist_bins,
        }, f, indent=2)
    with open(os.path.join(out_dir, "stats.txt"), "w") as f:
        f.write(text + "\n")
    all_channels.drop(columns=["psth_mean_off", "psth_mean_on"]).assign(
        kept=lambda d: d.set_index(["session_id", "channel"]).index.isin(
            table.set_index(["session_id", "channel"]).index)
    ).to_csv(os.path.join(out_dir, "choice_period_channels.csv"), index=False)

    fig = plot_summary(table, pop, alpha, normalize_psth, n_hist_bins, show_point_labels)
    fig.savefig(os.path.join(out_dir, "choice_period_estim.png"), dpi=150, bbox_inches="tight")
    fig.savefig(os.path.join(out_dir, "choice_period_estim.svg"), bbox_inches="tight")
    print(f"Saved to {out_dir}")
    if show_plots:
        plt.show()


if __name__ == "__main__":
    main()
