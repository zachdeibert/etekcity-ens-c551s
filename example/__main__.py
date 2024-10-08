import argparse
import asyncio
import ens_c551s
import re
import sys

ADDR_FORMAT = re.compile("^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$")


def ble_mac(addr: str) -> str:
    if ADDR_FORMAT.match(addr):
        return addr
    raise ValueError(f"Invalid BLE MAC address '{addr}'")


async def scan() -> None:
    print("Scanning for Etekcity ENS-C551S smart kitchen scales...")
    async for addr in ens_c551s.scan():
        print(addr)


async def connect(addr: str) -> None:
    print(f"Connecting to {addr}...", file=sys.stderr)
    async with ens_c551s.device(addr) as dev:
        print(f"Hardware revision = {await dev.hardware_ver}", file=sys.stderr)
        print(f"Software revision = {await dev.software_ver}", file=sys.stderr)

        async def handler(weight: ens_c551s.weight) -> None:
            print(weight.grams)

        await dev.start(handler)
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.exceptions.CancelledError:
            await dev.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="example ENS-C551S program")
    parser.add_argument(
        "addr",
        nargs="?",
        type=ble_mac,
        help="the BLE MAC address of the scale to connect to",
        metavar="XX:XX:XX:XX:XX:XX",
    )
    parsed = parser.parse_args()

    if parsed.addr is None:
        asyncio.run(scan())
    else:
        asyncio.run(connect(parsed.addr))
