import matplotlib.pyplot as plt
import numpy as np
from dataclasses import dataclass
from clat.util.connection import Connection
from src.pga.alexnet import alexnet_context
from PIL import Image
from typing import List, Dict
from collections import defaultdict


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


def load_stim_data(conn: Connection) -> Dict[str, List[StimData]]:
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
        stim = StimData(
            stim_id=r[0], path=r[1], parent_id=r[2], texture_type=r[3],
            light_pos_x=r[4], light_pos_y=r[5], light_pos_z=r[6], light_pos_w=r[7],
            activation=r[8]
        )
        if stim.texture_type in ['SPECULAR', 'SHADE']:
            stims_3d.append(stim)
        else:
            stims_2d.append(stim)

    return {'3D': stims_3d, '2D': stims_2d}


def organize_3d_stims(stims_3d: List[StimData]) -> Dict[int, Dict[str, List[StimData]]]:
    """Organize 3D stims by parent_id -> texture_type -> lighting variations"""
    organized = defaultdict(lambda: defaultdict(list))
    for stim in stims_3d:
        organized[stim.parent_id][stim.texture_type].append(stim)

    # Sort each lighting variation list by x position (arbitrary but consistent ordering)
    for parent in organized:
        for texture in organized[parent]:
            organized[parent][texture].sort(key=lambda x: x.light_pos_x)

    return organized


from src.pga.alexnet.analysis.plot_top_n import plot_stimuli_row, normalize_responses
def plot_stims(stims_3d: List[StimData], stims_2d: List[StimData], n_cols: int = 8):
    # Find max absolute activation for normalization
    all_activations = [stim.activation for stim in stims_3d + stims_2d]
    max_abs_activation = max(abs(min(all_activations)), abs(max(all_activations)))

    organized_3d = organize_3d_stims(stims_3d)
    organized_2d = defaultdict(list)
    for stim in stims_2d:
        organized_2d[stim.parent_id].append(stim)

    figs = []
    for parent_id in organized_3d:
        n_rows = 4
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(4 * n_cols, 16))
        figs.append(fig)

        def convert_to_plot_format(stims):
            return [{'stim_id': s.stim_id,
                    'response': s.activation,
                    'path': s.path,
                    'lineage_id': s.parent_id} for s in stims]

        # Plot SPECULAR row and its matching 2D row
        spec_3d = organized_3d[parent_id]['SPECULAR'][:n_cols]
        spec_3d_formatted = convert_to_plot_format(spec_3d)
        normalized_responses = normalize_responses(spec_3d_formatted)
        plot_stimuli_row(spec_3d_formatted, normalized_responses,
                         axes[0],
                         )  # Always false to allow both red and blue

        axes[0, 0].set_title(f'Parent {parent_id}\nSPECULAR')

        # Get 2D matches for SPECULAR variations
        spec_2d = []
        for spec_stim in spec_3d:
            matching_2d = [s for s in stims_2d if s.parent_id == spec_stim.stim_id]
            if matching_2d:
                spec_2d.append(matching_2d[0])
        spec_2d_formatted = convert_to_plot_format(spec_2d)
        plot_stimuli_row(spec_2d_formatted, [s['response'] for s in spec_2d_formatted],
                        axes[1],
                        )
        axes[1, 0].set_title('2D match for SPECULAR')

        # Plot SHADE row and its matching 2D row
        shade_3d = organized_3d[parent_id]['SHADE'][:n_cols]
        shade_3d_formatted = convert_to_plot_format(shade_3d)
        plot_stimuli_row(shade_3d_formatted, [s['response'] for s in shade_3d_formatted],
                        axes[2],
                        )
        axes[2, 0].set_title('SHADE')

        # Get 2D matches for SHADE variations
        shade_2d = []
        for shade_stim in shade_3d:
            matching_2d = [s for s in stims_2d if s.parent_id == shade_stim.stim_id]
            if matching_2d:
                shade_2d.append(matching_2d[0])
        shade_2d_formatted = convert_to_plot_format(shade_2d)
        plot_stimuli_row(spec_2d_formatted, [s['response'] for s in shade_2d_formatted],
                        axes[3],
                        )
        axes[3, 0].set_title('2D match for SHADE')

        plt.tight_layout()

    return figs
def main():
    conn = Connection(
        host='172.30.6.80',
        user='xper_rw',
        password='up2nite',
        database=alexnet_context.lighting_database
    )

    # Load data
    stims = load_stim_data(conn)
    print("Total 3D stims:", len(stims['3D']))
    print("Total 2D stims:", len(stims['2D']))

    # Create plots
    figs = plot_stims(stims['3D'], stims['2D'])

    # Show all figures
    plt.show()


if __name__ == "__main__":
    main()