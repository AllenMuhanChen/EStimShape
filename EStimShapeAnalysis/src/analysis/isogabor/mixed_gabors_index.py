import numpy as np

from clat.pipeline.pipeline_base_classes import AnalysisModuleFactory
from clat.pipeline.pipeline_base_classes import ComputationModule, InputT, OutputT
from clat.pipeline.pipeline_base_classes import OutputHandler
from clat.util.connection import Connection

# Mixed gabor stimulus types (chromatic/isoluminant grating + luminance/isochromatic
# grating superimposed). One of these is the cell's "best" color pair.
MIXED_TYPES = ['RedGreenMixed', 'CyanOrangeMixed']


def create_alignment_suppression_index_module(channel=None, session_id=None, spike_data_col=None):
    """Factory for the Alignment Suppression Index module.

    Computes, per luminance frequency, whether a color grating aligned in
    frequency with the luminance grating suppresses the response relative to a
    color grating at a mismatched frequency. Positive index => aligned color
    obscures the luminance response (the 3D/luminance-preferring hypothesis).
    """
    index_module = AnalysisModuleFactory.create(
        computation=AlignmentSuppressionIndexCalculator(
            response_key=channel, spike_data_col=spike_data_col),
        output_handler=AlignmentSuppressionIndexDBSaver(session_id, channel)
    )
    return index_module


def _parse_mixed_frequency(value):
    """'Mixed Frequency' is stored as "<chromatic>, <luminance>" (see
    MixedFrequencyField). Returns (chromatic_frequency, luminance_frequency) as
    floats, or None if it can't be parsed.

    Robust to stray brackets/quotes/whitespace and to values that arrive as an
    actual list/tuple (e.g. after a round-trip through the repository)."""
    if value is None:
        return None
    try:
        if isinstance(value, (list, tuple)):
            parts = list(value)
        else:
            # Strip brackets/quotes so "[2.0, 4.0]" or "'2.0, 4.0'" also parse.
            cleaned = str(value).strip().strip("[]()'\"")
            parts = cleaned.split(",")
        if len(parts) != 2:
            return None
        return float(parts[0]), float(parts[1])
    except (ValueError, AttributeError, TypeError):
        return None


class AlignmentSuppressionIndexCalculator(ComputationModule):
    """Computes an Alignment Suppression Index (ASI) per luminance frequency.

    For each luminance frequency f_L we compare, within the cell's best color
    pair:
        aligned    = R(f_L, f_C = f_L)                  (color matches luminance)
        misaligned = mean over f_C != f_L of R(f_L, f_C) (color mismatched)
        ASI(f_L)   = (misaligned - aligned) / (misaligned + aligned)

    Holding f_L fixed controls for luminance-frequency tuning, so the only thing
    varying within a row is whether the color grating is aligned. A positive ASI
    means the aligned color grating suppresses the response (supports the
    hypothesis that aligned color contrast obscures luminance contrast).
    """

    def __init__(self, *, response_key: str = None, spike_data_col: str = None):
        self.response_key = response_key
        self.spike_data_col = spike_data_col

    def _rate(self, row):
        """Pull this channel's rate out of the spike-rate dict for a trial."""
        rates = row[self.spike_data_col]
        if isinstance(rates, dict) and self.response_key in rates:
            return rates[self.response_key]
        return None

    def _response_matrix(self, data, type_name):
        """Mean rate keyed by (luminance_frequency, chromatic_frequency) for one
        color pair, plus the pair's overall mean response (used to pick the best
        pair) and a diagnostics dict explaining any dropped rows."""
        matrix = {}
        all_rates = []
        n_bad_freq = 0
        n_bad_rate = 0
        sample_freqs = []
        type_data = data[data['Type'] == type_name]
        for _, row in type_data.iterrows():
            raw_freq = row.get('Mixed Frequency')
            if len(sample_freqs) < 3:
                sample_freqs.append(repr(raw_freq))
            freqs = _parse_mixed_frequency(raw_freq)
            rate = self._rate(row)
            if freqs is None:
                n_bad_freq += 1
                continue
            if rate is None:
                n_bad_rate += 1
                continue
            chromatic_freq, luminance_freq = freqs
            matrix.setdefault((luminance_freq, chromatic_freq), []).append(rate)
            all_rates.append(rate)

        mean_matrix = {key: float(np.mean(vals)) for key, vals in matrix.items()}
        overall_mean = float(np.mean(all_rates)) if all_rates else 0.0
        diagnostics = {
            'n_rows': len(type_data),
            'n_bad_freq': n_bad_freq,
            'n_bad_rate': n_bad_rate,
            'sample_freqs': sample_freqs,
        }
        return mean_matrix, overall_mean, diagnostics

    def compute(self, prepared_data: InputT) -> OutputT:
        # Pick the best color pair for this cell: the one with the larger overall
        # mean response across its mixed trials.
        best_pair = None
        best_mean = -np.inf
        best_matrix = {}
        diagnostics_by_type = {}
        for type_name in MIXED_TYPES:
            matrix, overall_mean, diagnostics = self._response_matrix(prepared_data, type_name)
            diagnostics_by_type[type_name] = diagnostics
            if not matrix:
                continue
            print(f"  {type_name}: overall mean response = {overall_mean:.2f} "
                  f"spikes/s across {len(matrix)} frequency combinations")
            if overall_mean > best_mean:
                best_mean = overall_mean
                best_pair = type_name
                best_matrix = matrix

        if best_pair is None:
            # Explain WHY nothing matched rather than failing silently.
            available_types = sorted(str(t) for t in prepared_data['Type'].dropna().unique())
            print(f"  Warning: no mixed gabor data for {self.response_key}, skipping.")
            print(f"    Types present in data: {available_types}")
            print(f"    (looking for {MIXED_TYPES})")
            for type_name, d in diagnostics_by_type.items():
                print(f"    {type_name}: {d['n_rows']} rows, "
                      f"{d['n_bad_freq']} failed 'Mixed Frequency' parse, "
                      f"{d['n_bad_rate']} missing rate for channel {self.response_key!r}. "
                      f"Sample 'Mixed Frequency' values: {d['sample_freqs']}")
                if d['n_rows'] > 0 and d['n_bad_rate'] == d['n_rows']:
                    # Every row had the type but no rate for this channel: show what
                    # channel keys the rate dict actually contains.
                    first = prepared_data[prepared_data['Type'] == type_name].iloc[0]
                    rates = first.get(self.spike_data_col)
                    keys = sorted(rates.keys()) if isinstance(rates, dict) else rates
                    print(f"      Rate column {self.spike_data_col!r} keys available: {keys}")
            return {}

        print(f"\nBest color pair for {self.response_key}: {best_pair} "
              f"(mean {best_mean:.2f} spikes/s)")

        # One ASI per luminance frequency.
        luminance_frequencies = sorted({lum for (lum, _chrom) in best_matrix.keys()})
        frequency_indices = {}
        for luminance_freq in luminance_frequencies:
            aligned = best_matrix.get((luminance_freq, luminance_freq))
            misaligned_rates = [
                rate for (lum, chrom), rate in best_matrix.items()
                if lum == luminance_freq and chrom != luminance_freq
            ]

            if aligned is None or len(misaligned_rates) == 0:
                print(f"  Luminance {luminance_freq}: missing aligned or misaligned "
                      f"trials, skipping.")
                continue

            misaligned = float(np.mean(misaligned_rates))
            denom = misaligned + aligned
            if denom == 0:
                asi = 0.0
            else:
                asi = (misaligned - aligned) / denom

            frequency_indices[luminance_freq] = {
                'color_pair': best_pair,
                'aligned_response': aligned,
                'misaligned_response': misaligned,
                'alignment_suppression_index': asi,
            }

            print(f"  Luminance {luminance_freq}: aligned={aligned:.2f}, "
                  f"misaligned={misaligned:.2f}, ASI={asi:.3f}")

        print(f"\nFinal ASI by luminance frequency for {self.response_key}: "
              f"{ {f: v['alignment_suppression_index'] for f, v in frequency_indices.items()} }")
        return frequency_indices


