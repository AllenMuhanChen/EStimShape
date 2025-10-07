import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os
import json
from scipy import stats
from clat.util.connection import Connection


def create_preference_indices_at_preferred_frequency_plot(save_path=None, threshold=0.7):
    """Create a single plot showing solid vs isochromatic preference at each unit's preferred frequency.
    Only includes units with significant stimulus selectivity (>5% significant pairs) and where
    the frequency's max response is at least threshold (default 70%) of the absolute maximum.

    Args:
        save_path: Optional path to save the plot. If None, plot is only displayed.
        threshold: Minimum fraction of absolute max response required (default 0.7 = 70%)
    """

    # Create save directory if specified and doesn't exist
    if save_path is not None:
        save_dir = os.path.dirname(save_path)
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)

    # Connect to the data repository database
    conn = Connection("allen_data_repository")

    # First, get units that pass the stimulus selectivity threshold
    selectivity_query = """
                        SELECT session_id,
                               unit_name,
                               n_significant,
                               n_comparisons,
                               (n_significant / n_comparisons) as selectivity_ratio
                        FROM StimulusSelectivity
                        WHERE unit_name LIKE '%Unit%'
                          AND n_comparisons > 0
                          AND (n_significant / n_comparisons) >= 0.05
                        """

    conn.execute(selectivity_query)
    selectivity_data = conn.fetch_all()

    if not selectivity_data:
        print("No units meet the stimulus selectivity threshold (>5% significant pairs)")
        return None

    selectivity_df = pd.DataFrame(selectivity_data,
                                  columns=['session_id', 'unit_name', 'n_significant',
                                           'n_comparisons', 'selectivity_ratio'])

    print(f"Found {len(selectivity_df)} units meeting selectivity threshold (>5% significant pairs)")
    print(f"  Example units: {list(selectivity_df['unit_name'].head(3))}")

    # Query preferred frequencies with all frequency responses
    preferred_freq_query = """
                           SELECT session_id, unit_name, preferred_frequency, all_freq_responses
                           FROM PreferredFrequencies
                           WHERE unit_name LIKE '%Unit%'
                           """

    conn.execute(preferred_freq_query)
    preferred_freq_data = conn.fetch_all()

    if not preferred_freq_data:
        print("No preferred frequency data found")
        return None

    preferred_freq_df = pd.DataFrame(preferred_freq_data,
                                     columns=['session_id', 'unit_name', 'preferred_frequency',
                                              'all_freq_responses'])

    print(f"  Preferred freq units: {list(preferred_freq_df['unit_name'].head(3))}")

    # Parse JSON and filter by threshold
    def parse_and_filter_freqs(row):
        try:
            all_freqs = json.loads(row['all_freq_responses'])
            # Find absolute max across all frequencies
            absolute_max = max(all_freqs.values())
            # Get frequencies that are at least threshold% of absolute max
            # IMPORTANT: Convert string keys to float for comparison
            valid_freqs = [float(freq) for freq, response in all_freqs.items()
                           if response >= threshold * absolute_max]
            return valid_freqs
        except Exception as e:
            print(f"Error parsing frequencies for {row['session_id']}, {row['unit_name']}: {e}")
            return []

    preferred_freq_df['valid_frequencies'] = preferred_freq_df.apply(parse_and_filter_freqs, axis=1)

    # Query solid preference indices with p-values
    solid_query = """
                  SELECT session_id, unit_name, solid_preference_index, p_value
                  FROM SolidPreferenceIndices
                  WHERE unit_name LIKE '%Unit%'
                  """

    conn.execute(solid_query)
    solid_data = conn.fetch_all()
    solid_df = pd.DataFrame(solid_data,
                            columns=['session_id', 'unit_name', 'solid_preference_index', 'p_value'])

    print(f"  Solid pref units: {list(solid_df['unit_name'].head(3))}")

    # Query isochromatic preference indices (all frequencies)
    isochromatic_query = """
                         SELECT session_id, unit_name, frequency, isochromatic_preference_index
                         FROM IsochromaticPreferenceIndices
                         WHERE unit_name LIKE '%Unit%'
                         """

    conn.execute(isochromatic_query)
    isochromatic_data = conn.fetch_all()
    isochromatic_df = pd.DataFrame(isochromatic_data,
                                   columns=['session_id', 'unit_name', 'frequency',
                                            'isochromatic_preference_index'])

    print(f"  Isochromatic units: {list(isochromatic_df['unit_name'].unique()[:3])}")
    print(f"  Total isochromatic rows: {len(isochromatic_df)}")

    # Merge all data - step by step with debug
    print("\n=== Merge step 1: solid + selectivity ===")
    solid_df = solid_df.merge(selectivity_df[['session_id', 'unit_name', 'selectivity_ratio']],
                              on=['session_id', 'unit_name'], how='inner')
    print(f"  After merge: {len(solid_df)} rows")
    print(f"  Units: {list(solid_df['unit_name'].head(3))}")

    print("\n=== Merge step 2: + preferred frequency ===")
    solid_df = solid_df.merge(preferred_freq_df[['session_id', 'unit_name', 'valid_frequencies']],
                              on=['session_id', 'unit_name'], how='inner')
    print(f"  After merge: {len(solid_df)} rows")
    print(f"  Units: {list(solid_df['unit_name'].head(3))}")

    print("\n=== Merge step 3: + isochromatic ===")
    print(f"  Before merge - solid_df has {len(solid_df)} rows")
    print(f"  Before merge - isochromatic_df has {len(isochromatic_df)} rows")

    # Check for overlap
    solid_units = set(zip(solid_df['session_id'], solid_df['unit_name']))
    iso_units = set(zip(isochromatic_df['session_id'], isochromatic_df['unit_name']))
    overlap = solid_units & iso_units

    print(f"  Units in solid_df: {len(solid_units)}")
    print(f"  Units in isochromatic_df: {len(iso_units)}")
    print(f"  Overlapping units: {len(overlap)}")

    if len(overlap) == 0:
        print("\n  ERROR: No overlapping units! Sample units from each:")
        print(f"    Solid units: {list(solid_units)[:3]}")
        print(f"    Iso units: {list(iso_units)[:3]}")
        return None

    merged_df = solid_df.merge(isochromatic_df, on=['session_id', 'unit_name'], how='inner')
    print(f"  After merge: {len(merged_df)} rows")

    if merged_df.empty:
        print("No data after merging with isochromatic preferences")
        return None

    # Filter to only keep rows where frequency is in valid_frequencies list
    def is_valid_freq(row):
        freq = float(row['frequency'])
        valid = freq in row['valid_frequencies']
        return valid

    merged_df = merged_df[merged_df.apply(is_valid_freq, axis=1)]

    print(f"After frequency filter: {len(merged_df)} rows")

    if merged_df.empty:
        print(f"No matching data found after applying {threshold * 100}% threshold filter.")
        return None

    # Rest of the function...
    sessions = sorted(merged_df['session_id'].unique())
    all_freqs = sorted(merged_df['frequency'].unique())

    print(f"\nCreating plot for {len(sessions)} sessions: {sessions}")
    print(f"Frequencies found (at ≥{threshold * 100}% of max): {all_freqs}")
    print(f"Total data points: {len(merged_df)}")

    # Show breakdown by session
    for session in sessions:
        session_data = merged_df[merged_df['session_id'] == session]
        session_units = len(session_data)
        significant_units = session_data[session_data['p_value'] < 0.05].shape[0]
        print(f"  Session {session}: {session_units} data points ({significant_units} solid-pref significant)")

    # Create the plot
    plot_filtered_frequency_data(merged_df, sessions, all_freqs, save_path, threshold)

    return merged_df

