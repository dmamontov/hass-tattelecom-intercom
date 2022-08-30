"""Diagnostic."""

from __future__ import annotations

from typing import Final

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_TOKEN
from homeassistant.core import HomeAssistant

from .const import CONF_LOGIN, CONF_PHONE, CONF_SMS_CODE
from .updater import async_get_updater

TO_REDACT: Final = {
    CONF_PHONE,
    CONF_LOGIN,
    CONF_SMS_CODE,
    CONF_TOKEN,
    "sip_login",
    "sip_password",
    "title",
    "unique_id",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> dict:
    """Return diagnostics for a config entry."""

    _data: dict = {"config_entry": async_redact_data(config_entry.as_dict(), TO_REDACT)}

    if _updater := async_get_updater(hass, config_entry.entry_id):
        if hasattr(_updater, "data"):
            _data["data"] = async_redact_data(_updater.data, TO_REDACT)

        if len(_updater.client.diagnostics) > 0:  # pragma: no cover
            _data["requests"] = async_redact_data(
                _updater.client.diagnostics, TO_REDACT
            )

        if hasattr(_updater, "intercoms") and _updater.intercoms:
            _data["intercoms"] = list(_updater.intercoms.keys())

        if hasattr(_updater, "code_map") and _updater.code_map:
            _data["code_map"] = _updater.code_map

        if _updater.voip and _updater.voip.diagnostics:
            _data |= _updater.voip.diagnostics

    return _data
