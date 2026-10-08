"""Distance from each session's final recording site to selected atlas areas.

Final recording sites are the rows of the Penetrations table whose color is
RED (one or more per session). Each site is placed in MRI space exactly the
way the mri-viewer draws it:

    1. chamber screws (EBZ-relative, monkey_specific.py) + EBZ  -> raw world
    2. chamber correction 4x4 applied to the screws, chamber refit
       (origin / x / y / normal)
    3. pen offsets (global daz/del/ddepth + per-session corrections) added
       to the row's az / el / dist
    4. calc_penetration_target(...) -> site in corrected MRI world

The warped atlas (animal_warper output, same native space as the subject)
rides on the subject correction, so atlas voxel -> corrected world is
correction @ atlas_sform, the same matrix the viewer inverts to draw contours.

Distance to an area = Euclidean distance (mm) from the site to the nearest
voxel center labelled as that area. If the site's own atlas voxel already
carries that area's label, the distance is 0.

Outputs (never overwritten): OUT_BASE/<RUN_TAG>_<timestamp>/
    config.json                 every parameter used + resolved paths/matrices
    site_area_distances.csv     one row per red site, one column per area
    site_area_distances.png     heatmap: sites x areas, annotated in mm
    rf_map_by_area.png          receptive fields (ReceptiveFieldInfo) drawn as
                                circles at their location/size, colored by the
                                area the site is in (solid) or nearest to (dashed)
"""
import datetime
import importlib.util
import json
import os
from typing import Dict, List, Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from scipy.spatial import cKDTree

from src.mri.atlas import load_atlas, load_atlas_labels
from src.mri.chamber import calc_penetration_target, fit_chamber
from src.mri.correction import load_corrections

MRI_VIEWER_CONFIG_PATH = os.path.join(os.path.dirname(__file__), '../../mri/mri_viewer_config.json')


# ═══════════════════════════════════════════════════════════════════════════
#  Viewer-equivalent geometry
# ═══════════════════════════════════════════════════════════════════════════

