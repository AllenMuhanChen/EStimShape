import functools

import numpy as np
import matplotlib.pyplot as plt
from clat.util.connection import Connection
from PIL import Image

from src.pga.alexnet import alexnet_context


def main():
    conn = Connection(
        host='172.30.6.80',
        user='xper_rw',
        password='up2nite',
        database=alexnet_context.lighting_database
    )

    variations = get_stim_lighting_variations(conn, 1730132722800937)
    conn.execute("SELECT path FROM StimPath WHERE stim_id = %s", (1730132722800937,))
    parent_path = conn.fetch_one()
    # combination_func = lambda x: np.prod(x, axis=0)
    combination_func = lambda x: np.mean(x, axis=0)

    fig = plot_variations(conn, variations, parent_path,
                          combination_func)

    plt.show()


def plot_variations(conn: Connection, variations: list, parent_image_path: str, combination_func=np.mean):
    specular_vars = [v for v in variations if v[1] == 'SPECULAR']
    shade_vars = [v for v in variations if v[1] == 'SHADE']
    n_cols = max(len(specular_vars), len(shade_vars)) + 1

    fig = plt.figure(figsize=(20, 17))  # Increased height for double rows
    all_maps = {'SPECULAR': [], 'SHADE': []}

    # Plot SPECULAR variations
    for idx, (stim_id, texture_type, activation) in enumerate(specular_vars):
        contrib_map = calculate_contribution_map(conn, stim_id)
        all_maps['SPECULAR'].append(contrib_map)
        norm_map = contrib_map / contrib_map.max() if contrib_map.max() > 0 else contrib_map

        conn.execute("SELECT path FROM StimPath WHERE stim_id = %s", (stim_id,))
        variant_path = conn.fetch_one()

        # Original image
        ax = plt.subplot(6, n_cols, idx + 1)
        img = Image.open(variant_path)
        ax.imshow(img)
        ax.set_title(f'SPECULAR\nActivation: {activation:.3f}')
        ax.axis('off')

        # Contribution map
        ax_map = plt.subplot(6, n_cols, n_cols + idx + 1)
        heatmap = np.zeros((*norm_map.shape, 4))
        heatmap[..., 0] = 1.0
        heatmap[..., 3] = norm_map
        ax_map.imshow(img)
        ax_map.imshow(heatmap)
        ax_map.axis('off')

    # SPECULAR average
    spec_avg = combination_func(all_maps['SPECULAR'])
    norm_spec_avg = spec_avg / spec_avg.max() if spec_avg.max() > 0 else spec_avg

    # Original image for specular average
    ax_spec = plt.subplot(6, n_cols, len(specular_vars) + 1)
    img = Image.open(parent_image_path)
    ax_spec.imshow(img)
    ax_spec.set_title('SPECULAR Average')
    ax_spec.axis('off')

    # Contribution map for specular average
    ax_spec_map = plt.subplot(6, n_cols, n_cols + len(specular_vars) + 1)
    heatmap = np.zeros((*norm_spec_avg.shape, 4))
    heatmap[..., 0] = 1.0
    heatmap[..., 3] = norm_spec_avg
    ax_spec_map.imshow(img)
    ax_spec_map.imshow(heatmap)
    ax_spec_map.axis('off')

    # Plot SHADE variations
    for idx, (stim_id, texture_type, activation) in enumerate(shade_vars):
        contrib_map = calculate_contribution_map(conn, stim_id)
        all_maps['SHADE'].append(contrib_map)
        norm_map = contrib_map / contrib_map.max() if contrib_map.max() > 0 else contrib_map

        conn.execute("SELECT path FROM StimPath WHERE stim_id = %s", (stim_id,))
        variant_path = conn.fetch_one()

        # Original image
        ax = plt.subplot(6, n_cols, 2 * n_cols + idx + 1)
        img = Image.open(variant_path)
        ax.imshow(img)
        ax.set_title(f'SHADE\nActivation: {activation:.3f}')
        ax.axis('off')

        # Contribution map
        ax_map = plt.subplot(6, n_cols, 3 * n_cols + idx + 1)
        heatmap = np.zeros((*norm_map.shape, 4))
        heatmap[..., 0] = 1.0
        heatmap[..., 3] = norm_map
        ax_map.imshow(img)
        ax_map.imshow(heatmap)
        ax_map.axis('off')

    # SHADE average
    shade_avg = combination_func(all_maps['SHADE'])
    norm_shade_avg = shade_avg / shade_avg.max() if shade_avg.max() > 0 else shade_avg

    # Original image for shade average
    ax_shade = plt.subplot(6, n_cols, 2 * n_cols + len(shade_vars) + 1)
    ax_shade.imshow(img)
    ax_shade.set_title('SHADE Average')
    ax_shade.axis('off')

    # Contribution map for shade average
    ax_shade_map = plt.subplot(6, n_cols, 3 * n_cols + len(shade_vars) + 1)
    heatmap = np.zeros((*norm_shade_avg.shape, 4))
    heatmap[..., 0] = 1.0
    heatmap[..., 3] = norm_shade_avg
    ax_shade_map.imshow(img)
    ax_shade_map.imshow(heatmap)
    ax_shade_map.axis('off')

    # Grand average
    all_maps_flat = all_maps['SPECULAR'] + all_maps['SHADE']
    grand_avg = combination_func(all_maps_flat)
    norm_grand_avg = grand_avg / grand_avg.max() if grand_avg.max() > 0 else grand_avg

    # Original image for grand average
    ax_grand = plt.subplot(6, n_cols, 4 * n_cols + n_cols // 2)
    ax_grand.imshow(img)
    ax_grand.set_title('Grand Average')
    ax_grand.axis('off')

    # Contribution map for grand average
    ax_grand_map = plt.subplot(6, n_cols, 5 * n_cols + n_cols // 2)
    heatmap = np.zeros((*norm_grand_avg.shape, 4))
    heatmap[..., 0] = 1.0
    heatmap[..., 3] = norm_grand_avg
    im = ax_grand_map.imshow(img)
    im = ax_grand_map.imshow(heatmap)
    ax_grand_map.axis('off')

    plt.tight_layout()
    plt.subplots_adjust(hspace=0.0, wspace=0.1)
    return fig

def get_stim_lighting_variations(conn: Connection, parent_id: int) -> list:
    """Get all lighting variations for a given parent stimulus."""
    query = """
    SELECT si.stim_id, si.texture_type, ua.activation
    FROM StimInstructions si
    JOIN UnitActivations ua ON si.stim_id = ua.stim_id
    WHERE si.parent_id = %s AND si.stim_type = 'TEXTURE_3D_VARIATION'
    ORDER BY ua.activation DESC
    """
    conn.execute(query, (parent_id,))
    return conn.fetch_all()


def calculate_contribution_map(conn: Connection, stim_id: int) -> np.ndarray:
    """Calculate summed positive contributions for a single stimulus."""
    contribution_map = np.zeros((227, 227))

    query = """
    SELECT to_unit_id, contribution 
    FROM UnitContributions 
    WHERE stim_id = %s 
    AND to_unit_id LIKE 'IMAGE_%%'
    AND contribution > 0
    """
    conn.execute(query, (stim_id,))
    contributions = conn.fetch_all()

    for unit_id, contribution in contributions:
        # Parse x,y from format IMAGE_u0_x{num}_y{num}
        x = int(unit_id.split('_')[2][1:])
        y = int(unit_id.split('_')[3][1:])
        if 0 <= x < 227 and 0 <= y < 227:
            contribution_map[x, y] += float(contribution)

    return contribution_map


def calculate_average_contribution_map(conn: Connection, variations: list) -> np.ndarray:
    """Calculate average contribution map across lighting variations."""
    all_maps = []

    for stim_id, _, _ in variations:
        contrib_map = calculate_contribution_map(conn, stim_id)
        if contrib_map.max() > 0:  # Only include non-zero maps
            all_maps.append(contrib_map)

    if not all_maps:
        return np.zeros((227, 227))

    avg_map = np.mean(all_maps, axis=0)
    # Smooth the map slightly for better visualization
    return avg_map


def calculate_combined_contribution_map(conn: Connection, variations: list, combination_func) -> np.ndarray:
    """Calculate average contribution map across lighting variations."""
    all_maps = []

    for stim_id, _, _ in variations:
        contrib_map = calculate_contribution_map(conn, stim_id)
        if contrib_map.max() > 0:  # Only include non-zero maps
            all_maps.append(contrib_map)

    if not all_maps:
        return np.zeros((227, 227))

    avg_map = combination_func(all_maps)
    # Smooth the map slightly for better visualization
    return avg_map




if __name__ == "__main__":
    main()
