from enum import Enum


class RegimeType(Enum):
    REGIME_ZERO = "REGIME_ZERO"
    REGIME_ONE = "REGIME_ONE"
    REGIME_TWO = "REGIME_TWO"
    REGIME_THREE = "REGIME_THREE"

    def to_index(self):
        if self == RegimeType.REGIME_ZERO:
            return 0
        elif self == RegimeType.REGIME_ONE:
            return 1
        elif self == RegimeType.REGIME_TWO:
            return 2
        elif self == RegimeType.REGIME_THREE:
            return 3

    @staticmethod
    def from_index(index: int):
        if index == 0:
            return RegimeType.REGIME_ZERO
        elif index == 1:
            return RegimeType.REGIME_ONE
        elif index == 2:
            return RegimeType.REGIME_TWO
        elif index == 3:
            return RegimeType.REGIME_THREE