def plot_filtered_frequency_data(merged_df, sessions, all_freqs, save_path=None, threshold=0.7):
    """Create a single plot with units at frequencies ≥threshold of their max."""

    # Extract values
    x = merged_df['solid_preference_index'].values
    y = merged_df['isochromatic_preference_index'].values
    p_values = merged_df['p_value'].values
    frequencies = merged_df['frequency'].values

    # Calculate linear regression for all data
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
    r_squared = r_value ** 2

    # Create the scatter plot
    plt.figure(figsize=(12, 10))

    # Create color map for frequencies
    freq_cmap = plt.cm.viridis
    freq_colors = {freq: freq_cmap(i / len(all_freqs))
                   for i, freq in enumerate(all_freqs)}

    # Plot each point with same marker shape
    for i in range(len(x)):
        freq = frequencies[i]

        # Determine color based on frequency
        color = freq_colors[freq]

        # Determine alpha based on significance
        if pd.notna(p_values[i]) and p_values[i] < 0.05:
            alpha_val = 0.7
            edge_color = 'black'
            linewidth = 0.5
        else:
            alpha_val = 0.15
            edge_color = 'gray'
            linewidth = 0.3

        plt.scatter(x[i], y[i], alpha=alpha_val, s=100,
                    color=color, marker='o',
                    edgecolors=edge_color, linewidths=linewidth)

    # Add trend line
    line_x = np.linspace(x.min(), x.max(), 100)
    line_y = slope * line_x + intercept
    plt.plot(line_x, line_y, 'k-', linewidth=2, label=f'Trend (R² = {r_squared:.3f})')

    # Add labels and title
    n_significant = np.sum((pd.notna(p_values)) & (p_values < 0.05))
    plt.xlabel('Solid Preference Index', fontsize=14)
    plt.ylabel('Isochromatic Preference Index', fontsize=14)
    plt.title(
        f'Solid vs Isochromatic Preference at Strong Frequencies (≥{threshold * 100:.0f}% of max)\n'
        f'(Stimulus-selective units: n={len(merged_df)} total, {n_significant} solid-pref significant)',
        fontsize=16)

    # Add reference lines at zero
    plt.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    plt.axvline(x=0, color='gray', linestyle='--', alpha=0.5)

    # Add grid
    plt.grid(True, alpha=0.3)

    # Set axis limits
    plt.xlim(-1.1, 1.1)
    plt.ylim(-1.1, 1.1)

    # Create frequency color legend
    freq_legend_elements = [plt.Line2D([0], [0], marker='o', color='w',
                                       markerfacecolor=freq_colors[freq],
                                       markersize=10, label=f'{freq} Hz',
                                       markeredgecolor='black', markeredgewidth=0.5)
                            for freq in all_freqs]

    # Add trend line to legend
    trend_legend = [plt.Line2D([0], [0], color='black', linewidth=2,
                               label=f'Trend (R²={r_squared:.3f})')]

    # Combine legend elements
    all_legend_elements = freq_legend_elements + trend_legend

    # Add legend
    plt.legend(handles=all_legend_elements, bbox_to_anchor=(1.05, 1),
               loc='upper left', title='Frequency')

    # Add statistics text box
    stats_text = f'R² = {r_squared:.3f}\nr = {r_value:.3f}\np = {p_value:.3f}\nn = {len(merged_df)}\nsig. = {n_significant}'
    plt.text(0.02, 0.98, stats_text, transform=plt.gca().transAxes,
             verticalalignment='top', fontsize=10,
             bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))

    # Add quadrant labels
    plt.text(0.4, 0.9, 'Prefers 3D &\nIsochromatic', ha='center', va='center',
             bbox=dict(boxstyle="round,pad=0.3", facecolor='lightblue', alpha=0.5), fontsize=10)
    plt.text(-0.6, 0.9, 'Prefers 2D &\nIsochromatic', ha='center', va='center',
             bbox=dict(boxstyle="round,pad=0.3", facecolor='lightgreen', alpha=0.5), fontsize=10)
    plt.text(0.4, -0.9, 'Prefers 3D &\nIsoluminant', ha='center', va='center',
             bbox=dict(boxstyle="round,pad=0.3", facecolor='lightcoral', alpha=0.5), fontsize=10)
    plt.text(-0.6, -0.9, 'Prefers 2D &\nIsoluminant', ha='center', va='center',
             bbox=dict(boxstyle="round,pad=0.3", facecolor='lightyellow', alpha=0.5), fontsize=10)

    plt.tight_layout()

    # Save if path provided
    if save_path is not None:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"\nSaved: {save_path}")

    plt.show()

    # Print statistics
    print(f"\nStatistics at Strong Frequencies (≥{threshold * 100:.0f}% of max):")
    print(f"  Total data points: {len(merged_df)}")
    print(f"  Significant units (solid-pref p < 0.05): {n_significant}")
    print(f"  Solid Preference range: {x.min():.3f} to {x.max():.3f}")
    print(f"  Isochromatic Preference range: {y.min():.3f} to {y.max():.3f}")
    print(f"  Correlation: r = {r_value:.3f}, R² = {r_squared:.3f}, p = {p_value:.3f}")

    # Breakdown by frequency
    print(f"\n  Breakdown by frequency:")
    for freq in all_freqs:
        freq_data = merged_df[merged_df['frequency'] == freq]
        n_points = len(freq_data)
        n_sig = np.sum((pd.notna(freq_data['p_value'])) & (freq_data['p_value'] < 0.05))
        print(f"    {freq} Hz: {n_points} data points ({n_sig} significant)")


if __name__ == "__main__":
    # Example usage with 70% threshold
    data = create_preference_indices_at_preferred_frequency_plot(
        save_path="/home/connorlab/Documents/plots/spi_vs_ici/filtered_frequency_plot.png",
        threshold=0.7
    )