"""
Make an example image of a GA stimulus with the NAFC noise drawn on it, without running the
experiment.

Given a GA stim id, finds an NAFC (EStimShape procedural) trial whose sample is that GA stimulus
(BaseMStickId.base_mstick_stim_spec_id == GA stim id), reads the sample's NoisyPngSpec from
StimObjData (png path, noise map path, colour), loads the sample png and its noise map from the
NAFC stimuli folder, and draws the noise the same way the experiment does.

How the experiment draws noise (xper-allen NoisyTranslatableResizableImages.loadNoise, "twinkle"):
  - The red channel of each noise-map pixel / 255 is the probability that pixel is noise.
  - Frame 0: each pixel independently becomes noise with that probability. A noise pixel is opaque,
    with the stimulus colour's hue, a uniform random brightness in [0, 1], and a uniform random
    saturation in [0, 1] (saturation stays 0 when the stimulus colour is grey, so noise stays grey).
    Non-noise pixels are fully transparent.
  - Later frames: each pixel that was noise in the previous frame gets a new random colour with
    chance 0.5, otherwise keeps its colour. Pixels that were not noise stay transparent.
  - The noise frame is drawn over the sample png at the same size, with alpha blending, so a noise
    pixel simply replaces the stimulus pixel.

Read-only: this script only runs SELECT queries and never writes to any database.

Figure: left panel = the noisy sample, zoomed in. Right panel = the trial's match, one
distractor and one rand distractor, each cut out of its png background (threshold against the
png's border colour; pixels fully enclosed by the shape are kept) and arranged in a triangle at
their relative on-screen sizes.

Output: <SAVE_ROOT>/<session>/ga_noise_example/<ga_stim_id>_<timestamp>/
  noisy_stimulus.png (native resolution, frame 0), noisy_stimulus_frame<k>.png for later frames,
  sample_panel.png, choices_panel.png, figure.png, config.json.
"""

from __future__ import annotations

import colorsys
import glob
import json
import os
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
import xmltodict
from PIL import Image, ImageDraw
from scipy import ndimage

# Removed (deleted-limb) trials record the GA variant as their base mstick, but their sample is
# the variant with its tuned component deleted, so they are never used.
REMOVED_STIM_TYPE = "EStimShapeVariantsDeletedNAFCStim"


