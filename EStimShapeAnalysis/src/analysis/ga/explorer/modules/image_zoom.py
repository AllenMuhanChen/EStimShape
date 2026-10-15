"""
Zoom shared by the thumbnail modules: one zoom factor and one zoom center,
applied the same way to every image.

Center: (0, 0) is the image center; x = -1 / +1 are the left / right edges
and y = -1 / +1 the bottom / top edges. The zoom window is kept inside the
image, so a center near an edge is pulled in.
"""

from __future__ import annotations

from PIL import Image

from src.analysis.ga.explorer.explorer_module import Param

NO_ZOOM = (1.0, 0.0, 0.0)


def zoom_params(**kwargs) -> list[Param]:
    """The three zoom params; ``kwargs`` (e.g. live=True) go to each Param."""
    return [
        Param("zoom", "Image zoom (x)", "float", 1.0, minimum=1.0, maximum=20.0,
              step=0.25, decimals=2,
              tooltip="Zoom into every thumbnail by this factor (1 = no zoom).", **kwargs),
        Param("zoom_x", "Zoom center x", "float", 0.0, minimum=-1.0, maximum=1.0,
              step=0.05, decimals=2,
              tooltip="0 = image center, -1 = left edge, +1 = right edge.", **kwargs),
        Param("zoom_y", "Zoom center y", "float", 0.0, minimum=-1.0, maximum=1.0,
              step=0.05, decimals=2,
              tooltip="0 = image center, -1 = bottom edge, +1 = top edge.", **kwargs),
    ]


def zoom_from_values(values) -> tuple[float, float, float]:
    return (float(values.get("zoom", 1.0)), float(values.get("zoom_x", 0.0)),
            float(values.get("zoom_y", 0.0)))


def zoom_box(size, zoom, cx, cy):
    """(left, upper, right, lower) of the zoom window in an image of ``size``,
    or None for no zoom."""
    if zoom <= 1.0:
        return None
    w, h = size
    cw, ch = w / zoom, h / zoom
    x0 = min(max(0.0, w / 2 * (1 + cx) - cw / 2), w - cw)
    y0 = min(max(0.0, h / 2 * (1 - cy) - ch / 2), h - ch)
    return (x0, y0, x0 + cw, y0 + ch)


def zoom_crop(img: Image.Image, zoom, cx, cy, out_size=None,
              resample=Image.LANCZOS) -> Image.Image:
    """``img`` zoomed in ``zoom`` times around (cx, cy), resized to
    ``out_size`` (default: its own size)."""
    out_size = out_size or img.size
    box = zoom_box(img.size, zoom, cx, cy)
    if box is None and out_size == img.size:
        return img
    return img.resize(out_size, resample, box=box)
