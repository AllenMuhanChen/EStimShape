"""
Delta-variant curation: the explorer (PyQt) version of plot_variants_delta_gui.

Same behaviour as the Tkinter DeltaVariantCurationApp: deltas on top, the
variant (parent) each was made from underneath, one pair per column, an
"include" checkbox per pair; sort / group the columns; recompute pairs for any
channel / baseline / thresholds; load, reset and export the curation to the
session's IncludedDeltas table. The pair maths and DB reads/writes are reused
from PlotVariantDeltas, so both GUIs agree.

Differences from the Tkinter version:
  - Controls live in the explorer's side panel; switching session there swaps
    the whole curation to that session's GA database (manual include/exclude
    clicks are per session and are dropped on a switch, so export first).
  - Export names the session and database it will overwrite before asking.
"""

from __future__ import annotations

import os

import numpy as np
import pandas as pd
from PIL import Image, ImageOps
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (QCheckBox, QGridLayout, QLabel, QMessageBox,
                             QScrollArea, QWidget)

from src.analysis.ga.explorer.explorer_module import Action, ExplorerModule, Param
from src.analysis.ga.explorer.ga_data import (DATA_TYPES, load_ga_repository_data,
                                              parse_channel)
from src.startup import context

# Maps the user-facing sort option to the pairs-table column it sorts on.
SORT_COLUMNS = {
    "ratio": "Ratio",
    "delta_resp": "Delta Response",
    "variant_resp": "Variant Response",
}

# Width (px) of the response-colored border drawn around each thumbnail.
THUMB_BORDER = 6

# Component-index -> RGB color used by the Java comp-map renderer
# (AllenMatchStick.drawSkeleton's colorCode, 1-indexed). Same as the Tk GUI.
COMP_COLORS = {
    1: (255, 255, 255),
    2: (255, 0, 0),
    3: (0, 255, 0),
    4: (0, 0, 255),
    5: (0, 255, 255),
    6: (255, 0, 255),
    7: (255, 255, 0),
    8: (102, 26, 153),
}
OVERLAY_COLOR = (255, 0, 0)
OVERLAY_ALPHA = 0.45
NOISE_RING_COLOR = (255, 0, 0)

# Parameters whose change means the pair table must be recomputed (the rest
# only re-render).
RECOMPUTE_KEYS = {"data_type", "channel", "baseline", "delta_threshold", "variant_threshold"}


# ---------------------------------------------------------------------------
# Thumbnails (PIL side; mirrors the Tk GUI's _load_thumb helpers)
# ---------------------------------------------------------------------------

