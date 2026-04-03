import sys
from pathlib import Path
import os
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

from matplotlib import pyplot as plt
from matplotlib.gridspec import GridSpec
import matplotlib.cm as cm
from PIL import Image
import xmltodict

from clat.compile.tstamp.cached_tstamp_fields import CachedFieldList
from clat.util import time_util
from clat.util.connection import Connection

from src.analysis.nafc.nafc_database_fields import (
    IsCorrectField, NoiseChanceField, NumRandDistractorsField,
    StimTypeField, ChoiceField, AnswerField, GenIdField,
    BaseMStickIdField, IsDeltaField, IsHypothesizedField,
    EStimEnabledField, EStimSpecIdField, EStimSpecField, EStimPolarityField
)
from src.analysis.nafc.psychometric_curves import collect_choice_trials, plot_psychometric_curve_on_ax
from src.startup import context


# ===========================================================================
# Permutation test utilities
# ===========================================================================

def calculate_p_value(observed_diff, permuted_diffs, test_side):
    if test_side == 'positive':
        return np.mean(permuted_diffs >= observed_diff)
    elif test_side == 'negative':
        return np.mean(permuted_diffs <= observed_diff)
    elif test_side == 'two-tailed':
        return np.mean(np.abs(permuted_diffs) >= np.abs(observed_diff))
    else:
        raise ValueError(f"Invalid test_side: {test_side}")


def run_permutation_test(data_for_perm, noise_levels, metric_field,
                         global_test_side, n_permutations=1000):
    data_for_perm = data_for_perm.copy()
    data_for_perm.loc[data_for_perm[metric_field] == "No Data", metric_field] = False
    data_for_perm[f'{metric_field}_bool'] = (data_for_perm[metric_field] == True)

    def calculate_sum_diff(data):
        sum_diff = 0
        level_diffs = {}
        for noise in noise_levels:
            noise_data = data[data['NoiseChance'] == noise]
            on = noise_data[noise_data['EStimEnabled'] == True]
            off = noise_data[noise_data['EStimEnabled'] == False]
            if len(on) > 0 and len(off) > 0:
                pct_on = 100 * on[f'{metric_field}_bool'].mean()
                pct_off = 100 * off[f'{metric_field}_bool'].mean()
                diff = pct_on - pct_off
                sum_diff += diff
                level_diffs[noise] = (pct_on, pct_off, diff, len(on), len(off))
        return sum_diff, level_diffs

    observed_sum, observed_level_diffs = calculate_sum_diff(data_for_perm)

    permuted_sums = []
    permuted_level_diffs = {noise: [] for noise in noise_levels}

    for _ in range(n_permutations):
        perm_data = data_for_perm.copy()
        for noise in noise_levels:
            mask = perm_data['NoiseChance'] == noise
            idx = perm_data[mask].index
            if len(idx) > 0:
                perm_data.loc[idx, 'EStimEnabled'] = (
                    perm_data.loc[idx, 'EStimEnabled'].sample(frac=1).values
                )
        perm_sum, perm_level_dict = calculate_sum_diff(perm_data)
        permuted_sums.append(perm_sum)
        for noise, (_, _, diff, _, _) in perm_level_dict.items():
            permuted_level_diffs[noise].append(diff)

    permuted_sums = np.array(permuted_sums)
    overall_p = calculate_p_value(observed_sum, permuted_sums, global_test_side)

    def sig_stars(p):
        if p < 0.001: return "***"
        if p < 0.01:  return "**"
        if p < 0.05:  return "*"
        return "ns"

    overall_sig = sig_stars(overall_p)

    for noise in list(observed_level_diffs.keys()):
        pct_on, pct_off, diff, n_on, n_off = observed_level_diffs[noise]
        perm_diffs = np.array(permuted_level_diffs[noise])
        p = calculate_p_value(diff, perm_diffs, global_test_side)
        observed_level_diffs[noise] = (pct_on, pct_off, diff, n_on, n_off, p, sig_stars(p))

    return observed_sum, overall_p, overall_sig, observed_level_diffs, permuted_sums


# ===========================================================================
# Figure 1: EStimSpecId overview
# ===========================================================================

