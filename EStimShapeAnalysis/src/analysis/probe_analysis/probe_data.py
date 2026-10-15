"""
Everything a probe column can need for one session, loaded on first use and cached.

One ProbeData per session. Nothing is loaded until a column asks for it, so turning a
column off never costs a query. Database names and paths are read from ``context`` at
call time (the session must already be applied with apply_session_context).

All per-channel values are keyed by the channel string ("A-007"), the unit_name used
in the repository tables. Read-only: nothing here writes to a database.
"""

from __future__ import annotations

import os
from typing import Callable, Dict, List, Optional, Set

import numpy as np

from src.analysis.channel_metric_plot import build_channel_strings

PROBE_PITCH_UM = 65.0       # DBC probe: 65 µm centre to centre
DEFAULT_PLOTS_ROOT = "/home/connorlab/Documents/plots"


class ProbeData:
    def __init__(self, session_id: str, headstage: str = "A",
                 plots_root: str = DEFAULT_PLOTS_ROOT, axis_coding_dir: str = None):
        self.session_id = session_id
        self.headstage = headstage
        self.plots_root = plots_root
        self._axis_coding_dir = axis_coding_dir
        self._cache: dict = {}

    # ----------------------------------------------------------------- caching
    def _get(self, key, loader: Callable):
        if key not in self._cache:
            self._cache[key] = loader()
        return self._cache[key]

    def repo_conn(self):
        from clat.util.connection import Connection
        return self._get('repo_conn', lambda: Connection("allen_data_repository"))

    def ga_conn(self):
        from clat.util.connection import Connection
        from src.startup import context
        return self._get(('ga_conn', context.ga_database),
                         lambda: Connection(context.ga_database))

    # ------------------------------------------------------------------- probe
    def channel_strs(self) -> List[str]:
        """Probe channels top -> bottom."""
        return build_channel_strings(self.headstage)

    def positions_um(self) -> List[float]:
        """Depth of each channel below the top channel (µm), top -> bottom."""
        return [i * PROBE_PITCH_UM for i in range(len(self.channel_strs()))]

    def ga_channels(self) -> Set[str]:
        from src.analysis.channel_data_loaders import ClusterChannelLoader
        return self._get('ga_channels',
                         lambda: ClusterChannelLoader(self.session_id, self.repo_conn()).load())

    def estim_channels_by_spec(self) -> Dict[int, List[str]]:
        """{estim_spec_id: channels delivering current (a1 > 0)}. Empty if the session
        has no estim."""
        def load():
            from src.cluster.cluster_isolation_score import fetch_active_estim_channels_by_spec
            by_spec = fetch_active_estim_channels_by_spec(self.session_id)
            return {int(s): sorted(c.name.replace('_', '-') for c in chans)
                    for s, chans in by_spec.items() if chans}
        return self._get('estim_by_spec', load)

    # ------------------------------------------------------ tuning (isogabor etc.)
    def isochromatic(self):
        """(frequencies, {frequency: {channel: isochromatic preference index}})."""
        def load():
            from src.analysis.channel_data_loaders import IsochromaticPreferenceLoader
            loader = IsochromaticPreferenceLoader(self.session_id, self.repo_conn())
            data = loader.load()
            return loader.frequencies, data
        return self._get('iso', load)

    def preferred_frequency(self) -> Dict[str, float]:
        from src.analysis.channel_data_loaders import PreferredFrequencyLoader
        return self._get('pref_freq', lambda: PreferredFrequencyLoader(
            self.session_id, self.repo_conn()).load())

    def orientation_tuning_frequency(self) -> Dict[str, float]:
        """Frequency at which each channel's orientation tuning is deepest."""
        from src.analysis.channel_data_loaders import OrientationTuningWidthLoader
        return self._get('orient_freq', lambda: OrientationTuningWidthLoader(
            self.session_id, self.repo_conn()).load())

    def preferred_orientation(self) -> Dict[str, float]:
        from src.analysis.channel_data_loaders import PreferredOrientationLoader
        return self._get('pref_orient', lambda: PreferredOrientationLoader(
            self.session_id, self.repo_conn()).load())

    def preferred_color(self) -> Dict[str, str]:
        from src.analysis.channel_data_loaders import PreferredColorLoader
        return self._get('pref_color', lambda: PreferredColorLoader(
            self.session_id, self.repo_conn()).load())

    def solid_preference(self) -> Dict[str, float]:
        from src.analysis.channel_data_loaders import SolidPreferenceLoader
        return self._get('solid', lambda: SolidPreferenceLoader(
            self.session_id, self.repo_conn()).load())

    def solid_significance_strength(self) -> Dict[str, float]:
        from src.analysis.channel_data_loaders import SolidPreferenceLoader
        return self._get('solid_sig', lambda: SolidPreferenceLoader(
            self.session_id, self.repo_conn()).load_significance_strength())

    # ------------------------------------------------------------ GA responses
    def response_vectors(self, vector_type: str = 'ga_mean_response'):
        """{channel: {stim_id: mean GA response}} from ChannelResponseVectors."""
        from src.analysis.channel_data_loaders import ChannelResponseVectorLoader
        return self._get(('vectors', vector_type), lambda: ChannelResponseVectorLoader(
            self.session_id, self.repo_conn(), vector_type=vector_type).load())

    def ga_responses(self) -> Dict[int, float]:
        """{stim_id: GA response} from GAStimInfo."""
        from src.analysis.channel_data_loaders import GAResponseLoader
        return self._get('ga_responses', lambda: GAResponseLoader(
            self.session_id, self.repo_conn()).load())

    def raw_matrix(self, stim_ids) -> Dict[str, Dict[int, float]]:
        """{channel: {stim_id: mean rate}} from RawSpikeResponses for these stims."""
        from src.analysis.channel_data_loaders import RawSpikeResponseLoader
        key = ('raw_matrix', frozenset(stim_ids))
        return self._get(key, lambda: RawSpikeResponseLoader(
            self.repo_conn(), set(stim_ids)).load())

    def top_n_stim_ids(self, n: int) -> Set[int]:
        ga = self.ga_responses()
        return set(sorted(ga, key=ga.get, reverse=True)[:n])

    # ---------------------------------------------------------- delta / variant
    def delta_variant_stim_ids(self, included_only: bool = True) -> Set[int]:
        from src.analysis.channel_data_loaders import DeltaVariantStimLoader
        return self._get(('dv_ids', included_only), lambda: DeltaVariantStimLoader(
            self.ga_conn(), included_only).load())

    def variant_to_deltas(self, included_only: bool = True):
        def load():
            from src.analysis.nafc.group_analysis.compute_estim_neighbor_scores import \
                fetch_variant_delta_pairs
            return fetch_variant_delta_pairs(self.ga_conn(), included_only)[0]
        return self._get(('v2d', included_only), load)

    # ------------------------------------------------------- model predictions
    def compiled_ga_data(self):
        """Fresh compile of the GA DB (as plot_rwa_scatter), needed by the RWA."""
        def load():
            from src.pga.app.plot_rwa_scatter import compile_data
            return compile_data(self.ga_conn())
        return self._get('compiled_ga', load)

    def all_ga_matrix(self):
        """RawSpikeResponses matrix over every stim in the compiled GA data."""
        ids = set(self.compiled_ga_data()["StimSpecId"].astype(int))
        return self.raw_matrix(ids)

    def rwa_loader(self):
        """RWALoader for the current GA experiment, or None without an experiment."""
        def load():
            from src.analysis.channel_data_loaders import RWALoader
            from src.startup import context
            experiment_id = context.ga_config.db_util.read_current_experiment_id(
                context.ga_name)
            if experiment_id is None:
                return None
            return RWALoader(experiment_id, self.compiled_ga_data(), context.rwa_output_dir)
        return self._get('rwa_loader', load)

    def axis_coding_dir(self) -> str:
        """AxisCodingAnalysis output folder (default <plots_root>/<session>/axis_coding)."""
        return self._axis_coding_dir or os.path.join(self.plots_root, self.session_id,
                                                     "axis_coding")

    def axis_coding_loader(self, strategy: str):
        def load():
            from src.analysis.channel_data_loaders import AxisCodingPredictionLoader
            if not os.path.isdir(self.axis_coding_dir()):
                return None
            return AxisCodingPredictionLoader(save_dir=self.axis_coding_dir(),
                                              strategy=strategy)
        return self._get(('axis_loader', strategy), load)


