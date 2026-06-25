"""
channel_data_loaders.py
-----------------------
Data-loading classes that feed ChannelMetric instances.

Loader classes encapsulate SQL queries and file I/O so that the main analysis
functions stay free of raw queries and data-wrangling.

ABCs:
    ChannelValueLoader      – load ``{channel: scalar}``  (→ LookupMetric)
    ResponseMatrixLoader    – load ``{channel: {stim_id: response}}``
                               (→ StimVectorCorrelation input)

Shared loaders:
    ClusterChannelLoader          – cluster channel set for a session
    ChannelResponseVectorLoader   – pre-computed GA response vectors
    IsochromaticPreferenceLoader  – per-frequency isochromatic preference index
    SolidPreferenceLoader         – solid preference index per channel

GA-specific loaders:
    DeltaVariantStimLoader  – stim IDs from IncludedDeltas
    GAResponseLoader        – GA response values from GAStimInfo
    RawSpikeResponseLoader  – response matrix built from RawSpikeResponses
    RWALoader               – RWA pickle → list of Pearson-r StimVectorCorrelation
"""

from __future__ import annotations

import json
import os
import pickle
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Dict, List, Optional, Set

import numpy as np

from clat.util.connection import Connection
from src.analysis.channel_metric_plot import LookupMetric, StimVectorCorrelation


# ---------------------------------------------------------------------------
# ABCs
# ---------------------------------------------------------------------------

class ChannelValueLoader(ABC):
    """Load a ``{channel: scalar}`` dict for use in a LookupMetric."""

    @abstractmethod
    def load(self) -> Dict[str, float]: ...

    def as_metric(self, **kwargs) -> LookupMetric:
        """Wrap the loaded data as a LookupMetric.  Kwargs forwarded to
        ``LookupMetric`` (e.g. ``title=``, ``self_channel=``)."""
        return LookupMetric(self.load(), **kwargs)


class ResponseMatrixLoader(ABC):
    """Load a ``{channel: {stim_id: response}}`` matrix for use in
    ``StimVectorCorrelation``."""

    @abstractmethod
    def load(self) -> Dict[str, Dict[int, float]]: ...


# ---------------------------------------------------------------------------
# Shared loaders
# ---------------------------------------------------------------------------

class ClusterChannelLoader:
    """Load the set of cluster-channel names for a session."""

    def __init__(self, session_id: str, conn: Connection, experiment_type: str = "ga"):
        self._session_id = session_id
        self._conn = conn
        self._experiment_type = experiment_type

    def load(self) -> Set[str]:
        experiment_id = f"{self._session_id}_{self._experiment_type}"
        self._conn.execute(
            """SELECT DISTINCT c.channel
               FROM ClusterInfo c
               JOIN Experiments e ON c.experiment_id = e.experiment_id
               JOIN (
                   SELECT experiment_id, MAX(gen_id) AS max_gen_id
                   FROM ClusterInfo
                   GROUP BY experiment_id
               ) latest
                 ON c.experiment_id = latest.experiment_id
                AND c.gen_id = latest.max_gen_id
               WHERE e.session_id = %s
                 AND e.experiment_id = %s""",
            (self._session_id, experiment_id),
        )
        return {row[0] for row in self._conn.fetch_all()}


class ChannelResponseVectorLoader(ResponseMatrixLoader):
    """Load pre-computed GA response vectors and return a response matrix.

    Reads from ``ChannelResponseVectors`` (JSON-encoded id/response pairs) and
    converts to the standard ``{channel: {stim_id: response}}`` shape.
    """

    def __init__(self, session_id: str, conn: Connection,
                 vector_type: str = 'ga_mean_response'):
        self._session_id = session_id
        self._conn = conn
        self._vector_type = vector_type

    def load(self) -> Dict[str, Dict[int, float]]:
        self._conn.execute(
            """SELECT unit_name, id_vector, response_vector
               FROM ChannelResponseVectors
               WHERE session_id = %s AND vector_type = %s""",
            (self._session_id, self._vector_type),
        )
        matrix: Dict[str, Dict[int, float]] = {}
        for unit_name, id_json, resp_json in self._conn.fetch_all():
            matrix[unit_name] = dict(zip(json.loads(id_json), json.loads(resp_json)))
        return matrix


