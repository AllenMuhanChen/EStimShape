"""
Per-session EStim extremes table.

For each session_id, look at all conditions and pick two:
  - the MOST POSITIVE condition  (largest effect_size)
  - the MOST NEGATIVE condition  (smallest effect_size)

where effect_size = estim_on %hyp - estim_off %hyp under the configured METRIC.
For each extreme, the % hypothesized-vs-delta is broken back down into raw
choice counts, giving the four columns the analysis is about:

    estim_on_hyp | estim_on_delta | estim_off_hyp | estim_off_delta

Under the ``pct_hyp_vs_delta`` metric each trial the monkey committed to is
either the hypothesized or the delta alternative (rand/removed choices are
dropped upstream), so:

    n_trials  = #hyp + #delta
    pct       = #hyp / n_trials * 100
    #hyp      = round(pct/100 * n_trials)
    #delta    = n_trials - #hyp

This reader pulls the pre-computed rows straight from the EStimEffects table
(populated by ``analyze_estim_by_condition.run_pipeline``); it does not touch
raw trials.

Configure everything in the CONFIG block at the top. ALGORITHM_LABEL and METRIC
default to 'None' and 'pct_hyp_vs_delta'. START_SESSION_ID and
EXCLUDE_SESSION_IDS control which sessions appear (session_id is YYMMDD_N, so a
lexicographic ``>=`` comparison acts as a start date).
"""

import json

import pandas as pd
from clat.util.connection import Connection

from src.analysis.nafc.group_analysis.analyze_estim_by_condition import (
    METRIC_PCT_HYPOTHESIZED,
    METRIC_PCT_HYP_VS_DELTA,
    format_condition_label,
)
from src.analysis.nafc.group_analysis.max_estim_per_experiment import _expand_condition

# ===========================================================================
# CONFIG
# ===========================================================================

# Which stored EStimEffects rows to read.
ALGORITHM_LABEL = 'None'            # cutoff variant; 'None'/'none' = raw data
METRIC = METRIC_PCT_HYP_VS_DELTA    # the hyp-vs-delta collapse is what the counts mean

# Session selection. session_id is YYMMDD_N, so a lexicographic >= on
# START_SESSION_ID acts as a "start date". EXCLUDE_SESSION_IDS drops specific
# sessions entirely.
START_SESSION_ID = None             # e.g. "260402_0" for first variant experiment
EXCLUDE_SESSION_IDS = []            # e.g. ["260421_0", "260410_0"]

# A condition only qualifies as an extreme if it has at least this many trials
# in BOTH the estim-on and estim-off groups. 0 = consider every condition
# (the literal most/least positive, even if it rests on a single trial).
MIN_TRIALS = 0

# Unfurl estim_spec_id into physical stimulation params (polarity, shape, a1,
# pulse_rate_hz, ...) in the printed condition label. Requires a DB lookup per
# condition; set False for a faster, raw-dict label.
EXPAND_CONDITIONS = True

# Optional path to also write the table as CSV. None = print only.
OUTPUT_CSV = None


# ===========================================================================


def _hyp_delta_counts(pct, n_trials):
    """Break a stored (%hyp, n_trials) pair back into (#hyp, #delta) choice counts.

    Under pct_hyp_vs_delta, n_trials is the number of hyp-or-delta commitments and
    pct = #hyp / n_trials * 100, so #hyp is recovered exactly by rounding (pct is
    stored as a 4-byte FLOAT, so multiply-then-round undoes the precision loss).
    Returns (None, None) when the group was empty (pct is None / n_trials 0).
    """
    if pct is None or n_trials is None or n_trials == 0:
        return None, None
    hyp = int(round(pct / 100.0 * n_trials))
    hyp = max(0, min(hyp, int(n_trials)))
    return hyp, int(n_trials) - hyp


def _get_session_ids():
    """Distinct session_ids present in EStimEffects for the configured
    algorithm_label + metric, after START/EXCLUDE filtering."""
    conn = Connection("allen_data_repository")
    conn.execute(
        "SELECT DISTINCT session_id FROM EStimEffects "
        "WHERE algorithm_label = %s AND metric = %s ORDER BY session_id",
        (ALGORITHM_LABEL, METRIC))
    session_ids = [row[0] for row in conn.fetch_all()]

    if EXCLUDE_SESSION_IDS:
        excluded = set(EXCLUDE_SESSION_IDS)
        session_ids = [s for s in session_ids if s not in excluded]
    if START_SESSION_ID is not None:
        session_ids = [s for s in session_ids if s >= START_SESSION_ID]
    return session_ids


