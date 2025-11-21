import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from scipy import stats
from clat.util.connection import Connection


def permutation_test_lower_quantile(sig_3d_values, non_sig_values, quantile=10, n_permutations=10000):
    """
    Permutation test to check if sig 3D has a higher lower quantile than non-sig.

    Tests the hypothesis that sig 3D cells are excluded from low preference regions.

    Args:
        sig_3d_values: array of sig 3D preference values
        non_sig_values: array of non-sig preference values
        quantile: which percentile to test (default 10 = 10th percentile)
        n_permutations: number of permutations
    """
    # Actual quantile difference
    actual_q_sig = np.percentile(sig_3d_values, quantile)
    actual_q_nonsig = np.percentile(non_sig_values, quantile)
    actual_diff = actual_q_sig - actual_q_nonsig

    # Combine all values
    all_values = np.concatenate([sig_3d_values, non_sig_values])
    n_sig = len(sig_3d_values)
    n_total = len(all_values)

    # Permutation distribution
    perm_diffs = []
    for _ in range(n_permutations):
        # Shuffle and split
        shuffled = np.random.permutation(all_values)
        perm_sig = shuffled[:n_sig]
        perm_nonsig = shuffled[n_sig:]

        # Calculate quantile difference
        perm_diff = np.percentile(perm_sig, quantile) - np.percentile(perm_nonsig, quantile)
        perm_diffs.append(perm_diff)

    perm_diffs = np.array(perm_diffs)

    # One-sided p-value (testing if sig 3D quantile is HIGHER)
    p_value = np.mean(perm_diffs >= actual_diff)

    return {
        'q_sig_3d': actual_q_sig,
        'q_non_sig': actual_q_nonsig,
        'difference': actual_diff,
        'p_value': p_value,
        'quantile': quantile
    }


def create_isochromatic_preference_histograms(quantile=10):
    """
    Create histograms comparing isochromatic preference distributions
    between significant 3D and non-significant cells.
    Only plots frequencies: 0.5, 1.0, 2.0, 4.0 Hz

    Args:
        quantile: which percentile to test (default 10 = 10th percentile)
    """

    conn = Connection("allen_data_repository")

    # Query solid preference WITH p-values for significance classification
    solid_query = """
                  SELECT s.session_id, s.unit_name, s.solid_preference_index, s.p_value
                  FROM SolidPreferenceIndices s
                           JOIN GoodChannels g ON s.session_id = g.session_id AND s.unit_name = g.channel
                           JOIN ChannelFiltering c ON s.session_id = c.session_id AND s.unit_name = c.channel
                  WHERE c.is_good = TRUE
                  """

    # Isochromatic preference with frequency filter
    isochromatic_query = """
                         SELECT i.session_id, i.unit_name, i.frequency, i.isochromatic_preference_index
                         FROM IsochromaticPreferenceIndices i
                                  JOIN GoodChannels g ON i.session_id = g.session_id AND i.unit_name = g.channel
                                  JOIN ChannelFiltering c ON i.session_id = c.session_id AND i.unit_name = c.channel
                         WHERE c.is_good = TRUE
                           AND i.frequency IN (0.5, 1.0, 2.0, 4.0)
                         """

    # Fetch and merge data
    conn.execute(solid_query)
    solid_data = conn.fetch_all()

    conn.execute(isochromatic_query)
    isochromatic_data = conn.fetch_all()

    solid_df = pd.DataFrame(solid_data,
                            columns=['session_id', 'unit_name', 'solid_preference_index', 'p_value'])
    isochromatic_df = pd.DataFrame(isochromatic_data,
                                   columns=['session_id', 'unit_name', 'frequency', 'isochromatic_preference_index'])

    merged_df = pd.merge(solid_df, isochromatic_df, on=['session_id', 'unit_name'], how='inner')

    # Get frequencies (should only be 0.5, 1.0, 2.0, 4.0)
    frequencies = [0.5, 1.0, 2.0, 4.0]
    frequencies = [f for f in frequencies if f in merged_df['frequency'].values]

    print(f"Creating histograms for {len(frequencies)} frequencies: {frequencies}")
    print(f"Testing {quantile}th percentile constraint")

    # Create histograms for each frequency
    create_frequency_histograms(merged_df, frequencies, quantile)

    # Create solid preference histograms split by isochromatic sign
    create_solid_preference_by_isochromatic_sign(merged_df, frequencies, quantile)

    return merged_df


