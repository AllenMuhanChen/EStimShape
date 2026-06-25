"""
Selection-aware null simulation for the estim permutation tests.

THE PROBLEM (recap)
-------------------
max_estim_per_experiment's null shuffles EStim ON/OFF labels within each
*surviving* condition. That pays for multiplicity across survivors but takes the
surviving set as given. In reality conditions are adaptively killed early (the
calibration shows a 66% kill rate, median kill at n=5) when their interim effect
looks bad. Conditioning on "survived the early kill" left-truncates survivors'
effects upward — exactly the upper tail the max-stat and exceedance statistics read.

WHAT THIS DOES
--------------
Regenerates the WHOLE process under H0 (estim has no effect, ON and OFF share the
same Bernoulli rate p) and an adversarial-but-realistic kill rule, then recomputes
*your* statistics on the survivors. The distribution of those statistics across
simulated experiments IS the selection-aware null. Comparing your real observed
statistic to it answers: "could an experimenter using the most aggressive realistic
early-killing strategy manufacture my result from pure noise?"

This null subsumes the label-shuffle null: the simulated max is also taken over a
*surviving* set, so it corrects multiplicity AND selection jointly.

THE GENERATIVE MODEL (per simulated experiment)
-----------------------------------------------
For each real session (same session set the population test uses), reproduce its
real effort and constraints, all from calibration:
  - attempt the same number of conditions M_s the session really attempted
    (you only had so many distinct parameter combos to try);
  - spend at most the real ON-trial budget B_s;
  - each attempt draws a base rate p from the real per-condition OFF-rate pool;
  - stream Bernoulli(p) ON trials; at decision_n compute the interim effect vs p
    and KILL if it is below threshold tau (the AggressiveKillRule);
  - survivors grow to a final n drawn from the real survivor n distribution, the
    extra trials generated fresh under H0 (this is the dilution that partially
    washes out the early luck — median kill n=5 grown to median n=16);
  - apply the same n>=min_trials filter, then compute the studentized max-stat
    (best survivor per session) and pooled exceedance counts.

The adversary's only knobs are (decision_n, tau); both are swept and bounded to the
realistic kill envelope. We report the statistic across the sweep and the MOST
adversarial cell, so beating it means "robust to worst-case realistic selection".

KNOWN LIMITATION (conservative direction noted)
-----------------------------------------------
v1 draws each condition's OFF baseline independently. Real conditions in a session
share a gen-windowed OFF baseline, inducing positive cross-condition correlation
that makes the max heavier-tailed. Ignoring it makes the null slightly LIGHTER
(anticonservative for a real-effect claim). If your observed statistic only
marginally beats this null, add the shared-OFF refinement before trusting it.

Studentization here uses the analytic shuffle-null SD
    SD ~= 100 * sqrt(phat*(1-phat)*(1/n_on + 1/n_off)),  phat = pooled ON+OFF rate,
so no nested permutation is needed and the observed side is recomputed the same way
(it will be within rounding of the headline max-stat, which uses an empirical
shuffle SD).
"""

import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from matplotlib import pyplot as plt

sys.path.insert(0, str(Path(__file__).parents[3]))

from src.analysis.nafc.group_analysis.analyze_estim_by_condition import (
    METRIC_PCT_HYPOTHESIZED, METRIC_PCT_HYP_VS_DELTA)
from src.analysis.nafc.group_analysis.max_estim_per_experiment import (
    DEFAULT_MIN_TRIALS, make_weighting)
from src.analysis.nafc.group_analysis.selection_aware_null_calibration import (
    calibrate, Calibration)


# ---------------------------------------------------------------------------
# Kill rules (mirrors the PopulationWeighting ABC pattern in max_estim)
# ---------------------------------------------------------------------------

