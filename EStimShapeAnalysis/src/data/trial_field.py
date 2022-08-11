from collections import OrderedDict
import pandas as pd


class Field:
    def __init__(self):
        self.name = type(self).__name__

    def retrieveValue(self, when):
        self.value = self.name


class FieldList(list):
    def get_df(self):
        df = pd.DataFrame(columns=self.get_names())
        return df
    def get_names(self):
        return [field.name for field in self]


class Trial:

    def __init__(self, when):
        self.fields = FieldList()
        self.when = when

    def set_fields(self, fields: FieldList):
        self.fields = fields

    def append_to_data(self, data):
        self.__get_field_values()
        new_values = [i.value for i in self.fields]
        names = self.fields.get_names()
        new_row = OrderedDict(zip(names, new_values))
        data.append(new_row)

        return data

    def __get_field_values(self):
        for field in self.fields:
            field.retrieveValue(self.when)