def create_solid_preference_by_isochromatic_sign(merged_df, frequencies, quantile=10):
    """
    Create histograms of solid preference index split by isochromatic preference sign.

    Args:
        merged_df: DataFrame with solid and isochromatic preference data
        frequencies: List of frequencies to plot
        quantile: Which percentile to test
    """
    # Create subplot grid
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(
        f'Solid Preference Index: Isochromatic+ vs Isochromatic-\n(Testing {quantile}th Percentile Constraint)',
        fontsize=16)
    axes = axes.flatten()

    for freq_idx, frequency in enumerate(frequencies):
        ax = axes[freq_idx]
        freq_data = merged_df[merged_df['frequency'] == frequency]

        if freq_data.empty:
            ax.text(0.5, 0.5, 'No Data', ha='center', va='center', transform=ax.transAxes)
            continue

        # Split by isochromatic preference sign
        iso_positive_mask = freq_data['isochromatic_preference_index'] > 0
        iso_negative_mask = freq_data['isochromatic_preference_index'] < 0

        iso_pos_values = freq_data[iso_positive_mask]['solid_preference_index'].values
        iso_neg_values = freq_data[iso_negative_mask]['solid_preference_index'].values

        # Plot overlapping histograms
        bins = np.linspace(-1, 1, 21)  # 20 bins from -1 to 1

        ax.hist(iso_pos_values, bins=bins, alpha=0.6, color='red',
                label=f'Isochromatic Preferring (n={len(iso_pos_values)})', edgecolor='black')
        ax.hist(iso_neg_values, bins=bins, alpha=0.6, color='blue',
                label=f'Isoluminant Preferring (n={len(iso_neg_values)})', edgecolor='black')

        # Styling
        ax.set_xlabel('Solid Preference Index')
        ax.set_ylabel('Number of Cells')
        ax.set_title(f'{frequency} Hz')
        ax.axvline(x=0, color='gray', linestyle='--', alpha=0.5)
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')

        # Add statistics (Permutation test on lower quantile)
        if len(iso_pos_values) > 0 and len(iso_neg_values) > 0:
            perm_results = permutation_test_lower_quantile(iso_pos_values, iso_neg_values,
                                                           quantile=quantile, n_permutations=10000)

            # Add vertical lines showing the quantile values
            ax.axvline(x=perm_results['q_sig_3d'], color='red', linestyle=':',
                       linewidth=2, alpha=0.8)
            ax.axvline(x=perm_results['q_non_sig'], color='blue', linestyle=':',
                       linewidth=2, alpha=0.8)

            median_pos = np.median(iso_pos_values)
            median_neg = np.median(iso_neg_values)

            stats_text = f'P{quantile} (Iso+): {perm_results["q_sig_3d"]:.2f}\n' \
                         f'P{quantile} (Iso-): {perm_results["q_non_sig"]:.2f}\n' \
                         f'Difference: {perm_results["difference"]:.2f}\n' \
                         f'Perm test p: {perm_results["p_value"]:.4f}\n' \
                         f'---\n' \
                         f'Median (Iso+): {median_pos:.2f}\n' \
                         f'Median (Iso-): {median_neg:.2f}'

            ax.text(0.98, 0.98, stats_text, transform=ax.transAxes,
                    verticalalignment='top', horizontalalignment='right',
                    bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8),
                    fontsize=8)

    plt.tight_layout()
    plt.show()

    # Print summary statistics
    print("\n" + "=" * 70)
    print(f"SOLID PREFERENCE BY ISOCHROMATIC SIGN: {quantile}th Percentile")
    print("=" * 70)
    for frequency in frequencies:
        freq_data = merged_df[merged_df['frequency'] == frequency]
        if not freq_data.empty:
            iso_positive_mask = freq_data['isochromatic_preference_index'] > 0
            iso_negative_mask = freq_data['isochromatic_preference_index'] < 0

            iso_pos_values = freq_data[iso_positive_mask]['solid_preference_index'].values
            iso_neg_values = freq_data[iso_negative_mask]['solid_preference_index'].values

            if len(iso_pos_values) > 0 and len(iso_neg_values) > 0:
                results = permutation_test_lower_quantile(iso_pos_values, iso_neg_values, quantile=quantile)
                print(f"\n{frequency} Hz:")
                print(f"  Iso+ {quantile}th percentile: {results['q_sig_3d']:.3f}")
                print(f"  Iso- {quantile}th percentile: {results['q_non_sig']:.3f}")
                print(f"  Difference: {results['difference']:.3f}")
                print(
                    f"  P-value: {results['p_value']:.4f} {'***' if results['p_value'] < 0.001 else '**' if results['p_value'] < 0.01 else '*' if results['p_value'] < 0.05 else '(n.s.)'}")


