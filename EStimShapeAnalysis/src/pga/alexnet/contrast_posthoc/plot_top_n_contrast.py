import matplotlib.pyplot as plt
import numpy as np
from dataclasses import dataclass
from typing import List, Dict
from collections import defaultdict
from clat.util.connection import Connection
from src.pga.alexnet import alexnet_context
from src.pga.alexnet.analysis.plot_top_n import normalize_responses, add_colored_border, plot_stimuli_row
from PIL import Image


def load_contrast_data(conn: Connection) -> Dict[str, List[dict]]:
    """Load all stimuli data, organized by type (SPECULAR, SHADE, 2D)"""
    query = """
    SELECT si.stim_id, sp.path, si.parent_id, si.texture_type, 
           si.contrast, ua.activation
    FROM StimInstructions si
    JOIN StimPath sp ON si.stim_id = sp.stim_id
    JOIN UnitActivations ua ON si.stim_id = ua.stim_id
    ORDER BY si.parent_id, si.texture_type, si.contrast
    """
    conn.execute(query)
    results = conn.fetch_all()

    # Organize by texture type
    stims = defaultdict(list)
    for r in results:
        stim = {
            'stim_id': r[0],
            'path': r[1],
            'parent_id': r[2],
            'texture_type': r[3],
            'contrast': r[4],
            'response': r[5],
            'lineage_id': 0  # Kept for compatibility with plotting functions
        }
        stims[stim['texture_type']].append(stim)

    return stims


def organize_contrast_stims(stims: Dict[str, List[dict]]) -> Dict[int, Dict[str, List[dict]]]:
    """Organize stimuli by parent_id -> texture_type -> contrast variations"""
    organized = defaultdict(lambda: defaultdict(list))
    for texture_type, stim_list in stims.items():
        for stim in stim_list:
            organized[stim['parent_id']][texture_type].append(stim)

    # Sort each contrast variation list by contrast value
    for parent in organized:
        for texture in organized[parent]:
            organized[parent][texture].sort(key=lambda x: x['contrast'])

    return organized


def plot_contrast_variations(conn: Connection):
    """Plot contrast variations for each stimulus with texture types in different rows."""
    # Load and organize data
    stims = load_contrast_data(conn)

    # Get all stimuli for normalization
    all_stims = []
    for texture_stims in stims.values():
        all_stims.extend(texture_stims)
    normalize_responses(all_stims)

    # Organize by parent
    organized = organize_contrast_stims(stims)

    figs = []
    for parent_id in organized:
        # Determine number of contrast levels from data
        n_cols = max(len(organized[parent_id][texture]) for texture in organized[parent_id])
        n_rows = 3  # SPECULAR, SHADE, 2D

        fig, axes = plt.subplots(n_rows, n_cols, figsize=(4 * n_cols, 12))
        figs.append(fig)

        # Plot SPECULAR variations
        if 'SPECULAR' in organized[parent_id]:
            spec_variations = organized[parent_id]['SPECULAR']
            plot_stimuli_row(spec_variations, axes[0])
            axes[0, 0].set_title(f'Parent {parent_id}\nSPECULAR')
            # Add contrast values as subtitles
            for i, stim in enumerate(spec_variations):
                axes[0, i].set_xlabel(f'Contrast: {stim["contrast"]:.2f}')

        # Plot SHADE variations
        if 'SHADE' in organized[parent_id]:
            shade_variations = organized[parent_id]['SHADE']
            plot_stimuli_row(shade_variations, axes[1])
            axes[1, 0].set_title('SHADE')
            # Add contrast values as subtitles
            for i, stim in enumerate(shade_variations):
                axes[1, i].set_xlabel(f'Contrast: {stim["contrast"]:.2f}')

        # Plot 2D variations
        if '2D' in organized[parent_id]:
            flat_variations = organized[parent_id]['2D']
            plot_stimuli_row(flat_variations, axes[2])
            axes[2, 0].set_title('2D')
            # Add contrast values as subtitles
            for i, stim in enumerate(flat_variations):
                axes[2, i].set_xlabel(f'Contrast: {stim["contrast"]:.2f}')

        plt.tight_layout()
        plt.subplots_adjust(hspace=0.3)  # Add space for contrast value labels

    return figs


def main():
    conn = Connection(
        host='172.30.6.80',
        user='xper_rw',
        password='up2nite',
        database=alexnet_context.contrast_database
    )

    # Create plots
    figs = plot_contrast_variations(conn)

    # Save and show all figures
    for i, fig in enumerate(figs):
        plt.figure(fig.number)
        plt.savefig(
            f'/home/r2_allen/Documents/EStimShape/{alexnet_context.contrast_database}/plots/contrast_variation_{i}.png')
        plt.show()


if __name__ == "__main__":
    main()