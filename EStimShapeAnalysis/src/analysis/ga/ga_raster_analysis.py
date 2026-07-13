from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Union

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.gridspec import GridSpec

from clat.compile.task.cached_task_fields import CachedTaskFieldList
from clat.compile.task.classic_database_task_fields import StimSpecDataField, TaskIdField, StimSpecIdField
from clat.compile.task.compile_task_id import TaskIdCollector
from clat.pipeline.pipeline_base_classes import (
    InputHandler, ComputationModule, AnalysisModuleFactory, create_pipeline
)
from clat.util.connection import Connection
from src.analysis import Analysis
from src.analysis.fields.cached_task_fields import StimTypeField, StimPathField, ThumbnailField, HypothesizedCompField
from src.analysis.ga.cached_ga_fields import ParentIdField, LineageField, GenIdField, RegimeScoreField
from src.analysis.ga.plot_top_n import PlotTopNAnalysis
from src.analysis.isogabor.old_isogabor_analysis import append_response_fields
from src.analysis.modules.figure_output import FigureSaverOutput
from src.repository.export_to_repository import read_session_id_and_date_from_db_name
from src.repository.import_from_repository import import_from_repository
from src.startup import context

CHANNEL_ORDER = [7, 8, 25, 22, 0, 15, 24, 23, 6, 9, 26, 21, 5, 10, 31, 16,
                 27, 20, 4, 11, 28, 19, 1, 14, 3, 12, 29, 18, 2, 13, 30, 17]


def main():
    analysis = GARasterAnalysis(top_n=10, gen_id=None, data_type="mua")
    session_id, _ = read_session_id_and_date_from_db_name(context.ga_database)
    compiled_data = analysis.compile()
    analysis.run(session_id, "mua", "ALL", compiled_data)


