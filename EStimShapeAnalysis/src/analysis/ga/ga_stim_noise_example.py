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
    # GA_STIM_ID = 1780507361091158     # GA stim id to render with noise
    # DISTRACTOR_ID = 1780507918367969  # GA id of the delta (or variant) to show as the distractor.
    GA_STIM_ID = 1780507913222760
                                   # None = pick by DISTRACTOR_LABELS. If NAFC_STIM_ID is None,
    DISTRACTOR_ID = None
                                   # the latest trial that offered this GA stim is used.
    NAFC_STIM_ID = None            # None = latest NAFC trial with this GA stim as its sample;
                                   # or an NAFC StimSpec id to use that trial's noise map
    NOISE_CHANCE = 0.3            # noise amount: peak chance a pixel is noise (0-1), like the
                                   # NAFC noiseChance parameter. None = as the trial used.
    N_FRAMES = 1                   # number of noise frames (twinkle); frame 0 is what the
                                   # monkey sees on the first frame
    RANDOM_SEED = None             # int for a reproducible noise pattern, None = new each run
    NAFC_STIMULI_DIR = None        # None = <base_dir>/<nafc_database>/stimuli (searched for pngs)
    # Figure
    ZOOM = 2.5                     # sample panel zoom factor (1 = whole sample png); sets the field
                                   # of view (deg) shared by all three panels
    ZOOM_CENTER = "fixation"       # "fixation" = on the fixation point; (x, y) in -1..1 of the sample
                                   # png, +y up; None = centre of the shape (+ fixation)
    DISTRACTOR_LABELS = ("delta", "procedural")  # which distractor to show, by png label, first
                                   # found wins; falls back to any choice that isn't match/rand

    CHOICE_ORDER = ("match", "distractor", "rand")  # placed top, bottom-left, bottom-right
    IMAGE_ZOOM = 1.0               # enlarges the sample and choice images only (panels, positions
                                   # and fixation stay); same factor for both, so they stay matched
    CHOICE_MARGIN = 0.15           # gap between the choices and the panel edge, as a fraction of the
                                   # panel: top choice at the top centre, the other two in the
                                   # bottom corners. Smaller = more spread out
    BACKGROUND_THRESHOLD = 2       # 0-255; a pixel is shape if any channel differs from the
                                   # png's (flat) background colour by more than this. Keep it
                                   # small so faint edge pixels and highlights near the gray stay
    EDGE_BAND_PX = 1               # px inside the shape's edge whose gray share is subtracted out
                                   # (deeper pixels, highlights included, are left untouched)
    SCREEN_COLOR = (0, 0, 0)       # monitor background; pngs are alpha-blended onto it like on the rig
    SHOW_FIXATION = True           # fixation square at screen (0, 0) on the sample panel
    SHOW_FIXATION_PANEL = True     # extra leftmost panel with only the fixation square in its centre
    SHOW_EYE = True                # cyan eye symbol: on fixation (left, middle), on the match (right)
    EYE_SIZE = 0.18                # eye width as a fraction of the panel
    EYE_COLOR = "cyan"
    EYE_ALPHA = 0.6                # eye opacity (1 = solid, 0 = invisible)
    TWO_ROWS = True                # top row: no EStim (fainter eyes on match AND distractor);
                                   # bottom row: EStim (eye on the match only). False = bottom row only
    SPLIT_EYE_ALPHA = 0.3          # opacity of the two eyes on the choices in the top row
    FIXATION_SIZE_DEG = None       # None = xper_fixation_point_size from the NAFC SystemVar table
    FIXATION_COLOR = None          # (r, g, b) 0-255; None = xper_fixation_point_color from SystemVar
    PANEL_PX = None                # None = native resolution (no resampling of the pngs' pixels);
                                   # or a pixel size to resize each square panel to
    CORNER_RADIUS = 0.0            # rounded panel corners, as a fraction of the panel size (0 = square)
    SAVE_ROOT = "/home/connorlab/Documents/plots"
    SHOW_PLOTS = True
    # -----------------------------------------------------------------------------------------

    from src.startup import context
    if SESSION_ID is not None:
        from src.startup.apply_session_context import apply_session_context
        apply_session_context(SESSION_ID)

    from clat.util.connection import Connection
    nafc_conn = Connection(context.nafc_database)
    ga_conn = Connection(context.ga_database)

    stimuli_dir = NAFC_STIMULI_DIR or f"{context.base_dir}/{context.nafc_database}/stimuli"

    candidates = find_nafc_samples_for_ga_stim(nafc_conn, GA_STIM_ID)
    if not candidates:
        raise RuntimeError(
            f"No NAFC trial in {context.nafc_database} has GA stim {GA_STIM_ID} as its sample "
            f"(no non-removed BaseMStickId trial with a noise map). Check SESSION_ID and GA_STIM_ID.")
    print(f"NAFC trials with GA stim {GA_STIM_ID} as sample: "
          f"{[c['nafc_stim_id'] for c in candidates]}")

    if NAFC_STIM_ID is not None:
        candidates = [c for c in candidates if c['nafc_stim_id'] == NAFC_STIM_ID]
        if not candidates:
            raise RuntimeError(f"NAFC stim {NAFC_STIM_ID} is not a (non-removed) trial of GA stim {GA_STIM_ID}.")

    # newest trial first; with DISTRACTOR_ID, the newest one that offered that GA stim
    chosen = choices = None
    offered = set()
    for candidate in candidates:
        candidate_choices = read_choice_specs(nafc_conn, candidate['choice_obj_ids'])
        add_choice_ga_ids(nafc_conn, ga_conn, candidate, candidate_choices)
        offered.update(c['ga_id'] for c in candidate_choices if c['ga_id'] is not None)
        if DISTRACTOR_ID is None or any(c['ga_id'] == DISTRACTOR_ID for c in candidate_choices):
            chosen, choices = candidate, candidate_choices
            break
    if chosen is None:
        raise RuntimeError(
            f"No trial of GA stim {GA_STIM_ID} offered GA stim {DISTRACTOR_ID} as a choice. "
            f"GA ids offered as choices: {sorted(offered)}")
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

    shown = pick_choices(choices, DISTRACTOR_LABELS, DISTRACTOR_ID)
    for role, choice in shown.items():
        choice['local_png'] = locate_local_file(choice['png_path'], stimuli_dir)
        print(f"{role:>10}: GA id {choice['ga_id']}  {choice['local_png']}")

    background = estimate_background(sample_rgb)
    fixation = None
    if SHOW_FIXATION or SHOW_FIXATION_PANEL or SHOW_EYE:
        size_deg = FIXATION_SIZE_DEG
        if size_deg is None:
            size_deg = float(read_system_var(nafc_conn, "xper_fixation_point_size")[0])
        color = FIXATION_COLOR
        if color is None:
            color = tuple(int(round(float(v) * 255))
                          for v in read_system_var(nafc_conn, "xper_fixation_point_color")[:3])
        fixation = fixation_in_sample_pixels(chosen, sample_rgb.shape[:2], size_deg, color)
        print(f"Fixation: {size_deg} deg, colour {color}, at sample px {fixation['xy']}")
    sample_deg_per_px = chosen['width_deg'] / sample_rgb.shape[1]
    sample_panel = zoom_panel(noisy_frames[0], sample_rgb, ZOOM, ZOOM_CENTER, None,
                              background, BACKGROUND_THRESHOLD, fixation if SHOW_FIXATION else None,
                              IMAGE_ZOOM)
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
    centers = choices_panel.info['choice_centers']
    match_xy, distractor_xy = (centers[list(CHOICE_ORDER).index(r)] for r in ("match", "distractor"))
    eyes = {"sample_panel": (fx / sample_panel.width, fy / sample_panel.height)}
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
    estim_row = eye_row([(*match_xy, EYE_ALPHA)])
    no_estim_row = eye_row([(*match_xy, SPLIT_EYE_ALPHA), (*distractor_xy, SPLIT_EYE_ALPHA)])
    rows = [no_estim_row, estim_row] if TWO_ROWS else [estim_row]
    if not SHOW_EYE:
        rows = [[[] for _ in panels] for _ in rows]
    fig = plot_example_figure(list(panels.values()), rows, EYE_SIZE, EYE_COLOR)
    # dpi high enough that each panel is saved at (at least) its native pixel size
    panel_inches = fig.axes[0].get_window_extent().width / fig.dpi
    dpi = max(200, int(np.ceil(max(p.width for p in panels.values()) / panel_inches)))
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
        "choices_shown": {role: {'label': c['label'], 'ga_id': c['ga_id'], 'png': c['local_png'],
                                 'dimensions_deg': [c['width_deg'], c['height_deg']]}
                          for role, c in shown.items()},
        "zoom": ZOOM,
        "image_zoom": IMAGE_ZOOM,
        "eye": {"size": EYE_SIZE, "color": EYE_COLOR, "alpha": EYE_ALPHA,
                "split_alpha": SPLIT_EYE_ALPHA} if SHOW_EYE else None,
        "two_rows": TWO_ROWS,
        "zoom_center": ZOOM_CENTER,
        "distractor_labels": list(DISTRACTOR_LABELS),
        "distractor_ga_id": DISTRACTOR_ID,
        "choice_order": list(CHOICE_ORDER),
        "choice_margin": CHOICE_MARGIN,
        "field_of_view_deg": field_deg,
        "fixation_panel": SHOW_FIXATION_PANEL,
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
        candidates.append({'nafc_stim_id': nafc_stim_id, 'ga_sample_id': int(ga_stim_id), 'stim_type': stim_type, 'sample_obj_id': sample_obj_id,
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


# Choice labels that are GA lineage members (a delta, or the variant in a delta trial).
LINEAGE_DISTRACTOR_LABELS = ("delta", "delta_distractor")


def add_choice_ga_ids(nafc_conn, ga_conn, trial: dict, choices: list[dict]) -> None:
    """
    Set choice['ga_id'] (None for rand / removed / procedural morphs). The NAFC database only
    records the sample's GA id, so this rebuilds the generator's distractor list the same way
    PickedBaseMStickIdField does (EStimShapeVariantsDeltaNAFCStim): variant-sample trial ->
    the variant's included deltas; delta-sample trial -> [variant, other included deltas],
    both in IncludedDeltas' natural order. The k-th delta-labelled choice (choiceObjData order)
    is the k-th entry. Relies on IncludedDeltas not having changed since the trial was generated.
    """
    sample_id = trial['ga_sample_id']
    variant_id, is_delta = None, None
    nafc_conn.execute("SHOW TABLES LIKE 'NafcSampleRole'")
    if nafc_conn.fetch_one() is not None:
        nafc_conn.execute("SELECT is_sample_delta, variant_id FROM NafcSampleRole WHERE stim_id = %s",
                          params=(trial['nafc_stim_id'],))
        rows = nafc_conn.fetch_all()
        if rows:
            is_delta, variant_id = bool(rows[0][0]), int(rows[0][1])
    if variant_id is None:
        ga_conn.execute("SELECT variant_id FROM IncludedDeltas WHERE delta_id = %s AND included = 1",
                        params=(sample_id,))
        rows = ga_conn.fetch_all()
        is_delta = bool(rows)
        variant_id = int(rows[0][0]) if rows else sample_id

    ga_conn.execute("SELECT delta_id FROM IncludedDeltas WHERE variant_id = %s AND included = 1",
                    params=(variant_id,))
    included = [int(r[0]) for r in ga_conn.fetch_all()]
    order = [variant_id] + [d for d in included if d != sample_id] if is_delta else included

    k = 0
    for c in choices:
        c['ga_id'] = None
        if c['label'] == 'match':
            c['ga_id'] = sample_id
        elif c['label'] in LINEAGE_DISTRACTOR_LABELS:
            if k < len(order):
                c['ga_id'] = order[k]
            k += 1


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


def pick_choices(choices: list[dict], distractor_labels, distractor_ga_id=None) -> dict:
    """The match, one distractor (the choice drawn from GA stim distractor_ga_id if given; else
    the first label in distractor_labels found, else any choice that isn't the match or a rand)
    and the first rand distractor."""
    by_label = {}
    for c in choices:
        by_label.setdefault(c['label'], c)
    labels = [c['label'] for c in choices]
    if 'match' not in by_label:
        raise RuntimeError(f"No match among this trial's choices (labels: {labels})")
    if 'rand' not in by_label:
        raise RuntimeError(f"No rand distractor among this trial's choices (labels: {labels})")
    if distractor_ga_id is not None:
        distractor = next((c for c in choices
                           if c.get('ga_id') == distractor_ga_id and c['label'] != 'match'), None)
        if distractor is None:
            raise RuntimeError(f"GA stim {distractor_ga_id} is not a distractor in this trial "
                               f"(choice GA ids: {[c.get('ga_id') for c in choices]})")
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
               background: np.ndarray, threshold: float, fixation: dict | None = None,
               image_zoom: float = 1.0) -> Image.Image:
    """Square crop of side min(h, w) / zoom around center (default: centre of the bounding box
    of the shape in the clean sample, plus the fixation square if shown), at native resolution, or
    scaled to panel_px with nearest neighbour so noise pixels stay crisp. Anything outside the png is screen background.
    image_zoom enlarges the png (noise included) about its own centre without changing the crop
    or the fixation point."""
    h, w = noisy_rgb.shape[:2]
    side = max(1, int(round(min(h, w) / max(zoom, 1e-6))))
    if image_zoom != 1:  # nearest keeps the noise pixels crisp
        size = (max(1, round(w * image_zoom)), max(1, round(h * image_zoom)))
        noisy_rgb = np.array(Image.fromarray(noisy_rgb).resize(size, Image.NEAREST))
        sample_rgb = np.array(Image.fromarray(sample_rgb).resize(size, Image.NEAREST))
    ih, iw = noisy_rgb.shape[:2]
    ox, oy = int(round((w - iw) / 2)), int(round((h - ih) / 2))  # png corner, png coordinates

    # Scene = the png padded with background on every side, so the crop and the fixation point
    # can fall outside the png.
    pad = side + max(h, w, ih, iw)
    if fixation is not None:
        fx, fy = fixation['xy']
        pad = int(max(pad, abs(fx) + fixation['size_px'], abs(fy) + fixation['size_px'],
                      abs(fx - w) + fixation['size_px'], abs(fy - h) + fixation['size_px']))
    scene = np.empty((h + 2 * pad, w + 2 * pad, 3), dtype=np.uint8)
    scene[:] = background
    scene[pad + oy:pad + oy + ih, pad + ox:pad + ox + iw] = noisy_rgb

    boxes = []  # (x0, y0, x1, y1) in png coordinates
    if center == "fixation" and fixation is None:
        center = None  # no fixation point drawn: fall back to the shape
    if center is None:
        mask = shape_mask(sample_rgb, background, threshold)
        if mask.any():
            rows, cols = np.nonzero(mask)
            boxes.append((cols.min() + ox, rows.min() + oy, cols.max() + ox, rows.max() + oy))
    if fixation is not None:
        fx, fy = fixation['xy']
        half = max(fixation['size_px'] / 2, 0.5)
        x0f, x1f = int(round(fx - half)), int(round(fx + half))
        y0f, y1f = int(round(fy - half)), int(round(fy + half))
        scene[pad + y0f:pad + max(y1f, y0f + 1), pad + x0f:pad + max(x1f, x0f + 1)] = fixation['color']
        drawn_fixation = ((x0f + max(x1f, x0f + 1)) / 2, (y0f + max(y1f, y0f + 1)) / 2)
        if center is None:
            boxes.append((x0f, y0f, x1f, y1f))

    if center == "fixation":
        cx, cy = fixation['xy']
    elif center is not None:
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
    crop.info['origin_png_px'] = (x0 - pad, y0 - pad)  # crop's top-left corner in png coordinates
    if fixation is not None:  # centre of the fixation square as drawn, in crop pixel-edge coordinates
        crop.info['fixation_center'] = (drawn_fixation[0] + pad - x0, drawn_fixation[1] + pad - y0)
    if center == "fixation":
        rows, cols = np.nonzero(shape_mask(sample_rgb, background, threshold))
        cols, rows = cols + ox + pad, rows + oy + pad
        if rows.size and (cols.min() < x0 or cols.max() >= x0 + side
                          or rows.min() < y0 or rows.max() >= y0 + side):
            print("Warning: centred on the fixation point, part of the shape is outside the left "
                  "panel; lower ZOOM to fit it.")
    if panel_px is None:
        return crop
    return crop.resize((panel_px, panel_px), Image.NEAREST)


def resample(img: Image.Image, size: tuple) -> Image.Image:
    """Area averaging when shrinking, bilinear when enlarging: neither overshoots, so no bright
    or dark rims appear at the shape's edges (Lanczos/bicubic ring there)."""
    shrinking = size[0] < img.width or size[1] < img.height
    return img.resize(size, Image.BOX if shrinking else Image.BILINEAR)


def shape_colour(rgb_f: np.ndarray, mask: np.ndarray, png_background: np.ndarray, band_px: int):
    """
    Unit direction C of the shape's diffuse colour, or None if the shape is too gray to tell.

    Interior pixels are s*C + w*white (shading s, specular w), so their part perpendicular to
    the gray direction always points along C's hue; how much white C itself contains is the
    smallest white share any interior pixel shows (a pixel with no specular on it).
    """
    h = png_background / np.linalg.norm(png_background)
    depth = ndimage.distance_transform_cdt(mask, metric='chessboard')
    px = rgb_f[depth > band_px]
    if len(px) < 10:
        return None
    par = px @ h
    perp = px - par[:, None] * h
    x = np.linalg.norm(perp, axis=1)
    keep = x > max(0.25 * x.max(), 5.0)
    if keep.sum() < 10:
        return None
    hue = np.linalg.svd(perp[keep], full_matrices=False)[2][0]
    if (perp[keep] @ hue).mean() < 0:
        hue = -hue
    white = np.min(par[keep] / (perp[keep] @ hue))
    c = hue + white * h
    return c / np.linalg.norm(c)


def remove_flat_background(rgb: np.ndarray, mask: np.ndarray, png_background, new_background,
                           band_px: int) -> np.ndarray:
    """
    Take a shape off a flat png background g and put it on new_background (blend to black).

    An edge pixel is p = u*C + v*g: the shape's colour C (from shape_colour) times its shading,
    plus a share v of the background. u and v are solved exactly by least squares for each
    pixel within band_px of the edge, and only the background share is swapped:
    out = p - v*g + v*new_background. A pixel with no gray in it is left exactly as rendered.
    Pixels deeper than band_px are untouched; pixels outside the mask become new_background.
    Falls back to remove_flat_background_by_coverage for a black background or a gray shape.
    """
    rgb_f = rgb.astype(np.float64)
    g = np.asarray(png_background, dtype=np.float64)
    new_bg = np.asarray(new_background, dtype=np.float64)
    if np.linalg.norm(g) < 1e-6:
        return remove_flat_background_by_coverage(rgb, mask, png_background, new_background, band_px)
    c = shape_colour(rgb_f, mask, g, band_px)
    if c is None or abs(c @ g) / np.linalg.norm(g) > 0.98:  # shape colour too close to gray
        return remove_flat_background_by_coverage(rgb, mask, png_background, new_background, band_px)

    out = np.empty_like(rgb_f)
    out[:] = new_bg
    out[mask] = rgb_f[mask]
    # edge = pixels sharing a side with the background; a pixel touching it only at a corner is
    # (nearly) fully covered, and solving it would mistake its specular white for gray
    depth = ndimage.distance_transform_cdt(mask, metric='taxicab')
    edge = mask & (depth <= band_px)
    p = rgb_f[edge]
    uv = np.linalg.lstsq(np.stack([c, g], axis=1), p.T, rcond=None)[0]
    v = np.clip(uv[1], 0.0, 1.0)[:, None]
    out[edge] = p - v * g + v * new_bg
    return np.clip(np.round(out), 0, 255).astype(np.uint8)


def remove_flat_background_by_coverage(rgb: np.ndarray, mask: np.ndarray, png_background, new_background,
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
    border = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]]).astype(int)
    spread = int(np.abs(border - png_background.astype(int)).max())
    if spread > threshold:
        print(f"Warning: {os.path.basename(choice['local_png'])} background isn't flat (border varies "
              f"by {spread} > BACKGROUND_THRESHOLD {threshold}); raise BACKGROUND_THRESHOLD.")
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