def main():
    # ---- Parameters -------------------------------------------------------------------------
    SESSION_ID = "260603_0"        # session the GA stim belongs to; None = keep current context
    GA_STIM_ID = 1780507361091158     # GA stim id to render with noise
    DISTRACTOR_ID = 1780507018367969  # procedural distractor to show: the id in its png file name
    NAFC_STIM_ID = None            # None = latest NAFC trial with this GA stim as its sample;
                                   # or an NAFC StimSpec id to use that trial's noise map
    NOISE_CHANCE = 0.3            # noise amount: peak chance a pixel is noise (0-1), like the
                                   # NAFC noiseChance parameter. None = as the trial used.
    N_FRAMES = 1                   # number of noise frames (twinkle); frame 0 is what the
                                   # monkey sees on the first frame
    RANDOM_SEED = None             # int for a reproducible noise pattern, None = new each run
    NAFC_STIMULI_DIR = None        # None = <base_dir>/<nafc_database>/stimuli (searched for pngs)
    # Figure
    ZOOM = 4.0                     # left panel zoom factor (1 = whole sample png)
    ZOOM_CENTER = None             # (x, y) in -1..1 of the sample png, +y up; None = centre of the shape
    DISTRACTOR_LABELS = ("delta", "procedural")  # which distractor to show, by png label, first
                                   # found wins; falls back to any choice that isn't match/rand

                                   # (e.g. <id>_delta.png). If NAFC_STIM_ID is None, the latest
                                   # trial that offered this distractor is used. None = by label.
    CHOICE_ORDER = ("match", "distractor", "rand")  # placed top, bottom-left, bottom-right
    CHOICE_SPACING = 1.0           # >1 spreads the three choices apart, <1 packs them closer
    BACKGROUND_THRESHOLD = 12      # 0-255; a pixel is shape if any channel differs from the
                                   # png's background colour by more than this
    EDGE_BAND_PX = 2               # px either side of the shape's edge where the png's gray is
                                   # subtracted out of antialiased pixels
    SCREEN_COLOR = (0, 0, 0)       # monitor background; pngs are alpha-blended onto it like on the rig
    SHOW_FIXATION = True           # fixation square at screen (0, 0) on the left panel
    FIXATION_SIZE_DEG = None       # None = xper_fixation_point_size from the NAFC SystemVar table
    FIXATION_COLOR = None          # (r, g, b) 0-255; None = xper_fixation_point_color from SystemVar
    PANEL_PX = None                # None = native resolution (no resampling of the pngs' pixels);
                                   # or a pixel size to resize each square panel to
    CORNER_RADIUS = 0.03           # rounded panel corners, as a fraction of the panel size
    SAVE_ROOT = "/home/connorlab/Documents/plots"
    SHOW_PLOTS = True
    # -----------------------------------------------------------------------------------------

    from src.startup import context
    if SESSION_ID is not None:
        from src.startup.apply_session_context import apply_session_context
        apply_session_context(SESSION_ID)

    from clat.util.connection import Connection
    nafc_conn = Connection(context.nafc_database)

    stimuli_dir = NAFC_STIMULI_DIR or f"{context.base_dir}/{context.nafc_database}/stimuli"

    candidates = find_nafc_samples_for_ga_stim(nafc_conn, GA_STIM_ID)
    if not candidates:
        raise RuntimeError(
            f"No NAFC trial in {context.nafc_database} has GA stim {GA_STIM_ID} as its sample "
            f"(no non-removed BaseMStickId trial with a noise map). Check SESSION_ID and GA_STIM_ID.")
    print(f"NAFC trials with GA stim {GA_STIM_ID} as sample: "
          f"{[c['nafc_stim_id'] for c in candidates]}")

    if NAFC_STIM_ID is None and DISTRACTOR_ID is not None:
        with_distractor = [c for c in candidates if DISTRACTOR_ID in c['choice_obj_ids']]
        if not with_distractor:
            raise RuntimeError(f"No trial of GA stim {GA_STIM_ID} offered distractor {DISTRACTOR_ID}.")
        chosen = with_distractor[0]
    elif NAFC_STIM_ID is None:
        chosen = candidates[0]
    else:
        matches = [c for c in candidates if c['nafc_stim_id'] == NAFC_STIM_ID]
        if not matches:
            raise RuntimeError(f"NAFC stim {NAFC_STIM_ID} is not a (non-removed) trial of GA stim {GA_STIM_ID}.")
        chosen = matches[0]
    print(f"Using NAFC trial {chosen['nafc_stim_id']} ({chosen['stim_type']}, "
          f"sample obj {chosen['sample_obj_id']})")

    sample_png = locate_local_file(chosen['png_path'], stimuli_dir)
    noise_map_png = locate_local_file(chosen['noise_map_path'], stimuli_dir)
    print(f"Sample png:    {sample_png}")
    print(f"Noise map png: {noise_map_png}")

    sample_rgb = load_rgb(sample_png, SCREEN_COLOR)
    noise_probability = load_noise_probability(noise_map_png, sample_rgb.shape[:2])
    trial_peak = float(noise_probability.max())
    print(f"Trial noise chance (noise map peak): {trial_peak:.3f}")
    if NOISE_CHANCE is not None:
        noise_probability = rescale_noise_chance(noise_probability, NOISE_CHANCE)

    rng = np.random.default_rng(RANDOM_SEED)
    noise_frames = generate_twinkle_noise_frames(noise_probability, chosen['color'], N_FRAMES, rng)
    noisy_frames = [composite_noise(sample_rgb, frame) for frame in noise_frames]

    session_name = SESSION_ID or context.ga_database
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(SAVE_ROOT, str(session_name), "ga_noise_example", f"{GA_STIM_ID}_{timestamp}")
    os.makedirs(out_dir, exist_ok=True)

    for k, img in enumerate(noisy_frames):
        name = "noisy_stimulus.png" if k == 0 else f"noisy_stimulus_frame{k}.png"
        Image.fromarray(img).save(os.path.join(out_dir, name))

    choices = read_choice_specs(nafc_conn, chosen['choice_obj_ids'])
    shown = pick_choices(choices, DISTRACTOR_LABELS, DISTRACTOR_ID)
    for role, choice in shown.items():
        choice['local_png'] = locate_local_file(choice['png_path'], stimuli_dir)
        print(f"{role:>10}: {choice['local_png']}")

    background = estimate_background(sample_rgb)
    fixation = None
    if SHOW_FIXATION:
        size_deg = FIXATION_SIZE_DEG
        if size_deg is None:
            size_deg = float(read_system_var(nafc_conn, "xper_fixation_point_size")[0])
        color = FIXATION_COLOR
        if color is None:
            color = tuple(int(round(float(v) * 255))
                          for v in read_system_var(nafc_conn, "xper_fixation_point_color")[:3])
        fixation = fixation_in_sample_pixels(chosen, sample_rgb.shape[:2], size_deg, color)
        print(f"Fixation: {size_deg} deg, colour {color}, at sample px {fixation['xy']}")
    sample_panel = zoom_panel(noisy_frames[0], sample_rgb, ZOOM, ZOOM_CENTER, PANEL_PX,
                              background, BACKGROUND_THRESHOLD, fixation)
    choices_panel = choices_triangle_panel([shown[role] for role in CHOICE_ORDER], PANEL_PX,
                                           background, BACKGROUND_THRESHOLD, CHOICE_SPACING,
                                           SCREEN_COLOR, EDGE_BAND_PX)
    sample_panel = round_corners(sample_panel, CORNER_RADIUS)
    choices_panel = round_corners(choices_panel, CORNER_RADIUS)
    sample_panel.save(os.path.join(out_dir, "sample_panel.png"))
    choices_panel.save(os.path.join(out_dir, "choices_panel.png"))

    fig = plot_example_figure(sample_panel, choices_panel)
    # dpi high enough that each panel is saved at (at least) its native pixel size
    panel_inches = fig.axes[0].get_window_extent().width / fig.dpi
    dpi = max(200, int(np.ceil(max(sample_panel.width, choices_panel.width) / panel_inches)))
    fig.savefig(os.path.join(out_dir, "figure.png"), dpi=dpi, bbox_inches="tight")

    config = {
        "session_id": SESSION_ID,
        "ga_database": context.ga_database,
        "nafc_database": context.nafc_database,
        "ga_stim_id": GA_STIM_ID,
        "nafc_stim_id": chosen['nafc_stim_id'],
        "nafc_stim_type": chosen['stim_type'],
        "nafc_sample_obj_id": chosen['sample_obj_id'],
        "candidate_nafc_stim_ids": [c['nafc_stim_id'] for c in candidates],
        "sample_png": sample_png,
        "noise_map_png": noise_map_png,
        "noise_color_rgb": list(chosen['color']),
        "trial_noise_chance": trial_peak,
        "noise_chance": NOISE_CHANCE,
        "n_frames": N_FRAMES,
        "choices_shown": {role: {'label': c['label'], 'png': c['local_png'],
                                 'dimensions_deg': [c['width_deg'], c['height_deg']]}
                          for role, c in shown.items()},
        "zoom": ZOOM,
        "zoom_center": ZOOM_CENTER,
        "distractor_labels": list(DISTRACTOR_LABELS),
        "distractor_id": DISTRACTOR_ID,
        "choice_order": list(CHOICE_ORDER),
        "choice_spacing": CHOICE_SPACING,
        "background_threshold": BACKGROUND_THRESHOLD,
        "background_rgb": [int(v) for v in background],
        "panel_px": PANEL_PX,
        "edge_band_px": EDGE_BAND_PX,
        "screen_color": list(SCREEN_COLOR),
        "fixation": None if fixation is None else
                    {'size_deg': fixation['size_deg'], 'color': list(fixation['color'])},
        "corner_radius": CORNER_RADIUS,
        "random_seed": RANDOM_SEED,
        "noise_model": "twinkle (xper NoisyTranslatableResizableImages)",
    }
    with open(os.path.join(out_dir, "config.json"), "w") as f:
        json.dump(config, f, indent=2)
    print(f"Saved to {out_dir}")

    if SHOW_PLOTS:
        plt.show()


