"""Tests for the tattelecom_intercom component."""

# pylint: disable=no-member,too-many-statements,protected-access,too-many-lines

from __future__ import annotations

import json
import logging
import urllib.parse
from typing import Final
from unittest.mock import AsyncMock

from homeassistant import setup
from homeassistant.const import CONF_SCAN_INTERVAL, CONF_TOKEN
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry, load_fixture

from custom_components.tattelecom_intercom.const import (
    CLIENT_URL,
    CONF_PHONE,
    DOMAIN,
    OPTION_IS_FROM_FLOW,
    UPDATER,
)
from custom_components.tattelecom_intercom.enum import ApiVersion
from custom_components.tattelecom_intercom.helper import get_config_value
from custom_components.tattelecom_intercom.updater import IntercomUpdater

MOCK_PHONE: Final = 79998887766
MOCK_LOGIN: Final = "test"
MOCK_CODE: Final = "123456"
MOCK_TOKEN: Final = "000000000000000000000000000000000"
MOCK_INTERCOM_ID: Final = 1
MOCK_SCAN_INTERVAL: Final = 10

_LOGGER = logging.getLogger(__name__)


async def async_setup(
    hass: HomeAssistant, phone: int = MOCK_PHONE
) -> tuple[IntercomUpdater, MockConfigEntry]:
    """Setup.

    :param hass: HomeAssistant
    :param phone: int
    """

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_PHONE: phone,
            CONF_TOKEN: MOCK_TOKEN,
            CONF_SCAN_INTERVAL: MOCK_SCAN_INTERVAL,
        },
        options={OPTION_IS_FROM_FLOW: True},
    )
    config_entry.add_to_hass(hass)

    await setup.async_setup_component(hass, "http", {})

    updater: IntercomUpdater = IntercomUpdater(
        hass,
        get_config_value(config_entry, CONF_PHONE),
        get_config_value(config_entry, CONF_TOKEN),
        MOCK_SCAN_INTERVAL,
    )

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config_entry.entry_id] = {
        UPDATER: updater,
    }

    return updater, config_entry


async def async_mock_client(mock_client) -> None:
    """Mock"""

    mock_client.return_value.signin = AsyncMock(
        return_value=json.loads(load_fixture("signin_data.json"))
    )
    mock_client.return_value.register = AsyncMock(
        return_value=json.loads(load_fixture("register_data.json"))
    )
    mock_client.return_value.sms_confirm = AsyncMock(
        return_value=json.loads(load_fixture("sms_confirm_data.json"))
    )
    mock_client.return_value.update_push_token = AsyncMock(
        return_value=json.loads(load_fixture("update_push_token_data.json"))
    )
    mock_client.return_value.sip_settings = AsyncMock(
        return_value=json.loads(load_fixture("sip_settings_data.json"))
    )
    mock_client.return_value.intercoms = AsyncMock(
        return_value=json.loads(load_fixture("intercoms_data.json"))
    )
    mock_client.return_value.open = AsyncMock(
        return_value=json.loads(load_fixture("open_data.json"))
    )
    mock_client.return_value.mute = AsyncMock(
        return_value=json.loads(load_fixture("mute_data.json"))
    )
    mock_client.return_value.unmute = AsyncMock(
        return_value=json.loads(load_fixture("unmute_data.json"))
    )
    mock_client.return_value.schedule = AsyncMock(
        return_value=json.loads(load_fixture("schedule_data.json"))
    )


def get_url(
    path: str,
    query_params: dict | None = None,
) -> str:
    """Generate url

    :param path: str
    :param query_params: dict | None
    :return: str
    """

    if query_params is not None and len(query_params) > 0:
        path += f"?{urllib.parse.urlencode(query_params, doseq=True)}"

    return CLIENT_URL.format(api_version=ApiVersion.V1, path=path)


class MultipleSideEffect:  # pylint: disable=too-few-public-methods
    """Multiple side effect"""

    def __init__(self, *fns):
        """init"""

        self.funcs = iter(fns)

    def __call__(self, *args, **kwargs):
        """call"""

        func = next(self.funcs)
        return func(*args, **kwargs)
