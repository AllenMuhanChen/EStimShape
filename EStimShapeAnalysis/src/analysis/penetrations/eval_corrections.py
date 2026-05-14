#!/usr/bin/env python3
"""
eval_corrections.py — Evaluate saved trajectory corrections on held-out sessions.

Edit the variables in the CONFIG section at the bottom of this file, then run:
    python eval_corrections.py
"""

import json
import os
import sys

import numpy as np
import pandas as pd
from scipy.ndimage import map_coordinates

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, '../../..'))

from clat.util.connection import Connection
from src.analysis.penetrations.penetrations_pca import (
    MRI_VIEWER_CONFIG_PATH,
    MODEL_PCA_V2,
    _weighted_pearson_r,
    load_and_perform_pca,
    compute_tissue_confidence,
    get_penetration_for_session,
    load_mri_pipeline,
)
from src.mri.chamber import fit_chamber, calc_penetration_target


# ─────────────────────────────────────────────────────────────────────────────
# Core evaluation logic
# ─────────────────────────────────────────────────────────────────────────────

def load_corrections(corrections_path: str) -> dict:
    with open(corrections_path) as f:
        c = json.load(f)
    print(f"Loaded corrections: {corrections_path}")
    print(f"  score_before={c.get('score_before', '?'):.4f}  "
          f"score_after={c.get('score_after', '?'):.4f}")
    print(f"  global daz={c.get('daz_deg', 0):+.3f}°  "
          f"del={c.get('del_deg', 0):+.3f}°  "
          f"ddepth={c.get('ddepth_mm', 0):+.3f}mm")
    psc = c.get('per_session_corrections', {})
    if psc:
        print(f"  per-session corrections present for {len(psc)} session(s):")
        for sid, vals in psc.items():
            print(f"    {sid:<20s}  daz={vals.get('daz_deg', 0):+.3f}°  "
                  f"del={vals.get('del_deg', 0):+.3f}°  "
                  f"ddepth={vals.get('ddepth_mm', 0):+.3f}mm")
    return c


def build_corrected_pipeline(mri_pipeline: dict, corrections: dict) -> dict:
    """Apply chamber_correction_4x4 from JSON to get a new chamber geometry."""
    M = np.array(corrections['chamber_correction_4x4'])
    R, t = M[:3, :3], M[:3, 3]

    screws_corrected = (R @ mri_pipeline['screws_world_base'].T).T + t
    _, origin, x, y, normal = fit_chamber(
        screws_corrected,
        mri_pipeline['ref_idx'],
        mri_pipeline['cor_offset'],
        mri_pipeline['is_fit_circle'],
    )
    new_pipe = dict(mri_pipeline)
    new_pipe.update(origin=origin, x=x, y=y, normal=normal)
    return new_pipe