class KillRule(ABC):
    """Decides, at a condition's decision point, whether to abandon it."""
    label: str = "none"

    @abstractmethod
    def decision_n(self) -> int:
        """ON-trial count at which the keep/kill decision is made."""

    @abstractmethod
    def kill(self, interim_effect: float) -> bool:
        """True -> abandon the condition. interim_effect is ON% - p% at decision_n."""


class AggressiveKillRule(KillRule):
    """Idealized adversary: kill any condition whose interim effect (at decision_n)
    is below ``threshold`` percentage points. Higher threshold / smaller decision_n
    = more aggressive selection. Bounded to the realistic kill envelope by the sweep.
    """
    def __init__(self, decision_n=5, threshold=0.0):
        self._decision_n = int(decision_n)
        self.threshold = float(threshold)
        self.label = f"kill@n={decision_n} if effect<{threshold:+.0f}%"

    def decision_n(self) -> int:
        return self._decision_n

    def kill(self, interim_effect: float) -> bool:
        return interim_effect < self.threshold


# ---------------------------------------------------------------------------
# Statistic core — shared by the observed side and every simulated experiment
# ---------------------------------------------------------------------------

def _studentize(effect, n_on, n_off, p_off):
    """Analytic shuffle-null studentization. Returns z, or None if degenerate."""
    p_on = p_off + effect / 100.0
    n = n_on + n_off
    phat = (p_on * n_on + p_off * n_off) / n
    var = phat * (1.0 - phat) * (1.0 / n_on + 1.0 / n_off)
    sd = 100.0 * np.sqrt(var)
    if not np.isfinite(sd) or sd <= 0:
        return None
    return effect / sd


@dataclass
class _Entry:
    """One condition (real survivor or simulated survivor) feeding the statistic."""
    effect: float
    z: float
    n_on: int
    n_off: int


def _session_best(entries, studentize):
    """Best (largest signed) statistic among a session's survivors, plus the n's of
    the winner (for trial-weighting). None if the session has no usable survivor."""
    usable = [e for e in entries if (e.z is not None if studentize else True)]
    if not usable:
        return None
    stat = (lambda e: e.z) if studentize else (lambda e: e.effect)
    best = max(usable, key=stat)
    return {'observed_signed': stat(best), 'n_on': best.n_on, 'n_off': best.n_off}


def _population_stat(session_entries, studentize, weighting):
    """Weighted-mean best statistic across sessions (the max_estim A_obs)."""
    rows = []
    for entries in session_entries:
        best = _session_best(entries, studentize)
        if best is not None:
            rows.append(best)
    if not rows:
        return None
    w = make_weighting(weighting).normalized_weights(rows)
    observed = np.array([r['observed_signed'] for r in rows])
    return float(np.dot(w, observed))


def _exceedance_counts(session_entries, thresholds, studentize):
    """Pooled count of survivors with statistic >= each threshold."""
    vals = []
    for entries in session_entries:
        for e in entries:
            v = e.z if studentize else e.effect
            if v is not None:
                vals.append(v)
    vals = np.array(vals) if vals else np.array([])
    return np.array([int(np.sum(vals >= t)) for t in thresholds])


# ---------------------------------------------------------------------------
# Observed statistics (real survivors, recomputed with the same analytic SD)
# ---------------------------------------------------------------------------

def _real_session_entries(calib):
    """Group real survivors by session into _Entry lists (the observed side)."""
    by_session = {}
    for c in calib.survivors:
        z = _studentize(c.effect, c.n_on, c.n_off, c.p_off)
        by_session.setdefault(c.session_id, []).append(
            _Entry(effect=c.effect, z=z, n_on=c.n_on, n_off=c.n_off))
    return by_session


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------

@dataclass
class _SimInputs:
    """Calibration distilled into the arrays the per-experiment sim samples from."""
    session_ids: list
    budgets: dict           # session_id -> ON-trial budget B_s
    attempts: dict          # session_id -> # conditions attempted M_s
    base_rates: np.ndarray  # per-condition OFF rates (the H0 base-rate pool)
    surv_n_on: np.ndarray   # survivor final n_on pool
    surv_n_off: np.ndarray  # survivor n_off pool (sampled jointly with n_on)
    min_trials: int


