"""
Delta-variant pair viewer (read-only).

Shows every delta next to the stimulus it was made from (its parent, the
"variant" of the pair): deltas on top, variants underneath, one pair per
column, with their mean responses and the delta/variant ratio. For each pair:
  - "in estim exp": whether the pair was included in the EStim experiment
    (IncludedDeltas.included for this delta + variant). Read-only.
  - "select": your own pick. "Make figure from selected" draws the picked
    pairs as a standalone figure (e.g. good examples of a component or a
    combination of components), which you can save.

Nothing is written to the GA database. Thresholds that decided inclusion for
the experiment are not used here: all delta-parent pairs are shown.

The red overlay on deltas marks the hypothesized component(s); it needs the
comp-map thumbnails that only some experiments generate, and silently does
nothing for the others.

Selections are kept per session, so switching away and back keeps them.
"""

from __future__ import annotations

import json
import os
from datetime import datetime

import numpy as np
import pandas as pd
from PIL import Image, ImageOps
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (QCheckBox, QDialog, QGridLayout, QHBoxLayout, QLabel,
                             QMessageBox, QPushButton, QScrollArea, QVBoxLayout,
                             QWidget)

from src.analysis.ga.explorer.explorer_module import (Action, ExplorerModule, Param,
                                                      new_output_folder)
from src.analysis.ga.explorer.ga_data import (DATA_TYPES, load_ga_repository_data,
                                              parse_channel)
from src.startup import context

DELTA_STIM_TYPE = "REGIME_ESTIM_DELTA"

# Maps the user-facing sort option to the pairs-table column it sorts on.
SORT_COLUMNS = {
    "ratio": "Ratio",
    "delta_resp": "Delta Response",
    "variant_resp": "Variant Response",
    "delta_id": "StimSpecId",
}
SHOW_CHOICES = ["all", "included in estim exp", "not included", "selected"]

# Width (px) of the response-colored border drawn around each thumbnail.
THUMB_BORDER = 6

# Component-index -> RGB color used by the Java comp-map renderer
# (AllenMatchStick.drawSkeleton's colorCode, 1-indexed).
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

INCLUDED_COLOR = "#1b7f3b"
SELECTED_BG = "#fff3c4"

# Parameters whose change means the pair table must be recomputed (the rest
# only re-render or only affect the figure).
RECOMPUTE_KEYS = {"data_type", "channel", "baseline"}
FIGURE_KEYS = {"fig_title", "fig_pairs_per_row", "fig_show_values", "fig_pair_size"}

# Thumbnail resolution (px) used for the exported figure.
FIGURE_THUMB_PX = 300


# ---------------------------------------------------------------------------
# Pairs
# ---------------------------------------------------------------------------

def compute_all_pairs(data: pd.DataFrame, response_col: str) -> pd.DataFrame | None:
    """Every REGIME_ESTIM_DELTA stim paired with its parent, with mean
    responses. No thresholds. Columns: StimSpecId (delta), PairedVariantId
    (parent), Delta Response, Variant Response, Ratio."""
    data = data[data["StimType"] != "BASELINE"]
    mean_resp = data.groupby("StimSpecId")[response_col].mean()
    info = data.drop_duplicates("StimSpecId").set_index("StimSpecId")
    deltas = info[info["StimType"] == DELTA_STIM_TYPE]
    rows = []
    for delta_id, parent_id in deltas["ParentId"].items():
        if parent_id not in mean_resp.index:
            continue
        rows.append({"StimSpecId": int(delta_id), "PairedVariantId": int(parent_id),
                     "Delta Response": float(mean_resp[delta_id]),
                     "Variant Response": float(mean_resp[parent_id])})
    if not rows:
        return None
    pairs = pd.DataFrame(rows)
    pairs["Ratio"] = pairs["Delta Response"] / pairs["Variant Response"].replace(0, np.nan)
    return pairs


def read_estim_included_pairs() -> set | None:
    """{(delta_id, variant_id)} marked included in this session's
    IncludedDeltas table, or None when the table doesn't exist. Read-only."""
    from clat.util.connection import Connection
    try:
        conn = Connection(context.ga_database)
        conn.execute("SELECT delta_id, variant_id, included FROM IncludedDeltas")
        rows = conn.fetch_all()
    except Exception as exc:
        print(f"No IncludedDeltas for {context.ga_database}: {exc}")
        return None
    return {(int(d), int(v)) for d, v, inc in rows if inc}