# ---------------------------------------------------------------------------
# Database lookup (SELECT only)
# ---------------------------------------------------------------------------

def find_nafc_samples_for_ga_stim(nafc_conn, ga_stim_id: int) -> list[dict]:
    """
    Every NAFC trial whose sample is the GA stim, newest first, keeping only those whose sample
    spec has a noise map and skipping removed trials. Each entry: nafc_stim_id, stim_type,
    sample_obj_id, choice_obj_ids, png_path, noise_map_path, color (0-255 RGB), width_deg,
    height_deg.
    """
    nafc_conn.execute(
        "SELECT stim_id FROM BaseMStickId WHERE base_mstick_stim_spec_id = %s ORDER BY stim_id DESC",
        params=(int(ga_stim_id),))
    nafc_stim_ids = [int(row[0]) for row in nafc_conn.fetch_all()]

    candidates = []
    for nafc_stim_id in nafc_stim_ids:
        nafc_conn.execute("SELECT spec FROM StimSpec WHERE id = %s", params=(nafc_stim_id,))
        stim_spec_xml = nafc_conn.fetch_one()
        if not stim_spec_xml:
            continue
        stim_spec = xmltodict.parse(stim_spec_xml)['StimSpec']
        stim_type = stim_spec.get('stimType')
        if stim_type == REMOVED_STIM_TYPE:
            continue
        sample_obj_id = int(stim_spec['sampleObjData'])
        choice_obj_ids = (stim_spec.get('choiceObjData') or {}).get('long') or []
        if not isinstance(choice_obj_ids, list):
            choice_obj_ids = [choice_obj_ids]

        nafc_conn.execute("SELECT spec FROM StimObjData WHERE id = %s", params=(sample_obj_id,))
        sample_spec_xml = nafc_conn.fetch_one()
        if not sample_spec_xml:
            continue
        sample_spec = parse_noisy_png_spec(sample_spec_xml)
        if not sample_spec['noise_map_path']:
            continue
        candidates.append({'nafc_stim_id': nafc_stim_id, 'stim_type': stim_type, 'sample_obj_id': sample_obj_id,
                           'choice_obj_ids': [int(c) for c in choice_obj_ids], **sample_spec})
    return candidates


