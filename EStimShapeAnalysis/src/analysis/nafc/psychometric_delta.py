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
    StimTypeField, ChoiceField, AnswerField, GenIdField, EStimEnabledFieldLegacy,
    BaseMStickIdField, IsDeltaField, IsHypothesizedField, EStimEnabledField, EStimSpecIdField, EStimSpecField,
    EStimPolarityField
)
from src.analysis.nafc.psychometric_curves import collect_choice_trials, plot_psychometric_curve_on_ax


def calculate_p_value(observed_diff, permuted_diffs, test_side):
    """
    Calculate p-value based on test side.
    """
    import numpy as np

    if test_side == 'positive':
        p_value = np.mean(permuted_diffs >= observed_diff)
    elif test_side == 'negative':
        p_value = np.mean(permuted_diffs <= observed_diff)
    elif test_side == 'two-tailed':
        p_value = np.mean(np.abs(permuted_diffs) >= np.abs(observed_diff))
    else:
        raise ValueError(f"Invalid test_side: {test_side}")

    return p_value


def get_test_description(test_side, metric):
    """Get human-readable description of test."""
    if test_side == 'positive':
        return f"One-tailed (EStim increases {metric})"
    elif test_side == 'negative':
        return f"One-tailed (EStim decreases {metric})"
    elif test_side == 'two-tailed':
        return f"Two-tailed (EStim effect)"
    else:
        return f"Unknown test: {test_side}"


