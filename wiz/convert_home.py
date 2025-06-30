from dataclasses import dataclass, field
import json
from typing import Any

import aiohttp


@dataclass
class DeviceTraits:
    """Represents the traits of a device, including its capabilities and features."""

    is_dimmable: bool
    is_tunable_white: bool
    white_range: list[int]
    is_tunable_color: bool
    supports_light_mode: bool

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "DeviceTraits":
        """Create a DeviceTraits instance from a dictionary.

        Args:
            data (dict): Dictionary containing device traits.

        Returns:
            DeviceTraits: An instance of DeviceTraits populated with the provided data.

        """
        return DeviceTraits(
            is_dimmable=data.get("is_dimmable", False),
            is_tunable_white=data.get("is_tunable_white", False),
            white_range=list(data.get("white_range", [])),
            is_tunable_color=data.get("is_tunable_color", False),
            supports_light_mode=data.get("supports_light_mode", False),
        )


@dataclass
class Device:
    """Represents a device in the WiZ ecosystem."""

    device_id: int
    type: str
    room_id: int
    group_id: int | None
    name: str
    mac_address: str
    fw_version: str
    traits: DeviceTraits
    creation_date: str
    update_date: str

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Device":
        """Create a Device instance from a dictionary.

        Args:
            data (dict): Dictionary containing device information.

        Returns:
            Device: An instance of Device populated with the provided data.

        """
        return Device(
            device_id=data["device_id"],
            type=data["type"],
            room_id=data["room_id"],
            group_id=data.get("group_id"),
            name=data["name"],
            mac_address=data["mac_address"],
            fw_version=data["fw_version"],
            traits=DeviceTraits.from_dict(data["traits"]),
            creation_date=data["creation_date"],
            update_date=data["update_date"],
        )


@dataclass
class Room:
    """Represents a room in the WiZ ecosystem."""

    room_id: int
    name: str
    type: str
    creation_date: str
    update_date: str

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Room":
        """Create a Room instance from a dictionary.

        Args:
            data (dict): Dictionary containing room information.

        Returns:
            Room: An instance of Room populated with the provided data.

        """
        return Room(
            room_id=data["room_id"],
            name=data["name"],
            type=data["type"],
            creation_date=data["creation_date"],
            update_date=data["update_date"],
        )


@dataclass
class WiZHome:
    """Represents a WiZ home, including its rooms and devices."""

    name: str
    home_id: int
    region: str
    udp_signing_key: str
    version: str
    creation_date: str
    update_date: str
    rooms: list[Room] = field(default_factory=list)
    devices: list[Device] = field(default_factory=list)

    @staticmethod
    async def fetch_json(url: str) -> dict[Any, Any]:
        """Asynchronously fetch JSON data from a URL.

        Args:
            url (str): The URL to fetch the JSON data from.

        Returns:
            dict: Parsed JSON data.

        """
        async with aiohttp.ClientSession() as session:
            resp = await session.get(url)
            resp.raise_for_status()
            text = await resp.text()  # Read as text, not as JSON
            return json.loads(text)  # Parse the text as JSON

    @staticmethod
    def parse_json(data: dict[str, Any]) -> "WiZHome":
        """Parse JSON data and create a WiZHome instance.

        Args:
            data (dict): Dictionary containing WiZ home information.

        Returns:
            WiZHome: An instance of WiZHome populated with the provided data.

        """
        return WiZHome(
            name=data["name"],
            home_id=data["home_id"],
            region=data["region"],
            udp_signing_key=data["udp_signing_key"],
            version=data["version"],
            creation_date=data["creation_date"],
            update_date=data["update_date"],
            rooms=[Room.from_dict(room) for room in data.get("rooms", [])],
            devices=[Device.from_dict(dev) for dev in data.get("devices", [])],
        )
