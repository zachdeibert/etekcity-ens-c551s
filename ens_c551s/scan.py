import bleak
import time
import typing
from . import consts


async def scan(timeout: float = 10.0) -> typing.AsyncGenerator[str, None]:
    deadline = time.time() + timeout
    seen: set[str] = set()
    async with bleak.BleakScanner() as scanner:
        async for dev, adv in scanner.advertisement_data():
            if dev.address not in seen:
                seen.add(dev.address)
                if adv.manufacturer_data == {
                    consts.ADV_MANUFACTURER_ID: consts.ADV_MANUFACTURER_DATA
                }:
                    yield dev.address
            if time.time() >= deadline:
                break
