"""
Hand-placed noise for the noise example figures (pit_stim_noise_example).

place_noise_circles() opens a small window on the clean sample png:
  - pick which circle you are placing (Circle 1 / Circle 2),
  - left-click on the image to put that circle's centre there,
  - set its radius with the slider (or the mouse wheel over the image),
  - press Done (or close the window).
The circles come back as [(x_deg, y_deg, radius_deg), ...] in screen degrees (+y up, (0, 0) =
fixation), and are printed so they can be pasted into NOISE_CIRCLES to reuse them.

noise_map_from_circles() turns circles into a noise-probability map the same way xper's
GaussianNoiseMapper.generateTruncatedGaussianNoiseMap does for one circle: noise_chance inside
the circle, a Gaussian fade outside its edge. Two circles are combined with the max.
"""

from __future__ import annotations

import numpy as np
from matplotlib.figure import Figure
from matplotlib.patches import Circle
from matplotlib.widgets import Button, RadioButtons, Slider


def png_to_deg(px: float, py: float, sample_spec: dict, shape_hw: tuple) -> tuple:
    """Png pixel (x right, y down) -> screen degrees (+y up)."""
    h, w = shape_hw
    return (sample_spec['x_center_deg'] + (px - w / 2) * sample_spec['width_deg'] / w,
            sample_spec['y_center_deg'] - (py - h / 2) * sample_spec['height_deg'] / h)


def deg_to_png(x: float, y: float, sample_spec: dict, shape_hw: tuple) -> tuple:
    """Screen degrees (+y up) -> png pixel (x right, y down)."""
    h, w = shape_hw
    return (w / 2 + (x - sample_spec['x_center_deg']) * w / sample_spec['width_deg'],
            h / 2 - (y - sample_spec['y_center_deg']) * h / sample_spec['height_deg'])


def noise_map_from_circles(circles, sample_spec: dict, shape_hw: tuple, noise_chance: float,
                           edge_sigma_deg: float) -> np.ndarray:
    """Noise probability per sample png pixel: noise_chance inside each circle, and outside it
    noise_chance * exp(-0.5 * 2 * (d / sigma)^2) with d the distance past the edge (xper's
    truncated Gaussian, sigmaX = sigmaY = sigma). Circles combine with the max."""
    h, w = shape_hw
    px_per_deg = w / sample_spec['width_deg']
    yy, xx = np.mgrid[0:h, 0:w]
    prob = np.zeros((h, w))
    sigma = max(edge_sigma_deg * px_per_deg, 1e-6)
    for x, y, r in circles:
        cx, cy = deg_to_png(x, y, sample_spec, shape_hw)
        past_edge = np.maximum(np.hypot(xx - cx, yy - cy) - r * px_per_deg, 0.0)
        prob = np.maximum(prob, noise_chance * np.exp(-(past_edge / sigma) ** 2))
    return prob


def place_noise_circles(sample_rgb: np.ndarray, sample_spec: dict, fixation_xy=None,
                        initial=None, n_circles: int = 2, view_deg: float | None = None) -> list:
    """Open the placement window and return [(x_deg, y_deg, radius_deg), ...]."""
    shape_hw = sample_rgb.shape[:2]
    deg_per_px = sample_spec['width_deg'] / shape_hw[1]
    default_r = 0.1 * sample_spec['width_deg']
    circles = [list(c) for c in (initial or [])][:n_circles]
    state = {'active': 0}

    # its own Qt window (not pyplot), so it opens and blocks whatever matplotlib backend is set,
    # e.g. PyCharm's plot pane, which shows pyplot figures as static images
    from PyQt5.QtWidgets import QApplication, QDialog, QVBoxLayout
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
    app = QApplication.instance() or QApplication([])
    dialog = QDialog()
    dialog.setWindowTitle("Place noise circles")
    fig = Figure(figsize=(9, 8))
    canvas = FigureCanvasQTAgg(fig)
    toolbar = NavigationToolbar2QT(canvas, dialog)
    layout = QVBoxLayout(dialog)
    layout.addWidget(toolbar)
    layout.addWidget(canvas)
    ax = fig.add_axes([0.05, 0.2, 0.7, 0.75])
    ax.imshow(sample_rgb, interpolation="nearest")
    ax.set_axis_off()
    if fixation_xy is not None:
        ax.plot(*fixation_xy, marker="s", color="red", markersize=6)
    if view_deg is not None and fixation_xy is not None:  # start on the figure's field of view
        half = view_deg / deg_per_px / 2
        ax.set_xlim(fixation_xy[0] - half, fixation_xy[0] + half)
        ax.set_ylim(fixation_xy[1] + half, fixation_xy[1] - half)
    ax.set_title("Click to place the selected circle; slider / wheel = radius")

    colors = ["tab:cyan", "tab:orange", "tab:green", "tab:pink"]
    patches = []
    for i in range(n_circles):
        p = Circle((0, 0), 1, facecolor=colors[i % 4], alpha=0.25, edgecolor=colors[i % 4],
                   linewidth=2, visible=False)
        ax.add_patch(p)
        patches.append(p)

    radio = RadioButtons(fig.add_axes([0.78, 0.6, 0.18, 0.2]),
                         [f"Circle {i + 1}" for i in range(n_circles)])
    slider = Slider(fig.add_axes([0.15, 0.1, 0.55, 0.04]), "radius (deg)", 0.05,
                    sample_spec['width_deg'] / 2,
                    valinit=circles[0][2] if circles else default_r)
    done = Button(fig.add_axes([0.78, 0.1, 0.15, 0.06]), "Done")

    def redraw():
        for i, p in enumerate(patches):
            if i < len(circles):
                x, y, r = circles[i]
                p.center = deg_to_png(x, y, sample_spec, shape_hw)
                p.set_radius(r / deg_per_px)
                p.set_visible(True)
            p.set_linewidth(3 if i == state['active'] else 1.5)
        fig.canvas.draw_idle()

    def on_radio(label):
        state['active'] = int(label.split()[-1]) - 1
        if state['active'] < len(circles):
            slider.set_val(circles[state['active']][2])
        redraw()

    def on_slider(val):
        if state['active'] < len(circles):
            circles[state['active']][2] = float(val)
            redraw()

    def on_click(event):
        if event.inaxes is not ax or event.button != 1 or toolbar.mode:
            return  # ignore clicks while the zoom/pan tool is on
        x, y = png_to_deg(event.xdata, event.ydata, sample_spec, shape_hw)
        i = state['active']
        if i < len(circles):
            circles[i][:2] = [x, y]
        else:  # place circles in order
            while len(circles) < i:
                circles.append([x, y, float(slider.val)])
            circles.append([x, y, float(slider.val)])
        redraw()

    def on_scroll(event):
        if event.inaxes is ax:
            slider.set_val(np.clip(slider.val * (1.1 if event.button == 'up' else 1 / 1.1),
                                   slider.valmin, slider.valmax))

    radio.on_clicked(on_radio)
    slider.on_changed(on_slider)
    done.on_clicked(lambda _: dialog.accept())
    canvas.mpl_connect('button_press_event', on_click)
    canvas.mpl_connect('scroll_event', on_scroll)
    redraw()
    dialog.resize(900, 850)
    dialog.exec_()  # blocks until Done or the window is closed

    if not circles:
        raise RuntimeError("No noise circles were placed; click on the image before pressing Done.")
    result = [tuple(round(float(v), 3) for v in c) for c in circles]
    if len(result) < n_circles:
        print(f"Warning: only {len(result)} of {n_circles} noise circles placed.")
    print(f"Noise circles (paste into NOISE_CIRCLES to reuse): {result}")
    return result
