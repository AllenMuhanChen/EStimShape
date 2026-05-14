from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Union

import pandas as pd

from src.pga.response_processing import RankBaselineNormalizer
from src.startup import context

ChannelSpec = Union[str, list]


@dataclass
class PreparedResponses:
    """Result of applying a `ResponseSpec` to GA-style compiled data.

    Attributes:
        data: Copy of compiled_data filtered to rows with a usable response and
            with a populated `Spike Rate` column.
        response_col: Column name holding the per-trial response value. Always
            ``'Spike Rate'``; provided as a field so callers don't hardcode it.
        response_key: Channel name or list of channels for visualization
            modules that index by key. ``None`` for GA.
        channel: Resolved channel spec ("Cluster" expanded to the channel list).
        channel_label: Human-readable label suitable for filenames / titles.
        baseline_suffix: Filename suffix reflecting whether baseline correction
            was applied (empty string if not). Concatenate after `channel_label`.
    """
    data: pd.DataFrame
    response_col: str
    response_key: Optional[ChannelSpec]
    channel: ChannelSpec
    channel_label: str
    baseline_suffix: str = ""


class ResponseSpec:
    """Per-trial response extraction for GA-style compiled data.

    Encapsulates the (channel, baseline-correction) preprocessing that
    `PlotTopNAnalysis` subclasses each re-implement: resolving ``"Cluster"`` to
    the current cluster channel list, summing across channels, or pulling a
    single channel; or using the precomputed ``'GA Response'`` column.

    Always produces a scalar ``'Spike Rate'`` column on the returned DataFrame
    so downstream code (ranking, visualization, baseline correction) can work
    uniformly regardless of source.

    Baseline correction (rank-based; see
    `src.pga.response_processing.RankBaselineNormalizer`) is silently a no-op
    when using ``'GA Response'``, since that column already reflects whatever
    baseline policy the response processor used to generate it.
    """

    GA = "GA"
    CLUSTER = "Cluster"
    GA_RESPONSE_COL = "GA Response"
    SPIKE_RATE_COL = "Spike Rate"

    def __init__(self, channel: ChannelSpec, *, use_baseline_correction: bool = False):
        self.channel = channel
        self.use_baseline_correction = use_baseline_correction

    @property
    def use_ga_response(self) -> bool:
        return isinstance(self.channel, str) and self.channel == self.GA

    @property
    def baseline_suffix(self) -> str:
        """Filename suffix for the active correction state."""
        return "_baseline_corrected" if (self.use_baseline_correction and not self.use_ga_response) else ""

    def apply(self, compiled_data: pd.DataFrame, *, spike_rates_col: Optional[str]) -> PreparedResponses:
        """Build a 'Spike Rate' column on a copy of `compiled_data`.

        Args:
            compiled_data: Trial-level data with at minimum ``'GA Response'``
                (for GA mode) or `spike_rates_col` (for channel modes).
            spike_rates_col: Column in compiled_data holding the per-channel
                spike rate dict for each trial. Required for non-GA modes.
        """
        if self.use_ga_response:
            return self._apply_ga(compiled_data)
        return self._apply_channel(compiled_data, spike_rates_col)

    def _apply_ga(self, compiled_data: pd.DataFrame) -> PreparedResponses:
        if self.GA_RESPONSE_COL not in compiled_data.columns:
            raise ValueError(
                f"'{self.GA_RESPONSE_COL}' column not found in compiled data; "
                f"available: {compiled_data.columns.tolist()}"
            )
        data = compiled_data[compiled_data[self.GA_RESPONSE_COL].notna()].copy()
        data[self.SPIKE_RATE_COL] = data[self.GA_RESPONSE_COL]
        print("Using GA Response (not channel-specific)")
        return PreparedResponses(
            data=data,
            response_col=self.SPIKE_RATE_COL,
            response_key=None,
            channel=self.GA,
            channel_label=self.GA,
            baseline_suffix=self.baseline_suffix,
        )

    def _apply_channel(self, compiled_data: pd.DataFrame,
                       spike_rates_col: Optional[str]) -> PreparedResponses:
        if spike_rates_col is None:
            raise ValueError("spike_rates_col is required for non-GA channel modes")

        channel, channel_label = self._resolve_channel()

        data = compiled_data[compiled_data[spike_rates_col].notna()].copy()
        if isinstance(channel, list):
            channels = channel

            def extract(x):
                if not isinstance(x, dict):
                    return 0
                return sum(x.get(ch, 0) for ch in channels)

            data[self.SPIKE_RATE_COL] = data[spike_rates_col].apply(extract)
            print(f"Using channel-specific spike rates summed across {len(channels)} channels: {channels}")
        else:
            single = channel
            data[self.SPIKE_RATE_COL] = data[spike_rates_col].apply(
                lambda x: x[single] if isinstance(x, dict) and single in x else 0
            )
            print(f"Using channel-specific spike rates for {single}")

        if self.use_baseline_correction:
            data = self._apply_baseline_correction(data)

        return PreparedResponses(
            data=data,
            response_col=self.SPIKE_RATE_COL,
            response_key=channel,
            channel=channel,
            channel_label=channel_label,
            baseline_suffix=self.baseline_suffix,
        )

    def _resolve_channel(self) -> tuple[ChannelSpec, str]:
        channel = self.channel
        if isinstance(channel, str) and channel == self.CLUSTER:
            try:
                cluster = context.ga_config.db_util.read_current_cluster(context.ga_name)
            except Exception as exc:
                raise RuntimeError(
                    f"channel='Cluster' requires a defined cluster in the GA db: {exc}"
                ) from exc
            channels = [ch.value for ch in cluster]
            print(f"channel='Cluster' resolved to {len(channels)} channels: {channels}")
            return channels, self.CLUSTER
        if isinstance(channel, list):
            return channel, f"{len(channel)}_channels"
        return channel, channel

    def _apply_baseline_correction(self, data: pd.DataFrame) -> pd.DataFrame:
        """Multiply each trial's 'Spike Rate' by its stim's rank-based factor.

        Per-stim factor is computed from the stim's mean spike rate across
        trials, then applied uniformly to every trial of that stim. Baseline /
        catch / regime-zero stims pass through unchanged.
        """
        required = {'StimSpecId', 'StimType', 'GenId', 'ParentId', self.SPIKE_RATE_COL}
        missing = required - set(data.columns)
        if missing:
            print(f"Baseline correction skipped: missing columns {sorted(missing)}")
            return data

        mean_response_per_stim = (
            data.groupby('StimSpecId')[self.SPIKE_RATE_COL].mean().to_dict()
        )
        info = data.drop_duplicates('StimSpecId').set_index('StimSpecId')
        stim_types = info['StimType'].to_dict()
        gen_ids = info['GenId'].to_dict()
        parent_ids = info['ParentId'].to_dict()

        normalizer = RankBaselineNormalizer()
        normalized = normalizer.normalize(
            mean_response_per_stim, stim_types, gen_ids, parent_ids, strict=False,
        )

        factors: dict = {}
        for sid, raw in mean_response_per_stim.items():
            corrected = normalized.get(sid, raw)
            factors[sid] = (corrected / raw) if raw else 1.0

        n_corrected = sum(1 for f in factors.values() if f != 1.0)
        print(f"Baseline correction: applied non-trivial factor to {n_corrected}/{len(factors)} stims")

        data = data.copy()
        data[self.SPIKE_RATE_COL] = (
            data[self.SPIKE_RATE_COL]
            * data['StimSpecId'].map(factors).fillna(1.0)
        )
        return data
