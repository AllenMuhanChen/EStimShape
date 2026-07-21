"""MRI sampling along trajectories + chamber/per-session alignment optimisation.

Loads the MRI viewer pipeline, samples voxel intensities at each penetration
sample point, and provides:

  - `compute_mri_comparison`           : add MRI columns to a tissue-scored df
  - `compute_trajectory_fit_scores`    : per-session weighted Pearson r vs MRI
  - `optimize_trajectory_alignment`    : find chamber + per-session corrections
                                         that maximise mean fit across sessions
  - `apply_optimized_pipeline`         : project corrections back into the MRI pipeline
  - `save_optimized_params` / `apply_pca_opt_result` : persistence helpers
"""
import importlib.util
import json
import os
from typing import Optional

import numpy as np
import pandas as pd
from scipy.ndimage import map_coordinates

from clat.util.connection import Connection


OPTIMIZATIONS_path = "/home/connorlab/git/EStimShape/EStimShapeAnalysis/src/mri"
MRI_VIEWER_CONFIG_PATH = os.path.join(os.path.dirname(__file__), '../../mri/mri_viewer_config.json')

# Per-session az/el/depth correction (added on top of global daz/del/ddepth)
ENABLE_PER_SESSION_CORRECTIONS = True
SESSION_CORRECTION_BOUNDS = dict(daz=5.0, del_=5.0, ddepth=5.0)
SESSION_CORRECTION_PENALTY = 0.1

CHAMBER_DIST_PENALTY  = 0.001
CHAMBER_PARAM_PENALTY = 0.001
CHAMBER_PARAM_TOLERANCES = dict(t_mm=5, r_deg=5.0, daz_deg=1.0, del_deg=1.0, ddepth_mm=2.0)

# Down-weight the top X mm of each penetration when scoring tissue_score vs MRI.
TOP_DOWNWEIGHT_MM     = 0.0
TOP_DOWNWEIGHT_FACTOR = 0.25

VARIANCE_PENALTY = 0.0
SOFTMIN_BETA = 5

# λ on a penalty that samples the MRI volume at N points around the chamber
# circle (and uses the chamber's current pose). Only meaningful with a
# brain-extracted ("no-skull") MRI volume, where outside-brain voxels are 0
# and inside-brain voxels are positive. 0 = disabled.
CHAMBER_IN_BRAIN_PENALTY = 0.0

# Chamber circle geometry used by the chamber-in-brain penalty. Matches the
# default in the MRI viewer (viewer.py: 'radius': 7.0).
CHAMBER_RADIUS_MM = 7.0
N_CHAMBER_RING_SAMPLES = 32

_OPT_PARAM_NAMES = [
    'tx_mm', 'ty_mm', 'tz_mm',
    'rx_deg', 'ry_deg', 'rz_deg',
    'daz_deg', 'del_deg',
    'ddepth_mm',
]
_OPT_X0 = np.array([0., 0., 0.,   0., 0., 0.,   0., 0.,   0.])


# ---------------------------------------------------------------------------
# MRI pipeline + sampling
# ---------------------------------------------------------------------------