def parse_noisy_png_spec(xml: str) -> dict:
    """Read pngPath, noiseMapPath, color (java.awt.Color via XStream) and dimensions (degrees)
    from a NoisyPngSpec."""
    spec = xmltodict.parse(xml)['StimSpec']
    color = spec.get('color') or {}
    rgb = tuple(int(color.get(c, 255)) for c in ('red', 'green', 'blue'))
    dims = spec.get('dimensions') or {}
    return {
        'x_center_deg': float(spec.get('xCenter') or 0),
        'y_center_deg': float(spec.get('yCenter') or 0),
        'png_path': spec.get('pngPath') or '',
        'noise_map_path': spec.get('noiseMapPath') or '',
        'color': rgb,
        'width_deg': float(dims.get('width') or 0),
        'height_deg': float(dims.get('height') or 0),
    }


def read_system_var(nafc_conn, name: str) -> list[str]:
    """Latest value of an xper SystemVar, all array entries in order."""
    nafc_conn.execute(
        "SELECT arr_ind, val FROM SystemVar WHERE name = %s AND tstamp = "
        "(SELECT MAX(tstamp) FROM SystemVar WHERE name = %s) ORDER BY arr_ind",
        params=(name, name))
    rows = nafc_conn.fetch_all()
    if not rows:
        raise RuntimeError(f"SystemVar {name} not found; set it at the top of main() instead.")
    return [row[1] for row in rows]


def read_choice_specs(nafc_conn, choice_obj_ids: list[int]) -> list[dict]:
    """Each choice's NoisyPngSpec plus its label from the png file name (<id>_<label>.png)."""
    choices = []
    for obj_id in choice_obj_ids:
        nafc_conn.execute("SELECT spec FROM StimObjData WHERE id = %s", params=(obj_id,))
        xml = nafc_conn.fetch_one()
        if not xml:
            continue
        spec = parse_noisy_png_spec(xml)
        spec['obj_id'] = obj_id
        spec['label'] = png_label(spec['png_path'])
        choices.append(spec)
    return choices


def png_label(path: str) -> str:
    """'.../1780507913222760_delta.png' -> 'delta'."""
    stem = os.path.splitext(os.path.basename(path))[0]
    parts = stem.split("_", 1)
    return parts[1] if len(parts) == 2 and parts[0].isdigit() else stem


def pick_choices(choices: list[dict], distractor_labels, distractor_id=None) -> dict:
    """The match, one distractor (the choice with id distractor_id if given; else the first
    label in distractor_labels found, else any choice that isn't the match or a rand) and the
    first rand distractor."""
    by_label = {}
    for c in choices:
        by_label.setdefault(c['label'], c)
    labels = [c['label'] for c in choices]
    if 'match' not in by_label:
        raise RuntimeError(f"No match among this trial's choices (labels: {labels})")
    if 'rand' not in by_label:
        raise RuntimeError(f"No rand distractor among this trial's choices (labels: {labels})")
    if distractor_id is not None:
        distractor = next((c for c in choices if c['obj_id'] == distractor_id), None)
        if distractor is None:
            raise RuntimeError(f"Distractor {distractor_id} is not a choice in this trial "
                               f"(choice ids: {[c['obj_id'] for c in choices]})")
        return {'match': by_label['match'], 'distractor': distractor, 'rand': by_label['rand']}
    distractor = next((by_label[l] for l in distractor_labels if l in by_label), None)
    if distractor is None:
        distractor = next((c for c in choices if c['label'] not in ('match', 'rand')), None)
    if distractor is None:
        raise RuntimeError(f"No distractor among this trial's choices (labels: {labels})")
    return {'match': by_label['match'], 'distractor': distractor, 'rand': by_label['rand']}


