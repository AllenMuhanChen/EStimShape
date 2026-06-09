"""
Regression tests guarding the contract between the EStimEffects pipeline
(analyze_estim_by_condition) and the permutation-test pipeline
(estim_groups_permutation_test).

The invariant: for every condition, the trials that
``get_trial_data_for_condition`` feeds into the permutation null MUST be exactly
the estim-on / estim-off trials that ``calculate_estim_effects`` summarised into
the observed effect size. If they drift, the permutation null tests a different
quantity than the observed effect (this happened historically: the permutation
path re-filtered with its own SQL that pooled every spec on the on-side and
never applied the per-condition gen_id window on the off-side, inflating both
n's relative to EStimEffects).

These tests are hermetic — they stub the DB/session layer and drive the real
analysis functions from an in-memory DataFrame, so no live database is needed.
"""
import sys
import types
import json
import unittest

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Stub the DB / session-context layers BEFORE importing the modules under test,
# so importing them needs neither a live database nor the lab filesystem. The
# functions exercised here are driven entirely from an in-memory DataFrame.
# ---------------------------------------------------------------------------
def _install_import_stubs():
    # clat.util.connection.Connection is referenced at import time; the tests
    # monkeypatch the real data source, so a stub class is sufficient. Only stub
    # when the real package is unavailable (don't clobber a real install).
    if 'clat.util.connection' not in sys.modules:
        try:
            import clat.util.connection  # noqa: F401
        except Exception:
            clat = sys.modules.setdefault('clat', types.ModuleType('clat'))
            clat_util = sys.modules.setdefault('clat.util', types.ModuleType('clat.util'))
            clat_conn = types.ModuleType('clat.util.connection')

            class _Connection:  # never used: callers monkeypatch the data source
                def __init__(self, *a, **k):
                    raise RuntimeError("DB access not available in tests")

            clat_conn.Connection = _Connection
            clat_util.connection = clat_conn
            clat.util = clat_util
            sys.modules['clat.util.connection'] = clat_conn

    # src.startup.context runs heavy session / GA-config setup on import that
    # needs the lab filesystem. Nothing under test reads it (only context.ga_database,
    # inside functions we don't call), so stub it proactively to keep tests hermetic.
    if 'src.startup.context' not in sys.modules:
        ctx = types.ModuleType('src.startup.context')
        ctx.ga_database = 'test_stub'
        sys.modules['src.startup.context'] = ctx


_install_import_stubs()

from src.analysis.nafc.group_analysis.analyze_estim_by_condition import (  # noqa: E402
    split_data_by_conditions,
    calculate_estim_effects,
    _DEFAULT_BEHAVIORAL_CONDITIONS,
    _DEFAULT_ESTIM_CONDITIONS,
    _NumpyEncoder,
    METRIC_PCT_HYPOTHESIZED,
)
import src.analysis.nafc.group_analysis.estim_groups_permutation_test as perm  # noqa: E402


def _build_synthetic_session(seed=0):
    """One synthetic session that stresses the two failure modes:

    - spec keying: two specs (10, 20) must NOT be pooled on the estim-on side.
    - gen window: spec 10 runs only in gens 11-15 while estim-off baseline trials
      exist in every gen 6-30, so the baseline must be pruned to gens 11-15.
    """
    rng = np.random.default_rng(seed)
    rows = []

    def add(n, **kw):
        for _ in range(n):
            row = dict(trial_type='Hypothesized Shape', sample_length=500, choice='match')
            row.update(kw)
            rows.append(row)

    for noise in (0.2, 0.4):
        # estim-off baseline present in EVERY generation 6..30
        for gen in range(6, 31):
            add(4, noise_chance=noise, is_estim_on=0, estim_spec_id=np.nan, gen_id=gen,
                is_hypothesized_choice=int(rng.random() < 0.5))
        # spec 10: only generations 11..15
        for gen in range(11, 16):
            add(3, noise_chance=noise, is_estim_on=1, estim_spec_id=10, gen_id=gen,
                is_hypothesized_choice=int(rng.random() < 0.75))
        # spec 20: generations 6..30
        for gen in range(6, 31):
            add(2, noise_chance=noise, is_estim_on=1, estim_spec_id=20, gen_id=gen,
                is_hypothesized_choice=int(rng.random() < 0.55))

    df = pd.DataFrame(rows)
    df['trial_start'] = np.arange(len(df))
    return df


