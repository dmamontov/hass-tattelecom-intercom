"""General constants."""
from __future__ import annotations

from typing import Final

from aiohttp.hdrs import ACCEPT, ACCEPT_CHARSET, ACCEPT_ENCODING, USER_AGENT
from homeassistant.const import Platform

# fmt: off
DOMAIN: Final = "tattelecom_intercom"
NAME: Final = "Tattelecom Intercom"
MAINTAINER: Final = "Tattelecom"
ATTRIBUTION: Final = "Data provided by Tattelecom Intercom"

PLATFORMS: Final = [
    Platform.BINARY_SENSOR,
    Platform.CAMERA,
    Platform.BUTTON,
    Platform.SWITCH,
]

"""Diagnostic const"""
DIAGNOSTIC_DATE_TIME: Final = "date_time"
DIAGNOSTIC_MESSAGE: Final = "message"
DIAGNOSTIC_CONTENT: Final = "content"

"""Helper const"""
UPDATER: Final = "updater"
UPDATE_LISTENER: Final = "update_listener"
OPTION_IS_FROM_FLOW: Final = "is_from_flow"
SIGNAL_NEW_INTERCOM: Final = f"{DOMAIN}-new-intercom"

CONF_PHONE: Final = "phone"
CONF_LOGIN: Final = "login"
CONF_SMS_CODE: Final = "sms_code"

PHONE_MIN: Final = 70000000000
PHONE_MAX: Final = 79999999999
SMS_CODE_LENGTH: Final = 6

"""Default settings"""
DEFAULT_SCAN_INTERVAL: Final = 3600
DEFAULT_TIMEOUT: Final = 10
DEFAULT_CALL_DELAY: Final = 1
DEFAULT_SLEEP: Final = 3

"""Tattelecom intercom API client const"""
CLIENT_URL: Final = "https://domofon.tattelecom.ru/{api_version}/{path}"
HEADERS: Final = {
    ACCEPT: "application/json",
    ACCEPT_CHARSET: "UTF-8",
    USER_AGENT: "Ktor client",
    ACCEPT_ENCODING: "gzip",
}
DEVICE_CODE: Final = "Android_empty_push_token"
DEVICE_OS: Final = 1

"""Attributes"""
ATTR_STATE: Final = "state"
ATTR_STATE_NAME: Final = "State"

ATTR_SIP_STATE: Final = "sip_state"
ATTR_SIP_STATE_NAME: Final = "Sip state"

ATTR_SIP_ADDRESS: Final = "sip_address"
ATTR_SIP_LOGIN: Final = "sip_login"
ATTR_SIP_PASSWORD: Final = "sip_password"
ATTR_SIP_PORT: Final = "sip_port"

ATTR_STREAM_URL: Final = "stream_url"
ATTR_MUTE: Final = "mute"

"""Attributes camera"""
CAMERA_NAME: Final = "Camera"

"""Attributes button"""
BUTTON_OPEN_NAME: Final = "Open door"

"""Attributes switch"""
SWITCH_MUTE_NAME: Final = "Mute"
