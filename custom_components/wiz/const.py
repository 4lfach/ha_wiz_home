"""Constants for the WiZ Platform integration."""

from datetime import timedelta

from pywizlight import (
    WizLightConnectionError,
    WizLightNotKnownBulb,
    WizLightTimeOutError,
)

DOMAIN = "wiz_alfa"
DEFAULT_NAME = "WiZ alfa"

DISCOVER_SCAN_TIMEOUT = 10
DISCOVERY_INTERVAL = timedelta(minutes=15)

WIZ_EXCEPTIONS = (
    OSError,
    WizLightTimeOutError,
    TimeoutError,
    WizLightConnectionError,
    ConnectionRefusedError,
)
WIZ_CONNECT_EXCEPTIONS = (WizLightNotKnownBulb, *WIZ_EXCEPTIONS)

SIGNAL_WIZ_PIR = "wiz_pir_{}"

# The key used for the WiZ Home link in config flow and config entry data
WIZ_HOME_LINK = "WiZ app link"

WIZ_HOME_CONFIG = "wiz_home_config"

STORAGE_VERSION = 1
