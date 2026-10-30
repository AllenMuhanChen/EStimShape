"""
PIT version of nafc_stim_noise_example: the same figure, but you give the exact GA stim ids of
the sample (= match) and of the two distractors (for a PIT cell, each distractor shares one of
the two components the cell encodes a combination of).

The sample, its noise map and the match come from the newest NAFC trial whose sample is the GA
stim (same lookup as nafc_stim_noise_example). Each distractor is drawn from that trial's NAFC
choice png when one of the sample's trials offered it; otherwise from its GA generation png.

A GA png is rendered at the GA stim's own size (StimSize), while NAFC draws every choice at one
choice size, so a GA png is rescaled to where NAFC would have drawn it:
    scale = s_match * StimSize(match) / StimSize(distractor)
where s_match = (shape size in the match's NAFC choice png) / (shape size in the match's GA png),
shape size = sqrt(shape area) in degrees. Colour/texture are as the GA rendered them.

Read-only: this script only runs SELECT queries and never writes to any database.

Output: <SAVE_ROOT>/<session>/pit_noise_example/<sample_ga_id>_<timestamp>/
  noisy_stimulus.png, sample_panel.png, choices_panel.png, fixation_panel.png, figure.png,
  config.json.
"""

from __future__ import annotations

import json
import os
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
import xmltodict
from PIL import Image

from src.fig.nafc_stim_noise_example import (
    add_choice_ga_ids, choices_triangle_panel, composite_noise, estimate_background,
    find_nafc_samples_for_ga_stim, fixation_in_sample_pixels, fixation_panel,
    generate_twinkle_noise_frames, load_noise_probability, load_rgb, locate_local_file,
    plot_example_figure, read_choice_specs, read_system_var, resample, rescale_noise_chance,
    round_corners, shape_mask, zoom_panel)
from src.fig.noise_circle_gui import deg_to_png, noise_map_from_circles, place_noise_circles


