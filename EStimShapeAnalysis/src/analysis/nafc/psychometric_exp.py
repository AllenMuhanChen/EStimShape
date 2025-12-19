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
    StimTypeField, ChoiceField, AnswerField, GenIdField, EStimEnabledField
)
from src.analysis.nafc.psychometric_curves import collect_choice_trials, plot_psychometric_curve_on_ax


def filter_by_num_distractors(data, num_distractors):
    """Filter data by NumRandDistractors value."""
    return data[data['NumRandDistractors'] == num_distractors]


def main():
    # Database connection
    conn = Connection("allen_estimshape_exp_251218_0")

    # Time range
    since_date = time_util.from_date_to_now(2024, 7, 10)
    start_gen_id = 14  # Filter for all data (EStim OFF and general filtering)
    max_gen_id = float('inf')  # Maximum GenId to include (set to a number to limit, or leave as inf for no limit)
    start_gen_id_estim_on = 0  # Additional filter for EStim ON trials only (set higher to get only recent EStim ON data)
    max_gen_id_estim_on = float('inf')  # Maximum GenId for EStim ON trials (set to a number to limit)

    # Collect trial timestamps
    trial_tstamps = collect_choice_trials(conn, since_date)

    # Set up fields to collect
    fields = CachedFieldList()
    fields.append(IsCorrectField(conn))
    fields.append(NoiseChanceField(conn))
    fields.append(NumRandDistractorsField(conn))
    fields.append(StimTypeField(conn))
    fields.append(ChoiceField(conn))
    fields.append(AnswerField(conn))
    fields.append(GenIdField(conn))
    fields.append(EStimEnabledField(conn))

    # Convert to dataframe
    data = fields.to_data(trial_tstamps)

    # Filter data by GenId (both min and max)
    data = data[(data['GenId'] >= start_gen_id) & (data['GenId'] <= max_gen_id)]

    # Split into the two datasets we care about
    data_procedural = data[data['StimType'] == 'EStimShapeProceduralBehavioralStim']
    data_exp = data[data['StimType'] == 'EStimShapeVariantsNAFCStim']

    # Create figure with 2x2 subplots
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    # Get colormap for multiple lines
    colors = plt.colormaps['tab10'].colors

    # TOP LEFT: Plot procedural data - overall and by NumRandDistractors
    plot_psychometric_curve_on_ax(
        data_procedural,
        axes[0, 0],
        title='Procedural Behavioral Trials',
        show_n=True,
        num_rep_min=0,
        color='black',
        linewidth=2.5,
        marker='o',
        markersize=6,
        label='All'
    )

    # Plot separate lines for each NumRandDistractors value
    distractor_values_proc = sorted(data_procedural['NumRandDistractors'].unique())
    for i, num_dist in enumerate(distractor_values_proc):
        filtered_data = filter_by_num_distractors(data_procedural, num_dist)
        plot_psychometric_curve_on_ax(
            filtered_data,
            axes[0, 0],
            show_n=True,
            num_rep_min=0,
            color=colors[i % len(colors)],
            linewidth=1.5,
            marker='o',
            markersize=4,
            linestyle='--',
            label=f'NumDist={num_dist}'
        )

    # TOP RIGHT: Experimental plot with NumRandDistractors breakdown AND EStim variants
    plot_psychometric_curve_on_ax(
        data_exp,
        axes[0, 1],
        title='Experimental Procedural Trials (with EStim variants)',
        show_n=True,
        num_rep_min=0,
        color='black',
        linewidth=2.5,
        marker='s',
        markersize=6,
        label='All'
    )

    # Plot separate lines for each NumRandDistractors value, split by EStim enabled/disabled
    distractor_values_exp = sorted(data_exp['NumRandDistractors'].unique())
    for i, num_dist in enumerate(distractor_values_exp):
        filtered_data = filter_by_num_distractors(data_exp, num_dist)

        # Plot with EStim enabled (solid line, smaller)
        filtered_data_estim_on = filtered_data[(filtered_data['EStimEnabled'] == True) &
                                               (filtered_data['GenId'] >= start_gen_id_estim_on) &
                                               (filtered_data['GenId'] <= max_gen_id_estim_on)]
        if len(filtered_data_estim_on) > 0:
            plot_psychometric_curve_on_ax(
                filtered_data_estim_on,
                axes[0, 1],
                show_n=True,
                num_rep_min=0,
                color=colors[i % len(colors)],
                linewidth=1.5,
                marker='s',
                markersize=4,
                linestyle='-',
                label=f'NumDist={num_dist} (EStim ON)'
            )

        # Plot with EStim disabled (dashed line, smaller)
        filtered_data_estim_off = filtered_data[filtered_data['EStimEnabled'] == False]
        if len(filtered_data_estim_off) > 0:
            plot_psychometric_curve_on_ax(
                filtered_data_estim_off,
                axes[0, 1],
                show_n=True,
                num_rep_min=0,
                color=colors[i % len(colors)],
                linewidth=1.5,
                marker='o',
                markersize=4,
                linestyle='--',
                label=f'NumDist={num_dist} (EStim OFF)'
            )

    # BOTTOM RIGHT: Simple EStim ON vs OFF comparison (two solid lines only)
    data_exp_estim_on = data_exp[(data_exp['EStimEnabled'] == True) &
                                 (data_exp['GenId'] >= start_gen_id_estim_on) &
                                 (data_exp['GenId'] <= max_gen_id_estim_on)]
    data_exp_estim_off = data_exp[data_exp['EStimEnabled'] == False]

    if len(data_exp_estim_on) > 0:
        plot_psychometric_curve_on_ax(
            data_exp_estim_on,
            axes[1, 1],
            title='Experimental: EStim ON vs OFF',
            show_n=True,
            num_rep_min=0,
            color='red',
            linewidth=2.5,
            marker='s',
            markersize=6,
            linestyle='-',
            label='EStim ON'
        )

    if len(data_exp_estim_off) > 0:
        plot_psychometric_curve_on_ax(
            data_exp_estim_off,
            axes[1, 1],
            title='Experimental: EStim ON vs OFF',
            show_n=True,
            num_rep_min=0,
            color='blue',
            linewidth=2.5,
            marker='o',
            markersize=6,
            linestyle='-',
            label='EStim OFF'
        )

    # BOTTOM LEFT: Statistical analysis results
    # Permutation test across all noise levels
    import pandas as pd
    import numpy as np

    noise_levels = sorted(data_exp['NoiseChance'].unique())

    results_text = "PERMUTATION TEST ANALYSIS\n"
    results_text += "=" * 50 + "\n\n"

    # Prepare data for permutation test
    data_exp_for_analysis = data_exp.copy()

    # Apply EStim ON GenId filters
    data_exp_for_analysis_estim_on = data_exp_for_analysis[
        (data_exp_for_analysis['EStimEnabled'] == True) &
        (data_exp_for_analysis['GenId'] >= start_gen_id_estim_on) &
        (data_exp_for_analysis['GenId'] <= max_gen_id_estim_on)
        ].copy()

    data_exp_for_analysis_estim_off = data_exp_for_analysis[
        data_exp_for_analysis['EStimEnabled'] == False
        ].copy()

    # Combine back together
    data_for_perm = pd.concat([data_exp_for_analysis_estim_on, data_exp_for_analysis_estim_off])

    # Convert "No Data" to False
    data_for_perm.loc[data_for_perm['IsCorrect'] == "No Data", 'IsCorrect'] = False
    data_for_perm['IsCorrect_bool'] = (data_for_perm['IsCorrect'] == True)

    # Function to calculate sum of differences across noise levels
    def calculate_sum_diff(data):
        """Calculate sum of (estim_pct - no_estim_pct) across all noise levels"""
        sum_diff = 0
        valid_levels = 0
        level_diffs = {}

        for noise in noise_levels:
            noise_data = data[data['NoiseChance'] == noise]
            estim_on_data = noise_data[noise_data['EStimEnabled'] == True]
            estim_off_data = noise_data[noise_data['EStimEnabled'] == False]

            if len(estim_on_data) > 0 and len(estim_off_data) > 0:
                estim_pct = 100 * estim_on_data['IsCorrect_bool'].mean()
                no_estim_pct = 100 * estim_off_data['IsCorrect_bool'].mean()
                diff = estim_pct - no_estim_pct
                sum_diff += diff
                valid_levels += 1
                level_diffs[noise] = (estim_pct, no_estim_pct, diff,
                                      len(estim_on_data), len(estim_off_data))

        return sum_diff, valid_levels, level_diffs

    # Calculate observed sum of differences
    observed_sum, n_levels, observed_level_diffs = calculate_sum_diff(data_for_perm)

    # Run permutation test
    n_permutations = 10000
    np.random.seed(42)  # For reproducibility

    # Store permutations for both overall and per-level tests
    permuted_sums = []
    permuted_level_diffs = {noise: [] for noise in noise_levels}

    for i in range(n_permutations):
        # Create a copy for permutation
        perm_data = data_for_perm.copy()

        # For each noise level, permute the EStim labels independently
        for noise in noise_levels:
            noise_mask = perm_data['NoiseChance'] == noise
            noise_indices = perm_data[noise_mask].index

            if len(noise_indices) > 0:
                # Permute EStim labels within this noise level
                shuffled_estim = perm_data.loc[noise_indices, 'EStimEnabled'].sample(frac=1).values
                perm_data.loc[noise_indices, 'EStimEnabled'] = shuffled_estim

        # Calculate sum of differences for this permutation
        perm_sum, _, perm_level_dict = calculate_sum_diff(perm_data)
        permuted_sums.append(perm_sum)

        # Store per-level differences for this permutation
        for noise, (_, _, diff, _, _) in perm_level_dict.items():
            permuted_level_diffs[noise].append(diff)

    permuted_sums = np.array(permuted_sums)

    # Calculate overall p-value (one-tailed: testing if estim reduces performance)
    overall_p_value = np.mean(permuted_sums >= observed_sum)

    # Determine overall significance
    if overall_p_value < 0.001:
        overall_sig = "***"
    elif overall_p_value < 0.01:
        overall_sig = "**"
    elif overall_p_value < 0.05:
        overall_sig = "*"
    else:
        overall_sig = "ns"

    # Calculate per-level p-values
    level_p_values = {}
    for noise in observed_level_diffs.keys():
        observed_diff = observed_level_diffs[noise][2]  # The difference value
        perm_diffs = np.array(permuted_level_diffs[noise])
        # One-tailed: proportion of permutations with diff <= observed_diff
        level_p_values[noise] = np.mean(perm_diffs >= observed_diff)

        # Determine significance
        p = level_p_values[noise]
        if p < 0.001:
            level_sig = "***"
        elif p < 0.01:
            level_sig = "**"
        elif p < 0.05:
            level_sig = "*"
        else:
            level_sig = "ns"

        # Update the tuple to include p-value and significance
        estim_pct, no_estim_pct, diff, n_on, n_off = observed_level_diffs[noise]
        observed_level_diffs[noise] = (estim_pct, no_estim_pct, diff, n_on, n_off, p, level_sig)

    # Display results
    results_text += "Per-Level Permutation Tests:\n"
    results_text += "-" * 50 + "\n"

    for noise in sorted(observed_level_diffs.keys()):
        estim_pct, no_estim_pct, diff, n_on, n_off, p, sig = observed_level_diffs[noise]
        results_text += f"Noise {noise * 100:.0f}%:\n"
        results_text += f"  EStim {estim_pct:.1f}% (n={n_on}) vs "
        results_text += f"NoStim {no_estim_pct:.1f}% (n={n_off})\n"
        results_text += f"  Difference: {diff:+.1f}%, p={p:.4f} {sig}\n"

    results_text += "\n"
    results_text += "Overall Permutation Test:\n"
    results_text += "-" * 50 + "\n"
    results_text += f"Observed sum of differences: {observed_sum:+.1f}%\n"
    results_text += f"Permutations: {n_permutations:,}\n"
    results_text += f"P-value (one-tailed): {overall_p_value:.4f} {overall_sig}\n"
    results_text += f"Noise levels tested: {n_levels}\n"

    # Add distribution info
    results_text += f"\nNull distribution (95% CI):\n"
    results_text += f"  Mean: {np.mean(permuted_sums):.2f}%\n"
    results_text += f"  2.5th percentile: {np.percentile(permuted_sums, 2.5):.2f}%\n"
    results_text += f"  97.5th percentile: {np.percentile(permuted_sums, 97.5):.2f}%\n"

    results_text += "\n* p<0.05, ** p<0.01, *** p<0.001"
    results_text += "\nTest: One-tailed (EStim reduces performance)"

    # Display results in bottom left axes
    axes[1, 0].text(0.05, 0.95, results_text,
                    transform=axes[1, 0].transAxes,
                    fontsize=8,
                    verticalalignment='top',
                    fontfamily='monospace',
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    axes[1, 0].axis('off')

    # Format all axes (except the hidden one)
    for i in range(2):
        for j in range(2):
            if i == 1 and j == 0:  # Skip bottom left (hidden)
                continue
            axes[i, j].invert_xaxis()
            axes[i, j].set_ylim([0, 110])
            axes[i, j].grid(True, alpha=0.3)
            axes[i, j].legend()

    plt.tight_layout()
    plt.show()

    # Print summary statistics
    print("\n=== Summary Statistics ===")
    print(f"\nProcedural Behavioral Trials:")
    # Convert "No Data" to False instead of filtering out
    data_procedural_clean = data_procedural.copy()
    data_procedural_clean.loc[data_procedural_clean['IsCorrect'] == "No Data", 'IsCorrect'] = False
    print(f"  Total trials: {len(data_procedural_clean)}")
    if len(data_procedural_clean) > 0:
        print(f"  Overall accuracy: {(data_procedural_clean['IsCorrect'] == True).mean() * 100:.2f}%")
    print(f"  NumRandDistractors values: {distractor_values_proc}")

    print(f"\nExperimental Procedural Trials:")
    data_exp_clean = data_exp.copy()
    data_exp_clean.loc[data_exp_clean['IsCorrect'] == "No Data", 'IsCorrect'] = False
    print(f"  Total trials: {len(data_exp_clean)}")
    if len(data_exp_clean) > 0:
        print(f"  Overall accuracy: {(data_exp_clean['IsCorrect'] == True).mean() * 100:.2f}%")
    print(f"  NumRandDistractors values: {distractor_values_exp}")

    # EStim breakdown for experimental trials
    # Convert "No Data" to False
    data_exp_estim_on_clean = data_exp_estim_on.copy()
    data_exp_estim_on_clean.loc[data_exp_estim_on_clean['IsCorrect'] == "No Data", 'IsCorrect'] = False
    data_exp_estim_off_clean = data_exp_estim_off.copy()
    data_exp_estim_off_clean.loc[data_exp_estim_off_clean['IsCorrect'] == "No Data", 'IsCorrect'] = False

    print(f"\n  EStim Breakdown:")
    if len(data_exp_estim_on_clean) > 0:
        genid_range_on = f"GenId {start_gen_id_estim_on}-{max_gen_id_estim_on if max_gen_id_estim_on != float('inf') else '∞'}"
        print(
            f"    EStim ON ({genid_range_on}): {len(data_exp_estim_on_clean)} trials ({(data_exp_estim_on_clean['IsCorrect'] == True).mean() * 100:.2f}% accuracy)")
    if len(data_exp_estim_off_clean) > 0:
        genid_range_off = f"GenId {start_gen_id}-{max_gen_id if max_gen_id != float('inf') else '∞'}"
        print(
            f"    EStim OFF ({genid_range_off}): {len(data_exp_estim_off_clean)} trials ({(data_exp_estim_off_clean['IsCorrect'] == True).mean() * 100:.2f}% accuracy)")


if __name__ == '__main__':
    main()