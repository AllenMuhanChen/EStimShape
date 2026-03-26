"""
Tri-planar PAR/REC MRI Viewer — main UI class.

Delegates to:
    volume.py      — PAR/REC loading, reslicing
    correction.py  — correction matrix persistence, transforms
    chamber.py     — chamber geometry, overlay drawing
    penetrations.py — DB-backed penetration management
    atlas.py       — NIfTI atlas loading, reslicing, contour overlay
"""

import numpy as np
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import os, json, pprint
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from src.mri.volume import load_volume, compute_world_bbox, reslice_view
from src.mri.correction import (
    rot_x, rot_y, rot_z, xlate, scale,
    load_corrections, save_corrections, push_correction,
    load_crop_bounds, save_crop_bounds,
)
from src.mri.chamber import fit_chamber, draw_chamber_overlay, calc_penetration_target, calc_target_angles
from src.mri.penetrations import PenetrationStore, PenetrationListWindow, COLORS
from src.mri.atlas import (
    load_atlas, load_atlas_labels,
    reslice_atlas, draw_atlas_contours,
    atlas_label_at_cursor, atlas_label_detail,
    load_template_mri, reslice_template_mri,
)

# Probe geometry (matches import_penetration.py)
_TIP_TO_BOTTOM_CH_UM = 600   # μm from probe tip to bottommost channel
_CH_SPACING_UM = 65           # μm between adjacent channels
_N_CHANNELS = 32
_CHANNEL_ORDER = [
    7, 8, 25, 22, 0, 15, 24, 23, 6, 9, 26, 21, 5, 10, 31, 16,
    27, 20, 4, 11, 28, 19, 1, 14, 3, 12, 29, 18, 2, 13, 30, 17
]


def _channel_corrected_dist(tip_dist_mm, channel_num):
    """Apply channel offset correction: returns distance to given channel instead of tip."""
    idx = _CHANNEL_ORDER.index(channel_num)
    offset_um = _TIP_TO_BOTTOM_CH_UM + (31 - idx) * _CH_SPACING_UM
    return tip_dist_mm - offset_um / 1000.0


