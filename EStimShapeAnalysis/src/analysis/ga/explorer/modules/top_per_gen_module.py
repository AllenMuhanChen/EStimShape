"""
Top stimuli per generation, one panel per lineage: the explorer version of
plot_generations' "Top Stimuli Per Gen by Lineage" figure.

Same steps as PlotGenerationsAnalysis.analyze: ResponseSpec -> rank each
stim within its (generation, lineage) by mean response -> keep the top N per
generation in lineages with more than M stimuli -> GroupedStimuliPlotter with
one row per generation and one panel per lineage. Differences:
  - Trial types are filtered by hand ("Show ZERO", "Show SHUFFLE", ...)
    before ranking. SHUFFLE and LIGHTING are off by default.
  - Each lineage is drawn as its own panel, all on one shared response color
    scale and the same generation rows, so a panel can be copied on its own
    ("Copy panel") and the stacked panels are the whole figure ("Copy whole
    figure").
  - Border width is a text box (pixels added around the original thumbnail
    before it is scaled to the cell size, as in plot_generations).
  - On screen, panels are drawn directly with PIL in the plotter's layout
    (thumbnails cached across redraws and sessions), which is much faster
    than rendering plotly figures. Save also writes the plotter's own
    figure as svg/pdf.

Nothing is written to disk unless you press Save view: whole figure (png,
svg, pdf) plus one png per lineage panel.
"""

from __future__ import annotations

import os

from PIL import Image
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (QApplication, QCheckBox, QHBoxLayout, QLabel, QPushButton,
                             QScrollArea, QSpinBox, QVBoxLayout, QWidget)

from src.analysis.ga.explorer.explorer_module import ExplorerModule, Param
from src.analysis.ga.explorer.ga_data import (DATA_TYPES, load_ga_repository_data,
                                              parse_channel)
from src.analysis.ga.explorer.modules.stim_type_filter import (TYPE_FAMILIES, keep_types,
                                                               shown_families,
                                                               type_filter_params)

# plot_generations layout: (horizontal, vertical) px between cells.
SUBPLOT_SPACING = (75, 25)


def parse_border_width(text) -> int:
    try:
        value = int(str(text).strip())
    except ValueError:
        raise ValueError(f"Border width must be a whole number of pixels, got {text!r}")
    if value < 0:
        raise ValueError(f"Border width can't be negative, got {value}")
    return value


def rank_within_generation(data, response_col):
    """Adds RankWithinGeneration: 1 = best mean response of its (GenId,
    Lineage), as in plot_generations."""
    avg = data.groupby(["GenId", "StimSpecId", "Lineage"])[response_col].mean().reset_index()
    avg["RankWithinGeneration"] = avg.groupby(["GenId", "Lineage"])[response_col].rank(
        ascending=False, method="first")
    return data.merge(avg[["GenId", "StimSpecId", "RankWithinGeneration"]],
                      on=["GenId", "StimSpecId"], how="left")


def stack_vertically(images: list[Image.Image], gap=0) -> Image.Image:
    """Panels already start with the plotter's top margin, so no extra gap."""
    width = max(im.width for im in images)
    height = sum(im.height for im in images) + gap * (len(images) - 1)
    out = Image.new("RGB", (width, height), "white")
    y = 0
    for im in images:
        out.paste(im, (0, y))
        y += im.height + gap
    return out


def pil_to_qimage(img: Image.Image) -> QImage:
    img = img.convert("RGB")
    return QImage(img.tobytes("raw", "RGB"), img.width, img.height, 3 * img.width,
                  QImage.Format_RGB888).copy()


# ---------------------------------------------------------------------------
# Fast panel drawing (PIL), same layout as GroupedStimuliPlotter
# ---------------------------------------------------------------------------

# Thumbnails decoded once and kept small: path -> (original size, image with
# its longest side at most THUMB_CACHE_PX). Shared by every session.
THUMB_CACHE_PX = 600
_thumb_cache: dict[str, tuple] = {}
_cell_cache: dict[tuple, Image.Image] = {}