class IsochromaticPreferenceLoader:
    """Load isochromatic preference indices per frequency.

    After ``load()`` or ``as_metrics()``, the ``frequencies`` attribute holds
    the sorted list of frequencies (needed for x-axis labelling in the caller).
    """

    def __init__(self, session_id: str, conn: Connection):
        self._session_id = session_id
        self._conn = conn
        self.frequencies: List[float] = []

    def load(self) -> Dict[float, Dict[str, float]]:
        """Return ``{frequency: {channel: preference_index}}``."""
        self._conn.execute(
            """SELECT unit_name, frequency, isochromatic_preference_index
               FROM IsochromaticPreferenceIndices
               WHERE session_id = %s AND unit_name NOT LIKE '%%Unit%%'
               ORDER BY frequency, unit_name""",
            (self._session_id,),
        )
        data: Dict[float, Dict[str, float]] = {}
        for unit_name, frequency, index_value in self._conn.fetch_all():
            data.setdefault(frequency, {})[unit_name] = index_value
        self.frequencies = sorted(data)
        return data

    def as_metrics(self) -> List[LookupMetric]:
        """One ``LookupMetric`` per frequency, sorted ascending.  Each metric's
        ``title`` is set to the frequency string (e.g. ``'12.0 Hz'``)."""
        data = self.load()
        return [LookupMetric(data[freq], title=f'{freq} Hz') for freq in self.frequencies]


class PreferredFrequencyLoader(ChannelValueLoader):
    """Load preferred frequency per channel from ``PreferredFrequencies``.

    ``load()`` returns raw ``{channel: preferred_frequency}``.  Use
    ``as_normalized_metric(frequencies)`` to get a ``LookupMetric`` whose
    values are linearly mapped so the highest tested frequency → +1 and the
    lowest → -1 (centred at 0)."""

    def __init__(self, session_id: str, conn: Connection):
        self._session_id = session_id
        self._conn = conn

    def load(self) -> Dict[str, float]:
        self._conn.execute(
            """SELECT unit_name, preferred_frequency
               FROM PreferredFrequencies
               WHERE session_id = %s AND unit_name NOT LIKE '%%Unit%%'
               ORDER BY unit_name""",
            (self._session_id,),
        )
        return {row[0]: row[1] for row in self._conn.fetch_all()}

    def as_normalized_metric(self, frequencies: Optional[List[float]] = None,
                             **kwargs) -> LookupMetric:
        """Map preferred frequencies to [-1, 1] (highest → +1, lowest → -1).

        ``frequencies`` defines the reference range; if not supplied the range
        is taken from the loaded preferred-frequency values themselves."""
        data = self.load()
        if frequencies:
            lo, hi = min(frequencies), max(frequencies)
        else:
            vals = list(data.values())
            lo, hi = (min(vals), max(vals)) if vals else (0.0, 1.0)
        span = hi - lo
        normalized = {
            ch: (2.0 * (freq - lo) / span - 1.0) if span > 0 else 0.0
            for ch, freq in data.items()
        }
        return LookupMetric(normalized, **kwargs)


