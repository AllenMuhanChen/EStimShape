import sys
from pathlib import Path

# Add the parent directory to the path to import from the original file
# Adjust this path based on where you save this file relative to the original
sys.path.insert(0, str(Path(__file__).parent))

from matplotlib import pyplot as plt
from clat.compile.tstamp.cached_tstamp_fields import CachedFieldList
from clat.util import time_util
from clat.util.connection import Connection

from src.analysis.nafc.nafc_database_fields import (
    IsCorrectField, NoiseChanceField, NumRandDistractorsField,
    StimTypeField, ChoiceField, AnswerField, GenIdField, EStimEnabledField,
    BaseMStickIdField, IsDeltaField, IsHypothesizedField
)
from src.analysis.nafc.psychometric_curves import collect_choice_trials, plot_psychometric_curve_on_ax


def filter_by_num_distractors(data, num_distractors):
    """Filter data by NumRandDistractors value."""
    return data[data['NumRandDistractors'] == num_distractors]


def calculate_p_value(observed_diff, permuted_diffs, test_side):
    """
    Calculate p-value based on test side.

    Parameters:
    -----------
    observed_diff : float
        Observed difference (estim - no_estim)
    permuted_diffs : np.array
        Array of permuted differences
    test_side : str
        'positive' (estim > no_estim), 'negative' (estim < no_estim), or 'two-tailed'

    Returns:
    --------
    float : p-value
    """
    import numpy as np

    if test_side == 'positive':
        # One-tailed: testing if estim > no_estim
        p_value = np.mean(permuted_diffs >= observed_diff)
    elif test_side == 'negative':
        # One-tailed: testing if estim < no_estim
        p_value = np.mean(permuted_diffs <= observed_diff)
    elif test_side == 'two-tailed':
        # Two-tailed: testing if |estim - no_estim| is significant
        p_value = np.mean(np.abs(permuted_diffs) >= np.abs(observed_diff))
    else:
        raise ValueError(f"Invalid test_side: {test_side}. Must be 'positive', 'negative', or 'two-tailed'")

    return p_value


def get_test_description(test_side, metric):
    """Get human-readable description of test."""
    if test_side == 'positive':
        return f"One-tailed (EStim increases {metric})"
    elif test_side == 'negative':
        return f"One-tailed (EStim decreases {metric})"
    elif test_side == 'two-tailed':
        return f"Two-tailed (EStim effect in either direction)"
    else:
        return f"Unknown test: {test_side}"


