import json
import numpy as np
import pandas as pd
from clat.pipeline.pipeline_base_classes import ComputationModule, AnalysisModuleFactory, OutputHandler, create_branch, \
    create_pipeline
from clat.util.connection import Connection
from src.analysis.ga.plot_top_n import PlotTopNAnalysis, add_lineage_rank_to_df
from src.repository.export_to_repository import read_session_id_from_db_name
from src.repository.import_from_repository import import_from_repository
from src.startup import context


class GAResponseVectorAnalysis(PlotTopNAnalysis):
    """Analysis to extract mean response vectors per stimulus for GA data."""

    def analyze(self, channel, compiled_data: pd.DataFrame = None):
        if compiled_data is None:
            compiled_data = import_from_repository(
                self.session_id,
                "ga",
                "GAStimInfo",
                self.response_table
            )

        compiled_data = add_lineage_rank_to_df(compiled_data, self.spike_rates_col, channel)

        # Create response vector extraction module
        vector_module = create_ga_response_vector_module(
            channel=channel,
            session_id=self.session_id,
            spike_data_col=self.spike_rates_col
        )
        vector_branch = create_branch().then(vector_module)

        pipeline = create_pipeline().make_branch(vector_branch).build()
        result = pipeline.run(compiled_data)
        return result


class GAResponseVectorExtractor(ComputationModule):
    """
    Extract mean response vector for each stimulus, sorted by stimId.
    Also extracts conditional vectors based on texture type (2D, SHADE, SPECULAR).
    """

    def __init__(self, *, response_key=None, spike_data_col="Spike Rate by channel"):
        self.response_key = response_key
        self.spike_data_col = spike_data_col

    def compute(self, prepared_data):
        """
        Extract mean responses per stimulus, overall and by texture type.

        Returns:
            List of dictionaries, one for each vector_type:
            [
                {'channel': ..., 'vector_type': 'ga_mean_response', 'id_vector': [...], 'response_vector': [...]},
                {'channel': ..., 'vector_type': 'ga_mean_response_2d', 'id_vector': [...], 'response_vector': [...]},
                {'channel': ..., 'vector_type': 'ga_mean_response_shade', 'id_vector': [...], 'response_vector': [...]},
                {'channel': ..., 'vector_type': 'ga_mean_response_specular', 'id_vector': [...], 'response_vector': [...]},
                {'channel': ..., 'vector_type': 'ga_mean_response_3d', 'id_vector': [...], 'response_vector': [...]},
            ]
        """
        # Extract all responses grouped by stimulus (overall)
        all_responses = self._extract_responses_by_stimulus(prepared_data, self.response_key)

        # Extract responses grouped by stimulus and texture type
        texture_responses = self._extract_responses_by_stimulus_and_texture(prepared_data, self.response_key)

        results = []

        # 1. Overall vector (all stimuli)
        if len(all_responses) > 0:
            mean_responses = {stim_id: np.mean(rates) for stim_id, rates in all_responses.items()}
            sorted_stim_ids = sorted(mean_responses.keys())
            id_vector = sorted_stim_ids
            response_vector = [mean_responses[stim_id] for stim_id in sorted_stim_ids]

            results.append({
                'channel': self.response_key,
                'vector_type': 'ga_mean_response',
                'id_vector': id_vector,
                'response_vector': response_vector,
                'n_stimuli': len(id_vector)
            })

            print(f"\nGA Response Vector Extraction for {self.response_key}:")
            print(f"  All stimuli: {len(id_vector)} stimuli")

        # 2. Conditional vectors by texture type
        texture_types = {
            '2D': 'ga_mean_response_2d',
            'SHADE': 'ga_mean_response_shade',
            'SPECULAR': 'ga_mean_response_specular'
        }

        for texture, vector_type in texture_types.items():
            if texture in texture_responses and len(texture_responses[texture]) > 0:
                responses = texture_responses[texture]
                mean_responses = {stim_id: np.mean(rates) for stim_id, rates in responses.items()}
                sorted_stim_ids = sorted(mean_responses.keys())
                id_vector = sorted_stim_ids
                response_vector = [mean_responses[stim_id] for stim_id in sorted_stim_ids]

                results.append({
                    'channel': self.response_key,
                    'vector_type': vector_type,
                    'id_vector': id_vector,
                    'response_vector': response_vector,
                    'n_stimuli': len(id_vector)
                })

                print(f"  {texture} only: {len(id_vector)} stimuli")

        # 3. Combined 3D vector (SHADE + SPECULAR)
        combined_3d_responses = {}
        for texture in ['SHADE', 'SPECULAR']:
            if texture in texture_responses:
                for stim_id, rates in texture_responses[texture].items():
                    if stim_id not in combined_3d_responses:
                        combined_3d_responses[stim_id] = []
                    combined_3d_responses[stim_id].extend(rates)

        if len(combined_3d_responses) > 0:
            mean_responses = {stim_id: np.mean(rates) for stim_id, rates in combined_3d_responses.items()}
            sorted_stim_ids = sorted(mean_responses.keys())
            id_vector = sorted_stim_ids
            response_vector = [mean_responses[stim_id] for stim_id in sorted_stim_ids]

            results.append({
                'channel': self.response_key,
                'vector_type': 'ga_mean_response_3d',
                'id_vector': id_vector,
                'response_vector': response_vector,
                'n_stimuli': len(id_vector)
            })

            print(f"  3D (SHADE+SPECULAR): {len(id_vector)} stimuli")

        if not results:
            print(f"Warning: No stimuli found for channel {self.response_key}")
            return None

        print(
            f"  Mean response range (all): [{min(results[0]['response_vector']):.2f}, {max(results[0]['response_vector']):.2f}]")

        return results

    def _extract_responses_by_stimulus(self, data: pd.DataFrame, channel: str) -> dict:
        """Extract spike rates grouped by stimulus (all textures combined)."""
        responses_by_stim = {}

        for stim_id in data['StimSpecId'].unique():
            stim_trials = data[data['StimSpecId'] == stim_id]
            spike_rates = []

            for _, trial in stim_trials.iterrows():
                spike_rate_dict = trial[self.spike_data_col]
                if isinstance(spike_rate_dict, dict) and channel in spike_rate_dict:
                    spike_rates.append(spike_rate_dict[channel])

            if spike_rates:
                responses_by_stim[stim_id] = spike_rates

        return responses_by_stim

    def _extract_responses_by_stimulus_and_texture(self, data: pd.DataFrame, channel: str) -> dict:
        """
        Extract spike rates grouped by stimulus and texture type.

        Returns:
            dict: {texture_type: {stim_id: [spike_rates]}}
        """
        responses_by_texture = {}

        # Check if Texture column exists
        if 'Texture' not in data.columns:
            print("Warning: 'Texture' column not found in data. Skipping texture-specific vectors.")
            return responses_by_texture

        for texture in data['Texture'].unique():
            if pd.isna(texture):
                continue

            texture_data = data[data['Texture'] == texture]
            responses_by_texture[texture] = {}

            for stim_id in texture_data['StimSpecId'].unique():
                stim_trials = texture_data[texture_data['StimSpecId'] == stim_id]
                spike_rates = []

                for _, trial in stim_trials.iterrows():
                    spike_rate_dict = trial[self.spike_data_col]
                    if isinstance(spike_rate_dict, dict) and channel in spike_rate_dict:
                        spike_rates.append(spike_rate_dict[channel])

                if spike_rates:
                    responses_by_texture[texture][stim_id] = spike_rates

        return responses_by_texture


