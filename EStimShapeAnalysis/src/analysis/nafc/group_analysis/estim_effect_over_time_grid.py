"""
Sliding-window EStim effect over time, tiled as a grid of small multiples in a PDF.

This is the per-condition "effect size across trials" graph (the top panel of
``analyze_estim_by_condition.sliding_window_analysis``) drawn once per session and
tiled COLS-per-row, SESSIONS_PER_PAGE-per-page, into a single multi-page PDF.

For each sliding window of trials (sorted by trial_start) and each condition
(behavioral x estim_spec), the line value is:

    effect_size = estim_on %<METRIC> - estim_off %<METRIC>

so every condition gets its own colored line showing how stimulation's push
toward the hypothesized choice evolves over the session. Dotted vertical lines
mark generation boundaries.

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

WINDOW_SIZE = 100                   # trials per sliding window
STEP_SIZE = 10                      # window step (trials)

COLS = 5                            # sessions per row
ROWS_PER_PAGE = 1                   # -> 5 sessions per page

# Physical page size in inches. Default is US Letter, landscape. Each page is a
# real sheet of this size (subplots are laid out to fill it), so it prints 1:1.
# For A4 landscape use (11.69, 8.27); for portrait, swap the two numbers.
PAGE_SIZE_INCHES = (11.0, 8.5)

SHOW_GEN_BOUNDARIES = True
SHOW_LEGEND = True                  # per-subplot condition legend (tiny font)
Y_LIM = None                        # e.g. (-75, 75) for a shared y-axis; None = autoscale

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


def _condition_window_series(data, behavioral_conditions, estim_conditions):
    """Return {condition_key: {'label', 'behavioral', 'estim', 'windows':[...]}}.

    Mirrors analyze_estim_by_condition.sliding_window_analysis, but computes the
    effect with the configured METRIC instead of the raw pct_hypothesized.
    """
    data_sorted = data.sort_values('trial_start').reset_index(drop=True)

    condition_groups = {}
    for group in split_data_by_conditions(data, behavioral_conditions, estim_conditions):
        key = json.dumps({**group['behavioral_conditions'], **group['estim_conditions']},
                         sort_keys=True, cls=_NumpyEncoder)
        condition_groups[key] = {
            'label': format_condition_label(group['behavioral_conditions'],
                                            group['estim_conditions']),
            'behavioral': group['behavioral_conditions'],
            'estim': group['estim_conditions'],
            'windows': [],
        }

    for window_start in range(0, len(data_sorted) - WINDOW_SIZE + 1, STEP_SIZE):
        window_data = data_sorted.iloc[window_start:window_start + WINDOW_SIZE]
        window_groups = split_data_by_conditions(window_data, behavioral_conditions, estim_conditions)
        for result in calculate_estim_effects(window_groups, metrics=(METRIC,)):
            key = json.dumps(result['conditions'], sort_keys=True, cls=_NumpyEncoder)
            if key in condition_groups:
                condition_groups[key]['windows'].append({
                    'trial_number': window_start + WINDOW_SIZE // 2,
                    'effect_size': result['effect_size'],
                })

    return condition_groups, data_sorted


def build_session_result(session_id):
    """Compute the per-condition effect-over-time series for one session.

    Returns a plotting-ready dict (decoupled from the DB) or None if the session
    has no usable conditions:
        {'session_id', 'n_trials', 'conditions':[{'label','x','y'}], 'gen_boundaries'}
    """
    data = read_trial_data_from_repository(session_id)
    if data.empty:
        return None

    behavioral = [c for c in _DEFAULT_BEHAVIORAL_CONDITIONS if c in data.columns]
    condition_groups, data_sorted = _condition_window_series(
        data, behavioral, _DEFAULT_ESTIM_CONDITIONS)

    # Keep only conditions that actually produced a line (>=1 non-None window).
    active = [cg for cg in condition_groups.values()
              if cg['windows'] and not all(w['effect_size'] is None for w in cg['windows'])]

    # Label only the condition dimensions that vary within this session, so the
    # legend stays short (same approach as plot_sliding_window_results).
    values_by_key = {}
    for cg in active:
        for k, v in {**cg['behavioral'], **cg['estim']}.items():
            values_by_key.setdefault(k, set()).add(str(v))
    varying_keys = [k for k, vs in values_by_key.items() if len(vs) > 1]

    conditions = []
    for cg in active:
        conditions.append({
            'label': format_condition_label(cg['behavioral'], cg['estim'], varying_keys),
            'x': [w['trial_number'] for w in cg['windows']],
            'y': [np.nan if w['effect_size'] is None else w['effect_size'] for w in cg['windows']],
        })

    return {
        'session_id': session_id,
        'n_trials': len(data_sorted),
        'conditions': conditions,
        'gen_boundaries': compute_gen_boundaries(data_sorted) if SHOW_GEN_BOUNDARIES else [],
    }


def _palette(n):
    """n visually distinct colors (matches plot_sliding_window_results)."""
    import matplotlib.pyplot as plt
    if n <= 10:
        return [plt.cm.tab10(i / 10) for i in range(n)]
    if n <= 20:
        return [plt.cm.tab20(i / 20) for i in range(n)]
    return [plt.cm.hsv(i / n) for i in range(n)]


def _plot_session_into_ax(ax, result):
    """Draw one session's effect-over-time small multiple into ``ax``."""
    conditions = result['conditions']

    if not conditions:
        msg = ("too few trials\n(< window)" if result['n_trials'] < WINDOW_SIZE
               else "no conditions")
        ax.text(0.5, 0.5, msg, transform=ax.transAxes, ha='center', va='center',
                fontsize=7, color='gray')
        ax.set_title(f"{result['session_id']}  (n={result['n_trials']})", fontsize=8)
        ax.set_xticks([])
        ax.set_yticks([])
        return

    for cond, color in zip(conditions, _palette(len(conditions))):
        ax.plot(cond['x'], cond['y'], color=color, marker='o', markersize=2,
                linewidth=1.0, label=cond['label'])

    ax.axhline(0, color='black', linestyle='--', linewidth=0.8, alpha=0.5)

    for trial_num, gen_id in result['gen_boundaries']:
        ax.axvline(trial_num, color='gray', linestyle=':', linewidth=0.7, alpha=0.5)

    ax.set_title(f"{result['session_id']}  (n={result['n_trials']})", fontsize=8)
    ax.set_xlabel('Trial (window center)', fontsize=6)
    ax.set_ylabel('Effect (pp)', fontsize=6)
    ax.tick_params(labelsize=5)
    ax.grid(True, alpha=0.25)
    if Y_LIM is not None:
        ax.set_ylim(*Y_LIM)

    if SHOW_LEGEND:
        ax.legend(fontsize=3.5, loc='best', framealpha=0.7,
                  handlelength=1.2, borderpad=0.3, labelspacing=0.25)


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
                f"window={WINDOW_SIZE}, step={STEP_SIZE}  |  {len(session_results)} sessions")

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

            fig.suptitle(f"EStim Effect Over Time — {subtitle}      (page {pi + 1}/{len(pages)})",
                         fontsize=10, fontweight='bold')
            fig.tight_layout(rect=[0, 0, 1, 0.93])
            pdf.savefig(fig)
            plt.close(fig)

    print(f"Saved PDF to {path}")


def main():
    session_ids = _get_session_ids()
    print(f"Sessions to plot: {session_ids}")

    results = []
    for sid in session_ids:
        print(f"  computing {sid} ...")
        result = build_session_result(sid)
        if result is None:
            print(f"    [{sid}] no data, skipping")
            continue
        results.append(result)

    if not results:
        print("No sessions to plot.")
        return

    render_grid_pdf(results, OUTPUT_PDF)


if __name__ == '__main__':
    main()
