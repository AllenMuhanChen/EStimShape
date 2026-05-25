"""Interactive curation GUI for delta-variant pairs.

A Tkinter front-end for `PlotVariantDeltas` that replaces the
plot-then-manually-edit-the-DB workflow. It shows the same two-row layout the
static plot uses (deltas on top, paired variants on the bottom, one pair per
column), but every column carries a checkbox so pairs can be included/excluded
by hand. Sorting and grouping of the columns, the neural response source
(channel / baseline correction), and exporting the curated selection back to the
``IncludedDeltas`` table are all driven from controls at the top.

Run directly (``python -m ...`` or as a script) to launch against the current
GA context, or call `launch()` from elsewhere.
"""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import messagebox, ttk

import pandas as pd
from PIL import Image, ImageOps, ImageTk

from src.analysis.ga.plot_variants_delta import PlotVariantDeltas
from src.repository.export_to_repository import read_session_id_and_date_from_db_name
from src.startup import context

# Maps the user-facing sort option to the pairs-table column it sorts on.
SORT_COLUMNS = {
    "ratio": "Ratio",
    "delta_resp": "Delta Response",
    "variant_resp": "Variant Response",
}


class DeltaVariantCurationApp:
    """Tkinter app for curating delta-variant pairs."""

    def __init__(self, root: tk.Tk, analysis: PlotVariantDeltas,
                 compiled_data: pd.DataFrame, *, default_channel: str = "GA",
                 thumb_size: int = 140):
        self.root = root
        self.analysis = analysis
        self.compiled_data = compiled_data
        self.thumb_size = thumb_size

        # Current pair table (one row per pair). 'Included' tracks checkbox state.
        self.pairs: pd.DataFrame | None = None
        # StimSpecId -> thumbnail path, refreshed on every recompute.
        self.thumb_map: dict[int, str] = {}
        # Manual include/exclude decisions keyed by delta StimSpecId. Re-applied
        # after a recompute so changing channel/baseline doesn't wipe curation.
        self.manual_overrides: dict[int, bool] = {}
        # Keep PhotoImage references alive (Tk drops images that are GC'd).
        self._photo_refs: list[ImageTk.PhotoImage] = []
        # Cache of raw PIL images by path to avoid re-reading from disk.
        self._image_cache: dict[str, Image.Image] = {}

        self.root.title("Delta-Variant Curation")

        # --- control variables ---
        self.channel_var = tk.StringVar(value=str(default_channel))
        self.baseline_var = tk.BooleanVar(value=analysis.use_baseline_correction)
        self.sort_var = tk.StringVar(value="ratio")
        self.descending_var = tk.BooleanVar(value=False)
        self.included_first_var = tk.BooleanVar(value=True)
        self.group_variant_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Set the channel and click Recompute.")

        self._build_controls()
        self._build_plot_area()

        # Initial computation.
        self.recompute_pairs()

    # ------------------------------------------------------------------ UI
    def _build_controls(self):
        bar = tk.Frame(self.root)
        bar.pack(side="top", fill="x", padx=8, pady=6)

        # Response source.
        src = tk.LabelFrame(bar, text="Neural response", font=("Arial", 10, "bold"))
        src.pack(side="left", padx=4, fill="y")
        tk.Label(src, text="Channel:").grid(row=0, column=0, padx=4, pady=2, sticky="w")
        tk.Entry(src, textvariable=self.channel_var, width=18).grid(row=0, column=1, padx=4, pady=2)
        tk.Label(src, text='"GA", "Cluster", "A-006", or "A-000,A-006"',
                 font=("Arial", 7), fg="gray").grid(row=1, column=0, columnspan=2, sticky="w", padx=4)
        tk.Checkbutton(src, text="Baseline correction",
                       variable=self.baseline_var).grid(row=2, column=0, columnspan=2, sticky="w", padx=4)
        tk.Button(src, text="Recompute", bg="lightblue",
                  command=self.recompute_pairs).grid(row=0, column=2, rowspan=3, padx=6, pady=2, sticky="ns")

        # Ordering.
        order = tk.LabelFrame(bar, text="Ordering", font=("Arial", 10, "bold"))
        order.pack(side="left", padx=4, fill="y")
        tk.Label(order, text="Sort by:").grid(row=0, column=0, padx=4, pady=2, sticky="w")
        combo = ttk.Combobox(order, textvariable=self.sort_var, state="readonly",
                             values=list(SORT_COLUMNS.keys()), width=12)
        combo.grid(row=0, column=1, padx=4, pady=2)
        combo.bind("<<ComboboxSelected>>", lambda _e: self.render())
        tk.Checkbutton(order, text="Descending", variable=self.descending_var,
                       command=self.render).grid(row=1, column=0, columnspan=2, sticky="w", padx=4)
        tk.Checkbutton(order, text="Included first", variable=self.included_first_var,
                       command=self.render).grid(row=2, column=0, sticky="w", padx=4)
        tk.Checkbutton(order, text="Group by variant", variable=self.group_variant_var,
                       command=self.render).grid(row=2, column=1, sticky="w", padx=4)

        # Actions.
        actions = tk.LabelFrame(bar, text="Actions", font=("Arial", 10, "bold"))
        actions.pack(side="left", padx=4, fill="y")
        tk.Button(actions, text="Load from DB",
                  command=self.load_from_db).pack(side="top", padx=4, pady=2, fill="x")
        tk.Button(actions, text="Reset to threshold",
                  command=self.reset_to_threshold).pack(side="top", padx=4, pady=2, fill="x")
        tk.Button(actions, text="Export to DB", bg="lightgreen",
                  command=self.export_to_db).pack(side="top", padx=4, pady=2, fill="x")

        tk.Label(self.root, textvariable=self.status_var, anchor="w",
                 fg="gray").pack(side="top", fill="x", padx=10)

    def _build_plot_area(self):
        container = tk.Frame(self.root)
        container.pack(side="top", fill="both", expand=True, padx=6, pady=6)

        self.canvas = tk.Canvas(container, background="white")
        v_scroll = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        h_scroll = ttk.Scrollbar(container, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        v_scroll.pack(side="right", fill="y")
        h_scroll.pack(side="bottom", fill="x")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.grid_frame = tk.Frame(self.canvas, background="white")
        self.canvas.create_window((0, 0), window=self.grid_frame, anchor="nw")
        self.grid_frame.bind(
            "<Configure>",
            lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )

        # Vertical wheel; shift+wheel for horizontal.
        self.canvas.bind_all("<MouseWheel>",
                             lambda e: self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))
        self.canvas.bind_all("<Shift-MouseWheel>",
                             lambda e: self.canvas.xview_scroll(int(-1 * (e.delta / 120)), "units"))

    # ------------------------------------------------------------ data ops
    def _parse_channel(self):
        """Parse the channel entry into the form ResponseSpec expects."""
        text = self.channel_var.get().strip()
        if "," in text:
            return [c.strip() for c in text.split(",") if c.strip()]
        return text

    def recompute_pairs(self):
        """Recompute the pair table for the current channel / baseline setting,
        preserving any manual include/exclude overrides."""
        channel = self._parse_channel()
        if not channel:
            messagebox.showwarning("Channel required", "Please enter a channel.")
            return

        self.analysis.use_baseline_correction = self.baseline_var.get()
        try:
            pairs, prepared = self.analysis.compute_pairs(self.compiled_data, channel)
        except Exception as exc:  # surface ResponseSpec / data errors in the GUI
            messagebox.showerror("Recompute failed", str(exc))
            return

        if pairs is None or pairs.empty:
            self.pairs = None
            self._clear_grid()
            self.status_var.set("No delta-variant pairs found for this setting.")
            return

        self.thumb_map = (
            prepared.data.drop_duplicates("StimSpecId")
            .set_index("StimSpecId")["ThumbnailPath"].to_dict()
        )

        # Default the inclusion state to whatever is already curated in the DB;
        # pairs not present in the DB keep their ratio-threshold default.
        db_map = self._read_db_included()
        if db_map:
            for delta_id, included in db_map.items():
                mask = pairs["StimSpecId"] == delta_id
                if mask.any():
                    pairs.loc[mask, "Included"] = included

        # Manual overrides made during this session win over both.
        for delta_id, included in self.manual_overrides.items():
            mask = pairs["StimSpecId"] == delta_id
            if mask.any():
                pairs.loc[mask, "Included"] = included

        self.pairs = pairs.reset_index(drop=True)
        self.render()
        if db_map:
            self.status_var.set(self.status_var.get() + "   (defaults from DB)")

    def _read_db_included(self):
        """Return {delta_id: included} from the IncludedDeltas table, or None."""
        try:
            db = self.analysis._read_deltas_from_db()
        except Exception:
            return None
        if db is None or db.empty:
            return None
        return {int(r["StimSpecId"]): bool(r["Included"]) for _, r in db.iterrows()}

    def load_from_db(self):
        """Overwrite current checkbox states with the IncludedDeltas table."""
        if self.pairs is None:
            messagebox.showwarning("No pairs", "Compute pairs first.")
            return
        db_map = self._read_db_included()
        if not db_map:
            messagebox.showinfo("Load from DB", "No data found in the IncludedDeltas table.")
            return
        n_applied = 0
        for delta_id, included in db_map.items():
            mask = self.pairs["StimSpecId"] == delta_id
            if mask.any():
                self.pairs.loc[mask, "Included"] = included
                self.manual_overrides[delta_id] = included  # make the loaded state sticky
                n_applied += 1
        self.render()
        self.status_var.set(self.status_var.get() + f"   (loaded {n_applied} from DB)")

    def reset_to_threshold(self):
        """Discard manual overrides and restore the ratio-threshold defaults."""
        if self.pairs is None:
            return
        self.manual_overrides.clear()
        self.pairs["Included"] = self.pairs["Ratio"] < self.analysis.threshold
        self.render()

    def _ordered_pairs(self) -> pd.DataFrame:
        df = self.pairs.copy()
        sort_col = SORT_COLUMNS[self.sort_var.get()]
        ascending = not self.descending_var.get()

        by, asc = [], []
        if self.group_variant_var.get():
            # Keep the chosen metric as the primary ordering: position each
            # variant group by its best member under the current direction, so
            # groups flow left-to-right by metric while same-variant columns
            # stay adjacent. PairedVariantId only breaks ties between groups
            # that share the same representative value.
            group_agg = "min" if ascending else "max"
            df["_group_key"] = df.groupby("PairedVariantId")[sort_col].transform(group_agg)
            by += ["_group_key", "PairedVariantId"]
            asc += [ascending, True]
        if self.included_first_var.get():
            by.append("Included")
            asc.append(False)  # True (included) sorts first
        by.append(sort_col)
        asc.append(ascending)
        return df.sort_values(by=by, ascending=asc, kind="stable")

    def export_to_db(self):
        if self.pairs is None or self.pairs.empty:
            messagebox.showwarning("Nothing to export", "Compute pairs first.")
            return
        n_total = len(self.pairs)
        n_included = int(self.pairs["Included"].sum())
        if not messagebox.askyesno(
            "Export to IncludedDeltas",
            f"Replace the IncludedDeltas table with {n_total} pairs "
            f"({n_included} included, {n_total - n_included} excluded)?",
        ):
            return
        try:
            ok = self.analysis._save_deltas_to_db(self.pairs, skip_prompt=True)
        except Exception as exc:
            messagebox.showerror("Export failed", str(exc))
            return
        if ok:
            messagebox.showinfo("Exported",
                                f"Saved {n_total} pairs ({n_included} included) to IncludedDeltas.")

    # ------------------------------------------------------------- rendering
    def _clear_grid(self):
        for child in self.grid_frame.winfo_children():
            child.destroy()
        self._photo_refs.clear()

    def _response_range(self):
        vals = pd.concat([self.pairs["Delta Response"], self.pairs["Variant Response"]])
        vals = vals.dropna()
        if vals.empty:
            return 0.0, 1.0
        return float(vals.min()), float(vals.max())

    def _load_thumb(self, stim_id, response, vmin, vmax):
        path = self.thumb_map.get(stim_id)
        if not path or not os.path.exists(path):
            return None
        try:
            base = self._image_cache.get(path)
            if base is None:
                base = Image.open(path).convert("RGB")
                self._image_cache[path] = base
            if vmax > vmin and response is not None and not pd.isna(response):
                norm = max(0.0, min(1.0, (response - vmin) / (vmax - vmin)))
            else:
                norm = 0.5
            border_color = (int(255 * norm), 0, 0)  # black -> red intensity
            img = ImageOps.expand(base, border=20, fill=border_color)
            img = img.resize((self.thumb_size, self.thumb_size), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self._photo_refs.append(photo)
            return photo
        except Exception:
            return None

    def _make_image_cell(self, parent, photo, fallback_text):
        if photo is not None:
            return tk.Label(parent, image=photo, borderwidth=0, background="white")
        return tk.Label(parent, text=fallback_text, width=18, height=8,
                        relief="groove", background="white", fg="gray")

    def render(self):
        if self.pairs is None or self.pairs.empty:
            return
        self._clear_grid()

        ordered = self._ordered_pairs()
        vmin, vmax = self._response_range()

        # Row labels.
        tk.Label(self.grid_frame, text="Delta", font=("Arial", 11, "bold"),
                 background="white").grid(row=0, column=0, padx=4, sticky="e")
        tk.Label(self.grid_frame, text="Variant", font=("Arial", 11, "bold"),
                 background="white").grid(row=1, column=0, padx=4, sticky="e")

        for pos, (_, pair) in enumerate(ordered.iterrows()):
            col = pos + 1
            delta_id = int(pair["StimSpecId"])
            variant_id = int(pair["PairedVariantId"])
            d_resp = pair["Delta Response"]
            v_resp = pair["Variant Response"]
            ratio = pair["Ratio"]

            delta_photo = self._load_thumb(delta_id, d_resp, vmin, vmax)
            variant_photo = self._load_thumb(variant_id, v_resp, vmin, vmax)

            self._make_image_cell(self.grid_frame, delta_photo, f"delta\n{delta_id}").grid(
                row=0, column=col, padx=3, pady=2)
            self._make_image_cell(self.grid_frame, variant_photo, f"variant\n{variant_id}").grid(
                row=1, column=col, padx=3, pady=2)

            info = (f"ratio {ratio:.2f}\n"
                    f"Δ {d_resp:.1f}  V {v_resp:.1f}\n"
                    f"d{delta_id}\nv{variant_id}")
            tk.Label(self.grid_frame, text=info, font=("Arial", 8),
                     background="white", justify="center").grid(row=2, column=col, padx=3)

            var = tk.BooleanVar(value=bool(pair["Included"]))
            chk = tk.Checkbutton(
                self.grid_frame, text="include", variable=var, background="white",
                command=lambda did=delta_id, v=var: self._on_toggle(did, v),
            )
            chk.grid(row=3, column=col, padx=3, pady=2)

        self._update_status()
        self.canvas.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_toggle(self, delta_id, var):
        value = bool(var.get())
        self.pairs.loc[self.pairs["StimSpecId"] == delta_id, "Included"] = value
        self.manual_overrides[delta_id] = value
        self._update_status()

    def _update_status(self):
        n_total = len(self.pairs)
        n_included = int(self.pairs["Included"].sum())
        channel = self.channel_var.get().strip()
        baseline = " (baseline-corrected)" if self.baseline_var.get() else ""
        self.status_var.set(
            f"Channel: {channel}{baseline}   |   "
            f"{n_total} pairs, {n_included} included, {n_total - n_included} excluded"
        )


def launch(default_channel: str = "GA", *, delta_threshold: float = 0.6,
           variant_threshold: float = 0.4, use_baseline_correction: bool = False):
    """Load GA data for the current context and open the curation GUI."""
    analysis = PlotVariantDeltas(
        to_save_to_db=False,
        delta_threshold=delta_threshold,
        variant_threshold=variant_threshold,
        use_baseline_correction=use_baseline_correction,
    )
    session_id, _ = read_session_id_and_date_from_db_name(context.ga_database)
    analysis.session_id = session_id
    # Always load raw per-channel responses so the channel can be switched in
    # the GUI without re-importing; 'GA Response' rides along on the stim info.
    analysis.parse_data_type("raw", session_id=session_id)
    compiled_data = analysis.import_data(None)

    root = tk.Tk()
    root.geometry("1400x800")
    DeltaVariantCurationApp(root, analysis, compiled_data, default_channel=default_channel)
    root.mainloop()


def main():
    launch(default_channel="GA")


if __name__ == "__main__":
    main()
