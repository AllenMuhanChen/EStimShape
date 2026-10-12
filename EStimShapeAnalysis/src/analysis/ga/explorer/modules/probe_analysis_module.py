"""
Probe analysis: every channel of the probe, top -> bottom, with one column of coloured
dots per per-channel quantity (tuning preferences, correlations with the GA channels,
delta/variant and model-prediction columns). Tick the columns you want.

The columns and the figure live in src/analysis/probe_analysis/ (shared with the
standalone probe_analysis.py script); this module only exposes them as toggles.
Data is loaded the first time a column needs it and kept for the session, so turning
columns on and off is quick. Read-only.
"""

from __future__ import annotations

from src.analysis.ga.explorer.explorer_module import FigureModule, Param
from src.analysis.probe_analysis.probe_columns import COLUMNS, build_blocks
from src.analysis.probe_analysis.probe_data import ProbeData, parse_estim_spec
from src.analysis.probe_analysis.probe_figure import draw_probe_figure

VECTOR_TYPES = ['ga_mean_response', 'ga_mean_response_3d', 'ga_mean_response_2d',
                'ga_mean_response_shade', 'ga_mean_response_specular']


def column_param_key(column_key: str) -> str:
    return f"col_{column_key}"


def _parse_frequencies(text):
    """'all' / blank -> None (every frequency); '4, 12' -> [4.0, 12.0]."""
    text = (text or "").strip().lower()
    if text in ("", "all"):
        return None
    try:
        return [float(p) for p in text.replace(";", ",").split(",") if p.strip()]
    except ValueError:
        raise ValueError(f"Isochromatic freqs '{text}': use 'all' or numbers like 4, 12")


class ProbeAnalysisModule(FigureModule):
    name = "Probe analysis"
    description = ("Each channel down the probe, one column per quantity. Tick the "
                   "columns to show. Stars = GA channels.")

    def params(self):
        params = []
        group = None
        for col in COLUMNS:
            if col.group != group:
                group = col.group
                params.append(Param(f"header_{len(params)}", group, "header", None))
            params.append(Param(column_param_key(col.key), col.label, "bool", col.default,
                                tooltip=col.tooltip, live=True))
        params += [
            Param("header_display", "Display", "header", None),
            Param("y_labels", "Y axis labels", "choice", "channel",
                  choices=["channel", "depth", "both"], live=True,
                  tooltip="Channel names, depth along the probe (mm, 65 µm pitch), or both."),
            Param("font_size", "Font size", "int", 11, minimum=7, maximum=20, live=True),
            Param("estim_spec", "EStim spec", "str", "none",
                  tooltip="Hatch the estim channels and use them for 'ρ vs estim "
                          "average': none, all, or spec id(s) like 3 or 3,5. The "
                          "status bar lists the session's specs."),
            Param("iso_frequencies", "Isochromatic freqs (Hz)", "str", "all",
                  tooltip="'all', or the frequencies to show, e.g. 12 or 4, 12."),
            Param("header_corr", "Correlation settings", "header", None),
            Param("corr_reference", "Reference channels", "str", "GA",
                  tooltip="Columns of the per-channel ρ plots: GA = every GA channel, or "
                          "a list like A-022, A-008."),
            Param("corr_method", "Correlation", "choice", "spearman",
                  choices=["spearman", "pearson"]),
            Param("vector_type", "GA response vectors", "choice", VECTOR_TYPES[0],
                  choices=VECTOR_TYPES,
                  tooltip="ChannelResponseVectors type used by the GA-mean-response "
                          "correlation columns."),
            Param("group_leave_one_out", "Group ρ leave-one-out", "bool", True,
                  tooltip="'ρ vs GA / estim average': a channel in the group is compared "
                          "with the average of the OTHER group channels."),
            Param("rho_threshold", "ρ* (GA extent)", "float", 0.5, minimum=0.0,
                  maximum=1.0, step=0.05),
            Param("n_misses_to_stop", "Misses to stop walk", "int", 2, minimum=1,
                  maximum=10,
                  tooltip="Channels in a row below ρ* that end the extent walk."),
            Param("top_n", "Top N GA stims", "int", 20, minimum=3, maximum=1000),
            Param("included_only", "Included delta pairs only", "bool", True),
            Param("axis_strategy", "Axis-coding strategy", "str", "multi_prototype_pca"),
        ]
        return params

    def create_view(self, parent):
        from src.analysis.ga.explorer.figure_view import FigureView
        # Show the figure at its own size (scrolling if wide) so columns keep their
        # width however many are ticked.
        self._view = FigureView(parent, keep_size=True)
        return self._view

    def make_figure(self, session, values):
        data = session.get_or_load("probe_data", lambda: ProbeData(session.session_id))
        keys = [c.key for c in COLUMNS if values[column_param_key(c.key)]]
        if not keys:
            self.status("Tick at least one column.")
            return None

        estim, estim_label, by_spec = [], "", {}
        spec_text = (values["estim_spec"] or "").strip().lower()
        if spec_text not in ("", "none"):
            by_spec = data.estim_channels_by_spec()
            estim, estim_label = parse_estim_spec(spec_text, by_spec)

        opts = {k: values[k] for k in ("corr_reference", "corr_method", "vector_type",
                                       "group_leave_one_out", "rho_threshold",
                                       "n_misses_to_stop", "top_n", "included_only",
                                       "axis_strategy")}
        opts["estim_channels"] = estim
        opts["iso_frequencies"] = _parse_frequencies(values["iso_frequencies"])
        blocks, skipped = build_blocks(keys, data, opts)

        notes = [b.note for b in blocks if b.note]
        if skipped:
            notes.append("not shown: " + "; ".join(f"{label} ({why})"
                                                    for label, why in skipped))
        if by_spec:
            notes.append("estim specs: " + ", ".join(
                f"{s}: {'/'.join(ch)}" for s, ch in sorted(by_spec.items())))
        if not blocks:
            self.status("Nothing to show. " + " | ".join(notes))
            return None

        title = session.session_id + (f"  (estim {estim_label})" if estim_label else "")
        fig = draw_probe_figure(blocks, data.channel_strs(), data.ga_channels(),
                                estim_channels=estim, title=title,
                                y_labels=values["y_labels"], font_size=values["font_size"])
        self.status(f"{sum(len(b.subs) for b in blocks)} columns"
                    + (" | " + " | ".join(notes) if notes else ""))
        return fig
