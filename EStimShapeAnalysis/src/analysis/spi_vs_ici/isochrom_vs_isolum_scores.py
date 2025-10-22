import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os
from scipy import stats
from statsmodels.formula.api import ols
from statsmodels.stats.anova import anova_lm
from clat.util.connection import Connection


def main():
    # Example usage with different data sources

    # Option 1: Use sorted selective units
    create_isochrom_isolum_score_plots(
        save_path="/home/connorlab/Documents/plots/isochrom_vs_isolum",
        data_source='sorted_selective'
    )

    # Option 2: Use validated raw channels
    # create_isochrom_isolum_score_plots(
    #     save_path="/home/connorlab/Documents/plots/isochrom_vs_isolum",
    #     data_source='raw_validated'
    # )

    # Option 3: Use clustered raw channels
    create_isochrom_isolum_score_plots(
        save_path="/home/connorlab/Documents/plots/isochrom_vs_isolum",
        data_source='raw_clustered'
    )


def create_isochrom_isolum_score_plots(save_path=None, metric_name='raw_spikes_per_second',
                                       data_source='raw_validated'):
    """
    Create plots showing isochromatic vs isoluminant scores for each frequency.
    Points are colored by 3D significance status.
    Only plots frequencies: 0.5, 1.0, 2.0, 4.0 Hz

    Args:
        save_path: Optional directory path to save plots. If None, plots are only displayed.
        metric_name: The metric to plot from IsoChromaticLuminantScores table
        data_source: Which data loading method to use. Options:
            - 'raw_validated': Raw channels validated by both GoodChannels AND ChannelFiltering (e.g., A-001)
            - 'sorted_selective': Sorted units filtered by stimulus selectivity >5% (e.g., 250915_0_Unit_1)
            - 'raw_clustered': Raw cluster channels from ClusterInfo table
    """

    # Create save directory if specified and doesn't exist
    if save_path is not None:
        os.makedirs(save_path, exist_ok=True)

    # Load data based on selected source
    merged_df = load_data_by_source(data_source, metric_name)

    if merged_df is None or merged_df.empty:
        print(f"No data available for data source: {data_source}")
        return None

    # Get frequencies and ensure they're in order
    frequencies = [0.5, 1.0, 2.0, 4.0]
    # Filter to only include frequencies that exist in the data
    frequencies = [f for f in frequencies if f in merged_df['frequency'].values]

    print(f"\nCreating plots for {len(frequencies)} frequencies: {frequencies}")
    print(f"Total units/channels after filtering: {len(merged_df['unit_name'].unique())}")

    # Create combined plot with all frequencies
    create_combined_frequency_plots(merged_df, frequencies, metric_name, save_path, data_source)

    return merged_df


# ==================== DATA LOADING METHODS ====================

def load_data_by_source(data_source, metric_name):
    """
    Load and merge data based on the specified source.

    Args:
        data_source: String specifying which filtering method to use
        metric_name: The metric name to query from IsoChromaticLuminantScores

    Returns:
        DataFrame with merged score and solid preference data, filtered by the specified method
    """
    if data_source == 'raw_validated':
        return load_validated_raw_channels(metric_name)
    elif data_source == 'sorted_selective':
        return load_sorted_selective_units(metric_name)
    elif data_source == 'raw_clustered':
        return load_clustered_raw_channels(metric_name)
    else:
        raise ValueError(f"Unknown data_source: {data_source}. "
                         f"Options: 'raw_validated', 'sorted_selective', 'raw_clustered'")


