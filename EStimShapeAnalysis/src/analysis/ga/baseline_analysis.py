from __future__ import annotations

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib import cm

from src.analysis.ga.plot_top_n import PlotTopNAnalysis
from src.repository.export_to_repository import read_session_id_from_db_name
from src.repository.good_channels import read_cluster_channels
from src.repository.import_from_repository import import_from_repository
from src.startup import context


def main():
    analysis = BaselineAnalysis()
    compiled_data = analysis.compile()
    session_id, _ = read_session_id_from_db_name(context.ga_database)
    # session_id = "260327_0"
    channel = read_cluster_channels(session_id)
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

        # Average over trial repeats: one value per (ParentId, GenId)
        avg_baseline = (baseline_data
                        .groupby(['ParentId', 'GenId'])['Response']
                        .mean()
                        .reset_index())

        # Gen-1 reference: look up each parent's actual response from gen-1 data.
        # The baseline stims' ParentIds point to the original gen-1 regime-zero stims.
        gen1_avg = (compiled_data[compiled_data['GenId'] == 1]
                    .groupby('StimSpecId')['Response']
                    .mean()
                    .rename('Gen1Response'))

        avg_baseline['Gen1Response'] = avg_baseline['ParentId'].map(gen1_avg)

        # Average CATCH response per generation
        catch_data = compiled_data[compiled_data['StimType'] == 'CATCH']
        avg_catch = (catch_data
                     .groupby('GenId')['Response']
                     .mean()
                     .rename('AvgCatch')
                     .reset_index())

        channel_label = ', '.join(channel) if isinstance(channel, list) else channel
        channel_str = '_'.join(channel) if isinstance(channel, list) else channel

        fig = self._plot_baseline_curves(avg_baseline, gen1_avg, avg_catch, channel_label)

        save_file = f"{self.save_path}/{channel_str}_baseline_response_curves.png"
        fig.savefig(save_file, dpi=150, bbox_inches='tight')
        print(f"Saved baseline plot to {save_file}")
        plt.show()
        return fig

    def _plot_baseline_curves(
            self,
            avg_baseline: pd.DataFrame,
            gen1_avg: pd.Series,
            avg_catch: pd.DataFrame,
            channel_label: str,
    ) -> plt.Figure:
        """
        Single plot:
          x = 0          : avg CATCH response for that generation
          x = 1..N       : baseline stim rank, sorted by gen-1 response (lowest → highest)
          y-axis         : avg response
          lines          : one per generation; gen-1 (black dashed) is straight ascending
                           across x=1..N by construction
        """
        # Rank all ParentIds by their gen-1 response (baseline stims start at x=1)
        parent_gen1 = (avg_baseline[['ParentId', 'Gen1Response']]
                       .drop_duplicates('ParentId')
                       .sort_values('Gen1Response')
                       .reset_index(drop=True))
        parent_gen1['StimRank'] = range(1, len(parent_gen1) + 1)
        rank_map = parent_gen1.set_index('ParentId')['StimRank']
        avg_baseline['StimRank'] = avg_baseline['ParentId'].map(rank_map)

        all_generations = sorted(set(avg_baseline['GenId'].unique()) |
                                 set(avg_catch['GenId'].unique()))
        colors = cm.viridis(np.linspace(0, 1, max(len(all_generations), 1)))
        gen_color = {gen_id: colors[i] for i, gen_id in enumerate(all_generations)}

        fig, ax = plt.subplots(figsize=(10, 5))
        fig.suptitle(f'Baseline & Catch Response Profiles Across Generations\n'
                     f'Channel: {channel_label}', fontsize=14)

        # Gen-1 reference line (black dashed): catch at x=0, then baseline stims x=1..N
        gen1_catch = avg_catch.loc[avg_catch['GenId'] == 1, 'AvgCatch']
        catch_x = [0]
        catch_y_gen1 = [gen1_catch.values[0] if len(gen1_catch) else np.nan]
        baseline_x = list(parent_gen1['StimRank'])
        baseline_y_gen1 = list(parent_gen1['Gen1Response'])
        ax.plot(catch_x + baseline_x,
                catch_y_gen1 + baseline_y_gen1,
                marker='o', linewidth=2, markersize=5,
                color='black', linestyle='--', label='Gen 1 (reference)', zorder=3)

        # One line per generation (gen ≥ 2)
        for gen_id in all_generations:
            # Catch point at x=0
            catch_row = avg_catch[avg_catch['GenId'] == gen_id]
            catch_val = catch_row['AvgCatch'].values[0] if len(catch_row) else np.nan

            # Baseline points at x=1..N
            gen_data = avg_baseline[avg_baseline['GenId'] == gen_id].sort_values('StimRank')

            xs = [0] + list(gen_data['StimRank'])
            ys = [catch_val] + list(gen_data['Response'])

            ax.plot(xs, ys,
                    marker='o', linewidth=1.5, markersize=4,
                    color=gen_color[gen_id], label=f'Gen {gen_id}')

        # X-axis tick labels: "Catch" at 0, stim ranks at 1..N
        tick_positions = [0] + list(parent_gen1['StimRank'])
        tick_labels = ['Catch'] + [str(r) for r in parent_gen1['StimRank']]
        ax.set_xticks(tick_positions)
        ax.set_xticklabels(tick_labels)
        ax.set_xlabel('Stimulus (sorted by gen-1 response)')
        ax.set_ylabel('Avg Response')
        ax.legend(fontsize=8, bbox_to_anchor=(1.01, 1), loc='upper left')
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        return fig

    def clean_ga_data(self, data_for_all_tasks):
        # Remove trials with no response
        data_for_all_tasks = data_for_all_tasks[data_for_all_tasks['GA Response'].notna()]
        # Remove NaNs
        data_for_all_tasks = data_for_all_tasks[data_for_all_tasks['StimSpecId'].notna()]

        # DON'T REMOVE CATCH
        return data_for_all_tasks


if __name__ == "__main__":
    main()
