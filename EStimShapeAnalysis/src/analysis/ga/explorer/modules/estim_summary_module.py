"""
EStim results summary for this session. Every plot is drawn side by side in
one figure; tick "Show ..." to choose which are on screen.
  - Effect histogram: every EStim condition's effect size, with the max EStim
    effect written on the figure.
  - Effect vs parameter fitness: one dot per condition, its effect size (y)
    against the EStim parameter fitness of its spec (x).

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

EStim parameter fitness (higher = fitter, 1 = best), from the distance used by
avg_estim_per_experiment's 'closest' rule:
  fitness  = 1 / (1 + distance)          in (0, 1]; same ranking as the distance
  distance = |ratio - center|
  ratio   = current_per_second / correlation half-distance  ((µA·Hz) / µm), per spec
  center  = ESTIM_DISTANCE_CENTERS[condition's trial type]
            (Hypothesized Shape 4.0, Delta Shape 0.0)
  - current_per_second = a1 × active channels × pulse rate (estim_hyperparameters)
  - half-distance: distance from the estim channels at which the channel
    correlation falls halfway from its near-field level to its far-field
    baseline (plot_current_spread_vs_tuning.compute_session_half_distance),
    with Spearman or Pearson correlations ("Correlation").
  The ratio comes from estim_condition_table._fetch_spread (same numbers as
  avg_estim_per_experiment.get_spec_ratios). Conditions whose trial type has
  no center, or whose spec has no ratio, are left out of the scatter (count
  in the status bar, with the Spearman correlation of effect vs fitness).

Nothing is written to any database.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.analysis.ga.explorer.explorer_module import FigureModule, Param

METRICS = ["pct_hyp_vs_delta", "pct_hypothesized"]
CORR_METHODS = ["spearman", "pearson"]
FITNESS_LABEL = "EStim parameter fitness"
PANEL_SIZE = (6.0, 4.6)  # inches per plot
# Fitness scatter dot color per trial type (others fall back to FALLBACK_COLORS).
TRIAL_TYPE_COLORS = {"Hypothesized Shape": "#c0392b", "Delta Shape": "#2c7fb8"}
FALLBACK_COLORS = ["#27ae60", "#8e44ad", "#e67e22", "#555555"]


def condition_effects(session_id, algorithm_label, metric, min_trials, studentize):
    """(effects, null_matrix, conds) for the session's qualifying conditions,
    in % or z units. null_matrix is (conditions, permutations) in the same
    units; conds[i] is condition i's condition dict (estim_spec_id, trial_type, ...)."""
    from src.analysis.nafc.group_analysis.max_estim_per_experiment import \
        _load_qualifying_conditions
    entries = _load_qualifying_conditions(session_id, algorithm_label, metric,
                                          min_trials=min_trials)
    if not entries:
        return np.array([]), None, []
    n_perms = min(len(e["null"]) for e in entries)
    effects, nulls, conds = [], [], []
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
        conds.append(e.get("cond_dict") or {})
    if not effects:
        return np.array([]), None, []
    return np.asarray(effects), np.stack(nulls), conds


def spec_ratios(session, corr_method):
    """{estim_spec_id: current_per_second / half-distance, or None}, cached
    per session (the half-distance needs the session's channel responses)."""
    def load():
        from src.analysis.nafc.group_analysis.estim_condition_table import _fetch_spread
        spread = _fetch_spread([session.session_id], corr_method=corr_method)
        return {int(r.estim_spec_id): (None if r.ratio is None or pd.isna(r.ratio)
                                       else float(r.ratio))
                for r in spread.itertuples(index=False)}
    return session.get_or_load(("estim_spec_ratio", corr_method), load)


def condition_fitness(cond, ratios, centers):
    """1 / (1 + |ratio - center|) for one condition (1 = at the center), or
    None (trial type without a center, no spec, or no ratio for its spec)."""
    center = centers.get(cond.get("trial_type"))
    spec = cond.get("estim_spec_id")
    if center is None or spec is None or (isinstance(spec, float) and np.isnan(spec)):
        return None
    ratio = ratios.get(int(spec))
    return None if ratio is None else 1.0 / (1.0 + abs(ratio - center))


def _fmt_p(p):
    if p < 0.001:
        return "p < 0.001"
    return f"p = {p:.3f}" if p < 0.01 else f"p = {p:.2f}"


