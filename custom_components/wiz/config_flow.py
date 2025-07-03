"""Config flow for WiZ Platform."""

from __future__ import annotations

import logging
from typing import Any

from pywizlight.bulb import wizlight
from pywizlight.discovery import DiscoveredBulb
import voluptuous as vol

from homeassistant.components import onboarding
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST
from homeassistant.data_entry_flow import AbortFlow
from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo
from homeassistant.util.network import is_ip_address

from .const import (
    DEFAULT_NAME,
    DISCOVER_SCAN_TIMEOUT,
    DOMAIN,
    WIZ_CONNECT_EXCEPTIONS,
    WizLightConnectionError,
    WizLightTimeOutError,
)
from .discovery import async_discover_devices
from .utils import _short_mac, name_from_bulb_type_and_mac

_LOGGER = logging.getLogger(__name__)

CONF_DEVICE = "device"


class WizConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for WiZ."""

    VERSION = 2

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovered_device: DiscoveredBulb | None = None
        self._discovered_devices: dict[str, DiscoveredBulb] = {}
        self._name: str = ""

    async def async_step_dhcp(
        self, discovery_info: DhcpServiceInfo
    ) -> ConfigFlowResult:
        """Handle DHCP discovery."""
        self._discovered_device = DiscoveredBulb(
            discovery_info.ip, discovery_info.macaddress
        )
        return await self._async_handle_discovery()

    async def async_step_integration_discovery(
        self, discovery_info: dict[str, str]
    ) -> ConfigFlowResult:
        """Handle integration discovery."""
        self._discovered_device = DiscoveredBulb(
            discovery_info["ip_address"], discovery_info["mac_address"]
        )
        return await self._async_handle_discovery()

    async def _async_handle_discovery(self) -> ConfigFlowResult:
        """Handle any discovery."""
        if self._discovered_device is None:
            return self.async_abort(reason="no_device_found")

        device = self._discovered_device
        ip_address = device.ip_address
        mac = device.mac_address

        await self.async_set_unique_id(mac)
        self._abort_if_unique_id_configured(updates={CONF_HOST: ip_address})

        try:
            bulb = wizlight(ip_address)
            bulbtype = await bulb.get_bulbtype()
            self._name = name_from_bulb_type_and_mac(bulbtype, mac)
        except WIZ_CONNECT_EXCEPTIONS as ex:
            _LOGGER.debug(
                "Failed to connect to discovered device at %s: %s", ip_address, ex
            )
            raise AbortFlow("cannot_connect") from ex

        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm discovery."""
        if self._discovered_device is None:
            return self.async_abort(reason="no_device_found")

        if user_input is not None or not onboarding.async_is_onboarded(self.hass):
            ip_address = self._discovered_device.ip_address
            return self.async_create_entry(
                title=self._name,
                data={CONF_HOST: ip_address},
            )

        self._set_confirm_only()
        placeholders = {"name": self._name, "host": self._discovered_device.ip_address}
        self.context["title_placeholders"] = placeholders
        return self.async_show_form(
            step_id="discovery_confirm",
            description_placeholders=placeholders,
        )

    async def async_step_pick_device(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the step to pick discovered device."""
        if user_input is not None:
            device = self._discovered_devices[user_input[CONF_DEVICE]]
            await self.async_set_unique_id(device.mac_address, raise_on_progress=False)

            try:
                bulb = wizlight(device.ip_address)
                bulbtype = await bulb.get_bulbtype()
            except WIZ_CONNECT_EXCEPTIONS:
                return self.async_abort(reason="cannot_connect")

            return self.async_create_entry(
                title=name_from_bulb_type_and_mac(bulbtype, device.mac_address),
                data={CONF_HOST: device.ip_address},
            )

        current_unique_ids = self._async_current_ids()
        current_hosts = {
            entry.data[CONF_HOST]
            for entry in self._async_current_entries(include_ignore=False)
        }

        discovered_devices = await async_discover_devices(
            self.hass, DISCOVER_SCAN_TIMEOUT
        )
        self._discovered_devices = {
            device.mac_address: device for device in discovered_devices
        }

        devices_name = {
            mac: f"{DEFAULT_NAME} {_short_mac(mac)} ({device.ip_address})"
            for mac, device in self._discovered_devices.items()
            if mac not in current_unique_ids and device.ip_address not in current_hosts
        }

        if not devices_name:
            return self.async_abort(reason="no_devices_found")

        return self.async_show_form(
            step_id="pick_device",
            data_schema=vol.Schema({vol.Required(CONF_DEVICE): vol.In(devices_name)}),
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initialized by the user."""
        errors = {}

        if user_input is not None:
            host = user_input.get(CONF_HOST, "").strip()

            # If no host provided, go to discovery
            if not host:
                return await self.async_step_pick_device()

            # Validate IP address
            if not is_ip_address(host):
                errors["base"] = "no_ip"
            else:
                try:
                    bulb = wizlight(host)
                    bulbtype = await bulb.get_bulbtype()
                    mac = await bulb.getMac()
                except WizLightTimeOutError as ex:
                    _LOGGER.error("Connection to bulb at %s timed out: %s", host, ex)
                    errors["base"] = "bulb_time_out"
                except WizLightConnectionError as ex:
                    _LOGGER.error("Failed to connect to bulb at %s: %s", host, ex)
                    errors["base"] = "cannot_connect"
                except Exception as ex:
                    _LOGGER.exception(
                        "Unexpected error while connecting to bulb at %s: %s", host, ex
                    )
                    errors["base"] = "unknown"
                else:
                    await self.async_set_unique_id(mac, raise_on_progress=False)
                    self._abort_if_unique_id_configured(updates={CONF_HOST: host})

                    return self.async_create_entry(
                        title=name_from_bulb_type_and_mac(bulbtype, mac),
                        data={CONF_HOST: host},
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Optional(CONF_HOST, default=""): str}),
            errors=errors,
        )
