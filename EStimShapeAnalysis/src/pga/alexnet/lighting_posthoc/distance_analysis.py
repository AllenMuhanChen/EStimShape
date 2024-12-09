from typing import List, Tuple

import numpy as np
from PIL import Image
from clat.util.connection import Connection
from matplotlib import pyplot as plt

from src.pga.alexnet import alexnet_context
from src.pga.alexnet.lighting_posthoc.backtrace_analysis import ContributionType, calculate_raw_contribution_map
from src.pga.alexnet.lighting_posthoc.distance.distance_metrics import DistanceType, \
    DistanceMetric, EMDMetric, OverlapMetric, WeightedOverlapMetric


metrics = [
    (DistanceType.EMD, DistanceType.WEIGHTED_OVERLAP),
    (DistanceType.EMD, DistanceType.EMD),

]
def main():

    conn = Connection(
        host='172.30.6.80',
        user='xper_rw',
        password='up2nite',
        database=alexnet_context.lighting_database
    )

    make_contrib_response_plot = True
    for brightness_metric, contribution_metric in metrics:
        create_plots(brightness_metric, contribution_metric, conn, make_contrib_response_plot)
        # make_response_plot = False


def create_plots(brightness_metric, contribution_metric, conn, make_response_plot = True):
    calc_distance = create_distance_calculator(
        brightness_type=brightness_metric,
        contribution_type=contribution_metric,
        n_shuffles=3,
        threshold=0.1,
        spatial_tolerance=0
    )
    # Connect to database
    # Get parent IDs
    query = """
    SELECT DISTINCT parent_id 
    FROM StimInstructions 
    WHERE stim_type = 'TEXTURE_3D_VARIATION'
    """
    conn.execute(query)
    parent_ids = [row[0] for row in conn.fetch_all()]
    for parent_id in parent_ids:
        # Get variations for this parent
        query = """
        SELECT si.stim_id, sp.path, si.texture_type
        FROM StimInstructions si
        JOIN StimPath sp ON si.stim_id = sp.stim_id
        WHERE si.parent_id = %s AND si.stim_type = 'TEXTURE_3D_VARIATION'
        ORDER BY si.texture_type, si.light_pos_x
        """
        conn.execute(query, (parent_id,))
        images = [{'stim_id': r[0], 'path': r[1], 'texture_type': r[2]}
                  for r in conn.fetch_all()]

        # Calculate arrays
        luminance_arrays = [calculate_luminance(img['path']) for img in images]
        combined_contrib_arrays = [calculate_contribution_map(conn, img['stim_id'], ContributionType.BOTH)
                                   for img in images]
        pos_contrib_arrays = [calculate_contribution_map(conn, img['stim_id'], ContributionType.POSITIVE)
                              for img in images]
        neg_contrib_arrays = [calculate_contribution_map(conn, img['stim_id'], ContributionType.NEGATIVE)
                              for img in images]

        # Compute brightness distances once
        brightness_dist = calc_distance.compute_brightness_matrix(luminance_arrays)

        # Compute contribution distances for each type
        both_contrib_dist = calc_distance.compute_contribution_matrix(combined_contrib_arrays)
        pos_contrib_dist = calc_distance.compute_contribution_matrix(pos_contrib_arrays)
        neg_contrib_dist = calc_distance.compute_contribution_matrix(neg_contrib_arrays)

        # Create and save hybrid visualization
        fig = plot_distance_matrices(
            brightness_dist,
            both_contrib_dist,
            pos_contrib_dist,
            neg_contrib_dist,
            images,
            f'Distance Comparison for Parent ID: {parent_id}',
            f"Brightness {brightness_metric.value}",
            f"Contribution {contribution_metric.value}"
        )

        plt.savefig(
            f"{alexnet_context.lighting_plots_dir}/{parent_id}_distance_matrices_{brightness_metric}_{contribution_metric}.png",
            bbox_inches='tight', dpi=300)
        plt.show()
        plt.close()

        # Create and save correlation plot
        corr_fig = plot_distance_correlation(
            brightness_dist,
            both_contrib_dist,
            images,
            f'Parent ID: {parent_id}',
            f"Brightness {brightness_metric.value}",
            f"Contribution {contribution_metric.value}"
        )

        plt.savefig(
            f"{alexnet_context.lighting_plots_dir}/{parent_id}_correlation_{brightness_metric.value}_{contribution_metric.value}.png",
            bbox_inches='tight', dpi=300)
        plt.show()
        plt.close()

        if make_response_plot:
            resp_fig = plot_contribution_response_correlation(
                both_contrib_dist,
                images,
                conn,
                f'Parent ID: {parent_id}',
                f"Contribution {contribution_metric.value}"
            )

            plt.savefig(
                f"{alexnet_context.lighting_plots_dir}/{parent_id}_{contribution_metric.value}_response_correlation.png",
                bbox_inches='tight', dpi=300)
            plt.show()
            plt.close()


