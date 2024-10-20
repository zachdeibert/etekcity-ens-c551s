from __future__ import annotations
import asyncio
import contextlib
import types
from . import consts
from .async_queue import async_queue
from .protocol import protocol


class device(contextlib.AbstractAsyncContextManager["device"]):
    NEVER_TIMEOUT = 0

    __allowed_units: consts.allowed_unit
    __event: asyncio.Event
    __hardware_ver: str
    __is_connected: bool
    __is_stable: bool
    __proto: protocol
    __queue: async_queue
    __software_ver: str
    __timeout: int
    __unit: consts.unit
    __weight: float

    @property
    def allowed_units(self: device) -> consts.allowed_unit:
        return self.__allowed_units

    @allowed_units.setter
    def allowed_units(self: device, value: consts.allowed_unit) -> None:
        async def update() -> None:
            await self.__proto.set_allowed_units(value)
            self.__allowed_units = value

        self.__queue.queue(update())

    @property
    def hardware_ver(self: device) -> str:
        return self.__hardware_ver

    @property
    def is_connected(self: device) -> bool:
        return self.__is_connected

    @property
    def is_stable(self: device) -> bool:
        return self.__is_stable

    @property
    def software_ver(self: device) -> str:
        return self.__software_ver

    @property
    def timeout(self: device) -> int:
        return self.__timeout

    @timeout.setter
    def timeout(self: device, value: int) -> None:
        async def keepalive() -> None:
            await self.__proto.set_timeout(300)

        async def update() -> None:
            if value == device.NEVER_TIMEOUT:
                await keepalive()
                self.__queue.periodically(keepalive, 140.0)
            else:
                self.__queue.periodically(None, 0.0)
                await self.__proto.set_timeout(value)
                self.__timeout = value

        self.__queue.queue(update())

    @property
    def unit(self: device) -> consts.unit:
        return self.__unit

    @unit.setter
    def unit(self: device, value: consts.unit) -> None:
        async def update() -> None:
            await self.__proto.set_unit(value)
            self.__unit = value

        self.__queue.queue(update())

    @property
    def weight(self: device) -> float:
        return self.__weight

    def __init__(self: device, addr: str) -> None:
        super().__init__()
        self.__event = asyncio.Event()
        self.__proto = protocol(addr, self.__update)

    async def __aenter__(self: device) -> device:
        self.__queue = async_queue()
        await self.__proto.connect()
        self.__hardware_ver = await self.__proto.get_hw_rev()
        self.__software_ver = await self.__proto.get_sw_rev()
        await self.__proto.start_notify()
        await self.__proto.start()
        self.timeout = 30
        self.allowed_units = (
            consts.allowed_unit.ounce
            | consts.allowed_unit.pound_ounce
            | consts.allowed_unit.ounce_water
            | consts.allowed_unit.ounce_milk
            | consts.allowed_unit.gram
            | consts.allowed_unit.ml_water
            | consts.allowed_unit.ml_milk
        )
        await self.wait()
        return self

    async def __aexit__(
        self: device,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: types.TracebackType | None,
    ) -> None:
        await self.__queue.close()
        await self.__proto.disconnect()
        del (
            self.__allowed_units,
            self.__hardware_ver,
            self.__is_connected,
            self.__is_stable,
            self.__queue,
            self.__software_ver,
            self.__timeout,
            self.__unit,
            self.__weight,
        )

    def __update(self: device, state: protocol.state) -> None:
        self.__is_connected = state.connected
        self.__is_stable = state.stable
        self.__unit = state.unit
        self.__weight = state.weight
        self.__event.set()

    def tare(self: device) -> None:
        self.__queue.queue(self.__proto.tare())

    async def wait(self: device) -> None:
        await self.__event.wait()
        self.__event.clear()
