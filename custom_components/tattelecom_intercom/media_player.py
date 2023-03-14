"""Media player component."""


# pylint: disable=using-constant-test,missing-parentheses-for-call-in-test

from __future__ import annotations

import asyncio
import logging
import shlex
import subprocess
import time
from asyncio import Lock
from typing import Any, Final

from homeassistant.components.ffmpeg import FFmpegManager, get_ffmpeg_manager
from homeassistant.components.media_player import (
    ENTITY_ID_FORMAT,
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityDescription,
)
from homeassistant.components.media_player.const import (
    MEDIA_TYPE_MUSIC,
    SUPPORT_PLAY_MEDIA,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_IDLE, STATE_PLAYING
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import MEDIA_PLAYER_OUTGOING, MEDIA_PLAYER_OUTGOING_NAME, SIGNAL_CALL_STATE
from .entity import IntercomEntity
from .enum import CallState
from .exceptions import IntercomInvalidStateError
from .updater import IntercomUpdater, async_get_updater

PARALLEL_UPDATES = 0

_LOGGER = logging.getLogger(__name__)

EVENTS: Final = {
    MEDIA_PLAYER_OUTGOING: SIGNAL_CALL_STATE,
}

MEDIA_PLAYERS: tuple[MediaPlayerEntityDescription, ...] = (
    MediaPlayerEntityDescription(
        key=MEDIA_PLAYER_OUTGOING,
        name=MEDIA_PLAYER_OUTGOING_NAME,
        device_class=MediaPlayerDeviceClass.SPEAKER,
        icon="mdi:phone-outgoing",
        entity_registry_enabled_default=True,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tattelecom intercom media player entry.

    :param hass: HomeAssistant: Home Assistant object
    :param config_entry: ConfigEntry: ConfigEntry object
    :param async_add_entities: AddEntitiesCallback: AddEntitiesCallback callback object
    """

    updater: IntercomUpdater = async_get_updater(hass, config_entry.entry_id)

    entities: list[IntercomMediaPlayer] = [
        IntercomMediaPlayer(
            hass, f"{config_entry.entry_id}-{description.key}", description, updater
        )
        for description in MEDIA_PLAYERS
    ]
    async_add_entities(entities)


# pylint: disable=too-many-ancestors
class IntercomMediaPlayer(IntercomEntity, MediaPlayerEntity):
    """Intercom media player entry."""

    _unsub_update: CALLBACK_TYPE
    _attr_supported_features: int = SUPPORT_PLAY_MEDIA
    _attr_is_volume_muted: bool = False
    _play_lock: Lock

    def __init__(
        self,
        hass: HomeAssistant,
        unique_id: str,
        description: MediaPlayerEntityDescription,
        updater: IntercomUpdater,
    ) -> None:
        """Initialize media player.

        :param hass: HomeAssistant
        :param unique_id: str: Unique ID
        :param description: MediaPlayerEntityDescription object
        :param updater: IntercomUpdater: Intercom updater object
        """

        self._manager: FFmpegManager = get_ffmpeg_manager(hass)

        IntercomEntity.__init__(self, unique_id, description, updater, ENTITY_ID_FORMAT)

        self._attr_available = False
        self._attr_state = STATE_IDLE

        self._play_lock = Lock()

    @property
    def available(self) -> bool:
        """Is available

        :return bool: Is available
        """

        return self.coordinator.last_update_success and self._attr_available  # type: ignore

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""

        await IntercomEntity.async_added_to_hass(self)

        if self.entity_description.key in EVENTS:
            self._unsub_update = async_dispatcher_connect(
                self.hass,
                EVENTS[self.entity_description.key],
                self._handle_event_update,
            )

    async def will_remove_from_hass(self) -> None:  # pragma: no cover
        """Remove event"""

        if self._unsub_update:
            self._unsub_update()

    @callback
    def _handle_event_update(self) -> None:
        """Update state."""

        self._handle_coordinator_update()

    def _handle_coordinator_update(self) -> None:
        """Update state."""

        _available: bool = bool(
            self._updater.last_call
            and self._updater.last_call.state == CallState.ANSWERED
        )

        if self._attr_available == _available:  # type: ignore
            return

        self._attr_available = _available

        if _available:
            self._attr_state = STATE_IDLE

        self.async_write_ha_state()

    async def async_play_media(
        self, media_type: str, media_id: str, **kwargs: Any
    ) -> None:
        """Send the play_media command to the media player.

        :param media_type
        :param media_id: str
        :param kwargs: Any
        """

        if media_type != MEDIA_TYPE_MUSIC:  # pragma: no cover
            _LOGGER.error(
                "Invalid media type %s. Only %s is supported",
                media_type,
                MEDIA_TYPE_MUSIC,
            )

            return

        if (
            not self._updater.last_call
            or self._updater.last_call.state != CallState.ANSWERED
        ):  # pragma: no cover
            _LOGGER.error("Active answered call not found")

            return

        def _convert(command: str) -> bytes:
            """Run convert

            :param command: str
            :return bytes
            """

            return subprocess.run(
                shlex.split(command), check=False, shell=False, stdout=subprocess.PIPE
            ).stdout

        async with self._play_lock:
            data = await self.hass.async_add_executor_job(
                _convert,
                str(
                    f"{self._manager.binary} -loglevel quiet "
                    f"-i {media_id} "
                    "-ac 1 -ar 8000 -acodec pcm_u8 -f wav -"
                ),
            )

            if not data:  # pragma: no cover
                _LOGGER.error("Failed to send data to intercom, no data available")

                return

            stop: float = time.time() + (len(data) / 8000)

            self._attr_state = STATE_PLAYING

            try:
                await self._updater.last_call.write_audio(data)
            except IntercomInvalidStateError as _err:  # pragma: no cover
                self._attr_state = STATE_IDLE

                _LOGGER.error("Failed to send data to intercom, %r", _err)

                return

            while (
                time.time() <= stop
                and self._updater.last_call.state == CallState.ANSWERED
            ):
                await asyncio.sleep(1)

            self._attr_state = STATE_IDLE