def locate_local_file(spec_path: str, stimuli_dir: str) -> str:
    """
    The spec stores the path as the rig computer saw it (sftp prefix). Use it if it exists
    locally, otherwise find the same file name anywhere under the NAFC stimuli folder.
    """
    if os.path.isfile(spec_path):
        return spec_path
    name = os.path.basename(spec_path)
    hits = sorted(glob.glob(os.path.join(stimuli_dir, "**", name), recursive=True))
    if not hits:
        raise FileNotFoundError(f"Could not find {name} under {stimuli_dir} (spec path: {spec_path})")
    return hits[-1]


# ---------------------------------------------------------------------------
# Noise rendering (replicates xper NoisyTranslatableResizableImages)
# ---------------------------------------------------------------------------

def load_rgb(path: str, screen_color=(0, 0, 0)) -> np.ndarray:
    """The png as it appears on the monitor: alpha-blended onto the screen colour
    (GL_SRC_ALPHA / GL_ONE_MINUS_SRC_ALPHA), so semi-transparent edge pixels don't show their
    raw RGB."""
    rgba = np.asarray(Image.open(path).convert("RGBA"), dtype=np.float64)
    alpha = rgba[:, :, 3:4] / 255.0
    out = rgba[:, :, :3] * alpha + np.asarray(screen_color, dtype=np.float64) * (1.0 - alpha)
    return np.clip(np.round(out), 0, 255).astype(np.uint8)


def load_noise_probability(path: str, shape_hw: tuple) -> np.ndarray:
    """Red channel / 255. If the map's size differs from the sample, stretch it (nearest
    neighbour) to the sample, as OpenGL does when both textures are drawn on the same quad."""
    img = Image.open(path).convert("RGBA")
    if img.size != (shape_hw[1], shape_hw[0]):
        print(f"Warning: noise map size {img.size} != sample size {(shape_hw[1], shape_hw[0])}; resizing")
        img = img.resize((shape_hw[1], shape_hw[0]), Image.NEAREST)
    return np.asarray(img, dtype=np.float64)[:, :, 0] / 255.0


def rescale_noise_chance(noise_probability: np.ndarray, noise_chance: float) -> np.ndarray:
    """
    GaussianNoiseMapper draws the map with its peak = noiseChance (background 0), so a different
    noise amount is the same map scaled to a new peak.
    """
    peak = noise_probability.max()
    if peak == 0:
        raise ValueError("Noise map is empty (all red values are 0), so it can't be rescaled.")
    return np.clip(noise_probability * (noise_chance / peak), 0.0, 1.0)


def java_rgb_to_hsb(rgb: tuple) -> tuple:
    """java.awt.Color.RGBtoHSB (same as HSV)."""
    return colorsys.rgb_to_hsv(*(c / 255.0 for c in rgb))


def java_hsb_to_rgb(hue: float, saturation: np.ndarray, brightness: np.ndarray) -> np.ndarray:
    """Vectorised java.awt.Color.HSBtoRGB, including its (int)(x * 255 + 0.5) rounding."""
    saturation = np.asarray(saturation, dtype=np.float32)
    brightness = np.asarray(brightness, dtype=np.float32)
    h = (hue - np.floor(hue)) * 6.0
    sector = int(np.floor(h))
    f = h - np.floor(h)
    p = brightness * (1.0 - saturation)
    q = brightness * (1.0 - saturation * f)
    t = brightness * (1.0 - saturation * (1.0 - f))
    v = brightness
    r, g, b = {
        0: (v, t, p),
        1: (q, v, p),
        2: (p, v, t),
        3: (p, q, v),
        4: (t, p, v),
        5: (v, p, q),
    }[sector % 6]
    rgb = np.stack([r, g, b], axis=-1)
    grey = saturation == 0
    rgb[grey] = brightness[grey][:, None]
    return (rgb * 255.0 + 0.5).astype(np.uint8)