def _load_thumb(path):
    hit = _thumb_cache.get(path)
    if hit is None:
        try:
            with Image.open(path) as im:
                size = im.size
                im = im.convert("RGB")
                im.thumbnail((THUMB_CACHE_PX, THUMB_CACHE_PX), Image.LANCZOS)
                hit = (size, im)
        except Exception:
            hit = (None, None)
        _thumb_cache[path] = hit
    return hit


def bordered_cell(path, color, border, cell) -> Image.Image | None:
    """Thumbnail with a ``border``-px border (in original-image pixels) of
    ``color``, scaled to cell x cell: the same result as the plotter's
    ImageOps.expand(img, border) followed by resize((cell, cell))."""
    key = (path, border, cell)
    inner = _cell_cache.get(key)
    if inner is None:
        size, src = _load_thumb(path)
        if src is None:
            return None
        w, h = size
        iw = max(1, round(cell * w / (w + 2 * border)))
        ih = max(1, round(cell * h / (h + 2 * border)))
        inner = (src.resize((iw, ih), Image.LANCZOS), ((cell - iw) // 2, (cell - ih) // 2))
        _cell_cache[key] = inner
    img, offset = inner
    out = Image.new("RGB", (cell, cell), color)
    out.paste(img, offset)
    return out


def border_color(value, vmin, vmax):
    """Black -> red, as the plotter's 'intensity' color mode."""
    if vmax == vmin:
        norm = 0.5
    else:
        norm = min(1.0, max(0.0, (value - vmin) / (vmax - vmin)))
    return (int(255 * norm), 0, 0)


def _font(size):
    from matplotlib import font_manager
    from PIL import ImageFont
    try:
        return ImageFont.truetype(font_manager.findfont("DejaVu Sans"), size)
    except Exception:
        return ImageFont.load_default()


def draw_panel(cells: dict, row_values, col_values, *, cell, border, spacing, vmin, vmax,
               colorbar=True, labels=False) -> Image.Image:
    """One lineage panel. ``cells``: (row value, col value) -> (thumbnail
    path, mean response). Geometry follows GroupedStimuliPlotter.compute for
    one subgroup (margins, spacing, cell size)."""
    from PIL import ImageDraw
    hs, vs = spacing
    left = 200 if labels else 50
    right = 200 if colorbar else 50
    top = 100
    content_w = len(col_values) * (cell + hs)
    content_h = len(row_values) * (cell + vs)
    img = Image.new("RGB", (left + content_w + right, top + content_h), "white")
    draw = ImageDraw.Draw(img)
    label_font = _font(18)
    for r, row in enumerate(row_values):
        y = top + r * (cell + vs)
        if labels:
            draw.text((left - 6, y + cell / 2), str(row), fill="black", font=label_font,
                      anchor="rm")
        for c, col in enumerate(col_values):
            x = left + c * (cell + hs)
            if labels and r == 0:
                draw.text((x + cell / 2, y - 4), str(col), fill="black", font=label_font,
                          anchor="mb")
            hit = cells.get((row, col))
            if hit is None:
                continue
            path, value = hit
            tile = bordered_cell(path, border_color(value, vmin, vmax), border, cell)
            if tile is None:
                draw.text((x + cell / 2, y + cell / 2), "Image not found", fill="black",
                          font=_font(12), anchor="mm")
            else:
                img.paste(tile, (x, y))
    if colorbar:
        _draw_colorbar(img, draw, left + content_w + 10, top, content_h, vmin, vmax)
    return img


def _draw_colorbar(img, draw, x, top, height, vmin, vmax):
    """Vertical black -> red bar, 80% of the panel height, ticks + 'Response'."""
    import numpy as np
    from matplotlib.ticker import MaxNLocator
    bar_h = max(20, int(height * 0.8))
    y0 = top + (height - bar_h) // 2
    thickness = 20
    ramp = np.linspace(255, 0, bar_h).astype("uint8")
    bar = np.zeros((bar_h, thickness, 3), dtype="uint8")
    bar[:, :, 0] = ramp[:, None]
    img.paste(Image.fromarray(bar), (x, y0))
    font = _font(32)
    draw.text((x, y0 - 24), "Response", fill="#2a3f5f", font=font, anchor="lb")
    if vmax > vmin:
        for t in MaxNLocator(nbins=6).tick_values(vmin, vmax):
            if vmin <= t <= vmax:
                y = y0 + bar_h - (t - vmin) / (vmax - vmin) * bar_h
                draw.text((x + thickness + 6, y), f"{t:g}", fill="#2a3f5f", font=font,
                          anchor="lm")


# ---------------------------------------------------------------------------
# View: one panel per lineage, each with its own Copy button
# ---------------------------------------------------------------------------

class LineagePanelsView(QWidget):
    def __init__(self, parent=None, on_copy_whole=None):
        super().__init__(parent)
        self.images: list[tuple[str, Image.Image]] = []
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)

        bar = QHBoxLayout()
        copy_all = QPushButton("Copy whole figure")
        copy_all.setToolTip("Copy all lineage panels, stacked, as one image.")
        copy_all.clicked.connect(on_copy_whole)
        self.fit = QCheckBox("Fit to width")
        self.fit.setChecked(True)
        self.fit.toggled.connect(self._rescale)
        self.zoom = QSpinBox()
        self.zoom.setRange(5, 300)
        self.zoom.setValue(50)
        self.zoom.setSuffix(" %")
        self.zoom.setEnabled(False)
        self.zoom.valueChanged.connect(self._rescale)
        self.fit.toggled.connect(lambda on: self.zoom.setEnabled(not on))
        self.message = QLabel("")
        self.message.setStyleSheet("color: gray;")
        bar.addWidget(copy_all)
        bar.addWidget(self.fit)
        bar.addWidget(self.zoom)
        bar.addWidget(self.message, stretch=1)
        lay.addLayout(bar)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self._new_inner()
        self.scroll.setWidget(self.inner)
        self.scroll.viewport().installEventFilter(self)
        lay.addWidget(self.scroll, stretch=1)
        self._labels: list[QLabel] = []

    def _new_inner(self):
        self.inner = QWidget()
        self.inner.setStyleSheet("background: white;")
        self.panels = QVBoxLayout(self.inner)
        self.panels.setAlignment(Qt.AlignTop | Qt.AlignLeft)

    def show_message(self, text):
        self.set_panels([])
        self.message.setText(text)

    def set_panels(self, panels: list[tuple[str, Image.Image]]):
        """``panels``: (title, image) per lineage, top to bottom."""
        self._labels = []
        self._new_inner()
        self.images = panels
        for title, img in panels:
            header = QWidget()
            h = QHBoxLayout(header)
            h.setContentsMargins(4, 8, 4, 0)
            name = QLabel(title)
            name.setStyleSheet("font-weight: bold; font-size: 14px;")
            copy = QPushButton("Copy panel")
            copy.setToolTip(f"Copy only this panel ({title}) as an image.")
            copy.clicked.connect(lambda _c=False, im=img, t=title: self.copy_image(im, t))
            h.addWidget(name)
            h.addWidget(copy)
            h.addStretch(1)
            self.panels.addWidget(header)
            label = QLabel()
            label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            label.setProperty("qimage", pil_to_qimage(img))
            self.panels.addWidget(label)
            self._labels.append(label)
        self.message.setText("")
        self._rescale()
        # Hand the filled container over only now: widgets added to an
        # already-shown container are shown later, and the scroll area then
        # kept the old height and squeezed the panels together.
        self.scroll.setWidget(self.inner)  # deletes the previous container

    def copy_image(self, img: Image.Image, what: str):
        QApplication.clipboard().setImage(pil_to_qimage(img))
        self.message.setText(f"Copied {what} ({img.width}×{img.height} px)")

    def _rescale(self, *_):
        if not self._labels:
            return
        if self.fit.isChecked():
            avail = max(50, self.scroll.viewport().width() - 30)
            widest = max(lbl.property("qimage").width() for lbl in self._labels)
            scale = min(1.0, avail / widest)
        else:
            scale = self.zoom.value() / 100.0
        for lbl in self._labels:
            qimg = lbl.property("qimage")
            pix = QPixmap.fromImage(qimg)
            if scale != 1.0:
                pix = pix.scaledToWidth(max(1, int(qimg.width() * scale)), Qt.SmoothTransformation)
            lbl.setPixmap(pix)
            lbl.setFixedSize(pix.size())

    def eventFilter(self, obj, event):
        from PyQt5.QtCore import QEvent
        if obj is self.scroll.viewport() and event.type() == QEvent.Resize and self.fit.isChecked():
            self._rescale()
        return False


# ---------------------------------------------------------------------------
# The module
# ---------------------------------------------------------------------------

class TopPerGenModule(ExplorerModule):
    name = "Top stimuli per gen by lineage"
    description = ("plot_generations: one row per generation, one panel per lineage, "
                   "best stimuli first. Copy one lineage panel or the whole figure.")

    def __init__(self):
        super().__init__()
        self.view: LineagePanelsView | None = None
        self.values: dict = {}
        # (lineage id, panel image) for the current drawing, and what's needed
        # to re-draw the whole figure as vectors on Save.
        self.panels: list[tuple[str, Image.Image]] = []
        self._whole = None  # (handler output, plotter) for Save

    def params(self):
        return [
            Param("data_type", "Data type", "choice", "mua", choices=DATA_TYPES,
                  tooltip="Which responses to import from the repository. "
                          "'GA' only has the GA Response."),
            Param("channel", "Channel", "str", "Cluster",
                  tooltip='"GA", "Cluster", "A-006", or "A-000,A-006" (summed)'),
            Param("baseline", "Baseline correction", "bool", False,
                  tooltip="Rank-based baseline correction (no-op for GA Response)."),
            Param("top_n", "Top N per generation", "int", 14, minimum=1, maximum=100,
                  tooltip="plot_generations shows ranks 1-14."),
            Param("min_lineage_stims", "Min lineage size", "int", 10,
                  minimum=0, maximum=10000,
                  tooltip="Only lineages with MORE than this many stims (counted after "
                          "the trial-type filter). plot_generations uses 10."),
            Param("border_width", "Border width (px)", "str", "75", live=False,
                  tooltip="Pixels of response-colored border added around the "
                          "thumbnail before it's scaled to the cell size."),
            Param("cell_size", "Cell size (px)", "int", 100, minimum=20, maximum=1000, step=10),
            Param("colorbar", "Colorbar", "bool", True,
                  tooltip="Response colorbar next to each panel (as plot_generations)."),
            Param("labels", "Generation / rank labels", "bool", False,
                  tooltip="Generation number left of each row and rank above each column."),
            # Not live: tick several, then Apply (each redraw renders every panel).
            *type_filter_params(what="stims (filtered before ranking)", live=False),
        ]

    def create_view(self, parent):
        self.view = LineagePanelsView(parent, on_copy_whole=self.copy_whole)
        return self.view

    def set_session(self, session):
        super().set_session(session)
        self.panels = []
        self._whole = None

    # -- drawing ------------------------------------------------------------
    def refresh(self, values, changed=None):
        self.values = dict(values)
        self.panels, self._whole = [], None
        self.view.show_message("")
        self._draw(values)

    def _draw(self, values):
        from src.analysis.ga.response_spec import ResponseSpec
        from src.analysis.modules.grouped_stims_by_response import (
            GroupedStimuliInputHandler, GroupedStimuliPlotter)

        border = parse_border_width(values["border_width"])
        data_type = values["data_type"]
        channel = "GA" if data_type == "GA" else parse_channel(values["channel"])
        if not channel:
            self._nothing("Enter a channel.")
            return

        compiled_data, spike_rates_col = load_ga_repository_data(self.session, data_type)
        spec = ResponseSpec(channel, use_baseline_correction=values["baseline"])
        prepared = spec.apply(compiled_data, spike_rates_col=spike_rates_col)
        data = prepared.data
        shown = shown_families(values)
        data = data[keep_types(data["StimType"], shown)]
        if data.empty:
            self._nothing("No stimuli of the ticked trial types.")
            return

        counts = data.groupby("Lineage")["StimSpecId"].nunique()
        # Biggest lineage (most stims of the ticked types) first; ties by id.
        big = counts[counts > values["min_lineage_stims"]]
        lineages = sorted(big.index, key=lambda lin: (-big[lin], lin))
        if not lineages:
            self._nothing(f"No lineage has more than {values['min_lineage_stims']} stimuli "
                          "of the ticked trial types.")
            return
        data = rank_within_generation(data, prepared.response_col)

        handler = GroupedStimuliInputHandler(
            response_col=prepared.response_col,
            response_key=prepared.response_key,
            path_col="ThumbnailPath",
            row_col="GenId",
            col_col="RankWithinGeneration",
            subgroup_col="Lineage",
            filter_values={"RankWithinGeneration": range(1, values["top_n"] + 1),
                           "Lineage": lineages},
        )
        whole = handler.prepare(data)
        labels = values["labels"]

        def plotter(vmin=None, vmax=None):
            return GroupedStimuliPlotter(
                cell_size=(values["cell_size"], values["cell_size"]),
                border_width=border,
                min_response=vmin, max_response=vmax,
                info_box_columns=[],
                include_colorbar=values["colorbar"],
                include_labels_for={"row", "col"} if labels else None,
                subplot_spacing=SUBPLOT_SPACING,
            )

        # One color scale for every panel: the range the whole figure would use.
        scale = plotter()
        scale.response_key = whole["response_key"]
        vmin, vmax = scale._normalize_global(whole["data"], whole["response_col"])

        self.status(f"Drawing {len(whole['subgroup_values'])} lineage panels…")
        QApplication.processEvents()
        # Mean response per shown stim (as the plotter: mean over its trials).
        shown_data = whole["data"]
        values_per_row = shown_data.apply(scale._get_response_value, axis=1) \
            if shown_data[whole["response_col"]].dtype == object \
            else shown_data[whole["response_col"]].astype(float)
        means = (shown_data.assign(_resp=values_per_row)
                 .groupby(["Lineage", "GenId", "RankWithinGeneration"])
                 .agg(path=("ThumbnailPath", "first"), resp=("_resp", "mean")))
        images = []
        for lineage in whole["subgroup_values"]:
            sub = means.loc[lineage] if lineage in means.index.get_level_values(0) else None
            cells = {} if sub is None else {
                (gen, rank): (row.path, row.resp) for (gen, rank), row in sub.iterrows()}
            images.append(draw_panel(
                cells, whole["row_values"], whole["col_values"],
                cell=values["cell_size"], border=border, spacing=SUBPLOT_SPACING,
                vmin=vmin, vmax=vmax, colorbar=values["colorbar"], labels=labels))

        n_stims = {lin: int(counts[lin]) for lin in whole["subgroup_values"]}
        self.panels = [(f"Lineage {lin}  ({n_stims[lin]} stims)", img)
                       for lin, img in zip(whole["subgroup_values"], images)]
        self._whole = (whole, plotter(vmin, vmax))
        self.view.set_panels(self.panels)
        hidden = [f for f in TYPE_FAMILIES if f not in shown]
        self.status(f"{len(self.panels)} lineages, top {values['top_n']} per generation, "
                    f"channel {prepared.channel_label}{prepared.baseline_suffix}"
                    + (f"  |  hidden: {', '.join(hidden)}" if hidden else ""))

    def _nothing(self, text):
        self.view.show_message(text)
        self.status(text)

    # -- copy / save ----------------------------------------------------------
    def whole_image(self) -> Image.Image | None:
        if not self.panels:
            return None
        return stack_vertically([img for _t, img in self.panels])

    def copy_whole(self):
        img = self.whole_image()
        if img is None:
            self.status("Nothing to copy.")
            return
        self.view.copy_image(img, "whole figure")
        self.status(f"Copied whole figure ({len(self.panels)} lineages)")

    def save(self, folder):
        written = []
        if not self.panels:
            return written
        path = os.path.join(folder, "top_per_gen_by_lineage.png")
        self.whole_image().save(path)
        written.append(path)
        # Vector versions of the whole figure, drawn by the plotter in one go.
        if self._whole is not None:
            whole, plotter = self._whole
            fig = plotter.compute(whole)
            for fmt in ("svg", "pdf"):
                out = os.path.join(folder, f"top_per_gen_by_lineage.{fmt}")
                try:
                    fig.write_image(out, format=fmt, width=fig.layout.width,
                                    height=fig.layout.height)
                    written.append(out)
                except Exception as exc:
                    print(f"Could not save {fmt}: {exc}")
        for title, img in self.panels:
            lineage = title.split()[1]
            out = os.path.join(folder, f"lineage_{lineage}.png")
            img.save(out)
            written.append(out)
        return written