def load_viewer_geometry(config_path: str, corrections_file: Optional[str] = None) -> dict:
    """Rebuild the viewer's chamber frame, pen offsets, subject correction and atlas.

    corrections_file : optional opt_*.json (the file you load with "Load PCA
        result" in the viewer). If None, uses what the viewer currently has
        applied: <monkey_specific>_chamber_corrections.json (current version)
        and <monkey_specific>_pen_offsets.json.
    """
    with open(config_path) as f:
        cfg = json.load(f)

    # Subject (MRI) correction: the viewer reads <volume>_corrections.json.
    subj_corr_path = os.path.splitext(cfg['default_path'])[0] + '_corrections.json'
    if not os.path.exists(subj_corr_path):
        print(f"WARNING: no subject correction at {subj_corr_path}; using identity (as the viewer would)")
    subj_corr, _ = load_corrections(subj_corr_path)

    # Chamber
    monkey_path = cfg['monkey_specific_path']
    spec = importlib.util.spec_from_file_location('monkey_specific', monkey_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    screws_ebz = np.array(mod.get_screw_hole_coords(), dtype=float)
    ref_idx = mod.get_reference_screw_idx()
    cor_offset = mod.get_center_of_rotation_offset()
    is_fit_circle = mod.get_is_fit_circle() if hasattr(mod, 'get_is_fit_circle') else False
    ebz_world = np.array(cfg['ebz_world'], dtype=float)

    if corrections_file:
        with open(corrections_file) as f:
            opt = json.load(f)
        ch_corr = np.array(opt['chamber_correction_4x4'], dtype=float)
        pen_offsets = {
            'daz_deg': float(opt.get('daz_deg', 0.0)),
            'del_deg': float(opt.get('del_deg', 0.0)),
            'ddepth_mm': float(opt.get('ddepth_mm', 0.0)),
            'per_session_corrections': opt.get('per_session_corrections', {}) or {},
        }
        ch_corr_source = corrections_file
        offsets_source = corrections_file
    else:
        ch_corr_source = os.path.splitext(monkey_path)[0] + '_chamber_corrections.json'
        ch_corr, _ = load_corrections(ch_corr_source)
        offsets_source = os.path.splitext(monkey_path)[0] + '_pen_offsets.json'
        pen_offsets = {'daz_deg': 0.0, 'del_deg': 0.0, 'ddepth_mm': 0.0,
                       'per_session_corrections': {}}
        if os.path.exists(offsets_source):
            with open(offsets_source) as f:
                data = json.load(f)
            for k in ('daz_deg', 'del_deg', 'ddepth_mm'):
                pen_offsets[k] = float(data.get(k, 0.0))
            pen_offsets['per_session_corrections'] = data.get('per_session_corrections', {}) or {}
        else:
            offsets_source = None

    # Same as ChamberMixin._refit_chamber
    screws_world = screws_ebz + ebz_world
    if not np.allclose(ch_corr, np.eye(4)):
        screws_world = (ch_corr[:3, :3] @ screws_world.T).T + ch_corr[:3, 3]
    center, origin, x, y, normal = fit_chamber(screws_world, ref_idx, cor_offset, is_fit_circle)

    atlas_data, atlas_sform = load_atlas(cfg['atlas_nifti_path'])
    label_names = load_atlas_labels(cfg['atlas_label_path'])

    return {
        'cfg': cfg,
        'chamber': dict(origin=origin, x=x, y=y, normal=normal, cor_offset=cor_offset),
        'pen_offsets': pen_offsets,
        'subj_corr': subj_corr,
        'atlas_data': atlas_data,
        'atlas_sform': atlas_sform,
        'label_names': label_names,
        'sources': dict(subject_correction=subj_corr_path,
                        chamber_correction=ch_corr_source,
                        pen_offsets=offsets_source,
                        monkey_specific=monkey_path,
                        atlas_nifti=cfg['atlas_nifti_path'],
                        atlas_labels=cfg['atlas_label_path']),
        'chamber_correction': ch_corr,
    }


def offset_pen(pen: dict, pen_offsets: dict, per_session: bool) -> dict:
    """Same as ChamberMixin._offset_pen."""
    sc = pen_offsets.get('per_session_corrections', {}).get(pen['session_id'], {}) if per_session else {}
    return dict(pen,
                az_deg=pen['az_deg'] + pen_offsets.get('daz_deg', 0.) + sc.get('daz_deg', 0.),
                el_deg=pen['el_deg'] + pen_offsets.get('del_deg', 0.) + sc.get('del_deg', 0.),
                dist_mm=pen['dist_mm'] + pen_offsets.get('ddepth_mm', 0.) + sc.get('ddepth_mm', 0.))


def site_world(pen: dict, chamber: dict) -> np.ndarray:
    target, _, _ = calc_penetration_target(
        chamber['origin'], pen['az_deg'], pen['el_deg'], pen['dist_mm'],
        chamber['x'], chamber['y'], chamber['normal'], chamber['cor_offset'])
    return target


# ═══════════════════════════════════════════════════════════════════════════
#  Atlas areas
# ═══════════════════════════════════════════════════════════════════════════

def resolve_area_indices(label_names: Dict[int, str], area_names: Dict[str, List[str]]) -> Dict[str, List[int]]:
    """Map each area to its atlas label indices by exact (case-insensitive) name
    match against any comma-separated token of the label name, like the
    viewer's region highlighter. Fails loudly if an area matches nothing."""
    out = {}
    for area, aliases in area_names.items():
        wanted = {a.strip().lower() for a in aliases}
        idxs = [idx for idx, name in label_names.items()
                if wanted & {t.strip().lower() for t in [name] + name.split(',')}]
        if not idxs:
            # Loose stems (e.g. 'v4d' -> 'v4') so the error shows the neighbours
            stems = wanted | {w.rstrip('dvtlrsmpi') or w for w in wanted}
            near = [f"{i}: {n}" for i, n in label_names.items()
                    if any(st in n.lower() for st in stems)]
            raise ValueError(f"Area '{area}' (aliases {aliases}) matched no atlas label. "
                             f"Partial matches: {near[:20] or 'none'}")
        out[area] = sorted(idxs)
        print(f"  {area:>5} -> " + ", ".join(f"{i}: {label_names[i]}" for i in out[area]))
    return out


def area_distances(sites: np.ndarray, atlas_data: np.ndarray, atlas_to_world: np.ndarray,
                   area_indices: Dict[str, List[int]]) -> pd.DataFrame:
    """Distance (mm) from each site to the nearest voxel of each area; 0 if inside."""
    world_to_vox = np.linalg.inv(atlas_to_world)
    sites_h = np.c_[sites, np.ones(len(sites))]
    vox = np.round((world_to_vox @ sites_h.T).T[:, :3]).astype(int)
    in_bounds = np.all((vox >= 0) & (vox < np.array(atlas_data.shape[:3])), axis=1)
    site_labels = np.zeros(len(sites), dtype=int)
    site_labels[in_bounds] = atlas_data[vox[in_bounds, 0], vox[in_bounds, 1], vox[in_bounds, 2]]

    cols = {}
    for area, idxs in area_indices.items():
        ijk = np.argwhere(np.isin(atlas_data, idxs))
        if len(ijk) == 0:
            raise ValueError(f"Area '{area}' has labels {idxs} but no voxels in the atlas volume")
        area_world = (atlas_to_world @ np.c_[ijk, np.ones(len(ijk))].T).T[:, :3]
        d, _ = cKDTree(area_world).query(sites)
        d[np.isin(site_labels, idxs)] = 0.0
        cols[area] = d
    df = pd.DataFrame(cols)
    df.insert(0, 'site_label_index', site_labels)
    return df


# ═══════════════════════════════════════════════════════════════════════════
#  Penetrations table
# ═══════════════════════════════════════════════════════════════════════════

def fetch_red_penetrations(conn, table: str, color: str = 'red') -> List[dict]:
    conn.execute(
        f"SELECT id, session_id, label, az_deg, el_deg, dist_mm, pen_type, color, notes "
        f"FROM {table} WHERE LOWER(color) = %s ORDER BY session_id, id", (color.lower(),))
    keys = ['id', 'session_id', 'label', 'az_deg', 'el_deg', 'dist_mm', 'pen_type', 'color', 'notes']
    return [dict(zip(keys, row)) for row in conn.fetch_all()]


# ═══════════════════════════════════════════════════════════════════════════
#  Main computation + plot
# ═══════════════════════════════════════════════════════════════════════════

def compute_site_distances(pens: List[dict], geom: dict, area_names: Dict[str, List[str]],
                           per_session_corrections: bool = True) -> pd.DataFrame:
    if not pens:
        raise ValueError("No red penetrations found — nothing to compute.")
    chamber = geom['chamber']
    rows, sites = [], []
    for p in pens:
        po = offset_pen(p, geom['pen_offsets'], per_session_corrections)
        w = site_world(po, chamber)
        sites.append(w)
        rows.append(dict(pen_id=p['id'], session_id=p['session_id'], label=p['label'],
                         pen_type=p['pen_type'],
                         az_deg=p['az_deg'], el_deg=p['el_deg'], dist_mm=p['dist_mm'],
                         az_deg_corrected=po['az_deg'], el_deg_corrected=po['el_deg'],
                         dist_mm_corrected=po['dist_mm'],
                         ML=w[0], AP=w[1], DV=w[2]))
    sites = np.array(sites)
    area_idx = resolve_area_indices(geom['label_names'], area_names)
    atlas_to_world = geom['subj_corr'] @ geom['atlas_sform']
    dists = area_distances(sites, geom['atlas_data'], atlas_to_world, area_idx)

    df = pd.DataFrame(rows)
    ebz = np.array(geom['cfg'].get('ebz_world', [0, 0, 0]), dtype=float)
    df['ML_ebz'], df['AP_ebz'], df['DV_ebz'] = (sites - ebz).T
    df['site_region'] = [geom['label_names'].get(int(i), 'outside atlas / unlabelled') if i else
                         'outside atlas / unlabelled' for i in dists['site_label_index']]
    df = pd.concat([df, dists.drop(columns='site_label_index')], axis=1)
    df.attrs['area_indices'] = area_idx
    return df


def plot_distance_heatmap(df: pd.DataFrame, areas: List[str], out_path: str, title: str):
    # One row per site; label with session (+ pen label if a session has several)
    multi = df['session_id'].duplicated(keep=False)
    row_labels = [f"{s}  ({l})" if m else str(s)
                  for s, l, m in zip(df['session_id'], df['label'], multi)]
    D = df[areas].to_numpy(dtype=float)

    vmax = max(1.0, float(np.nanmax(D)))
    cmap = LinearSegmentedColormap.from_list('dist', ['#1b7f3b', '#f7f7f7', '#b2182b'])
    n_rows = len(df)
    fig, ax = plt.subplots(figsize=(2.0 + 1.6 * len(areas), 1.5 + 0.45 * n_rows))
    im = ax.imshow(D, cmap=cmap, vmin=0, vmax=vmax, aspect='auto')
    for i in range(D.shape[0]):
        for j in range(D.shape[1]):
            v = D[i, j]
            txt = 'in' if v == 0 else f"{v:.1f}"
            ax.text(j, i, txt, ha='center', va='center', fontsize=12,
                    fontweight='bold' if v == 0 else 'normal',
                    color='white' if (v == 0 or v > 0.75 * vmax) else 'black')
    ax.set_xticks(range(len(areas)))
    ax.set_xticklabels(areas, fontsize=14)
    ax.xaxis.tick_top()
    ax.set_yticks(range(n_rows))
    ax.set_yticklabels(row_labels, fontsize=12)
    ax.set_title(title, fontsize=15, pad=30)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xticks(np.arange(-.5, len(areas)), minor=True)
    ax.set_yticks(np.arange(-.5, n_rows), minor=True)
    ax.grid(which='minor', color='white', linewidth=2)
    ax.tick_params(which='minor', length=0)
    cb = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02)
    cb.set_label('Distance to area (mm)', fontsize=13)
    cb.ax.tick_params(labelsize=11)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    return fig


