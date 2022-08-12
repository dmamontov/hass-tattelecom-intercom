"""Integration helper."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration
from homeassistant.util import slugify

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


def get_config_value(
    config_entry: config_entries.ConfigEntry | None, param: str, default=None
) -> Any:
    """Get current value for configuration parameter.

    :param config_entry: config_entries.ConfigEntry|None: config entry from Flow
    :param param: str: parameter name for getting value
    :param default: default value for parameter, defaults to None
    :return Any: parameter value, or default value or None
    """

    return (
        config_entry.options.get(param, config_entry.data.get(param, default))
        if config_entry is not None
        else default
    )


async def async_get_version(hass: HomeAssistant) -> str:
    """Get the documentation url for creating a local user.

    :param hass: HomeAssistant: Home Assistant object
    :return str: Documentation URL
    """

    integration = await async_get_integration(hass, DOMAIN)

    return f"{integration.version}"


def generate_entity_id(
    entity_id_format: str, phone: int, name: str | None = None
) -> str:
    """Generate Entity ID

    :param entity_id_format: str: Format
    :param phone: int: Phone number
    :param name: str | None: Name
    :return str: Entity ID
    """

    _name: str = f"_{name}" if name is not None else ""

    return entity_id_format.format(slugify(f"{DOMAIN}_{phone}{_name}".lower()))
