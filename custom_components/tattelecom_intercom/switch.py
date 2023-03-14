"""Switch component."""


from __future__ import annotations

import logging
from typing import Any, Final

from homeassistant.components.switch import (
    ENTITY_ID_FORMAT,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import ATTR_MUTE, SIGNAL_NEW_INTERCOM, SWITCH_MUTE_NAME
from .entity import IntercomEntity
from .exceptions import IntercomError
from .updater import IntercomEntityDescription, IntercomUpdater, async_get_updater

PARALLEL_UPDATES = 0

ICONS: Final = {
    STATE_ON: "mdi:bell-off",
    STATE_OFF: "mdi:bell",
}

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tattelecom intercom switch entry.

    :param hass: HomeAssistant: Home Assistant object
    :param config_entry: ConfigEntry: ConfigEntry object
    :param async_add_entities: AddEntitiesCallback: AddEntitiesCallback callback object
    """

    updater: IntercomUpdater = async_get_updater(hass, config_entry.entry_id)

    @callback
    def add_switch(entity: IntercomEntityDescription) -> None:
        """Add switch.

        :param entity: IntercomEntityDescription: Sensor object
        """

        async_add_entities(
            [
                IntercomSwitch(
                    f"{config_entry.entry_id}-switch-{entity.id}",
                    entity,
                    updater,
                )
            ]
        )

    for intercom in updater.intercoms.values():
        add_switch(intercom)

    updater.new_intercom_callbacks.append(
        async_dispatcher_connect(hass, SIGNAL_NEW_INTERCOM, add_switch)
    )


# pylint: disable=too-many-ancestors
class IntercomSwitch(IntercomEntity, SwitchEntity):
    """Intercom switch entry."""

    _attr_field: str

    def __init__(
        self,
        unique_id: str,
        entity: IntercomEntityDescription,
        updater: IntercomUpdater,
    ) -> None:
        """Initialize switch.

        :param unique_id: str: Unique ID
        :param entity: IntercomEntityDescription object
        :param updater: IntercomUpdater: Intercom updater object
        """

        _description: SwitchEntityDescription = SwitchEntityDescription(
            key=str(entity.id),
            name=SWITCH_MUTE_NAME,
            entity_category=EntityCategory.CONFIG,
            entity_registry_enabled_default=True,
        )

        IntercomEntity.__init__(
            self, unique_id, _description, updater, ENTITY_ID_FORMAT
        )

        self._attr_device_info = entity.device_info

        self._attr_field = f"{_description.key}_{ATTR_MUTE}"

        self._attr_is_on = bool(updater.data.get(self._attr_field, False))

        self._change_icon(self._attr_is_on)

    def _handle_coordinator_update(self) -> None:
        """Update state."""

        is_on: bool = self._updater.data.get(self._attr_field, False)

        if self._attr_is_on == is_on:  # type: ignore
            return

        self._attr_is_on = is_on

        self._change_icon(self._attr_is_on)

        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Set turn on

        :param **kwargs: Any
        """

        try:
            await self._updater.client.mute(int(self.entity_description.key))

            self._attr_is_on = True
            self._change_icon(self._attr_is_on)
            self._updater.update_data(self._attr_field, self._attr_is_on)
        except IntercomError as _err:
            _LOGGER.error("An error occurred while enabling mute: %r", _err)

        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Set turn off

        :param **kwargs: Any
        """

        try:
            await self._updater.client.unmute(int(self.entity_description.key))

            self._attr_is_on = False
            self._change_icon(self._attr_is_on)
            self._updater.update_data(self._attr_field, self._attr_is_on)
        except IntercomError as _err:
            _LOGGER.error("An error occurred while disabling mute: %r", _err)

        self.async_write_ha_state()

    def _change_icon(self, is_on: bool) -> None:
        """Change icon

        :param is_on: bool
        """

        icon_name: str = STATE_ON if is_on else STATE_OFF

        if icon_name in ICONS:
            self._attr_icon = ICONS[icon_name]
