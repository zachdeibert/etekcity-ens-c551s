import enum


class allowed_unit(enum.Flag):
    ounce = 0x01
    pound_ounce = 0x02
    ounce_water = 0x04
    ounce_milk = 0x08
    gram = 0x10
    ml_water = 0x20
    ml_milk = 0x40


class command(enum.Enum):
    enable_units = 0x4102
    sleep = 0xA001
    set_timeout = 0xA104
    set_unit = 0xA180
    weight = 0xA183
    power_on = 0xA184
    tare = 0xA185


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


ADV_MANUFACTURER_ID = 0x06D0
ADV_MANUFACTURER_DATA = b"\x01\x07\x98\x41\x00\x4D\xD0\x02\x01"

CHAR_HW_REV = "2A27"
CHAR_SW_REV = "2A28"
CHAR_TX = "FFF2"
CHAR_RX = "FFF1"

MAGIC_HEADER = b"\xA5\x22"

UNIT_PRECISION = {
    unit.ounce: 100,
    unit.pound_once: 100,
    unit.gram: 10,
    unit.ml_water: 10,
    unit.ounce_water: 100,
    unit.ml_milk: 10,
    unit.ounce_milk: 100,
}
