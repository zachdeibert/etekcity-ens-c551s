from __future__ import annotations
import enum
import typing


class sign(enum.Enum):
    positive = 0
    negative = 1


class unit(enum.Enum):
    ounce = 0
    pound_once = 1
    gram = 2
    ml_water = 259
    ounce_water = 260
    ml_milk = 515
    ounce_milk = 516


UNIT_CALIBRATION: dict[unit, float] = {
    unit.ounce: 176.35,
    unit.pound_once: 176.35,
    unit.gram: 5000.0,
    unit.ml_water: 5000.0,
    unit.ounce_water: 169.1,
    unit.ml_milk: 4854.0,
    unit.ounce_milk: 164.1,
}


class weight(typing.NamedTuple):
    sign: sign
    weight: float
    unit: unit
    stable: bool

    @property
    def grams(self: weight) -> float:
        weight = self.weight
        if self.sign == sign.negative:
            weight = -weight
        return weight * UNIT_CALIBRATION[unit.gram] / UNIT_CALIBRATION[self.unit]
