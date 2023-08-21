from unittest import TestCase

from compile.trial.matchstick_fields import MatchStickField, ShaftField, TerminationField, JunctionField
from src.util.time_util import When


class Test(TestCase):

    def test_match_stick_field(self):
        field = MatchStickField(TestMStickSource())
        mstick_spec = field.get(None)
        assert(list(mstick_spec.keys())[0] == "AllenMStickData")

    def test_shaft_field(self):
        field = ShaftField(TestMStickSource())
        for field in field.get(None):
            data_fields = field.keys()
            assert(data_fields.__contains__('angularPosition'))
            assert(data_fields.__contains__('radialPosition'))
            assert(data_fields.__contains__('orientation'))
            assert(data_fields.__contains__('radius'))
            assert(data_fields.__contains__('length'))
            assert(data_fields.__contains__('curvature'))

    def test_termination_field(self):
        field = TerminationField(TestMStickSource())
        for field in field.get(None):
            data_fields = field.keys()
            assert(data_fields.__contains__('angularPosition'))
            assert(data_fields.__contains__('radialPosition'))
            assert(data_fields.__contains__('direction'))
            assert(data_fields.__contains__('radius'))

    def test_junction_field(self):
        field = JunctionField(TestMStickSource())
        for field in field.get(None):
            print(field)
            data_fields = field.keys()
            print(data_fields)
            assert(data_fields.__contains__('angularPosition'))
            assert(data_fields.__contains__('radialPosition'))
            assert(data_fields.__contains__('angleBisectorDirection'))
            assert(data_fields.__contains__('radius'))

    def test_comp_txt(self):
        comp_file = open("/home/r2_allen/Documents/EStimShape/dev_221110/specs/1670009332620530_comp.txt")
        comp = comp_file.read()
        comp_file.close()
        print(comp)



class TestMStickSource:

    def get(self, when:When):
        xml_file = open("/home/r2_allen/git/EStimShape/xper-train/xper-allen/test/test-resources/testBin/AllenMStickDataTest_testFile_spec.xml")
        spec = xml_file.read()
        xml_file.close()
        return spec
