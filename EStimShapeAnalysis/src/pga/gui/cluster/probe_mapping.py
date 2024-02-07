from typing import Any

import numpy as np
from clat.intan.channels import Channel

from pga.gui.cluster.cluster_app_classes import ChannelMapper


class DBCChannelMapper(ChannelMapper):
    def __init__(self, headstage_label: str):
        self.channel_map = {}
        channel_numbers_top_to_bottom = [15, 16, 1, 30, 8, 23, 0, 31, 14, 17, 2, 29, 13, 18, 7, 24, 3, 28, 12, 19, 4, 27, 9, 22, 11, 20, 5, 26, 10, 21, 6, 25]
        channel_strings_top_to_bottom = [f"{headstage_label}-{num:03}" for num in channel_numbers_top_to_bottom]
        channels_top_to_bottom = [Channel[channel.replace("-", "_")] for channel in channel_strings_top_to_bottom]

        height = 2015
        for channel in channels_top_to_bottom:
            self.channel_map[channel] = np.array([0, height])
            height -= 65

    def get_coordinates(self, channel: Channel) -> dict[Any, np.ndarray]:
        return self.channel_map[channel]


def main():
    mapper = DBCChannelMapper("A")
    print(mapper.channel_map)


if __name__ == '__main__':
    main()