def choices_triangle_panel(choices: list[dict], field_deg: float, background: np.ndarray,
                           threshold: float, margin: float, screen_color=(0, 0, 0),
                           band_px: int = 2, image_zoom: float = 1.0) -> Image.Image:
    """
    Three cut-out choices at the top centre, bottom-left and bottom-right corners of a
    square panel field_deg wide, so they are at the same scale (deg) as the sample panel. The
    panel's resolution is the finest of the choice pngs, so no choice is downsampled.
    image_zoom enlarges the choices themselves; the panel's field of view stays field_deg.
    """
    cutouts = [cut_out_choice(c, threshold, screen_color, band_px, background) for c in choices]
    scales = [d for _, _, d in cutouts if d is not None]
    if len(scales) != len(cutouts):
        raise RuntimeError("A choice spec has no dimensions, so it can't be put on the sample's scale.")
    ref = min(scales)  # deg per px of the panel
    shapes, masks = [], []
    for img, mask_img, deg_per_px in cutouts:
        f = deg_per_px / ref * image_zoom
        size = (max(1, round(img.width * f)), max(1, round(img.height * f)))
        if size != img.size:  # choices already at the common scale are left untouched
            img = resample(img, size)
            mask_img = mask_img.resize(size, Image.NEAREST)
        shapes.append(img)
        masks.append(mask_img)

    side = int(round(field_deg / ref))
    gap = margin * side
    top, left, right = shapes
    corners = [((side - top.width) / 2, gap),                       # top centre
               (gap, side - gap - left.height),                     # bottom-left
               (side - gap - right.width, side - gap - right.height)]  # bottom-right
    boxes = [(x0, y0, x0 + im.width, y0 + im.height) for (x0, y0), im in zip(corners, shapes)]
    if any(x0 < 0 or y0 < 0 for x0, y0, _, _ in boxes):
        print("Warning: a choice is cut off by the edge of its panel; lower ZOOM, IMAGE_ZOOM or CHOICE_MARGIN.")
    if any(boxes[i][0] < boxes[j][2] and boxes[j][0] < boxes[i][2] and
           boxes[i][1] < boxes[j][3] and boxes[j][1] < boxes[i][3] for i, j in ((0, 1), (1, 2), (0, 2))):
        print("Warning: choices may overlap; lower ZOOM or IMAGE_ZOOM.")

    canvas = Image.new("RGB", (side, side), tuple(int(v) for v in background))
    for (x0, y0, _, _), im, mk in zip(boxes, shapes, masks):
        canvas.paste(im, (int(round(x0)), int(round(y0))), mk)
    # centre of each choice, as a fraction of the panel (x right, y down)
    canvas.info['choice_centers'] = [((round(b[0]) + (b[2] - b[0]) / 2) / side,
                                      (round(b[1]) + (b[3] - b[1]) / 2) / side) for b in boxes]
    return canvas


