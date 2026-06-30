import ast
import re

import xmltodict

from clat.compile.tstamp.cached_tstamp_fields import CachedDatabaseField

from clat.util.connection import Connection
from clat.util.time_util import When


class StimSpecIdField(CachedDatabaseField):
    def get_name(self):
        return "StimSpecId"

    def get(self, when: When):
        return get_stim_spec_id(self.conn, when)


class StimSpecDataField(CachedDatabaseField):
    def get_name(self):
        return "StimSpecData"

    def __init__(self, conn: Connection):
        super().__init__(conn)

    def get(self, when: When):
        return get_stim_spec_data(self.conn, when)


class StimSpecField(CachedDatabaseField):
    def get_name(self):
        return "StimSpec"

    def __init__(self, conn: Connection):
        super().__init__(conn)

    def get(self, when: When) -> dict:
        return get_stim_spec(self.conn, when)


class StimTypeField(StimSpecField):
    def get_name(self):
        return "StimType"

    def get(self, when: When):
        stim_spec = self.get_cached_super(when, StimSpecField)
        try:
            stimType = stim_spec['StimSpec']['stimType']
        except KeyError:
            stimType = "None"
        return stimType

class SampleLengthField(StimSpecField):
    def get_name(self):
        return "SampleLength"

    def get(self, when: When):
        stim_spec = self.get_cached_super(when, StimSpecField)
        try:
            sampleLength = stim_spec['StimSpec']['sampleDuration']
        except KeyError:
            sampleLength = 1000
        return sampleLength

class CoherenceField(StimSpecField):
    """Signed coherence in [-1, 1] for coherence trials (0 = balanced). None for every other trial
    type (the element is absent from their StimSpec)."""
    def get_name(self):
        return "Coherence"

    def get(self, when: When):
        stim_spec = self.get_cached_super(when, StimSpecField)
        try:
            value = stim_spec['StimSpec']['coherence']
        except (KeyError, TypeError):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None


class IsRewardedField(CachedDatabaseField):
    def __init__(self, conn: Connection):
        super().__init__(conn)

    def get_name(self):
        return "IsRewarded"

    def get(self, when: When):
        # SQL to check for the presence of "ChoiceSelectionCorrect" or "ChoiceSelectionIncorrect" in the specified time frame.
        query = """
        SELECT type
        FROM BehMsg
        WHERE (type = 'ChoiceSelectionCorrect' OR type = 'ChoiceSelectionIncorect')
          AND tstamp BETWEEN %s AND %s;
        """
        self.conn.execute(query, params=(int(when.start), int(when.stop)))
        results = self.conn.fetch_all()

        # Process results.
        # Check for the presence of "ChoiceSelectionCorrect" or "ChoiceSelectionIncorrect" in the type column.
        correct = any(result[0] == 'ChoiceSelectionCorrect' for result in results)
        incorrect = any(result[0] == 'ChoiceSelectionIncorect' for result in results)

        # Return the status based on the types found.
        if correct:
            return True
        elif incorrect:
            return False
        else:
            return "No Data"


class AnswerField(StimSpecField):
    def __init__(self, conn: Connection):
        super().__init__(conn)

    def get_name(self):
        return "Answer"

    def get(self, when: When):
        query = """
              SELECT msg
              FROM BehMsg
              WHERE (type = 'ChoiceSelectionCorrect' OR type = 'ChoiceSelectionIncorect')
                AND tstamp BETWEEN %s AND %s;
              """
        self.conn.execute(query, params=(int(when.start), int(when.stop)))
        msgs = self.conn.fetch_one()

        if msgs:
            pass
        answer_indx = ast.literal_eval(msgs)

        stim_spec = self.get_cached_super(when, StimSpecField)
        answer_stim_obj_id = stim_spec['StimSpec']['choiceObjData']['long'][answer_indx[0]]
        answer_png_path = self._get_choice_png_path(answer_stim_obj_id)
        answer_set_condition = extract_roman_numeral(answer_png_path)
        return answer_set_condition

    def _get_choice_png_path(self, choice_stim_obj_id):
        query = """
        SELECT spec
        FROM StimObjData
        WHERE id=%s;
        """
        self.conn.execute(query, params=(choice_stim_obj_id,))
        results = self.conn.fetch_one()
        stim_obj_spec = xmltodict.parse(results)
        choice_path = stim_obj_spec['StimSpec']['pngPath']
        return choice_path


def extract_roman_numeral(file_path: str) -> str:
    # Define the regular expression pattern for Roman numerals
    roman_numeral_pattern = r'_([IVXLCDM]+)\.png$'

    # Search for the pattern in the file path
    match = re.search(roman_numeral_pattern, file_path)

    # If a match is found, return the Roman numeral
    if match:
        return match.group(1)
    else:
        return None



