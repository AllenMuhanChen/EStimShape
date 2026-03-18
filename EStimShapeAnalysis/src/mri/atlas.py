"""
Atlas overlay for the tri-planar MRI viewer.

Loads a NIfTI label atlas (e.g. D99 in NMT v2.0), applies a user-adjustable
correction transform to register it to the MRI's corrected world space, and
draws region-boundary contours on top of the MRI slices.

Transform chain
---------------
    atlas_voxel  →  [atlas_sform]  →  atlas_stereo  →  [atlas_correction]  →  corrected_world

    atlas_correction is the manually adjustable 4×4 affine (rotation + translation)
    that brings the atlas template space into alignment with the subject MRI.

    To reslice from corrected_world back to atlas voxels:
        atlas_voxel = inv(atlas_correction @ atlas_sform) @ corrected_world_pt
"""

import numpy as np
import nibabel as nib
from scipy.ndimage import map_coordinates


# ====================================================================
# Loading
# ====================================================================

def load_atlas(nifti_path):
    """
    Load a NIfTI atlas volume.

    Returns
    -------
    data : ndarray, shape (I, J, K) — integer label volume
    sform : ndarray, shape (4, 4) — voxel-to-stereotax affine from the NIfTI header
    """
    img = nib.load(nifti_path)
    sform = img.affine.copy()

    # Fix NIfTI headers with nan slope/intercept — nibabel multiplies raw
    # data by scl_slope which turns everything to nan → 0 when cast to int.
    # For integer label atlases, slope=1 intercept=0 is always correct.
    hdr = img.header
    slope, inter = hdr.get_slope_inter()
    if slope is None or np.isnan(slope):
        hdr.set_slope_inter(1, 0)

    data = np.asarray(img.dataobj)

    # Squeeze trailing singleton dims (some atlases are (I,J,K,1))
    if data.ndim == 4 and data.shape[3] == 1:
        data = data[:, :, :, 0]
    data = data.astype(int)
    return data, sform


def load_atlas_labels(label_file):
    """
    Load label name table (D99 format: ``index  name [name ...]`` per line).

    Returns dict  {int_index: str_name}.
    """
    labels = {}
    with open(label_file) as f:
        for line in f:
            fields = line.rstrip().split()
            if not fields:
                continue
            try:
                idx = int(fields[0])
            except ValueError:
                continue
            labels[idx] = ', '.join(fields[1:])
    return labels


# ====================================================================
# Reslicing
# ====================================================================

def reslice_atlas(atlas_data, inv_atlas_combined, view_display_bounds, grid_size,
                  slice_cfg, cursor_world):
    """
    Sample a 2-D label slice from the atlas volume.

    Uses nearest-neighbour interpolation (order 0) since the atlas contains
    integer region labels.

    Parameters
    ----------
    atlas_data : ndarray (I, J, K)
        Integer label volume.
    inv_atlas_combined : ndarray (4, 4)
        inv(atlas_correction @ atlas_sform) — maps corrected-world → atlas voxel.
    view_display_bounds : (h_lo, h_hi, v_lo, v_hi)
        Horizontal and vertical world-coordinate extent for this view.
    grid_size : (n_h, n_v)
        Number of sample points along each axis.
    slice_cfg : (fix_wax, h_wax, v_wax)
        Which world axes are fixed / horizontal / vertical for this view.
    cursor_world : array (3,)
        Current crosshair position — supplies the fixed-axis value.

    Returns
    -------
    label_2d : ndarray (n_v, n_h), int
    h_coords : 1-D array, mm
    v_coords : 1-D array, mm
    """
    fix_wax, h_wax, v_wax = slice_cfg
    n_h, n_v = grid_size
    h_lo, h_hi, v_lo, v_hi = view_display_bounds

    fix_val = cursor_world[fix_wax]

    h_coords = np.linspace(h_lo, h_hi, n_h)
    v_coords = np.linspace(v_hi, v_lo, n_v)  # top = max (matches volume.reslice_view)

    hh, vv = np.meshgrid(h_coords, v_coords)

    world_pts = np.ones((n_v, n_h, 4))
    world_pts[:, :, fix_wax] = fix_val
    world_pts[:, :, h_wax] = hh
    world_pts[:, :, v_wax] = vv

    flat = world_pts.reshape(-1, 4)
    vox_flat = (inv_atlas_combined @ flat.T).T[:, :3]

    coords = [vox_flat[:, ax] for ax in range(3)]
    sampled = map_coordinates(atlas_data, coords, order=0, mode='constant', cval=0)
    label_2d = sampled.reshape(n_v, n_h).astype(int)
    return label_2d, h_coords, v_coords


