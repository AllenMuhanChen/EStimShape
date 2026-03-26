import numpy as np
import tkinter as tk
from tkinter import ttk, messagebox
from src.mri.volume import reslice_view
from src.mri.chamber import draw_chamber_overlay, calc_target_angles
from src.mri.atlas import reslice_atlas, draw_atlas_contours, atlas_label_at_cursor, atlas_label_detail, reslice_template_mri
from src.mri.correction import save_crop_bounds, save_corrections

_TIP_TO_BOTTOM_CH_UM = 600   # μm from probe tip to bottommost channel
_CH_SPACING_UM = 65           # μm between adjacent channels

class DisplayMixin:
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

            # EBZ -- always at (0,0) in EBZ-relative display space
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

            # Apply zoom -- restricts the visible window WITHOUT changing what was resliced
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
            self._pan_start = (event.x, event.y)  # pixel coords (stable during drag)
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
                px, py = event.x, event.y
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
                        status += f"   Az={az_h:.1f} El={el_h:.1f} Dist={dist_h:.1f}mm"
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
            self.ebz_pick_label_var.set("EBZ PICK ACTIVE -- right-click to set, or click button to cancel")
            self.btn_ebz_pick.config(text="Cancel EBZ Pick")
            if self.crop_mode:
                self._exit_crop_mode()

    def _disarm_ebz_pick(self):
        self.ebz_pick_armed = False
        self.ebz_pick_label_var.set("")
        self.btn_ebz_pick.config(text="Pick EBZ (right-click)")

    # ================================================================ Cropping