class ChoiceSetField(StimSpecField):

    def get_name(self):
        return "ChoiceSet"

    def get(self, when: When):
        choice = self._get_choice_index(when)

        choice_stim_obj_id = self._get_choice_stim_obj_id(choice, when)

        choice_path = self._get_choice_png_path(choice_stim_obj_id)

        choice_set_condition = extract_roman_numeral(choice_path)

        return choice_set_condition

    def _get_choice_png_path(self, choice_stim_obj_id):
        query = """
        SELECT spec
        FROM StimObjData
        WHERE id=%s;
        """
        self.conn.execute(query, params=(choice_stim_obj_id,))
        results = self.conn.fetch_one()
        stim_obj_spec = xmltodict.parse(results)
        choice_path = stim_obj_spec['StimSpec']['pngPath']
        return choice_path

    def _get_choice_stim_obj_id(self, choice, when):
        stim_spec = self.get_cached_super(when, StimSpecField)
        choice_stim_obj_id = stim_spec['StimSpec']['choiceObjData']['long'][int(choice)]
        return choice_stim_obj_id

    def _get_choice_index(self, when):
        query = """
                SELECT msg
                FROM BehMsg
                WHERE (type = 'ChoiceSelectionSuccess')
                  AND tstamp BETWEEN %s AND %s;
                """
        self.conn.execute(query, params=(int(when.start), int(when.stop)))
        choices = self.conn.fetch_all()
        if choices:
            choice = choices[0][0]
        return choice

def classify_choice_path(choice_path):
    """Map a choice PNG path to its category label, by the tag the generator appended to the
    filename. Shared by ChoiceField and the picked-stimulus reconstruction so both agree on the
    category of any choice in a trial (not just the one that was picked)."""
    if choice_path is None:
        return "None"
    if "_match" in choice_path:
        return "match"
    elif "_textureFoil" in choice_path:
        # Split-texture trials: the same-geometry shape as the match, rendered with the
        # opposite texture treatment (the critical lure). See EStimShapeSplitTextureNAFCStim.
        return "textureFoil"
    elif "_procedural" in choice_path:
        return "procedural"
    elif "_variant" in choice_path:
        return "variant"
    elif "_removed" in choice_path:
        return "removed"
    elif "_delta_distractor" in choice_path:
        # Must precede "_delta" — the substring "_delta" matches both "_delta.png" and
        # "_delta_distractor.png", so the more specific tag has to be tested first.
        # "_delta_distractor" identifies the extra delta(s) in a delta trial that are NOT the
        # hypothesized comparison (slot 0, the variant by convention, is labeled "_delta"
        # and IsHypothesizedField treats only that one as hypothesized).
        return "delta_distractor"
    elif "_delta" in choice_path:
        return "delta"
    elif "_rand" in choice_path:
        return "rand"
    else:
        return "None"


class ChoiceField(ChoiceSetField):
    def get_name(self):
        return "Choice"

    def get(self, when: When):
        choice = self._get_choice_index(when)

        choice_stim_obj_id = self._get_choice_stim_obj_id(choice, when)

        choice_path = self._get_choice_png_path(choice_stim_obj_id)

        return classify_choice_path(choice_path)

_COHERENCE_STIM_TYPE = 'EStimShapeCoherenceNAFCStim'


class IsCorrectField(ChoiceField):
    def get_name(self):
        return "IsCorrect"

    def get(self, when: When) -> bool:
        choice = self.get_cached_super(when, ChoiceField)
        stim_type = self.get_cached_super(when, StimTypeField)
        if stim_type == _COHERENCE_STIM_TYPE:
            return self._coherence_correct(when, choice)
        # Normal trials: the match is the one rewarded/correct option.
        return choice == "match"

    def _coherence_correct(self, when, choice):
        """Coherence-aware correctness, mirroring the generator's reward rule
        (EStimShapeCoherenceNAFCStim.specifyRewardBehavior): the correct shape is the one the
        mixture favors. The variant is the match; the mixed delta is a 'delta'-category choice.
        On truly ambiguous trials (balanced coherence, estim, or pure noise) the generator rewards
        either composing shape, so either counts as correct."""
        chose_variant = (choice == "match")
        chose_delta = choice in ("delta", "delta_distractor")

        coherence = self.get_cached_super(when, CoherenceField)
        estim_on = bool(self.get_cached_super(when, EStimEnabledField))
        noise = self.get_cached_super(when, NoiseChanceField)
        ambiguous = (coherence is None) or (float(coherence) == 0.0) or estim_on \
            or (noise is not None and float(noise) == 1.0)

        if ambiguous:
            return chose_variant or chose_delta
        if float(coherence) > 0:
            return chose_variant       # mixture favors the variant
        return chose_delta             # mixture favors the (mixed) delta