def fixation_panel(side: int, fixation: dict, background: np.ndarray) -> Image.Image:
    """Empty screen with only the fixation square in the centre, on the sample panel's scale."""
    canvas = np.empty((side, side, 3), dtype=np.uint8)
    canvas[:] = background
    half = max(fixation['size_px'] / 2, 0.5)
    lo, hi = int(round(side / 2 - half)), int(round(side / 2 + half))
    hi = max(hi, lo + 1)
    canvas[lo:hi, lo:hi] = fixation['color']
    panel = Image.fromarray(canvas)
    panel.info['fixation_center'] = ((lo + hi) / 2, (lo + hi) / 2)  # pixel-edge coordinates
    return panel


def round_corners(panel: Image.Image, radius_fraction: float) -> Image.Image:
    panel = panel.convert("RGBA")
    if radius_fraction <= 0:
        return panel
    mask = Image.new("L", panel.size, 0)
    r = int(round(radius_fraction * min(panel.size)))
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, panel.width - 1, panel.height - 1), r, fill=255)
    panel.putalpha(mask)
    return panel


def draw_eye(ax, x: float, y: float, width: float, color, alpha: float = 1.0):
    """Eye symbol centred on (x, y) in data (pixel) coordinates: almond outline plus an open iris ring (no pupil, so the centre stays visible)."""
    from matplotlib.path import Path
    from matplotlib.patches import Circle, PathPatch
    w, h = width / 2, width * 0.3  # half width; control-point height of the lids
    lids = Path([(x - w, y), (x, y - 2 * h), (x + w, y), (x, y + 2 * h), (x - w, y)],
                [Path.MOVETO, Path.CURVE3, Path.CURVE3, Path.CURVE3, Path.CURVE3])
    lw = 2.5  # points, so the line weight is the same in every panel
    ax.add_patch(PathPatch(lids, facecolor="none", edgecolor=color, linewidth=lw, alpha=alpha))
    ax.add_patch(Circle((x, y), width * 0.17, facecolor="none", edgecolor=color, linewidth=lw,
                        alpha=alpha))