class ThumbnailRenderer:
    """Builds bordered (optionally comp-highlighted) thumbnails as QPixmaps,
    with the same caches as the Tk GUI so re-sorting is cheap."""

    def __init__(self):
        self.thumb_size = 140
        self._image_cache: dict[str, Image.Image] = {}
        self._compmap_cache: dict[str, object] = {}
        self._pixmap_cache: dict[tuple, QPixmap] = {}

    def clear(self, keep_images=True):
        self._pixmap_cache.clear()
        if not keep_images:
            self._image_cache.clear()
            self._compmap_cache.clear()

    def set_size(self, size):
        if size != self.thumb_size:
            self.thumb_size = size
            self.clear(keep_images=False)

    @property
    def inner(self):
        return max(1, self.thumb_size - 2 * THUMB_BORDER)

    @staticmethod
    def compmap_path(thumb_path):
        if thumb_path.endswith("_thumbnail.png"):
            return thumb_path[:-len("_thumbnail.png")] + "_compmap_thumbnail.png"
        if thumb_path.endswith(".png"):
            return thumb_path[:-4] + "_compmap_thumbnail.png"
        return None

    def _compmap_inner(self, thumb_path):
        cached = self._compmap_cache.get(thumb_path)
        if cached is not None:
            return cached or None
        cm_path = self.compmap_path(thumb_path)
        if not cm_path or not os.path.exists(cm_path):
            self._compmap_cache[thumb_path] = False
            return None
        try:
            with Image.open(cm_path) as im:
                img = im.convert("RGB").resize((self.inner, self.inner), Image.NEAREST)
        except Exception:
            self._compmap_cache[thumb_path] = False
            return None
        self._compmap_cache[thumb_path] = img
        return img

    def _hypothesized_mask(self, thumb_path, comps):
        wanted = [c for c in comps if 1 <= c <= 8]
        if not wanted:
            return None
        comp_img = self._compmap_inner(thumb_path)
        if comp_img is None:
            return None
        # int32: squared color differences overflow int16.
        arr = np.asarray(comp_img, dtype=np.int32)
        corners = np.stack([arr[0, 0], arr[0, -1], arr[-1, 0], arr[-1, -1]])
        bg = np.median(corners, axis=0)
        targets = np.asarray([bg] + [COMP_COLORS[i] for i in range(1, 9)], dtype=np.int32)
        diff = arr[:, :, None, :] - targets[None, None, :, :]
        nearest = (diff * diff).sum(axis=3).argmin(axis=2)
        return np.isin(nearest, wanted)

    def _noise_ring_mask(self, thumb_path):
        comp_img = self._compmap_inner(thumb_path)
        if comp_img is None:
            return None
        arr = np.asarray(comp_img, dtype=np.int32)
        r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
        return (r > 200) & (g > 30) & (g < 150) & (b < 80)

    def pixmap(self, path, response, vmin, vmax, overlay_comps=None):
        if not path or not os.path.exists(path):
            return None
        if vmax > vmin and response is not None and not pd.isna(response):
            norm = max(0.0, min(1.0, (response - vmin) / (vmax - vmin)))
        else:
            norm = 0.5
        border_color = (int(255 * norm), 0, 0)  # black -> red intensity
        overlay_comps = tuple(overlay_comps) if overlay_comps else ()
        key = (path, border_color, overlay_comps)
        cached = self._pixmap_cache.get(key)
        if cached is not None:
            return cached
        try:
            base = self._image_cache.get(path)
            if base is None:
                with Image.open(path) as im:
                    base = im.convert("RGB").resize((self.inner, self.inner), Image.LANCZOS)
                self._image_cache[path] = base
            img = base
            if overlay_comps:
                mask = self._hypothesized_mask(path, overlay_comps)
                if mask is not None and mask.any():
                    overlay = Image.new("RGB", base.size, OVERLAY_COLOR)
                    alpha = Image.fromarray((mask * int(255 * OVERLAY_ALPHA)).astype("uint8"), mode="L")
                    img = Image.composite(overlay, base, alpha)
                ring = self._noise_ring_mask(path)
                if ring is not None and ring.any():
                    ring_img = Image.new("RGB", img.size, NOISE_RING_COLOR)
                    ring_alpha = Image.fromarray((ring * 255).astype("uint8"), mode="L")
                    img = Image.composite(ring_img, img, ring_alpha)
            img = ImageOps.expand(img, border=THUMB_BORDER, fill=border_color)
            pix = pil_to_pixmap(img)
            self._pixmap_cache[key] = pix
            return pix
        except Exception:
            return None


def pil_to_pixmap(img: Image.Image) -> QPixmap:
    img = img.convert("RGB")
    w, h = img.size
    qimg = QImage(img.tobytes("raw", "RGB"), w, h, 3 * w, QImage.Format_RGB888)
    return QPixmap.fromImage(qimg.copy())


# ---------------------------------------------------------------------------
# The grid widget
# ---------------------------------------------------------------------------

