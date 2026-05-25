import sys
from pathlib import Path
import os

sys.path.insert(0, str(Path(__file__).parent))

from matplotlib import pyplot as plt

from clat.compile.tstamp.cached_tstamp_fields import CachedFieldList
from clat.util import time_util
from clat.util.connection import Connection

from src.analysis.nafc.nafc_database_fields import (
    IsCorrectField, IsHypothesizedField, StimTypeField, GenIdField,
    EStimEnabledField, BaseMStickIdField, IsRemovedTrialField,
    VariantIdField, VariantPctMaxResponseField,
)
from src.analysis.nafc.psychometric_curves import collect_choice_trials
from src.startup import context


def plot_variant_response_vs_effect(data_exp, metric_field,
                                    start_gen_id_estim_on, max_gen_id_estim_on):
    """Scatter of estim effect against the variant's GA response tuning.

    x-axis: VariantPctMaxResponse — the variant's response as a percentage of the max
            variant response across all included variants.
    y-axis: estim effect = (% estim-on - % estim-off) on `metric_field` (e.g. IsHypothesized).

    One dot per variant_id: delta and variant trials of the same (delta, variant) pair are
    pooled (they share a variant_id), and all conditions (NoiseChance, EStimSpecId,
    SampleLength, ...) are pooled into a single on/off average.
    """
    df = data_exp.copy()
    if 'IsRemovedTrial' in df.columns:
        df = df[df['IsRemovedTrial'] != True]
    df = df[df['VariantId'].notna() & df['VariantPctMaxResponse'].notna()].copy()
    if len(df) == 0:
        print("No variant tuning data — skipping variant-response-vs-effect plot.")
        return None

    df.loc[df[metric_field] == "No Data", metric_field] = False
    df[f'{metric_field}_bool'] = (df[metric_field] == True)

    on_mask = (
        (df['EStimEnabled'] == True) &
        (df['GenId'] >= start_gen_id_estim_on) &
        (df['GenId'] <= max_gen_id_estim_on)
    )
    off_mask = (df['EStimEnabled'] == False)

    points = []  # (x, effect, n_on, n_off, variant_id)
    for variant_id, grp in df.groupby('VariantId'):
        x = grp['VariantPctMaxResponse'].iloc[0]
        on = grp[on_mask.loc[grp.index]]
        off = grp[off_mask.loc[grp.index]]
        if len(on) == 0 or len(off) == 0:
            continue
        pct_on = 100 * on[f'{metric_field}_bool'].mean()
        pct_off = 100 * off[f'{metric_field}_bool'].mean()
        points.append((x, pct_on - pct_off, len(on), len(off), int(variant_id)))

    if not points:
        print("No variants with both estim-on and estim-off trials — skipping plot.")
        return None

    fig, ax = plt.subplots(figsize=(8, 7))
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    ax.scatter(xs, ys, s=80, color='steelblue', edgecolors='black', linewidths=0.8, zorder=5)
    for x, y, n_on, n_off, variant_id in points:
        ax.annotate(f"{variant_id}\n(on={n_on}/off={n_off})", (x, y),
                    fontsize=5, textcoords='offset points', xytext=(5, 4))
    ax.axhline(0, color='gray', lw=1, ls='--', zorder=1)
    ax.set_xlabel('Variant response (% of max variant response)')
    ax.set_ylabel(f'EStim effect: %on - %off ({metric_field})')
    ax.set_title('EStim effect vs. variant tuning\n(one dot per variant; delta + variant trials pooled)')
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return fig


def main():
    # ============ CONFIGURATION ============
    exp_db_name = "allen_estimshape_exp_260520_0"
    exp_conn = Connection(exp_db_name)
    ga_conn  = Connection(context.ga_database)

    since_date            = time_util.from_date_to_now(2024, 7, 10)
    start_gen_id          = 9
    max_gen_id            = float('inf')
    start_gen_id_estim_on = 0
    max_gen_id_estim_on   = float('inf')

    isCorrectFieldName = "IsHypothesized"
    # =======================================

    session_id = exp_db_name.split("allen_estimshape_exp_")[-1]

    trial_tstamps = collect_choice_trials(exp_conn, since_date)

    if trial_tstamps:
        first_task_id       = min(t.start for t in trial_tstamps)
        most_recent_task_id = max(t.start for t in trial_tstamps)
        task_range          = f"{first_task_id}_{most_recent_task_id}"
    else:
        task_range = "no_trials"
    save_path = f"/home/connorlab/Documents/plots/{session_id}/estim/{task_range}_response_effect_estim_results.png"
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    fields = CachedFieldList()
    fields.append(IsCorrectField(exp_conn))
    fields.append(IsHypothesizedField(exp_conn))
    fields.append(StimTypeField(exp_conn))
    fields.append(GenIdField(exp_conn))
    fields.append(EStimEnabledField(exp_conn))
    fields.append(BaseMStickIdField(exp_conn))
    fields.append(VariantIdField(exp_conn, ga_conn))
    fields.append(VariantPctMaxResponseField(exp_conn, ga_conn))
    fields.append(IsRemovedTrialField(exp_conn))

    data = fields.to_data(trial_tstamps)
    data = data[(data['GenId'] >= start_gen_id) & (data['GenId'] <= max_gen_id)]
    data_exp = data[data['StimType'].isin([
        'EStimShapeVariantsDeltaNAFCStim',
        'EStimShapeVariantsDeletedNAFCStim',
    ])]

    fig = plot_variant_response_vs_effect(
        data_exp, isCorrectFieldName, start_gen_id_estim_on, max_gen_id_estim_on
    )
    if fig is not None:
        fig.savefig(save_path, bbox_inches='tight', dpi=150)
        print(f"Saved plot to {save_path}")

    plt.show()


if __name__ == '__main__':
    main()
