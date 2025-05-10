from abc import ABC, abstractmethod

import pandas as pd

from src.analysis.compile_all import analyses


def main():
    session_id = "250427_0"
    channel = "A-018"
    for analysis in analyses:
        # TODO: we could refractor the parsing of data_type to here and pass in the cols and stuff
        # and perhaps pack the parameters into a class so it can be more flexible!

        analysis.analyze(channel, "raw", session_id=session_id)

class Analysis(ABC):
    @abstractmethod
    def analyze(self, channel, data_type: str, session_id: str = None, compiled_data: pd.DataFrame = None):
        pass

    @abstractmethod
    def compile_and_export(self):
        pass

    @abstractmethod
    def compile(self):
        pass



if __name__ == "__main__":
    main()