class DeltaGridView(QScrollArea):
    """Scrollable grid: row 0 ratio, 1 delta image, 2 delta info, 3 variant
    image, 4 variant info, 5 include checkbox. Column widgets are pooled and
    re-gridded on re-sort instead of being rebuilt."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.inner = QWidget()
        self.inner.setStyleSheet("background: white;")
        self.grid = QGridLayout(self.inner)
        self.grid.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.grid.setHorizontalSpacing(6)
        self.grid.setVerticalSpacing(2)
        self.setWidget(self.inner)
        self.pool: list[dict] = []

        self.message = QLabel("")
        self.message.setStyleSheet("color: gray; font-size: 16px;")
        self.grid.addWidget(self.message, 0, 0, 1, 1)
        for row, text in ((1, "Delta"), (3, "Variant")):
            lbl = QLabel(text)
            lbl.setStyleSheet("font-weight: bold; font-size: 14px;")
            lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.grid.addWidget(lbl, row, 0)

    def column(self, idx):
        while len(self.pool) <= idx:
            col = {
                "ratio": QLabel(),
                "delta_img": QLabel(),
                "delta_info": QLabel(),
                "variant_img": QLabel(),
                "variant_info": QLabel(),
                "chk": QCheckBox("include"),
            }
            col["ratio"].setStyleSheet("font-weight: bold; font-size: 12px;")
            for k in ("delta_info", "variant_info"):
                col[k].setStyleSheet("font-size: 11px;")
            for k in ("ratio", "delta_img", "delta_info", "variant_img", "variant_info"):
                col[k].setAlignment(Qt.AlignCenter)
            col["handler"] = None
            self.pool.append(col)
        return self.pool[idx]

    def hide_from(self, n):
        for col in self.pool[n:]:
            for key, w in col.items():
                if isinstance(w, QWidget):
                    w.hide()


# ---------------------------------------------------------------------------
# The module
# ---------------------------------------------------------------------------

class DeltaCurationModule(ExplorerModule):
    name = "Delta-variant curation"
    description = ("Pairs every delta with the variant it was made from; tick which "
                   "pairs to keep and export them to IncludedDeltas.")

    def __init__(self):
        super().__init__()
        self.view: DeltaGridView | None = None
        self.analysis = None
        self.pairs: pd.DataFrame | None = None
        self.thumb_map: dict = {}
        self.gen_map: dict = {}
        self.hypothesized_map: dict = {}
        self.manual_overrides: dict = {}
        self.values: dict = {}
        self.thumbs = ThumbnailRenderer()

    # -- declaration ------------------------------------------------------
    def params(self):
        return [
            Param("data_type", "Data type", "choice", "mua", choices=DATA_TYPES,
                  tooltip="Responses imported from the repository. 'GA' forces channel GA."),
            Param("channel", "Channel", "str", "GA",
                  tooltip='"GA", "Cluster", "A-006", or "A-000,A-006" (summed)'),
            Param("baseline", "Baseline correction", "bool", False),
            Param("delta_threshold", "Delta threshold (ratio <)", "float", 0.6,
                  minimum=0.0, maximum=10.0, step=0.05),
            Param("variant_threshold", "Variant threshold (frac of max)", "float", 0.4,
                  minimum=0.0, maximum=1.0, step=0.05),
            Param("sort_by", "Sort by", "choice", "ratio", choices=list(SORT_COLUMNS), live=True),
            Param("descending", "Descending", "bool", False, live=True),
            Param("included_first", "Included first", "bool", True, live=True),
            Param("group_variant", "Group by variant", "bool", False, live=True),
            Param("show_comps", "Hypothesized comps overlay", "bool", True, live=True,
                  tooltip="Red overlay on the delta's hypothesized component "
                          "(needs comp-map thumbnails)."),
            Param("thumb_size", "Thumbnail size (px)", "int", 140, minimum=60, maximum=400,
                  step=10, live=True),
        ]

    def actions(self):
        return [
            Action("Load from DB", self.load_from_db,
                   "Tick exactly the pairs IncludedDeltas marks included."),
            Action("Reset to threshold", self.reset_to_threshold,
                   "Drop manual ticks; include pairs with ratio < delta threshold."),
            Action("Export to DB", self.export_to_db,
                   "Replace this session's IncludedDeltas table with the current ticks.",
                   color="lightgreen"),
        ]

    # -- lifecycle ----------------------------------------------------------
    def create_view(self, parent):
        self.view = DeltaGridView(parent)
        return self.view

    def set_session(self, session):
        super().set_session(session)
        from src.analysis.ga.plot_variants_delta import PlotVariantDeltas
        self.analysis = PlotVariantDeltas(to_save_to_db=False)
        self.pairs = None
        self.manual_overrides = {}
        self.thumbs.clear(keep_images=False)

    def refresh(self, values, changed=None):
        self.values = dict(values)
        self.thumbs.set_size(values["thumb_size"])
        if changed is None or self.pairs is None or (changed & RECOMPUTE_KEYS):
            self.recompute_pairs()
        else:
            self.render()

    # -- data ops -----------------------------------------------------------
    def recompute_pairs(self):
        v = self.values
        data_type = v["data_type"]
        channel = "GA" if data_type == "GA" else parse_channel(v["channel"])
        if not channel:
            self._show_message("Enter a channel.")
            return
        compiled_data, spike_rates_col = load_ga_repository_data(self.session, data_type)

        a = self.analysis
        a.session_id = self.session.session_id
        a.spike_rates_col = spike_rates_col
        a.threshold = float(v["delta_threshold"])
        a.variant_threshold = float(v["variant_threshold"])
        a.use_baseline_correction = bool(v["baseline"])
        pairs, prepared = a.compute_pairs(compiled_data, channel)

        if pairs is None or pairs.empty:
            self.pairs = None
            self._show_message("No delta-variant pairs found for this setting.")
            return

        info = prepared.data.drop_duplicates("StimSpecId").set_index("StimSpecId")
        self.thumb_map = info["ThumbnailPath"].to_dict()
        self.gen_map = info["GenId"].to_dict() if "GenId" in info.columns else {}

        # DB curation, when present, is the default; manual ticks win over it.
        db_map = self._read_db_included()
        if db_map:
            self._apply_db_authoritative(pairs, db_map)
        for (delta_id, variant_id), included in self.manual_overrides.items():
            mask = (pairs["StimSpecId"] == delta_id) & (pairs["PairedVariantId"] == variant_id)
            if mask.any():
                pairs.loc[mask, "Included"] = included

        self.pairs = pairs.reset_index(drop=True)
        self.hypothesized_map = self._load_hypothesized_comps(self.pairs["StimSpecId"].unique())
        self.thumbs.clear()  # border colors depend on the new response range
        self.render()
        if db_map:
            self.status(self._summary() + "   (defaults from DB)")

    def _read_db_included(self):
        try:
            db = self.analysis._read_deltas_from_db()
        except Exception:
            return None
        if db is None or db.empty:
            return None
        return {(int(r["StimSpecId"]), int(r["PairedVariantId"])): bool(r["Included"])
                for _, r in db.iterrows()}

    @staticmethod
    def _apply_db_authoritative(df, db_map):
        df["Included"] = False
        for (delta_id, variant_id), included in db_map.items():
            if included:
                mask = (df["StimSpecId"] == delta_id) & (df["PairedVariantId"] == variant_id)
                df.loc[mask, "Included"] = True

    def _load_hypothesized_comps(self, stim_ids):
        result = {}
        try:
            from clat.util.connection import Connection
            conn = Connection(context.ga_database)
            conn.execute("SHOW TABLES LIKE 'HypothesizedComp'")
            table = "HypothesizedComp" if conn.fetch_one() else "StimCompsToPreserve"
            for sid in stim_ids:
                conn.execute(f"SELECT hypothesized_comp FROM {table} WHERE stim_id = %s", (int(sid),))
                row = conn.fetch_one()
                if row is None:
                    continue
                comps = [int(p.strip()) for p in str(row).split(",")
                         if p.strip().lstrip("-").isdigit()]
                if comps:
                    result[int(sid)] = comps
        except Exception as exc:
            print(f"Could not read hypothesized comps: {exc}")
        return result

    # -- actions ------------------------------------------------------------
    def load_from_db(self):
        if self.pairs is None:
            QMessageBox.warning(self.view, "No pairs", "Compute pairs first.")
            return
        db_map = self._read_db_included()
        if not db_map:
            QMessageBox.information(self.view, "Load from DB",
                                    f"No data in IncludedDeltas for {context.ga_database}.")
            return
        self.manual_overrides.clear()
        self._apply_db_authoritative(self.pairs, db_map)
        self.render()
        self.status(self._summary() + f"   (loaded {int(self.pairs['Included'].sum())} included from DB)")

    def reset_to_threshold(self):
        if self.pairs is None:
            return
        self.manual_overrides.clear()
        self.pairs["Included"] = self.pairs["Ratio"] < self.analysis.threshold
        self.render()

    def export_to_db(self):
        if self.pairs is None or self.pairs.empty:
            QMessageBox.warning(self.view, "Nothing to export", "Compute pairs first.")
            return
        # Guard against the global context having moved under us.
        if context.ga_database != self.session.ga_database:
            QMessageBox.critical(
                self.view, "Context mismatch",
                f"The active context is {context.ga_database} but this curation is for "
                f"{self.session.ga_database}. Re-select the session and try again.")
            return
        n_total = len(self.pairs)
        n_inc = int(self.pairs["Included"].sum())
        if QMessageBox.question(
                self.view, "Export to IncludedDeltas",
                f"Session {self.session.session_id}\nDatabase {context.ga_database}\n\n"
                f"Replace its IncludedDeltas table with {n_total} pairs "
                f"({n_inc} included, {n_total - n_inc} excluded)?") != QMessageBox.Yes:
            return
        try:
            ok = self.analysis._save_deltas_to_db(self.pairs, skip_prompt=True)
        except Exception as exc:
            QMessageBox.critical(self.view, "Export failed", str(exc))
            return
        if ok:
            QMessageBox.information(self.view, "Exported",
                                    f"Saved {n_total} pairs ({n_inc} included) to "
                                    f"{context.ga_database}.IncludedDeltas.")

    # -- ordering + rendering --------------------------------------------------
    def ordered_pairs(self) -> pd.DataFrame:
        """Same ordering rules as the Tk GUI's _ordered_pairs."""
        v = self.values
        df = self.pairs.copy()
        sort_col = SORT_COLUMNS[v["sort_by"]]
        ascending = not v["descending"]
        included_first = v["included_first"]
        by, asc = [], []
        if v["group_variant"]:
            group_agg = "min" if ascending else "max"
            df["_group_key"] = df.groupby("PairedVariantId")[sort_col].transform(group_agg)
            if included_first:
                df["_group_has_included"] = df.groupby("PairedVariantId")["Included"].transform("any")
                by.append("_group_has_included")
                asc.append(False)
            by += ["_group_key", "PairedVariantId"]
            asc += [ascending, True]
        if included_first:
            by.append("Included")
            asc.append(False)
        by.append(sort_col)
        asc.append(ascending)
        return df.sort_values(by=by, ascending=asc, kind="stable")

    def _response_range(self):
        vals = pd.concat([self.pairs["Delta Response"], self.pairs["Variant Response"]]).dropna()
        if vals.empty:
            return 0.0, 1.0
        return float(vals.min()), float(vals.max())

    def _show_message(self, text):
        if self.view is not None:
            self.view.hide_from(0)
            self.view.message.setText(text)
            self.view.message.show()
        self.status(text)

    def _gen_label(self, stim_id):
        gen = self.gen_map.get(stim_id)
        if gen is None or pd.isna(gen):
            return "?"
        return str(int(gen))

    @staticmethod
    def _set_image(label, pix, fallback, size):
        if pix is not None:
            label.setPixmap(pix)
            label.setStyleSheet("")
        else:
            label.setPixmap(QPixmap())
            label.setText(fallback)
            label.setFixedSize(size, size)
            label.setStyleSheet("color: gray; border: 1px dashed gray;")
            return
        label.setFixedSize(pix.size())

    def render(self):
        if self.view is None or self.pairs is None or self.pairs.empty:
            return
        self.view.message.hide()
        ordered = self.ordered_pairs()
        vmin, vmax = self._response_range()
        variant_max = float(self.pairs["Variant Response"].max())
        show_comps = self.values.get("show_comps", True)
        size = self.thumbs.thumb_size

        sids = ordered["StimSpecId"].to_numpy()
        vids = ordered["PairedVariantId"].to_numpy()
        dresps = ordered["Delta Response"].to_numpy()
        vresps = ordered["Variant Response"].to_numpy()
        ratios = ordered["Ratio"].to_numpy()
        incs = ordered["Included"].to_numpy()

        grid = self.view.grid
        n = len(ordered)
        self.view.inner.setUpdatesEnabled(False)
        try:
            for pos in range(n):
                delta_id, variant_id = int(sids[pos]), int(vids[pos])
                d_resp, v_resp = dresps[pos], vresps[pos]
                pct = (100.0 * v_resp / variant_max) if variant_max else 0.0
                c = pos + 1
                w = self.view.column(pos)

                comps = self.hypothesized_map.get(delta_id) if show_comps else None
                d_pix = self.thumbs.pixmap(self.thumb_map.get(delta_id), d_resp, vmin, vmax, comps)
                v_pix = self.thumbs.pixmap(self.thumb_map.get(variant_id), v_resp, vmin, vmax)

                w["ratio"].setText(f"ratio {float(ratios[pos]):.2f}")
                self._set_image(w["delta_img"], d_pix, f"delta\n{delta_id}", size)
                w["delta_info"].setText(f"Δ {d_resp:.1f}\ngen {self._gen_label(delta_id)}\nd{delta_id}")
                self._set_image(w["variant_img"], v_pix, f"variant\n{variant_id}", size)
                w["variant_info"].setText(f"V {v_resp:.1f} ({pct:.0f}% max)\n"
                                          f"gen {self._gen_label(variant_id)}\nv{variant_id}")
                chk = w["chk"]
                if w["handler"] is not None:
                    chk.toggled.disconnect(w["handler"])
                chk.setChecked(bool(incs[pos]))
                w["handler"] = (lambda checked, did=delta_id, vid=variant_id:
                                self._on_toggle(did, vid, checked))
                chk.toggled.connect(w["handler"])

                for row, key in enumerate(("ratio", "delta_img", "delta_info",
                                           "variant_img", "variant_info", "chk")):
                    grid.addWidget(w[key], row, c, Qt.AlignHCenter)
                    w[key].show()
            self.view.hide_from(n)
        finally:
            self.view.inner.setUpdatesEnabled(True)
        self.status(self._summary())

    def _on_toggle(self, delta_id, variant_id, checked):
        mask = (self.pairs["StimSpecId"] == delta_id) & (self.pairs["PairedVariantId"] == variant_id)
        self.pairs.loc[mask, "Included"] = bool(checked)
        self.manual_overrides[(delta_id, variant_id)] = bool(checked)
        self.status(self._summary())

    def _summary(self):
        n_total = len(self.pairs)
        n_inc = int(self.pairs["Included"].sum())
        v = self.values
        channel = "GA" if v.get("data_type") == "GA" else v.get("channel", "")
        baseline = " (baseline-corrected)" if v.get("baseline") else ""
        return (f"Channel: {channel}{baseline}   |   {n_total} pairs, {n_inc} included, "
                f"{n_total - n_inc} excluded")

    def save(self, folder):
        """Screenshot of the whole grid plus the pair table as CSV."""
        written = []
        if self.view is not None and self.pairs is not None:
            png = os.path.join(folder, "delta_curation.png")
            self.view.inner.grab().save(png)
            written.append(png)
            csv = os.path.join(folder, "delta_pairs.csv")
            self.ordered_pairs().drop(columns=["_group_key", "_group_has_included"],
                                      errors="ignore").to_csv(csv, index=False)
            written.append(csv)
        return written