def run_permutation_test(data_for_perm, noise_levels, metric_field, global_test_side, per_level_test_sides,
                         n_permutations=10000):
    """Run permutation test for a given metric."""
    import numpy as np

    # Convert "No Data" to False
    data_for_perm = data_for_perm.copy()
    data_for_perm.loc[data_for_perm[metric_field] == "No Data", metric_field] = False
    data_for_perm[f'{metric_field}_bool'] = (data_for_perm[metric_field] == True)

    def calculate_sum_diff(data, noise_levels):
        """Calculate sum of (estim_pct - no_estim_pct) across all noise levels"""
        sum_diff = 0
        valid_levels = 0
        level_diffs = {}

        for noise in noise_levels:
            noise_data = data[data['NoiseChance'] == noise]
            estim_on_data = noise_data[noise_data['EStimEnabled'] == True]
            estim_off_data = noise_data[noise_data['EStimEnabled'] == False]

            if len(estim_on_data) > 0 and len(estim_off_data) > 0:
                estim_pct = 100 * estim_on_data[f'{metric_field}_bool'].mean()
                no_estim_pct = 100 * estim_off_data[f'{metric_field}_bool'].mean()
                diff = estim_pct - no_estim_pct
                sum_diff += diff
                valid_levels += 1
                level_diffs[noise] = (estim_pct, no_estim_pct, diff,
                                      len(estim_on_data), len(estim_off_data))

        return sum_diff, valid_levels, level_diffs

    # Calculate observed sum of differences
    observed_sum, n_levels, observed_level_diffs = calculate_sum_diff(data_for_perm, noise_levels)

    # Store permutations
    permuted_sums = []
    permuted_level_diffs = {noise: [] for noise in noise_levels}

    for i in range(n_permutations):
        perm_data = data_for_perm.copy()

        for noise in noise_levels:
            noise_mask = perm_data['NoiseChance'] == noise
            noise_indices = perm_data[noise_mask].index

            if len(noise_indices) > 0:
                shuffled_estim = perm_data.loc[noise_indices, 'EStimEnabled'].sample(frac=1).values
                perm_data.loc[noise_indices, 'EStimEnabled'] = shuffled_estim

        perm_sum, _, perm_level_dict = calculate_sum_diff(perm_data, noise_levels)
        permuted_sums.append(perm_sum)

        for noise, (_, _, diff, _, _) in perm_level_dict.items():
            permuted_level_diffs[noise].append(diff)

    permuted_sums = np.array(permuted_sums)

    # Calculate overall p-value
    overall_p_value = calculate_p_value(observed_sum, permuted_sums, global_test_side)

    if overall_p_value < 0.001:
        overall_sig = "***"
    elif overall_p_value < 0.01:
        overall_sig = "**"
    elif overall_p_value < 0.05:
        overall_sig = "*"
    else:
        overall_sig = "ns"

    # Calculate per-level p-values
    for noise in observed_level_diffs.keys():
        observed_diff = observed_level_diffs[noise][2]
        perm_diffs = np.array(permuted_level_diffs[noise])
        level_test_side = per_level_test_sides.get(noise, global_test_side)
        p = calculate_p_value(observed_diff, perm_diffs, level_test_side)

        if p < 0.001:
            level_sig = "***"
        elif p < 0.01:
            level_sig = "**"
        elif p < 0.05:
            level_sig = "*"
        else:
            level_sig = "ns"

        estim_pct, no_estim_pct, diff, n_on, n_off = observed_level_diffs[noise]
        observed_level_diffs[noise] = (estim_pct, no_estim_pct, diff, n_on, n_off, p, level_sig, level_test_side)

    return observed_sum, overall_p_value, overall_sig, observed_level_diffs, permuted_sums


