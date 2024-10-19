import ens_c551s
import re

ADDR_FORMAT = re.compile("^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$")


def ble_mac(addr: str) -> str:
    if ADDR_FORMAT.match(addr):
        return addr
    raise ValueError(f"Invalid BLE MAC address '{addr}'")


async def scan() -> None:
    print("Scanning for Etekcity ENS-C551S smart kitchen scales...")
    async for addr in ens_c551s.scan():
        print(addr)
