from __future__ import annotations
import argparse
import asyncio
import bleak
import ens_c551s
import getpass
import json
import keyring
import paho.mqtt.client
import re
import typing
from . import utils


class mqtt_addr:
    __FORMAT = re.compile("^(?:([^:]+)://)?(?:([^@]+)@)?([^:]+)(?::([0-9]+))?/(.+)$")
    __PROTOCOLS: dict[str, tuple[typing.Literal["tcp", "websockets", "unix"], bool]] = {
        "file": ("unix", False),
        "files": ("unix", True),
        "tcp": ("tcp", False),
        "tcps": ("tcp", True),
        "ws": ("websockets", False),
        "wss": ("websockets", True),
    }

    __hostname: str
    __port: int
    __prefix: str
    __protocol: typing.Literal["tcp", "websockets", "unix"]
    __tls: bool
    __user: str

    @property
    def hostname(self: mqtt_addr) -> str:
        return self.__hostname

    @property
    def port(self: mqtt_addr) -> int:
        return self.__port

    @property
    def prefix(self: mqtt_addr) -> str:
        return self.__prefix

    @property
    def protocol(self: mqtt_addr) -> typing.Literal["tcp", "websockets", "unix"]:
        return self.__protocol

    @property
    def tls(self: mqtt_addr) -> bool:
        return self.__tls

    @property
    def user(self: mqtt_addr) -> str:
        return self.__user

    def __init__(self: mqtt_addr, addr: str) -> None:
        match = mqtt_addr.__FORMAT.match(addr)
        if match is None:
            raise ValueError(
                "MQTT address should be of the form [<proto>://][<user>@]<hostname>[:<port>]/<discovery prefix>"
            )
        self.__hostname = match.group(3)
        group = match.group(4)
        if group is None:
            self.__port = 1883
        else:
            self.__port = int(group)
        self.__prefix = match.group(5)
        group = match.group(1)
        if group is None:
            self.__protocol = "tcp"
            self.__tls = False
        else:
            self.__protocol, self.__tls = mqtt_addr.__PROTOCOLS[group]
        group = match.group(2)
        if group is None:
            self.__user = getpass.getuser()
        else:
            self.__user = group


async def run(mqtt_addr: mqtt_addr, mqtt_ca: str | None, ble_addr: str) -> None:
    ble_addr = ble_addr.upper()
    ble_addr_hex = ble_addr.replace(":", "")
    object_id = f"ENS-C551S_{ble_addr_hex}"
    mqtt = paho.mqtt.client.Client(
        paho.mqtt.client.CallbackAPIVersion.VERSION2,  # pyright: ignore[reportPrivateImportUsage]
        object_id,
        transport=mqtt_addr.protocol,
    )
    if mqtt_addr.tls:
        if mqtt_ca is None:
            mqtt.tls_insecure_set(True)
        else:
            mqtt.tls_set(mqtt_ca)  # pyright: ignore[reportUnknownMemberType]
    keyring_service = f"{mqtt_addr.protocol}://{mqtt_addr.hostname}:{mqtt_addr.port}"
    password = keyring.get_password(keyring_service, mqtt_addr.user)
    if password is None:
        password = getpass.getpass(
            f"Password for {mqtt_addr.protocol}://{mqtt_addr.user}@{mqtt_addr.hostname}:{mqtt_addr.port}: "
        )
        keyring.set_password(keyring_service, mqtt_addr.user, password)
    mqtt.username_pw_set(mqtt_addr.user, password)
    mqtt.will_set(f"{mqtt_addr.prefix}/{object_id}/availability", b"offline", 1, True)
    mqtt.connect(mqtt_addr.hostname, mqtt_addr.port)
    try:
        mqtt.loop_start()
        print("Connected to MQTT.")
        mqtt.publish(
            f"{mqtt_addr.prefix}/{object_id}/availability", b"offline", 1, True
        )
        async with ens_c551s.device(ble_addr) as dev:
            dev.timeout = ens_c551s.device.NEVER_TIMEOUT
            print("Connected to ENS-C551S.")
            try:
                base_config: dict[str, typing.Any] = {
                    "availability_topic": f"{mqtt_addr.prefix}/{object_id}/availability",
                    "device": {
                        "connections": [["mac", ble_addr]],
                        "hw_version": dev.hardware_ver,
                        "manufacturer": "Etekcity",
                        "model": "ENS-C551S",
                        "name": "Etekcity Nutrition Scale",
                        "sw_version": dev.software_ver,
                    },
                    "icon": "mdi:scale",
                    "origin": {
                        "name": "Etekcity ENS-C551S Library",
                        "support_url": "https://github.com/zachdeibert/etekcity-ens-c551s/issues",
                        "sw_version": "0.1.0",
                    },
                }
                mqtt.publish(
                    f"{mqtt_addr.prefix}/button/{object_id}/config",
                    json.dumps(
                        {
                            **base_config,
                            "command_topic": f"{mqtt_addr.prefix}/button/{object_id}/command",
                            "name": "Tare",
                            "unique_id": f"2A76D837-A343-4E55-91F8-{ble_addr_hex}",
                        }
                    ).encode(),
                    1,
                    True,
                )
                mqtt.publish(
                    f"{mqtt_addr.prefix}/sensor/{object_id}/config",
                    json.dumps(
                        {
                            **base_config,
                            "device_class": "weight",
                            "name": "Weight",
                            "qos": 1,
                            "state_class": "measurement",
                            "state_topic": f"{mqtt_addr.prefix}/sensor/{object_id}/state",
                            "unique_id": f"45D499DB-C80C-4FB8-9D50-{ble_addr_hex}",
                            "unit_of_measurement": "gram",
                        }
                    ).encode(),
                    1,
                    True,
                )
                mqtt.publish(
                    f"{mqtt_addr.prefix}/{object_id}/availability", b"online", 1, True
                )

                def on_message(
                    client: paho.mqtt.client.Client,
                    userdata: None,
                    message: paho.mqtt.client.MQTTMessage,
                ) -> None:
                    if (
                        message.topic
                        == f"{mqtt_addr.prefix}/button/{object_id}/command"
                        and message.payload == b"PRESS"
                    ):
                        dev.tare()

                mqtt.on_message = on_message
                mqtt.subscribe(f"{mqtt_addr.prefix}/button/{object_id}/command")
                while True:
                    if not dev.is_connected:
                        print("ENS-C551S disconnected.")
                        break
                    try:
                        await dev.wait()
                    except asyncio.exceptions.CancelledError:
                        break
                    if not mqtt.is_connected():
                        print("MQTT disconnected.")
                        break
                    mqtt.publish(
                        f"{mqtt_addr.prefix}/sensor/{object_id}/state",
                        str(dev.weight).encode(),
                        1 if dev.is_stable else 0,
                    )
            finally:
                dev.timeout = 30
    except bleak.exc.BleakError as exc:
        if exc.args != ("Not connected",):
            raise
    finally:
        mqtt.publish(
            f"{mqtt_addr.prefix}/{object_id}/availability", b"offline", 1, True
        )
        mqtt.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="connect ENS-C551S to MQTT server")
    parser.add_argument(
        "--ca", help="the root certificate for the MQTT server", metavar="ca.crt"
    )
    parser.add_argument(
        "--mqtt",
        default=mqtt_addr("127.0.0.1/homeassistant"),
        type=mqtt_addr,
        help="the address of the MQTT server to connect to",
        metavar="[<proto>://][<user>@]<hostname>[:<port>]/<discovery prefix>",
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
        asyncio.run(run(parsed.mqtt, parsed.ca, parsed.addr))
