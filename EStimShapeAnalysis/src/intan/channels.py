from enum import Enum


class Channel(Enum):
    pass


for letter in 'ABCD':
    for number in range(32):
        enum_name = f"{letter}_{number:03}"
        channel_id = f"{letter}-{number:03}"
        setattr(Channel, enum_name, channel_id)
