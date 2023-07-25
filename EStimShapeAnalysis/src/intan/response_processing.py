from dataclasses import dataclass

from newga.multi_ga_db_util import MultiGaDbUtil


@dataclass
class ResponseProcessor:
    db_util: MultiGaDbUtil
    def process_to_db(self, ga_name: str) -> None:
        # Read unprocessed responses from database
        self.db_util.read_stims_with_no_driving_response()
        # Process responses
            # Group by channels
            # Average or sum

        # Write processed responses to database
        pass