from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.gridspec import GridSpec
from matplotlib.patches import Patch

from clat.pipeline.pipeline_base_classes import (
    InputHandler, ComputationModule, AnalysisModuleFactory, create_pipeline
)
from src.analysis import Analysis
from src.analysis.modules.figure_output import FigureSaverOutput
from src.repository.export_to_repository import read_session_id_from_db_name
from src.repository.import_from_repository import import_from_repository
from src.startup import context

CHANNEL_ORDER = [7, 8, 25, 22, 0, 15, 24, 23, 6, 9, 26, 21, 5, 10, 31, 16,
                 27, 20, 4, 11, 28, 19, 1, 14, 3, 12, 29, 18, 2, 13, 30, 17]

TOP_N = 10


def main():
    analysis = GARasterAnalysis()
    session_id, _ = read_session_id_from_db_name(context.ga_database)
    analysis.run(session_id, "raw", "ALL")


class GARasterAnalysis(Analysis):
    logging_path = context.logging_path

    def import_data(self, compiled_data: pd.DataFrame) -> pd.DataFrame:
        if compiled_data is None:
            compiled_data = import_from_repository(
                self.session_id,
                "ga",
                "GAStimInfo",
                self.response_table,
            )
        return compiled_data

    def analyze(self, channel, compiled_data: pd.DataFrame = None):
        channels = [f"A-{i:03d}" for i in CHANNEL_ORDER]

        module = create_ga_raster_module(
            channels=channels,
            top_n=TOP_N,
            spike_data_col=self.spike_tstamps_col,
            spike_rate_col=self.spike_rates_col,
            time_range=(-0.2, 0.7),
            title="GA Top Stimuli Rasters by Channel",
            save_path=f"{self.save_path}/ga_raster_top_{TOP_N}.png",
        )

        pipeline = create_pipeline().then(module).build()
        result = pipeline.run(compiled_data)
        plt.show()
        return result

    def compile_and_export(self):
        raise NotImplementedError("Use PlotTopNAnalysis.compile_and_export() to compile GA data.")

    def compile(self):
        raise NotImplementedError("Use PlotTopNAnalysis.compile() to compile GA data.")


# ---------------------------------------------------------------------------
# Module factory
# ---------------------------------------------------------------------------

def create_ga_raster_module(
        channels: List[str],
        top_n: int = 10,
        spike_data_col: str = 'Spikes by channel',
        spike_rate_col: str = 'Spike Rate by channel',
        time_range: Tuple[float, float] = (-0.2, 0.7),
        title: Optional[str] = None,
        save_path: Optional[str] = None,
) -> Any:
    """
    Create an analysis module that plots a single tall figure with one raster
    row per channel.  Within each row the top-N stimuli (ranked by mean spike
    rate on that channel) are shown as coloured vertical lines – one colour per
    stimulus rank so the legend is shared across all rows.

    Args:
        channels:       Ordered list of channel names (e.g. ['A-007', 'A-008', ...]).
        top_n:          How many top stimuli to show per channel.
        spike_data_col: DataFrame column holding spike-timestamp dicts.
        spike_rate_col: DataFrame column holding spike-rate dicts (used for ranking).
        time_range:     (start, stop) in seconds relative to stimulus onset.
        title:          Figure title.
        save_path:      If given, the figure is saved here.
    """
    return AnalysisModuleFactory.create(
        input_handler=GARasterInputHandler(
            channels=channels,
            top_n=top_n,
            spike_data_col=spike_data_col,
            spike_rate_col=spike_rate_col,
        ),
        computation=GARasterPlotter(
            channels=channels,
            top_n=top_n,
            time_range=time_range,
            title=title,
        ),
        output_handler=FigureSaverOutput(save_path=save_path),
        name="ga_raster",
    )


# ---------------------------------------------------------------------------
# Input handler
# ---------------------------------------------------------------------------

class GARasterInputHandler(InputHandler):
    """
    For each channel, identify the top-N stimuli by mean spike rate and collect
    the trials that belong to those stimuli.  The rank index (0 = best) is
    preserved so that colour assignment is consistent across channels.
    """

    def __init__(self,
                 channels: List[str],
                 top_n: int,
                 spike_data_col: str,
                 spike_rate_col: str):
        self.channels = channels
        self.top_n = top_n
        self.spike_data_col = spike_data_col
        self.spike_rate_col = spike_rate_col

    def prepare(self, compiled_data: pd.DataFrame) -> Dict[str, Any]:
        data = compiled_data.copy()

        # Drop catch / baseline stimuli that have no meaningful spike data
        if 'StimType' in data.columns:
            data = data[~data['StimType'].isin(['CATCH', 'BASELINE'])]

        channel_data: Dict[str, Dict] = {}
        for channel in self.channels:
            # Extract per-trial rate for this channel
            data['_rate'] = data[self.spike_rate_col].apply(
                lambda d: d.get(channel, 0) if isinstance(d, dict) else 0
            )

            # Average across repeats of the same stimulus
            avg_rates = (
                data.groupby('StimSpecId')['_rate']
                .mean()
                .nlargest(self.top_n)
            )
            top_stim_ids = avg_rates.index.tolist()  # ordered best → worst

            channel_data[channel] = {
                'data': data[data['StimSpecId'].isin(top_stim_ids)].copy(),
                'top_stim_ids': top_stim_ids,  # rank 0 = best
            }

        data.drop(columns=['_rate'], inplace=True, errors='ignore')

        return {
            'channel_data': channel_data,
            'spike_data_col': self.spike_data_col,
        }