class NoiseChanceField(StimSpecDataField):
    def __init__(self, conn: Connection):
        super().__init__(conn)

    def get_name(self):
        return "NoiseChance"

    def get(self, when: When):
        stim_spec_data = self.get_cached_super(when, StimSpecDataField)

        noiseChance = stim_spec_data[next(iter(stim_spec_data))]["noiseChance"]
        noiseChance = float(noiseChance)
        return noiseChance


class GenIdField(CachedDatabaseField):
    def __init__(self, conn: Connection):
        super().__init__(conn)

    def get_name(self):
        return "GenId"

    def get(self, when: When):
        stim_spec_id = get_stim_spec_id(self.conn, when)
        if stim_spec_id is None:
            return None

        # SQL to get the gen_id from TaskToDo based on the stim_id
        query = """
        SELECT gen_id
        FROM TaskToDo
        WHERE stim_id = %s
        LIMIT 1;
        """
        self.conn.execute(query, params=(stim_spec_id,))
        result = self.conn.fetch_one()

        if result:
            return result



def _stim_spec_param(stim_spec_data, key):
    """Read a scalar param (e.g. 'numChoices') from the trial's serialized StimSpec data.

    The XML's single top-level element is the trial-parameters object (e.g.
    ProceduralStimParameters); the behavioral counts live directly under it. Returns None
    when the key is absent (legacy trials / trial types that don't record it) so compilation
    of a mixed session never crashes on one odd trial."""
    try:
        params = stim_spec_data[next(iter(stim_spec_data))]
        return params[key]
    except (KeyError, StopIteration, TypeError):
        return None


class NumRandDistractorsField(StimSpecDataField):
    def __init__(self, conn: Connection):
        super().__init__(conn)

    def get_name(self):
        return "NumRandDistractors"

    def get(self, when: When):
        stim_spec_data = self.get_cached_super(when, StimSpecDataField)
        num = _stim_spec_param(stim_spec_data, "numRandDistractors")
        return int(num) if num is not None else None


class NumChoicesField(StimSpecDataField):
    """Number of choices offered on the trial (the match plus every distractor).

    Read straight from the trial's StimSpec params (ProceduralStimParameters.numChoices)."""
    def __init__(self, conn: Connection):
        super().__init__(conn)

    def get_name(self):
        return "NumChoices"

    def get(self, when: When):
        stim_spec_data = self.get_cached_super(when, StimSpecDataField)
        num = _stim_spec_param(stim_spec_data, "numChoices")
        return int(num) if num is not None else None


class NumProceduralDistractorsField(StimSpecDataField):
    """Number of procedural (structured, non-random) distractors on the trial.

    Not stored explicitly in the StimSpec params, so it is derived the same way the Java
    generator does (ProceduralStim.assignStimObjIds):
        numProceduralDistractors = numChoices - numRandDistractors - 1
    (the -1 is the match). Returns None if either input is missing."""
    def __init__(self, conn: Connection):
        super().__init__(conn)

    def get_name(self):
        return "NumProceduralDistractors"

    def get(self, when: When):
        stim_spec_data = self.get_cached_super(when, StimSpecDataField)
        num_choices = _stim_spec_param(stim_spec_data, "numChoices")
        num_rand = _stim_spec_param(stim_spec_data, "numRandDistractors")
        if num_choices is None or num_rand is None:
            return None
        return int(num_choices) - int(num_rand) - 1


class TrialTypeField(StimSpecDataField):

    def __init__(self, conn: Connection):
        super().__init__(conn)

    def get(self, when: When):
        stim_spec_data = StimSpecDataField.get(self, when)
        return self._parse_type_from_stim_spec_data(stim_spec_data)

    @staticmethod
    def _parse_type_from_stim_spec_data(stim_spec_data):
        try:
            stim_spec_data_type = list(stim_spec_data.keys())[0]
            if "RandNoisyTrialParameters" in stim_spec_data_type:
                return "Rand"
            elif "Psychometric" in stim_spec_data_type:
                return "Psychometric"
            else:
                return "Unknown"
        except:
            print(stim_spec_data)
            return "Unknown"

class EStimObjDataField(CachedDatabaseField):
    def __init__(self, conn: Connection):
        super().__init__(conn)
    def get_name(self):
        return "EStimObjData"
    def get(self, when: When)->dict:
        stim_spec = self.get_cached_super(when, StimSpecField)
        estim_obj_data = stim_spec['StimSpec']['eStimObjData']
        return estim_obj_data



class EStimEnabledField(CachedDatabaseField):
    def __init__(self, conn: Connection):
        super().__init__(conn)

    def get_name(self):
        return "EStimEnabled"

    def get(self, when: When):

        estim_obj_data = self.get_cached_super(when, EStimObjDataField)
        print(estim_obj_data)
        if estim_obj_data is None:
            return False
        else:
            return True

