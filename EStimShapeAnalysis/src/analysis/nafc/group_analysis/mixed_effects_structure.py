"""
Session-controlled test of spatial structure in the estim effect over
(current_per_second × corr half-distance) space — the model-based companion to the
permutation Moran's I in ``moran_effect_structure``.

We fit a flexible 2-D surface s(current, half_distance) — a low-rank radial-basis
expansion (columns S0..S{K-1}) — plus the condition main effects, and ask two
nested-model questions:

  Q1  "Is there spatial structure beyond condition + session?"
        does the surface block jointly matter?
  Q2  "Does the structure DIFFER by a condition (polarity / trial_type / their
       JOINT combination)?"
        does the surface × condition interaction jointly matter?

**How session is controlled (and why not a mixed model).** A proper mixed model
(session random intercept + a per-spec term) is the textbook tool, but statsmodels'
MixedLM is numerically fragile here — with a flexible basis on modest, clustered
data it hits singular random-effect covariances and returns NaN. So we use the
robust fixed-effects equivalent:

  * WITHIN-SESSION demeaning (subtract each session's mean from y and every
    predictor) — removes session baselines exactly, like a session fixed effect,
    with no variance component to estimate. This is the honest "beyond session"
    control. (A variable that does not vary within any session — e.g. a polarity
    that's constant per session — is not identifiable this way; that test is
    reported as "not identifiable within session".)
  * CLUSTER-ROBUST standard errors by session — makes inference valid under the
    residual within-session correlation, including the trial_type repeats (same
    spec, one row per trial type, nested in session).
  * A WALD test on the surface (or surface × condition) coefficient block — the
    joint "does this block matter" test, robust to the clustering.

Caveats it does NOT remove: you can only compare condition surfaces where they
OVERLAP in the plane; the joint trial_type × polarity interaction spends many
degrees of freedom (a bendy surface × many combinations), so it's usually
under-powered and reported descriptively via the maps.

The plot: the fitted effect surface — pooled, one map per condition level (each
fit on its OWN specs, so joint conditions really differ), and (for a 2-level
factor) their difference — shown only where there's data.

Needs statsmodels + patsy. Run this file (shared COMPARISON_* config).
"""

import os
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parents[3]))

from src.analysis.nafc.group_analysis.plot_current_spread_vs_tuning import (
    build_spec_metric_table, build_points, HALFDIST_COL, X_LABELS, _slug,
)
from src.analysis.nafc.group_analysis.analyze_estim_isolation_effect import (
    COMPARISON_METRIC,
    COMPARISON_REQUIRED_CONDITIONS,
    COMPARISON_START_SESSION_ID,
    COMPARISON_EXCLUDE_SESSION_IDS,
    COMPARISON_MIN_ON_TRIALS,
    COMPARISON_TRIAL_TYPES,
    COMPARISON_SAVE_DIR,
    _discover_trial_types,
)

# Spatial basis: N_PER_AXIS² radial basis functions over the standardised plane.
# Kept small (2 -> 4 columns) so the design stays well-conditioned on modest data.
N_PER_AXIS = 2
RBF_SPREAD = 1.4
VALUE_COL = 'effect_size'
CONDITION_FACTORS = ('polarity', 'waveform', 'trial_type')
# A tuple entry is a JOINT (combined) moderator — polarity and trial_type are
# coupled, so ('trial_type','polarity') asks whether the structure differs across
# the actual combinations, not each factor marginally.
MODERATORS = ('polarity', 'trial_type', ('trial_type', 'polarity'))
# Trial types dropped from this structure test only (too few specs to fit) — the
# global COMPARISON_TRIAL_TYPES that drives the other plots is left untouched.
EXCLUDE_TRIAL_TYPES = ('Removed Trial', 'Coherence')


def _analysis_trial_types():
    base = COMPARISON_TRIAL_TYPES or ['Hypothesized Shape', 'Delta Shape']
    return [t for t in base if t not in EXCLUDE_TRIAL_TYPES]


# ---------------------------------------------------------------------------
# Spatial basis + scaler
# ---------------------------------------------------------------------------

