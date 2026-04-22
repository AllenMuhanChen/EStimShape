from __future__ import annotations

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib import cm

from src.analysis.ga.plot_top_n import PlotTopNAnalysis
from src.repository.export_to_repository import read_session_id_and_date_from_db_name
from src.repository.good_channels import read_cluster_channels
from src.repository.import_from_repository import import_from_repository
from src.startup import context


def main():
    analysis = BaselineAnalysis()
    compiled_data = None
    # compiled_data = analysis.compile_and_export()
    session_id, _ = read_session_id_and_date_from_db_name(context.ga_database)
    # session_id = "260327_0"
    channel = read_cluster_channels(session_id)
    # channel = ["A-021"]
    analysis.run(session_id, "raw", channel, compiled_data=compiled_data)


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

        # Build gen1_dict and bN_by_gen to mirror the response processor exactly
        parent_ids = set(avg_baseline['ParentId'].unique())
        gen1_dict = gen1_avg[gen1_avg.index.isin(parent_ids)].to_dict()

        bN_by_gen = (avg_baseline
                     .groupby('GenId')
                     .apply(lambda df: df.set_index('ParentId')['Response'].to_dict())
                     .to_dict())

        # Apply interpolated factor per experimental stim — identical to processor logic
        experimental = compiled_data[~compiled_data['StimType'].isin(['BASELINE', 'CATCH'])].copy()
        experimental['NormFactor'] = experimental.apply(
            lambda row: self._interpolated_factor(
                row['Response'],
                bN_by_gen.get(row['GenId'], {}),
                gen1_dict
            ), axis=1
        )
        experimental['NormResponse'] = experimental['Response'] * experimental['NormFactor']

        avg_raw_per_gen = (experimental
                           .groupby('GenId')['Response']
                           .mean()
                           .reset_index()
                           .rename(columns={'Response': 'AvgRawResponse'}))

        avg_norm_per_gen = (experimental
                            .groupby('GenId')['NormResponse']
                            .mean()
                            .reset_index()
                            .rename(columns={'NormResponse': 'AvgNormResponse'}))
        avg_norm_per_gen = avg_raw_per_gen.merge(avg_norm_per_gen, on='GenId', how='left')

        norm_factor = (experimental
                       .groupby('GenId')['NormFactor']
                       .mean()
                       .reset_index())
        norm_factor.columns = ['GenId', 'NormFactor']

        channel_label = ', '.join(channel) if isinstance(channel, list) else channel
        channel_str = '_'.join(channel) if isinstance(channel, list) else channel

        fig = self._plot_baseline_curves(avg_baseline, gen1_avg, avg_catch,
                                         avg_raw_per_gen, avg_norm_per_gen,
                                         norm_factor, channel_label)

        save_file = f"{self.save_path}/{channel_str}_baseline_response_curves.png"
        fig.savefig(save_file, dpi=150, bbox_inches='tight')
        print(f"Saved baseline plot to {save_file}")

        fig2 = self._plot_interpolation_normalization(avg_baseline, channel_label)
        save_file2 = f"{self.save_path}/{channel_str}_interpolation_normalization.png"
        fig2.savefig(save_file2, dpi=150, bbox_inches='tight')
        print(f"Saved interpolation normalization plot to {save_file2}")

        fig3 = self._plot_normalization_comparison(avg_baseline, experimental, channel_label)
        save_file3 = f"{self.save_path}/{channel_str}_normalization_comparison.png"
        fig3.savefig(save_file3, dpi=150, bbox_inches='tight')
        print(f"Saved normalization comparison plot to {save_file3}")

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

        for gen_id in [g for g in all_generations if g > 1]:
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

    def _plot_interpolation_normalization(
            self,
            avg_baseline: pd.DataFrame,
            channel_label: str,
    ) -> plt.Figure:
        """
        For each gen N (≥ 2) plot the correction-factor curve that the processor would
        apply: x = response value, y = interpolated factor (gen1/bN at control points,
        clamped at boundaries). A flat line at 1.0 means no correction needed.
        """
        gen1_dict: dict[int, float] = (
            avg_baseline[['ParentId', 'Gen1Response']]
            .drop_duplicates('ParentId')
            .set_index('ParentId')['Gen1Response']
            .to_dict()
        )

        all_gens = sorted(avg_baseline['GenId'].unique())
        target_gens = [g for g in all_gens if g >= 2]
        colors = cm.viridis(np.linspace(0, 1, max(len(all_gens), 1)))
        gen_color = {g: colors[i] for i, g in enumerate(all_gens)}

        fig, ax = plt.subplots(figsize=(10, 5))
        fig.suptitle(f'Interpolated Correction Factor Curve per Generation\n'
                     f'Channel: {channel_label}', fontsize=13)

        ax.axhline(1.0, color='black', linestyle='--', linewidth=1.2,
                   label='factor = 1 (no correction)', zorder=5)

        for gen_id in target_gens:
            bN_dict: dict[int, float] = (
                avg_baseline[avg_baseline['GenId'] == gen_id]
                .set_index('ParentId')['Response']
                .to_dict()
            )
            common = sorted(set(bN_dict) & set(gen1_dict))
            if len(common) < 2:
                continue

            bN_arr   = np.array([bN_dict[p]  for p in common])
            gen1_arr = np.array([gen1_dict[p] for p in common])
            sort_N       = np.argsort(bN_arr)
            bN_sorted    = bN_arr[sort_N]
            gen1_sorted  = gen1_arr[sort_N]
            factors      = gen1_sorted / bN_sorted

            # Sample densely across the control-point range (np.interp clamps outside)
            x_dense = np.linspace(bN_sorted[0], bN_sorted[-1], 200)
            y_dense = np.interp(x_dense, bN_sorted, factors)

            color = gen_color[gen_id]
            ax.plot(x_dense, y_dense, linewidth=1.5, color=color, label=f'Gen {gen_id}')
            ax.scatter(bN_sorted, factors, color=color, s=30, zorder=4)
            for bN_val, factor_val, gen1_val in zip(bN_sorted, factors, gen1_sorted):
                ax.annotate(f'{gen1_val:.1f}', (bN_val, factor_val),
                            textcoords='offset points', xytext=(3, 3),
                            fontsize=6, color=color, alpha=0.8)

        ax.set_xlabel('Response value in gen N (Hz)')
        ax.set_ylabel('Correction factor (gen-1 / gen-N)')
        ax.legend(fontsize=8, bbox_to_anchor=(1.01, 1), loc='upper left')
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        return fig

    @staticmethod
    def _interpolated_factor(r: float,
                             bN_dict: dict,
                             gen1_dict: dict) -> float:
        if r == 0:
            return 1.0
        common = sorted(set(bN_dict) & set(gen1_dict))
        if len(common) < 2:
            return 1.0
        bN_arr = np.array([bN_dict[p] for p in common])
        gen1_arr = np.array([gen1_dict[p] for p in common])
        sort_idx = np.argsort(bN_arr)
        bN_sorted = bN_arr[sort_idx]
        gen1_sorted = gen1_arr[sort_idx]
        factors = gen1_sorted / bN_sorted
        if r > bN_sorted[-1]:
            return float(factors[int(np.argmax(gen1_sorted))])
        return float(np.interp(r, bN_sorted, factors))

    def _plot_normalization_comparison(
            self,
            avg_baseline: pd.DataFrame,
            experimental: pd.DataFrame,
            channel_label: str,
    ) -> plt.Figure:
        """
        For each gen N (≥ 2) plot the correction-factor curve under three strategies:
          - Clamped (current): np.interp, flat outside control-point range
          - Log-space extrapolation: extends endpoint slope in log(factor) space
          - Linear extrapolation: extends endpoint slope directly in factor space
        The distribution of actual experimental responses is overlaid as a rug plot
        so you can see which extrapolation zone actually matters.
        """
        gen1_dict: dict[int, float] = (
            avg_baseline[['ParentId', 'Gen1Response']]
            .drop_duplicates('ParentId')
            .set_index('ParentId')['Gen1Response']
            .to_dict()
        )

        all_gens = sorted(avg_baseline['GenId'].unique())
        target_gens = [g for g in all_gens if g >= 2]
        n_gens = len(target_gens)
        if n_gens == 0:
            fig, ax = plt.subplots()
            ax.text(0.5, 0.5, 'No gen ≥ 2 data', ha='center', va='center')
            return fig

        fig, axes = plt.subplots(1, n_gens, figsize=(6 * n_gens, 5), squeeze=False)
        fig.suptitle(
            f'Normalization Method Comparison per Generation\nChannel: {channel_label}',
            fontsize=13
        )

        method_styles = {
            'Clamped (old)':           {'color': 'steelblue',   'ls': '-'},
            'Best-ref clamp (new)':    {'color': 'crimson',     'ls': '-'},
            'Log-space extrapolation': {'color': 'darkorange',  'ls': '--'},
            'Linear extrapolation':    {'color': 'forestgreen', 'ls': '-.'},
        }

        for col_idx, gen_id in enumerate(target_gens):
            ax = axes[0][col_idx]
            bN_dict: dict[int, float] = (
                avg_baseline[avg_baseline['GenId'] == gen_id]
                .set_index('ParentId')['Response']
                .to_dict()
            )
            common = sorted(set(bN_dict) & set(gen1_dict))
            if len(common) < 2:
                ax.text(0.5, 0.5, 'Too few control points', ha='center', va='center')
                ax.set_title(f'Gen {gen_id}')
                continue

            bN_arr   = np.array([bN_dict[p]  for p in common])
            ref_arr  = np.array([gen1_dict[p] for p in common])
            sort_idx = np.argsort(bN_arr)
            bN_sorted  = bN_arr[sort_idx]
            ref_sorted = ref_arr[sort_idx]
            factors    = ref_sorted / bN_sorted

            # Extend x-axis 30% beyond control-point range on each side
            span = bN_sorted[-1] - bN_sorted[0]
            pad  = 0.30 * span if span > 0 else 1.0
            x_min = max(0.0, bN_sorted[0]  - pad)
            x_max = bN_sorted[-1] + pad
            x_dense = np.linspace(x_min, x_max, 400)

            # Old: clamp to the factor at the highest-Gen-N baseline
            y_clamped = np.interp(x_dense, bN_sorted, factors)

            # New: clamp to the factor at the highest-ref (Gen-1) baseline
            best_ref_factor = float(factors[int(np.argmax(ref_sorted))])
            y_best_ref = np.where(x_dense > bN_sorted[-1], best_ref_factor,
                                  np.interp(x_dense, bN_sorted, factors))

            # Log-space extrapolation
            log_f = np.log(np.maximum(factors, 1e-9))
            y_log = np.empty_like(x_dense)
            for i, xv in enumerate(x_dense):
                if xv <= bN_sorted[0]:
                    slope = (log_f[1] - log_f[0]) / (bN_sorted[1] - bN_sorted[0])
                    y_log[i] = np.exp(log_f[0] + slope * (xv - bN_sorted[0]))
                elif xv >= bN_sorted[-1]:
                    slope = (log_f[-1] - log_f[-2]) / (bN_sorted[-1] - bN_sorted[-2])
                    y_log[i] = np.exp(log_f[-1] + slope * (xv - bN_sorted[-1]))
                else:
                    y_log[i] = np.exp(float(np.interp(xv, bN_sorted, log_f)))

            # Linear extrapolation in factor space
            y_lin = np.empty_like(x_dense)
            for i, xv in enumerate(x_dense):
                if xv <= bN_sorted[0]:
                    slope = (factors[1] - factors[0]) / (bN_sorted[1] - bN_sorted[0])
                    y_lin[i] = factors[0] + slope * (xv - bN_sorted[0])
                elif xv >= bN_sorted[-1]:
                    slope = (factors[-1] - factors[-2]) / (bN_sorted[-1] - bN_sorted[-2])
                    y_lin[i] = factors[-1] + slope * (xv - bN_sorted[-1])
                else:
                    y_lin[i] = float(np.interp(xv, bN_sorted, factors))

            for label, y_vals in [
                ('Clamped (old)', y_clamped),
                ('Best-ref clamp (new)', y_best_ref),
                ('Log-space extrapolation', y_log),
                ('Linear extrapolation', y_lin),
            ]:
                style = method_styles[label]
                ax.plot(x_dense, y_vals, linewidth=1.8,
                        color=style['color'], linestyle=style['ls'], label=label)

            # Control points
            ax.scatter(bN_sorted, factors, color='black', s=40, zorder=5,
                       label='Control points')

            # Shade extrapolation zones
            ax.axvspan(x_min, bN_sorted[0],  alpha=0.08, color='gray', label='Extrapolated zone')
            ax.axvspan(bN_sorted[-1], x_max, alpha=0.08, color='gray')

            # Rug plot of experimental responses for this gen
            exp_gen = experimental[experimental['GenId'] == gen_id]['Response'].dropna()
            if not exp_gen.empty:
                rug_y = ax.get_ylim()[0]
                ax.plot(exp_gen, np.full(len(exp_gen), rug_y),
                        '|', color='black', alpha=0.3, markersize=8,
                        label='Experimental responses')

            ax.axhline(1.0, color='black', linestyle=':', linewidth=0.9, alpha=0.6)
            ax.set_title(f'Gen {gen_id}')
            ax.set_xlabel('Response in gen N (Hz)')
            ax.set_ylabel('Correction factor')
            ax.legend(fontsize=7)
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
