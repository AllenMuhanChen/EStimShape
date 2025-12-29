import ast
import re

import xmltodict
from clat.compile.tstamp.cached_tstamp_fields import CachedDatabaseField

from clat.util.connection import Connection
from clat.util.time_util import When


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

class ChoiceField(ChoiceSetField):
    def get_name(self):
        return "Choice"

    def get(self, when: When):
        choice = self._get_choice_index(when)

        choice_stim_obj_id = self._get_choice_stim_obj_id(choice, when)

        choice_path = self._get_choice_png_path(choice_stim_obj_id)


        if "match" in choice_path:
            return "match"
        elif "procedural" in choice_path:
            return "procedural"
        elif "rand" in choice_path:
            return "rand"
        else:
            return "None"

class IsCorrectField(ChoiceField):
    def get_name(self):
        return "IsCorrect"

    def get(self, when: When) -> bool:
        choice = self.get_cached_super(when, ChoiceField)
        if choice == "match":
            return True
        else:
            return False


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




class NumRandDistractorsField(StimSpecDataField):
    def __init__(self, conn: Connection):
        super().__init__(conn)

    def get_name(self):
        return "NumRandDistractors"

    def get(self, when: When):
        stim_spec_data = super().get(when)

        numRandDistractors = stim_spec_data[next(iter(stim_spec_data))]["numRandDistractors"]
        numRandDistractors = int(numRandDistractors)
        return numRandDistractors


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


class EStimEnabledField(CachedDatabaseField):
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