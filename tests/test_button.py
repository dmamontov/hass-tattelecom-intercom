"""Tests for the tattelecom_intercom component."""

# pylint: disable=no-member,too-many-statements,protected-access,too-many-lines

from __future__ import annotations

import json
import logging
from datetime import timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN
from homeassistant.components.button import ENTITY_ID_FORMAT as BUTTON_ENTITY_ID_FORMAT
from homeassistant.components.button import SERVICE_PRESS
from homeassistant.const import ATTR_ENTITY_ID, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, State
from homeassistant.util.dt import utcnow
from pytest_homeassistant_custom_component.common import (
    async_fire_time_changed,
    load_fixture,
)

from custom_components.tattelecom_intercom.const import (
    ATTRIBUTION,
    BUTTON_ANSWER,
    BUTTON_ANSWER_NAME,
    BUTTON_DECLINE,
    BUTTON_DECLINE_NAME,
    BUTTON_HANGUP,
    BUTTON_HANGUP_NAME,
    BUTTON_OPEN,
    BUTTON_OPEN_NAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
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
    async_mock_call,
    async_mock_client,
    async_setup,
)

_LOGGER = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations"""

    yield


async def test_open(hass: HomeAssistant) -> None:
    """Test open.

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

        def success(intercom_id: int) -> dict:
            assert intercom_id == MOCK_INTERCOM_ID

            return json.loads(load_fixture("open_data.json"))

        def error(intercom_id: int) -> None:
            raise IntercomRequestError

        mock_client.return_value.open = AsyncMock(
            side_effect=MultipleSideEffect(success, error)
        )

        _, config_entry = await async_setup(hass)

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: IntercomUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]

        assert updater.last_update_success

        unique_id: str = _generate_id(str(MOCK_INTERCOM_ID), updater.phone)

        state: State = hass.states.get(unique_id)
        assert state.state == STATE_UNKNOWN
        assert state.name == BUTTON_OPEN_NAME
        assert state.attributes["icon"] == "mdi:lock-open"
        assert state.attributes["attribution"] == ATTRIBUTION

        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        _prev_calls: int = len(mock_client.mock_calls)

        assert await hass.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: [unique_id]},
            blocking=True,
            limit=None,
        )

        assert len(mock_client.mock_calls) == _prev_calls + 1

        assert await hass.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: [unique_id]},
            blocking=True,
            limit=None,
        )

        assert len(mock_client.mock_calls) == _prev_calls + 2


async def test_open_current_call(hass: HomeAssistant) -> None:
    """Test open.

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

        def success(intercom_id: int) -> dict:
            assert intercom_id == MOCK_INTERCOM_ID

            return json.loads(load_fixture("open_data.json"))

        mock_client.return_value.open = AsyncMock(side_effect=success)

        _, config_entry = await async_setup(hass)

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: IntercomUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]

        assert updater.last_update_success

        unique_id: str = _generate_id(BUTTON_OPEN, updater.phone)

        state: State = hass.states.get(unique_id)
        assert state.state == STATE_UNKNOWN
        assert state.name == BUTTON_OPEN_NAME
        assert state.attributes["icon"] == "mdi:lock-open"
        assert state.attributes["attribution"] == ATTRIBUTION

        _prev_calls: int = len(mock_client.mock_calls)

        assert await hass.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: [unique_id]},
            blocking=True,
            limit=None,
        )

        assert len(mock_client.mock_calls) == _prev_calls

        await updater._call_callback(
            await async_mock_call(updater.voip, load_fixture("invite_data.txt"))  # type: ignore
        )

        assert await hass.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: [unique_id]},
            blocking=True,
            limit=None,
        )

        assert len(mock_client.mock_calls) == _prev_calls + 1


async def test_answer_hangup(hass: HomeAssistant) -> None:
    """Test answer and hangup.

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
        mock_socket.return_value.recv = Mock(side_effect=IntercomError)
        mock_socket.return_value.sendto = Mock(return_value=None)

        await async_mock_client(mock_client)

        _, config_entry = await async_setup(hass)

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: IntercomUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]

        assert updater.last_update_success

        answer_unique_id: str = _generate_id(BUTTON_ANSWER, updater.phone)
        hangup_unique_id: str = _generate_id(BUTTON_HANGUP, updater.phone)

        state: State = hass.states.get(answer_unique_id)
        assert state.state == STATE_UNKNOWN
        assert state.name == BUTTON_ANSWER_NAME
        assert state.attributes["icon"] == "mdi:phone-in-talk"
        assert state.attributes["attribution"] == ATTRIBUTION

        state = hass.states.get(hangup_unique_id)
        assert state.state == STATE_UNKNOWN
        assert state.name == BUTTON_HANGUP_NAME
        assert state.attributes["icon"] == "mdi:phone-hangup"
        assert state.attributes["attribution"] == ATTRIBUTION

        assert await hass.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: [answer_unique_id]},
            blocking=True,
            limit=None,
        )

        assert await hass.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: [hangup_unique_id]},
            blocking=True,
            limit=None,
        )

        await updater._call_callback(
            await async_mock_call(updater.voip, load_fixture("invite_data.txt"))  # type: ignore
        )

        await hass.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: [answer_unique_id]},
            blocking=False,
            limit=None,
        )

        await hass.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: [hangup_unique_id]},
            blocking=False,
            limit=None,
        )


async def test_decline(hass: HomeAssistant) -> None:
    """Test decline.

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
        mock_socket.return_value.recv = Mock(side_effect=IntercomError)
        mock_socket.return_value.sendto = Mock(return_value=None)

        await async_mock_client(mock_client)

        _, config_entry = await async_setup(hass)

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        updater: IntercomUpdater = hass.data[DOMAIN][config_entry.entry_id][UPDATER]

        assert updater.last_update_success

        unique_id: str = _generate_id(BUTTON_DECLINE, updater.phone)

        state: State = hass.states.get(unique_id)
        assert state.state == STATE_UNKNOWN
        assert state.name == BUTTON_DECLINE_NAME
        assert state.attributes["icon"] == "mdi:phone-cancel"
        assert state.attributes["attribution"] == ATTRIBUTION

        assert await hass.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: [unique_id]},
            blocking=True,
            limit=None,
        )

        await updater._call_callback(
            await async_mock_call(updater.voip, load_fixture("invite_data.txt"))  # type: ignore
        )

        assert await hass.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: [unique_id]},
            blocking=True,
            limit=None,
        )


def _generate_id(code: str, phone: int) -> str:
    """Generate unique id

    :param code: str
    :param phone: int
    :return str
    """

    return generate_entity_id(
        BUTTON_ENTITY_ID_FORMAT,
        phone,
        code,
    )
