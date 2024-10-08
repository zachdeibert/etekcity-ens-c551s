from __future__ import annotations
import bleak
import bleak.backends.characteristic
import contextlib
import struct
import sys
import types
import typing
from . import consts
from .weight import sign, unit, weight


class device(contextlib.AbstractAsyncContextManager["device"]):
    __client: bleak.BleakClient

    @property
    async def hardware_ver(self: device) -> str:
        return (
            await self.__client.read_gatt_char(  # pyright: ignore[reportUnknownMemberType]
                consts.CHAR_HW_REV
            )
        ).decode()

    @property
    async def software_ver(self: device) -> str:
        return (
            await self.__client.read_gatt_char(  # pyright: ignore[reportUnknownMemberType]
                consts.CHAR_SW_REV
            )
        ).decode()

    def __init__(self: device, addr: str) -> None:
        super().__init__()
        self.__client = bleak.BleakClient(addr)

    async def __aenter__(self: device) -> device:
        await self.__client.connect()  # pyright: ignore[reportUnknownMemberType]
        return self

    async def __aexit__(
        self: device,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: types.TracebackType | None,
    ) -> None:
        await self.__client.disconnect()

    async def start(
        self: device,
        callback: typing.Callable[[weight], typing.Coroutine[None, None, None]],
    ) -> None:
        async def handler(
            char: bleak.backends.characteristic.BleakGATTCharacteristic, data: bytearray
        ) -> None:
            (id,) = struct.unpack_from("<H", data, 7)
            if id == consts.CMD_SLEEP:
                pass
            elif id == consts.CMD_UNIT_CHANGE:
                pass
            elif id == consts.CMD_WEIGHT:
                sign_, weight_, unit_, stable_ = struct.unpack_from("<BHH?", data, 10)
                if unit_ in (unit.gram.value, unit.ml_water.value, unit.ml_milk.value):
                    weight_ /= 10
                else:
                    weight_ /= 100
                await callback(weight(sign(sign_), weight_, unit(unit_), stable_))
            elif id == consts.CMD_WEIGHT_CHANGE:
                pass
            elif True:
                print(f"Unknown packet ID {id:04X}: {data.hex(' ')}", file=sys.stderr)

        await self.__client.start_notify(  # pyright: ignore[reportUnknownMemberType]
            consts.CHAR_RX, handler
        )
        await self.__client.write_gatt_char(
            consts.CHAR_TX, struct.pack("<H", consts.CMD_WEIGHT)
        )

    async def stop(self: device) -> None:
        await self.__client.stop_notify(consts.CHAR_RX)