def run_permutation_test(data_for_perm, noise_levels, metric_field, global_test_side, per_level_test_sides,
                         stimulus_type=None, polarity=None, n_permutations=1000):
    """
    Run permutation test for a given metric.

    Parameters:
    -----------
    stimulus_type : str, optional
        'delta' or 'variant'
    polarity : str, optional
        'anodic', 'cathodic', or 'combined'
    """
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

    # Calculate per-level p-values with hierarchical lookup
    for noise in observed_level_diffs.keys():
        observed_diff = observed_level_diffs[noise][2]
        perm_diffs = np.array(permuted_level_diffs[noise])

        # Hierarchical lookup for test side
        level_test_side = None

        # Try most specific: (stimulus_type, polarity, noise)
        if stimulus_type and polarity:
            level_test_side = per_level_test_sides.get((stimulus_type, polarity, noise))

        # Try: (stimulus_type, polarity) - all noise levels for this combo
        if level_test_side is None and stimulus_type and polarity:
            level_test_side = per_level_test_sides.get((stimulus_type, polarity))

        # Try: (stimulus_type, noise) - all polarities for this stimulus at this noise
        if level_test_side is None and stimulus_type:
            level_test_side = per_level_test_sides.get((stimulus_type, noise))

        # Try: (polarity, noise) - all stimuli for this polarity at this noise
        if level_test_side is None and polarity:
            level_test_side = per_level_test_sides.get((polarity, noise))

        # Try: just noise level (backward compatible)
        if level_test_side is None:
            level_test_side = per_level_test_sides.get(noise)

        # Try: just stimulus_type
        if level_test_side is None and stimulus_type:
            level_test_side = per_level_test_sides.get((stimulus_type,))

        # Try: just polarity
        if level_test_side is None and polarity:
            level_test_side = per_level_test_sides.get((polarity,))

        # Fall back to global
        if level_test_side is None:
            level_test_side = global_test_side

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
    conn = Connection("allen_estimshape_exp_260325_0")

    # Time range
    since_date = time_util.from_date_to_now(2024, 7, 10)
    start_gen_id = 2
    max_gen_id = float('inf')
    start_gen_id_estim_on = 0
    max_gen_id_estim_on = float('inf')

    # ============ CORRECTNESS FIELD SELECTION ============
    # Specify which field to use for correctness metric
    # Options: "IsCorrect" or "IsHypothesized"
    isCorrectFieldName = "IsHypothesized"
    # ====================================================

    # ============ PERMUTATION TEST PARAMETERS ============
    # Global test side (fallback for all conditions)
    global_test_side = 'two-tailed'

    # Per-level test sides with hierarchical lookup
    per_level_test_sides = {
        # Most specific: test each combination independently
        ('delta', 'anodic', 1.0): "negative",
        ('delta', 'anodic', 0.9): "negative",
        ('delta', 'cathodic', 1.0): "negative",
        ('delta', 'cathodic', 0.9): "positive",
        ('delta', 'combined', 1.0): "negative",
        ('delta', 'combined', 0.9): "positive",
        ('variant', 'anodic', 1.0): "positive",
        ('variant', 'anodic', 0.9): "positive",
        ('variant', 'cathodic', 1.0): "positive",
        ('variant', 'cathodic', 0.9): "positive",
        ('variant', 'combined', 1.0): "positive",
        ('variant', 'combined', 0.9): "positive",
    }

    if per_level_test_sides is None:
        per_level_test_sides = {}
    # ====================================================

    # Collect trial timestamps
    trial_tstamps = collect_choice_trials(conn, since_date)

    # Set up fields to collect
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

    # Convert to dataframe
    data = fields.to_data(trial_tstamps)

    # Filter data by GenId
    data = data[(data['GenId'] >= start_gen_id) & (data['GenId'] <= max_gen_id)]

    # Split datasets
    data_exp = data[data['StimType'] == 'EStimShapeVariantsDeltaNAFCStim']

    # Split by IsDelta
    data_exp_delta = data_exp[data_exp['IsDelta'] == True].copy()
    data_exp_variant = data_exp[data_exp['IsDelta'] == False].copy()

    # Apply EStim filters and split by polarity
    data_exp_delta_estim_on = data_exp_delta[(data_exp_delta['EStimEnabled'] == True) &
                                             (data_exp_delta['GenId'] >= start_gen_id_estim_on) &
                                             (data_exp_delta['GenId'] <= max_gen_id_estim_on)].copy()
    data_exp_delta_estim_off = data_exp_delta[data_exp_delta['EStimEnabled'] == False].copy()

    data_exp_variant_estim_on = data_exp_variant[(data_exp_variant['EStimEnabled'] == True) &
                                                 (data_exp_variant['GenId'] >= start_gen_id_estim_on) &
                                                 (data_exp_variant['GenId'] <= max_gen_id_estim_on)].copy()
    data_exp_variant_estim_off = data_exp_variant[data_exp_variant['EStimEnabled'] == False].copy()

    # Split EStim ON by polarity
    data_exp_delta_pos = data_exp_delta_estim_on[data_exp_delta_estim_on['EStimPolarity'] == 'PositiveFirst'].copy()
    data_exp_delta_neg = data_exp_delta_estim_on[data_exp_delta_estim_on['EStimPolarity'] == 'NegativeFirst'].copy()
    data_exp_delta_combined = data_exp_delta_estim_on.copy()  # Combined: all EStim ON

    data_exp_variant_pos = data_exp_variant_estim_on[data_exp_variant_estim_on['EStimPolarity'] == 'PositiveFirst'].copy()
    data_exp_variant_neg = data_exp_variant_estim_on[data_exp_variant_estim_on['EStimPolarity'] == 'NegativeFirst'].copy()
    data_exp_variant_combined = data_exp_variant_estim_on.copy()  # Combined: all EStim ON

    noise_levels = sorted(data_exp['NoiseChance'].unique())

    # ==================== FIGURE: SELECTED METRIC ====================
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    # Determine metric name for title
    metric_name = "ACCURACY" if isCorrectFieldName == "IsCorrect" else "% HYPOTHESIZED"

    # Plot: Delta Positive First
    if len(data_exp_delta_pos) > 0:
        plot_psychometric_curve_on_ax(
            data_exp_delta_pos, axes[0],
            title=f'{metric_name}: Delta vs Variant by Polarity',
            show_n=True, num_rep_min=0,
            color='red',
            label=f'Delta Anodic (n={len(data_exp_delta_pos)})',
            isCorrectColumnName=isCorrectFieldName)

    # Plot: Delta Negative First
    if len(data_exp_delta_neg) > 0:
        plot_psychometric_curve_on_ax(
            data_exp_delta_neg, axes[0],
            title=f'{metric_name}: Delta vs Variant by Polarity',
            show_n=True, num_rep_min=0,
            color='red',
            label=f'Delta Cathodic (n={len(data_exp_delta_neg)})',
            isCorrectColumnName=isCorrectFieldName)

    # # Plot: Delta Combined
    # if len(data_exp_delta_combined) > 0:
    #     plot_psychometric_curve_on_ax(
    #         data_exp_delta_combined, axes[0],
    #         title=f'{metric_name}: Delta vs Variant by Polarity',
    #         show_n=True, num_rep_min=0,
    #         color='darkred',
    #         label=f'Delta Combined (n={len(data_exp_delta_combined)})',
    #         isCorrectColumnName=isCorrectFieldName)

    # Plot: Delta EStim OFF
    if len(data_exp_delta_estim_off) > 0:
        plot_psychometric_curve_on_ax(
            data_exp_delta_estim_off, axes[0],
            title=f'{metric_name}: Delta vs Variant by Polarity',
            show_n=True, num_rep_min=0,
            color='pink',
            label=f'Delta OFF (n={len(data_exp_delta_estim_off)})',
            isCorrectColumnName=isCorrectFieldName)

    # Plot: Variant Positive First
    if len(data_exp_variant_pos) > 0:
        plot_psychometric_curve_on_ax(
            data_exp_variant_pos, axes[0],
            title=f'{metric_name}: Delta vs Variant by Polarity',
            show_n=True, num_rep_min=0,
            color='blue',
            label=f'Variant Anodic (n={len(data_exp_variant_pos)})',
            isCorrectColumnName=isCorrectFieldName)

    # Plot: Variant Negative First
    if len(data_exp_variant_neg) > 0:
        plot_psychometric_curve_on_ax(
            data_exp_variant_neg, axes[0],
            title=f'{metric_name}: Delta vs Variant by Polarity',
            show_n=True, num_rep_min=0,
            color='blue',
            label=f'Variant Cathodic (n={len(data_exp_variant_neg)})',
            isCorrectColumnName=isCorrectFieldName)

    # # Plot: Variant Combined
    # if len(data_exp_variant_combined) > 0:
    #     plot_psychometric_curve_on_ax(
    #         data_exp_variant_combined, axes[0],
    #         title=f'{metric_name}: Delta vs Variant by Polarity',
    #         show_n=True, num_rep_min=0,
    #         color='darkblue', linewidth=2.5, marker='D', markersize=6, linestyle='--',
    #         label=f'Variant Combined (n={len(data_exp_variant_combined)})',
    #         isCorrectColumnName=isCorrectFieldName)

    # Plot: Variant EStim OFF
    if len(data_exp_variant_estim_off) > 0:
        plot_psychometric_curve_on_ax(
            data_exp_variant_estim_off, axes[0],
            title=f'{metric_name}: Delta vs Variant by Polarity',
            show_n=True, num_rep_min=0,
            color='lightblue', linewidth=2.5, marker='o', markersize=6, linestyle='-',
            label=f'Variant OFF (n={len(data_exp_variant_estim_off)})',
            isCorrectColumnName=isCorrectFieldName)

    axes[0].invert_xaxis()
    axes[0].set_ylim([0, 110])
    axes[0].grid(True, alpha=0.3)
    axes[0].legend(fontsize=7)

    # Statistics
    results_text = f"PERMUTATION TEST - {metric_name}\n"
    results_text += "=" * 50 + "\n\n"

    # Delta Anodic vs OFF test
    results_text += "DELTA ANODIC vs OFF\n" + "=" * 50 + "\n"
    data_delta_anodic_for_perm = pd.concat([data_exp_delta_pos, data_exp_delta_estim_off])

    if len(data_exp_delta_pos) > 0 and len(data_exp_delta_estim_off) > 0:
        np.random.seed(42)
        observed_sum, overall_p, overall_sig, level_diffs, _ = \
            run_permutation_test(data_delta_anodic_for_perm, noise_levels, isCorrectFieldName,
                                 global_test_side, per_level_test_sides,
                                 stimulus_type='delta', polarity='anodic')

        for noise in sorted(level_diffs.keys()):
            estim_pct, no_estim_pct, diff, n_on, n_off, p, sig, test_side = level_diffs[noise]
            results_text += f"N{noise * 100:.0f}%: {diff:+.1f}% p={p:.3f}{sig}\n"
        results_text += f"Overall: {observed_sum:+.1f}% p={overall_p:.4f} {overall_sig}\n"
    else:
        results_text += "Insufficient data\n"

    results_text += "\n"

    # Delta Cathodic vs OFF test
    results_text += "DELTA CATHODIC vs OFF\n" + "=" * 50 + "\n"
    data_delta_cathodic_for_perm = pd.concat([data_exp_delta_neg, data_exp_delta_estim_off])

    if len(data_exp_delta_neg) > 0 and len(data_exp_delta_estim_off) > 0:
        np.random.seed(42)
        observed_sum, overall_p, overall_sig, level_diffs, _ = \
            run_permutation_test(data_delta_cathodic_for_perm, noise_levels, isCorrectFieldName,
                                 global_test_side, per_level_test_sides,
                                 stimulus_type='delta', polarity='cathodic')

        for noise in sorted(level_diffs.keys()):
            estim_pct, no_estim_pct, diff, n_on, n_off, p, sig, test_side = level_diffs[noise]
            results_text += f"N{noise * 100:.0f}%: {diff:+.1f}% p={p:.3f}{sig}\n"
        results_text += f"Overall: {observed_sum:+.1f}% p={overall_p:.4f} {overall_sig}\n"
    else:
        results_text += "Insufficient data\n"

    results_text += "\n"

    # Delta Combined vs OFF test
    results_text += "DELTA COMBINED vs OFF\n" + "=" * 50 + "\n"
    data_delta_combined_for_perm = pd.concat([data_exp_delta_combined, data_exp_delta_estim_off])

    if len(data_exp_delta_combined) > 0 and len(data_exp_delta_estim_off) > 0:
        np.random.seed(42)
        observed_sum, overall_p, overall_sig, level_diffs, _ = \
            run_permutation_test(data_delta_combined_for_perm, noise_levels, isCorrectFieldName,
                                 global_test_side, per_level_test_sides,
                                 stimulus_type='delta', polarity='combined')

        for noise in sorted(level_diffs.keys()):
            estim_pct, no_estim_pct, diff, n_on, n_off, p, sig, test_side = level_diffs[noise]
            results_text += f"N{noise * 100:.0f}%: {diff:+.1f}% p={p:.3f}{sig}\n"
        results_text += f"Overall: {observed_sum:+.1f}% p={overall_p:.4f} {overall_sig}\n"
    else:
        results_text += "Insufficient data\n"

    results_text += "\n"

    # Variant Anodic vs OFF test
    results_text += "VARIANT ANODIC vs OFF\n" + "=" * 50 + "\n"
    data_variant_anodic_for_perm = pd.concat([data_exp_variant_pos, data_exp_variant_estim_off])

    if len(data_exp_variant_pos) > 0 and len(data_exp_variant_estim_off) > 0:
        np.random.seed(42)
        observed_sum, overall_p, overall_sig, level_diffs, _ = \
            run_permutation_test(data_variant_anodic_for_perm, noise_levels, isCorrectFieldName,
                                 global_test_side, per_level_test_sides,
                                 stimulus_type='variant', polarity='anodic')

        for noise in sorted(level_diffs.keys()):
            estim_pct, no_estim_pct, diff, n_on, n_off, p, sig, test_side = level_diffs[noise]
            results_text += f"N{noise * 100:.0f}%: {diff:+.1f}% p={p:.3f}{sig}\n"
        results_text += f"Overall: {observed_sum:+.1f}% p={overall_p:.4f} {overall_sig}\n"
    else:
        results_text += "Insufficient data\n"

    results_text += "\n"

    # Variant Cathodic vs OFF test
    results_text += "VARIANT CATHODIC vs OFF\n" + "=" * 50 + "\n"
    data_variant_cathodic_for_perm = pd.concat([data_exp_variant_neg, data_exp_variant_estim_off])

    if len(data_exp_variant_neg) > 0 and len(data_exp_variant_estim_off) > 0:
        np.random.seed(42)
        observed_sum, overall_p, overall_sig, level_diffs, _ = \
            run_permutation_test(data_variant_cathodic_for_perm, noise_levels, isCorrectFieldName,
                                 global_test_side, per_level_test_sides,
                                 stimulus_type='variant', polarity='cathodic')

        for noise in sorted(level_diffs.keys()):
            estim_pct, no_estim_pct, diff, n_on, n_off, p, sig, test_side = level_diffs[noise]
            results_text += f"N{noise * 100:.0f}%: {diff:+.1f}% p={p:.3f}{sig}\n"
        results_text += f"Overall: {observed_sum:+.1f}% p={overall_p:.4f} {overall_sig}\n"
    else:
        results_text += "Insufficient data\n"

    results_text += "\n"

    # Variant Combined vs OFF test
    results_text += "VARIANT COMBINED vs OFF\n" + "=" * 50 + "\n"
    data_variant_combined_for_perm = pd.concat([data_exp_variant_combined, data_exp_variant_estim_off])

    if len(data_exp_variant_combined) > 0 and len(data_exp_variant_estim_off) > 0:
        np.random.seed(42)
        observed_sum, overall_p, overall_sig, level_diffs, _ = \
            run_permutation_test(data_variant_combined_for_perm, noise_levels, isCorrectFieldName,
                                 global_test_side, per_level_test_sides,
                                 stimulus_type='variant', polarity='combined')

        for noise in sorted(level_diffs.keys()):
            estim_pct, no_estim_pct, diff, n_on, n_off, p, sig, test_side = level_diffs[noise]
            results_text += f"N{noise * 100:.0f}%: {diff:+.1f}% p={p:.3f}{sig}\n"
        results_text += f"Overall: {observed_sum:+.1f}% p={overall_p:.4f} {overall_sig}\n"
    else:
        results_text += "Insufficient data\n"

    results_text += "\n* p<0.05, ** p<0.01, *** p<0.001"

    axes[1].text(0.05, 0.95, results_text,
                  transform=axes[1].transAxes, fontsize=6,
                  verticalalignment='top', fontfamily='monospace',
                  bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    axes[1].axis('off')

    plt.tight_layout()
    fig.suptitle(f'{metric_name} ANALYSIS by Polarity - {isCorrectFieldName}', fontsize=16, y=1.02)

    plt.show()


if __name__ == '__main__':
    main()