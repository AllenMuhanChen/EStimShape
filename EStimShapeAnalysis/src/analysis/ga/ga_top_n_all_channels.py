from __future__ import annotations

from typing import List, Optional, Union

import pandas as pd
from clat.pipeline.pipeline_base_classes import create_pipeline
from matplotlib import pyplot as plt

from src.analysis.ga.ga_raster_analysis import CHANNEL_ORDER, GARasterAnalysis
from src.analysis.modules.grouped_stims_by_response import create_grouped_stimuli_module
from src.repository.export_to_repository import read_session_id_from_db_name
from src.startup import context


def main():
    analysis = GATopNAllChannelsAnalysis(top_n=10)
    session_id, _ = read_session_id_from_db_name(context.ga_database)
    compiled_data = None
    # compiled_data = analysis.compile()
    analysis.run(session_id, "raw", "ALL", compiled_data)


class GATopNAllChannelsAnalysis(GARasterAnalysis):
    """
    Plots a grid of thumbnails showing the top-N stimuli for each channel.

    Rows: all 32 channels in CHANNEL_ORDER.
    Columns: rank 1 … top_n, ordered best to worst by mean spike rate.
    Border color intensity reflects the mean spike rate for that stimulus on
    that channel (same convention as PlotTopNAnalysis).

    Inherits compile() / clean_ga_data() / import_data() from GARasterAnalysis
    so the same raw Intan spike data pipeline is reused.
    """
    logging_path = context.logging_path

    def __init__(self, top_n: int = 5, gen_id: Optional[Union[int, List[int]]] = None):
        super().__init__(top_n=top_n, gen_id=gen_id)

    def analyze(self, channel, compiled_data: pd.DataFrame = None):
        data = compiled_data.copy()

        # Optional generation filter
        if self.gen_ids is not None and 'GenId' in data.columns:
            data = data[data['GenId'].isin(self.gen_ids)]

        # Remove non-stimulus rows
        if 'StimType' in data.columns:
            data = data[~data['StimType'].isin(['CATCH', 'BASELINE'])]

        channels = [f"A-{i:03d}" for i in CHANNEL_ORDER]
        spike_rate_col = self.spike_rates_col  # 'Spike Rate by channel' for data_type='raw'

        # Build an exploded DataFrame: for each channel, replicate the trials of its
        # top-N stimuli and tag them with Channel + RankWithinChannel.
        blocks = []
        for rank_channel in channels:
            data['_rate'] = data[spike_rate_col].apply(
                lambda d, ch=rank_channel: d.get(ch, 0) if isinstance(d, dict) else 0
            )
            top_stim_ids = (
                data.groupby('StimSpecId')['_rate']
                .mean()
                .nlargest(self.top_n)
                .index
            )
            for rank, stim_id in enumerate(top_stim_ids, start=1):
                stim_trials = data[data['StimSpecId'] == stim_id].copy()
                stim_trials['Channel'] = rank_channel
                stim_trials['RankWithinChannel'] = rank
                stim_trials['ChannelSpikeRate'] = stim_trials[spike_rate_col].apply(
                    lambda d, ch=rank_channel: d.get(ch, 0) if isinstance(d, dict) else 0
                )
                blocks.append(stim_trials)

        data.drop(columns=['_rate'], inplace=True, errors='ignore')

        if not blocks:
            print("No data to plot.")
            return None

        exploded = pd.concat(blocks, ignore_index=True)

        gen_suffix = (
            f"_gen{'_'.join(str(g) for g in self.gen_ids)}" if self.gen_ids else ""
        )
        save_path = f"{self.save_path}/ga_top_{self.top_n}_all_channels{gen_suffix}.png"

        module = create_grouped_stimuli_module(
            response_rate_col='ChannelSpikeRate',
            path_col='ThumbnailPath',
            row_col='Channel',
            col_col='RankWithinChannel',
            title=f'Top {self.top_n} Stimuli per Channel',
            # filter_values also controls ordering: channels follow CHANNEL_ORDER,
            # ranks appear 1 … top_n left-to-right.
            filter_values={
                'Channel': channels,
                'RankWithinChannel': list(range(1, self.top_n + 1)),
            },
            # publish_mode=True never sets include_labels_for, so pass it explicitly.
            include_labels_for={"row"},
            save_path=save_path,
            publish_mode=True,
            subplot_spacing=(20, 0),
            module_name='ga_top_n_all_channels',
            border_width=30,
        )

        pipeline = create_pipeline().then(module).build()
        result = pipeline.run(exploded)
        plt.show()
        return result


if __name__ == "__main__":
    main()
