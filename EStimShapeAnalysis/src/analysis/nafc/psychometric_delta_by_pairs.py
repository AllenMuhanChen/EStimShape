import sys
from pathlib import Path
import numpy as np
from PIL import Image
import xmltodict
import os

# Add the parent directory to the path to import from the original file
sys.path.insert(0, str(Path(__file__).parent))

from matplotlib import pyplot as plt
from matplotlib.gridspec import GridSpec
from clat.compile.tstamp.cached_tstamp_fields import CachedFieldList
from clat.util import time_util
from clat.util.connection import Connection

from src.analysis.nafc.nafc_database_fields import (
    IsCorrectField, NoiseChanceField, NumRandDistractorsField,
    StimTypeField, ChoiceField, AnswerField, GenIdField, EStimEnabledFieldLegacy,
    BaseMStickIdField
)
from src.analysis.nafc.psychometric_curves import collect_choice_trials, plot_psychometric_curve_on_ax
from src.startup import context


def get_variant_delta_pairs(ga_conn):
    """
    Query IncludedDeltas table to get variant-delta pairs.
    Returns dict mapping variant_id -> delta_id for included deltas only.
    """
    query_sql = """
                SELECT variant_id, delta_id
                FROM IncludedDeltas
                WHERE included = TRUE \
                """
    ga_conn.execute(query_sql)
    results = ga_conn.fetch_all()

    variant_to_delta = {}
    for variant_id, delta_id in results:
        variant_to_delta[int(variant_id)] = int(delta_id)

    return variant_to_delta


def get_thumbnail_path_for_stim(exp_conn, stim_id):
    """
    Get thumbnail path for a specific stim_id.
    Replicates the logic from ThumbnailField.
    """
    # Get StimSpec XML
    exp_conn.execute("SELECT spec FROM StimSpec WHERE id = %s", (stim_id,))
    stim_spec_xml = exp_conn.fetch_one()

    if stim_spec_xml:
        # Parse XML to dict
        stim_spec_dict = xmltodict.parse(stim_spec_xml)
        path = stim_spec_dict['StimSpec']['path']

        # Clean path - remove sftp prefix
        if 'sftp:host=' in path:
            path = path[path.find('/home/'):]

        # Add thumbnail suffix before .png
        if path.endswith('.png'):
            thumbnail_path = path[:-4] + '_thumbnail.png'
            if os.path.exists(thumbnail_path):
                return thumbnail_path
            else:
                return path

    return None


def load_and_display_image(ax, image_path):
    """Load and display an image on the given axes."""
    try:
        if image_path and Path(image_path).exists():
            img = Image.open(image_path)
            ax.imshow(img)
            ax.axis('off')
        else:
            ax.text(0.5, 0.5, 'Image not found',
                    ha='center', va='center', transform=ax.transAxes)
            ax.axis('off')
    except Exception as e:
        ax.text(0.5, 0.5, f'Error loading image',
                ha='center', va='center', transform=ax.transAxes)
        ax.axis('off')


