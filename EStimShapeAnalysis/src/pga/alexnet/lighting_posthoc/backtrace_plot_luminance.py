import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from clat.util.connection import Connection
from src.pga.alexnet import alexnet_context
from src.pga.alexnet.lighting_posthoc.backtrace_analysis import get_stim_lighting_variations, ContributionType
from src.pga.alexnet.lighting_posthoc.distance_analysis import calculate_contribution_map
from src.startup import db_ip


def get_background_mask(img_array):
    """Create mask for background pixels (gray values 127 or 128)."""
    return ((img_array[:, :, 0] == 127) & (img_array[:, :, 1] == 127) & (img_array[:, :, 2] == 127)) | \
        ((img_array[:, :, 0] == 128) & (img_array[:, :, 1] == 128) & (img_array[:, :, 2] == 128))


def calculate_average_foreground(img_array):
    """Calculate average value of non-background pixels."""
    background_mask = get_background_mask(img_array)
    foreground_mask = ~background_mask
    foreground_pixels = img_array[foreground_mask]
    return np.mean(foreground_pixels, axis=0) if len(foreground_pixels) > 0 else np.array([127, 127, 127])


def create_2d_version(img_array):
    """Create 2D version preserving background pixels."""
    avg_color = calculate_average_foreground(img_array)
    background_mask = get_background_mask(img_array)
    foreground_mask = ~background_mask

    result = img_array.copy()
    result[foreground_mask] = avg_color
    return result


def apply_contribution_brightness(img_array, contrib_map):
    """Apply contribution map as brightness modulation, preserving background."""
    background_mask = get_background_mask(img_array)

    if contrib_map.max() != 0:
        norm_map = contrib_map / contrib_map.max()
    else:
        norm_map = contrib_map

    img_hsv = np.array(Image.fromarray(img_array).convert('HSV'))
    scale_factor = 1.0 + norm_map

    # Only modify non-background pixels
    foreground_mask = ~background_mask
    img_hsv[foreground_mask, 2] = np.clip(img_hsv[foreground_mask, 2] * scale_factor[foreground_mask], 0, 255)

    return np.array(Image.fromarray(img_hsv, 'HSV').convert('RGB'))