def parse_channel_list(text: str, ga_channels) -> List[str]:
    """'GA' (or blank) -> the GA channels; 'A-022, A-008' -> those channels."""
    text = (text or "").strip()
    if not text or text.upper() == "GA":
        return sorted(ga_channels)
    return [c.strip() for c in text.replace(";", ",").split(",") if c.strip()]


def parse_estim_spec(text: str, by_spec: Dict[int, List[str]]):
    """EStim spec box -> (channels to mark, label). 'none'/blank -> nothing;
    'all' -> every channel stimulated in the session; '3' or '3,5' -> those specs;
    'A-008, A-022' -> those channels (no estim lookup needed)."""
    text = (text or "").strip().lower()
    if not text or text == "none":
        return [], ""
    if text == "all":
        chans = sorted({c for cs in by_spec.values() for c in cs})
        return chans, "all specs"
    parts = [p.strip() for p in text.replace(";", ",").split(",") if p.strip()]
    if all("-" in p for p in parts):            # channel names, e.g. "A-008, A-022"
        chans = sorted(p.upper() for p in parts)
        return chans, ", ".join(chans)
    ids = []
    for part in parts:
        try:
            ids.append(int(part))
        except ValueError:
            raise ValueError(f"EStim spec '{part}' is not a spec id, a channel like "
                             f"A-008, 'all' or 'none'")
    missing = [i for i in ids if i not in by_spec]
    if missing:
        raise ValueError(f"No estim spec {missing} in this session "
                         f"(specs: {sorted(by_spec) or 'none'})")
    chans = sorted({c for i in ids for c in by_spec[i]})
    return chans, "spec " + ", ".join(str(i) for i in ids)


def finite_values(data: Dict[str, float]) -> list:
    return [v for v in data.values()
            if v is not None and isinstance(v, (int, float)) and np.isfinite(v)]
