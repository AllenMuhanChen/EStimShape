import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from matplotlib import pyplot as plt
import matplotlib.cm as cm
import numpy as np
import pandas as pd

from clat.compile.tstamp.cached_tstamp_fields import CachedFieldList
from clat.util import time_util
from clat.util.connection import Connection

from src.analysis.nafc.nafc_database_fields import (
    IsCorrectField, NoiseChanceField, NumRandDistractorsField,
    StimTypeField, ChoiceField, AnswerField, GenIdField,
    BaseMStickIdField, IsDeltaField, IsHypothesizedField,
    EStimEnabledField, EStimSpecIdField, EStimSpecField, EStimPolarityField
)
from src.analysis.nafc.psychometric_curves import collect_choice_trials, plot_psychometric_curve_on_ax


def calculate_p_value(observed_diff, permuted_diffs, test_side):
    if test_side == 'positive':
        return np.mean(permuted_diffs >= observed_diff)
    elif test_side == 'negative':
        return np.mean(permuted_diffs <= observed_diff)
    elif test_side == 'two-tailed':
        return np.mean(np.abs(permuted_diffs) >= np.abs(observed_diff))
    else:
        raise ValueError(f"Invalid test_side: {test_side}")


def run_permutation_test(data_for_perm, noise_levels, metric_field,
                         global_test_side, n_permutations=1000):
    data_for_perm = data_for_perm.copy()
    data_for_perm.loc[data_for_perm[metric_field] == "No Data", metric_field] = False
    data_for_perm[f'{metric_field}_bool'] = (data_for_perm[metric_field] == True)

    def calculate_sum_diff(data):
        sum_diff = 0
        level_diffs = {}
        for noise in noise_levels:
            noise_data = data[data['NoiseChance'] == noise]
            on = noise_data[noise_data['EStimEnabled'] == True]
            off = noise_data[noise_data['EStimEnabled'] == False]
            if len(on) > 0 and len(off) > 0:
                pct_on = 100 * on[f'{metric_field}_bool'].mean()
                pct_off = 100 * off[f'{metric_field}_bool'].mean()
                diff = pct_on - pct_off
                sum_diff += diff
                level_diffs[noise] = (pct_on, pct_off, diff, len(on), len(off))
        return sum_diff, level_diffs

    observed_sum, observed_level_diffs = calculate_sum_diff(data_for_perm)

    permuted_sums = []
    permuted_level_diffs = {noise: [] for noise in noise_levels}

    for _ in range(n_permutations):
        perm_data = data_for_perm.copy()
        for noise in noise_levels:
            mask = perm_data['NoiseChance'] == noise
            idx = perm_data[mask].index
            if len(idx) > 0:
                perm_data.loc[idx, 'EStimEnabled'] = (
                    perm_data.loc[idx, 'EStimEnabled'].sample(frac=1).values
                )
        perm_sum, perm_level_dict = calculate_sum_diff(perm_data)
        permuted_sums.append(perm_sum)
        for noise, (_, _, diff, _, _) in perm_level_dict.items():
            permuted_level_diffs[noise].append(diff)

    permuted_sums = np.array(permuted_sums)
    overall_p = calculate_p_value(observed_sum, permuted_sums, global_test_side)

    def sig_stars(p):
        if p < 0.001: return "***"
        if p < 0.01:  return "**"
        if p < 0.05:  return "*"
        return "ns"

    overall_sig = sig_stars(overall_p)

    for noise in list(observed_level_diffs.keys()):
        pct_on, pct_off, diff, n_on, n_off = observed_level_diffs[noise]
        perm_diffs = np.array(permuted_level_diffs[noise])
        p = calculate_p_value(diff, perm_diffs, global_test_side)
        observed_level_diffs[noise] = (pct_on, pct_off, diff, n_on, n_off, p, sig_stars(p))

    return observed_sum, overall_p, overall_sig, observed_level_diffs, permuted_sums


def plot_spec_id_panel(ax, stim_subset, estim_off_data, spec_ids, noise_levels,
                       metric_field, title, global_test_side, n_permutations=1000):
    """
    Plot psychometric curves for EStim OFF + each unique EStimSpecId,
    and return a stats text block.
    """
    # EStim OFF baseline
    if len(estim_off_data) > 0:
        plot_psychometric_curve_on_ax(
            estim_off_data, ax,
            title=title,
            show_n=True, num_rep_min=0,
            color='black', linestyle='--', linewidth=2,
            label=f'EStim OFF (n={len(estim_off_data)})',
            isCorrectColumnName=metric_field
        )

    # Color map for spec IDs
    colors = cm.tab10(np.linspace(0, 1, max(len(spec_ids), 1)))

    results_text = f"{title}\n{'=' * 50}\n\n"

    for color, spec_id in zip(colors, sorted(spec_ids)):
        spec_data = stim_subset[stim_subset['EStimSpecId'] == spec_id].copy()
        if len(spec_data) == 0:
            continue

        plot_psychometric_curve_on_ax(
            spec_data, ax,
            title=title,
            show_n=True, num_rep_min=0,
            color=color,
            label=f'SpecId={spec_id} (n={len(spec_data)})',
            isCorrectColumnName=metric_field
        )

        # Permutation test: this spec_id vs EStim OFF
        combined = pd.concat([spec_data, estim_off_data])
        results_text += f"SpecId={spec_id} vs OFF\n{'-' * 30}\n"

        if len(spec_data) > 0 and len(estim_off_data) > 0:
            np.random.seed(42)
            observed_sum, overall_p, overall_sig, level_diffs, _ = run_permutation_test(
                combined, noise_levels, metric_field, global_test_side, n_permutations
            )
            for noise in sorted(level_diffs.keys()):
                pct_on, pct_off, diff, n_on, n_off, p, sig = level_diffs[noise]
                results_text += f"  N{noise * 100:.0f}%: {diff:+.1f}% p={p:.3f}{sig}\n"
            results_text += f"  Overall: {observed_sum:+.1f}% p={overall_p:.4f} {overall_sig}\n\n"
        else:
            results_text += "  Insufficient data\n\n"

    ax.invert_xaxis()
    ax.set_ylim([0, 110])
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=7)

    return results_text


