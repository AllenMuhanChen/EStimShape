"""
Top-N stimuli per lineage: the explorer version of plot_top_n.PlotTopNAnalysis.

Same steps as PlotTopNAnalysis.analyze (ResponseSpec -> drop BASELINE ->
rank within lineage -> grouped-stimuli plot), with the hardcoded choices
(4 lineages, top 20, publish mode, cell/border size) exposed as parameters.
Nothing is written to disk unless you press Save in the explorer.
"""

from __future__ import annotations

from src.analysis.ga.explorer.explorer_module import FigureModule, Param
from src.analysis.ga.explorer.ga_data import (DATA_TYPES, load_ga_repository_data,
                                              parse_channel)


class TopNModule(FigureModule):
    name = "Top N per lineage"
    description = ("Best stimuli of the largest lineages, ranked by mean response "
                   "(plot_top_n).")

    def params(self):
        return [
            Param("data_type", "Data type", "choice", "mua", choices=DATA_TYPES,
                  tooltip="Which responses to import from the repository. "
                          "'GA' only has the GA Response."),
            Param("channel", "Channel", "str", "Cluster",
                  tooltip='"GA", "Cluster", "A-006", or "A-000,A-006" (summed)'),
            Param("baseline", "Baseline correction", "bool", False,
                  tooltip="Rank-based baseline correction (no-op for GA Response)."),
            Param("n_lineages", "Lineages shown", "int", 4, minimum=1, maximum=50,
                  tooltip="The N lineages with the most stimuli."),
            Param("top_n", "Top N per lineage", "int", 20, minimum=1, maximum=200),
            Param("publish_mode", "Publish mode", "bool", True,
                  tooltip="Colorbar, no info boxes (as plot_top_n). Off shows "
                          "response + StimSpecId under each stimulus."),
            Param("cell_size", "Cell size (px)", "int", 300, minimum=50, maximum=1000, step=25),
            Param("border_width", "Border width (px)", "int", 50, minimum=0, maximum=200, step=5),
        ]

    def make_figure(self, session, values):
        from src.analysis.ga.plot_top_n import get_top_n_lineages, rank_within_lineage
        from src.analysis.ga.response_spec import ResponseSpec
        from src.analysis.modules.grouped_stims_by_response import (
            GroupedStimuliInputHandler, GroupedStimuliPlotter)

        data_type = values["data_type"]
        channel = parse_channel(values["channel"])
        if data_type == "GA":
            channel = "GA"  # no per-channel rates in a GA-only import
        if not channel:
            self.status("Enter a channel.")
            return None

        compiled_data, spike_rates_col = load_ga_repository_data(session, data_type)

        spec = ResponseSpec(channel, use_baseline_correction=values["baseline"])
        prepared = spec.apply(compiled_data, spike_rates_col=spike_rates_col)
        data = prepared.data
        if spec.use_ga_response:
            data = data.sort_values(by=["Lineage", prepared.response_col],
                                    ascending=[True, False])
        data = data[data["StimType"] != "BASELINE"]
        if data.empty:
            self.status("No non-baseline stimuli with a response.")
            return None
        data = rank_within_lineage(data, prepared.response_col)

        lineages = get_top_n_lineages(data, values["n_lineages"])
        publish = values["publish_mode"]
        handler = GroupedStimuliInputHandler(
            response_col=prepared.response_col,
            response_key=prepared.response_key,
            path_col="ThumbnailPath",
            row_col="Lineage",
            col_col="RankWithinLineage",
            filter_values={"Lineage": lineages,
                           "RankWithinLineage": range(1, values["top_n"] + 1)},
            sort_rules={"RankWithinLineage": "ascending"},
        )
        plotter = GroupedStimuliPlotter(
            cell_size=(values["cell_size"], values["cell_size"]),
            border_width=values["border_width"],
            title=f"Top Stimuli Per Lineage  ({session.session_id}, "
                  f"{prepared.channel_label}{prepared.baseline_suffix})",
            # Same publish-mode switches as create_grouped_stimuli_module.
            info_box_columns=[] if publish else ["Response", "StimSpecId"],
            include_colorbar=publish,
            include_labels_for=None if publish else {"row", "col", "subgroup"},
            subplot_spacing=(20, 0),
        )
        fig = plotter.compute(handler.prepare(data))
        n_stims = data[data["Lineage"].isin(lineages)]["StimSpecId"].nunique()
        self.status(f"{len(lineages)} lineages, {n_stims} stimuli in them, "
                    f"channel {prepared.channel_label}")
        return fig