def main():
    # ---- Parameters -------------------------------------------------------------------------
    SESSION_ID = None              # session the GA stims belong to; None = keep current context
    SAMPLE_GA_ID = None            # GA stim id of the sample (shown as the match too)
    DISTRACTOR_1_GA_ID = None      # GA stim id sharing the first component
    DISTRACTOR_2_GA_ID = None      # GA stim id sharing the second component
    DISTRACTOR_SOURCE = "nafc_if_available"  # "nafc_if_available": a distractor's NAFC choice png
                                   # if a trial of this sample offered it, else its GA png;
                                   # "ga": always the GA png (both distractors rendered alike)
    NAFC_STIM_ID = None            # None = newest NAFC trial of the sample (preferring one that
                                   # offered the distractors); or an NAFC StimSpec id
    NOISE_CHANCE = 1.0             # noise amount: peak chance a pixel is noise (0-1).
                                   # None = as the trial used.
    NOISE_CIRCLES = None           # None = the NAFC trial's noise map; "gui" = place circles by hand
                                   # in a window; or [(x_deg, y_deg, radius_deg), ...] in screen
                                   # degrees (+y up, (0, 0) = fixation), e.g. as printed by the gui
    N_NOISE_CIRCLES = 2            # how many circles the gui places
    NOISE_EDGE_SIGMA_DEG = 0.1     # Gaussian fade outside each circle's edge (like xper's
                                   # truncated-Gaussian noise map); 0 = hard edge
    RANDOM_SEED = None             # int for a reproducible noise pattern, None = new each run
    NAFC_STIMULI_DIR = None        # None = <base_dir>/<nafc_database>/stimuli (searched for pngs)
    GA_PNG_DIR = None              # None = <base_dir>/<ga_database>/stimuli/ga/pngs
    # Figure
    ZOOM = 3                       # sample panel zoom factor (1 = whole sample png); sets the field
                                   # of view (deg) shared by all three panels
    ZOOM_CENTER = "fixation"       # "fixation", (x, y) in -1..1 of the sample png (+y up), or None
                                   # = centre of the shape (+ fixation)
    CHOICE_ORDER = ("match", "distractor_1", "distractor_2")  # top, bottom-left, bottom-right
    IMAGE_ZOOM = 1.0               # enlarges the sample and choice images only
    CHOICE_MARGIN = 0.15           # gap between the choices and the panel edge (fraction of panel)
    BACKGROUND_THRESHOLD = 2       # 0-255; shape = any channel differs from the png background by more
    EDGE_BAND_PX = 1               # px inside the shape's edge whose gray share is subtracted out
    SCREEN_COLOR = (0, 0, 0)       # monitor background
    SHOW_FIXATION = True           # fixation square at screen (0, 0) on the sample panel
    SHOW_FIXATION_PANEL = True     # extra leftmost panel with only the fixation square
    SHOW_EYE = True                # cyan eye symbol: on fixation (left, middle), on choices (right)
    EYE_SIZE = 0.18                # eye width as a fraction of the panel
    EYE_COLOR = "cyan"
    EYE_ALPHA = 0.7                # eye opacity (1 = solid, 0 = invisible)
    TWO_ROWS = True                # top row: no EStim (fainter eyes on SPLIT_EYE_CHOICES);
                                   # bottom row: EStim (eye on the match only)
    SPLIT_EYE_CHOICES = ("match", "distractor_1")  # choices with an eye in the top row
    SPLIT_EYE_ALPHA = 0.4          # opacity of those eyes
    SHOW_BOLTS = True              # thunderbolt left of each row (no EStim dashed, EStim orange)
    BOLT_SIZE = 0.3                # bolt height as a fraction of the panel height
    BOLT_MARGIN = 0.1              # gap between the bolt and the first panel, fraction of panel width
    FIXATION_SIZE_DEG = 0.5        # None = xper_fixation_point_size from the NAFC SystemVar table
    FIXATION_COLOR = None          # (r, g, b) 0-255; None = xper_fixation_point_color from SystemVar
    PANEL_PX = None                # None = native resolution; or a pixel size for each panel
    CORNER_RADIUS = 0.0            # rounded panel corners, fraction of the panel size (0 = square)
    SAVE_ROOT = "/home/connorlab/Documents/plots"
    SHOW_PLOTS = True
    # -----------------------------------------------------------------------------------------

    if None in (SAMPLE_GA_ID, DISTRACTOR_1_GA_ID, DISTRACTOR_2_GA_ID):
        raise RuntimeError("Set SAMPLE_GA_ID, DISTRACTOR_1_GA_ID and DISTRACTOR_2_GA_ID at the top of main().")

    from src.startup import context
    if SESSION_ID is not None:
        from src.startup.apply_session_context import apply_session_context
        apply_session_context(SESSION_ID)

    from clat.util.connection import Connection
    nafc_conn = Connection(context.nafc_database)
    ga_conn = Connection(context.ga_database)

    stimuli_dir = NAFC_STIMULI_DIR or f"{context.base_dir}/{context.nafc_database}/stimuli"
    ga_png_dir = GA_PNG_DIR or f"{context.base_dir}/{context.ga_database}/stimuli/ga/pngs"
    distractor_ids = {"distractor_1": DISTRACTOR_1_GA_ID, "distractor_2": DISTRACTOR_2_GA_ID}

    candidates = find_nafc_samples_for_ga_stim(nafc_conn, SAMPLE_GA_ID)
    if not candidates:
        raise RuntimeError(
            f"No NAFC trial in {context.nafc_database} has GA stim {SAMPLE_GA_ID} as its sample "
            f"(no non-removed BaseMStickId trial with a noise map). Check SESSION_ID and SAMPLE_GA_ID.")
    if NAFC_STIM_ID is not None:
        candidates = [c for c in candidates if c['nafc_stim_id'] == NAFC_STIM_ID]
        if not candidates:
            raise RuntimeError(f"NAFC stim {NAFC_STIM_ID} is not a (non-removed) trial of GA stim {SAMPLE_GA_ID}.")

    # newest trial that offered the most of the distractors (ties: newest)
    best, best_count = None, -1
    for candidate in candidates:
        choices = read_choice_specs(nafc_conn, candidate['choice_obj_ids'])
        add_choice_ga_ids(nafc_conn, ga_conn, candidate, choices)
        count = sum(any(c['ga_id'] == d for c in choices) for d in distractor_ids.values())
        if count > best_count:
            best, best_count, trial_choices = candidate, count, choices
    chosen = best
    print(f"Using NAFC trial {chosen['nafc_stim_id']} ({chosen['stim_type']})")

    match = next((c for c in trial_choices if c['label'] == 'match'), None)
    if match is None:
        raise RuntimeError(f"No match among trial {chosen['nafc_stim_id']}'s choices.")
    match['local_png'] = locate_local_file(match['png_path'], stimuli_dir)
    shown = {"match": {**match, 'ga_id': SAMPLE_GA_ID, 'source': 'nafc'}}

    match_scale = None
    for role, ga_id in distractor_ids.items():
        nafc_choice = next((c for c in trial_choices
                            if c['ga_id'] == ga_id and c['label'] != 'match'), None)
        if nafc_choice is not None and DISTRACTOR_SOURCE == "nafc_if_available":
            nafc_choice['local_png'] = locate_local_file(nafc_choice['png_path'], stimuli_dir)
            shown[role] = {**nafc_choice, 'source': 'nafc'}
            continue
        if match_scale is None:
            match_scale = nafc_over_ga_scale(ga_conn, match, SAMPLE_GA_ID, ga_png_dir,
                                             SCREEN_COLOR, BACKGROUND_THRESHOLD)
        shown[role] = ga_png_choice(ga_conn, ga_id, SAMPLE_GA_ID, match_scale, ga_png_dir)
    for role in CHOICE_ORDER:
        c = shown[role]
        print(f"{role:>13}: GA id {c['ga_id']}  ({c['source']} png)  {c['local_png']}")

    sample_png = locate_local_file(chosen['png_path'], stimuli_dir)
    noise_map_png = locate_local_file(chosen['noise_map_path'], stimuli_dir)
    sample_rgb = load_rgb(sample_png, SCREEN_COLOR)
    noise_probability = load_noise_probability(noise_map_png, sample_rgb.shape[:2])
    trial_peak = float(noise_probability.max())
    noise_circles = NOISE_CIRCLES
    if noise_circles is None:
        if NOISE_CHANCE is not None:
            noise_probability = rescale_noise_chance(noise_probability, NOISE_CHANCE)
    else:
        if noise_circles == "gui":
            view_deg = min(sample_rgb.shape[:2]) / ZOOM * chosen['width_deg'] / sample_rgb.shape[1]
            noise_circles = place_noise_circles(
                sample_rgb, chosen, deg_to_png(0, 0, chosen, sample_rgb.shape[:2]),
                n_circles=N_NOISE_CIRCLES, view_deg=view_deg)
        noise_probability = noise_map_from_circles(
            noise_circles, chosen, sample_rgb.shape[:2],
            NOISE_CHANCE if NOISE_CHANCE is not None else trial_peak, NOISE_EDGE_SIGMA_DEG)
    rng = np.random.default_rng(RANDOM_SEED)
    noise = generate_twinkle_noise_frames(noise_probability, chosen['color'], 1, rng)[0]
    noisy = composite_noise(sample_rgb, noise)

    session_name = SESSION_ID or context.ga_database
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(SAVE_ROOT, str(session_name), "pit_noise_example", f"{SAMPLE_GA_ID}_{timestamp}")
    os.makedirs(out_dir, exist_ok=True)
    Image.fromarray(noisy).save(os.path.join(out_dir, "noisy_stimulus.png"))

    background = estimate_background(sample_rgb)
    size_deg = FIXATION_SIZE_DEG
    if size_deg is None:
        size_deg = float(read_system_var(nafc_conn, "xper_fixation_point_size")[0])
    color = FIXATION_COLOR
    if color is None:
        color = tuple(int(round(float(v) * 255))
                      for v in read_system_var(nafc_conn, "xper_fixation_point_color")[:3])
    fixation = fixation_in_sample_pixels(chosen, sample_rgb.shape[:2], size_deg, color)

    sample_deg_per_px = chosen['width_deg'] / sample_rgb.shape[1]
    sample_panel = zoom_panel(noisy, sample_rgb, ZOOM, ZOOM_CENTER, None, background,
                              BACKGROUND_THRESHOLD, fixation if SHOW_FIXATION else None, IMAGE_ZOOM)
    field_deg = sample_panel.width * sample_deg_per_px  # every panel shows this many degrees
    print(f"Panel field of view: {field_deg:.2f} deg")
    choices_panel = choices_triangle_panel([shown[role] for role in CHOICE_ORDER], field_deg,
                                           background, BACKGROUND_THRESHOLD, CHOICE_MARGIN,
                                           SCREEN_COLOR, EDGE_BAND_PX, IMAGE_ZOOM)
    panels = {"sample_panel": sample_panel, "choices_panel": choices_panel}
    # eye positions as fractions of each panel (x right, y down)
    crop_x, crop_y = sample_panel.info['origin_png_px']
    fx, fy = sample_panel.info.get('fixation_center',
                                   (fixation['xy'][0] - crop_x, fixation['xy'][1] - crop_y))
    eyes = {"sample_panel": (fx / sample_panel.width, fy / sample_panel.height)}
    centers = dict(zip(CHOICE_ORDER, choices_panel.info['choice_centers']))
    if SHOW_FIXATION_PANEL:
        fixation_only = fixation_panel(sample_panel.width, fixation, background)
        panels = {"fixation_panel": fixation_only, **panels}
        fx, fy = fixation_only.info['fixation_center']
        eyes["fixation_panel"] = (fx / fixation_only.width, fy / fixation_only.height)
    for name, panel in panels.items():
        if PANEL_PX is not None:  # nearest keeps noise pixels crisp; choices are smooth-resampled
            panel = (resample(panel, (PANEL_PX, PANEL_PX)) if name == "choices_panel"
                     else panel.resize((PANEL_PX, PANEL_PX), Image.NEAREST))
        panels[name] = round_corners(panel, CORNER_RADIUS)
        panels[name].save(os.path.join(out_dir, f"{name}.png"))

    # each row: per panel, a list of (x, y, opacity) eyes
    def eye_row(choice_eyes):
        return [[(*eyes[name], EYE_ALPHA)] if name in eyes else choice_eyes for name in panels]
    estim_row = eye_row([(*centers["match"], EYE_ALPHA)])
    no_estim_row = eye_row([(*centers[role], SPLIT_EYE_ALPHA) for role in SPLIT_EYE_CHOICES])
    rows = [no_estim_row, estim_row] if TWO_ROWS else [estim_row]
    bolts = ["no_estim", "estim"] if TWO_ROWS else ["estim"]
    if not SHOW_EYE:
        rows = [[[] for _ in panels] for _ in rows]
    fig = plot_example_figure(list(panels.values()), rows, EYE_SIZE, EYE_COLOR,
                              bolts if SHOW_BOLTS else None, BOLT_SIZE, BOLT_MARGIN)
    # dpi high enough that each panel is saved at (at least) its native pixel size
    panel_inches = fig.axes[0].get_window_extent().width / fig.dpi
    dpi = max(200, int(np.ceil(max(p.width for p in panels.values()) / panel_inches)))
    fig.savefig(os.path.join(out_dir, "figure.png"), dpi=dpi, bbox_inches="tight")

    config = {
        "session_id": SESSION_ID,
        "ga_database": context.ga_database,
        "nafc_database": context.nafc_database,
        "sample_ga_id": SAMPLE_GA_ID,
        "distractor_ga_ids": distractor_ids,
        "distractor_source": DISTRACTOR_SOURCE,
        "nafc_stim_id": chosen['nafc_stim_id'],
        "nafc_stim_type": chosen['stim_type'],
        "sample_png": sample_png,
        "noise_map_png": noise_map_png,
        "noise_color_rgb": list(chosen['color']),
        "trial_noise_chance": trial_peak,
        "noise_chance": NOISE_CHANCE,
        "noise_circles_deg": None if noise_circles is None else [list(c) for c in noise_circles],
        "noise_edge_sigma_deg": NOISE_EDGE_SIGMA_DEG if noise_circles is not None else None,
        "choices_shown": {role: {'ga_id': c['ga_id'], 'source': c['source'], 'png': c['local_png'],
                                 'dimensions_deg': [c['width_deg'], c['height_deg']],
                                 **({'ga_png_scale': c['ga_png_scale']} if 'ga_png_scale' in c else {})}
                          for role, c in shown.items()},
        "nafc_over_ga_scale_of_match": match_scale,
        "zoom": ZOOM,
        "zoom_center": ZOOM_CENTER,
        "image_zoom": IMAGE_ZOOM,
        "choice_order": list(CHOICE_ORDER),
        "choice_margin": CHOICE_MARGIN,
        "field_of_view_deg": field_deg,
        "eye": {"size": EYE_SIZE, "color": EYE_COLOR, "alpha": EYE_ALPHA,
                "split_alpha": SPLIT_EYE_ALPHA, "split_choices": list(SPLIT_EYE_CHOICES)} if SHOW_EYE else None,
        "two_rows": TWO_ROWS,
        "bolts": {"size": BOLT_SIZE, "margin": BOLT_MARGIN} if SHOW_BOLTS else None,
        "fixation_panel": SHOW_FIXATION_PANEL,
        "background_threshold": BACKGROUND_THRESHOLD,
        "edge_band_px": EDGE_BAND_PX,
        "screen_color": list(SCREEN_COLOR),
        "fixation": {'size_deg': fixation['size_deg'], 'color': list(fixation['color'])},
        "panel_px": PANEL_PX,
        "corner_radius": CORNER_RADIUS,
        "random_seed": RANDOM_SEED,
    }
    with open(os.path.join(out_dir, "config.json"), "w") as f:
        json.dump(config, f, indent=2)
    print(f"Saved to {out_dir}")

    if SHOW_PLOTS:
        plt.show()


