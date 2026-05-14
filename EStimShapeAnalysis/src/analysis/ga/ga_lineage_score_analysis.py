from __future__ import annotations

import pandas as pd
from clat.util.connection import Connection
from src.analysis import Analysis
from src.analysis.ga.plot_top_n import PlotTopNAnalysis
from src.analysis.ga.response_spec import ResponseSpec
from src.repository.good_channels import read_cluster_channels
from src.repository.import_from_repository import import_from_repository
from src.startup import context


def main():
    """Example usage"""
    analysis = GALineageScoreAnalysis()
    session_ids = ["260120_0", "260115_0", "260113_0", "260108_0", "260107_0", "251231_0", "251226_0"]

    for session_id in session_ids:
        channels = read_cluster_channels(session_id)
        data_type = "GA" if channels == "GA" else "raw"
        analysis.run(session_id, data_type, channels, compiled_data=None)





class GALineageScoreAnalysis(PlotTopNAnalysis):

    def analyze(self, channel, compiled_data: pd.DataFrame = None):
        """
        Calculate normalized lineage score for a session.

        Args:
            channel: Either a single channel name (str) or list of channel names (List[str]).
                    If list is provided, responses are summed across all specified channels.
            compiled_data: Pre-compiled data (optional)
        """
        if compiled_data is None:
            compiled_data = import_from_repository(
                self.session_id,
                "ga",
                "GAStimInfo",
                self.response_table
            )

        # Calculate the lineage score
        lineage_score = self._calculate_lineage_score(compiled_data, channel)

        # Store in database
        self._store_lineage_score(lineage_score)

        print(f"Session {self.session_id}: Lineage Score = {lineage_score:.4f}")

        return lineage_score

    def _calculate_lineage_score(self, compiled_data: pd.DataFrame, channel) -> float:
        """
        Calculate the lineage score metric:
        - M = max response across entire experiment
        - m_i = max response for lineage i
        - score = sum(m_i / M) across all lineages with more than one stimulus
        """
        spec = ResponseSpec(channel, use_baseline_correction=self.use_baseline_correction)
        try:
            prepared = spec.apply(compiled_data, spike_rates_col=self.spike_rates_col)
        except ValueError as exc:
            print(f"Error: {exc}")
            return 0.0
        compiled_data = prepared.data
        response_col = prepared.response_col

        # Filter out lineages with too few stimuli
        lineage_stim_counts = compiled_data.groupby('Lineage')['StimSpecId'].nunique()
        valid_lineages = lineage_stim_counts[lineage_stim_counts > 10].index
        compiled_data = compiled_data[compiled_data['Lineage'].isin(valid_lineages)]

        if len(compiled_data) == 0:
            print(f"Warning: No lineages with more than one stimulus for session {self.session_id}")
            return 0.0

        M = compiled_data[response_col].max()
        if M == 0:
            print(f"Warning: Maximum response is 0 for session {self.session_id}")
            return 0.0

        lineage_max_responses = compiled_data.groupby('Lineage')[response_col].max()
        lineage_score = (lineage_max_responses / M).sum() / len(valid_lineages)
        return float(lineage_score)

    def _store_lineage_score(self, lineage_score: float):
        """Store the lineage score in the EStimShapeSessionData table"""
        conn = Connection("allen_data_repository")

        # First, ensure the column exists (add if it doesn't)
        self._ensure_column_exists(conn)

        # Insert or update the record
        query = """
                INSERT INTO EStimShapeSessionData (session_id, lineage_score)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE lineage_score = %s \
                """

        conn.execute(query, (self.session_id, lineage_score, lineage_score))

        print(f"Stored lineage_score={lineage_score:.4f} for session_id={self.session_id}")

    def _ensure_column_exists(self, conn: Connection):
        """Add lineage_score column if it doesn't exist"""
        try:
            # Check if column exists
            check_query = """
                          SELECT COUNT(*) as count
                          FROM INFORMATION_SCHEMA.COLUMNS
                          WHERE TABLE_SCHEMA = 'central_data_repository'
                            AND TABLE_NAME = 'EStimShapeSessionData'
                            AND COLUMN_NAME = 'lineage_score' \
                          """
            result = conn.execute(check_query)

            if result[0]['count'] == 0:
                # Column doesn't exist, add it
                alter_query = """
                              ALTER TABLE EStimShapeSessionData
                                  ADD COLUMN lineage_score FLOAT NULL \
                              """
                conn.execute(alter_query)
                conn.commit()
                print("Added lineage_score column to EStimShapeSessionData table")
        except Exception as e:
            print(f"Warning: Could not verify/add column: {e}")


if __name__ == "__main__":
    main()