from clat.intan.channels import Channel
from clat.util.connection import Connection
from src.cluster.cluster_app import ClusterApplicationWindow
from src.cluster.dimensionality_reduction import KernelPCAReducer, PCAReducer, MDSReducer, SparsePCAReducer
from src.cluster.mock_cluster_app import get_qapplication_instance
from src.cluster.probe_mapping import DBCChannelMapper
from src.pga.app.run_cluster_app import DbDataLoader
from src.pga.multi_ga_db_util import MultiGaDbUtil
from src.repository.export_to_repository import read_session_id_from_db_name
from src.startup import context


class DbRepoDataExporter:
    def __init__(self, multi_ga_db_util: MultiGaDbUtil):
        self.db_util = multi_ga_db_util

    def export_channels_for_clusters(self, channels_for_clusters: dict[int, list[Channel]]):
        cluster_to_export = 1
        channels_to_export = channels_for_clusters[cluster_to_export]
        print(f"Exporting channels for cluster {cluster_to_export}: {channels_to_export}")

        session_id, _ = read_session_id_from_db_name(context.ga_database)

        # Connect to the repository database
        conn = Connection("allen_data_repository")

        # Create the GoodChannels table if it doesn't exist
        self._ensure_good_channels_table_exists(conn)

        # Clear existing data for this session
        self._clear_session_good_channels(conn, session_id)

        # Insert the new good channels
        self._insert_good_channels(conn, session_id, channels_to_export)

        print(f"Successfully exported {len(channels_to_export)} good channels for session {session_id}")

    def _ensure_good_channels_table_exists(self, conn: Connection):
        """Create the GoodChannels table if it doesn't exist."""
        create_table_sql = """
                           CREATE TABLE IF NOT EXISTS GoodChannels \
                           ( \
                               session_id VARCHAR(10)  NOT NULL, \
                               channel    VARCHAR(255) NOT NULL, \
                               PRIMARY KEY (session_id, channel), \
                               CONSTRAINT GoodChannels_ibfk_1 \
                                   FOREIGN KEY (session_id) REFERENCES Sessions (session_id) \
                                       ON DELETE CASCADE
                           ) CHARSET = latin1;
                           """
        conn.execute(create_table_sql)
        print("Ensured GoodChannels table exists")

    def _clear_session_good_channels(self, conn: Connection, session_id: str):
        """Delete all existing good channels for this session."""
        delete_sql = "DELETE FROM GoodChannels WHERE session_id = %s"
        conn.execute(delete_sql, (session_id,))
        print(f"Cleared existing good channels data for session {session_id}")

    def _insert_good_channels(self, conn: Connection, session_id: str, channels: list[Channel]):
        """Insert the good channels for this session."""
        insert_sql = """
                     INSERT INTO GoodChannels (session_id, channel)
                     VALUES (%s, %s)
                     """

        for channel in channels:
            channel_name = channel.value  # Convert Channel enum to string
            conn.execute(insert_sql, (session_id, channel_name))
            print(f"Inserted good channel: {session_id} -> {channel_name}")


def main():
    app = get_qapplication_instance()
    window = ClusterApplicationWindow(DbDataLoader(context.ga_config.connection()),
                                      DbRepoDataExporter(context.ga_config.db_util),
                                      [KernelPCAReducer(),
                                       PCAReducer(),
                                       MDSReducer(),
                                       SparsePCAReducer()],
                                      DBCChannelMapper("A"))
    window.show()
    app.exec_()


if __name__ == '__main__':
    main()