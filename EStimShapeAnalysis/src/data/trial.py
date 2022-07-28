import pandas as pd
import timeutil

class Field:
    def __init__(self):
        self.name = type(self).__name__
    def getValue(self, when):
        self.value = self.name

class FieldList(list):
    pass

class Trial:

    def __init__(self, when):
        self.fields = []
        self.when = when

    def add_field(self, field:Field):
        self.fields.append(field)

    def append_to_data_frame(self, df:pd.DataFrame):
        self.__get_field_values()
        # df.iloc[-1:] = [i.value for i in self.fields]
        df = df.append(pd.Series([i.value for i in self.fields]), ignore_index=True)
        return df

    def __get_field_values(self):
        for field in self.fields:
            field.getValue(self.when)
