class EStimSpecIdField(EStimObjDataField):
    def __init__(self, conn: Connection):
        super().__init__(conn)

    def get_name(self):
        return "EStimSpecId"

    def get(self, when: When):
        estim_obj_data = self.get_cached_super(when, EStimObjDataField)
        print(estim_obj_data)
        if estim_obj_data is None:
            return None
        else:
            estim_spec_id = estim_obj_data['long']
            return estim_spec_id

class EStimSpecField(EStimSpecIdField):
    def __init__(self, conn: Connection):
        super().__init__(conn)

    def get_name(self):
        return "EStimSpec"

    def get(self, when: When) -> dict:
        estim_spec_id = self.get_cached_super(when, EStimSpecIdField)
        if estim_spec_id is None:
            return None
        query = """
        SELECT spec FROM EStimObjData
            WHERE id = %s
        """
        self.conn.execute(query, params=(estim_spec_id,))
        result = self.conn.fetch_one()
        if result is None:
            return None
        spec = xmltodict.parse(result)['EStimParameters']['eStimParametersForChannels']['entry']

        return spec

class WaveformField(EStimSpecField):
    def __init__(self, conn: Connection):
        super().__init__(conn)

    def get_name(self):
        return "EStimWaveform"

    def get(self, when: When) -> dict:
        estim_spec = self.get_cached_super(when, EStimSpecField)
        if estim_spec is None:
            return None
        if type(estim_spec) == list:
            return estim_spec[0]['org.xper.intan.stimulation.ChannelEStimParameters']['waveformParameters']
        else:
            return estim_spec['org.xper.intan.stimulation.ChannelEStimParameters']['waveformParameters']

class PulseTrainParametersField(EStimSpecField):
    """Returns the pulseTrainParameters dict from the EStim XML."""
    def __init__(self, conn: Connection):
        super().__init__(conn)

    def get_name(self):
        return "EStimPulseTrainParameters"

    def get(self, when: When) -> dict:
        estim_spec = self.get_cached_super(when, EStimSpecField)
        if estim_spec is None:
            return None
        if type(estim_spec) == list:
            return estim_spec[0]['org.xper.intan.stimulation.ChannelEStimParameters']['pulseTrainParameters']
        else:
            return estim_spec['org.xper.intan.stimulation.ChannelEStimParameters']['pulseTrainParameters']


class EStimPostTriggerDelayField(PulseTrainParametersField):
    """postTriggerDelay (us): time between trigger edge and stim onset."""
    def __init__(self, conn: Connection):
        super().__init__(conn)

    def get_name(self):
        return "EStimPostTriggerDelay"

    def get(self, when: When):
        params = self.get_cached_super(when, PulseTrainParametersField)
        if params is None:
            return None
        return float(params['postTriggerDelay'])


class EStimNumPulsesField(PulseTrainParametersField):
    """numRepetitions: number of pulses per trigger."""
    def __init__(self, conn: Connection):
        super().__init__(conn)

    def get_name(self):
        return "EStimNumPulses"

    def get(self, when: When):
        params = self.get_cached_super(when, PulseTrainParametersField)
        if params is None:
            return None
        return int(params['numRepetitions'])


class EStimPulseTrainPeriodField(PulseTrainParametersField):
    """pulseTrainPeriod (us): interval between successive pulses in a train."""
    def __init__(self, conn: Connection):
        super().__init__(conn)

    def get_name(self):
        return "EStimPulseTrainPeriod"

    def get(self, when: When):
        params = self.get_cached_super(when, PulseTrainParametersField)
        if params is None:
            return None
        return float(params['pulseTrainPeriod'])


class EStimPostStimRefractoryPeriodField(PulseTrainParametersField):
    """postStimRefractoryPeriod (us)."""
    def __init__(self, conn: Connection):
        super().__init__(conn)

    def get_name(self):
        return "EStimPostStimRefractoryPeriod"

    def get(self, when: When):
        params = self.get_cached_super(when, PulseTrainParametersField)
        if params is None:
            return None
        return float(params['postStimRefractoryPeriod'])


class EStimPulseWidthField(WaveformField):
    """Total stim waveform duration (us). For biphasic polarity the XML
    only stores one phase's worth of d1/dp/d2, so the result is doubled."""
    def __init__(self, conn: Connection):
        super().__init__(conn)

    def get_name(self):
        return "EStimPulseWidth"

    def get(self, when: When):
        wf = self.get_cached_super(when, WaveformField)
        if wf is None:
            return None
        d1 = float(wf.get('d1') or 0.0)
        d2 = float(wf.get('d2') or 0.0)
        dp = float(wf.get('dp') or 0.0)
        shape = str(wf.get('shape') or '').lower()
        # dp (interphase delay) only contributes when the shape explicitly
        # has an interphase delay; plain Biphasic / Triphasic skip it.
        if 'interphasedelay' in shape:
            return d1 + dp + d2
        return d1 + d2