class DistanceCalculator:
    """Main class for computing distance matrices with different metrics"""

    def __init__(self,
                 brightness_metric: DistanceMetric,
                 contribution_metric: DistanceMetric):
        self.brightness_metric = brightness_metric
        self.contribution_metric = contribution_metric

    def compute_distance_matrices(self,
                                  brightness_arrays: List[np.ndarray],
                                  contribution_arrays: List[np.ndarray]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compute both distance matrices
        """
        brightness_matrix = self.compute_brightness_matrix(brightness_arrays)
        contribution_matrix = self.compute_contribution_matrix(contribution_arrays)
        return brightness_matrix, contribution_matrix

    def compute_brightness_matrix(self, arrays: List[np.ndarray]) -> np.ndarray:
        """Compute distance matrix using brightness metric"""
        return self._compute_matrix(arrays, self.brightness_metric)

    def compute_contribution_matrix(self, arrays: List[np.ndarray]) -> np.ndarray:
        """Compute distance matrix using contribution metric"""
        return self._compute_matrix(arrays, self.contribution_metric)

    def _compute_matrix(self, arrays: List[np.ndarray], metric: DistanceMetric) -> np.ndarray:
        """Helper method to compute distance matrix using given metric"""
        n_arrays = len(arrays)
        matrix = np.zeros((n_arrays, n_arrays))

        for i in range(n_arrays):
            for j in range(n_arrays):
                matrix[i, j] = metric.compute_distance(arrays[i], arrays[j])

        return matrix


def plot_distance_matrices(brightness_dist: np.ndarray,
                           both_contrib_dist: np.ndarray,
                           pos_contrib_dist: np.ndarray,
                           neg_contrib_dist: np.ndarray,
                           images: List[dict],
                           title: str,
                           brightness_label: str = "Brightness Distance",
                           contrib_label: str = "Contribution Distance") -> plt.Figure:
    """Create a side-by-side visualization of brightness and contribution distance matrices."""
    n_images = len(images)
    labels = [f"{img['texture_type']}_Angle {i + 1}" for i, img in enumerate(images)]

    fig, axes = plt.subplots(2, 2, figsize=(24, 8))

    matrices = [
        (brightness_dist, f"{brightness_label}", 0, 0),
        (both_contrib_dist, f"Both {contrib_label}", 0, 1),
        (pos_contrib_dist, f"Positive {contrib_label}", 1, 0),
        (neg_contrib_dist, f"Negative {contrib_label}", 1, 1)
    ]

    for matrix, subtitle, row, col in matrices:
        im = axes[row, col].imshow(matrix, cmap='viridis')
        plt.colorbar(im, ax=axes[row, col])

        axes[row, col].set_xticks(np.arange(n_images))
        axes[row, col].set_yticks(np.arange(n_images))
        axes[row, col].set_xticklabels(labels, rotation=90, ha='right')
        axes[row, col].set_yticklabels(labels)
        axes[row, col].set_title(subtitle)

    fig.suptitle(title, y=0.95, fontsize=16)
    plt.tight_layout()
    return fig


def plot_distance_correlation(brightness_dist: np.ndarray,
                              contrib_dist: np.ndarray,
                              images: List[dict],
                              title: str,
                              x_label: str = "Brightness Distance",
                              y_label: str = "Contribution Distance") -> plt.Figure:
    """Create a scatter plot comparing brightness distance to contribution distance."""
    specular_idx = [i for i, img in enumerate(images) if img['texture_type'] == 'SPECULAR']
    shade_idx = [i for i, img in enumerate(images) if img['texture_type'] == 'SHADE']

    n_images = len(images)
    within_spec_mask = np.zeros((n_images, n_images), dtype=bool)
    within_shade_mask = np.zeros((n_images, n_images), dtype=bool)
    between_mask = np.zeros((n_images, n_images), dtype=bool)

    for i in range(n_images):
        for j in range(i + 1, n_images):
            if i in specular_idx and j in specular_idx:
                within_spec_mask[i, j] = True
            elif i in shade_idx and j in shade_idx:
                within_shade_mask[i, j] = True
            elif (i in specular_idx and j in shade_idx) or (i in shade_idx and j in specular_idx):
                between_mask[i, j] = True

    fig, ax = plt.subplots(figsize=(10, 10))

    def plot_masked_comparisons(mask, color, label):
        x = brightness_dist[mask]
        y = contrib_dist[mask]
        ax.scatter(x, y, c=color, label=label, alpha=0.6)

    plot_masked_comparisons(within_spec_mask, 'blue', 'Within Specular')
    plot_masked_comparisons(within_shade_mask, 'red', 'Within Shade')
    plot_masked_comparisons(between_mask, 'green', 'Between Shade-Specular')

    all_valid_mask = within_spec_mask | within_shade_mask | between_mask
    x = brightness_dist[all_valid_mask]
    y = contrib_dist[all_valid_mask]
    correlation = np.corrcoef(x, y)[0, 1]

    # Fit correlation line
    z = np.polyfit(x, y, 1)
    p = np.poly1d(z)
    x_range = np.linspace(x.min(), x.max(), 100)
    ax.plot(x_range, p(x_range), 'k--', alpha=0.5,
            label=f'Correlation: {correlation:.3f}')

    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.set_title(f'{title}\nCorrelation between {x_label} and {y_label}')
    ax.legend()
    # ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)
    # set axis limits
    y_axis_max = max(y) if max(y) > 1 else 1
    ax.set_ylim(0, y_axis_max)

    plt.tight_layout()
    return fig


def calculate_luminance(image_path: str) -> np.ndarray:
    """Calculate luminance values for each pixel in the image."""
    img = Image.open(image_path).convert('RGB')
    img_array = np.array(img)

    background_mask = ((img_array[:, :, 0] == 127) & (img_array[:, :, 1] == 127) & (img_array[:, :, 2] == 127)) | \
                      ((img_array[:, :, 0] == 128) & (img_array[:, :, 1] == 128) & (img_array[:, :, 2] == 128))
    foreground_mask = ~background_mask

    luminance = (0.2126 * img_array[:, :, 0] +
                 0.7152 * img_array[:, :, 1] +
                 0.0722 * img_array[:, :, 2])

    luminance[~foreground_mask] = 0
    return luminance


def calculate_contribution_map(conn: Connection,
                               stim_id: int,
                               contribution_type: ContributionType, contribution_type_c1=ContributionType.BOTH) -> np.ndarray:
    """Calculate contribution map for a given stimulus.
    Normalize it
    And set all areas in background to zero"""
    # Get the original image path from the database
    query = "SELECT path FROM StimPath WHERE stim_id = %s"
    conn.execute(query, (stim_id,))
    image_path = conn.fetch_one()

    if not image_path:
        raise ValueError(f"No image path found for stim_id {stim_id}")

    # Load and create background mask from original image
    img = Image.open(image_path).convert('RGB')
    img_array = np.array(img)

    # Create mask for background (both 127 and 128 gray values)
    background_mask = ((img_array[:, :, 0] == 127) &
                       (img_array[:, :, 1] == 127) &
                       (img_array[:, :, 2] == 127)) | \
                      ((img_array[:, :, 0] == 128) &
                       (img_array[:, :, 1] == 128) &
                       (img_array[:, :, 2] == 128))
    foreground_mask = ~background_mask

    # Calculate contribution map
    contrib_map = calculate_raw_contribution_map(
        conn,
        stim_id,
        contribution_type,
        contribution_type_c1
    )

    # Add small random perturbation to foreground areas so that we can quickly identify foreground
    # areas in the contribution map
    epsilon = 1e-6

    # Apply foreground mask and add perturbation
    masked_contrib_map = (contrib_map + epsilon) * foreground_mask

    # Normalize the masked map
    if masked_contrib_map.max() != 0:
        normalized_map = abs(masked_contrib_map / masked_contrib_map.max())
    else:
        normalized_map = masked_contrib_map

    return normalized_map


def create_distance_calculator(brightness_type: DistanceType,
                               contribution_type: DistanceType,
                               **kwargs) -> DistanceCalculator:
    """Factory function to create DistanceCalculator with specified metrics"""

    metric_map = {
        DistanceType.EMD: lambda: EMDMetric(
            n_shuffles=kwargs.get('n_shuffles', 3)
        ),
        DistanceType.OVERLAP: lambda: OverlapMetric(
            threshold=kwargs.get('threshold', 0.5),
            spatial_tolerance=kwargs.get('spatial_tolerance', 5)
        ),
        DistanceType.WEIGHTED_OVERLAP: lambda: WeightedOverlapMetric(
            threshold=kwargs.get('threshold', 0.1),
            spatial_tolerance=kwargs.get('spatial_tolerance', 0)
        )
    }

    brightness_metric = metric_map[brightness_type]()
    contribution_metric = metric_map[contribution_type]()

    return DistanceCalculator(brightness_metric, contribution_metric)


def plot_contribution_response_correlation(contribution_dist: np.ndarray,
                                           images: List[dict],
                                           conn: Connection,
                                           title: str,
                                           y_label: str) -> plt.Figure:
    """Create a scatter plot comparing brightness distance to response differences."""
    # Get responses for all stimuli
    query = """
    SELECT stim_id, activation 
    FROM UnitActivations 
    WHERE stim_id IN ({})
    """.format(','.join(str(img['stim_id']) for img in images))
    conn.execute(query)
    responses = {row[0]: row[1] for row in conn.fetch_all()}

    specular_idx = [i for i, img in enumerate(images) if img['texture_type'] == 'SPECULAR']
    shade_idx = [i for i, img in enumerate(images) if img['texture_type'] == 'SHADE']

    n_images = len(images)
    within_spec_mask = np.zeros((n_images, n_images), dtype=bool)
    within_shade_mask = np.zeros((n_images, n_images), dtype=bool)
    between_mask = np.zeros((n_images, n_images), dtype=bool)

    # Create response difference matrix
    response_diff = np.zeros_like(contribution_dist)
    for i in range(n_images):
        for j in range(i + 1, n_images):
            if i in specular_idx and j in specular_idx:
                within_spec_mask[i, j] = True
            elif i in shade_idx and j in shade_idx:
                within_shade_mask[i, j] = True
            elif (i in specular_idx and j in shade_idx) or (i in shade_idx and j in specular_idx):
                between_mask[i, j] = True

            # Calculate absolute difference in responses
            response_diff[i, j] = abs(responses[images[i]['stim_id']] - responses[images[j]['stim_id']])

    fig, ax = plt.subplots(figsize=(10, 10))

    def plot_masked_comparisons(mask, color, label):
        x = response_diff[mask]
        y = contribution_dist[mask]
        ax.scatter(x, y, c=color, label=label, alpha=0.6)

    plot_masked_comparisons(within_spec_mask, 'blue', 'Within Specular')
    plot_masked_comparisons(within_shade_mask, 'red', 'Within Shade')
    plot_masked_comparisons(between_mask, 'green', 'Between Shade-Specular')

    all_valid_mask = within_spec_mask | within_shade_mask | between_mask
    x = response_diff[all_valid_mask]
    y = contribution_dist[all_valid_mask]
    correlation = np.corrcoef(x, y)[0, 1]

    # Fit correlation line
    z = np.polyfit(x, y, 1)
    p = np.poly1d(z)
    x_range = np.linspace(x.min(), x.max(), 100)
    ax.plot(x_range, p(x_range), 'k--', alpha=0.5,
            label=f'Correlation: {correlation:.3f}')

    ax.set_ylabel(y_label)
    ax.set_xlabel('Response Difference')
    ax.set_title(f'{title}\nCorrelation between {y_label} and Response Difference')
    ax.legend()
    ax.grid(True, alpha=0.3)

    y_axis_max = max(y) if max(y) > 1 else 1
    ax.set_ylim(0, y_axis_max)

    plt.tight_layout()
    return fig


if __name__ == "__main__":
    main()
