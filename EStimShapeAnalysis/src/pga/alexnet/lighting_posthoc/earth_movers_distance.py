import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
from scipy.stats import wasserstein_distance
from clat.util.connection import Connection
from src.pga.alexnet import alexnet_context
from src.pga.alexnet.lighting_posthoc.backtrace_analysis import calculate_contribution_map, ContributionType
from typing import Dict, List, Tuple, Optional


def main():
    conn = Connection(
        host='172.30.6.80',
        user='xper_rw',
        password='up2nite',
        database=alexnet_context.lighting_database
    )

    # Get all parent IDs
    query = """
    SELECT DISTINCT parent_id 
    FROM StimInstructions 
    WHERE stim_type = 'TEXTURE_3D_VARIATION'
    """
    conn.execute(query)
    parent_ids = [row[0] for row in conn.fetch_all()]

    for parent_id in parent_ids:
        # Get all variations for this parent
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

        # Calculate distributions for each image
        luminance_arrays = [calculate_luminance(img['path']) for img in images]
        luminance_arrays = [arr / arr.sum() for arr in luminance_arrays]  # Normalize

        combined_contrib_arrays = [calculate_contribution_distribution(conn, img['stim_id'], ContributionType.BOTH)
                                   for img in images]
        pos_contrib_arrays = [calculate_contribution_distribution(conn, img['stim_id'], ContributionType.POSITIVE)
                              for img in images]
        neg_contrib_arrays = [calculate_contribution_distribution(conn, img['stim_id'], ContributionType.NEGATIVE)
                              for img in images]

        # Compute EMD matrices
        brightness_emd = compute_emd_matrix(luminance_arrays)
        pos_contrib_emd = compute_emd_matrix(pos_contrib_arrays)
        neg_contrib_emd = compute_emd_matrix(neg_contrib_arrays)
        both_contrib_emd = compute_emd_matrix(combined_contrib_arrays)
        # Create visualization
        fig = plot_emd_matrices(
            brightness_emd,
            both_contrib_emd,
            pos_contrib_emd,
            neg_contrib_emd,
            images,
            f'EMD Comparison for Parent ID: {parent_id}'
        )

        # Save the plot
        plt.savefig(f"{alexnet_context.lighting_plots_dir}/{parent_id}_combined_emd.png",
                    bbox_inches='tight', dpi=300)
        plt.show()
        plt.close()

        # Create and save the EMD correlation plot
        corr_fig = plot_emd_correlation(
            brightness_emd,
            both_contrib_emd,  # Using the combined contributions
            images,
            f'Parent ID: {parent_id}'
        )

        # Save the correlation plot
        plt.savefig(f"{alexnet_context.lighting_plots_dir}/{parent_id}_emd_correlation.png",
                    bbox_inches='tight', dpi=300)
        plt.show()
        plt.close()


def plot_emd_correlation(brightness_emd: np.ndarray,
                         contrib_emd: np.ndarray,
                         images: List[dict],
                         title: str) -> plt.Figure:
    """Create a scatter plot comparing brightness EMD to contribution EMD."""

    # Create masks for different comparison types
    specular_idx = [i for i, img in enumerate(images) if img['texture_type'] == 'SPECULAR']
    shade_idx = [i for i, img in enumerate(images) if img['texture_type'] == 'SHADE']

    # Get all pairwise comparisons
    n_images = len(images)
    within_spec_mask = np.zeros((n_images, n_images), dtype=bool)
    within_shade_mask = np.zeros((n_images, n_images), dtype=bool)
    between_mask = np.zeros((n_images, n_images), dtype=bool)

    # Set masks for different comparison types
    for i in range(n_images):
        for j in range(i + 1, n_images):  # Only use upper triangle to avoid duplicates
            if i in specular_idx and j in specular_idx:
                within_spec_mask[i, j] = True
            elif i in shade_idx and j in shade_idx:
                within_shade_mask[i, j] = True
            elif (i in specular_idx and j in shade_idx) or (i in shade_idx and j in specular_idx):
                between_mask[i, j] = True

    # Create figure
    fig, ax = plt.subplots(figsize=(10, 10))

    # Plot each comparison type with different colors
    def plot_masked_comparisons(mask, color, label):
        x = brightness_emd[mask]
        y = contrib_emd[mask]
        ax.scatter(x, y, c=color, label=label, alpha=0.6)

    plot_masked_comparisons(within_spec_mask, 'blue', 'Within Specular')
    plot_masked_comparisons(within_shade_mask, 'red', 'Within Shade')
    plot_masked_comparisons(between_mask, 'green', 'Between Shade-Specular')

    # Calculate and plot correlation line
    all_valid_mask = within_spec_mask | within_shade_mask | between_mask
    x = brightness_emd[all_valid_mask]
    y = contrib_emd[all_valid_mask]

    # Calculate correlation coefficient
    correlation = np.corrcoef(x, y)[0, 1]

    # Fit line
    z = np.polyfit(x, y, 1)
    p = np.poly1d(z)
    x_range = np.linspace(x.min(), x.max(), 100)
    ax.plot(x_range, p(x_range), 'k--', alpha=0.5,
            label=f'Correlation: {correlation:.3f}')

    # Customize plot
    ax.set_xlabel('Brightness EMD')
    ax.set_ylabel('Contribution EMD')
    ax.set_title(f'{title}\nCorrelation between Brightness and Contribution EMD')
    ax.legend()

    # Set equal aspect ratio
    ax.set_aspect('equal')

    # Add grid
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    return fig
def calculate_luminance(image_path: str) -> np.ndarray:
    """Calculate luminance values for each pixel in the image."""
    img = Image.open(image_path).convert('RGB')
    img_array = np.array(img)

    # Create mask to exclude background (assuming 127/128 RGB gray background)
    background_mask = ((img_array[:, :, 0] == 127) & (img_array[:, :, 1] == 127) & (img_array[:, :, 2] == 127)) | \
                      ((img_array[:, :, 0] == 128) & (img_array[:, :, 1] == 128) & (img_array[:, :, 2] == 128))
    foreground_mask = ~background_mask

    # Calculate luminance using standard coefficients
    luminance = (0.2126 * img_array[:, :, 0] +
                 0.7152 * img_array[:, :, 1] +
                 0.0722 * img_array[:, :, 2])

    # Zero out background pixels
    luminance[~foreground_mask] = 0

    return luminance


