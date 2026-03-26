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
    StimTypeField, ChoiceField, AnswerField, GenIdField, EStimEnabledField,
    BaseMStickIdField, IsDeltaField, EStimPolarityField, IsHypothesizedField
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


def get_stim_response_from_ga(ga_conn, stim_id):
    """
    Query StimGaInfo to get response value for a specific stim_id.
    Returns the response value or None if not found.
    """
    query_sql = "SELECT response FROM StimGaInfo WHERE stim_id = %s"
    ga_conn.execute(query_sql, (stim_id,))
    result = ga_conn.fetch_one()
    return float(result) if result is not None else None


def get_all_ga_responses(ga_conn):
    """
    Query StimGaInfo to get all response values for calculating global min/max.
    Returns list of response values.
    """
    query_sql = "SELECT response FROM StimGaInfo WHERE response IS NOT NULL"
    ga_conn.execute(query_sql)
    results = ga_conn.fetch_all()
    return [float(r[0]) for r in results if r is not None]


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


def add_border_to_image(img, response_rate, min_val=0.0, max_val=100.0,
                        border_width=20, color_mode='intensity'):
    """
    Add a colored border to an image based on response rate.

    Args:
        img: PIL Image
        response_rate: Response rate value (0-100 for percentage)
        min_val: Minimum value for normalization
        max_val: Maximum value for normalization
        border_width: Width of border in pixels
        color_mode: 'intensity' (black to red) or 'divergent' (blue-white-red)

    Returns:
        PIL Image with border
    """
    from PIL import ImageOps

    # Calculate normalized response (0-1 range)
    if min_val == max_val:
        normalized_response = 0.5
    else:
        normalized_response = (response_rate - min_val) / (max_val - min_val)
        normalized_response = max(0.0, min(1.0, normalized_response))

    # Determine border color based on color mode
    if color_mode == 'intensity':
        # Red scale intensity (black to red)
        border_color = (int(255 * normalized_response), 0, 0)
    else:  # 'divergent'
        # Center point for divergent color scale
        center_point = 0.5
        if normalized_response >= center_point:
            # Red for values above center
            intensity = (normalized_response - center_point) * 2
            border_color = (int(255 * intensity), 0, 0)
        else:
            # Blue for values below center
            intensity = (center_point - normalized_response) * 2
            border_color = (0, 0, int(255 * intensity))

    # Add border to image
    img_with_border = ImageOps.expand(img, border=border_width, fill=border_color)
    return img_with_border


