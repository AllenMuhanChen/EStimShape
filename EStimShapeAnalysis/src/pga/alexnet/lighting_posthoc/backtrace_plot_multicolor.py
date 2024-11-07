import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from clat.util.connection import Connection

from src.pga.alexnet import alexnet_context
from src.pga.alexnet.analysis.plot_top_n import normalize_responses
from src.pga.alexnet.lighting_posthoc.backtrace_analysis import calculate_raw_contribution_map, \
    get_stim_lighting_variations, \
    ContributionType


def main():
    conn = Connection(
        host='172.30.6.80',
        user='xper_rw',
        password='up2nite',
        database=alexnet_context.lighting_database
    )

    contribution_types = [
        (ContributionType.POSITIVE, ContributionType.BOTH),
        (ContributionType.NEGATIVE, ContributionType.BOTH)
    ]

    # Get unique parent IDs
    query = """
       SELECT DISTINCT parent_id 
       FROM StimInstructions 
       WHERE stim_type = 'TEXTURE_3D_VARIATION'
       """
    conn.execute(query)
    parent_ids = [row[0] for row in conn.fetch_all()]

    for parent_id in parent_ids:
        # for parent_id in [1730131310638022]:
        variations = get_stim_lighting_variations(conn, parent_id)

        conn.execute("SELECT path FROM StimPath WHERE stim_id = %s", (parent_id,))
        parent_path = conn.fetch_one()
        # combination_func = lambda x: np.prod(x, axis=0)
        combination_func = lambda x: np.mean(x, axis=0)

        fig = plot_variations_multi_colors(conn, variations, parent_path, combination_func,
                                           contribution_types=contribution_types)
        plt.figure(fig.number)
        plt.suptitle('Lighting variations for Parent ID: ' + str(parent_id))
        plt.savefig(f"{alexnet_context.lighting_plots_dir}/{parent_id}_{contribution_types[0]}_{contribution_types[1]}_multi.png")
        plt.show()