class EStimPolarityField(WaveformField):
    def __init__(self, conn: Connection):
        super().__init__(conn)

    def get_name(self):
        return "EStimPolarity"

    def get(self, when: When) -> dict:
        waveform_params = self.get_cached_super(when, WaveformField)
        if waveform_params is None:
            return None
        print(waveform_params)
        polarity = waveform_params['polarity']
        print(polarity)
        return polarity

class EStimEnabledFieldLegacy(CachedDatabaseField):
    def __init__(self, conn: Connection):
        super().__init__(conn)

    def get_name(self):
        return "EStimEnabled"

    def get(self, when: When):
        stim_spec_id = get_stim_spec_id(self.conn, when)
        if stim_spec_id is None:
            return False

        # SQL to get the spec from EStimObjData based on the stim_id
        query = """
        SELECT spec
        FROM EStimObjData
        WHERE id = %s
        LIMIT 1;
        """
        self.conn.execute(query, params=(stim_spec_id,))
        result = self.conn.fetch_one()

        # If no result found, return False
        if not result:
            return False

        # Check if "EStimEnabled" is in the spec
        spec = result
        if spec and "EStimEnabled" in spec:
            return True
        else:
            return False


def get_stim_spec_id(conn: Connection, when: When) -> int:
    conn.execute(
        "SELECT msg from BehMsg WHERE "
        "msg LIKE '%TrialMessage%' AND "
        "tstamp >= %s AND tstamp <= %s",
        params=(int(when.start), int(when.stop)))
    trial_msg_xml = conn.fetch_one()
    trial_msg_dict = xmltodict.parse(trial_msg_xml)
    return int(trial_msg_dict['TrialMessage']['stimSpecId'])


def get_stim_spec_data(conn: Connection, when: When) -> dict:
    """Given a tstamp of trialStart and trialStop, finds the stimSpec Id from Trial Message and then reads data from
    StimSpec """
    stim_spec_id = get_stim_spec_id(conn, when)
    conn.execute("SELECT data from StimSpec WHERE "
                 "id = %s",
                 params=(stim_spec_id,))

    stim_spec_data_xml = conn.fetch_one()
    stim_spec_data_dict = xmltodict.parse(stim_spec_data_xml)
    return stim_spec_data_dict


def get_stim_spec(conn: Connection, when: When) -> dict:
    stim_spec_id = get_stim_spec_id(conn, when)
    conn.execute("SELECT spec from StimSpec WHERE "
                 "id = %s",
                 params=(stim_spec_id,))

    stim_spec_xml = conn.fetch_one()
    stim_spec_dict = xmltodict.parse(stim_spec_xml)
    return stim_spec_dict


class BaseMStickIdField(CachedDatabaseField):
    def __init__(self, conn: Connection):
        super().__init__(conn)

    def get_name(self):
        return "BaseMStickId"

    def get(self, when: When):
        stim_spec_id = get_stim_spec_id(self.conn, when)
        if stim_spec_id is None:
            return None

        # SQL to get the base_mstick_stim_spec_id from BaseMStickId based on the stim_id
        query = """
        SELECT base_mstick_stim_spec_id
        FROM BaseMStickId
        WHERE stim_id = %s
        LIMIT 1;
        """
        self.conn.execute(query, params=(stim_spec_id,))
        result = self.conn.fetch_one()

        if result:
            return result
        else:
            return None



class IsDeltaField(CachedDatabaseField):
    def __init__(self, conn: Connection):
        super().__init__(conn)

    def get_name(self):
        return "IsDelta"

    def _has_sample_role_table(self) -> bool:
        if not hasattr(self, "_sample_role_checked"):
            self.conn.execute("SHOW TABLES LIKE 'NafcSampleRole'")
            self._sample_role_exists = self.conn.fetch_one() is not None
            self._sample_role_checked = True
        return self._sample_role_exists

    def get(self, when: When):
        # Prefer the per-trial role recorded by the generator. This is unambiguous for delta->delta
        # chains, where a stimulus can be the delta in one pair and the variant in another, so its
        # role can't be decided from global IncludedDeltas membership.
        if self._has_sample_role_table():
            trial_stim_id = get_stim_spec_id(self.conn, when)
            if trial_stim_id is not None:
                self.conn.execute(
                    "SELECT is_sample_delta FROM NafcSampleRole WHERE stim_id = %s LIMIT 1;",
                    params=(trial_stim_id,))
                role = self.conn.fetch_one()
                if role is not None:
                    return bool(role)

        # Fallback for trials generated before per-trial roles were recorded (no delta->delta
        # chains exist there, so global IncludedDeltas membership is unambiguous).
        base_mstick_id = self.get_cached_super(when, BaseMStickIdField)

        if base_mstick_id is None:
            raise ValueError(f"BaseMStickId is None for timestamp {when.start}-{when.stop}")

        # Check if this ID appears as delta_id (returns True)
        query_delta = """
                      SELECT delta_id
                      FROM IncludedDeltas
                      WHERE delta_id = %s AND included = 1
                      LIMIT 1; \
                      """
        self.conn.execute(query_delta, params=(base_mstick_id,))
        delta_result = self.conn.fetch_one()

        if delta_result is not None:
            return True

        # Check if this ID appears as variant_id (returns False)
        query_variant = """
                        SELECT variant_id
                        FROM IncludedDeltas
                        WHERE variant_id = %s AND included = 1
                        LIMIT 1; \
                        """
        self.conn.execute(query_variant, params=(base_mstick_id,))
        variant_result = self.conn.fetch_one()

        if variant_result is not None:
            return False

        # If not found in either column, raise an error
        raise ValueError(f"BaseMStickId {base_mstick_id} not found in IncludedDeltas table")