def load_validated_raw_channels(metric_name):
    """
    Load raw channel data (e.g., A-001) filtered by BOTH GoodChannels AND ChannelFiltering.
    This matches the method used in spi_vs_ici.py.

    Channels must pass both:
    - Manual validation (GoodChannels table)
    - Algorithmic validation (ChannelFiltering with is_good=TRUE)
    """
    conn = Connection("allen_data_repository")

    # Query scores with both filters (no Unit filter for raw channels)
    scores_query = """
                   SELECT s.session_id,
                          s.unit_name,
                          s.frequency,
                          s.metric_name,
                          s.isochromatic_score,
                          s.isoluminant_score
                   FROM IsoChromaticLuminantScores s
                            JOIN GoodChannels g ON s.session_id = g.session_id AND s.unit_name = g.channel
                            JOIN ChannelFiltering c ON s.session_id = c.session_id AND s.unit_name = c.channel
                   WHERE s.metric_name = %s
                     AND s.frequency IN (0.5, 1.0, 2.0, 4.0)
                     AND c.is_good = TRUE
                   """

    # Query solid preference with both filters
    solid_query = """
                  SELECT s.session_id, s.unit_name, s.solid_preference_index, s.p_value
                  FROM SolidPreferenceIndices s
                           JOIN GoodChannels g ON s.session_id = g.session_id AND s.unit_name = g.channel
                           JOIN ChannelFiltering c ON s.session_id = c.session_id AND s.unit_name = c.channel
                  WHERE c.is_good = TRUE
                  """

    conn.execute(scores_query, (metric_name,))
    scores_data = conn.fetch_all()

    conn.execute(solid_query)
    solid_data = conn.fetch_all()

    scores_df = pd.DataFrame(scores_data,
                             columns=['session_id', 'unit_name', 'frequency', 'metric_name',
                                      'isochromatic_score', 'isoluminant_score'])
    solid_df = pd.DataFrame(solid_data,
                            columns=['session_id', 'unit_name', 'solid_preference_index', 'p_value'])

    merged_df = pd.merge(scores_df, solid_df, on=['session_id', 'unit_name'], how='inner')

    print(f"Found {len(merged_df['unit_name'].unique())} validated raw channels (GoodChannels ∩ ChannelFiltering)")

    return merged_df


def load_sorted_selective_units(metric_name):
    """
    Load sorted unit data (e.g., 250915_0_Unit_1) filtered by stimulus selectivity.
    This matches the method used in spi_vs_ici_windowsorted.py.

    Units must have >5% significant pairwise comparisons in stimulus selectivity.
    """
    conn = Connection("allen_data_repository")

    # Get selectivity-filtered units
    selectivity_query = """
                        SELECT session_id,
                               unit_name,
                               n_significant,
                               n_comparisons,
                               (n_significant / n_comparisons) as selectivity_ratio
                        FROM StimulusSelectivity
                        WHERE unit_name LIKE '%Unit%'
                          AND n_comparisons > 0
                          AND n_significant >= 5 * (n_stimuli - 5)
                        """

    conn.execute(selectivity_query)
    selectivity_data = conn.fetch_all()

    if not selectivity_data:
        print("No units meet the stimulus selectivity threshold (>5% significant pairs)")
        return None

    selectivity_df = pd.DataFrame(selectivity_data,
                                  columns=['session_id', 'unit_name', 'n_significant',
                                           'n_comparisons', 'selectivity_ratio'])

    print(f"Found {len(selectivity_df)} sorted units meeting selectivity threshold (>5% significant pairs)")

    # Query scores (only sorted units)
    scores_query = """
                   SELECT session_id,
                          unit_name,
                          frequency,
                          metric_name,
                          isochromatic_score,
                          isoluminant_score
                   FROM IsoChromaticLuminantScores
                   WHERE unit_name LIKE '%Unit%'
                     AND metric_name = %s
                     AND frequency IN (0.5, 1.0, 2.0, 4.0)
                   """

    # Query solid preference (only sorted units)
    solid_query = """
                  SELECT session_id, unit_name, solid_preference_index, p_value
                  FROM SolidPreferenceIndices
                  WHERE unit_name LIKE '%Unit%'
                  """

    conn.execute(scores_query, (metric_name,))
    scores_data = conn.fetch_all()

    conn.execute(solid_query)
    solid_data = conn.fetch_all()

    scores_df = pd.DataFrame(scores_data,
                             columns=['session_id', 'unit_name', 'frequency', 'metric_name',
                                      'isochromatic_score', 'isoluminant_score'])
    solid_df = pd.DataFrame(solid_data,
                            columns=['session_id', 'unit_name', 'solid_preference_index', 'p_value'])

    # Merge with selectivity filter
    scores_df = scores_df.merge(selectivity_df[['session_id', 'unit_name', 'selectivity_ratio']],
                                on=['session_id', 'unit_name'], how='inner')

    # Merge with solid preference p_values
    merged_df = pd.merge(scores_df, solid_df, on=['session_id', 'unit_name'], how='inner')

    return merged_df


