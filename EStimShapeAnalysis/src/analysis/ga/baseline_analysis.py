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
    analysis = RankBaselineAnalysis(data_type="mua")
    compiled_data = None
    # compiled_data = analysis.compile_and_export()
    session_id, _ = read_session_id_and_date_from_db_name(context.ga_database)
    # session_id = "260426_0"
    channel = read_cluster_channels(session_id)
    # channel = "A-002"
    # channel = ["A-021"]
    analysis.run(session_id, channel=channel, compiled_data=compiled_data)


class BaselineAnalysis(PlotTopNAnalysis):

    def _check_responses_present(self, compiled_data):
        """Fail with an actionable message (instead of a later KeyError) when the
        import returned nothing usable."""
        n = 0 if compiled_data is None else len(compiled_data)
        if self.spike_rates_col == 'GA Response':
            col_ok = compiled_data is not None and 'GA Response' in compiled_data.columns
        else:
            col_ok = compiled_data is not None and self.spike_rates_col in compiled_data.columns
        if not col_ok:
            method = (f", mua_method={self.mua_method!r}"
                      if self.response_table == "MUASpikeResponses" else "")
            raise ValueError(
                f"No '{self.spike_rates_col}' column in imported data ({n} rows). "
                f"response_table={self.response_table!r}{method}. This usually means that "
                f"table has no rows for session {self.session_id!r}'s task_ids "
                f"(see the import diagnostics printed above). Compile+export this session "
                f"first (e.g. analysis.compile_and_export()), or check the mua_method.")

    def analyze(self, channel, compiled_data: pd.DataFrame = None):
        if compiled_data is None:
            compiled_data = import_from_repository(
                self.session_id,
                "ga",
                "GAStimInfo",
                self.response_table,
                mua_method=self.mua_method if self.response_table == "MUASpikeResponses" else None,
            )

        self._check_responses_present(compiled_data)

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
        return float(np.interp(r, bN_sorted, factors))

    def clean_ga_data(self, data_for_all_tasks):
        # Remove trials with no response
        data_for_all_tasks = data_for_all_tasks[data_for_all_tasks['GA Response'].notna()]
        # Remove NaNs
        data_for_all_tasks = data_for_all_tasks[data_for_all_tasks['StimSpecId'].notna()]

        # DON'T REMOVE CATCH
        return data_for_all_tasks