class OrientationTuningWidthLoader(ChannelValueLoader):
    """Load, per channel, the frequency at which orientation tuning is deepest.

    Reads ``PreferredOrientations`` and, for each channel, selects the frequency
    whose ``max_minus_min`` (max - min response across orientations) is largest.

    ``load()`` returns raw ``{channel: frequency_of_deepest_tuning}``.  Use
    ``as_normalized_metric(frequencies)`` to map values to [-1, 1] so the highest
    spatial frequency → +1 (red) and the lowest → -1 (blue), matching the
    PreferredFrequency colouring.

    Not every session has orientation data; a missing ``PreferredOrientations``
    table (or empty result) yields an empty dict rather than an error."""

    def __init__(self, session_id: str, conn: Connection):
        self._session_id = session_id
        self._conn = conn

    def load(self) -> Dict[str, float]:
        try:
            self._conn.execute(
                """SELECT unit_name, frequency, max_minus_min
                   FROM PreferredOrientations
                   WHERE session_id = %s AND unit_name NOT LIKE '%%Unit%%'
                   ORDER BY unit_name""",
                (self._session_id,),
            )
            rows = self._conn.fetch_all()
        except Exception as exc:  # table may not exist for non-orientation sessions
            print(f"Warning: could not load orientation tuning width: {exc}")
            return {}

        best: Dict[str, tuple] = {}  # channel -> (frequency, max_minus_min)
        for unit_name, frequency, max_minus_min in rows:
            if max_minus_min is None:
                continue
            if unit_name not in best or max_minus_min > best[unit_name][1]:
                best[unit_name] = (frequency, max_minus_min)
        return {ch: freq for ch, (freq, _depth) in best.items()}

    def as_normalized_metric(self, frequencies: Optional[List[float]] = None,
                             **kwargs) -> LookupMetric:
        """Map deepest-tuning frequencies to [-1, 1] (highest → +1, lowest → -1).

        ``frequencies`` defines the reference range; if not supplied the range is
        taken from the loaded values themselves."""
        data = self.load()
        if frequencies:
            lo, hi = min(frequencies), max(frequencies)
        else:
            vals = list(data.values())
            lo, hi = (min(vals), max(vals)) if vals else (0.0, 1.0)
        span = hi - lo
        normalized = {
            ch: (2.0 * (freq - lo) / span - 1.0) if span > 0 else 0.0
            for ch, freq in data.items()
        }
        return LookupMetric(normalized, **kwargs)


class SolidPreferenceLoader(ChannelValueLoader):
    """Load solid preference indices from ``SolidPreferenceIndices``."""

    SIGNIFICANCE_ALPHA = 0.05   # p below this → "significant" → full saturation
    NEAR_SIG_CEILING = 0.5      # max |colour| just above alpha (paleness of near-sig)

    def __init__(self, session_id: str, conn: Connection):
        self._session_id = session_id
        self._conn = conn

    def load(self) -> Dict[str, float]:
        self._conn.execute(
            """SELECT unit_name, solid_preference_index
               FROM SolidPreferenceIndices
               WHERE session_id = %s AND unit_name NOT LIKE '%%Unit%%'
               ORDER BY unit_name""",
            (self._session_id,),
        )
        return {row[0]: row[1] for row in self._conn.fetch_all()}

    def _load_index_and_pvalue(self):
        """Yield ``(unit_name, solid_preference_index, p_value)`` rows.

        Returns an empty list if the ``p_value`` column does not exist yet
        (permutation test never run for this DB)."""
        try:
            self._conn.execute(
                """SELECT unit_name, solid_preference_index, p_value
                   FROM SolidPreferenceIndices
                   WHERE session_id = %s AND unit_name NOT LIKE '%%Unit%%'
                   ORDER BY unit_name""",
                (self._session_id,),
            )
        except Exception as exc:  # p_value column missing or query failed
            print(f"Warning: could not load solid preference significance: {exc}")
            return []
        return self._conn.fetch_all()

    def load_significance(self) -> Dict[str, float]:
        """Return ``{channel: significance_category}`` for the solid preference.

        The category combines the permutation-test ``p_value`` with the sign of
        the solid preference index:

            ``1``   significant 3D preference  (p < alpha and index > 0)
            ``-1``  significant 2D preference  (p < alpha and index <= 0)
            ``0``   not significant            (p >= alpha)

        Channels with no ``p_value`` (test not run) are omitted so they render
        as gray "no data" markers.
        """
        result: Dict[str, float] = {}
        for unit_name, index_value, p_value in self._load_index_and_pvalue():
            if p_value is None:
                continue  # test not run for this channel → "no data"
            if p_value < self.SIGNIFICANCE_ALPHA:
                result[unit_name] = 1.0 if (index_value is not None and index_value > 0) else -1.0
            else:
                result[unit_name] = 0.0
        return result

    def load_significance_strength(self) -> Dict[str, float]:
        """Return ``{channel: signed significance strength}`` in ``[-1, 1]`` for
        colouring, where the *magnitude* scales with the p-value:

            ``|strength| = 1``                              when p < alpha
            ``|strength| = ceiling * (1 - p)/(1 - alpha)``  when p >= alpha

        The sign encodes direction (``+`` = 3D / index > 0, ``-`` = 2D).  So a
        significant channel is drawn at full saturation, a *near*-significant
        channel (p just above alpha) is pale, and a clearly non-significant
        channel (large p) fades toward white.  Channels with no ``p_value`` are
        omitted so they render as gray "no data" markers.
        """
        result: Dict[str, float] = {}
        for unit_name, index_value, p_value in self._load_index_and_pvalue():
            if p_value is None:
                continue  # test not run for this channel → "no data"
            sign = 1.0 if (index_value is not None and index_value > 0) else -1.0
            if p_value < self.SIGNIFICANCE_ALPHA:
                magnitude = 1.0
            else:
                magnitude = self.NEAR_SIG_CEILING * (1.0 - p_value) / (1.0 - self.SIGNIFICANCE_ALPHA)
                magnitude = max(0.0, magnitude)
            result[unit_name] = sign * magnitude
        return result

    def as_significance_metric(self, **kwargs) -> LookupMetric:
        """Wrap ``load_significance_strength()`` as a LookupMetric whose colour
        magnitude scales with the p-value (full at p < alpha, pale near it)."""
        return LookupMetric(self.load_significance_strength(), **kwargs)


