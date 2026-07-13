"""
raw_channel_candidacy_analysis.py
----------------------------------
Investigates which raw Intan channels are strong candidates for GA study,
BEFORE any GA-computed response values are used.

Three metrics are computed per channel:

  1. Top-N Z-score      – mean z-score of the top-N stimuli (normalized firing rate).
                         Channels driven far above their own baseline show high values.

  2. Kruskal-Wallis p   – non-parametric test of whether firing rate varies
                         significantly across stimuli (p < 0.05 = selective channel).

  3. Onset latency      – mean ± std of the first-spike latency (ms) after stimulus
                         onset, across all trials with at least one post-stimulus spike.
                         Computed via the reusable `response_onset` module.

The figure is a three-column summary sorted by z-score (best candidates at top).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.gridspec import GridSpec
from scipy import stats as scipy_stats

from clat.compile.task.cached_task_fields import CachedTaskFieldList
from clat.compile.task.classic_database_task_fields import TaskIdField, StimSpecIdField
from clat.pipeline.pipeline_base_classes import (
    InputHandler, ComputationModule, AnalysisModuleFactory, create_pipeline,
)
from clat.util.connection import Connection

from src.analysis import Analysis
from src.analysis.fields.cached_task_fields import StimTypeField, StimPathField, ThumbnailField
from src.analysis.ga.ga_raster_analysis import GARasterAnalysis, CHANNEL_ORDER
from src.analysis.ga.response_onset import (
    OnsetStats,
    compute_onset_stats_for_all_channels,
    get_channel_spikes,
)
from src.analysis.isogabor.old_isogabor_analysis import append_response_fields
from src.analysis.modules.figure_output import FigureSaverOutput
from src.repository.export_to_repository import read_session_id_and_date_from_db_name
from src.startup import context


def main():
    analysis = RawChannelCandidacyAnalysis(top_n=4, data_type="mua")
    session_id, _ = read_session_id_and_date_from_db_name(context.ga_database)
    compiled_data = analysis.compile()
    analysis.run(session_id, "mua", "ALL", compiled_data)


# ---------------------------------------------------------------------------
# Analysis class
# ---------------------------------------------------------------------------

class RawChannelCandidacyAnalysis(Analysis):
    """
    Identifies candidate channels for GA study from raw spike data.

    Args:
        top_n:  Number of top stimuli (per channel) used to compute the mean z-score.
    """

    logging_path = context.logging_path

    def __init__(self, top_n: int = 4, data_type: str = None):
        super().__init__(data_type=data_type)
        self.top_n = top_n

    def compile(self) -> pd.DataFrame:
        """Compile raw spike data without GA-evolution metadata."""
        conn = Connection(context.ga_database)

        from clat.compile.task.compile_task_id import TaskIdCollector
        task_ids = TaskIdCollector(conn).collect_task_ids()

        fields = CachedTaskFieldList()
        fields.append(TaskIdField(conn))
        fields.append(StimSpecIdField(conn))
        fields.append(StimTypeField(conn))
        fields.append(StimPathField(conn))
        fields.append(ThumbnailField(conn))
        # Spike source: MUA (wideband -kxMAD, reusing MUAChannelResponses) or spike.dat.
        rename_map = append_response_fields(
            fields, conn, task_ids, context.ga_intan_path,
            is_mua=self.response_table == "MUASpikeResponses",
            parsed_spikes_path=context.ga_parsed_spikes_path,
            db_name=context.ga_database,
            mua_metric=self.mua_method or "mad_k4_block100",
            mua_k=self.mua_k or 4.0, mua_block=self.mua_block or 100)

        data = fields.to_data(task_ids)
        if rename_map:
            data = data.rename(columns=rename_map)
        data = GARasterAnalysis.clean_ga_data(data)
        return data

    def compile_and_export(self):
        raise NotImplementedError(
            "RawChannelCandidacyAnalysis works on raw Intan data; "
            "use compile() instead."
        )

    def analyze(self, channel, compiled_data: pd.DataFrame = None):
        channels = [f"A-{i:03d}" for i in CHANNEL_ORDER]
        save_path = f"{self.save_path}/raw_channel_candidacy_top{self.top_n}.png"

        module = create_raw_channel_candidacy_module(
            channels=channels,
            top_n=self.top_n,
            spike_data_col=self.spike_tstamps_col,
            spike_rate_col=self.spike_rates_col,
            baseline_window=(-0.2, 0.0),
            response_window=(0.0, 0.7),
            title="Raw Channel Candidacy — Z-score / Kruskal-Wallis / Onset Latency",
            save_path=save_path,
        )

        pipeline = create_pipeline().then(module).build()
        result = pipeline.run(compiled_data)
        plt.show()
        return result


# ---------------------------------------------------------------------------
# Module factory
# ---------------------------------------------------------------------------

def create_raw_channel_candidacy_module(
        channels: List[str],
        top_n: int = 10,
        spike_data_col: str = "Spikes by channel",
        spike_rate_col: str = "Spike Rate by channel",
        baseline_window: tuple = (-0.2, 0.0),
        response_window: tuple = (0.0, 0.7),
        title: Optional[str] = None,
        save_path: Optional[str] = None,
) -> Any:
    """
    Create a pipeline module that computes and plots per-channel candidacy metrics.

    Args:
        channels:         Ordered list of channel names (e.g. from CHANNEL_ORDER).
        top_n:            Number of top stimuli whose z-scores are averaged.
        spike_data_col:   DataFrame column with spike-timestamp dicts.
        spike_rate_col:   DataFrame column with spike-rate dicts (used for z-score / KW).
        baseline_window:  Pre-stimulus window (seconds) for PSTH baseline stats.
        response_window:  Post-stimulus window (seconds) searched for onset crossing.
        title:            Figure suptitle.
        save_path:        If given, the figure is saved here.
    """
    return AnalysisModuleFactory.create(
        input_handler=RawChannelMetricsInputHandler(
            channels=channels,
            top_n=top_n,
            spike_data_col=spike_data_col,
            spike_rate_col=spike_rate_col,
            baseline_window=baseline_window,
            response_window=response_window,
        ),
        computation=RawChannelCandidacyPlotter(title=title),
        output_handler=FigureSaverOutput(save_path=save_path),
        name="raw_channel_candidacy",
    )


# ---------------------------------------------------------------------------
# Input handler – computes all per-channel metrics
# ---------------------------------------------------------------------------

class RawChannelMetricsInputHandler(InputHandler):
    """
    For every channel compute:
      - mean z-score of the top-N stimuli
      - Kruskal-Wallis H-statistic and p-value across stimuli
      - PSTH onset (10% of peak) and rise time (10%→90%) via response_onset module
    """

    def __init__(
            self,
            channels: List[str],
            top_n: int,
            spike_data_col: str,
            spike_rate_col: str,
            baseline_window: tuple = (-0.2, 0.0),
            response_window: tuple = (0.0, 0.7),
    ):
        self.channels = channels
        self.top_n = top_n
        self.spike_data_col = spike_data_col
        self.spike_rate_col = spike_rate_col
        self.baseline_window = baseline_window
        self.response_window = response_window

    def prepare(self, compiled_data: pd.DataFrame) -> Dict[str, Any]:
        data = compiled_data.copy()

        # Exclude CATCH / BASELINE trials
        if "StimType" in data.columns:
            data = data[~data["StimType"].isin(["CATCH", "BASELINE"])]

        # --- Onset stats (reusable module) ---
        onset_by_channel: Dict[str, OnsetStats] = compute_onset_stats_for_all_channels(
            data,
            spike_data_col=self.spike_data_col,
            channels=self.channels,
            baseline_window=self.baseline_window,
            response_window=self.response_window,
        )

        # --- Z-score and Kruskal-Wallis per channel ---
        channel_metrics: Dict[str, Dict] = {}
        for ch in self.channels:
            metrics = self._compute_channel_metrics(data, ch, onset_by_channel[ch])
            channel_metrics[ch] = metrics

        return {"channel_metrics": channel_metrics, "channel_order": self.channels}

    def _compute_channel_metrics(
            self, data: pd.DataFrame, channel: str, onset_stats: OnsetStats
    ) -> Dict[str, Any]:
        # Per-trial rate for this channel
        rates = data[self.spike_rate_col].apply(
            lambda d: d.get(channel, 0.0) if isinstance(d, dict) else 0.0
        )

        # --- Z-score ---
        mean_r = rates.mean()
        std_r = rates.std()
        if std_r > 0:
            z_scores = (rates - mean_r) / std_r
        else:
            z_scores = pd.Series(0.0, index=rates.index)

        data_with_z = data.assign(_z=z_scores, _rate=rates)

        mean_z_per_stim = data_with_z.groupby("StimSpecId")["_z"].mean()
        top_z_stims = mean_z_per_stim.nlargest(self.top_n)
        top_z_mean = float(top_z_stims.mean()) if len(top_z_stims) > 0 else np.nan

        # --- Kruskal-Wallis across stimuli ---
        groups = [
            grp.tolist()
            for _, grp in data_with_z.groupby("StimSpecId")["_rate"]
            if len(grp) >= 2
        ]
        if len(groups) >= 2:
            kw_h, kw_p = scipy_stats.kruskal(*groups)
        else:
            kw_h, kw_p = np.nan, np.nan

        return {
            "top_z_mean": top_z_mean,
            "kw_h": kw_h,
            "kw_p": kw_p,
            "onset": onset_stats,
            "mean_rate": mean_r,
        }


# ---------------------------------------------------------------------------
# Plotter
# ---------------------------------------------------------------------------

class RawChannelCandidacyPlotter(ComputationModule):
    """
    Three-column summary figure:
      Col 0 – Horizontal bar: mean z-score of top-N stimuli
      Col 1 – Horizontal bar: –log10(KW p-value); vertical reference at p=0.05
      Col 2 – Span bar from PSTH 10% onset to 90% peak; short bar = consistent

    Channels are displayed in probe layout order (CHANNEL_ORDER), matching GARasterAnalysis.
    """

    _KW_ALPHA = 0.05

    def __init__(self, title: Optional[str] = None):
        self.title = title

    def compute(self, prepared_data: Dict[str, Any]) -> plt.Figure:
        metrics = prepared_data["channel_metrics"]
        channels_sorted = prepared_data["channel_order"]  # probe layout order (CHANNEL_ORDER)

        n = len(channels_sorted)
        fig_height = max(n * 0.45, 10)
        fig, axes = plt.subplots(
            1, 3, figsize=(18, fig_height),
            gridspec_kw={"width_ratios": [2, 2, 2], "wspace": 0.55},
        )

        ax_z, ax_kw, ax_onset = axes
        y_positions = np.arange(n)

        z_vals    = [metrics[ch]["top_z_mean"] for ch in channels_sorted]
        kw_p_vals = [metrics[ch]["kw_p"]       for ch in channels_sorted]
        onset_vals     = [metrics[ch]["onset"].onset_ms     for ch in channels_sorted]
        rise_time_vals = [metrics[ch]["onset"].rise_time_ms for ch in channels_sorted]

        # --- Column 0: Z-score bars ---
        colors_z = [
            "#d62728" if (not np.isnan(z) and z > 1.0) else "#aec7e8"
            for z in z_vals
        ]
        ax_z.barh(y_positions, z_vals, color=colors_z, edgecolor="none")
        ax_z.axvline(0, color="black", lw=0.8, linestyle="--")
        ax_z.set_yticks(y_positions)
        ax_z.set_yticklabels(channels_sorted, fontsize=7)
        ax_z.set_xlabel("Mean z-score (top stimuli)", fontsize=9)
        ax_z.set_title("Z-score", fontsize=10)
        ax_z.invert_yaxis()

        # --- Column 1: Kruskal-Wallis –log10(p) ---
        neg_log_p = [
            -np.log10(max(p, 1e-300)) if not np.isnan(p) else 0.0
            for p in kw_p_vals
        ]
        threshold_line = -np.log10(self._KW_ALPHA)
        colors_kw = [
            "#2ca02c" if (not np.isnan(p) and p < self._KW_ALPHA) else "#c7c7c7"
            for p in kw_p_vals
        ]
        ax_kw.barh(y_positions, neg_log_p, color=colors_kw, edgecolor="none")
        ax_kw.axvline(threshold_line, color="red", lw=1.0, linestyle="--",
                      label=f"p={self._KW_ALPHA}")
        ax_kw.set_yticks(y_positions)
        ax_kw.set_yticklabels([])
        ax_kw.set_xlabel("−log₁₀(KW p-value)", fontsize=9)
        ax_kw.set_title("Kruskal-Wallis", fontsize=10)
        ax_kw.legend(fontsize=7, loc="lower right")
        ax_kw.invert_yaxis()

        # --- Column 2: PSTH onset and rise time ---
        # onset_ms    = time to 10% of PSTH peak above baseline (response start)
        # rise_time_ms = time from 10% to 90% of peak (consistency proxy)
        #   Short bar = sharp PSTH rise = consistent timing across trials
        #   Long bar  = gradual PSTH rise = variable/scattered responses
        # Bar drawn from onset to onset+rise_time; a dot marks the onset.
        for y, onset, rise in zip(y_positions, onset_vals, rise_time_vals):
            if np.isnan(onset):
                continue
            ax_onset.plot(onset, y, "o", color="#9467bd", markersize=4, zorder=3)
            if not np.isnan(rise):
                ax_onset.hlines(y, onset, onset + rise,
                                colors="#9467bd", linewidth=3, alpha=0.7)
        ax_onset.set_yticks(y_positions)
        ax_onset.set_yticklabels([])
        ax_onset.set_xlabel("PSTH onset → 90% rise (ms)", fontsize=9)
        ax_onset.set_title("Onset / Rise Time", fontsize=10)
        ax_onset.set_xlim(left=0)
        ax_onset.invert_yaxis()

        if self.title:
            fig.suptitle(self.title, fontsize=11, y=1.01)

        fig.tight_layout()
        return fig


if __name__ == "__main__":
    main()
