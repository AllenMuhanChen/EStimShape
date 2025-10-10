import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os
import json
from scipy import stats
from clat.util.connection import Connection
from src.analysis.spi_vs_ici.spi_vs_ici_windowsorted import get_selectivity_query


def create_all_preference_plots(save_dir=None, threshold=0.7):
    """
    Create all three types of preference plots.

    Args:
        save_dir: Directory to save plots. If None, plots are only displayed.
        threshold: Minimum fraction of absolute max response required (default 0.7 = 70%)
    """
    if save_dir is not None:
        os.makedirs(save_dir, exist_ok=True)

    # Get the data
    merged_data = load_and_filter_data(threshold)

    if merged_data is None:
        print("No data available for plotting")
        return

    # 1. Preferred frequency only plot
    print("\n" + "=" * 60)
    print("Creating Plot 1: Preferred Frequencies Only")
    print("=" * 60)
    preferred_only_data = merged_data['preferred_only']
    if not preferred_only_data.empty:
        save_path_1 = os.path.join(save_dir, "01_preferred_frequency_only.png") if save_dir else None
        plot_preferred_frequency_only(preferred_only_data, save_path_1)
    else:
        print("No data for preferred frequency plot")

    # 2. Combined plot with all strong frequencies
    print("\n" + "=" * 60)
    print("Creating Plot 2: Combined Strong Frequencies")
    print("=" * 60)
    combined_data = merged_data['all_strong']
    if not combined_data.empty:
        save_path_2 = os.path.join(save_dir, "02_combined_strong_frequencies.png") if save_dir else None
        plot_combined_strong_frequencies(combined_data, save_path_2, threshold)
    else:
        print("No data for combined plot")

    # 3. Individual plots for each frequency
    print("\n" + "=" * 60)
    print("Creating Plot 3: Individual Frequency Plots")
    print("=" * 60)
    individual_data = merged_data['all_strong']
    if not individual_data.empty:
        plot_individual_frequencies(individual_data, save_dir, threshold)
    else:
        print("No data for individual frequency plots")

    plt.show()


def load_and_filter_data(threshold=0.7):
    """
    Load and filter all necessary data from database.

    Returns:
        Dictionary with 'preferred_only' and 'all_strong' DataFrames
    """
    conn = Connection("allen_data_repository")

    # Get units that pass stimulus selectivity threshold


    conn.execute(get_selectivity_query())
    selectivity_data = conn.fetch_all()

    if not selectivity_data:
        print("No units meet the stimulus selectivity threshold (>5% significant pairs)")
        return None

    selectivity_df = pd.DataFrame(selectivity_data,
                                  columns=['session_id', 'unit_name', 'n_significant',
                                           'n_comparisons', 'selectivity_ratio'])

    print(f"Found {len(selectivity_df)} units meeting selectivity threshold")

    # Get preferred frequencies
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

    # Parse JSON and identify strong frequencies
    def parse_frequencies(row):
        try:
            all_freqs = json.loads(row['all_freq_responses'])
            absolute_max = max(all_freqs.values())

            # Get all frequencies >= threshold
            strong_freqs = [float(freq) for freq, response in all_freqs.items()
                            if response >= threshold * absolute_max]

            return strong_freqs
        except Exception as e:
            print(f"Error parsing frequencies: {e}")
            return []

    preferred_freq_df['strong_frequencies'] = preferred_freq_df.apply(parse_frequencies, axis=1)

    # Get solid preference indices
    solid_query = """
                  SELECT session_id, unit_name, solid_preference_index, p_value
                  FROM SolidPreferenceIndices
                  WHERE unit_name LIKE '%Unit%'
                  """

    conn.execute(solid_query)
    solid_data = conn.fetch_all()
    solid_df = pd.DataFrame(solid_data,
                            columns=['session_id', 'unit_name', 'solid_preference_index', 'p_value'])

    # Get isochromatic preference indices
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

    # Merge base data
    base_df = solid_df.merge(
        selectivity_df[['session_id', 'unit_name', 'selectivity_ratio']],
        on=['session_id', 'unit_name'], how='inner'
    )

    base_df = base_df.merge(
        preferred_freq_df[['session_id', 'unit_name', 'preferred_frequency', 'strong_frequencies']],
        on=['session_id', 'unit_name'], how='inner'
    )

    base_df = base_df.merge(
        isochromatic_df,
        on=['session_id', 'unit_name'], how='inner'
    )

    if base_df.empty:
        print("No data after merging")
        return None

    # Filter to allowed frequencies
    allowed_frequencies = [0.5, 1.0, 2.0, 4.0]
    base_df = base_df[base_df['frequency'].isin(allowed_frequencies)]

    # Create dataset 1: Preferred frequency only
    preferred_only = base_df[base_df['frequency'] == base_df['preferred_frequency']].copy()

    # Create dataset 2: All strong frequencies
    def is_strong_freq(row):
        return float(row['frequency']) in row['strong_frequencies']

    all_strong = base_df[base_df.apply(is_strong_freq, axis=1)].copy()

    return {
        'preferred_only': preferred_only,
        'all_strong': all_strong
    }