# ---------------------------------------------------------------------------
# GA pngs (SELECT only)
# ---------------------------------------------------------------------------

def read_ga_png_spec(ga_conn, ga_id: int, ga_png_dir: str) -> dict:
    """The GA stim's PngSpec (path, dimensions in degrees), with the png found locally."""
    ga_conn.execute("SELECT spec FROM StimSpec WHERE id = %s", params=(int(ga_id),))
    xml = ga_conn.fetch_one()
    if not xml:
        raise RuntimeError(f"GA stim {ga_id} has no StimSpec in the GA database.")
    spec = xmltodict.parse(xml)['StimSpec']
    dims = spec.get('dimensions') or {}
    width, height = float(dims.get('width') or 0), float(dims.get('height') or 0)
    if width <= 0:
        raise RuntimeError(f"GA stim {ga_id}'s StimSpec has no dimensions (catch stim?).")
    return {'png_path': spec['path'], 'local_png': locate_local_file(spec['path'], ga_png_dir),
            'width_deg': width, 'height_deg': height}


def read_ga_size(ga_conn, ga_id: int):
    """The GA stim's mstick size (StimSize.size, deg), or None if not recorded."""
    ga_conn.execute("SELECT size FROM StimSize WHERE stim_id = %s", params=(int(ga_id),))
    size = ga_conn.fetch_one()
    return float(size) if size is not None else None