def score_session(
    session_id: str,
    df_conf: pd.DataFrame,
    conn: Connection,
    mri_pipeline: dict,
    daz: float = 0.0,
    del_: float = 0.0,
    ddepth: float = 0.0,
) -> dict:
    """
    Score a single session: compute weighted and unweighted Pearson r
    between tissue_score and MRI signal sampled along the (corrected) trajectory.
    """
    pen = get_penetration_for_session(conn, session_id)
    if pen is None:
        return {'session_id': session_id, 'r_weighted': np.nan,
                'r_unweighted': np.nan, 'n_points': 0, 'error': 'no penetration'}

    mask = df_conf['session_id'] == session_id
    sdata = df_conf[mask].dropna(subset=['tissue_score', 'depth_under_chamber_mm'])
    n = len(sdata)
    if n < 3:
        return {'session_id': session_id, 'r_weighted': np.nan,
                'r_unweighted': np.nan, 'n_points': n, 'error': 'too few points'}

    depths = sdata['depth_under_chamber_mm'].values + ddepth
    ts = sdata['tissue_score'].values
    conf = sdata['tissue_confidence'].values if 'tissue_confidence' in sdata.columns else None

    if depths.max() <= 0:
        return {'session_id': session_id, 'r_weighted': np.nan,
                'r_unweighted': np.nan, 'n_points': n, 'error': 'depths non-positive'}

    try:
        data = mri_pipeline['data']
        inv_corrected = mri_pipeline['inv_corrected']
        origin = mri_pipeline['origin']
        x = mri_pipeline['x']
        y = mri_pipeline['y']
        normal = mri_pipeline['normal']
        cor_offset = mri_pipeline['cor_offset']

        _, direction, top_pt = calc_penetration_target(
            origin, pen['az_deg'] + daz, pen['el_deg'] + del_,
            float(depths.max()) + 1.0, x, y, normal, cor_offset,
        )
        pts = top_pt + depths[:, None] * direction[None, :]
        ones = np.ones((len(pts), 1))
        vox = (inv_corrected @ np.hstack([pts, ones]).T).T[:, :3]
        mri_vals = map_coordinates(data, vox.T, order=1,
                                   mode='constant', cval=0.0).astype(float)
    except Exception as e:
        return {'session_id': session_id, 'r_weighted': np.nan,
                'r_unweighted': np.nan, 'n_points': n, 'error': str(e)}

    r_w = _weighted_pearson_r(ts, mri_vals, conf)
    r_u = _weighted_pearson_r(ts, mri_vals, None)
    return {'session_id': session_id, 'r_weighted': r_w,
            'r_unweighted': r_u, 'n_points': n, 'error': None}