def create_frequency_histograms(merged_df, frequencies, quantile=10):
    """Create overlapping histograms for each frequency."""

    # Create subplot grid
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(
        f'Isochromatic Preference Index: Significant 3D vs Non-Significant\n(Testing {quantile}th Percentile Constraint)',
        fontsize=16)
    axes = axes.flatten()

    for freq_idx, frequency in enumerate(frequencies):
        ax = axes[freq_idx]
        freq_data = merged_df[merged_df['frequency'] == frequency]

        if freq_data.empty:
            ax.text(0.5, 0.5, 'No Data', ha='center', va='center', transform=ax.transAxes)
            continue

        # Classify into groups
        sig_3d_mask = (pd.notna(freq_data['p_value'])) & \
                      (freq_data['p_value'] < 0.05) & \
                      (freq_data['solid_preference_index'] > 0)

        sig_3d_values = freq_data[sig_3d_mask]['isochromatic_preference_index'].values
        non_sig_values = freq_data[~sig_3d_mask]['isochromatic_preference_index'].values

        # Plot overlapping histograms
        bins = np.linspace(-1, 1, 11)  # 20 bins from -1 to 1

        ax.hist(sig_3d_values, bins=bins, alpha=0.6, color='blue',
                label=f'Sig 3D (n={len(sig_3d_values)})', edgecolor='black')
        ax.hist(non_sig_values, bins=bins, alpha=0.6, color='orange',
                label=f'Non-sig (n={len(non_sig_values)})', edgecolor='black')

        # Styling
        ax.set_xlabel('Isochromatic Preference Index')
        ax.set_ylabel('Number of Cells')
        ax.set_title(f'{frequency} Hz')
        ax.axvline(x=0, color='gray', linestyle='--', alpha=0.5)
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')

        # Add statistics (Permutation test on lower quantile)
        if len(sig_3d_values) > 0 and len(non_sig_values) > 0:
            perm_results = permutation_test_lower_quantile(sig_3d_values, non_sig_values,
                                                           quantile=quantile, n_permutations=10000)

            # Add vertical lines showing the quantile values
            ax.axvline(x=perm_results['q_sig_3d'], color='blue', linestyle=':',
                       linewidth=2, alpha=0.8)
            ax.axvline(x=perm_results['q_non_sig'], color='orange', linestyle=':',
                       linewidth=2, alpha=0.8)

            median_sig = np.median(sig_3d_values)
            median_nonsig = np.median(non_sig_values)

            stats_text = f'P{quantile} (Sig 3D): {perm_results["q_sig_3d"]:.2f}\n' \
                         f'P{quantile} (Non-sig): {perm_results["q_non_sig"]:.2f}\n' \
                         f'Difference: {perm_results["difference"]:.2f}\n' \
                         f'Perm test p: {perm_results["p_value"]:.4f}\n' \
                         f'---\n' \
                         f'Median (Sig 3D): {median_sig:.2f}\n' \
                         f'Median (Non-sig): {median_nonsig:.2f}'

            ax.text(0.98, 0.98, stats_text, transform=ax.transAxes,
                    verticalalignment='top', horizontalalignment='right',
                    bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8),
                    fontsize=8)

    plt.tight_layout()
    plt.show()

    # Print summary statistics
    print("\n" + "=" * 70)
    print(f"PERMUTATION TEST RESULTS: {quantile}th Percentile Constraint")
    print("=" * 70)
    for frequency in frequencies:
        freq_data = merged_df[merged_df['frequency'] == frequency]
        if not freq_data.empty:
            sig_3d_mask = (pd.notna(freq_data['p_value'])) & \
                          (freq_data['p_value'] < 0.05) & \
                          (freq_data['solid_preference_index'] > 0)

            sig_3d_values = freq_data[sig_3d_mask]['isochromatic_preference_index'].values
            non_sig_values = freq_data[~sig_3d_mask]['isochromatic_preference_index'].values

            if len(sig_3d_values) > 0 and len(non_sig_values) > 0:
                results = permutation_test_lower_quantile(sig_3d_values, non_sig_values, quantile=quantile)
                print(f"\n{frequency} Hz:")
                print(f"  Sig 3D {quantile}th percentile: {results['q_sig_3d']:.3f}")
                print(f"  Non-sig {quantile}th percentile: {results['q_non_sig']:.3f}")
                print(f"  Difference: {results['difference']:.3f}")
                print(
                    f"  P-value: {results['p_value']:.4f} {'***' if results['p_value'] < 0.001 else '**' if results['p_value'] < 0.01 else '*' if results['p_value'] < 0.05 else '(n.s.)'}")


if __name__ == "__main__":
    # You can change the quantile here (10 = 10th percentile, 25 = 25th percentile, etc.)
    data = create_isochromatic_preference_histograms(quantile=10)