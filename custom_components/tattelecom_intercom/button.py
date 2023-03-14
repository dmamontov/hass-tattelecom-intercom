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
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    BUTTON_ANSWER,
    BUTTON_ANSWER_NAME,
    BUTTON_DECLINE,
    BUTTON_DECLINE_NAME,
    BUTTON_HANGUP,
    BUTTON_HANGUP_NAME,
    BUTTON_OPEN,
    BUTTON_OPEN_NAME,
    SIGNAL_CALL_STATE,
    SIGNAL_NEW_INTERCOM,
)
from .entity import IntercomEntity
from .exceptions import IntercomError
from .updater import IntercomEntityDescription, IntercomUpdater, async_get_updater

PARALLEL_UPDATES = 0

_LOGGER = logging.getLogger(__name__)

BUTTONS: tuple[ButtonEntityDescription, ...] = (
    ButtonEntityDescription(
        key=BUTTON_ANSWER,
        name=BUTTON_ANSWER_NAME,
        icon="mdi:phone-in-talk",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=True,
    ),
    ButtonEntityDescription(
        key=BUTTON_DECLINE,
        name=BUTTON_DECLINE_NAME,
        icon="mdi:phone-cancel",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=True,
    ),
    ButtonEntityDescription(
        key=BUTTON_HANGUP,
        name=BUTTON_HANGUP_NAME,
        icon="mdi:phone-hangup",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=True,
    ),
    ButtonEntityDescription(
        key=BUTTON_OPEN,
        name=BUTTON_OPEN_NAME,
        icon="mdi:lock-open",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=True,
    ),
)


# pylint: disable=too-many-ancestors
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
                    ButtonEntityDescription(
                        key=str(entity.id),
                        name=BUTTON_OPEN_NAME,
                        icon="mdi:lock-open",
                        entity_category=EntityCategory.CONFIG,
                        entity_registry_enabled_default=True,
                    ),
                    updater,
                    entity.device_info,
                )
            ]
        )

    entities: list[IntercomButton] = [
        IntercomButton(
            f"{config_entry.entry_id}-{description.key}", description, updater
        )
        for description in BUTTONS
    ]
    async_add_entities(entities)

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
        description: ButtonEntityDescription,
        updater: IntercomUpdater,
        device_info: DeviceInfo | None = None,
    ) -> None:
        """Initialize button.

        :param unique_id: str: Unique ID
        :param description: ButtonEntityDescription object
        :param updater: IntercomUpdater: Intercom updater object
        :param device_info: DeviceInfo | None: DeviceInfo object
        """

        IntercomEntity.__init__(self, unique_id, description, updater, ENTITY_ID_FORMAT)

        if device_info:
            self._attr_device_info = device_info

    async def async_press(self) -> None:
        """Async press action."""

        try:
            intercom_id: str = str(self.entity_description.key)

            if self.entity_description.key == BUTTON_OPEN:
                if (
                    not self._updater.last_call
                    or self._updater.last_call.login not in self._updater.code_map
                ):
                    _LOGGER.error("Intercom not found.")

                    return

                intercom_id = str(self._updater.code_map[self._updater.last_call.login])

            if self.entity_description.key not in (
                BUTTON_ANSWER,
                BUTTON_DECLINE,
                BUTTON_HANGUP,
            ):
                await self._updater.client.open(int(intercom_id))

                return

            if not self._updater.last_call:
                _LOGGER.error("There is no active call.")

                return

            if self.entity_description.key == BUTTON_ANSWER:
                await self._updater.last_call.answer()
            elif self.entity_description.key == BUTTON_DECLINE:
                await self._updater.last_call.decline()
            elif self.entity_description.key == BUTTON_HANGUP:
                await self._updater.last_call.hangup()

            async_dispatcher_send(self.hass, SIGNAL_CALL_STATE)
        except IntercomError as _err:
            _LOGGER.error(
                "An error occurred while pressing the button %r: %r",
                self.entity_description.key,
                _err,
            )
