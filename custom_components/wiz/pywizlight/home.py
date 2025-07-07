"""pywizlight integration."""
import asyncio
import json
import logging
import os
import requests

from .exceptions import (
    WizHomeError,
    WizHomeParsingError,
)
_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel('DEBUG')

_DEFAULT_HOME_STRUCTURE_FILEPATH= "home_structure.json"
class wizhome:
    """Create an instance of a WiZ Home."""
    # default port for WiZ home: ???
    def __init__(
        self,
        homeID: int,
        cloudURL: str,
        fileName: str
    ) -> None:
        _LOGGER.warning(f'HOME __init__ from: {str(cloudURL)[:42]}/{str(fileName)[:42]}')
        self.homeID = homeID        # the homeID, atfer processing JSON
        self.cloudURL = cloudURL      # the URL to the JSON content
        self.fileName = fileName      # the URL to the JSON content
        self.jsonHome = None        # the JSON content itself
        self.devices = {}
        self.groups = {}
        self.rooms = {}
        self.name = None
        self.creation_date = None
        self.update_date = None
        self.udp_signing_key = None

    async def fetchJSONContent(self, current_loop: asyncio.AbstractEventLoop) -> int:
        if self.fileName != None:
            _LOGGER.debug(f'fetchJSONContent from: {self.fileName}')
            with open(self.fileName, "r") as f:
                self.jsonHome = f.read()
            _LOGGER.debug(f'-fetchJSONContent-              : {self.jsonHome[:96]}')
            return 200
        elif self.cloudURL != None:
            _LOGGER.debug(f'fetchJSONContent from: {self.cloudURL[:96]}')
            response1 = await current_loop.run_in_executor(None, requests.get, self.cloudURL)
            _LOGGER.debug(f'-fetchJSONContent- Call returned: {response1.status_code}')
            _LOGGER.debug(f'-fetchJSONContent-              : {response1.text[:96]}')
            with open("home_structure.json", "w") as f:
                f.write(response1.text)
            if response1.status_code == 200:
                self.jsonHome = response1.text
            return response1.status_code
        elif os.path.isfile(_DEFAULT_HOME_STRUCTURE_FILEPATH):
            _LOGGER.debug(f'fetchJSONContent from default path: {_DEFAULT_HOME_STRUCTURE_FILEPATH}')
            with open(_DEFAULT_HOME_STRUCTURE_FILEPATH, "r") as f:
                self.jsonHome = f.read()
            _LOGGER.debug(f'-fetchJSONContent-              : {self.jsonHome[:96]}')
            return 200
        else:
            _LOGGER.warning(f'-fetchJSONContent-              : No File or URL to fetch')
            raise WizHomeError(f'-fetchJSONContent-              : No File or URL to fetch')

    def parseJSON(self):
        _LOGGER.debug("loadingJSON for current home %s, from homeKey %s", self.homeID, self.cloudURL)
        if self.jsonHome == None:
            _LOGGER.warning("No json content present, fetch from Cloud first")
            raise WizHomeParsingError(f"No json content exist for this Home, URL: {str(self.cloudURL)[:64]}")

        try:
            hd = json.loads(self.jsonHome)
            #_LOGGER.info(json.dumps(hd, indent=2))

            self.homeID = hd["home_id"]
            self.name = hd["name"]
            self.creation_date = hd["creation_date"]
            self.update_date = hd["update_date"]
            self.udp_signing_key = hd["udp_signing_key"]
            self.rooms = {}
            for room in hd.get('rooms', {}):
                _LOGGER.debug(f'Room {room}')
                self.rooms.update({room['room_id']: room })
                
            self.devices = {}
            for device in hd.get('devices', {}):
                _LOGGER.debug(f'Device {device}')
                self.devices.update({device['mac_address']: device})

            self.groups = {}
            for group in hd.get('groups', {}):
                _LOGGER.debug(f'Group {group}')
                self.groups.update({group['group_id']: group})

        except json.JSONDecodeError as ex:
            _LOGGER.warning("Failed to json parse the message: %s", self.jsonHome[:64])
            raise WizHomeParsingError(f"Failed to decode existing json: {self.jsonHome[:64]}: {ex}")

        return

    def get_device_details(self, mac):
        _LOGGER.debug("getDeviceDetails checking in home %s if any details about wizlight %s", self.homeID, mac)
        if self.jsonHome is None:
            _LOGGER.warning("getDeviceDetails checking in home %s, no Home Structure loaded", self.homeID)
            return {}
        else:
            device_info = self.devices.get(mac)
            _LOGGER.debug("getDeviceDetails checking in home %s if any details about wizlight %s found %s", self.homeID, mac, device_info)
            return device_info