class EStimConditionPermutationConsistencyTest(unittest.TestCase):
    def setUp(self):
        self.df = _build_synthetic_session()
        # Point the permutation path at the in-memory session instead of the DB.
        self._orig_reader = perm._read_session_data_cached
        perm._read_session_data_cached = lambda session_id: self.df
        # Reference EStimEffects split + summary.
        comps = split_data_by_conditions(
            self.df, _DEFAULT_BEHAVIORAL_CONDITIONS, _DEFAULT_ESTIM_CONDITIONS)
        self.effects = calculate_estim_effects(comps, metrics=(METRIC_PCT_HYPOTHESIZED,))

    def tearDown(self):
        perm._read_session_data_cached = self._orig_reader

    @staticmethod
    def _stored_cond(effect):
        """conditions dict as it round-trips through EStimEffects storage."""
        return json.loads(json.dumps(effect['conditions'], cls=_NumpyEncoder))

    def test_permutation_trials_match_estim_effects_exactly(self):
        """Per condition, the permutation on/off trials reproduce EStimEffects' n and %."""
        self.assertTrue(self.effects, "fixture produced no conditions")
        for effect in self.effects:
            cond = self._stored_cond(effect)
            td = perm.get_trial_data_for_condition(
                'sess', cond, metric=METRIC_PCT_HYPOTHESIZED)

            self.assertEqual(len(td['estim_on']), effect['estim_on_n_trials'], cond)
            self.assertEqual(len(td['estim_off']), effect['estim_off_n_trials'], cond)

            on_pct = 100 * np.mean(td['estim_on']) if td['estim_on'] else None
            off_pct = 100 * np.mean(td['estim_off']) if td['estim_off'] else None
            self.assertAlmostEqual(on_pct, effect['estim_on_pct_hypothesized'], places=9, msg=cond)
            self.assertAlmostEqual(off_pct, effect['estim_off_pct_hypothesized'], places=9, msg=cond)

    def test_estim_off_baseline_restricted_to_condition_gen_window(self):
        """spec 10 ran only in gens 11-15, so its baseline excludes other gens."""
        spec10 = next(e for e in self.effects
                      if self._stored_cond(e)['estim_spec_id'] == 10
                      and abs(self._stored_cond(e)['noise_chance'] - 0.2) < 1e-9)
        # off trials for noise 0.2 in gens 11-15: 5 gens * 4 = 20; full baseline = 25*4 = 100
        self.assertEqual(spec10['estim_off_n_trials'], 20)
        full_baseline = len(self.df[(self.df['is_estim_on'] == 0)
                                    & (np.abs(self.df['noise_chance'] - 0.2) < 1e-9)])
        self.assertEqual(full_baseline, 100)
        self.assertLess(spec10['estim_off_n_trials'], full_baseline)

    def test_estim_on_side_not_pooled_across_specs(self):
        """Each spec's on-trials stay separate (spec 10 = 15, spec 20 = 50 per noise)."""
        by_spec = {}
        for e in self.effects:
            cond = self._stored_cond(e)
            by_spec.setdefault(cond['estim_spec_id'], set()).add(e['estim_on_n_trials'])
        self.assertEqual(by_spec.get(10), {15})
        self.assertEqual(by_spec.get(20), {50})

    def test_single_key_condition_value_is_scalar_not_list(self):
        """Regression: pandas single-column groupby returns a length-1 tuple; the
        stored condition value must be unwrapped to a scalar, not [10.0]."""
        for effect in self.effects:
            value = effect['conditions']['estim_spec_id']
            self.assertNotIsInstance(value, (list, tuple),
                                     f"estim_spec_id stored as {value!r}")


if __name__ == '__main__':
    unittest.main()
