from unittest import TestCase

import xmltodict

from src.compile.matchstick_fields import MatchStickField, ShaftField
from src.util.time_util import When


class Test(TestCase):

    def test_match_stick_field(self):
        field = MatchStickField(TestMStickSource())
        mstick_spec = field.get(None)
        assert(list(mstick_spec.keys())[0] == "AllenMStickSpec")

    def test_shaft_field(self):
        field = ShaftField(TestMStickSource())
        print(field.get(None))


class TestMStickSource:

    def get(self, when:When):
        xml_file = open("/home/r2_allen/Documents/EStimShape/dev_221110/specs/1670009332620530_spec.xml")
        spec = xml_file.read()
        xml_file.close()
        return spec
