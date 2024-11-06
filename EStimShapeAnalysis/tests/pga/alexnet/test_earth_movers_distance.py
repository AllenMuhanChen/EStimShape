import unittest
import numpy as np
import ot
from scipy.stats import wasserstein_distance
from PIL import Image
import matplotlib.pyplot as plt
from clat.util.connection import Connection
from src.pga.alexnet import alexnet_context
from src.pga.alexnet.lighting_posthoc.backtrace_analysis import calculate_contribution_map, ContributionType
from src.pga.alexnet.lighting_posthoc.earth_movers_distance import compute_spatial_wasserstein


def test_emd_with_real_data():
    """Test EMD calculation using real data and controlled transformations."""
    # Setup connection and test data
    conn = Connection(
        host='172.30.6.80',
        user='xper_rw',
        password='up2nite',
        database="allen_alexnet_lighting_exp_241101_0"
    )

    # Test IDs
    test_stim_id = 1730491137733279

    # Load original data
    original_image, original_contributions = load_test_data(conn, test_stim_id)


    # Create transformations
    transformations = create_transformations(original_contributions)

    # Calculate EMDs and verify
    emds = calculate_emds(transformations)

    # Visualize results
    visualize_results(original_image, transformations, emds, test_stim_id)


def load_test_data(conn, stim_id):
    """Load image and contribution data for testing."""
    # Get image path
    query = "SELECT path FROM StimPath WHERE stim_id = %s"
    conn.execute(query, (stim_id,))
    image_path = conn.fetch_one()

    # Load image
    image = np.array(Image.open(image_path).convert('RGB'))

    # Get contribution map
    contributions = calculate_contribution_map(
        conn,
        stim_id,
        ContributionType.BOTH,
        ContributionType.BOTH
    )
    contributions = abs(contributions / contributions.sum())

    return image, contributions

def create_transformations(contributions):
    """Create controlled transformations of contribution pattern."""
    return {
        'original': contributions,
        'shift_right': np.roll(contributions, shift=100, axis=1),  # Shift columns
        'shift_down': np.roll(contributions, shift=100, axis=0),   # Shift rows
        'shift_diagonal': np.roll(np.roll(contributions, shift=100, axis=0), shift=100, axis=1),  # Shift both
        'random_shuffle': random_shuffle_contributions(contributions),
    }


def random_shuffle_contributions(contributions):
    """Randomly shuffle non-zero contribution positions."""
    shuffled = contributions.copy()
    non_zero_mask = contributions > 0
    values = shuffled[non_zero_mask]
    np.random.shuffle(values)
    # Add some random noise to ensure values change
    # values = values * (1 + np.random.normal(0, 0.1, size=len(values)))
    shuffled[non_zero_mask] = values
    return shuffled / shuffled.sum()


def calculate_emds(transformations):
    """Calculate EMDs between original and transformed patterns."""
    emds = {}
    original = transformations['original']

    # Normalize original if it contains non-zero values
    if original.sum() > 0:
        original = original / original.sum()

    print("\nDEBUG INFO:")
    print(f"Original shape: {original.shape}")
    print(f"Non-zero values: {np.sum(original > 0)}")

    for name, pattern in transformations.items():
        print(f"\nProcessing {name}:")

        # Normalize pattern if it contains non-zero values
        if pattern.sum() > 0:
            pattern = pattern / pattern.sum()

        if original.sum() > 0 and pattern.sum() > 0:
            emds[name] = ot.sliced_wasserstein_distance(
                original,
                pattern
            )
        else:
            emds[name] = np.nan

        print(f'EMD for {name}: {emds[name]}')

    return emds
def visualize_results(original_image, transformations, emds, stim_id):
    """Visualize original and transformed patterns with EMD values."""
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    axes = axes.flatten()

    # Plot original
    axes[0].imshow(original_image)
    axes[0].imshow(transformations['original'], cmap='hot', alpha=0.5)
    axes[0].set_title('Original')
    axes[0].axis('off')

    # Plot transformations
    for idx, (name, pattern) in enumerate(transformations.items()):
        if name != 'original':
            ax = axes[idx + 1]
            ax.imshow(original_image)
            ax.imshow(pattern, cmap='hot', alpha=0.5)
            ax.set_title(f'{name}\nEMD: {emds[name]:.10f}')
            ax.axis('off')

    plt.tight_layout()
    plt.savefig(f"{alexnet_context.lighting_plots_dir}/emd_validation_{stim_id}.png",
                bbox_inches='tight', dpi=300)
    plt.show()
    plt.close()


if __name__ == '__main__':
    test_emd_with_real_data()