def read_hypothesized_comps(stim_ids) -> dict:
    """{stim_id: [comp, ...]} from HypothesizedComp (or the older
    StimCompsToPreserve). Missing table or rows -> empty."""
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


# ---------------------------------------------------------------------------
# Thumbnails
# ---------------------------------------------------------------------------

class ThumbnailRenderer:
    """Bordered (optionally comp-highlighted) thumbnails, cached."""

    def __init__(self, thumb_size=140):
        self.thumb_size = thumb_size
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

    def has_compmap(self, thumb_path):
        return bool(thumb_path) and self._compmap_inner(thumb_path) is not None

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

    @staticmethod
    def border_color(response, vmin, vmax):
        if vmax > vmin and response is not None and not pd.isna(response):
            norm = max(0.0, min(1.0, (response - vmin) / (vmax - vmin)))
        else:
            norm = 0.5
        return (int(255 * norm), 0, 0)  # black -> red intensity

    def image(self, path, response, vmin, vmax, overlay_comps=None):
        """PIL image with border (and overlay), or None if the file is missing."""
        if not path or not os.path.exists(path):
            return None
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
        return ImageOps.expand(img, border=THUMB_BORDER,
                               fill=self.border_color(response, vmin, vmax))

    def pixmap(self, path, response, vmin, vmax, overlay_comps=None):
        overlay_comps = tuple(overlay_comps) if overlay_comps else ()
        key = (path, self.border_color(response, vmin, vmax), overlay_comps)
        cached = self._pixmap_cache.get(key)
        if cached is not None:
            return cached
        try:
            img = self.image(path, response, vmin, vmax, overlay_comps)
        except Exception:
            return None
        if img is None:
            return None
        pix = pil_to_pixmap(img)
        self._pixmap_cache[key] = pix
        return pix


def pil_to_pixmap(img: Image.Image) -> QPixmap:
    img = img.convert("RGB")
    w, h = img.size
    qimg = QImage(img.tobytes("raw", "RGB"), w, h, 3 * w, QImage.Format_RGB888)
    return QPixmap.fromImage(qimg.copy())


# ---------------------------------------------------------------------------
# The grid widget
# ---------------------------------------------------------------------------

GRID_ROWS = ("ratio", "delta_img", "delta_info", "variant_img", "variant_info",
             "included", "select")


