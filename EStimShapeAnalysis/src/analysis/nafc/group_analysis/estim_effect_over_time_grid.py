"""
Sliding-window EStim effect over time, tiled as a grid of small multiples in a PDF.

For each session, every condition (behavioral x estim_spec) gets a colored line
showing its estim effect over the course of the session. Crucially, there is one
dot per actual estim trial: each estim-on presentation of a condition is placed at
the x-position where it occurred (trials sorted by trial_start), and its y is the
LOCAL WINDOWED effect around that trial:

    effect = estim_on %<METRIC> - estim_off %<METRIC>

computed within a WINDOW_SIZE-trial window centered on that presentation. So a
condition with 5 estim trials shows 5 dots. Dotted vertical lines mark generation
boundaries.

Sessions with too little data are skipped. Sessions are tiled COLS-per-row,
ROWS_PER_PAGE-per-page, into one multi-page PDF at a standard paper size.

Configure everything in the CONFIG block. ALGORITHM_LABEL and METRIC default to
'None' and 'pct_hyp_vs_delta'. START_SESSION_ID and EXCLUDE_SESSION_IDS choose
which sessions appear (session_id is YYMMDD_N, so a lexicographic >= acts as a
start date).
"""

import json

import numpy as np
from clat.util.connection import Connection

from src.analysis.nafc.group_analysis.analyze_estim_by_condition import (
    METRIC_PCT_HYPOTHESIZED,
    METRIC_PCT_HYP_VS_DELTA,
    _DEFAULT_BEHAVIORAL_CONDITIONS,
    _DEFAULT_ESTIM_CONDITIONS,
    _NumpyEncoder,
    calculate_estim_effects,
    compute_gen_boundaries,
    format_condition_label,
    read_trial_data_from_repository,
    split_data_by_conditions,
)

# ===========================================================================
# CONFIG
# ===========================================================================

ALGORITHM_LABEL = 'None'            # kept for parity; raw trials are used either way
METRIC = METRIC_PCT_HYP_VS_DELTA    # effect = estim_on %metric - estim_off %metric

START_SESSION_ID = None             # e.g. "260402_0"
EXCLUDE_SESSION_IDS = []            # e.g. ["260421_0", "260410_0"]

WINDOW_SIZE = 100                   # trials in the window centered on each estim trial
MIN_SESSION_TRIALS = WINDOW_SIZE    # skip sessions with fewer trials than this

COLS = 1                            # plots per row
ROWS_PER_PAGE = 5                   # -> 5 sessions stacked per page

# Physical page size in inches. Default is US Letter, portrait, so five full-width
# time-series panels stack cleanly down the page and it prints 1:1. For A4 use
# (8.27, 11.69); for landscape, swap the two numbers.
PAGE_SIZE_INCHES = (8.5, 11.0)

SHOW_GEN_BOUNDARIES = True
Y_LIM = (-100, 100)                 # shared y-axis on every panel; set None to autoscale

OUTPUT_PDF = '/home/connorlab/Documents/plots/across_experiments/estim_effect_over_time_grid.pdf'


# ===========================================================================


def _get_session_ids():
    """Distinct session_ids in EStimShapeTrials, after START/EXCLUDE filtering."""
    conn = Connection("allen_data_repository")
    conn.execute("SELECT DISTINCT session_id FROM EStimShapeTrials ORDER BY session_id")
    session_ids = [row[0] for row in conn.fetch_all()]
    if EXCLUDE_SESSION_IDS:
        excluded = set(EXCLUDE_SESSION_IDS)
        session_ids = [s for s in session_ids if s not in excluded]
    if START_SESSION_ID is not None:
        session_ids = [s for s in session_ids if s >= START_SESSION_ID]
    return session_ids


def _windowed_effect_at(data_sorted, behavioral, key, trial_idx):
    """Local windowed effect for condition ``key`` in a WINDOW_SIZE window centered
    on the trial at global index ``trial_idx`` (clamped to the session bounds).

    Reuses split_data_by_conditions + calculate_estim_effects on the window slice so
    the value matches the offline pipeline's effect exactly (same gen-id-restricted
    baseline and same metric filtering). Returns the effect or None.
    """
    n = len(data_sorted)
    half = WINDOW_SIZE // 2
    lo = max(0, min(trial_idx - half, n - WINDOW_SIZE))
    window = data_sorted.iloc[lo:lo + WINDOW_SIZE]
    for res in calculate_estim_effects(
            split_data_by_conditions(window, behavioral, _DEFAULT_ESTIM_CONDITIONS),
            metrics=(METRIC,)):
        if json.dumps(res['conditions'], sort_keys=True, cls=_NumpyEncoder) == key:
            return res['effect_size']
    return None