def load_clustered_raw_channels(metric_name):
    """
    Load raw cluster channel data from ClusterInfo table.
    This matches the method used in spi_ici_clusters.py.

    Channels are filtered by presence in ClusterInfo table.
    """
    conn = Connection("allen_data_repository")

    # Query scores with ClusterInfo filter
    scores_query = """
                   SELECT s.session_id,
                          s.unit_name,
                          s.frequency,
                          s.metric_name,
                          s.isochromatic_score,
                          s.isoluminant_score
                   FROM IsoChromaticLuminantScores s
                            JOIN Experiments e ON s.session_id = e.session_id
                            JOIN ClusterInfo c ON e.experiment_id = c.experiment_id AND s.unit_name = c.channel
                   WHERE s.metric_name = %s
                     AND s.frequency IN (0.5, 1.0, 2.0, 4.0)
                   """

    # Query solid preference with ClusterInfo filter
    solid_query = """
                  SELECT s.session_id, s.unit_name, s.solid_preference_index, s.p_value
                  FROM SolidPreferenceIndices s
                           JOIN Experiments e ON s.session_id = e.session_id
                           JOIN ClusterInfo c ON e.experiment_id = c.experiment_id AND s.unit_name = c.channel
                  """

    conn.execute(scores_query, (metric_name,))
    scores_data = conn.fetch_all()

    conn.execute(solid_query)
    solid_data = conn.fetch_all()

    scores_df = pd.DataFrame(scores_data,
                             columns=['session_id', 'unit_name', 'frequency', 'metric_name',
                                      'isochromatic_score', 'isoluminant_score'])
    solid_df = pd.DataFrame(solid_data,
                            columns=['session_id', 'unit_name', 'solid_preference_index', 'p_value'])

    # Remove duplicates
    scores_df = scores_df.drop_duplicates(['session_id', 'unit_name', 'frequency'])
    solid_df = solid_df.drop_duplicates(['session_id', 'unit_name'])

    merged_df = pd.merge(scores_df, solid_df, on=['session_id', 'unit_name'], how='inner')

    print(f"Found {len(merged_df['unit_name'].unique())} cluster channels from ClusterInfo")

    return merged_df


# ==================== ANALYSIS FUNCTIONS ====================

def perform_ancova(x, y, groups):
    """
    Perform ANCOVA to test if slopes are different between groups.

    Args:
        x: isochromatic scores
        y: isoluminant scores
        groups: group labels (0 or 1)

    Returns:
        dict with p-values for main effects and interaction
    """
    # Create dataframe for statsmodels
    df = pd.DataFrame({
        'isochromatic': x,
        'isoluminant': y,
        'group': groups
    })

    # Fit model with interaction term
    # isoluminant ~ isochromatic + group + isochromatic:group
    model = ols('isoluminant ~ isochromatic * C(group)', data=df).fit()

    # Perform ANOVA on the model
    anova_results = anova_lm(model, typ=2)

    # Extract p-values
    results = {
        'interaction_p': anova_results.loc['isochromatic:C(group)', 'PR(>F)'],
        'group_p': anova_results.loc['C(group)', 'PR(>F)'],
        'isochromatic_p': anova_results.loc['isochromatic', 'PR(>F)']
    }

    return results


# ==================== PLOTTING FUNCTIONS ====================

