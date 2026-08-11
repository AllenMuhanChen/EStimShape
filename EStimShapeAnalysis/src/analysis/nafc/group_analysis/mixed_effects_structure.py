"""
Mixed-effects (GAMM-style) test of spatial structure in the estim effect over
(current_per_second × corr half-distance) space — the model-based companion to
the permutation Moran's I in ``moran_effect_structure``.

Instead of shuffling, we MODEL the nuisance and test nested models:

    fixed:  condition main effects (polarity, waveform, trial_type)
          + a flexible 2-D spatial surface s(current, half_distance),
            built as a low-rank radial-basis expansion (columns S0..S{K-1})
    random: (1 | session)                        — session baseline offset
          + (1 | spec) nested in session         — handles the trial_type repeats
                                                    (same spec appears once per trial
                                                    type at the same position)

Two questions, each a likelihood-ratio test between nested models (fit by ML):

  Q1  "Is there spatial structure beyond condition + session?"
        M1 (condition + spatial) vs M0 (condition only).     LRT on the S-columns.

  Q2  "Does the structure DIFFER by a condition (polarity / trial_type)?"
        M2 (M1 + s(...) : condition) vs M1.                  LRT on the interaction.
      A flat surface for one level and a bumpy one for another IS a difference the
      test detects — this is the "does condition influence the structure" question.

Why this instead of (or beside) the permutation test: the session random intercept
soaks up per-session baselines (partial pooling — robust to small sessions), so it
keeps ALL the data and is better powered than a within-session shuffle when the
condition cells are thin. Caveats it does NOT remove: you can only compare
surfaces where the conditions OVERLAP in the plane, interactions need more data
than main effects (an n.s. interaction = "couldn't tell", not "same"), and this is
a low-rank regression-spline surface (unpenalized), so keep the basis modest.

Needs statsmodels + patsy + scipy. Run this file (shared COMPARISON_* config).
Prints the LRT table and plots the model's fitted spatial surface(s).
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

# Spatial basis size: N_PER_AXIS² radial basis functions over the standardised
# plane. 3 -> 9 columns; keep small so the (unpenalised) surface can't overfit.
N_PER_AXIS = 3
RBF_SPREAD = 1.4          # kernel width as a multiple of the centre spacing
VALUE_COL = 'effect_size'
CONDITION_FACTORS = ('polarity', 'waveform', 'trial_type')   # fixed main effects
MODERATORS = ('polarity', 'trial_type')                       # interactions to test


# ---------------------------------------------------------------------------
# Low-rank spatial basis (radial basis functions on the standardised plane)
# ---------------------------------------------------------------------------

class SpatialRBF:
    """A small grid of Gaussian radial basis functions over standardised 2-D
    coordinates — a flexible-but-low-rank surface basis (columns S0..S{K-1})."""

    def __init__(self, n_per_axis=N_PER_AXIS, spread=RBF_SPREAD):
        self.n_per_axis = n_per_axis
        self.spread = spread

    def fit(self, coords):
        qs = np.linspace(0.15, 0.85, self.n_per_axis)
        cx = np.quantile(coords[:, 0], qs)
        cy = np.quantile(coords[:, 1], qs)
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
    """z-score with stored mean/std so a prediction grid uses the same scaling."""

    def fit(self, a):
        a = np.asarray(a, dtype=float)
        self.mean = float(a.mean())
        self.std = float(a.std()) or 1.0
        return self

    def transform(self, a):
        return (np.asarray(a, dtype=float) - self.mean) / self.std


# ---------------------------------------------------------------------------
# Model fitting + likelihood-ratio test
# ---------------------------------------------------------------------------

def _present_factors(d, factors):
    """Categorical factors present in d with >1 level (usable as fixed effects)."""
    return [f for f in factors if f in d.columns and d[f].dropna().nunique() > 1]


def _fit_mixed(formula, d, *, group_col='session_id', vc=None):
    """Fit a linear mixed model (ML, so LRTs on fixed effects are valid). Falls back
    to a session-only random intercept if the variance-component fit fails."""
    import statsmodels.formula.api as smf
    try:
        md = smf.mixedlm(formula, d, groups=d[group_col], vc_formula=vc)
        return md.fit(reml=False, method='lbfgs', maxiter=300)
    except Exception as exc:
        if vc is not None:
            print(f"    (spec variance-component fit failed: {exc}; "
                  f"retrying with session random intercept only)")
            md = smf.mixedlm(formula, d, groups=d[group_col])
            return md.fit(reml=False, method='lbfgs', maxiter=300)
        raise


def _lrt(full, reduced):
    """Likelihood-ratio test of nested models (full nests reduced); df = added fixed
    params. Returns (chi2 stat, df, p)."""
    from scipy.stats import chi2
    stat = 2.0 * (full.llf - reduced.llf)
    df = int(len(full.fe_params) - len(reduced.fe_params))
    if df <= 0 or not np.isfinite(stat) or stat < 0:
        return float(stat), df, float('nan')
    return float(stat), df, float(chi2.sf(stat, df))


# ---------------------------------------------------------------------------
# Fitted-surface prediction (for the plot)
# ---------------------------------------------------------------------------

def _spatial_coef(res, k):
    return np.array([float(res.fe_params.get(f"S{j}", 0.0)) for j in range(k)])


def _interaction_coef(res, k, factor, level):
    """Coefficients of the S{j}:C(factor)[T.level] interaction terms (0 if absent —
    e.g. for the reference level)."""
    out = []
    for j in range(k):
        name = None
        for n in res.fe_params.index:
            if f"S{j}" in n and factor in n and f"{level}]" in n and ':' in n:
                name = n
                break
        out.append(float(res.fe_params[name]) if name else 0.0)
    return np.array(out)


def _surface_grid(rbf, scx, scy, xr, yr, gridsize=60):
    gx = np.linspace(xr[0], xr[1], gridsize)
    gy = np.linspace(yr[0], yr[1], gridsize)
    GX, GY = np.meshgrid(gx, gy)
    coords = np.column_stack([scx.transform(GX.ravel()), scy.transform(GY.ravel())])
    B = rbf.transform(coords)                       # (gridsize², K)
    return gx, gy, GX.shape, B


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_mixed_structure_test(trial_types=None, *, x_col='current_per_second',
                             y_col=HALFDIST_COL, condition_factors=CONDITION_FACTORS,
                             moderators=MODERATORS, n_per_axis=N_PER_AXIS,
                             start_session_id=None, exclude_session_ids=None,
                             effect_metric=COMPARISON_METRIC, base_required_conditions=None,
                             min_on_trials=COMPARISON_MIN_ON_TRIALS, save_dir=None):
    """Fit the mixed-effects models and run the LRTs (spatial structure; structure ×
    moderator). Prints a results table and plots the fitted surfaces. Returns a dict
    of results."""
    try:
        import statsmodels.formula.api as smf  # noqa: F401
        import patsy  # noqa: F401
        from scipy.stats import chi2  # noqa: F401
    except Exception as exc:
        print(f"This test needs statsmodels + patsy + scipy ({exc}). "
              f"Install with: pip install statsmodels patsy scipy")
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
    if len(d) < 20:
        print(f"Only {len(d)} specs with complete data — too few for a stable fit.")
        return {}
    d['spec_uid'] = (d['session_id'].astype(str) + '_' +
                     d['estim_spec_id'].astype(int).astype(str))
    has_repeats = bool(d['spec_uid'].duplicated().any())

    # Standardised coords + spatial basis.
    scx, scy = _Scaler().fit(d[x_col]), _Scaler().fit(d[y_col])
    coords = np.column_stack([scx.transform(d[x_col]), scy.transform(d[y_col])])
    rbf = SpatialRBF(n_per_axis=n_per_axis).fit(coords)
    B = rbf.transform(coords)
    k = rbf.k
    s_cols = [f"S{j}" for j in range(k)]
    for j in range(k):
        d[s_cols[j]] = B[:, j]

    factors = _present_factors(d, condition_factors)
    base_terms = " + ".join(f"C({f})" for f in factors) or "1"
    spatial_terms = " + ".join(s_cols)
    # (1|spec) nested in session handles the same-spec-across-trial_types repeats.
    vc = {'spec': '0 + C(spec_uid)'} if has_repeats else None
    print(f"[config] MIXED-EFFECTS  n={len(d)} specs, {d['session_id'].nunique()} "
          f"sessions, {d['spec_uid'].nunique()} unique specs; factors={factors}; "
          f"K={k} spatial basis fns; spec-RE={'yes' if vc else 'no'}")

    print("\nFitting M0 (condition only) ...")
    m0 = _fit_mixed(f"{VALUE_COL} ~ {base_terms}", d, vc=vc)
    print("Fitting M1 (condition + spatial surface) ...")
    m1 = _fit_mixed(f"{VALUE_COL} ~ {base_terms} + {spatial_terms}", d, vc=vc)
    stat1, df1, p1 = _lrt(m1, m0)

    results = {'m0': m0, 'm1': m1, 'lrt_structure': (stat1, df1, p1),
               'rbf': rbf, 'scx': scx, 'scy': scy, 'k': k, 'data': d,
               'x_col': x_col, 'y_col': y_col, 'interactions': {}}

    print("\n=== Q1: spatial structure beyond condition + session ===")
    print(f"    LRT(M1 vs M0): chi2({df1}) = {stat1:.2f}   p = {p1:.4g}"
          f"   {'-> structure' if p1 < 0.05 else '-> no evidence of structure'}")

    for mod in moderators:
        if mod not in factors:
            continue
        inter = " + ".join(f"{s}:C({mod})" for s in s_cols)
        print(f"\nFitting M2[{mod}] (M1 + spatial × {mod}) ...")
        m2 = _fit_mixed(f"{VALUE_COL} ~ {base_terms} + {spatial_terms} + {inter}",
                        d, vc=vc)
        stat2, df2, p2 = _lrt(m2, m1)
        results['interactions'][mod] = {'model': m2, 'lrt': (stat2, df2, p2)}
        print(f"=== Q2: does the structure differ by {mod}? ===")
        print(f"    LRT(M2[{mod}] vs M1): chi2({df2}) = {stat2:.2f}   p = {p2:.4g}"
              f"   {'-> structure differs by ' + mod if p2 < 0.05 else '-> no evidence it differs'}")

    _print_summary(results, moderators)
    out_path = (os.path.join(save_dir, f"mixed_effects_surface_vs_{_slug(x_col)}.png")
                if save_dir else None)
    plot_model_surfaces(results, x_label=X_LABELS.get(x_col, x_col),
                        y_label='corr half-distance (µm)', primary_moderator='polarity',
                        output_path=out_path)
    return results


def _print_summary(results, moderators):
    rows = [{'test': 'spatial structure (M1 vs M0)',
             'chi2': round(results['lrt_structure'][0], 2),
             'df': results['lrt_structure'][1],
             'p': results['lrt_structure'][2]}]
    for mod in moderators:
        if mod in results['interactions']:
            s, dfree, p = results['interactions'][mod]['lrt']
            rows.append({'test': f'structure × {mod} (M2 vs M1)',
                         'chi2': round(s, 2), 'df': dfree, 'p': p})
    board = pd.DataFrame(rows)
    print("\n=== Mixed-effects LRT summary ===")
    with pd.option_context('display.width', 160):
        print(board.to_string(index=False))


# ---------------------------------------------------------------------------
# Plot: the model's fitted spatial surface(s)
# ---------------------------------------------------------------------------

def plot_model_surfaces(results, *, x_label, y_label, primary_moderator='polarity',
                        output_path=None):
    """Left: the pooled fitted spatial surface (M1). Right: per-level surfaces of the
    primary moderator (M2), so you SEE whether the structure differs by condition.
    Surfaces are the spatial component of the fitted effect (ON − OFF %)."""
    rbf, scx, scy = results['rbf'], results['scx'], results['scy']
    d, k = results['data'], results['k']
    x_col, y_col = results['x_col'], results['y_col']
    xr = (float(d[x_col].min()), float(d[x_col].max()))
    yr = (float(d[y_col].min()), float(d[y_col].max()))
    gx, gy, shape, Bg = _surface_grid(rbf, scx, scy, xr, yr)

    m1 = results['m1']
    surf_shared = (Bg @ _spatial_coef(m1, k)).reshape(shape)

    panels = [('pooled (M1)', surf_shared, d)]
    mod_info = results['interactions'].get(primary_moderator)
    if mod_info is not None:
        m2 = mod_info['model']
        base = _spatial_coef(m2, k)
        levels = [lv for lv in d[primary_moderator].dropna().unique()]
        for lv in levels:
            coef = base + _interaction_coef(m2, k, primary_moderator, lv)
            panels.append((f"{primary_moderator}={lv} (M2)",
                           (Bg @ coef).reshape(shape),
                           d[d[primary_moderator] == lv]))

    vmax = max(float(np.abs(np.concatenate([p[1].ravel() for p in panels])).max()), 1e-6)
    n = len(panels)
    fig, axes = plt.subplots(1, n, figsize=(4.8 * n, 4.4), squeeze=False,
                             constrained_layout=True)
    mesh = None
    for i, (title, surf, pts) in enumerate(panels):
        ax = axes[0][i]
        mesh = ax.pcolormesh(gx, gy, surf, cmap='RdBu_r', vmin=-vmax, vmax=vmax,
                             shading='auto')
        ax.scatter(pts[x_col], pts[y_col], s=10, c='black', alpha=0.35, linewidths=0)
        ax.set_title(title, fontsize=11)
        ax.set_xlabel(x_label, fontsize=9)
        if i == 0:
            ax.set_ylabel(y_label, fontsize=9)

    if mesh is not None:
        cbar = fig.colorbar(mesh, ax=axes.ravel().tolist(), shrink=0.7, pad=0.02)
        cbar.set_label('fitted spatial effect (ON − OFF %)', fontsize=9)

    s, dfree, p = results['lrt_structure']
    sub = f"structure LRT p={p:.3g}"
    if mod_info is not None:
        s2, df2, p2 = mod_info['lrt']
        sub += f"   |   structure×{primary_moderator} LRT p={p2:.3g}"
    fig.suptitle(f"Mixed-effects fitted spatial surface — effect over "
                 f"(current × half-distance)\n{sub}", fontsize=12, fontweight='bold')
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        fig.savefig(output_path, dpi=150, bbox_inches='tight')
        fig.savefig(output_path.rsplit('.', 1)[0] + '.svg', bbox_inches='tight')
        print(f"Saved mixed-effects surface figure to {output_path}")
    plt.show()
    return fig


def main():
    """Mixed-effects test of spatial structure of the estim effect in
    (current_per_second × corr half-distance) space, and whether it differs by
    polarity / trial_type. Uses the shared COMPARISON_* config."""
    run_mixed_structure_test(
        trial_types=(COMPARISON_TRIAL_TYPES or None),
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
