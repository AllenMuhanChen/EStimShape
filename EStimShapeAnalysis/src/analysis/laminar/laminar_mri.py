"""
MRI along one session's penetration, in the same depth coordinate as
PenetrationMetrics (depth under chamber, mm, from the top-of-chamber point).

Geometry is the MRI viewer's: chamber frame + corrections from
recording_site_area_distances.load_viewer_geometry (viewer sidecars, or an opt_*.json),
the MRI volume + its subject correction from alignment_optimize.load_mri_pipeline, and
the NMT segmentation (mri_viewer_config 'follower_nifti_path'), mapped to
0 = CSF / outside, 1 = gray matter, 2 = white matter (alignment_optimize.seg_values_to_classes),
and the warped D99 atlas (atlas_nifti_path / atlas_label_path) on the subject correction,
as in recording_site_area_distances (atlas voxel -> world = subject correction @ atlas sform).

Penetration = the session's final recording site (fetch_final_site: a red Penetrations
row whose label contains 'rec' or 'loc', as in recording_site_area_distances.py), with the
global + per-session az / el / depth offsets added.
"""

import re
from typing import Optional, Sequence

import numpy as np
from scipy.ndimage import gaussian_filter, map_coordinates

SEG_CSF, SEG_GM, SEG_WM = 0, 1, 2


class TrajectoryMRI:
    def __init__(self, mri_data, mri_inv_affine, seg_data, seg_inv_affine,
                 top_pt, direction, ref_axis, ddepth_mm: float = 0.0, seg_mapper=None,
                 atlas_data=None, atlas_inv_affine=None, label_names: Optional[dict] = None):
        self.mri_data = mri_data
        self.mri_inv = mri_inv_affine
        self.seg_data = seg_data
        self.seg_inv = seg_inv_affine
        self.top_pt = np.asarray(top_pt, float)
        self.u = np.asarray(direction, float) / np.linalg.norm(direction)
        e1 = np.asarray(ref_axis, float) - np.dot(ref_axis, self.u) * self.u
        self.e1 = e1 / np.linalg.norm(e1)
        self.e2 = np.cross(self.u, self.e1)
        self.ddepth = float(ddepth_mm)
        self.seg_mapper = seg_mapper or (lambda v: v)
        self.atlas_data = atlas_data
        self.atlas_inv = atlas_inv_affine
        self.label_names = label_names or {}

    # ---------------------------------------------------------------- sampling
    def points(self, depths_mm, lateral_mm=0.0, phi_deg=0.0, out_of_plane_mm=0.0):
        d = np.asarray(depths_mm, float) + self.ddepth
        phi = np.radians(phi_deg)
        v = np.cos(phi) * self.e1 + np.sin(phi) * self.e2
        w = np.cross(self.u, v)
        lat = np.asarray(lateral_mm, float)
        oop = np.asarray(out_of_plane_mm, float)
        return (self.top_pt + d[..., None] * self.u + lat[..., None] * v + oop[..., None] * w)

    def _sample(self, data, inv, pts, order):
        flat = pts.reshape(-1, 3)
        vox = (inv @ np.hstack([flat, np.ones((len(flat), 1))]).T)[:3]
        vals = map_coordinates(data, vox, order=order, mode='constant', cval=0.0)
        return vals.reshape(pts.shape[:-1])

    def mri_at(self, pts):
        return self._sample(self.mri_data, self.mri_inv, pts, order=1)

    def seg_at(self, pts):
        if self.seg_data is None:
            return np.full(pts.shape[:-1], -1)
        return np.asarray(self.seg_mapper(self._sample(self.seg_data, self.seg_inv, pts, order=0)), int)

    def atlas_at(self, pts):
        """Atlas label index at each point (0 = unlabelled / outside; -1 = no atlas)."""
        if self.atlas_data is None:
            return np.full(pts.shape[:-1], -1)
        return np.asarray(self._sample(self.atlas_data, self.atlas_inv, pts, order=0), int)

    def seg_along(self, depths_mm):
        return self.seg_at(self.points(depths_mm))

    def slice(self, depth_range_mm, half_width_mm=6.0, phi_deg=0.0, res_mm=0.1):
        """MRI + segmentation on the plane holding the trajectory, rotated phi_deg
        about it. Rows = depth along the trajectory, cols = lateral offset (mm)."""
        depths = np.arange(depth_range_mm[0], depth_range_mm[1] + res_mm / 2, res_mm)
        lats = np.arange(-half_width_mm, half_width_mm + res_mm / 2, res_mm)
        D, L = np.meshgrid(depths, lats, indexing='ij')
        pts = self.points(D, L, phi_deg)
        return dict(mri=self.mri_at(pts), seg=self.seg_at(pts), atlas=self.atlas_at(pts),
                    extent=(lats[0], lats[-1], depths[-1], depths[0]))

    # ---------------------------------------------------------- cortical angle
    def cortical_angle(self, depth_mm, half_size_mm=3.0, res_mm=0.25, sigma_mm=1.0) -> Optional[dict]:
        """Angle between the probe and the local cortical normal at depth_mm.

        The normal is the gradient of smooth(WM) - smooth(CSF/outside) from the
        segmentation, i.e. it points from pia toward white matter. Returns
        angle_deg (0 = probe perpendicular to the layers) and normal_order
        (True if going deeper on the probe moves toward white matter).
        """
        if self.seg_data is None:
            return None
        ax = np.arange(-half_size_mm, half_size_mm + res_mm / 2, res_mm)
        A, B, C = np.meshgrid(ax, ax, ax, indexing='ij')   # along u, e1, e2
        pts = (self.top_pt + (depth_mm + self.ddepth + A)[..., None] * self.u
               + B[..., None] * self.e1 + C[..., None] * self.e2)
        seg = self.seg_at(pts)
        near = (A ** 2 + B ** 2 + C ** 2) <= (1.5 * sigma_mm) ** 2
        if not np.any(seg[near] == SEG_GM):      # no cortex near this point: no meaningful normal
            return None
        f = gaussian_filter((seg == SEG_WM).astype(float), sigma_mm / res_mm) - \
            gaussian_filter((seg == SEG_CSF).astype(float), sigma_mm / res_mm)
        c = len(ax) // 2
        g = np.array([np.gradient(f, axis=k)[c, c, c] for k in range(3)])
        n = np.linalg.norm(g)
        if n < 1e-6:
            return None
        return dict(angle_deg=float(np.degrees(np.arccos(min(1.0, abs(g[0]) / n)))),
                    normal_order=bool(g[0] > 0))