# ═══════════════════════════════════════════════════════════════════════════
#  Receptive fields colored by area
# ═══════════════════════════════════════════════════════════════════════════

def assign_area(df: pd.DataFrame, areas: List[str]) -> pd.DataFrame:
    """Add 'area' (the area the site is in, else the nearest one) and
    'inside' (True if the site is in that area)."""
    D = df[areas].to_numpy(dtype=float)
    j = np.argmin(D, axis=1)
    out = df.copy()
    out['area'] = [areas[k] for k in j]
    out['inside'] = D[np.arange(len(D)), j] == 0
    return out


def fetch_rfs(conn, channel: str) -> pd.DataFrame:
    conn.execute("SELECT session_id, x, y, radius FROM ReceptiveFieldInfo WHERE channel = %s",
                 (channel,))
    rows = [r for r in conn.fetch_all() if None not in r]
    return pd.DataFrame(rows, columns=['session_id', 'rf_x', 'rf_y', 'rf_radius'])


def one_site_per_session(df: pd.DataFrame) -> pd.DataFrame:
    """RFs are per session; if a session has several red sites, keep the most
    recently added one (highest pen_id)."""
    dup = df['session_id'][df['session_id'].duplicated()].unique()
    if len(dup):
        print(f"  Sessions with >1 red site (using the latest pen_id for RF coloring): {list(dup)}")
    return df.sort_values('pen_id').groupby('session_id', as_index=False).last()