def _load_effects(session_id):
    """All EStimEffects rows for this session under the configured algorithm_label
    + metric, as a list of dicts."""
    conn = Connection("allen_data_repository")
    conn.execute("""
        SELECT conditions,
               estim_on_pct_hypothesized,
               estim_off_pct_hypothesized,
               estim_on_n_trials,
               estim_off_n_trials,
               effect_size
        FROM EStimEffects
        WHERE session_id = %s AND algorithm_label = %s AND metric = %s
    """, (session_id, ALGORITHM_LABEL, METRIC))
    cols = [desc[0] for desc in conn.my_cursor.description]
    return [dict(zip(cols, row)) for row in conn.fetch_all()]


def _condition_label(session_id, conditions_json):
    """Human-readable label for a stored conditions JSON string."""
    cond = json.loads(conditions_json)
    if EXPAND_CONDITIONS:
        cond = _expand_condition(session_id, cond)
    return format_condition_label(cond, {})


def _extreme_row(session_id, effect_row, extreme):
    """Assemble one output row (a dict) for a chosen extreme condition."""
    on_hyp, on_delta = _hyp_delta_counts(
        effect_row['estim_on_pct_hypothesized'], effect_row['estim_on_n_trials'])
    off_hyp, off_delta = _hyp_delta_counts(
        effect_row['estim_off_pct_hypothesized'], effect_row['estim_off_n_trials'])
    return {
        'session_id':      session_id,
        'extreme':         extreme,
        'condition':       _condition_label(session_id, effect_row['conditions']),
        'effect_size':     effect_row['effect_size'],
        'estim_on_hyp':    on_hyp,
        'estim_on_delta':  on_delta,
        'estim_off_hyp':   off_hyp,
        'estim_off_delta': off_delta,
        'estim_on_pct':    effect_row['estim_on_pct_hypothesized'],
        'estim_off_pct':   effect_row['estim_off_pct_hypothesized'],
        'estim_on_n':      effect_row['estim_on_n_trials'],
        'estim_off_n':     effect_row['estim_off_n_trials'],
    }


def build_table():
    """Build the per-session most-positive / most-negative extremes table.

    Returns a pandas DataFrame with two rows per session (most_positive,
    most_negative); a session with no qualifying condition is skipped.
    """
    rows = []
    for session_id in _get_session_ids():
        effects = _load_effects(session_id)

        # Only conditions with a defined effect and enough trials in both groups
        # can be an extreme.
        eligible = [
            e for e in effects
            if e['effect_size'] is not None
            and (e['estim_on_n_trials'] or 0) >= MIN_TRIALS
            and (e['estim_off_n_trials'] or 0) >= MIN_TRIALS
        ]
        if not eligible:
            print(f"[{session_id}] no condition with a defined effect and "
                  f"n>={MIN_TRIALS} in both groups, skipping")
            continue

        most_positive = max(eligible, key=lambda e: e['effect_size'])
        most_negative = min(eligible, key=lambda e: e['effect_size'])

        rows.append(_extreme_row(session_id, most_positive, 'most_positive'))
        rows.append(_extreme_row(session_id, most_negative, 'most_negative'))

    columns = ['session_id', 'extreme', 'condition', 'effect_size',
               'estim_on_hyp', 'estim_on_delta', 'estim_off_hyp', 'estim_off_delta',
               'estim_on_pct', 'estim_off_pct', 'estim_on_n', 'estim_off_n']
    return pd.DataFrame(rows, columns=columns)


def main():
    df = build_table()

    if df.empty:
        print("No data — check ALGORITHM_LABEL / METRIC and that EStimEffects "
              "has been populated (analyze_estim_by_condition.run_pipeline).")
        return

    print(f"\nEStim extremes  (algorithm_label='{ALGORITHM_LABEL}', metric='{METRIC}', "
          f"min_trials={MIN_TRIALS})\n")
    with pd.option_context('display.max_rows', None,
                           'display.max_columns', None,
                           'display.width', None,
                           'display.max_colwidth', 60,
                           'display.float_format', lambda v: f"{v:.1f}"):
        print(df.to_string(index=False))

    if OUTPUT_CSV:
        df.to_csv(OUTPUT_CSV, index=False)
        print(f"\nSaved table to {OUTPUT_CSV}")


if __name__ == '__main__':
    main()
