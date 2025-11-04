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
    conn = Connection("allen_estimshape_exp_251030_0")

    # Time range
    since_date = time_util.from_date_to_now(2024, 7, 10)
    start_gen_id = 21  # Filter for all data (EStim OFF and general filtering)
    max_gen_id = 25  # Maximum GenId to include (set to a number to limit, or leave as inf for no limit)
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
    data_exp = data[data['StimType'] == 'EStimShapeProceduralStim']

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
    # Run BOTH per-level tests AND logistic regression
    import pandas as pd
    import numpy as np

    noise_levels = sorted(data_exp['NoiseChance'].unique())

    results_text = "STATISTICAL ANALYSIS\n"
    results_text += "=" * 50 + "\n\n"

    # PART 1: Per-Level Independent Tests
    results_text += "Per-Level Tests (EStim ON vs OFF):\n"
    results_text += "-" * 50 + "\n"

    for noise in noise_levels:
        noise_data = data_exp[data_exp['NoiseChance'] == noise]

        # Get EStim ON and OFF data for this noise level
        estim_on = noise_data[(noise_data['EStimEnabled'] == True) &
                              (noise_data['GenId'] >= start_gen_id_estim_on) &
                              (noise_data['GenId'] <= max_gen_id_estim_on)].copy()
        estim_off = noise_data[noise_data['EStimEnabled'] == False].copy()

        # Convert "No Data" to False (treat as incorrect)
        estim_on.loc[estim_on['IsCorrect'] == "No Data", 'IsCorrect'] = False
        estim_off.loc[estim_off['IsCorrect'] == "No Data", 'IsCorrect'] = False

        # Only test if both conditions have data
        if len(estim_on) > 0 and len(estim_off) > 0:
            on_correct = (estim_on['IsCorrect'] == True).sum()
            on_total = len(estim_on)
            off_correct = (estim_off['IsCorrect'] == True).sum()
            off_total = len(estim_off)

            on_pct = 100 * on_correct / on_total
            off_pct = 100 * off_correct / off_total

            # Create contingency table
            from scipy.stats import chi2_contingency, fisher_exact
            table = [[on_correct, on_total - on_correct],
                     [off_correct, off_total - off_correct]]

            # Use Fisher's exact for small samples, chi-square otherwise
            if min(on_total, off_total) < 30 or min(on_correct, off_correct, on_total - on_correct,
                                                    off_total - off_correct) < 5:
                odds_ratio, p_value = fisher_exact(table)
                test_name = "Fisher"
            else:
                chi2, p_value, dof, expected = chi2_contingency(table)
                if (on_total - on_correct) > 0 and (off_total - off_correct) > 0:
                    odds_ratio = (on_correct / (on_total - on_correct)) / (off_correct / (off_total - off_correct))
                else:
                    odds_ratio = float('inf')
                test_name = "Chi-sq"

            # Determine significance
            if p_value < 0.001:
                sig = "***"
            elif p_value < 0.01:
                sig = "**"
            elif p_value < 0.05:
                sig = "*"
            else:
                sig = "ns"

            results_text += f"Noise {noise * 100:.0f}%: "
            results_text += f"{on_correct}/{on_total}({on_pct:.0f}%) vs "
            results_text += f"{off_correct}/{off_total}({off_pct:.0f}%), "
            results_text += f"p={p_value:.3f}{sig}, OR={odds_ratio:.2f}\n"

    # PART 2: Logistic Regression
    results_text += "\n"
    results_text += "Logistic Regression (Overall Model):\n"
    results_text += "-" * 50 + "\n"

    # Prepare data for logistic regression
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
    data_for_model = pd.concat([data_exp_for_analysis_estim_on, data_exp_for_analysis_estim_off])

    # Convert "No Data" to False
    data_for_model.loc[data_for_model['IsCorrect'] == "No Data", 'IsCorrect'] = False

    # Convert IsCorrect to numeric (1 for True, 0 for False)
    data_for_model['IsCorrect_numeric'] = (data_for_model['IsCorrect'] == True).astype(int)

    if len(data_for_model) > 0 and len(data_for_model[data_for_model['EStimEnabled'] == True]) > 0:
        try:
            import statsmodels.api as sm
            from statsmodels.formula.api import glm

            # Fit logistic regression model
            # Model: IsCorrect ~ EStimEnabled * NoiseChance
            model = glm("IsCorrect_numeric ~ C(EStimEnabled) * NoiseChance",
                        data=data_for_model,
                        family=sm.families.Binomial())
            result = model.fit()

            # Extract key statistics
            params = result.params
            pvalues = result.pvalues
            conf_int = result.conf_int()

            # Display main effects and interaction
            for param_name in params.index:
                if param_name == 'Intercept':
                    continue

                coef = params[param_name]
                p = pvalues[param_name]

                # Significance markers
                if p < 0.001:
                    sig = "***"
                elif p < 0.01:
                    sig = "**"
                elif p < 0.05:
                    sig = "*"
                else:
                    sig = "ns"

                # Odds Ratio
                or_value = np.exp(coef)
                or_ci_low = np.exp(conf_int.loc[param_name, 0])
                or_ci_high = np.exp(conf_int.loc[param_name, 1])

                # Shorten parameter names for display
                display_name = param_name.replace('C(EStimEnabled)[T.True]', 'EStim')
                display_name = display_name.replace('NoiseChance', 'Noise')
                display_name = display_name.replace(':', '×')

                results_text += f"{display_name}: OR={or_value:.2f} "
                results_text += f"[{or_ci_low:.2f},{or_ci_high:.2f}], "
                results_text += f"p={p:.3f}{sig}\n"

            results_text += f"\nModel: n={len(data_for_model)}, "
            results_text += f"AIC={result.aic:.1f}, "
            results_text += f"R²={1 - (result.deviance / result.null_deviance):.3f}\n"

        except Exception as e:
            results_text += f"Model fitting error: {str(e)}\n"
    else:
        results_text += "Insufficient data for regression.\n"

    results_text += "\n* p<0.05, ** p<0.01, *** p<0.001"
    results_text += "\nPer-level: Independent tests (no correction)"

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