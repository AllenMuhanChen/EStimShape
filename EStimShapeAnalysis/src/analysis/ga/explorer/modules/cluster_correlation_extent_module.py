"""
GA cluster correlation extent for this session: the figure from
nafc/group_analysis/plot_cluster_correlation_spread (see that module for the method).

Each channel's GA response vector is correlated with the average GA cluster response
(GA channels leave-one-out); the extent is walked up and down the probe from the GA
channels and stops after n channels in a row below the ρ threshold. Read-only.
"""

from __future__ import annotations

from src.analysis.ga.explorer.explorer_module import FigureModule, Param
from src.analysis.nafc.group_analysis import plot_cluster_correlation_spread as ccs


class ClusterCorrelationExtentModule(FigureModule):
    name = "GA cluster correlation extent"
    description = ("Each channel's ρ with the GA cluster response along the probe, and "
                   "the contiguous extent above the ρ threshold.")

    def params(self):
        return [
            Param("rho_threshold", "ρ threshold", "float", 0.5, minimum=0.0,
                  maximum=1.0, step=0.05,
                  tooltip="Channels with ρ >= this count as part of the cluster."),
            Param("n_misses_to_stop", "Misses to stop", "int", 2, minimum=1, maximum=10,
                  tooltip="Channels in a row below the threshold that end the walk."),
            Param("method", "Correlation", "choice", "spearman",
                  choices=["spearman", "pearson"]),
        ]

    def make_figure(self, session, values):
        from matplotlib.figure import Figure

        method = values["method"]
        try:
            rho_n, channel_strs, positions_um, ga_strs = session.get_or_load(
                ("cluster_corr_rhos", method),
                lambda: ccs.load_session_rhos(session.session_id, method=method,
                                              switch_context=False))
        except RuntimeError as e:  # no response vectors / no GA channels with data
            self.status(str(e))
            return None
        ext = ccs.contiguous_extent(channel_strs, positions_um, rho_n, ga_strs,
                                    rho_threshold=values["rho_threshold"],
                                    n_misses_to_stop=values["n_misses_to_stop"])
        self.status(f"Extent {ext['extent_total_um']:.0f} µm "
                    f"(up {ext['extent_up_um']:.0f}, down {ext['extent_down_um']:.0f})")
        return ccs.plot_extent_figure(session.session_id, ext, channel_strs, ga_strs,
                                      n_misses_to_stop=values["n_misses_to_stop"],
                                      fig=Figure(figsize=(13, 11)))