class SpatialRBF:
    """A small grid of Gaussian radial basis functions over standardised 2-D coords."""

    def __init__(self, n_per_axis=N_PER_AXIS, spread=RBF_SPREAD):
        self.n_per_axis = n_per_axis
        self.spread = spread

    def fit(self, coords):
        qs = np.linspace(0.2, 0.8, self.n_per_axis)
        cx, cy = np.quantile(coords[:, 0], qs), np.quantile(coords[:, 1], qs)
        self.centers = np.array([[a, b] for a in cx for b in cy], dtype=float)
        d2 = ((self.centers[:, None, :] - self.centers[None, :, :]) ** 2).sum(-1)
        np.fill_diagonal(d2, np.inf)
        spacing = float(np.median(np.sqrt(d2.min(axis=1))))
        self.h = self.spread * (spacing if spacing > 0 else 1.0)
        return self

    def transform(self, coords):
        d2 = ((coords[:, None, :] - self.centers[None, :, :]) ** 2).sum(-1)
        return np.exp(-0.5 * d2 / self.h ** 2)

    @property
    def k(self):
        return len(self.centers)


class _Scaler:
    def fit(self, a):
        a = np.asarray(a, dtype=float)
        self.mean, self.std = float(a.mean()), float(a.std()) or 1.0
        return self

    def transform(self, a):
        return (np.asarray(a, dtype=float) - self.mean) / self.std


# ---------------------------------------------------------------------------
# Robust fitting: within-session demeaned OLS + cluster-robust Wald
# ---------------------------------------------------------------------------

def _spatial_coef(params, k):
    return np.array([float(params.get(f"S{j}", 0.0)) for j in range(k)])


def _pooled_spatial_coef(sub, spatial_cols, other_mains):
    """Plain OLS spatial coefficients (for drawing a fitted surface). None on failure."""
    import statsmodels.api as sm
    import patsy
    rhs = " + ".join(t for t in (other_mains, " + ".join(spatial_cols)) if t)
    try:
        y, X = patsy.dmatrices(f"{VALUE_COL} ~ {rhs}", sub, return_type='dataframe')
        res = sm.OLS(y.iloc[:, 0], X).fit()
        return np.array([float(res.params.get(s, 0.0)) for s in spatial_cols])
    except Exception as exc:
        print(f"      (surface fit failed: {exc})")
        return None


def _within_wald(d, formula, block_is, group_col):
    """Within-session-demeaned OLS with cluster-robust (by session) covariance; Wald
    test that the coefficients whose name satisfies block_is() are jointly zero.
    Returns (chi2, df, p) or None if not identifiable / rank-deficient."""
    import statsmodels.api as sm
    import patsy
    try:
        y, X = patsy.dmatrices(formula, d, return_type='dataframe')
    except Exception as exc:
        print(f"      (design build failed: {exc})")
        return None
    g = d[group_col].to_numpy()
    ycol = y.columns[0]
    yw = y[ycol] - y[ycol].groupby(g).transform('mean')
    Xw = X - X.groupby(g).transform('mean')
    keep = [c for c in Xw.columns if float(Xw[c].abs().max()) > 1e-8]  # drop constant-in-session cols
    Xw = Xw[keep]
    idx = [i for i, c in enumerate(keep) if block_is(c)]
    if not idx or Xw.shape[1] == 0 or len(Xw) <= Xw.shape[1] + 2:
        return None
    try:
        res = sm.OLS(yw.to_numpy(), Xw.to_numpy()).fit(
            cov_type='cluster', cov_kwds={'groups': g})
        R = np.zeros((len(idx), len(keep)))
        for r, i in enumerate(idx):
            R[r, i] = 1.0
        wt = res.wald_test(R, use_f=False)
        stat = float(np.ravel(wt.statistic)[0])
        p = float(np.ravel(wt.pvalue)[0])
        if not np.isfinite(stat) or not np.isfinite(p):
            return None
        return stat, len(idx), p
    except Exception as exc:
        print(f"      (Wald test failed: {exc})")
        return None


# ---------------------------------------------------------------------------
# Grouping + surface helpers
# ---------------------------------------------------------------------------

def _present_factors(d, factors):
    return [f for f in factors if f in d.columns and d[f].dropna().nunique() > 1]


