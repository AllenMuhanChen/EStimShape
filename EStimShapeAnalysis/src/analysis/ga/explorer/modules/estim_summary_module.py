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
# Trial-type filter (applies to every plot). "Other" = any other trial type, or
# conditions without one.
TRIAL_TYPES = ["Hypothesized Shape", "Delta Shape", "Removed Trial", "Coherence"]
OTHER_TRIAL_TYPE = "Other"
STATS_BOX_WIDTH = 1.9  # inches, linear-fit stats box right of the fitness plot


def _tt_key(trial_type):
    return "tt_" + trial_type.lower().replace(" ", "_")


def shown_trial_types(values):
    """Ticked trial types (OTHER_TRIAL_TYPE stands for everything not listed)."""
    return {tt for tt in TRIAL_TYPES + [OTHER_TRIAL_TYPE] if values.get(_tt_key(tt), True)}


def keep_condition(cond, shown):
    tt = cond.get("trial_type")
    return (tt in shown) if tt in TRIAL_TYPES else (OTHER_TRIAL_TYPE in shown)


def max_stat(effects, raws, null_matrix):
    """Max-stat test over the given conditions, as
    max_estim_per_experiment._build_max_stat_for_session (direction 'max'):
    best = largest effect; null = per-permutation max across conditions;
    p = fraction of null maxima >= the observed max."""
    best = int(np.argmax(effects))
    null_max = null_matrix.max(axis=0)
    observed = float(effects[best])
    return {"observed_signed": observed, "observed_raw": float(raws[best]),
            "p_value": float(np.mean(null_max >= observed))}


