"""Binary sensor component."""

from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    ENTITY_ID_FORMAT,
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import ATTR_UPDATE_STATE, ATTR_UPDATE_STATE_NAME
from .entity import IntercomEntity
from .updater import IntercomUpdater, async_get_updater

PARALLEL_UPDATES = 0

BINARY_SENSORS: tuple[BinarySensorEntityDescription, ...] = (
    BinarySensorEntityDescription(
        key=ATTR_UPDATE_STATE,
        name=ATTR_UPDATE_STATE_NAME,
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=True,
    ),
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Intercom binary sensor entry.

    :param hass: HomeAssistant: Home Assistant object
    :param config_entry: ConfigEntry: Config Entry object
    :param async_add_entities: AddEntitiesCallback: Async add callback
    """

    updater: IntercomUpdater = async_get_updater(hass, config_entry.entry_id)

    entities: list[IntercomBinarySensor] = [
        IntercomBinarySensor(
            f"{config_entry.entry_id}-{description.key}",
            description,
            updater,
        )
        for description in BINARY_SENSORS
    ]
    async_add_entities(entities)


# pylint: disable=too-many-ancestors
class IntercomBinarySensor(IntercomEntity, BinarySensorEntity):
    """Intercom binary sensor entry."""

    def __init__(
        self,
        unique_id: str,
        description: BinarySensorEntityDescription,
        updater: IntercomUpdater,
    ) -> None:
        """Initialize sensor.

        :param unique_id: str: Unique ID
        :param description: BinarySensorEntityDescription: BinarySensorEntityDescription object
        :param updater: IntercomUpdater: Intercom updater object
        """

        IntercomEntity.__init__(self, unique_id, description, updater, ENTITY_ID_FORMAT)

        self._attr_available: bool = (
            updater.data.get(ATTR_UPDATE_STATE, False)
            if description.key != ATTR_UPDATE_STATE
            else True
        )

        self._attr_is_on = updater.data.get(description.key, False)

    def _handle_coordinator_update(self) -> None:
        """Update state."""

        is_available: bool = (
            self._updater.data.get(ATTR_UPDATE_STATE, False)
            if self.entity_description.key != ATTR_UPDATE_STATE
            else True
        )

        is_on: bool = self._updater.data.get(self.entity_description.key, False)

        if self._attr_is_on == is_on and self._attr_available == is_available:  # type: ignore
            return

        self._attr_available = is_available
        self._attr_is_on = is_on

        self.async_write_ha_state()
