"""Tests for the tattelecom_intercom component."""

# pylint: disable=no-member,too-many-statements,protected-access,too-many-lines

from __future__ import annotations

import logging
from datetime import timedelta
from unittest.mock import Mock, patch

import pytest
from homeassistant.components.camera import ENTITY_ID_FORMAT as CAMERA_ENTITY_ID_FORMAT
from homeassistant.components.camera import STATE_STREAMING
from homeassistant.core import HomeAssistant, State
from homeassistant.util.dt import utcnow
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.tattelecom_intercom.const import (
    ATTRIBUTION,
    CAMERA_NAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAINTAINER,
    UPDATER,
)
from custom_components.tattelecom_intercom.exceptions import IntercomError
from custom_components.tattelecom_intercom.helper import generate_entity_id
from custom_components.tattelecom_intercom.updater import IntercomUpdater
from tests.setup import MOCK_INTERCOM_ID, async_mock_client, async_setup

_LOGGER = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations"""

    yield


async def test_init(hass: HomeAssistant) -> None:
    """Test init.

    :param hass: HomeAssistant
    """

    with patch(
        "custom_components.tattelecom_intercom.updater.IntercomClient"
    ) as mock_client, patch(
        "custom_components.tattelecom_intercom.updater.async_dispatcher_send"
    ), patch(
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

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        updater: IntercomUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]

        assert updater.last_update_success

        state: State = hass.states.get(
            _generate_id(str(MOCK_INTERCOM_ID), updater.phone)
        )
        assert state.state == STATE_STREAMING
        assert state.name == CAMERA_NAME
        assert state.attributes["icon"] == "mdi:doorbell-video"
        assert state.attributes["brand"] == MAINTAINER
        assert state.attributes["attribution"] == ATTRIBUTION


def _generate_id(code: str, phone: int) -> str:
    """Generate unique id

    :param code: str
    :param phone: int
    :return str
    """

    return generate_entity_id(
        CAMERA_ENTITY_ID_FORMAT,
        phone,
        code,
    )
