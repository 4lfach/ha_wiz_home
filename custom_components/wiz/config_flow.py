"""Config flow for WiZ Platform."""

from __future__ import annotations

import json
import logging
from typing import Any

import aiohttp
from .pywizlight.bulb import wizlight
from .pywizlight.discovery import DiscoveredBulb
from .pywizlight.exceptions import WizLightConnectionError, WizLightTimeOutError
import voluptuous as vol

from homeassistant.components import onboarding
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST
from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo
from homeassistant.helpers.storage import Store
from homeassistant.util.network import is_ip_address

from .const import DOMAIN, STORAGE_VERSION, WIZ_HOME_LINK
from .utils import build_full_bulb_name

_LOGGER = logging.getLogger(__name__)

CONF_DEVICE = "device"


class WizConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for WiZ."""

    VERSION = 2

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovered_device: DiscoveredBulb | None = None

    async def _is_first_setup(self) -> bool:
        """Check if this is the first setup by verifying config entries and storage."""
        store: Store = Store(self.hass, STORAGE_VERSION, "wiz_home_config")
        stored_data = await store.async_load()

        return stored_data is None or not stored_data.get("config")

    async def async_download_and_validate_wiz_home(self, url: str) -> bool:
        """Download and validate WiZ home file."""
        try:
            async with aiohttp.ClientSession() as session:
                response = await session.get(
                    url, timeout=aiohttp.ClientTimeout(total=30)
                )
                if response.status != 200:
                    _LOGGER.error(
                        "Failed to download WiZ home config: HTTP %s", response.status
                    )
                    return False
                content = await response.text()

            json_data = json.loads(content)

            store: Store = Store(self.hass, STORAGE_VERSION, "wiz_home_config")
            await store.async_save(
                {
                    "url": url,
                    "config": json_data,
                    "downloaded_at": self.hass.loop.time(),
                }
            )
            return True

        except aiohttp.ClientError as ex:
            _LOGGER.error("Network error while downloading WiZ home config: %s", ex)
        except json.JSONDecodeError as ex:
            _LOGGER.error("Invalid JSON in WiZ home config: %s", ex)
        except KeyError as ex:
            _LOGGER.error("Missing expected data in WiZ home config: %s", ex)
        except Exception as ex:
            _LOGGER.error("Unexpected error processing WiZ home config: %s", ex)

        return False

    async def async_validate_and_connect_bulb(
        self, host: str
    ) -> tuple[str | None, str | None, dict]:
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
            except Exception as ex:
                _LOGGER.error(
                    "Unexpected error while connecting to bulb at %s: %s", host, ex
                )
                errors["base"] = "unknown"
            else:
                return bulbtype, mac, {}

        return None, None, errors

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
        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm discovered device."""
        if self._discovered_device is None:
            return self.async_abort(reason="no_device_found")
        if user_input is not None or not onboarding.async_is_onboarded(self.hass):
            ip_address = self._discovered_device.ip_address
            bulbtype, mac, errors = await self.async_validate_and_connect_bulb(
                str(ip_address)
            )
            if not errors and bulbtype is not None and mac is not None:
                return await self.async_create_bulb_entry(
                    str(ip_address), str(bulbtype), str(mac)
                )
            return self.async_abort(reason="cannot_connect")

        return self.async_show_form(step_id="discovery_confirm")

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initialized by the user."""
        errors = {}
        first_setup = await self._is_first_setup()

        if user_input is not None:
            host = user_input.get(CONF_HOST)
            if not isinstance(host, str):
                host = str(host) if host is not None else ""

            if first_setup:
                wiz_link = user_input.get(WIZ_HOME_LINK, "")
                if not isinstance(wiz_link, str):
                    wiz_link = str(wiz_link)
                if not wiz_link.startswith(
                    "https://wiz-s3-local-integration-dev-artifacts"
                ) or not await self.async_download_and_validate_wiz_home(wiz_link):
                    errors["base"] = "invalid_link"

            if not errors:
                bulbtype, mac, bulb_errors = await self.async_validate_and_connect_bulb(
                    host
                )
                errors.update(bulb_errors)

                if not errors and bulbtype is not None and mac is not None:
                    _LOGGER.info(
                        "Successfully connected to bulb %s (%s)", bulbtype, mac
                    )
                    return await self.async_create_bulb_entry(host, bulbtype, str(mac))

        schema_dict: dict[Any, Any] = {vol.Required(CONF_HOST): str}
        if first_setup:
            schema_dict[vol.Optional(WIZ_HOME_LINK)] = str
        schema = vol.Schema(schema_dict)

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
