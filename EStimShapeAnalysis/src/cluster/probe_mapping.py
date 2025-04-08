from typing import Any

import numpy as np
from clat.intan.channels import Channel

from src.cluster.cluster_app_classes import ChannelMapper


class DBCChannelMapper(ChannelMapper):
    def __init__(self, headstage_label: str):
        # channel_numbers_top_to_bottom = [15, 16, 1, 30, 8, 23, 0, 31, 14, 17, 2, 29, 13, 18, 7, 24, 3, 28, 12, 19, 4, 27, 9, 22, 11, 20, 5, 26, 10, 21, 6, 25]
        channel_numbers_top_to_bottom = [7, 8, 25, 22, 0, 15, 24, 23, 6, 9, 26, 21, 5, 10, 31, 16, 27, 20, 4, 11, 28, 19, 1, 14, 3, 12, 29, 18, 2, 13, 30, 17]
        channel_strings_top_to_bottom = [f"{headstage_label}-{num:03}" for num in channel_numbers_top_to_bottom]
        self.channels_top_to_bottom = [Channel[channel.replace("-", "_")] for channel in channel_strings_top_to_bottom]
        self.channel_map = {}

        height = 2015
        for channel in self.channels_top_to_bottom:
            self.channel_map[channel] = np.array([0, height])
            height -= 65

    def get_coordinates(self, channel: Channel) -> dict[Any, np.ndarray]:
        return self.channel_map[channel]


def main():
    mapper = DBCChannelMapper("A")
    print(mapper.channel_map)


if __name__ == '__main__':
    main()