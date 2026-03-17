"""
GUI tool to import a penetration into the Penetrations table.

Distance correction:
    The input distance is measured to the probe tip. Each channel sits above the tip:
      - 600 μm from tip to the bottommost channel (ch 17, index 31)
      - 65 μm spacing between adjacent channels
    So for a given channel at position `idx` in channel_order:
      corrected_dist = tip_dist - (600 + (31 - idx) * 65) / 1000  [mm]
"""

import tkinter as tk
from tkinter import ttk, messagebox
import time
import mysql.connector

CHANNEL_ORDER = [
    7, 8, 25, 22, 0, 15, 24, 23, 6, 9, 26, 21, 5, 10, 31, 16,
    27, 20, 4, 11, 28, 19, 1, 14, 3, 12, 29, 18, 2, 13, 30, 17
]

TIP_TO_BOTTOM_CHANNEL_UM = 600
CHANNEL_SPACING_UM = 65

DB_HOST = "172.30.6.61"
DB_NAME = "allen_data_repository"
DB_USER = "xper_rw"
DB_PASS = "up2nite"

COLORS = ['cyan', 'yellow', 'magenta', 'orange', 'lime', 'deepskyblue',
          'red', 'white', 'pink', 'gold']


def channel_offset_um(channel_num):
    if channel_num not in CHANNEL_ORDER:
        raise ValueError(f"Channel {channel_num} not in channel order")
    idx = CHANNEL_ORDER.index(channel_num)
    bottom_idx = 31
    steps_from_bottom = bottom_idx - idx
    return TIP_TO_BOTTOM_CHANNEL_UM + steps_from_bottom * CHANNEL_SPACING_UM


def corrected_distance(tip_dist_mm, channel_num):
    offset_mm = channel_offset_um(channel_num) / 1000.0
    return tip_dist_mm - offset_mm


def insert_penetration(az_deg, el_deg, dist_mm, label, color="cyan", notes=""):
    conn = mysql.connector.connect(
        host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS, autocommit=True
    )
    cursor = conn.cursor()
    tstamp = int(time.time() * 1000)
    cursor.execute(
        "INSERT INTO Penetrations (tstamp, label, az_deg, el_deg, dist_mm, color, visible, notes) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        (tstamp, label, az_deg, el_deg, dist_mm, color, 1, notes),
    )
    pen_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return pen_id


class ImportPenetrationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Import Penetration")
        self.root.resizable(False, False)

        self._build_ui()
        self._update_preview()

    def _build_ui(self):
        pad = dict(padx=8, pady=4)

        # ── Probe parameters ──────────────────────────────────────────────
        probe_frame = ttk.LabelFrame(self.root, text="Probe Parameters")
        probe_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(10, 4))

        ttk.Label(probe_frame, text="Azimuth (°):").grid(row=0, column=0, sticky="w", **pad)
        self.az_var = tk.DoubleVar(value=0.0)
        ttk.Entry(probe_frame, textvariable=self.az_var, width=12).grid(row=0, column=1, sticky="w", **pad)

        ttk.Label(probe_frame, text="Elevation (°):").grid(row=1, column=0, sticky="w", **pad)
        self.el_var = tk.DoubleVar(value=0.0)
        ttk.Entry(probe_frame, textvariable=self.el_var, width=12).grid(row=1, column=1, sticky="w", **pad)

        ttk.Label(probe_frame, text="Tip distance (mm):").grid(row=2, column=0, sticky="w", **pad)
        self.dist_var = tk.DoubleVar(value=35.0)
        dist_entry = ttk.Entry(probe_frame, textvariable=self.dist_var, width=12)
        dist_entry.grid(row=2, column=1, sticky="w", **pad)
        self.dist_var.trace_add("write", lambda *_: self._update_preview())

        ttk.Label(probe_frame, text="Channel:").grid(row=3, column=0, sticky="w", **pad)
        self.channel_var = tk.IntVar(value=0)
        channel_cb = ttk.Combobox(
            probe_frame, textvariable=self.channel_var,
            values=sorted(CHANNEL_ORDER), width=10, state="readonly"
        )
        channel_cb.grid(row=3, column=1, sticky="w", **pad)
        channel_cb.set(0)
        self.channel_var.trace_add("write", lambda *_: self._update_preview())

        # ── Session / label ───────────────────────────────────────────────
        meta_frame = ttk.LabelFrame(self.root, text="Label & Appearance")
        meta_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=4)

        ttk.Label(meta_frame, text="Session ID (label):").grid(row=0, column=0, sticky="w", **pad)
        self.session_var = tk.StringVar()
        ttk.Entry(meta_frame, textvariable=self.session_var, width=24).grid(row=0, column=1, sticky="w", **pad)

        ttk.Label(meta_frame, text="Color:").grid(row=1, column=0, sticky="w", **pad)
        self.color_var = tk.StringVar(value="cyan")
        color_cb = ttk.Combobox(meta_frame, textvariable=self.color_var,
                                values=COLORS, width=14, state="readonly")
        color_cb.grid(row=1, column=1, sticky="w", **pad)

        ttk.Label(meta_frame, text="Notes:").grid(row=2, column=0, sticky="w", **pad)
        self.notes_var = tk.StringVar()
        ttk.Entry(meta_frame, textvariable=self.notes_var, width=36).grid(
            row=2, column=1, columnspan=3, sticky="ew", **pad)

        # ── Preview ───────────────────────────────────────────────────────
        prev_frame = ttk.LabelFrame(self.root, text="Distance Correction Preview")
        prev_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=4)

        self.preview_var = tk.StringVar(value="—")
        ttk.Label(prev_frame, textvariable=self.preview_var, foreground="#006699",
                  font=("Courier", 10)).grid(row=0, column=0, sticky="w", padx=10, pady=6)

        # ── Status ────────────────────────────────────────────────────────
        self.status_var = tk.StringVar(value="")
        ttk.Label(self.root, textvariable=self.status_var, foreground="green").grid(
            row=3, column=0, columnspan=2, sticky="w", padx=12, pady=(2, 0))

        # ── Buttons ───────────────────────────────────────────────────────
        btn_frame = ttk.Frame(self.root)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=(6, 12))
        ttk.Button(btn_frame, text="Insert Penetration", command=self._insert).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_frame, text="Clear", command=self._clear).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_frame, text="Quit", command=self.root.destroy).pack(side=tk.LEFT, padx=6)

    def _update_preview(self, *_):
        try:
            tip = self.dist_var.get()
            ch = int(self.channel_var.get())
            offset_um = channel_offset_um(ch)
            corrected = corrected_distance(tip, ch)
            idx = CHANNEL_ORDER.index(ch)
            self.preview_var.set(
                f"Channel {ch}  |  probe index {idx}  |  offset {offset_um} μm ({offset_um/1000:.3f} mm)\n"
                f"Tip dist: {tip:.3f} mm  →  Corrected dist: {corrected:.3f} mm"
            )
        except Exception:
            self.preview_var.set("—")

    def _insert(self):
        # Validate
        try:
            az = float(self.az_var.get())
            el = float(self.el_var.get())
            tip = float(self.dist_var.get())
        except (ValueError, tk.TclError):
            messagebox.showerror("Input Error", "Az, El, and Tip distance must be numbers.")
            return

        session = self.session_var.get().strip()
        if not session:
            messagebox.showerror("Input Error", "Session ID / label is required.")
            return

        try:
            ch = int(self.channel_var.get())
        except ValueError:
            messagebox.showerror("Input Error", "Select a valid channel.")
            return

        offset_um = channel_offset_um(ch)
        dist_corrected = corrected_distance(tip, ch)
        color = self.color_var.get()
        extra_notes = self.notes_var.get().strip()


        # Confirm
        msg = (
            f"Insert penetration?\n\n"
            f"  Label:      {session}\n"
            f"  Az / El:    {az}° / {el}°\n"
            f"  Tip dist:   {tip:.3f} mm\n"
            f"  Corrected:  {dist_corrected:.3f} mm\n"
            f"  Channel:    {ch}  (offset {offset_um} μm)\n"
            f"  Color:      {color}\n"
            f"  Notes:      {extra_notes}"
        )
        if not messagebox.askyesno("Confirm Insert", msg):
            return

        try:
            pen_id = insert_penetration(
                az_deg=az, el_deg=el, dist_mm=dist_corrected,
                label=session, color=color, notes=extra_notes
            )
            self.status_var.set(f"✓ Inserted penetration id={pen_id}")
        except Exception as e:
            messagebox.showerror("DB Error", str(e))

    def _clear(self):
        self.az_var.set(0.0)
        self.el_var.set(0.0)
        self.dist_var.set(35.0)
        self.channel_var.set(0)
        self.session_var.set("")
        self.color_var.set("cyan")
        self.notes_var.set("")
        self.status_var.set("")
        self._update_preview()


def main():
    root = tk.Tk()
    app = ImportPenetrationApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()