def condition_effects(session_id, algorithm_label, metric, min_trials, studentize):
    """(effects, null_matrix, conds, raws) for the session's qualifying
    conditions, in % or z units. null_matrix is (conditions, permutations) in
    the same units; conds[i] is condition i's condition dict (estim_spec_id,
    trial_type, ...); raws[i] its effect in % points."""
    from src.analysis.nafc.group_analysis.max_estim_per_experiment import \
        _load_qualifying_conditions
    entries = _load_qualifying_conditions(session_id, algorithm_label, metric,
                                          min_trials=min_trials)
    if not entries:
        return np.array([]), None, [], np.array([])
    effects, nulls, conds, raws = [], [], [], []
    for e in entries:
        null = np.asarray(e["null"], dtype=float)
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
        raws.append(float(e["obs_effect"]))
    if not effects:
        return np.array([]), None, [], np.array([])
    # Align permutation counts (rows written at different times), as max_estim does.
    n_perms = min(len(n) for n in nulls)
    return (np.asarray(effects), np.stack([n[:n_perms] for n in nulls]), conds,
            np.asarray(raws))


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
            *[Param(_tt_key(tt), f"Show {tt}", "bool", True,
                    tooltip="Include this trial type's conditions in every plot."
                    + (" (any trial type not listed above, or none)"
                       if tt == OTHER_TRIAL_TYPE else ""))
              for tt in TRIAL_TYPES + [OTHER_TRIAL_TYPE]],

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
                  tooltip="Least-squares line of effect on fitness, over all dots, "
                          "with its stats in a box right of the plot."),
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
        effects, null_matrix, conds, raws = condition_effects(
            session.session_id, label, values["metric"], values["min_trials"], studentize)
        if effects.size == 0:
            self.status(f"No EStim conditions for {session.session_id} with metric "
                        f"{values['metric']}, cutoff '{label}' and at least "
                        f"{values['min_trials']} trials per group.")
            return None
        shown = shown_trial_types(values)
        keep = np.array([keep_condition(c, shown) for c in conds], dtype=bool)
        if not keep.any():
            self.status(f"None of the {effects.size} conditions is of a ticked trial type.")
            return None
        effects, null_matrix, raws = effects[keep], null_matrix[keep], raws[keep]
        conds = [c for c, k in zip(conds, keep) if k]

        fitness = self._fitness_data(session, values, effects, conds) \
            if "fitness" in panels else None
        fit_box = fitness is not None and fitness.get("fit") is not None

        w, h = PANEL_SIZE
        ratios = [w] * len(panels) + ([STATS_BOX_WIDTH] if fit_box else [])
        fig = Figure(figsize=(sum(ratios), h))
        grid = fig.add_gridspec(1, len(ratios), width_ratios=ratios)
        notes = []
        for i, panel in enumerate(panels):
            ax = fig.add_subplot(grid[0, i])
            if panel == "histogram":
                notes.append(self._draw_histogram(ax, values, effects, null_matrix, raws,
                                                  label))
            else:
                notes.append(self._draw_fitness(ax, values, fitness))
        if fit_box:
            self._draw_fit_box(fig.add_subplot(grid[0, len(panels)]), fitness)
        fig.tight_layout()
        hidden = [tt for tt in TRIAL_TYPES + [OTHER_TRIAL_TYPE] if tt not in shown]
        if hidden:
            notes.append("hidden: " + ", ".join(hidden))
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

    def _fitness_data(self, session, values, effects, conds):
        """Everything the fitness scatter needs: dict with 'x', 'y', 'types',
        'n_missing', 'fit' (linregress result or None), 'rho', 'p_rho', or with
        'error' / 'empty' set when there is nothing to plot."""
        from scipy.stats import linregress, spearmanr
        from src.analysis.nafc.group_analysis.avg_estim_per_experiment import \
            ESTIM_DISTANCE_CENTERS

        try:
            ratios = spec_ratios(session, values["corr_method"])
        except Exception as exc:
            return {"error": f"Fitness failed: {type(exc).__name__}: {exc}"}
        x = np.array([np.nan if (f := condition_fitness(c, ratios, ESTIM_DISTANCE_CENTERS))
                      is None else f for c in conds], dtype=float)
        keep = np.isfinite(x)
        out = {"n_missing": int((~keep).sum()), "n_total": int(len(x)),
               "corr_method": values["corr_method"], "fit": None, "rho": None,
               "order": list(ESTIM_DISTANCE_CENTERS)}
        if not keep.any():
            out["empty"] = True
            return out
        out["types"] = np.array([c.get("trial_type") for c in conds], dtype=object)[keep]
        out["x"], out["y"] = x[keep], effects[keep]
        if len(out["x"]) >= 3 and np.ptp(out["x"]) > 0:
            out["rho"], out["p_rho"] = spearmanr(out["x"], out["y"])
            if values.get("fit_line", True):
                out["fit"] = linregress(out["x"], out["y"])
        return out

    def _draw_fitness(self, ax, values, d):
        self._style(ax, "EStim effect vs parameter fitness")
        ax.set_xlabel(FITNESS_LABEL, fontsize=15)
        ax.set_ylabel(self._effect_label(values["studentize"]), fontsize=15)
        if "error" in d:
            # Keep the other plots; say loudly why this one is empty.
            ax.text(0.5, 0.5, d["error"], ha="center", va="center", transform=ax.transAxes,
                    fontsize=12, color="#c0392b", wrap=True)
            return d["error"]
        if d.get("empty"):
            ax.text(0.5, 0.5, "No parameter fitness for these conditions", ha="center",
                    va="center", transform=ax.transAxes, fontsize=14, color="gray")
            return (f"fitness: none of {d['n_total']} conditions has a fitness (needs "
                    "Hypothesized/Delta trial type and current / half-distance)")
        x, y, types = d["x"], d["y"], d["types"]
        ax.axhline(0, color="black", linewidth=1, zorder=1)
        # One color per trial type, in ESTIM_DISTANCE_CENTERS order.
        fallback = iter(FALLBACK_COLORS * 4)
        for tt in [t for t in d["order"] if t in set(types)]:
            on = types == tt
            ax.scatter(x[on], y[on], color=TRIAL_TYPE_COLORS.get(tt) or next(fallback),
                       s=60, alpha=0.8, zorder=3, label=tt)
        if d["fit"] is not None:
            xs = np.linspace(0, 1.03, 100)
            ax.plot(xs, d["fit"].slope * xs + d["fit"].intercept, color="black",
                    linewidth=1.8, zorder=2, label="Linear fit")
        ax.legend(fontsize=12, frameon=False, loc="lower right")
        ax.set_xlim(0, 1.03)  # fitness is in (0, 1]
        stats = (f", Spearman ρ = {d['rho']:+.2f} ({_fmt_p(d['p_rho'])})"
                 if d["rho"] is not None else "")
        return (f"fitness: {len(x)} conditions{stats}"
                + (f", {d['n_missing']} without a fitness left out" if d["n_missing"] else "")
                + f", half-distance from {d['corr_method']}")

    @staticmethod
    def _draw_fit_box(ax, d):
        """Linear-fit stats in a box beside (not inside) the fitness plot."""
        ax.axis("off")
        fit = d["fit"]
        text = (f"Linear fit\n"
                f"slope = {fit.slope:+.2f}\n"
                f"r² = {fit.rvalue ** 2:.2f}\n"
                f"{_fmt_p(fit.pvalue)}\n"
                f"n = {len(d['x'])}")
        ax.text(0.0, 0.5, text, transform=ax.transAxes, ha="left", va="center",
                fontsize=13, linespacing=1.5,
                bbox=dict(boxstyle="round,pad=0.5", facecolor="white", edgecolor="#cccccc"))

    def _draw_histogram(self, ax, values, effects, null_matrix, raws, label):
        studentize = values["studentize"]
        # Max-stat over the shown conditions only (trial-type filter applied).
        best = max_stat(effects, raws, null_matrix)

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