def nearest_runs(depths_mm: np.ndarray, labels: np.ndarray, target, top_mm: float, bottom_mm: float) -> dict:
    """Nearest depth with label == target above top_mm and below bottom_mm (None if absent)."""
    depths_mm = np.asarray(depths_mm)
    hit = np.isin(labels, np.atleast_1d(target))
    above = depths_mm[hit & (depths_mm < top_mm)]
    below = depths_mm[hit & (depths_mm > bottom_mm)]
    inside = depths_mm[hit & (depths_mm >= top_mm) & (depths_mm <= bottom_mm)]
    return dict(above=float(above.max()) if len(above) else None,
                below=float(below.min()) if len(below) else None,
                on_probe=len(inside) > 0)


def fetch_final_site(conn, session_id: str, table: str = 'Penetrations', color: str = 'red',
                     label_keywords: Sequence[str] = ('rec', 'loc'),
                     tip_override_mm: Optional[float] = None) -> Optional[dict]:
    """The session's final recording site, the way recording_site_area_distances.py picks it:
    a Penetrations row with color 'red' and 'rec' or 'loc' in its label (case-insensitive).

    Adds tip_mm, the probe tip distance, recovered from the notes the MRI viewer writes when
    it records an actual point ('ch<N> tip=<X>mm corrected=...', 'tip=<X>mm bottom_ch=...',
    'tip=<X>mm (no channel correction)'). Raises if the session has several such rows, or if
    the tip can't be recovered (pass it as tip_override_mm, FINAL_TIP_MM in laminar_profiles.py).
    """
    from src.analysis.penetrations.recording_site_area_distances import (
        fetch_red_penetrations, filter_by_label_substring)
    from src.analysis.laminar.laminar_core import tip_from_corrected

    rows = [p for p in fetch_red_penetrations(conn, table, color) if p['session_id'] == session_id]
    rows = filter_by_label_substring(rows, list(label_keywords))
    if not rows:
        return None
    if len(rows) > 1:
        raise RuntimeError(f"{session_id}: {len(rows)} final-site rows, expected one: "
                           + ', '.join(f"id {p['id']} {p['label']!r}" for p in rows))
    pen = dict(rows[0])
    notes = pen.get('notes') or ''
    m = re.search(r'tip=([-\d.]+)\s*mm', notes)
    if tip_override_mm is not None:
        pen['tip_mm'] = float(tip_override_mm)
    elif m:
        pen['tip_mm'] = float(m.group(1))
    elif (c := re.search(r'\bch(\d+)\b', notes)):
        pen['tip_mm'] = tip_from_corrected(float(pen['dist_mm']), int(c.group(1)))
    else:
        raise RuntimeError(f"{session_id}: final-site row id {pen['id']} ({pen['label']!r}) has no tip "
                           f"distance or channel in its notes ({notes!r}); its dist_mm "
                           f"{pen['dist_mm']} could be any channel. Set FINAL_TIP_MM for this session.")
    return pen