class AlignmentSuppressionIndexDBSaver(OutputHandler):
    """Saves the Alignment Suppression Index (one row per luminance frequency) to
    the data repository, mirroring the IsoChromaticLuminantScore saver."""

    def __init__(self, session_id: str, unit_name: str):
        self.unit_name = unit_name
        self.session_id = session_id
        self.conn = Connection("allen_data_repository")
        self._ensure_table_exists()

    def _ensure_table_exists(self):
        try:
            create_table_sql = """
                               CREATE TABLE IF NOT EXISTS MixedGaborAlignmentIndices
                               (
                                   session_id                  VARCHAR(10)  NOT NULL,
                                   unit_name                   VARCHAR(255) NOT NULL,
                                   luminance_frequency         FLOAT        NOT NULL,
                                   color_pair                  VARCHAR(64)  NOT NULL,
                                   aligned_response            FLOAT        NOT NULL,
                                   misaligned_response         FLOAT        NOT NULL,
                                   alignment_suppression_index FLOAT        NOT NULL,
                                   PRIMARY KEY (session_id, unit_name, luminance_frequency),
                                   CONSTRAINT MixedGaborAlignmentIndices_ibfk_1
                                       FOREIGN KEY (session_id) REFERENCES Sessions (session_id)
                                           ON DELETE CASCADE
                               ) CHARSET = latin1;
                               """
            self.conn.execute(create_table_sql)
            self._clear_session_data()
        except Exception as e:
            print(f"Warning: Could not initialize database: {e}")
            print("Will print results instead of saving to database.")

    def _clear_session_data(self):
        delete_sql = "DELETE FROM MixedGaborAlignmentIndices WHERE session_id = %s AND unit_name = %s"
        self.conn.execute(delete_sql, (self.session_id, self.unit_name))
        print(f"Cleared existing Alignment Suppression Index data for session "
              f"{self.session_id}, unit {self.unit_name}")

    def process(self, result: dict) -> dict:
        for luminance_frequency, values in result.items():
            if luminance_frequency is None or np.isnan(luminance_frequency):
                continue
            try:
                insert_sql = """
                             INSERT INTO MixedGaborAlignmentIndices
                             (session_id, unit_name, luminance_frequency, color_pair,
                              aligned_response, misaligned_response, alignment_suppression_index)
                             VALUES (%s, %s, %s, %s, %s, %s, %s)
                             """
                self.conn.execute(insert_sql, (
                    self.session_id,
                    self.unit_name,
                    float(luminance_frequency),
                    values['color_pair'],
                    float(values['aligned_response']),
                    float(values['misaligned_response']),
                    float(values['alignment_suppression_index']),
                ))
                print(f"Saved Alignment Suppression Index for session {self.session_id}, "
                      f"unit {self.unit_name}, luminance frequency {luminance_frequency}: "
                      f"ASI={values['alignment_suppression_index']:.3f}")
            except Exception as e:
                print(f"Warning: Could not save to database: {e}")
                print(f"Results - session {self.session_id}, unit {self.unit_name}, "
                      f"luminance frequency {luminance_frequency}: {values}")

        return result
