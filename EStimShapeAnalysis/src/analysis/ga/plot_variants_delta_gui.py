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

# Width (px) of the response-colored border drawn around each thumbnail in the
# final, already-downscaled image.
THUMB_BORDER = 6


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
        # StimSpecId -> thumbnail path / generation id, refreshed on recompute.
        self.thumb_map: dict[int, str] = {}
        self.gen_map: dict[int, int] = {}
        # Manual include/exclude decisions keyed by delta StimSpecId. Re-applied
        # after a recompute so changing channel/baseline doesn't wipe curation.
        self.manual_overrides: dict[int, bool] = {}
        # Keep PhotoImage references alive (Tk drops images that are GC'd).
        self._photo_refs: list[ImageTk.PhotoImage] = []
        # Cache of raw PIL images by path to avoid re-reading from disk.
        self._image_cache: dict[str, Image.Image] = {}
        # Cache of final rendered PhotoImages keyed by (path, border_color), so a
        # sort/group change reuses photos without redoing the LANCZOS resize.
        # Cleared on recompute since vmin/vmax (and thus border colors) change.
        self._photo_cache: dict[tuple, ImageTk.PhotoImage] = {}
        # Pool of column widget sets reused across renders; resorting just
        # re-grids existing widgets instead of destroying and rebuilding them.
        self._column_pool: list[dict] = []
        self._row_labels_built = False

        self.root.title("Delta-Variant Curation")

        # --- control variables ---
        self.channel_var = tk.StringVar(value=str(default_channel))
        self.baseline_var = tk.BooleanVar(value=analysis.use_baseline_correction)
        self.delta_threshold_var = tk.StringVar(value=str(analysis.threshold))
        self.variant_threshold_var = tk.StringVar(value=str(analysis.variant_threshold))
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
                  command=self.recompute_pairs).grid(row=0, column=3, rowspan=3, padx=6, pady=2, sticky="ns")

        # Thresholds (applied on Recompute).
        thr = tk.LabelFrame(bar, text="Thresholds", font=("Arial", 10, "bold"))
        thr.pack(side="left", padx=4, fill="y")
        tk.Label(thr, text="Delta (ratio <):").grid(row=0, column=0, padx=4, pady=2, sticky="w")
        tk.Entry(thr, textvariable=self.delta_threshold_var, width=8).grid(row=0, column=1, padx=4, pady=2)
        tk.Label(thr, text="Variant (frac of max):").grid(row=1, column=0, padx=4, pady=2, sticky="w")
        tk.Entry(thr, textvariable=self.variant_threshold_var, width=8).grid(row=1, column=1, padx=4, pady=2)
        tk.Label(thr, text="applied on Recompute", font=("Arial", 7),
                 fg="gray").grid(row=2, column=0, columnspan=2, sticky="w", padx=4)

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

        try:
            self.analysis.threshold = float(self.delta_threshold_var.get())
            self.analysis.variant_threshold = float(self.variant_threshold_var.get())
        except ValueError:
            messagebox.showwarning("Invalid threshold",
                                   "Delta and variant thresholds must be numbers.")
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

        info = prepared.data.drop_duplicates("StimSpecId").set_index("StimSpecId")
        self.thumb_map = info["ThumbnailPath"].to_dict()
        self.gen_map = info["GenId"].to_dict() if "GenId" in info.columns else {}

        # If the DB already has curated pairs, it is the source of truth: a pair
        # is included only if it appears in the DB with included=TRUE (matched on
        # the full delta+variant pair). Otherwise we keep the ratio-threshold
        # default that compute_pairs produced.
        db_map = self._read_db_included()
        if db_map:
            self._apply_db_authoritative(pairs, db_map)

        # Manual overrides made during this session win over the default.
        for (delta_id, variant_id), included in self.manual_overrides.items():
            mask = ((pairs["StimSpecId"] == delta_id)
                    & (pairs["PairedVariantId"] == variant_id))
            if mask.any():
                pairs.loc[mask, "Included"] = included

        self.pairs = pairs.reset_index(drop=True)
        # vmin/vmax (and thus border colors) may have changed, so cached
        # PhotoImages are stale.
        self._photo_cache.clear()
        self._photo_refs.clear()
        self.render()
        if db_map:
            self.status_var.set(self.status_var.get() + "   (defaults from DB)")

    def _read_db_included(self):
        """Return {(delta_id, variant_id): included} from IncludedDeltas, or None.

        Keyed by the full pair so a delta paired with a different variant in the
        DB than in the current computation does not inherit that included flag.
        """
        try:
            db = self.analysis._read_deltas_from_db()
        except Exception:
            return None
        if db is None or db.empty:
            return None
        return {
            (int(r["StimSpecId"]), int(r["PairedVariantId"])): bool(r["Included"])
            for _, r in db.iterrows()
        }

    def _apply_db_authoritative(self, df, db_map):
        """Set ``Included`` so it is True only for pairs the DB marks included=TRUE.

        Every other pair (excluded in the DB, or absent from it) is set False.
        Matches on the full (delta, variant) pair.
        """
        df["Included"] = False
        for (delta_id, variant_id), included in db_map.items():
            if not included:
                continue
            mask = ((df["StimSpecId"] == delta_id)
                    & (df["PairedVariantId"] == variant_id))
            df.loc[mask, "Included"] = True

    def load_from_db(self):
        """Set the checkboxes to exactly the DB's included=TRUE pairs.

        This is authoritative: any pair not marked included in the DB (whether
        stored as excluded or simply absent) is unchecked. Discards in-session
        manual overrides so the displayed state matches the DB exactly.
        """
        if self.pairs is None:
            messagebox.showwarning("No pairs", "Compute pairs first.")
            return
        db_map = self._read_db_included()
        if not db_map:
            messagebox.showinfo("Load from DB", "No data found in the IncludedDeltas table.")
            return
        self.manual_overrides.clear()
        self._apply_db_authoritative(self.pairs, db_map)
        n_included = int(self.pairs["Included"].sum())
        self.render()
        self.status_var.set(self.status_var.get() + f"   (loaded {n_included} included from DB)")

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
        included_first = self.included_first_var.get()
        group_variant = self.group_variant_var.get()

        by, asc = [], []
        if group_variant:
            # Keep the chosen metric as the primary ordering: position each
            # variant group by its best member under the current direction, so
            # groups flow left-to-right by metric while same-variant columns
            # stay adjacent. PairedVariantId only breaks ties between groups
            # that share the same representative value.
            group_agg = "min" if ascending else "max"
            df["_group_key"] = df.groupby("PairedVariantId")[sort_col].transform(group_agg)
            if included_first:
                # Lift any group that contains at least one included pair above
                # groups that have none; without this, the per-row Included key
                # only ever sorts within a group (PairedVariantId already
                # distinguishes groups), so "Included first" silently no-ops.
                df["_group_has_included"] = (
                    df.groupby("PairedVariantId")["Included"].transform("any"))
                by.append("_group_has_included")
                asc.append(False)
            by += ["_group_key", "PairedVariantId"]
            asc += [ascending, True]
        if included_first:
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
        self._photo_cache.clear()
        self._column_pool.clear()
        self._row_labels_built = False

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
        if vmax > vmin and response is not None and not pd.isna(response):
            norm = max(0.0, min(1.0, (response - vmin) / (vmax - vmin)))
        else:
            norm = 0.5
        border_color = (int(255 * norm), 0, 0)  # black -> red intensity
        key = (path, border_color)
        cached = self._photo_cache.get(key)
        if cached is not None:
            return cached
        try:
            # Cache the image already downscaled to its final inner size, NOT at
            # full resolution. With many stimuli, caching full-res PIL images
            # (and LANCZOS-resizing each) costs gigabytes and swaps the machine
            # to a crawl; the inner-sized base is ~100x smaller and is resized
            # only once per path.
            inner = max(1, self.thumb_size - 2 * THUMB_BORDER)
            base = self._image_cache.get(path)
            if base is None:
                with Image.open(path) as im:
                    base = im.convert("RGB").resize((inner, inner), Image.LANCZOS)
                self._image_cache[path] = base
            img = ImageOps.expand(base, border=THUMB_BORDER, fill=border_color)
            photo = ImageTk.PhotoImage(img)
            self._photo_cache[key] = photo
            self._photo_refs.append(photo)
            return photo
        except Exception:
            return None

    def _ensure_row_labels(self):
        if self._row_labels_built:
            return
        tk.Label(self.grid_frame, text="Delta", font=("Arial", 11, "bold"),
                 background="white").grid(row=1, column=0, padx=4, sticky="e")
        tk.Label(self.grid_frame, text="Variant", font=("Arial", 11, "bold"),
                 background="white").grid(row=3, column=0, padx=4, sticky="e")
        self._row_labels_built = True

    def _get_column(self, idx):
        """Return (creating if needed) the widget set for column ``idx``."""
        while len(self._column_pool) <= idx:
            col = {
                "ratio": tk.Label(self.grid_frame, font=("Arial", 9, "bold"),
                                  background="white"),
                "delta_img": tk.Label(self.grid_frame, borderwidth=0,
                                      background="white"),
                "delta_info": tk.Label(self.grid_frame, font=("Arial", 8),
                                       background="white", justify="center"),
                "variant_img": tk.Label(self.grid_frame, borderwidth=0,
                                        background="white"),
                "variant_info": tk.Label(self.grid_frame, font=("Arial", 8),
                                         background="white", justify="center"),
            }
            var = tk.BooleanVar()
            col["var"] = var
            col["chk"] = tk.Checkbutton(self.grid_frame, text="include",
                                        variable=var, background="white")
            self._column_pool.append(col)
        return self._column_pool[idx]

    @staticmethod
    def _set_image_label(label, photo, fallback_text):
        if photo is not None:
            label.configure(image=photo, text="", width=0, height=0,
                            relief="flat", fg="black")
        else:
            label.configure(image="", text=fallback_text, width=18, height=8,
                            relief="groove", fg="gray")

    def render(self):
        if self.pairs is None or self.pairs.empty:
            return

        ordered = self._ordered_pairs()
        vmin, vmax = self._response_range()
        variant_max = float(self.pairs["Variant Response"].max())

        # Grid rows: 0 ratio, 1 delta image, 2 delta info, 3 variant image,
        # 4 variant info, 5 checkbox. Row labels align with the image rows.
        self._ensure_row_labels()

        # Pull column arrays once; iterrows is slow at this scale and itertuples
        # mangles the ``Delta Response`` / ``Variant Response`` names.
        sids = ordered["StimSpecId"].to_numpy()
        vids = ordered["PairedVariantId"].to_numpy()
        dresps = ordered["Delta Response"].to_numpy()
        vresps = ordered["Variant Response"].to_numpy()
        ratios = ordered["Ratio"].to_numpy()
        incs = ordered["Included"].to_numpy()

        n = len(ordered)
        for pos in range(n):
            delta_id = int(sids[pos])
            variant_id = int(vids[pos])
            d_resp = dresps[pos]
            v_resp = vresps[pos]
            ratio = float(ratios[pos])
            included = bool(incs[pos])
            pct_of_max = (100.0 * v_resp / variant_max) if variant_max else 0.0
            col = pos + 1

            widgets = self._get_column(pos)
            delta_photo = self._load_thumb(delta_id, d_resp, vmin, vmax)
            variant_photo = self._load_thumb(variant_id, v_resp, vmin, vmax)

            widgets["ratio"].configure(text=f"ratio {ratio:.2f}")
            widgets["ratio"].grid(row=0, column=col, padx=3, pady=(2, 0))

            self._set_image_label(widgets["delta_img"], delta_photo,
                                  f"delta\n{delta_id}")
            widgets["delta_img"].grid(row=1, column=col, padx=3, pady=2)

            widgets["delta_info"].configure(
                text=f"Δ {d_resp:.1f}\ngen {self._gen_label(delta_id)}\nd{delta_id}")
            widgets["delta_info"].grid(row=2, column=col, padx=3)

            self._set_image_label(widgets["variant_img"], variant_photo,
                                  f"variant\n{variant_id}")
            widgets["variant_img"].grid(row=3, column=col, padx=3, pady=2)

            widgets["variant_info"].configure(
                text=f"V {v_resp:.1f} ({pct_of_max:.0f}% max)\n"
                     f"gen {self._gen_label(variant_id)}\nv{variant_id}")
            widgets["variant_info"].grid(row=4, column=col, padx=3)

            widgets["var"].set(included)
            widgets["chk"].configure(
                command=lambda did=delta_id, vid=variant_id, v=widgets["var"]:
                    self._on_toggle(did, vid, v))
            widgets["chk"].grid(row=5, column=col, padx=3, pady=2)

        # Hide pool columns left over from a larger previous render.
        for pos in range(n, len(self._column_pool)):
            for w in self._column_pool[pos].values():
                if isinstance(w, (tk.Label, tk.Checkbutton)):
                    w.grid_forget()

        self._update_status()
        self.canvas.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_toggle(self, delta_id, variant_id, var):
        value = bool(var.get())
        mask = self._pair_mask(delta_id, variant_id)
        self.pairs.loc[mask, "Included"] = value
        self.manual_overrides[(delta_id, variant_id)] = value
        self._update_status()

    def _pair_mask(self, delta_id, variant_id):
        """Row mask matching a single (delta, variant) pair, not just the delta."""
        return ((self.pairs["StimSpecId"] == delta_id)
                & (self.pairs["PairedVariantId"] == variant_id))

    def _gen_label(self, stim_id):
        gen = self.gen_map.get(stim_id)
        if gen is None or pd.isna(gen):
            return "?"
        return str(int(gen))

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

    # Closing a window holding thousands of Tk widgets and PhotoImages (one per
    # stimulus) triggers a very slow synchronous teardown: Tk destroys every
    # widget/image one at a time, then the interpreter GCs every cached PIL/Tk
    # image during shutdown. With a lot of stimuli this pegs a core and thrashes
    # memory, freezing the machine. This GUI runs in its own subprocess whose
    # only job is the window, so on close we skip the graceful teardown entirely
    # and let the OS reclaim everything at once — an instant exit.
    root.protocol("WM_DELETE_WINDOW", lambda: os._exit(0))
    root.mainloop()


def main():
    launch(default_channel="GA")


if __name__ == "__main__":
    main()
