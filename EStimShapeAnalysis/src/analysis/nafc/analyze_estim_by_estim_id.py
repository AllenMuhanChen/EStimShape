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
    EStimEnabledField, EStimSpecIdField, EStimSpecField, EStimPolarityField, SampleLengthField
)
from src.analysis.nafc.psychometric_curves import collect_choice_trials, plot_psychometric_curve_on_ax
from src.startup import context



# ===========================================================================
# Main
# ===========================================================================

def main():
    # ============ CONFIGURATION ============
    exp_db_name = "allen_estimshape_exp_260423_0"
    exp_conn = Connection(exp_db_name)
    ga_conn  = Connection(context.ga_database)

    since_date            = time_util.from_date_to_now(2024, 7, 10)
    start_gen_id          = 3
    max_gen_id            = 6
    start_gen_id_estim_on = 0
    max_gen_id_estim_on   = float('inf')

    isCorrectFieldName = "IsHypothesized"
    global_test_side   = 'two-tailed'
    n_permutations     = 1000

    add_borders       = True
    border_width      = 20
    border_color_mode = 'intensity'

    # --- Optional filtering & combining ---
    # SpecIds: None = include all; list = include only those EStimSpecId values
    include_spec_ids       = [1,2] # e.g. [1, 3]
    # combine_spec_ids: True = pool all (filtered) SpecIds into one curve
    combine_spec_ids       = True
    # NoiseLevels: None = include all; list = include only those NoiseChance values
    include_noise_chances  = None   # e.g. [0.2, 0.4]
    # combine_noise_chances: True = pool all selected noise levels into one aggregate point
    combine_noise_chances  = False
    # SampleLengths: None = include all; list = include only those SampleLength values
    include_sample_lengths = None  # e.g. [0.5]
    # combine_sample_lengths: True = suppress per-SL stratification (treat all as one pool)
    combine_sample_lengths = False
    # stim_group_mode controls the Delta/Variant axis:
    #   'both'     — separate Delta and Variant columns (current default)
    #   'delta'    — show only Delta
    #   'variant'  — show only Variant
    #   'combined' — merge Delta + Variant into a single pool (one column, not two)
    stim_group_mode        = 'variant'
    # =======================================

    session_id = exp_db_name.split("allen_estimshape_exp_")[-1]

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

    trial_tstamps = collect_choice_trials(exp_conn, since_date)

    if trial_tstamps:
        first_task_id          = min([trial_tstamp.start for trial_tstamp in trial_tstamps])
        most_recent_task_id    = max([trial_tstamp.start for trial_tstamp in trial_tstamps])
        task_range             = f"{first_task_id}_{most_recent_task_id}"
    else:
        task_range = "no_trials"
    save_path = f"/home/connorlab/Documents/plots/{session_id}/estim/{task_range}_estim_results.png"
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

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
    fields.append(ChoiceField(exp_conn))
    fields.append(SampleLengthField(exp_conn))

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

    if include_sample_lengths is not None:
        sl_set = set(include_sample_lengths)
        data_delta_on    = data_delta_on[data_delta_on['SampleLength'].isin(sl_set)].copy()
        data_delta_off   = data_delta_off[data_delta_off['SampleLength'].isin(sl_set)].copy()
        data_variant_on  = data_variant_on[data_variant_on['SampleLength'].isin(sl_set)].copy()
        data_variant_off = data_variant_off[data_variant_off['SampleLength'].isin(sl_set)].copy()

    delta_spec_ids   = data_delta_on['EStimSpecId'].dropna().unique()
    variant_spec_ids = data_variant_on['EStimSpecId'].dropna().unique()

    if include_spec_ids is not None:
        spec_id_set      = set(include_spec_ids)
        delta_spec_ids   = [s for s in delta_spec_ids   if s in spec_id_set]
        variant_spec_ids = [s for s in variant_spec_ids if s in spec_id_set]

    noise_levels = sorted(data_exp['NoiseChance'].unique())

    if include_noise_chances is not None:
        nc_set = set(include_noise_chances)
        noise_levels = [n for n in noise_levels if n in nc_set]
        data_delta_on    = data_delta_on[data_delta_on['NoiseChance'].isin(nc_set)].copy()
        data_delta_off   = data_delta_off[data_delta_off['NoiseChance'].isin(nc_set)].copy()
        data_variant_on  = data_variant_on[data_variant_on['NoiseChance'].isin(nc_set)].copy()
        data_variant_off = data_variant_off[data_variant_off['NoiseChance'].isin(nc_set)].copy()

    if combine_noise_chances and noise_levels:
        combined_nc = float(np.mean(noise_levels))
        for df in [data_delta_on, data_delta_off, data_variant_on, data_variant_off]:
            df['NoiseChance'] = combined_nc
        noise_levels = [combined_nc]

    metric_name  = "ACCURACY" if isCorrectFieldName == "IsCorrect" else "% HYPOTHESIZED"

    # ---- Figure 1: combined metrics ----
    row_labels = [
        (metric_name,                   isCorrectFieldName, plot_spec_id_panel),
        ('% Rand Choice',               None,               plot_rand_choice_panel),
        (f'% Hypothesized (rand-excl)', isCorrectFieldName, plot_rand_excluded_panel),
    ]

    def _call_panel(panel_fn, ax, data_on, data_off, spec_ids, noise_levels, metric_field, title):
        kwargs = dict(title=title, global_test_side=global_test_side,
                      n_permutations=n_permutations, combine_sample_lengths=combine_sample_lengths,
                      combine_spec_ids=combine_spec_ids)
        if metric_field is not None:
            return panel_fn(ax, data_on, data_off, spec_ids, noise_levels, metric_field, **kwargs)
        else:
            return panel_fn(ax, data_on, data_off, spec_ids, noise_levels, **kwargs)

    if stim_group_mode == 'both':
        fig1 = plt.figure(figsize=(22, 21))
        gs1 = GridSpec(3, 3, figure=fig1, width_ratios=[2, 2, 3], hspace=0.45, wspace=0.3)

        for row, (row_title, metric_field, panel_fn) in enumerate(row_labels):
            ax_delta   = fig1.add_subplot(gs1[row, 0])
            ax_variant = fig1.add_subplot(gs1[row, 1])
            ax_stats   = fig1.add_subplot(gs1[row, 2])

            delta_stats   = _call_panel(panel_fn, ax_delta,   data_delta_on,   data_delta_off,
                                        delta_spec_ids,   noise_levels, metric_field,
                                        title=f'{row_title}: Delta')
            variant_stats = _call_panel(panel_fn, ax_variant, data_variant_on, data_variant_off,
                                        variant_spec_ids, noise_levels, metric_field,
                                        title=f'{row_title}: Variant')

            stats_text = (
                f"{row_title.upper()} — PERMUTATION TEST ({global_test_side})\n"
                f"n_permutations={n_permutations}\n"
                f"{'=' * 45}\n\n"
                + delta_stats + "\n" + variant_stats
                + "\n* p<0.05, ** p<0.01, *** p<0.001"
            )
            ax_stats.text(0.02, 0.98, stats_text,
                          transform=ax_stats.transAxes, fontsize=6,
                          verticalalignment='top', fontfamily='monospace',
                          bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
            ax_stats.axis('off')

    else:
        # Single-column mode: delta, variant, or combined
        if stim_group_mode == 'delta':
            grp_on, grp_off, grp_spec_ids, grp_label = (
                data_delta_on, data_delta_off, delta_spec_ids, 'Delta'
            )
        elif stim_group_mode == 'variant':
            grp_on, grp_off, grp_spec_ids, grp_label = (
                data_variant_on, data_variant_off, variant_spec_ids, 'Variant'
            )
        else:  # 'combined'
            grp_on  = pd.concat([data_delta_on,  data_variant_on],  ignore_index=True)
            grp_off = pd.concat([data_delta_off, data_variant_off], ignore_index=True)
            grp_spec_ids = list(set(list(delta_spec_ids) + list(variant_spec_ids)))
            grp_label = 'Combined'

        fig1 = plt.figure(figsize=(14, 21))
        gs1 = GridSpec(3, 2, figure=fig1, width_ratios=[2, 3], hspace=0.45, wspace=0.3)

        for row, (row_title, metric_field, panel_fn) in enumerate(row_labels):
            ax_stim  = fig1.add_subplot(gs1[row, 0])
            ax_stats = fig1.add_subplot(gs1[row, 1])

            grp_stats = _call_panel(panel_fn, ax_stim, grp_on, grp_off, grp_spec_ids,
                                    noise_levels, metric_field,
                                    title=f'{row_title}: {grp_label}')

            stats_text = (
                f"{row_title.upper()} — PERMUTATION TEST ({global_test_side})\n"
                f"n_permutations={n_permutations}\n"
                f"{'=' * 45}\n\n"
                + grp_stats
                + "\n* p<0.05, ** p<0.01, *** p<0.001"
            )
            ax_stats.text(0.02, 0.98, stats_text,
                          transform=ax_stats.transAxes, fontsize=6,
                          verticalalignment='top', fontfamily='monospace',
                          bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
            ax_stats.axis('off')

    fig1.suptitle(f'EStimSpecId Analysis — {isCorrectFieldName}', fontsize=15, y=1.01)

    # ---- Figure 2: Variant-delta pairs ----
    pairs_fig = plot_pairs_figure(
        data_exp, ga_conn, variant_to_delta,
        global_min_response, global_max_response,
        start_gen_id_estim_on, max_gen_id_estim_on,
        isCorrectFieldName, add_borders, border_width, border_color_mode
    )

    fig1.savefig(save_path.replace("_estim_results.png", "_overview_estim_results.png"),
                 bbox_inches='tight', dpi=150)
    if pairs_fig is not None:
        pairs_fig.savefig(save_path.replace("_estim_results.png", "_pairs_estim_results.png"),
                          bbox_inches='tight', dpi=150)
    print(f"Saved plots to {os.path.dirname(save_path)}")

    plt.show()


# ===========================================================================
# SampleLength scatter overlay
# ===========================================================================

_SL_SHAPES = ['o', 's', '^', 'D', 'v', 'P', '*', 'X']


def get_sl_marker_map(full_df):
    """Build a consistent SampleLength -> marker mapping from the full dataset."""
    sample_lengths = sorted(full_df['SampleLength'].dropna().unique(), key=str)
    if len(sample_lengths) <= 1:
        return None
    return {sl: _SL_SHAPES[i % len(_SL_SHAPES)] for i, sl in enumerate(sample_lengths)}


def scatter_by_sample_length(ax, df, metric_field, noise_levels, color='black',
                             label_prefix='', sl_marker_map=None):
    """Overlay per-noise-level dots with marker shape keyed to SampleLength for ONE curve."""
    if sl_marker_map is None:
        return

    df = df.copy()
    df.loc[df[metric_field] == "No Data", metric_field] = False
    df[f'{metric_field}_bool'] = (df[metric_field] == True)

    for sl, marker in sl_marker_map.items():
        sl_data = df[df['SampleLength'] == sl]
        xs, ys, ns = [], [], []
        for noise in noise_levels:
            nd = sl_data[sl_data['NoiseChance'] == noise]
            if len(nd) > 0:
                xs.append(noise)
                ys.append(100 * nd[f'{metric_field}_bool'].mean())
                ns.append(len(nd))
        if xs:
            ax.scatter(xs, ys, marker=marker, s=60, edgecolors=color,
                       facecolors='none', linewidths=1.5, zorder=5,
                       label=f'{label_prefix} SL={sl}')
            for x, y, n in zip(xs, ys, ns):
                ax.text(x, y + 2.5, str(n), ha='center', va='bottom',
                        fontsize=5, color=color, zorder=6)


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
# Per-SampleLength permutation test wrapper
# ===========================================================================

def run_per_sample_length_stats(spec_data, off_data, noise_levels, metric_field,
                                global_test_side, n_permutations):
    """Run permutation test separately for each unique SampleLength present in both groups."""
    all_data = pd.concat([spec_data, off_data])
    sample_lengths = sorted(all_data['SampleLength'].dropna().unique(), key=str)
    if len(sample_lengths) <= 1:
        return ""

    text = ""
    for sl in sample_lengths:
        on_sl = spec_data[spec_data['SampleLength'] == sl]
        off_sl = off_data[off_data['SampleLength'] == sl]
        if len(on_sl) == 0 or len(off_sl) == 0:
            text += f"    SL={sl}: insufficient data\n"
            continue
        combined_sl = pd.concat([on_sl, off_sl])
        np.random.seed(42)
        obs, p, sig, level_diffs, _ = run_permutation_test(
            combined_sl, noise_levels, metric_field, global_test_side, n_permutations
        )
        text += f"    SL={sl} (n_on={len(on_sl)}, n_off={len(off_sl)}): {obs:+.1f}% p={p:.4f} {sig}\n"
        for noise in sorted(level_diffs.keys()):
            pct_on, pct_off, diff, n_on, n_off, lp, lsig = level_diffs[noise]
            text += f"      N{noise*100:.0f}%: {diff:+.1f}% p={lp:.3f}{lsig}\n"
    return text


# ===========================================================================
# Figure 1: EStimSpecId overview
# ===========================================================================

def plot_spec_id_panel(ax, stim_subset, estim_off_data, spec_ids, noise_levels,
                       metric_field, title, global_test_side, n_permutations=1000,
                       combine_sample_lengths=False, combine_spec_ids=False):
    sl_map = None if combine_sample_lengths else get_sl_marker_map(pd.concat([stim_subset, estim_off_data]))

    if len(estim_off_data) > 0:
        plot_psychometric_curve_on_ax(
            estim_off_data, ax,
            title=title, show_n=True, num_rep_min=0,
            color='black', linestyle='--', linewidth=2, marker='o',
            label=f'EStim OFF (n={len(estim_off_data)})',
            isCorrectColumnName=metric_field
        )
        scatter_by_sample_length(ax, estim_off_data, metric_field, noise_levels,
                                 color='black', label_prefix='OFF', sl_marker_map=sl_map)

    results_text = f"{title}\n{'=' * 50}\n\n"

    if combine_spec_ids:
        spec_data = stim_subset[stim_subset['EStimSpecId'].isin(spec_ids)].copy()
        label = f'All SpecIds combined (n={len(spec_data)})'
        if len(spec_data) > 0:
            plot_psychometric_curve_on_ax(
                spec_data, ax,
                title=title, show_n=True, num_rep_min=0,
                color='tab:blue', marker='o', label=label,
                isCorrectColumnName=metric_field
            )
            scatter_by_sample_length(ax, spec_data, metric_field, noise_levels,
                                     color='tab:blue', label_prefix='Combined', sl_marker_map=sl_map)
            combined = pd.concat([spec_data, estim_off_data])
            results_text += f"All SpecIds combined vs OFF\n{'-' * 30}\n"
            if len(estim_off_data) > 0:
                np.random.seed(42)
                observed_sum, overall_p, overall_sig, level_diffs, _ = run_permutation_test(
                    combined, noise_levels, metric_field, global_test_side, n_permutations
                )
                for noise in sorted(level_diffs.keys()):
                    pct_on, pct_off, diff, n_on, n_off, p, sig = level_diffs[noise]
                    results_text += f"  N{noise * 100:.0f}%: {diff:+.1f}% p={p:.3f}{sig}\n"
                results_text += f"  Overall: {observed_sum:+.1f}% p={overall_p:.4f} {overall_sig}\n"
                if not combine_sample_lengths:
                    sl_text = run_per_sample_length_stats(
                        spec_data, estim_off_data, noise_levels, metric_field,
                        global_test_side, n_permutations
                    )
                    if sl_text:
                        results_text += f"  By SampleLength:\n{sl_text}"
                results_text += "\n"
            else:
                results_text += "  Insufficient data\n\n"
    else:
        colors = cm.tab10(np.linspace(0, 1, max(len(spec_ids), 1)))
        for color, spec_id in zip(colors, sorted(spec_ids)):
            spec_data = stim_subset[stim_subset['EStimSpecId'] == spec_id].copy()
            if len(spec_data) == 0:
                continue

            plot_psychometric_curve_on_ax(
                spec_data, ax,
                title=title, show_n=True, num_rep_min=0,
                color=color, marker='o',
                label=f'SpecId={spec_id} (n={len(spec_data)})',
                isCorrectColumnName=metric_field
            )
            scatter_by_sample_length(ax, spec_data, metric_field, noise_levels,
                                     color=color, label_prefix=f'Spec{spec_id}',
                                     sl_marker_map=sl_map)

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
                results_text += f"  Overall: {observed_sum:+.1f}% p={overall_p:.4f} {overall_sig}\n"
                if not combine_sample_lengths:
                    sl_text = run_per_sample_length_stats(
                        spec_data, estim_off_data, noise_levels, metric_field,
                        global_test_side, n_permutations
                    )
                    if sl_text:
                        results_text += f"  By SampleLength:\n{sl_text}"
                results_text += "\n"
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
    base_mstick_ids = sorted(int(x) for x in data_exp['BaseMStickId'].dropna().unique())
    variants_in_data = [bid for bid in base_mstick_ids if bid in variant_to_delta]

    if not variants_in_data:
        print("No variant-delta pairs found in behavioral data — skipping pairs figure.")
        return None

    noise_levels = sorted(data_exp['NoiseChance'].unique())

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

            sl_map = get_sl_marker_map(pd.concat([on, off]))

            if len(off) > 0:
                plot_psychometric_curve_on_ax(
                    off, ax,
                    title=f'{label_prefix} {stim_id}',
                    show_n=True, num_rep_min=0,
                    color='black', linestyle='--', linewidth=2, marker='o',
                    label=f'EStim OFF (n={len(off)})',
                    isCorrectColumnName=isCorrectFieldName
                )
                scatter_by_sample_length(ax, off, isCorrectFieldName, noise_levels,
                                         color='black', label_prefix='OFF', sl_marker_map=sl_map)

            spec_ids = on['EStimSpecId'].dropna().unique()
            colors = cm.tab10(np.linspace(0, 1, max(len(spec_ids), 1)))
            for color, spec_id in zip(colors, sorted(spec_ids)):
                spec_data = on[on['EStimSpecId'] == spec_id]
                if len(spec_data) > 0:
                    plot_psychometric_curve_on_ax(
                        spec_data, ax,
                        title=f'{label_prefix} {stim_id}',
                        show_n=True, num_rep_min=0,
                        color=color, marker='o',
                        label=f'SpecId={spec_id} (n={len(spec_data)})',
                        isCorrectColumnName=isCorrectFieldName
                    )
                    scatter_by_sample_length(ax, spec_data, isCorrectFieldName, noise_levels,
                                             color=color, label_prefix=f'Spec{spec_id}',
                                             sl_marker_map=sl_map)

            ax.invert_xaxis()
            ax.set_ylim([0, 110])
            ax.grid(True, alpha=0.3)
            ax.legend(fontsize=8)

        print(f"Pair {pair_idx + 1}: Variant {variant_id} & Delta {delta_id}")

    fig.suptitle(
        f'Psychometric Curves: Variant-Delta Pairs (by EStimSpecId) — {isCorrectFieldName}',
        fontsize=16, y=0.995
    )
    return fig


# ===========================================================================
# Figure 3: % Rand choice by EStimSpecId
# ===========================================================================

def plot_rand_choice_panel(ax, stim_subset, estim_off_data, spec_ids, noise_levels,
                           title, global_test_side, n_permutations=1000,
                           combine_sample_lengths=False, combine_spec_ids=False):
    METRIC = 'IsRand'

    def inject_is_rand(df):
        d = df.copy()
        d[METRIC] = d['Choice'] == 'rand'
        return d

    off_data = inject_is_rand(estim_off_data)
    on_data  = inject_is_rand(stim_subset)

    sl_map = None if combine_sample_lengths else get_sl_marker_map(pd.concat([on_data, off_data]))

    if len(off_data) > 0:
        plot_psychometric_curve_on_ax(
            off_data, ax,
            title=title, show_n=True, num_rep_min=0,
            color='black', linestyle='--', linewidth=2, marker='o',
            label=f'EStim OFF (n={len(off_data)})',
            isCorrectColumnName=METRIC
        )
        scatter_by_sample_length(ax, off_data, METRIC, noise_levels,
                                 color='black', label_prefix='OFF', sl_marker_map=sl_map)

    results_text = f"{title}\n{'=' * 50}\n\n"

    if combine_spec_ids:
        spec_data = on_data[on_data['EStimSpecId'].isin(spec_ids)].copy()
        if len(spec_data) > 0:
            plot_psychometric_curve_on_ax(
                spec_data, ax,
                title=title, show_n=True, num_rep_min=0,
                color='tab:blue', marker='o',
                label=f'All SpecIds combined (n={len(spec_data)})',
                isCorrectColumnName=METRIC
            )
            scatter_by_sample_length(ax, spec_data, METRIC, noise_levels,
                                     color='tab:blue', label_prefix='Combined', sl_marker_map=sl_map)
            combined = pd.concat([spec_data, off_data])
            results_text += f"All SpecIds combined vs OFF\n{'-' * 30}\n"
            if len(off_data) > 0:
                np.random.seed(42)
                observed_sum, overall_p, overall_sig, level_diffs, _ = run_permutation_test(
                    combined, noise_levels, METRIC, global_test_side, n_permutations
                )
                for noise in sorted(level_diffs.keys()):
                    pct_on, pct_off, diff, n_on, n_off, p, sig = level_diffs[noise]
                    results_text += f"  N{noise * 100:.0f}%: {diff:+.1f}% p={p:.3f}{sig}\n"
                results_text += f"  Overall: {observed_sum:+.1f}% p={overall_p:.4f} {overall_sig}\n"
                if not combine_sample_lengths:
                    sl_text = run_per_sample_length_stats(
                        spec_data, off_data, noise_levels, METRIC,
                        global_test_side, n_permutations
                    )
                    if sl_text:
                        results_text += f"  By SampleLength:\n{sl_text}"
                results_text += "\n"
            else:
                results_text += "  Insufficient data\n\n"
    else:
        colors = cm.tab10(np.linspace(0, 1, max(len(spec_ids), 1)))
        for color, spec_id in zip(colors, sorted(spec_ids)):
            spec_data = on_data[on_data['EStimSpecId'] == spec_id].copy()
            if len(spec_data) == 0:
                continue

            plot_psychometric_curve_on_ax(
                spec_data, ax,
                title=title, show_n=True, num_rep_min=0,
                color=color, marker='o',
                label=f'SpecId={spec_id} (n={len(spec_data)})',
                isCorrectColumnName=METRIC
            )
            scatter_by_sample_length(ax, spec_data, METRIC, noise_levels,
                                     color=color, label_prefix=f'Spec{spec_id}',
                                     sl_marker_map=sl_map)

            combined = pd.concat([spec_data, off_data])
            results_text += f"SpecId={spec_id} vs OFF\n{'-' * 30}\n"

            if len(spec_data) > 0 and len(off_data) > 0:
                np.random.seed(42)
                observed_sum, overall_p, overall_sig, level_diffs, _ = run_permutation_test(
                    combined, noise_levels, METRIC, global_test_side, n_permutations
                )
                for noise in sorted(level_diffs.keys()):
                    pct_on, pct_off, diff, n_on, n_off, p, sig = level_diffs[noise]
                    results_text += f"  N{noise * 100:.0f}%: {diff:+.1f}% p={p:.3f}{sig}\n"
                results_text += f"  Overall: {observed_sum:+.1f}% p={overall_p:.4f} {overall_sig}\n"
                if not combine_sample_lengths:
                    sl_text = run_per_sample_length_stats(
                        spec_data, off_data, noise_levels, METRIC,
                        global_test_side, n_permutations
                    )
                    if sl_text:
                        results_text += f"  By SampleLength:\n{sl_text}"
                results_text += "\n"
            else:
                results_text += "  Insufficient data\n\n"

    ax.invert_xaxis()
    ax.set_ylim([0, 110])
    ax.set_ylabel('% Chose Rand')
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=7)

    return results_text


# ===========================================================================
# Figure 4: % Hypothesized (rand-excluded) by EStimSpecId
# ===========================================================================

def plot_rand_excluded_panel(ax, stim_subset, estim_off_data, spec_ids, noise_levels,
                             metric_field, title, global_test_side, n_permutations=1000,
                             combine_sample_lengths=False, combine_spec_ids=False):
    def drop_rand(df):
        return df[df['Choice'] != 'rand'].copy()

    off_data = drop_rand(estim_off_data)
    on_data  = drop_rand(stim_subset)

    sl_map = None if combine_sample_lengths else get_sl_marker_map(pd.concat([on_data, off_data]))

    if len(off_data) > 0:
        plot_psychometric_curve_on_ax(
            off_data, ax,
            title=title, show_n=True, num_rep_min=0,
            color='black', linestyle='--', linewidth=2, marker='o',
            label=f'EStim OFF (n={len(off_data)})',
            isCorrectColumnName=metric_field
        )
        scatter_by_sample_length(ax, off_data, metric_field, noise_levels,
                                 color='black', label_prefix='OFF', sl_marker_map=sl_map)

    results_text = f"{title}\n{'=' * 50}\n\n"

    if combine_spec_ids:
        spec_data = on_data[on_data['EStimSpecId'].isin(spec_ids)].copy()
        if len(spec_data) > 0:
            plot_psychometric_curve_on_ax(
                spec_data, ax,
                title=title, show_n=True, num_rep_min=0,
                color='tab:blue', marker='o',
                label=f'All SpecIds combined (n={len(spec_data)})',
                isCorrectColumnName=metric_field
            )
            scatter_by_sample_length(ax, spec_data, metric_field, noise_levels,
                                     color='tab:blue', label_prefix='Combined', sl_marker_map=sl_map)
            combined = pd.concat([spec_data, off_data])
            results_text += f"All SpecIds combined vs OFF\n{'-' * 30}\n"
            if len(off_data) > 0:
                np.random.seed(42)
                observed_sum, overall_p, overall_sig, level_diffs, _ = run_permutation_test(
                    combined, noise_levels, metric_field, global_test_side, n_permutations
                )
                for noise in sorted(level_diffs.keys()):
                    pct_on, pct_off, diff, n_on, n_off, p, sig = level_diffs[noise]
                    results_text += f"  N{noise * 100:.0f}%: {diff:+.1f}% p={p:.3f}{sig}\n"
                results_text += f"  Overall: {observed_sum:+.1f}% p={overall_p:.4f} {overall_sig}\n"
                if not combine_sample_lengths:
                    sl_text = run_per_sample_length_stats(
                        spec_data, off_data, noise_levels, metric_field,
                        global_test_side, n_permutations
                    )
                    if sl_text:
                        results_text += f"  By SampleLength:\n{sl_text}"
                results_text += "\n"
            else:
                results_text += "  Insufficient data\n\n"
    else:
        colors = cm.tab10(np.linspace(0, 1, max(len(spec_ids), 1)))
        for color, spec_id in zip(colors, sorted(spec_ids)):
            spec_data = on_data[on_data['EStimSpecId'] == spec_id].copy()
            if len(spec_data) == 0:
                continue

            plot_psychometric_curve_on_ax(
                spec_data, ax,
                title=title, show_n=True, num_rep_min=0,
                color=color, marker='o',
                label=f'SpecId={spec_id} (n={len(spec_data)})',
                isCorrectColumnName=metric_field
            )
            scatter_by_sample_length(ax, spec_data, metric_field, noise_levels,
                                     color=color, label_prefix=f'Spec{spec_id}',
                                     sl_marker_map=sl_map)

            combined = pd.concat([spec_data, off_data])
            results_text += f"SpecId={spec_id} vs OFF\n{'-' * 30}\n"

            if len(spec_data) > 0 and len(off_data) > 0:
                np.random.seed(42)
                observed_sum, overall_p, overall_sig, level_diffs, _ = run_permutation_test(
                    combined, noise_levels, metric_field, global_test_side, n_permutations
                )
                for noise in sorted(level_diffs.keys()):
                    pct_on, pct_off, diff, n_on, n_off, p, sig = level_diffs[noise]
                    results_text += f"  N{noise * 100:.0f}%: {diff:+.1f}% p={p:.3f}{sig}\n"
                results_text += f"  Overall: {observed_sum:+.1f}% p={overall_p:.4f} {overall_sig}\n"
                if not combine_sample_lengths:
                    sl_text = run_per_sample_length_stats(
                        spec_data, off_data, noise_levels, metric_field,
                        global_test_side, n_permutations
                    )
                    if sl_text:
                        results_text += f"  By SampleLength:\n{sl_text}"
                results_text += "\n"
            else:
                results_text += "  Insufficient data\n\n"

    ax.invert_xaxis()
    ax.set_ylim([0, 110])
    ax.set_ylabel(f'% {metric_field} (rand excluded)')
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=7)

    return results_text


if __name__ == '__main__':
    main()