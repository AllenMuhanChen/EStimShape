import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from clat.util.connection import Connection

from src.pga.alexnet import alexnet_context
from src.pga.alexnet.posthoc.backtrace_analysis import calculate_contribution_map, get_stim_lighting_variations



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

        fig = plot_variations_multi_colors(conn, variations, parent_path, combination_func)
        plt.figure(fig.number)
        plt.suptitle('Lighting variations for Parent ID: ' + str(parent_id))
        plt.savefig('/home/r2_allen/Documents/EStimShape/allen_alexnet_lighting_exp_241028_0/plots/' + str(
            parent_id) + "_multi" + '.png')
        plt.show()

def plot_variations_multi_colors(conn: Connection, variations: list, parent_image_path: str, combination_func=np.mean):
    specular_vars = [v for v in variations if v[1] == 'SPECULAR']
    shade_vars = [v for v in variations if v[1] == 'SHADE']
    n_cols = max(len(specular_vars), len(shade_vars)) + 1

    fig = plt.figure(figsize=(20, 17))  # Increased height for double rows
    all_maps = {'SPECULAR': [], 'SHADE': []}
    colors = [(1,1,0), (1,0,0), (0,1,1), (0,1,0)]

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
        contrib_maps = calculate_each_contribution_map(conn, stim_id)
        all_maps['SPECULAR'].append(contrib_maps)
        combined_heatmap = np.zeros((*contrib_maps[0].shape, 4))
        for i, contrib_map in enumerate(contrib_maps):
            heatmap = np.zeros((*contrib_map.shape, 4))
            norm_map = contrib_map / contrib_map.max() if contrib_map.max() > 0 else contrib_map
            heatmap[..., 0] = colors[i][0]
            heatmap[..., 1] = colors[i][1]
            heatmap[..., 2] = colors[i][2]
            heatmap[..., 3] = norm_map
            ax_map.imshow(heatmap)
        ax_map.axis('off')






    # # SPECULAR average
    # spec_avg = combination_func(all_maps['SPECULAR'])
    # norm_spec_avg = spec_avg / spec_avg.max() if spec_avg.max() > 0 else spec_avg
    #
    # # Original image for specular average
    # ax_spec = plt.subplot(6, n_cols, len(specular_vars) + 1)
    # img = Image.open(parent_image_path)
    # ax_spec.imshow(img)
    # ax_spec.set_title('SPECULAR Average')
    # ax_spec.axis('off')
    #
    # # Contribution map for specular average
    # ax_spec_map = plt.subplot(6, n_cols, n_cols + len(specular_vars) + 1)
    # heatmap = np.zeros((*norm_spec_avg.shape, 4))
    # heatmap[..., 0] = 1.0
    # heatmap[..., 3] = norm_spec_avg
    # ax_spec_map.imshow(img)
    # ax_spec_map.imshow(heatmap)
    # ax_spec_map.axis('off')

    # # Plot SHADE variations
    # for idx, (stim_id, texture_type, activation) in enumerate(shade_vars):
    #     contrib_map = calculate_contribution_map(conn, stim_id)
    #     all_maps['SHADE'].append(contrib_map)
    #     norm_map = contrib_map / contrib_map.max() if contrib_map.max() > 0 else contrib_map
    #
    #     conn.execute("SELECT path FROM StimPath WHERE stim_id = %s", (stim_id,))
    #     variant_path = conn.fetch_one()
    #
    #     # Original image
    #     ax = plt.subplot(6, n_cols, 2 * n_cols + idx + 1)
    #     img = Image.open(variant_path)
    #     ax.imshow(img)
    #     ax.set_title(f'SHADE\nActivation: {activation:.3f}')
    #     ax.axis('off')
    #
    #     # Contribution map
    #     ax_map = plt.subplot(6, n_cols, 3 * n_cols + idx + 1)
    #     heatmap = np.zeros((*norm_map.shape, 4))
    #     heatmap[..., 0] = 1.0
    #     heatmap[..., 3] = norm_map
    #     ax_map.imshow(img)
    #     ax_map.imshow(heatmap)
    #     ax_map.axis('off')
    #
    # # SHADE average
    # shade_avg = combination_func(all_maps['SHADE'])
    # norm_shade_avg = shade_avg / shade_avg.max() if shade_avg.max() > 0 else shade_avg
    #
    # # Original image for shade average
    # ax_shade = plt.subplot(6, n_cols, 2 * n_cols + len(shade_vars) + 1)
    # ax_shade.imshow(img)
    # ax_shade.set_title('SHADE Average')
    # ax_shade.axis('off')
    #
    # # Contribution map for shade average
    # ax_shade_map = plt.subplot(6, n_cols, 3 * n_cols + len(shade_vars) + 1)
    # heatmap = np.zeros((*norm_shade_avg.shape, 4))
    # heatmap[..., 0] = 1.0
    # heatmap[..., 3] = norm_shade_avg
    # ax_shade_map.imshow(img)
    # ax_shade_map.imshow(heatmap)
    # ax_shade_map.axis('off')
    #
    # # Grand average
    # all_maps_flat = all_maps['SPECULAR'] + all_maps['SHADE']
    # grand_avg = combination_func(all_maps_flat)
    # norm_grand_avg = grand_avg / grand_avg.max() if grand_avg.max() > 0 else grand_avg
    #
    # # Original image for grand average
    # ax_grand = plt.subplot(6, n_cols, 4 * n_cols + n_cols // 2)
    # ax_grand.imshow(img)
    # ax_grand.set_title('Grand Average')
    # ax_grand.axis('off')
    #
    # # Contribution map for grand average
    # ax_grand_map = plt.subplot(6, n_cols, 5 * n_cols + n_cols // 2)
    # heatmap = np.zeros((*norm_grand_avg.shape, 4))
    # heatmap[..., 0] = 1.0
    # heatmap[..., 3] = norm_grand_avg
    # im = ax_grand_map.imshow(img)
    # im = ax_grand_map.imshow(heatmap)
    # ax_grand_map.axis('off')

    plt.tight_layout()
    plt.subplots_adjust(hspace=0.0, wspace=0.1)
    return fig

def calculate_each_contribution_map(conn: Connection, stim_id: int) -> list[np.ndarray]:
    contrib_maps = []
    conditions = [(True, True), (True, False), (False, True), (False, False)]
    for is_positive_conv2, is_positive_conv1 in conditions:
        contrib_map = calculate_contribution_map(conn, stim_id, is_positive_conv2, is_positive_conv1)
        contrib_maps.append(contrib_map)
    return contrib_maps

if __name__ == "__main__":
    main()
