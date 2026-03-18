"""
Volume loading, reslicing, and affine coordinate math.
"""

import numpy as np
from nibabel.parrec import load as load_parrec
import nibabel as nib
from scipy.ndimage import map_coordinates


def load_volume(par_path):
    """Load a PAR/REC file. Returns (data_3or4d, native_affine, voxel_sizes)."""
    img = load_parrec(par_path, strict_sort=True)
    data = img.get_fdata()
    affine = img.affine.copy()
    voxel_sizes = nib.affines.voxel_sizes(affine)
    return data, affine, voxel_sizes, img


def compute_world_bbox(corrected_affine, dim_sizes):
    """Compute world-space bounding box from voxel corners."""
    ds = dim_sizes
    corners = np.array([
        [0, 0, 0, 1], [ds[0]-1, 0, 0, 1], [0, ds[1]-1, 0, 1],
        [0, 0, ds[2]-1, 1], [ds[0]-1, ds[1]-1, 0, 1],
        [ds[0]-1, 0, ds[2]-1, 1], [0, ds[1]-1, ds[2]-1, 1],
        [ds[0]-1, ds[1]-1, ds[2]-1, 1],
    ], dtype=float)
    cw = (corrected_affine @ corners.T).T[:, :3]
    return cw.min(axis=0), cw.max(axis=0)


def reslice_view(data, inv_corrected, view_display_bounds, grid_size,
                 slice_cfg, cursor_world, current_dynamic=0, has_dynamics=False,
                 interp_order=3):
    """
    Sample a 2D slice from the volume for a given view.

    interp_order: passed to scipy.ndimage.map_coordinates.
        0 = nearest-neighbour, 1 = linear, 3 = cubic (smoothest).

    Returns (img2d, h_coords, v_coords) where h_coords and v_coords are in mm.
    """
    fix_wax, h_wax, v_wax = slice_cfg
    n_h, n_v = grid_size
    h_lo, h_hi, v_lo, v_hi = view_display_bounds

    fix_val = cursor_world[fix_wax]

    h_coords = np.linspace(h_lo, h_hi, n_h)
    v_coords = np.linspace(v_hi, v_lo, n_v)  # top = max

    hh, vv = np.meshgrid(h_coords, v_coords)

    world_pts = np.ones((n_v, n_h, 4))
    world_pts[:, :, fix_wax] = fix_val
    world_pts[:, :, h_wax] = hh
    world_pts[:, :, v_wax] = vv

    flat = world_pts.reshape(-1, 4)
    vox_flat = (inv_corrected @ flat.T).T[:, :3]

    vol = data
    if has_dynamics:
        vol = data[:, :, :, current_dynamic]

    coords = [vox_flat[:, ax] for ax in range(3)]
    sampled = map_coordinates(vol, coords, order=interp_order, mode='constant', cval=0)
    return sampled.reshape(n_v, n_h), h_coords, v_coords