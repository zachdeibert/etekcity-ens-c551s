from __future__ import annotations
import bleak
import bleak.backends.characteristic
import struct
import typing
from . import consts

UNIT_CALIBRATION: dict[consts.unit, float] = {
    consts.unit.ounce: 176.35,
    consts.unit.pound_once: 176.35,
    consts.unit.gram: 5000.0,
    consts.unit.ml_water: 5000.0,
    consts.unit.ounce_water: 169.1,
    consts.unit.ml_milk: 4854.0,
    consts.unit.ounce_milk: 164.1,
}


class protocol:
    class state(typing.NamedTuple):
        stable: bool
        unit: consts.unit
        weight: float

    __callback: typing.Callable[[state], None]
    __client: bleak.BleakClient
    __seq: int

    def __init__(
        self: protocol, addr: str, callback: typing.Callable[[state], None]
    ) -> None:
        self.__callback = callback
        self.__client = bleak.BleakClient(addr)
        self.__seq = 1

    async def connect(self: protocol) -> None:
        await self.__client.connect()  # pyright: ignore[reportUnknownMemberType]

    async def disconnect(self: protocol) -> None:
        await self.__client.disconnect()

    async def get_hw_rev(self: protocol) -> str:
        return (
            await self.__client.read_gatt_char(  # pyright: ignore[reportUnknownMemberType]
                consts.CHAR_HW_REV
            )
        ).decode()

    async def get_sw_rev(self: protocol) -> str:
        return (
            await self.__client.read_gatt_char(  # pyright: ignore[reportUnknownMemberType]
                consts.CHAR_SW_REV
            )
        ).decode()

    async def set_allowed_units(self: protocol, units: consts.allowed_unit) -> None:
        await self.__tx(consts.command.enable_units, "<H", units.value)

    async def set_timeout(self: protocol, seconds: int) -> None:
        await self.__tx(consts.command.set_timeout, "<H", seconds)

    async def set_unit(self: protocol, unit: consts.unit) -> None:
        await self.__tx(consts.command.set_unit, "<H", unit.value)

    async def start(self: protocol) -> None:
        await self.__tx(consts.command.power_on)

    async def start_notify(self: protocol) -> None:
        await self.__client.start_notify(  # pyright: ignore[reportUnknownMemberType]
            consts.CHAR_RX, self.__rx
        )

    async def tare(self: protocol) -> None:
        await self.__tx(consts.command.tare)

    async def __rx(
        self: protocol,
        char: bleak.backends.characteristic.BleakGATTCharacteristic,
        data: bytearray,
    ) -> None:
        (id,) = struct.unpack_from("<H", data, 7)
        if id == consts.command.sleep.value:
            await self.__client.disconnect()
        elif id == consts.command.weight.value:
            sign, weight, unit, stable = struct.unpack_from("<BHH?", data, 10)
            unit = consts.unit(unit)
            weight /= consts.UNIT_PRECISION[unit]
            if sign == consts.sign.negative.value:
                weight = -weight
            weight *= UNIT_CALIBRATION[consts.unit.gram] / UNIT_CALIBRATION[unit]
            self.__callback(protocol.state(stable, unit, weight))

    async def __tx(
        self: protocol, cmd: consts.command, format: str = "", *values: int
    ) -> None:
        payload = struct.pack(format, *values)
        pkt = bytearray(
            consts.MAGIC_HEADER
            + struct.pack("<BHxBHx", self.__seq, len(payload) + 4, 1, cmd.value)
            + payload
        )
        pkt[5] = 0xFF - (sum(pkt) % 0x100)
        await self.__client.write_gatt_char(consts.CHAR_TX, pkt)
        self.__seq += 1
