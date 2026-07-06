from __future__ import annotations

"""Reusable engine for drawing stimuli as points in a 2D space, colored by
per-stimulus conditions.

This is the shared drawing core behind two callers that ask the *same* visual
question from opposite matrices:

  * ``StimulusPCAAnalysis`` (stimulus-as-point PCA): points are stimuli in
    neural **PC-score** space (their responses reduced over channels).

  * the cluster_app PC-interpretation exporter (channel-as-point PCA): points
    are stimuli in **loading** space -- PC1 loading on x, PC2 loading on y --
    which is what actually drives each channel PC.

Both want the same overlays: color stimuli by Texture / Lineage / GA Response /
StimType / center-of-mass / AlexNet similarity, and ring the included
delta/variant stimuli (connecting each pair with a line). Keeping that logic
here means the two views stay visually identical and only differ in the
coordinates fed in and the axis wording ("PC" vs "PC loading").

The engine never touches ``pyplot``: figures are built through an injected
``figure_factory`` (defaulting to a bare ``Figure``) so it is safe to call from
inside a running Qt event loop. A batch caller that wants ``plt.show()`` to pick
the figures up can pass ``figure_factory=plt.figure`` to get pyplot-managed
figures instead.
"""

import ast
import os
from dataclasses import dataclass, field
from typing import Callable, Optional, Sequence

import numpy as np
import pandas as pd
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import matplotlib.image as mpimg
from matplotlib.figure import Figure
from mpl_toolkits.axes_grid1.inset_locator import inset_axes

# A ``value_lookup`` maps a condition column name (e.g. "Texture") to a
# ``{stim_id: value}`` dict, or None when that column is unavailable.
ValueLookup = Callable[[str], Optional[dict]]

# Ring color + legend label per highlight role.
HIGHLIGHT_STYLE = {
    'variant': ('red', 'included variant'),
    'delta': ('black', 'included Δ (delta)'),
    'highlight': ('black', 'included Δ / variant'),
}


# ---- per-stimulus value lookups -----------------------------------------
def dataframe_value_lookup(compiled_data: Optional[pd.DataFrame]) -> ValueLookup:
    """Back a value_lookup with a compiled_data DataFrame keyed by StimSpecId."""
    def lookup(column: str) -> Optional[dict]:
        if compiled_data is None or column not in compiled_data.columns:
            return None
        sub = (compiled_data[['StimSpecId', column]]
               .dropna(subset=['StimSpecId'])
               .drop_duplicates('StimSpecId'))
        return dict(zip(sub['StimSpecId'], sub[column]))
    return lookup


def dict_value_lookup(columns: dict[str, dict]) -> ValueLookup:
    """Back a value_lookup with a preassembled ``{column: {stim_id: value}}``."""
    return lambda column: columns.get(column)


# ---- highlight spec ------------------------------------------------------
@dataclass
class HighlightSpec:
    """Which stimuli to ring on every scatter, and how.

    ``roles`` maps a role ('delta' / 'variant' / 'highlight') to a boolean mask
    over the stimulus order; ``items`` is ``[(pos, stim_id, role, letter), ...]``
    for per-point labels + the legend; ``pairs`` is ``[(delta_pos, variant_pos),
    ...]`` positions to connect with a line.
    """
    roles: dict[str, np.ndarray]
    items: list = field(default_factory=list)
    pairs: list = field(default_factory=list)


def _letter(k: int) -> str:
    """0->A, 1->B, ... 25->Z, 26->AA, 27->AB, ... (spreadsheet-style)."""
    s = ""
    k += 1
    while k > 0:
        k, r = divmod(k - 1, 26)
        s = chr(65 + r) + s
    return s


def _resolve_highlight_roles(ga_database: str, override) -> dict:
    """``{stim_id -> role}``. Honors a dict override directly, treats a set
    override as role-unknown ('highlight'), else reads ``IncludedDeltas``."""
    if override is not None:
        if isinstance(override, dict):
            return {int(k): v for k, v in override.items()}
        return {int(k): 'highlight' for k in override}
    return _load_included_delta_variant_roles(ga_database)


