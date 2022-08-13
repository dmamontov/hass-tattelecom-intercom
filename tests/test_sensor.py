"""Tests for the tattelecom_intercom component."""

# pylint: disable=no-member,too-many-statements,protected-access,too-many-lines

from __future__ import annotations

import logging
from datetime import timedelta
from unittest.mock import Mock, patch

import pytest
from homeassistant.components.sensor import ENTITY_ID_FORMAT as SENSOR_ENTITY_ID_FORMAT
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import EntityCategory
from homeassistant.util.dt import utcnow
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.tattelecom_intercom.const import (
    ATTRIBUTION,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    SENSOR_SIP_STATE,
    SENSOR_SIP_STATE_NAME,
    UPDATER,
)
from custom_components.tattelecom_intercom.enum import VoipState
from custom_components.tattelecom_intercom.exceptions import IntercomError
from custom_components.tattelecom_intercom.helper import generate_entity_id
from custom_components.tattelecom_intercom.updater import IntercomUpdater
from tests.setup import async_mock_client, async_setup

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

        updater: IntercomUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]

        assert updater.last_update_success

        state: State = hass.states.get(_generate_id(SENSOR_SIP_STATE, updater.phone))
        assert state.state == VoipState.INACTIVE.value
        assert state.name == SENSOR_SIP_STATE_NAME
        assert state.attributes["attribution"] == ATTRIBUTION


async def test_update_state(hass: HomeAssistant) -> None:
    """Test update state.

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
        registry = er.async_get(hass)

        assert updater.last_update_success

        unique_id: str = _generate_id(SENSOR_SIP_STATE, updater.phone)

        entry: er.RegistryEntry | None = registry.async_get(unique_id)
        state: State = hass.states.get(unique_id)
        assert state.state == VoipState.INACTIVE
        assert state.name == SENSOR_SIP_STATE_NAME
        assert state.attributes["attribution"] == ATTRIBUTION
        assert entry is not None
        assert entry.entity_category == EntityCategory.DIAGNOSTIC

        updater.voip._change_status(VoipState.FAILED)  # type: ignore

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == VoipState.FAILED


def _generate_id(code: str, phone: int) -> str:
    """Generate unique id

    :param code: str
    :param phone: int
    :return str
    """

    return generate_entity_id(
        SENSOR_ENTITY_ID_FORMAT,
        phone,
        code,
    )