def random_noise_colors(n: int, hue: float, base_saturation: float, rng) -> np.ndarray:
    """calculateNoisePixels: random brightness; random saturation unless the base colour is grey."""
    brightness = rng.random(n)
    saturation = np.zeros(n) if base_saturation == 0 else rng.random(n)
    return java_hsb_to_rgb(hue, saturation, brightness)


def generate_twinkle_noise_frames(noise_probability: np.ndarray, color_rgb: tuple, n_frames: int,
                                  rng) -> list[np.ndarray]:
    """RGBA noise frames, frame 0 from generateNoise, later frames from generateTwinkleNoise(0.5)."""
    hue, base_saturation, _ = java_rgb_to_hsb(color_rgb)
    h, w = noise_probability.shape

    frames = []
    frame = np.zeros((h, w, 4), dtype=np.uint8)
    is_noise = rng.random((h, w)) < noise_probability
    frame[is_noise, :3] = random_noise_colors(int(is_noise.sum()), hue, base_saturation, rng)
    frame[is_noise, 3] = 255
    frames.append(frame)

    for _ in range(1, n_frames):
        previous = frames[-1]
        frame = np.zeros_like(previous)
        was_noise = previous[:, :, 3] == 255
        frame[was_noise] = previous[was_noise]
        twinkle = was_noise & (rng.random((h, w)) < 0.5)
        frame[twinkle, :3] = random_noise_colors(int(twinkle.sum()), hue, base_saturation, rng)
        frames.append(frame)
    return frames


def composite_noise(sample_rgb: np.ndarray, noise_rgba: np.ndarray) -> np.ndarray:
    """GL_SRC_ALPHA / GL_ONE_MINUS_SRC_ALPHA blend of the noise frame over the sample."""
    alpha = noise_rgba[:, :, 3:4].astype(np.float64) / 255.0
    out = noise_rgba[:, :, :3] * alpha + sample_rgb * (1.0 - alpha)
    return np.clip(np.round(out), 0, 255).astype(np.uint8)


# ---------------------------------------------------------------------------
# Figure
# ---------------------------------------------------------------------------

def estimate_background(rgb: np.ndarray) -> np.ndarray:
    """Median colour of the png's 1-pixel border."""
    border = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]])
    return np.median(border, axis=0).astype(np.uint8)


def shape_mask(rgb: np.ndarray, background: np.ndarray, threshold: float) -> np.ndarray:
    """Pixels that differ from the background by more than threshold in any channel, with
    holes filled so dark pixels fully enclosed by the shape are kept."""
    diff = np.abs(rgb.astype(np.int16) - background.astype(np.int16)).max(axis=2)
    return ndimage.binary_fill_holes(diff > threshold)


def fixation_in_sample_pixels(sample_spec: dict, shape_hw: tuple, size_deg: float, color) -> dict:
    """Where screen (0, 0) falls in the sample png. The sample png is drawn centred at
    (xCenter, yCenter) deg and stretched to its spec dimensions, +y up."""
    h, w = shape_hw
    px_per_deg_x = w / sample_spec['width_deg']
    px_per_deg_y = h / sample_spec['height_deg']
    x = w / 2 - sample_spec['x_center_deg'] * px_per_deg_x
    y = h / 2 + sample_spec['y_center_deg'] * px_per_deg_y
    return {'xy': (x, y), 'size_px': size_deg * px_per_deg_x, 'size_deg': size_deg,
            'color': tuple(int(c) for c in color)}


