"""
Correction matrix persistence, history management, and rotation/translation builders.

The correction matrix is a 4x4 affine that sits between native MRI world space
and corrected stereotaxic world space:
    voxel -> [native_affine] -> raw_world -> [correction] -> corrected_world
"""

import numpy as np
import json, os, datetime


# ====================================================================
# Rotation / translation builders (world-space, degrees)
# ====================================================================

def rot_x(deg):
    r = np.radians(deg); c, s = np.cos(r), np.sin(r)
    M = np.eye(4); M[1,1]=c; M[1,2]=-s; M[2,1]=s; M[2,2]=c; return M

def rot_y(deg):
    r = np.radians(deg); c, s = np.cos(r), np.sin(r)
    M = np.eye(4); M[0,0]=c; M[0,2]=s; M[2,0]=-s; M[2,2]=c; return M

def rot_z(deg):
    r = np.radians(deg); c, s = np.cos(r), np.sin(r)
    M = np.eye(4); M[0,0]=c; M[0,1]=-s; M[1,0]=s; M[1,1]=c; return M

def xlate(dx, dy, dz):
    M = np.eye(4); M[:3, 3] = [dx, dy, dz]; return M

def scale(sx, sy, sz):
    M = np.eye(4); M[0,0]=sx; M[1,1]=sy; M[2,2]=sz; return M


# ====================================================================
# Persistence
# ====================================================================

def _default_entry(matrix=None, note="identity"):
    return {
        "timestamp": datetime.datetime.now().isoformat(),
        "note": note,
        "matrix": (matrix if matrix is not None else np.eye(4)).tolist(),
    }

def load_corrections(path):
    """Load correction matrix and config from JSON. Returns (matrix_4x4, config_dict)."""
    if not os.path.exists(path):
        e = _default_entry()
        cfg = {"correction_history": [e], "current_index": 0}
        return np.eye(4), cfg
    with open(path) as f:
        cfg = json.load(f)
    hist = cfg.get("correction_history", [])
    if not hist:
        e = _default_entry()
        cfg["correction_history"] = [e]
        cfg["current_index"] = 0
        return np.eye(4), cfg
    idx = cfg.get("current_index", len(hist) - 1)
    return np.array(hist[idx]["matrix"]), cfg

def save_corrections(path, cfg):
    with open(path, "w") as f:
        json.dump(cfg, f, indent=2)

def push_correction(cfg, mat, note=""):
    """Append a new correction to history and set as current."""
    cfg["correction_history"].append(_default_entry(mat, note))
    cfg["current_index"] = len(cfg["correction_history"]) - 1

def load_crop_bounds(cfg):
    """Extract crop bounds dict from config."""
    cb = cfg.get("crop_bounds", {})
    return {int(k): tuple(v) for k, v in cb.items()}

def save_crop_bounds(cfg, crop_bounds):
    """Store crop bounds into config dict."""
    if crop_bounds:
        cfg["crop_bounds"] = {str(k): list(v) for k, v in crop_bounds.items()}
    else:
        cfg.pop("crop_bounds", None)