def load_mri_pipeline(
        config_path: str = MRI_VIEWER_CONFIG_PATH,
        volume_path: Optional[str] = None,
) -> dict:
    """Load MRI volume, correction matrix, and chamber geometry for trajectory sampling.

    volume_path : optional override that replaces `cfg['default_path']` for the
        MRI volume. Use to swap in a brain-extracted ("no-skull") MRI so the
        trajectory sampler doesn't read skull/scalp signal. The MRI corrections
        file is still resolved relative to `volume_path` (so place a paired
        `<volume_path>_corrections.json` next to it, or rely on identity).
        Chamber geometry, screws, and the monkey-specific config still come
        from the JSON config.
    """
    from src.mri.volume import load_volume
    from src.mri.correction import load_corrections
    from src.mri.chamber import fit_chamber

    with open(config_path) as f:
        cfg = json.load(f)

    par_path = volume_path if volume_path is not None else cfg['default_path']
    ebz_world = np.array(cfg['ebz_world'])
    monkey_specific_path = cfg['monkey_specific_path']

    data, native_affine, voxel_sizes, img = load_volume(par_path)
    if data.ndim == 4:
        data = data[..., 0]

    mri_corr_path = os.path.splitext(par_path)[0] + '_corrections.json'
    mri_corr, _ = load_corrections(mri_corr_path)
    print(f"  MRI correction: {mri_corr_path}")
    print(f"  MRI correction matrix:\n{np.round(mri_corr, 4)}")
    corrected_affine = mri_corr @ native_affine
    inv_corrected = np.linalg.inv(corrected_affine)

    spec = importlib.util.spec_from_file_location('monkey_specific', monkey_specific_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    screws_ebz = np.array(mod.get_screw_hole_coords())
    ref_idx = mod.get_reference_screw_idx()
    cor_offset = mod.get_center_of_rotation_offset()
    is_fit_circle = mod.get_is_fit_circle() if hasattr(mod, 'get_is_fit_circle') else False

    ch_corr_path = os.path.splitext(monkey_specific_path)[0] + '_chamber_corrections.json'
    ch_corr, _ = load_corrections(ch_corr_path)
    print(f"  Chamber correction: {ch_corr_path}")
    print(f"  Chamber correction matrix:\n{np.round(ch_corr, 4)}")

    screws_raw = screws_ebz + ebz_world
    center, origin, x, y, normal = fit_chamber(screws_raw, ref_idx, cor_offset, is_fit_circle)

    return {
        'data': data,
        'inv_corrected': inv_corrected,
        'origin': origin,
        'x': x,
        'y': y,
        'normal': normal,
        'cor_offset': cor_offset,
        'screws_world_base': screws_raw,
        'chamber_center_base': center,   # pivot for the rx/ry/rz optimisation params
        'ref_idx': ref_idx,
        'is_fit_circle': is_fit_circle,
        'ch_corr': ch_corr,
        'ch_corr_path': ch_corr_path,
        'monkey_specific_path': monkey_specific_path,
    }


def sample_mri_along_trajectory(
        mri_pipeline: dict,
        az_deg: float,
        el_deg: float,
        depths_mm: np.ndarray,
) -> np.ndarray:
    """Sample MRI voxel intensities at specified depths along a trajectory."""
    from src.mri.chamber import calc_penetration_target

    data = mri_pipeline['data']
    inv_corrected = mri_pipeline['inv_corrected']
    origin = mri_pipeline['origin']
    x = mri_pipeline['x']
    y = mri_pipeline['y']
    normal = mri_pipeline['normal']
    cor_offset = mri_pipeline['cor_offset']

    max_dist = float(np.max(depths_mm)) + 1.0
    _, direction, top_pt = calc_penetration_target(
        origin, az_deg, el_deg, max_dist, x, y, normal, cor_offset
    )

    pts = np.array([top_pt + d * direction for d in depths_mm])
    ones = np.ones((len(pts), 1))
    vox_coords = (inv_corrected @ np.hstack([pts, ones]).T).T[:, :3]

    values = map_coordinates(data, vox_coords.T, order=1, mode='constant', cval=0.0)
    return values.astype(float)


def get_penetration_for_session(conn: Connection, session_id: str) -> Optional[dict]:
    """Query the Penetrations table for a session's trajectory angles."""
    for pen_type in ('actual', 'planned_tip', 'planned'):
        conn.execute(
            "SELECT az_deg, el_deg, dist_mm FROM Penetrations "
            "WHERE session_id = %s AND pen_type = %s LIMIT 1",
            (session_id, pen_type),
        )
        rows = conn.fetch_all()
        if rows:
            az, el, dist = rows[0]
            return {'az_deg': float(az), 'el_deg': float(el),
                    'dist_mm': float(dist), 'pen_type': pen_type}
    return None


def compute_mri_comparison(
        df: pd.DataFrame,
        conn: Connection,
        mri_pipeline: dict,
        daz: float = 0.0,
        del_: float = 0.0,
        ddepth: float = 0.0,
        per_session_corrections: dict = None,
) -> pd.DataFrame:
    """Add MRI intensity sampled along each session's trajectory."""
    df = df.copy()
    df['mri_raw'] = np.nan
    df['mri_normalized'] = np.nan

    for session_id in df['session_id'].unique():
        pen = get_penetration_for_session(conn, session_id)
        if pen is None:
            print(f"  Warning: no penetration found for session {session_id}, skipping MRI.")
            continue

        sc = (per_session_corrections or {}).get(session_id, {})
        sess_daz    = daz    + sc.get('daz_deg',    0.0)
        sess_del    = del_   + sc.get('del_deg',    0.0)
        sess_ddepth = ddepth + sc.get('ddepth_mm',  0.0)

        mask = df['session_id'] == session_id
        depths = df.loc[mask, 'depth_under_chamber_mm'].values + sess_ddepth
        mri_vals = sample_mri_along_trajectory(
            mri_pipeline, pen['az_deg'] + sess_daz, pen['el_deg'] + sess_del, depths
        )
        df.loc[mask, 'mri_raw'] = mri_vals
        df.loc[mask, 'mri_normalized'] = mri_vals

        print(f"  {session_id} ({pen['pen_type']}): "
              f"MRI [{mri_vals.min():.0f}–{mri_vals.max():.0f}]")

    return df


def _weighted_pearson_r(ts: np.ndarray, mri_vals: np.ndarray,
                        confidence: np.ndarray = None) -> float:
    """Weighted Pearson r between tissue_score and MRI raw values.

    Robust to degenerate confidence weights: if the weighted computation is
    undefined (all-zero / non-finite weights, or the weight concentrates on
    bins with constant tissue_score so the weighted variance collapses), fall
    back to the UNWEIGHTED r rather than returning NaN and silently dropping the
    session from the fit report / optimiser loss. Compositional tissue models
    make this common — their confidence can be exactly 0 (nuisance-only bins)
    and is bimodal, which the smoother PCA-softmax confidence never was.
    """
    ts = np.asarray(ts, dtype=float)
    mri_vals = np.asarray(mri_vals, dtype=float)

    pos = mri_vals[mri_vals > 0]
    if len(pos) < 3:
        return np.nan
    mri_ref = float(np.percentile(pos, 99))
    finite_ts = ts[np.isfinite(ts)]
    ts_max = float(finite_ts.max()) if finite_ts.size else 0.0
    if mri_ref <= 0 or ts_max <= 0:
        return np.nan

    mri_norm = np.clip(mri_vals, 0.0, mri_ref) / mri_ref * ts_max
    valid = np.isfinite(ts) & np.isfinite(mri_norm)

    def _wr(w: np.ndarray) -> float:
        ww = w[valid]
        t = ts[valid]
        m = mri_norm[valid]
        w_sum = ww.sum()
        if not np.isfinite(w_sum) or w_sum <= 0:
            return np.nan
        t_wm = (ww * t).sum() / w_sum
        m_wm = (ww * m).sum() / w_sum
        tc = t - t_wm
        mc = m - m_wm
        denom = np.sqrt((ww * tc ** 2).sum() * (ww * mc ** 2).sum())
        return float((ww * tc * mc).sum() / denom) if denom > 0 else np.nan

    if confidence is None:
        return _wr(np.ones(len(ts)))

    w = np.asarray(confidence, dtype=float)
    w = np.clip(np.where(np.isfinite(w), w, 0.0), 0.0, None)   # NaN weight -> 0
    r = _wr(w)
    if not np.isfinite(r):
        # Weighted r undefined (degenerate weights) -> use unweighted so the
        # session still contributes instead of being dropped.
        r = _wr(np.ones(len(ts)))
    return r


def compute_trajectory_fit_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Weighted Pearson r between tissue_score and mri_normalized per session."""
    records = []
    for session_id in df['session_id'].unique():
        mask = df['session_id'] == session_id
        sdata = df[mask].dropna(subset=['tissue_score', 'mri_normalized'])
        n = len(sdata)

        if n < 3:
            records.append({'session_id': session_id, 'fit_score': np.nan, 'n_points': n})
            continue

        ts = sdata['tissue_score'].values
        mri = sdata['mri_normalized'].values
        conf = sdata['tissue_confidence'].values if 'tissue_confidence' in sdata.columns else None
        r_w = _weighted_pearson_r(ts, mri, conf)
        r_u = _weighted_pearson_r(ts, mri, None)
        records.append({'session_id': session_id, 'fit_score': r_w,
                        'fit_score_unweighted': r_u, 'n_points': n})

    result = pd.DataFrame(records).set_index('session_id')
    print("\nTrajectory fit scores (tissue_score vs MRI):")
    print(result.to_string())
    return result


# ---------------------------------------------------------------------------
# Chamber param projection + optimiser back-ends
# ---------------------------------------------------------------------------

def _chamber_correction_matrix(params: np.ndarray, center: np.ndarray) -> np.ndarray:
    """4x4 world-space chamber correction from the optimisation params.

    Rotation (rx/ry/rz) is applied about the chamber `center`, so a pure
    rotation reorients the chamber IN PLACE without translating it — decoupling
    the r* params from the t* params. Translation (tx/ty/tz) is then applied.
    This matches the MRI viewer's convention
    (viewer_chamber._apply_chamber_correction), so optimised params and
    viewer-entered corrections mean the same pose.
    """
    from src.mri.correction import rot_x, rot_y, rot_z, xlate
    tx, ty, tz, rx, ry, rz, *_ = params
    c = np.asarray(center, dtype=float)
    R_pure = rot_z(rz) @ rot_y(ry) @ rot_x(rx)
    R_about_center = xlate(c[0], c[1], c[2]) @ R_pure @ xlate(-c[0], -c[1], -c[2])
    return xlate(tx, ty, tz) @ R_about_center


def _apply_chamber_params(params: np.ndarray, mri_pipeline: dict):
    """Return (origin, x, y, normal) after applying optimisation params to chamber."""
    from src.mri.chamber import fit_chamber

    screws = mri_pipeline['screws_world_base']
    center = mri_pipeline.get('chamber_center_base', np.zeros(3))

    corr = _chamber_correction_matrix(params, center)
    R, t = corr[:3, :3], corr[:3, 3]
    screws_new = (R @ screws.T).T + t

    _, origin, x, y, normal = fit_chamber(
        screws_new,
        mri_pipeline['ref_idx'],
        mri_pipeline['cor_offset'],
        mri_pipeline['is_fit_circle'],
    )
    return origin, x, y, normal


def _tanh_bound(raw: float, bound: float) -> float:
    """Map unconstrained raw value to (-bound, +bound) via tanh reparameterization."""
    return bound * float(np.tanh(raw))


def _run_nelder_mead(score_fn, x0, steps, callback, maxiter):
    from scipy.optimize import minimize
    n_p = len(x0)
    init_simplex = np.tile(x0, (n_p + 1, 1))
    for i in range(n_p):
        init_simplex[i + 1, i] += steps[i]
    return minimize(
        score_fn, x0, method='Nelder-Mead', callback=callback,
        options={'maxiter': maxiter, 'xatol': 1e-3, 'fatol': 1e-4,
                 'adaptive': True, 'disp': True,
                 'initial_simplex': init_simplex},
    )


def _run_cma_es(score_fn, x0, steps, callback, maxiter):
    try:
        import cma
    except ImportError:
        raise ImportError(
            "CMA-ES requires the 'cma' package.  Install with:  pip install cma")
    from scipy.optimize import OptimizeResult

    opts = {
        'maxiter':               maxiter,
        'tolx':                  1e-3,
        'tolfun':                1e-4,
        'scaling_of_variables':  steps.tolist(),
        'verbose':               -9,
    }
    es = cma.CMAEvolutionStrategy(x0.tolist(), 1.0, opts)
    while not es.stop():
        solutions = es.ask()
        fitvals   = [score_fn(np.asarray(s)) for s in solutions]
        es.tell(solutions, fitvals)
        if es.result.xbest is not None:
            callback(np.asarray(es.result.xbest))

    r = es.result
    return OptimizeResult(
        x       = np.asarray(r.xbest),
        fun     = float(r.fbest),
        message = f"CMA-ES stopped: {es.stop()}",
        nfev    = int(r.evaluations),
        success = True,
    )


_OPTIMIZERS = {
    'nelder-mead': _run_nelder_mead,
    'cma-es':      _run_cma_es,
}


def optimize_trajectory_alignment(
        df_conf: pd.DataFrame,
        conn: Connection,
        mri_pipeline: dict,
        maxiter: int = 10000,
        start_from_file: Optional[str] = None,
        enable_per_session_corrections: bool = ENABLE_PER_SESSION_CORRECTIONS,
        session_corr_bounds: dict = None,
        session_corr_penalty: float = SESSION_CORRECTION_PENALTY,
        chamber_dist_penalty: float = CHAMBER_DIST_PENALTY,
        chamber_param_penalty: float = CHAMBER_PARAM_PENALTY,
        chamber_param_tolerances: dict = None,
        variance_penalty: float = VARIANCE_PENALTY,
        softmin_beta: float = SOFTMIN_BETA,
        optimizer: str = 'nelder-mead',
        use_confidence_weights: bool = True,
        top_downweight_mm: float = TOP_DOWNWEIGHT_MM,
        top_downweight_factor: float = TOP_DOWNWEIGHT_FACTOR,
        fixed_globals: Optional[dict] = None,
        chamber_in_brain_penalty: float = CHAMBER_IN_BRAIN_PENALTY,
        chamber_radius_mm: float = CHAMBER_RADIUS_MM,
        n_chamber_ring_samples: int = N_CHAMBER_RING_SAMPLES,
) -> dict:
    """
    Find the rigid-body + angle + depth correction that maximises the
    mean weighted Pearson r between tissue_score and MRI across all sessions.

    chamber_in_brain_penalty : λ on a penalty that samples mri_pipeline['data']
        at n_chamber_ring_samples points around the chamber circle (radius
        chamber_radius_mm, in the chamber's current x/y plane at center =
        origin - cor_offset * normal). Adds the mean normalised intensity to
        the loss. Sampling the whole ring (rather than just the discrete screw
        positions) prevents the optimiser from tucking the chamber so that
        screws are safe but a chunk of the ring between two screws lands
        inside brain tissue. Designed for use with a brain-extracted MRI
        (load_mri_pipeline(volume_path=...)) where outside-brain voxels are 0.
        0 = disabled. Values around 10 give "heavy" penalisation on the same
        scale as a 1.0 swing in mean fit r.
    """
    from src.mri.chamber import calc_penetration_target

    if session_corr_bounds is None:
        session_corr_bounds = SESSION_CORRECTION_BOUNDS
    if chamber_param_tolerances is None:
        chamber_param_tolerances = CHAMBER_PARAM_TOLERANCES

    fix_idx_val = []
    if fixed_globals:
        for name, val in fixed_globals.items():
            if name not in _OPT_PARAM_NAMES:
                raise ValueError(f"Unknown global param {name!r}. "
                                 f"Choose from: {_OPT_PARAM_NAMES}")
            fix_idx_val.append((_OPT_PARAM_NAMES.index(name), float(val)))
        print(f"  Holding fixed: " + ", ".join(
            f"{_OPT_PARAM_NAMES[i]}={v:+.4f}" for i, v in fix_idx_val))

    session_info = {}
    for session_id in df_conf['session_id'].unique():
        pen = get_penetration_for_session(conn, session_id)
        if pen is None:
            continue
        mask = df_conf['session_id'] == session_id
        depths = df_conf.loc[mask, 'depth_under_chamber_mm'].values.copy()
        if top_downweight_mm > 0 and len(depths) > 0:
            top_thresh = depths.min() + top_downweight_mm
            depth_weight = np.where(depths <= top_thresh, top_downweight_factor, 1.0)
        else:
            depth_weight = None
        session_info[session_id] = {
            'az': pen['az_deg'],
            'el': pen['el_deg'],
            'depths': depths,
            'ts': df_conf.loc[mask, 'tissue_score'].values.copy(),
            'confidence': df_conf.loc[mask, 'tissue_confidence'].values.copy()
                if 'tissue_confidence' in df_conf.columns else None,
            'depth_weight': depth_weight,
        }

    if not session_info:
        raise RuntimeError("No sessions with penetration data found.")

    data = mri_pipeline['data']
    inv_corrected = mri_pipeline['inv_corrected']
    cor_offset = mri_pipeline['cor_offset']

    # Pre-compute normaliser for the chamber-in-brain penalty so the lambda
    # magnitude is on the same scale as the Pearson-r loss (≈ [0, 1]).
    # We use the 99th percentile of positive voxel intensities — robust to
    # outliers, ≈ peak brain intensity for a brain-extracted MRI.
    if chamber_in_brain_penalty > 0:
        brain_pos = data[data > 0]
        chamber_brain_ref = float(np.percentile(brain_pos, 99)) if brain_pos.size > 0 else 1.0
        if chamber_brain_ref <= 0:
            chamber_brain_ref = 1.0
        # Pre-compute ring angles once.
        ring_theta = np.linspace(0.0, 2.0 * np.pi, n_chamber_ring_samples, endpoint=False)
        ring_cos = np.cos(ring_theta)
        ring_sin = np.sin(ring_theta)
        print(f"  Chamber-in-brain penalty λ={chamber_in_brain_penalty:g}  "
              f"(ring: {n_chamber_ring_samples} pts × r={chamber_radius_mm}mm; "
              f"normalised by 99th-pctile brain intensity = {chamber_brain_ref:.1f})")
    else:
        chamber_brain_ref = 1.0
        ring_cos = ring_sin = None

    origin_b, x_b, y_b, normal_b = _apply_chamber_params(_OPT_X0, mri_pipeline)
    baseline_pts = {}
    for sid, sdata in session_info.items():
        depths0 = sdata['depths']
        if depths0.max() <= 0:
            baseline_pts[sid] = None
            continue
        try:
            _, direction0, top_pt0 = calc_penetration_target(
                origin_b, sdata['az'], sdata['el'],
                float(depths0.max()) + 1.0, x_b, y_b, normal_b, cor_offset,
            )
            baseline_pts[sid] = top_pt0 + depths0[:, None] * direction0[None, :]
        except Exception:
            baseline_pts[sid] = None

    session_ids = list(session_info.keys())
    n_sess = len(session_ids)

    if enable_per_session_corrections:
        per_sess_names = []
        for sid in session_ids:
            per_sess_names += [f'daz_{sid}', f'del_{sid}', f'ddepth_{sid}']
        full_param_names = _OPT_PARAM_NAMES + per_sess_names
        full_x0 = np.concatenate([_OPT_X0, np.zeros(3 * n_sess)])
        print(f"  Per-session corrections enabled: {n_sess} sessions × 3 params "
              f"(bounds: ±{session_corr_bounds['daz']}° az, "
              f"±{session_corr_bounds['del_']}° el, "
              f"±{session_corr_bounds['ddepth']} mm depth)")
    else:
        full_param_names = _OPT_PARAM_NAMES
        full_x0 = _OPT_X0.copy()

    if start_from_file is not None:
        with open(start_from_file) as _f:
            _prior = json.load(_f)
        _prior_params = _prior.get('params', {})
        for _i, _name in enumerate(_OPT_PARAM_NAMES):
            if _name in _prior_params:
                full_x0[_i] = float(_prior_params[_name])
        if enable_per_session_corrections and 'per_session_corrections' in _prior:
            _prior_sess = _prior['per_session_corrections']
            for _j, _sid in enumerate(session_ids):
                _sc = _prior_sess.get(str(_sid), {})
                if _sc:
                    full_x0[9 + _j * 3]     = float(np.arctanh(np.clip(
                        _sc.get('daz_deg',   0.) / session_corr_bounds['daz'],   -0.9999, 0.9999)))
                    full_x0[9 + _j * 3 + 1] = float(np.arctanh(np.clip(
                        _sc.get('del_deg',   0.) / session_corr_bounds['del_'],  -0.9999, 0.9999)))
                    full_x0[9 + _j * 3 + 2] = float(np.arctanh(np.clip(
                        _sc.get('ddepth_mm', 0.) / session_corr_bounds['ddepth'], -0.9999, 0.9999)))
        print(f"  Warm-starting from: {os.path.basename(start_from_file)}")
        print(f"  Initial global params: tx={full_x0[0]:+.3f}  ty={full_x0[1]:+.3f}  tz={full_x0[2]:+.3f}  "
              f"rx={full_x0[3]:+.3f}  ry={full_x0[4]:+.3f}  rz={full_x0[5]:+.3f}  "
              f"daz={full_x0[6]:+.3f}  del={full_x0[7]:+.3f}  ddepth={full_x0[8]:+.3f}")
    else:
        print("  Starting from zero (no prior correction file provided)")

    for idx, val in fix_idx_val:
        full_x0[idx] = val

    best = {'score': -np.inf, 'params': full_x0.copy(), 'iter': 0}
    call_count = [0]
    latest = {'mean_weighted': np.nan, 'mean_raw': np.nan}

    def score_for_params(params, include_reg=True):
        if fix_idx_val:
            params = np.array(params, dtype=float, copy=True)
            for idx, val in fix_idx_val:
                params[idx] = val
        try:
            origin, x_vec, y_vec, normal = _apply_chamber_params(params, mri_pipeline)
        except Exception:
            return np.inf

        _, _, _, _, _, _, daz, del_, ddepth = params[:9]
        per_sess_raw = params[9:].reshape(-1, 3) if enable_per_session_corrections else None

        rs, rs_raw, reg_sum = [], [], 0.0
        chamber_dist_sq_sum = 0.0
        chamber_dist_n = 0

        for i, sid in enumerate(session_ids):
            sdata = session_info[sid]

            if per_sess_raw is not None:
                daz_i  = _tanh_bound(per_sess_raw[i, 0], session_corr_bounds['daz'])
                del_i  = _tanh_bound(per_sess_raw[i, 1], session_corr_bounds['del_'])
                ddep_i = _tanh_bound(per_sess_raw[i, 2], session_corr_bounds['ddepth'])
                reg_sum += (daz_i  / session_corr_bounds['daz'])  ** 2
                reg_sum += (del_i  / session_corr_bounds['del_']) ** 2
                reg_sum += (ddep_i / session_corr_bounds['ddepth']) ** 2
            else:
                daz_i = del_i = ddep_i = 0.0

            depths_g = sdata['depths'] + ddepth
            if depths_g.max() > 0 and baseline_pts.get(sid) is not None:
                try:
                    _, direction_g, top_pt_g = calc_penetration_target(
                        origin, sdata['az'] + daz, sdata['el'] + del_,
                        float(depths_g.max()) + 1.0, x_vec, y_vec, normal, cor_offset,
                    )
                    pts_g = top_pt_g + depths_g[:, None] * direction_g[None, :]
                    diffs = pts_g - baseline_pts[sid]
                    chamber_dist_sq_sum += float(np.sum(diffs * diffs))
                    chamber_dist_n += len(diffs)
                except Exception:
                    pass

            depths = sdata['depths'] + ddepth + ddep_i
            if depths.max() <= 0:
                continue
            try:
                _, direction, top_pt = calc_penetration_target(
                    origin, sdata['az'] + daz + daz_i, sdata['el'] + del_ + del_i,
                    float(depths.max()) + 1.0, x_vec, y_vec, normal, cor_offset,
                )
                pts = top_pt + depths[:, None] * direction[None, :]
                ones = np.ones((len(pts), 1))
                vox = (inv_corrected @ np.hstack([pts, ones]).T).T[:, :3]
                mri_vals = map_coordinates(data, vox.T, order=1,
                                           mode='constant', cval=0.0).astype(float)
            except Exception:
                continue

            conf = sdata['confidence'] if use_confidence_weights else None
            dw = sdata.get('depth_weight')
            if dw is not None:
                conf = (conf if conf is not None else np.ones(len(sdata['ts']))) * dw
            r = _weighted_pearson_r(sdata['ts'], mri_vals, conf)
            r_raw = _weighted_pearson_r(sdata['ts'], mri_vals, None)
            if not np.isnan(r):
                rs.append(r)
            if not np.isnan(r_raw):
                rs_raw.append(r_raw)

        latest['mean_weighted'] = float(np.mean(rs)) if rs else np.nan
        latest['mean_raw']      = float(np.mean(rs_raw)) if rs_raw else np.nan
        if not rs:
            return np.inf
        rs_arr = np.array(rs)
        if softmin_beta > 0 and len(rs_arr) > 1:
            # Normalized softmin: a softmax(-beta*r)-weighted average of the
            # per-session r. Emphasises the worst-fitting sessions (-> min(r) as
            # beta->inf, -> mean(r) as beta->0) while always staying within
            # [min(r), mean(r)]. NB: this is NOT -logsumexp(-beta*r)/beta, which
            # carries a spurious -log(N)/beta offset that drags the reported
            # score below every session's r and makes it scale with the session
            # count. The argmin is essentially the same; only the score's scale
            # is fixed so it is interpretable and comparable across runs.
            w = np.exp(-softmin_beta * (rs_arr - rs_arr.max()))
            loss = -float((w * rs_arr).sum() / w.sum())
        else:
            loss = -rs_arr.mean()
        if include_reg and variance_penalty > 0 and len(rs_arr) > 1:
            loss += variance_penalty * rs_arr.var()
        if include_reg:
            if chamber_dist_penalty > 0 and chamber_dist_n > 0:
                chamber_dist_reg = chamber_dist_sq_sum / chamber_dist_n
                loss += chamber_dist_penalty * chamber_dist_reg
            if chamber_param_penalty > 0:
                tx, ty, tz, rx, ry, rz, daz_g, del_g, ddepth_g = params[:9]
                s = chamber_param_tolerances
                chamber_param_reg = (
                    (tx / s['t_mm'])**2 + (ty / s['t_mm'])**2 + (tz / s['t_mm'])**2
                    + (rx / s['r_deg'])**2 + (ry / s['r_deg'])**2 + (rz / s['r_deg'])**2
                    + (daz_g / s['daz_deg'])**2 + (del_g / s['del_deg'])**2
                    + (ddepth_g / s['ddepth_mm'])**2
                )
                loss += chamber_param_penalty * chamber_param_reg
            if chamber_in_brain_penalty > 0:
                # Sample MRI at n_chamber_ring_samples points around the chamber
                # circle in its current pose. Chamber center = origin - cor_offset
                # * normal; ring lies in the (x_vec, y_vec) plane at radius
                # chamber_radius_mm. With a brain-extracted MRI, any positive
                # intensity along the ring indicates a portion of the chamber
                # footprint landed inside brain tissue (physically impossible).
                # Sampling the whole ring (not just the discrete screws) catches
                # chamber poses where the gaps between screws end up in brain.
                center_w = origin - cor_offset * normal
                ring_pts = (center_w[None, :]
                            + chamber_radius_mm * (ring_cos[:, None] * x_vec[None, :]
                                                   + ring_sin[:, None] * y_vec[None, :]))
                ones_r = np.ones((len(ring_pts), 1))
                vox_ring = (inv_corrected @ np.hstack([ring_pts, ones_r]).T).T[:, :3]
                ring_intensities = map_coordinates(
                    data, vox_ring.T, order=1, mode='constant', cval=0.0,
                ).astype(float)
                ring_penalty = float(np.clip(ring_intensities, 0.0, None).mean()) / chamber_brain_ref
                loss += chamber_in_brain_penalty * ring_penalty
            if enable_per_session_corrections:
                loss += session_corr_penalty * reg_sum
        return loss

    def callback_nelder(xk):
        call_count[0] += 1
        s_pure = -score_for_params(xk, include_reg=False)
        if s_pure > best['score']:
            best['score'] = s_pure
            best['params'] = xk.copy()
            best['iter'] = call_count[0]
            tx, ty, tz, rx, ry, rz, daz, del_, ddepth = xk[:9]
            print(f"  [{call_count[0]:4d}] score={s_pure:.4f}  raw={latest['mean_raw']:.4f}  "
                  f"t=({tx:.2f},{ty:.2f},{tz:.2f})  "
                  f"r=({rx:.2f},{ry:.2f},{rz:.2f})  "
                  f"daz={daz:.2f}  del={del_:.2f}  ddepth={ddepth:.2f}")
            if enable_per_session_corrections and len(xk) > 9:
                per = xk[9:].reshape(-1, 3)
                eff_daz  = np.array([_tanh_bound(v, session_corr_bounds['daz'])  for v in per[:, 0]])
                eff_del  = np.array([_tanh_bound(v, session_corr_bounds['del_']) for v in per[:, 1]])
                eff_ddep = np.array([_tanh_bound(v, session_corr_bounds['ddepth']) for v in per[:, 2]])
                print(f"         max|Δaz|={np.abs(eff_daz).max():.2f}°  "
                      f"max|Δel|={np.abs(eff_del).max():.2f}°  "
                      f"max|Δdep|={np.abs(eff_ddep).max():.2f}mm")

    score_before = -score_for_params(full_x0, include_reg=False)
    raw_before = latest['mean_raw']
    agg_note = (f"  softmin β={softmin_beta}" if softmin_beta > 0 else "  mean aggregation")
    var_note  = (f"  variance penalty λ={variance_penalty}"
                 if variance_penalty > 0 else "")
    conf_note = "" if use_confidence_weights else "  confidence weights OFF"
    top_note = (f"  top {top_downweight_mm:.2f}mm × {top_downweight_factor:.2f}"
                if top_downweight_mm > 0 else "")
    print(f"\nOptimising over {len(session_info)} sessions  "
          f"(initial score = {score_before:.4f}, raw = {raw_before:.4f})"
          f"{agg_note}{var_note}{conf_note}{top_note} ...")
    print(f"  Optimizer: {optimizer}")

    if optimizer not in _OPTIMIZERS:
        raise ValueError(f"Unknown optimizer {optimizer!r}.  Choose from: {list(_OPTIMIZERS)}")

    n_p = len(full_x0)
    steps = np.zeros(n_p)
    steps[:3] = 1.0
    steps[3:6] = 1.0
    steps[6]   = 0.5
    steps[7]   = 0.5
    steps[8]   = 0.5
    if enable_per_session_corrections and n_p > 9:
        steps[9:] = 0.5
    for idx, _ in fix_idx_val:
        steps[idx] = 1e-9

    maxiter_adj = maxiter + 500 * n_sess if enable_per_session_corrections else maxiter
    result = _OPTIMIZERS[optimizer](score_for_params, full_x0, steps, callback_nelder, maxiter_adj)

    for idx, val in fix_idx_val:
        result.x[idx] = val

    score_after = -score_for_params(result.x, include_reg=False)
    raw_after = latest['mean_raw']
    print(f"\nOptimisation done: {result.message}")
    print(f"  score: {score_before:.4f} → {score_after:.4f}  "
          f"(Δ = {score_after - score_before:+.4f})")
    print(f"  raw:   {raw_before:.4f} → {raw_after:.4f}  "
          f"(Δ = {raw_after - raw_before:+.4f})")
    print("\nOptimised global parameters:")
    for name, val in zip(_OPT_PARAM_NAMES, result.x[:9]):
        print(f"  {name:<14s} = {val:+.4f}")

    per_session_corrections = {}
    if enable_per_session_corrections and len(result.x) > 9:
        per = result.x[9:].reshape(-1, 3)
        for i, sid in enumerate(session_ids):
            per_session_corrections[sid] = dict(
                daz_deg   = _tanh_bound(per[i, 0], session_corr_bounds['daz']),
                del_deg   = _tanh_bound(per[i, 1], session_corr_bounds['del_']),
                ddepth_mm = _tanh_bound(per[i, 2], session_corr_bounds['ddepth']),
            )
        print("\nPer-session corrections (effective, deg/mm):")
        for sid, c in per_session_corrections.items():
            print(f"  {str(sid):<20s}  daz={c['daz_deg']:+.3f}°  "
                  f"del={c['del_deg']:+.3f}°  ddepth={c['ddepth_mm']:+.3f}mm")

    return {
        'params': result.x,
        'param_names': full_param_names,
        'result': result,
        'score_before': score_before,
        'score_after': score_after,
        'raw_before': raw_before,
        'raw_after': raw_after,
        'per_session_corrections': per_session_corrections,
        'session_ids': session_ids,
        'session_corr_bounds': session_corr_bounds,
        'session_corr_penalty': session_corr_penalty,
        'variance_penalty': variance_penalty,
        'softmin_beta': softmin_beta,
        'optimizer': optimizer,
        'use_confidence_weights': use_confidence_weights,
        'fixed_globals': dict(fixed_globals) if fixed_globals else None,
        'chamber_in_brain_penalty': chamber_in_brain_penalty,
        'chamber_radius_mm': chamber_radius_mm,
        'n_chamber_ring_samples': n_chamber_ring_samples,
    }


def optimize_trajectory_alignment_seg(
        df_conf: pd.DataFrame,
        conn: Connection,
        mri_pipeline: dict,
        seg_volume: dict,
        maxiter: int = 10000,
        start_from_file: Optional[str] = None,
        enable_per_session_corrections: bool = ENABLE_PER_SESSION_CORRECTIONS,
        session_corr_bounds: dict = None,
        session_corr_penalty: float = SESSION_CORRECTION_PENALTY,
        chamber_dist_penalty: float = CHAMBER_DIST_PENALTY,
        chamber_param_penalty: float = CHAMBER_PARAM_PENALTY,
        chamber_param_tolerances: dict = None,
        variance_penalty: float = VARIANCE_PENALTY,
        softmin_beta: float = SOFTMIN_BETA,
        optimizer: str = 'cma-es',
        use_confidence_weights: bool = True,
        top_downweight_mm: float = TOP_DOWNWEIGHT_MM,
        top_downweight_factor: float = TOP_DOWNWEIGHT_FACTOR,
        fixed_globals: Optional[dict] = None,
) -> dict:
    """Seg-target counterpart of optimize_trajectory_alignment.

    Scores 3-class classification accuracy of argmax(p_sulcus, p_gm, p_wm) vs
    the segmentation class label sampled along the trajectory. Predicted
    class is invariant during optimization (depends only on the fixed PC
    scores); only the segmentation samples move as chamber/per-session
    corrections change.

    Note: accuracy is a step function in the chamber parameters (a small
    wiggle only changes the score when a sample's seg class flips), so the
    landscape is rougher than the Pearson-r version. Default optimizer is
    CMA-ES; Nelder-Mead is likely to stall. Use more iterations than for
    the MRI version.

    Requires df_conf to contain columns: p_sulcus, p_gm, p_wm,
    tissue_confidence (optional), and depth_under_chamber_mm + session_id.
    """
    from src.mri.chamber import calc_penetration_target

    if session_corr_bounds is None:
        session_corr_bounds = SESSION_CORRECTION_BOUNDS
    if chamber_param_tolerances is None:
        chamber_param_tolerances = CHAMBER_PARAM_TOLERANCES

    required_p = ['p_sulcus', 'p_gm', 'p_wm']
    missing = [c for c in required_p if c not in df_conf.columns]
    if missing:
        raise RuntimeError(
            f"optimize_trajectory_alignment_seg needs columns {required_p}; "
            f"missing {missing}. Use a TissueModel with sulcus/gm/wm classes."
        )

    fix_idx_val = []
    if fixed_globals:
        for name, val in fixed_globals.items():
            if name not in _OPT_PARAM_NAMES:
                raise ValueError(f"Unknown global param {name!r}. "
                                 f"Choose from: {_OPT_PARAM_NAMES}")
            fix_idx_val.append((_OPT_PARAM_NAMES.index(name), float(val)))
        print(f"  Holding fixed: " + ", ".join(
            f"{_OPT_PARAM_NAMES[i]}={v:+.4f}" for i, v in fix_idx_val))

    # Pre-cache per session. predicted_class is invariant during optimization
    # because the PC scores (and therefore the p_* columns) don't depend on the
    # chamber/per-session corrections — only the sampled signal does.
    session_info = {}
    for session_id in df_conf['session_id'].unique():
        pen = get_penetration_for_session(conn, session_id)
        if pen is None:
            continue
        mask = df_conf['session_id'] == session_id
        depths = df_conf.loc[mask, 'depth_under_chamber_mm'].values.copy()
        if top_downweight_mm > 0 and len(depths) > 0:
            top_thresh = depths.min() + top_downweight_mm
            depth_weight = np.where(depths <= top_thresh, top_downweight_factor, 1.0)
        else:
            depth_weight = None
        p_arr = df_conf.loc[mask, required_p].values
        predicted_class = np.argmax(p_arr, axis=1).astype(int)
        session_info[session_id] = {
            'az': pen['az_deg'],
            'el': pen['el_deg'],
            'depths': depths,
            'predicted_class': predicted_class,
            'confidence': df_conf.loc[mask, 'tissue_confidence'].values.copy()
                if 'tissue_confidence' in df_conf.columns else None,
            'depth_weight': depth_weight,
        }

    if not session_info:
        raise RuntimeError("No sessions with penetration data found.")

    seg_data = seg_volume['data']
    seg_inv = seg_volume['inv_corrected']
    cor_offset = mri_pipeline['cor_offset']

    origin_b, x_b, y_b, normal_b = _apply_chamber_params(_OPT_X0, mri_pipeline)
    baseline_pts = {}
    for sid, sdata in session_info.items():
        depths0 = sdata['depths']
        if depths0.max() <= 0:
            baseline_pts[sid] = None
            continue
        try:
            _, direction0, top_pt0 = calc_penetration_target(
                origin_b, sdata['az'], sdata['el'],
                float(depths0.max()) + 1.0, x_b, y_b, normal_b, cor_offset,
            )
            baseline_pts[sid] = top_pt0 + depths0[:, None] * direction0[None, :]
        except Exception:
            baseline_pts[sid] = None

    session_ids = list(session_info.keys())
    n_sess = len(session_ids)

    if enable_per_session_corrections:
        per_sess_names = []
        for sid in session_ids:
            per_sess_names += [f'daz_{sid}', f'del_{sid}', f'ddepth_{sid}']
        full_param_names = _OPT_PARAM_NAMES + per_sess_names
        full_x0 = np.concatenate([_OPT_X0, np.zeros(3 * n_sess)])
        print(f"  Per-session corrections enabled: {n_sess} sessions × 3 params")
    else:
        full_param_names = _OPT_PARAM_NAMES
        full_x0 = _OPT_X0.copy()

    if start_from_file is not None:
        with open(start_from_file) as _f:
            _prior = json.load(_f)
        _prior_params = _prior.get('params', {})
        for _i, _name in enumerate(_OPT_PARAM_NAMES):
            if _name in _prior_params:
                full_x0[_i] = float(_prior_params[_name])
        if enable_per_session_corrections and 'per_session_corrections' in _prior:
            _prior_sess = _prior['per_session_corrections']
            for _j, _sid in enumerate(session_ids):
                _sc = _prior_sess.get(str(_sid), {})
                if _sc:
                    full_x0[9 + _j * 3]     = float(np.arctanh(np.clip(
                        _sc.get('daz_deg',   0.) / session_corr_bounds['daz'],   -0.9999, 0.9999)))
                    full_x0[9 + _j * 3 + 1] = float(np.arctanh(np.clip(
                        _sc.get('del_deg',   0.) / session_corr_bounds['del_'],  -0.9999, 0.9999)))
                    full_x0[9 + _j * 3 + 2] = float(np.arctanh(np.clip(
                        _sc.get('ddepth_mm', 0.) / session_corr_bounds['ddepth'], -0.9999, 0.9999)))
        print(f"  Warm-starting from: {os.path.basename(start_from_file)}")

    for idx, val in fix_idx_val:
        full_x0[idx] = val

    best = {'score': -np.inf, 'params': full_x0.copy(), 'iter': 0}
    call_count = [0]
    latest = {'mean_weighted': np.nan, 'mean_raw': np.nan}

    def _session_accuracy(predicted_class, seg_class, conf):
        """Per-session classification accuracy (optionally confidence-weighted)."""
        match = (predicted_class == seg_class).astype(float)
        if conf is None:
            return float(match.mean())
        w_sum = float(conf.sum())
        if w_sum <= 0:
            return float(match.mean())
        return float((conf * match).sum() / w_sum)

    def score_for_params(params, include_reg=True):
        if fix_idx_val:
            params = np.array(params, dtype=float, copy=True)
            for idx, val in fix_idx_val:
                params[idx] = val
        try:
            origin, x_vec, y_vec, normal = _apply_chamber_params(params, mri_pipeline)
        except Exception:
            return np.inf

        _, _, _, _, _, _, daz, del_, ddepth = params[:9]
        per_sess_raw = params[9:].reshape(-1, 3) if enable_per_session_corrections else None

        accs, accs_raw, reg_sum = [], [], 0.0
        chamber_dist_sq_sum = 0.0
        chamber_dist_n = 0

        for i, sid in enumerate(session_ids):
            sdata = session_info[sid]

            if per_sess_raw is not None:
                daz_i  = _tanh_bound(per_sess_raw[i, 0], session_corr_bounds['daz'])
                del_i  = _tanh_bound(per_sess_raw[i, 1], session_corr_bounds['del_'])
                ddep_i = _tanh_bound(per_sess_raw[i, 2], session_corr_bounds['ddepth'])
                reg_sum += (daz_i  / session_corr_bounds['daz'])  ** 2
                reg_sum += (del_i  / session_corr_bounds['del_']) ** 2
                reg_sum += (ddep_i / session_corr_bounds['ddepth']) ** 2
            else:
                daz_i = del_i = ddep_i = 0.0

            depths_g = sdata['depths'] + ddepth
            if depths_g.max() > 0 and baseline_pts.get(sid) is not None:
                try:
                    _, direction_g, top_pt_g = calc_penetration_target(
                        origin, sdata['az'] + daz, sdata['el'] + del_,
                        float(depths_g.max()) + 1.0, x_vec, y_vec, normal, cor_offset,
                    )
                    pts_g = top_pt_g + depths_g[:, None] * direction_g[None, :]
                    diffs = pts_g - baseline_pts[sid]
                    chamber_dist_sq_sum += float(np.sum(diffs * diffs))
                    chamber_dist_n += len(diffs)
                except Exception:
                    pass

            depths = sdata['depths'] + ddepth + ddep_i
            if depths.max() <= 0:
                continue
            try:
                _, direction, top_pt = calc_penetration_target(
                    origin, sdata['az'] + daz + daz_i, sdata['el'] + del_ + del_i,
                    float(depths.max()) + 1.0, x_vec, y_vec, normal, cor_offset,
                )
                pts = top_pt + depths[:, None] * direction[None, :]
                ones = np.ones((len(pts), 1))
                vox = (seg_inv @ np.hstack([pts, ones]).T).T[:, :3]
                seg_vals = map_coordinates(seg_data, vox.T, order=0,
                                           mode='constant', cval=0.0).astype(int)
            except Exception:
                continue

            seg_class = seg_values_to_classes(seg_vals)
            conf = sdata['confidence'] if use_confidence_weights else None
            dw = sdata.get('depth_weight')
            if dw is not None:
                conf = (conf if conf is not None
                        else np.ones(len(sdata['predicted_class']))) * dw

            acc = _session_accuracy(sdata['predicted_class'], seg_class, conf)
            acc_raw = _session_accuracy(sdata['predicted_class'], seg_class, None)
            if not np.isnan(acc):
                accs.append(acc)
            if not np.isnan(acc_raw):
                accs_raw.append(acc_raw)

        latest['mean_weighted'] = float(np.mean(accs)) if accs else np.nan
        latest['mean_raw']      = float(np.mean(accs_raw)) if accs_raw else np.nan
        if not accs:
            return np.inf
        accs_arr = np.array(accs)
        if softmin_beta > 0 and len(accs_arr) > 1:
            # Normalized softmin: a softmax(-beta*acc)-weighted average of the
            # per-session accuracy. Emphasises the worst sessions (-> min(acc) as
            # beta->inf, -> mean(acc) as beta->0) while always staying within
            # [min(acc), mean(acc)]. NB: this is NOT -logsumexp(-beta*acc)/beta,
            # which carries a spurious -log(N)/beta offset that drags the score
            # below every session's accuracy and makes it scale with the session
            # count. The argmin is essentially the same; only the score's scale
            # is fixed so it is interpretable and comparable across runs.
            w = np.exp(-softmin_beta * (accs_arr - accs_arr.max()))
            loss = -float((w * accs_arr).sum() / w.sum())
        else:
            loss = -accs_arr.mean()
        if include_reg and variance_penalty > 0 and len(accs_arr) > 1:
            loss += variance_penalty * accs_arr.var()
        if include_reg:
            if chamber_dist_penalty > 0 and chamber_dist_n > 0:
                chamber_dist_reg = chamber_dist_sq_sum / chamber_dist_n
                loss += chamber_dist_penalty * chamber_dist_reg
            if chamber_param_penalty > 0:
                tx, ty, tz, rx, ry, rz, daz_g, del_g, ddepth_g = params[:9]
                s = chamber_param_tolerances
                chamber_param_reg = (
                    (tx / s['t_mm'])**2 + (ty / s['t_mm'])**2 + (tz / s['t_mm'])**2
                    + (rx / s['r_deg'])**2 + (ry / s['r_deg'])**2 + (rz / s['r_deg'])**2
                    + (daz_g / s['daz_deg'])**2 + (del_g / s['del_deg'])**2
                    + (ddepth_g / s['ddepth_mm'])**2
                )
                loss += chamber_param_penalty * chamber_param_reg
            if enable_per_session_corrections:
                loss += session_corr_penalty * reg_sum
        return loss

    def callback_progress(xk):
        call_count[0] += 1
        s_pure = -score_for_params(xk, include_reg=False)
        if s_pure > best['score']:
            best['score'] = s_pure
            best['params'] = xk.copy()
            best['iter'] = call_count[0]
            tx, ty, tz, rx, ry, rz, daz, del_, ddepth = xk[:9]
            print(f"  [{call_count[0]:4d}] acc={s_pure:.4f}  raw={latest['mean_raw']:.4f}  "
                  f"t=({tx:.2f},{ty:.2f},{tz:.2f})  "
                  f"r=({rx:.2f},{ry:.2f},{rz:.2f})  "
                  f"daz={daz:.2f}  del={del_:.2f}  ddepth={ddepth:.2f}")

    score_before = -score_for_params(full_x0, include_reg=False)
    raw_before = latest['mean_raw']
    print(f"\nOptimising (segmentation accuracy) over {len(session_info)} sessions  "
          f"(initial acc = {score_before:.4f}, raw = {raw_before:.4f}) ...")
    print(f"  Optimizer: {optimizer}")

    if optimizer not in _OPTIMIZERS:
        raise ValueError(f"Unknown optimizer {optimizer!r}.  Choose from: {list(_OPTIMIZERS)}")

    n_p = len(full_x0)
    steps = np.zeros(n_p)
    steps[:3] = 1.0
    steps[3:6] = 1.0
    steps[6]   = 0.5
    steps[7]   = 0.5
    steps[8]   = 0.5
    if enable_per_session_corrections and n_p > 9:
        steps[9:] = 0.5
    for idx, _ in fix_idx_val:
        steps[idx] = 1e-9

    maxiter_adj = maxiter + 500 * n_sess if enable_per_session_corrections else maxiter
    result = _OPTIMIZERS[optimizer](score_for_params, full_x0, steps,
                                    callback_progress, maxiter_adj)

    for idx, val in fix_idx_val:
        result.x[idx] = val

    score_after = -score_for_params(result.x, include_reg=False)
    raw_after = latest['mean_raw']
    print(f"\nOptimisation done: {result.message}")
    print(f"  acc:   {score_before:.4f} → {score_after:.4f}  "
          f"(Δ = {score_after - score_before:+.4f})")
    print(f"  raw:   {raw_before:.4f} → {raw_after:.4f}  "
          f"(Δ = {raw_after - raw_before:+.4f})")
    print("\nOptimised global parameters:")
    for name, val in zip(_OPT_PARAM_NAMES, result.x[:9]):
        print(f"  {name:<14s} = {val:+.4f}")

    per_session_corrections = {}
    if enable_per_session_corrections and len(result.x) > 9:
        per = result.x[9:].reshape(-1, 3)
        for i, sid in enumerate(session_ids):
            per_session_corrections[sid] = dict(
                daz_deg   = _tanh_bound(per[i, 0], session_corr_bounds['daz']),
                del_deg   = _tanh_bound(per[i, 1], session_corr_bounds['del_']),
                ddepth_mm = _tanh_bound(per[i, 2], session_corr_bounds['ddepth']),
            )
        print("\nPer-session corrections (effective, deg/mm):")
        for sid, c in per_session_corrections.items():
            print(f"  {str(sid):<20s}  daz={c['daz_deg']:+.3f}°  "
                  f"del={c['del_deg']:+.3f}°  ddepth={c['ddepth_mm']:+.3f}mm")

    return {
        'params': result.x,
        'param_names': full_param_names,
        'result': result,
        'score_before': score_before,
        'score_after': score_after,
        'raw_before': raw_before,
        'raw_after': raw_after,
        'per_session_corrections': per_session_corrections,
        'session_ids': session_ids,
        'session_corr_bounds': session_corr_bounds,
        'session_corr_penalty': session_corr_penalty,
        'variance_penalty': variance_penalty,
        'softmin_beta': softmin_beta,
        'optimizer': optimizer,
        'use_confidence_weights': use_confidence_weights,
        'fixed_globals': dict(fixed_globals) if fixed_globals else None,
        'target': 'segmentation',
    }


def apply_optimized_pipeline(mri_pipeline: dict, opt_result: dict) -> tuple:
    """Build a corrected pipeline and extract angle/depth offsets from opt_result."""
    params = opt_result['params']
    _, _, _, _, _, _, daz, del_, ddepth = params[:9]

    origin, x, y, normal = _apply_chamber_params(params, mri_pipeline)
    new_pipeline = dict(mri_pipeline)
    new_pipeline['origin'] = origin
    new_pipeline['x'] = x
    new_pipeline['y'] = y
    new_pipeline['normal'] = normal

    return new_pipeline, float(daz), float(del_), float(ddepth)


def save_optimized_params(
        opt_result: dict,
        mri_pipeline: dict,
        copy_dir: Optional[str] = None,
) -> str:
    """Save optimisation result to a timestamped file for later comparison."""
    import datetime

    params = opt_result['params']
    tx, ty, tz, rx, ry, rz, daz, del_, ddepth = params[:9]

    # Build the SAME correction the optimiser applied (rotation about the
    # chamber centre), so the saved 4x4 reproduces the optimised pose.
    center = mri_pipeline.get('chamber_center_base', np.zeros(3))
    M = _chamber_correction_matrix(params, center)

    results_dir = OPTIMIZATIONS_path
    os.makedirs(results_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    result_path = os.path.join(results_dir, f'opt_{timestamp}.json')

    result_data = {
        'timestamp': datetime.datetime.now().isoformat(),
        'score_before': float(opt_result['score_before']),
        'score_after': float(opt_result['score_after']),
        'params': {name: float(val)
                   for name, val in zip(opt_result['param_names'], params)},
        'chamber_correction_4x4': M.tolist(),
        'daz_deg': float(daz),
        'del_deg': float(del_),
        'ddepth_mm': float(ddepth),
        'per_session_corrections': opt_result.get('per_session_corrections', {}),
        'session_corr_bounds': opt_result.get('session_corr_bounds', SESSION_CORRECTION_BOUNDS),
        'session_corr_penalty': opt_result.get('session_corr_penalty', SESSION_CORRECTION_PENALTY),
        'variance_penalty': opt_result.get('variance_penalty', VARIANCE_PENALTY),
        'softmin_beta': opt_result.get('softmin_beta', SOFTMIN_BETA),
    }
    with open(result_path, 'w') as f:
        json.dump(result_data, f, indent=2)

    if copy_dir:
        import shutil
        copy_path = os.path.join(copy_dir, os.path.basename(result_path))
        shutil.copy2(result_path, copy_path)
        print(f"  Result saved → {result_path}")
        print(f"           copy → {copy_path}")
    else:
        print(f"  Result saved → {result_path}")
    print(f"  score: {opt_result['score_before']:.4f} → {opt_result['score_after']:.4f}")
    print(f"  daz={daz:+.4f}°  del={del_:+.4f}°  ddepth={ddepth:+.4f} mm")
    print(f"  To apply: apply_pca_opt_result('{result_path}', mri_pipeline)")
    return result_path


def apply_pca_opt_result(result_path: str, mri_pipeline: dict) -> None:
    """Apply a saved PCA optimisation result to the MRI viewer files."""
    from src.mri.correction import push_correction, save_corrections, load_corrections

    with open(result_path) as f:
        result = json.load(f)

    monkey_specific_path = mri_pipeline['monkey_specific_path']
    ch_corr_path = mri_pipeline['ch_corr_path']

    M = np.array(result['chamber_correction_4x4'])
    note = (f"PCA opt applied from {os.path.basename(result_path)} "
            f"(r {result['score_before']:.4f}→{result['score_after']:.4f})")
    _, ch_corr_cfg = load_corrections(ch_corr_path)
    push_correction(ch_corr_cfg, M, note=note)
    save_corrections(ch_corr_path, ch_corr_cfg)
    print(f"  Chamber correction updated → {ch_corr_path}")

    pen_offsets_path = os.path.splitext(monkey_specific_path)[0] + '_pen_offsets.json'
    offsets = {
        'timestamp': result['timestamp'],
        'note': note,
        'daz_deg': result['daz_deg'],
        'del_deg': result['del_deg'],
        'ddepth_mm': result['ddepth_mm'],
        'score_before': result['score_before'],
        'score_after': result['score_after'],
        'per_session_corrections': result.get('per_session_corrections', {}),
    }
    with open(pen_offsets_path, 'w') as f:
        json.dump(offsets, f, indent=2)
    print(f"  Pen offsets updated → {pen_offsets_path}")


# ---------------------------------------------------------------------------
# Segmentation-volume comparison
# ---------------------------------------------------------------------------
#
# Maps NMT-style segmentation values (0=out-of-brain, 1=sulcus, 2=GM,
# 3=sub-brain, 4=WM) onto a 3-class tissue label:
#   {0, 1} -> 0 (sulcus, tissue_score 0.0)
#   {2, 3} -> 1 (GM,     tissue_score 0.5)
#   {4}    -> 2 (WM,     tissue_score 1.0)

_SEG_CLASS_NAMES = ['sulcus', 'gm', 'wm']
_SEG_CLASS_TISSUE_SCORES = np.array([0.0, 0.5, 1.0])


def seg_values_to_classes(values: np.ndarray) -> np.ndarray:
    """Vectorised mapping of raw seg values (0-4) to 3-class labels (0/1/2)."""
    v = np.asarray(values)
    return np.where(v <= 1, 0, np.where(v <= 3, 1, 2)).astype(int)


def load_segmentation_volume(seg_path: str) -> dict:
    """Load a segmentation NIfTI for nearest-neighbor sampling along trajectories.

    If a paired `<seg_path>_corrections.json` exists, that correction is applied
    (analogous to load_mri_pipeline). Otherwise the native affine is used as-is,
    which is the right choice when the segmentation has been rigidly aligned
    into MRI space already (e.g. NMT_v2.0_asym_segmentation_rigid_aligned).
    """
    from src.mri.volume import load_volume
    from src.mri.correction import load_corrections

    data, native_affine, _, _ = load_volume(seg_path)
    if data.ndim == 4:
        data = data[..., 0]

    corr_path = os.path.splitext(seg_path)[0] + '_corrections.json'
    if os.path.exists(corr_path):
        seg_corr, _ = load_corrections(corr_path)
        print(f"  Segmentation correction: {corr_path}")
    else:
        seg_corr = np.eye(4)
        print(f"  Segmentation: no paired _corrections.json found "
              f"(assuming already aligned to MRI space)")

    corrected_affine = seg_corr @ native_affine
    inv_corrected = np.linalg.inv(corrected_affine)

    return {
        'data': data,
        'inv_corrected': inv_corrected,
        'path': seg_path,
    }


def sample_segmentation_along_trajectory(
        mri_pipeline: dict,
        seg_volume: dict,
        az_deg: float,
        el_deg: float,
        depths_mm: np.ndarray,
) -> np.ndarray:
    """Nearest-neighbor sample of the segmentation volume along a trajectory.

    Penetration geometry (chamber origin/x/y/normal, cor_offset) is reused from
    mri_pipeline; only the voxel grid changes. order=0 because segmentation
    labels are categorical.
    """
    from src.mri.chamber import calc_penetration_target

    origin = mri_pipeline['origin']
    x = mri_pipeline['x']
    y = mri_pipeline['y']
    normal = mri_pipeline['normal']
    cor_offset = mri_pipeline['cor_offset']

    data = seg_volume['data']
    inv_corrected = seg_volume['inv_corrected']

    max_dist = float(np.max(depths_mm)) + 1.0
    _, direction, top_pt = calc_penetration_target(
        origin, az_deg, el_deg, max_dist, x, y, normal, cor_offset
    )

    pts = np.array([top_pt + d * direction for d in depths_mm])
    ones = np.ones((len(pts), 1))
    vox_coords = (inv_corrected @ np.hstack([pts, ones]).T).T[:, :3]

    values = map_coordinates(data, vox_coords.T, order=0, mode='constant', cval=0.0)
    return values.astype(int)


def compute_segmentation_comparison(
        df: pd.DataFrame,
        conn: Connection,
        mri_pipeline: dict,
        seg_volume: dict,
        daz: float = 0.0,
        del_: float = 0.0,
        ddepth: float = 0.0,
        per_session_corrections: dict = None,
) -> pd.DataFrame:
    """Add segmentation columns sampled along each session's corrected trajectory.

    Adds:
      seg_raw          : raw seg label (0-4)
      seg_class        : 3-class label (0=sulcus, 1=GM, 2=WM); -1 where no penetration
      seg_tissue_score : 0.0 / 0.5 / 1.0
    """
    df = df.copy()
    df['seg_raw'] = -1
    df['seg_class'] = -1
    df['seg_tissue_score'] = np.nan

    for session_id in df['session_id'].unique():
        pen = get_penetration_for_session(conn, session_id)
        if pen is None:
            print(f"  Warning: no penetration found for session {session_id}, skipping segmentation.")
            continue

        sc = (per_session_corrections or {}).get(session_id, {})
        sess_daz    = daz    + sc.get('daz_deg',    0.0)
        sess_del    = del_   + sc.get('del_deg',    0.0)
        sess_ddepth = ddepth + sc.get('ddepth_mm',  0.0)

        mask = df['session_id'] == session_id
        depths = df.loc[mask, 'depth_under_chamber_mm'].values + sess_ddepth
        seg_vals = sample_segmentation_along_trajectory(
            mri_pipeline, seg_volume,
            pen['az_deg'] + sess_daz, pen['el_deg'] + sess_del, depths,
        )
        classes = seg_values_to_classes(seg_vals)
        tissue_scores = _SEG_CLASS_TISSUE_SCORES[classes]

        df.loc[mask, 'seg_raw'] = seg_vals
        df.loc[mask, 'seg_class'] = classes
        df.loc[mask, 'seg_tissue_score'] = tissue_scores

        n_sulcus = int((classes == 0).sum())
        n_gm     = int((classes == 1).sum())
        n_wm     = int((classes == 2).sum())
        print(f"  {session_id} ({pen['pen_type']}): "
              f"seg sulcus/gm/wm = {n_sulcus}/{n_gm}/{n_wm}")

    return df


def compute_segmentation_accuracy(df: pd.DataFrame) -> pd.DataFrame:
    """Per-session 3-class classification accuracy (argmax over p_sulcus/p_gm/p_wm
    vs seg_class).

    Confidence-weighted accuracy is also returned for inspection (rewards
    confident correct predictions, downweights uncertain ones).
    """
    required_p = ['p_sulcus', 'p_gm', 'p_wm']
    missing = [c for c in required_p if c not in df.columns]
    if missing:
        raise RuntimeError(
            f"compute_segmentation_accuracy needs columns {required_p}; missing {missing}. "
            "Make sure the predictor's TissueModel has sulcus / gm / wm classes."
        )
    if 'seg_class' not in df.columns:
        raise RuntimeError("compute_segmentation_accuracy needs a 'seg_class' column "
                           "(call compute_segmentation_comparison first).")

    p_arr = df[required_p].values
    predicted_class = np.argmax(p_arr, axis=1)
    has_conf = 'tissue_confidence' in df.columns

    records = []
    for session_id in df['session_id'].unique():
        mask = df['session_id'] == session_id
        sdata = df[mask]
        valid = (sdata['seg_class'] >= 0).values
        n_valid = int(valid.sum())
        if n_valid < 1:
            records.append({
                'session_id': session_id,
                'accuracy': np.nan,
                'weighted_accuracy': np.nan,
                'n_points': 0,
            })
            continue

        true_c = sdata['seg_class'].values[valid]
        pred_c = predicted_class[mask.values][valid]
        match = (pred_c == true_c).astype(float)

        acc = float(match.mean())
        if has_conf:
            w = sdata['tissue_confidence'].values[valid]
            w_sum = float(w.sum())
            w_acc = float((w * match).sum() / w_sum) if w_sum > 0 else np.nan
        else:
            w_acc = np.nan

        records.append({
            'session_id': session_id,
            'accuracy': acc,
            'weighted_accuracy': w_acc,
            'n_points': n_valid,
        })

    result = pd.DataFrame(records).set_index('session_id')
    print("\nSegmentation classification accuracy:")
    print(result.to_string())
    return result


def load_corrections_file(corrections_path: str) -> dict:
    """Load a saved opt_*.json corrections file (timestamped output of save_optimized_params).

    Returns the raw dict with keys: daz_deg, del_deg, ddepth_mm, per_session_corrections,
    chamber_correction_4x4, ... — used by run_pooled.py to apply a single corrections
    file before comparing multiple predictors.
    """
    with open(corrections_path) as f:
        return json.load(f)


def apply_corrections_to_pipeline(
        mri_pipeline: dict,
        corrections: dict,
) -> tuple:
    """Apply a loaded corrections dict (from load_corrections_file) to mri_pipeline.

    Returns (new_pipeline, daz, del_, ddepth, per_session_corrections) ready
    to pass to compute_mri_comparison.
    """
    from src.mri.chamber import fit_chamber

    M = np.array(corrections['chamber_correction_4x4'])
    R = M[:3, :3]
    t = M[:3, 3]

    screws = mri_pipeline['screws_world_base']
    screws_new = (R @ screws.T).T + t
    _, origin, x, y, normal = fit_chamber(
        screws_new,
        mri_pipeline['ref_idx'],
        mri_pipeline['cor_offset'],
        mri_pipeline['is_fit_circle'],
    )

    new_pipeline = dict(mri_pipeline)
    new_pipeline['origin'] = origin
    new_pipeline['x'] = x
    new_pipeline['y'] = y
    new_pipeline['normal'] = normal

    return (
        new_pipeline,
        float(corrections.get('daz_deg', 0.0)),
        float(corrections.get('del_deg', 0.0)),
        float(corrections.get('ddepth_mm', 0.0)),
        corrections.get('per_session_corrections', {}) or {},
    )
