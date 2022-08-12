"""Camera component."""


from __future__ import annotations

import logging

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
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv, template as template_helper
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import ATTR_STREAM_URL, CAMERA_NAME, MAINTAINER, SIGNAL_NEW_INTERCOM
from .entity import IntercomEntity
from .updater import IntercomEntityDescription, IntercomUpdater, async_get_updater

PARALLEL_UPDATES = 0

_LOGGER = logging.getLogger(__name__)


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
                    entity,
                    updater,
                )
            ]
        )

    for intercom in updater.intercoms.values():
        add_camera(intercom)

    updater.new_intercom_callbacks.append(
        async_dispatcher_connect(hass, SIGNAL_NEW_INTERCOM, add_camera)
    )


class IntercomCamera(IntercomEntity, GenericCamera):
    """Intercom camera entry."""

    _attr_field: str
    _attr_stream_url: str

    def __init__(
        self,
        unique_id: str,
        entity: IntercomEntityDescription,
        updater: IntercomUpdater,
    ) -> None:
        """Initialize camera.

        :param unique_id: str: Unique ID
        :param entity: IntercomEntityDescription object
        :param updater: IntercomUpdater: Intercom updater object
        """

        _description: EntityDescription = EntityDescription(
            key=str(entity.id),
            name=CAMERA_NAME,
            icon="mdi:doorbell-video",
            entity_registry_enabled_default=True,
        )

        self._attr_field = f"{_description.key}_{ATTR_STREAM_URL}"

        GenericCamera.__init__(
            self,
            self.hass,
            {
                CONF_STREAM_SOURCE: updater.data.get(self._attr_field),
                CONF_AUTHENTICATION: HTTP_BASIC_AUTHENTICATION,
                CONF_LIMIT_REFETCH_TO_URL_CHANGE: False,
                CONF_NAME: CAMERA_NAME,
                CONF_CONTENT_TYPE: DEFAULT_CONTENT_TYPE,
                CONF_FRAMERATE: 2,
                CONF_VERIFY_SSL: True,
            },
            unique_id,
            CAMERA_NAME,
        )
        IntercomEntity.__init__(
            self, unique_id, _description, updater, ENTITY_ID_FORMAT
        )

        self._attr_available = True
        self._attr_brand = MAINTAINER

        self._attr_stream_url = updater.data.get(self._attr_field, "")

        self._attr_device_info = entity.device_info

    def _handle_coordinator_update(self) -> None:
        """Update state."""

        _stream_url: str = self._updater.data.get(self._attr_field, "")

        if self._attr_stream_url == _stream_url:  # type: ignore
            return

        self._attr_stream_url = _stream_url

        _stream_source: template_helper.Template = cv.template(_stream_url)
        _stream_source.hass = self.hass

        self._stream_source = _stream_source

        self.async_write_ha_state()
