"""Tattelecom Intercom data updater."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta
from functools import cached_property
from typing import Any

from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import event
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity import DeviceEntryType, DeviceInfo
from homeassistant.helpers.httpx_client import get_async_client
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import utcnow
from httpx import codes
from pyVoIP.VoIP import InvalidStateError, VoIPCall, VoIPPhone

from .client import IntercomClient
from .const import (
    ATTR_MUTE,
    ATTR_SIP_ADDRESS,
    ATTR_SIP_LOGIN,
    ATTR_SIP_PASSWORD,
    ATTR_SIP_PORT,
    ATTR_SIP_STATE,
    ATTR_STATE,
    ATTR_STREAM_URL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DOMAIN,
    MAINTAINER,
    NAME,
    SIGNAL_NEW_INTERCOM,
    UPDATER,
)
from .exceptions import IntercomError, IntercomUnauthorizedError

_LOGGER = logging.getLogger(__name__)


# pylint: disable=too-many-branches,too-many-lines,too-many-arguments
class IntercomUpdater(DataUpdateCoordinator):
    """Tattelecom Intercom data updater for interaction with Tattelecom intercom API."""

    client: IntercomClient
    sip_client: VoIPPhone | None = None

    code: codes = codes.BAD_GATEWAY

    phone: int
    token: str

    new_intercom_callbacks: list[CALLBACK_TYPE] = []

    _scan_interval: int

    def __init__(
        self,
        hass: HomeAssistant,
        phone: int,
        token: str,
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize updater.

        :rtype: object
        :param hass: HomeAssistant: Home Assistant object
        :param phone: int: Phone number
        :param token: str: Token
        :param scan_interval: int: Update interval
        :param timeout: int: Query execution timeout
        """

        self.client = IntercomClient(
            get_async_client(hass, False),
            phone,
            token,
            timeout,
        )

        self.phone = phone

        self._scan_interval = scan_interval

        if hass is not None:
            super().__init__(
                hass,
                _LOGGER,
                name=f"{NAME} updater",
                update_interval=self._update_interval,
                update_method=self.update,
            )

        self.data: dict[str, Any] = {}

        self.intercoms: dict[str, IntercomEntityDescription] = {}

        self._is_first_update: bool = True

    async def async_stop(self) -> None:
        """Stop updater"""

        if self.sip_client and self.data.get(ATTR_SIP_STATE, False):
            self.sip_client.stop()

        for _callback in self.new_intercom_callbacks:
            _callback()  # pylint: disable=not-callable

    @cached_property
    def _update_interval(self) -> timedelta:
        """Update interval

        :return timedelta: update_interval
        """

        return timedelta(seconds=self._scan_interval)

    async def update(self) -> dict:
        """Update Intercom information.

        :return dict: dict with Intercom data.
        """

        self.code = codes.OK

        _err: IntercomError | None = None

        try:
            await self._async_prepare(self.data)
        except IntercomUnauthorizedError as _e:
            raise ConfigEntryAuthFailed(_e) from _e
        except IntercomError as _e:
            _err = _e

            self.code = codes.SERVICE_UNAVAILABLE

        self.data[ATTR_STATE] = codes.is_success(self.code)

        return self.data

    def update_data(self, field: str, value: Any) -> None:
        """Update data

        :param field: str
        :param value: Any
        """

        self.data[field] = value

    @property
    def device_info(self) -> DeviceInfo:
        """Device info.

        :return DeviceInfo: Service DeviceInfo.
        """

        return DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, str(self.phone))},
            name=NAME,
            manufacturer=MAINTAINER,
        )

    def schedule_refresh(self, offset: timedelta) -> None:
        """Schedule refresh.

        :param offset: timedelta
        """

        if self._unsub_refresh:  # type: ignore
            self._unsub_refresh()  # type: ignore
            self._unsub_refresh = None

        self._unsub_refresh = event.async_track_point_in_utc_time(
            self.hass,
            self._job,
            utcnow().replace(microsecond=0) + offset,
        )

    async def _async_prepare(self, data: dict) -> None:
        """Prepare data.

        :param data: dict
        """

        await self._async_prepare_intercoms(data)
        await self._async_prepare_sip_settings(data)

    async def _async_prepare_intercoms(self, data: dict) -> None:
        """Prepare intercoms.

        :param data: dict
        """

        response: dict = await self.client.intercoms()

        if "addresses" in response:
            for address, intercoms in response["addresses"].items():
                for intercom in intercoms:
                    for attr in [ATTR_STREAM_URL, ATTR_MUTE, ATTR_SIP_LOGIN]:
                        data[f"{intercom['id']}_{attr}"] = intercom[attr]

                    if intercom["id"] in self.intercoms:
                        continue

                    self.intercoms[intercom["id"]] = IntercomEntityDescription(
                        id=intercom["id"],
                        device_info=DeviceInfo(
                            identifiers={(DOMAIN, str(intercom["id"]))},
                            name=" ".join(
                                [
                                    address,
                                    intercom.get(
                                        "gate_name", intercom.get("intercom_name", "")
                                    ),
                                ]
                            ).strip(),
                            manufacturer=MAINTAINER,
                        ),
                    )

                    if self.new_intercom_callbacks:
                        async_dispatcher_send(
                            self.hass,
                            SIGNAL_NEW_INTERCOM,
                            self.intercoms[intercom["id"]],
                        )

    async def _async_prepare_sip_settings(self, data: dict) -> None:
        """Prepare sip_settings.

        :param data: dict
        """

        response: dict = await self.client.sip_settings()

        if "success" in response and response["success"]:
            del response["success"]

            _need_init: bool = any(
                code not in data or value != data[code]
                for code, value in response.items()
            )

            data |= response

            if _need_init:
                self._start_sip(
                    response[ATTR_SIP_ADDRESS],
                    response[ATTR_SIP_LOGIN],
                    response[ATTR_SIP_PASSWORD],
                    response[ATTR_SIP_PORT],
                )

    def _start_sip(self, address: str, login: str, password: str, port: int) -> None:
        """Start sip

        :param address: str: SIP address
        :param login: str: SIP login
        :param password: str: SIP password
        :param port: str: SIP port
        """

        if self.sip_client:
            self.sip_client.stop()

        self.sip_client = VoIPPhone(address, port, login, password, self._sip_callback)

        #try:
        # self.sip_client.start()
        # self.data[ATTR_SIP_STATE] = True
        # _LOGGER.error("RRR {}".format(self.sip_client.call("D108614")))
        # except OSError as _err:
        #     _LOGGER.error("SIP start error: %r", _err)
        #
        #     self.data[ATTR_SIP_STATE] = False

    @callback
    def _sip_callback(self, call: VoIPCall) -> None:
        """SIP Callback"""

        _LOGGER.error("RRR {}".format(call))

        try:
            call.answer()
            call.hangup()
        except InvalidStateError as err:
            _LOGGER.error("RRR %r", err)


@dataclass
class IntercomEntityDescription:
    """Intercom entity description."""

    # pylint: disable=invalid-name
    id: int
    device_info: DeviceInfo


@callback
def async_get_updater(hass: HomeAssistant, identifier: str) -> IntercomUpdater:
    """Return IntercomUpdater for username or entry id.

    :param hass: HomeAssistant
    :param identifier: str
    :return IntercomUpdater
    """

    if (
        DOMAIN not in hass.data
        or identifier not in hass.data[DOMAIN]
        or UPDATER not in hass.data[DOMAIN][identifier]
    ):
        raise ValueError(f"Integration with identifier: {identifier} not found.")

    return hass.data[DOMAIN][identifier][UPDATER]
