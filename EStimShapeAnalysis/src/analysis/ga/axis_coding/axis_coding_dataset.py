from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Optional, Union

import numpy as np
import pandas as pd

from src.analysis.ga.axis_coding.component_encoding import ComponentEncoder


@dataclass
class AxisCodingDataset:
    """
    Builds (components_per_stim, responses, stim_ids, feature_names) for one
    channel and one component type. Encoder scaler is fit on all components from
    all stimuli so distances live on a comparable scale across the dataset.
    """

    components_per_stim: list[np.ndarray]
    responses: np.ndarray
    stim_ids: np.ndarray
    feature_names: list[str]
    encoder: ComponentEncoder
    n_dropped_no_components: int = 0
    n_dropped_no_response: int = 0

    @property
    def n_stim(self) -> int:
        return len(self.components_per_stim)

    @property
    def n_features(self) -> int:
        return len(self.feature_names)

    @classmethod
    def build(
        cls,
        df: pd.DataFrame,
        component_type: str,
        encoder: ComponentEncoder,
        channel: Union[str, list[str]],
        spike_rates_col: Optional[str],
    ) -> "AxisCodingDataset":
        """
        Parameters
        ----------
        df
            Cleaned, conditioned dataframe (post `condition_spherical_angles` /
            `hemisphericalize_orientation`). Must contain `StimSpecId`, the
            ``component_type`` column (list[dict] or stringified list[dict]),
            and either ``spike_rates_col`` or ``GA Response``.
        component_type
            "Shaft" | "Termination" | "Junction".
        encoder
            ComponentEncoder for this type. The scaler will be fit here.
        channel
            "GA" -> use the ``GA Response`` column.
            str  -> intan channel; extract from ``spike_rates_col`` dict.
            list -> sum responses across listed channels.
        spike_rates_col
            Name of the per-trial spike-rate column (None if channel == "GA").
        """
        df = df.copy()
        df = df[df["StimSpecId"].notna()]

        if component_type not in df.columns:
            raise KeyError(
                f"Column '{component_type}' not in dataframe. "
                f"Columns: {list(df.columns)}"
            )

        df[component_type] = df[component_type].apply(_coerce_to_list_of_dicts)

        # Per-trial response extraction (mirrors plot_top_n.add_lineage_rank_to_df).
        df["_axis_resp"] = _extract_per_trial_response(df, channel, spike_rates_col)

        # Drop trials with no response.
        before = len(df)
        df = df[df["_axis_resp"].notna()]
        n_dropped_no_response = before - len(df)

        # Mean response per StimSpecId across trials.
        per_stim_response = df.groupby("StimSpecId")["_axis_resp"].mean()

        # First-occurrence component list per stim (components are stim-spec, not trial).
        per_stim_components = (
            df.groupby("StimSpecId")[component_type].first()
        )

        # Drop stimuli with no components for this type.
        n_dropped_no_components = 0
        kept_stim_ids: list = []
        kept_components: list[list[dict]] = []
        kept_responses: list[float] = []
        for stim_id, comps in per_stim_components.items():
            if comps is None or (isinstance(comps, list) and len(comps) == 0):
                n_dropped_no_components += 1
                continue
            kept_stim_ids.append(stim_id)
            kept_components.append(comps)
            kept_responses.append(float(per_stim_response[stim_id]))

        # Encode (un-scaled) so we can fit the scaler on the union.
        encoded_per_stim = [encoder.encode_components(c) for c in kept_components]

        valid = [(e, r, s) for e, r, s in
                 zip(encoded_per_stim, kept_responses, kept_stim_ids)
                 if e.shape[0] > 0]
        if not valid:
            raise RuntimeError(
                f"No valid stimuli with components for type {component_type}."
            )

        encoded_per_stim, kept_responses, kept_stim_ids = map(list, zip(*valid))
        all_components = np.vstack(encoded_per_stim)
        encoder.fit_scaler(all_components)
        scaled_per_stim = [encoder.transform_with_scaler(e) for e in encoded_per_stim]

        return cls(
            components_per_stim=scaled_per_stim,
            responses=np.asarray(kept_responses, dtype=np.float64),
            stim_ids=np.asarray(kept_stim_ids),
            feature_names=list(encoder.feature_names),
            encoder=encoder,
            n_dropped_no_components=n_dropped_no_components,
            n_dropped_no_response=n_dropped_no_response,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _coerce_to_list_of_dicts(value):
    """
    Components round-tripped through the repository come back as the string repr
    of a list/dict of dicts (export_to_repository falls back to ``str(value)``
    for complex types -- comment at export_to_repository.py:474). Parse those
    back via ast.literal_eval. A single-component stimulus comes back as a bare
    dict (see matchstick_fields.py:53-60); wrap it into a one-element list so
    downstream code can iterate uniformly.
    """
    if value is None:
        return None
    if isinstance(value, str):
        try:
            value = ast.literal_eval(value)
        except (SyntaxError, ValueError):
            return None
    if isinstance(value, dict):
        return [value]
    if isinstance(value, list):
        return value
    return value


def remove_trial_outliers(
    df: pd.DataFrame,
    channel: Union[str, list[str]],
    spike_rates_col: Optional[str],
    n_sigma: float = 3.0,
    min_trials: int = 3,
) -> pd.DataFrame:
    """
    Drop outlier trials within each stimulus before averaging.

    For each stimulus with >= ``min_trials`` repetitions, any trial whose
    response deviates more than ``n_sigma`` standard deviations from the
    within-stimulus mean is removed.  Stimuli with fewer than ``min_trials``
    repetitions are left untouched (not enough data to reliably call an
    outlier).

    Returns a new dataframe with outlier rows removed and a console note
    reporting the number of trials dropped.
    """
    df = df.copy()
    df["_or_resp"] = _extract_per_trial_response(df, channel, spike_rates_col)

    n_before = len(df)
    drop_mask = pd.Series(False, index=df.index)

    for _, grp in df.groupby("StimSpecId"):
        resp = grp["_or_resp"].dropna()
        if len(resp) < min_trials:
            continue
        std = resp.std(ddof=1)
        if std < 1e-12:
            continue
        mean = resp.mean()
        outlier_idx = resp.index[np.abs(resp - mean) > n_sigma * std]
        drop_mask.loc[outlier_idx] = True

    df = df[~drop_mask].drop(columns=["_or_resp"])
    n_dropped = n_before - len(df)
    if n_dropped > 0:
        print(
            f"  [outlier_removal] removed {n_dropped} trials "
            f"({n_dropped / n_before:.1%} of {n_before}) "
            f"threshold={n_sigma}σ  min_trials={min_trials}"
        )
    return df


def _extract_per_trial_response(
    df: pd.DataFrame,
    channel: Union[str, list[str]],
    spike_rates_col: Optional[str],
) -> pd.Series:
    """Mirror plot_top_n.add_lineage_rank_to_df:181 channel-selection convention."""
    if channel == "GA":
        if "GA Response" not in df.columns:
            raise KeyError(
                "channel='GA' requires a 'GA Response' column. "
                f"Columns: {list(df.columns)}"
            )
        return pd.to_numeric(df["GA Response"], errors="coerce")

    if spike_rates_col is None:
        raise ValueError(
            "spike_rates_col must be set when channel is not 'GA'."
        )
    if spike_rates_col not in df.columns:
        raise KeyError(
            f"Spike rates column '{spike_rates_col}' not in dataframe. "
            f"Columns: {list(df.columns)}"
        )

    rates_dicts = df[spike_rates_col]

    if isinstance(channel, list):
        def _sum_channels(d):
            if not isinstance(d, dict):
                return np.nan
            total = 0.0
            seen_any = False
            for ch in channel:
                if ch in d and d[ch] is not None:
                    total += float(d[ch])
                    seen_any = True
            return total if seen_any else np.nan
        return rates_dicts.apply(_sum_channels)

    # Single intan channel as a string.
    def _pick(d):
        if not isinstance(d, dict):
            return np.nan
        v = d.get(channel)
        return np.nan if v is None else float(v)
    return rates_dicts.apply(_pick)