class PairGridView(QScrollArea):
    """Scrollable grid, one pair per column. Column widgets are pooled and
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
            col = {k: QLabel() for k in GRID_ROWS[:-2]}
            col["included"] = QCheckBox("in estim exp")
            col["included"].setEnabled(False)  # read-only
            col["included"].setToolTip("Included in the EStim experiment (IncludedDeltas). Read-only.")
            col["select"] = QCheckBox("select")
            col["select"].setToolTip("Pick this pair for 'Make figure from selected'.")
            col["ratio"].setStyleSheet("font-weight: bold; font-size: 12px;")
            for k in ("delta_info", "variant_info"):
                col[k].setStyleSheet("font-size: 11px;")
            for k in GRID_ROWS[:-2]:
                col[k].setAlignment(Qt.AlignCenter)
            col["handler"] = None
            self.pool.append(col)
        return self.pool[idx]

    def hide_from(self, n):
        for col in self.pool[n:]:
            for w in col.values():
                if isinstance(w, QWidget):
                    w.hide()


# ---------------------------------------------------------------------------
# Figure of selected pairs
# ---------------------------------------------------------------------------

def make_pairs_figure(rows: list[dict], *, title="", pairs_per_row=0, show_values=True,
                      pair_size=2.0, show_comps=True):
    """Matplotlib figure: one column per pair, delta above its variant.

    ``rows``: dicts with delta_id, variant_id, delta_resp, variant_resp,
    ratio, delta_path, variant_path, comps. Borders use one black->red scale
    shared by all pairs in the figure (colorbar on the right).
    """
    from matplotlib.colors import LinearSegmentedColormap, Normalize
    from matplotlib.cm import ScalarMappable
    from matplotlib.figure import Figure

    n = len(rows)
    per_row = n if pairs_per_row <= 0 else min(pairs_per_row, n)
    n_bands = int(np.ceil(n / per_row))
    resp = [r["delta_resp"] for r in rows] + [r["variant_resp"] for r in rows]
    vmin, vmax = float(np.nanmin(resp)), float(np.nanmax(resp))
    renderer = ThumbnailRenderer(FIGURE_THUMB_PX)

    label_h = 0.35 if show_values else 0.0
    fig_w = pair_size * per_row + 1.6
    fig_h = n_bands * 2 * (pair_size + label_h) + (0.6 if title else 0.2)
    fig = Figure(figsize=(fig_w, fig_h))
    left, right = 0.9 / fig_w, 1 - 0.7 / fig_w
    top = 1 - ((0.6 if title else 0.2) / fig_h)
    grid = fig.add_gridspec(n_bands * 2, per_row, left=left, right=right, top=top,
                            bottom=0.02, hspace=0.25 if show_values else 0.06, wspace=0.06)
    for i, r in enumerate(rows):
        band, col = divmod(i, per_row)
        for k, (role, path, value, comps) in enumerate((
                ("Delta", r["delta_path"], r["delta_resp"], r["comps"] if show_comps else None),
                ("Variant", r["variant_path"], r["variant_resp"], None))):
            ax = fig.add_subplot(grid[band * 2 + k, col])
            img = renderer.image(path, value, vmin, vmax, comps)
            if img is not None:
                ax.imshow(np.asarray(img))
            else:
                ax.text(0.5, 0.5, "missing\nimage", ha="center", va="center", color="gray")
            ax.set_xticks([])
            ax.set_yticks([])
            for spine in ax.spines.values():
                spine.set_visible(False)
            if show_values:
                ax.set_xlabel(f"{value:.1f}", fontsize=11, labelpad=2)
            if col == 0:
                ax.set_ylabel(role, fontsize=13, fontweight="bold")
    if title:
        fig.suptitle(title, fontsize=16)
    cmap = LinearSegmentedColormap.from_list("black_red", [(0, 0, 0), (1, 0, 0)])
    cax = fig.add_axes([1 - 0.55 / fig_w, 0.15, 0.12 / fig_w, 0.6])
    cb = fig.colorbar(ScalarMappable(norm=Normalize(vmin, vmax), cmap=cmap), cax=cax)
    cb.set_label("Response", fontsize=12)
    cb.ax.tick_params(labelsize=10)
    return fig


class PairsFigureDialog(QDialog):
    """Non-modal window showing the figure of selected pairs, with Save."""

    def __init__(self, parent, fig, *, save_root, session, rows, params):
        super().__init__(parent)
        from src.analysis.ga.explorer.figure_view import FigureView
        self.setWindowTitle(f"Selected delta-variant pairs  ({session.session_id})")
        self.resize(1200, 700)
        self.fig, self.save_root, self.session = fig, save_root, session
        self.rows, self.params = rows, params
        lay = QVBoxLayout(self)
        self.view = FigureView(self, keep_size=True)
        self.view.show_figure(fig)
        lay.addWidget(self.view, stretch=1)
        bar = QHBoxLayout()
        self.saved_label = QLabel("")
        self.saved_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        save_btn = QPushButton("Save figure…")
        save_btn.clicked.connect(self.save)
        bar.addWidget(self.saved_label, stretch=1)
        bar.addWidget(save_btn)
        lay.addLayout(bar)

    def save(self):
        try:
            folder = new_output_folder(self.save_root, self.session.session_id,
                                       "delta_pair_figure")
            files = self.view.save(folder, basename="delta_pairs")
            config = {
                "figure": "selected delta-variant pairs",
                "session_id": self.session.session_id,
                "ga_database": self.session.ga_database,
                "params": self.params,
                "pairs": [{k: v for k, v in r.items() if not k.endswith("_path")}
                          for r in self.rows],
                "files": [os.path.basename(f) for f in files],
                "saved_at": datetime.now().isoformat(timespec="seconds"),
            }
            with open(os.path.join(folder, "config.json"), "w") as f:
                json.dump(config, f, indent=2, default=str)
        except Exception as exc:
            QMessageBox.critical(self, "Save failed", str(exc))
            return
        self.saved_label.setText(f"Saved to {folder}")


# ---------------------------------------------------------------------------
# The module
# ---------------------------------------------------------------------------

class DeltaPairViewerModule(ExplorerModule):
    name = "Delta-variant pairs"
    description = ("Every delta with the variant it was made from. 'in estim exp' "
                   "shows EStim inclusion (read-only); tick 'select' and press "
                   "'Make figure from selected' to build an example figure.")

    def __init__(self):
        super().__init__()
        self.view: PairGridView | None = None
        self.pairs: pd.DataFrame | None = None
        self.thumb_map: dict = {}
        self.gen_map: dict = {}
        self.hypothesized_map: dict = {}
        self.has_included_table = False
        # session_id -> set of (delta_id, variant_id) picked for the figure.
        self.selections: dict[str, set] = {}
        self.values: dict = {}
        self.thumbs = ThumbnailRenderer()
        self._dialogs: list = []

    # -- declaration ------------------------------------------------------
    def params(self):
        return [
            Param("data_type", "Data type", "choice", "mua", choices=DATA_TYPES,
                  tooltip="Responses imported from the repository. 'GA' forces channel GA."),
            Param("channel", "Channel", "str", "GA",
                  tooltip='"GA", "Cluster", "A-006", or "A-000,A-006" (summed)'),
            Param("baseline", "Baseline correction", "bool", False),
            Param("show", "Show", "choice", "all", choices=SHOW_CHOICES, live=True),
            Param("sort_by", "Sort by", "choice", "ratio", choices=list(SORT_COLUMNS), live=True),
            Param("descending", "Descending", "bool", False, live=True),
            Param("included_first", "Included first", "bool", False, live=True,
                  tooltip="Pairs included in the EStim experiment first."),
            Param("group_variant", "Group by variant", "bool", False, live=True),
            Param("show_comps", "Hypothesized comps overlay", "bool", True, live=True,
                  tooltip="Red overlay on the delta's hypothesized component. Only for "
                          "experiments that generated comp-map thumbnails."),
            Param("thumb_size", "Thumbnail size (px)", "int", 140, minimum=60, maximum=400,
                  step=10, live=True),
            # Figure of selected pairs (used when you press the button).
            Param("fig_title", "Figure: title", "str", "", live=True,
                  tooltip="Empty = no title."),
            Param("fig_pairs_per_row", "Figure: pairs per row", "int", 0, minimum=0,
                  maximum=50, live=True, tooltip="0 = all pairs in one row."),
            Param("fig_show_values", "Figure: show responses", "bool", True, live=True),
            Param("fig_pair_size", "Figure: image size (in)", "float", 2.0, minimum=0.5,
                  maximum=6.0, step=0.25, live=True),
        ]

    def actions(self):
        return [
            Action("Make figure from selected", self.make_figure_from_selected,
                   "Draw the selected pairs (in the current sort order) as a figure.",
                   color="lightgreen"),
            Action("Clear selection", self.clear_selection,
                   "Untick every selected pair in this session."),
        ]

    # -- lifecycle ----------------------------------------------------------
    def create_view(self, parent):
        self.view = PairGridView(parent)
        return self.view

    def set_session(self, session):
        super().set_session(session)
        self.pairs = None
        self.thumbs.clear(keep_images=False)

    @property
    def selected(self) -> set:
        return self.selections.setdefault(self.session.session_id, set())

    def refresh(self, values, changed=None):
        self.values = dict(values)
        self.thumbs.set_size(values["thumb_size"])
        if changed and changed <= FIGURE_KEYS and self.pairs is not None:
            return  # figure settings only matter when the figure is made
        if changed is None or self.pairs is None or (changed & RECOMPUTE_KEYS):
            self.recompute_pairs()
        else:
            self.render()

    # -- data -----------------------------------------------------------------
    def recompute_pairs(self):
        from src.analysis.ga.response_spec import ResponseSpec

        v = self.values
        data_type = v["data_type"]
        channel = "GA" if data_type == "GA" else parse_channel(v["channel"])
        if not channel:
            self._show_message("Enter a channel.")
            return
        compiled_data, spike_rates_col = load_ga_repository_data(self.session, data_type)
        prepared = ResponseSpec(channel, use_baseline_correction=bool(v["baseline"])).apply(
            compiled_data, spike_rates_col=spike_rates_col)

        pairs = compute_all_pairs(prepared.data, prepared.response_col)
        if pairs is None:
            self.pairs = None
            self._show_message("No deltas in this session.")
            return

        included = read_estim_included_pairs()
        self.has_included_table = included is not None
        pairs["Included"] = [(d, p) in (included or set())
                             for d, p in zip(pairs["StimSpecId"], pairs["PairedVariantId"])]

        info = prepared.data.drop_duplicates("StimSpecId").set_index("StimSpecId")
        self.thumb_map = info["ThumbnailPath"].to_dict()
        self.gen_map = info["GenId"].to_dict() if "GenId" in info.columns else {}
        self.pairs = pairs
        self.hypothesized_map = read_hypothesized_comps(pairs["StimSpecId"].unique())
        self.thumbs.clear()  # border colors depend on the new response range
        self.render()

    # -- actions ------------------------------------------------------------
    def clear_selection(self):
        if self.session is None:
            return
        self.selected.clear()
        self.render()

    def selected_rows(self) -> list[dict]:
        """Selected pairs, in the grid's current sort order, as plain dicts."""
        if self.pairs is None:
            return []
        ordered = self.ordered_pairs(apply_filter=False)
        rows = []
        for _, r in ordered.iterrows():
            key = (int(r["StimSpecId"]), int(r["PairedVariantId"]))
            if key not in self.selected:
                continue
            rows.append({
                "delta_id": key[0], "variant_id": key[1],
                "delta_resp": float(r["Delta Response"]),
                "variant_resp": float(r["Variant Response"]),
                "ratio": float(r["Ratio"]),
                "included_in_estim": bool(r["Included"]),
                "comps": self.hypothesized_map.get(key[0]),
                "delta_path": self.thumb_map.get(key[0]),
                "variant_path": self.thumb_map.get(key[1]),
            })
        return rows

    def make_figure_from_selected(self):
        rows = self.selected_rows()
        if not rows:
            QMessageBox.information(self.view, "No pairs selected",
                                    "Tick 'select' under the pairs you want in the figure.")
            return
        v = self.values
        fig = make_pairs_figure(rows, title=v["fig_title"], pairs_per_row=v["fig_pairs_per_row"],
                                show_values=v["fig_show_values"], pair_size=v["fig_pair_size"],
                                show_comps=v["show_comps"])
        params = {k: v[k] for k in ("data_type", "channel", "baseline", "show_comps",
                                    *sorted(FIGURE_KEYS))}
        dlg = PairsFigureDialog(self.view.window(), fig, save_root=self.save_root,
                                session=self.session, rows=rows, params=params)
        self._dialogs = [d for d in self._dialogs if d.isVisible()] + [dlg]
        dlg.show()
        self.status(f"Figure of {len(rows)} selected pairs opened")

    # -- ordering + rendering --------------------------------------------------
    def ordered_pairs(self, apply_filter=True) -> pd.DataFrame:
        v = self.values
        df = self.pairs.copy()
        if apply_filter:
            show = v.get("show", "all")
            if show == "included in estim exp":
                df = df[df["Included"]]
            elif show == "not included":
                df = df[~df["Included"]]
            elif show == "selected":
                keys = list(zip(df["StimSpecId"], df["PairedVariantId"]))
                df = df[[k in self.selected for k in keys]]
        sort_col = SORT_COLUMNS[v["sort_by"]]
        ascending = not v["descending"]
        included_first = v["included_first"]
        by, asc = [], []
        if v["group_variant"] and not df.empty:
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
            label.setFixedSize(pix.size())
        else:
            label.setPixmap(QPixmap())
            label.setText(fallback)
            label.setFixedSize(size, size)
            label.setStyleSheet("color: gray; border: 1px dashed gray;")

    def render(self):
        if self.view is None or self.pairs is None:
            return
        ordered = self.ordered_pairs()
        if ordered.empty:
            self._show_message(f"No pairs to show for '{self.values.get('show')}'.")
            return
        self.view.message.hide()
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
                w = self.view.column(pos)

                comps = self.hypothesized_map.get(delta_id) if show_comps else None
                d_pix = self.thumbs.pixmap(self.thumb_map.get(delta_id), d_resp, vmin, vmax, comps)
                v_pix = self.thumbs.pixmap(self.thumb_map.get(variant_id), v_resp, vmin, vmax)

                w["ratio"].setText(f"ratio {float(ratios[pos]):.2f}")
                self._set_image(w["delta_img"], d_pix, f"delta\n{delta_id}", size)
                comp_txt = f"\ncomp {','.join(map(str, comps))}" if comps else ""
                w["delta_info"].setText(f"Δ {d_resp:.1f}\ngen {self._gen_label(delta_id)}"
                                        f"\nd{delta_id}{comp_txt}")
                self._set_image(w["variant_img"], v_pix, f"variant\n{variant_id}", size)
                w["variant_info"].setText(f"V {v_resp:.1f} ({pct:.0f}% max)\n"
                                          f"gen {self._gen_label(variant_id)}\nv{variant_id}")
                inc = bool(incs[pos])
                w["included"].setChecked(inc)
                w["included"].setStyleSheet(
                    f"color: {INCLUDED_COLOR}; font-weight: bold;" if inc else "color: gray;")

                key = (delta_id, variant_id)
                chk = w["select"]
                if w["handler"] is not None:
                    chk.toggled.disconnect(w["handler"])
                chk.setChecked(key in self.selected)
                w["handler"] = lambda checked, k=key, col=w: self._on_select(k, checked, col)
                chk.toggled.connect(w["handler"])
                self._style_selected(w, key in self.selected)

                for row, name in enumerate(GRID_ROWS):
                    grid.addWidget(w[name], row, pos + 1, Qt.AlignHCenter)
                    w[name].show()
            self.view.hide_from(n)
        finally:
            self.view.inner.setUpdatesEnabled(True)
        self.status(self._summary(n))

    @staticmethod
    def _style_selected(col, selected):
        col["select"].setStyleSheet(
            f"background: {SELECTED_BG}; font-weight: bold;" if selected else "")
        col["ratio"].setStyleSheet(
            "font-weight: bold; font-size: 12px;"
            + (f" background: {SELECTED_BG};" if selected else ""))

    def _on_select(self, key, checked, col):
        if checked:
            self.selected.add(key)
        else:
            self.selected.discard(key)
        self._style_selected(col, checked)
        self.status(self._summary())

    def _summary(self, n_shown=None):
        n_total = len(self.pairs)
        n_inc = int(self.pairs["Included"].sum())
        v = self.values
        channel = "GA" if v.get("data_type") == "GA" else v.get("channel", "")
        baseline = " (baseline-corrected)" if v.get("baseline") else ""
        inc_txt = (f"{n_inc} in estim exp" if self.has_included_table
                   else "no IncludedDeltas table")
        shown = f"{n_shown} shown, " if n_shown is not None and n_shown != n_total else ""
        return (f"Channel: {channel}{baseline}   |   {n_total} pairs ({shown}{inc_txt}), "
                f"{len(self.selected)} selected")

    def save(self, folder):
        """Screenshot of the grid plus the pair table (with selections) as CSV."""
        written = []
        if self.view is not None and self.pairs is not None:
            png = os.path.join(folder, "delta_pairs_grid.png")
            self.view.inner.grab().save(png)
            written.append(png)
            csv = os.path.join(folder, "delta_pairs.csv")
            table = self.ordered_pairs(apply_filter=False).drop(
                columns=["_group_key", "_group_has_included"], errors="ignore")
            table = table.rename(columns={"Included": "Included in estim exp"})
            table["Selected"] = [(d, p) in self.selected for d, p in
                                 zip(table["StimSpecId"], table["PairedVariantId"])]
            table.to_csv(csv, index=False)
            written.append(csv)
        return written