AREA_COLORS = {   # roughly ventral -> dorsal stream, distinct hues
    'V3v': '#9467bd', 'V4v': '#1f77b4', 'TEO': '#17becf',
    'V3d': '#e377c2', 'V4d': '#2ca02c', 'V4t': '#ff7f0e', 'MT': '#d62728',
}


def plot_rf_map(df: pd.DataFrame, areas: List[str], out_path: str, title: str,
                label_sessions: bool = True):
    from matplotlib.lines import Line2D
    from matplotlib.patches import Circle
    fallback = plt.get_cmap('tab10')
    colors = {a: AREA_COLORS.get(a, fallback(i % 10)) for i, a in enumerate(areas)}

    fig, ax = plt.subplots(figsize=(10, 9))
    # Big circles first so small ones stay visible on top
    for _, r in df.sort_values('rf_radius', ascending=False).iterrows():
        c = colors[r['area']]
        ax.add_patch(Circle((r['rf_x'], r['rf_y']), r['rf_radius'], facecolor=c, alpha=0.18,
                            edgecolor='none'))
        ax.add_patch(Circle((r['rf_x'], r['rf_y']), r['rf_radius'], facecolor='none',
                            edgecolor=c, lw=2.2, linestyle='-' if r['inside'] else '--'))
        ax.plot(r['rf_x'], r['rf_y'], 'o', color=c, markersize=4)
        if label_sessions:
            ax.annotate(str(r['session_id']), (r['rf_x'], r['rf_y']), xytext=(4, 4),
                        textcoords='offset points', fontsize=9, color='#333333')

    ext = np.r_[np.abs(df['rf_x']) + df['rf_radius'], np.abs(df['rf_y']) + df['rf_radius']]
    lim = float(np.ceil(np.max(ext) + 1)) if len(ext) else 10.0
    ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim)
    ax.set_aspect('equal')
    ax.axhline(0, color='#999999', lw=0.8, zorder=0)
    ax.axvline(0, color='#999999', lw=0.8, zorder=0)
    ax.plot(0, 0, '+', color='black', markersize=14, markeredgewidth=2)
    ax.set_xlabel('Horizontal position (deg)', fontsize=14)
    ax.set_ylabel('Vertical position (deg)', fontsize=14)
    ax.tick_params(labelsize=12)
    ax.set_title(title, fontsize=15)

    counts = df['area'].value_counts()
    handles = [Line2D([], [], color=colors[a], lw=6, alpha=0.6,
                      label=f"{a} (n={counts.get(a, 0)})") for a in areas if counts.get(a, 0)]
    handles += [Line2D([], [], color='#444444', lw=2, ls='-', label='inside area'),
                Line2D([], [], color='#444444', lw=2, ls='--', label='nearest area')]
    ax.legend(handles=handles, fontsize=12, loc='center left', bbox_to_anchor=(1.02, 0.5),
              frameon=False)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches='tight')
    return fig