def load_trajectory_mri(conn, session_id: str, config_path: str, corrections_file: Optional[str] = None,
                        geometry_cache: Optional[dict] = None, pen: Optional[dict] = None) -> Optional[TrajectoryMRI]:
    """Build a TrajectoryMRI for one session from the lab's MRI viewer setup.
    pen: the Penetrations row giving az / el (default: the session's final site)."""
    from src.analysis.penetrations.alignment_optimize import (
        load_mri_pipeline, load_segmentation_volume, seg_values_to_classes)
    from src.analysis.penetrations.recording_site_area_distances import load_viewer_geometry
    from src.mri.chamber import calc_penetration_target

    cache = geometry_cache if geometry_cache is not None else {}
    if 'mri' not in cache:
        cache['mri'] = load_mri_pipeline(config_path)
        cache['geom'] = load_viewer_geometry(config_path, corrections_file)
        seg_path = cache['geom']['cfg'].get('follower_nifti_path')
        cache['seg'] = load_segmentation_volume(seg_path) if seg_path else None
    mri, geom, seg = cache['mri'], cache['geom'], cache['seg']

    if pen is None:
        pen = fetch_final_site(conn, session_id)
    if pen is None:
        return None
    offs = geom['pen_offsets']
    sc = offs.get('per_session_corrections', {}).get(session_id, {})
    az = pen['az_deg'] + offs.get('daz_deg', 0.0) + sc.get('daz_deg', 0.0)
    el = pen['el_deg'] + offs.get('del_deg', 0.0) + sc.get('del_deg', 0.0)
    ddepth = offs.get('ddepth_mm', 0.0) + sc.get('ddepth_mm', 0.0)
    ch = geom['chamber']
    _, direction, top_pt = calc_penetration_target(
        ch['origin'], az, el, 10.0, ch['x'], ch['y'], ch['normal'], ch['cor_offset'])
    return TrajectoryMRI(mri['data'], mri['inv_corrected'],
                         seg['data'] if seg else None, seg['inv_corrected'] if seg else None,
                         top_pt, direction, ref_axis=ch['x'], ddepth_mm=ddepth,
                         seg_mapper=seg_values_to_classes,
                         atlas_data=geom['atlas_data'],
                         atlas_inv_affine=np.linalg.inv(geom['subj_corr'] @ geom['atlas_sform']),
                         label_names=geom['label_names'])