class GARasterAnalysis(Analysis):
    """
    Plots a single tall figure with one raster row per channel showing the
    top-N stimuli for that channel.

    Args:
        top_n:   Number of top stimuli to show per channel (ranked by mean spike rate).
        gen_id:  Filter to a specific generation, a list of generations, or None for all.
    """
    logging_path = context.logging_path

    def __init__(self, top_n: int = 10, gen_id: Optional[Union[int, List[int]]] = None,
                 data_type: str = None):
        super().__init__(data_type=data_type)
        self.top_n = top_n
        if gen_id is None or isinstance(gen_id, list):
            self.gen_ids = gen_id          # None = all, list = filter to these
        else:
            self.gen_ids = [gen_id]        # wrap single int in a list
    @staticmethod
    def clean_ga_data(data_for_all_tasks):
        # Remove trials with no response
        data_for_all_tasks = data_for_all_tasks[data_for_all_tasks['Spikes by channel'].notna()]
        # Remove NaNs
        data_for_all_tasks = data_for_all_tasks[data_for_all_tasks['StimSpecId'].notna()]
        # Remove Catch
        data_for_all_tasks = data_for_all_tasks[data_for_all_tasks['ThumbnailPath'].apply(lambda x: x is not None)]
        return data_for_all_tasks

    def compile(self) -> pd.DataFrame:
        conn = Connection(context.ga_database)
        collector = TaskIdCollector(conn)
        task_ids = collector.collect_task_ids()

        fields = CachedTaskFieldList()
        fields.append(TaskIdField(conn))
        fields.append(StimSpecIdField(conn))
        fields.append(ParentIdField(conn))
        fields.append(LineageField(conn))
        fields.append(GenIdField(conn))
        fields.append(RegimeScoreField(conn))
        fields.append(StimTypeField(conn))
        fields.append(StimPathField(conn))
        fields.append(ThumbnailField(conn))
        fields.append(HypothesizedCompField(conn))
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

        data = self.clean_ga_data(data)
        return data

    def compile_and_export(self) -> pd.DataFrame:
        raise NotImplementedError("This analysis does not implement compile_and_export since it relies on raw data fields that are not pre-compiled. Use compile() instead to get the raw data.")
    def import_data(self, compiled_data: pd.DataFrame) -> pd.DataFrame:
        if compiled_data is None:
            compiled_data = import_from_repository(
                self.session_id,
                "ga",
                "GAStimInfo",
                self.response_table,
                mua_method=self.mua_method if self.response_table == "MUASpikeResponses" else None,
            )
        return compiled_data

    def analyze(self, channel, compiled_data: pd.DataFrame = None):
        # Filter by generation if requested
        data = compiled_data
        if self.gen_ids is not None and 'GenId' in data.columns:
            data = data[data['GenId'].isin(self.gen_ids)]

        channels = [f"A-{i:03d}" for i in CHANNEL_ORDER]

        gen_suffix = (
            f"_gen{'_'.join(str(g) for g in self.gen_ids)}" if self.gen_ids else ""
        )
        save_path = f"{self.save_path}/ga_raster_top_{self.top_n}{gen_suffix}.png"

        module = create_ga_raster_module(
            channels=channels,
            top_n=self.top_n,
            spike_data_col=self.spike_tstamps_col,
            spike_rate_col=self.spike_rates_col,
            time_range=(-0.2, 0.7),
            title="GA Top Stimuli Rasters by Channel",
            save_path=save_path,
        )

        pipeline = create_pipeline().then(module).build()
        result = pipeline.run(data)
        plt.show()
        return result


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
    rate on that channel) are shown as black vertical lines grouped by stimulus.

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
    the trials that belong to those stimuli.
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
            data['_rate'] = data[self.spike_rate_col].apply(
                lambda d: d.get(channel, 0) if isinstance(d, dict) else 0
            )

            avg_rates = (
                data.groupby('StimSpecId')['_rate']
                .mean()
                .nlargest(self.top_n)
            )
            top_stim_ids = avg_rates.index.tolist()  # ordered best → worst

            channel_data[channel] = {
                'data': data[data['StimSpecId'].isin(top_stim_ids)].copy(),
                'top_stim_ids': top_stim_ids,
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
    vertically grouped by stimulus, all in black.  A thin horizontal separator
    line is drawn between stimulus groups.
    """

    # Vertical pixels (in data units) allocated per trial row
    _TRIAL_HEIGHT = 1.0
    # Extra data-units of gap between stimulus groups (set to 0 to remove entirely)
    _GROUP_GAP = 0.5

    def __init__(self,
                 channels: List[str],
                 top_n: int,
                 time_range: Tuple[float, float],
                 title: Optional[str] = None):
        self.channels = channels
        self.top_n = top_n
        self.time_range = time_range
        self.title = title

    def compute(self, prepared_data: Dict[str, Any]) -> plt.Figure:
        channel_data = prepared_data['channel_data']
        spike_data_col = prepared_data['spike_data_col']

        n_channels = len(self.channels)

        # Height ratios proportional to how many trials + gaps each channel has
        height_ratios = []
        for ch in self.channels:
            n_trials = len(channel_data[ch]['data'])
            n_groups = len(channel_data[ch]['top_stim_ids'])
            height_ratios.append(max(
                n_trials * self._TRIAL_HEIGHT + n_groups * self._GROUP_GAP,
                3
            ))

        total_data_units = sum(height_ratios)
        # Scale figure height so each data-unit is roughly 0.15 inches
        fig_height = max(total_data_units * 0.15, 20)

        fig = plt.figure(figsize=(28, fig_height))
        gs = GridSpec(
            n_channels, 1,
            figure=fig,
            height_ratios=height_ratios,
            hspace=0.08,   # tight spacing between subplots
        )

        for row_idx, channel in enumerate(self.channels):
            ax = fig.add_subplot(gs[row_idx])
            self._plot_channel(
                ax=ax,
                channel=channel,
                ch_info=channel_data[channel],
                spike_data_col=spike_data_col,
                is_last_row=(row_idx == n_channels - 1),
            )

        if self.title:
            fig.suptitle(self.title, fontsize=13)

        return fig

    def _plot_channel(self,
                      ax: plt.Axes,
                      channel: str,
                      ch_info: Dict,
                      spike_data_col: str,
                      is_last_row: bool):
        data = ch_info['data']
        top_stim_ids = ch_info['top_stim_ids']

        y_pos = 0.0
        for stim_id in top_stim_ids:
            stim_trials = data[data['StimSpecId'] == stim_id]

            for _, trial in stim_trials.iterrows():
                spike_times = self._extract_spikes(trial, spike_data_col, channel)
                if spike_times:
                    ax.vlines(spike_times,
                              y_pos, y_pos + self._TRIAL_HEIGHT * 0.9,
                              color='black', lw=0.5)
                y_pos += self._TRIAL_HEIGHT

            y_pos += self._GROUP_GAP  # small gap between stimulus groups

        total_height = y_pos

        ax.set_xlim(*self.time_range)
        ax.set_ylim(-0.2, total_height + 0.2)
        ax.axvline(0, color='black', lw=2.0, linestyle='-')

        ax.set_ylabel(channel, rotation=0, ha='right', va='center', fontsize=22,
                      labelpad=60)
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
