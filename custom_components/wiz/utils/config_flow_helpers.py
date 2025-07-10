"""Config flow helpers for WiZ Platform."""

from __future__ import annotations

import logging
from typing import Any

from pywizlight import wizlight
from pywizlight.discovery import DiscoveredBulb
from pywizlight.exceptions import WizLightConnectionError, WizLightTimeOutError

from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.util.network import is_ip_address

from ..const import DEFAULT_NAME, WIZ_CONNECT_EXCEPTIONS, WIZ_HOME_LINK
from .utils import _short_mac, build_full_bulb_name

_LOGGER = logging.getLogger(__name__)


async def async_validate_and_connect_bulb(
    host: str,
) -> tuple[str | None, str | None, dict[str, str]]:
    """Validate and connect to bulb. Returns (bulbtype, mac, errors)."""
    errors = {}

    if not host:
        errors[CONF_HOST] = "host_required"
    elif not is_ip_address(host):
        errors[CONF_HOST] = "no_ip"
    else:
        try:
            bulb = wizlight(host)
            bulbtype = await bulb.get_bulbtype()
            mac = await bulb.getMac()
        except WizLightConnectionError as ex:
            _LOGGER.error("Failed to connect to bulb at %s: %s", host, ex)
            errors["base"] = "cannot_connect"
        except WizLightTimeOutError as ex:
            _LOGGER.error("Connection to bulb at %s timed out: %s", host, ex)
            errors["base"] = "bulb_time_out"
        except (OSError, ConnectionRefusedError) as ex:
            _LOGGER.error(
                "Connection error while connecting to bulb at %s: %s", host, ex
            )
            errors["base"] = "cannot_connect"
        else:
            return bulbtype, mac, {}

    return None, None, errors


def get_wiz_home_link_from_entries(entries: list[Any]) -> str | None:
    """Get WiZ home link from existing entries."""
    for entry in entries:
        if WIZ_HOME_LINK in entry.data:
            return entry.data[WIZ_HOME_LINK]
    return None


def format_discovered_devices(
    discovered_devices: dict[str, DiscoveredBulb],
    current_unique_ids: set[str],
    current_hosts: set[str],
) -> dict[str, str]:
    """Format discovered devices for display in config flow."""
    return {
        mac: f"{DEFAULT_NAME} {_short_mac(mac)} ({device.ip_address})"
        for mac, device in discovered_devices.items()
        if mac not in current_unique_ids and device.ip_address not in current_hosts
    }


async def async_create_bulb_entry_data(
    hass: HomeAssistant,
    host: str,
    bulbtype: str,
    mac: str,
    wiz_home_link: str | None = None,
) -> tuple[str, dict[str, str]]:
    """Create bulb entry data. Returns (title, data)."""
    data = {CONF_HOST: host}
    if wiz_home_link:
        data[WIZ_HOME_LINK] = wiz_home_link

    title = await build_full_bulb_name(hass, bulbtype, mac)
    return title, data


def validate_wiz_home_link(link: str) -> bool:
    """Validate WiZ home link format."""
    return link.startswith("https://wiz-s3-local-integration-dev-artifacts")


async def async_update_existing_device_names(self) -> None:
    """Update names of existing devices when Wiz home config is added."""
    for entry in self._async_current_entries(include_ignore=False):
        # Skip if this entry already has a Wiz home link
        if WIZ_HOME_LINK in entry.data:
            continue

        mac_address = entry.unique_id

        # Skip if this entry already has a host
        host = entry.data.get(CONF_HOST)
        if not host:
            continue

        try:
            bulb = wizlight(host)
            bulbtype = await bulb.get_bulbtype()

            new_title = await build_full_bulb_name(self.hass, bulbtype, mac_address)

            # Update entry if name has changed
            if new_title != entry.title:
                _LOGGER.debug(
                    "Updating device name from '%s' to '%s'",
                    entry.title,
                    new_title,
                )
                self.hass.config_entries.async_update_entry(entry, title=new_title)
            else:
                _LOGGER.debug("Device name unchanged for %s", entry.title)

        except WIZ_CONNECT_EXCEPTIONS as ex:
            _LOGGER.debug(
                "Failed to connect to device %s during name update: %s",
                host,
                ex,
            )
            continue
        except Exception as ex:  # noqa: BLE001
            _LOGGER.error(
                "Unexpected error updating device name for %s: %s",
                entry.title,
                ex,
            )
            continue
