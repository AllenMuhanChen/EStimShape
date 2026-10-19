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

Output: <SAVE_ROOT>/<session>/ga_noise_example/<ga_stim_id>_<timestamp>/
  noisy_stimulus.png (native resolution, frame 0), noisy_stimulus_frame<k>.png for later frames,
  figure.png, config.json.
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
from PIL import Image


def main():
    # ---- Parameters -------------------------------------------------------------------------
    SESSION_ID = "260603_0"        # session the GA stim belongs to; None = keep current context
    GA_STIM_ID = 1780507913222760     # GA stim id to render with noise
    NAFC_STIM_ID = None            # None = latest NAFC trial with this GA stim as its sample;
                                   # or an NAFC StimSpec id to use that trial's noise map
    NOISE_CHANCE = None            # noise amount: peak chance a pixel is noise (0-1), like the
                                   # NAFC noiseChance parameter. None = as the trial used.
    N_FRAMES = 1                   # number of noise frames (twinkle); frame 0 is what the
                                   # monkey sees on the first frame
    RANDOM_SEED = None             # int for a reproducible noise pattern, None = new each run
    NAFC_STIMULI_DIR = None        # None = <base_dir>/<nafc_database>/stimuli (searched for pngs)
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
            f"(no BaseMStickId row with a noise map). Check SESSION_ID and GA_STIM_ID.")
    print(f"NAFC trials with GA stim {GA_STIM_ID} as sample: "
          f"{[c['nafc_stim_id'] for c in candidates]}")

    if NAFC_STIM_ID is None:
        chosen = candidates[0]
    else:
        matches = [c for c in candidates if c['nafc_stim_id'] == NAFC_STIM_ID]
        if not matches:
            raise RuntimeError(f"NAFC stim {NAFC_STIM_ID} is not a trial of GA stim {GA_STIM_ID}.")
        chosen = matches[0]
    print(f"Using NAFC trial {chosen['nafc_stim_id']} (sample obj {chosen['sample_obj_id']})")

    sample_png = locate_local_file(chosen['png_path'], stimuli_dir)
    noise_map_png = locate_local_file(chosen['noise_map_path'], stimuli_dir)
    print(f"Sample png:    {sample_png}")
    print(f"Noise map png: {noise_map_png}")

    sample_rgb = load_rgb(sample_png)
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

    fig = plot_noisy_frames(noisy_frames)
    fig.savefig(os.path.join(out_dir, "figure.png"), dpi=200, bbox_inches="tight")

    config = {
        "session_id": SESSION_ID,
        "ga_database": context.ga_database,
        "nafc_database": context.nafc_database,
        "ga_stim_id": GA_STIM_ID,
        "nafc_stim_id": chosen['nafc_stim_id'],
        "nafc_sample_obj_id": chosen['sample_obj_id'],
        "candidate_nafc_stim_ids": [c['nafc_stim_id'] for c in candidates],
        "sample_png": sample_png,
        "noise_map_png": noise_map_png,
        "noise_color_rgb": list(chosen['color']),
        "trial_noise_chance": trial_peak,
        "noise_chance": NOISE_CHANCE,
        "n_frames": N_FRAMES,
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
    spec has a noise map. Each entry: nafc_stim_id, sample_obj_id, png_path, noise_map_path,
    color (0-255 RGB).
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
        sample_obj_id = int(xmltodict.parse(stim_spec_xml)['StimSpec']['sampleObjData'])

        nafc_conn.execute("SELECT spec FROM StimObjData WHERE id = %s", params=(sample_obj_id,))
        sample_spec_xml = nafc_conn.fetch_one()
        if not sample_spec_xml:
            continue
        sample_spec = parse_noisy_png_spec(sample_spec_xml)
        if not sample_spec['noise_map_path']:
            continue
        candidates.append({'nafc_stim_id': nafc_stim_id, 'sample_obj_id': sample_obj_id, **sample_spec})
    return candidates


def parse_noisy_png_spec(xml: str) -> dict:
    """Read pngPath, noiseMapPath and color (java.awt.Color via XStream) from a NoisyPngSpec."""
    spec = xmltodict.parse(xml)['StimSpec']
    color = spec.get('color') or {}
    rgb = tuple(int(color.get(c, 255)) for c in ('red', 'green', 'blue'))
    return {
        'png_path': spec.get('pngPath') or '',
        'noise_map_path': spec.get('noiseMapPath') or '',
        'color': rgb,
    }


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

def load_rgb(path: str) -> np.ndarray:
    return np.array(Image.open(path).convert("RGB"), dtype=np.uint8)


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

def plot_noisy_frames(noisy_frames: list[np.ndarray]):
    n = len(noisy_frames)
    fig, axes = plt.subplots(1, n, figsize=(6 * n, 6), squeeze=False)
    for ax, img in zip(axes[0], noisy_frames):
        ax.imshow(img, interpolation="nearest")
        ax.set_axis_off()
    fig.tight_layout()
    return fig


if __name__ == "__main__":
    main()
