"""
Solid preference index (SPI) for this session's 2D vs 3D side test.

Scatter as side_test.TwoDvsThreeDScatterPlotter: one dot per tested shape
(TestId), mean 2D response (x) vs mean 3D response (y), identity line and a
least-squares fit. The SPI and its significance are written on the plot.

  SPI = (sum of 3D trial responses - sum of 2D trial responses)
        / max(the two sums)                  (as solid_preference_index.py)
  p   = two-tailed permutation test (as solid_preference_permutation_test.py):
        shuffle the 2D/3D labels across trials n_perm times, recompute the
        SPI each time, p = fraction with |SPI_null| >= |SPI|.

Responses: by default the GA channels (channel "Cluster") summed per trial,
from the repository table 2Dvs3DStimInfo. Read-only.
"""

from __future__ import annotations

import numpy as np

from src.analysis.ga.explorer.explorer_module import FigureModule, Param
from src.analysis.ga.explorer.ga_data import (DATA_TYPES, load_side_test_data,
                                              parse_channel)


def solid_preference_index(resp_3d, resp_2d) -> float:
    total_3d, total_2d = float(np.sum(resp_3d)), float(np.sum(resp_2d))
    denom = max(total_3d, total_2d)
    return 0.0 if denom == 0 else (total_3d - total_2d) / denom


def spi_permutation_test(resp_3d, resp_2d, n_perm=10000, seed=None):
    """(spi, p, null): two-tailed label-shuffle test of the SPI."""
    resp_3d, resp_2d = np.asarray(resp_3d, float), np.asarray(resp_2d, float)
    spi = solid_preference_index(resp_3d, resp_2d)
    pooled = np.concatenate([resp_3d, resp_2d])
    n_3d, total = len(resp_3d), pooled.sum()
    rng = np.random.default_rng(seed)
    null = np.empty(n_perm)
    chunk = 1000
    for start in range(0, n_perm, chunk):
        k = min(chunk, n_perm - start)
        # Each row a random permutation; the first n_3d go to "3D".
        idx = np.argsort(rng.random((k, pooled.size)), axis=1)[:, :n_3d]
        sum_3d = pooled[idx].sum(axis=1)
        sum_2d = total - sum_3d
        denom = np.maximum(sum_3d, sum_2d)
        with np.errstate(invalid="ignore", divide="ignore"):
            null[start:start + k] = np.where(denom == 0, 0.0, (sum_3d - sum_2d) / denom)
    p = float(np.mean(np.abs(null) >= abs(spi)))
    return spi, p, null


def _fmt_p(p, n_perm=None):
    """``n_perm``: for a permutation p of 0, report the resolution limit."""
    if n_perm and p == 0:
        return f"p < {1 / n_perm:g}"
    if p < 0.001:
        return "p < 0.001"
    return f"p = {p:.3f}" if p < 0.01 else f"p = {p:.2f}"


class SolidPreferenceModule(FigureModule):
    name = "Solid preference index"
    description = ("2D vs 3D side test: mean response per shape (2D vs 3D) with the "
                   "solid preference index and its permutation p-value.")

    def params(self):
        return [
            Param("data_type", "Data type", "choice", "mua", choices=DATA_TYPES,
                  tooltip="Which responses to import. 'GA' = the GA's own per-stim "
                          "response (no per-trial rates)."),
            Param("channel", "Channel", "str", "Cluster",
                  tooltip='"Cluster" = the GA channels, summed per trial. Or "A-006", '
                          'or "A-000,A-006" (summed).'),
            Param("n_perm", "Permutations", "int", 10000, minimum=100, maximum=1000000,
                  step=1000),
            Param("alpha", "Significance level", "float", 0.05, minimum=0.0001,
                  maximum=0.5, step=0.01, decimals=4),
            Param("fit_line", "Regression line", "bool", True,
                  tooltip="Least-squares fit of 3D on 2D, with slope, r² and p."),
        ]

    def make_figure(self, session, values):
        from matplotlib.figure import Figure
        from scipy.stats import linregress
        from src.analysis.ga.response_spec import ResponseSpec

        data_type = values["data_type"]
        channel = "GA" if data_type == "GA" else parse_channel(values["channel"])
        if not channel:
            self.status("Enter a channel.")
            return None
        compiled, spike_rates_col = load_side_test_data(session, data_type)
        if compiled is None or compiled.empty or "TestType" not in compiled.columns:
            self.status(f"No 2D vs 3D side-test data for {session.session_id}.")
            return None
        prepared = ResponseSpec(channel, use_baseline_correction=False).apply(
            compiled, spike_rates_col=spike_rates_col)
        data = prepared.data
        resp = data[prepared.response_col].astype(float)
        data = data.assign(_resp=resp)[resp.notna()]
        r3 = data.loc[data["TestType"] == "3D", "_resp"].to_numpy()
        r2 = data.loc[data["TestType"] == "2D", "_resp"].to_numpy()
        if len(r3) == 0 or len(r2) == 0:
            self.status("Side test needs both 2D and 3D trials with responses.")
            return None

        n_perm = values["n_perm"]
        spi, p, _null = spi_permutation_test(r3, r2, n_perm=n_perm)
        significant = p < values["alpha"]

        means = data.groupby(["TestId", "TestType"])["_resp"].mean().unstack("TestType")
        means = means.dropna(subset=["2D", "3D"])
        x, y = means["2D"].to_numpy(), means["3D"].to_numpy()

        fig = Figure(figsize=(7.5, 7))
        ax = fig.add_subplot(111)
        vals = np.concatenate([x, y]) if len(x) else np.array([0.0, 1.0])
        lo, hi = float(vals.min()), float(vals.max())
        pad = (hi - lo) * 0.08 or 1.0
        lo, hi = lo - pad, hi + pad
        ax.plot([lo, hi], [lo, hi], color="gray", lw=1.2, ls="--", zorder=1, label="y = x")
        ax.scatter(x, y, color="black", s=60, alpha=0.8, zorder=3)
        if values["fit_line"] and len(x) >= 3:
            fit = linregress(x, y)
            xs = np.linspace(lo, hi, 200)
            ax.plot(xs, fit.slope * xs + fit.intercept, color="#c0392b", lw=1.8, zorder=2,
                    label=f"fit: slope {fit.slope:.2f}, $r^2$ = {fit.rvalue ** 2:.2f}, "
                          f"{_fmt_p(fit.pvalue)}")
        ax.set_xlim(lo, hi)
        ax.set_ylim(lo, hi)
        ax.set_aspect("equal", adjustable="box")

        verdict = "significant" if significant else "not significant"
        ax.text(0.03, 0.97, f"SPI = {spi:+.3f}\n{_fmt_p(p, n_perm)}, {verdict}",
                transform=ax.transAxes, ha="left", va="top", fontsize=15,
                color="#c0392b" if significant else "black",
                bbox=dict(boxstyle="round,pad=0.4", facecolor="white", edgecolor="#cccccc"))
        unit = "GA response" if channel == "GA" else "response (sp/s)"
        ax.set_xlabel(f"2D mean {unit}", fontsize=15)
        ax.set_ylabel(f"3D mean {unit}", fontsize=15)
        ax.set_title("Solid preference", fontsize=16)
        ax.tick_params(labelsize=13)
        ax.legend(fontsize=11, frameon=False, loc="lower right")
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        fig.tight_layout()
        self.status(f"SPI {spi:+.3f}, {_fmt_p(p, n_perm)} ({n_perm} permutations), "
                    f"{len(r3)} 3D / {len(r2)} 2D trials, {len(x)} shapes, "
                    f"channel {prepared.channel_label}")
        return fig
