import argparse
import asyncio
import ens_c551s
import sys
from . import utils


async def connect(addr: str) -> None:
    print(f"Connecting to {addr}...", file=sys.stderr)
    async with ens_c551s.device(addr) as dev:
        print(f"Hardware revision = {dev.hardware_ver}", file=sys.stderr)
        print(f"Software revision = {dev.software_ver}", file=sys.stderr)

        while dev.is_connected:
            print(dev.weight)
            try:
                await asyncio.sleep(1)
            except asyncio.exceptions.CancelledError:
                break


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="example ENS-C551S program")
    parser.add_argument(
        "addr",
        nargs="?",
        type=utils.ble_mac,
        help="the BLE MAC address of the scale to connect to",
        metavar="XX:XX:XX:XX:XX:XX",
    )
    parsed = parser.parse_args()

    if parsed.addr is None:
        asyncio.run(utils.scan())
    else:
        asyncio.run(connect(parsed.addr))