def plot_preferred_frequency_only(data, save_path=None):
    """Plot 1: Only the preferred frequency for each unit."""

    x = data['solid_preference_index'].values
    y = data['isochromatic_preference_index'].values
    p_values = data['p_value'].values
    frequencies = data['preferred_frequency'].values

    # Calculate regression
    slope, intercept, r_value, p_value, _ = stats.linregress(x, y)
    r_squared = r_value ** 2

    # Create plot
    plt.figure(figsize=(12, 10))

    # Color map for frequencies
    all_freqs = sorted(data['preferred_frequency'].unique())
    freq_cmap = plt.cm.viridis
    freq_colors = {freq: freq_cmap(i / (len(all_freqs) - 1)) for i, freq in enumerate(all_freqs)}

    # Plot points
    for i in range(len(x)):
        freq = frequencies[i]
        color = freq_colors[freq]

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
    line_x = np.linspace(-1.1, 1.1, 100)
    line_y = slope * line_x + intercept
    plt.plot(line_x, line_y, 'k-', linewidth=2, label=f'Trend (R²={r_squared:.3f})')

    # Formatting
    n_significant = np.sum((pd.notna(p_values)) & (p_values < 0.05))
    plt.xlabel('Solid Preference Index', fontsize=14)
    plt.ylabel('Isochromatic Preference Index', fontsize=14)
    plt.title(
        f'Solid vs Isochromatic Preference at Preferred Frequency\n'
        f'(n={len(data)} units, {n_significant} solid-pref significant)',
        fontsize=16)

    add_plot_formatting(plt.gca(), r_squared, r_value, p_value, len(data), n_significant)

    # Legend for frequencies
    freq_legend = [plt.Line2D([0], [0], marker='o', color='w',
                              markerfacecolor=freq_colors[freq],
                              markersize=10, label=f'{freq} Hz',
                              markeredgecolor='black', markeredgewidth=0.5)
                   for freq in all_freqs]
    freq_legend.append(plt.Line2D([0], [0], color='black', linewidth=2,
                                  label=f'Trend (R²={r_squared:.3f})'))

    plt.legend(handles=freq_legend, bbox_to_anchor=(1.05, 1),
               loc='upper left', title='Preferred Frequency')

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Saved: {save_path}")

    print(f"\nPreferred Frequency Only Statistics:")
    print(f"  Total units: {len(data)}")
    print(f"  Significant: {n_significant}")
    print(f"  R² = {r_squared:.3f}, r = {r_value:.3f}, p = {p_value:.3f}")


def plot_combined_strong_frequencies(data, save_path=None, threshold=0.7):
    """Plot 2: Combined plot with all strong frequencies and separate trend lines."""

    x = data['solid_preference_index'].values
    y = data['isochromatic_preference_index'].values
    p_values = data['p_value'].values
    frequencies = data['frequency'].values

    # Overall regression
    slope_all, intercept_all, r_value_all, p_value_all, _ = stats.linregress(x, y)
    r_squared_all = r_value_all ** 2

    # Create plot
    plt.figure(figsize=(12, 10))

    # Color map
    all_freqs = [0.5, 1.0, 2.0, 4.0]
    freq_cmap = plt.cm.viridis
    freq_colors = {freq: freq_cmap(i / 3) for i, freq in enumerate(all_freqs)}

    # Plot points
    for i in range(len(x)):
        freq = frequencies[i]
        color = freq_colors[freq]

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

    # Plot trend lines for each frequency
    line_x = np.linspace(-1.1, 1.1, 100)

    for freq in all_freqs:
        freq_data = data[data['frequency'] == freq]
        if len(freq_data) > 1:
            x_freq = freq_data['solid_preference_index'].values
            y_freq = freq_data['isochromatic_preference_index'].values

            slope, intercept, r_value, p_val, _ = stats.linregress(x_freq, y_freq)
            r_squared = r_value ** 2

            line_y = slope * line_x + intercept
            plt.plot(line_x, line_y, linewidth=2, color=freq_colors[freq],
                     linestyle='--', alpha=0.8,
                     label=f'{freq} Hz (R²={r_squared:.2f}, n={len(x_freq)})')

    # Overall trend line
    line_y_all = slope_all * line_x + intercept_all
    plt.plot(line_x, line_y_all, 'k-', linewidth=3, alpha=0.5,
             label=f'All (R²={r_squared_all:.2f}, n={len(x)})')

    # Formatting
    n_significant = np.sum((pd.notna(p_values)) & (p_values < 0.05))
    plt.xlabel('Solid Preference Index', fontsize=14)
    plt.ylabel('Isochromatic Preference Index', fontsize=14)
    plt.title(
        f'Solid vs Isochromatic Preference at Strong Frequencies (≥{threshold * 100:.0f}% of max)\n'
        f'(n={len(data)} data points, {n_significant} solid-pref significant)',
        fontsize=16)

    add_plot_formatting(plt.gca(), r_squared_all, r_value_all, p_value_all, len(data), n_significant)

    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', title='Frequency')
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Saved: {save_path}")

    # Print statistics
    print(f"\nCombined Strong Frequencies Statistics:")
    print(f"  Total data points: {len(data)}")
    print(f"  Significant: {n_significant}")
    print(f"  Overall: R² = {r_squared_all:.3f}, r = {r_value_all:.3f}, p = {p_value_all:.3f}")

    for freq in all_freqs:
        freq_data = data[data['frequency'] == freq]
        if not freq_data.empty:
            n_sig = np.sum((pd.notna(freq_data['p_value'])) & (freq_data['p_value'] < 0.05))
            if len(freq_data) > 1:
                x_f = freq_data['solid_preference_index'].values
                y_f = freq_data['isochromatic_preference_index'].values
                _, _, r_val, p_val, _ = stats.linregress(x_f, y_f)
                print(f"    {freq} Hz: n={len(freq_data)} ({n_sig} sig.), r={r_val:.3f}, p={p_val:.3f}")


