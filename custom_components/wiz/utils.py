"""WiZ utils."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import aiofiles
from .pywizlight.bulblibrary import BulbType, BulbClass

from homeassistant.core import HomeAssistant

from const import DEFAULT_NAME

_LOGGER = logging.getLogger("Alfach")
_LOGGER.setLevel(logging.DEBUG)

STORAGE_KEY = "wiz_home_config"


def _short_mac(mac: str) -> str:
    """Get the short mac address from the full mac."""
    return mac.replace(":", "").upper()[-6:]


def name_from_bulb_type_and_mac(bulb_type: BulbType, mac: str) -> str:
    """Generate a name from bulb_type and mac."""
    if bulb_type.bulb_type == BulbClass.RGB:
        if bulb_type.white_channels == 2:
            description = "RGBWW Tunable"
        else:
            description = "RGBW Tunable"
    else:
        _LOGGER.debug(
            "Bulb type %s not recognized, using default description", bulb_type
        )
        description = "Random bulb lol"
    return f"{DEFAULT_NAME} {description} {_short_mac(mac)}"


async def build_full_bulb_name(
    hass: HomeAssistant, bulb_type: BulbType, mac_address: str
) -> str:
    """Create a string with bulb type and device name using the MAC address and bulb_type.

    Includes room name if WiZ home config is available.
    """
    device_name, room_name = await get_device_and_room_name_by_mac(hass, mac_address)

    if not device_name:
        # Fallback to bulb type name if device not found in config
        return name_from_bulb_type_and_mac(bulb_type, mac_address)

    # Build the name with room if available
    if room_name:
        full_device_name = f"{device_name} ({room_name})"
    else:
        full_device_name = device_name

    # Get bulb type string for additional info
    bulb_type_string = name_from_bulb_type_and_mac(bulb_type, mac_address)

    return f"{full_device_name} [{bulb_type_string}]"


async def get_device_and_room_name_by_mac(
    hass: HomeAssistant, mac_address: str
) -> tuple[str | None, str | None]:
    """Fetch the device name and room name from WiZ home config by MAC address.

    Returns (device_name, room_name) or (None, None) if not found.
    """
    try:
        # Try to find any stored WiZ home config
        wiz_config = await _load_wiz_home_config(hass)
        if not wiz_config:
            _LOGGER.debug("No WiZ home config found")
            return None, None

        # Find device by MAC address
        device = _find_device_by_mac(wiz_config, mac_address)
        if not device:
            _LOGGER.debug("Device with MAC %s not found in WiZ config", mac_address)
            return None, None

        device_name = device.get("name")
        room_name = None

        # Find room name if room_id exists
        room_id = device.get("room_id")
        if room_id:
            room = _find_room_by_id(wiz_config, room_id)
            if room:
                room_name = room.get("name")

        _LOGGER.debug("Found device: %s in room: %s", device_name, room_name)
        return device_name, room_name

    except Exception as ex:
        _LOGGER.error("Error fetching device info from WiZ config: %s", ex)
        return None, None


async def _load_wiz_home_config(hass: HomeAssistant) -> dict[Any, Any] | None:
    """Load WiZ home config from storage. Returns the first found config."""
    try:
        # Get all storage files to find WiZ configs
        storage_path = hass.config.path(".storage")

        if not os.path.exists(storage_path):
            return None

        # Look for any wiz_home_config files
        for filename in os.listdir(storage_path):
            if filename.startswith(f"{STORAGE_KEY}"):
                file_path = os.path.join(storage_path, filename)
                try:
                    async with aiofiles.open(file_path) as f:
                        content = await f.read()
                        storage_data: dict[Any, Any] = json.loads(content)
                        config_data = storage_data.get("data", {}).get("config")
                        if isinstance(config_data, dict):
                            _LOGGER.debug("Loaded WiZ config from %s", filename)
                            return config_data
                except (json.JSONDecodeError, KeyError) as ex:
                    _LOGGER.warning(
                        "Failed to load WiZ config from %s: %s", filename, ex
                    )
                    continue

        return None

    except Exception as ex:
        _LOGGER.error("Error loading WiZ home config: %s", ex)
        return None


def _find_device_by_mac(config: dict, mac_address: str) -> dict | None:
    """Find device in config by MAC address."""
    devices = config.get("devices", [])
    for device in devices:
        if device.get("mac_address", "").lower() == mac_address.lower():
            return device
    return None


def _find_room_by_id(config: dict, room_id: int) -> dict | None:
    """Find room in config by room ID."""
    rooms = config.get("rooms", [])
    for room in rooms:
        if room.get("room_id") == room_id:
            return room
    return None