# ====================================================================
# Boundary extraction
# ====================================================================

def label_boundaries(label_2d):
    """
    Compute a binary edge mask from a 2-D label image.

    A pixel is marked as a boundary if:
      - it has a nonzero label, AND
      - at least one of its 4-connected neighbours has a different label.

    Returns
    -------
    edges : ndarray (n_v, n_h), bool
    """
    lbl = label_2d
    mask = lbl > 0

    # Shift in four cardinal directions and compare
    diff_up    = np.zeros_like(mask)
    diff_down  = np.zeros_like(mask)
    diff_left  = np.zeros_like(mask)
    diff_right = np.zeros_like(mask)

    diff_up[1:, :]    = lbl[1:, :]  != lbl[:-1, :]
    diff_down[:-1, :] = lbl[:-1, :] != lbl[1:, :]
    diff_left[:, 1:]  = lbl[:, 1:]  != lbl[:, :-1]
    diff_right[:, :-1] = lbl[:, :-1] != lbl[:, 1:]

    edges = mask & (diff_up | diff_down | diff_left | diff_right)
    return edges


# ====================================================================
# Drawing
# ====================================================================

def draw_atlas_contours(ax, label_2d, h_coords, v_coords,
                        display_offset_h=0.0, display_offset_v=0.0,
                        color='cyan', linewidth=0.6, alpha=0.7):
    """
    Draw atlas region boundary contours on a matplotlib Axes.

    Parameters
    ----------
    ax : matplotlib Axes
    label_2d : ndarray (n_v, n_h), int  — resliced label image
    h_coords, v_coords : 1-D arrays      — world coordinates of the grid
    display_offset_h/v : float            — EBZ offset to convert to display coords
    color : str
    linewidth : float
    alpha : float
    """
    edges = label_boundaries(label_2d)
    if not edges.any():
        return

    # Coordinate arrays in display (EBZ-relative) space
    h_disp = h_coords - display_offset_h
    v_disp = v_coords - display_offset_v

    # contour expects (rows, cols) with coordinate arrays matching the grid
    ax.contour(h_disp, v_disp, edges.astype(float),
               levels=[0.5], colors=color, linewidths=linewidth,
               alpha=alpha)


def atlas_label_at_cursor(atlas_data, inv_atlas_combined, cursor_world, label_names):
    """
    Look up the atlas region label at a world-space point.

    Returns
    -------
    label_str : str or None
        Region name, or None if outside the atlas / label 0.
    """
    info = atlas_label_detail(atlas_data, inv_atlas_combined, cursor_world, label_names)
    if info is None:
        return None
    return info['name']


def atlas_label_detail(atlas_data, inv_atlas_combined, cursor_world, label_names):
    """
    Detailed atlas lookup at a world-space point.

    Returns
    -------
    dict with keys 'index', 'name', 'atlas_voxel' — or None if outside / label 0.
    """
    pt = np.array([cursor_world[0], cursor_world[1], cursor_world[2], 1.0])
    vox = (inv_atlas_combined @ pt)[:3]
    vox_idx = tuple(np.round(vox).astype(int))

    shape = atlas_data.shape[:3]  # handle (I,J,K) or (I,J,K,1)
    for v, s in zip(vox_idx, shape):
        if v < 0 or v >= s:
            return None

    # Index into first 3 dims only
    label_val = int(atlas_data[vox_idx[0], vox_idx[1], vox_idx[2]])
    if label_val == 0:
        return None

    name = label_names.get(label_val, f"label {label_val}")
    return {
        'index': label_val,
        'name': name,
        'atlas_voxel': vox_idx,
    }