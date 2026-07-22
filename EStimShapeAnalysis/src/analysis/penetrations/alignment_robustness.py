"""Robustness / identifiability analysis for the trajectory-alignment optimiser.

Motivation
----------
`optimize_trajectory_alignment` has many degrees of freedom (9 global +
3 per-session) and a small number of noisy per-session correlations to fit, so
the objective is under-identified: many different corrections fit almost
equally well, and the "best" answer bounces between local minima / overfits
particular sessions depending on the random seed, softmin beta, and chamber
constraints. A single run therefore can't tell you whether a large correction
is a real anatomical fix or an artefact.

This module runs the optimiser MANY times (silently, no plotting in the middle)
and produces three complementary readouts:

  A. Pareto frontier  — raw correlation vs. correction magnitude measured
     against the TRUE/nominal start (zeros), NOT the random start. The knee is
     the parsimonious answer: most of the achievable raw_r for the smallest
     correction. Points far to the right that only add tiny raw_r are overfits.

  B. Multi-start stability — from randomised global starts under the SAME
     settings, cluster the endpoints. Tight cluster => identifiable; wide
     scatter at equal raw_r => degenerate objective (the "randomness" you see).

  C. Leave-one-session-out cross-validation (optional, the decisive overfitting
     test) — optimise on N-1 sessions, score raw_r on the held-out session. A
     correction that raises in-sample but not held-out raw_r is memorising.

Run it like run_per_session.py: edit the CONFIG block + __main__ and execute.
Nothing is written to the real corrections files; results go to OUT_DIR as a
CSV plus a few summary PNGs.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
from typing import Optional

import numpy as np
import pandas as pd

from clat.util.connection import Connection

from src.analysis.penetrations.pca_predict import TissuePipeline
from src.analysis.penetrations.alignment_optimize import (
    MRI_VIEWER_CONFIG_PATH,
    _OPT_PARAM_NAMES,
    _OPT_X0,
    _apply_chamber_params,
    get_penetration_for_session,
    load_mri_pipeline,
    optimize_trajectory_alignment,
    save_optimized_params,
)
from src.analysis.penetrations.pca_predict import (
    compute_tissue_confidence,
    load_and_perform_pca,
)


# ═══════════════════════════════════════════════════════════════════════════
#  Metrics
# ═══════════════════════════════════════════════════════════════════════════
def sample_shift_mm(mri_pipeline: dict, opt_result: dict,
                    conn: Connection, df_conf: pd.DataFrame) -> float:
    """RMS millimetre displacement of every sampled trajectory point between the
    nominal (zero-correction) pose and the optimised pose (global + per-session).

    This is the physically honest "how far did the correction actually move
    things" — unlike parameter norms, it accounts for the lever arm of chamber
    rotations (a small rz moves a deep sample by several mm). Used as the
    Pareto x-axis.
    """
    from src.mri.chamber import calc_penetration_target

    params = np.asarray(opt_result['params'], dtype=float)
    daz_g, del_g, ddepth_g = params[6], params[7], params[8]
    psc = opt_result.get('per_session_corrections', {}) or {}
    cor_offset = mri_pipeline['cor_offset']

    o0, x0, y0, n0 = _apply_chamber_params(_OPT_X0, mri_pipeline)
    oc, xc, yc, nc = _apply_chamber_params(params, mri_pipeline)

    sq = []
    for sid in df_conf['session_id'].unique():
        pen = get_penetration_for_session(conn, sid)
        if pen is None:
            continue
        depths = df_conf.loc[df_conf['session_id'] == sid,
                             'depth_under_chamber_mm'].values
        if len(depths) == 0 or depths.max() <= 0:
            continue
        sc = psc.get(sid, psc.get(str(sid), {})) or {}
        az, el = pen['az_deg'], pen['el_deg']
        try:
            _, d0, t0 = calc_penetration_target(
                o0, az, el, float(depths.max()) + 1.0, x0, y0, n0, cor_offset)
            p0 = t0 + depths[:, None] * d0[None, :]

            dep_c = depths + ddepth_g + sc.get('ddepth_mm', 0.0)
            _, dc, tc = calc_penetration_target(
                oc, az + daz_g + sc.get('daz_deg', 0.0),
                el + del_g + sc.get('del_deg', 0.0),
                float(dep_c.max()) + 1.0, xc, yc, nc, cor_offset)
            pc = tc + dep_c[:, None] * dc[None, :]
            sq.append(np.sum((pc - p0) ** 2, axis=1))
        except Exception:
            continue
    if not sq:
        return np.nan
    return float(np.sqrt(np.concatenate(sq).mean()))


# A sample counts as 'in brain' when its MRI intensity exceeds this. 0.0 assumes
# a clean brain-extracted volume (exactly 0 outside the brain). Raise it if your
# no-skull volume has a non-zero background so background noise isn't counted as
# brain (a good value is a little above the background level).
INBRAIN_THRESH = 0.0


def inbrain_fraction(mri_pipeline: dict, opt_result: dict,
                     conn: Connection, df_conf: pd.DataFrame,
                     thresh: float = None) -> float:
    """Fraction of ALL trajectory sample points that land on in-brain voxels
    (MRI intensity > thresh) of the (no-skull) MRI, under the optimised pose.

    This is the guard against the degenerate optimum that maximises Pearson r by
    grazing the brain EDGE: such poses hit few positive voxels (most samples fall
    in the 0 region outside the brain) yet still score r~1 because the handful of
    in-brain samples ramp monotonically. A genuine alignment keeps most of each
    penetration inside the brain, so inbrain_fraction ~1; an edge-grazer is low.
    Only meaningful with a brain-extracted MRI (outside-brain voxels == 0).
    """
    from src.mri.chamber import calc_penetration_target
    from scipy.ndimage import map_coordinates

    if thresh is None:
        thresh = INBRAIN_THRESH
    params = np.asarray(opt_result['params'], dtype=float)
    daz_g, del_g, ddepth_g = params[6], params[7], params[8]
    psc = opt_result.get('per_session_corrections', {}) or {}
    data = mri_pipeline['data']
    inv = mri_pipeline['inv_corrected']
    cor_offset = mri_pipeline['cor_offset']
    oc, xc, yc, nc = _apply_chamber_params(params, mri_pipeline)

    tot = 0
    pos = 0
    for sid in df_conf['session_id'].unique():
        pen = get_penetration_for_session(conn, sid)
        if pen is None:
            continue
        depths = df_conf.loc[df_conf['session_id'] == sid,
                             'depth_under_chamber_mm'].values
        if len(depths) == 0 or depths.max() <= 0:
            continue
        sc = psc.get(sid, psc.get(str(sid), {})) or {}
        dep = depths + ddepth_g + sc.get('ddepth_mm', 0.0)
        try:
            _, d, t = calc_penetration_target(
                oc, pen['az_deg'] + daz_g + sc.get('daz_deg', 0.0),
                pen['el_deg'] + del_g + sc.get('del_deg', 0.0),
                float(dep.max()) + 1.0, xc, yc, nc, cor_offset)
            pts = t + dep[:, None] * d[None, :]
            vox = (inv @ np.hstack([pts, np.ones((len(pts), 1))]).T).T[:, :3]
            vals = map_coordinates(data, vox.T, order=1, mode='constant', cval=0.0)
            tot += len(vals)
            pos += int((np.asarray(vals) > thresh).sum())
        except Exception:
            continue
    return float(pos) / tot if tot else np.nan


def _per_session_stats(opt_result: dict) -> tuple[float, float]:
    """(RMS, max) of the per-session correction magnitudes across sessions.

    Magnitude combines the three per-session channels into one scalar per
    session (sqrt(daz^2 + del^2 + ddepth^2), mixed deg/mm — a rough size proxy).
    """
    psc = opt_result.get('per_session_corrections', {}) or {}
    if not psc:
        return 0.0, 0.0
    mags = []
    for c in psc.values():
        mags.append(np.sqrt(c.get('daz_deg', 0.0) ** 2
                            + c.get('del_deg', 0.0) ** 2
                            + c.get('ddepth_mm', 0.0) ** 2))
    mags = np.array(mags)
    return float(np.sqrt((mags ** 2).mean())), float(mags.max())


def _row_from_result(opt_result, mri_pipeline, conn, df_conf, tags: dict) -> dict:
    g = np.asarray(opt_result['params'][:9], dtype=float)
    ps_rms, ps_max = _per_session_stats(opt_result)
    row = dict(tags)
    row.update({
        'raw_after':   float(opt_result['raw_after']),
        'raw_before':  float(opt_result['raw_before']),
        'score_after': float(opt_result['score_after']),
        't_norm_mm':   float(np.linalg.norm(g[:3])),
        'r_norm_deg':  float(np.linalg.norm(g[3:6])),
        'daz_g':       float(g[6]),
        'del_g':       float(g[7]),
        'ddepth_g':    float(g[8]),
        'ps_rms':      ps_rms,
        'ps_max':      ps_max,
        'shift_mm':    sample_shift_mm(mri_pipeline, opt_result, conn, df_conf),
        'inbrain_frac': inbrain_fraction(mri_pipeline, opt_result, conn, df_conf),
    })
    for name, val in zip(_OPT_PARAM_NAMES, g):
        row[name] = float(val)
    # Store the per-session offsets so the correction is reconstructable exactly
    # from the CSV later (keys/values coerced to plain str/float for JSON).
    psc = opt_result.get('per_session_corrections', {}) or {}
    row['per_session_json'] = json.dumps(
        {str(k): {kk: float(vv) for kk, vv in v.items()} for k, v in psc.items()})
    return row


# ═══════════════════════════════════════════════════════════════════════════
#  Data preparation (mirrors run_per_session.run_analysis, minus plotting)
# ═══════════════════════════════════════════════════════════════════════════
def prepare_data(conn, pipeline: TissuePipeline, table_name: str,
                 exclude_sessions, mri_config_path, no_skull_mri_path):
    """Build the df_conf + mri_pipeline the optimiser needs, driven by a
    TissuePipeline (same recipe object used by run_per_session)."""
    df, pca, X_pca, feature_columns, scaler = load_and_perform_pca(
        conn, table_name,
        exclude_sessions=exclude_sessions,
        within_session_normalize=pipeline.within_session_normalize,
        pc_smooth_sigma=pipeline.pc_smooth_sigma,
        n_components=pipeline.n_components,
        varimax_n_components=pipeline.varimax_n_components,
        decomp_method=pipeline.decomp_method,
        use_varimax=pipeline.use_varimax,
        exclude_features=list(pipeline.exclude_features),
    )
    df_conf = compute_tissue_confidence(df, model=pipeline.model)
    mri_pipeline = load_mri_pipeline(mri_config_path, volume_path=no_skull_mri_path)
    return df_conf, mri_pipeline


# ═══════════════════════════════════════════════════════════════════════════
#  One optimiser run (silenced)
# ═══════════════════════════════════════════════════════════════════════════
def _silent_optimize(df_conf, conn, mri_pipeline, **kw):
    """Call optimize_trajectory_alignment with all its console output swallowed."""
    with contextlib.redirect_stdout(io.StringIO()):
        return optimize_trajectory_alignment(df_conf, conn, mri_pipeline, **kw)


def _random_global_start(rng, scale, enabled_mask=None) -> np.ndarray:
    """Randomised 9-vector global start: t (mm), r (deg), daz/del (deg), ddepth (mm).

    Disabled dims (enabled_mask False) are set to 0 so the logged start is
    honest — the optimiser's fixed_globals would zero them anyway.
    """
    x0 = np.zeros(9)
    x0[:3] = rng.uniform(-scale['t'],      scale['t'],      3)   # tx ty tz
    x0[3:6] = rng.uniform(-scale['r'],     scale['r'],      3)   # rx ry rz
    x0[6:8] = rng.uniform(-scale['ang'],   scale['ang'],    2)   # daz del
    x0[8] = rng.uniform(-scale['depth'],   scale['depth'])       # ddepth
    if enabled_mask is not None:
        x0 = np.where(np.asarray(enabled_mask, dtype=bool), x0, 0.0)
    return x0


def fixed_from_enabled(enabled, base_fixed=None) -> dict:
    """Turn an 'enabled global params' list into a fixed_globals dict that
    HARD-FREEZES every disabled global at 0.0.

    This is the clean way to drop daz_deg/del_deg/ddepth_mm (or any global) from
    the search: the optimiser removes the DOF entirely (simplex step ~0, value
    forced each eval) instead of merely soft-penalising it via a tiny
    chamber_param_tolerance — which still lets the optimiser wiggle it into
    overfit corners. Merges with any explicit base_fixed (base wins on conflict).
    """
    fixed = dict(base_fixed or {})
    for name in _OPT_PARAM_NAMES:
        if name not in enabled and name not in fixed:
            fixed[name] = 0.0
    return fixed


def _enabled_mask(enabled) -> np.ndarray:
    return np.array([name in enabled for name in _OPT_PARAM_NAMES], dtype=bool)


# ═══════════════════════════════════════════════════════════════════════════
#  Study A — multi-start Pareto sweep
# ═══════════════════════════════════════════════════════════════════════════
def sweep(df_conf, conn, mri_pipeline, *,
          param_sets, betas, penalties, per_session_opts, n_random_starts,
          start_scale, base_kw, seed=0):
    """Grid over (param_set x beta x chamber_param_penalty x per_session) with n
    random global starts each. Returns a tidy DataFrame, one row per run.

    param_sets : dict {name: [enabled global param names]}. Globals NOT listed
        are hard-frozen at 0 (see fixed_from_enabled) — e.g. an entry
        'rigid': ['tx_mm',...,'rz_deg'] drops daz/del/ddepth from the search, so
        you can compare it head-to-head against the full 9-param model and see
        whether the extra DOF buy real raw_r or just overfit.
    """
    rng = np.random.default_rng(seed)
    rows = []
    base_fixed = base_kw.get('fixed_globals')
    total = (len(param_sets) * len(betas) * len(penalties)
             * len(per_session_opts) * n_random_starts)
    done = 0
    for pset_name, enabled in param_sets.items():
        fixed = fixed_from_enabled(enabled, base_fixed)
        mask = _enabled_mask(enabled)
        n_free = int(mask.sum())
        for beta in betas:
            for pen in penalties:
                for ps in per_session_opts:
                    for k in range(n_random_starts):
                        x0 = (_random_global_start(rng, start_scale, mask)
                              if k > 0 else np.zeros(9))   # k==0 = nominal start
                        kw = dict(base_kw)
                        kw.update(softmin_beta=beta, chamber_param_penalty=pen,
                                  enable_per_session_corrections=ps, x0_override=x0,
                                  fixed_globals=fixed)
                        tags = dict(param_set=pset_name, n_free_global=n_free,
                                    beta=beta, chamber_param_penalty=pen,
                                    per_session=ps, start=k,
                                    start_kind=('nominal' if k == 0 else 'random'))
                        try:
                            res = _silent_optimize(df_conf, conn, mri_pipeline, **kw)
                            row = _row_from_result(res, mri_pipeline, conn, df_conf, tags=tags)
                        except Exception as exc:
                            row = dict(tags, raw_after=np.nan, error=str(exc))
                        rows.append(row)
                        done += 1
                        print(f"  [{done:3d}/{total}] set={pset_name} beta={beta} "
                              f"pen={pen} ps={ps} start={k:2d}  "
                              f"raw={row.get('raw_after', float('nan')):.4f}  "
                              f"shift={row.get('shift_mm', float('nan')):.2f}mm")
    return pd.DataFrame(rows)


def pareto_knee(df: pd.DataFrame, tol=0.01, x='shift_mm', y='raw_after',
                min_inbrain=None, raw_max=None):
    """The parsimonious pick: among runs whose y is within `tol` of the best y,
    the one with the smallest x — 'most raw correlation for the least correction'.

    Degeneracy guards (IMPORTANT — high Pearson r alone is fooled by edge-grazing
    poses that sit mostly OUTSIDE the brain, see inbrain_fraction):
      min_inbrain : drop rows whose inbrain_frac is below this before choosing,
          so the 'best raw' bar is set by genuine in-brain solutions, not
          edge-grazers. Strongly recommended (e.g. 0.9) for no-skull sweeps.
      raw_max     : also drop rows with y above this (a hard 'too good to be
          true' cap) — use if a spurious cluster sits above the real ceiling.
    """
    d = df.dropna(subset=[x, y])
    if min_inbrain is not None and 'inbrain_frac' in d.columns:
        d = d[d['inbrain_frac'].fillna(0.0) >= min_inbrain]
    if raw_max is not None:
        d = d[d[y] <= raw_max]
    if d.empty:
        return None
    y_best = d[y].max()
    near = d[d[y] >= y_best - tol]
    return near.loc[near[x].idxmin()]


# ═══════════════════════════════════════════════════════════════════════════
#  Recover a correction file from a sweep row (the harness itself never writes
#  correction files — only sweep.csv — so this rebuilds one on demand).
# ═══════════════════════════════════════════════════════════════════════════
def pareto_front(df, min_inbrain=None, raw_max=None, x='shift_mm', y='raw_after'):
    """Non-degenerate efficient frontier: the non-dominated rows in (maximise y,
    minimise x) space, after dropping edge-grazers (inbrain_frac < min_inbrain).

    These are exactly the 'highest correlation achievable at each correction
    size' points — no other run gives more raw_after for equal-or-less shift.
    Returned sorted by shift ascending (raw_after therefore strictly increasing).
    """
    d = df.dropna(subset=[x, y]).copy()
    if min_inbrain is not None:
        if 'inbrain_frac' not in d.columns:
            print("  [pareto_front] min_inbrain requested but the sweep has NO "
                  "'inbrain_frac' column (old run) — degenerate edge-grazers CANNOT "
                  "be filtered. Re-run the sweep (or backfill the column). Refusing "
                  "to return possibly-degenerate points.")
            return d.iloc[0:0]
        n0 = len(d)
        d = d[d['inbrain_frac'].fillna(0.0) >= min_inbrain]
        print(f"  [pareto_front] in-brain filter: kept {len(d)}/{n0} rows with "
              f"inbrain_frac >= {min_inbrain}")
        if n0 > 0 and len(d) == n0:
            print("  [pareto_front] WARNING: the filter removed NOTHING — every row "
                  "passes. Either all solutions are genuinely in-brain, or the metric "
                  "is not discriminating (the sweep likely sampled a FULL-SKULL volume; "
                  "set NO_SKULL_MRI in the sweep so outside-brain voxels are 0).")
    if raw_max is not None:
        d = d[d[y] <= raw_max]
    if d.empty:
        return d
    d = d.sort_values([x, y], ascending=[True, False])
    keep, best_y = [], -np.inf
    for idx, r in d.iterrows():
        if r[y] > best_y:
            keep.append(idx)
            best_y = r[y]
    return d.loc[keep]


def chamber_pose(mri_pipeline, params):
    """(origin[3], normal[3]) of the chamber under a global correction vector —
    the physical, interpretable pose used to compare corrections to each other
    (origin distance in mm, normal angle in deg)."""
    o, x, y, n = _apply_chamber_params(np.asarray(params, dtype=float), mri_pipeline)
    return np.asarray(o, dtype=float), np.asarray(n, dtype=float)


def pose_diff(mri_pipeline, params_a, params_b):
    """(translation mm of origin, angle deg between normals) between two poses."""
    oa, na = chamber_pose(mri_pipeline, params_a)
    ob, nb = chamber_pose(mri_pipeline, params_b)
    dpos = float(np.linalg.norm(oa - ob))
    cos = float(np.clip(np.dot(na, nb) / (np.linalg.norm(na) * np.linalg.norm(nb) + 1e-12),
                        -1.0, 1.0))
    return dpos, float(np.degrees(np.arccos(cos)))


def optimize_subset(df_conf, conn, mri_pipeline, session_ids, base_kw, x0_global=None):
    """Run the optimiser (silently) on only the given session_ids, optionally
    warm-started from a global 9-vector (so residual variation across subsets is
    session-driven, not optimiser-local-minimum-driven)."""
    sub = df_conf[df_conf['session_id'].isin(list(session_ids))]
    kw = dict(base_kw)
    if x0_global is not None:
        kw['x0_override'] = np.asarray(x0_global, dtype=float)[:9]
    return _silent_optimize(sub, conn, mri_pipeline, **kw)


def _dedup_frontier(front, eps_shift=0.4, eps_raw=0.01):
    """Drop frontier points that are near-duplicates of an already-kept point
    (within eps in BOTH shift and raw), so candidates never land on top of each
    other. Keeps the first (lower-shift) of each cluster."""
    kept = []
    for idx, r in front.sort_values('shift_mm').iterrows():
        if all(not (abs(r['shift_mm'] - front.loc[k, 'shift_mm']) < eps_shift and
                    abs(r['raw_after'] - front.loc[k, 'raw_after']) < eps_raw)
               for k in kept):
            kept.append(idx)
    return front.loc[kept]


def select_candidates(df, n=3, min_inbrain=0.9, raw_max=None, method='knee'):
    """Pick up to `n` non-degenerate, efficiency-optimal candidates on the Pareto
    frontier — the points with the most raw correlation per unit correction size.

    method:
      'knee'  (default) — rank frontier points by how far they beat the straight
          cheap->expensive tradeoff line (max of raw_norm - shift_norm, i.e. the
          normalised distance above the min->max diagonal). This picks the
          elbow region — high correlation while the shift is still small — NOT
          the useless low-raw far-left corner nor the expensive flat tail.
      'ratio' — rank by raw_after / shift_mm (steepest from the origin); favours
          the very cheapest corrections.
      'span'  — evenly spaced along the frontier (legacy; not efficiency-based).
    Near-duplicate frontier points are merged first so candidates are distinct.
    """
    front = pareto_front(df, min_inbrain=min_inbrain, raw_max=raw_max)
    if front.empty:
        return front
    front = _dedup_frontier(front)
    if len(front) <= n:
        return front.sort_values('shift_mm')

    x = front['shift_mm'].to_numpy(float)
    y = front['raw_after'].to_numpy(float)
    xr = (x.max() - x.min()) or 1.0
    yr = (y.max() - y.min()) or 1.0
    xn, yn = (x - x.min()) / xr, (y - y.min()) / yr

    if method == 'ratio':
        score = y / np.maximum(x, 1e-9)
    elif method == 'span':
        idxs = sorted(set(np.linspace(0, len(front) - 1, n).round().astype(int)))
        return front.iloc[idxs]
    else:  # 'knee'
        score = yn - xn

    top = np.argsort(-score)[:n]
    return front.iloc[sorted(top)].sort_values('shift_mm')


def per_session_raw(mri_pipeline, opt_result, conn, df_conf):
    """Per-session UNWEIGHTED Pearson r for a candidate pose (array over sessions).
    Needs the DB (angles) + df_conf (depths/tissue). Used for consistency stats:
    a high-mean but high-variance candidate fits some sessions and misses others.
    """
    import contextlib
    import io
    from src.analysis.penetrations.alignment_optimize import (
        compute_mri_comparison, compute_trajectory_fit_scores, apply_optimized_pipeline)
    with contextlib.redirect_stdout(io.StringIO()):
        opt_pipeline, daz, del_, ddepth = apply_optimized_pipeline(mri_pipeline, opt_result)
        one = compute_mri_comparison(
            df_conf.copy(), conn, opt_pipeline, daz=daz, del_=del_, ddepth=ddepth,
            per_session_corrections=opt_result.get('per_session_corrections'))
        fs = compute_trajectory_fit_scores(one)
    col = 'fit_score_unweighted' if 'fit_score_unweighted' in fs.columns else 'fit_score'
    return fs[col].dropna().to_numpy()


def candidate_report(cands, mri_pipeline, conn=None, df_conf=None):
    """Build a per-candidate stats table. CSV-derived stats (efficiency ratio,
    in-brain, correction size) always; per-session fit mean/SD/min/worst only if
    conn + df_conf are given (recompute). Returns (stats_df, per_session_dict)."""
    recs, per_sess = [], {}
    for i, (_, r) in enumerate(cands.iterrows(), 1):
        name = f'c{i}'
        rec = dict(
            name=name,
            raw_after=float(r['raw_after']),
            shift_mm=float(r['shift_mm']),
            ratio=float(r['raw_after']) / max(float(r['shift_mm']), 1e-9),
            inbrain=float(r['inbrain_frac']) if pd.notna(r.get('inbrain_frac')) else np.nan,
            t_norm_mm=float(r.get('t_norm_mm', np.nan)),
            ps_max=float(r.get('ps_max', np.nan)),
            beta=r.get('beta'), per_session=r.get('per_session'), param_set=r.get('param_set'),
        )
        if conn is not None and df_conf is not None:
            try:
                rs = per_session_raw(mri_pipeline, opt_result_from_row(r, warn=False), conn, df_conf)
                rec.update(raw_mean=float(np.mean(rs)), raw_std=float(np.std(rs)),
                           raw_min=float(np.min(rs)), n_sess=int(len(rs)))
                per_sess[name] = rs
            except Exception as exc:
                print(f"  per-session stats failed for {name}: {exc}")
        recs.append(rec)
    return pd.DataFrame(recs), per_sess


def plot_candidate_stats(stats_df, per_sess, out_path, min_inbrain=0.9):
    """Multi-panel bar figure of candidate stats: efficiency ratio, raw fit
    mean±SD (consistency), per-session r distribution, worst-session r, in-brain
    fraction, and correction size."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    labels = stats_df['name'].tolist()
    xp = np.arange(len(labels))
    has_ps = 'raw_std' in stats_df.columns and stats_df['raw_std'].notna().any()

    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    axes = axes.ravel()

    axes[0].bar(xp, stats_df['ratio'], color='steelblue')
    axes[0].set_title('efficiency:  raw_after / shift_mm  (higher = better)')

    if has_ps:
        axes[1].bar(xp, stats_df['raw_mean'], yerr=stats_df['raw_std'], capsize=5, color='seagreen')
        axes[1].set_title('raw fit: mean ± SD across sessions\n(shorter bar of error = more consistent)')
    else:
        axes[1].bar(xp, stats_df['raw_after'], color='seagreen')
        axes[1].set_title('raw_after (mean r)\n[per-session SD needs DB]')

    if per_sess:
        axes[2].boxplot([per_sess[n] for n in labels], tick_labels=labels, showmeans=True)
        axes[2].set_title('per-session r distribution\n(tight box = consistent)')
    else:
        axes[2].axis('off')
        axes[2].text(0.5, 0.5, 'per-session distribution\nneeds DB (COMPUTE_PERSESSION)',
                     ha='center', va='center', fontsize=9)

    if has_ps:
        axes[3].bar(xp, stats_df['raw_min'], color='indianred')
        axes[3].set_title('worst-session r (min)\n(higher = no session left behind)')
    else:
        axes[3].axis('off')

    axes[4].bar(xp, stats_df['inbrain'], color='goldenrod')
    axes[4].axhline(min_inbrain, ls='--', color='k', lw=1)
    axes[4].set_ylim(0, 1.02)
    axes[4].set_title('in-brain fraction  (1 = fully in brain)')

    w = 0.38
    axes[5].bar(xp - w / 2, stats_df['shift_mm'], w, label='shift (RMS mm)', color='slategray')
    axes[5].bar(xp + w / 2, stats_df['t_norm_mm'], w, label='|translation| mm', color='darkkhaki')
    axes[5].legend(fontsize=8)
    axes[5].set_title('correction size (smaller = more parsimonious)')

    for ax in axes:
        if ax.has_data():
            ax.set_xticks(xp)
            ax.set_xticklabels(labels)
    fig.suptitle('Candidate statistics', fontsize=13)
    fig.tight_layout()
    fig.savefig(out_path, dpi=140)
    plt.close(fig)


def save_candidates(cands, mri_pipeline, copy_dir=None) -> list:
    """Save each candidate row as its own correction file (suffix _c1.._cN,
    ordered cheapest->highest-raw). Returns list of (row, path)."""
    out = []
    for i, (_, r) in enumerate(cands.iterrows(), 1):
        p = save_correction_from_row(r, mri_pipeline, copy_dir=copy_dir, suffix=f'_c{i}')
        out.append((r, p))
    return out


def opt_result_from_row(row, warn=True) -> dict:
    """Reconstruct a minimal opt_result dict from one sweep-CSV row.

    The 9 global params (tx..ddepth) come straight from the row columns; the
    per-session offsets from the row's per_session_json if present (newer runs).
    Enough for both save_correction_from_row (needs params[:9] for the 4x4) and
    inbrain_fraction / sample_shift_mm (need params + per_session_corrections)."""
    g = np.array([float(row[n]) for n in _OPT_PARAM_NAMES])
    psc = {}
    pj = row.get('per_session_json') if hasattr(row, 'get') else None
    if isinstance(pj, str) and pj:
        try:
            psc = json.loads(pj)
        except Exception:
            psc = {}
    if warn and not psc and bool(row.get('per_session', False)):
        print("  WARNING: this row used per-session corrections but the CSV has no "
              "per_session_json column (older run). Only the GLOBAL pose is used; "
              "per-session angle/depth offsets are omitted.")
    return {
        'params': g,
        'param_names': list(_OPT_PARAM_NAMES),
        'score_before': float(row.get('raw_before', np.nan)),
        'score_after':  float(row.get('raw_after', np.nan)),
        'per_session_corrections': psc,
        'softmin_beta': float(row.get('beta', 5.0)),
    }


def backfill_inbrain(df, mri_pipeline, conn, df_conf, thresh=None):
    """Add/refresh an 'inbrain_frac' column on an existing sweep DataFrame WITHOUT
    re-running the optimisation — only the cheap MRI-sampling per stored pose.

    IMPORTANT: mri_pipeline must be loaded with the BRAIN-EXTRACTED (no-skull)
    volume, so voxels outside the brain are ~0 and the fraction is meaningful.
    Returns the same df with the column filled in (mutated in place too)."""
    vals = []
    n = len(df)
    for i, (_, row) in enumerate(df.iterrows()):
        try:
            res = opt_result_from_row(row, warn=False)
            v = inbrain_fraction(mri_pipeline, res, conn, df_conf, thresh=thresh)
        except Exception as exc:
            print(f"  row {i}: inbrain failed ({exc})")
            v = np.nan
        vals.append(v)
        if (i + 1) % 20 == 0 or i + 1 == n:
            print(f"  backfilled {i + 1}/{n}  (last inbrain={v:.3f})")
    df['inbrain_frac'] = vals
    return df


def save_correction_from_row(row, mri_pipeline, copy_dir=None, suffix='') -> str:
    """Rebuild and save the MRI-viewer chamber-correction JSON from one sweep
    row, via alignment_optimize.save_optimized_params.

    The chamber 4x4 the viewer applies is built purely from the 9 global params
    (tx..ddepth) + the chamber centre, all of which are in the row, so the
    GLOBAL correction is reconstructed EXACTLY. Per-session offsets are taken
    from the row's per_session_json if present (written by newer runs); older
    CSVs lack that column, in which case only the global part is recovered and
    a warning is printed. Apply the saved file with
    alignment_optimize.apply_pca_opt_result(path, mri_pipeline).
    """
    opt_result = opt_result_from_row(row)
    return save_optimized_params(opt_result, mri_pipeline, copy_dir=copy_dir, suffix=suffix)


def save_knee_correction(sweep, mri_pipeline, copy_dir=None, tol=0.01,
                         min_inbrain=None, raw_max=None) -> Optional[str]:
    """Find the parsimony knee in a sweep (DataFrame or path to sweep.csv) and
    write its correction file. Returns the saved path (or None if no knee).

    min_inbrain / raw_max are the degeneracy guards forwarded to pareto_knee —
    set min_inbrain (e.g. 0.9) on no-skull sweeps so edge-grazing poses that
    score high r while sitting outside the brain are excluded."""
    df = pd.read_csv(sweep) if isinstance(sweep, str) else sweep
    knee = pareto_knee(df, tol=tol, min_inbrain=min_inbrain, raw_max=raw_max)
    if knee is None:
        print("  No knee found (no successful runs in the sweep).")
        return None
    print(f"  Knee: raw_r={knee['raw_after']:.4f}  shift={knee['shift_mm']:.2f}mm  "
          f"set={knee.get('param_set')}  beta={knee.get('beta')}  "
          f"pen={knee.get('chamber_param_penalty')}  per_session={knee.get('per_session')}")
    return save_correction_from_row(knee, mri_pipeline, copy_dir=copy_dir)


# ═══════════════════════════════════════════════════════════════════════════
#  Study C — leave-one-session-out cross-validation
# ═══════════════════════════════════════════════════════════════════════════
def loso_cv(df_conf, conn, mri_pipeline, *, base_kw, configs):
    """For each named config, optimise on N-1 sessions and score raw_r on the
    held-out session (per-session corr for the held-out session is 0, since it
    was never fit). Returns a tidy DataFrame with in-sample vs held-out raw_r.

    `configs` : list of (name, kw_overrides) — kw_overrides merged into base_kw.
    Global-only (per_session=False) is strongly recommended here: it is the
    correction that must generalise, and it keeps N optimisations tractable.
    """
    from src.analysis.penetrations.alignment_optimize import (
        compute_mri_comparison, compute_trajectory_fit_scores, apply_optimized_pipeline,
    )
    sessions = list(df_conf['session_id'].unique())
    rows = []
    for name, ov in configs:
        for held in sessions:
            train = df_conf[df_conf['session_id'] != held]
            kw = dict(base_kw); kw.update(ov)
            try:
                res = _silent_optimize(train, conn, mri_pipeline, **kw)
                opt_pipeline, daz, del_, ddepth = apply_optimized_pipeline(mri_pipeline, res)
                # Score the held-out session with the trained GLOBAL correction only.
                one = df_conf[df_conf['session_id'] == held].copy()
                with contextlib.redirect_stdout(io.StringIO()):
                    one = compute_mri_comparison(one, conn, opt_pipeline,
                                                 daz=daz, del_=del_, ddepth=ddepth)
                    fs = compute_trajectory_fit_scores(one)
                held_r = float(fs['fit_score_unweighted'].iloc[0]) if 'fit_score_unweighted' in fs else np.nan
                rows.append(dict(config=name, held_session=held,
                                 insample_raw=float(res['raw_after']),
                                 heldout_raw=held_r,
                                 shift_mm=sample_shift_mm(mri_pipeline, res, conn, train)))
            except Exception as exc:
                rows.append(dict(config=name, held_session=held, error=str(exc)))
            print(f"  LOSO[{name}] held={held}  heldout_raw={rows[-1].get('heldout_raw', float('nan'))}")
    return pd.DataFrame(rows)


# ═══════════════════════════════════════════════════════════════════════════
#  Plots (Agg; guarded)
# ═══════════════════════════════════════════════════════════════════════════
def make_plots(sweep_df: pd.DataFrame, out_dir: str, loso_df: Optional[pd.DataFrame] = None):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    os.makedirs(out_dir, exist_ok=True)
    d = sweep_df.dropna(subset=['shift_mm', 'raw_after'])

    # 1. Pareto: raw_r vs correction magnitude, coloured by in-brain fraction so
    #    edge-grazing degenerate optima (high r, low in-brain) are obvious.
    try:
        has_ib = 'inbrain_frac' in d.columns and d['inbrain_frac'].notna().any()
        fig, ax = plt.subplots(figsize=(7.5, 5.5))
        cvar = d['inbrain_frac'].fillna(0.0) if has_ib else d['beta']
        for ps, mk in [(True, 'o'), (False, 's')]:
            sub = d[d['per_session'] == ps]
            cv = sub['inbrain_frac'].fillna(0.0) if has_ib else sub['beta']
            sc = ax.scatter(sub['shift_mm'], sub['raw_after'], c=cv, marker=mk,
                            cmap='viridis', vmin=(0.0 if has_ib else None),
                            vmax=(1.0 if has_ib else None), s=40, alpha=0.85,
                            label=('with per-session' if ps else 'global only'))
        knee = pareto_knee(d, min_inbrain=(0.9 if has_ib else None))
        if knee is not None:
            ax.scatter([knee['shift_mm']], [knee['raw_after']], s=280,
                       facecolors='none', edgecolors='red', linewidths=2.2,
                       label='parsimony knee (guarded)', zorder=5)
        ax.set_xlabel('correction magnitude  (RMS mm shift of sampled points from nominal)')
        ax.set_ylabel('raw correlation  (mean unweighted Pearson r)')
        ax.set_title('Fit quality vs correction size — knee = most r for least correction')
        ax.legend(fontsize=8)
        fig.colorbar(sc, ax=ax,
                     label=('in-brain fraction (dark = edge-grazer)' if has_ib else 'softmin beta'))
        fig.tight_layout(); fig.savefig(os.path.join(out_dir, 'pareto_fit_vs_correction.png'), dpi=140)
        plt.close(fig)
    except Exception as exc:
        print(f"  pareto plot skipped: {exc}")

    # 2. Multi-start stability: spread of the 6 rigid params across random starts,
    #    per (beta, penalty, per_session) config.
    try:
        rigid = ['tx_mm', 'ty_mm', 'tz_mm', 'rx_deg', 'ry_deg', 'rz_deg']
        rnd = d[d['start_kind'] == 'random']
        grp = rnd.groupby(['param_set', 'beta', 'chamber_param_penalty', 'per_session'])
        stds = grp[rigid + ['raw_after']].std(numeric_only=True)
        fig, ax = plt.subplots(figsize=(9, max(3, 0.4 * len(stds) + 1)))
        im = ax.imshow(stds[rigid].values, aspect='auto', cmap='magma')
        ax.set_xticks(range(len(rigid))); ax.set_xticklabels(rigid, rotation=45, ha='right')
        ax.set_yticks(range(len(stds)))
        ax.set_yticklabels([f'{ps_} b={b} pen={p} ses={s}'
                            for (ps_, b, p, s) in stds.index], fontsize=7)
        ax.set_title('Endpoint spread across random starts (std) — low = identifiable')
        fig.colorbar(im, ax=ax, label='std of optimised param')
        fig.tight_layout(); fig.savefig(os.path.join(out_dir, 'multistart_stability.png'), dpi=140)
        plt.close(fig)
    except Exception as exc:
        print(f"  stability plot skipped: {exc}")

    # 3. LOSO in-sample vs held-out
    if loso_df is not None and 'heldout_raw' in loso_df.columns:
        try:
            fig, ax = plt.subplots(figsize=(6, 5))
            agg = loso_df.dropna(subset=['heldout_raw']).groupby('config').agg(
                insample=('insample_raw', 'mean'), heldout=('heldout_raw', 'mean'),
                shift=('shift_mm', 'mean'))
            x = np.arange(len(agg)); w = 0.38
            ax.bar(x - w / 2, agg['insample'], w, label='in-sample raw_r')
            ax.bar(x + w / 2, agg['heldout'], w, label='held-out raw_r')
            ax.set_xticks(x); ax.set_xticklabels(agg.index, rotation=20, ha='right')
            ax.set_ylabel('mean raw correlation')
            ax.set_title('LOSO cross-validation — gap = overfitting')
            ax.legend()
            fig.tight_layout(); fig.savefig(os.path.join(out_dir, 'loso_crossval.png'), dpi=140)
            plt.close(fig)
        except Exception as exc:
            print(f"  loso plot skipped: {exc}")


# ═══════════════════════════════════════════════════════════════════════════
#  Text summary
# ═══════════════════════════════════════════════════════════════════════════
def summarize(sweep_df: pd.DataFrame) -> str:
    d = sweep_df.dropna(subset=['shift_mm', 'raw_after'])
    lines = ["", "=" * 70, "ROBUSTNESS SUMMARY", "=" * 70]
    if d.empty:
        return "\n".join(lines + ["  (no successful runs)"])

    best = d.loc[d['raw_after'].idxmax()]
    knee = pareto_knee(d)
    lines.append(f"  max raw_r observed : {best['raw_after']:.4f}  "
                 f"(shift={best['shift_mm']:.2f}mm, beta={best['beta']}, "
                 f"pen={best['chamber_param_penalty']}, ps={best['per_session']})")
    if knee is not None:
        lines.append(f"  parsimony knee     : {knee['raw_after']:.4f}  "
                     f"(shift={knee['shift_mm']:.2f}mm, beta={knee['beta']}, "
                     f"pen={knee['chamber_param_penalty']}, ps={knee['per_session']})")
        lines.append(f"    -> the knee recovers {knee['raw_after'] / best['raw_after'] * 100:.1f}% "
                     f"of the best raw_r with {knee['shift_mm'] / max(best['shift_mm'], 1e-9):.2f}x "
                     f"the correction size.")

    # param-set (dimensionality) comparison — does adding daz/del/ddepth buy raw_r?
    if 'param_set' in d.columns:
        lines.append("  -- param set (dimensionality) --")
        for pset in d['param_set'].unique():
            sub = d[d['param_set'] == pset]
            k = pareto_knee(sub)
            n_free = int(sub['n_free_global'].iloc[0]) if 'n_free_global' in sub else -1
            lines.append(f"    {pset:<14s} (n_free={n_free}): best raw_r={sub['raw_after'].max():.4f}, "
                         f"knee raw_r={k['raw_after'] if k is not None else float('nan'):.4f} @ "
                         f"{k['shift_mm'] if k is not None else float('nan'):.2f}mm, "
                         f"median ps_max={sub['ps_max'].median():.2f}")

    # global-only vs +per-session at matched settings
    for ps in sorted(d['per_session'].unique()):
        sub = d[d['per_session'] == ps]
        lines.append(f"  per_session={ps}: best raw_r={sub['raw_after'].max():.4f}, "
                     f"median shift={sub['shift_mm'].median():.2f}mm, "
                     f"median ps_max={sub['ps_max'].median():.2f}")

    # identifiability: spread across random starts within each config
    rnd = d[d['start_kind'] == 'random']
    if not rnd.empty:
        rigid = ['tx_mm', 'ty_mm', 'tz_mm', 'rx_deg', 'ry_deg', 'rz_deg']
        spread = (rnd.groupby(['param_set', 'beta', 'chamber_param_penalty', 'per_session'])[rigid]
                  .std().mean(axis=1))
        worst = spread.idxmax(); best_id = spread.idxmin()
        lines.append(f"  most identifiable  : set={best_id[0]} beta={best_id[1]} pen={best_id[2]} "
                     f"ps={best_id[3]} (mean rigid std={spread.min():.3f})")
        lines.append(f"  least identifiable : set={worst[0]} beta={worst[1]} pen={worst[2]} "
                     f"ps={worst[3]} (mean rigid std={spread.max():.3f})")
    lines.append("=" * 70)
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
#  Entry point — edit like run_per_session.__main__
# ═══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    from src.analysis.penetrations.run_pooled import PIPE_AA_K5, PIPE_AA_K3  # pick your recipe

    # ---- CONFIG ----------------------------------------------------------
    OUT_DIR = "/home/connorlab/Documents/penetration_optimization_plots/_robustness"
    TABLE = "PenetrationMetrics"
    EXCLUDE = ["260327_0", "260331_0", "260402_0", "260520_0", "260423_0"]
    NO_SKULL_MRI = "/home/connorlab/Documents/MRI/45X_MRI/45X_110315_4_1_corrected_warper_native/rigid_aligned/subject_ns_rigid_aligned.nii.gz"          # set to brain-extracted volume path if you use one
    PIPELINE = PIPE_AA_K3        # the tissue model / decomposition recipe

    # Which global params the optimiser is allowed to move. Globals not listed
    # are HARD-FROZEN at 0 (cleaner than a tiny chamber_param_tolerance, which
    # only soft-penalises them). 'rigid' drops daz/del/ddepth — the extra
    # angular/depth DOF that tend to overfit; compare it against 'full'.
    RIGID = ['tx_mm', 'ty_mm', 'tz_mm', 'rx_deg', 'ry_deg', 'rz_deg']
    PARAM_SETS = {
        'rigid': RIGID,                 # 6 DOF: translation + rotation only
        # 'full':  list(_OPT_PARAM_NAMES),  # 9 DOF: + global daz/del/ddepth
    }

    BETAS = [0.0, 1.0, 5.0, 20.0]         # 0 == mean aggregation
    PENALTIES = [0.0, 0.0001, 0.001, 0.01]  # chamber_param_penalty; 0 == unconstrained
    PER_SESSION = [False, True]
    N_RANDOM_STARTS = 8          # start 0 is the nominal (zero) start; 1..7 random
    START_SCALE = dict(t=6.0, r=6.0, ang=4.0, depth=4.0)   # random-start ranges
    MAXITER = 100000
    RUN_LOSO = False             # decisive overfitting test; N optimisations/config
    SAVE_KNEE = True             # write the parsimony-knee correction file at the end
    KNEE_MIN_INBRAIN = 0.90      # exclude edge-grazing degenerate optima from the knee

    # kwargs held fixed across the whole sweep (everything the optimiser needs
    # that we are NOT varying). Match your production run_per_session settings.
    BASE_KW = dict(
        maxiter=MAXITER,
        optimizer='cma-es',
        use_confidence_weights=True,
        variance_penalty=0.0,
        chamber_dist_penalty=0.000,
        session_corr_penalty=0.1,
        top_downweight_mm=1.0,
        top_downweight_factor=0.25
    )
    # ----------------------------------------------------------------------

    os.makedirs(OUT_DIR, exist_ok=True)
    conn = Connection(database="allen_data_repository", user="xper_rw",
                      password="up2nite", host="172.30.6.61")

    print("Preparing data ...")
    df_conf, mri_pipeline = prepare_data(
        conn, PIPELINE, TABLE, EXCLUDE, MRI_VIEWER_CONFIG_PATH, NO_SKULL_MRI)

    print(f"\nSweeping "
          f"{len(PARAM_SETS)*len(BETAS)*len(PENALTIES)*len(PER_SESSION)*N_RANDOM_STARTS} runs ...")
    sweep_df = sweep(df_conf, conn, mri_pipeline,
                     param_sets=PARAM_SETS,
                     betas=BETAS, penalties=PENALTIES, per_session_opts=PER_SESSION,
                     n_random_starts=N_RANDOM_STARTS, start_scale=START_SCALE,
                     base_kw=BASE_KW)
    sweep_df.to_csv(os.path.join(OUT_DIR, 'sweep.csv'), index=False)

    loso_df = None
    if RUN_LOSO:
        print("\nLOSO cross-validation ...")
        loso_df = loso_cv(df_conf, conn, mri_pipeline, base_kw=BASE_KW, configs=[
            ('rigid', dict(softmin_beta=5.0, chamber_param_penalty=0.001,
                           enable_per_session_corrections=False,
                           fixed_globals=fixed_from_enabled(RIGID))),
            ('full',  dict(softmin_beta=5.0, chamber_param_penalty=0.001,
                           enable_per_session_corrections=False,
                           fixed_globals=fixed_from_enabled(list(_OPT_PARAM_NAMES)))),
        ])
        loso_df.to_csv(os.path.join(OUT_DIR, 'loso.csv'), index=False)

    make_plots(sweep_df, OUT_DIR, loso_df=loso_df)
    print(summarize(sweep_df))

    if SAVE_KNEE:
        print("\nSaving parsimony-knee correction file ...")
        knee_path = save_knee_correction(sweep_df, mri_pipeline, copy_dir=OUT_DIR,
                                         min_inbrain=KNEE_MIN_INBRAIN)
        if knee_path:
            print(f"  Apply with: apply_pca_opt_result('{knee_path}', mri_pipeline)")

    print(f"\nOutputs → {OUT_DIR}")