def create_combined_frequency_plots(merged_df, frequencies, metric_name, save_path=None, data_source='raw_validated'):
    """Create combined plots showing all data for each frequency."""

    # Create 2x2 subplot layout for 4 frequencies
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))

    # Update title to include data source
    data_source_labels = {
        'raw_validated': 'Validated raw channels (GoodChannels ∩ ChannelFiltering)',
        'sorted_selective': 'Stimulus-selective sorted units (>5% sig. pairs)',
        'raw_clustered': 'Cluster channels (ClusterInfo)'
    }

    fig.suptitle(
        f'Isochromatic vs Isoluminant Scores by Frequency\n'
        f'Metric: {metric_name} ({data_source_labels.get(data_source, data_source)})',
        fontsize=16)

    axes = axes.flatten()

    # Plot each frequency
    for freq_idx, frequency in enumerate(frequencies):
        ax = axes[freq_idx]
        freq_data = merged_df[merged_df['frequency'] == frequency]

        if freq_data.empty:
            ax.text(0.5, 0.5, 'No Data', ha='center', va='center', transform=ax.transAxes)
            ax.set_title(f'{frequency} Hz')
            continue

        # Extract values
        x = freq_data['isochromatic_score'].values
        y = freq_data['isoluminant_score'].values
        p_values = freq_data['p_value'].values
        spi_values = freq_data['solid_preference_index'].values

        # Classify points:
        # Significant 3D: p_value < 0.05 AND solid_preference_index > 0
        # Other: everything else
        sig_3d_mask = (pd.notna(p_values)) & (p_values < 0.05) & (spi_values > 0)

        # Initialize stats variables
        r_sig = r_squared_sig = p_sig = slope_sig = 0
        r_nonsig = r_squared_nonsig = p_nonsig = slope_nonsig = 0
        ancova_p = np.nan

        # Plot significant 3D points
        if sig_3d_mask.any():
            ax.scatter(x[sig_3d_mask], y[sig_3d_mask],
                       c='blue', alpha=0.7, s=60, label='Significant 3D (p<0.05)',
                       edgecolors='black', linewidths=0.5)

            # Plot trend line for sig 3D points
            x_sig = x[sig_3d_mask]
            y_sig = y[sig_3d_mask]
            if len(x_sig) > 1:
                slope_sig, intercept_sig, r_sig, p_sig, _ = stats.linregress(x_sig, y_sig)
                r_squared_sig = r_sig ** 2
                line_x_sig = np.linspace(x_sig.min(), x_sig.max(), 100)
                line_y_sig = slope_sig * line_x_sig + intercept_sig
                ax.plot(line_x_sig, line_y_sig, 'b-', linewidth=2, alpha=0.8)

        # Plot non-significant points
        if (~sig_3d_mask).any():
            ax.scatter(x[~sig_3d_mask], y[~sig_3d_mask],
                       c='orange', alpha=0.7, s=60, label='Non-significant 3D',
                       edgecolors='black', linewidths=0.5)

            # Plot trend line for non-sig points
            x_nonsig = x[~sig_3d_mask]
            y_nonsig = y[~sig_3d_mask]
            if len(x_nonsig) > 1:
                slope_nonsig, intercept_nonsig, r_nonsig, p_nonsig, _ = stats.linregress(x_nonsig, y_nonsig)
                r_squared_nonsig = r_nonsig ** 2
                line_x_nonsig = np.linspace(x_nonsig.min(), x_nonsig.max(), 100)
                line_y_nonsig = slope_nonsig * line_x_nonsig + intercept_nonsig
                ax.plot(line_x_nonsig, line_y_nonsig, color='orange', linestyle='-', linewidth=2, alpha=0.8)

        # Perform ANCOVA if both groups have enough data
        n_sig_3d = np.sum(sig_3d_mask)
        n_other = np.sum(~sig_3d_mask)

        if n_sig_3d > 2 and n_other > 2:  # Need at least 3 points per group
            try:
                # Create group labels (0 for non-sig, 1 for sig 3D)
                groups = sig_3d_mask.astype(int)
                ancova_results = perform_ancova(x, y, groups)
                ancova_p = ancova_results['interaction_p']
            except Exception as e:
                print(f"ANCOVA failed for {frequency} Hz: {e}")
                ancova_p = np.nan

        # Set title and labels
        ax.set_title(f'{frequency} Hz (n={len(freq_data)}, {n_sig_3d} sig. 3D, {n_other} non-sig)')
        ax.set_xlabel('Isochromatic Score (spikes/s)')
        ax.set_ylabel('Isoluminant Score (spikes/s)')

        # Add diagonal reference line (y=x)
        lims = [
            np.min([ax.get_xlim(), ax.get_ylim()]),
            np.max([ax.get_xlim(), ax.get_ylim()]),
        ]
        ax.plot(lims, lims, 'k--', alpha=0.3, zorder=0, linewidth=1)

        # Add grid
        ax.grid(True, alpha=0.3)

        # Add statistics text - separate for each group plus ANCOVA
        stats_text = f'Sig 3D: slope={slope_sig:.3f}, R²={r_squared_sig:.3f}, r={r_sig:.3f}, p={p_sig:.3f}, n={n_sig_3d}\n' \
                     f'Non-sig: slope={slope_nonsig:.3f}, R²={r_squared_nonsig:.3f}, r={r_nonsig:.3f}, p={p_nonsig:.3f}, n={n_other}\n' \
                     f'ANCOVA (slopes diff): p={ancova_p:.3f}'
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
                verticalalignment='top', fontsize=8,
                bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))

        # Add legend
        ax.legend(loc='lower right', fontsize=9)

    plt.tight_layout()

    # Save if path provided
    if save_path is not None:
        filename = os.path.join(save_path, f'isochrom_vs_isolum_{metric_name}_{data_source}.png')
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"Saved: {filename}")

    plt.show()

    # Print statistics
    print(f"\nOverall Statistics for {metric_name} (data_source={data_source}):")
    for frequency in frequencies:
        freq_data = merged_df[merged_df['frequency'] == frequency]
        if not freq_data.empty:
            x = freq_data['isochromatic_score'].values
            y = freq_data['isoluminant_score'].values
            p_vals = freq_data['p_value'].values
            spi_vals = freq_data['solid_preference_index'].values

            sig_3d_mask = (pd.notna(p_vals)) & (p_vals < 0.05) & (spi_vals > 0)
            n_sig_3d = np.sum(sig_3d_mask)
            n_other = np.sum(~sig_3d_mask)

            print(f"  {frequency} Hz: n={len(freq_data)} ({n_sig_3d} sig. 3D, {n_other} non-sig)")

            if n_sig_3d > 1:
                x_sig = x[sig_3d_mask]
                y_sig = y[sig_3d_mask]
                slope, _, r_sig, p_sig, _ = stats.linregress(x_sig, y_sig)
                print(f"    Sig 3D: slope={slope:.3f}, r={r_sig:.3f}, p={p_sig:.3f}")
            else:
                print(f"    Sig 3D: insufficient data for correlation")

            if n_other > 1:
                x_other = x[~sig_3d_mask]
                y_other = y[~sig_3d_mask]
                slope, _, r_other, p_other, _ = stats.linregress(x_other, y_other)
                print(f"    Non-sig: slope={slope:.3f}, r={r_other:.3f}, p={p_other:.3f}")
            else:
                print(f"    Non-sig: insufficient data for correlation")

            # Print ANCOVA result
            if n_sig_3d > 2 and n_other > 2:
                try:
                    groups = sig_3d_mask.astype(int)
                    ancova_results = perform_ancova(x, y, groups)
                    print(f"    ANCOVA interaction p-value: {ancova_results['interaction_p']:.3f}")
                except Exception as e:
                    print(f"    ANCOVA failed: {e}")


if __name__ == "__main__":
    main()