from __future__ import annotations

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

        # Attach a scalar 'Response' column for the requested channel
        compiled_data = compiled_data.copy()
        if self.spike_rates_col == 'GA Response':
            compiled_data['Response'] = compiled_data['GA Response']
        elif isinstance(channel, list):
            def sum_channels(x):
                if not isinstance(x, dict):
                    return 0
                return sum(x.get(ch, 0) for ch in channel)
            compiled_data['Response'] = compiled_data[self.spike_rates_col].apply(sum_channels)
        else:
            compiled_data['Response'] = compiled_data[self.spike_rates_col].apply(
                lambda x: x.get(channel, 0) if isinstance(x, dict) else 0
            )

        baseline_data = compiled_data[compiled_data['StimType'] == 'BASELINE'].copy()

        if baseline_data.empty:
            print("No BASELINE stimuli found in the data.")
            return None

        if 'ParentId' not in baseline_data.columns:
            print("Warning: ParentId not in data — cannot link baseline stims to their "
                  "gen-1 parent responses. Aborting.")
            return None

        # Average over trial repeats: one value per (ParentId, Lineage, GenId)
        avg_baseline = (baseline_data
                        .groupby(['ParentId', 'Lineage', 'GenId'])['Response']
                        .mean()
                        .reset_index())

        # Gen-1 reference: look up each parent's actual response from gen-1 data.
        # The baseline stims' ParentIds point to the original gen-1 regime-zero stims.
        gen1_avg = (compiled_data[compiled_data['GenId'] == 1]
                    .groupby('StimSpecId')['Response']
                    .mean()
                    .rename('Gen1Response'))

        avg_baseline['Gen1Response'] = avg_baseline['ParentId'].map(gen1_avg)

        channel_label = ', '.join(channel) if isinstance(channel, list) else channel
        channel_str = '_'.join(channel) if isinstance(channel, list) else channel

        fig = self._plot_baseline_curves(avg_baseline, channel_label)

        save_file = f"{self.save_path}/{channel_str}_baseline_response_curves.png"
        fig.savefig(save_file, dpi=150, bbox_inches='tight')
        print(f"Saved baseline plot to {save_file}")
        plt.show()
        return fig

    def _plot_baseline_curves(self, avg_baseline: pd.DataFrame, channel_label: str) -> plt.Figure:
        """
        For each lineage subplot:
          x-axis  = baseline stim rank, sorted by gen-1 response (lowest → highest)
          y-axis  = avg response
          lines   = one per generation (gen-1 = straight ascending line by construction)
        """
        lineages = sorted(avg_baseline['Lineage'].unique())
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
        fig.suptitle(f'Baseline Stimulus Response Profiles Across Generations\n'
                     f'Channel: {channel_label}',
                     fontsize=14, y=1.01)

        for idx, lineage in enumerate(lineages):
            row, col = divmod(idx, n_cols)
            ax = axes[row][col]

            lin_data = avg_baseline[avg_baseline['Lineage'] == lineage].copy()

            # Determine x-axis ordering: rank each ParentId by its gen-1 response
            parent_gen1 = (lin_data[['ParentId', 'Gen1Response']]
                           .drop_duplicates('ParentId')
                           .sort_values('Gen1Response')
                           .reset_index(drop=True))
            parent_gen1['StimRank'] = range(1, len(parent_gen1) + 1)
            rank_map = parent_gen1.set_index('ParentId')['StimRank']

            lin_data['StimRank'] = lin_data['ParentId'].map(rank_map)

            generations = sorted(lin_data['GenId'].unique())
            n_gens = len(generations)
            colors = cm.viridis(np.linspace(0, 1, max(n_gens, 1)))

            # Plot gen-1 reference line first (from parent_gen1)
            ax.plot(parent_gen1['StimRank'], parent_gen1['Gen1Response'],
                    marker='o', linewidth=2, markersize=5,
                    color='black', linestyle='--', label='Gen 1 (reference)', zorder=3)

            # Plot each subsequent generation
            for g_idx, gen_id in enumerate(generations):
                gen_data = lin_data[lin_data['GenId'] == gen_id].sort_values('StimRank')
                ax.plot(gen_data['StimRank'], gen_data['Response'],
                        marker='o', linewidth=1.5, markersize=4,
                        color=colors[g_idx], label=f'Gen {gen_id}')

            ax.set_title(f'Lineage {lineage}', fontsize=11)
            ax.set_xlabel('Baseline Stim (sorted by gen-1 response)')
            ax.set_ylabel('Avg Response')
            ax.set_xticks(parent_gen1['StimRank'])
            ax.legend(fontsize=7, loc='upper left')
            ax.grid(True, alpha=0.3)

        # Hide unused panels
        for idx in range(n_lineages, n_rows * n_cols):
            row, col = divmod(idx, n_cols)
            axes[row][col].set_visible(False)

        fig.tight_layout()
        return fig


if __name__ == "__main__":
    main()