def _resolve_moderator(d, mod, factors):
    """(display key, dataframe column, other-factor list) for a moderator spec. A
    tuple builds a JOINT column ('Delta Shape | anodic'); a string is a single
    factor. Materialises the joint column. (None, None, None) if unusable."""
    if isinstance(mod, (tuple, list)):
        comps = [c for c in mod if c in factors]
        if len(comps) < 2:
            return None, None, None
        col = "__x__".join(comps)
        d[col] = d[comps].astype(str).agg(" | ".join, axis=1)
        others = [f for f in factors if f not in comps]
        return " × ".join(comps), col, others
    if mod not in factors:
        return None, None, None
    return mod, mod, [f for f in factors if f != mod]


def _surface_grid(rbf, scx, scy, xr, yr, gridsize=60):
    gx, gy = np.linspace(*xr, gridsize), np.linspace(*yr, gridsize)
    GX, GY = np.meshgrid(gx, gy)
    coords = np.column_stack([scx.transform(GX.ravel()), scy.transform(GY.ravel())])
    return gx, gy, GX.shape, rbf.transform(coords), coords


def _support_keep(grid_coords, data_coords, *, base_radius=1.0, min_keep=0.45):
    if len(data_coords) == 0:
        return np.ones(grid_coords.shape[0], dtype=bool)
    d2 = ((grid_coords[:, None, :] - data_coords[None, :, :]) ** 2).sum(-1)
    nearest = np.sqrt(d2.min(axis=1))
    r = max(base_radius, float(np.quantile(nearest, min_keep)))
    keep = nearest <= r
    return np.ones_like(keep) if keep.mean() < 0.2 else keep


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_mixed_structure_test(trial_types=None, *, x_col='current_per_second',
                             y_col=HALFDIST_COL, condition_factors=CONDITION_FACTORS,
                             moderators=MODERATORS, n_per_axis=N_PER_AXIS,
                             start_session_id=None, exclude_session_ids=None,
                             effect_metric=COMPARISON_METRIC, base_required_conditions=None,
                             min_on_trials=COMPARISON_MIN_ON_TRIALS, save_dir=None):
    """Within-session fixed-effects OLS + cluster-robust Wald tests of spatial
    structure (Q1) and structure × condition (Q2). Prints a table and plots the
    fitted surfaces. Returns a results dict."""
    try:
        import statsmodels.api as sm  # noqa: F401
        import patsy  # noqa: F401
    except Exception as exc:
        print(f"This test needs statsmodels + patsy ({exc}). "
              f"Install with: pip install statsmodels patsy")
        return {}

    if trial_types is None:
        trial_types = _discover_trial_types(start_session_id, exclude_session_ids)
    df = build_spec_metric_table(
        trial_types, start_session_id=start_session_id,
        exclude_session_ids=exclude_session_ids, effect_metric=effect_metric,
        base_required_conditions=base_required_conditions, min_on_trials=min_on_trials)
    if len(df) == 0:
        print("Nothing to test.")
        return {}
    points = build_points(df, [y_col], aggregate_by='spec')

    keep = [x_col, y_col, VALUE_COL, 'session_id', 'estim_spec_id'] + \
           [f for f in condition_factors if f in points.columns]
    d = points[keep].dropna(subset=[x_col, y_col, VALUE_COL, 'session_id']).copy()
    d = d.reset_index(drop=True)
    if len(d) < 20:
        print(f"Only {len(d)} rows with complete data — too few for a stable fit.")
        return {}
    d['spec_uid'] = (d['session_id'].astype(str) + '_' +
                     d['estim_spec_id'].astype(int).astype(str))
    n_repeats = int(d['spec_uid'].duplicated().sum())

    scx, scy = _Scaler().fit(d[x_col]), _Scaler().fit(d[y_col])
    coords = np.column_stack([scx.transform(d[x_col]), scy.transform(d[y_col])])
    rbf = SpatialRBF(n_per_axis=n_per_axis).fit(coords)
    B = rbf.transform(coords)
    # Centre the basis columns so the surface captures ONLY spatial variation, not
    # the overall level. Uncentred RBFs are collinear with the intercept and would
    # absorb each condition's MEAN effect into the "spatial" coefficients — making a
    # pure mean difference look like a spatial-structure difference.
    b_mean = B.mean(axis=0)
    B = B - b_mean
    k = rbf.k
    spatial_cols = [f"S{j}" for j in range(k)]
    for j in range(k):
        d[spatial_cols[j]] = B[:, j]
    spatial_terms = " + ".join(spatial_cols)
    spatial_set = set(spatial_cols)

    factors = _present_factors(d, condition_factors)
    base_terms = " + ".join(f"C({f})" for f in factors) or "1"
    n_sess = d['session_id'].nunique()
    print(f"[config] n={len(d)} rows, {n_sess} sessions, {d['spec_uid'].nunique()} "
          f"unique specs ({n_repeats} trial-type repeat rows); factors={factors}; "
          f"K={k} basis fns; within-session OLS + cluster-robust(session)")

    # Q1: spatial structure beyond condition + session.
    struct = _within_wald(
        d, f"{VALUE_COL} ~ {base_terms} + {spatial_terms}",
        block_is=lambda c: c in spatial_set, group_col='session_id')
    pooled_coef = _pooled_spatial_coef(d, spatial_cols, base_terms)
    results = {'lrt_structure': struct, 'pooled_coef': pooled_coef, 'rbf': rbf,
               'scx': scx, 'scy': scy, 'k': k, 'b_mean': b_mean, 'data': d,
               'x_col': x_col, 'y_col': y_col, 'interactions': {}}
    print("\n=== Q1: is there spatial structure beyond condition + session? ===")
    if struct is not None:
        s, dfree, p = struct
        print(f"    Wald chi2({dfree}) = {s:.2f}   p = {p:.4g}   "
              f"{'-> structure' if p < 0.05 else '-> no evidence of structure'}")
    else:
        print("    not identifiable (surface has no within-session variation / rank-deficient)")

    for mod in moderators:
        key, fcol, others = _resolve_moderator(d, mod, factors)
        if key is None:
            continue
        levels = [lv for lv in d[fcol].dropna().unique() if int((d[fcol] == lv).sum()) >= 8]
        if len(levels) < 2:
            print(f"\n[{key}] <2 levels with >= 8 specs; skipping")
            continue
        other_mains = " + ".join(f"C({f})" for f in others)

        # Per-level fit + a SEPARATE structure test *within each level* — this is the
        # "does THIS trial_type × polarity combo have spatial structure?" question,
        # one independent Wald test per panel (session-controlled on that combo's
        # own specs), which is what the maps actually show.
        coef_by_level = {}
        struct_by_level = {}
        for lv in levels:
            sub = d[d[fcol] == lv]
            c = _pooled_spatial_coef(sub, spatial_cols, other_mains)
            if c is not None:
                coef_by_level[lv] = c
            rhs = " + ".join(t for t in (other_mains, spatial_terms) if t)
            struct_by_level[lv] = _within_wald(
                sub, f"{VALUE_COL} ~ {rhs}",
                block_is=lambda c: c in spatial_set, group_col='session_id')

        inter = " + ".join(f"{s}:C({fcol})" for s in spatial_cols)
        reduced_mains = " + ".join(t for t in (other_mains, f"C({fcol})") if t)
        wald = _within_wald(
            d, f"{VALUE_COL} ~ {reduced_mains} + {spatial_terms} + {inter}",
            block_is=lambda c: ':' in c, group_col='session_id')
        results['interactions'][key] = {'lrt': wald, 'factor_col': fcol,
                                        'levels': levels, 'coef_by_level': coef_by_level,
                                        'struct_by_level': struct_by_level}
        print(f"\n=== structure WITHIN each {key} combo (independent test per panel) ===")
        for lv in levels:
            r = struct_by_level.get(lv)
            lbl = _level_label(fcol, lv)
            if r is not None:
                s0, df0, p0 = r
                print(f"    {lbl:<32} Wald chi2({df0}) = {s0:6.2f}   p = {p0:.4g}   "
                      f"{'-> structured' if p0 < 0.05 else '-> no evidence'}")
            else:
                print(f"    {lbl:<32} not identifiable within session")
        print(f"\n=== Q2: does the structure differ by {key}? ===")
        if wald is not None:
            s2, df2, p2 = wald
            print(f"    Wald chi2({df2}) = {s2:.2f}   p = {p2:.4g}   "
                  f"{'-> structure differs' if p2 < 0.05 else '-> no evidence it differs'}")
        else:
            print("    not testable (too many params for the data, or the factor "
                  "doesn't vary within session) — maps below are descriptive")

    _print_summary(results)
    x_label = X_LABELS.get(x_col, x_col)
    for key in (list(results['interactions'].keys()) or [None]):
        out_path = None
        if save_dir:
            tag = _slug(key) if key else 'pooled'
            out_path = os.path.join(save_dir, f"mixed_effects_surface_{tag}_vs_{_slug(x_col)}.png")
        plot_model_surfaces(results, key, x_label=x_label,
                            y_label='corr half-distance (µm)', output_path=out_path)
    return results


