"""Camera component."""


# pylint: disable=using-constant-test,missing-parentheses-for-call-in-test

from __future__ import annotations

import contextlib
import logging
from typing import Final

from homeassistant.components.camera import ENTITY_ID_FORMAT
from homeassistant.components.generic.camera import (
    CONF_AUTHENTICATION,
    CONF_CONTENT_TYPE,
    CONF_FRAMERATE,
    CONF_LIMIT_REFETCH_TO_URL_CHANGE,
    CONF_STREAM_SOURCE,
    CONF_VERIFY_SSL,
    DEFAULT_CONTENT_TYPE,
    HTTP_BASIC_AUTHENTICATION,
    GenericCamera,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import template as template_helper
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo, EntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ATTR_SIP_LOGIN,
    ATTR_STREAM_URL,
    CAMERA_INCOMING,
    CAMERA_INCOMING_NAME,
    CAMERA_NAME,
    MAINTAINER,
    SIGNAL_CALL_STATE,
    SIGNAL_NEW_INTERCOM,
)
from .entity import IntercomEntity
from .enum import CallState
from .updater import IntercomEntityDescription, IntercomUpdater, async_get_updater

PARALLEL_UPDATES = 0

_LOGGER = logging.getLogger(__name__)

EVENTS: Final = {
    CAMERA_INCOMING: SIGNAL_CALL_STATE,
}

CAMERAS: tuple[EntityDescription, ...] = (
    EntityDescription(
        key=CAMERA_INCOMING,
        name=CAMERA_INCOMING_NAME,
        icon="mdi:phone-incoming",
        entity_registry_enabled_default=True,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tattelecom intercom camera entry.

    :param hass: HomeAssistant: Home Assistant object
    :param config_entry: ConfigEntry: ConfigEntry object
    :param async_add_entities: AddEntitiesCallback: AddEntitiesCallback callback object
    """

    updater: IntercomUpdater = async_get_updater(hass, config_entry.entry_id)

    @callback
    def add_camera(entity: IntercomEntityDescription) -> None:
        """Add camera.

        :param entity: IntercomEntityDescription: Sensor object
        """

        async_add_entities(
            [
                IntercomCamera(
                    f"{config_entry.entry_id}-camera-{entity.id}",
                    EntityDescription(
                        key=str(entity.id),
                        name=CAMERA_NAME,
                        icon="mdi:doorbell-video",
                        entity_registry_enabled_default=True,
                    ),
                    updater,
                    entity.device_info,
                )
            ]
        )

    entities: list[IntercomCamera] = [
        IntercomCamera(
            f"{config_entry.entry_id}-{description.key}", description, updater
        )
        for description in CAMERAS
    ]
    async_add_entities(entities)

    for intercom in updater.intercoms.values():
        add_camera(intercom)

    updater.new_intercom_callbacks.append(
        async_dispatcher_connect(hass, SIGNAL_NEW_INTERCOM, add_camera)
    )


# pylint: disable=too-many-ancestors
class IntercomCamera(IntercomEntity, GenericCamera):
    """Intercom camera entry."""

    _attr_stream_url: str
    _unsub_update: CALLBACK_TYPE

    def __init__(  # pylint: disable=too-many-arguments
        self,
        unique_id: str,
        description: EntityDescription,
        updater: IntercomUpdater,
        device_info: DeviceInfo | None = None,
    ) -> None:
        """Initialize camera.

        :param unique_id: str: Unique ID
        :param description: EntityDescription object
        :param updater: IntercomUpdater: Intercom updater object
        :param device_info: DeviceInfo | None: DeviceInfo object
        """

        source: str = ""

        if description.key != CAMERA_INCOMING:
            self._attr_is_streaming = True

            source = updater.data.get(f"{description.key}_{ATTR_STREAM_URL}", "")

            self._attr_extra_state_attributes = {
                ATTR_STREAM_URL: source,
                ATTR_SIP_LOGIN: updater.data.get(f"{description.key}_{ATTR_SIP_LOGIN}"),
            }

        GenericCamera.__init__(
            self,
            self.hass,
            {
                CONF_STREAM_SOURCE: source,
                CONF_AUTHENTICATION: HTTP_BASIC_AUTHENTICATION,
                CONF_LIMIT_REFETCH_TO_URL_CHANGE: False,
                CONF_NAME: description.name,
                CONF_CONTENT_TYPE: DEFAULT_CONTENT_TYPE,
                CONF_FRAMERATE: 2,
                CONF_VERIFY_SSL: False,
            },
            unique_id,
            description.name,
        )
        IntercomEntity.__init__(self, unique_id, description, updater, ENTITY_ID_FORMAT)

        self._attr_brand = MAINTAINER

        self._attr_stream_url = source

        if device_info:
            self._attr_device_info = device_info

    @property
    def available(self) -> bool:
        """Is available

        :return bool: Is available
        """

        return self.coordinator.last_update_success and len(self._attr_stream_url) > 0

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""

        await GenericCamera.async_added_to_hass(self)
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

        key: str = f"{self.entity_description.key}_{ATTR_STREAM_URL}"

        if (
            self.entity_description.key == CAMERA_INCOMING
            and self._updater.last_call
            and self._updater.last_call.login in self._updater.code_map
            and self._updater.last_call.state in (CallState.RINGING, CallState.ANSWERED)
        ):
            key = f"{self._updater.code_map[self._updater.last_call.login]}_{ATTR_STREAM_URL}"

        _stream_url: str = self._updater.data.get(key, "")

        if self._attr_stream_url == _stream_url:  # type: ignore
            return

        self._attr_stream_url = _stream_url

        _stream_source: template_helper.Template = cv.template(_stream_url)
        _stream_source.hass = self.hass

        self._stream_source = _stream_source

        self._attr_is_streaming = _stream_url != ""

        self.async_write_ha_state()

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:  # pragma: no cover
        """Return a still image response from the camera.

        :param width: int | None
        :param height: int | None
        :return bytes | None
        """

        with contextlib.suppress(AttributeError):
            return await GenericCamera.async_camera_image(self, width, height)

        return None