def _load_included_delta_variant_roles(ga_database: str) -> dict:
    """``{stim_id -> 'delta'|'variant'}`` for included REGIME_ESTIM_DELTA stimuli
    and their paired REGIME_ESTIM_VARIANTS, from ``IncludedDeltas``.

    Returns an empty dict if the table is missing/empty or unreadable."""
    try:
        from clat.util.connection import Connection
        conn = Connection(ga_database)
        conn.execute(
            "SELECT delta_id, variant_id FROM IncludedDeltas WHERE included = 1"
        )
        roles: dict = {}
        for delta_id, variant_id in conn.fetch_all():
            if delta_id is not None:
                roles[int(delta_id)] = 'delta'
            if variant_id is not None:
                roles[int(variant_id)] = 'variant'
        return roles
    except Exception as exc:
        print(f"Could not read IncludedDeltas (highlight skipped): {exc}")
        return {}


def _load_included_delta_variant_pairs(ga_database: str) -> list:
    """``[(delta_id, variant_id), ...]`` for the included pairs, from
    ``IncludedDeltas``. Empty if the table is missing/unreadable."""
    try:
        from clat.util.connection import Connection
        conn = Connection(ga_database)
        conn.execute(
            "SELECT delta_id, variant_id FROM IncludedDeltas WHERE included = 1"
        )
        pairs = []
        for delta_id, variant_id in conn.fetch_all():
            if delta_id is not None and variant_id is not None:
                pairs.append((int(delta_id), int(variant_id)))
        return pairs
    except Exception as exc:
        print(f"Could not read IncludedDeltas pairs (lines skipped): {exc}")
        return []


def build_highlight_spec(stim_ids: Sequence, ga_database: str, *,
                         stim_type_for_id: Optional[dict] = None,
                         override=None) -> Optional[HighlightSpec]:
    """Assemble the delta/variant highlight overlay for a given stimulus order.

    Args:
        stim_ids: the stimulus ids in row order of the scatter positions.
        ga_database: session db name holding the ``IncludedDeltas`` table.
        stim_type_for_id: ``{stim_id -> StimType}`` used to refine an unknown
            'highlight' role into 'delta' / 'variant'.
        override: optional ``highlighted_stim_ids`` -- a set (role unknown) or a
            dict ``{stim_id: role}``. Carries no pairing info, so no lines drawn.

    Returns a ``HighlightSpec`` or None when nothing is highlighted.
    """
    roles_for_id = _resolve_highlight_roles(ga_database, override)
    if not roles_for_id:
        return None

    stim_type_for_id = stim_type_for_id or {}
    stim_ids = list(stim_ids)
    role_per_index = []
    for sid in stim_ids:
        role = roles_for_id.get(sid)
        if role == 'highlight':
            st = stim_type_for_id.get(sid)
            if st == 'REGIME_ESTIM_VARIANTS':
                role = 'variant'
            elif st == 'REGIME_ESTIM_DELTA':
                role = 'delta'
        role_per_index.append(role)
    role_per_index = np.array(role_per_index, dtype=object)

    masks = {}
    for role in ('delta', 'variant', 'highlight'):
        mask = role_per_index == role
        if mask.any():
            masks[role] = mask
    if not masks:
        print("No highlighted (included delta/variant) stimuli are in this data.")
        return None

    # Stable letter (A, B, C, ...) per highlighted stimulus, grouped by role
    # then stim id, for per-point labels + the legend.
    items = [[pos, stim_ids[pos], role_per_index[pos]]
             for pos in range(len(stim_ids))
             if role_per_index[pos] in ('delta', 'variant', 'highlight')]
    items.sort(key=lambda t: (t[2], t[1]))
    for k, item in enumerate(items):
        item.append(_letter(k))
    items = [tuple(it) for it in items]

    # Positions of each paired delta/variant so scatters can connect them.
    pos_for_id = {sid: pos for pos, sid in enumerate(stim_ids)}
    pairs = []
    if override is None:
        for delta_id, variant_id in _load_included_delta_variant_pairs(ga_database):
            dp = pos_for_id.get(delta_id)
            vp = pos_for_id.get(variant_id)
            if dp is not None and vp is not None:
                pairs.append((dp, vp))

    summary = ", ".join(f"{int(m.sum())} {r}" for r, m in masks.items())
    print(f"Highlighting {summary}:")
    for _pos, sid, role, letter in items:
        print(f"  {letter} = {sid} ({role})")
    if pairs:
        print(f"Connecting {len(pairs)} delta/variant pair(s) with lines.")
    return HighlightSpec(roles=masks, items=items, pairs=pairs)