def build_session_result(session_id):
    """Compute the per-condition, per-estim-trial effect series for one session.

    Returns a plotting-ready dict (decoupled from the DB), or None if the session
    has too few trials or no usable conditions:
        {'session_id', 'n_trials', 'conditions':[{'x','y'}], 'gen_boundaries'}
    where each condition's x are the estim trials' positions (session order) and y
    the local windowed effect at each.
    """
    data = read_trial_data_from_repository(session_id)
    if data.empty or len(data) < MIN_SESSION_TRIALS:
        return None

    behavioral = [c for c in _DEFAULT_BEHAVIORAL_CONDITIONS if c in data.columns]
    data_sorted = data.sort_values('trial_start').reset_index(drop=True)
    n = len(data_sorted)

    full_groups = split_data_by_conditions(data_sorted, behavioral, _DEFAULT_ESTIM_CONDITIONS)

    # Full-session effect per condition — used to pick the most positive / most
    # negative (same definition as the extremes table).
    full_effect_by_key = {
        json.dumps(res['conditions'], sort_keys=True, cls=_NumpyEncoder): res['effect_size']
        for res in calculate_estim_effects(full_groups, metrics=(METRIC,))
    }

    conditions = []
    for group in full_groups:
        cond = {**group['behavioral_conditions'], **group['estim_conditions']}
        key = json.dumps(cond, sort_keys=True, cls=_NumpyEncoder)

        # One dot per estim-on presentation of this condition, at its session position.
        estim_trial_idxs = sorted(int(i) for i in group['estim_on_data'].index)
        if not estim_trial_idxs:
            continue

        xs, ys = [], []
        for i in estim_trial_idxs:
            eff = _windowed_effect_at(data_sorted, behavioral, key, i)
            xs.append(i)
            ys.append(np.nan if eff is None else eff)

        if all(np.isnan(y) for y in ys):
            continue
        conditions.append({
            'x': xs, 'y': ys,
            'behavioral': group['behavioral_conditions'],
            'estim': group['estim_conditions'],
            'spec': group['estim_conditions'].get('estim_spec_id'),
            'full_effect': full_effect_by_key.get(key),
        })

    if not conditions:
        return None

    # Short label per condition: only the dimensions that vary across this session.
    values_by_key = {}
    for c in conditions:
        for k, v in {**c['behavioral'], **c['estim']}.items():
            values_by_key.setdefault(k, set()).add(str(v))
    varying = [k for k, vs in values_by_key.items() if len(vs) > 1] or None
    for c in conditions:
        c['label'] = format_condition_label(c['behavioral'], c['estim'], varying)

    # Tag the most positive / most negative condition by full-session effect.
    ranked = [(i, c['full_effect']) for i, c in enumerate(conditions) if c['full_effect'] is not None]
    if ranked:
        i_pos = max(ranked, key=lambda t: t[1])[0]
        i_neg = min(ranked, key=lambda t: t[1])[0]
        if i_pos == i_neg:
            conditions[i_pos]['extreme'] = 'only'
        else:
            conditions[i_pos]['extreme'] = 'pos'
            conditions[i_neg]['extreme'] = 'neg'

    n_estim = int((data_sorted['is_estim_on'] == 1).sum())
    n_off = int((data_sorted['is_estim_on'] == 0).sum())

    return {
        'session_id': session_id,
        'n_trials': n,
        'n_estim': n_estim,
        'n_off': n_off,
        'conditions': conditions,
        'gen_boundaries': compute_gen_boundaries(data_sorted) if SHOW_GEN_BOUNDARIES else [],
    }


# Fixed-meaning colors: the most-positive condition is green, the most-negative is
# red, and every other condition is a muted low-alpha gray so the two extremes read
# instantly. A few gray shades keep overlapping background lines distinguishable.
_POS_COLOR = '#2ca02c'   # green
_NEG_COLOR = '#d62728'   # red
_GRAYS = ['0.45', '0.55', '0.65', '0.72']