def plot_example_figure(panels: list[Image.Image], eye_rows=None, eye_size: float = 0.18,
                        eye_color="cyan"):
    """
    One row of the panels per entry of eye_rows (the same panels in every row). Each row gives,
    per panel, a list of (x, y, opacity) eye symbols with x, y as fractions of the panel.
    """
    eye_rows = eye_rows or [[[] for _ in panels]]
    # panel size grows with the field of view (sample panel px), so the stimuli keep their size
    inches = max(4.0, panels[-2 if len(panels) > 1 else 0].width / 80)
    fig, axes = plt.subplots(len(eye_rows), len(panels), squeeze=False,
                             figsize=(inches * len(panels), inches * len(eye_rows)),
                             gridspec_kw={'wspace': 0.04, 'hspace': 0.04})
    for row_axes, row_eyes in zip(axes, eye_rows):
        for ax, img, panel_eyes in zip(row_axes, panels, row_eyes):
            # antialiased: the window shows the native-resolution panel shrunk, and "none" or
            # "nearest" would alias (checkerboard / moire), worst on the noise
            ax.imshow(img, interpolation="antialiased")
            ax.set_axis_off()
            for x, y, alpha in panel_eyes:
                # eye is in pixel-edge coordinates; imshow centres pixel i on i, so shift by -0.5
                draw_eye(ax, x * img.width - 0.5, y * img.height - 0.5, eye_size * img.width,
                         eye_color, alpha)
    return fig


if __name__ == "__main__":
    main()