def evaluate(
    corrections_path: str,
    session_ids: list,
    conn: Connection,
    table_name: str = 'PenetrationMetrics',
    mri_config_path: str = MRI_VIEWER_CONFIG_PATH,
    exclude_from_pca: list = None,
) -> pd.DataFrame:
    """
    Full evaluation pipeline.

    Returns a DataFrame with columns:
        session_id, r_w_before, r_u_before, r_w_after, r_u_after,
        delta_r_w, delta_r_u, n_points
    """
    corrections = load_corrections(corrections_path)

    # ── Load tissue scores (PCA fit on all or training-only sessions) ──────
    print(f"\nLoading PenetrationMetrics and fitting PCA ...")
    df, pca, X_pca, feature_columns, scaler = load_and_perform_pca(
        conn, table_name,
        exclude_sessions=exclude_from_pca or [],
        within_session_normalize=True,
        pc_smooth_sigma=2.0,
        varimax_n_components=2,
    )
    df_conf = compute_tissue_confidence(df, model=MODEL_PCA_V2)

    # ── Load MRI pipeline ──────────────────────────────────────────────────
    print("\nLoading MRI pipeline ...")
    mri_pipeline = load_mri_pipeline(mri_config_path)

    # ── Build corrected pipeline ───────────────────────────────────────────
    corrected_pipeline = build_corrected_pipeline(mri_pipeline, corrections)

    global_daz    = corrections.get('daz_deg',    0.0)
    global_del    = corrections.get('del_deg',    0.0)
    global_ddepth = corrections.get('ddepth_mm',  0.0)
    per_sess_corr = corrections.get('per_session_corrections', {})

    # ── Score each requested session ───────────────────────────────────────
    # Check which sessions actually have data
    available = set(df_conf['session_id'].unique())
    missing = [s for s in session_ids if s not in available]
    if missing:
        print(f"\nWarning: no PCA data for session(s): {missing}")

    rows = []
    for sid in session_ids:
        if sid not in available:
            rows.append({'session_id': sid, 'r_w_before': np.nan,
                         'r_u_before': np.nan, 'r_w_after': np.nan,
                         'r_u_after': np.nan, 'n_points': 0,
                         'note': 'no PCA data'})
            continue

        # Uncorrected score (raw chamber, zero angle/depth offsets)
        before = score_session(sid, df_conf, conn, mri_pipeline,
                               daz=0.0, del_=0.0, ddepth=0.0)

        # Corrected score
        psc = per_sess_corr.get(sid, {})
        after = score_session(
            sid, df_conf, conn, corrected_pipeline,
            daz   = global_daz    + psc.get('daz_deg',    0.0),
            del_  = global_del    + psc.get('del_deg',    0.0),
            ddepth= global_ddepth + psc.get('ddepth_mm',  0.0),
        )

        rows.append({
            'session_id':  sid,
            'r_w_before':  before['r_weighted'],
            'r_u_before':  before['r_unweighted'],
            'r_w_after':   after['r_weighted'],
            'r_u_after':   after['r_unweighted'],
            'delta_r_w':   after['r_weighted']   - before['r_weighted']
                           if not (np.isnan(after['r_weighted']) or np.isnan(before['r_weighted']))
                           else np.nan,
            'delta_r_u':   after['r_unweighted'] - before['r_unweighted']
                           if not (np.isnan(after['r_unweighted']) or np.isnan(before['r_unweighted']))
                           else np.nan,
            'n_points':    after['n_points'],
            'note':        after.get('error') or '',
        })

    result = pd.DataFrame(rows).set_index('session_id')

    # ── Print summary ──────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("CORRECTION EVALUATION (held-out sessions)")
    print("=" * 70)
    print(f"{'Session':<20s} {'r_w_before':>10s} {'r_w_after':>10s} "
          f"{'Δr_w':>8s} {'r_u_before':>10s} {'r_u_after':>10s} "
          f"{'Δr_u':>8s} {'N':>5s}  note")
    print("-" * 90)
    for sid, row in result.iterrows():
        def fmt(v):
            return f"{v:+.4f}" if not np.isnan(v) else "    nan"
        print(f"{str(sid):<20s} {fmt(row.r_w_before):>10s} {fmt(row.r_w_after):>10s} "
              f"{fmt(row.delta_r_w):>8s} {fmt(row.r_u_before):>10s} "
              f"{fmt(row.r_u_after):>10s} {fmt(row.delta_r_u):>8s} "
              f"{int(row.n_points):>5d}  {row.note}")
    print("-" * 90)

    valid = result.dropna(subset=['r_w_before', 'r_w_after'])
    if len(valid) > 0:
        print(f"{'MEAN':<20s} {valid.r_w_before.mean():>+10.4f} "
              f"{valid.r_w_after.mean():>+10.4f} "
              f"{valid.delta_r_w.mean():>+8.4f} "
              f"{valid.r_u_before.mean():>+10.4f} "
              f"{valid.r_u_after.mean():>+10.4f} "
              f"{valid.delta_r_u.mean():>+8.4f} "
              f"{int(valid.n_points.sum()):>5d}")
    print("=" * 70)

    return result


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG — edit these variables, then run the script
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':

    # Path to the corrections JSON saved by save_optimized_params()
    CORRECTIONS_PATH = "/home/connorlab/git/EStimShape/EStimShapeAnalysis/src/mri/opt_20260512_150605.json"

    # Sessions to evaluate (held-out sessions not used during optimization)
    SESSIONS = [
        "260514_0",
    ]

    # Set to the same list as SESSIONS for a strict train/test PCA split
    # (those sessions are excluded from PCA fitting so their tissue scores
    #  come from the training distribution).  Set to [] to include all sessions
    # in PCA fitting (simpler, slightly less rigorous).
    EXCLUDE_FROM_PCA = []

    # Database connection
    DB_NAME  = "allen_data_repository"
    DB_HOST  = "172.30.6.61"
    DB_USER  = "xper_rw"
    DB_PASS  = "up2nite"

    # PenetrationMetrics table
    TABLE = "PenetrationMetrics"

    # MRI viewer config (leave as-is unless you have a non-default setup)
    MRI_CONFIG = MRI_VIEWER_CONFIG_PATH

    # ── run ──────────────────────────────────────────────────────────────────
    conn = Connection(database=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
    evaluate(
        corrections_path=CORRECTIONS_PATH,
        session_ids=SESSIONS,
        conn=conn,
        table_name=TABLE,
        mri_config_path=MRI_CONFIG,
        exclude_from_pca=EXCLUDE_FROM_PCA or None,
    )
