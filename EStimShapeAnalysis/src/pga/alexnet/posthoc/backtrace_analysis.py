from __future__ import annotations
from enum import Enum

import numpy as np
import matplotlib.pyplot as plt
from clat.util.connection import Connection
from PIL import Image

from src.pga.alexnet import alexnet_context


class ContributionType(Enum):
    POSITIVE = 'POSITIVE'
    NEGATIVE = 'NEGATIVE'
    BOTH = 'BOTH'


def main():
    conn = Connection(
        host='172.30.6.80',
        user='xper_rw',
        password='up2nite',
        database=alexnet_context.lighting_database
    )

    # Get unique parent IDs
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
        # combination_func = lambda x: np.prod(x, axis=0)
        combination_func = lambda x: np.mean(x, axis=0)

        conv2_contribution = ContributionType.POSITIVE
        conv1_contribution = ContributionType.BOTH
        fig = plot_variations(conn, variations, parent_path, combination_func, conv2_contribution_type=conv2_contribution,
                              conv1_contribution_type=conv1_contribution)
        plt.figure(fig.number)
        plt.suptitle('Lighting variations for Parent ID: ' + str(parent_id))
        plt.savefig('/home/r2_allen/Documents/EStimShape/allen_alexnet_lighting_exp_241028_0/plots/' + str(
            parent_id) + str(conv2_contribution) + str(conv1_contribution) + '.png')
        plt.show()


def plot_variations(conn: Connection, variations: list, parent_image_path: str, combination_func=np.mean,
                    conv2_contribution_type=ContributionType.POSITIVE, conv1_contribution_type=ContributionType.BOTH):
    specular_vars = [v for v in variations if v[1] == 'SPECULAR']
    shade_vars = [v for v in variations if v[1] == 'SHADE']
    n_cols = max(len(specular_vars), len(shade_vars)) + 1

    fig = plt.figure(figsize=(20, 17))
    all_maps = {'SPECULAR': [], 'SHADE': []}

    # Plot SPECULAR variations
    for idx, (stim_id, texture_type, activation) in enumerate(specular_vars):
        contrib_map = calculate_contribution_map(conn, stim_id, conv2_contribution_type, conv1_contribution_type)
        all_maps['SPECULAR'].append(contrib_map)
        norm_map = contrib_map / contrib_map.max() if contrib_map.max() > 0 else contrib_map

        conn.execute("SELECT path FROM StimPath WHERE stim_id = %s", (stim_id,))
        variant_path = conn.fetch_one()

        # Plot Original image
        ax = plt.subplot(6, n_cols, idx + 1)
        img = Image.open(variant_path)
        ax.imshow(img)
        ax.set_title(f'SPECULAR\nActivation: {activation:.3f}')
        ax.axis('off')

        # Plot Contribution map
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
        contrib_map = calculate_contribution_map(conn, stim_id, conv2_contribution_type, conv1_contribution_type)
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


def calculate_contribution_map(conn: Connection, stim_id: int, conv2_contribution_type: ContributionType, conv1_contribution_type: ContributionType) -> np.ndarray:
    """Find all positive conv2 contributions:"""
    contribution_line = build_sql_contribution_line(conv2_contribution_type)
    query = f"""
    SELECT to_unit_id
    FROM UnitContributions
    WHERE stim_id = %s
    AND from_unit_id LIKE 'conv3%%'
    {contribution_line}
    """

    conn.execute(query, (stim_id,))
    conv2s = [result[0] for result in conn.fetch_all()]
    """Find all is_positive contributions for each conv2 unit:"""
    contribution_line = build_sql_contribution_line(conv1_contribution_type)
    all_conv1s = []
    for conv2 in conv2s:
        query = f"""
        SELECT to_unit_id 
        FROM UnitContributions 
        WHERE stim_id = %s 
        AND from_unit_id = %s 
        {contribution_line}
        """

        conn.execute(query, (stim_id, conv2))
        conv1s = [result[0] for result in conn.fetch_all()]
        all_conv1s.extend(conv1s)

    contribution_map = np.zeros((227, 227))

    for conv1 in all_conv1s:
        """Calculate summed positive contributions for a single stimulus."""
        query = """
            SELECT to_unit_id, contribution 
            FROM UnitContributions 
            WHERE stim_id = %s 
            AND from_unit_id = %s
            """

        conn.execute(query, (stim_id, conv1))
        contributions_for_to_unit_ids = conn.fetch_all()

        for unit_id, contribution in contributions_for_to_unit_ids:
            # Parse x,y from format IMAGE_u0_x{num}_y{num}
            x = int(unit_id.split('_')[2][1:])
            y = int(unit_id.split('_')[3][1:])
            if 0 <= x < 227 and 0 <= y < 227:
                contribution_map[x, y] += abs(float(contribution))

    return contribution_map


def build_sql_contribution_line(contribution_type):
    if contribution_type == ContributionType.POSITIVE:
        contribution_line = "AND contribution > 0"
    elif contribution_type == ContributionType.NEGATIVE:
        contribution_line = "AND contribution < 0"
    else:
        contribution_line = ""
    return contribution_line


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


if __name__ == "__main__":
    main()
