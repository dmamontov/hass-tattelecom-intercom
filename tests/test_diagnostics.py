"""Tests for the tattelecom_intercom component."""

# pylint: disable=no-member,too-many-statements,protected-access,too-many-lines

from __future__ import annotations

import logging
from unittest.mock import Mock, patch

import pytest
from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant
from pytest_httpx import HTTPXMock

from custom_components.tattelecom_intercom.const import DOMAIN, UPDATER
from custom_components.tattelecom_intercom.diagnostics import (
    TO_REDACT,
    async_get_config_entry_diagnostics,
)
from custom_components.tattelecom_intercom.exceptions import IntercomError
from custom_components.tattelecom_intercom.updater import IntercomUpdater
from tests.setup import async_mock_client, async_setup

_LOGGER = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations"""

    yield


@pytest.mark.asyncio
async def test_init(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """Test init.

    :param hass: HomeAssistant
    """

    with patch(
        "custom_components.tattelecom_intercom.updater.IntercomClient"
    ) as mock_client, patch(
        "custom_components.tattelecom_intercom.updater.asyncio.sleep", return_value=None
    ), patch(
        "custom_components.tattelecom_intercom.sip.socket.socket"
    ) as mock_socket:
        mock_socket.return_value.setblocking = Mock(return_value=None)
        mock_socket.return_value.recv = Mock(return_value=None)
        mock_socket.return_value.sendto = Mock(side_effect=IntercomError)
        await async_mock_client(mock_client)

        _, config_entry = await async_setup(hass)

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: IntercomUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]

        assert updater.last_update_success

        diagnostics_data: dict = await async_get_config_entry_diagnostics(
            hass, config_entry
        )

        assert diagnostics_data["code_map"] == {"G0001": 1, "G0002": 2, "G0003": 3}
        assert diagnostics_data["config_entry"] == async_redact_data(
            config_entry.as_dict(), TO_REDACT
        )
        assert diagnostics_data["data"] == {
            "1_mute": False,
            "1_sip_login": "G0001",
            "1_stream_url": "https://test.com/intercom_1/index.m3u8?token=2.0000000000",
            "2_mute": False,
            "2_sip_login": "G0002",
            "2_stream_url": "https://test.com/intercom_2/index.m3u8?token=2.0000000000",
            "3_mute": False,
            "3_sip_login": "G0003",
            "3_stream_url": "https://test.com/intercom_3/index.m3u8?token=2.0000000000",
            "sip_address": "127.0.0.1",
            "sip_login": "**REDACTED**",
            "sip_password": "**REDACTED**",
            "sip_port": 9740,
            "update_state": False,
        }
        assert diagnostics_data["intercoms"] == [1, 2, 3]
        assert len(diagnostics_data["sip_send"]) == 11
