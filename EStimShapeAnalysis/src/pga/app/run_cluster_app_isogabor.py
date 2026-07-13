"""
Isogabor variant of the channel-clustering app.

This is the same clustering GUI wired up by ``run_cluster_app.py``, but
instead of reading per-channel responses from the GA experiment
(``ChannelResponses`` in the GA database) it reads them from the *isogabor*
experiment. It reuses the existing config dependency-injection system:
the session is taken from ``context.isogabor_database``, and the
``ClusterApplicationWindow`` receives its data source by constructor
injection — only the injected ``DataLoader`` changes.

Each channel's feature vector is its mean spike rate to every isogabor
stimulus (one entry per stim id, ordered by stim id), exactly mirroring how
``DbDataLoader`` builds one value per GA stim. Channels are then clustered by
how similarly they respond across the isogabor stimulus set.
"""

import numpy as np
import pandas as pd

from src.cluster.cluster_app import ClusterApplicationWindow
from src.cluster.cluster_app_classes import DataLoader, DataExporter
from src.cluster.dimensionality_reduction import PCAReducer, MDSReducer, KernelPCAReducer, SparsePCAReducer
from src.cluster.mock_cluster_app import get_qapplication_instance
from src.cluster.probe_mapping import DBCChannelMapper
from src.pga.app.run_cluster_app import channels_for_prefix
from src.repository.export_to_repository import read_session_id_and_date_from_db_name
from src.repository.import_from_repository import import_from_repository
from src.startup import context


class IsogaborDataLoader(DataLoader):
    """
    Loads per-channel response profiles from an isogabor experiment.

    Counterpart to ``DbDataLoader``: that one queries the GA experiment's
    ``ChannelResponses`` table, this one imports the isogabor session's
    compiled responses from the data repository and reshapes them into the
    same ``dict[Channel, np.ndarray]`` the clustering app expects. For each
    channel we average its spike rate across the repeats of each stimulus and
    order the resulting vector by stim id — one feature per stimulus.

    Isogabor experiments have no generation structure, so ``max_gen`` is
    accepted for protocol compatibility but ignored.
    """

    def __init__(self, session_id: str, *, data_type: str = "mua"):
        self.session_id = session_id
        self.mua_method = None
        if data_type == "raw":
            self.response_table = "RawSpikeResponses"
            self.spike_rate_col = "Spike Rate by channel"
        elif data_type == "sorted":
            self.response_table = "WindowSortedResponses"
            self.spike_rate_col = "Spike Rate by unit"
        elif data_type == "mua":
            self.response_table = "MUASpikeResponses"
            self.spike_rate_col = "Spike Rate by channel"
            self.mua_method = "mad_k4_block100"
        else:
            raise ValueError(f"Unknown data type: {data_type}")
        self._compiled_data: pd.DataFrame | None = None

    def _get_data(self) -> pd.DataFrame:
        """Import (and cache) the compiled isogabor responses for this session."""
        if self._compiled_data is None:
            self._compiled_data = import_from_repository(
                self.session_id,
                "isogabor",
                "IsoGaborStimInfo",
                self.response_table,
                mua_method=self.mua_method,
            )
        return self._compiled_data

    def load_data_for_channels(self, max_gen: int | None = None) -> dict:
        data = self._get_data()

        # One feature per stimulus, ordered by stim id — averaging across the
        # repeats (tasks) of each stim, just as the GA loader averages
        # spikes_per_second across task_ids for each stim_id.
        stim_ids = sorted(data["StimSpecId"].unique())

        data_for_channels = {}
        for channel in channels_for_prefix("A"):
            channel_key = channel.value
            rates = []
            has_any_data = False
            for stim_id in stim_ids:
                stim_rows = data[data["StimSpecId"] == stim_id]
                values = []
                for _, row in stim_rows.iterrows():
                    rate_dict = row[self.spike_rate_col]
                    if isinstance(rate_dict, dict) and channel_key in rate_dict:
                        values.append(rate_dict[channel_key])
                if values:
                    has_any_data = True
                    rates.append(float(np.mean(values)))
                else:
                    # Keep every channel's vector the same length so the
                    # clustering app can stack them; missing stims read as 0.
                    rates.append(0.0)
            # Channels with no recorded data at all return an empty array and
            # are filtered out downstream, matching DbDataLoader's behavior.
            data_for_channels[channel] = np.array(rates) if has_any_data else np.array([])
        return data_for_channels

    def get_max_generation(self) -> int:
        # Isogabor experiments are not organized into generations.
        return 1


class IsogaborDataExporter(DataExporter):
    """
    Reports the selected cluster's channels.

    The GA exporter writes cluster membership back to the GA experiment's
    cluster tables; the isogabor experiment has no such tables, so here we
    simply print the channels in cluster 1 for inspection.
    """

    def export_channels_for_clusters(self, channels_for_clusters: dict[int, list]):
        cluster_to_export = 1
        channels = channels_for_clusters.get(cluster_to_export, [])
        print(f"Cluster {cluster_to_export} channels ({len(channels)}): "
              f"{[channel.value for channel in channels]}")


def main():
    session_id, _ = read_session_id_and_date_from_db_name(context.isogabor_database)
    print(f"Loading isogabor session {session_id} from {context.isogabor_database}")

    app = get_qapplication_instance()
    window = ClusterApplicationWindow(
        IsogaborDataLoader(session_id),
        IsogaborDataExporter(),
        [PCAReducer(),
         MDSReducer(),
         KernelPCAReducer(),
         SparsePCAReducer()],
        DBCChannelMapper("A"),
    )

    window.show()
    app.exec_()


if __name__ == '__main__':
    main()
