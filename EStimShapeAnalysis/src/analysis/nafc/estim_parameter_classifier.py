from clat.util.connection import Connection


class EStimParameterClassifier:
    """
    Classifies and parameterizes estim specs from the EStimParameters table.

    Handles two stimulation paradigms:
    - Legacy: single active channel with charge recovery on the stimming channel itself.
    - Ground pulse: multiple channels where non-active channels receive a 0-amplitude
      pulse with charge recovery enabled (the "ground pulse"). Only channels with a1 > 0
      are actively delivering current.

    Currently all active channels share identical parameters. The class is designed
    to be extended when channels may have independent parameters.
    """

    @staticmethod
    def active_channel_sql_subquery() -> str:
        """
        SQL subquery that selects per-estim-spec parameters from the first active channel.

        Active channels are those with a1 > 0.  Ground channels (a1 = 0) are excluded
        from the count and from parameter reading.

        num_channels reflects only the number of active channels.

        Usage: LEFT JOIN (<subquery>) ep ON t.session_id = ep.session_id
                                        AND t.estim_spec_id = ep.estim_spec_id
        """
        return """
            SELECT ep1.*, active_counts.num_channels
            FROM EStimParameters ep1
            INNER JOIN (
                SELECT session_id,
                       estim_spec_id,
                       MIN(channel) AS first_active_channel,
                       COUNT(*)     AS num_channels
                FROM EStimParameters
                WHERE a1 > 0
                GROUP BY session_id, estim_spec_id
            ) active_counts
              ON ep1.session_id = active_counts.session_id
             AND ep1.estim_spec_id = active_counts.estim_spec_id
             AND ep1.channel = active_counts.first_active_channel
        """

    @staticmethod
    def create_estim_location_stats_table():
        """
        Create the EStimLocationStats table keyed by (session_id, channel).

        This table will hold per-stimulation-site statistics for sessions where
        different estim_spec_ids target different electrode locations.
        Population logic to be added when multi-location analysis is implemented.
        """
        conn = Connection("allen_data_repository")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS EStimLocationStats (
                session_id  VARCHAR(10) NOT NULL,
                channel     VARCHAR(4)  NOT NULL,
                PRIMARY KEY (session_id, channel),
                FOREIGN KEY (session_id) REFERENCES Sessions (session_id) ON DELETE CASCADE
            ) ENGINE = InnoDB DEFAULT CHARSET = latin1
        """)
        print("EStimLocationStats table created/verified")