class TriplanarMRIViewer:
    """
    Coordinate convention (RAS+):  +X = Right, +Y = Anterior, +Z = Superior
    Lab labels:  ML = world X,  AP = world Y,  DV = world Z

    Display:
        Sagittal : fix X, show Y(horiz) x Z(vert), S at top
        Coronal  : fix Y, show X(horiz) x Z(vert), S at top
        Axial    : fix Z, show X(horiz) x Y(vert), A at top
    """

    VIEW_NAMES = ["Sagittal", "Coronal", "Axial"]
    SLICE_CFG = [(0, 1, 2), (1, 0, 2), (2, 0, 1)]
    WORLD_LABELS = ["ML (R/L)", "AP (A/P)", "DV (S/I)"]

    def __init__(self, root, default_path=None):
        self.root = root
        self.root.title("PAR/REC Tri-Planar MRI Viewer")
        self.root.geometry("1450x960")
        self.root.resizable(True, True)

        # Volume state
        self.img = None
        self.data = None
        self.native_affine = None
        self.correction = np.eye(4)
        self.corrected_affine = None
        self.inv_corrected = None
        self.voxel_sizes = None
        self.default_path = default_path
        self.output_voxel_size = 0.4

        # Correction persistence
        self.corr_config = None
        self.corr_json_path = None

        # Volume dims
        self.dim_sizes = [0, 0, 0]
        self.has_dynamics = False
        self.dynamics = 1
        self.current_dynamic = 0

        # Bounding boxes
        self.full_world_min = np.zeros(3)
        self.full_world_max = np.zeros(3)
        self.world_min = np.zeros(3)
        self.world_max = np.zeros(3)
        self.world_center = np.zeros(3)
        self.view_display_bounds = [(0, 1, 0, 1)] * 3
        self.grid_sizes = [(2, 2)] * 3

        # Crosshair (corrected world mm)
        self.cursor_world = np.zeros(3)

        # EBZ
        self.ebz_set = False
        self.ebz_world = np.zeros(3)
        self.ebz_pick_armed = False

        # Crop
        self.crop_bounds = {}
        self.crop_mode = False
        self._crop_rect = None
        self._crop_start = None
        self._crop_view = None

        # Zoom: per-view viewport in display (EBZ-relative) coords {vi: (h_lo,h_hi,v_lo,v_hi)}
        # Reslicing always uses full crop extent; zoom only restricts the visible window via ax limits.
        self.zoom_bounds = {}

        # Pan: middle-mouse-drag state
        self._pan_start = None   # (x, y) in display coords at drag start
        self._pan_view = None    # view index being panned
        self._pan_bounds = None  # zoom_bounds snapshot at drag start

        # Interpolation order for reslicing (0=nearest, 1=linear, 3=cubic)
        self.interp_order = 3

        # Chamber state (dict passed to chamber.draw_chamber_overlay)
        self.chamber_state = {
            'loaded': False, 'screws_ebz': None,
            'center': None, 'origin': None, 'x': None, 'y': None, 'normal': None,
            'radius': 7.0, 'cor_offset': 2.54,
        }
        self.chamber_show = True
        self._chamber_params = {
            'ref_screw_idx': 4, 'is_fit_circle': True,
            'center_of_rotation_offset': 2.54, 'chamber_depth': 12.0,
        }

        # Penetrations (DB-backed)
        self.pen_store = PenetrationStore()
        self.pen_show = True

        self._chamber_path = None  # set by _load_chamber_from_path; persisted in config

        # Trajectory planner (temp trajectory before saving)
        self.temp_trajectory = None  # dict: az_deg, el_deg, dist_mm, target, direction, top_pt
        self.temp_points = []        # list of dicts: az_deg, el_deg, dist_mm, label, color, target, direction, top_pt
        self._traj_updating = False  # guard against infinite loops in bidirectional entry sync

        # ---- Atlas state ----
        self.atlas_data = None          # ndarray (I,J,K) int labels
        self.atlas_sform = None         # 4×4 voxel→atlas-stereo
        self.atlas_correction = np.eye(4)  # 4×4 atlas-stereo→corrected-world
        self.atlas_label_names = {}     # {int: str}
        self.atlas_show = False         # overlay visible?
        self.atlas_loaded = False
        self._atlas_nifti_path = None
        self._atlas_label_path = None
        # Atlas correction persistence (reuses correction.py helpers)
        self.atlas_corr_config = None
        self.atlas_corr_json_path = None
        # Contour appearance
        self.atlas_contour_color = 'cyan'
        self.atlas_contour_lw = 0.6
        self.atlas_contour_alpha = 0.7

        # ---- Template MRI state ----
        self.template_data = None       # ndarray (I,J,K) float — template MRI volume
        self.template_sform = None      # should match atlas_sform
        self.template_loaded = False
        self._template_mri_path = None
        self.template_blend = 0.0       # 0=subject only, 0.5=blend, 1.0=template only

        self._setup_ui()

    # ================================================================ UI
    def _setup_ui(self):
        main = ttk.Frame(self.root)
        main.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # File row
        row = ttk.Frame(main); row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text="PAR File:").pack(side=tk.LEFT, padx=3)
        self.file_path_var = tk.StringVar(value=self.default_path or "")
        ttk.Entry(row, textvariable=self.file_path_var, width=55).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=3)
        ttk.Button(row, text="Browse...", command=self._browse).pack(side=tk.LEFT, padx=2)
        ttk.Button(row, text="Load", command=self.load_and_visualize).pack(side=tk.LEFT, padx=2)
        ttk.Button(row, text="Save Defaults", command=self._save_defaults).pack(side=tk.LEFT, padx=2)

        # Status
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(main, textvariable=self.status_var).pack(fill=tk.X, padx=5)

        # Session ID row
        sess_row = ttk.Frame(main); sess_row.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(sess_row, text="Session ID:", font=("TkDefaultFont", 10, "bold")).pack(side=tk.LEFT, padx=3)
        self.session_id_var = tk.StringVar(value="")
        ttk.Entry(sess_row, textvariable=self.session_id_var, width=20,
                  font=("TkDefaultFont", 10)).pack(side=tk.LEFT, padx=3)
        ttk.Label(sess_row, text="(YYMMDD_location, e.g. 260318_0)",
                  foreground="#555555").pack(side=tk.LEFT, padx=6)
        self.btn_load_session = ttk.Button(sess_row, text="Load Session",
                                            command=self._load_session, state="disabled")
        self.btn_load_session.pack(side=tk.LEFT, padx=6)

        # ---- Panel toolbar (one button per section) ----
        self._panel_bar = ttk.Frame(main)
        self._panel_bar.pack(fill=tk.X, padx=5, pady=2)
        self._panel_container = ttk.Frame(main)
        self._panel_container.pack(fill=tk.X)
        self._active_panel = None   # key of currently open panel, or None
        self._panel_frames = {}     # key → LabelFrame
        self._panel_buttons = {}    # key → Button

        panel_defs = [
            ("EBZ",         "ebz",         self._build_ebz_panel),
            ("Correction",  "correction",  self._build_correction_panel),
            ("Crop/Display","crop",        self._build_crop_panel),
            ("Chamber",     "chamber",     self._build_chamber_panel),
            ("Trajectory",  "trajectory",  self._build_trajectory_panel),
            ("Atlas",       "atlas",       self._build_atlas_panel),
        ]
        for label, key, builder in panel_defs:
            btn = ttk.Button(self._panel_bar, text=label,
                             command=lambda k=key: self._toggle_panel(k))
            btn.pack(side=tk.LEFT, padx=2)
            self._panel_buttons[key] = btn
            builder(self._panel_container)
            # Builder stores frame in self._panel_frames[key]; hide it initially
            self._panel_frames[key].pack_forget()

        # Figure
        fig_frame = ttk.Frame(main)
        fig_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=3)
        self.fig = Figure(figsize=(14, 5), dpi=100)
        self.fig.subplots_adjust(left=0.04, right=0.98, top=0.93, bottom=0.07, wspace=0.25)
        self.axes = [self.fig.add_subplot(1, 3, i + 1) for i in range(3)]
        self.canvas = FigureCanvasTkAgg(self.fig, master=fig_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.toolbar = NavigationToolbar2Tk(self.canvas, fig_frame)
        self.toolbar.update()
        self.canvas.mpl_connect("button_press_event", self._on_click)
        self.canvas.mpl_connect("button_release_event", self._on_release)
        self.canvas.mpl_connect("motion_notify_event", self._on_motion)
        self.canvas.mpl_connect("scroll_event", self._on_scroll)

        # Global key bindings
        self.root.bind("<a>", self._on_key_atlas_toggle)
        self.root.bind("<A>", self._on_key_atlas_toggle)
        self.root.bind("<t>", self._on_key_blend_snap)
        self.root.bind("<T>", self._on_key_blend_snap)

        # Sliders
        self._build_sliders(main)

    # ---- Panel builders ----
    def _build_ebz_panel(self, parent):
        ebz = ttk.LabelFrame(parent, text="EBZ (External Brain Zero)")
        ebz.pack(fill=tk.X, padx=5, pady=2)
        self._panel_frames['ebz'] = ebz
        for i, (lbl, vn) in enumerate([("AP mm:", "ebz_ap"), ("DV mm:", "ebz_dv"), ("ML mm:", "ebz_ml")]):
            ttk.Label(ebz, text=lbl).grid(row=0, column=2*i, padx=3, pady=2)
            v = tk.DoubleVar(value=0.0); setattr(self, vn + "_var", v)
            ttk.Entry(ebz, textvariable=v, width=10).grid(row=0, column=2*i+1, padx=3)
        self.btn_set_ebz = ttk.Button(ebz, text="Set EBZ (manual)", command=self._set_ebz_manual, state="disabled")
        self.btn_set_ebz.grid(row=0, column=6, padx=3)
        self.btn_ebz_xhair = ttk.Button(ebz, text="Set EBZ to crosshair", command=self._set_ebz_to_crosshair, state="disabled")
        self.btn_ebz_xhair.grid(row=0, column=7, padx=3)
        self.btn_reset_ebz = ttk.Button(ebz, text="Reset EBZ", command=self._reset_ebz, state="disabled")
        self.btn_reset_ebz.grid(row=0, column=8, padx=3)
        self.btn_ebz_pick = ttk.Button(ebz, text="Pick EBZ (right-click)", command=self._toggle_ebz_pick, state="disabled")
        self.btn_ebz_pick.grid(row=0, column=9, padx=3)
        self.cursor_info_var = tk.StringVar(value="Crosshair: ---")
        ttk.Label(ebz, textvariable=self.cursor_info_var).grid(row=1, column=0, columnspan=10, sticky="w", padx=5)
        self.ebz_pick_label_var = tk.StringVar(value="")
        ttk.Label(ebz, textvariable=self.ebz_pick_label_var, foreground="red").grid(row=2, column=0, columnspan=10, sticky="w", padx=5)

    def _build_correction_panel(self, parent):
        corr = ttk.LabelFrame(parent, text="Correction Matrix")
        corr.pack(fill=tk.X, padx=5, pady=2)
        self._panel_frames['correction'] = corr
        r_row = ttk.Frame(corr); r_row.pack(fill=tk.X, padx=3, pady=2)
        ttk.Label(r_row, text="Rotate (deg):").pack(side=tk.LEFT, padx=3)
        for al, an in [("X(ML/roll)", "x"), ("Y(AP/pitch)", "y"), ("Z(DV/yaw)", "z")]:
            ttk.Label(r_row, text=f"{al}:").pack(side=tk.LEFT, padx=(6, 2))
            v = tk.DoubleVar(value=0.0); setattr(self, f"rot_{an}_var", v)
            ttk.Entry(r_row, textvariable=v, width=7).pack(side=tk.LEFT, padx=2)
        t_row = ttk.Frame(corr); t_row.pack(fill=tk.X, padx=3, pady=2)
        ttk.Label(t_row, text="Translate (mm):").pack(side=tk.LEFT, padx=3)
        for al, an in [("X(ML)", "tx"), ("Y(AP)", "ty"), ("Z(DV)", "tz")]:
            ttk.Label(t_row, text=f"{al}:").pack(side=tk.LEFT, padx=(6, 2))
            v = tk.DoubleVar(value=0.0); setattr(self, f"trans_{an}_var", v)
            ttk.Entry(t_row, textvariable=v, width=7).pack(side=tk.LEFT, padx=2)
        b_row = ttk.Frame(corr); b_row.pack(fill=tk.X, padx=3, pady=2)
        self.btn_apply = ttk.Button(b_row, text="Apply", command=self._apply_correction, state="disabled")
        self.btn_apply.pack(side=tk.LEFT, padx=3)
        self.btn_reset_corr = ttk.Button(b_row, text="Reset to Identity", command=self._reset_correction, state="disabled")
        self.btn_reset_corr.pack(side=tk.LEFT, padx=3)
        self.btn_undo = ttk.Button(b_row, text="Undo", command=self._undo, state="disabled")
        self.btn_undo.pack(side=tk.LEFT, padx=3)
        self.btn_redo = ttk.Button(b_row, text="Redo", command=self._redo, state="disabled")
        self.btn_redo.pack(side=tk.LEFT, padx=3)
        ttk.Button(b_row, text="History", command=self._show_history).pack(side=tk.LEFT, padx=3)
        ttk.Button(b_row, text="Header", command=self._show_header).pack(side=tk.LEFT, padx=3)
        self.corr_info_var = tk.StringVar(value="Correction: identity")
        ttk.Label(corr, textvariable=self.corr_info_var).pack(anchor="w", padx=5, pady=1)
        self.corr_ver_var = tk.StringVar(value="")
        ttk.Label(corr, textvariable=self.corr_ver_var).pack(anchor="w", padx=5, pady=1)
        note_row = ttk.Frame(corr); note_row.pack(fill=tk.X, padx=3, pady=2)
        ttk.Label(note_row, text="Note:").pack(side=tk.LEFT, padx=3)
        self.corr_note_var = tk.StringVar(value="")
        ttk.Entry(note_row, textvariable=self.corr_note_var, width=50).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)

    def _build_crop_panel(self, parent):
        crop = ttk.LabelFrame(parent, text="View Cropping & Display")
        crop.pack(fill=tk.X, padx=5, pady=2)
        self._panel_frames['crop'] = crop

        row1 = ttk.Frame(crop); row1.pack(fill=tk.X, padx=3, pady=2)
        self.btn_crop = ttk.Button(row1, text="Crop (drag rect)", command=self._toggle_crop_mode, state="disabled")
        self.btn_crop.pack(side=tk.LEFT, padx=3)
        self.btn_reset_crop = ttk.Button(row1, text="Reset Crops", command=self._reset_crop, state="disabled")
        self.btn_reset_crop.pack(side=tk.LEFT, padx=3)
        self.btn_reset_zoom = ttk.Button(row1, text="Reset Zoom", command=self._reset_zoom, state="disabled")
        self.btn_reset_zoom.pack(side=tk.LEFT, padx=3)
        ttk.Label(row1, text="  Scroll to zoom, double-click to reset view", foreground="#555555").pack(side=tk.LEFT, padx=6)
        self.crop_status_var = tk.StringVar(value="")
        ttk.Label(row1, textvariable=self.crop_status_var, foreground="blue").pack(side=tk.LEFT, padx=6)

        row2 = ttk.Frame(crop); row2.pack(fill=tk.X, padx=3, pady=(0, 4))
        ttk.Label(row2, text="Interpolation:").pack(side=tk.LEFT, padx=3)
        self.interp_var = tk.StringVar(value="Cubic (order 3)")
        interp_cb = ttk.Combobox(row2, textvariable=self.interp_var, state="readonly", width=18,
                                  values=["Nearest (order 0)", "Linear (order 1)", "Cubic (order 3)"])
        interp_cb.pack(side=tk.LEFT, padx=3)
        interp_cb.bind("<<ComboboxSelected>>", self._on_interp_change)

        ttk.Label(row2, text="  Sample res (mm/px):").pack(side=tk.LEFT, padx=(12, 3))
        self.voxel_size_var = tk.DoubleVar(value=self.output_voxel_size)
        voxel_entry = ttk.Entry(row2, textvariable=self.voxel_size_var, width=6)
        voxel_entry.pack(side=tk.LEFT, padx=3)
        voxel_entry.bind("<Return>", self._on_voxel_size_change)
        ttk.Label(row2, text="(lower = finer, Enter to apply)").pack(side=tk.LEFT, padx=3)

    def _build_chamber_panel(self, parent):
        ch = ttk.LabelFrame(parent, text="Chamber & Penetrations")
        ch.pack(fill=tk.X, padx=5, pady=2)
        self._panel_frames['chamber'] = ch
        r1 = ttk.Frame(ch); r1.pack(fill=tk.X, padx=3, pady=2)
        self.btn_load_chamber = ttk.Button(r1, text="Load monkey_specific.py...", command=self._load_chamber_file)
        self.btn_load_chamber.pack(side=tk.LEFT, padx=3)
        self.btn_toggle_chamber = ttk.Button(r1, text="Hide Chamber", command=self._toggle_chamber, state="disabled")
        self.btn_toggle_chamber.pack(side=tk.LEFT, padx=3)
        self.btn_connect_db = ttk.Button(r1, text="Connect DB", command=self._connect_db)
        self.btn_connect_db.pack(side=tk.LEFT, padx=3)
        self.btn_pen_list = ttk.Button(r1, text="Penetration List", command=self._show_pen_list, state="disabled")
        self.btn_pen_list.pack(side=tk.LEFT, padx=3)
        self.chamber_info_var = tk.StringVar(value="No chamber loaded")
        ttk.Label(ch, textvariable=self.chamber_info_var).pack(anchor="w", padx=5, pady=1)

        pen_row = ttk.Frame(ch); pen_row.pack(fill=tk.X, padx=3, pady=2)
        ttk.Label(pen_row, text="Az(°):").pack(side=tk.LEFT, padx=2)
        self.pen_az_var = tk.DoubleVar(value=0.0)
        ttk.Entry(pen_row, textvariable=self.pen_az_var, width=7).pack(side=tk.LEFT, padx=2)
        ttk.Label(pen_row, text="El(°):").pack(side=tk.LEFT, padx=2)
        self.pen_el_var = tk.DoubleVar(value=0.0)
        ttk.Entry(pen_row, textvariable=self.pen_el_var, width=7).pack(side=tk.LEFT, padx=2)
        ttk.Label(pen_row, text="Dist(mm):").pack(side=tk.LEFT, padx=2)
        self.pen_dist_var = tk.DoubleVar(value=35.0)
        ttk.Entry(pen_row, textvariable=self.pen_dist_var, width=7).pack(side=tk.LEFT, padx=2)
        ttk.Label(pen_row, text="Label:").pack(side=tk.LEFT, padx=2)
        self.pen_label_var = tk.StringVar(value="")
        ttk.Entry(pen_row, textvariable=self.pen_label_var, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Label(pen_row, text="Notes:").pack(side=tk.LEFT, padx=2)
        self.pen_notes_var = tk.StringVar(value="")
        ttk.Entry(pen_row, textvariable=self.pen_notes_var, width=20).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

        br = ttk.Frame(ch); br.pack(fill=tk.X, padx=3, pady=2)
        self.btn_add_pen = ttk.Button(br, text="Add Penetration", command=self._add_penetration, state="disabled")
        self.btn_add_pen.pack(side=tk.LEFT, padx=3)
        self.btn_toggle_pens = ttk.Button(br, text="Hide Penetrations", command=self._toggle_pens, state="disabled")
        self.btn_toggle_pens.pack(side=tk.LEFT, padx=3)

    # ---- Trajectory Planner panel ----
    def _build_trajectory_panel(self, parent):
        tp = ttk.LabelFrame(parent, text="Trajectory Planner")
        tp.pack(fill=tk.X, padx=5, pady=2)
        self._panel_frames['trajectory'] = tp

        # ── Section 1: Define the trajectory line ──
        s1 = ttk.LabelFrame(tp, text="1. Define Trajectory (sets the line)")
        s1.pack(fill=tk.X, padx=3, pady=2)

        r1a = ttk.Frame(s1); r1a.pack(fill=tk.X, padx=3, pady=1)
        ttk.Label(r1a, text="Stereotaxic:").pack(side=tk.LEFT, padx=3)
        self.traj_ml_var = tk.DoubleVar(value=0.0)
        self.traj_ap_var = tk.DoubleVar(value=0.0)
        self.traj_dv_var = tk.DoubleVar(value=0.0)
        for lbl, var in [("ML:", self.traj_ml_var), ("AP:", self.traj_ap_var), ("DV:", self.traj_dv_var)]:
            ttk.Label(r1a, text=lbl).pack(side=tk.LEFT, padx=(6, 1))
            e = ttk.Entry(r1a, textvariable=var, width=8)
            e.pack(side=tk.LEFT, padx=1)
            e.bind("<Return>", lambda ev: self._on_traj_stereo_enter())
        self.traj_stereo_label = ttk.Label(r1a, text="", foreground="#555555")
        self.traj_stereo_label.pack(side=tk.LEFT, padx=4)

        r1b = ttk.Frame(s1); r1b.pack(fill=tk.X, padx=3, pady=1)
        ttk.Label(r1b, text="Chamber:").pack(side=tk.LEFT, padx=3)
        self.traj_az_var = tk.DoubleVar(value=0.0)
        self.traj_el_var = tk.DoubleVar(value=0.0)
        self.traj_dist_var = tk.DoubleVar(value=35.0)
        for lbl, var in [("Az(°):", self.traj_az_var), ("El(°):", self.traj_el_var), ("Dist(mm):", self.traj_dist_var)]:
            ttk.Label(r1b, text=lbl).pack(side=tk.LEFT, padx=(6, 1))
            e = ttk.Entry(r1b, textvariable=var, width=8)
            e.pack(side=tk.LEFT, padx=1)
            e.bind("<Return>", lambda ev: self._on_traj_chamber_enter())

        r1c = ttk.Frame(s1); r1c.pack(fill=tk.X, padx=3, pady=2)
        self.btn_plan_traj = ttk.Button(r1c, text="Plan to Cursor",
                                         command=self._plan_trajectory, state="disabled")
        self.btn_plan_traj.pack(side=tk.LEFT, padx=3)
        self.btn_set_traj = ttk.Button(r1c, text="Set Trajectory (from entries)",
                                        command=self._on_traj_chamber_enter, state="disabled")
        self.btn_set_traj.pack(side=tk.LEFT, padx=3)
        self.btn_clear_traj = ttk.Button(r1c, text="Clear All",
                                          command=self._clear_trajectory, state="disabled")
        self.btn_clear_traj.pack(side=tk.LEFT, padx=3)

        self.traj_info_var = tk.StringVar(value="No trajectory set")
        ttk.Label(s1, textvariable=self.traj_info_var, font=("TkDefaultFont", 9),
                  foreground="#006699").pack(anchor="w", padx=5, pady=(0, 2))

        # ── Section 2: Add points along the trajectory ──
        s2 = ttk.LabelFrame(tp, text="2. Mark Points (along the trajectory)")
        s2.pack(fill=tk.X, padx=3, pady=2)

        r2a = ttk.Frame(s2); r2a.pack(fill=tk.X, padx=3, pady=2)
        ttk.Label(r2a, text="Point Dist(mm):").pack(side=tk.LEFT, padx=3)
        self.traj_pt_dist_var = tk.DoubleVar(value=35.0)
        pt_dist_entry = ttk.Entry(r2a, textvariable=self.traj_pt_dist_var, width=8)
        pt_dist_entry.pack(side=tk.LEFT, padx=2)
        pt_dist_entry.bind("<Return>", lambda ev: self._on_pt_dist_enter())

        ttk.Label(r2a, text="Label:").pack(side=tk.LEFT, padx=(8, 2))
        self.traj_label_var = tk.StringVar(value="")
        ttk.Entry(r2a, textvariable=self.traj_label_var, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Label(r2a, text="Color:").pack(side=tk.LEFT, padx=(6, 2))
        self.traj_color_var = tk.StringVar(value="yellow")
        ttk.Combobox(r2a, textvariable=self.traj_color_var, state="readonly", width=8,
                      values=COLORS).pack(side=tk.LEFT, padx=2)
        ttk.Label(r2a, text="Notes:").pack(side=tk.LEFT, padx=(6, 2))
        self.traj_notes_var = tk.StringVar(value="")
        ttk.Entry(r2a, textvariable=self.traj_notes_var, width=15).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

        r2b = ttk.Frame(s2); r2b.pack(fill=tk.X, padx=3, pady=2)
        self.btn_add_point = ttk.Button(r2b, text="Add Point at Dist",
                                         command=self._add_temp_point, state="disabled")
        self.btn_add_point.pack(side=tk.LEFT, padx=3)
        self.btn_remove_point = ttk.Button(r2b, text="Remove Last",
                                            command=self._remove_last_temp_point, state="disabled")
        self.btn_remove_point.pack(side=tk.LEFT, padx=3)
        self.traj_pt_info_var = tk.StringVar(value="")
        ttk.Label(r2b, textvariable=self.traj_pt_info_var, foreground="#555555",
                  font=("TkDefaultFont", 8)).pack(side=tk.LEFT, padx=8)

        # ── Section 3: Record Actual (during experiment) ──
        s3 = ttk.LabelFrame(tp, text="3. Record Actual (during experiment)")
        s3.pack(fill=tk.X, padx=3, pady=2)

        r3a = ttk.Frame(s3); r3a.pack(fill=tk.X, padx=3, pady=2)
        ttk.Label(r3a, text="Tip Dist(mm):").pack(side=tk.LEFT, padx=3)
        self.traj_actual_dist_var = tk.DoubleVar(value=35.0)
        ttk.Entry(r3a, textvariable=self.traj_actual_dist_var, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Label(r3a, text="Channel#:").pack(side=tk.LEFT, padx=(8, 2))
        self.traj_channel_var = tk.StringVar(value="0")
        ttk.Combobox(r3a, textvariable=self.traj_channel_var, width=6,
                      values=sorted(_CHANNEL_ORDER)).pack(side=tk.LEFT, padx=2)
        ttk.Label(r3a, text="Label:").pack(side=tk.LEFT, padx=(8, 2))
        self.traj_actual_label_var = tk.StringVar(value="")
        ttk.Entry(r3a, textvariable=self.traj_actual_label_var, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Label(r3a, text="Notes:").pack(side=tk.LEFT, padx=(6, 2))
        self.traj_actual_notes_var = tk.StringVar(value="")
        ttk.Entry(r3a, textvariable=self.traj_actual_notes_var, width=15).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=2)

        r3b = ttk.Frame(s3); r3b.pack(fill=tk.X, padx=3, pady=2)
        self.btn_record_actual = ttk.Button(r3b, text="Record Actual Point",
                                             command=self._record_actual_point, state="disabled")
        self.btn_record_actual.pack(side=tk.LEFT, padx=3)
        self.traj_actual_info_var = tk.StringVar(value="")
        ttk.Label(r3b, textvariable=self.traj_actual_info_var, foreground="#006699",
                  font=("TkDefaultFont", 8)).pack(side=tk.LEFT, padx=8)

        # ── Section 4: Save planned points ──
        s4 = ttk.LabelFrame(tp, text="4. Save Planned Points")
        s4.pack(fill=tk.X, padx=3, pady=2)

        r4a = ttk.Frame(s4); r4a.pack(fill=tk.X, padx=3, pady=2)
        self.btn_save_traj = ttk.Button(r4a, text="Save Planned to DB",
                                         command=self._save_trajectory, state="disabled")
        self.btn_save_traj.pack(side=tk.LEFT, padx=3)

        self.traj_points_var = tk.StringVar(value="")
        ttk.Label(s4, textvariable=self.traj_points_var, font=("TkDefaultFont", 8),
                  foreground="#444444").pack(anchor="w", padx=5, pady=(0, 3))

    # ---- Atlas panel ----
    def _build_atlas_panel(self, parent):
        at = ttk.LabelFrame(parent, text="Atlas Alignment  (hotkey 'A' to toggle)")
        at.pack(fill=tk.X, padx=5, pady=2)
        self._panel_frames['atlas'] = at

        # Row 1: file loading + toggle
        r1 = ttk.Frame(at); r1.pack(fill=tk.X, padx=3, pady=2)
        self.btn_load_atlas = ttk.Button(r1, text="Load Atlas NIfTI...", command=self._browse_atlas_nifti)
        self.btn_load_atlas.pack(side=tk.LEFT, padx=3)
        self.btn_load_atlas_labels = ttk.Button(r1, text="Load Labels...", command=self._browse_atlas_labels, state="disabled")
        self.btn_load_atlas_labels.pack(side=tk.LEFT, padx=3)
        self.btn_load_template = ttk.Button(r1, text="Load Template MRI...", command=self._browse_template_mri, state="disabled")
        self.btn_load_template.pack(side=tk.LEFT, padx=3)
        self.btn_toggle_atlas = ttk.Button(r1, text="Show Atlas", command=self._toggle_atlas, state="disabled")
        self.btn_toggle_atlas.pack(side=tk.LEFT, padx=3)
        self.atlas_info_var = tk.StringVar(value="No atlas loaded")
        ttk.Label(r1, textvariable=self.atlas_info_var).pack(side=tk.LEFT, padx=8)

        # Row 1b: template MRI blend slider
        r1b = ttk.Frame(at); r1b.pack(fill=tk.X, padx=3, pady=2)
        ttk.Label(r1b, text="MRI Blend ('T' to snap):").pack(side=tk.LEFT, padx=3)
        ttk.Label(r1b, text="Subject").pack(side=tk.LEFT, padx=(3, 0))
        self.blend_var = tk.DoubleVar(value=0.0)
        self.blend_scale = ttk.Scale(r1b, from_=0.0, to=1.0, orient=tk.HORIZONTAL,
                                      variable=self.blend_var,
                                      command=self._on_blend_slider)
        self.blend_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)
        ttk.Label(r1b, text="Template").pack(side=tk.LEFT, padx=(0, 3))
        self.blend_lbl = ttk.Label(r1b, text="0%", width=5)
        self.blend_lbl.pack(side=tk.LEFT, padx=3)

        # Row 2: rotation
        r2 = ttk.Frame(at); r2.pack(fill=tk.X, padx=3, pady=2)
        ttk.Label(r2, text="Rotate (deg):").pack(side=tk.LEFT, padx=3)
        for al, an in [("X(ML/roll)", "x"), ("Y(AP/pitch)", "y"), ("Z(DV/yaw)", "z")]:
            ttk.Label(r2, text=f"{al}:").pack(side=tk.LEFT, padx=(6, 2))
            v = tk.DoubleVar(value=0.0); setattr(self, f"atlas_rot_{an}_var", v)
            ttk.Entry(r2, textvariable=v, width=7).pack(side=tk.LEFT, padx=2)

        # Row 3: translation
        r3 = ttk.Frame(at); r3.pack(fill=tk.X, padx=3, pady=2)
        ttk.Label(r3, text="Translate (mm):").pack(side=tk.LEFT, padx=3)
        for al, an in [("X(ML)", "tx"), ("Y(AP)", "ty"), ("Z(DV)", "tz")]:
            ttk.Label(r3, text=f"{al}:").pack(side=tk.LEFT, padx=(6, 2))
            v = tk.DoubleVar(value=0.0); setattr(self, f"atlas_trans_{an}_var", v)
            ttk.Entry(r3, textvariable=v, width=7).pack(side=tk.LEFT, padx=2)

        # Row 3b: scale (uniform by default, per-axis optional)
        r3b = ttk.Frame(at); r3b.pack(fill=tk.X, padx=3, pady=2)
        ttk.Label(r3b, text="Scale (%):").pack(side=tk.LEFT, padx=3)
        ttk.Label(r3b, text="Uniform:").pack(side=tk.LEFT, padx=(6, 2))
        self.atlas_scale_uniform_var = tk.DoubleVar(value=0.0)
        self.atlas_scale_uniform_entry = ttk.Entry(r3b, textvariable=self.atlas_scale_uniform_var, width=7)
        self.atlas_scale_uniform_entry.pack(side=tk.LEFT, padx=2)
        ttk.Label(r3b, text="  Per-axis:").pack(side=tk.LEFT, padx=(10, 2))
        self.atlas_scale_peraxis_var = tk.BooleanVar(value=False)
        self.atlas_scale_peraxis_cb = ttk.Checkbutton(
            r3b, variable=self.atlas_scale_peraxis_var,
            command=self._on_atlas_scale_mode_change)
        self.atlas_scale_peraxis_cb.pack(side=tk.LEFT, padx=2)
        self.atlas_scale_axis_vars = {}
        self.atlas_scale_axis_entries = {}
        for al, an in [("X:", "sx"), ("Y:", "sy"), ("Z:", "sz")]:
            lbl = ttk.Label(r3b, text=al); lbl.pack(side=tk.LEFT, padx=(4, 1))
            v = tk.DoubleVar(value=0.0); self.atlas_scale_axis_vars[an] = v
            e = ttk.Entry(r3b, textvariable=v, width=6, state="disabled")
            e.pack(side=tk.LEFT, padx=1)
            self.atlas_scale_axis_entries[an] = e
        ttk.Label(r3b, text="(0 = no change)", foreground="#555555").pack(side=tk.LEFT, padx=6)

        # Row 4: buttons
        r4 = ttk.Frame(at); r4.pack(fill=tk.X, padx=3, pady=2)
        self.btn_atlas_apply = ttk.Button(r4, text="Apply", command=self._apply_atlas_correction, state="disabled")
        self.btn_atlas_apply.pack(side=tk.LEFT, padx=3)
        self.btn_atlas_reset = ttk.Button(r4, text="Reset to Identity", command=self._reset_atlas_correction, state="disabled")
        self.btn_atlas_reset.pack(side=tk.LEFT, padx=3)
        self.btn_atlas_undo = ttk.Button(r4, text="Undo", command=self._atlas_undo, state="disabled")
        self.btn_atlas_undo.pack(side=tk.LEFT, padx=3)
        self.btn_atlas_redo = ttk.Button(r4, text="Redo", command=self._atlas_redo, state="disabled")
        self.btn_atlas_redo.pack(side=tk.LEFT, padx=3)
        ttk.Button(r4, text="History", command=self._show_atlas_history).pack(side=tk.LEFT, padx=3)

        # Row 5: appearance
        r5 = ttk.Frame(at); r5.pack(fill=tk.X, padx=3, pady=2)
        ttk.Label(r5, text="Contour color:").pack(side=tk.LEFT, padx=3)
        self.atlas_color_var = tk.StringVar(value="cyan")
        color_cb = ttk.Combobox(r5, textvariable=self.atlas_color_var, state="readonly", width=10,
                                values=["cyan", "yellow", "lime", "magenta", "red", "orange", "white"])
        color_cb.pack(side=tk.LEFT, padx=3)
        color_cb.bind("<<ComboboxSelected>>", self._on_atlas_color_change)

        ttk.Label(r5, text="Line width:").pack(side=tk.LEFT, padx=(8, 3))
        self.atlas_lw_var = tk.DoubleVar(value=0.6)
        ttk.Entry(r5, textvariable=self.atlas_lw_var, width=5).pack(side=tk.LEFT, padx=3)

        ttk.Label(r5, text="Alpha:").pack(side=tk.LEFT, padx=(8, 3))
        self.atlas_alpha_var = tk.DoubleVar(value=0.7)
        ttk.Entry(r5, textvariable=self.atlas_alpha_var, width=5).pack(side=tk.LEFT, padx=3)

        # Info / version
        self.atlas_corr_info_var = tk.StringVar(value="")
        ttk.Label(at, textvariable=self.atlas_corr_info_var).pack(anchor="w", padx=5, pady=1)
        self.atlas_corr_ver_var = tk.StringVar(value="")
        ttk.Label(at, textvariable=self.atlas_corr_ver_var).pack(anchor="w", padx=5, pady=1)

        # Note
        nr = ttk.Frame(at); nr.pack(fill=tk.X, padx=3, pady=2)
        ttk.Label(nr, text="Note:").pack(side=tk.LEFT, padx=3)
        self.atlas_corr_note_var = tk.StringVar(value="")
        ttk.Entry(nr, textvariable=self.atlas_corr_note_var, width=50).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)

    def _build_sliders(self, parent):
        sf = ttk.Frame(parent); sf.pack(fill=tk.X, padx=5, pady=2)
        self.slice_vars, self.slice_scales, self.slice_lbls, self.ebz_goto_btns = [], [], [], []
        for i, name in enumerate(self.VIEW_NAMES):
            ttk.Label(sf, text=f"{name}:").grid(row=i, column=0, sticky="w", padx=3, pady=1)
            v = tk.DoubleVar(value=0.0)
            sc = ttk.Scale(sf, from_=0, to=1, orient=tk.HORIZONTAL, variable=v,
                           command=lambda val, idx=i: self._on_slider(idx))
            sc.grid(row=i, column=1, sticky="we", padx=3)
            lb = ttk.Label(sf, text="0.00 mm", width=20)
            lb.grid(row=i, column=2, padx=3)
            btn = ttk.Button(sf, text="→0", width=3,
                             command=lambda idx=i: self._goto_ebz_zero(idx), state="disabled")
            btn.grid(row=i, column=3, padx=2)
            self.slice_vars.append(v); self.slice_scales.append(sc)
            self.slice_lbls.append(lb); self.ebz_goto_btns.append(btn)
        sf.columnconfigure(1, weight=1)

        self.dyn_frame = ttk.Frame(sf)
        self.dyn_frame.grid(row=3, column=0, columnspan=4, sticky="we")
        ttk.Label(self.dyn_frame, text="Dynamic:").grid(row=0, column=0, sticky="w", padx=3)
        self.dyn_var = tk.IntVar(value=0)
        self.dyn_scale = ttk.Scale(self.dyn_frame, from_=0, to=0, orient=tk.HORIZONTAL,
                                   variable=self.dyn_var, command=lambda *a: self._on_dyn_slider())
        self.dyn_scale.grid(row=0, column=1, sticky="we", padx=3)
        self.dyn_lbl = ttk.Label(self.dyn_frame, text="0/0", width=14)
        self.dyn_lbl.grid(row=0, column=2, padx=3)
        self.dyn_frame.columnconfigure(1, weight=1)
        self.dyn_frame.grid_remove()

    def _toggle_panel(self, key):
        """Show/hide a single control panel. Only one panel visible at a time."""
        if self._active_panel == key:
            # Clicking the active panel's button collapses it
            self._panel_frames[key].pack_forget()
            self._panel_buttons[key].state(['!pressed'])
            self._active_panel = None
        else:
            # Hide the currently active panel (if any)
            if self._active_panel is not None:
                self._panel_frames[self._active_panel].pack_forget()
                self._panel_buttons[self._active_panel].state(['!pressed'])
            # Show the new one
            self._panel_frames[key].pack(fill=tk.X, padx=5, pady=2,
                                          in_=self._panel_container)
            self._panel_buttons[key].state(['pressed'])
            self._active_panel = key

    # ================================================================ File I/O
    def _browse(self):
        d = os.path.dirname(self.default_path) if self.default_path and not os.path.isdir(self.default_path) else self.default_path
        fn = filedialog.askopenfilename(title="Select PAR File",
                                        filetypes=[("PAR", "*.PAR *.par"), ("All", "*.*")],
                                        initialdir=d)
        if fn:
            self.file_path_var.set(fn)

    def _check_rec(self, par):
        b = os.path.splitext(par)[0]
        return os.path.exists(b + ".REC") or os.path.exists(b + ".rec")

    def _save_defaults(self):
        p = self.file_path_var.get().strip()
        if not p:
            messagebox.showerror("Error", "No path"); return
        cp = os.path.join(os.getcwd(), "mri_viewer_config.json")
        try:
            c = {"default_path": p}
            if self.ebz_set:
                c["ebz_world"] = self.ebz_world.tolist()
            if self._chamber_path and os.path.exists(self._chamber_path):
                c["monkey_specific_path"] = self._chamber_path
            if self._atlas_nifti_path and os.path.exists(self._atlas_nifti_path):
                c["atlas_nifti_path"] = self._atlas_nifti_path
            if self._atlas_label_path and os.path.exists(self._atlas_label_path):
                c["atlas_label_path"] = self._atlas_label_path
            if self._template_mri_path and os.path.exists(self._template_mri_path):
                c["template_mri_path"] = self._template_mri_path
            with open(cp, "w") as f:
                json.dump(c, f, indent=2)
            self.default_path = p
            # Show exactly what got saved so it's easy to verify
            saved_keys = [k for k in c if k != "default_path"]
            extra = f"  +  {', '.join(saved_keys)}" if saved_keys else ""
            messagebox.showinfo("Saved", f"Defaults saved{extra}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _corr_json_for(self, par):
        return os.path.splitext(par)[0] + "_corrections.json"

    # ================================================================ Loading
    def load_and_visualize(self):
        par = self.file_path_var.get().strip()
        if not par:
            messagebox.showerror("Error", "Select a PAR file."); return
        if not os.path.exists(par):
            messagebox.showerror("Error", f"{par} not found."); return
        if not par.upper().endswith(".PAR"):
            if not messagebox.askyesno("Warning", "Not a .PAR extension. Continue?"):
                return
        if not self._check_rec(par):
            messagebox.showerror("Error", ".REC not found."); return

        try:
            self.status_var.set(f"Loading {par}..."); self.root.update()
            self.data, self.native_affine, self.voxel_sizes, self.img = load_volume(par)

            if self.data.ndim == 4:
                self.has_dynamics = True; self.dynamics = self.data.shape[3]
            else:
                self.has_dynamics = False; self.dynamics = 1
            self.dim_sizes = list(self.data.shape[:3])

            self.corr_json_path = self._corr_json_for(par)
            self.correction, self.corr_config = load_corrections(self.corr_json_path)
            self.crop_bounds = load_crop_bounds(self.corr_config)
            self._recompute()
            self.cursor_world = self.world_center.copy()
            self._setup_sliders()

            if self.has_dynamics:
                self.dyn_scale.configure(from_=0, to=self.dynamics - 1)
                self.dyn_var.set(0); self.dyn_frame.grid()
            else:
                self.dyn_frame.grid_remove()

            for b in (self.btn_set_ebz, self.btn_ebz_xhair, self.btn_apply,
                      self.btn_reset_corr, self.btn_undo, self.btn_redo,
                      self.btn_ebz_pick, self.btn_crop, self.btn_reset_crop,
                      self.btn_reset_zoom):
                b.config(state="normal")
            for b in self.ebz_goto_btns:
                b.config(state="normal")

            if self.chamber_state['loaded']:
                self.btn_plan_traj.config(state="normal")
                self.btn_set_traj.config(state="normal")

            self._update_corr_info()
            self.display_all()
            self.status_var.set(
                f"Loaded {os.path.basename(par)}  shape={self.dim_sizes}  "
                f"voxel={self.voxel_sizes[0]:.3f}×{self.voxel_sizes[1]:.3f}×{self.voxel_sizes[2]:.3f} mm")
        except Exception as e:
            self.status_var.set("Error"); messagebox.showerror("Error", str(e))
            import traceback; traceback.print_exc()

    # ================================================================ Recompute
    def _recompute(self):
        self.corrected_affine = self.correction @ self.native_affine
        self.inv_corrected = np.linalg.inv(self.corrected_affine)

        self.full_world_min, self.full_world_max = compute_world_bbox(self.corrected_affine, self.dim_sizes)
        self.world_center = (self.full_world_min + self.full_world_max) / 2.0
        self.world_min = self.full_world_min.copy()
        self.world_max = self.full_world_max.copy()

        vs = self.output_voxel_size
        self.view_display_bounds = []
        self.grid_sizes = []
        for vi in range(3):
            _, h_wax, v_wax = self.SLICE_CFG[vi]
            h_lo, h_hi = self.full_world_min[h_wax], self.full_world_max[h_wax]
            v_lo, v_hi = self.full_world_min[v_wax], self.full_world_max[v_wax]
            if vi in self.crop_bounds:
                ch_lo, ch_hi, cv_lo, cv_hi = self.crop_bounds[vi]
                h_lo = max(h_lo, ch_lo); h_hi = min(h_hi, ch_hi)
                v_lo = max(v_lo, cv_lo); v_hi = min(v_hi, cv_hi)
            self.view_display_bounds.append((h_lo, h_hi, v_lo, v_hi))
            n_h = max(2, int(np.ceil((h_hi - h_lo) / vs)))
            n_v = max(2, int(np.ceil((v_hi - v_lo) / vs)))
            self.grid_sizes.append((n_h, n_v))

    def _setup_sliders(self):
        for i in range(3):
            fix_wax = self.SLICE_CFG[i][0]
            lo, hi = self.full_world_min[fix_wax], self.full_world_max[fix_wax]
            self.slice_scales[i].configure(from_=lo, to=hi)
            self.slice_vars[i].set(self.world_center[fix_wax])

    # ================================================================ Coordinate transforms
    def vox_to_world(self, vox):
        return (self.corrected_affine @ np.array([*vox[:3], 1.0]))[:3]

    def world_to_vox(self, w):
        return (self.inv_corrected @ np.array([*w[:3], 1.0]))[:3]

    # ================================================================ Atlas combined inverse
    def _atlas_inv_combined(self):
        """inv(atlas_correction @ atlas_sform): corrected_world → atlas_voxel."""
        return np.linalg.inv(self.atlas_correction @ self.atlas_sform)

    # ================================================================ Display
    def display_all(self):
        if self.data is None:
            return

        # Pre-compute atlas inverse if atlas is visible
        atlas_inv = None
        if self.atlas_loaded and self.atlas_show:
            atlas_inv = self._atlas_inv_combined()

        # Template blend factor
        blend = self.template_blend if self.template_loaded and atlas_inv is not None else 0.0

        for vi in range(3):
            ax = self.axes[vi]
            ax.clear()

            fix_wax, h_wax, v_wax = self.SLICE_CFG[vi]
            img2d, h_coords, v_coords = reslice_view(
                self.data, self.inv_corrected, self.view_display_bounds[vi],
                self.grid_sizes[vi], self.SLICE_CFG[vi], self.cursor_world,
                self.current_dynamic, self.has_dynamics,
                interp_order=self.interp_order)

            # ---- Template MRI blending ----
            if blend > 0 and atlas_inv is not None:
                try:
                    tmpl_2d, _, _ = reslice_template_mri(
                        self.template_data, atlas_inv,
                        self.view_display_bounds[vi],
                        self.grid_sizes[vi],
                        self.SLICE_CFG[vi],
                        self.cursor_world,
                        interp_order=self.interp_order)
                    # Normalize both to [0, 1] for blending
                    sub_norm = img2d.astype(np.float64)
                    tmpl_norm = tmpl_2d.astype(np.float64)
                    # Use percentile-based normalization for each
                    snz = sub_norm[sub_norm > 0]
                    if len(snz) > 100:
                        s_lo, s_hi = np.percentile(snz, [1, 99])
                        sub_norm = np.clip((sub_norm - s_lo) / max(s_hi - s_lo, 1), 0, 1)
                    elif sub_norm.max() > 0:
                        sub_norm /= sub_norm.max()

                    tnz = tmpl_norm[tmpl_norm > 0]
                    if len(tnz) > 100:
                        t_lo, t_hi = np.percentile(tnz, [1, 99])
                        tmpl_norm = np.clip((tmpl_norm - t_lo) / max(t_hi - t_lo, 1), 0, 1)
                    elif tmpl_norm.max() > 0:
                        tmpl_norm /= tmpl_norm.max()

                    # Linear blend
                    img2d = (1.0 - blend) * sub_norm + blend * tmpl_norm
                except Exception:
                    pass  # fall through to unblended subject MRI

            # When EBZ is set, show coords relative to EBZ so the star is at (0,0)
            disp_off = self.ebz_world if self.ebz_set else np.zeros(3)
            h_off = disp_off[h_wax]
            v_off = disp_off[v_wax]

            extent = [h_coords[0] - h_off, h_coords[-1] - h_off,
                      v_coords[-1] - v_off, v_coords[0] - v_off]
            im = ax.imshow(img2d, cmap='gray', aspect='equal', origin='upper',
                           interpolation='nearest', extent=extent)
            # Set contrast: blended images are already [0,1]; raw images need percentile scaling
            if blend > 0:
                im.set_clim(0, 1)
            else:
                try:
                    nz = img2d[img2d > 0]
                    if len(nz) > 100:
                        im.set_clim(*np.percentile(nz, [1, 99]))
                except:
                    pass

            # ---- Atlas contour overlay ----
            if atlas_inv is not None:
                try:
                    label_2d, a_h, a_v = reslice_atlas(
                        self.atlas_data, atlas_inv,
                        self.view_display_bounds[vi],
                        self.grid_sizes[vi],
                        self.SLICE_CFG[vi],
                        self.cursor_world)
                    draw_atlas_contours(
                        ax, label_2d, a_h, a_v,
                        display_offset_h=h_off,
                        display_offset_v=v_off,
                        color=self.atlas_contour_color,
                        linewidth=self.atlas_contour_lw,
                        alpha=self.atlas_contour_alpha)
                except Exception:
                    pass  # don't let atlas errors break MRI display

            # Crosshair
            ax.axvline(self.cursor_world[h_wax] - h_off, color='lime', lw=0.7, alpha=0.6)
            ax.axhline(self.cursor_world[v_wax] - v_off, color='lime', lw=0.7, alpha=0.6)

            # EBZ — always at (0,0) in EBZ-relative display space
            if self.ebz_set:
                ax.axvline(0, color='red', lw=0.5, alpha=0.4, ls='--')
                ax.axhline(0, color='red', lw=0.5, alpha=0.4, ls='--')
                ax.plot(0, 0, 'r*', markersize=8)

            # Chamber + penetrations
            draw_chamber_overlay(
                ax, vi, self.SLICE_CFG[vi], self.chamber_state,
                self.ebz_world if self.ebz_set else np.zeros(3),
                self.pen_store.penetrations if self.pen_store.connected else [],
                show_chamber=self.chamber_show,
                show_penetrations=self.pen_show,
                display_offset=disp_off)

            # Temp trajectory from planner (solid yellow line, red channel dots)
            if self.temp_trajectory is not None and self.chamber_show:
                t = self.temp_trajectory
                top_pt = t['top_pt']
                direction = t['direction']
                dist = t['dist_mm']
                track_end = top_pt + (dist + 5) * direction
                target = t['target']
                ax.plot([top_pt[h_wax] - h_off, track_end[h_wax] - h_off],
                        [top_pt[v_wax] - v_off, track_end[v_wax] - v_off],
                        '-', color='yellow', lw=1.5, alpha=0.9)
                ax.plot(target[h_wax] - h_off, target[v_wax] - v_off,
                        'x', color='yellow', markersize=8, markeredgewidth=2)
                # Per-channel dots along the probe shank
                for idx in range(32):
                    offset_mm = (_TIP_TO_BOTTOM_CH_UM + (31 - idx) * _CH_SPACING_UM) / 1000.0
                    ch_dist = dist - offset_mm
                    if ch_dist < 0:
                        continue
                    pt = top_pt + ch_dist * direction
                    ax.plot(pt[h_wax] - h_off, pt[v_wax] - v_off,
                            'o', color='red', markersize=3, alpha=0.8)

            # Temp points from planner (labeled markers with trajectory lines)
            if self.temp_points and self.chamber_show:
                for tp in self.temp_points:
                    target = tp['target']
                    color = tp.get('color', 'yellow')
                    top_pt = tp['top_pt']
                    direction = tp['direction']
                    dist = tp['dist_mm']
                    track_end = top_pt + (dist + 5) * direction
                    # Trajectory line
                    ax.plot([top_pt[h_wax] - h_off, track_end[h_wax] - h_off],
                            [top_pt[v_wax] - v_off, track_end[v_wax] - v_off],
                            '-', color=color, lw=1.0, alpha=0.7)
                    # Target marker
                    ax.plot(target[h_wax] - h_off, target[v_wax] - v_off,
                            'o', color=color, markersize=6, markeredgecolor='white', markeredgewidth=0.5)
                    # Label
                    ax.annotate(tp.get('label', ''),
                                (target[h_wax] - h_off, target[v_wax] - v_off),
                                fontsize=7, color=color, ha='left', va='bottom')
                    # Depth ticks every 5mm
                    for d in range(0, int(dist) + 1, 5):
                        pt = top_pt + d * direction
                        ax.plot(pt[h_wax] - h_off, pt[v_wax] - v_off,
                                '.', color=color, markersize=2, alpha=0.5)

            # Title
            wval = self.cursor_world[fix_wax]
            if self.ebz_set:
                rel = wval - self.ebz_world[fix_wax]
                title = f"{self.VIEW_NAMES[vi]}  {self.WORLD_LABELS[fix_wax]}={rel:+.2f} mm (EBZ)"
            else:
                title = f"{self.VIEW_NAMES[vi]}  {self.WORLD_LABELS[fix_wax]}={wval:.2f} mm"
            ax.set_title(title, fontsize=10)
            ax.set_xlabel(self.WORLD_LABELS[h_wax], fontsize=9)
            ax.set_ylabel(self.WORLD_LABELS[v_wax], fontsize=9)
            ax.tick_params(labelsize=7)
            ax._vi = vi

            # Apply zoom — restricts the visible window WITHOUT changing what was resliced
            if vi in self.zoom_bounds:
                zh_lo, zh_hi, zv_lo, zv_hi = self.zoom_bounds[vi]
                ax.set_xlim(zh_lo, zh_hi)
                # origin='upper' means y-axis is inverted; pass (hi, lo) to keep that orientation
                ax.set_ylim(zv_hi, zv_lo)

        self.fig.canvas.draw_idle()
        self._update_info()
        self._sync_sliders()

    def _update_info(self):
        if self.data is None:
            return
        w = self.cursor_world
        vox = self.world_to_vox(w)
        if self.ebz_set:
            rel = w - self.ebz_world
            txt = f"Crosshair: ML={rel[0]:+.2f}, AP={rel[1]:+.2f}, DV={rel[2]:+.2f} mm (rel EBZ)"
        else:
            txt = f"Crosshair: ML={w[0]:.2f}, AP={w[1]:.2f}, DV={w[2]:.2f} mm   voxel=[{vox[0]:.1f}, {vox[1]:.1f}, {vox[2]:.1f}]"
        # Atlas region at crosshair
        if self.atlas_loaded and self.atlas_show and self.atlas_label_names:
            try:
                region = atlas_label_at_cursor(
                    self.atlas_data, self._atlas_inv_combined(),
                    self.cursor_world, self.atlas_label_names)
                if region:
                    txt += f"   atlas: {region}"
            except Exception:
                pass
        self.cursor_info_var.set(txt)

    def _sync_sliders(self):
        for i in range(3):
            fix_wax = self.SLICE_CFG[i][0]
            val = self.cursor_world[fix_wax]
            self.slice_vars[i].set(val)
            if self.ebz_set:
                rel = val - self.ebz_world[fix_wax]
                self.slice_lbls[i].config(text=f"{rel:+.2f} mm (EBZ)")
            else:
                self.slice_lbls[i].config(text=f"{val:.2f} mm")

    # ================================================================ Mouse events
    def _on_slider(self, view_idx):
        if self.data is None:
            return
        fix_wax = self.SLICE_CFG[view_idx][0]
        new_val = self.slice_vars[view_idx].get()
        if abs(new_val - self.cursor_world[fix_wax]) > 0.01:
            self.cursor_world[fix_wax] = new_val
            self.display_all()

    def _goto_ebz_zero(self, view_idx):
        if self.data is None or not self.ebz_set:
            self.status_var.set("Set EBZ first."); return
        self.cursor_world[self.SLICE_CFG[view_idx][0]] = self.ebz_world[self.SLICE_CFG[view_idx][0]]
        self.display_all()

    def _on_dyn_slider(self):
        self.current_dynamic = self.dyn_var.get()
        self.dyn_lbl.config(text=f"{self.current_dynamic}/{self.dynamics-1}")
        self.display_all()

    def _on_click(self, event):
        if self.data is None or event.inaxes is None:
            return
        ax = event.inaxes
        if not hasattr(ax, '_vi'):
            return
        vi = ax._vi
        _, h_wax, v_wax = self.SLICE_CFG[vi]
        x, y = event.xdata, event.ydata
        if x is None or y is None:
            return

        # Double-click resets zoom on this view
        if event.dblclick and event.button == 1 and not self.crop_mode:
            self._reset_zoom(vi)
            return

        # Display coords are EBZ-relative; convert back to absolute world coords
        disp_off = self.ebz_world if self.ebz_set else np.zeros(3)
        x_world = x + disp_off[h_wax]
        y_world = y + disp_off[v_wax]

        if self.crop_mode and event.button == 1:
            from matplotlib.patches import Rectangle
            self._crop_start = (x, y)
            self._crop_view = vi
            self._crop_rect = Rectangle((x, y), 0, 0, linewidth=2,
                                         edgecolor='cyan', facecolor='cyan', alpha=0.15)
            ax.add_patch(self._crop_rect)
            self.fig.canvas.draw_idle()
            return

        if self.ebz_pick_armed and event.button == 3:
            self.cursor_world[h_wax] = np.clip(x_world, self.world_min[h_wax], self.world_max[h_wax])
            self.cursor_world[v_wax] = np.clip(y_world, self.world_min[v_wax], self.world_max[v_wax])
            self._set_ebz_to_crosshair()
            self._disarm_ebz_pick()
            return

        # Right-click atlas query (when not in EBZ pick mode)
        if event.button == 3 and self.atlas_loaded and self.atlas_show and self.atlas_label_names:
            query_world = self.cursor_world.copy()
            query_world[h_wax] = np.clip(x_world, self.world_min[h_wax], self.world_max[h_wax])
            query_world[v_wax] = np.clip(y_world, self.world_min[v_wax], self.world_max[v_wax])
            self._show_atlas_popup(query_world, event)
            return

        # Middle-click starts a pan drag
        if event.button == 2:
            self._pan_start = (event.min_num_generations, event.y)  # pixel coords (stable during drag)
            self._pan_view = vi
            if vi in self.zoom_bounds:
                self._pan_bounds = self.zoom_bounds[vi]
            else:
                # Compute default full-extent bounds in display coords
                disp_off2 = self.ebz_world if self.ebz_set else np.zeros(3)
                db = self.view_display_bounds[vi]
                self._pan_bounds = (db[0] - disp_off2[h_wax], db[1] - disp_off2[h_wax],
                                    db[3] - disp_off2[v_wax], db[2] - disp_off2[v_wax])
            return

        if event.button == 1:
            self.cursor_world[h_wax] = np.clip(x_world, self.world_min[h_wax], self.world_max[h_wax])
            self.cursor_world[v_wax] = np.clip(y_world, self.world_min[v_wax], self.world_max[v_wax])
            self.display_all()

    def _on_release(self, event):
        # End middle-mouse pan
        if event.button == 2 and self._pan_start is not None:
            self._pan_start = None
            self._pan_view = None
            self._pan_bounds = None
            return

        if not self.crop_mode or self._crop_start is None:
            return
        if event.inaxes is None:
            return
        ax = event.inaxes
        if not hasattr(ax, '_vi') or ax._vi != self._crop_view:
            return
        x, y = event.xdata, event.ydata
        if x is None or y is None:
            return
        x0, y0 = self._crop_start
        h_lo, h_hi = min(x0, x), max(x0, x)
        v_lo, v_hi = min(y0, y), max(y0, y)
        if (h_hi - h_lo) < 5 or (v_hi - v_lo) < 5:
            self.crop_status_var.set("Too small, ignored.")
            self._crop_start = None; self._crop_rect = None; self._crop_view = None
            self.display_all()
            return

        vi = self._crop_view
        # Convert display (EBZ-relative) coords back to absolute world for storage
        _, h_wax_c, v_wax_c = self.SLICE_CFG[vi]
        disp_off = self.ebz_world if self.ebz_set else np.zeros(3)
        h_lo += disp_off[h_wax_c]; h_hi += disp_off[h_wax_c]
        v_lo += disp_off[v_wax_c]; v_hi += disp_off[v_wax_c]
        old_crops = getattr(self, '_saved_crop_for_cancel', {})
        self.crop_bounds = {k: v for k, v in old_crops.items() if k != vi}
        self.crop_bounds[vi] = (h_lo, h_hi, v_lo, v_hi)
        if hasattr(self, '_saved_crop_for_cancel'):
            delattr(self, '_saved_crop_for_cancel')
        self.crop_mode = False
        self._crop_start = None; self._crop_rect = None; self._crop_view = None
        self.btn_crop.config(text="Crop Views (drag rectangle)")

        self._recompute()
        self.cursor_world = np.clip(self.cursor_world, self.full_world_min, self.full_world_max)
        self._setup_sliders()
        save_crop_bounds(self.corr_config, self.crop_bounds)
        save_corrections(self.corr_json_path, self.corr_config)
        self.display_all()
        self.crop_status_var.set(f"Cropped {self.VIEW_NAMES[vi]}")

    def _on_motion(self, event):
        if self.data is None or event.inaxes is None:
            return

        # Middle-mouse pan drag
        if self._pan_start is not None and event.inaxes is not None:
            ax = event.inaxes
            if hasattr(ax, '_vi') and ax._vi == self._pan_view:
                # Compute pixel delta from drag start
                px, py = event.min_num_generations, event.y
                px0, py0 = self._pan_start
                dpx, dpy = px - px0, py - py0

                # Convert pixel delta to data delta using the initial bounds and axes pixel extent
                pb = self._pan_bounds
                bbox = ax.get_window_extent()
                h_range = pb[1] - pb[0]
                v_range = pb[3] - pb[2]
                dx_data = -dpx * h_range / bbox.width
                # y-axis is inverted in display (origin='upper')
                dy_data = dpy * v_range / bbox.height

                new_bounds = (pb[0] + dx_data, pb[1] + dx_data,
                              pb[2] + dy_data, pb[3] + dy_data)
                self.zoom_bounds[self._pan_view] = new_bounds
                self.display_all()
            return

        if self.crop_mode and self._crop_start is not None and self._crop_rect is not None:
            x, y = event.xdata, event.ydata
            if x is not None and y is not None:
                x0, y0 = self._crop_start
                self._crop_rect.set_xy((min(x0, x), min(y0, y)))
                self._crop_rect.set_width(abs(x - x0))
                self._crop_rect.set_height(abs(y - y0))
                self.fig.canvas.draw_idle()
            return
        ax = event.inaxes
        if hasattr(ax, '_vi'):
            vi = ax._vi
            x, y = event.xdata, event.ydata
            if x is not None and y is not None:
                _, h_wax, v_wax = self.SLICE_CFG[vi]
                if self.ebz_set:
                    status = (f"{self.VIEW_NAMES[vi]}  {self.WORLD_LABELS[h_wax]}={x:+.2f}  "
                              f"{self.WORLD_LABELS[v_wax]}={y:+.2f} mm  (EBZ-relative)")
                else:
                    status = (f"{self.VIEW_NAMES[vi]}  {self.WORLD_LABELS[h_wax]}={x:.2f}  "
                              f"{self.WORLD_LABELS[v_wax]}={y:.2f} mm")

                # Atlas region lookup at hover position
                hover_world = self.cursor_world.copy()
                disp_off = self.ebz_world if self.ebz_set else np.zeros(3)
                hover_world[h_wax] = x + disp_off[h_wax]
                hover_world[v_wax] = y + disp_off[v_wax]

                if self.atlas_loaded and self.atlas_show and self.atlas_label_names:
                    try:
                        region = atlas_label_at_cursor(
                            self.atlas_data, self._atlas_inv_combined(),
                            hover_world, self.atlas_label_names)
                        if region:
                            status += f"   [{region}]"
                    except Exception:
                        pass

                # Chamber coordinates at hover position
                if self.chamber_state.get('loaded', False):
                    try:
                        _, az_h, el_h, dist_h, _ = calc_target_angles(
                            hover_world,
                            self.chamber_state['origin'],
                            self.chamber_state['x'],
                            self.chamber_state['y'],
                            self.chamber_state['normal'],
                            self.chamber_state['cor_offset'])
                        status += f"   Az={az_h:.1f}° El={el_h:.1f}° Dist={dist_h:.1f}mm"
                    except Exception:
                        pass

                self.status_var.set(status)

    # ================================================================ Keyboard
    def _on_key_atlas_toggle(self, event=None):
        """Hotkey 'A' toggles atlas overlay (only when no text entry has focus)."""
        # Don't toggle if a text entry is focused
        w = self.root.focus_get()
        if isinstance(w, (tk.Entry, ttk.Entry)):
            return
        if self.atlas_loaded:
            self._toggle_atlas()

    # ================================================================ EBZ
    def _set_ebz_to_crosshair(self):
        if self.data is None:
            return
        self.ebz_world = self.cursor_world.copy()
        self.ebz_ap_var.set(round(self.ebz_world[1], 3))
        self.ebz_dv_var.set(round(self.ebz_world[2], 3))
        self.ebz_ml_var.set(round(self.ebz_world[0], 3))
        self.ebz_set = True
        self.btn_reset_ebz.config(state="normal")
        self.display_all()

    def _set_ebz_manual(self):
        if self.data is None:
            return
        try:
            self.ebz_world = np.array([self.ebz_ml_var.get(), self.ebz_ap_var.get(), self.ebz_dv_var.get()])
            self.ebz_set = True
            self.btn_reset_ebz.config(state="normal")
            self.display_all()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _reset_ebz(self):
        self.ebz_set = False; self.ebz_world = np.zeros(3)
        self.ebz_ap_var.set(0); self.ebz_dv_var.set(0); self.ebz_ml_var.set(0)
        self.btn_reset_ebz.config(state="disabled")
        self.display_all()

    def _toggle_ebz_pick(self):
        if self.ebz_pick_armed:
            self._disarm_ebz_pick()
        else:
            self.ebz_pick_armed = True
            self.ebz_pick_label_var.set("EBZ PICK ACTIVE — right-click to set, or click button to cancel")
            self.btn_ebz_pick.config(text="Cancel EBZ Pick")
            if self.crop_mode:
                self._exit_crop_mode()

    def _disarm_ebz_pick(self):
        self.ebz_pick_armed = False
        self.ebz_pick_label_var.set("")
        self.btn_ebz_pick.config(text="Pick EBZ (right-click)")

    # ================================================================ Cropping
    def _toggle_crop_mode(self):
        if self.crop_mode:
            self._exit_crop_mode(); return
        if self.ebz_pick_armed:
            self._disarm_ebz_pick()
        self.crop_mode = True
        self.btn_crop.config(text="Cancel Crop")
        self.crop_status_var.set("CROP MODE: drag a rectangle on any view")
        self._saved_crop_for_cancel = self.crop_bounds.copy()
        self.crop_bounds = {}
        self._recompute(); self._setup_sliders(); self.display_all()

    def _exit_crop_mode(self):
        self.crop_mode = False
        self._crop_start = None; self._crop_rect = None; self._crop_view = None
        self.btn_crop.config(text="Crop Views (drag rectangle)")
        if hasattr(self, '_saved_crop_for_cancel'):
            if not self.crop_bounds and self._saved_crop_for_cancel:
                self.crop_bounds = self._saved_crop_for_cancel
                self._recompute(); self.cursor_world = np.clip(self.cursor_world, self.full_world_min, self.full_world_max)
                self._setup_sliders(); self.display_all()
            delattr(self, '_saved_crop_for_cancel')
        self.crop_status_var.set("")

    # ================================================================ Zoom
    def _on_scroll(self, event):
        """Scroll-wheel zooms the view under the cursor, centered on the mouse.
        zoom_bounds are stored in EBZ-relative display coords."""
        if self.data is None or event.inaxes is None:
            return
        ax = event.inaxes
        if not hasattr(ax, '_vi'):
            return
        vi = ax._vi
        _, h_wax, v_wax = self.SLICE_CFG[vi]

        # Current visible window in display coords
        if vi in self.zoom_bounds:
            h_lo, h_hi, v_lo, v_hi = self.zoom_bounds[vi]
        else:
            # Default: full resliced extent in display (EBZ-relative) coords
            disp_off = self.ebz_world if self.ebz_set else np.zeros(3)
            db = self.view_display_bounds[vi]
            h_lo = db[0] - disp_off[h_wax]
            h_hi = db[1] - disp_off[h_wax]
            v_lo = db[3] - disp_off[v_wax]   # v_hi becomes v_lo in display (inverted)
            v_hi = db[2] - disp_off[v_wax]

        mx, my = event.xdata, event.ydata  # already in EBZ-relative display coords
        if mx is None or my is None:
            return

        factor = 0.75 if event.button == 'up' else (1.0 / 0.75)

        new_h_lo = mx + (h_lo - mx) * factor
        new_h_hi = mx + (h_hi - mx) * factor
        new_v_lo = my + (v_lo - my) * factor
        new_v_hi = my + (v_hi - my) * factor

        # Full extent in display coords (used as zoom-out limit)
        disp_off = self.ebz_world if self.ebz_set else np.zeros(3)
        db = self.view_display_bounds[vi]
        full_h_span = db[1] - db[0]
        full_v_span = db[3] - db[2]

        if (new_h_hi - new_h_lo) >= full_h_span * 1.01 and \
           abs(new_v_hi - new_v_lo) >= full_v_span * 1.01:
            self.zoom_bounds.pop(vi, None)
        else:
            self.zoom_bounds[vi] = (new_h_lo, new_h_hi, new_v_lo, new_v_hi)

        self.display_all()

    def _reset_zoom(self, vi=None):
        """Reset zoom for one view index, or all if vi is None."""
        if vi is None:
            self.zoom_bounds.clear()
        else:
            self.zoom_bounds.pop(vi, None)
        if self.data is not None:
            self.display_all()

    # ================================================================ Interpolation / resolution
    def _on_interp_change(self, event=None):
        order_map = {"Nearest (order 0)": 0, "Linear (order 1)": 1, "Cubic (order 3)": 3}
        self.interp_order = order_map.get(self.interp_var.get(), 3)
        if self.data is not None:
            self.display_all()

    def _on_voxel_size_change(self, event=None):
        try:
            vs = float(self.voxel_size_var.get())
            if vs <= 0:
                raise ValueError
        except (ValueError, tk.TclError):
            self.voxel_size_var.set(self.output_voxel_size)
            return
        self.output_voxel_size = vs
        if self.data is not None:
            self._recompute()
            self.display_all()

    def _reset_crop(self):
        self.crop_bounds = {}
        if self.crop_mode:
            self._exit_crop_mode()
        self._recompute()
        self.cursor_world = np.clip(self.cursor_world, self.full_world_min, self.full_world_max)
        self._setup_sliders()
        save_crop_bounds(self.corr_config, self.crop_bounds)
        save_corrections(self.corr_json_path, self.corr_config)
        self.display_all()
        self.crop_status_var.set("Crop reset.")

    # ================================================================ Chamber
    def _load_chamber_file(self):
        fn = filedialog.askopenfilename(title="Select monkey_specific.py",
                                        filetypes=[("Python", "*.py"), ("All", "*.*")])
        if not fn:
            return
        self._load_chamber_from_path(fn)

    def _load_chamber_from_path(self, fn):
        """Load a monkey_specific.py by absolute path. Safe to call before a volume is loaded."""
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("monkey_specific", fn)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)

            screws_ebz = mod.get_screw_hole_coords()
            self._chamber_params['ref_screw_idx'] = mod.get_reference_screw_idx()
            self._chamber_params['center_of_rotation_offset'] = mod.get_center_of_rotation_offset()
            self._chamber_params['is_fit_circle'] = mod.get_is_fit_circle()
            if hasattr(mod, 'get_chamber_depth'):
                self._chamber_params['chamber_depth'] = mod.get_chamber_depth()

            self.chamber_state['screws_ebz'] = screws_ebz
            self.chamber_state['cor_offset'] = self._chamber_params['center_of_rotation_offset']
            self._chamber_path = fn  # remembered so _save_defaults can persist it
            self._refit_chamber()

            self.btn_toggle_chamber.config(state="normal")
            if self.pen_store.connected:
                self.btn_add_pen.config(state="normal")
                self.btn_load_session.config(state="normal")
            if self.data is not None:
                self.btn_plan_traj.config(state="normal")
                self.btn_set_traj.config(state="normal")

            if hasattr(mod, 'get_electrode_target'):
                mode, coords = mod.get_electrode_target()
                if mode == 'angles':
                    self.pen_az_var.set(coords[0]); self.pen_el_var.set(coords[1]); self.pen_dist_var.set(coords[2])

            if self.data is not None:
                self.display_all()
        except Exception as e:
            messagebox.showerror("Error loading chamber file", str(e))
            import traceback; traceback.print_exc()

    def _refit_chamber(self):
        screws_ebz = self.chamber_state['screws_ebz']
        if screws_ebz is None:
            return
        ebz = self.ebz_world if self.ebz_set else np.zeros(3)
        screws_world = screws_ebz + ebz

        center, origin, x, y, normal = fit_chamber(
            screws_world,
            self._chamber_params['ref_screw_idx'],
            self._chamber_params['center_of_rotation_offset'],
            self._chamber_params['is_fit_circle'])

        self.chamber_state.update({
            'loaded': True, 'center': center, 'origin': origin,
            'x': x, 'y': y, 'normal': normal,
        })
        self.chamber_info_var.set(
            f"Chamber: {len(screws_ebz)} screwholes, origin="
            f"[{origin[0]:.1f}, {origin[1]:.1f}, {origin[2]:.1f}] mm")

    def _toggle_chamber(self):
        self.chamber_show = not self.chamber_show
        self.btn_toggle_chamber.config(text="Show Chamber" if not self.chamber_show else "Hide Chamber")
        self.display_all()

    # ================================================================ Penetrations (DB)
    def _connect_db(self):
        try:
            self.pen_store.connect()
            self.btn_pen_list.config(state="normal")
            self.btn_toggle_pens.config(state="normal")
            if self.chamber_state['loaded']:
                self.btn_add_pen.config(state="normal")
            if self.temp_trajectory is not None or self.temp_points:
                self.btn_save_traj.config(state="normal")
            if self.temp_trajectory is not None:
                self.btn_record_actual.config(state="normal")
            n = len(self.pen_store.penetrations)
            self.status_var.set(f"DB connected. {n} penetrations loaded.")
            if self.chamber_state['loaded']:
                self.btn_load_session.config(state="normal")
            self.display_all()
        except Exception as e:
            messagebox.showerror("DB Error", str(e))
            import traceback; traceback.print_exc()

    def _add_penetration(self):
        if not self.pen_store.connected:
            messagebox.showerror("Error", "Connect to DB first."); return
        if not self.chamber_state['loaded']:
            messagebox.showerror("Error", "Load chamber first."); return
        az = self.pen_az_var.get()
        el = self.pen_el_var.get()
        dist = self.pen_dist_var.get()
        label = self.pen_label_var.get().strip()
        notes = self.pen_notes_var.get().strip()
        session_id = self.session_id_var.get().strip()
        color = COLORS[len(self.pen_store.penetrations) % len(COLORS)]
        self.pen_store.add(az, el, dist, label=label, session_id=session_id,
                           color=color, notes=notes)
        self.display_all()

    def _toggle_pens(self):
        self.pen_show = not self.pen_show
        self.btn_toggle_pens.config(text="Show Penetrations" if not self.pen_show else "Hide Penetrations")
        self.display_all()

    def _show_pen_list(self):
        if not self.pen_store.connected:
            messagebox.showerror("Error", "Connect to DB first."); return
        PenetrationListWindow(self.root, self.pen_store, on_change_callback=self.display_all)

    # ================================================================ Trajectory Planner
    def _plan_trajectory(self):
        """Compute trajectory from chamber origin to current cursor position and lock it in."""
        if not self.chamber_state['loaded']:
            messagebox.showerror("Error", "Load chamber first."); return
        if self.data is None:
            messagebox.showerror("Error", "Load a volume first."); return
        target = self.cursor_world.copy()
        self._update_traj_from_target(target)

    def _on_traj_stereo_enter(self):
        """User pressed Enter in a stereotaxic entry — set trajectory from target coords."""
        if not self.chamber_state['loaded']:
            self.traj_info_var.set("Load chamber first."); return
        try:
            ml = self.traj_ml_var.get()
            ap = self.traj_ap_var.get()
            dv = self.traj_dv_var.get()
        except (ValueError, tk.TclError):
            self.traj_info_var.set("Invalid stereotaxic coordinates."); return
        target = np.array([ml, ap, dv])
        if self.ebz_set:
            target = target + self.ebz_world
        self._update_traj_from_target(target)

    def _on_traj_chamber_enter(self):
        """User pressed Enter in a chamber entry — set trajectory from az/el/dist."""
        if not self.chamber_state['loaded']:
            self.traj_info_var.set("Load chamber first."); return
        try:
            az_deg = self.traj_az_var.get()
            el_deg = self.traj_el_var.get()
            dist = self.traj_dist_var.get()
        except (ValueError, tk.TclError):
            self.traj_info_var.set("Invalid chamber coordinates."); return
        self._update_traj_from_chamber(az_deg, el_deg, dist)

    def _update_traj_from_target(self, target):
        """Given a target point, compute chamber coords and lock in the trajectory."""
        if self._traj_updating:
            return
        self._traj_updating = True
        try:
            origin = self.chamber_state['origin']
            x_vec = self.chamber_state['x']
            y_vec = self.chamber_state['y']
            normal = self.chamber_state['normal']
            cor_offset = self.chamber_state['cor_offset']

            direction, az_deg, el_deg, distance, top_pt = calc_target_angles(
                target, origin, x_vec, y_vec, normal, cor_offset)

            # Update both entry rows
            self.traj_az_var.set(round(az_deg, 2))
            self.traj_el_var.set(round(el_deg, 2))
            self.traj_dist_var.set(round(distance, 2))
            if self.ebz_set:
                rel = target - self.ebz_world
                self.traj_ml_var.set(round(rel[0], 2))
                self.traj_ap_var.set(round(rel[1], 2))
                self.traj_dv_var.set(round(rel[2], 2))
                self.traj_stereo_label.config(text="(rel EBZ)")
            else:
                self.traj_ml_var.set(round(target[0], 2))
                self.traj_ap_var.set(round(target[1], 2))
                self.traj_dv_var.set(round(target[2], 2))
                self.traj_stereo_label.config(text="")

            self._lock_trajectory(az_deg, el_deg, distance, target, direction, top_pt)
        finally:
            self._traj_updating = False

    def _update_traj_from_chamber(self, az_deg, el_deg, dist):
        """Given chamber angles, compute target and lock in the trajectory."""
        if self._traj_updating:
            return
        self._traj_updating = True
        try:
            origin = self.chamber_state['origin']
            x_vec = self.chamber_state['x']
            y_vec = self.chamber_state['y']
            normal = self.chamber_state['normal']
            cor_offset = self.chamber_state['cor_offset']

            target, direction, top_pt = calc_penetration_target(
                origin, az_deg, el_deg, dist, x_vec, y_vec, normal, cor_offset)

            # Update stereo entries
            if self.ebz_set:
                rel = target - self.ebz_world
                self.traj_ml_var.set(round(rel[0], 2))
                self.traj_ap_var.set(round(rel[1], 2))
                self.traj_dv_var.set(round(rel[2], 2))
                self.traj_stereo_label.config(text="(rel EBZ)")
            else:
                self.traj_ml_var.set(round(target[0], 2))
                self.traj_ap_var.set(round(target[1], 2))
                self.traj_dv_var.set(round(target[2], 2))
                self.traj_stereo_label.config(text="")

            self.traj_az_var.set(round(az_deg, 2))
            self.traj_el_var.set(round(el_deg, 2))
            self.traj_dist_var.set(round(dist, 2))

            self._lock_trajectory(az_deg, el_deg, dist, target, direction, top_pt)
        finally:
            self._traj_updating = False

    def _lock_trajectory(self, az_deg, el_deg, dist, target, direction, top_pt):
        """Lock in the trajectory line. Enables point-adding controls."""
        self.temp_trajectory = {
            'az_deg': az_deg, 'el_deg': el_deg, 'dist_mm': dist,
            'target': target, 'direction': direction, 'top_pt': top_pt,
        }

        # Default the point dist to the trajectory dist
        self.traj_pt_dist_var.set(round(dist, 2))
        self._update_pt_info()

        # Info label
        if self.ebz_set:
            rel = target - self.ebz_world
            self.traj_info_var.set(
                f"Trajectory locked: Az={az_deg:.1f}°  El={el_deg:.1f}°  Dist={dist:.1f} mm    |    "
                f"Target: ML={rel[0]:+.2f}, AP={rel[1]:+.2f}, DV={rel[2]:+.2f} (rel EBZ)")
        else:
            self.traj_info_var.set(
                f"Trajectory locked: Az={az_deg:.1f}°  El={el_deg:.1f}°  Dist={dist:.1f} mm    |    "
                f"Target: ML={target[0]:.2f}, AP={target[1]:.2f}, DV={target[2]:.2f}")

        # Enable controls
        self.btn_clear_traj.config(state="normal")
        self.btn_add_point.config(state="normal")
        self.btn_save_traj.config(state="normal" if self.pen_store.connected else "disabled")
        self.btn_record_actual.config(state="normal" if self.pen_store.connected else "disabled")
        self.traj_actual_dist_var.set(round(dist, 2))

        if self.data is not None:
            self.display_all()

    def _on_pt_dist_enter(self):
        """User changed point dist — update the stereo readout for this depth."""
        self._update_pt_info()

    def _update_pt_info(self):
        """Show where the current point dist falls in stereotaxic coords."""
        if self.temp_trajectory is None:
            self.traj_pt_info_var.set("")
            return
        try:
            pt_dist = self.traj_pt_dist_var.get()
        except (ValueError, tk.TclError):
            return
        t = self.temp_trajectory
        origin = self.chamber_state['origin']
        cor_offset = self.chamber_state['cor_offset']
        el_rad = np.radians(t['el_deg'])
        origin_offset = cor_offset / np.cos(el_rad) if np.cos(el_rad) != 0 else 0.0
        pt = t['top_pt'] + pt_dist * t['direction'] if pt_dist > origin_offset else t['top_pt']
        # Actually compute properly: target at pt_dist along trajectory
        target_at_dist, _, _ = calc_penetration_target(
            origin, t['az_deg'], t['el_deg'], pt_dist,
            self.chamber_state['x'], self.chamber_state['y'],
            self.chamber_state['normal'], cor_offset)
        if self.ebz_set:
            rel = target_at_dist - self.ebz_world
            self.traj_pt_info_var.set(
                f"At {pt_dist:.1f}mm: ML={rel[0]:+.2f}, AP={rel[1]:+.2f}, DV={rel[2]:+.2f} (rel EBZ)")
        else:
            self.traj_pt_info_var.set(
                f"At {pt_dist:.1f}mm: ML={target_at_dist[0]:.2f}, AP={target_at_dist[1]:.2f}, DV={target_at_dist[2]:.2f}")

    def _add_temp_point(self):
        """Snapshot a point at the current Point Dist along the locked trajectory."""
        if self.temp_trajectory is None:
            messagebox.showerror("Error", "Set a trajectory first."); return
        try:
            pt_dist = self.traj_pt_dist_var.get()
        except (ValueError, tk.TclError):
            messagebox.showerror("Error", "Invalid point distance."); return

        t = self.temp_trajectory
        label = self.traj_label_var.get().strip()
        if not label:
            label = f"T{len(self.temp_points) + 1}"
        color = self.traj_color_var.get()
        notes = self.traj_notes_var.get().strip()

        # Compute the target at this dist along the same az/el
        origin = self.chamber_state['origin']
        cor_offset = self.chamber_state['cor_offset']
        target_at_dist, direction, top_pt = calc_penetration_target(
            origin, t['az_deg'], t['el_deg'], pt_dist,
            self.chamber_state['x'], self.chamber_state['y'],
            self.chamber_state['normal'], cor_offset)

        point = {
            'az_deg': t['az_deg'], 'el_deg': t['el_deg'], 'dist_mm': pt_dist,
            'label': label, 'color': color, 'notes': notes,
            'target': target_at_dist, 'direction': direction, 'top_pt': top_pt,
        }
        self.temp_points.append(point)

        self.traj_label_var.set(f"T{len(self.temp_points) + 1}")
        self.btn_remove_point.config(state="normal")
        self._update_temp_points_display()
        if self.data is not None:
            self.display_all()

    def _remove_last_temp_point(self):
        """Remove the most recently added temp point."""
        if self.temp_points:
            self.temp_points.pop()
        if not self.temp_points:
            self.btn_remove_point.config(state="disabled")
        self._update_temp_points_display()
        if self.data is not None:
            self.display_all()

    def _update_temp_points_display(self):
        """Update the summary label showing all temp points."""
        if not self.temp_points:
            self.traj_points_var.set("No points added yet")
            return
        parts = []
        for p in self.temp_points:
            parts.append(f"{p['label']}({p['color']}, D={p['dist_mm']:.1f})")
        self.traj_points_var.set(f"{len(self.temp_points)} point(s): " + "  |  ".join(parts))

    def _record_actual_point(self):
        """Record an actual experimental point: saves immediately to DB with channel correction."""
        if self.temp_trajectory is None:
            messagebox.showerror("Error", "Set a trajectory first."); return
        if not self.pen_store.connected:
            messagebox.showerror("Error", "Connect to DB first."); return

        session_id = self.session_id_var.get().strip()
        if not session_id:
            messagebox.showerror("Error", "Enter a Session ID at the top of the window."); return

        try:
            tip_dist = self.traj_actual_dist_var.get()
        except (ValueError, tk.TclError):
            messagebox.showerror("Error", "Invalid tip distance."); return

        try:
            channel_num = int(self.traj_channel_var.get())
            if channel_num not in _CHANNEL_ORDER:
                messagebox.showerror("Error", f"Channel {channel_num} not in channel order."); return
        except (ValueError, tk.TclError):
            messagebox.showerror("Error", "Select a valid channel number."); return

        t = self.temp_trajectory
        label = self.traj_actual_label_var.get().strip() or session_id
        notes = self.traj_actual_notes_var.get().strip()

        # Apply channel correction
        corrected_dist = _channel_corrected_dist(tip_dist, channel_num)

        # Compute target at the corrected dist
        origin = self.chamber_state['origin']
        cor_offset = self.chamber_state['cor_offset']
        target_at_dist, _, _ = calc_penetration_target(
            origin, t['az_deg'], t['el_deg'], corrected_dist,
            self.chamber_state['x'], self.chamber_state['y'],
            self.chamber_state['normal'], cor_offset)

        # Build notes
        notes_extra = f"ch{channel_num} tip={tip_dist:.2f}mm corrected={corrected_dist:.2f}mm"
        if self.ebz_set:
            rel = target_at_dist - self.ebz_world
            coord_note = f"target=[{rel[0]:+.2f}, {rel[1]:+.2f}, {rel[2]:+.2f}] rel EBZ"
        else:
            coord_note = f"target=[{target_at_dist[0]:.2f}, {target_at_dist[1]:.2f}, {target_at_dist[2]:.2f}]"
        full_notes = "  ".join(part for part in [notes, notes_extra, coord_note] if part)

        color = COLORS[len(self.pen_store.penetrations) % len(COLORS)]
        pen_id = self.pen_store.add(
            t['az_deg'], t['el_deg'], corrected_dist,
            label=label, session_id=session_id, pen_type="actual",
            color=color, notes=full_notes)

        self.traj_actual_info_var.set(
            f"Saved actual id={pen_id}: ch{channel_num}, tip={tip_dist:.1f}→{corrected_dist:.1f}mm")
        self.display_all()

    def _save_trajectory(self):
        """Save all planned temp points to the DB. If no points, save the trajectory tip."""
        if not self.pen_store.connected:
            messagebox.showerror("Error", "Connect to DB first."); return

        session_id = self.session_id_var.get().strip()
        if not session_id:
            messagebox.showerror("Error", "Enter a Session ID at the top of the window."); return

        to_save = list(self.temp_points)

        # If no points were explicitly added, save the trajectory tip itself
        if not to_save and self.temp_trajectory is not None:
            t = self.temp_trajectory
            label = self.traj_label_var.get().strip() or "P1"
            color = self.traj_color_var.get()
            notes = self.traj_notes_var.get().strip()
            to_save.append({
                'az_deg': t['az_deg'], 'el_deg': t['el_deg'], 'dist_mm': t['dist_mm'],
                'label': label, 'color': color, 'notes': notes, 'target': t['target'].copy(),
            })

        if not to_save:
            messagebox.showerror("Error", "Nothing to save."); return

        n_saved = 0
        for p in to_save:
            dist = p['dist_mm']
            notes = p.get('notes', '')

            target = p['target']
            if self.ebz_set:
                rel = target - self.ebz_world
                coord_note = f"target=[{rel[0]:+.2f}, {rel[1]:+.2f}, {rel[2]:+.2f}] rel EBZ"
            else:
                coord_note = f"target=[{target[0]:.2f}, {target[1]:.2f}, {target[2]:.2f}]"

            full_notes = "  ".join(part for part in [notes, coord_note] if part)
            self.pen_store.add(p['az_deg'], p['el_deg'], dist,
                               label=p['label'], session_id=session_id,
                               pen_type="planned", color=p['color'], notes=full_notes)
            n_saved += 1

        # Also save the trajectory tip position as planned_tip
        if self.temp_trajectory is not None:
            t = self.temp_trajectory
            tip_target = t['target']
            if self.ebz_set:
                rel = tip_target - self.ebz_world
                tip_coord = f"target=[{rel[0]:+.2f}, {rel[1]:+.2f}, {rel[2]:+.2f}] rel EBZ"
            else:
                tip_coord = f"target=[{tip_target[0]:.2f}, {tip_target[1]:.2f}, {tip_target[2]:.2f}]"
            self.pen_store.add(
                t['az_deg'], t['el_deg'], t['dist_mm'],
                label="tip", session_id=session_id,
                pen_type="planned_tip", color="white", notes=tip_coord)
            n_saved += 1

        self.traj_info_var.set(f"Saved {n_saved} planned point{'s' if n_saved != 1 else ''} to DB.")
        self.display_all()

    def _load_session(self):
        """Load all penetrations for the current session_id and display them as temp trajectory + points."""
        if not self.pen_store.connected:
            messagebox.showerror("Error", "Connect to DB first."); return
        if not self.chamber_state['loaded']:
            messagebox.showerror("Error", "Load chamber first."); return

        session_id = self.session_id_var.get().strip()
        if not session_id:
            messagebox.showerror("Error", "Enter a Session ID."); return

        self.pen_store.refresh()
        session_pens = [p for p in self.pen_store.penetrations if p['session_id'] == session_id]
        if not session_pens:
            messagebox.showinfo("Info", f"No penetrations found for session '{session_id}'.")
            return

        origin = self.chamber_state['origin']
        x_vec = self.chamber_state['x']
        y_vec = self.chamber_state['y']
        normal = self.chamber_state['normal']
        cor_offset = self.chamber_state['cor_offset']

        # Find the planned_tip entry to set the trajectory line
        tip_entry = None
        for p in session_pens:
            if p['pen_type'] == 'planned_tip':
                tip_entry = p
                break

        # If no planned_tip, use the first entry's az/el to define the line
        if tip_entry is None:
            tip_entry = session_pens[0]

        az, el, dist = tip_entry['az_deg'], tip_entry['el_deg'], tip_entry['dist_mm']
        target, direction, top_pt = calc_penetration_target(
            origin, az, el, dist, x_vec, y_vec, normal, cor_offset)

        # Lock this as the trajectory
        self._traj_updating = True
        try:
            self.traj_az_var.set(round(az, 2))
            self.traj_el_var.set(round(el, 2))
            self.traj_dist_var.set(round(dist, 2))
            if self.ebz_set:
                rel = target - self.ebz_world
                self.traj_ml_var.set(round(rel[0], 2))
                self.traj_ap_var.set(round(rel[1], 2))
                self.traj_dv_var.set(round(rel[2], 2))
                self.traj_stereo_label.config(text="(rel EBZ)")
            else:
                self.traj_ml_var.set(round(target[0], 2))
                self.traj_ap_var.set(round(target[1], 2))
                self.traj_dv_var.set(round(target[2], 2))
                self.traj_stereo_label.config(text="")
        finally:
            self._traj_updating = False

        self.temp_trajectory = {
            'az_deg': az, 'el_deg': el, 'dist_mm': dist,
            'target': target, 'direction': direction, 'top_pt': top_pt,
        }
        self.traj_pt_dist_var.set(round(dist, 2))

        # Load all non-tip entries as temp points
        self.temp_points.clear()
        for p in session_pens:
            if p['pen_type'] == 'planned_tip':
                continue
            pt_target, pt_dir, pt_top = calc_penetration_target(
                origin, p['az_deg'], p['el_deg'], p['dist_mm'],
                x_vec, y_vec, normal, cor_offset)
            self.temp_points.append({
                'az_deg': p['az_deg'], 'el_deg': p['el_deg'], 'dist_mm': p['dist_mm'],
                'label': p['label'], 'color': p['color'], 'notes': p.get('notes', ''),
                'target': pt_target, 'direction': pt_dir, 'top_pt': pt_top,
            })

        n_planned = sum(1 for p in session_pens if p['pen_type'] == 'planned')
        n_actual = sum(1 for p in session_pens if p['pen_type'] == 'actual')
        self.traj_info_var.set(
            f"Loaded session '{session_id}': {n_planned} planned, {n_actual} actual, "
            f"Az={az:.1f}° El={el:.1f}° Dist={dist:.1f}mm")
        self._update_pt_info()
        self._update_temp_points_display()

        # Enable all controls
        self.btn_clear_traj.config(state="normal")
        self.btn_add_point.config(state="normal")
        self.btn_save_traj.config(state="normal")
        self.btn_record_actual.config(state="normal")
        if self.temp_points:
            self.btn_remove_point.config(state="normal")

        if self.data is not None:
            self.display_all()

    def _clear_trajectory(self):
        """Remove the trajectory and all temp points."""
        self.temp_trajectory = None
        self.temp_points.clear()
        self.traj_info_var.set("No trajectory set")
        self.traj_pt_info_var.set("")
        self.traj_actual_info_var.set("")
        self._update_temp_points_display()
        self.traj_ml_var.set(0.0); self.traj_ap_var.set(0.0); self.traj_dv_var.set(0.0)
        self.traj_az_var.set(0.0); self.traj_el_var.set(0.0); self.traj_dist_var.set(35.0)
        self.traj_pt_dist_var.set(35.0)
        self.btn_save_traj.config(state="disabled")
        self.btn_clear_traj.config(state="disabled")
        self.btn_remove_point.config(state="disabled")
        self.btn_add_point.config(state="disabled")
        self.btn_record_actual.config(state="disabled")
        if self.data is not None:
            self.display_all()

    # ================================================================ Correction matrix
    def _apply_correction(self):
        if self.data is None:
            return
        rx, ry, rz = self.rot_x_var.get(), self.rot_y_var.get(), self.rot_z_var.get()
        tx, ty, tz = self.trans_tx_var.get(), self.trans_ty_var.get(), self.trans_tz_var.get()
        delta = xlate(tx, ty, tz) @ rot_z(rz) @ rot_y(ry) @ rot_x(rx)
        new_corr = delta @ self.correction
        note = self.corr_note_var.get().strip()
        if not note:
            parts = []
            if rx: parts.append(f"Rx={rx}");
            if ry: parts.append(f"Ry={ry}")
            if rz: parts.append(f"Rz={rz}")
            if tx: parts.append(f"Tx={tx}");
            if ty: parts.append(f"Ty={ty}")
            if tz: parts.append(f"Tz={tz}")
            note = ", ".join(parts) if parts else "no-op"
        self.correction = new_corr
        push_correction(self.corr_config, new_corr, note)
        save_corrections(self.corr_json_path, self.corr_config)
        self._recompute()
        self.cursor_world = np.clip(self.cursor_world, self.full_world_min, self.full_world_max)
        self._setup_sliders(); self._update_corr_info()
        for v in (self.rot_x_var, self.rot_y_var, self.rot_z_var,
                  self.trans_tx_var, self.trans_ty_var, self.trans_tz_var):
            v.set(0)
        self.corr_note_var.set("")
        self.display_all()

    def _reset_correction(self):
        if self.data is None:
            return
        self.correction = np.eye(4)
        push_correction(self.corr_config, self.correction, "reset to identity")
        save_corrections(self.corr_json_path, self.corr_config)
        self._recompute()
        self.cursor_world = np.clip(self.cursor_world, self.full_world_min, self.full_world_max)
        self._setup_sliders(); self._update_corr_info(); self.display_all()

    def _load_version(self, idx):
        hist = self.corr_config["correction_history"]
        if 0 <= idx < len(hist):
            self.corr_config["current_index"] = idx
            self.correction = np.array(hist[idx]["matrix"])
            save_corrections(self.corr_json_path, self.corr_config)
            self._recompute()
            self.cursor_world = np.clip(self.cursor_world, self.full_world_min, self.full_world_max)
            self._setup_sliders(); self._update_corr_info(); self.display_all()

    def _undo(self):
        if self.data is None:
            return
        idx = self.corr_config.get("current_index", 0)
        if idx > 0:
            self._load_version(idx - 1)
        else:
            self.status_var.set("Already at oldest version.")

    def _redo(self):
        if self.data is None:
            return
        idx = self.corr_config.get("current_index", 0)
        if idx < len(self.corr_config.get("correction_history", [])) - 1:
            self._load_version(idx + 1)
        else:
            self.status_var.set("Already at newest version.")

    def _update_corr_info(self):
        if self.corr_config is None:
            return
        idx = self.corr_config.get("current_index", 0)
        n = len(self.corr_config["correction_history"])
        entry = self.corr_config["correction_history"][idx]
        if np.allclose(self.correction, np.eye(4)):
            self.corr_info_var.set("Correction: identity")
        else:
            det = np.linalg.det(self.correction[:3, :3])
            t = self.correction[:3, 3]
            self.corr_info_var.set(f"Correction: det={det:.6f}  T=[{t[0]:.2f}, {t[1]:.2f}, {t[2]:.2f}] mm")
        self.corr_ver_var.set(f"Version {idx+1}/{n}  |  {entry.get('timestamp','')}  |  {entry.get('note','')}")

    def _show_history(self):
        if not self.corr_config:
            return
        win = tk.Toplevel(self.root); win.title("Correction History"); win.geometry("850x550")
        frame = ttk.Frame(win); frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        sb = ttk.Scrollbar(frame); sb.pack(side=tk.RIGHT, fill=tk.Y)
        txt = tk.Text(frame, wrap=tk.WORD, yscrollcommand=sb.set, font=("Courier", 10))
        txt.pack(fill=tk.BOTH, expand=True); sb.config(command=txt.yview)
        cur = self.corr_config.get("current_index", 0)
        for i, e in enumerate(self.corr_config["correction_history"]):
            mark = "  << CURRENT" if i == cur else ""
            txt.insert(tk.END, f"--- Version {i+1}{mark} ---\n")
            txt.insert(tk.END, f"  Time: {e.get('timestamp','')}\n  Note: {e.get('note','')}\n")
            for row in np.array(e["matrix"]):
                txt.insert(tk.END, f"    [{row[0]:10.6f} {row[1]:10.6f} {row[2]:10.6f} {row[3]:10.6f}]\n")
            txt.insert(tk.END, "\n")
        jf = ttk.Frame(win); jf.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(jf, text="Jump to:").pack(side=tk.LEFT, padx=3)
        jv = tk.IntVar(value=cur + 1)
        ttk.Entry(jf, textvariable=jv, width=5).pack(side=tk.LEFT, padx=3)
        def jump():
            t = jv.get() - 1
            if 0 <= t < len(self.corr_config["correction_history"]):
                self._load_version(t); win.destroy()
        ttk.Button(jf, text="Jump", command=jump).pack(side=tk.LEFT, padx=3)
        txt.config(state=tk.DISABLED)

    def _show_header(self):
        if self.img is None:
            return
        win = tk.Toplevel(self.root); win.title("Header"); win.geometry("900x700")
        frame = ttk.Frame(win); frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        sb = ttk.Scrollbar(frame); sb.pack(side=tk.RIGHT, fill=tk.Y)
        txt = tk.Text(frame, wrap=tk.WORD, yscrollcommand=sb.set)
        txt.pack(fill=tk.BOTH, expand=True); sb.config(command=txt.yview)
        for label, val in [("NATIVE AFFINE", self.native_affine), ("CORRECTION", self.correction),
                           ("CORRECTED AFFINE", self.corrected_affine)]:
            txt.insert(tk.END, f"=== {label} ===\n{val}\n\n")
        txt.insert(tk.END, f"Voxel sizes: {self.voxel_sizes}\nDims: {self.dim_sizes}\n")
        txt.insert(tk.END, f"Full bbox: {self.full_world_min} to {self.full_world_max}\n")
        if self.crop_bounds:
            txt.insert(tk.END, f"Crops: {self.crop_bounds}\n")
        if self.atlas_loaded:
            txt.insert(tk.END, f"\n=== ATLAS ===\n")
            txt.insert(tk.END, f"NIfTI: {self._atlas_nifti_path}\n")
            txt.insert(tk.END, f"sform:\n{self.atlas_sform}\n")
            txt.insert(tk.END, f"atlas_correction:\n{self.atlas_correction}\n")
            txt.insert(tk.END, f"combined (atlas_corr @ sform):\n{self.atlas_correction @ self.atlas_sform}\n")
        h = self.img.header
        if hasattr(h, "general_info"):
            txt.insert(tk.END, "\n=== GENERAL INFO ===\n")
            for k, v in sorted(h.general_info.items()):
                txt.insert(tk.END, f"  {k}: {v}\n")
        txt.insert(tk.END, f"\n=== FULL HEADER ===\n{pprint.pformat(h.__dict__)}")
        txt.config(state=tk.DISABLED)

    # ================================================================ Atlas
    def _browse_atlas_nifti(self):
        fn = filedialog.askopenfilename(
            title="Select Atlas NIfTI",
            filetypes=[("NIfTI", "*.nii *.nii.gz"), ("All", "*.*")])
        if not fn:
            return
        self._load_atlas_from_path(fn)

    def _browse_atlas_labels(self):
        fn = filedialog.askopenfilename(
            title="Select Atlas Label Table",
            filetypes=[("Text", "*.txt *.tsv *.csv"), ("All", "*.*")])
        if not fn:
            return
        self._load_atlas_labels_from_path(fn)

    def _load_atlas_from_path(self, nifti_path):
        """Load a NIfTI atlas volume.  Safe to call at any time."""
        try:
            self.status_var.set(f"Loading atlas {os.path.basename(nifti_path)}...")
            self.root.update()
            data, sform = load_atlas(nifti_path)
            self.atlas_data = data
            self.atlas_sform = sform
            self._atlas_nifti_path = nifti_path
            self.atlas_loaded = True

            # Load or create atlas correction JSON alongside the NIfTI
            self.atlas_corr_json_path = self._atlas_corr_json_for(nifti_path)
            self.atlas_correction, self.atlas_corr_config = load_corrections(self.atlas_corr_json_path)

            # Enable UI
            self.btn_load_atlas_labels.config(state="normal")
            self.btn_load_template.config(state="normal")
            self.btn_toggle_atlas.config(state="normal")
            self.btn_atlas_apply.config(state="normal")
            self.btn_atlas_reset.config(state="normal")
            self.btn_atlas_undo.config(state="normal")
            self.btn_atlas_redo.config(state="normal")

            n_labels = len(np.unique(data)) - (1 if 0 in data else 0)
            self.atlas_info_var.set(
                f"Atlas: {os.path.basename(nifti_path)}  shape={list(data.shape)}  "
                f"{n_labels} regions")
            self._update_atlas_corr_info()

            # Auto-show on first load
            self.atlas_show = True
            self.btn_toggle_atlas.config(text="Hide Atlas")

            if self.data is not None:
                self.display_all()
            self.status_var.set(f"Atlas loaded: {os.path.basename(nifti_path)}")
        except Exception as e:
            messagebox.showerror("Error loading atlas", str(e))
            import traceback; traceback.print_exc()

    def _load_atlas_labels_from_path(self, label_path):
        """Load atlas label names from a text file."""
        try:
            self.atlas_label_names = load_atlas_labels(label_path)
            self._atlas_label_path = label_path
            n = len(self.atlas_label_names)
            self.status_var.set(f"Loaded {n} atlas labels from {os.path.basename(label_path)}")
            if self.data is not None:
                self.display_all()  # refresh to show label at cursor
        except Exception as e:
            messagebox.showerror("Error loading labels", str(e))

    def _atlas_corr_json_for(self, nifti_path):
        """Derive atlas correction JSON path from atlas NIfTI path."""
        # Strip .nii.gz or .nii, then append _atlas_corrections.json
        base = nifti_path
        if base.endswith('.gz'):
            base = base[:-3]
        base = os.path.splitext(base)[0]
        return base + "_atlas_corrections.json"

    def _toggle_atlas(self):
        self.atlas_show = not self.atlas_show
        self.btn_toggle_atlas.config(text="Hide Atlas" if self.atlas_show else "Show Atlas")
        if self.data is not None:
            self.display_all()

    def _show_atlas_popup(self, world_pt, mpl_event):
        """Show a right-click popup with atlas region info at the given world coordinate."""
        try:
            inv_combined = self._atlas_inv_combined()
            pt4 = np.array([*world_pt[:3], 1.0])
            vox = (inv_combined @ pt4)[:3]
            vox_idx = np.round(vox).astype(int)

            shape = self.atlas_data.shape
            if any(v < 0 or v >= s for v, s in zip(vox_idx, shape)):
                label_val = 0
                region = "(outside atlas)"
            else:
                label_val = int(self.atlas_data[vox_idx[0], vox_idx[1], vox_idx[2]])
                if label_val == 0:
                    region = "(no label / background)"
                else:
                    region = self.atlas_label_names.get(label_val, f"unknown label")

            # Build info text
            w = world_pt
            lines = [
                f"Atlas Region: {region}",
                f"Label index: {label_val}",
                f"World: ML={w[0]:.2f}, AP={w[1]:.2f}, DV={w[2]:.2f} mm",
            ]
            if self.ebz_set:
                rel = w - self.ebz_world
                lines.append(f"EBZ-rel: ML={rel[0]:.2f}, AP={rel[1]:.2f}, DV={rel[2]:.2f} mm")
            lines.append(f"Atlas voxel: [{vox_idx[0]}, {vox_idx[1]}, {vox_idx[2]}]")

            # Show as a transient popup menu (auto-dismisses on click elsewhere)
            popup = tk.Menu(self.root, tearoff=0)
            for line in lines:
                popup.add_command(label=line, state="disabled")
            popup.add_separator()
            popup.add_command(label="Copy region name",
                             command=lambda: self._copy_to_clipboard(region))
            popup.add_command(label="Copy coordinates",
                             command=lambda: self._copy_to_clipboard(
                                 f"ML={w[0]:.2f}, AP={w[1]:.2f}, DV={w[2]:.2f}"))

            # Position popup at the mouse pointer
            popup.tk_popup(mpl_event.guiEvent.x_root, mpl_event.guiEvent.y_root)
        except Exception as e:
            self.status_var.set(f"Atlas query error: {e}")

    def _copy_to_clipboard(self, text):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.status_var.set(f"Copied: {text}")

    # ---- Template MRI ----
    def _browse_template_mri(self):
        fn = filedialog.askopenfilename(
            title="Select Template MRI NIfTI",
            filetypes=[("NIfTI", "*.nii *.nii.gz"), ("All", "*.*")])
        if not fn:
            return
        self._load_template_from_path(fn)

    def _load_template_from_path(self, nifti_path):
        """Load a template MRI that shares the atlas voxel space."""
        try:
            self.status_var.set(f"Loading template MRI {os.path.basename(nifti_path)}...")
            self.root.update()
            data, sform = load_template_mri(nifti_path)
            self.template_data = data
            self.template_sform = sform
            self._template_mri_path = nifti_path
            self.template_loaded = True

            self.status_var.set(
                f"Template MRI loaded: {os.path.basename(nifti_path)}  "
                f"shape={list(data.shape)}  Use blend slider to overlay.")
            if self.data is not None and self.atlas_show:
                self.display_all()
        except Exception as e:
            messagebox.showerror("Error loading template MRI", str(e))
            import traceback; traceback.print_exc()

    def _on_blend_slider(self, val=None):
        """Called when the blend slider moves."""
        self.template_blend = self.blend_var.get()
        pct = int(self.template_blend * 100)
        self.blend_lbl.config(text=f"{pct}%")
        if self.data is not None:
            self.display_all()

    def _on_key_blend_snap(self, event=None):
        """Hotkey 'T' snaps blend between 0 → 0.5 → 1.0 → 0."""
        w = self.root.focus_get()
        if isinstance(w, (tk.Entry, ttk.Entry)):
            return
        if not self.template_loaded:
            return
        cur = self.template_blend
        if cur < 0.25:
            nxt = 0.5
        elif cur < 0.75:
            nxt = 1.0
        else:
            nxt = 0.0
        self.blend_var.set(nxt)
        self.template_blend = nxt
        pct = int(nxt * 100)
        self.blend_lbl.config(text=f"{pct}%")
        if self.data is not None:
            self.display_all()

    def _on_atlas_color_change(self, event=None):
        self.atlas_contour_color = self.atlas_color_var.get()
        if self.data is not None and self.atlas_show:
            self.display_all()

    def _on_atlas_scale_mode_change(self):
        """Toggle between uniform and per-axis scale entry."""
        per_axis = self.atlas_scale_peraxis_var.get()
        if per_axis:
            self.atlas_scale_uniform_entry.config(state="disabled")
            for e in self.atlas_scale_axis_entries.values():
                e.config(state="normal")
        else:
            self.atlas_scale_uniform_entry.config(state="normal")
            for e in self.atlas_scale_axis_entries.values():
                e.config(state="disabled")

    # ---- Atlas correction ----
    def _apply_atlas_correction(self):
        if not self.atlas_loaded:
            return
        rx = self.atlas_rot_x_var.get()
        ry = self.atlas_rot_y_var.get()
        rz = self.atlas_rot_z_var.get()
        tx = self.atlas_trans_tx_var.get()
        ty = self.atlas_trans_ty_var.get()
        tz = self.atlas_trans_tz_var.get()

        # Build scale matrix from percent values (0 = no change)
        if self.atlas_scale_peraxis_var.get():
            sx_pct = self.atlas_scale_axis_vars['sx'].get()
            sy_pct = self.atlas_scale_axis_vars['sy'].get()
            sz_pct = self.atlas_scale_axis_vars['sz'].get()
        else:
            sx_pct = sy_pct = sz_pct = self.atlas_scale_uniform_var.get()
        sx = 1.0 + sx_pct / 100.0
        sy = 1.0 + sy_pct / 100.0
        sz = 1.0 + sz_pct / 100.0

        # Order: translate, then scale, then rotate (outermost first)
        delta = xlate(tx, ty, tz) @ scale(sx, sy, sz) @ rot_z(rz) @ rot_y(ry) @ rot_x(rx)
        new_corr = delta @ self.atlas_correction

        note = self.atlas_corr_note_var.get().strip()
        if not note:
            parts = []
            if rx: parts.append(f"Rx={rx}")
            if ry: parts.append(f"Ry={ry}")
            if rz: parts.append(f"Rz={rz}")
            if tx: parts.append(f"Tx={tx}")
            if ty: parts.append(f"Ty={ty}")
            if tz: parts.append(f"Tz={tz}")
            if sx_pct: parts.append(f"Sx={sx_pct}%")
            if sy_pct and self.atlas_scale_peraxis_var.get(): parts.append(f"Sy={sy_pct}%")
            if sz_pct and self.atlas_scale_peraxis_var.get(): parts.append(f"Sz={sz_pct}%")
            note = ", ".join(parts) if parts else "no-op"

        self.atlas_correction = new_corr
        push_correction(self.atlas_corr_config, new_corr, note)
        save_corrections(self.atlas_corr_json_path, self.atlas_corr_config)
        self._update_atlas_corr_info()

        # Reset entry fields
        for v in (self.atlas_rot_x_var, self.atlas_rot_y_var, self.atlas_rot_z_var,
                  self.atlas_trans_tx_var, self.atlas_trans_ty_var, self.atlas_trans_tz_var):
            v.set(0)
        self.atlas_scale_uniform_var.set(0)
        for v in self.atlas_scale_axis_vars.values():
            v.set(0)
        self.atlas_corr_note_var.set("")

        # Update contour appearance from UI
        self.atlas_contour_color = self.atlas_color_var.get()
        try:
            self.atlas_contour_lw = float(self.atlas_lw_var.get())
        except (ValueError, tk.TclError):
            pass
        try:
            self.atlas_contour_alpha = float(self.atlas_alpha_var.get())
        except (ValueError, tk.TclError):
            pass

        if self.data is not None:
            self.display_all()

    def _reset_atlas_correction(self):
        if not self.atlas_loaded:
            return
        self.atlas_correction = np.eye(4)
        push_correction(self.atlas_corr_config, self.atlas_correction, "reset to identity")
        save_corrections(self.atlas_corr_json_path, self.atlas_corr_config)
        self._update_atlas_corr_info()
        if self.data is not None:
            self.display_all()

    def _load_atlas_version(self, idx):
        hist = self.atlas_corr_config["correction_history"]
        if 0 <= idx < len(hist):
            self.atlas_corr_config["current_index"] = idx
            self.atlas_correction = np.array(hist[idx]["matrix"])
            save_corrections(self.atlas_corr_json_path, self.atlas_corr_config)
            self._update_atlas_corr_info()
            if self.data is not None:
                self.display_all()

    def _atlas_undo(self):
        if not self.atlas_loaded:
            return
        idx = self.atlas_corr_config.get("current_index", 0)
        if idx > 0:
            self._load_atlas_version(idx - 1)
        else:
            self.status_var.set("Atlas: already at oldest version.")

    def _atlas_redo(self):
        if not self.atlas_loaded:
            return
        idx = self.atlas_corr_config.get("current_index", 0)
        if idx < len(self.atlas_corr_config.get("correction_history", [])) - 1:
            self._load_atlas_version(idx + 1)
        else:
            self.status_var.set("Atlas: already at newest version.")

    def _update_atlas_corr_info(self):
        if self.atlas_corr_config is None:
            return
        idx = self.atlas_corr_config.get("current_index", 0)
        n = len(self.atlas_corr_config["correction_history"])
        entry = self.atlas_corr_config["correction_history"][idx]
        if np.allclose(self.atlas_correction, np.eye(4)):
            self.atlas_corr_info_var.set("Atlas correction: identity")
        else:
            t = self.atlas_correction[:3, 3]
            # Extract effective scale factors (singular values of the 3×3 sub-matrix)
            sv = np.linalg.svd(self.atlas_correction[:3, :3], compute_uv=False)
            self.atlas_corr_info_var.set(
                f"Atlas correction: S=[{sv[0]:.3f}, {sv[1]:.3f}, {sv[2]:.3f}]  "
                f"T=[{t[0]:.2f}, {t[1]:.2f}, {t[2]:.2f}] mm")
        self.atlas_corr_ver_var.set(
            f"Version {idx+1}/{n}  |  {entry.get('timestamp','')}  |  {entry.get('note','')}")

    def _show_atlas_history(self):
        if not self.atlas_corr_config:
            return
        win = tk.Toplevel(self.root); win.title("Atlas Correction History"); win.geometry("850x550")
        frame = ttk.Frame(win); frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        sb = ttk.Scrollbar(frame); sb.pack(side=tk.RIGHT, fill=tk.Y)
        txt = tk.Text(frame, wrap=tk.WORD, yscrollcommand=sb.set, font=("Courier", 10))
        txt.pack(fill=tk.BOTH, expand=True); sb.config(command=txt.yview)
        cur = self.atlas_corr_config.get("current_index", 0)
        for i, e in enumerate(self.atlas_corr_config["correction_history"]):
            mark = "  << CURRENT" if i == cur else ""
            txt.insert(tk.END, f"--- Version {i+1}{mark} ---\n")
            txt.insert(tk.END, f"  Time: {e.get('timestamp','')}\n  Note: {e.get('note','')}\n")
            for row in np.array(e["matrix"]):
                txt.insert(tk.END, f"    [{row[0]:10.6f} {row[1]:10.6f} {row[2]:10.6f} {row[3]:10.6f}]\n")
            txt.insert(tk.END, "\n")
        jf = ttk.Frame(win); jf.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(jf, text="Jump to:").pack(side=tk.LEFT, padx=3)
        jv = tk.IntVar(value=cur + 1)
        ttk.Entry(jf, textvariable=jv, width=5).pack(side=tk.LEFT, padx=3)
        def jump():
            t = jv.get() - 1
            if 0 <= t < len(self.atlas_corr_config["correction_history"]):
                self._load_atlas_version(t); win.destroy()
        ttk.Button(jf, text="Jump", command=jump).pack(side=tk.LEFT, padx=3)
        txt.config(state=tk.DISABLED)