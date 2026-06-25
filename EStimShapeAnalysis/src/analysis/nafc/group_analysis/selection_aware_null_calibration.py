"""
Calibration / diagnostics for the selection-aware null simulation.

WHY THIS EXISTS
---------------
The existing permutation test (estim_groups_permutation_test ->
max_estim_per_experiment) shuffles EStim ON/OFF labels *within each surviving
condition*. That correctly pays for multiplicity across the surviving set, but it
takes the surviving set as given. It does NOT account for the fact that conditions
were adaptively killed early (before n~10) when their interim effect looked bad.
Conditioning on "survived the early kill" left-truncates the per-condition effect
distribution, biasing the survivors' effects upward — exactly in the upper tail
that the max-stat and exceedance statistics read.

This module does NOT run the simulation. It reads EStimShapeTrials (which still
contains the *killed* conditions as low-n rows that the n>=min_trials filter later
drops) and measures the inputs a selection-aware null needs:

  1. budget   : total EStim-ON trials spent per session (the constraint a real or
                adversarial experimenter operates under — killing early frees
                trials to attempt more conditions).
  2. attempts : how many distinct conditions were attempted per session, INCLUDING
                the ones killed early. This is the "M" the previous discussion said
                you must know or the selection power is undefined. You already
                logged it implicitly: killed conditions left their partial trials.
  3. baseline : the per-condition EStim-OFF hypothesized-choice rate (p), used as
                the H0 Bernoulli rate (under H0, ON and OFF share p). Kept per
                behavioral context so the simulation reproduces realistic base-rate
                heterogeneity (the effect's variance depends on p).
  4. kill envelope : for every killed condition, the pair (n_kill, effect_at_kill).
                Because a killed condition's own (n_on, effect) IS a sample of the
                (decision_n, kill_threshold) the experimenter actually used, this
                scatter directly delimits the *realistic* corner of kill-rule space.
                The simulation's adversary is bounded to this envelope so it stays a
                "best a real experimenter could do" upper bound, not a strawman.
  5. survivor final-n distribution : selection bias scales with decision_n / final_n,
                so the simulation must match the real final-n of survivors.

The condition enumeration reuses split_data_by_conditions / _filter_for_metric so a
"condition" here is exactly an EStimEffects row (behavioral x estim_spec_id), with
the same gen-windowed OFF baseline. Survived vs killed is decided by the same
min_trials filter the population tests use.

NEXT STEP (separate module): selection_aware_null_simulation.py consumes a
Calibration and, for a swept KillRule, regenerates the whole
attempt -> kill -> n>=min_trials filter -> max/exceedance process under H0, giving
a selection-aware null for the SAME statistic max_estim_per_experiment reports.
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

sys.path.insert(0, str(Path(__file__).parents[3]))

from src.analysis.nafc.group_analysis.analyze_estim_by_condition import (
    METRIC_PCT_HYPOTHESIZED, METRIC_PCT_HYP_VS_DELTA,
    read_trial_data_from_repository, split_data_by_conditions, _filter_for_metric,
    _DEFAULT_BEHAVIORAL_CONDITIONS, _DEFAULT_ESTIM_CONDITIONS, _get_all_session_ids)
from src.analysis.nafc.group_analysis.max_estim_per_experiment import DEFAULT_MIN_TRIALS


@dataclass
class ConditionObservation:
    """One attempted condition (survivor OR killed), reconstructed from raw trials."""
    session_id: str
    cond_dict: dict
    behavioral_key: tuple          # behavioral context, for base-rate heterogeneity
    n_on: int
    n_off: int
    p_off: float                   # gen-windowed OFF hypothesized rate (the H0 base rate)
    effect: float                  # (ON% - OFF%), percentage points, on final trials
    on_trajectory: list            # cumulative ON hypothesized rate after 1,2,...,n_on ON trials
    survived: bool                 # n_on >= min_trials AND n_off >= min_trials


@dataclass
class Calibration:
    """Everything the selection-aware simulation needs, measured from real data."""
    min_trials: int
    metric: str
    conditions: list = field(default_factory=list)           # all ConditionObservation
    per_session_budget: dict = field(default_factory=dict)   # session_id -> total ON trials
    per_session_attempts: dict = field(default_factory=dict) # session_id -> # conditions attempted

    # --- convenience views -------------------------------------------------
    @property
    def killed(self):
        return [c for c in self.conditions if not c.survived]

    @property
    def survivors(self):
        return [c for c in self.conditions if c.survived]

    def baseline_rate_pool(self):
        """OFF hypothesized rates across all attempted conditions — the sampler the
        simulation draws each condition's H0 base rate from. Returned with the
        behavioral key so a caller can condition on context if desired."""
        return [(c.behavioral_key, c.p_off, c.n_off) for c in self.conditions
                if c.p_off is not None and np.isfinite(c.p_off)]

    def survivor_final_n(self):
        """(n_on, n_off) for survivors — the final-n distribution to match."""
        return [(c.n_on, c.n_off) for c in self.survivors]

    def kill_envelope(self):
        """(n_kill, effect_at_kill) for killed conditions. n_kill is the killed
        condition's realized ON count; effect is on those trials. The upper edge of
        effect at each n is the realistic kill threshold tau(n)."""
        return [(c.n_on, c.effect) for c in self.killed if c.effect is not None]


def _condition_observation(session_id, comp, metric, min_trials):
    """Build a ConditionObservation from one split_data_by_conditions comparison."""
    on_df = _filter_for_metric(comp['estim_on_data'], metric)
    off_df = _filter_for_metric(comp['estim_off_data'], metric)

    on_df = on_df.dropna(subset=['is_hypothesized_choice'])
    off_df = off_df.dropna(subset=['is_hypothesized_choice'])

    n_on, n_off = len(on_df), len(off_df)
    if n_on == 0 or n_off == 0:
        return None

    p_off = float(off_df['is_hypothesized_choice'].mean())
    p_on = float(on_df['is_hypothesized_choice'].mean())
    effect = 100.0 * (p_on - p_off)

    # Reconstruct the trajectory the experimenter watched: cumulative ON rate in
    # trial order. The interim *effect* at k is on_trajectory[k-1]*100 - p_off*100;
    # we store p_off separately. NOTE: this uses the final gen-windowed OFF rate as a
    # proxy for the running baseline the experimenter actually saw (the OFF baseline
    # is shared across conditions and stabilizes faster than any single condition).
    if 'trial_start' in on_df.columns:
        on_ordered = on_df.sort_values('trial_start')['is_hypothesized_choice'].to_numpy(dtype=float)
    else:
        on_ordered = on_df['is_hypothesized_choice'].to_numpy(dtype=float)
    cum = np.cumsum(on_ordered) / np.arange(1, len(on_ordered) + 1)

    behavioral_key = tuple(sorted(comp['behavioral_conditions'].items()))

    return ConditionObservation(
        session_id=session_id,
        cond_dict={**comp['behavioral_conditions'], **comp['estim_conditions']},
        behavioral_key=behavioral_key,
        n_on=n_on,
        n_off=n_off,
        p_off=p_off,
        effect=effect,
        on_trajectory=cum.tolist(),
        survived=(n_on >= min_trials and n_off >= min_trials),
    )


def calibrate(session_ids=None, metric=METRIC_PCT_HYP_VS_DELTA,
              min_trials=DEFAULT_MIN_TRIALS,
              behavioral_conditions=None, estim_conditions=None):
    """Read EStimShapeTrials and measure the selection-model inputs.

    Enumerates conditions exactly as the effect pipeline does (same behavioral x
    estim_spec_id grouping, same gen-windowed OFF baseline), so "attempted
    conditions" includes the early-killed ones that the n>=min_trials filter later
    removes from the population tests.
    """
    if behavioral_conditions is None:
        behavioral_conditions = _DEFAULT_BEHAVIORAL_CONDITIONS
    if estim_conditions is None:
        estim_conditions = _DEFAULT_ESTIM_CONDITIONS

    ids = _get_all_session_ids() if session_ids is None else list(session_ids)

    calib = Calibration(min_trials=min_trials, metric=metric)

    for sid in ids:
        data = read_trial_data_from_repository(sid)
        if data is None or len(data) == 0:
            continue
        comps = split_data_by_conditions(data, behavioral_conditions, estim_conditions)

        session_budget = 0
        session_attempts = 0
        for comp in comps:
            obs = _condition_observation(sid, comp, metric, min_trials)
            if obs is None:
                continue
            calib.conditions.append(obs)
            session_budget += obs.n_on
            session_attempts += 1

        calib.per_session_budget[sid] = session_budget
        calib.per_session_attempts[sid] = session_attempts

    return calib


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_summary(calib):
    n_sess = len(calib.per_session_attempts)
    n_cond = len(calib.conditions)
    n_surv = len(calib.survivors)
    n_kill = len(calib.killed)

    print(f"\n=== Selection-model calibration "
          f"(metric={calib.metric}, min_trials={calib.min_trials}) ===")
    print(f"Sessions:               {n_sess}")
    print(f"Conditions attempted:   {n_cond}  "
          f"(survivors {n_surv}, killed {n_kill}, "
          f"kill rate {100.0 * n_kill / n_cond:.0f}%)" if n_cond else "no conditions")
    if not n_cond:
        return

    attempts = np.array(list(calib.per_session_attempts.values()))
    budgets = np.array(list(calib.per_session_budget.values()))
    print(f"\nAttempts per session:   median {np.median(attempts):.0f}  "
          f"range [{attempts.min()}, {attempts.max()}]")
    print(f"ON-trial budget/session: median {np.median(budgets):.0f}  "
          f"range [{budgets.min()}, {budgets.max()}]")

    surv_n = np.array([c.n_on for c in calib.survivors]) if n_surv else np.array([])
    kill_n = np.array([c.n_on for c in calib.killed]) if n_kill else np.array([])
    if surv_n.size:
        print(f"\nSurvivor n_on:          median {np.median(surv_n):.0f}  "
              f"range [{surv_n.min()}, {surv_n.max()}]")
    if kill_n.size:
        print(f"Killed n_on:            median {np.median(kill_n):.0f}  "
              f"range [{kill_n.min()}, {kill_n.max()}]")
        print("  -> kill points are the decision_n the experimenter actually used; "
              "the simulation's adversary is bounded to this range.")

    # Kill envelope: at each killed-n, the most generous (largest) surviving-into-kill
    # effect is the realistic threshold tau(n). Print it as a quick table.
    env = calib.kill_envelope()
    if env:
        print("\nKill envelope  (n_kill: effect range of killed conditions):")
        by_n = {}
        for n, eff in env:
            by_n.setdefault(n, []).append(eff)
        for n in sorted(by_n):
            effs = np.array(by_n[n])
            print(f"  n={n:2d}  killed={len(effs):2d}  "
                  f"effect median {np.median(effs):+5.1f}%  max {effs.max():+5.1f}%")
        print("  -> tau(n) ~ max killed effect at each n: the most lenient kill the "
              "data is consistent with.")


def plot_calibration(calib, save_path=None):
    """Three diagnostics: kill envelope, attempts/budget per session, base-rate pool."""
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    # (1) Kill envelope: effect vs n, killed (red) vs survivors (gray) ---------
    ax = axes[0]
    for c in calib.survivors:
        ax.scatter(c.n_on, c.effect, s=20, color="gray", alpha=0.5, zorder=2)
    for c in calib.killed:
        ax.scatter(c.n_on, c.effect, s=30, color="red", alpha=0.8, zorder=3,
                   edgecolors="black", linewidths=0.4)
    ax.axvline(calib.min_trials, color="blue", linestyle="--", linewidth=1,
               label=f"min_trials={calib.min_trials}")
    ax.axhline(0, color="gray", linewidth=0.8, alpha=0.5)
    ax.set_xlabel("n_on (realized ON trials)")
    ax.set_ylabel("effect (ON% - OFF%)")
    ax.set_title("Kill envelope\nred = killed (decision_n, threshold) samples")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # (2) Attempts and budget per session ------------------------------------
    ax = axes[1]
    sids = list(calib.per_session_attempts)
    attempts = [calib.per_session_attempts[s] for s in sids]
    killed_per = {s: 0 for s in sids}
    for c in calib.killed:
        killed_per[c.session_id] = killed_per.get(c.session_id, 0) + 1
    killed_counts = [killed_per[s] for s in sids]
    x = np.arange(len(sids))
    ax.bar(x, attempts, color="steelblue", label="attempted")
    ax.bar(x, killed_counts, color="red", alpha=0.7, label="killed")
    ax.set_xticks(x)
    ax.set_xticklabels(sids, rotation=45, ha="right", fontsize=7)
    ax.set_ylabel("# conditions")
    ax.set_title("Attempts vs killed per session")
    ax.legend(fontsize=8)
    ax.grid(True, axis="y", alpha=0.3)

    # (3) Base-rate pool ------------------------------------------------------
    ax = axes[2]
    rates = [100.0 * p for _, p, _ in calib.baseline_rate_pool()]
    if rates:
        ax.hist(rates, bins=20, color="seagreen", edgecolor="black", alpha=0.8)
    ax.axvline(50, color="gray", linestyle="--", linewidth=1)
    ax.set_xlabel("OFF hypothesized rate p (%)")
    ax.set_ylabel("# conditions")
    ax.set_title("H0 base-rate pool\n(ON==OFF under H0)")
    ax.grid(True, axis="y", alpha=0.3)

    fig.tight_layout()
    if save_path:
        import os
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        fig.savefig(save_path, bbox_inches="tight", dpi=150)
        print(f"Saved to {save_path}")
    plt.show()
    return fig


def main():
    calib = calibrate(
        session_ids=None,          # all sessions; pass a list to restrict
        metric=METRIC_PCT_HYP_VS_DELTA,
        min_trials=10,             # match max_estim_per_experiment's min_trials
    )
    print_summary(calib)
    plot_calibration(
        calib,
        save_path="/home/connorlab/Documents/plots/across_experiments/selection_calibration.png",
    )


if __name__ == "__main__":
    main()
