"""
The data columns a probe figure can show. Each column is one per-channel quantity
(or a small set of them, e.g. one per frequency) drawn as dots down the probe.

Every column is listed in COLUMNS with a key, a label and whether it is on by
default. ``build_block(key, data, opts)`` turns a key into a ColumnBlock (the values
plus how to colour them); a column whose data the session doesn't have raises NoData
with the reason, so the figure can skip it and say why.

Where each column comes from (the scripts it replaces):
  preference_cluster.py          preferred frequency, deepest orientation-tuning
                                 frequency, preferred orientation, preferred colour,
                                 isochromatic preference per frequency, solid
                                 preference + significance, ρ vs each GA channel
  delta_variant_correlation.py   ρ on delta/variant stims, ρ on top-N GA stims,
                                 variant vs delta |d'|, RWA and axis-coding prediction r
  plot_estim_correlation_spread  ρ vs the average estim-channel response
  plot_cluster_correlation_spread
    (branch ga-cluster-correlation-extent)
                                 ρ vs the average GA-channel response, with the
                                 contiguous extent at a fixed ρ*
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

import numpy as np

from src.analysis.probe_analysis.correlation import contiguous_extent, group_reference_rhos
from src.analysis.probe_analysis.probe_data import ProbeData, finite_values, parse_channel_list


class NoData(Exception):
    """The session has no data for this column (message says what is missing)."""


# Colour scales. 'diverging' columns share one -1..+1 colorbar.
DIVERGING, CYCLIC, CATEGORICAL, SEQUENTIAL = 'diverging', 'cyclic', 'categorical', 'sequential'


@dataclass
class SubColumn:
    title: str
    data: Dict[str, float]
    self_channel: Optional[str] = None


@dataclass
class ColumnBlock:
    key: str
    label: str                   # group label over the block ('' = none)
    subs: List[SubColumn]
    scale: str = DIVERGING
    vmax: float = 1.0            # SEQUENTIAL only: top of the colour scale
    scale_label: str = ""        # SEQUENTIAL / CYCLIC colorbar label
    categories: List[str] = field(default_factory=list)       # CATEGORICAL
    category_colors: Dict[str, str] = field(default_factory=dict)
    ringed: set = field(default_factory=set)       # channels drawn with a ring (ρ ≥ ρ*)
    extent_rows: Optional[tuple] = None            # (top row, bottom row) to shade
    note: str = ""                                 # one-line result for the status bar


@dataclass
class ColumnDef:
    key: str
    label: str        # checkbox label
    group: str        # section in the toggle list
    default: bool
    build: Callable[[ProbeData, dict], ColumnBlock]
    tooltip: str = ""


# Default options for the builders. The explorer module and the script override them.
DEFAULT_OPTIONS = {
    'vector_type': 'ga_mean_response',   # ChannelResponseVectors vector type
    'corr_method': 'spearman',           # 'spearman' or 'pearson'
    'corr_reference': 'GA',              # 'GA' = every GA channel, or 'A-022, A-008'
    'group_leave_one_out': True,         # group ρ: compare a group channel with the others
    'rho_threshold': 0.5,                # ρ* for the GA-average extent
    'n_misses_to_stop': 2,               # channels in a row below ρ* that end the walk
    'top_n': 20,                         # top-N GA stims for the top-N correlation
    'included_only': True,               # delta/variant: only IncludedDeltas.included
    'axis_strategy': 'multi_prototype_pca',
    'iso_frequencies': None,             # None = every tested frequency, or e.g. [12]
    'estim_channels': [],                # resolved from the EStim spec box
}


# ---------------------------------------------------------------- helpers

def _require(data, what):
    if not data or not finite_values(data) and not any(isinstance(v, str) for v in data.values()):
        raise NoData(f"no {what}")
    return data


def _normalize_to_range(values: Dict[str, float], frequencies) -> Dict[str, float]:
    """Map frequencies to [-1, 1]: lowest tested -> -1 (blue), highest -> +1 (red)."""
    if frequencies:
        lo, hi = min(frequencies), max(frequencies)
    else:
        vals = finite_values(values)
        lo, hi = (min(vals), max(vals)) if vals else (0.0, 1.0)
    span = hi - lo
    return {ch: (2.0 * (f - lo) / span - 1.0) if span > 0 else 0.0
            for ch, f in values.items() if f is not None}


def _iso_frequencies(data: ProbeData):
    try:
        return data.isochromatic()[0]
    except Exception:
        return []


def _reference_channels(data: ProbeData, opts, matrix):
    refs = parse_channel_list(opts['corr_reference'], data.ga_channels())
    with_data = [r for r in refs if r in matrix]
    if not with_data:
        raise NoData(f"no response data for reference channel(s) {refs or '(no GA channels)'}")
    return with_data


def _per_reference(matrix, refs, opts, zscore=False, title_suffix=""):
    from src.analysis.channel_metric_plot import StimVectorCorrelation
    subs = []
    for ref in refs:
        metric = StimVectorCorrelation.vs_channel(matrix, ref, method=opts['corr_method'],
                                                  zscore=zscore)
        subs.append(SubColumn(f"ρ vs {ref}{title_suffix}", metric.compute(),
                              self_channel=ref))
    return subs


def _vectors(data: ProbeData, opts):
    matrix = data.response_vectors(opts['vector_type'])
    if not matrix:
        raise NoData(f"no GA response vectors ({opts['vector_type']})")
    return matrix


# ---------------------------------------------------------------- tuning columns

def _pref_freq(data, opts):
    values = _require(data.preferred_frequency(), "preferred frequencies")
    return ColumnBlock('pref_freq', '', [SubColumn(
        "Preferred\nfrequency", _normalize_to_range(values, _iso_frequencies(data)))])


def _orient_freq(data, opts):
    values = _require(data.orientation_tuning_frequency(), "orientation tuning data")
    return ColumnBlock('orient_freq', '', [SubColumn(
        "Orientation\ntuning freq.", _normalize_to_range(values, _iso_frequencies(data)))])


def _pref_orient(data, opts, period=180.0):
    values = _require(data.preferred_orientation(), "preferred orientations")
    folded = {ch: ((a % period) / (period / 2.0)) - 1.0 for ch, a in values.items()}
    return ColumnBlock('pref_orient', '', [SubColumn("Preferred\norientation", folded)],
                       scale=CYCLIC, scale_label="Preferred orientation")


def _pref_color(data, opts):
    from src.analysis.isogabor.preferred_color import TYPE_DISPLAY_COLORS, TYPE_ORDER
    values = data.preferred_color()
    if not values:
        raise NoData("no preferred colours")
    index_of = {t: i for i, t in enumerate(TYPE_ORDER)}
    indexed = {ch: float(index_of[c]) for ch, c in values.items() if c in index_of}
    return ColumnBlock('pref_color', '', [SubColumn("Preferred\ncolour", indexed)],
                       scale=CATEGORICAL, categories=list(TYPE_ORDER),
                       category_colors=dict(TYPE_DISPLAY_COLORS))


def _isochromatic(data, opts):
    frequencies, by_freq = data.isochromatic()
    if not frequencies:
        raise NoData("no isochromatic preference indices")
    if opts['iso_frequencies']:
        wanted = [float(f) for f in opts['iso_frequencies']]
        frequencies = [f for f in frequencies if any(abs(f - w) < 1e-6 for w in wanted)]
        if not frequencies:
            raise NoData(f"no isochromatic data at {wanted} Hz")
    return ColumnBlock('iso', 'Isochromatic preference',
                       [SubColumn(f"{f:g} Hz", by_freq[f]) for f in frequencies])


def _solid(data, opts):
    return ColumnBlock('solid', '', [SubColumn(
        "Solid\npreference", _require(data.solid_preference(), "solid preference indices"))])


def _solid_sig(data, opts):
    values = data.solid_significance_strength()
    if not values:
        raise NoData("no solid preference p-values (permutation test not run)")
    return ColumnBlock('solid_sig', '', [SubColumn("Solid pref.\nsignificance", values)])


# ---------------------------------------------------------------- correlation columns

def _corr_each(data, opts):
    matrix = _vectors(data, opts)
    refs = _reference_channels(data, opts, matrix)
    return ColumnBlock('corr_each', 'ρ, GA mean response', _per_reference(matrix, refs, opts))


def _corr_ga_avg(data, opts):
    matrix = _vectors(data, opts)
    ga = [g for g in sorted(data.ga_channels()) if g in matrix]
    if not ga:
        raise NoData("no GA channels with response vectors")
    rhos = group_reference_rhos(matrix, ga, method=opts['corr_method'],
                                leave_one_out=opts['group_leave_one_out'])
    channels = data.channel_strs()
    ext = contiguous_extent(channels, data.positions_um(), rhos, set(ga),
                            rho_threshold=opts['rho_threshold'],
                            n_misses_to_stop=opts['n_misses_to_stop'])
    block = ColumnBlock('corr_ga_avg', '', [SubColumn("ρ vs GA\naverage", rhos)])
    if ext is not None:
        block.ringed = {ch for ch, a in zip(channels, ext['above']) if a}
        block.extent_rows = (ext['up_edge'], ext['down_edge'])
        ends = [side for side, hit in (('up', ext['up_reached_end']),
                                       ('down', ext['down_reached_end'])) if hit]
        block.note = (f"GA extent {ext['extent_total_um']:.0f} µm at ρ* = "
                      f"{ext['rho_threshold']:.2f} (up {ext['extent_up_um']:.0f}, "
                      f"down {ext['extent_down_um']:.0f})"
                      + (f", reaches probe end {'/'.join(ends)}" if ends else ""))
    return block


def _corr_estim_avg(data, opts):
    estim = list(opts['estim_channels'])
    if not estim:
        raise NoData("no estim channels chosen (set 'EStim spec')")
    matrix = _vectors(data, opts)
    with_data = [e for e in estim if e in matrix]
    if not with_data:
        raise NoData(f"no response vectors for estim channels {estim}")
    rhos = group_reference_rhos(matrix, with_data, method=opts['corr_method'],
                                leave_one_out=opts['group_leave_one_out'])
    return ColumnBlock('corr_estim_avg', '', [SubColumn("ρ vs estim\naverage", rhos)])


def _corr_dv(data, opts):
    ids = data.delta_variant_stim_ids(opts['included_only'])
    if not ids:
        raise NoData("no delta/variant stims in IncludedDeltas")
    matrix = data.raw_matrix(ids)
    if not matrix:
        raise NoData("no spike data for the delta/variant stims")
    refs = _reference_channels(data, opts, matrix)
    which = "included" if opts['included_only'] else "all"
    return ColumnBlock('corr_dv', f'ρ, delta/variant stims ({which})',
                       _per_reference(matrix, refs, opts, zscore=True))


def _corr_topn(data, opts):
    if not data.ga_responses():
        raise NoData("no GA Response in GAStimInfo")
    matrix = data.raw_matrix(data.top_n_stim_ids(opts['top_n']))
    if not matrix:
        raise NoData("no spike data for the top GA stims")
    refs = _reference_channels(data, opts, matrix)
    return ColumnBlock('corr_topn', f"ρ, top {opts['top_n']} GA stims",
                       _per_reference(matrix, refs, opts, zscore=True))


def _dprime(data, opts):
    from src.analysis.nafc.group_analysis.compute_estim_neighbor_scores import \
        DeltaVariantDPrime
    v2d = data.variant_to_deltas(opts['included_only'])
    if not v2d:
        raise NoData("no delta/variant pairs")
    matrix = data.raw_matrix(data.delta_variant_stim_ids(opts['included_only']))
    scorer = DeltaVariantDPrime('dprime', matrix, v2d, min_pairs=2)
    values = {ch: scorer.channel_score(ch) for ch in data.channel_strs()}
    finite = finite_values(values)
    if not finite:
        raise NoData("too few delta/variant pairs for d'")
    return ColumnBlock('dprime', '', [SubColumn("Variant vs\ndelta |d'|", values)],
                       scale=SEQUENTIAL, vmax=max(finite),
                       scale_label="|d'|, variant vs delta")


def _prediction_block(key, label, metrics):
    return ColumnBlock(key, label, [SubColumn(m.title.split()[0], m.compute())
                                    for m in metrics])


def _rwa(data, opts):
    loader = data.rwa_loader()
    if loader is None:
        raise NoData("no current GA experiment for the RWA")
    metrics = loader.as_metrics(data.all_ga_matrix())
    if metrics is None:
        raise NoData("no RWA pickle files")
    return _prediction_block('rwa', 'RWA prediction r', metrics)


def _axis(data, opts):
    loader = data.axis_coding_loader(opts['axis_strategy'])
    if loader is None:
        raise NoData(f"no axis-coding folder ({data.axis_coding_dir()})")
    metrics = loader.as_metrics(data.all_ga_matrix())
    if metrics is None:
        raise NoData(f"no axis-coding JSONs for {opts['axis_strategy']}")
    return _prediction_block('axis', 'Axis-coding prediction r', metrics)


# ---------------------------------------------------------------- registry

TUNING, CORRELATION, DELTA, MODEL = ("Tuning", "Correlation (GA mean response)",
                                     "Delta/variant & top-N (spike rates)",
                                     "Model predictions")

COLUMNS: List[ColumnDef] = [
    ColumnDef('pref_freq', "Preferred frequency", TUNING, True, _pref_freq,
              "Lowest tested frequency = -1 (blue), highest = +1 (red)."),
    ColumnDef('orient_freq', "Orientation tuning freq.", TUNING, True, _orient_freq,
              "Frequency where orientation tuning is deepest (max - min), same scale "
              "as preferred frequency."),
    ColumnDef('pref_orient', "Preferred orientation", TUNING, True, _pref_orient,
              "At the preferred frequency (else the next higher one), folded mod 180°."),
    ColumnDef('pref_color', "Preferred colour", TUNING, True, _pref_color,
              "Best gabor type at the preferred frequency."),
    ColumnDef('iso', "Isochromatic preference", TUNING, True, _isochromatic,
              "One column per tested frequency."),
    ColumnDef('solid', "Solid preference", TUNING, True, _solid),
    ColumnDef('solid_sig', "Solid pref. significance", TUNING, True, _solid_sig,
              "Full colour when p < 0.05, paler as p grows; sign = 3D (red) / 2D (blue)."),
    ColumnDef('corr_each', "ρ vs each GA channel", CORRELATION, True, _corr_each,
              "One column per reference channel (see 'Reference channels')."),
    ColumnDef('corr_ga_avg', "ρ vs GA average + extent", CORRELATION, False, _corr_ga_avg,
              "ρ with the average z-scored GA response. Ringed: ρ ≥ ρ*. Shaded: "
              "contiguous extent (walk up / down from the GA channels)."),
    ColumnDef('corr_estim_avg', "ρ vs estim average", CORRELATION, False, _corr_estim_avg,
              "ρ with the average z-scored response of the estim channels "
              "(needs 'EStim spec')."),
    ColumnDef('corr_dv', "ρ on delta/variant stims", DELTA, False, _corr_dv,
              "Spike-rate correlation over the IncludedDeltas stims."),
    ColumnDef('corr_topn', "ρ on top-N GA stims", DELTA, False, _corr_topn,
              "Spike-rate correlation over the top-N stims by GA Response."),
    ColumnDef('dprime', "Variant vs delta |d'|", DELTA, False, _dprime),
    ColumnDef('rwa', "RWA prediction r", MODEL, False, _rwa,
              "Pearson r between each channel and the shaft / termination / junction "
              "RWA prediction."),
    ColumnDef('axis', "Axis-coding prediction r", MODEL, False, _axis),
]

COLUMN_BY_KEY = {c.key: c for c in COLUMNS}


def build_blocks(keys, data: ProbeData, opts: dict):
    """(blocks, skipped) for the column keys in order. skipped = [(label, reason)]."""
    opts = {**DEFAULT_OPTIONS, **opts}
    blocks, skipped = [], []
    for key in keys:
        col = COLUMN_BY_KEY[key]
        try:
            blocks.append(col.build(data, opts))
        except NoData as exc:
            skipped.append((col.label, str(exc)))
    return blocks, skipped