def _print_summary(results):
    def _row(name, res):
        if res is None:
            return {'test': name, 'chi2': None, 'df': None, 'p': None}
        s, dfree, p = res
        return {'test': name, 'chi2': round(s, 2), 'df': dfree, 'p': round(p, 4)}
    rows = [_row('spatial structure', results['lrt_structure'])]
    for mod in results['interactions']:
        rows.append(_row(f'structure × {mod}', results['interactions'][mod]['lrt']))
    print("\n=== Wald test summary ===")
    with pd.option_context('display.width', 160):
        print(pd.DataFrame(rows).to_string(index=False))


# ---------------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------------

def _mod_label(mod, level):
    short = {'polarity': {'PositiveFirst': 'anodic', 'NegativeFirst': 'cathodic'},
             'waveform': {'Biphasic': 'biphasic',
                          'BiphasicWithInterphaseDelay': 'biphasic+delay'}}
    return short.get(mod, {}).get(level, str(level))


def _level_label(fcol, lv):
    return str(lv) if '__x__' in fcol else _mod_label(fcol, lv)


def plot_model_surfaces(results, key, *, x_label, y_label, output_path=None):
    """Pooled fitted effect map + one map per condition level (each fit on its own
    specs) + (2-level only) their difference. Red = positive, blue = negative; grey =
    no data. Titles carry the plain-language verdict from the Wald tests."""
    rbf, scx, scy = results['rbf'], results['scx'], results['scy']
    d, k = results['data'], results['k']
    b_mean = results['b_mean']
    x_col, y_col = results['x_col'], results['y_col']
    xr = (float(d[x_col].min()), float(d[x_col].max()))
    yr = (float(d[y_col].min()), float(d[y_col].max()))
    gx, gy, shape, Bg, gcoords = _surface_grid(rbf, scx, scy, xr, yr)
    # Coefficients were fitted on CENTRED basis columns (B - b_mean), so the drawn
    # surface must subtract the same b_mean. It then represents spatial DEVIATION
    # from the mean level — the mean itself is shown separately per panel.
    Bg = Bg - b_mean

    def _std(sub):
        return np.column_stack([scx.transform(sub[x_col]), scy.transform(sub[y_col])])

    keep = _support_keep(gcoords, _std(d)).reshape(shape)

    def _surf(coef):
        if coef is None:
            return np.full(shape, np.nan)
        return np.where(keep, (Bg @ coef).reshape(shape), np.nan)

    def _struct_tag(r):
        if r is None:
            return "structure: n/a"
        p = r[2]
        return f"structure p = {p:.2g} {'✓ structured' if p < 0.05 else '(ns)'}"

    struct = results['lrt_structure']
    pooled_title = 'pooled — single shared surface'
    if struct is not None:
        pooled_title += f"\nshared-surface {_struct_tag(struct)}"
    panels = [(pooled_title, _surf(results['pooled_coef']), d)]
    info = results['interactions'].get(key) if key else None
    if info is not None:
        fcol, cbl = info['factor_col'], info['coef_by_level']
        sbl = info.get('struct_by_level', {})
        levels = [lv for lv in info['levels'] if lv in cbl]
        for lv in levels:
            title = f"{_level_label(fcol, lv)}\n{_struct_tag(sbl.get(lv))}"
            panels.append((title, _surf(cbl[lv]), d[d[fcol] == lv]))
        if len(levels) == 2:
            panels.append((f"difference:\n{_level_label(fcol, levels[0])} − "
                           f"{_level_label(fcol, levels[1])}",
                           _surf(cbl[levels[0]] - cbl[levels[1]]), None))

    finite = [p[1][np.isfinite(p[1])] for p in panels if np.isfinite(p[1]).any()]
    allv = np.concatenate(finite) if finite else np.array([0.0])
    vmax = max(float(np.abs(allv).max()) if allv.size else 1.0, 1e-6)

    n = len(panels)
    ncols = min(4, n)
    nrows = int(np.ceil(n / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(4.5 * ncols, 4.4 * nrows),
                             squeeze=False, constrained_layout=True)
    mesh = None
    for i, (title, surf, pts) in enumerate(panels):
        ax = axes[i // ncols][i % ncols]
        ax.set_facecolor('#eeeeee')
        mesh = ax.pcolormesh(gx, gy, np.ma.masked_invalid(surf), cmap='RdBu_r',
                             vmin=-vmax, vmax=vmax, shading='auto')
        if pts is not None:
            ax.scatter(pts[x_col], pts[y_col], s=10, c='black', alpha=0.4, linewidths=0)
            # Show the MEAN effect as text — the surface is the spatial DEVIATION
            # only, so the overall red/blue level of a condition lives here, not in
            # the map. This is what keeps "Hyp positive / Delta negative" from
            # masquerading as a difference in spatial pattern.
            title = f"{title}\nmean effect {pts[VALUE_COL].mean():+.0f}% (n={len(pts)})"
        ax.set_title(title, fontsize=9)
        if i // ncols == nrows - 1:
            ax.set_xlabel(x_label, fontsize=9)
        if i % ncols == 0:
            ax.set_ylabel(y_label, fontsize=9)
    for j in range(n, nrows * ncols):
        axes[j // ncols][j % ncols].axis('off')

    if mesh is not None:
        cbar = fig.colorbar(mesh, ax=axes.ravel().tolist(), shrink=0.6, pad=0.02)
        cbar.set_label('fitted estim effect (ON − OFF %)\nred = positive, blue = negative',
                       fontsize=9)

    if struct is not None:
        p_s = struct[2]
        sub = (f"One shared surface across all conditions?  p = {p_s:.3g}  →  "
               f"{'YES' if p_s < 0.05 else 'no — structure is condition-specific (see per-panel tests)'}")
    else:
        sub = "One shared surface across all conditions?  not identifiable within session"
    if info is not None:
        lrt = info.get('lrt')
        if lrt is not None:
            p_i = lrt[2]
            sub += (f"      |      Differs by {key}?  p = {p_i:.3g}  →  "
                    f"{'YES' if p_i < 0.05 else 'no significant difference'}")
        else:
            sub += f"      |      Differs by {key}?  not testable — maps are descriptive"
    fig.suptitle(f"Model-estimated estim effect across current × half-distance space"
                 f"{(' by ' + key) if key else ''}\n{sub}",
                 fontsize=11, fontweight='bold')
    fig.text(0.5, -0.02,
             "Each map = the model's estimated effect at each point (grey = no data). "
             "p < 0.05 means the pattern is real, not noise.",
             ha='center', fontsize=9, color='#444444')
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        fig.savefig(output_path, dpi=150, bbox_inches='tight')
        fig.savefig(output_path.rsplit('.', 1)[0] + '.svg', bbox_inches='tight')
        print(f"Saved surface figure to {output_path}")
    plt.show()
    return fig


def main():
    """Session-controlled test of spatial structure of the estim effect in
    (current_per_second × corr half-distance) space, and whether it differs by
    polarity / trial_type / their combination. Uses the shared COMPARISON_* config."""
    run_mixed_structure_test(
        trial_types=_analysis_trial_types(),   # drops Removed Trial / Coherence
        x_col='current_per_second', y_col=HALFDIST_COL,
        condition_factors=CONDITION_FACTORS, moderators=MODERATORS,
        start_session_id=COMPARISON_START_SESSION_ID,
        exclude_session_ids=COMPARISON_EXCLUDE_SESSION_IDS,
        effect_metric=COMPARISON_METRIC,
        base_required_conditions=COMPARISON_REQUIRED_CONDITIONS or None,
        min_on_trials=COMPARISON_MIN_ON_TRIALS,
        save_dir=COMPARISON_SAVE_DIR,
    )


if __name__ == '__main__':
    main()