# ---- color helpers -------------------------------------------------------
def distinct_colors(n: int) -> list:
    """`n` visually distinct colors: strong tab10 hues first, then tab20b/c
    (50 total), falling back to evenly-spaced HSV beyond that."""
    palette: list = []
    for name in ('tab10', 'tab20b', 'tab20c'):
        palette.extend(cm.get_cmap(name).colors)
    if n <= len(palette):
        return [tuple(palette[i]) for i in range(n)]
    hues = np.linspace(0, 1, n, endpoint=False)
    return [tuple(mcolors.hsv_to_rgb((h, 0.65, 0.9))) for h in hues]


def category_colors(n: int, cmap: Optional[str]) -> list:
    """A color per category. Uses the named qualitative `cmap` when it has
    enough discrete entries; otherwise a large distinct palette."""
    if cmap is not None:
        listed = getattr(cm.get_cmap(cmap), 'colors', None)
        if listed is not None and n <= len(listed):
            return [listed[i] for i in range(n)]
    return distinct_colors(n)


def two_d_color_array(a_norm: np.ndarray, b_norm: np.ndarray) -> np.ndarray:
    """Map two [0,1] coordinates to RGB with each axis on its own strongly
    varying channel: axis-1 -> red, axis-2 -> green (constant blue floor so
    nothing is pure black)."""
    a = np.asarray(a_norm, dtype=float)
    b = np.asarray(b_norm, dtype=float)
    blue = np.full_like(a, 0.35)
    return np.clip(np.stack([a, b, blue], axis=-1), 0.0, 1.0)