def _prepare_sim_inputs(calib):
    base_rates = np.array([p for _, p, _ in calib.baseline_rate_pool()])
    surv = calib.survivors
    surv_n_on = np.array([c.n_on for c in surv])
    surv_n_off = np.array([c.n_off for c in surv])
    # Only simulate sessions that contribute a real survivor, so the observed and
    # null statistics are built over the same session set.
    session_ids = sorted({c.session_id for c in surv})
    return _SimInputs(
        session_ids=session_ids,
        budgets={s: calib.per_session_budget[s] for s in session_ids},
        attempts={s: calib.per_session_attempts[s] for s in session_ids},
        base_rates=base_rates,
        surv_n_on=surv_n_on,
        surv_n_off=surv_n_off,
        min_trials=calib.min_trials,
    )


def _simulate_session(rng, sim, session_id, kill_rule):
    """One session under H0 + kill_rule. Returns a list of survivor _Entry."""
    budget = sim.budgets[session_id]
    n_attempts = sim.attempts[session_id]
    d_n = kill_rule.decision_n()
    survivors = []
    spent = 0

    for _ in range(n_attempts):
        if spent + d_n > budget:
            break  # cannot afford even the decision window -> stop attempting
        p = float(rng.choice(sim.base_rates))

        # Decision window: stream d_n ON trials, compare interim ON rate to p.
        on_decision = rng.random(d_n) < p
        interim_effect = 100.0 * (on_decision.mean() - p)
        spent += d_n

        if kill_rule.kill(interim_effect):
            continue  # abandoned early; only d_n ON trials spent

        # Survivor: grow to a final n drawn from the real survivor distribution,
        # generating the EXTRA trials fresh under H0 (dilutes the early luck).
        idx = rng.integers(len(sim.surv_n_on))
        target_n_on = int(sim.surv_n_on[idx])
        n_off = int(sim.surv_n_off[idx])
        n_on = max(target_n_on, d_n)

        extra = n_on - d_n
        if spent + extra > budget:           # respect the trial budget
            n_on = d_n + max(0, budget - spent)
            extra = n_on - d_n
        spent += extra

        if n_on < sim.min_trials or n_off < sim.min_trials:
            continue  # same filter the population test applies

        on_full = np.concatenate([on_decision, rng.random(extra) < p])
        off = rng.random(n_off) < p
        effect = 100.0 * (on_full.mean() - off.mean())
        z = _studentize(effect, n_on, n_off, float(off.mean()))
        survivors.append(_Entry(effect=effect, z=z, n_on=n_on, n_off=n_off))

    return survivors


def run_selection_null(calib, kill_rule, n_sims=2000, studentize=True,
                       weighting=None, thresholds=None, seed=0):
    """Monte-Carlo null for the max-stat A and the exceedance counts under
    H0 + ``kill_rule``. Returns dict with the null arrays and the realized survival
    summary."""
    if thresholds is None:
        thresholds = (1.0, 1.5, 2.0, 2.5, 3.0) if studentize else (5.0, 10.0, 15.0, 20.0)
    sim = _prepare_sim_inputs(calib)
    rng = np.random.default_rng(seed)

    null_A = np.full(n_sims, np.nan)
    null_exc = np.zeros((n_sims, len(thresholds)), dtype=int)
    surv_counts = np.zeros(n_sims, dtype=int)

    for k in range(n_sims):
        session_entries = [_simulate_session(rng, sim, s, kill_rule)
                           for s in sim.session_ids]
        surv_counts[k] = sum(len(e) for e in session_entries)
        A = _population_stat(session_entries, studentize, weighting)
        if A is not None:
            null_A[k] = A
        null_exc[k] = _exceedance_counts(session_entries, thresholds, studentize)

    return {
        'thresholds': list(thresholds),
        'null_A': null_A,
        'null_exc': null_exc,
        'mean_survivors': float(np.mean(surv_counts)),
        'studentize': studentize,
    }


