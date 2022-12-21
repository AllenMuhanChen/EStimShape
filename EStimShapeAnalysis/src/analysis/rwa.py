from collections import namedtuple

import pandas as pd


class Bins:
    def __init__(self, start, end, num_bins):
        self.num_bins = num_bins
        self.end = end
        self.start = start
        self._generate_bins()

    def _generate_bins(self):
        bin_size = (self.end - self.start) / self.num_bins

        # Initialize a list to hold the bin ranges
        bin_ranges = []

        # Iterate over the number of bins
        for i in range(self.num_bins):
            # Calculate the start and end of the bin range
            bin_start = self.start + i * bin_size
            bin_end = bin_start + bin_size
            bin_middle = (bin_start + bin_end) / 2

            # Add the bin range to the list
            BinRange = namedtuple('BinRange', 'start middle end')
            bin_range = BinRange(bin_start, bin_middle, bin_end)
            bin_ranges.append(bin_range)

        # Return the list of bin ranges
        self.bins = bin_ranges

    def assign_bin(self, value) -> (int, tuple):
        for i, bin_range in enumerate(self.bins):
            # Check if the value is within the current bin_range range
            if bin_range.start <= value < bin_range.end:
                # Return the current bin_range range
                return i, bin_range


def rwa(stim_df: pd.DataFrame, resp_vect: list[float], bins: Bins):
    pass
