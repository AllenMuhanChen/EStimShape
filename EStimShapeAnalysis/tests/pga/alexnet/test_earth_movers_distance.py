import numpy as np
from PIL import Image
from clat.util.connection import Connection
from matplotlib import pyplot as plt

from src.pga.alexnet import alexnet_context
from src.pga.alexnet.lighting_posthoc.backtrace_analysis import ContributionType
from src.pga.alexnet.lighting_posthoc.distance.distance_metrics import (
    DistanceType, EMDMetric, OverlapMetric, SpatialEMDMetric
)
from src.pga.alexnet.lighting_posthoc.distance_analysis import calculate_contribution_map
from src.startup import db_ip


def test_distance_metrics():
    # Connect to database
    conn = Connection(
        host=db_ip,
        user='xper_rw',
        password='up2nite',
        database=alexnet_context.lighting_database
    )

    # Get a test image
    query = """
    SELECT si.stim_id, sp.path, si.texture_type
    FROM StimInstructions si
    JOIN StimPath sp ON si.stim_id = sp.stim_id
    WHERE si.stim_type = 'TEXTURE_3D_VARIATION'
    LIMIT 1
    """
    conn.execute(query)
    stim_id, path, texture_type = conn.fetch_all()[0]

    # Get original contribution map
    orig_map = calculate_contribution_map(conn, stim_id, ContributionType.BOTH)

    def create_random_shuffle(arr):
        shuffled = arr.copy()
        non_zero_mask = shuffled > 0
        non_zero_values = shuffled[non_zero_mask]
        np.random.shuffle(non_zero_values)
        shuffled[non_zero_mask] = non_zero_values
        return shuffled

    # Create perturbed versions
    perturbations = [
        ("Original", orig_map),
        ("Large Translation X", np.roll(orig_map, 20, axis=0)),
        ("Large Translation Y", np.roll(orig_map, 20, axis=1)),
        ("Random Shuffle", create_random_shuffle(orig_map))
    ]


    # Initialize metrics
    metrics = [
        ("EMD", EMDMetric(n_shuffles=3)),
        ("Spatial EMD", SpatialEMDMetric(threshold=0.1, n_shuffles=3)),
        ("Overlap", OverlapMetric(threshold=0.1, spatial_tolerance=5))
    ]

    # Calculate distances for all perturbations
    distances = {}
    for metric_name, metric in metrics:
        distances[metric_name] = {}
        for perturb_name, perturbed_map in perturbations:
            if perturb_name != "Original":  # Skip computing distance to itself
                distance = metric.compute_distance(orig_map, perturbed_map)
                distances[metric_name][perturb_name] = distance

    # Plot results with all perturbations
    n_rows = 3
    n_cols = 3
    fig = plt.figure(figsize=(20, 20))
    fig.suptitle(f'Distance Metric Analysis for {texture_type} Image', fontsize=16, y=0.95)

    # Plot original image
    ax = plt.subplot(n_rows, n_cols, 1)
    img = Image.open(path)
    ax.imshow(img)
    ax.set_title('Original Image')
    ax.axis('off')

    # Plot all contribution maps
    for idx, (perturb_name, perturbed_map) in enumerate(perturbations):
        ax = plt.subplot(n_rows, n_cols, idx + 1)
        im = ax.imshow(perturbed_map, cmap='viridis')
        plt.colorbar(im, ax=ax)

        title = perturb_name
        if perturb_name != "Original":
            title += "\n" + " | ".join(
                [f"{m_name}: {distances[m_name][perturb_name]:.3f}"
                 for m_name, _ in metrics]
            )

        ax.set_title(title)
        ax.axis('off')

    plt.tight_layout()
    plt.savefig(f"{alexnet_context.lighting_plots_dir}/distance_metric_test_all_perturbations.png",
                bbox_inches='tight', dpi=300)
    plt.show()

    # Print detailed results
    print("\nDetailed Results:")
    print("-" * 50)
    for metric_name, _ in metrics:
        print(f"\n{metric_name}:")
        for perturb_name in distances[metric_name]:
            print(f"  {perturb_name}: {distances[metric_name][perturb_name]:.4f}")


if __name__ == "__main__":
    test_distance_metrics()