def plot_variations_multi_colors(conn: Connection, variations: list, parent_image_path: str, combination_func=np.mean,
                                 contribution_types=None):
    if contribution_types is None:
        contribution_types = [
            (ContributionType.POSITIVE, ContributionType.BOTH),
            (ContributionType.NEGATIVE, ContributionType.BOTH)
        ]
    specular_vars = [v for v in variations if v[1] == 'SPECULAR']
    shade_vars = [v for v in variations if v[1] == 'SHADE']
    n_cols = max(len(specular_vars), len(shade_vars)) + 1

    fig = plt.figure(figsize=(20, 17))  # Increased height for double rows
    all_maps = {'SPECULAR': [], 'SHADE': []}
    colors = [(1, 0, 0), (0, 0, 1)]  # Red and Blue for positive and negative contributions

    # Plot SPECULAR variations
    for idx, (stim_id, texture_type, activation) in enumerate(specular_vars):
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
        ax_map.imshow(img)
        # Calculate Contributions
        contrib_maps = calculate_each_contribution_map(conn, stim_id, contribution_types)
        all_maps['SPECULAR'].append(contrib_maps)

        # Plot each contribution type with its respective color

        for i, contrib_map in enumerate(contrib_maps):
            heatmap = np.zeros((*contrib_map.shape, 4))
            norm_map = contrib_map / contrib_map.max() if contrib_map.max() > 0 else contrib_map
            heatmap[..., 0] = colors[i][0]
            heatmap[..., 1] = colors[i][1]
            heatmap[..., 2] = colors[i][2]
            heatmap[..., 3] = norm_map
            ax_map.imshow(heatmap)
        ax_map.axis('off')

    # SPECULAR average
    spec_maps_avg = [
        combination_func([maps[i] for maps in all_maps['SPECULAR']])
        for i in range(2)  # For positive and negative contributions
    ]

    # Original image for specular average
    ax_spec = plt.subplot(6, n_cols, len(specular_vars) + 1)
    img = Image.open(parent_image_path)
    ax_spec.imshow(img)
    ax_spec.set_title('SPECULAR Average')
    ax_spec.axis('off')

    # Contribution map for specular average
    ax_spec_map = plt.subplot(6, n_cols, n_cols + len(specular_vars) + 1)
    ax_spec_map.imshow(img)
    for i, spec_avg in enumerate(spec_maps_avg):
        norm_spec_avg = spec_avg / spec_avg.max() if spec_avg.max() > 0 else spec_avg
        heatmap = np.zeros((*norm_spec_avg.shape, 4))
        heatmap[..., 0] = colors[i][0]
        heatmap[..., 1] = colors[i][1]
        heatmap[..., 2] = colors[i][2]
        heatmap[..., 3] = norm_spec_avg
        ax_spec_map.imshow(heatmap)
    ax_spec_map.axis('off')

    # Plot SHADE variations
    for idx, (stim_id, texture_type, activation) in enumerate(shade_vars):
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
        ax_map.imshow(img)
        # Calculate Contributions
        contrib_maps = calculate_each_contribution_map(conn, stim_id, contribution_types)
        all_maps['SHADE'].append(contrib_maps)

        # Plot each contribution type with its respective color
        for i, contrib_map in enumerate(contrib_maps):
            heatmap = np.zeros((*contrib_map.shape, 4))
            norm_map = contrib_map / contrib_map.max() if contrib_map.max() > 0 else contrib_map
            heatmap[..., 0] = colors[i][0]
            heatmap[..., 1] = colors[i][1]
            heatmap[..., 2] = colors[i][2]
            heatmap[..., 3] = norm_map
            ax_map.imshow(heatmap)
        ax_map.axis('off')

    # SHADE average
    shade_maps_avg = [
        combination_func([maps[i] for maps in all_maps['SHADE']])
        for i in range(2)  # For positive and negative contributions
    ]

    # Original image for shade average
    ax_shade = plt.subplot(6, n_cols, 2 * n_cols + len(shade_vars) + 1)
    ax_shade.imshow(img)
    ax_shade.set_title('SHADE Average')
    ax_shade.axis('off')

    # Contribution map for shade average
    ax_shade_map = plt.subplot(6, n_cols, 3 * n_cols + len(shade_vars) + 1)
    ax_shade_map.imshow(img)
    for i, shade_avg in enumerate(shade_maps_avg):
        norm_shade_avg = shade_avg / shade_avg.max() if shade_avg.max() > 0 else shade_avg
        heatmap = np.zeros((*norm_shade_avg.shape, 4))
        heatmap[..., 0] = colors[i][0]
        heatmap[..., 1] = colors[i][1]
        heatmap[..., 2] = colors[i][2]
        heatmap[..., 3] = norm_shade_avg
        ax_shade_map.imshow(heatmap)
    ax_shade_map.axis('off')

    # Grand average
    all_maps_flat = [
        combination_func([
            *[maps[i] for maps in all_maps['SPECULAR']],
            *[maps[i] for maps in all_maps['SHADE']]
        ])
        for i in range(2)  # For positive and negative contributions
    ]

    # Original image for grand average
    ax_grand = plt.subplot(6, n_cols, 4 * n_cols + n_cols // 2)
    ax_grand.imshow(img)
    ax_grand.set_title('Grand Average')
    ax_grand.axis('off')

    # Contribution map for grand average
    ax_grand_map = plt.subplot(6, n_cols, 5 * n_cols + n_cols // 2)
    ax_grand_map.imshow(img)
    for i, grand_avg in enumerate(all_maps_flat):
        norm_grand_avg = grand_avg / grand_avg.max() if grand_avg.max() > 0 else grand_avg
        heatmap = np.zeros((*norm_grand_avg.shape, 4))
        heatmap[..., 0] = colors[i][0]
        heatmap[..., 1] = colors[i][1]
        heatmap[..., 2] = colors[i][2]
        heatmap[..., 3] = norm_grand_avg
        ax_grand_map.imshow(heatmap)
    ax_grand_map.axis('off')

    plt.tight_layout()
    plt.subplots_adjust(hspace=0.0, wspace=0.1)
    return fig


def calculate_each_contribution_map(conn: Connection, stim_id: int,
                                    conditions: list[tuple[ContributionType, ContributionType]]) -> list[np.ndarray]:
    contrib_maps = []
    for contrib_type_conv2, contrib_type_conv1 in conditions:
        contrib_map = calculate_raw_contribution_map(conn, stim_id, contrib_type_conv2, contrib_type_conv1)
        contrib_maps.append(contrib_map)
    return contrib_maps


if __name__ == "__main__":
    main()
