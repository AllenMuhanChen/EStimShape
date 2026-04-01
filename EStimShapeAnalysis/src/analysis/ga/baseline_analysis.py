from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib import cm

from src.analysis.ga.plot_top_n import PlotTopNAnalysis, compile
from src.repository.export_to_repository import read_session_id_from_db_name
from src.repository.import_from_repository import import_from_repository
from src.startup import context


def main():
    analysis = BaselineAnalysis()
    compiled_data = compile()
    session_id, _ = read_session_id_from_db_name(context.ga_database)
    channel = "GA"
    analysis.run(session_id, "GA", channel, compiled_data=compiled_data)


class BaselineAnalysis(PlotTopNAnalysis):

    def analyze(self, channel, compiled_data: pd.DataFrame = None):
        if compiled_data is None:
            compiled_data = import_from_repository(
                self.session_id,
                "ga",
                "GAStimInfo",
                self.response_table
            )

        baseline_data = compiled_data[compiled_data['StimType'] == 'BASELINE'].copy()

        if baseline_data.empty:
            print("No BASELINE stimuli found in the data.")
            return None

        # Extract scalar response for the given channel
        if self.spike_rates_col == 'GA Response':
            baseline_data['Response'] = baseline_data['GA Response']
        elif isinstance(channel, list):
            def sum_channels(x):
                if not isinstance(x, dict):
                    return 0
                return sum(x.get(ch, 0) for ch in channel)
            baseline_data['Response'] = baseline_data[self.spike_rates_col].apply(sum_channels)
        else:
            baseline_data['Response'] = baseline_data[self.spike_rates_col].apply(
                lambda x: x.get(channel, 0) if isinstance(x, dict) else 0
            )

        # Use ParentId to track the same baseline stim across generations.
        # Each BASELINE stim's parent_id points to its original gen-1 regime-zero stim,
        # so rows sharing a parent_id are the same baseline stim repeated over generations.
        if 'ParentId' in baseline_data.columns:
            stim_id_col = 'ParentId'
        else:
            print("Warning: ParentId not in data. Using StimSpecId; baseline stims will not be "
                  "linked across generations.")
            stim_id_col = 'StimSpecId'

        # Average over repeats within the same (stim identity, lineage, generation) group
        avg = (baseline_data
               .groupby([stim_id_col, 'Lineage', 'GenId'])['Response']
               .mean()
               .reset_index()
               .rename(columns={'Response': 'Avg Response'}))

        channel_label = ', '.join(channel) if isinstance(channel, list) else channel
        channel_str = '_'.join(channel) if isinstance(channel, list) else channel

        fig = self._plot_baseline_curves(avg, stim_id_col, channel_label)

        save_file = f"{self.save_path}/{channel_str}_baseline_response_curves.png"
        fig.savefig(save_file, dpi=150, bbox_inches='tight')
        print(f"Saved baseline plot to {save_file}")
        plt.show()
        return fig

    def _plot_baseline_curves(
            self,
            avg: pd.DataFrame,
            stim_id_col: str,
            channel_label: str,
    ) -> plt.Figure:
        lineages = sorted(avg['Lineage'].unique())
        n_lineages = len(lineages)

        if n_lineages == 0:
            fig, ax = plt.subplots()
            ax.text(0.5, 0.5, 'No data', ha='center', va='center')
            return fig

        n_cols = min(n_lineages, 3)
        n_rows = int(np.ceil(n_lineages / n_cols))

        fig, axes = plt.subplots(n_rows, n_cols,
                                 figsize=(6 * n_cols, 4 * n_rows),
                                 squeeze=False)
        fig.suptitle(f'Baseline Stimulus Responses Across Generations\nChannel: {channel_label}',
                     fontsize=14, y=1.01)

        colors = cm.tab10(np.linspace(0, 1, 10))

        for idx, lineage in enumerate(lineages):
            row, col = divmod(idx, n_cols)
            ax = axes[row][col]

            lin_data = avg[avg['Lineage'] == lineage]
            unique_stims = sorted(lin_data[stim_id_col].unique())

            for i, stim_id in enumerate(unique_stims):
                stim_data = lin_data[lin_data[stim_id_col] == stim_id].sort_values('GenId')
                color = colors[i % len(colors)]
                ax.plot(stim_data['GenId'], stim_data['Avg Response'],
                        marker='o', linewidth=1.5, markersize=4,
                        color=color, label=f"stim {i + 1} (id={stim_id})")

            ax.set_title(f'Lineage {lineage}', fontsize=11)
            ax.set_xlabel('Generation')
            ax.set_ylabel('Avg Response')
            ax.legend(fontsize=7, loc='upper left')
            ax.grid(True, alpha=0.3)

        # Hide any unused subplot panels
        for idx in range(n_lineages, n_rows * n_cols):
            row, col = divmod(idx, n_cols)
            axes[row][col].set_visible(False)

        fig.tight_layout()
        return fig


if __name__ == "__main__":
    main()