def zoom_panel(noisy_rgb: np.ndarray, sample_rgb: np.ndarray, zoom: float, center, panel_px,
               background: np.ndarray, threshold: float, fixation: dict | None = None) -> Image.Image:
    """Square crop of side min(h, w) / zoom around center (default: centre of the bounding box
    of the shape in the clean sample, plus the fixation square if shown), at native resolution, or
    scaled to panel_px with nearest neighbour so noise pixels stay crisp. Anything outside the png is screen background."""
    h, w = noisy_rgb.shape[:2]
    side = max(1, int(round(min(h, w) / max(zoom, 1e-6))))

    # Scene = the png padded with background on every side, so the crop and the fixation point
    # can fall outside the png.
    pad = side + max(h, w)
    if fixation is not None:
        fx, fy = fixation['xy']
        pad = int(max(pad, abs(fx) + fixation['size_px'], abs(fy) + fixation['size_px'],
                      abs(fx - w) + fixation['size_px'], abs(fy - h) + fixation['size_px']))
    scene = np.empty((h + 2 * pad, w + 2 * pad, 3), dtype=np.uint8)
    scene[:] = background
    scene[pad:pad + h, pad:pad + w] = noisy_rgb

    boxes = []  # (x0, y0, x1, y1) in png coordinates
    if center is None:
        mask = shape_mask(sample_rgb, background, threshold)
        if mask.any():
            rows, cols = np.nonzero(mask)
            boxes.append((cols.min(), rows.min(), cols.max(), rows.max()))
    if fixation is not None:
        fx, fy = fixation['xy']
        half = max(fixation['size_px'] / 2, 0.5)
        x0f, x1f = int(round(fx - half)), int(round(fx + half))
        y0f, y1f = int(round(fy - half)), int(round(fy + half))
        scene[pad + y0f:pad + max(y1f, y0f + 1), pad + x0f:pad + max(x1f, x0f + 1)] = fixation['color']
        if center is None:
            boxes.append((x0f, y0f, x1f, y1f))

    if center is not None:
        cx = (center[0] + 1) / 2 * w
        cy = (1 - center[1]) / 2 * h
    elif boxes:
        cx = (min(b[0] for b in boxes) + max(b[2] for b in boxes)) / 2
        cy = (min(b[1] for b in boxes) + max(b[3] for b in boxes)) / 2
    else:
        cx, cy = w / 2, h / 2
    x0 = int(round(cx - side / 2)) + pad
    y0 = int(round(cy - side / 2)) + pad
    crop = Image.fromarray(scene[y0:y0 + side, x0:x0 + side])
    if panel_px is None:
        return crop
    return crop.resize((panel_px, panel_px), Image.NEAREST)


def resample(img: Image.Image, size: tuple) -> Image.Image:
    """Area averaging when shrinking, bilinear when enlarging: neither overshoots, so no bright
    or dark rims appear at the shape's edges (Lanczos/bicubic ring there)."""
    shrinking = size[0] < img.width or size[1] < img.height
    return img.resize(size, Image.BOX if shrinking else Image.BILINEAR)


def remove_flat_background(rgb: np.ndarray, mask: np.ndarray, png_background, new_background,
                           band_px: int) -> np.ndarray:
    """
    Take a shape off a flat png background and put it on new_background.

    An antialiased edge pixel is p = a*f + (1-a)*g, with g the (known, flat) png background,
    f the shape's colour there and a its coverage. f is taken from the nearest pixel fully
    inside the shape (mask eroded by 1), and a is the least-squares solution
    a = <p - g, f - g> / |f - g|^2, clipped to [0, 1]. The pixel's own colour is kept and only
    its background share is swapped: p - (1-a)*g + (1-a)*new_background. Pixels farther than
    band_px outside the shape become new_background; pixels inside the shape are unchanged.
    """
    rgb_f = rgb.astype(np.float64)
    g = np.asarray(png_background, dtype=np.float64)
    new_bg = np.asarray(new_background, dtype=np.float64)
    interior = ndimage.binary_erosion(mask)
    if not interior.any():
        interior = mask
    band = ndimage.binary_dilation(mask, iterations=max(band_px, 1)) & ~interior

    _, (iy, ix) = ndimage.distance_transform_edt(~interior, return_indices=True)
    f = rgb_f[iy, ix]
    d = f - g
    d2 = (d * d).sum(axis=2)
    a = np.clip(((rgb_f - g) * d).sum(axis=2) / np.maximum(d2, 1e-6), 0.0, 1.0)
    # where the shape colour is too close to the background to separate, keep the mask's call
    unresolved = d2 < 10.0 ** 2
    a[unresolved] = mask[unresolved]

    out = np.empty_like(rgb_f)
    out[:] = new_bg
    out[interior] = rgb_f[interior]
    swapped = rgb_f - (1 - a)[..., None] * g + (1 - a)[..., None] * new_bg
    out[band] = swapped[band]
    return np.clip(np.round(out), 0, 255).astype(np.uint8)