# ---------------------------------------------------------------------------
# GA-specific loaders
# ---------------------------------------------------------------------------

class DeltaVariantStimLoader:
    """Load stim IDs (both delta and variant sides) from ``IncludedDeltas``."""

    def __init__(self, ga_conn: Connection, included_only: bool = True):
        self._conn = ga_conn
        self._included_only = included_only

    def load(self) -> Set[int]:
        if self._included_only:
            self._conn.execute(
                "SELECT delta_id, variant_id FROM IncludedDeltas WHERE included = TRUE"
            )
        else:
            self._conn.execute("SELECT delta_id, variant_id FROM IncludedDeltas")
        stim_ids: Set[int] = set()
        for delta_id, variant_id in self._conn.fetch_all():
            stim_ids.add(int(delta_id))
            stim_ids.add(int(variant_id))
        print(f"Found {len(stim_ids)} unique stim_ids in IncludedDeltas "
              f"({'included only' if self._included_only else 'all pairs'})")
        return stim_ids


class GAResponseLoader:
    """Load GA response values from ``GAStimInfo`` for a session."""

    def __init__(self, session_id: str, repo_conn: Connection):
        self._session_id = session_id
        self._conn = repo_conn

    def load(self) -> Dict[int, float]:
        experiment_id = f"{self._session_id}_ga"
        self._conn.execute(
            """SELECT g.stim_id, g.ga_response
               FROM GAStimInfo g
               JOIN StimExperimentMapping s ON g.stim_id = s.stim_id
               WHERE s.experiment_id = %s AND g.ga_response IS NOT NULL""",
            (experiment_id,),
        )
        responses = {int(r[0]): float(r[1]) for r in self._conn.fetch_all()}
        print(f"Loaded GA Response for {len(responses)} stim_ids")
        return responses