# ---------------------------------------------------------------------------
# Pinned-count null (the one run_selection_test uses)
# ---------------------------------------------------------------------------
#
# run_selection_null above regenerates the whole attempt->kill->filter process, so
# the SURVIVOR COUNT changes with the kill threshold: a more aggressive threshold
# kills more, leaves fewer survivors, and the per-session max is taken over fewer
# conditions -> the null shrinks -> p drops. That p-vs-threshold trend is a count
# artifact, not a change in selection-bias strength, and it makes the comparison
# unfair: your observed max is over your REAL ~K survivors, so the null must use the
# same K (and the same per-survivor n's) or it is comparing different-sized maxima.
#
# This version pins the null to the real survivor structure: one simulated survivor
# per real survivor, with that survivor's own (n_on, n_off, p_off), differing from
# the observed only in that its outcomes are H0 + selection. The kill rule then acts
# ONLY by conditioning each survivor on having passed its early bar (reject-sample
# the decision window until interim effect >= threshold). The threshold now controls
# selection bias PER SURVIVOR -- the quantity we actually want to bound -- instead of
# secretly controlling how many survivors there are. Counts and n's match observed,
# so p rises with threshold (more bias = heavier null), the intuitive direction.

_MAX_REJECT_TRIES = 500


def _simulate_pinned_survivor(rng, n_on, n_off, p_off, decision_n, threshold):
    """One H0 survivor matched to a real survivor's (n_on, n_off, p_off), conditioned
    on passing the kill bar at decision_n. Returns an _Entry."""
    d = min(decision_n, n_on)
    # Reject-sample the decision window until the interim effect clears the bar
    # (this IS the selection: survivors are the early-lucky draws).
    on_dec = rng.random(d) < p_off
    for _ in range(_MAX_REJECT_TRIES):
        if 100.0 * (on_dec.mean() - p_off) >= threshold:
            break
        on_dec = rng.random(d) < p_off
    # Remaining ON trials are fresh H0 draws (the growth that dilutes the early luck).
    extra = n_on - d
    on_full = np.concatenate([on_dec, rng.random(extra) < p_off]) if extra > 0 else on_dec
    off = rng.random(n_off) < p_off
    effect = 100.0 * (on_full.mean() - off.mean())
    z = _studentize(effect, n_on, n_off, float(off.mean()))
    return _Entry(effect=effect, z=z, n_on=int(n_on), n_off=int(n_off))


def run_selection_null_pinned(calib, decision_n, threshold, n_sims=2000,
                              studentize=True, weighting=None, thresholds=None,
                              seed=0):
    """Selection-aware null with survivor count and per-survivor n's pinned to the
    real survivors. Each real survivor is replaced by an H0 survivor that passed the
    (decision_n, threshold) bar. Returns the same dict shape as run_selection_null."""
    if thresholds is None:
        thresholds = (1.0, 1.5, 2.0, 2.5, 3.0) if studentize else (5.0, 10.0, 15.0, 20.0)

    # Group the real survivors by session, keeping each one's (n_on, n_off, p_off).
    by_session = {}
    for c in calib.survivors:
        by_session.setdefault(c.session_id, []).append((c.n_on, c.n_off, c.p_off))

    rng = np.random.default_rng(seed)
    null_A = np.full(n_sims, np.nan)
    null_exc = np.zeros((n_sims, len(thresholds)), dtype=int)

    for k in range(n_sims):
        session_entries = []
        for survs in by_session.values():
            entries = [_simulate_pinned_survivor(rng, n_on, n_off, p_off,
                                                 decision_n, threshold)
                       for (n_on, n_off, p_off) in survs]
            session_entries.append(entries)
        A = _population_stat(session_entries, studentize, weighting)
        if A is not None:
            null_A[k] = A
        null_exc[k] = _exceedance_counts(session_entries, thresholds, studentize)

    return {
        'thresholds': list(thresholds),
        'null_A': null_A,
        'null_exc': null_exc,
        'mean_survivors': float(len(calib.survivors)),  # pinned, so constant
        'studentize': studentize,
    }