def main():
    # ============ CONFIGURATION ============
    conn = Connection("allen_estimshape_exp_260325_0")
    since_date = time_util.from_date_to_now(2024, 7, 10)
    start_gen_id = 2
    max_gen_id = float('inf')
    start_gen_id_estim_on = 0
    max_gen_id_estim_on = float('inf')

    isCorrectFieldName = "IsHypothesized"  # "IsCorrect" or "IsHypothesized"
    global_test_side = 'two-tailed'
    n_permutations = 1000
    # =======================================

    trial_tstamps = collect_choice_trials(conn, since_date)

    fields = CachedFieldList()
    fields.append(IsCorrectField(conn))
    fields.append(IsHypothesizedField(conn))
    fields.append(NoiseChanceField(conn))
    fields.append(NumRandDistractorsField(conn))
    fields.append(StimTypeField(conn))
    fields.append(ChoiceField(conn))
    fields.append(GenIdField(conn))
    fields.append(EStimEnabledField(conn))
    fields.append(EStimSpecIdField(conn))
    fields.append(BaseMStickIdField(conn))
    fields.append(IsDeltaField(conn))
    fields.append(EStimPolarityField(conn))

    data = fields.to_data(trial_tstamps)
    data = data[(data['GenId'] >= start_gen_id) & (data['GenId'] <= max_gen_id)]
    data_exp = data[data['StimType'] == 'EStimShapeVariantsDeltaNAFCStim']

    # Split by IsDelta
    data_delta = data_exp[data_exp['IsDelta'] == True].copy()
    data_variant = data_exp[data_exp['IsDelta'] == False].copy()

    # EStim ON subsets (respecting gen_id filter)
    def estim_on(df):
        return df[(df['EStimEnabled'] == True) &
                  (df['GenId'] >= start_gen_id_estim_on) &
                  (df['GenId'] <= max_gen_id_estim_on)].copy()

    data_delta_on = estim_on(data_delta)
    data_delta_off = data_delta[data_delta['EStimEnabled'] == False].copy()

    data_variant_on = estim_on(data_variant)
    data_variant_off = data_variant[data_variant['EStimEnabled'] == False].copy()

    # Unique spec IDs (EStim ON only — OFF rows have no meaningful SpecId)
    delta_spec_ids = data_delta_on['EStimSpecId'].dropna().unique()
    variant_spec_ids = data_variant_on['EStimSpecId'].dropna().unique()

    noise_levels = sorted(data_exp['NoiseChance'].unique())
    metric_name = "ACCURACY" if isCorrectFieldName == "IsCorrect" else "% HYPOTHESIZED"

    # ==================== FIGURE ====================
    fig, axes = plt.subplots(1, 3, figsize=(22, 7),
                             gridspec_kw={'width_ratios': [2, 2, 3]})

    # Left: Delta
    delta_stats = plot_spec_id_panel(
        axes[0], data_delta_on, data_delta_off,
        delta_spec_ids, noise_levels,
        isCorrectFieldName,
        title=f'{metric_name}: Delta by EStimSpecId',
        global_test_side=global_test_side,
        n_permutations=n_permutations
    )

    # Middle: Variant
    variant_stats = plot_spec_id_panel(
        axes[1], data_variant_on, data_variant_off,
        variant_spec_ids, noise_levels,
        isCorrectFieldName,
        title=f'{metric_name}: Variant by EStimSpecId',
        global_test_side=global_test_side,
        n_permutations=n_permutations
    )

    # Right: Stats text
    full_stats = (
        f"PERMUTATION TEST ({global_test_side})\n"
        f"n_permutations={n_permutations}  metric={isCorrectFieldName}\n"
        f"{'=' * 50}\n\n"
        + delta_stats + "\n" + variant_stats
        + "\n* p<0.05, ** p<0.01, *** p<0.001"
    )

    axes[2].text(0.02, 0.98, full_stats,
                 transform=axes[2].transAxes, fontsize=6,
                 verticalalignment='top', fontfamily='monospace',
                 bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    axes[2].axis('off')

    plt.tight_layout()
    fig.suptitle(f'{metric_name} by EStimSpecId — {isCorrectFieldName}', fontsize=14, y=1.02)
    plt.show()


if __name__ == '__main__':
    main()