def two_d_colors(ab: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Per-point RGB for an (n, 2) array, min-max normalized over `valid`."""
    out = np.zeros((len(ab), 3))
    sub = ab[valid]
    mn, mx = sub.min(axis=0), sub.max(axis=0)
    span = np.where((mx - mn) > 1e-12, mx - mn, 1.0)
    norm = (sub - mn) / span
    out[valid] = two_d_color_array(norm[:, 0], norm[:, 1])
    return out


def to_xyz(value) -> Optional[np.ndarray]:
    """Coerce a MassCenter-style value into a length-3 float array, or None.

    Handles tuples/lists of (x, y, z) and string reprs from the repository
    round-trip (e.g. ``"('0.1', '0.2', '0.3')"`` or ``"(0.1, 0.2, 0.3)"``).
    """
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    try:
        parsed = ast.literal_eval(value) if isinstance(value, str) else value
        parts = list(parsed)
        if len(parts) != 3:
            return None
        return np.array([float(p) for p in parts], dtype=float)
    except (ValueError, TypeError, SyntaxError):
        return None


def slug(column: str) -> str:
    return column.strip().lower().replace(' ', '_')


def _show_thumb(ax, path: Optional[str]) -> None:
    """Draw a stimulus thumbnail into `ax`, or a placeholder if it's missing /
    unreadable. Uses ``matplotlib.image`` (not pyplot) so it is Qt-safe."""
    ax.set_xticks([])
    ax.set_yticks([])
    if path and os.path.exists(path):
        try:
            ax.imshow(mpimg.imread(path))
            return
        except Exception:  # unreadable image -> placeholder, keep going
            ax.text(0.5, 0.5, "(unreadable)", ha='center', va='center', fontsize=6)
    else:
        ax.text(0.5, 0.5, "(no thumb)", ha='center', va='center',
                fontsize=7, color='gray')


# ---- the scatter figure builder -----------------------------------------
@dataclass
class ScatterFigure:
    """A produced figure plus the metadata a cycler/gallery needs: a display
    ``title`` and a filename ``slug``."""
    title: str
    slug: str
    figure: Figure


class StimulusScatterFigures:
    """Draw stimuli as points in a 2D space, colored by per-stimulus conditions.

    Args:
        positions: (n_stimuli, n_components) coordinates. Columns are the axes;
            PC1 vs PC2 is always drawn, PC3 vs PC4 too when >= 4 columns exist.
        stim_ids: stimulus ids in row order of ``positions``.
        value_lookup: ``column -> {stim_id: value}`` provider (see the
            ``*_value_lookup`` factories).
        variance_ratio: optional per-component fraction of variance, for axis
            labels; ``None`` omits the percentages (e.g. SparsePCA loadings).
        highlight: optional ``HighlightSpec`` to ring delta/variant stimuli.
        space: ``"score"`` labels axes "PC{n}"; ``"loading"`` labels them
            "PC{n} loading" and titles say "loading space".
        figure_factory: constructs blank figures; defaults to a bare ``Figure``
            (Qt-safe). Pass ``plt.figure`` for pyplot-managed figures.
    """

    def __init__(self, positions: np.ndarray, stim_ids: Sequence,
                 value_lookup: ValueLookup, *,
                 variance_ratio: Optional[np.ndarray] = None,
                 highlight: Optional[HighlightSpec] = None,
                 space: str = "score",
                 figure_factory: Callable[..., Figure] = Figure):
        self.positions = np.asarray(positions, dtype=float)
        self.stim_ids = list(stim_ids)
        self.value_lookup = value_lookup
        self.variance_ratio = variance_ratio
        self.highlight = highlight
        self.space = space
        self.figure_factory = figure_factory

    # ---- public: build the standard set ---------------------------------
    def build_standard(self, alexnet_pcs: Optional[dict] = None) -> list[ScatterFigure]:
        """The full set of condition scatters, in a stable order. Entries whose
        source column/data is unavailable are silently skipped, so callers get
        exactly the plots this data can support."""
        candidates = [
            lambda: self.categorical('Lineage', cmap='tab20'),
            lambda: self.continuous('GA Response'),
            lambda: self.categorical('Texture', cmap='Set1'),
            lambda: self.categorical('StimType', cmap=None),
            lambda: self.rgb('MassCenter'),
        ]
        if alexnet_pcs:
            candidates.append(lambda: self.alexnet(alexnet_pcs))
        figures = [make() for make in candidates]
        return [f for f in figures if f is not None]

    def build_pc_examples(self, max_pcs: int = 4, *,
                          n_bins: int = 5, n_per_bin: int = 6) -> list[ScatterFigure]:
        """One example-thumbnail grid per component (up to ``max_pcs``), binned
        by position along that PC. Components with no thumbnails / no spread are
        skipped."""
        figures = []
        for pc_idx in range(min(max_pcs, self.positions.shape[1])):
            sf = self.pc_examples(pc_idx, n_bins=n_bins, n_per_bin=n_per_bin)
            if sf is not None:
                figures.append(sf)
        return figures

    # ---- public: individual scatters ------------------------------------
    def categorical(self, column: str, cmap: Optional[str] = 'tab20') -> Optional[ScatterFigure]:
        """Stimuli colored by a discrete `column` (Lineage, Texture, StimType).
        ``cmap=None`` (or more categories than the map holds) uses a large
        distinct palette."""
        values = self.value_lookup(column)
        if values is None:
            print(f"Skipping '{column}' scatter: column not available.")
            return None

        per_stim = np.array([values.get(sid, None) for sid in self.stim_ids],
                            dtype=object)
        categories = [c for c in pd.unique(per_stim) if c is not None]
        colors = category_colors(len(categories), cmap)
        missing = per_stim == None  # noqa: E711  (elementwise on object array)

        def draw(ax, fig, px, py, is_first, is_last):
            if missing.any():
                ax.scatter(self.positions[missing, px], self.positions[missing, py],
                           s=20, color='lightgray', alpha=0.6,
                           label='(missing)' if is_first else None)
            for i, cat in enumerate(categories):
                mask = per_stim == cat
                ax.scatter(self.positions[mask, px], self.positions[mask, py],
                           s=25, alpha=0.8, color=colors[i],
                           label=str(cat) if is_first else None)
            if is_first and len(categories) <= 30:
                ax.legend(title=column, loc='best', fontsize=8, markerscale=1.2)

        return self._coloring(column, slug(column),
                              f"Stimuli in {self._space_word()} (colored by {column})",
                              draw)

    def continuous(self, column: str) -> Optional[ScatterFigure]:
        """Stimuli colored by a continuous `column` (e.g. GA Response)."""
        values = self.value_lookup(column)
        if values is None:
            print(f"Skipping '{column}' scatter: column not available.")
            return None

        raw = [values.get(sid, np.nan) for sid in self.stim_ids]
        vals = pd.to_numeric(pd.Series(raw), errors='coerce').to_numpy()
        valid = ~np.isnan(vals)
        vmin = float(np.min(vals[valid])) if valid.any() else 0.0
        vmax = float(np.max(vals[valid])) if valid.any() else 1.0

        def draw(ax, fig, px, py, is_first, is_last):
            if (~valid).any():
                ax.scatter(self.positions[~valid, px], self.positions[~valid, py],
                           s=20, color='lightgray', alpha=0.6)
            sc = ax.scatter(self.positions[valid, px], self.positions[valid, py],
                            c=vals[valid], cmap='viridis', s=28, alpha=0.9,
                            vmin=vmin, vmax=vmax)
            fig.colorbar(sc, ax=ax, label=column)

        return self._coloring(column, slug(column),
                              f"Stimuli in {self._space_word()} (colored by {column})",
                              draw)

    def rgb(self, column: str) -> Optional[ScatterFigure]:
        """Stimuli colored by a 3-vector `column` (e.g. MassCenter x/y/z) mapped
        to RGB, each component min-max normalized across stimuli."""
        values = self.value_lookup(column)
        if values is None:
            print(f"Skipping '{column}' RGB scatter: column not available.")
            return None

        raw = [values.get(sid) for sid in self.stim_ids]
        coords = np.full((len(raw), 3), np.nan)
        for i, v in enumerate(raw):
            vec = to_xyz(v)
            if vec is not None:
                coords[i] = vec
        valid = ~np.isnan(coords).any(axis=1)
        if not valid.any():
            print(f"Skipping '{column}' RGB scatter: no parseable (x, y, z) values.")
            return None

        rgb = np.zeros((len(raw), 3))
        cmin = coords[valid].min(axis=0)
        cmax = coords[valid].max(axis=0)
        span = np.where((cmax - cmin) > 1e-12, cmax - cmin, 1.0)
        rgb[valid] = np.clip((coords[valid] - cmin) / span, 0.0, 1.0)

        def draw(ax, fig, px, py, is_first, is_last):
            if (~valid).any():
                ax.scatter(self.positions[~valid, px], self.positions[~valid, py],
                           s=20, color='lightgray', alpha=0.5)
            ax.scatter(self.positions[valid, px], self.positions[valid, py],
                       c=rgb[valid], s=32, alpha=0.95, edgecolor='none')
            if is_first:
                ax.text(0.99, 0.01, "R = x   G = y   B = z\n(each min–max normalized)",
                        transform=ax.transAxes, ha='right', va='bottom',
                        fontsize=8, color='dimgray')

        return self._coloring(column, slug(column),
                              f"Stimuli in {self._space_word()} (colored by {column} → RGB)",
                              draw)

    def alexnet(self, alexnet_pcs: dict,
                key_labels: tuple[str, str] = ("AlexNet PC1", "AlexNet PC2")) -> Optional[ScatterFigure]:
        """Stimuli colored by the first two PCs of their AlexNet conv3
        activations, mapped to a 2D color (PC1->x/red, PC2->y/green)."""
        raw = [alexnet_pcs.get(sid) for sid in self.stim_ids]
        ab = np.full((len(raw), 2), np.nan)
        for i, v in enumerate(raw):
            if v is not None and len(v) >= 2:
                ab[i] = [float(v[0]), float(v[1])]
        valid = ~np.isnan(ab).any(axis=1)
        if not valid.any():
            print("Skipping AlexNet scatter: no usable coordinates.")
            return None

        colors = two_d_colors(ab, valid)

        def draw(ax, fig, px, py, is_first, is_last):
            if (~valid).any():
                ax.scatter(self.positions[~valid, px], self.positions[~valid, py],
                           s=20, color='lightgray', alpha=0.5)
            ax.scatter(self.positions[valid, px], self.positions[valid, py],
                       c=colors[valid], s=32, alpha=0.95, edgecolor='none')
            if is_last:
                self._add_2d_color_key(ax, key_labels[0], key_labels[1])

        return self._coloring(
            "AlexNet conv3 PCA", "alexnet_conv3_pca",
            f"Stimuli in {self._space_word()} (colored by AlexNet conv3 PCA: PC1→x, PC2→y)",
            draw, right_pad_in=2.0)

    def pc_examples(self, pc_idx: int, *,
                    n_bins: int = 5, n_per_bin: int = 6) -> Optional[ScatterFigure]:
        """Grid of example thumbnails for one PC: rows are equal-width value
        ranges of the PC (high at top), each row showing several example stimuli
        drawn from that range. In loading space the "value" is the stimulus's
        loading on that PC, so the grid reads as "what stimuli drive this PC."
        """
        thumbs = self.value_lookup('ThumbnailPath')
        if thumbs is None:
            print(f"Skipping PC{pc_idx + 1} examples: 'ThumbnailPath' not available.")
            return None
        if pc_idx >= self.positions.shape[1]:
            return None

        pc = self.positions[:, pc_idx]
        lo, hi = float(np.min(pc)), float(np.max(pc))
        if hi - lo < 1e-12:
            print(f"Skipping PC{pc_idx + 1} examples: no spread along this PC.")
            return None
        edges = np.linspace(lo, hi, n_bins + 1)

        fig = self.figure_factory(figsize=(2.0 * n_per_bin, 2.3 * n_bins))
        axes = fig.subplots(n_bins, n_per_bin, squeeze=False)
        for row in range(n_bins):
            bin_idx = n_bins - 1 - row  # top row = highest range
            b_lo, b_hi = edges[bin_idx], edges[bin_idx + 1]
            if bin_idx == n_bins - 1:  # include the right edge in the top bin
                in_bin = np.where((pc >= b_lo) & (pc <= b_hi))[0]
            else:
                in_bin = np.where((pc >= b_lo) & (pc < b_hi))[0]
            in_bin = in_bin[np.argsort(pc[in_bin])]
            if len(in_bin) > n_per_bin:
                sel = in_bin[np.linspace(0, len(in_bin) - 1, n_per_bin).round().astype(int)]
            else:
                sel = in_bin

            for col in range(n_per_bin):
                ax = axes[row][col]
                if col < len(sel):
                    _show_thumb(ax, thumbs.get(self.stim_ids[sel[col]]))
                else:
                    ax.axis('off')
            # Range label on the leftmost cell (frame off, keep the y-label).
            left = axes[row][0]
            left.set_xticks([])
            left.set_yticks([])
            for spine in left.spines.values():
                spine.set_visible(False)
            left.set_ylabel(f"[{b_lo:.1f}, {b_hi:.1f}]\nn={len(in_bin)}",
                            fontsize=8, rotation=0, ha='right', va='center', labelpad=28)

        suffix = " loading" if self.space == "loading" else ""
        title = (f"Example stimuli by PC{pc_idx + 1}{suffix} range "
                 f"({self._var_text(pc_idx)}top = high)")
        fig.suptitle(title)
        fig.tight_layout()
        name_slug = f"pc{pc_idx + 1}{'_loading' if self.space == 'loading' else ''}_examples"
        return ScatterFigure(title=title, slug=name_slug, figure=fig)

    # ---- shared multi-panel layout --------------------------------------
    def _coloring(self, column: str, name_slug: str, suptitle: str, draw_fn,
                  right_pad_in: float = 0.0) -> ScatterFigure:
        """One figure with PC1/PC2 (and PC3/PC4 when >= 4 components) side by
        side. ``draw_fn(ax, fig, pc_x, pc_y, is_first, is_last)`` paints a single
        panel."""
        pc_pairs = [(0, 1)]
        if self.positions.shape[1] >= 4:
            pc_pairs.append((2, 3))

        # Reserve real space at the bottom for the highlight legend so it stays
        # inside the figure for both an interactive canvas and a saved PNG.
        caption = self._highlight_caption()
        n_cap_lines = caption.count('\n') + 1 if caption else 0
        extra_h = 0.32 * n_cap_lines

        fig_h = 7.0 + extra_h
        fig_w = 7.5 * len(pc_pairs) + right_pad_in
        fig = self.figure_factory(figsize=(fig_w, fig_h))
        axes = np.atleast_1d(fig.subplots(1, len(pc_pairs)))
        last = len(pc_pairs) - 1
        for i, (ax, (px, py)) in enumerate(zip(axes, pc_pairs)):
            draw_fn(ax, fig, px, py, i == 0, i == last)
            self._draw_highlights(ax, px, py, annotate=(i == 0))
            self._axis_labels(ax, px, py)
            ax.set_title(self._pc_pair_label(px, py))
        fig.suptitle(suptitle)

        bottom_frac = (extra_h + 0.25) / fig_h if caption else 0.0
        right_frac = 1.0 - (right_pad_in / fig_w) if right_pad_in else 1.0
        fig.tight_layout(rect=[0, bottom_frac, right_frac, 1])
        if caption:
            fig.text(0.5 * right_frac, bottom_frac * 0.55, caption,
                     ha='center', va='center', fontsize=8, family='monospace')
        return ScatterFigure(title=suptitle, slug=name_slug, figure=fig)

    # ---- axis + highlight rendering -------------------------------------
    def _space_word(self) -> str:
        return "loading space" if self.space == "loading" else "PC space"

    def _axis_labels(self, ax, pc_x: int, pc_y: int) -> None:
        suffix = " loading" if self.space == "loading" else ""
        ax.set_xlabel(f"PC{pc_x + 1}{suffix}{self._var_pct(pc_x)}")
        ax.set_ylabel(f"PC{pc_y + 1}{suffix}{self._var_pct(pc_y)}")

    def _var_pct(self, pc: int) -> str:
        evr = self.variance_ratio
        if evr is None or pc >= len(evr):
            return ""
        return f" ({evr[pc] * 100:.1f}%)"

    def _var_text(self, pc: int) -> str:
        """'12.3% var; ' for a PC with known variance, else '' -- used inside the
        pc-examples title, which stays legible with or without the percentage."""
        evr = self.variance_ratio
        if evr is None or pc >= len(evr):
            return ""
        return f"{evr[pc] * 100:.1f}% var; "

    def _pc_pair_label(self, pc_x: int, pc_y: int) -> str:
        suffix = " loading" if self.space == "loading" else ""
        return f"PC{pc_x + 1} vs PC{pc_y + 1}{suffix}"

    def _draw_highlights(self, ax, pc_x: int, pc_y: int, annotate: bool) -> None:
        """Ring the highlighted stimuli (one ring color per role), connect each
        delta/variant pair with a line, and label each point with its letter."""
        if not self.highlight:
            return
        positions = self.positions
        for dp, vp in self.highlight.pairs:
            ax.plot([positions[dp, pc_x], positions[vp, pc_x]],
                    [positions[dp, pc_y], positions[vp, pc_y]],
                    color='dimgray', linestyle='-', linewidth=1.0,
                    alpha=0.7, zorder=5)
        y = 0.01
        for role, mask in self.highlight.roles.items():
            color, lbl = HIGHLIGHT_STYLE.get(role, ('black', role))
            ax.scatter(positions[mask, pc_x], positions[mask, pc_y], s=180,
                       facecolors='none', edgecolors=color, linewidths=1.8, zorder=6)
            if annotate:
                ax.text(0.01, y, f"○ {lbl} (n={int(mask.sum())})",
                        transform=ax.transAxes, ha='left', va='bottom',
                        fontsize=8, color=color,
                        bbox=dict(boxstyle='round', fc='white', ec='gray', alpha=0.75))
                y += 0.05
        if annotate and self.highlight.pairs:
            ax.text(0.01, y, f"— Δ↔variant pair (n={len(self.highlight.pairs)})",
                    transform=ax.transAxes, ha='left', va='bottom',
                    fontsize=8, color='dimgray',
                    bbox=dict(boxstyle='round', fc='white', ec='gray', alpha=0.75))
        for pos, _sid, role, letter in self.highlight.items:
            color = HIGHLIGHT_STYLE.get(role, ('black', role))[0]
            ax.annotate(letter, (positions[pos, pc_x], positions[pos, pc_y]),
                        xytext=(5, 5), textcoords='offset points',
                        fontsize=9, fontweight='bold', color=color, zorder=7)

    def _highlight_caption(self) -> Optional[str]:
        """A 'A = <id> (role)' legend for the ringed stimuli, a few per line."""
        if not self.highlight or not self.highlight.items:
            return None
        entries = [f"{letter} = {sid} ({role})"
                   for _pos, sid, role, letter in self.highlight.items]
        per_line = 3
        lines = ["     ".join(entries[i:i + per_line])
                 for i in range(0, len(entries), per_line)]
        return "Highlighted stimuli:\n" + "\n".join(lines)

    def _add_2d_color_key(self, ax, xlabel: str, ylabel: str) -> None:
        """Small 2D color-map key placed *outside* the right edge of `ax`, in the
        margin reserved via ``_coloring(right_pad_in=...)``."""
        cax = inset_axes(
            ax, width="100%", height="100%",
            bbox_to_anchor=(1.06, 0.38, 0.22, 0.24),
            bbox_transform=ax.transAxes, loc='lower left', borderpad=0,
        )
        n = 50
        aa, bb = np.meshgrid(np.linspace(0, 1, n), np.linspace(0, 1, n))
        grid = two_d_color_array(aa.ravel(), bb.ravel()).reshape(n, n, 3)
        cax.imshow(grid, origin='lower', extent=[0, 1, 0, 1], aspect='auto')
        cax.set_xticks([])
        cax.set_yticks([])
        cax.set_xlabel(xlabel, fontsize=7)
        cax.set_ylabel(ylabel, fontsize=7)
        cax.set_title("color key", fontsize=7)