class RawSpikeResponseLoader(ResponseMatrixLoader):
    """Build a response matrix from ``RawSpikeResponses`` for a set of stim IDs.

    Spike rates are averaged across repeated trials of the same stimulus.
    """

    def __init__(self, repo_conn: Connection, stim_ids: Set[int]):
        self._conn = repo_conn
        self._stim_ids = stim_ids

    def load(self) -> Dict[str, Dict[int, float]]:
        if not self._stim_ids:
            return {}

        ph = ', '.join(['%s'] * len(self._stim_ids))
        self._conn.execute(
            f"SELECT task_id, stim_id FROM TaskStimMapping WHERE stim_id IN ({ph})",
            list(self._stim_ids),
        )
        task_stim_pairs = self._conn.fetch_all()
        if not task_stim_pairs:
            print("Warning: no TaskStimMapping entries found for these stim_ids")
            return {}

        task_ids = [r[0] for r in task_stim_pairs]
        task_to_stim = {r[0]: int(r[1]) for r in task_stim_pairs}

        ph = ', '.join(['%s'] * len(task_ids))
        self._conn.execute(
            f"SELECT task_id, channel_id, response_rate "
            f"FROM RawSpikeResponses WHERE task_id IN ({ph})",
            task_ids,
        )

        raw: Dict[str, Dict[int, list]] = defaultdict(lambda: defaultdict(list))
        for task_id, channel_id, rate in self._conn.fetch_all():
            raw[channel_id][task_to_stim[task_id]].append(float(rate))

        matrix = {
            ch: {sid: float(np.mean(rates)) for sid, rates in stim_dict.items()}
            for ch, stim_dict in raw.items()
        }
        print(f"Built response matrix for {len(matrix)} channels "
              f"over up to {len(self._stim_ids)} stimuli")
        return matrix


class RWALoader:
    """Load RWA pickle files and produce Pearson-r ``StimVectorCorrelation`` metrics.

    Call ``as_metrics(response_matrix)`` to get the three column metrics
    (Shaft / Termination / Junction).  Returns ``None`` if any pickle file is
    missing.
    """

    def __init__(self, experiment_id, compiled_data, rwa_output_dir: str):
        self._experiment_id = experiment_id
        self._compiled_data = compiled_data
        self._rwa_dir = rwa_output_dir
        self.pred_map: Optional[Dict[int, tuple]] = None  # set by as_metrics()

    def _load_pkl(self, name: str):
        path = os.path.join(self._rwa_dir, f"{self._experiment_id}_{name}.pkl")
        with open(path, "rb") as fh:
            return pickle.load(fh)

    def _build_pred_map(self, shaft_rwa, term_rwa, junc_rwa) -> Dict[int, tuple]:
        from src.analysis.ga.rwa_prediction import compute_predictions
        data = self._compiled_data
        stim_ids = list(data["StimSpecId"].astype(int))
        shaft_p = compute_predictions(shaft_rwa, data["Shaft"])
        term_p  = compute_predictions(term_rwa,  data["Termination"])
        junc_p  = compute_predictions(junc_rwa,  data["Junction"])
        return {sid: (shaft_p[i], term_p[i], junc_p[i]) for i, sid in enumerate(stim_ids)}

    def as_metrics(
            self, response_matrix: Dict[str, Dict[int, float]]
    ) -> Optional[List[StimVectorCorrelation]]:
        """Return three Pearson-r metrics, or ``None`` if RWA files not found."""
        try:
            shaft_rwa = self._load_pkl("shaft_rwa")
            term_rwa  = self._load_pkl("termination_rwa")
            junc_rwa  = self._load_pkl("junction_rwa")
        except FileNotFoundError as exc:
            print(f"RWA matrices not found — skipping RWA columns: {exc}")
            return None

        pred_map = self._build_pred_map(shaft_rwa, term_rwa, junc_rwa)
        self.pred_map = pred_map
        metrics = []
        for slot, label in [(0, "Shaft"), (1, "Termination"), (2, "Junction")]:
            target = {sid: triple[slot] for sid, triple in pred_map.items()}
            metrics.append(StimVectorCorrelation(
                response_matrix, target,
                method='pearson',
                title=f"{label} RWA\nr (Pearson)",
            ))
        return metrics


