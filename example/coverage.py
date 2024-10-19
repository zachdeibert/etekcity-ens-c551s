import argparse
import asyncio
import ens_c551s
import sys
from . import utils


async def wait(prompt: str) -> None:
    print(prompt, end="", flush=True)
    await asyncio.sleep(0.1)
    sys.stdin.readline()


async def test(addr: str) -> None:
    print(f"Connecting to {addr}...", file=sys.stderr)
    async with ens_c551s.device(addr) as dev:
        all = dev.allowed_units
        await wait("All units should be enabled")
        dev.allowed_units = ens_c551s.allowed_unit.gram
        await wait("Only grams should be enabled")
        dev.allowed_units = (
            ens_c551s.allowed_unit.ounce_water
            | ens_c551s.allowed_unit.ounce_milk
            | ens_c551s.allowed_unit.ml_water
            | ens_c551s.allowed_unit.ml_milk
        )
        await wait("Only fluid units should be enabled")
        dev.allowed_units ^= all
        await wait("No fluid units should be enabled")
        dev.allowed_units = all

        await wait("Apply varying load to scale")
        await dev.wait()
        await dev.wait()
        while not dev.is_stable:
            await dev.wait()
        print("Scale stabilized")

        for unit in ens_c551s.unit:
            dev.unit = unit
            await wait(f"Units should be {unit.name}")
        await wait("Change the scale units")
        await dev.wait()
        await dev.wait()
        print(f"New units: {dev.unit.name}")

        dev.tare()
        await wait("Scale should have just tared")

        dev.timeout = 45
        print("Scale should turn off in 45 seconds...")
        await asyncio.sleep(30)
        print("Scale should turn off in 15 seconds...")
        await asyncio.sleep(5)
        for i in range(10):
            print(f"Scale should turn off in {10 - i} seconds...")
            await asyncio.sleep(1)
        print("Scale should have just turned off.")
        await asyncio.sleep(3)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="example ENS-C551S program to cover all supported functionality"
    )
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
        asyncio.run(test(parsed.addr))
