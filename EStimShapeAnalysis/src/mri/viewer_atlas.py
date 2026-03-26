import os
import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from src.mri.atlas import load_atlas, load_atlas_labels, reslice_atlas, draw_atlas_contours, atlas_label_at_cursor, atlas_label_detail, load_template_mri, reslice_template_mri
from src.mri.correction import rot_x, rot_y, rot_z, xlate, load_corrections, save_corrections, push_correction

class AtlasMixin:
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
        """Hotkey 'T' snaps blend between 0 -> 0.5 -> 1.0 -> 0."""
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
            # Extract effective scale factors (singular values of the 3x3 sub-matrix)
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
