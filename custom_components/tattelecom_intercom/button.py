"""Button component."""


from __future__ import annotations

import logging

from homeassistant.components.button import (
    ENTITY_ID_FORMAT,
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import ATTR_STATE, BUTTON_OPEN_NAME, SIGNAL_NEW_INTERCOM
from .entity import IntercomEntity
from .updater import IntercomEntityDescription, IntercomUpdater, async_get_updater

PARALLEL_UPDATES = 0

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tattelecom intercom button entry.

    :param hass: HomeAssistant: Home Assistant object
    :param config_entry: ConfigEntry: ConfigEntry object
    :param async_add_entities: AddEntitiesCallback: AddEntitiesCallback callback object
    """

    updater: IntercomUpdater = async_get_updater(hass, config_entry.entry_id)

    @callback
    def add_button(entity: IntercomEntityDescription) -> None:
        """Add button.

        :param entity: IntercomEntityDescription: Sensor object
        """

        async_add_entities(
            [
                IntercomButton(
                    f"{config_entry.entry_id}-button-{entity.id}",
                    entity,
                    updater,
                )
            ]
        )

    for intercom in updater.intercoms.values():
        add_button(intercom)

    updater.new_intercom_callbacks.append(
        async_dispatcher_connect(hass, SIGNAL_NEW_INTERCOM, add_button)
    )


class IntercomButton(IntercomEntity, ButtonEntity):
    """Intercom button entry."""

    def __init__(
        self,
        unique_id: str,
        entity: IntercomEntityDescription,
        updater: IntercomUpdater,
    ) -> None:
        """Initialize button.

        :param unique_id: str: Unique ID
        :param entity: IntercomEntityDescription object
        :param updater: IntercomUpdater: Intercom updater object
        """

        _description: ButtonEntityDescription = ButtonEntityDescription(
            key=str(entity.id),
            name=BUTTON_OPEN_NAME,
            icon="mdi:lock-open",
            entity_category=EntityCategory.CONFIG,
            entity_registry_enabled_default=True,
        )

        IntercomEntity.__init__(
            self, unique_id, _description, updater, ENTITY_ID_FORMAT
        )

        self._attr_device_info = entity.device_info

    def _handle_coordinator_update(self) -> None:
        """Update state."""

        is_available: bool = self._updater.data.get(ATTR_STATE, False)

        if self._attr_available == is_available:  # type: ignore
            return

        self._attr_available = is_available

        self.async_write_ha_state()

    async def async_press(self) -> None:
        """Async press action."""

        await self._updater.client.open(int(self.entity_description.key))
