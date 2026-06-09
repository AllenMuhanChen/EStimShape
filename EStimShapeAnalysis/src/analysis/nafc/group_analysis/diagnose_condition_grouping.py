"""
Diagnostic: show how analyze_estim_by_condition collapses estim_spec_ids into
condition groups, and what that does to the estim-on n, the gen range, and the
gen-matched estim-off baseline n.

Run with the session_id you're investigating. Any condition group that lists
more than one estim_spec_id or more than one channel is being POOLED — that is
the source of a diluted effect size and an inflated n versus analyze_estim_by_id
(which keys on estim_spec_id).
"""
import pandas as pd

from src.analysis.nafc.group_analysis.analyze_estim_by_condition import (
    read_trial_data_from_repository,
    _DEFAULT_BEHAVIORAL_CONDITIONS,
    _DEFAULT_ESTIM_CONDITIONS,
)

pd.set_option('display.width', 200)
pd.set_option('display.max_columns', 50)


def diagnose(session_id,
             behavioral_conditions=None,
             estim_conditions=None):
    behavioral_conditions = behavioral_conditions or _DEFAULT_BEHAVIORAL_CONDITIONS
    estim_conditions = estim_conditions or _DEFAULT_ESTIM_CONDITIONS

    data = read_trial_data_from_repository(session_id)
    print(f"=== {session_id}: {len(data)} trials ===")
    print(f"grouping estim conditions on: {estim_conditions}")
    print(f"(channel in grouping? {'channel' in estim_conditions})\n")

    on = data[data['is_estim_on'] == 1].copy()
    off = data[data['is_estim_on'] == 0].copy()

    groups = on.groupby(estim_conditions, dropna=False)
    for vals, grp in groups:
        vals = vals if isinstance(vals, tuple) else (vals,)
        cond = dict(zip(estim_conditions, vals))
        spec_ids = sorted(grp['estim_spec_id'].dropna().unique().tolist())
        channels = sorted(grp['channel'].dropna().unique().tolist()) if 'channel' in grp else []
        cond_gen_ids = sorted(grp['gen_id'].dropna().unique().tolist())
        n_on = len(grp)

        # baseline n the pipeline actually uses (current isin logic), pooled across
        # behavioral groups here for a quick total
        off_matched = off[off['gen_id'].isin(cond_gen_ids)]
        n_off = len(off_matched)

        pooled = len(spec_ids) > 1 or len(channels) > 1
        flag = "  <-- POOLED (multiple specs/channels merged)" if pooled else ""
        print(f"condition {cond}{flag}")
        print(f"    spec_ids={spec_ids}  channels={channels}")
        print(f"    n_on={n_on}  gen_range={cond_gen_ids[:1]}..{cond_gen_ids[-1:]}  "
              f"gen-matched n_off={n_off}")

        # Per-spec breakdown so you can see each spec's own effect/n
        if pooled and 'is_hypothesized_choice' in grp:
            for sid in spec_ids:
                sg = grp[grp['estim_spec_id'] == sid]
                sg_gens = sorted(sg['gen_id'].dropna().unique().tolist())
                sg_off = off[off['gen_id'].isin(sg_gens)]
                on_pct = sg['is_hypothesized_choice'].mean() * 100
                off_pct = (sg_off['is_hypothesized_choice'].mean() * 100
                           if len(sg_off) else float('nan'))
                print(f"      spec {sid}: n_on={len(sg)} on%={on_pct:.1f}  "
                      f"n_off={len(sg_off)} off%={off_pct:.1f}  "
                      f"effect={on_pct - off_pct:+.1f}")
        print()


if __name__ == '__main__':
    import sys
    session = sys.argv[1] if len(sys.argv) > 1 else '260605_0'
    diagnose(session)