def main():
    # Database connections
    exp_conn = Connection("allen_estimshape_exp_260115_0")
    ga_conn = Connection(context.ga_database)

    # Time range
    since_date = time_util.from_date_to_now(2024, 7, 10)
    start_gen_id = 3
    max_gen_id = 4
    start_gen_id_estim_on = 0
    max_gen_id_estim_on = float('inf')

    # Get variant-delta pairs
    variant_to_delta = get_variant_delta_pairs(ga_conn)
    print(f"Found {len(variant_to_delta)} variant-delta pairs from IncludedDeltas table")

    # Collect trial timestamps
    trial_tstamps = collect_choice_trials(exp_conn, since_date)

    # Set up fields to collect
    fields = CachedFieldList()
    fields.append(IsCorrectField(exp_conn))
    fields.append(NoiseChanceField(exp_conn))
    fields.append(NumRandDistractorsField(exp_conn))
    fields.append(StimTypeField(exp_conn))
    fields.append(ChoiceField(exp_conn))
    fields.append(GenIdField(exp_conn))
    fields.append(EStimEnabledFieldLegacy(exp_conn))
    fields.append(BaseMStickIdField(exp_conn))

    # Convert to dataframe
    data = fields.to_data(trial_tstamps)

    # Filter data by GenId
    data = data[(data['GenId'] >= start_gen_id) & (data['GenId'] <= max_gen_id)]

    # Filter for experimental trials only
    data_exp = data[data['StimType'] == 'EStimShapeVariantsDeltaNAFCStim']

    # Get unique BaseMStickId values
    base_mstick_ids = data_exp['BaseMStickId'].dropna().unique()
    base_mstick_ids = sorted([int(x) for x in base_mstick_ids if x is not None])

    if len(base_mstick_ids) == 0:
        print("No BaseMStickId values found in the data!")
        return

    # Separate variants and deltas, and pair them
    variants_in_data = [bid for bid in base_mstick_ids if bid in variant_to_delta]

    print(f"Found {len(variants_in_data)} variants with delta pairs in the data")

    if len(variants_in_data) == 0:
        print("No variant-delta pairs found in the behavioral data!")
        return

    # Calculate grid dimensions (2 columns per row: variant + delta)
    n_pairs = len(variants_in_data)
    n_rows = n_pairs

    # Create figure with GridSpec for flexible layout
    # Each row has: [variant_image, delta_image] on top, [variant_plot, delta_plot] below
    fig = plt.figure(figsize=(12, 6 * n_rows))
    gs = GridSpec(n_rows * 2, 2, figure=fig, height_ratios=[1, 2] * n_rows,
                  hspace=0.7, wspace=0.3)

    # Plot each variant-delta pair
    for pair_idx, variant_id in enumerate(variants_in_data):
        delta_id = variant_to_delta[variant_id]

        row_start = pair_idx * 2

        # Get thumbnail paths using the stim IDs directly
        variant_thumb = get_thumbnail_path_for_stim(ga_conn, variant_id)
        delta_thumb = get_thumbnail_path_for_stim(ga_conn, delta_id)

        # Create axes for images (top row)
        ax_variant_img = fig.add_subplot(gs[row_start, 0])
        ax_delta_img = fig.add_subplot(gs[row_start, 1])

        # Display images
        load_and_display_image(ax_variant_img, variant_thumb)
        ax_variant_img.set_title(f'Variant: {variant_id}', fontsize=10, fontweight='bold')

        load_and_display_image(ax_delta_img, delta_thumb)
        ax_delta_img.set_title(f'Delta: {delta_id}', fontsize=10, fontweight='bold')

        # Create axes for psychometric curves (bottom row)
        ax_variant = fig.add_subplot(gs[row_start + 1, 0])
        ax_delta = fig.add_subplot(gs[row_start + 1, 1])

        # Filter data for variant
        data_variant = data_exp[data_exp['BaseMStickId'] == variant_id].copy()
        data_variant_estim_on = data_variant[
            (data_variant['EStimEnabled'] == True) &
            (data_variant['GenId'] >= start_gen_id_estim_on) &
            (data_variant['GenId'] <= max_gen_id_estim_on)
            ]
        data_variant_estim_off = data_variant[data_variant['EStimEnabled'] == False]

        # Plot variant curves
        if len(data_variant_estim_on) > 0:
            plot_psychometric_curve_on_ax(
                data_variant_estim_on, ax_variant,
                title=f'Variant {variant_id}',
                show_n=True, num_rep_min=0,
                color='red', linewidth=2.5, marker='s', markersize=6,
                label=f'EStim ON (n={len(data_variant_estim_on)})'
            )

        if len(data_variant_estim_off) > 0:
            plot_psychometric_curve_on_ax(
                data_variant_estim_off, ax_variant,
                title=f'Variant {variant_id}',
                show_n=True, num_rep_min=0,
                color='blue', linewidth=2.5, marker='o', markersize=6,
                label=f'EStim OFF (n={len(data_variant_estim_off)})'
            )

        ax_variant.invert_xaxis()
        ax_variant.set_ylim([0, 110])
        ax_variant.grid(True, alpha=0.3)
        ax_variant.legend()

        # Filter data for delta
        data_delta = data_exp[data_exp['BaseMStickId'] == delta_id].copy()
        data_delta_estim_on = data_delta[
            (data_delta['EStimEnabled'] == True) &
            (data_delta['GenId'] >= start_gen_id_estim_on) &
            (data_delta['GenId'] <= max_gen_id_estim_on)
            ]
        data_delta_estim_off = data_delta[data_delta['EStimEnabled'] == False]

        # Plot delta curves
        if len(data_delta_estim_on) > 0:
            plot_psychometric_curve_on_ax(
                data_delta_estim_on, ax_delta,
                title=f'Delta {delta_id}',
                show_n=True, num_rep_min=0,
                color='red', linewidth=2.5, marker='s', markersize=6,
                label=f'EStim ON (n={len(data_delta_estim_on)})'
            )

        if len(data_delta_estim_off) > 0:
            plot_psychometric_curve_on_ax(
                data_delta_estim_off, ax_delta,
                title=f'Delta {delta_id}',
                show_n=True, num_rep_min=0,
                color='blue', linewidth=2.5, marker='o', markersize=6,
                label=f'EStim OFF (n={len(data_delta_estim_off)})'
            )

        ax_delta.invert_xaxis()
        ax_delta.set_ylim([0, 110])
        ax_delta.grid(True, alpha=0.3)
        ax_delta.legend()

        # Print statistics
        print(f"\nPair {pair_idx + 1}: Variant {variant_id} & Delta {delta_id}")
        print(f"  Variant - EStim ON: {len(data_variant_estim_on)} trials, "
              f"EStim OFF: {len(data_variant_estim_off)} trials")
        print(f"  Delta - EStim ON: {len(data_delta_estim_on)} trials, "
              f"EStim OFF: {len(data_delta_estim_off)} trials")

    plt.suptitle('Psychometric Curves: Variant-Delta Pairs', fontsize=16, y=0.995)
    plt.show()


if __name__ == '__main__':
    main()