def cut_out_choice(choice: dict, threshold: float, screen_color, band_px: int,
                   fill_color) -> tuple:
    """
    (RGB crop of the choice on fill_color, paste mask, degrees per png pixel or None).

    The choice pngs have a flat gray background; it is removed with remove_flat_background
    BEFORE any resizing, so no gray can bleed into the edge.
    """
    rgb = load_rgb(choice['local_png'], screen_color)
    png_background = estimate_background(rgb)
    mask = shape_mask(rgb, png_background, threshold)
    if not mask.any():
        raise RuntimeError(f"No shape found in {choice['local_png']} at threshold {threshold}")
    rgb = remove_flat_background(rgb, mask, png_background, fill_color, band_px)
    # paste a grown mask: the extra ring is already fill_color, so resampled edges blend into it
    paste_mask = ndimage.binary_dilation(mask, iterations=max(band_px, 1) + 2)
    rows, cols = np.nonzero(paste_mask)
    r0, r1, c0, c1 = rows.min(), rows.max() + 1, cols.min(), cols.max() + 1
    img = Image.fromarray(rgb[r0:r1, c0:c1])
    mask_img = Image.fromarray((paste_mask[r0:r1, c0:c1] * 255).astype(np.uint8), "L")
    deg_per_px = (choice['width_deg'] / rgb.shape[1]) if choice['width_deg'] > 0 else None
    return img, mask_img, deg_per_px


def choices_triangle_panel(choices: list[dict], panel_px, background: np.ndarray,
                           threshold: float, spacing: float, screen_color=(0, 0, 0),
                           band_px: int = 2) -> Image.Image:
    """Three cut-out choices at the vertices of a triangle (top, bottom-left, bottom-right)."""
    cutouts = [cut_out_choice(c, threshold, screen_color, band_px, background) for c in choices]
    scales = [d for _, _, d in cutouts if d is not None]
    # common pixels-per-degree = the finest of the choices, so nothing is downsampled first
    ref = min(scales) if len(scales) == len(cutouts) else None
    shapes, masks = [], []
    for img, mask_img, deg_per_px in cutouts:
        if ref is not None:
            f = deg_per_px / ref
            size = (max(1, round(img.width * f)), max(1, round(img.height * f)))
            if size != img.size:  # choices already at the common scale are left untouched
                img = resample(img, size)
                mask_img = mask_img.resize(size, Image.NEAREST)
        shapes.append(img)
        masks.append(mask_img)

    # radius so neighbouring shapes (half-diagonals r_i, r_j) don't overlap: side = R*sqrt(3)
    half_diag = [np.hypot(im.width, im.height) / 2 for im in shapes]
    pairs = [(0, 1), (1, 2), (0, 2)]
    radius = spacing * max(half_diag[i] + half_diag[j] for i, j in pairs) / np.sqrt(3)
    angles = np.deg2rad([90, 210, 330])
    centers = [(radius * np.cos(a), -radius * np.sin(a)) for a in angles]  # image y is down

    lefts = [cx - im.width / 2 for (cx, _), im in zip(centers, shapes)]
    rights = [cx + im.width / 2 for (cx, _), im in zip(centers, shapes)]
    tops = [cy - im.height / 2 for (_, cy), im in zip(centers, shapes)]
    bottoms = [cy + im.height / 2 for (_, cy), im in zip(centers, shapes)]
    x_min, x_max, y_min, y_max = min(lefts), max(rights), min(tops), max(bottoms)
    side = int(np.ceil(max(x_max - x_min, y_max - y_min) * 1.15))  # 15% margin
    ox = (side - (x_max - x_min)) / 2 - x_min
    oy = (side - (y_max - y_min)) / 2 - y_min

    canvas = Image.new("RGB", (side, side), tuple(int(v) for v in background))
    for (cx, cy), im, mk in zip(centers, shapes, masks):
        canvas.paste(im, (int(round(cx - im.width / 2 + ox)), int(round(cy - im.height / 2 + oy))), mk)
    if panel_px is None:
        return canvas
    return resample(canvas, (panel_px, panel_px))


def round_corners(panel: Image.Image, radius_fraction: float) -> Image.Image:
    panel = panel.convert("RGBA")
    if radius_fraction <= 0:
        return panel
    mask = Image.new("L", panel.size, 0)
    r = int(round(radius_fraction * min(panel.size)))
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, panel.width - 1, panel.height - 1), r, fill=255)
    panel.putalpha(mask)
    return panel


def plot_example_figure(sample_panel: Image.Image, choices_panel: Image.Image):
    fig, axes = plt.subplots(1, 2, figsize=(10, 5), gridspec_kw={'wspace': 0.04})
    for ax, img in zip(axes, (sample_panel, choices_panel)):
        # antialiased: the window shows the native-resolution panel shrunk, and "none" or
        # "nearest" would alias (checkerboard / moire), worst on the noise
        ax.imshow(img, interpolation="antialiased")
        ax.set_axis_off()
    return fig


if __name__ == "__main__":
    main()