def plot_spec_id_panel(ax, stim_subset, estim_off_data, spec_ids, noise_levels,
                       metric_field, title, global_test_side, n_permutations=1000):
    """
    Plot psychometric curves for EStim OFF + each unique EStimSpecId,
    and return a stats text block.
    """
    if len(estim_off_data) > 0:
        plot_psychometric_curve_on_ax(
            estim_off_data, ax,
            title=title, show_n=True, num_rep_min=0,
            color='black', linestyle='--', linewidth=2,
            label=f'EStim OFF (n={len(estim_off_data)})',
            isCorrectColumnName=metric_field
        )

    colors = cm.tab10(np.linspace(0, 1, max(len(spec_ids), 1)))
    results_text = f"{title}\n{'=' * 50}\n\n"

    for color, spec_id in zip(colors, sorted(spec_ids)):
        spec_data = stim_subset[stim_subset['EStimSpecId'] == spec_id].copy()
        if len(spec_data) == 0:
            continue

        plot_psychometric_curve_on_ax(
            spec_data, ax,
            title=title, show_n=True, num_rep_min=0,
            color=color,
            label=f'SpecId={spec_id} (n={len(spec_data)})',
            isCorrectColumnName=metric_field
        )

        combined = pd.concat([spec_data, estim_off_data])
        results_text += f"SpecId={spec_id} vs OFF\n{'-' * 30}\n"

        if len(spec_data) > 0 and len(estim_off_data) > 0:
            np.random.seed(42)
            observed_sum, overall_p, overall_sig, level_diffs, _ = run_permutation_test(
                combined, noise_levels, metric_field, global_test_side, n_permutations
            )
            for noise in sorted(level_diffs.keys()):
                pct_on, pct_off, diff, n_on, n_off, p, sig = level_diffs[noise]
                results_text += f"  N{noise * 100:.0f}%: {diff:+.1f}% p={p:.3f}{sig}\n"
            results_text += f"  Overall: {observed_sum:+.1f}% p={overall_p:.4f} {overall_sig}\n\n"
        else:
            results_text += "  Insufficient data\n\n"

    ax.invert_xaxis()
    ax.set_ylim([0, 110])
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=7)

    return results_text


# ===========================================================================
# Figure 2: Variant-delta pairs helpers
# ===========================================================================

def get_variant_delta_pairs(ga_conn):
    ga_conn.execute("""
        SELECT variant_id, delta_id
        FROM IncludedDeltas
        WHERE included = TRUE
    """)
    return {int(v): int(d) for v, d in ga_conn.fetch_all()}


def get_stim_response_from_ga(ga_conn, stim_id):
    ga_conn.execute("SELECT response FROM StimGaInfo WHERE stim_id = %s", (stim_id,))
    result = ga_conn.fetch_one()
    return float(result) if result is not None else None


def get_all_ga_responses(ga_conn):
    ga_conn.execute("SELECT response FROM StimGaInfo WHERE response IS NOT NULL")
    return [float(r[0]) for r in ga_conn.fetch_all() if r is not None]


def get_thumbnail_path_for_stim(ga_conn, stim_id):
    ga_conn.execute("SELECT spec FROM StimSpec WHERE id = %s", (stim_id,))
    stim_spec_xml = ga_conn.fetch_one()
    if stim_spec_xml:
        path = xmltodict.parse(stim_spec_xml)['StimSpec']['path']
        if 'sftp:host=' in path:
            path = path[path.find('/home/'):]
        if path.endswith('.png'):
            thumbnail_path = path[:-4] + '_thumbnail.png'
            return thumbnail_path if os.path.exists(thumbnail_path) else path
    return None


def add_border_to_image(img, response_rate, min_val=0.0, max_val=100.0,
                        border_width=20, color_mode='intensity'):
    from PIL import ImageOps
    normalized = (response_rate - min_val) / (max_val - min_val) if min_val != max_val else 0.5
    normalized = max(0.0, min(1.0, normalized))
    if color_mode == 'intensity':
        border_color = (int(255 * normalized), 0, 0)
    else:
        if normalized >= 0.5:
            intensity = (normalized - 0.5) * 2
            border_color = (int(255 * intensity), 0, 0)
        else:
            intensity = (0.5 - normalized) * 2
            border_color = (0, 0, int(255 * intensity))
    return ImageOps.expand(img, border=border_width, fill=border_color)


def load_and_display_image(ax, image_path, response_rate=None, min_val=0.0, max_val=100.0,
                           border_width=20, color_mode='intensity'):
    try:
        if image_path and Path(image_path).exists():
            img = Image.open(image_path)
            if response_rate is not None:
                img = add_border_to_image(img, response_rate, min_val, max_val,
                                          border_width, color_mode)
            ax.imshow(img)
        else:
            ax.text(0.5, 0.5, 'Image not found', ha='center', va='center',
                    transform=ax.transAxes)
    except Exception:
        ax.text(0.5, 0.5, 'Error loading image', ha='center', va='center',
                transform=ax.transAxes)
    ax.axis('off')


# ===========================================================================
# Figure 2: Variant-delta pairs figure
# ===========================================================================