class IsRemovedTrialField(ChoiceSetField):
    """True when the trial's sample is the variant with its tuned-for component deleted.

    Detected by choice composition: deleted-as-sample trials offer the intact variant as a
    procedural distractor labeled "_variant", which never appears in variant/delta paired
    trials (their non-match procedural is always labeled "_delta" by legacy convention).
    """
    def __init__(self, conn: Connection):
        super().__init__(conn)

    def get_name(self):
        return "IsRemovedTrial"

    def get(self, when: When):
        stim_spec = self.get_cached_super(when, StimSpecField)
        choice_obj_ids = stim_spec['StimSpec']['choiceObjData']['long']
        # choiceObjData['long'] is a list when multiple choices; a single value otherwise.
        if not isinstance(choice_obj_ids, list):
            choice_obj_ids = [choice_obj_ids]
        for cid in choice_obj_ids:
            path = self._get_choice_png_path(cid)
            if "_variant" in path:
                return True
        return False

class TrialTypeField(IsDeltaField):
    def __init__(self, conn: Connection):
        super().__init__(conn)

    def get_name(self):
        return "TrialType"

    def get(self, when: When):
        is_removed_trial = self.get_cached_super(when, IsRemovedTrialField)
        if is_removed_trial:
            return "Removed Shape"
        is_delta = self.get_cached_super(when, IsDeltaField)
        if is_delta is None:
            return "Hypothesized Shape"
        if is_delta:
            return "Delta Shape"
        else:
            return "Hypothesized Shape"

class IsHypothesizedField(IsDeltaField):
    def __init__(self, conn: Connection):
        super().__init__(conn)

    def get_name(self):
        return "IsHypothesized"

    def get(self, when: When):
        is_removed_trial = self.get_cached_super(when, IsRemovedTrialField)
        choice = self.get_cached_super(when, ChoiceField)
        if is_removed_trial:
            # Sample is the removed shape; the variant is offered as an explicit choice.
            # IsDelta would say False here (baseMStickId is the variantId), so the variant-trial
            # branch below would misclassify match-picks as hypothesized. Handle this case first.
            return choice == "variant"
        is_delta = self.get_cached_super(when, IsDeltaField)
        if not is_delta:
            # Variant trial: the sample (= match) is the variant.
            if choice == "match":
                return True
            else:
                return False
        else:
            # Delta trial: the non-match procedural (labeled "_delta" by legacy convention) is
            # actually the variant. See nafc_database_fields.py history and the Java side at
            # EStimShapeVariantsDeltaNAFCStim.assignLabels.
            if choice == "delta":
                return True
            else:
                return False

class IsTextureSplitField(StimTypeField):
    """True for split-texture trials (stimType EStimShapeSplitTextureNAFCStim)."""
    def get_name(self):
        return "IsTextureSplit"

    def get(self, when: When):
        stim_type = self.get_cached_super(when, StimTypeField)
        return stim_type == "EStimShapeSplitTextureNAFCStim"


class _SplitTextureParamsField(CachedDatabaseField):
    """Base for fields read from NafcSplitTextureParams (written by the generator per split trial)."""
    def _has_split_texture_table(self) -> bool:
        if not hasattr(self, "_split_params_checked"):
            self.conn.execute("SHOW TABLES LIKE 'NafcSplitTextureParams'")
            self._split_params_exists = self.conn.fetch_one() is not None
            self._split_params_checked = True
        return self._split_params_exists

    def _read_param(self, when: When, column: str):
        if not self._has_split_texture_table():
            return None
        stim_id = get_stim_spec_id(self.conn, when)
        if stim_id is None:
            return None
        self.conn.execute(
            "SELECT " + column + " FROM NafcSplitTextureParams WHERE stim_id = %s LIMIT 1;",
            params=(stim_id,))
        return self.conn.fetch_one()


