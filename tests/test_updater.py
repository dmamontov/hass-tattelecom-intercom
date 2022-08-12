"""Tests for the tattelecom_intercom component."""

# pylint: disable=no-member,too-many-statements,protected-access,too-many-lines

from __future__ import annotations

import logging
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.tattelecom_intercom.const import DOMAIN, UPDATER
from custom_components.tattelecom_intercom.updater import async_get_updater
from tests.setup import async_mock_client, async_setup

_LOGGER = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations"""

    yield


async def test_updater_schedule(hass: HomeAssistant) -> None:
    """Test updater schedule.

    :param hass: HomeAssistant
    """

    updater, _ = await async_setup(hass)

    assert updater._unsub_refresh is None

    updater.schedule_refresh(updater._update_interval)
    updater.schedule_refresh(updater._update_interval)

    assert updater._unsub_refresh is not None


async def test_updater_get_updater(hass: HomeAssistant) -> None:
    """Test updater get updater.

    :param hass: HomeAssistant
    """

    with patch(
        "custom_components.tattelecom_intercom.updater.IntercomClient"
    ) as mock_client:
        await async_mock_client(mock_client)

        _, config_entry = await async_setup(hass)

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        assert hass.data[DOMAIN][config_entry.entry_id][UPDATER] == async_get_updater(
            hass, config_entry.entry_id
        )

        with pytest.raises(ValueError):
            async_get_updater(hass, "incorrect")
