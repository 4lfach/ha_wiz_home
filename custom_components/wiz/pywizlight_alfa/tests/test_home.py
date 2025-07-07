"""Tests for the Bulb API."""
from typing import AsyncGenerator
from unittest.mock import patch
import asyncio
import pytest
from pywizlight_alfa.home import wizhome
from pywizlight_alfa.exceptions import (
    WizLightError,
)
import logging
_LOGGER = logging.getLogger(__name__)

@pytest.fixture(scope="module")
def cloud_home():
    _LOGGER.info("---cloud_home()---- Creating the Home fixture.")
    wh = wizhome(None, 'https://wiz-s3-local-integration-prd-artifacts..amazonaws.com/ENTER_HERE_THE_FULL_URL_FROM_THE_INTEGRATION_PAGE_IN_THE_WIZ_APP', None)
    return wh

@pytest.fixture(scope="module")
def local_home():
    _LOGGER.info("---local_home()---- Creating the Home fixture.")
    wh = wizhome(None, None, "home_structure.json")
    return wh

@pytest.fixture(scope="module")
def wiz_home(local_home):
    _LOGGER.info("---wiz_home()---- Returning the Home fixture.")
    return local_home




def test_beforeJSONParsing(wiz_home):
    _LOGGER.info(f'[test_noCloudFetch] start ### {type(wiz_home)}')
    with pytest.raises(WizLightError):
        wiz_home.parseJSON()

@pytest.mark.asyncio
async def test_fetchJSONContent(wiz_home) -> None:
    _LOGGER.info('[test_fetchJSONContent] start ###')
    error_code = await wiz_home.fetchJSONContent(asyncio.get_running_loop())
    _LOGGER.info(f'[test_fetchJSONContent] returned error code: {error_code}')
    assert error_code and error_code == 200

def test_afterJSONParsing(wiz_home) -> None:
    _LOGGER.info('[test_loadCorrectJSON] start ###')
    wiz_home.parseJSON()
    assert len(wiz_home.rooms) > 0
    assert len(wiz_home.devices) > 0
