import numpy as np
import tkinter as tk
from tkinter import ttk
from src.mri.correction import rot_x, rot_y, rot_z, xlate, load_corrections, save_corrections, push_correction

class CorrectionMixin:
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
