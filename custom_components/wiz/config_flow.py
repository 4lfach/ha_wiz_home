"""Config flow for WiZ Platform."""

from __future__ import annotations

import logging
from typing import Any

from pywizlight import wizlight
from pywizlight.discovery import DiscoveredBulb
import voluptuous as vol

from homeassistant.components import onboarding
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST
from homeassistant.data_entry_flow import AbortFlow
from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo

from .const import DISCOVER_SCAN_TIMEOUT, DOMAIN, WIZ_CONNECT_EXCEPTIONS, WIZ_HOME_LINK
from .discovery import async_discover_devices
from .utils.config_flow_helpers import (
    async_update_existing_device_names,
    async_validate_and_connect_bulb,
    format_discovered_devices,
    validate_wiz_home_link,
)
from .utils.storage import WizHomeConfigStorage
from .utils.utils import build_full_bulb_name

_LOGGER = logging.getLogger(__name__)

CONF_DEVICE = "device"


class WizConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for WiZ."""

    VERSION = 1

    _discovered_device: DiscoveredBulb
    _discovered_devices: dict[str, DiscoveredBulb]
    _name: str

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovered_device: DiscoveredBulb | None = None
        self._discovered_devices: dict[str, DiscoveredBulb] = {}

    async def async_create_bulb_entry(
        self, host: str, bulbtype: str, mac: str
    ) -> ConfigFlowResult:
        """Create bulb entry."""
        wiz_home_link = None
        for entry in self._async_current_entries(include_ignore=False):
            if WIZ_HOME_LINK in entry.data:
                wiz_home_link = entry.data[WIZ_HOME_LINK]
                break

        await self.async_set_unique_id(mac, raise_on_progress=False)
        self._abort_if_unique_id_configured(updates={CONF_HOST: host})

        data = {CONF_HOST: host}
        if wiz_home_link:
            data[WIZ_HOME_LINK] = wiz_home_link

        return self.async_create_entry(
            title=await build_full_bulb_name(self.hass, bulbtype, mac), data=data
        )

    async def async_step_dhcp(
        self, discovery_info: DhcpServiceInfo
    ) -> ConfigFlowResult:
        """Handle discovery via dhcp."""
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
        device = self._discovered_device
        _LOGGER.debug("Discovered device: %s", device)
        ip_address = device.ip_address
        mac = device.mac_address
        await self.async_set_unique_id(mac)
        self._abort_if_unique_id_configured(updates={CONF_HOST: ip_address})
        await self._async_connect_discovered_or_abort()
        return await self.async_step_discovery_confirm()

    async def _async_connect_discovered_or_abort(self) -> None:
        """Connect to the device and verify its responding."""
        device = self._discovered_device
        bulb = wizlight(device.ip_address)
        try:
            bulbtype = await bulb.get_bulbtype()
        except WIZ_CONNECT_EXCEPTIONS as ex:
            _LOGGER.debug(
                "Failed to connect to %s during discovery: %s",
                device.ip_address,
                ex,
                exc_info=True,
            )
            raise AbortFlow("cannot_connect") from ex
        self._name = await build_full_bulb_name(self.hass, bulbtype, device.mac_address)

    async def async_step_discovery_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm discovery."""
        ip_address = self._discovered_device.ip_address
        if user_input is not None or not onboarding.async_is_onboarded(self.hass):
            # Make sure the device is still there and
            # update the name if the firmware has auto
            # updated since discovery
            await self._async_connect_discovered_or_abort()
            return self.async_create_entry(
                title=self._name,
                data={CONF_HOST: ip_address},
            )

        self._set_confirm_only()
        placeholders = {"name": self._name, "host": ip_address}
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
            bulb = wizlight(device.ip_address)
            try:
                bulbtype = await bulb.get_bulbtype()
            except WIZ_CONNECT_EXCEPTIONS:
                return self.async_abort(reason="cannot_connect")

            return await self.async_create_bulb_entry(
                device.ip_address, bulbtype, device.mac_address
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
        devices_name = format_discovered_devices(
            self._discovered_devices,
            current_unique_ids,
            current_hosts,
        )
        # Check if there is at least one device
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
        configStorage = WizHomeConfigStorage(self.hass, "wiz_home_config")

        if user_input is not None:
            if user_input.get(WIZ_HOME_LINK) is not None:
                wiz_link = str(user_input.get(WIZ_HOME_LINK, ""))
                if validate_wiz_home_link(wiz_link):
                    # success = await configStorage.async_download_and_store_config(
                    #     wiz_link
                    # )
                    success = await configStorage.async_load_local_config_and_store()
                    if success:
                        await async_update_existing_device_names(self)
                    else:
                        errors["base"] = "invalid_api_key"

            if not (host := user_input[CONF_HOST]):
                return await self.async_step_pick_device()

            bulbtype, mac, bulb_errors = await async_validate_and_connect_bulb(host)
            errors.update(bulb_errors)

            if not errors and bulbtype is not None and mac is not None:
                return await self.async_create_bulb_entry(host, bulbtype, str(mac))

        schema_dict: dict[Any, Any] = {
            vol.Optional(CONF_HOST, default=""): str,
            vol.Optional(WIZ_HOME_LINK): str,
        }
        schema = vol.Schema(schema_dict)

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