class RankBaselineAnalysis(BaselineAnalysis):
    """
    Mirrors RankBaselineNormalizeResponseProcessor with multi-gen averaging:
    pairs Gen-N and Gen-k baselines by rank, averages correction factors
    across all prior generations k=1..N-1, and produces detailed plots showing
    how each comparison contributes and how individual stims are corrected.
    """

    def analyze(self, channel, compiled_data=None):
        if compiled_data is None:
            compiled_data = import_from_repository(
                self.session_id, "ga", "GAStimInfo", self.response_table,
                mua_method=self.mua_method if self.response_table == "MUASpikeResponses" else None,
            )
        self._check_responses_present(compiled_data)
        compiled_data = compiled_data.copy()
        if self.spike_rates_col == 'GA Response':
            compiled_data['Response'] = compiled_data['GA Response']
        elif isinstance(channel, list):
            compiled_data['Response'] = compiled_data[self.spike_rates_col].apply(
                lambda x: sum(x.get(ch, 0) for ch in channel) if isinstance(x, dict) else 0
            )
        else:
            compiled_data['Response'] = compiled_data[self.spike_rates_col].apply(
                lambda x: x.get(channel, 0) if isinstance(x, dict) else 0
            )

        baseline_data = compiled_data[compiled_data['StimType'] == 'BASELINE'].copy()
        if baseline_data.empty:
            print("No BASELINE stimuli found.")
            return None
        if 'ParentId' not in baseline_data.columns:
            print("Warning: ParentId not in data. Aborting.")
            return None

        avg_baseline = (baseline_data
                        .groupby(['ParentId', 'GenId'])['Response']
                        .mean().reset_index())
        gen1_avg = (compiled_data[compiled_data['GenId'] == 1]
                    .groupby('StimSpecId')['Response'].mean().rename('Gen1Response'))
        avg_baseline['Gen1Response'] = avg_baseline['ParentId'].map(gen1_avg)

        avg_catch = (compiled_data[compiled_data['StimType'] == 'CATCH']
                     .groupby('GenId')['Response'].mean().rename('AvgCatch').reset_index())

        parent_ids = set(avg_baseline['ParentId'].unique())
        gen1_dict = gen1_avg[gen1_avg.index.isin(parent_ids)].to_dict()

        baselines_by_gen = (avg_baseline
                            .groupby('GenId')
                            .apply(lambda df: df.set_index('ParentId')['Response'].to_dict())
                            .to_dict())

        experimental = compiled_data[~compiled_data['StimType'].isin(['BASELINE', 'CATCH'])].copy()

        def compute_factors(row):
            gen_id = int(row['GenId'])
            r = row['Response']
            bN_dict = baselines_by_gen.get(gen_id, {})
            per_k = {}
            for k in range(1, gen_id):
                bk_dict = gen1_dict if k == 1 else baselines_by_gen.get(k, {})
                if bk_dict:
                    per_k[k] = self._interpolated_factor(r, bN_dict, bk_dict)
            avg_f = float(np.mean(list(per_k.values()))) if per_k else 1.0
            return pd.Series({'NormFactor': avg_f, 'PerKFactors': per_k})

        factor_data = experimental.apply(compute_factors, axis=1)
        experimental['NormFactor'] = factor_data['NormFactor']
        experimental['PerKFactors'] = factor_data['PerKFactors']
        experimental['NormResponse'] = experimental['Response'] * experimental['NormFactor']

        avg_raw_per_gen = (experimental.groupby('GenId')['Response'].mean().reset_index()
                           .rename(columns={'Response': 'AvgRawResponse'}))
        avg_norm_per_gen = (experimental.groupby('GenId')['NormResponse'].mean().reset_index()
                            .rename(columns={'NormResponse': 'AvgNormResponse'}))
        avg_norm_per_gen = avg_raw_per_gen.merge(avg_norm_per_gen, on='GenId', how='left')
        norm_factor_df = (experimental.groupby('GenId')['NormFactor'].mean().reset_index())
        norm_factor_df.columns = ['GenId', 'NormFactor']

        channel_label = ', '.join(channel) if isinstance(channel, list) else channel
        channel_str = '_'.join(channel) if isinstance(channel, list) else channel

        fig1 = self._plot_baseline_curves(avg_baseline, gen1_avg, avg_catch,
                                          avg_raw_per_gen, avg_norm_per_gen,
                                          norm_factor_df, channel_label)
        save1 = f"{self.save_path}/{channel_str}_baseline_response_curves.png"
        fig1.savefig(save1, dpi=150, bbox_inches='tight')
        print(f"Saved baseline curves to {save1}")

        fig2 = self._plot_multi_gen_factor_curves(baselines_by_gen, gen1_dict,
                                                   experimental, channel_label)
        save2 = f"{self.save_path}/{channel_str}_multi_gen_factor_curves.png"
        fig2.savefig(save2, dpi=150, bbox_inches='tight')
        print(f"Saved multi-gen factor curves to {save2}")

        fig3 = self._plot_individual_stim_application(experimental, baselines_by_gen,
                                                       gen1_dict, channel_label)
        save3 = f"{self.save_path}/{channel_str}_individual_stim_application.png"
        fig3.savefig(save3, dpi=150, bbox_inches='tight')
        print(f"Saved individual stim application to {save3}")

        plt.show()
        return fig1

    @staticmethod
    def _interpolated_factor(r: float, bN_dict: dict, gen1_dict: dict) -> float:
        if r == 0:
            return 1.0
        bN_sorted   = np.sort(list(bN_dict.values()))
        gen1_sorted = np.sort(list(gen1_dict.values()))
        n = min(len(bN_sorted), len(gen1_sorted))
        if n < 2:
            return 1.0
        bN_sorted   = bN_sorted[:n]
        gen1_sorted = gen1_sorted[:n]
        factors     = gen1_sorted / bN_sorted
        return float(np.interp(r, bN_sorted, factors))

    def _plot_multi_gen_factor_curves(
            self,
            baselines_by_gen: dict,
            gen1_dict: dict,
            experimental: pd.DataFrame,
            channel_label: str,
    ) -> plt.Figure:
        """
        One subplot per target generation N (≥2).  Each subplot shows:
          - a thin colored line per reference generation k (Gen-N vs Gen-k)
          - a bold black average curve
          - control-point scatter dots for each comparison
          - per-k factor values for each experimental stim (gray tick marks)
          - average factor applied to each stim (red star)
        """
        all_gens = sorted(baselines_by_gen.keys())
        target_gens = [g for g in all_gens if g >= 2]
        if not target_gens:
            fig, ax = plt.subplots()
            ax.text(0.5, 0.5, 'No generations ≥ 2', ha='center', va='center',
                    transform=ax.transAxes)
            return fig

        n_cols = min(3, len(target_gens))
        n_rows = (len(target_gens) + n_cols - 1) // n_cols
        fig, axes = plt.subplots(n_rows, n_cols,
                                 figsize=(6 * n_cols, 4 * n_rows), squeeze=False)
        fig.suptitle(f'Rank-Based Multi-Gen Factor Breakdown  |  Channel: {channel_label}',
                     fontsize=13)

        for idx, gen_N in enumerate(target_gens):
            ax = axes[idx // n_cols][idx % n_cols]
            bN_dict = baselines_by_gen.get(gen_N, {})
            bN_sorted_all = np.sort(list(bN_dict.values()))

            ref_gens = list(range(1, gen_N))
            ref_colors = cm.cool(np.linspace(0, 1, max(len(ref_gens), 1)))

            factor_curves = []

            for ref_idx, k in enumerate(ref_gens):
                bk_dict = gen1_dict if k == 1 else baselines_by_gen.get(k, {})
                if not bk_dict:
                    continue
                bk_sorted = np.sort(list(bk_dict.values()))
                n = min(len(bN_sorted_all), len(bk_sorted))
                if n < 2:
                    continue
                bN_n = bN_sorted_all[:n]
                bk_n = bk_sorted[:n]
                factors = bk_n / bN_n

                x_dense = np.linspace(bN_n[0], bN_n[-1], 200)
                y_dense = np.interp(x_dense, bN_n, factors)

                color = ref_colors[ref_idx]
                ref_label = 'Gen 1 (regime-zero)' if k == 1 else f'Gen {k}'
                ax.plot(x_dense, y_dense, linewidth=1.2, color=color, alpha=0.65,
                        label=f'vs {ref_label}')
                ax.scatter(bN_n, factors, color=color, s=25, alpha=0.8, zorder=3)
                factor_curves.append((bN_n, factors))

            if factor_curves:
                x_min = min(c[0][0] for c in factor_curves)
                x_max = max(c[0][-1] for c in factor_curves)
                x_grid = np.linspace(x_min, x_max, 300)
                avg_y = np.mean([np.interp(x_grid, b, f) for b, f in factor_curves], axis=0)
                ax.plot(x_grid, avg_y, linewidth=2.5, color='black', zorder=5, label='Average')

            exp_gen = experimental[experimental['GenId'] == gen_N]
            for _, stim_row in exp_gen.iterrows():
                r = stim_row['Response']
                per_k = stim_row['PerKFactors']
                avg_f = stim_row['NormFactor']
                if per_k:
                    ax.scatter([r] * len(per_k), list(per_k.values()),
                               marker='|', s=80, color='dimgray', zorder=5, linewidths=2)
                ax.scatter(r, avg_f, marker='*', s=140, color='red', zorder=7)

            ax.axhline(1.0, color='gray', linestyle='--', linewidth=0.8, alpha=0.6)
            ax.set_title(f'Gen {gen_N}  ({len(exp_gen)} experimental stims)')
            ax.set_xlabel('Gen-N response (Hz)')
            ax.set_ylabel('Correction factor')
            ax.legend(fontsize=6, loc='upper right')
            ax.grid(True, alpha=0.3)

        for idx in range(len(target_gens), n_rows * n_cols):
            axes[idx // n_cols][idx % n_cols].set_visible(False)

        fig.tight_layout()
        return fig

    def _plot_individual_stim_application(
            self,
            experimental: pd.DataFrame,
            baselines_by_gen: dict,
            gen1_dict: dict,
            channel_label: str,
    ) -> plt.Figure:
        """
        Two panels:
          Left  — x=raw response, y=correction factor applied; average correction
                  curve overlaid for each gen; each stim shown as a dot.
          Right — x=raw response, y=normalized response; y=x identity line shows
                  how far each stim was moved by the correction.
        """
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        fig.suptitle(f'Individual Stim Correction Applied  |  Channel: {channel_label}',
                     fontsize=13)

        all_gens = sorted(experimental['GenId'].unique())
        colors = cm.viridis(np.linspace(0, 1, max(len(all_gens), 1)))
        gen_color = {g: colors[i] for i, g in enumerate(all_gens)}

        for gen_N in all_gens:
            if gen_N < 2:
                continue
            exp_gen = experimental[experimental['GenId'] == gen_N]
            color = gen_color[gen_N]

            bN_dict = baselines_by_gen.get(gen_N, {})
            bN_sorted_all = np.sort(list(bN_dict.values()))
            curve_parts = []
            for k in range(1, int(gen_N)):
                bk_dict = gen1_dict if k == 1 else baselines_by_gen.get(k, {})
                if not bk_dict:
                    continue
                bk_sorted = np.sort(list(bk_dict.values()))
                n = min(len(bN_sorted_all), len(bk_sorted))
                if n < 2:
                    continue
                bN_n = bN_sorted_all[:n]
                bk_n = bk_sorted[:n]
                curve_parts.append((bN_n, bk_n / bN_n))

            if curve_parts:
                x_min = min(c[0][0] for c in curve_parts)
                x_max = max(c[0][-1] for c in curve_parts)
                x_grid = np.linspace(x_min, x_max, 300)
                avg_curve = np.mean([np.interp(x_grid, b, f) for b, f in curve_parts], axis=0)
                ax1.plot(x_grid, avg_curve, linewidth=1.8, color=color, alpha=0.45)

            ax1.scatter(exp_gen['Response'], exp_gen['NormFactor'],
                        color=color, s=55, zorder=4, label=f'Gen {gen_N}',
                        edgecolors='white', linewidths=0.5)
            for _, row in exp_gen.iterrows():
                ax1.annotate(
                    f'{row["Response"]:.0f}→×{row["NormFactor"]:.2f}',
                    (row['Response'], row['NormFactor']),
                    textcoords='offset points', xytext=(4, 4),
                    fontsize=6, color=color, alpha=0.9,
                )

        ax1.axhline(1.0, color='gray', linestyle='--', linewidth=0.8, label='factor = 1')
        ax1.set_xlabel('Raw Response (Hz)')
        ax1.set_ylabel('Correction Factor Applied')
        ax1.set_title('Correction Factor per Stim\n(curve = average, dots = stims)')
        ax1.legend(fontsize=7)
        ax1.grid(True, alpha=0.3)

        all_vals = pd.concat([experimental['Response'],
                               experimental['NormResponse']]).dropna()
        max_val = all_vals.max() if not all_vals.empty else 1.0
        ax2.plot([0, max_val], [0, max_val], 'k--', linewidth=1,
                 label='y = x  (no correction)', zorder=2)

        for gen_N in all_gens:
            exp_gen = experimental[experimental['GenId'] == gen_N]
            color = gen_color[gen_N]
            ax2.scatter(exp_gen['Response'], exp_gen['NormResponse'],
                        color=color, s=45, alpha=0.85, label=f'Gen {gen_N}',
                        edgecolors='white', linewidths=0.5, zorder=3)
            for _, row in exp_gen.iterrows():
                if abs(row['NormResponse'] - row['Response']) > 0.5:
                    ax2.annotate('', xy=(row['Response'], row['NormResponse']),
                                 xytext=(row['Response'], row['Response']),
                                 arrowprops=dict(arrowstyle='->', color=color,
                                                 lw=1.0, alpha=0.45))

        ax2.set_xlabel('Raw Response (Hz)')
        ax2.set_ylabel('Normalized Response (Hz)')
        ax2.set_title('Raw vs Normalized Response\n(arrows show correction direction)')
        ax2.legend(fontsize=7)
        ax2.grid(True, alpha=0.3)

        fig.tight_layout()
        return fig


if __name__ == "__main__":
    main()