def plot_variations(conn: Connection, variations: list, parent_image_path: str):
    specular_vars = [v for v in variations if v[1] == 'SPECULAR']
    shade_vars = [v for v in variations if v[1] == 'SHADE']
    n_cols = max(len(specular_vars), len(shade_vars)) + 1

    fig = plt.figure(figsize=(20, 35))

    # Process and store images for averages
    specular_2d = []
    specular_2d_contrib = []
    shade_2d = []
    shade_2d_contrib = []

    # Plot SPECULAR variations
    for idx, (stim_id, texture_type, activation) in enumerate(specular_vars):
        conn.execute("SELECT path FROM StimPath WHERE stim_id = %s", (stim_id,))
        variant_path = conn.fetch_one()

        img = Image.open(variant_path)
        img_array = np.array(img)
        contrib_map = calculate_contribution_map(conn, stim_id, ContributionType.BOTH)
        img_2d = create_2d_version(img_array)
        img_2d_contrib = apply_contribution_brightness(img_2d, contrib_map)

        specular_2d.append(img_2d)
        specular_2d_contrib.append(img_2d_contrib)

        # Plot original
        ax1 = plt.subplot(8, n_cols, idx + 1)
        ax1.imshow(img_array)
        ax1.set_title(f'SPECULAR Original\nActivation: {activation:.3f}')
        ax1.axis('off')

        # Plot 2D version
        ax2 = plt.subplot(8, n_cols, n_cols + idx + 1)
        ax2.imshow(img_2d)
        ax2.set_title('2D Version')
        ax2.axis('off')

        # Plot 2D + contributions
        ax3 = plt.subplot(8, n_cols, 2 * n_cols + idx + 1)
        ax3.imshow(img_2d_contrib)
        ax3.set_title('2D + Contributions')
        ax3.axis('off')

    # Plot SPECULAR averages
    if specular_2d:
        avg_2d = np.mean(specular_2d, axis=0).astype(np.uint8)
        avg_2d_contrib = np.mean(specular_2d_contrib, axis=0).astype(np.uint8)

        ax_avg = plt.subplot(8, n_cols, len(specular_vars) + 1)
        ax_avg.imshow(avg_2d)
        ax_avg.set_title('SPECULAR\n2D Average')
        ax_avg.axis('off')

        ax_avg_contrib = plt.subplot(8, n_cols, n_cols + len(specular_vars) + 1)
        ax_avg_contrib.imshow(avg_2d_contrib)
        ax_avg_contrib.set_title('SPECULAR\n2D + Contrib Average')
        ax_avg_contrib.axis('off')

    # Plot SHADE variations
    for idx, (stim_id, texture_type, activation) in enumerate(shade_vars):
        conn.execute("SELECT path FROM StimPath WHERE stim_id = %s", (stim_id,))
        variant_path = conn.fetch_one()

        img = Image.open(variant_path)
        img_array = np.array(img)
        contrib_map = calculate_contribution_map(conn, stim_id, ContributionType.BOTH)
        img_2d = create_2d_version(img_array)
        img_2d_contrib = apply_contribution_brightness(img_2d, contrib_map)

        shade_2d.append(img_2d)
        shade_2d_contrib.append(img_2d_contrib)

        # Plot original
        ax1 = plt.subplot(8, n_cols, 4 * n_cols + idx + 1)
        ax1.imshow(img_array)
        ax1.set_title(f'SHADE Original\nActivation: {activation:.3f}')
        ax1.axis('off')

        # Plot 2D version
        ax2 = plt.subplot(8, n_cols, 5 * n_cols + idx + 1)
        ax2.imshow(img_2d)
        ax2.set_title('2D Version')
        ax2.axis('off')

        # Plot 2D + contributions
        ax3 = plt.subplot(8, n_cols, 6 * n_cols + idx + 1)
        ax3.imshow(img_2d_contrib)
        ax3.set_title('2D + Contributions')
        ax3.axis('off')

    # Plot SHADE averages
    if shade_2d:
        avg_2d = np.mean(shade_2d, axis=0).astype(np.uint8)
        avg_2d_contrib = np.mean(shade_2d_contrib, axis=0).astype(np.uint8)

        ax_avg = plt.subplot(8, n_cols, 4 * n_cols + len(shade_vars) + 1)
        ax_avg.imshow(avg_2d)
        ax_avg.set_title('SHADE\n2D Average')
        ax_avg.axis('off')

        ax_avg_contrib = plt.subplot(8, n_cols, 5 * n_cols + len(shade_vars) + 1)
        ax_avg_contrib.imshow(avg_2d_contrib)
        ax_avg_contrib.set_title('SHADE\n2D + Contrib Average')
        ax_avg_contrib.axis('off')

    plt.tight_layout()
    return fig


def main():
    conn = Connection(
        host=db_ip,
        user='xper_rw',
        password='up2nite',
        database=alexnet_context.lighting_database
    )

    query = """
       SELECT DISTINCT parent_id 
       FROM StimInstructions 
       WHERE stim_type = 'TEXTURE_3D_VARIATION'
       """
    conn.execute(query)
    parent_ids = [row[0] for row in conn.fetch_all()]

    for parent_id in parent_ids:
        variations = get_stim_lighting_variations(conn, parent_id)
        conn.execute("SELECT path FROM StimPath WHERE stim_id = %s", (parent_id,))
        parent_path = conn.fetch_one()

        fig = plot_variations(conn, variations, parent_path)
        plt.figure(fig.number)
        plt.suptitle('Lighting variations for Parent ID: ' + str(parent_id))
        plt.savefig(f"{alexnet_context.lighting_plots_dir}/{parent_id}_2d_contrib_with_avg.png")
        plt.show()


if __name__ == "__main__":
    main()