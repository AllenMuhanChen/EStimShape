"""
plot_bias_controller.py
-----------------------
Quick diagnostics for the NAFC anti-bias controller. Reads the two tables the live controller writes
into the experiment (nafc) database and plots them:

  * bias_controller_events  -- append-only, one row per bias-eligible/shaped trial
  * bias_controller_state   -- current per-stimulus snapshot (resume-safe source of truth)

Three panels:
  1. Bias score over trials, one line per stimulus (by chosen id), with the flag / un-flag
     thresholds. Shows when each stimulus was detected as biased.
  2. Reward per correct trial: the un-shaped base vs. what was actually delivered (they overlap in
     shadow mode); biased picks highlighted.
  3. Current per-stimulus bias score, grouped by variant, red where currently flagged.

Usage: edit the config constants just below, then run this file (from your IDE, or
`python -m src.analysis.nafc.plot_bias_controller`). No command-line arguments.
"""

import sys

import pandas as pd
import matplotlib.pyplot as plt

from clat.util.connection import Connection

try:
    from src.startup import context
    DEFAULT_DB = context.nafc_database
except Exception:
    DEFAULT_DB = None

# ---------------------------------------------------------------------------
# Configure here -- just edit these and run the file. No command-line arguments.
# ---------------------------------------------------------------------------
# Experiment (nafc) database to read. None -> context.nafc_database; or set explicitly, e.g.
# DATABASE = "allen_estimshape_exp_260630_0".
DATABASE = None
# None -> show the figure interactively; set a path (e.g. "bias_diag.png") to save it instead.
SAVE_PATH = None
# Flag / un-flag thresholds; mirror your BiasTrackerConfig if you changed them from the defaults.
S_HIGH = 0.60
S_LOW = 0.35

EVENT_COLS = [
    "tstamp", "trial_stim_id", "variant_id", "sample_id", "chosen_id", "num_choices",
    "correct", "chosen_biased", "avoided_biased", "bias_score", "reward_pulses_base",
    "reward_pulses_delivered", "extra_iti_ms", "shaping_applied", "shadow_mode",
]
STATE_COLS = [
    "stim_id", "variant_id", "num_choices", "ewma_chose", "ewma_chose_when_wrong",
    "ewma_hit_when_correct", "n_present", "n_distractor", "n_correct_present", "biased",
    "bias_score", "last_updated",
]


def _read(conn, table, cols):
    try:
        conn.execute("SELECT " + ", ".join(cols) + " FROM " + table)
        rows = conn.fetch_all()
    except Exception as e:
        print("Could not read %s (%s) -- has the controller run yet?" % (table, e))
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(list(rows), columns=cols)


def load(db):
    conn = Connection(db)
    events = _read(conn, "bias_controller_events", EVENT_COLS)
    state = _read(conn, "bias_controller_state", STATE_COLS)
    return events, state


def _with_trial_index(events):
    ev = events.sort_values("tstamp").reset_index(drop=True)
    ev["trial"] = range(1, len(ev) + 1)
    return ev


def plot_bias_scores(ax, events):
    ax.set_title("Per-stimulus bias score over trials")
    ax.set_xlabel("bias-eligible / shaped trial")
    ax.set_ylabel("bias score of chosen stimulus")
    ax.set_ylim(-0.02, 1.02)
    if events.empty:
        ax.text(0.5, 0.5, "no events logged yet", ha="center", va="center", transform=ax.transAxes)
        return
    ev = _with_trial_index(events)
    ev = ev[ev["chosen_id"].notna()]
    stim_ids = sorted(ev["chosen_id"].dropna().unique())
    show_stim_legend = len(stim_ids) <= 10
    cmap = plt.get_cmap("tab10")
    for i, stim in enumerate(stim_ids):
        grp = ev[ev["chosen_id"] == stim]
        label = ("stim %d" % int(stim)) if show_stim_legend else None
        ax.plot(grp["trial"], grp["bias_score"], marker="o", ms=3, lw=1,
                color=cmap(i % 10), label=label)
    ax.axhline(S_HIGH, color="crimson", ls="--", lw=1, label="flag (%.2f)" % S_HIGH)
    ax.axhline(S_LOW, color="gray", ls="--", lw=1, label="un-flag (%.2f)" % S_LOW)
    ax.legend(fontsize=7, ncol=2, loc="upper left")
    if not show_stim_legend:
        ax.text(0.99, 0.02, "%d stimuli" % len(stim_ids), ha="right", va="bottom",
                transform=ax.transAxes, fontsize=7, color="gray")


def plot_reward(ax, events):
    ax.set_title("Reward per correct trial: base vs delivered")
    ax.set_xlabel("trial")
    ax.set_ylabel("juice pulses")
    if events.empty:
        ax.text(0.5, 0.5, "no events logged yet", ha="center", va="center", transform=ax.transAxes)
        return
    ev = _with_trial_index(events)
    corr = ev[ev["correct"] == 1]
    if corr.empty:
        ax.text(0.5, 0.5, "no correct trials logged yet", ha="center", va="center", transform=ax.transAxes)
        return
    ax.plot(corr["trial"], corr["reward_pulses_base"], color="steelblue", lw=1, label="base (un-shaped)")
    ax.plot(corr["trial"], corr["reward_pulses_delivered"], color="darkorange", lw=1, label="delivered")
    biased = corr[corr["chosen_biased"] == 1]
    if not biased.empty:
        ax.scatter(biased["trial"], biased["reward_pulses_delivered"], color="crimson", s=16,
                   zorder=3, label="biased pick")
    if bool(ev["shadow_mode"].iloc[-1]):
        ax.text(0.99, 0.98, "shadow mode", ha="right", va="top", transform=ax.transAxes,
                fontsize=8, color="crimson")
    ax.legend(fontsize=7)


def plot_state(ax, state):
    ax.set_title("Current per-stimulus bias (red = flagged)")
    ax.set_ylabel("current bias score")
    ax.set_ylim(0, 1.02)
    if state.empty:
        ax.text(0.5, 0.5, "no state rows yet", ha="center", va="center", transform=ax.transAxes)
        return
    st = state.sort_values(["variant_id", "stim_id"]).reset_index(drop=True)
    colors = ["crimson" if bool(b) else "steelblue" for b in st["biased"]]
    xs = list(range(len(st)))
    ax.bar(xs, st["bias_score"], color=colors)
    ax.axhline(S_HIGH, color="crimson", ls="--", lw=1)
    ax.axhline(S_LOW, color="gray", ls="--", lw=1)
    ax.set_xticks(xs)
    ax.set_xticklabels([str(int(s)) for s in st["stim_id"]], rotation=90, fontsize=6)
    ax.set_xlabel("stimulus lineage id (grouped by variant)")


def main():
    db = DATABASE if DATABASE else DEFAULT_DB
    if not db:
        print("Set DATABASE at the top of this file (context.nafc_database is unavailable).")
        sys.exit(1)

    events, state = load(db)
    print("Loaded %d events, %d state rows from %s" % (len(events), len(state), db))

    fig, axes = plt.subplots(3, 1, figsize=(11, 12))
    plot_bias_scores(axes[0], events)
    plot_reward(axes[1], events)
    plot_state(axes[2], state)
    fig.suptitle("NAFC anti-bias controller diagnostics -- %s" % db)
    fig.tight_layout(rect=[0, 0, 1, 0.98])

    if SAVE_PATH:
        fig.savefig(SAVE_PATH, dpi=120)
        print("Saved", SAVE_PATH)
    else:
        plt.show()


if __name__ == "__main__":
    main()
