"""Sensor component."""

# pylint: disable=using-constant-test,missing-parentheses-for-call-in-test

from __future__ import annotations

import logging
from typing import Final

from homeassistant.components.sensor import (
    ENTITY_ID_FORMAT,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_UPDATE_STATE,
    SENSOR_CALL_STATE,
    SENSOR_CALL_STATE_NAME,
    SENSOR_SIP_STATE,
    SENSOR_SIP_STATE_NAME,
    SIGNAL_CALL_STATE,
    SIGNAL_SIP_STATE,
)
from .entity import IntercomEntity
from .enum import CallState, VoipState, DeviceClass
from .updater import IntercomUpdater, async_get_updater

PARALLEL_UPDATES = 0

ICONS: Final = {
    SENSOR_CALL_STATE: {
        CallState.RINGING.value: "mdi:phone-ring",
        CallState.ANSWERED.value: "mdi:phone-incoming-outgoing",
        CallState.ENDED.value: "mdi:phone-hangup",
    }
}

EVENTS: Final = {
    SENSOR_SIP_STATE: SIGNAL_SIP_STATE,
    SENSOR_CALL_STATE: SIGNAL_CALL_STATE,
}

SENSORS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key=SENSOR_SIP_STATE,
        name=SENSOR_SIP_STATE_NAME,
        icon="mdi:phone-voip",
        device_class=DeviceClass.SIP_STATE,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=True,
    ),
    SensorEntityDescription(
        key=SENSOR_CALL_STATE,
        name=SENSOR_CALL_STATE_NAME,
        icon=ICONS[SENSOR_CALL_STATE][CallState.ENDED.value],
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=DeviceClass.CALL_STATE,
        entity_registry_enabled_default=True,
    ),
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Intercom sensor entry.

    :param hass: HomeAssistant: Home Assistant object
    :param config_entry: ConfigEntry: Config Entry object
    :param async_add_entities: AddEntitiesCallback: Async add callback
    """

    updater: IntercomUpdater = async_get_updater(hass, config_entry.entry_id)

    entities: list[IntercomSensor] = [
        IntercomSensor(
            f"{config_entry.entry_id}-{description.key}", description, updater
        )
        for description in SENSORS
    ]
    async_add_entities(entities)


# pylint: disable=too-many-ancestors
class IntercomSensor(IntercomEntity, SensorEntity):
    """Intercom sensor entry."""

    _unsub_update: CALLBACK_TYPE

    def __init__(
        self,
        unique_id: str,
        description: SensorEntityDescription,
        updater: IntercomUpdater,
    ) -> None:
        """Initialize sensor.

        :param unique_id: str: Unique ID
        :param description: SensorEntityDescription: SensorEntityDescription object
        :param updater: IntercomUpdater: Intercom updater object
        """

        IntercomEntity.__init__(self, unique_id, description, updater, ENTITY_ID_FORMAT)

        self._attr_available: bool = updater.data.get(ATTR_UPDATE_STATE, False)

        if description.key == SENSOR_SIP_STATE:
            self._attr_native_value = str(
                updater.voip.status.value if updater.voip else VoipState.INACTIVE.value
            )
        elif description.key == SENSOR_CALL_STATE:
            self._attr_native_value = str(
                updater.last_call.state.value
                if updater.last_call
                else CallState.ENDED.value
            )

        self._change_icon()

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""

        await CoordinatorEntity.async_added_to_hass(self)

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

        is_available: bool = self._updater.data.get(ATTR_UPDATE_STATE, False)

        native_value: str | None = None

        if self.entity_description.key == SENSOR_SIP_STATE:
            native_value = str(
                self._updater.voip.status.value
                if self._updater.voip
                else VoipState.INACTIVE.value
            )
        elif self.entity_description.key == SENSOR_CALL_STATE:
            native_value = str(
                self._updater.last_call.state.value
                if self._updater.last_call
                else CallState.ENDED.value
            )

        if (
            self._attr_native_value == native_value
            and self._attr_available == is_available  # type: ignore
        ):
            return

        self._attr_available = is_available
        self._attr_native_value = native_value  # type: ignore

        self._change_icon()

        self.async_write_ha_state()

    def _change_icon(self) -> None:
        """Change icon"""

        if (
            self.entity_description.key in ICONS
            and self._attr_native_value in ICONS[self.entity_description.key]
        ):
            self._attr_icon = ICONS[self.entity_description.key][
                self._attr_native_value
            ]