def plot_pairs_figure(data_exp, ga_conn, variant_to_delta,
                      global_min_response, global_max_response,
                      start_gen_id_estim_on, max_gen_id_estim_on,
                      isCorrectFieldName, add_borders, border_width, border_color_mode):
    """
    One row per variant-delta pair: [images] on top, [psychometric curves by EStimSpecId] below.
    """
    base_mstick_ids = sorted(int(x) for x in data_exp['BaseMStickId'].dropna().unique())
    variants_in_data = [bid for bid in base_mstick_ids if bid in variant_to_delta]

    if not variants_in_data:
        print("No variant-delta pairs found in behavioral data — skipping pairs figure.")
        return

    n_rows = len(variants_in_data)
    fig = plt.figure(figsize=(12, 6 * n_rows))
    gs = GridSpec(n_rows * 2, 2, figure=fig,
                  height_ratios=[1, 2] * n_rows, hspace=1.0, wspace=0.3)

    for pair_idx, variant_id in enumerate(variants_in_data):
        delta_id = variant_to_delta[variant_id]
        row_start = pair_idx * 2

        variant_thumb = get_thumbnail_path_for_stim(ga_conn, variant_id)
        delta_thumb   = get_thumbnail_path_for_stim(ga_conn, delta_id)
        variant_response = get_stim_response_from_ga(ga_conn, variant_id) if add_borders else None
        delta_response   = get_stim_response_from_ga(ga_conn, delta_id)   if add_borders else None

        # --- Images ---
        ax_vimg = fig.add_subplot(gs[row_start, 0])
        ax_dimg = fig.add_subplot(gs[row_start, 1])

        load_and_display_image(ax_vimg, variant_thumb, variant_response,
                               global_min_response, global_max_response,
                               border_width, border_color_mode)
        vtitle = f'Variant: {variant_id}'
        if variant_response is not None:
            vtitle += f'\nResponse: {variant_response:.3f}'
        ax_vimg.set_title(vtitle, fontsize=10, fontweight='bold')

        load_and_display_image(ax_dimg, delta_thumb, delta_response,
                               global_min_response, global_max_response,
                               border_width, border_color_mode)
        dtitle = f'Delta: {delta_id}'
        if delta_response is not None:
            dtitle += f'\nResponse: {delta_response:.3f}'
        ax_dimg.set_title(dtitle, fontsize=10, fontweight='bold')

        # --- Psychometric curves ---
        ax_v = fig.add_subplot(gs[row_start + 1, 0])
        ax_d = fig.add_subplot(gs[row_start + 1, 1])

        for stim_id, ax, label_prefix in [
            (variant_id, ax_v, 'Variant'),
            (delta_id,   ax_d, 'Delta'),
        ]:
            stim_data = data_exp[data_exp['BaseMStickId'] == stim_id].copy()
            on = stim_data[
                (stim_data['EStimEnabled'] == True) &
                (stim_data['GenId'] >= start_gen_id_estim_on) &
                (stim_data['GenId'] <= max_gen_id_estim_on)
            ]
            off = stim_data[stim_data['EStimEnabled'] == False]

            # EStim OFF baseline
            if len(off) > 0:
                plot_psychometric_curve_on_ax(
                    off, ax,
                    title=f'{label_prefix} {stim_id}',
                    show_n=True, num_rep_min=0,
                    color='black', linestyle='--', linewidth=2,
                    label=f'EStim OFF (n={len(off)})',
                    isCorrectColumnName=isCorrectFieldName
                )

            # One curve per EStimSpecId
            spec_ids = on['EStimSpecId'].dropna().unique()
            colors = cm.tab10(np.linspace(0, 1, max(len(spec_ids), 1)))
            for color, spec_id in zip(colors, sorted(spec_ids)):
                spec_data = on[on['EStimSpecId'] == spec_id]
                if len(spec_data) > 0:
                    plot_psychometric_curve_on_ax(
                        spec_data, ax,
                        title=f'{label_prefix} {stim_id}',
                        show_n=True, num_rep_min=0,
                        color=color,
                        label=f'SpecId={spec_id} (n={len(spec_data)})',
                        isCorrectColumnName=isCorrectFieldName
                    )

            ax.invert_xaxis()
            ax.set_ylim([0, 110])
            ax.grid(True, alpha=0.3)
            ax.legend(fontsize=8)

        print(f"Pair {pair_idx + 1}: Variant {variant_id} & Delta {delta_id}")

    fig.suptitle(
        f'Psychometric Curves: Variant-Delta Pairs (by EStimSpecId) — {isCorrectFieldName}',
        fontsize=16, y=0.995
    )


# ===========================================================================
# Main
# ===========================================================================