# ---------------------------------------------------------------------------
# Top-level test: observed vs selection-aware null, swept over the adversary grid
# ---------------------------------------------------------------------------

def run_selection_test(calib=None, decision_ns=(3, 4, 5, 6, 8),
                       thresholds_kill=(0.0, 5.0, 10.0, 15.0),
                       n_sims=2000, studentize=True, weighting=None,
                       exceedance_thresholds=None, seed=0, **calib_kwargs):
    """Compute the observed studentized max-stat and its selection-aware p-value
    across the adversary grid (decision_n x kill-threshold).

    Returns a dict with the observed statistic, a grid of selection-aware p-values,
    and the most adversarial cell.
    """
    if calib is None:
        calib = calibrate(**calib_kwargs)

    real_entries = list(_real_session_entries(calib).values())
    A_obs = _population_stat(real_entries, studentize, weighting)
    if A_obs is None:
        print("No real survivors; nothing to test.")
        return None

    if exceedance_thresholds is None:
        exceedance_thresholds = ((1.0, 1.5, 2.0, 2.5, 3.0) if studentize
                                 else (5.0, 10.0, 15.0, 20.0))
    exc_obs = _exceedance_counts(real_entries, exceedance_thresholds, studentize)

    unit = "z" if studentize else "%"
    print(f"\nObserved studentized max-stat A_obs = {A_obs:+.3f}{unit}")
    print(f"Observed exceedance counts {list(exceedance_thresholds)} = "
          f"{[int(c) for c in exc_obs]}")
    print(f"\nSelection-aware p-values (P[null A >= A_obs]) over adversary grid:")
    print(f"  rows = decision_n, cols = kill threshold (%)")
    header = "  n\\tau  " + "".join(f"{t:>8.0f}" for t in thresholds_kill)
    print(header)

    grid = np.full((len(decision_ns), len(thresholds_kill)), np.nan)
    # For each exceedance threshold, track the most adversarial (largest) p over the grid.
    exc_worst_p = np.full(len(exceedance_thresholds), -1.0)
    worst = {'p': -1.0}
    for i, d_n in enumerate(decision_ns):
        cells = []
        for j, tau in enumerate(thresholds_kill):
            res = run_selection_null_pinned(calib, decision_n=d_n, threshold=tau,
                                            n_sims=n_sims, studentize=studentize,
                                            weighting=weighting,
                                            thresholds=exceedance_thresholds, seed=seed)
            valid = res['null_A'][~np.isnan(res['null_A'])]
            p = float(np.mean(valid >= A_obs)) if valid.size else float('nan')
            grid[i, j] = p
            cells.append(p)
            # exceedance selection-aware p at this cell, per threshold
            for t_idx in range(len(exceedance_thresholds)):
                pe = float(np.mean(res['null_exc'][:, t_idx] >= exc_obs[t_idx]))
                exc_worst_p[t_idx] = max(exc_worst_p[t_idx], pe)
            if p > worst['p']:
                worst = {'p': p, 'decision_n': d_n, 'threshold': tau,
                         'result': res}
        print(f"  {d_n:>3}   " + "".join(f"{p:>8.3f}" for p in cells))

    print(f"\nMost adversarial cell (max-stat): decision_n={worst['decision_n']}, "
          f"kill threshold={worst['threshold']:+.0f}%  ->  "
          f"selection-aware p = {worst['p']:.3f}")
    if worst['p'] < 0.05:
        print("  => observed max-stat beats even the worst-case realistic selection (p<0.05).")
    else:
        print("  => observed max-stat is NOT robust to worst-case realistic selection.")

    print(f"\nExceedance counts vs selection null (worst-case p over the grid):")
    for t, n_obs, pe in zip(exceedance_thresholds, exc_obs, exc_worst_p):
        flag = "robust" if pe < 0.05 else "NOT robust"
        print(f"  effect >= {t:.1f}{unit}:  observed={int(n_obs):3d}   "
              f"worst-case selection p = {pe:.3f}  ({flag})")

    return {
        'A_obs': A_obs,
        'exc_obs': exc_obs,
        'exc_worst_p': exc_worst_p,
        'exceedance_thresholds': list(exceedance_thresholds),
        'decision_ns': list(decision_ns),
        'thresholds_kill': list(thresholds_kill),
        'p_grid': grid,
        'worst': worst,
        'studentize': studentize,
        'unit': unit,
    }