# ---------------------------------------------------------------------------
# Plotter
# ---------------------------------------------------------------------------

class GARasterPlotter(ComputationModule):
    """
    Draws one subplot per channel.  Within each subplot, trials are stacked
    vertically grouped by stimulus.  The colour of each group is determined by
    its rank (rank 0 = best), making the shared legend interpretable.
    """

    def __init__(self,
                 channels: List[str],
                 top_n: int,
                 time_range: Tuple[float, float],
                 title: Optional[str] = None):
        self.channels = channels
        self.top_n = top_n
        self.time_range = time_range
        self.title = title

    # ---- colour helpers ----

    def _palette(self) -> np.ndarray:
        """Return an (top_n, 4) RGBA array – one colour per rank."""
        if self.top_n <= 10:
            return plt.cm.tab10(np.linspace(0, 1, 10)[:self.top_n])
        return plt.cm.tab20(np.linspace(0, 1, 20)[:self.top_n])

    # ---- main entry point ----

    def compute(self, prepared_data: Dict[str, Any]) -> plt.Figure:
        channel_data = prepared_data['channel_data']
        spike_data_col = prepared_data['spike_data_col']

        palette = self._palette()
        n_channels = len(self.channels)

        # Height of each subplot proportional to number of plotted trials
        height_ratios = []
        for ch in self.channels:
            n_trials = len(channel_data[ch]['data'])
            n_gaps = len(channel_data[ch]['top_stim_ids'])  # one gap per stimulus
            height_ratios.append(max(n_trials + n_gaps, 5))

        fig_height = max(n_channels * 1.5, 32)
        fig = plt.figure(figsize=(14, fig_height))
        gs = GridSpec(
            n_channels, 1,
            figure=fig,
            height_ratios=height_ratios,
            hspace=0.6,
        )

        for row_idx, channel in enumerate(self.channels):
            ax = fig.add_subplot(gs[row_idx])
            self._plot_channel(
                ax=ax,
                channel=channel,
                ch_info=channel_data[channel],
                spike_data_col=spike_data_col,
                palette=palette,
                is_last_row=(row_idx == n_channels - 1),
            )

        # Shared legend: rank → colour
        legend_handles = [
            Patch(facecolor=palette[rank], label=f"Rank {rank + 1}")
            for rank in range(self.top_n)
        ]
        fig.legend(
            handles=legend_handles,
            loc='upper right',
            bbox_to_anchor=(1.0, 1.0),
            ncol=1,
            fontsize=7,
            title="Stimulus rank\n(per channel)",
            title_fontsize=7,
            framealpha=0.8,
        )

        if self.title:
            fig.suptitle(self.title, fontsize=13, x=0.45)

        return fig

    def _plot_channel(self,
                      ax: plt.Axes,
                      channel: str,
                      ch_info: Dict,
                      spike_data_col: str,
                      palette: np.ndarray,
                      is_last_row: bool):
        data = ch_info['data']
        top_stim_ids = ch_info['top_stim_ids']

        y_pos = 0
        for rank, stim_id in enumerate(top_stim_ids):
            color = palette[rank]
            stim_trials = data[data['StimSpecId'] == stim_id]

            for _, trial in stim_trials.iterrows():
                spike_times = self._extract_spikes(trial, spike_data_col, channel)
                if spike_times:
                    ax.vlines(spike_times, y_pos, y_pos + 0.9, color=color, lw=0.5)
                y_pos += 1

            y_pos += 1  # blank row gap between stimulus groups

        total_height = y_pos

        ax.set_xlim(*self.time_range)
        ax.set_ylim(-0.5, total_height + 0.5)
        ax.axvline(0, color='gray', lw=0.5, linestyle='--', alpha=0.6)

        # Channel label on y-axis
        ax.set_ylabel(channel, rotation=0, ha='right', va='center', fontsize=7,
                      labelpad=35)
        ax.set_yticks([])
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_visible(False)

        if is_last_row:
            ax.set_xlabel('Time (s)', fontsize=8)
        else:
            ax.set_xticks([])
            ax.spines['bottom'].set_visible(False)

    @staticmethod
    def _extract_spikes(trial: pd.Series,
                        spike_data_col: str,
                        channel: str) -> List[float]:
        """Pull the spike-time list for *channel* out of this trial row."""
        raw = trial.get(spike_data_col)
        if isinstance(raw, dict):
            times = raw.get(channel, [])
        elif isinstance(raw, list):
            times = raw
        else:
            times = []
        return times if times is not None else []


if __name__ == "__main__":
    main()