class EStimSummaryModule(FigureModule):
    name = "EStim results summary"
    description = ("EStim conditions of this session: histogram of effect sizes with "
                   "the max EStim effect, and effect vs EStim parameter fitness "
                   "(1 = best). Tick which to show.")

    def params(self):
        return [
            Param("sec_all", "All plots", "header", None),
            Param("metric", "Metric", "choice", "pct_hyp_vs_delta", choices=METRICS,
                  tooltip="EStimPermutationTests metric."),
            Param("algorithm_label", "Cutoff algorithm", "str", "none",
                  tooltip="EStimPermutationTests algorithm_label; 'none' = all trials."),
            Param("min_trials", "Min trials per group", "int", 10, minimum=1, maximum=1000,
                  tooltip="Conditions need at least this many EStim ON and OFF trials."),
            Param("studentize", "Studentize (z units)", "bool", True,
                  tooltip="Standardize each condition's effect by its own permutation null."),

            Param("sec_hist", "Effect histogram", "header", None),
            Param("show_histogram", "Show", "bool", True, live=True),
            Param("bins", "Bins", "int", 20, minimum=3, maximum=200),
            Param("show_null", "Chance outline", "bool", True,
                  tooltip="Expected count per bin with no EStim effect (permutation null)."),

            Param("sec_fit", "Effect vs parameter fitness", "header", None),
            Param("show_fitness", "Show", "bool", True, live=True),
            Param("corr_method", "Half-distance correlation", "choice", "spearman",
                  choices=CORR_METHODS,
                  tooltip="Channel correlation used for the half-distance in the "
                          "parameter fitness."),
            Param("fit_line", "Regression line", "bool", True, live=True,
                  tooltip="Least-squares line of effect on fitness, over all dots "
                          "(slope, r² and p in the status bar)."),
        ]

    def make_figure(self, session, values):
        from matplotlib.figure import Figure

        panels = [name for name, key in (("histogram", "show_histogram"),
                                         ("fitness", "show_fitness"))
                  if values.get(key, True)]
        if not panels:
            self.status("Tick a plot to show.")
            return None
        studentize = values["studentize"]
        label = values["algorithm_label"].strip() or "none"
        effects, null_matrix, conds = condition_effects(
            session.session_id, label, values["metric"], values["min_trials"], studentize)
        if effects.size == 0:
            self.status(f"No EStim conditions for {session.session_id} with metric "
                        f"{values['metric']}, cutoff '{label}' and at least "
                        f"{values['min_trials']} trials per group.")
            return None

        w, h = PANEL_SIZE
        fig = Figure(figsize=(w * len(panels), h))
        axes = fig.subplots(1, len(panels), squeeze=False)[0]
        notes = []
        for ax, panel in zip(axes, panels):
            if panel == "histogram":
                notes.append(self._draw_histogram(ax, session, values, effects,
                                                  null_matrix, label))
            else:
                notes.append(self._draw_fitness(ax, session, values, effects, conds))
        fig.tight_layout()
        self.status("  |  ".join(n for n in notes if n))
        return fig

    def create_view(self, parent):
        # Whole figure scaled to the window (all plots visible, layout kept).
        from src.analysis.ga.explorer.figure_view import FigureView
        self._view = FigureView(parent, keep_size=True, fit_height=True, fit_width=True)
        return self._view

    @staticmethod
    def _effect_label(studentize):
        return ("EStim effect (z, studentized)" if studentize
                else "EStim effect (% points, ON − OFF)")

    @staticmethod
    def _style(ax, title):
        ax.set_title(title, fontsize=16)
        ax.tick_params(labelsize=13)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)

    def _draw_fitness(self, ax, session, values, effects, conds):
        from scipy.stats import linregress, spearmanr
        from src.analysis.nafc.group_analysis.avg_estim_per_experiment import \
            ESTIM_DISTANCE_CENTERS

        self._style(ax, "EStim effect vs parameter fitness")
        ax.set_xlabel(FITNESS_LABEL, fontsize=15)
        ax.set_ylabel(self._effect_label(values["studentize"]), fontsize=15)
        try:
            ratios = spec_ratios(session, values["corr_method"])
        except Exception as exc:
            # Keep the other plots; say loudly why this one is empty.
            msg = f"Fitness failed: {type(exc).__name__}: {exc}"
            ax.text(0.5, 0.5, msg, ha="center", va="center", transform=ax.transAxes,
                    fontsize=12, color="#c0392b", wrap=True)
            return msg
        x = np.array([np.nan if (f := condition_fitness(c, ratios, ESTIM_DISTANCE_CENTERS))
                      is None else f for c in conds], dtype=float)
        keep = np.isfinite(x)
        n_missing = int((~keep).sum())
        if not keep.any():
            ax.text(0.5, 0.5, "No parameter fitness for these conditions", ha="center",
                    va="center", transform=ax.transAxes, fontsize=14, color="gray")
            return (f"fitness: none of {effects.size} conditions has a fitness (needs "
                    "Hypothesized/Delta trial type and current / half-distance)")
        types = np.array([c.get("trial_type") for c in conds], dtype=object)[keep]
        x, y = x[keep], effects[keep]
        ax.axhline(0, color="black", linewidth=1, zorder=1)
        # One color per trial type, in ESTIM_DISTANCE_CENTERS order.
        present = [t for t in ESTIM_DISTANCE_CENTERS if t in set(types)]
        fallback = iter(FALLBACK_COLORS * 4)
        for tt in present:
            on = types == tt
            ax.scatter(x[on], y[on], color=TRIAL_TYPE_COLORS.get(tt) or next(fallback),
                       s=60, alpha=0.8, zorder=3, label=tt)

        stats = ""
        if len(x) >= 3 and np.ptp(x) > 0:
            rho, p = spearmanr(x, y)
            stats = f", Spearman ρ = {rho:+.2f} ({_fmt_p(p)})"
            if values.get("fit_line", True):
                fit = linregress(x, y)
                xs = np.linspace(0, 1.03, 100)
                ax.plot(xs, fit.slope * xs + fit.intercept, color="black", linewidth=1.8,
                        zorder=2, label="Linear fit")
                stats += (f", fit slope {fit.slope:+.2f}, r² = {fit.rvalue ** 2:.2f} "
                          f"({_fmt_p(fit.pvalue)})")
        ax.legend(fontsize=12, frameon=False, loc="best")
        ax.set_xlim(0, 1.03)  # fitness is in (0, 1]
        return (f"fitness: {len(x)} conditions{stats}"
                + (f", {n_missing} without a fitness left out" if n_missing else "")
                + f", half-distance from {values['corr_method']}")

    def _draw_histogram(self, ax, session, values, effects, null_matrix, label):
        from src.analysis.nafc.group_analysis.max_estim_per_experiment import \
            _build_max_stat_for_session

        studentize = values["studentize"]
        best = _build_max_stat_for_session(session.session_id, label, values["metric"],
                                           min_trials=values["min_trials"],
                                           studentize=studentize)

        unit = "z" if studentize else "%"
        lo = min(effects.min(), 0.0)
        hi = max(effects.max(), 0.0)
        if null_matrix is not None and values["show_null"]:
            lo = min(lo, float(np.percentile(null_matrix, 0.5)))
            hi = max(hi, float(np.percentile(null_matrix, 99.5)))
        edges = np.linspace(lo, hi, values["bins"] + 1)

        ax.hist(effects, bins=edges, color="#c0392b", edgecolor="white", linewidth=0.8,
                label="Conditions")
        if null_matrix is not None and values["show_null"]:
            # Expected count per bin under the null = mean over permutations.
            per_perm = np.stack([np.histogram(null_matrix[:, k], bins=edges)[0]
                                 for k in range(null_matrix.shape[1])])
            expected = per_perm.mean(axis=0)
            ax.stairs(expected, edges, color="#555555", linewidth=2, label="Chance")
            ax.legend(fontsize=12, frameon=False, loc="upper left")
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
                    fontsize=13, bbox=dict(boxstyle="round,pad=0.4", facecolor="white",
                                           edgecolor="#cccccc"))

        # Headroom above the bars for the legend and the max-effect box.
        ax.set_ylim(0, ax.get_ylim()[1] * 1.35)
        ax.set_xlabel(self._effect_label(studentize), fontsize=15)
        ax.set_ylabel("Conditions", fontsize=15)
        self._style(ax, "EStim effects")
        ax.yaxis.get_major_locator().set_params(integer=True)
        return (f"{effects.size} conditions, metric {values['metric']}, cutoff '{label}', "
                f"max {effects.max():.2f}{unit}")
