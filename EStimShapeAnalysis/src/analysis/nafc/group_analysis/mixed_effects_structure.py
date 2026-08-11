"""
Session-controlled test of spatial structure in the estim effect over
(current_per_second × corr half-distance) space — the model-based companion to the
permutation Moran's I in ``moran_effect_structure``.

**The one question this asks.** For each trial_type × polarity GROUP separately:
*does the estim effect have spatial structure in the current × half-distance plane?*
One independent test per group. Nothing about trial_type alone, polarity alone, or
whether the groups differ from each other — just per-group structure.

**How the surface + test work.** Within a group we fit a flexible 2-D surface
s(current, half_distance) — a small low-rank radial-basis expansion (columns
S0..S{K-1}) — and ask whether that surface block jointly matters, i.e. whether the
effect varies with position beyond a flat level.

**How session is controlled (and why not a mixed model).** A proper mixed model
(session random intercept) is the textbook tool, but statsmodels' MixedLM is
numerically fragile here — with a flexible basis on modest, clustered data it hits
singular random-effect covariances and returns NaN. So we use the robust
fixed-effects equivalent, all *within each group*:

  * WITHIN-SESSION demeaning (subtract each session's mean from y and every
    predictor) — removes session baselines exactly, like a session fixed effect,
    with no variance component to estimate. (A surface with no within-session
    variation is not identifiable this way; reported as "not identifiable".)
  * CLUSTER-ROBUST standard errors by session — valid under residual within-session
    correlation (incl. the trial_type repeats nested in session).
  * A WALD test on the surface coefficient block — the joint "does position matter"
    test, robust to the clustering.

The plot: one fitted effect map per group, each carrying its own structure p-value.
The basis is CENTRED, so a map shows spatial DEVIATION from the group's mean level;
the mean effect is printed separately in each panel title (so an overall red/blue
level is never mistaken for a spatial pattern).

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
# The groups we test independently. Each distinct combination of these factors is
# one group with its own structure test + map.
GROUP_FACTORS = ('trial_type', 'polarity')
# Minimum specs in a group to attempt a fit.
MIN_GROUP_SPECS = 8
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

def _pooled_spatial_coef(sub, spatial_cols):
    """Plain OLS spatial coefficients (for drawing a fitted surface). None on failure."""
    import statsmodels.api as sm
    import patsy
    rhs = " + ".join(spatial_cols)
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

def _group_label(g):
    """Pretty a 'Trial Type | Polarity' group key (maps polarity tokens)."""
    pol = {'PositiveFirst': 'anodic', 'NegativeFirst': 'cathodic'}
    return " | ".join(pol.get(tok.strip(), tok.strip()) for tok in str(g).split('|'))


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

def run_group_structure_test(trial_types=None, *, x_col='current_per_second',
                             y_col=HALFDIST_COL, group_factors=GROUP_FACTORS,
                             n_per_axis=N_PER_AXIS, min_group_specs=MIN_GROUP_SPECS,
                             start_session_id=None, exclude_session_ids=None,
                             effect_metric=COMPARISON_METRIC, base_required_conditions=None,
                             min_on_trials=COMPARISON_MIN_ON_TRIALS, save_dir=None):
    """For each trial_type × polarity group, an independent within-session
    fixed-effects OLS + cluster-robust Wald test of spatial structure in the
    (x_col × y_col) plane. Prints a per-group table and plots one map per group.
    Returns a results dict."""
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

    gfactors = [f for f in group_factors if f in points.columns]
    keep = [x_col, y_col, VALUE_COL, 'session_id', 'estim_spec_id'] + gfactors
    d = points[keep].dropna(subset=[x_col, y_col, VALUE_COL, 'session_id'] + gfactors).copy()
    d = d.reset_index(drop=True)
    if len(d) < 20:
        print(f"Only {len(d)} rows with complete data — too few for a stable fit.")
        return {}

    # Standardise the plane and build a CENTRED basis (shared across groups so all
    # maps live on the same coordinates / colour scale). Centring makes the surface
    # capture spatial DEVIATION only — the group mean is reported separately.
    scx, scy = _Scaler().fit(d[x_col]), _Scaler().fit(d[y_col])
    coords = np.column_stack([scx.transform(d[x_col]), scy.transform(d[y_col])])
    rbf = SpatialRBF(n_per_axis=n_per_axis).fit(coords)
    B = rbf.transform(coords)
    b_mean = B.mean(axis=0)
    B = B - b_mean
    k = rbf.k
    spatial_cols = [f"S{j}" for j in range(k)]
    for j in range(k):
        d[spatial_cols[j]] = B[:, j]
    spatial_terms = " + ".join(spatial_cols)
    spatial_set = set(spatial_cols)

    d['__group__'] = d[gfactors].astype(str).agg('|'.join, axis=1)
    groups = [g for g in sorted(d['__group__'].unique())
              if int((d['__group__'] == g).sum()) >= min_group_specs]
    n_sess = d['session_id'].nunique()
    print(f"[config] n={len(d)} rows, {n_sess} sessions, K={k} basis fns; "
          f"grouping by {gfactors}; within-session OLS + cluster-robust(session)")

    results = {'rbf': rbf, 'scx': scx, 'scy': scy, 'k': k, 'b_mean': b_mean,
               'data': d, 'x_col': x_col, 'y_col': y_col, 'groups': {}}
    print("\n=== spatial structure WITHIN each group (independent test each) ===")
    for g in groups:
        sub = d[d['__group__'] == g]
        coef = _pooled_spatial_coef(sub, spatial_cols)
        struct = _within_wald(sub, f"{VALUE_COL} ~ {spatial_terms}",
                              block_is=lambda c: c in spatial_set, group_col='session_id')
        results['groups'][g] = {'coef': coef, 'struct': struct, 'sub': sub}
        lbl = _group_label(g)
        if struct is not None:
            s0, df0, p0 = struct
            print(f"    {lbl:<28} n={len(sub):<4} Wald chi2({df0}) = {s0:6.2f}   "
                  f"p = {p0:.4g}   {'-> structured' if p0 < 0.05 else '-> no evidence'}")
        else:
            print(f"    {lbl:<28} n={len(sub):<4} not identifiable within session")

    _print_summary(results)
    x_label = X_LABELS.get(x_col, x_col)
    out_path = None
    if save_dir:
        out_path = os.path.join(save_dir, f"group_structure_surfaces_vs_{_slug(x_col)}.png")
    plot_group_surfaces(results, x_label=x_label,
                        y_label='corr half-distance (µm)', output_path=out_path)
    return results


def _print_summary(results):
    rows = []
    for g, info in results['groups'].items():
        res = info['struct']
        if res is None:
            rows.append({'group': _group_label(g), 'n': len(info['sub']),
                         'chi2': None, 'df': None, 'p': None, 'structured?': 'n/a'})
        else:
            s, dfree, p = res
            rows.append({'group': _group_label(g), 'n': len(info['sub']),
                         'chi2': round(s, 2), 'df': dfree, 'p': round(p, 4),
                         'structured?': 'YES' if p < 0.05 else 'no'})
    print("\n=== per-group structure summary ===")
    with pd.option_context('display.width', 160):
        print(pd.DataFrame(rows).to_string(index=False))


# ---------------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------------

def plot_group_surfaces(results, *, x_label, y_label, output_path=None):
    """One fitted effect map per group, each carrying its own structure p-value.
    Red = positive, blue = negative deviation from the group mean; grey = no data.
    The group's mean effect is printed in the title (not baked into the map)."""
    rbf, scx, scy = results['rbf'], results['scx'], results['scy']
    d, b_mean = results['data'], results['b_mean']
    x_col, y_col = results['x_col'], results['y_col']
    xr = (float(d[x_col].min()), float(d[x_col].max()))
    yr = (float(d[y_col].min()), float(d[y_col].max()))
    gx, gy, shape, Bg, gcoords = _surface_grid(rbf, scx, scy, xr, yr)
    # Coefficients were fitted on CENTRED basis columns (B - b_mean), so the drawn
    # surface subtracts the same b_mean and represents spatial DEVIATION from the
    # mean level — the mean itself is shown in each title.
    Bg = Bg - b_mean

    def _std(sub):
        return np.column_stack([scx.transform(sub[x_col]), scy.transform(sub[y_col])])

    def _surf(coef, sub):
        keep = _support_keep(gcoords, _std(sub)).reshape(shape)
        if coef is None:
            return np.full(shape, np.nan)
        return np.where(keep, (Bg @ coef).reshape(shape), np.nan)

    def _tag(res):
        if res is None:
            return "structure: n/a"
        p = res[2]
        return f"structure p = {p:.2g} {'✓ structured' if p < 0.05 else '(ns)'}"

    panels = []
    for g, info in results['groups'].items():
        sub = info['sub']
        title = (f"{_group_label(g)}\n{_tag(info['struct'])}\n"
                 f"mean effect {sub[VALUE_COL].mean():+.0f}% (n={len(sub)})")
        panels.append((title, _surf(info['coef'], sub), sub))
    if not panels:
        print("No groups with enough data to plot.")
        return None

    finite = [p[1][np.isfinite(p[1])] for p in panels if np.isfinite(p[1]).any()]
    allv = np.concatenate(finite) if finite else np.array([0.0])
    vmax = max(float(np.abs(allv).max()) if allv.size else 1.0, 1e-6)

    n = len(panels)
    ncols = min(4, n)
    nrows = int(np.ceil(n / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(4.5 * ncols, 4.6 * nrows),
                             squeeze=False, constrained_layout=True)
    mesh = None
    for i, (title, surf, pts) in enumerate(panels):
        ax = axes[i // ncols][i % ncols]
        ax.set_facecolor('#eeeeee')
        mesh = ax.pcolormesh(gx, gy, np.ma.masked_invalid(surf), cmap='RdBu_r',
                             vmin=-vmax, vmax=vmax, shading='auto')
        ax.scatter(pts[x_col], pts[y_col], s=10, c='black', alpha=0.4, linewidths=0)
        ax.set_title(title, fontsize=9)
        if i // ncols == nrows - 1:
            ax.set_xlabel(x_label, fontsize=9)
        if i % ncols == 0:
            ax.set_ylabel(y_label, fontsize=9)
    for j in range(n, nrows * ncols):
        axes[j // ncols][j % ncols].axis('off')

    if mesh is not None:
        cbar = fig.colorbar(mesh, ax=axes.ravel().tolist(), shrink=0.6, pad=0.02)
        cbar.set_label('fitted estim effect deviation (ON − OFF %)\n'
                       'red = positive, blue = negative', fontsize=9)

    fig.suptitle("Does the estim effect have spatial structure within each "
                 "trial_type × polarity group?\n"
                 "Each map is fit on that group's own specs; p < 0.05 → the effect "
                 "varies with position (not just noise).",
                 fontsize=11, fontweight='bold')
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        fig.savefig(output_path, dpi=150, bbox_inches='tight')
        fig.savefig(output_path.rsplit('.', 1)[0] + '.svg', bbox_inches='tight')
        print(f"Saved surface figure to {output_path}")
    plt.show()
    return fig


def main():
    """Per-group (trial_type × polarity) test of whether the estim effect has spatial
    structure in (current_per_second × corr half-distance) space. Uses the shared
    COMPARISON_* config."""
    run_group_structure_test(
        trial_types=_analysis_trial_types(),   # drops Removed Trial / Coherence
        x_col='current_per_second', y_col=HALFDIST_COL,
        group_factors=GROUP_FACTORS,
        start_session_id=COMPARISON_START_SESSION_ID,
        exclude_session_ids=COMPARISON_EXCLUDE_SESSION_IDS,
        effect_metric=COMPARISON_METRIC,
        base_required_conditions=COMPARISON_REQUIRED_CONDITIONS or None,
        min_on_trials=COMPARISON_MIN_ON_TRIALS,
        save_dir=COMPARISON_SAVE_DIR,
    )


if __name__ == '__main__':
    main()
