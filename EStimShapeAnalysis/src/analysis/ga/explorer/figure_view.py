"""
Qt widget that shows whatever a FigureModule returns: a matplotlib Figure
(embedded canvas + the usual zoom/pan toolbar) or a plotly figure (rendered to
an image with kaleido, with zoom controls and an "Open interactive" button that
opens the hover-able version in the browser).
"""

from __future__ import annotations

import os

from PyQt5.QtCore import QEvent, Qt
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (QCheckBox, QHBoxLayout, QLabel, QPushButton,
                             QScrollArea, QSpinBox, QVBoxLayout, QWidget)

MPL_SAVE_DPI = 300
MPL_CLIPBOARD_DPI = 200


def _is_plotly(fig) -> bool:
    return type(fig).__module__.startswith("plotly")


class FigureView(QWidget):
    def __init__(self, parent=None, keep_size=False, fit_height=False):
        """keep_size: show matplotlib figures at their own size (scrolling if
        needed) instead of stretching them to the window, so what you see is
        what gets saved. Use it for layout-sensitive figures.
        fit_height (with keep_size): by default scale the whole figure (text
        included, layout unchanged) so its full height fits the window; wide
        figures scroll sideways. A checkbox above the figure turns it off."""
        super().__init__(parent)
        self._keep_size = keep_size
        self._fit_height = fit_height
        self._mpl = None   # (fig, canvas, scroll, size_in, base_dpi) when fitting
        self._fig = None
        self._pixmap: QPixmap | None = None

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._placeholder = QLabel("Nothing to show yet.")
        self._placeholder.setAlignment(Qt.AlignCenter)
        self._placeholder.setStyleSheet("color: gray; font-size: 16px;")
        self._layout.addWidget(self._placeholder)
        self._content: QWidget | None = None

    # ------------------------------------------------------------- display
    def show_figure(self, fig):
        self._clear()
        self._fig = fig
        if fig is None:
            self._placeholder.show()
            return
        self._placeholder.hide()
        if _is_plotly(fig):
            self._content = self._build_plotly_view(fig)
        else:
            self._content = self._build_mpl_view(fig)
        self._layout.addWidget(self._content)

    def _clear(self):
        if self._content is not None:
            self._layout.removeWidget(self._content)
            self._content.deleteLater()
            self._content = None
        self._pixmap = None
        self._fig = None
        if self._mpl is not None:
            fig, base_dpi = self._mpl[0], self._mpl[4]
            fig.set_dpi(base_dpi)   # saved / reused figures keep their own dpi
            self._mpl = None

    def _build_mpl_view(self, fig):
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
        from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

        box = QWidget()
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        size_in = fig.get_size_inches().copy()
        canvas = FigureCanvas(fig)
        lay.addWidget(NavigationToolbar(canvas, box))
        if self._keep_size:
            # Pin the canvas to the figure's own size; the scroll area absorbs
            # any difference with the window.
            scroll = QScrollArea()
            scroll.setWidget(canvas)
            scroll.setStyleSheet("background: white;")
            if self._fit_height:
                fit = QCheckBox("Fit height to window")
                fit.setChecked(True)
                fit.setToolTip("Scale the figure so the whole probe and legend are "
                               "visible. Off = actual size (scroll).")
                fit.toggled.connect(lambda _on: self._fit_mpl())
                lay.addWidget(fit)
                self._mpl = (fig, canvas, scroll, size_in, fig.dpi, fit)
                scroll.viewport().installEventFilter(self)
            lay.addWidget(scroll, stretch=1)
            self._pin_canvas(fig, canvas, size_in, fig.dpi)
        else:
            lay.addWidget(canvas, stretch=1)
        canvas.draw_idle()
        return box

    @staticmethod
    def _pin_canvas(fig, canvas, size_in, dpi):
        ratio = canvas.devicePixelRatioF() or 1.0
        fig.set_dpi(dpi)
        w, h = (int(round(v * dpi / ratio)) for v in size_in)
        canvas.setFixedSize(w, h)
        fig.set_size_inches(size_in)   # undo any rounding from the resize event
        canvas.draw_idle()

    def _fit_mpl(self):
        """Scale the figure's dpi so its height matches the visible area."""
        if self._mpl is None:
            return
        fig, canvas, scroll, size_in, base_dpi, fit = self._mpl
        dpi = base_dpi
        if fit.isChecked():
            ratio = canvas.devicePixelRatioF() or 1.0
            # leave room for the horizontal scrollbar when the figure is wide
            avail = scroll.viewport().height() + (
                0 if scroll.horizontalScrollBar().isVisible() else
                -scroll.horizontalScrollBar().sizeHint().height()) - 4
            if avail > 50:
                dpi = avail * ratio / size_in[1]
        self._pin_canvas(fig, canvas, size_in, dpi)

    def _build_plotly_view(self, fig):
        box = QWidget()
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)

        bar = QHBoxLayout()
        self._fit_check = QCheckBox("Fit to window")
        self._fit_check.setChecked(True)
        self._zoom_spin = QSpinBox()
        self._zoom_spin.setRange(10, 400)
        self._zoom_spin.setSingleStep(10)
        self._zoom_spin.setValue(100)
        self._zoom_spin.setSuffix(" %")
        self._zoom_spin.setEnabled(False)
        open_btn = QPushButton("Open interactive (browser)")
        open_btn.setToolTip("Opens the plotly figure in your browser, with hover info.")
        open_btn.clicked.connect(lambda: fig.show())
        bar.addWidget(self._fit_check)
        bar.addWidget(QLabel("Zoom:"))
        bar.addWidget(self._zoom_spin)
        bar.addStretch(1)
        bar.addWidget(open_btn)
        lay.addLayout(bar)

        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self._scroll = QScrollArea()
        self._scroll.setWidget(self._image_label)
        self._scroll.setWidgetResizable(False)
        self._scroll.setStyleSheet("background: white;")
        # Re-fit whenever the visible area changes size (incl. first layout).
        self._scroll.viewport().installEventFilter(self)
        lay.addWidget(self._scroll, stretch=1)

        try:
            png = fig.to_image(format="png", width=fig.layout.width,
                               height=fig.layout.height)
            img = QImage.fromData(png, "PNG")
            self._pixmap = QPixmap.fromImage(img)
        except Exception as exc:  # kaleido missing or failed
            self._image_label.setText(
                f"Could not render the plotly figure to an image ({exc}).\n"
                f"Use 'Open interactive (browser)' instead.")
            self._image_label.adjustSize()
            return box

        self._fit_check.toggled.connect(self._on_fit_toggled)
        self._zoom_spin.valueChanged.connect(lambda _v: self._rescale())
        self._rescale()
        return box

    def _on_fit_toggled(self, fit):
        self._zoom_spin.setEnabled(not fit)
        self._rescale()

    def _rescale(self):
        if self._pixmap is None:
            return
        if self._fit_check.isChecked():
            vp = self._scroll.viewport().size()
            factor = min(1.0, (vp.width() - 4) / self._pixmap.width(),
                         (vp.height() - 4) / self._pixmap.height())
            scaled = self._pixmap.scaledToWidth(max(50, int(self._pixmap.width() * factor)),
                                                Qt.SmoothTransformation)
        else:
            factor = self._zoom_spin.value() / 100.0
            scaled = self._pixmap.scaledToWidth(int(self._pixmap.width() * factor),
                                                Qt.SmoothTransformation)
        self._image_label.setPixmap(scaled)
        self._image_label.resize(scaled.size())

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Resize:
            if self._pixmap is not None and self._fit_check.isChecked():
                self._rescale()
            elif self._mpl is not None and obj is self._mpl[2].viewport():
                self._fit_mpl()
        return False

    # ----------------------------------------------------------- clipboard
    def clipboard_image(self) -> QImage | None:
        """The whole figure as an image (not just the visible part): matplotlib
        rendered at MPL_CLIPBOARD_DPI, plotly at its full rendered size."""
        if self._fig is None:
            return None
        if _is_plotly(self._fig):
            return self._pixmap.toImage() if self._pixmap is not None else None
        import io
        buf = io.BytesIO()
        self._fig.savefig(buf, format="png", dpi=MPL_CLIPBOARD_DPI, bbox_inches="tight",
                          facecolor="white")
        return QImage.fromData(buf.getvalue(), "PNG")

    # ---------------------------------------------------------------- save
    def save(self, folder: str, basename: str) -> list[str]:
        """Write the figure in several formats. A format that fails (e.g. no
        PDF support in kaleido) is skipped with a printed warning, so the
        others and the explorer's config.json are still written."""
        if self._fig is None:
            return []
        fig = self._fig
        base = os.path.join(folder, basename)
        if _is_plotly(fig):
            size = dict(width=fig.layout.width, height=fig.layout.height)
            writers = {
                "png": lambda path: fig.write_image(path, scale=2, **size),
                "pdf": lambda path: fig.write_image(path, **size),
                "html": lambda path: fig.write_html(path),
            }
        else:
            writers = {ext: (lambda path: fig.savefig(path, dpi=MPL_SAVE_DPI, bbox_inches="tight"))
                       for ext in ("png", "svg", "pdf")}
        written = []
        for ext, write in writers.items():
            path = f"{base}.{ext}"
            try:
                write(path)
                written.append(path)
            except Exception as exc:
                print(f"Could not save {path}: {exc}")
        if not written:
            raise RuntimeError("Could not save the figure in any format")
        return written