class SplitRenderIsSampleField(_SplitTextureParamsField):
    """Whether the split cue rode on the sample/match (True) or the texture foil (False).
    None for non-split trials."""
    def get_name(self):
        return "SplitRenderIsSample"

    def get(self, when: When):
        row = self._read_param(when, "split_render_is_sample")
        return None if row is None else bool(row)


class InvertedShadingField(_SplitTextureParamsField):
    """Whether the body was the contrast texture and the hypothesized limb the original (True),
    vs. the normal arrangement (False). None for non-split trials."""
    def get_name(self):
        return "InvertedShading"

    def get(self, when: When):
        row = self._read_param(when, "inverted_shading")
        return None if row is None else bool(row)


class ContrastTextureField(_SplitTextureParamsField):
    """The contrast texture used in a split trial (e.g. '2D'). None for non-split trials."""
    def get_name(self):
        return "ContrastTexture"

    def get(self, when: When):
        return self._read_param(when, "contrast_texture")


class Is3DChoiceField(CachedDatabaseField):
    """For split-texture trials where the subject chose the match or the texture foil: True if the
    chosen option's hypothesized limb was rendered in 3D (SPECULAR/SHADE), False if 2D, None
    otherwise (non-split trial, or a choice that was neither the match nor the foil).

    The match and foil are the same geometry with opposite texture treatments, so exactly one of
    them shows the hypothesized limb in 3D. The match shows the 3D limb iff
    split_render_is_sample == inverted_shading (see SplitTextureConfig on the Java side); the foil
    is the opposite. This is the primitive for the split panel's "% 3D" metric, which compares
    only match-vs-foil picks (other distractors don't count toward it)."""
    def get_name(self):
        return "Is3DChoice"

    def get(self, when: When):
        choice = self.get_cached_super(when, ChoiceField)
        if choice not in ("match", "textureFoil"):
            return None
        split_render_is_sample = self.get_cached_super(when, SplitRenderIsSampleField)
        inverted = self.get_cached_super(when, InvertedShadingField)
        if split_render_is_sample is None or inverted is None:
            return None
        match_is_3d_limb = (bool(split_render_is_sample) == bool(inverted))
        return match_is_3d_limb if choice == "match" else (not match_is_3d_limb)


class IsHypothesizedFieldLegacy(IsDeltaField):
    def __init__(self, conn: Connection):
        super().__init__(conn)

    def get_name(self):
        return "IsHypothesized"

    def get(self, when: When):
        is_delta = self.get_cached_super(when, IsDeltaField)
        choice = self.get_cached_super(when, ChoiceField)
        if not is_delta:
            if choice == "match":
                return True
            else:
                return False
        else:
            if choice == "procedural":
                return True
            else:
                return False


# Choice categories that correspond to a non-sample lineage member (a variant or delta offered
# as a procedural distractor). Used to map a pick back to its specific lineage stimulus.
_LINEAGE_DISTRACTOR_CATEGORIES = ("delta", "delta_distractor")


def reconstruct_picked_lineage_id(categories, picked_index, sample_id,
                                  distractor_lineage_order):
    """Pure mapping from a trial's choice layout to the lineage id of the picked shape.

    Args:
        categories: per-choice category labels in choiceObjData order (see classify_choice_path).
        picked_index: index into ``categories`` of the choice the animal selected.
        sample_id: the sample's lineage id (== the 'match' choice's lineage id).
        distractor_lineage_order: lineage ids of the procedural distractors, in the order the
            generator added them (so the k-th delta-category choice is entry k).

    Returns the picked lineage id, or None when the pick isn't a plain lineage member
    (rand/removed/textureFoil/procedural) or the layout can't be mapped. Kept free of DB/IO so it
    can be unit-tested and reused.
    """
    if picked_index is None or picked_index < 0 or picked_index >= len(categories):
        return None
    picked_cat = categories[picked_index]
    if picked_cat == "match":
        return sample_id
    if picked_cat not in _LINEAGE_DISTRACTOR_CATEGORIES:
        return None
    if distractor_lineage_order is None:
        return None
    # Rank of the pick among delta-category choices, in order, indexes the distractor list.
    k = sum(1 for c in categories[:picked_index] if c in _LINEAGE_DISTRACTOR_CATEGORIES)
    if k >= len(distractor_lineage_order):
        return None
    return distractor_lineage_order[k]


