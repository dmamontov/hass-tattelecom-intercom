"""Provide info to system health."""

from __future__ import annotations

import logging

from homeassistant.components.system_health import SystemHealthRegistration
from homeassistant.core import HomeAssistant, callback

from .const import ATTR_UPDATE_STATE, DOMAIN, UPDATER
from .helper import async_get_version
from .updater import IntercomUpdater

_LOGGER = logging.getLogger(__name__)


@callback
def async_register(hass: HomeAssistant, register: SystemHealthRegistration) -> None:
    """Register system health info

    :param hass: HomeAssistant
    :param register: SystemHealthRegistration
    """

    register.async_register_info(system_health_info)


async def system_health_info(hass: HomeAssistant) -> dict[str, str]:
    """System health info

    :param hass: HomeAssistant
    :return dict[str, Any]
    """

    info: dict[str, str] = {
        "version": f"{await async_get_version(hass)}",
    }

    for integration in hass.data[DOMAIN].values():
        updater: IntercomUpdater = integration[UPDATER]

        info |= {
            "update_state": "error"
            if updater.data.get(ATTR_UPDATE_STATE, False)
            else "ok",
            "sip_state": updater.voip.status.value if updater.voip else "unknown",
        }

        break

    return info
