"""Tests for the tattelecom_intercom component."""

# pylint: disable=no-member,too-many-statements,protected-access,too-many-lines,too-many-locals

from __future__ import annotations

import json
import logging
from datetime import timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.components.switch import ENTITY_ID_FORMAT as SWITCH_ENTITY_ID_FORMAT
from homeassistant.components.switch import SERVICE_TURN_OFF, SERVICE_TURN_ON
from homeassistant.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant, State
from homeassistant.util.dt import utcnow
from pytest_homeassistant_custom_component.common import (
    async_fire_time_changed,
    load_fixture,
)

from custom_components.tattelecom_intercom.const import (
    ATTRIBUTION,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    SWITCH_MUTE_NAME,
    UPDATER,
)
from custom_components.tattelecom_intercom.exceptions import (
    IntercomError,
    IntercomRequestError,
)
from custom_components.tattelecom_intercom.helper import generate_entity_id
from custom_components.tattelecom_intercom.updater import IntercomUpdater
from tests.setup import (
    MOCK_INTERCOM_ID,
    MultipleSideEffect,
    async_mock_client,
    async_setup,
)

_LOGGER = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations"""

    yield


@pytest.mark.asyncio
async def test_mute(hass: HomeAssistant) -> None:
    """Test mute.

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

        def success_mute(intercom_id: int) -> dict:
            assert intercom_id == MOCK_INTERCOM_ID

            return json.loads(load_fixture("mute_data.json"))

        def error_mute(intercom_id: int) -> None:
            raise IntercomRequestError

        mock_client.return_value.mute = AsyncMock(
            side_effect=MultipleSideEffect(success_mute, error_mute)
        )

        def success_unmute(intercom_id: int) -> dict:
            assert intercom_id == MOCK_INTERCOM_ID

            return json.loads(load_fixture("unmute_data.json"))

        def error_unmute(intercom_id: int) -> None:
            raise IntercomRequestError

        mock_client.return_value.unmute = AsyncMock(
            side_effect=MultipleSideEffect(success_unmute, error_unmute)
        )

        _, config_entry = await async_setup(hass)

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: IntercomUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]

        assert updater.last_update_success

        unique_id: str = _generate_id(str(MOCK_INTERCOM_ID), updater.phone)

        state: State = hass.states.get(unique_id)
        assert state.state == STATE_OFF
        assert state.name == SWITCH_MUTE_NAME
        assert state.attributes["icon"] == "mdi:bell"
        assert state.attributes["attribution"] == ATTRIBUTION

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        _prev_calls: int = len(mock_client.mock_calls)

        assert await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: [unique_id]},
            blocking=True,
            limit=None,
        )

        _prev_calls += 1
        state = hass.states.get(unique_id)
        assert state.state == STATE_ON
        assert state.attributes["icon"] == "mdi:bell-off"
        assert len(mock_client.mock_calls) == _prev_calls

        assert await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: [unique_id]},
            blocking=True,
            limit=None,
        )

        _prev_calls += 1
        state = hass.states.get(unique_id)
        assert state.state == STATE_OFF
        assert state.attributes["icon"] == "mdi:bell"
        assert len(mock_client.mock_calls) == _prev_calls

        _prev_calls += 1
        assert await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: [unique_id]},
            blocking=True,
            limit=None,
        )

        assert len(mock_client.mock_calls) == _prev_calls

        _prev_calls += 1
        assert await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: [unique_id]},
            blocking=True,
            limit=None,
        )

        assert len(mock_client.mock_calls) == _prev_calls


@pytest.mark.asyncio
async def test_mute_change(hass: HomeAssistant) -> None:
    """Test mute change.

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

        def mute_off() -> None:
            return json.loads(load_fixture("intercoms_data.json"))

        def mute_on() -> None:
            return json.loads(load_fixture("intercoms_mute_on_data.json"))

        mock_client.return_value.intercoms = AsyncMock(
            side_effect=MultipleSideEffect(mute_off, mute_on)
        )

        _, config_entry = await async_setup(hass)

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: IntercomUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]

        assert updater.last_update_success

        unique_id: str = _generate_id(str(MOCK_INTERCOM_ID), updater.phone)

        state: State = hass.states.get(unique_id)
        assert state.state == STATE_OFF
        assert state.name == SWITCH_MUTE_NAME
        assert state.attributes["icon"] == "mdi:bell"
        assert state.attributes["attribution"] == ATTRIBUTION

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == STATE_ON
        assert state.name == SWITCH_MUTE_NAME
        assert state.attributes["icon"] == "mdi:bell-off"
        assert state.attributes["attribution"] == ATTRIBUTION


def _generate_id(code: str, phone: int) -> str:
    """Generate unique id

    :param code: str
    :param phone: int
    :return str
    """

    return generate_entity_id(
        SWITCH_ENTITY_ID_FORMAT,
        phone,
        code,
    )