class AxisCodingPredictionLoader:
    """Load preferred-axis ridge predictions from ``axis_coding_*.json`` files
    and produce Pearson-r ``StimVectorCorrelation`` metrics, one per component
    type (Shaft / Termination / Junction).

    Same shape as ``RWALoader`` so the two are interchangeable downstream:
    ``as_metrics(response_matrix)`` returns a 3-element list or ``None`` if
    any required JSON is missing, and ``pred_map`` is populated for use by
    per-channel scatter subfolders.

    The "prediction" used here is the model's ``predicted_responses`` per
    stim — already saved in the JSON by ``fit_axis_coding`` — which is the
    ridge fit ``X @ w + intercept`` of the preferred-axis model. Correlation
    is affine-invariant, so projection-vs-prediction is equivalent for the
    Pearson r; ``predicted_responses`` is chosen for parity with the RWA
    convention of "predicted response value."
    """

    DEFAULT_COMPONENT_TYPES: tuple = ("Shaft", "Termination", "Junction")

    def __init__(
        self,
        save_dir: str,
        *,
        strategy: str = "multi_prototype_pca",
        channel_pattern: str = "*",
        component_types: tuple = DEFAULT_COMPONENT_TYPES,
    ):
        self._save_dir = save_dir
        self._strategy = strategy
        self._channel_pattern = channel_pattern
        self._component_types = tuple(component_types)
        self.pred_map: Optional[Dict[int, tuple]] = None  # set by as_metrics()

    # ------------------------------------------------------------------ JSON lookup

    def _find_json(self, component_type: str) -> Optional[str]:
        import glob as _glob
        pattern = os.path.join(
            self._save_dir,
            f"axis_coding_{self._channel_pattern}_{component_type}_{self._strategy}.json",
        )
        matches = sorted(_glob.glob(pattern))
        if not matches:
            return None
        if len(matches) > 1:
            print(
                f"  [axis_loader] multiple JSONs match {component_type}/"
                f"{self._strategy}; using first: {os.path.basename(matches[0])}"
            )
        return matches[0]

    def _load_pred_for_ctype(self, component_type: str) -> Optional[Dict[int, float]]:
        path = self._find_json(component_type)
        if path is None:
            print(
                f"  [axis_loader] no JSON for {component_type}/{self._strategy} "
                f"in {self._save_dir}"
            )
            return None
        with open(path, "r") as f:
            result = json.load(f)
        stim_ids = result.get("stim_ids") or []
        preds = result.get("predicted_responses")
        if not stim_ids or preds is None or len(preds) != len(stim_ids):
            print(
                f"  [axis_loader] {os.path.basename(path)}: stim_ids / "
                f"predicted_responses missing or mismatched"
            )
            return None
        out: Dict[int, float] = {}
        for sid, pred in zip(stim_ids, preds):
            try:
                sid_key = int(sid)
            except (TypeError, ValueError):
                sid_key = sid
            try:
                out[sid_key] = float(pred)
            except (TypeError, ValueError):
                continue
        return out

    # ------------------------------------------------------------------ public API

    def _build_pred_map(self) -> Optional[Dict[int, tuple]]:
        """Return ``{stim_id: (shaft_pred, term_pred, junc_pred)}`` aligned
        across the three component_types. Returns ``None`` if any ctype's
        JSON can't be loaded."""
        per_ctype: Dict[str, Dict[int, float]] = {}
        for ctype in self._component_types:
            m = self._load_pred_for_ctype(ctype)
            if m is None:
                return None
            per_ctype[ctype] = m
        all_sids = sorted(set().union(*(set(m) for m in per_ctype.values())))
        return {
            sid: tuple(
                per_ctype[ctype].get(sid, float("nan"))
                for ctype in self._component_types
            )
            for sid in all_sids
        }

    def as_metrics(
        self, response_matrix: Dict[str, Dict[int, float]]
    ) -> Optional[List["StimVectorCorrelation"]]:
        from src.analysis.channel_metric_plot import StimVectorCorrelation
        pred_map = self._build_pred_map()
        if pred_map is None:
            return None
        self.pred_map = pred_map
        metrics = []
        for slot, label in enumerate(self._component_types):
            target = {sid: triple[slot] for sid, triple in pred_map.items()}
            metrics.append(StimVectorCorrelation(
                response_matrix, target,
                method='pearson',
                title=f"{label} Axis\nr (Pearson)",
            ))
        return metrics