def shape_size_deg(png: str, width_deg: float, screen_color, threshold: float) -> float:
    """sqrt(shape area) in degrees: the shape is everything that differs from the png background."""
    rgb = load_rgb(png, screen_color)
    mask = shape_mask(rgb, estimate_background(rgb), threshold)
    if not mask.any():
        raise RuntimeError(f"No shape found in {png} at threshold {threshold}")
    return float(np.sqrt(mask.sum())) * width_deg / rgb.shape[1]


def nafc_over_ga_scale(ga_conn, match: dict, sample_ga_id: int, ga_png_dir: str,
                       screen_color, threshold: float) -> float:
    """How much bigger NAFC drew the match than the GA png of the same stim."""
    ga = read_ga_png_spec(ga_conn, sample_ga_id, ga_png_dir)
    scale = (shape_size_deg(match['local_png'], match['width_deg'], screen_color, threshold) /
             shape_size_deg(ga['local_png'], ga['width_deg'], screen_color, threshold))
    print(f"Match: NAFC choice is {scale:.3f}x its GA png ({ga['local_png']})")
    return scale


def ga_png_choice(ga_conn, ga_id: int, sample_ga_id: int, match_scale: float, ga_png_dir: str) -> dict:
    """A choice drawn from the GA png, sized as NAFC would draw it (all choices at one size)."""
    ga = read_ga_png_spec(ga_conn, ga_id, ga_png_dir)
    size, sample_size = read_ga_size(ga_conn, ga_id), read_ga_size(ga_conn, sample_ga_id)
    if size is None or sample_size is None:
        print(f"Warning: no StimSize for GA stim {ga_id if size is None else sample_ga_id}; "
              f"assuming it has the same GA size as the sample.")
        size = sample_size = 1.0
    scale = match_scale * sample_size / size
    return {'ga_id': ga_id, 'source': 'ga', 'png_path': ga['png_path'], 'local_png': ga['local_png'],
            'width_deg': ga['width_deg'] * scale, 'height_deg': ga['height_deg'] * scale,
            'ga_png_scale': scale}


if __name__ == "__main__":
    main()