class PickedBaseMStickIdField(ChoiceSetField):
    """The lineage stim-spec id (a variant_id or a delta_id) of the shape the animal actually
    PICKED on a variant/delta NAFC trial — the counterpart to BaseMStickId, which is the SAMPLE's
    lineage id. Returns None when the pick is not a plain lineage member (rand/removed/textureFoil),
    when the trial isn't a variant/delta trial, or when the mapping can't be reconstructed.

    Reconstruction (the DB records only the sample's lineage id, not each choice's):
      - A 'match' pick is the sample itself  -> base_mstick_id.
      - A non-match delta-category pick is the k-th lineage distractor, where k is its rank among
        the trial's delta-category choices in choiceObjData order. That order mirrors the
        generator's distractor list (EStimShapeVariantsDeltaNAFCStim.generateProceduralDistractors
        / assignLabels): for a variant-sample trial the distractors are the variant's included
        deltas (IncludedDeltas order); for a delta-sample trial they are [variant, other deltas...].

    This relies on the per-variant IncludedDeltas ordering being stable between trial generation
    and analysis, which holds within a session. Any failure degrades to None rather than raising,
    so one odd trial never breaks compilation."""

    def get_name(self):
        return "PickedBaseMStickId"

    def get(self, when: When):
        try:
            return self._compute(when)
        except Exception:
            return None

    def _compute(self, when: When):
        stim_spec = self.get_cached_super(when, StimSpecField)
        choice_ids = stim_spec['StimSpec']['choiceObjData']['long']
        if not isinstance(choice_ids, list):
            # A single choice (non-NAFC) — no lineage distractor structure to map.
            return None

        picked_index = int(self._get_choice_index(when))
        categories = [self._safe_category(cid) for cid in choice_ids]

        sample_id = self.get_cached_super(when, BaseMStickIdField)
        if sample_id is None:
            return None
        sample_id = int(sample_id)

        # Only resolve the distractor order when the pick is actually a non-sample lineage member
        # (avoids the extra IncludedDeltas queries on match/rand picks).
        needs_distractors = (picked_index < len(categories)
                             and categories[picked_index] in _LINEAGE_DISTRACTOR_CATEGORIES)
        distractors = self._distractor_lineage_order(when, sample_id) if needs_distractors else None
        return reconstruct_picked_lineage_id(categories, picked_index, sample_id, distractors)

    def _safe_category(self, choice_stim_obj_id):
        """Category of one choice, tolerant of a missing/unreadable StimObjData row so one bad
        choice doesn't nullify the whole trial's pick (returns 'None' on failure)."""
        try:
            return classify_choice_path(self._get_choice_png_path(choice_stim_obj_id))
        except Exception:
            return "None"

    def _distractor_lineage_order(self, when: When, sample_id: int):
        """The lineage ids of this trial's procedural distractors, in the order the generator
        added them. None if the lineage can't be resolved."""
        is_delta = self.get_cached_super(when, IsDeltaField)
        variant_id = self._variant_id_for_trial(when, sample_id, is_delta)
        if variant_id is None:
            return None
        included = self._included_delta_ids(variant_id)
        if not is_delta:
            # Variant-sample trial: distractors are the variant's included deltas, in order.
            return included
        # Delta-sample trial: distractors are [variant, then the other included deltas].
        return [variant_id] + [d for d in included if d != sample_id]

    def _variant_id_for_trial(self, when: When, sample_id: int, is_delta):
        """The variant id of this trial's lineage. Prefers the per-trial NafcSampleRole record
        (authoritative for delta->delta chains); falls back to IncludedDeltas membership."""
        # Per-trial role (records the lineage's variant_id directly) when available.
        if self._has_sample_role_table():
            trial_stim_id = get_stim_spec_id(self.conn, when)
            if trial_stim_id is not None:
                self.conn.execute(
                    "SELECT variant_id FROM NafcSampleRole WHERE stim_id = %s LIMIT 1;",
                    params=(trial_stim_id,))
                row = self.conn.fetch_one()
                if row is not None:
                    return int(row)
        if not is_delta:
            return sample_id  # the sample IS the variant
        # Fallback: look the delta up in IncludedDeltas.
        self.conn.execute(
            "SELECT variant_id FROM IncludedDeltas WHERE delta_id = %s AND included = 1 LIMIT 1;",
            params=(sample_id,))
        row = self.conn.fetch_one()
        return None if row is None else int(row)

    def _included_delta_ids(self, variant_id: int):
        """The included delta ids for a variant, in the DB's natural order — matching the
        unordered query the generator used (EStimShapeVariantsDeltaNAFCStim.getDeltaIdsFromVariantId)
        so distractor slot positions line up."""
        self.conn.execute(
            "SELECT delta_id FROM IncludedDeltas WHERE variant_id = %s AND included = 1;",
            params=(int(variant_id),))
        return [int(r[0]) for r in self.conn.fetch_all()]

    def _has_sample_role_table(self) -> bool:
        """Whether the per-trial NafcSampleRole table exists (added partway through the project)."""
        if not hasattr(self, "_sample_role_checked"):
            self.conn.execute("SHOW TABLES LIKE 'NafcSampleRole'")
            self._sample_role_exists = self.conn.fetch_one() is not None
            self._sample_role_checked = True
        return self._sample_role_exists