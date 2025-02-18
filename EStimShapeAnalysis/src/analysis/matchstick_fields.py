from clat.compile.trial.cached_fields import CachedDatabaseField
from clat.util.time_util import When


class MatchStickField(CachedDatabaseField):
    def __init__(self, conn, mstick_spec_data_source):
        super().__init__(conn)
        self.mstick_spec_source = mstick_spec_data_source

    def get(self, when: When) -> dict:
        return self.mstick_spec_source.get(when)

    def get_name(self):
        return "MatchStickData"


class ShaftField(MatchStickField):
    def get(self, when: When) -> list[dict]:
        mstick_data = self.get_cached_super(when, MatchStickField, self.mstick_spec_source)
        shaft_data = mstick_data["AllenMStickData"]['shaftData']['ShaftData']
        return shaft_data

    def get_name(self):
        return "Shaft"


class TerminationField(MatchStickField):
    def get(self, when: When) -> list[dict]:
        mstick_data = self.get_cached_super(when, MatchStickField, self.mstick_spec_source)
        termination_data = mstick_data["AllenMStickData"]['terminationData']['TerminationData']
        return termination_data

    def get_name(self):
        return "Termination"


class JunctionField(MatchStickField):
    def get(self, when: When) -> list[dict]:
        mstick_data = self.get_cached_super(when, MatchStickField, self.mstick_spec_source)
        junction_data = mstick_data["AllenMStickData"]['junctionData']['JunctionData']

        # We don't need these for RWA so let's remove them
        if isinstance(junction_data, list):
            for junction in junction_data:
                del junction['id']
                del junction['connectedCompIds']
        else:
            del junction_data['id']
            del junction_data['connectedCompIds']

        return junction_data

    def get_name(self):
        return "Junction"