def _plot_session_into_ax(ax, result):
    """Draw one session's effect-over-time small multiple into ``ax``.

    Most-positive condition = green, most-negative = red, all others = muted gray.
    Each dot is one estim trial at the position it occurred; a small legend names the
    two extremes with their full-session effect.
    """
    conditions = result['conditions']

    # Draw the muted background conditions first so green/red sit on top.
    gray_i = 0
    for cond in conditions:
        if cond.get('extreme') in ('pos', 'neg', 'only'):
            continue
        gray = _GRAYS[gray_i % len(_GRAYS)]
        gray_i += 1
        ax.plot(cond['x'], cond['y'], color=gray, marker='o', markersize=2,
                linewidth=0.8, alpha=0.35, zorder=2)

    pos_handle = neg_handle = None
    for cond in conditions:
        ex = cond.get('extreme')
        if ex not in ('pos', 'neg', 'only'):
            continue
        eff = cond.get('full_effect')
        if ex == 'neg':
            color, label = _NEG_COLOR, f"▼ most − ({eff:+.0f} pp): {cond['label']}"
        elif ex == 'only':
            color, label = _POS_COLOR, f"only cond ({eff:+.0f} pp): {cond['label']}"
        else:
            color, label = _POS_COLOR, f"▲ most + ({eff:+.0f} pp): {cond['label']}"
        line, = ax.plot(cond['x'], cond['y'], color=color, marker='o', markersize=4,
                        linewidth=2.2, alpha=0.95, zorder=5, label=label)
        if ex == 'neg':
            neg_handle = line
        else:
            pos_handle = line

    ax.axhline(0, color='black', linestyle='--', linewidth=0.8, alpha=0.5)
    for trial_num, _gen_id in result['gen_boundaries']:
        ax.axvline(trial_num, color='gray', linestyle=':', linewidth=0.7, alpha=0.5)

    ax.set_title(f"{result['session_id']}  "
                 f"(n={result['n_trials']}: {result['n_estim']} estim / {result['n_off']} off)",
                 fontsize=9)
    ax.set_xlabel('Trial (session order)', fontsize=7)
    ax.set_ylabel('Effect (pp)', fontsize=7)
    ax.tick_params(labelsize=6)
    ax.grid(True, alpha=0.25)
    if Y_LIM is not None:
        ax.set_ylim(*Y_LIM)

    # Tiny legend naming just the most-positive and most-negative conditions.
    handles = [h for h in (pos_handle, neg_handle) if h is not None]
    if handles:
        ax.legend(handles=handles, loc='upper left', fontsize=5, framealpha=0.85,
                  handlelength=1.4, borderpad=0.3, labelspacing=0.25)


def render_grid_pdf(session_results, path, cols=COLS, rows_per_page=ROWS_PER_PAGE):
    """Tile per-session effect-over-time plots into a multi-page PDF.

    Pure plotting: takes the list of dicts from build_session_result, so it can be
    exercised without a database.
    """
    import os

    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    out_dir = os.path.dirname(path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    per_page = cols * rows_per_page
    pages = [session_results[i:i + per_page] for i in range(0, len(session_results), per_page)]
    subtitle = (f"algorithm_label={ALGORITHM_LABEL}  |  metric={METRIC}  |  "
                f"window={WINDOW_SIZE}  |  {len(session_results)} sessions")

    with PdfPages(path) as pdf:
        for pi, page in enumerate(pages):
            fig, axes = plt.subplots(rows_per_page, cols,
                                     figsize=PAGE_SIZE_INCHES,
                                     squeeze=False)
            for slot in range(per_page):
                ax = axes[slot // cols][slot % cols]
                if slot < len(page):
                    _plot_session_into_ax(ax, page[slot])
                else:
                    ax.axis('off')

            fig.suptitle(f"EStim Effect Over Time — {subtitle}\n(page {pi + 1}/{len(pages)})",
                         fontsize=9, fontweight='bold')
            fig.tight_layout(rect=[0, 0, 1, 0.94])
            pdf.savefig(fig)
            plt.close(fig)

    print(f"Saved PDF to {path}")


def main():
    session_ids = _get_session_ids()
    print(f"Sessions to consider: {session_ids}")

    results = []
    for sid in session_ids:
        print(f"  computing {sid} ...")
        result = build_session_result(sid)
        if result is None:
            print(f"    [{sid}] skipped (fewer than {MIN_SESSION_TRIALS} trials or no conditions)")
            continue
        results.append(result)

    if not results:
        print("No sessions to plot.")
        return

    render_grid_pdf(results, OUTPUT_PDF)


if __name__ == '__main__':
    main()
