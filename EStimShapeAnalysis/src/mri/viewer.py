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
from src.mri.viewer_panels import PanelsMixin
from src.mri.viewer_display import DisplayMixin
from src.mri.viewer_crop import CropMixin
from src.mri.viewer_chamber import ChamberMixin
from src.mri.viewer_correction import CorrectionMixin
from src.mri.viewer_atlas import AtlasMixin
from src.mri.viewer_trajectory import TrajectoryMixin

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


class TriplanarMRIViewer(PanelsMixin, DisplayMixin, CropMixin, ChamberMixin,
                         CorrectionMixin, AtlasMixin, TrajectoryMixin):
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

        # Chamber correction
        self.chamber_correction = np.eye(4)
        self.chamber_corr_config = None
        self.chamber_corr_json_path = None
        self._base_screws_ebz = None  # raw screws from monkey_specific.py, before chamber correction

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

    def _chamber_corr_json_for(self, fn):
        return os.path.splitext(fn)[0] + "_chamber_corrections.json"

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