def plot_individual_frequencies(data, save_dir=None, threshold=0.7):
    """Plot 3: Individual plots for each frequency."""

    allowed_frequencies = [0.5, 1.0, 2.0, 4.0]

    # Color map
    freq_cmap = plt.cm.viridis
    freq_colors = {freq: freq_cmap(i / 3) for i, freq in enumerate(allowed_frequencies)}

    for freq in allowed_frequencies:
        freq_data = data[data['frequency'] == freq]

        if freq_data.empty:
            print(f"No data for {freq} Hz")
            continue

        x = freq_data['solid_preference_index'].values
        y = freq_data['isochromatic_preference_index'].values
        p_values = freq_data['p_value'].values

        # Calculate regression
        if len(x) > 1:
            slope, intercept, r_value, p_value, _ = stats.linregress(x, y)
            r_squared = r_value ** 2
        else:
            slope = intercept = r_value = p_value = r_squared = 0

        # Create plot
        plt.figure(figsize=(10, 8))

        color = freq_colors[freq]

        # Plot points
        for i in range(len(x)):
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
        if len(x) > 1:
            line_x = np.linspace(-1.1, 1.1, 100)
            line_y = slope * line_x + intercept
            plt.plot(line_x, line_y, linewidth=2, color=color,
                     label=f'Trend (R²={r_squared:.3f})')

        # Formatting
        n_significant = np.sum((pd.notna(p_values)) & (p_values < 0.05))
        plt.xlabel('Solid Preference Index', fontsize=14)
        plt.ylabel('Isochromatic Preference Index', fontsize=14)
        plt.title(
            f'Solid vs Isochromatic Preference at {freq} Hz (≥{threshold * 100:.0f}% of max)\n'
            f'(n={len(freq_data)} data points, {n_significant} solid-pref significant)',
            fontsize=16)

        add_plot_formatting(plt.gca(), r_squared, r_value, p_value, len(freq_data), n_significant)

        if len(x) > 1:
            plt.legend(loc='upper left')

        plt.tight_layout()

        if save_dir:
            save_path = os.path.join(save_dir, f"03_individual_{freq}Hz.png")
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Saved: {save_path}")

        print(f"\n{freq} Hz Statistics:")
        print(f"  Data points: {len(freq_data)}")
        print(f"  Significant: {n_significant}")
        if len(x) > 1:
            print(f"  R² = {r_squared:.3f}, r = {r_value:.3f}, p = {p_value:.3f}")


def add_plot_formatting(ax, r_squared, r_value, p_value, n, n_sig):
    """Add common formatting to plots."""

    # Reference lines
    ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    ax.axvline(x=0, color='gray', linestyle='--', alpha=0.5)

    # Grid
    ax.grid(True, alpha=0.3)

    # Axis limits
    ax.set_xlim(-1.1, 1.1)
    ax.set_ylim(-1.1, 1.1)

    # Statistics text box
    stats_text = f'R² = {r_squared:.3f}\nr = {r_value:.3f}\np = {p_value:.3f}\nn = {n}\nsig. = {n_sig}'
    ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
            verticalalignment='top', fontsize=10,
            bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))

    # Quadrant labels
    ax.text(0.4, 0.9, 'Prefers 3D &\nIsochromatic', ha='center', va='center',
            bbox=dict(boxstyle="round,pad=0.3", facecolor='lightblue', alpha=0.5), fontsize=10)
    ax.text(-0.6, 0.9, 'Prefers 2D &\nIsochromatic', ha='center', va='center',
            bbox=dict(boxstyle="round,pad=0.3", facecolor='lightgreen', alpha=0.5), fontsize=10)
    ax.text(0.4, -0.9, 'Prefers 3D &\nIsoluminant', ha='center', va='center',
            bbox=dict(boxstyle="round,pad=0.3", facecolor='lightcoral', alpha=0.5), fontsize=10)
    ax.text(-0.6, -0.9, 'Prefers 2D &\nIsoluminant', ha='center', va='center',
            bbox=dict(boxstyle="round,pad=0.3", facecolor='lightyellow', alpha=0.5), fontsize=10)


if __name__ == "__main__":
    # Create all three types of plots
    create_all_preference_plots(
        save_dir="/home/connorlab/Documents/plots/spi_vs_ici",
        threshold=0.7
    )