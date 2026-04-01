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

        # Normalization factor per generation: reference_mean / gen_baseline_mean
        # reference_mean = mean of the gen-1 regime-zero parents of baseline stims
        parent_ids = set(avg_baseline['ParentId'].unique())
        reference_mean = gen1_avg[gen1_avg.index.isin(parent_ids)].mean()
        gen_baseline_mean = avg_baseline.groupby('GenId')['Response'].mean()
        norm_factor = (reference_mean / gen_baseline_mean).reset_index()
        norm_factor.columns = ['GenId', 'NormFactor']

        # Average raw response per generation — experimental stims only (no BASELINE/CATCH)
        experimental = compiled_data[~compiled_data['StimType'].isin(['BASELINE', 'CATCH'])]
        avg_raw_per_gen = (experimental
                           .groupby('GenId')['Response']
                           .mean()
                           .reset_index()
                           .rename(columns={'Response': 'AvgRawResponse'}))

        # Normalized avg response per generation = avg_raw × norm_factor
        avg_norm_per_gen = avg_raw_per_gen.merge(norm_factor, on='GenId', how='left')
        avg_norm_per_gen['AvgNormResponse'] = (avg_norm_per_gen['AvgRawResponse']
                                               * avg_norm_per_gen['NormFactor'])

        channel_label = ', '.join(channel) if isinstance(channel, list) else channel
        channel_str = '_'.join(channel) if isinstance(channel, list) else channel

        fig = self._plot_baseline_curves(avg_baseline, gen1_avg, avg_catch,
                                         avg_raw_per_gen, avg_norm_per_gen,
                                         norm_factor, channel_label)

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
            avg_raw_per_gen: pd.DataFrame,
            avg_norm_per_gen: pd.DataFrame,
            norm_factor: pd.DataFrame,
            channel_label: str,
    ) -> plt.Figure:
        """
        Three subplots (wide | narrow | narrow):
          1. Baseline/catch response profiles per generation (x=stim rank, y=response)
          2. Avg raw response per generation (experimental stims only)
          3. Normalized avg response per generation + normalization factor (dual y-axis)
        """
        # --- shared x-axis for subplot 1: use gen-1 response value as x-position ---
        parent_gen1 = (avg_baseline[['ParentId', 'Gen1Response']]
                       .drop_duplicates('ParentId')
                       .sort_values('Gen1Response')
                       .reset_index(drop=True))
        # Map each ParentId to its gen-1 response value (used as x-coordinate)
        x_map = parent_gen1.set_index('ParentId')['Gen1Response']
        avg_baseline['StimX'] = avg_baseline['ParentId'].map(x_map)

        # Catch x-position: avg catch response in gen-1 (or leftmost position if unavailable)
        gen1_catch_val = avg_catch.loc[avg_catch['GenId'] == 1, 'AvgCatch']
        catch_x = gen1_catch_val.values[0] if len(gen1_catch_val) else (
            parent_gen1['Gen1Response'].min() - parent_gen1['Gen1Response'].std())

        all_generations = sorted(set(avg_baseline['GenId'].unique()) |
                                 set(avg_catch['GenId'].unique()))
        colors = cm.viridis(np.linspace(0, 1, max(len(all_generations), 1)))
        gen_color = {gen_id: colors[i] for i, gen_id in enumerate(all_generations)}

        fig, (ax, ax_raw, ax_norm) = plt.subplots(
            1, 3, figsize=(18, 5),
            gridspec_kw={'width_ratios': [3, 1, 1]}
        )
        fig.suptitle(f'Baseline & Catch Response Profiles Across Generations  |  Channel: {channel_label}',
                     fontsize=13)

        # --- Subplot 1: response profiles ---
        # Gen-1 reference: y = gen-1 response, x = gen-1 response → diagonal line
        gen1_catch_y = gen1_catch_val.values[0] if len(gen1_catch_val) else np.nan
        ax.plot([catch_x] + list(parent_gen1['Gen1Response']),
                [gen1_catch_y] + list(parent_gen1['Gen1Response']),
                marker='o', linewidth=2, markersize=5,
                color='black', linestyle='--', label='Gen 1 (reference)', zorder=3)

        for gen_id in all_generations:
            catch_row = avg_catch[avg_catch['GenId'] == gen_id]
            catch_val = catch_row['AvgCatch'].values[0] if len(catch_row) else np.nan
            gen_data = avg_baseline[avg_baseline['GenId'] == gen_id].sort_values('StimX')
            ax.plot([catch_x] + list(gen_data['StimX']),
                    [catch_val] + list(gen_data['Response']),
                    marker='o', linewidth=1.5, markersize=4,
                    color=gen_color[gen_id], label=f'Gen {gen_id}')

        # Tick at each gen-1 response value + catch
        tick_xs = [catch_x] + list(parent_gen1['Gen1Response'])
        tick_labels = [f'{catch_x:.1f}\n(catch)'] + [f'{v:.1f}' for v in parent_gen1['Gen1Response']]
        ax.set_xticks(tick_xs)
        ax.set_xticklabels(tick_labels, rotation=45, ha='right', fontsize=8)
        ax.set_xlabel('Gen-1 response (Hz)')
        ax.set_ylabel('Avg Response')
        ax.set_title('Baseline / Catch Profiles')
        ax.legend(fontsize=7, bbox_to_anchor=(1.01, 1), loc='upper left')
        ax.grid(True, alpha=0.3)

        # --- Subplot 2: avg raw response per generation ---
        ax_raw.plot(avg_raw_per_gen['GenId'], avg_raw_per_gen['AvgRawResponse'],
                    marker='o', linewidth=1.5, markersize=4, color='steelblue')
        ax_raw.set_xlabel('Generation')
        ax_raw.set_ylabel('Avg Raw Response')
        ax_raw.set_title('Avg Raw Response\nper Generation')
        ax_raw.grid(True, alpha=0.3)

        # --- Subplot 3: normalized avg response + normalization factor (dual y-axis) ---
        ax_norm.plot(avg_norm_per_gen['GenId'], avg_norm_per_gen['AvgNormResponse'],
                     marker='o', linewidth=1.5, markersize=4,
                     color='darkorange', label='Normalized response')
        ax_norm.set_xlabel('Generation')
        ax_norm.set_ylabel('Avg Normalized Response', color='darkorange')
        ax_norm.tick_params(axis='y', labelcolor='darkorange')
        ax_norm.set_title('Normalized Response &\nNormalization Factor')
        ax_norm.grid(True, alpha=0.3)

        ax_factor = ax_norm.twinx()
        ax_factor.plot(norm_factor['GenId'], norm_factor['NormFactor'],
                       marker='s', linewidth=1.5, markersize=4,
                       color='purple', linestyle='--', label='Norm factor')
        ax_factor.axhline(1.0, color='purple', linewidth=0.8, linestyle=':', alpha=0.6)
        ax_factor.set_ylabel('Normalization Factor', color='purple')
        ax_factor.tick_params(axis='y', labelcolor='purple')

        # Combined legend for subplot 3
        lines1, labels1 = ax_norm.get_legend_handles_labels()
        lines2, labels2 = ax_factor.get_legend_handles_labels()
        ax_norm.legend(lines1 + lines2, labels1 + labels2, fontsize=7, loc='upper right')

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