def calculate_contribution_distribution(conn: Connection, stim_id: int,
                                        contribution_type: ContributionType) -> np.ndarray:
    """Calculate contribution distribution for a given stimulus."""
    # Get contribution map using existing function
    contrib_map = calculate_contribution_map(
        conn,
        stim_id,
        contribution_type,  # for conv2
        ContributionType.BOTH  # for conv1
    )

    # Normalize if there are any non-zero contributions

    contrib_map = abs(contrib_map / contrib_map.sum())

    return contrib_map


def compute_emd_matrix(data_arrays: List[np.ndarray]) -> np.ndarray:
    """
    Compute EMD between all pairs of distributions.

    Args:
        data_arrays: List of 2D numpy arrays containing distributions

    Returns:
        2D numpy array containing EMD values between all pairs
    """
    n_arrays = len(data_arrays)
    emd_matrix = np.zeros((n_arrays, n_arrays))

    # Preprocess arrays: flatten and filter non-zero values
    processed_data = []
    for arr in data_arrays:
        flat_data = arr[arr > 0].flatten()
        if len(flat_data) > 0:  # Only normalize if there are non-zero values
            flat_data = flat_data / flat_data.sum()
        processed_data.append(flat_data)

    # Compute EMD between all pairs
    for i in range(n_arrays):
        for j in range(n_arrays):
            if len(processed_data[i]) > 0 and len(processed_data[j]) > 0:
                emd_matrix[i, j] = wasserstein_distance(
                    processed_data[i],
                    processed_data[j]
                )
            else:
                emd_matrix[i, j] = np.nan

    return emd_matrix

def plot_emd_matrices(brightness_emd: np.ndarray,
                      both_contrib_emd: np.ndarray,
                      pos_contrib_emd: np.ndarray,
                      neg_contrib_emd: np.ndarray,
                      images: List[dict],
                      title: str) -> plt.Figure:
    """Create a side-by-side visualization of brightness and contribution EMD matrices."""
    n_images = len(images)

    # Create labels for the plot
    labels = [f"{img['texture_type']}_ Angle {i + 1}" for i, img in enumerate(images)]

    fig, axes = plt.subplots(2, 2, figsize=(24, 8))

    # Plot matrices
    matrices = [
        (brightness_emd, "Brightness EMD", 0, 0),
        (both_contrib_emd, "Both Contributions EMD", 0, 1),
        (pos_contrib_emd, "Positive Contributions EMD", 1, 0),
        (neg_contrib_emd, "Negative Contributions EMD", 1, 1)
    ]

    for matrix, subtitle, row, col in matrices:
        im = axes[row, col].imshow(matrix, cmap='viridis')
        plt.colorbar(im, ax=axes[row, col], label='Earth Mover\'s Distance')

        # Configure axes
        axes[row, col].set_xticks(np.arange(n_images))
        axes[row, col].set_yticks(np.arange(n_images))
        axes[row, col].set_xticklabels(labels, rotation=90, ha='right')
        axes[row, col].set_yticklabels(labels)

        # Add subtitle
        axes[row, col].set_title(subtitle)

        # # Add numeric values in cells
        # for i in range(n_images):
        #     for j in range(n_images):
        #         if not np.isnan(matrix[i, j]):
        #             text = axes[row, col].text(j, i, f'{matrix[i, j]:.3f}',
        #                                        ha='center', va='center',
        #                                        color='white' if matrix[i, j] > np.nanmax(matrix) / 2 else 'black')

        # Add overall title
    fig.suptitle(title, y=0.95, fontsize=16)

    plt.tight_layout()
    return fig


if __name__ == "__main__":
    main()