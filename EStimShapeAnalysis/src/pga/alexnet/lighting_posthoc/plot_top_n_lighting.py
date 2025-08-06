import matplotlib.pyplot as plt
import numpy as np
from dataclasses import dataclass
from clat.util.connection import Connection
from src.pga.alexnet import alexnet_context
from PIL import Image
from typing import List, Dict
from collections import defaultdict

from src.startup import db_ip


@dataclass
class StimData:
    stim_id: int
    path: str
    parent_id: int
    texture_type: str
    light_pos_x: float
    light_pos_y: float
    light_pos_z: float
    light_pos_w: float
    activation: float


def main():
    conn = Connection(
        host=db_ip,
        user='xper_rw',
        password='up2nite',
        database=alexnet_context.lighting_database
    )

    # Load data
    stims: dict[str, list[dict]] = load_all_stim_data(conn)
    print("Total 3D stims:", len(stims['3D']))
    print("Total 2D stims:", len(stims['2D']))

    # Create plots
    all_stims = []
    all_stims.extend(stims['3D'])
    all_stims.extend(stims['2D'])
    normalize_responses(all_stims)
    plot_stims(stims['3D'], stims['2D'])

    # Show all figures
    plt.show()


def load_all_stim_data(conn: Connection) -> Dict[str, List[dict]]:
    """Load all stimuli data, organized by type (3D vs 2D)"""
    query = """
    SELECT si.stim_id, sp.path, si.parent_id, si.texture_type, 
           si.light_pos_x, si.light_pos_y, si.light_pos_z, si.light_pos_w,
           ua.activation
    FROM StimInstructions si
    JOIN StimPath sp ON si.stim_id = sp.stim_id
    JOIN UnitActivations ua ON si.stim_id = ua.stim_id
    ORDER BY si.parent_id, si.texture_type, si.light_pos_x
    """
    conn.execute(query)
    results = conn.fetch_all()

    # Organize by stim type
    stims_3d = []
    stims_2d = []

    for r in results:
        stim = {
            'stim_id': r[0],
            'path': r[1],
            'parent_id': r[2],
            'texture_type': r[3],
            'light_pos_x': r[4],
            'light_pos_y': r[5],
            'light_pos_z': r[6],
            'light_pos_w': r[7],
            'response': r[8],
            'lineage_id': 0
        }
        if stim['texture_type'] in ['SPECULAR', 'SHADE']:
            stims_3d.append(stim)
        else:
            stims_2d.append(stim)

    return {'3D': stims_3d, '2D': stims_2d}


def organize_3d_stims(stims_3d: List[dict]) -> Dict[int, Dict[str, List[dict]]]:
    """Organize 3D stims by parent_id -> texture_type -> lighting variations"""
    organized = defaultdict(lambda: defaultdict(list))
    for stim in stims_3d:
        organized[stim['parent_id']][stim['texture_type']].append(stim)

    # Sort each lighting variation list by x position (arbitrary but consistent ordering)
    for parent in organized:
        for texture in organized[parent]:
            organized[parent][texture].sort(key=lambda x: x['light_pos_x'])

    return organized


from src.pga.alexnet.analysis.plot_top_n_alexnet import plot_stimuli_row, normalize_responses


def plot_stims(stims_3d: List[dict], stims_2d: List[dict], n_cols: int = 8):
    # Find max absolute activation for normalization
    organized_3d = organize_3d_stims(stims_3d)
    organized_2d = defaultdict(list)
    for stim in stims_2d:
        organized_2d[stim['parent_id']].append(stim)

    figs = []
    for parent_id in organized_3d:
        n_rows = 4
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(4 * n_cols, 16))
        figs.append(fig)



        # Plot SPECULAR row and its matching 2D row
        spec_3d = organized_3d[parent_id]['SPECULAR'][:n_cols]
        spec_3d_formatted = spec_3d
        #get normalized responses from all_activations_normalized

        # normalized_responses = normalize_responses(spec_3d_formatted)
        plot_stimuli_row(spec_3d,
                         axes[0],)  # Always false to allow both red and blue

        axes[0, 0].set_title(f'Parent {parent_id}\nSPECULAR')

        # Get 2D matches for SPECULAR variations
        spec_2d = []
        for spec_stim in spec_3d:
            matching_2d = [s for s in stims_2d if s['parent_id'] == spec_stim['stim_id']]
            if matching_2d:
                spec_2d.append(matching_2d[0])

        plot_stimuli_row(spec_2d,
                         axes[1],
                         )
        axes[1, 0].set_title('2D match for SPECULAR')

        # Plot SHADE row and its matching 2D row
        shade_3d = organized_3d[parent_id]['SHADE'][:n_cols]

        plot_stimuli_row(shade_3d,
                         axes[2],
                         )
        axes[2, 0].set_title('SHADE')

        # Get 2D matches for SHADE variations
        shade_2d = []
        for shade_stim in shade_3d:
            matching_2d = [s for s in stims_2d if s['parent_id'] == shade_stim['stim_id']]
            if matching_2d:
                shade_2d.append(matching_2d[0])
        plot_stimuli_row(spec_2d,
                         axes[3],
                         )
        axes[3, 0].set_title('2D match for SHADE')

        plt.tight_layout()
        plt.savefig(f"{alexnet_context.lighting_plots_dir}/{parent_id}_responses.png")

    return figs


if __name__ == "__main__":
    main()
