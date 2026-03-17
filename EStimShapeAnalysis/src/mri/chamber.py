"""
Chamber geometry: fit screwholes, compute reference frame, draw overlays.
Adapted from stereotax.py.
"""

import numpy as np
from numpy.linalg import svd, lstsq, norm


def fit_chamber(screws, ref_screw_idx, center_of_rotation_offset, is_fit_circle=True):
    """
    Fit a plane and circle to screwhole positions.
    
    Parameters:
        screws: (N, 3) array in world coordinates [ML, AP, DV] = [X, Y, Z]
        ref_screw_idx: which screw defines 0-degree azimuth
        center_of_rotation_offset: mm from screw plane to center of rotation
        is_fit_circle: if True, fit a circle; else use centroid
    
    Returns:
        center: center of screwhole circle (on the plane)
        origin: center of rotation (offset along normal)
        x, y: orthonormal basis in the chamber plane
        normal: unit normal pointing into the brain
    """
    mean_pt = screws.mean(axis=0)
    centered = screws - mean_pt
    _, _, vh = svd(centered, full_matrices=False)
    normal = vh[-1]

    if np.dot(normal, mean_pt) > 0:
        normal *= -1

    if not is_fit_circle:
        center = mean_pt
    else:
        projected = []
        for p in screws:
            vec = p - mean_pt
            proj = vec - np.dot(vec, normal) * normal
            projected.append(mean_pt + proj)
        projected = np.array(projected)

        temp = projected[0] - mean_pt
        temp = temp - np.dot(temp, normal) * normal
        v1 = temp / norm(temp)
        v2 = np.cross(normal, v1)
        v2 /= norm(v2)

        pts2d = np.array([[np.dot(p - mean_pt, v1), np.dot(p - mean_pt, v2)]
                          for p in projected])

        A = np.column_stack([pts2d[:, 0], pts2d[:, 1], np.ones(len(pts2d))])
        b = pts2d[:, 0]**2 + pts2d[:, 1]**2
        params, _, _, _ = lstsq(A, b, rcond=None)
        h, k = params[0] / 2, params[1] / 2
        center = mean_pt + h * v1 + k * v2

    ref_vec = screws[ref_screw_idx] - center
    ref_vec -= np.dot(ref_vec, normal) * normal
    x = ref_vec / norm(ref_vec)
    y = np.cross(normal, x)
    y /= norm(y)

    origin = center + center_of_rotation_offset * normal
    return center, origin, x, y, normal


def calc_penetration_target(origin, az_deg, el_deg, dist, x, y, normal, cor_offset):
    """
    Compute target point and trajectory from chamber angles.
    
    Returns (target_3d, direction_unit_vec, top_of_chamber_point).
    """
    az = np.radians(az_deg)
    el = np.radians(el_deg)
    direction = (np.cos(el) * normal
                 + np.sin(el) * np.cos(az) * x
                 + np.sin(el) * np.sin(az) * y)
    origin_offset = cor_offset / np.cos(el)
    dist_from_origin = dist - origin_offset
    target = origin + direction * dist_from_origin
    top_pt = origin - origin_offset * direction
    return target, direction, top_pt


def draw_chamber_overlay(ax, vi, slice_cfg, chamber_state, ebz_world, penetrations,
                         show_chamber=True, show_penetrations=True):
    """
    Draw chamber screwholes, ring, axes, and penetration tracks on a matplotlib axes.
    
    chamber_state: dict with keys: screws_ebz, center, origin, x, y, normal,
                   radius, cor_offset, loaded
    """
    if not chamber_state.get('loaded', False):
        return

    fix_wax, h_wax, v_wax = slice_cfg

    if show_chamber:
        ebz = ebz_world
        screws_world = chamber_state['screws_ebz'] + ebz

        # Screwholes
        sh = screws_world[:, h_wax]
        sv = screws_world[:, v_wax]
        ax.plot(sh, sv, 'o', color='gray', markersize=4, alpha=0.8)
        for i, (hh, vv) in enumerate(zip(sh, sv)):
            ax.annotate(str(i), (hh, vv), fontsize=6, color='gray',
                        ha='center', va='bottom', alpha=0.7)

        # Chamber ring
        center = chamber_state['center']
        x_vec = chamber_state['x']
        y_vec = chamber_state['y']
        radius = chamber_state['radius']
        theta = np.linspace(0, 2 * np.pi, 72)
        ring = (center[np.newaxis, :] +
                radius * (np.cos(theta)[:, np.newaxis] * x_vec +
                          np.sin(theta)[:, np.newaxis] * y_vec))
        ax.plot(ring[:, h_wax], ring[:, v_wax], '-', color='gray', lw=1, alpha=0.5)

        # Chamber origin
        origin = chamber_state['origin']
        ax.plot(origin[h_wax], origin[v_wax], '+', color='white',
                markersize=8, markeredgewidth=1.5)

        # Chamber axes
        for vec, c in [(x_vec, 'red'), (y_vec, 'green')]:
            tip = origin + 5 * vec
            ax.annotate('', xy=(tip[h_wax], tip[v_wax]),
                        xytext=(origin[h_wax], origin[v_wax]),
                        arrowprops=dict(arrowstyle='->', color=c, lw=1.5))

    # Penetrations
    if show_penetrations and penetrations:
        origin = chamber_state['origin']
        x_vec = chamber_state['x']
        y_vec = chamber_state['y']
        normal = chamber_state['normal']
        cor_offset = chamber_state['cor_offset']

        for pen in penetrations:
            if not pen.get('visible', True):
                continue
            target, direction, top_pt = calc_penetration_target(
                origin, pen['az_deg'], pen['el_deg'], pen['dist_mm'],
                x_vec, y_vec, normal, cor_offset)

            track_end = top_pt + (pen['dist_mm'] + 5) * direction
            color = pen.get('color', 'cyan')
            ax.plot([top_pt[h_wax], track_end[h_wax]],
                    [top_pt[v_wax], track_end[v_wax]],
                    '-', color=color, lw=1.2, alpha=0.8)

            ax.plot(target[h_wax], target[v_wax], 'o', color=color, markersize=5)

            for d in range(0, int(pen['dist_mm']) + 1, 5):
                pt = top_pt + d * direction
                ax.plot(pt[h_wax], pt[v_wax], '.', color=color, markersize=2, alpha=0.5)

            ax.annotate(pen.get('label', ''), (target[h_wax], target[v_wax]),
                        fontsize=7, color=color, ha='left', va='bottom')