def main():
    # ---- PARAMETERS ------------------------------------------------------
    OUT_BASE = "/home/connorlab/Documents/penetration_optimization_plots/recording_site_area_distances"
    RUN_TAG = None                       # e.g. "45X"; None -> timestamp only
    MRI_CONFIG = MRI_VIEWER_CONFIG_PATH  # same config the mri-viewer loads
    # Correction file: an opt_*.json (what "Load PCA result" takes in the viewer).
    # None -> use whatever the viewer currently has applied (chamber correction
    # sidecar + pen offsets beside monkey_specific.py).
    CORRECTIONS_FILE = None
    PER_SESSION_CORRECTIONS = True       # viewer's "Sess.Corr: ON" (its default)
    PEN_TABLE = None                     # None -> config's penetration_table
    FINAL_SITE_COLOR = "red"
    SHOW_PLOTS = True                    # open the figure in a window after saving
    # Area -> atlas label name(s) to match (case-insensitive, whole name or
    # any comma-separated token of the D99 label).
    AREAS = {
        'V4v': ['V4v'],
        'V4d': ['V4d', 'V4'],   # D99 labels dorsal V4 as plain 'V4'
        'TEO': ['TEO'],
        'V4t': ['V4t'],
        'MT':  ['MT'],
        'V3d': ['V3d', 'V3'],
        'V3v': ['V3v'],
    }
    # Receptive-field map (ReceptiveFieldInfo in the data repository)
    PLOT_RF_MAP = True
    RF_CHANNEL = 'SUPRA-000'             # which channel's RF to draw per session
    LABEL_SESSIONS = True                # session id next to each RF center
    DB = dict(database="allen_data_repository", user="xper_rw",
              password="up2nite", host="172.30.6.61")
    # ----------------------------------------------------------------------

    from clat.util.connection import Connection

    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    out_dir = os.path.join(OUT_BASE, f"{RUN_TAG}_{ts}" if RUN_TAG else ts)
    os.makedirs(out_dir, exist_ok=True)

    geom = load_viewer_geometry(MRI_CONFIG, CORRECTIONS_FILE)
    table = PEN_TABLE or geom['cfg'].get('penetration_table', 'Penetrations')

    conn = Connection(**DB)
    pens = fetch_red_penetrations(conn, table, FINAL_SITE_COLOR)
    df = compute_site_distances(pens, geom, AREAS, PER_SESSION_CORRECTIONS)

    with open(os.path.join(out_dir, 'config.json'), 'w') as f:
        json.dump(dict(
            timestamp=ts, run_tag=RUN_TAG, mri_config=os.path.abspath(MRI_CONFIG),
            corrections_file=CORRECTIONS_FILE, per_session_corrections=PER_SESSION_CORRECTIONS,
            pen_table=table, final_site_color=FINAL_SITE_COLOR, areas=AREAS, show_plots=SHOW_PLOTS,
            plot_rf_map=PLOT_RF_MAP, rf_channel=RF_CHANNEL, label_sessions=LABEL_SESSIONS,
            area_label_indices=df.attrs['area_indices'],
            sources=geom['sources'],
            subject_correction=geom['subj_corr'].tolist(),
            chamber_correction=geom['chamber_correction'].tolist(),
            pen_offsets=geom['pen_offsets'],
            n_sites=len(df), n_sessions=int(df['session_id'].nunique()),
        ), f, indent=2)
    df.to_csv(os.path.join(out_dir, 'site_area_distances.csv'), index=False)
    plot_distance_heatmap(df, list(AREAS), os.path.join(out_dir, 'site_area_distances.png'),
                          f"Final recording site distance to area ({table}, {len(df)} sites)")

    if PLOT_RF_MAP:
        sites = assign_area(one_site_per_session(df), list(AREAS))
        rfs = fetch_rfs(conn, RF_CHANNEL)
        rf_df = sites.merge(rfs, on='session_id', how='inner')
        missing = sorted(set(sites['session_id']) - set(rf_df['session_id']))
        if missing:
            print(f"  No {RF_CHANNEL} RF for sessions: {missing}")
        if rf_df.empty:
            raise ValueError(f"No ReceptiveFieldInfo rows for channel {RF_CHANNEL} match the red sites")
        rf_df.to_csv(os.path.join(out_dir, 'rf_map_by_area.csv'), index=False)
        plot_rf_map(rf_df, list(AREAS), os.path.join(out_dir, 'rf_map_by_area.png'),
                    f"Receptive fields by recording area ({RF_CHANNEL}, {len(rf_df)} sessions)",
                    LABEL_SESSIONS)

    print(f"Wrote {len(df)} sites from {df['session_id'].nunique()} sessions -> {out_dir}")
    if SHOW_PLOTS:
        plt.show()


if __name__ == "__main__":
    main()
