"""Tattelecom Intercom entity."""

from __future__ import annotations

import logging

from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION
from .helper import generate_entity_id
from .updater import IntercomUpdater

_LOGGER = logging.getLogger(__name__)


class IntercomEntity(CoordinatorEntity):
    """Tattelecom Intercom entity."""

    _attr_attribution: str = ATTRIBUTION
    _attr_id: int = -1

    def __init__(
        self,
        unique_id: str,
        description: EntityDescription,
        updater: IntercomUpdater,
        entity_id_format: str,
    ) -> None:
        """Initialize entity.

        :param unique_id: str: Unique ID
        :param description: EntityDescription: EntityDescription object
        :param updater: IntercomUpdater: Intercom updater object
        :param entity_id_format: str: ENTITY_ID_FORMAT
        """

        CoordinatorEntity.__init__(self, coordinator=updater)

        self.entity_description = description
        self._updater: IntercomUpdater = updater

        self.entity_id = generate_entity_id(
            entity_id_format,
            updater.phone,
            description.key,
        )

        self._attr_name = description.name
        self._attr_unique_id = unique_id

        self._attr_device_info = updater.device_info

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""

        await CoordinatorEntity.async_added_to_hass(self)

    @property
    def available(self) -> bool:
        """Is available

        :return bool: Is available
        """

        return self.coordinator.last_update_success

    def _handle_coordinator_update(self) -> None:
        """Update state."""

        self.async_write_ha_state()  # pragma: no cover
