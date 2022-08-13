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


def byte_to_bits(byte: bytes) -> str:
    """Byte to bits

    :param byte: bytes
    :return str
    """

    if not byte:  # pragma: no cover
        return ""

    _byte = bin(ord(byte)).lstrip("-0b")

    return ("0" * (8 - len(_byte))) + _byte


def add_bytes(bytes_string: bytes) -> int:
    """Add bytes

    :param bytes_string: bytes
    :return int
    """

    binary = ""
    for byte in bytes_string:
        _byte = bin(byte).lstrip("-0b")
        binary += ("0" * (8 - len(_byte))) + _byte

    return int(binary, 2)


class Counter:  # pylint: disable=too-few-public-methods
    """Counter class"""

    _cnt: int

    def __init__(self, start: int = 1) -> None:
        """Init

        :param start: int
        """

        self._cnt = start

    def next(self) -> int:
        """Get next count

        :return int
        """

        cnt = self._cnt
        self._cnt += 1

        return cnt