def plot_selection_test(test, save_path=None):
    """Heatmap of selection-aware p over the adversary grid, plus the worst-case
    null vs the observed statistic."""
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    ax = axes[0]
    grid = test['p_grid']
    im = ax.imshow(grid, aspect='auto', cmap='RdYlGn_r', vmin=0, vmax=0.2,
                   origin='upper')
    ax.set_xticks(range(len(test['thresholds_kill'])))
    ax.set_xticklabels([f"{t:+.0f}%" for t in test['thresholds_kill']])
    ax.set_yticks(range(len(test['decision_ns'])))
    ax.set_yticklabels(test['decision_ns'])
    ax.set_xlabel("kill threshold (interim effect)")
    ax.set_ylabel("decision_n")
    ax.set_title("Selection-aware p-value\n(P[null max-stat >= observed]; green = robust)")
    for i in range(grid.shape[0]):
        for j in range(grid.shape[1]):
            ax.text(j, i, f"{grid[i, j]:.3f}", ha="center", va="center", fontsize=8)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    ax = axes[1]
    worst = test['worst']
    null_A = worst['result']['null_A']
    null_A = null_A[~np.isnan(null_A)]
    ax.hist(null_A, bins=40, color="gray", alpha=0.7, label="selection null (worst case)")
    ax.axvline(test['A_obs'], color="red", linewidth=2,
               label=f"observed = {test['A_obs']:+.2f}{test['unit']}")
    ax.axvline(np.percentile(null_A, 95), color="black", linestyle="--", linewidth=1,
               label="null 95th pct")
    ax.set_xlabel(f"max-stat A ({test['unit']})")
    ax.set_ylabel("# simulated experiments")
    ax.set_title(f"Worst-case adversary: kill@n={worst['decision_n']} "
                 f"if effect<{worst['threshold']:+.0f}%  (p={worst['p']:.3f})")
    ax.legend(fontsize=8)

    fig.tight_layout()
    if save_path:
        import os
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        fig.savefig(save_path, bbox_inches="tight", dpi=150)
        print(f"Saved to {save_path}")
    plt.show()
    return fig


def main():
    # Mirror max_estim_per_experiment.main() session selection.
    metric = METRIC_PCT_HYP_VS_DELTA
    exclude_session_ids = ["260421_0", "260410_0"]
    start_session_id = "260402_0"
    algorithm_label = 'None'

    calib = calibrate(
        exclude_session_ids=exclude_session_ids,
        start_session_id=start_session_id,
        algorithm_label=algorithm_label,
        metric=metric,
        min_trials=10,
    )

    test = run_selection_test(
        calib=calib,
        decision_ns=(3, 4, 5, 6, 8),       # bounded to the realistic kill range
        thresholds_kill=(0.0, 5.0, 10.0, 15.0),
        n_sims=2000,
        studentize=True,                    # match max_estim_per_experiment.main()
        weighting=None,                     # unweighted, like the default headline
    )
    if test is not None:
        plot_selection_test(
            test,
            save_path="/home/connorlab/Documents/plots/across_experiments/selection_aware_test.png",
        )


if __name__ == "__main__":
    main()
