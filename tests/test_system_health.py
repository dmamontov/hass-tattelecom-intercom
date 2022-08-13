"""Tests for the tattelecom_intercom component."""

# pylint: disable=no-member,too-many-statements,protected-access,too-many-lines

from __future__ import annotations

import logging
from unittest.mock import Mock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import get_system_health_info

from custom_components.tattelecom_intercom.const import DOMAIN
from custom_components.tattelecom_intercom.exceptions import IntercomError
from custom_components.tattelecom_intercom.helper import async_get_version
from tests.setup import async_mock_client, async_setup

_LOGGER = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations"""

    yield


async def test_system_health(hass: HomeAssistant) -> None:
    """Test system_health.

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

        assert await async_setup_component(hass, "system_health", {})
        _, config_entry = await async_setup(hass)

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        info = await get_system_health_info(hass, DOMAIN)

        assert info is not None

        assert info == {
            "sip_state": "inactive",
            "update_state": "ok",
            "version": await async_get_version(hass),
        }
