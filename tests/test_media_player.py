"""Tests for the ledfx component."""

# pylint: disable=no-member,too-many-statements,protected-access,too-many-lines

from __future__ import annotations

import logging
from datetime import timedelta
from unittest.mock import Mock, patch

import pytest
from homeassistant.components.media_player import (
    ATTR_MEDIA_CONTENT_ID,
    ATTR_MEDIA_CONTENT_TYPE,
)
from homeassistant.components.media_player import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.components.media_player import (
    ENTITY_ID_FORMAT as MEDIA_PLAYER_ENTITY_ID_FORMAT,
)
from homeassistant.components.media_player import SERVICE_PLAY_MEDIA
from homeassistant.const import ATTR_ENTITY_ID, STATE_IDLE, STATE_UNAVAILABLE
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
    MEDIA_PLAYER_OUTGOING,
    MEDIA_PLAYER_OUTGOING_NAME,
    UPDATER,
)
from custom_components.tattelecom_intercom.enum import CallState
from custom_components.tattelecom_intercom.exceptions import IntercomError
from custom_components.tattelecom_intercom.helper import generate_entity_id
from custom_components.tattelecom_intercom.updater import IntercomUpdater
from tests.setup import (
    async_mock_call,
    async_mock_client,
    async_setup,
    get_audio_fixture_path,
)

_LOGGER = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations"""

    yield


@pytest.mark.asyncio
async def test_play(hass: HomeAssistant) -> None:
    """Test play.

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

        unique_id: str = _generate_id(MEDIA_PLAYER_OUTGOING, updater.phone)

        state: State = hass.states.get(unique_id)
        assert state.state == STATE_UNAVAILABLE
        assert state.name == MEDIA_PLAYER_OUTGOING_NAME
        assert state.attributes["icon"] == "mdi:phone-outgoing"
        assert state.attributes["attribution"] == ATTRIBUTION

        await updater._call_callback(
            await async_mock_call(
                updater.voip,  # type: ignore
                load_fixture("invite_data.txt"),
                CallState.ANSWERED,
            )
        )
        async_fire_time_changed(
            hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
        )
        await hass.async_block_till_done()

        state = hass.states.get(unique_id)
        assert state.state == STATE_IDLE

        await hass.services.async_call(
            MEDIA_PLAYER_DOMAIN,
            SERVICE_PLAY_MEDIA,
            {
                ATTR_ENTITY_ID: [unique_id],
                ATTR_MEDIA_CONTENT_TYPE: "music",
                ATTR_MEDIA_CONTENT_ID: get_audio_fixture_path("rtp_write.wav"),
            },
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
        MEDIA_PLAYER_ENTITY_ID_FORMAT,
        phone,
        code,
    )