def main():
    # ============ CONFIGURATION ============
    exp_conn = Connection("allen_estimshape_exp_260402_0")
    ga_conn  = Connection(context.ga_database)

    since_date            = time_util.from_date_to_now(2024, 7, 10)
    start_gen_id          = 2
    max_gen_id            = float('inf')
    start_gen_id_estim_on = 0
    max_gen_id_estim_on   = float('inf')

    isCorrectFieldName = "IsHypothesized"  # "IsCorrect" or "IsHypothesized"
    global_test_side   = 'two-tailed'
    n_permutations     = 1000

    # Border settings for the pairs figure
    add_borders       = True
    border_width      = 20
    border_color_mode = 'intensity'   # 'intensity' or 'divergent'
    # =======================================

    # GA response range for borders
    all_ga_responses = get_all_ga_responses(ga_conn)
    if all_ga_responses:
        global_min_response = min(all_ga_responses)
        global_max_response = max(all_ga_responses)
        print(f"GA Response range: {global_min_response:.2f} to {global_max_response:.2f}")
    else:
        global_min_response, global_max_response = 0.0, 1.0
        print("Warning: No GA responses found, using default range [0, 1]")

    variant_to_delta = get_variant_delta_pairs(ga_conn)
    print(f"Found {len(variant_to_delta)} variant-delta pairs")

    # Collect behavioral data
    trial_tstamps = collect_choice_trials(exp_conn, since_date)

    fields = CachedFieldList()
    fields.append(IsCorrectField(exp_conn))
    fields.append(IsHypothesizedField(exp_conn))
    fields.append(NoiseChanceField(exp_conn))
    fields.append(NumRandDistractorsField(exp_conn))
    fields.append(StimTypeField(exp_conn))
    fields.append(ChoiceField(exp_conn))
    fields.append(GenIdField(exp_conn))
    fields.append(EStimEnabledField(exp_conn))
    fields.append(EStimSpecIdField(exp_conn))
    fields.append(BaseMStickIdField(exp_conn))
    fields.append(IsDeltaField(exp_conn))
    fields.append(EStimPolarityField(exp_conn))

    data = fields.to_data(trial_tstamps)
    data = data[(data['GenId'] >= start_gen_id) & (data['GenId'] <= max_gen_id)]
    data_exp = data[data['StimType'] == 'EStimShapeVariantsDeltaNAFCStim']

    data_delta   = data_exp[data_exp['IsDelta'] == True].copy()
    data_variant = data_exp[data_exp['IsDelta'] == False].copy()

    def estim_on(df):
        return df[
            (df['EStimEnabled'] == True) &
            (df['GenId'] >= start_gen_id_estim_on) &
            (df['GenId'] <= max_gen_id_estim_on)
        ].copy()

    data_delta_on    = estim_on(data_delta)
    data_delta_off   = data_delta[data_delta['EStimEnabled'] == False].copy()
    data_variant_on  = estim_on(data_variant)
    data_variant_off = data_variant[data_variant['EStimEnabled'] == False].copy()

    delta_spec_ids   = data_delta_on['EStimSpecId'].dropna().unique()
    variant_spec_ids = data_variant_on['EStimSpecId'].dropna().unique()

    noise_levels = sorted(data_exp['NoiseChance'].unique())
    metric_name  = "ACCURACY" if isCorrectFieldName == "IsCorrect" else "% HYPOTHESIZED"

    # ---- Figure 1: EStimSpecId overview ----
    fig1, axes = plt.subplots(1, 3, figsize=(22, 7),
                              gridspec_kw={'width_ratios': [2, 2, 3]})

    delta_stats = plot_spec_id_panel(
        axes[0], data_delta_on, data_delta_off,
        delta_spec_ids, noise_levels, isCorrectFieldName,
        title=f'{metric_name}: Delta by EStimSpecId',
        global_test_side=global_test_side, n_permutations=n_permutations
    )
    variant_stats = plot_spec_id_panel(
        axes[1], data_variant_on, data_variant_off,
        variant_spec_ids, noise_levels, isCorrectFieldName,
        title=f'{metric_name}: Variant by EStimSpecId',
        global_test_side=global_test_side, n_permutations=n_permutations
    )

    full_stats = (
        f"PERMUTATION TEST ({global_test_side})\n"
        f"n_permutations={n_permutations}  metric={isCorrectFieldName}\n"
        f"{'=' * 50}\n\n"
        + delta_stats + "\n" + variant_stats
        + "\n* p<0.05, ** p<0.01, *** p<0.001"
    )
    axes[2].text(0.02, 0.98, full_stats,
                 transform=axes[2].transAxes, fontsize=6,
                 verticalalignment='top', fontfamily='monospace',
                 bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    axes[2].axis('off')

    fig1.tight_layout()
    fig1.suptitle(f'{metric_name} by EStimSpecId — {isCorrectFieldName}', fontsize=14, y=1.02)

    # ---- Figure 2: Variant-delta pairs ----
    plot_pairs_figure(
        data_exp, ga_conn, variant_to_delta,
        global_min_response, global_max_response,
        start_gen_id_estim_on, max_gen_id_estim_on,
        isCorrectFieldName, add_borders, border_width, border_color_mode
    )

    plt.show()


if __name__ == '__main__':
    main()