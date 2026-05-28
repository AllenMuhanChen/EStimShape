"""
Atlas overlay for the tri-planar MRI viewer.

Loads a NIfTI label atlas (e.g. D99 in NMT v2.0) that animal_warper has
warped into the subject's native scanner space, and draws region-boundary
contours on top of the MRI slices.

Transform chain
---------------
    atlas_voxel  →  [atlas_sform]  →  subject_native_world  →  [correction]  →  corrected_world

    The atlas shares the subject's native voxel→world map (animal_warper output),
    so the subject correction (AC/PC alignment) moves the atlas in lock-step
    with the subject MRI — there is no atlas-specific correction.

    To reslice from corrected_world back to atlas voxels:
        atlas_voxel = inv(correction @ atlas_sform) @ corrected_world_pt
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
        inv(correction @ atlas_sform) — maps corrected-world → atlas voxel.
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


def draw_region_fills(ax, label_2d, h_coords, v_coords, highlights,
                      display_offset_h=0.0, display_offset_v=0.0, alpha=0.5):
    """
    Fill specific atlas regions with solid colors.

    Parameters
    ----------
    label_2d : ndarray (n_v, n_h), int — resliced atlas label image
    highlights : dict {int label_index: color_str}
    alpha : float — fill transparency
    """
    h_disp = h_coords - display_offset_h
    v_disp = v_coords - display_offset_v
    for idx, color in highlights.items():
        mask = (label_2d == idx)
        if not mask.any():
            continue
        # contourf needs at least one full cell of the region; guard tiny masks
        try:
            ax.contourf(h_disp, v_disp, mask.astype(float),
                        levels=[0.5, 1.5], colors=[color], alpha=alpha)
        except Exception:
            pass


# ====================================================================
# Follower overlay (arbitrary NIfTI shown as a filled colormap, no labels)
# ====================================================================

def load_follower(nifti_path):
    """
    Load an arbitrary overlay NIfTI (e.g. a tissue segmentation) that shares
    the atlas's aligned world space.

    Returns
    -------
    data : ndarray (I, J, K), float32
    sform : ndarray (4, 4)
    is_label : bool — True if the volume looks like discrete integer labels
    """
    img = nib.load(nifti_path)
    sform = img.affine.copy()

    hdr = img.header
    slope, inter = hdr.get_slope_inter()
    if slope is None or (isinstance(slope, float) and np.isnan(slope)):
        hdr.set_slope_inter(1, 0)

    data = np.asarray(img.dataobj, dtype=np.float32)
    if data.ndim == 4 and data.shape[3] == 1:
        data = data[:, :, :, 0]

    # Heuristic: integer-valued with few distinct values => label volume.
    finite = data[np.isfinite(data)]
    is_label = False
    if finite.size:
        rounded = np.round(finite)
        if np.allclose(finite, rounded, atol=1e-4):
            n_distinct = len(np.unique(rounded))
            is_label = n_distinct <= 256
    return data, sform, is_label


def reslice_follower(data, inv_combined, view_display_bounds, grid_size,
                     slice_cfg, cursor_world, interp_order=0):
    """
    Sample a 2-D slice from a follower volume. interp_order=0 (NN) for label
    volumes, higher for continuous. Returns (val_2d float, h_coords, v_coords).
    """
    fix_wax, h_wax, v_wax = slice_cfg
    n_h, n_v = grid_size
    h_lo, h_hi, v_lo, v_hi = view_display_bounds

    fix_val = cursor_world[fix_wax]
    h_coords = np.linspace(h_lo, h_hi, n_h)
    v_coords = np.linspace(v_hi, v_lo, n_v)
    hh, vv = np.meshgrid(h_coords, v_coords)

    world_pts = np.ones((n_v, n_h, 4))
    world_pts[:, :, fix_wax] = fix_val
    world_pts[:, :, h_wax] = hh
    world_pts[:, :, v_wax] = vv

    flat = world_pts.reshape(-1, 4)
    vox_flat = (inv_combined @ flat.T).T[:, :3]
    coords = [vox_flat[:, ax] for ax in range(3)]
    sampled = map_coordinates(data, coords, order=interp_order,
                              mode='constant', cval=0)
    return sampled.reshape(n_v, n_h), h_coords, v_coords


def draw_follower_overlay(ax, val_2d, h_coords, v_coords,
                          display_offset_h=0.0, display_offset_v=0.0,
                          cmap='tab10', alpha=0.5, vmin=None, vmax=None,
                          mask_zero=True):
    """
    Draw a follower volume as a translucent filled colormap over the MRI.

    Background (value 0) is rendered transparent when mask_zero is True.
    """
    arr = np.array(val_2d, dtype=float)
    if mask_zero:
        arr = np.ma.masked_where(arr == 0, arr)
    if not np.ma.is_masked(arr) and not np.any(np.isfinite(arr)):
        return
    h_disp = h_coords - display_offset_h
    v_disp = v_coords - display_offset_v
    extent = [h_disp[0], h_disp[-1], v_disp[-1], v_disp[0]]
    ax.imshow(arr, cmap=cmap, alpha=alpha, aspect='equal', origin='upper',
              interpolation='nearest', extent=extent, vmin=vmin, vmax=vmax)


def follower_value_at_cursor(data, inv_combined, cursor_world, is_label=True):
    """
    Return the follower volume's value at a world point, or None if outside.
    For label volumes the value is returned as an int.
    """
    pt = np.array([cursor_world[0], cursor_world[1], cursor_world[2], 1.0])
    vox = (inv_combined @ pt)[:3]
    vox_idx = tuple(np.round(vox).astype(int))
    shape = data.shape[:3]
    for v, s in zip(vox_idx, shape):
        if v < 0 or v >= s:
            return None
    val = data[vox_idx[0], vox_idx[1], vox_idx[2]]
    if is_label:
        return int(round(float(val)))
    return float(val)


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


# ====================================================================
# Template MRI (e.g. NMT_v2.0_sym.nii.gz)
# ====================================================================

def load_template_mri(nifti_path):
    """
    Load a template MRI volume that shares the same voxel space as the atlas.

    Handles the same nan slope/intercept issue as load_atlas.

    Returns
    -------
    data : ndarray (I, J, K), float32
    sform : ndarray (4, 4)
    """
    img = nib.load(nifti_path)
    sform = img.affine.copy()

    hdr = img.header
    slope, inter = hdr.get_slope_inter()
    if slope is None or (isinstance(slope, float) and np.isnan(slope)):
        hdr.set_slope_inter(1, 0)

    data = np.asarray(img.dataobj, dtype=np.float32)
    if data.ndim == 4 and data.shape[3] == 1:
        data = data[:, :, :, 0]
    return data, sform


def reslice_template_mri(template_data, inv_atlas_combined, view_display_bounds,
                         grid_size, slice_cfg, cursor_world, interp_order=3):
    """
    Reslice the template MRI using the same transform as the atlas.

    Uses cubic interpolation by default (continuous-valued volume).

    Parameters match reslice_atlas; returns (img2d, h_coords, v_coords).
    """
    fix_wax, h_wax, v_wax = slice_cfg
    n_h, n_v = grid_size
    h_lo, h_hi, v_lo, v_hi = view_display_bounds

    fix_val = cursor_world[fix_wax]

    h_coords = np.linspace(h_lo, h_hi, n_h)
    v_coords = np.linspace(v_hi, v_lo, n_v)

    hh, vv = np.meshgrid(h_coords, v_coords)

    world_pts = np.ones((n_v, n_h, 4))
    world_pts[:, :, fix_wax] = fix_val
    world_pts[:, :, h_wax] = hh
    world_pts[:, :, v_wax] = vv

    flat = world_pts.reshape(-1, 4)
    vox_flat = (inv_atlas_combined @ flat.T).T[:, :3]

    from scipy.ndimage import map_coordinates
    coords = [vox_flat[:, ax] for ax in range(3)]
    sampled = map_coordinates(template_data, coords, order=interp_order,
                              mode='constant', cval=0)
    return sampled.reshape(n_v, n_h), h_coords, v_coords