def load_and_display_image(ax, image_path, response_rate=None, min_val=0.0, max_val=100.0,
                           border_width=20, color_mode='intensity'):
    """
    Load and display an image on the given axes with optional colored border.

    Args:
        ax: Matplotlib axes
        image_path: Path to image file
        response_rate: Optional response rate for border coloring (0-100)
        min_val: Minimum value for normalization
        max_val: Maximum value for normalization
        border_width: Width of border in pixels
        color_mode: 'intensity' or 'divergent'
    """
    try:
        if image_path and Path(image_path).exists():
            img = Image.open(image_path)

            # Add border if response_rate is provided
            if response_rate is not None:
                img = add_border_to_image(img, response_rate, min_val, max_val,
                                          border_width, color_mode)

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
    exp_conn = Connection("allen_estimshape_exp_260325_0")
    ga_conn = Connection(context.ga_database)

    # Time range
    since_date = time_util.from_date_to_now(2024, 7, 10)
    start_gen_id = 2
    max_gen_id = float('inf')
    start_gen_id_estim_on = 0
    max_gen_id_estim_on = float('inf')

    # ============ CORRECTNESS FIELD SELECTION ============
    # Specify which field to use for correctness metric
    # Options: "IsCorrect" or "IsHypothesized"
    isCorrectFieldName = "IsHypothesized"
    # ====================================================

    # ============ BORDER VISUALIZATION SETTINGS ============
    # Add colored borders to images based on GA response values
    add_borders = True
    border_width = 20  # Width of border in pixels
    border_color_mode = 'intensity'  # 'intensity' (black->red) or 'divergent' (blue->white->red)
    # ======================================================

    # Get variant-delta pairs
    variant_to_delta = get_variant_delta_pairs(ga_conn)
    print(f"Found {len(variant_to_delta)} variant-delta pairs from IncludedDeltas table")

    # Get all GA responses for global min/max calculation
    all_ga_responses = get_all_ga_responses(ga_conn)
    if all_ga_responses:
        global_min_response = min(all_ga_responses)
        global_max_response = max(all_ga_responses)
        print(f"GA Response range: {global_min_response:.2f} to {global_max_response:.2f}")
    else:
        global_min_response = 0.0
        global_max_response = 1.0
        print("Warning: No GA responses found, using default range [0, 1]")

    # Collect trial timestamps
    trial_tstamps = collect_choice_trials(exp_conn, since_date)

    # Set up fields to collect
    fields = CachedFieldList()
    fields.append(IsCorrectField(exp_conn))
    fields.append(IsHypothesizedField(exp_conn))
    fields.append(NoiseChanceField(exp_conn))
    fields.append(NumRandDistractorsField(exp_conn))
    fields.append(StimTypeField(exp_conn))
    fields.append(ChoiceField(exp_conn))
    fields.append(GenIdField(exp_conn))
    fields.append(EStimEnabledField(exp_conn))
    fields.append(BaseMStickIdField(exp_conn))
    fields.append(IsDeltaField(exp_conn))
    fields.append(EStimPolarityField(exp_conn))

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
                  hspace=1.0, wspace=0.3)

    # Plot each variant-delta pair
    for pair_idx, variant_id in enumerate(variants_in_data):
        delta_id = variant_to_delta[variant_id]

        row_start = pair_idx * 2

        # Get thumbnail paths using the stim IDs directly
        variant_thumb = get_thumbnail_path_for_stim(ga_conn, variant_id)
        delta_thumb = get_thumbnail_path_for_stim(ga_conn, delta_id)

        # Get response values from StimGaInfo for border coloring
        variant_response = get_stim_response_from_ga(ga_conn, variant_id) if add_borders else None
        delta_response = get_stim_response_from_ga(ga_conn, delta_id) if add_borders else None

        # Create axes for images (top row)
        ax_variant_img = fig.add_subplot(gs[row_start, 0])
        ax_delta_img = fig.add_subplot(gs[row_start, 1])

        # Display images with borders based on GA response
        load_and_display_image(ax_variant_img, variant_thumb,
                               response_rate=variant_response,
                               min_val=global_min_response,
                               max_val=global_max_response,
                               border_width=border_width,
                               color_mode=border_color_mode)
        # Set title with stim ID and response value
        variant_title = f'Variant: {variant_id}'
        if variant_response is not None:
            variant_title += f'\nResponse: {variant_response:.3f}'
        ax_variant_img.set_title(variant_title, fontsize=10, fontweight='bold')

        load_and_display_image(ax_delta_img, delta_thumb,
                               response_rate=delta_response,
                               min_val=global_min_response,
                               max_val=global_max_response,
                               border_width=border_width,
                               color_mode=border_color_mode)
        # Set title with stim ID and response value
        delta_title = f'Delta: {delta_id}'
        if delta_response is not None:
            delta_title += f'\nResponse: {delta_response:.3f}'
        ax_delta_img.set_title(delta_title, fontsize=10, fontweight='bold')

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

        # Split variant EStim ON by polarity
        data_variant_anodic = data_variant_estim_on[data_variant_estim_on['EStimPolarity'] == 'PositiveFirst']
        data_variant_cathodic = data_variant_estim_on[data_variant_estim_on['EStimPolarity'] == 'NegativeFirst']
        data_variant_combined = data_variant_estim_on  # All EStim ON

        # Plot variant curves
        if len(data_variant_anodic) > 0:
            plot_psychometric_curve_on_ax(
                data_variant_anodic, ax_variant,
                title=f'Variant {variant_id}',
                show_n=True, num_rep_min=0,
                color='blue', linewidth=2.5, marker='s', markersize=6, linestyle='-',
                label=f'Anodic (n={len(data_variant_anodic)})',
                isCorrectColumnName=isCorrectFieldName
            )

        if len(data_variant_cathodic) > 0:
            plot_psychometric_curve_on_ax(
                data_variant_cathodic, ax_variant,
                title=f'Variant {variant_id}',
                show_n=True, num_rep_min=0,
                color='blue', linewidth=2.5, marker='s', markersize=6, linestyle=':',
                label=f'Cathodic (n={len(data_variant_cathodic)})',
                isCorrectColumnName=isCorrectFieldName
            )

        if len(data_variant_combined) > 0:
            plot_psychometric_curve_on_ax(
                data_variant_combined, ax_variant,
                title=f'Variant {variant_id}',
                show_n=True, num_rep_min=0,
                color='darkblue', linewidth=2.5, marker='D', markersize=6, linestyle='--',
                label=f'Combined (n={len(data_variant_combined)})',
                isCorrectColumnName=isCorrectFieldName
            )

        if len(data_variant_estim_off) > 0:
            plot_psychometric_curve_on_ax(
                data_variant_estim_off, ax_variant,
                title=f'Variant {variant_id}',
                show_n=True, num_rep_min=0,
                color='lightblue', linewidth=2.5, marker='o', markersize=6, linestyle='-',
                label=f'OFF (n={len(data_variant_estim_off)})',
                isCorrectColumnName=isCorrectFieldName
            )

        ax_variant.invert_xaxis()
        ax_variant.set_ylim([0, 110])
        ax_variant.grid(True, alpha=0.3)
        ax_variant.legend(fontsize=8)

        # Filter data for delta
        data_delta = data_exp[data_exp['BaseMStickId'] == delta_id].copy()
        data_delta_estim_on = data_delta[
            (data_delta['EStimEnabled'] == True) &
            (data_delta['GenId'] >= start_gen_id_estim_on) &
            (data_delta['GenId'] <= max_gen_id_estim_on)
            ]
        data_delta_estim_off = data_delta[data_delta['EStimEnabled'] == False]

        # Split delta EStim ON by polarity
        data_delta_anodic = data_delta_estim_on[data_delta_estim_on['EStimPolarity'] == 'PositiveFirst']
        data_delta_cathodic = data_delta_estim_on[data_delta_estim_on['EStimPolarity'] == 'NegativeFirst']
        data_delta_combined = data_delta_estim_on  # All EStim ON

        # Plot delta curves
        if len(data_delta_anodic) > 0:
            plot_psychometric_curve_on_ax(
                data_delta_anodic, ax_delta,
                title=f'Delta {delta_id}',
                show_n=True, num_rep_min=0,
                color='red', linewidth=2.5, marker='s', markersize=6, linestyle='-',
                label=f'Anodic (n={len(data_delta_anodic)})',
                isCorrectColumnName=isCorrectFieldName
            )

        if len(data_delta_cathodic) > 0:
            plot_psychometric_curve_on_ax(
                data_delta_cathodic, ax_delta,
                title=f'Delta {delta_id}',
                show_n=True, num_rep_min=0,
                color='red', linewidth=2.5, marker='s', markersize=6, linestyle=':',
                label=f'Cathodic (n={len(data_delta_cathodic)})',
                isCorrectColumnName=isCorrectFieldName
            )

        if len(data_delta_combined) > 0:
            plot_psychometric_curve_on_ax(
                data_delta_combined, ax_delta,
                title=f'Delta {delta_id}',
                show_n=True, num_rep_min=0,
                color='darkred', linewidth=2.5, marker='D', markersize=6, linestyle='--',
                label=f'Combined (n={len(data_delta_combined)})',
                isCorrectColumnName=isCorrectFieldName
            )

        if len(data_delta_estim_off) > 0:
            plot_psychometric_curve_on_ax(
                data_delta_estim_off, ax_delta,
                title=f'Delta {delta_id}',
                show_n=True, num_rep_min=0,
                color='pink', linewidth=2.5, marker='o', markersize=6, linestyle='-',
                label=f'OFF (n={len(data_delta_estim_off)})',
                isCorrectColumnName=isCorrectFieldName
            )

        ax_delta.invert_xaxis()
        ax_delta.set_ylim([0, 110])
        ax_delta.grid(True, alpha=0.3)
        ax_delta.legend(fontsize=8)

        # Print statistics
        print(f"\nPair {pair_idx + 1}: Variant {variant_id} & Delta {delta_id}")
        print(f"  Variant - Anodic: {len(data_variant_anodic)}, "
              f"Cathodic: {len(data_variant_cathodic)}, "
              f"Combined: {len(data_variant_combined)}, "
              f"OFF: {len(data_variant_estim_off)}")
        print(f"  Delta - Anodic: {len(data_delta_anodic)}, "
              f"Cathodic: {len(data_delta_cathodic)}, "
              f"Combined: {len(data_delta_combined)}, "
              f"OFF: {len(data_delta_estim_off)}")

    plt.suptitle(f'Psychometric Curves: Variant-Delta Pairs (by Polarity) - {isCorrectFieldName}',
                 fontsize=16, y=0.995)
    plt.show()


if __name__ == '__main__':
    main()