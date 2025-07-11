"""Storage manager for WiZ home configuration."""

import json
import logging
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from ..const import STORAGE_VERSION, WIZ_HOME_CONFIG

_LOGGER = logging.getLogger(__name__)


class WizHomeConfigStorage:
    """Manager for WiZ home configuration storage."""

    def __init__(self, hass: HomeAssistant, filename: str = WIZ_HOME_CONFIG) -> None:
        """Initialize the storage manager."""
        self.hass = hass
        self._store: Store = Store(hass, STORAGE_VERSION, filename)

    async def async_download_and_store_config(self, url: str) -> bool:
        """Download WiZ home config from URL and store it."""
        if not url:
            return False

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

            await self._store.async_save(
                {
                    "url": url,
                    "config": json.loads(content),
                    "downloaded_at": self.hass.loop.time(),
                }
            )
        except (aiohttp.ClientError, json.JSONDecodeError, OSError) as ex:
            _LOGGER.error("Error processing WiZ home config: %s", ex)
            return False
        else:
            _LOGGER.debug("Successfully downloaded and stored WiZ home config")
            return True

    async def async_get_stored_data(self) -> dict[str, Any] | None:
        """Get the complete stored data including metadata."""
        return await self._store.async_load()

    async def async_load_config(self) -> dict[str, Any] | None:
        """Load the stored WiZ home config."""
        stored_data = await self.async_get_stored_data()
        return stored_data.get("config") if stored_data else None

    async def async_has_stored_config(self) -> bool:
        """Check if there is a stored WiZ home config."""
        return await self.async_load_config() is not None

    async def async_get_stored_config_url(self) -> str | None:
        """Get the stored WiZ home config URL."""
        stored_data = await self.async_get_stored_data()
        return stored_data.get("url") if stored_data else None

    async def async_clear_config(self) -> None:
        """Clear the stored WiZ home config."""
        await self._store.async_remove()

    async def async_load_local_config_and_store(self) -> bool:
        """Load WiZ home config from local utils folder and store it."""
        import os

        # Get the utils folder path (current directory of this file)
        utils_folder = os.path.dirname(__file__)
        config_file_path = os.path.join(utils_folder, "wiz_home_config.json")

        if not os.path.exists(config_file_path):
            _LOGGER.error("WiZ home config file not found: %s", config_file_path)
            return False

        try:
            with open(config_file_path, "r", encoding="utf-8") as file:
                content = file.read()

            await self._store.async_save(
                {
                    "file_path": config_file_path,
                    "config": json.loads(content),
                    "loaded_at": self.hass.loop.time(),
                }
            )
        except (json.JSONDecodeError, OSError) as ex:
            _LOGGER.error("Error processing WiZ home config file: %s", ex)
            return False
        else:
            _LOGGER.debug(
                "Successfully loaded and stored WiZ home config from utils folder"
            )
            return True