class ResponseVectorDBSaver(OutputHandler):
    """Output handler that saves response vectors to database (generic, reusable)."""

    def __init__(self, session_id: str, unit_name: str):
        self.unit_name = unit_name
        self.session_id = session_id
        self.conn = Connection("allen_data_repository")
        self._ensure_table_exists()

    def _ensure_table_exists(self):
        """Create the ChannelResponseVectors table if it doesn't exist."""
        # First, try to get the exact session_id type from Sessions table
        try:
            result = self.conn.execute("SHOW CREATE TABLE Sessions")
            sessions_def = list(result)[0][1]
            print(f"Sessions table definition found")
        except Exception as e:
            print(f"Note: Could not query Sessions table: {e}")
            sessions_def = None

        # Try creating with foreign key first
        create_table_with_fk_sql = """
                                   CREATE TABLE IF NOT EXISTS ChannelResponseVectors \
                                   ( \
                                       session_id      VARCHAR(10)  NOT NULL, \
                                       unit_name       VARCHAR(255) NOT NULL, \
                                       vector_type     VARCHAR(50)  NOT NULL, \
                                       id_vector       TEXT         NOT NULL, \
                                       response_vector TEXT         NOT NULL, \
                                       PRIMARY KEY (session_id, unit_name, vector_type), \
                                       CONSTRAINT ChannelResponseVectors_ibfk_1 \
                                           FOREIGN KEY (session_id) REFERENCES Sessions (session_id) \
                                               ON DELETE CASCADE
                                   ) CHARSET = latin1; \
                                   """

        # Fallback without foreign key
        create_table_without_fk_sql = """
                                      CREATE TABLE IF NOT EXISTS ChannelResponseVectors \
                                      ( \
                                          session_id      VARCHAR(10)  NOT NULL, \
                                          unit_name       VARCHAR(255) NOT NULL, \
                                          vector_type     VARCHAR(50)  NOT NULL, \
                                          id_vector       TEXT         NOT NULL, \
                                          response_vector TEXT         NOT NULL, \
                                          PRIMARY KEY (session_id, unit_name, vector_type)
                                      ) CHARSET = latin1; \
                                      """

        try:
            self.conn.execute(create_table_with_fk_sql)
            print("Table created with foreign key constraint")
        except Exception as e:
            print(f"Could not create table with foreign key: {e}")
            print("Attempting to create without foreign key...")
            try:
                self.conn.execute(create_table_without_fk_sql)
                print("Table created successfully without foreign key constraint")
            except Exception as e2:
                print(f"Error creating table: {e2}")
                raise

    def process(self, result) -> dict:
        """Save the response vectors to the database (handles multiple vector types)."""
        if result is None:
            print(f"No results to save for {self.unit_name}")
            return None

        # Handle both single dict and list of dicts
        if isinstance(result, dict):
            results = [result]
        else:
            results = result

        saved_count = 0
        for res in results:
            try:
                # Convert to native Python types (handles numpy types)
                # Use tolist() if available (for numpy arrays), otherwise convert element by element
                id_vector = res['id_vector']
                response_vector = res['response_vector']

                if hasattr(id_vector, 'tolist'):
                    id_vector = id_vector.tolist()
                else:
                    id_vector = [int(x) for x in id_vector]

                if hasattr(response_vector, 'tolist'):
                    response_vector = response_vector.tolist()
                else:
                    response_vector = [float(x) for x in response_vector]

                # Convert vectors to JSON strings
                id_vector_json = json.dumps(id_vector)
                response_vector_json = json.dumps(response_vector)

                insert_sql = """
                             INSERT INTO ChannelResponseVectors
                                 (session_id, unit_name, vector_type, id_vector, response_vector)
                             VALUES (%s, %s, %s, %s, %s)
                             ON DUPLICATE KEY UPDATE id_vector       = VALUES(id_vector),
                                                     response_vector = VALUES(response_vector)
                             """

                self.conn.execute(insert_sql, (
                    self.session_id,
                    self.unit_name,
                    res['vector_type'],
                    id_vector_json,
                    response_vector_json
                ))

                saved_count += 1

            except Exception as e:
                print(f"Could not save {res.get('vector_type', 'unknown')} to database: {e}")

        if saved_count > 0:
            print(f"\nSaved {saved_count} response vectors for session {self.session_id}, unit {self.unit_name}")
        else:
            print(f"\nGA Response Vector Results:")
            print(f"Session: {self.session_id}, Unit: {self.unit_name}")
            print(f"Generated {len(results)} vectors but could not save to database")

        return result


def create_ga_response_vector_module(channel=None, session_id=None, spike_data_col=None):
    """Create a module for GA response vector extraction."""
    vector_module = AnalysisModuleFactory.create(
        computation=GAResponseVectorExtractor(
            response_key=channel,
            spike_data_col=spike_data_col
        ),
        output_handler=ResponseVectorDBSaver(session_id, channel)
    )
    return vector_module


def main():
    """Example usage of GAResponseVectorAnalysis."""
    # Example parameters - adjust as needed
    (session_id, _) = read_session_id_from_db_name(context.ga_database)
    channel = "A-027"

    analysis = GAResponseVectorAnalysis()

    # Run analysis - will extract and save response vector
    result = analysis.run(session_id, "raw", channel)


if __name__ == "__main__":
    main()