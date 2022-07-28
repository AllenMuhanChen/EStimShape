import pandas as pd

class Field:
    def getValue(self):
        self.value = "foo"


class Trial:
    def __init__(self):
        self.fields = []
    def append_field(self, field:Field):
        self.fields.append(field)
    def append_to_data_frame(self, df:pd.DataFrame):
        # df.iloc[-1:] = [i.value for i in self.fields]
        df = df.append(pd.Series([i.value for i in self.fields]), ignore_index=True)
        return df


trial = Trial()


class DuckField:
    def __init__(self, quack):
        self.quack = quack
    def getValue(self):
        self.value = self.quack

## Interface for defining fields
f = Field()
d1 = DuckField("duck1")
d2 = DuckField("duck2")

## Interface for adding fields to a trial
trial.append_field(f)
trial.append_field(d1)
trial.append_field(d2)


## Interface for getting fields
for f in trial.fields:
    f.getValue()

## Interface for converting to dataframe for storage
df = pd.DataFrame()
for field in trial.fields:
    print(field.value)

df = trial.append_to_data_frame(df)
print(df)