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

Nothing is written to disk unless you press Save view: whole figure (png,
svg, pdf) plus one png per lineage panel.
"""

from __future__ import annotations

import os
import tempfile

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


def figures_to_images(figs) -> list[Image.Image]:
    """Render plotly figures to PIL images in one kaleido session."""
    import plotly.io as pio
    with tempfile.TemporaryDirectory() as tmp:
        paths = [os.path.join(tmp, f"{i}.png") for i in range(len(figs))]
        pio.write_images(list(figs), paths, format="png",
                         width=[f.layout.width for f in figs],
                         height=[f.layout.height for f in figs])
        images = []
        for p in paths:
            with Image.open(p) as im:
                images.append(im.convert("RGB"))
    return images


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
        figs = []
        for lineage in whole["subgroup_values"]:
            one = dict(whole)
            one["data"] = whole["data"][whole["data"]["Lineage"] == lineage]
            one["subgroup_values"] = [lineage]  # rows stay = every generation shown
            figs.append(plotter(vmin, vmax).compute(one))
        images = figures_to_images(figs)

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