def main():
    import pandas as pd
    import numpy as np

    # Database connection
    conn = Connection("allen_estimshape_exp_260107_0")

    # Time range
    since_date = time_util.from_date_to_now(2024, 7, 10)
    start_gen_id = 8
    max_gen_id = 11
    start_gen_id_estim_on = 0
    max_gen_id_estim_on = float('inf')

    # PERMUTATION TEST PARAMETERS
    global_test_side = 'two-tailed'
    per_level_test_sides = {1.0: "positive", 0.9: "positive", 0.8: "positive", 0.75: "negative"}
    if per_level_test_sides is None:
        per_level_test_sides = {}

    # Collect trial timestamps
    trial_tstamps = collect_choice_trials(conn, since_date)

    # Set up fields to collect - BOTH IsCorrect AND IsHypothesized
    fields = CachedFieldList()
    fields.append(IsCorrectField(conn))
    fields.append(IsHypothesizedField(conn))
    fields.append(NoiseChanceField(conn))
    fields.append(NumRandDistractorsField(conn))
    fields.append(StimTypeField(conn))
    fields.append(ChoiceField(conn))
    fields.append(GenIdField(conn))
    fields.append(EStimEnabledField(conn))
    fields.append(BaseMStickIdField(conn))
    fields.append(IsDeltaField(conn))

    # Convert to dataframe
    data = fields.to_data(trial_tstamps)

    # Filter data by GenId
    data = data[(data['GenId'] >= start_gen_id) & (data['GenId'] <= max_gen_id)]

    # Split datasets
    data_procedural = data[data['StimType'] == 'EStimShapeProceduralBehavioralStim']
    data_exp = data[data['StimType'] == 'EStimShapeVariantsDeltaNAFCStim']

    # Get colormap
    colors = plt.colormaps['tab10'].colors

    # Split by IsDelta
    data_exp_delta = data_exp[data_exp['IsDelta'] == True]
    data_exp_variant = data_exp[data_exp['IsDelta'] == False]

    # Apply EStim filters
    data_exp_delta_estim_on = data_exp_delta[(data_exp_delta['EStimEnabled'] == True) &
                                             (data_exp_delta['GenId'] >= start_gen_id_estim_on) &
                                             (data_exp_delta['GenId'] <= max_gen_id_estim_on)]
    data_exp_delta_estim_off = data_exp_delta[data_exp_delta['EStimEnabled'] == False]

    data_exp_variant_estim_on = data_exp_variant[(data_exp_variant['EStimEnabled'] == True) &
                                                 (data_exp_variant['GenId'] >= start_gen_id_estim_on) &
                                                 (data_exp_variant['GenId'] <= max_gen_id_estim_on)]
    data_exp_variant_estim_off = data_exp_variant[data_exp_variant['EStimEnabled'] == False]

    noise_levels = sorted(data_exp['NoiseChance'].unique())

    # ==================== FIGURE 1: ACCURACY ====================
    fig1, axes1 = plt.subplots(1, 2, figsize=(16, 6))

    # ACCURACY: Delta vs Variant EStim ON vs OFF
    if len(data_exp_delta_estim_on) > 0:
        plot_psychometric_curve_on_ax(
            data_exp_delta_estim_on, axes1[0],
            title='ACCURACY: Delta vs Variant, EStim ON vs OFF',
            show_n=True, num_rep_min=0,
            color='red', linewidth=2.5, marker='s', markersize=6, linestyle='-',
            label=f'Delta EStim ON (n={len(data_exp_delta_estim_on)})')

    if len(data_exp_delta_estim_off) > 0:
        plot_psychometric_curve_on_ax(
            data_exp_delta_estim_off, axes1[0],
            title='ACCURACY: Delta vs Variant, EStim ON vs OFF',
            show_n=True, num_rep_min=0,
            color='pink', linewidth=2.5, marker='o', markersize=6, linestyle='--',
            label=f'Delta EStim OFF (n={len(data_exp_delta_estim_off)})')

    if len(data_exp_variant_estim_on) > 0:
        plot_psychometric_curve_on_ax(
            data_exp_variant_estim_on, axes1[0],
            title='ACCURACY: Delta vs Variant, EStim ON vs OFF',
            show_n=True, num_rep_min=0,
            color='blue', linewidth=2.5, marker='s', markersize=6, linestyle='-',
            label=f'Variant EStim ON (n={len(data_exp_variant_estim_on)})')

    if len(data_exp_variant_estim_off) > 0:
        plot_psychometric_curve_on_ax(
            data_exp_variant_estim_off, axes1[0],
            title='ACCURACY: Delta vs Variant, EStim ON vs OFF',
            show_n=True, num_rep_min=0,
            color='lightblue', linewidth=2.5, marker='o', markersize=6, linestyle='--',
            label=f'Variant EStim OFF (n={len(data_exp_variant_estim_off)})')

    axes1[0].invert_xaxis()
    axes1[0].set_ylim([0, 110])
    axes1[0].grid(True, alpha=0.3)
    axes1[0].legend()

    # ACCURACY: Statistics
    results_text = "PERMUTATION TEST - ACCURACY\n"
    results_text += "=" * 50 + "\n\n"

    # Delta accuracy test
    results_text += "DELTA STIMULI\n" + "=" * 50 + "\n"
    data_delta_for_perm = pd.concat([data_exp_delta_estim_on, data_exp_delta_estim_off])

    if len(data_exp_delta_estim_on) > 0 and len(data_exp_delta_estim_off) > 0:
        np.random.seed(42)
        observed_sum_delta, overall_p_delta, overall_sig_delta, level_diffs_delta, _ = \
            run_permutation_test(data_delta_for_perm, noise_levels, 'IsCorrect', global_test_side, per_level_test_sides)

        for noise in sorted(level_diffs_delta.keys()):
            estim_pct, no_estim_pct, diff, n_on, n_off, p, sig, test_side = level_diffs_delta[noise]
            results_text += f"N{noise * 100:.0f}%: {diff:+.1f}% p={p:.3f}{sig}\n"
        results_text += f"Overall: {observed_sum_delta:+.1f}% p={overall_p_delta:.4f} {overall_sig_delta}\n"
    else:
        results_text += "Insufficient data\n"

    results_text += "\n"

    # Variant accuracy test
    results_text += "VARIANT STIMULI\n" + "=" * 50 + "\n"
    data_variant_for_perm = pd.concat([data_exp_variant_estim_on, data_exp_variant_estim_off])

    if len(data_exp_variant_estim_on) > 0 and len(data_exp_variant_estim_off) > 0:
        np.random.seed(43)
        observed_sum_variant, overall_p_variant, overall_sig_variant, level_diffs_variant, _ = \
            run_permutation_test(data_variant_for_perm, noise_levels, 'IsCorrect', global_test_side,
                                 per_level_test_sides)

        for noise in sorted(level_diffs_variant.keys()):
            estim_pct, no_estim_pct, diff, n_on, n_off, p, sig, test_side = level_diffs_variant[noise]
            results_text += f"N{noise * 100:.0f}%: {diff:+.1f}% p={p:.3f}{sig}\n"
        results_text += f"Overall: {observed_sum_variant:+.1f}% p={overall_p_variant:.4f} {overall_sig_variant}\n"
    else:
        results_text += "Insufficient data\n"

    results_text += "\n* p<0.05, ** p<0.01, *** p<0.001"
    results_text += f"\nTest: {get_test_description(global_test_side, 'accuracy')}"

    axes1[1].text(0.05, 0.95, results_text,
                  transform=axes1[1].transAxes, fontsize=7,
                  verticalalignment='top', fontfamily='monospace',
                  bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    axes1[1].axis('off')

    plt.tight_layout()
    fig1.suptitle('ACCURACY ANALYSIS', fontsize=16, y=1.02)

    # ==================== FIGURE 2: HYPOTHESIZED ====================
    fig2, axes2 = plt.subplots(1, 2, figsize=(16, 6))

    # For hypothesized plots, we need to rename the column temporarily
    # Create temporary dataframes with IsHypothesized as IsCorrect
    data_exp_delta_estim_on_hyp = data_exp_delta_estim_on.copy()
    data_exp_delta_estim_on_hyp['IsCorrect'] = data_exp_delta_estim_on_hyp['IsHypothesized']

    data_exp_delta_estim_off_hyp = data_exp_delta_estim_off.copy()
    data_exp_delta_estim_off_hyp['IsCorrect'] = data_exp_delta_estim_off_hyp['IsHypothesized']

    data_exp_variant_estim_on_hyp = data_exp_variant_estim_on.copy()
    data_exp_variant_estim_on_hyp['IsCorrect'] = data_exp_variant_estim_on_hyp['IsHypothesized']

    data_exp_variant_estim_off_hyp = data_exp_variant_estim_off.copy()
    data_exp_variant_estim_off_hyp['IsCorrect'] = data_exp_variant_estim_off_hyp['IsHypothesized']

    # HYPOTHESIZED: Delta vs Variant EStim ON vs OFF
    if len(data_exp_delta_estim_on_hyp) > 0:
        plot_psychometric_curve_on_ax(
            data_exp_delta_estim_on_hyp, axes2[0],
            title='% HYPOTHESIZED: Delta vs Variant, EStim ON vs OFF',
            show_n=True, num_rep_min=0,
            color='red', linewidth=2.5, marker='s', markersize=6, linestyle='-',
            label=f'Delta EStim ON (n={len(data_exp_delta_estim_on_hyp)})')

    if len(data_exp_delta_estim_off_hyp) > 0:
        plot_psychometric_curve_on_ax(
            data_exp_delta_estim_off_hyp, axes2[0],
            title='% HYPOTHESIZED: Delta vs Variant, EStim ON vs OFF',
            show_n=True, num_rep_min=0,
            color='pink', linewidth=2.5, marker='o', markersize=6, linestyle='--',
            label=f'Delta EStim OFF (n={len(data_exp_delta_estim_off_hyp)})')

    if len(data_exp_variant_estim_on_hyp) > 0:
        plot_psychometric_curve_on_ax(
            data_exp_variant_estim_on_hyp, axes2[0],
            title='% HYPOTHESIZED: Delta vs Variant, EStim ON vs OFF',
            show_n=True, num_rep_min=0,
            color='blue', linewidth=2.5, marker='s', markersize=6, linestyle='-',
            label=f'Variant EStim ON (n={len(data_exp_variant_estim_on_hyp)})')

    if len(data_exp_variant_estim_off_hyp) > 0:
        plot_psychometric_curve_on_ax(
            data_exp_variant_estim_off_hyp, axes2[0],
            title='% HYPOTHESIZED: Delta vs Variant, EStim ON vs OFF',
            show_n=True, num_rep_min=0,
            color='lightblue', linewidth=2.5, marker='o', markersize=6, linestyle='--',
            label=f'Variant EStim OFF (n={len(data_exp_variant_estim_off_hyp)})')

    axes2[0].invert_xaxis()
    axes2[0].set_ylim([0, 110])
    axes2[0].grid(True, alpha=0.3)
    axes2[0].legend()

    # HYPOTHESIZED: Statistics
    results_text = "PERMUTATION TEST - % HYPOTHESIZED\n"
    results_text += "=" * 50 + "\n\n"

    # Delta hypothesized test
    results_text += "DELTA STIMULI\n" + "=" * 50 + "\n"

    if len(data_exp_delta_estim_on) > 0 and len(data_exp_delta_estim_off) > 0:
        np.random.seed(42)
        observed_sum_delta, overall_p_delta, overall_sig_delta, level_diffs_delta, _ = \
            run_permutation_test(data_delta_for_perm, noise_levels, 'IsHypothesized', global_test_side,
                                 per_level_test_sides)

        for noise in sorted(level_diffs_delta.keys()):
            estim_pct, no_estim_pct, diff, n_on, n_off, p, sig, test_side = level_diffs_delta[noise]
            results_text += f"N{noise * 100:.0f}%: {diff:+.1f}% p={p:.3f}{sig}\n"
        results_text += f"Overall: {observed_sum_delta:+.1f}% p={overall_p_delta:.4f} {overall_sig_delta}\n"
    else:
        results_text += "Insufficient data\n"

    results_text += "\n"

    # Variant hypothesized test
    results_text += "VARIANT STIMULI\n" + "=" * 50 + "\n"

    if len(data_exp_variant_estim_on) > 0 and len(data_exp_variant_estim_off) > 0:
        np.random.seed(43)
        observed_sum_variant, overall_p_variant, overall_sig_variant, level_diffs_variant, _ = \
            run_permutation_test(data_variant_for_perm, noise_levels, 'IsHypothesized', global_test_side,
                                 per_level_test_sides)

        for noise in sorted(level_diffs_variant.keys()):
            estim_pct, no_estim_pct, diff, n_on, n_off, p, sig, test_side = level_diffs_variant[noise]
            results_text += f"N{noise * 100:.0f}%: {diff:+.1f}% p={p:.3f}{sig}\n"
        results_text += f"Overall: {observed_sum_variant:+.1f}% p={overall_p_variant:.4f} {overall_sig_variant}\n"
    else:
        results_text += "Insufficient data\n"

    results_text += "\n* p<0.05, ** p<0.01, *** p<0.001"
    results_text += f"\nTest: {get_test_description(global_test_side, '% hypothesized')}"

    axes2[1].text(0.05, 0.95, results_text,
                  transform=axes2[1].transAxes, fontsize=7,
                  verticalalignment='top', fontfamily='monospace',
                  bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    axes2[1].axis('off')

    plt.tight_layout()
    fig2.suptitle('% HYPOTHESIZED ANALYSIS', fontsize=16, y=1.02)

    plt.show()


if __name__ == '__main__':
    main()