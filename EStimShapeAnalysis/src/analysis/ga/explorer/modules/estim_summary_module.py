"""
EStim results summary: histogram of every EStim condition's effect size in
this session, with the max EStim effect written on the figure.

Data and statistics come from max_estim_per_experiment (read-only):
  - Conditions: EStimPermutationTests rows for this session, metric and
    cutoff algorithm, with at least `min_trials` trials in BOTH the EStim ON
    and OFF groups (_load_qualifying_conditions).
  - Effect size: observed_effect_size (EStim ON minus OFF, percentage
    points). With "Studentize" on, each condition's effect is standardized by
    its own permutation null, z = (effect - mean(null)) / sd(null), as in
    max_estim_per_experiment's studentized tests.
  - Max EStim effect: the best (most positive) condition and its max-stat
    permutation p-value (_build_max_stat_for_session): p = fraction of
    permutations whose max across conditions >= the observed max.
  - Chance outline (optional): expected count per bin if EStim had no
    effect, i.e. each bin's count averaged over the permutations
    (the same null the exceedance-count test uses).

Nothing is written to any database.
"""

from __future__ import annotations

import numpy as np

from src.analysis.ga.explorer.explorer_module import FigureModule, Param

METRICS = ["pct_hyp_vs_delta", "pct_hypothesized"]


def condition_effects(session_id, algorithm_label, metric, min_trials, studentize):
    """(effects, null_matrix) for the session's qualifying conditions, in %
    or z units. null_matrix is (conditions, permutations) in the same units."""
    from src.analysis.nafc.group_analysis.max_estim_per_experiment import \
        _load_qualifying_conditions
    entries = _load_qualifying_conditions(session_id, algorithm_label, metric,
                                          min_trials=min_trials)
    if not entries:
        return np.array([]), None
    n_perms = min(len(e["null"]) for e in entries)
    effects, nulls = [], []
    for e in entries:
        null = np.asarray(e["null"][:n_perms], dtype=float)
        if studentize:
            mu, sd = float(np.mean(null)), float(np.std(null, ddof=1))
            if not np.isfinite(sd) or sd <= 0:
                continue  # degenerate null, dropped as in max_estim_per_experiment
            effects.append((e["obs_effect"] - mu) / sd)
            nulls.append((null - mu) / sd)
        else:
            effects.append(float(e["obs_effect"]))
            nulls.append(null)
    if not effects:
        return np.array([]), None
    return np.asarray(effects), np.stack(nulls)


def _fmt_p(p):
    if p < 0.001:
        return "p < 0.001"
    return f"p = {p:.3f}" if p < 0.01 else f"p = {p:.2f}"


class EStimSummaryModule(FigureModule):
    name = "EStim results summary"
    description = ("Histogram of the effect size of every EStim condition in this "
                   "session, with the max EStim effect.")

    def params(self):
        return [
            Param("metric", "Metric", "choice", "pct_hyp_vs_delta", choices=METRICS,
                  tooltip="EStimPermutationTests metric."),
            Param("algorithm_label", "Cutoff algorithm", "str", "none",
                  tooltip="EStimPermutationTests algorithm_label; 'none' = all trials."),
            Param("min_trials", "Min trials per group", "int", 10, minimum=1, maximum=1000,
                  tooltip="Conditions need at least this many EStim ON and OFF trials."),
            Param("studentize", "Studentize (z units)", "bool", True,
                  tooltip="Standardize each condition's effect by its own permutation null."),
            Param("bins", "Bins", "int", 20, minimum=3, maximum=200),
            Param("show_null", "Show chance outline", "bool", True,
                  tooltip="Expected count per bin with no EStim effect (permutation null)."),
        ]

    def make_figure(self, session, values):
        from matplotlib.figure import Figure
        from src.analysis.nafc.group_analysis.max_estim_per_experiment import \
            _build_max_stat_for_session

        studentize = values["studentize"]
        label = values["algorithm_label"].strip() or "none"
        effects, null_matrix = condition_effects(
            session.session_id, label, values["metric"], values["min_trials"], studentize)
        if effects.size == 0:
            self.status(f"No EStim conditions for {session.session_id} with metric "
                        f"{values['metric']}, cutoff '{label}' and at least "
                        f"{values['min_trials']} trials per group.")
            return None
        best = _build_max_stat_for_session(session.session_id, label, values["metric"],
                                           min_trials=values["min_trials"],
                                           studentize=studentize)

        unit = "z" if studentize else "%"
        xlabel = ("EStim effect (z, studentized)" if studentize
                  else "EStim effect (% points, ON − OFF)")
        lo = min(effects.min(), 0.0)
        hi = max(effects.max(), 0.0)
        if null_matrix is not None and values["show_null"]:
            lo = min(lo, float(np.percentile(null_matrix, 0.5)))
            hi = max(hi, float(np.percentile(null_matrix, 99.5)))
        edges = np.linspace(lo, hi, values["bins"] + 1)

        fig = Figure(figsize=(9, 6))
        ax = fig.add_subplot(111)
        ax.hist(effects, bins=edges, color="#c0392b", edgecolor="white", linewidth=0.8,
                label="Conditions")
        if null_matrix is not None and values["show_null"]:
            # Expected count per bin under the null = mean over permutations.
            per_perm = np.stack([np.histogram(null_matrix[:, k], bins=edges)[0]
                                 for k in range(null_matrix.shape[1])])
            expected = per_perm.mean(axis=0)
            ax.stairs(expected, edges, color="#555555", linewidth=2, label="Chance")
            ax.legend(fontsize=13, frameon=False, loc="upper left")
        ax.axvline(0, color="black", linewidth=1)

        if best is not None:
            top = best["observed_signed"]
            ax.axvline(top, ymax=0.8, color="#c0392b", linestyle="--", linewidth=1.5)
            if studentize:
                text = (f"Max EStim effect: z = {top:.2f}  ({best['observed_raw']:+.1f}%)\n"
                        f"max-stat {_fmt_p(best['p_value'])}")
            else:
                text = f"Max EStim effect: {top:+.1f}%\nmax-stat {_fmt_p(best['p_value'])}"
            ax.text(0.98, 0.97, text, transform=ax.transAxes, ha="right", va="top",
                    fontsize=14, bbox=dict(boxstyle="round,pad=0.4", facecolor="white",
                                           edgecolor="#cccccc"))

        ax.set_xlabel(xlabel, fontsize=15)
        ax.set_ylabel("Conditions", fontsize=15)
        ax.set_title("EStim effects", fontsize=16)
        ax.tick_params(labelsize=13)
        ax.yaxis.get_major_locator().set_params(integer=True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        fig.tight_layout()
        self.status(f"{effects.size} conditions, metric {values['metric']}, cutoff '{label}', "
                    f"max {effects.max():.2f}{unit}")
        return fig
