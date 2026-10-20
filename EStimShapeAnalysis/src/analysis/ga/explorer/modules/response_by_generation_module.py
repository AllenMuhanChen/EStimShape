"""
Response across generations, one line per lineage.

Small matplotlib module that doubles as the template for new custom plots:
declare params, load data through ga_data (shared, cached per session), build
a matplotlib Figure (not pyplot) and return it.
"""

from __future__ import annotations

import matplotlib
from matplotlib.figure import Figure

from src.analysis.ga.explorer.explorer_module import FigureModule, Param
from src.analysis.ga.explorer.ga_data import (DATA_TYPES, load_ga_repository_data,
                                              parse_channel)

FONT = 14


class ResponseByGenerationModule(FigureModule):
    name = "Response by generation"
    description = "Mean stimulus response per generation for the largest lineages."

    def params(self):
        return [
            Param("data_type", "Data type", "choice", "mua", choices=DATA_TYPES),
            Param("channel", "Channel", "str", "GA",
                  tooltip='"GA", "Cluster", "A-006", or "A-000,A-006" (summed)'),
            Param("baseline", "Baseline correction", "bool", False),
            Param("n_lineages", "Lineages shown", "int", 4, minimum=1, maximum=30),
            Param("show_stims", "Show each stimulus", "bool", True, live=True),
        ]

    def make_figure(self, session, values):
        from src.analysis.ga.plot_top_n import get_top_n_lineages
        from src.analysis.ga.response_spec import ResponseSpec

        data_type = values["data_type"]
        channel = "GA" if data_type == "GA" else parse_channel(values["channel"])
        compiled_data, spike_rates_col = load_ga_repository_data(session, data_type)
        prepared = ResponseSpec(channel, use_baseline_correction=values["baseline"]).apply(
            compiled_data, spike_rates_col=spike_rates_col)
        data = prepared.data[prepared.data["StimType"] != "BASELINE"]
        if data.empty:
            self.status("No non-baseline stimuli with a response.")
            return None

        lineages = get_top_n_lineages(data, values["n_lineages"])
        per_stim = (data[data["Lineage"].isin(lineages)]
                    .groupby(["Lineage", "StimSpecId", "GenId"])[prepared.response_col]
                    .mean().reset_index())

        fig = Figure(figsize=(11, 6.5), constrained_layout=True)
        ax = fig.add_subplot(111)
        cmap = matplotlib.colormaps["tab10"]
        for i, lineage in enumerate(lineages):
            sub = per_stim[per_stim["Lineage"] == lineage]
            color = cmap(i % 10)
            if values["show_stims"]:
                ax.scatter(sub["GenId"], sub[prepared.response_col], s=14, alpha=0.35,
                           color=color, linewidths=0)
            by_gen = sub.groupby("GenId")[prepared.response_col].mean()
            ax.plot(by_gen.index, by_gen.values, "-o", color=color, lw=2.5, ms=6,
                    label=f"Lineage {lineage} (n={len(sub)})")
        ax.set_xlabel("Generation", fontsize=FONT + 2)
        ax.set_ylabel(f"Response ({prepared.channel_label}{prepared.baseline_suffix})",
                      fontsize=FONT + 2)
        ax.set_title(f"Response by generation  ({session.session_id})", fontsize=FONT + 2)
        ax.tick_params(labelsize=FONT)
        ax.spines[["top", "right"]].set_visible(False)
        ax.legend(fontsize=FONT - 2, frameon=False)
        self.status(f"{len(lineages)} lineages, {len(per_stim)} stimuli")
        return fig
