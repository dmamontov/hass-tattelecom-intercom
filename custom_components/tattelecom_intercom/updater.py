"""Tattelecom Intercom data updater."""


from __future__ import annotations

import asyncio
import contextlib
import logging
from dataclasses import dataclass
from datetime import timedelta
from functools import cached_property
from random import randint
from typing import Any

from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import event
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.httpx_client import create_async_httpx_client
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import utcnow
from httpx import AsyncHTTPTransport, codes

from .client import IntercomClient
from .const import (
    ATTR_MUTE,
    ATTR_SIP_ADDRESS,
    ATTR_SIP_LOGIN,
    ATTR_SIP_PASSWORD,
    ATTR_SIP_PORT,
    ATTR_STREAM_URL,
    ATTR_STREAM_URL_MPEG,
    ATTR_UPDATE_STATE,
    DEFAULT_RETRY,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DOMAIN,
    MAINTAINER,
    NAME,
    SIGNAL_CALL_STATE,
    SIGNAL_NEW_INTERCOM,
    SIP_DEFAULT_RETRY,
    UPDATER,
)
from .exceptions import (
    IntercomConnectionError,
    IntercomError,
    IntercomUnauthorizedError,
)
from .voip import Call, IntercomVoip

_LOGGER = logging.getLogger(__name__)


# pylint: disable=too-many-branches,too-many-lines,too-many-arguments
class IntercomUpdater(DataUpdateCoordinator):
    """Tattelecom Intercom data updater for interaction with Tattelecom intercom API."""

    client: IntercomClient

    voip: IntercomVoip | None = None
    last_call: Call | None = None

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

        _transport: AsyncHTTPTransport = AsyncHTTPTransport(
            http1=False, http2=True, retries=3
        )
        self.client = IntercomClient(
            create_async_httpx_client(
                hass, True, http1=False, http2=True, transport=_transport
            ),
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

        self.code_map: dict[str, int] = {}

        self._is_first_update: bool = True

    async def async_stop(self) -> None:
        """Stop updater"""

        for _callback in self.new_intercom_callbacks:
            _callback()  # pylint: disable=not-callable

        if self.voip:
            await self.voip.stop()

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

        if not self._is_first_update:
            await asyncio.sleep(randint(1, 3) * 60)

        self.code = codes.OK

        _err: IntercomError | None = None

        try:
            await self._async_prepare(self.data)
        except IntercomUnauthorizedError as _e:
            raise ConfigEntryAuthFailed(_e) from _e
        except IntercomError as _e:
            _err = _e

            self.code = codes.SERVICE_UNAVAILABLE

        self.data[ATTR_UPDATE_STATE] = codes.is_error(self.code)

        if self._is_first_update:
            self._is_first_update = False

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

    async def _async_prepare(self, data: dict, retry: int = 1) -> None:
        """Prepare data.

        :param data: dict
        :param retry: int
        """

        _error: IntercomConnectionError | None = None

        try:
            await self._async_prepare_sip_settings(data)
        except IntercomConnectionError as _err:  # pragma: no cover
            _error = _err

        await asyncio.sleep(randint(5, 10))

        try:
            await self._async_prepare_intercoms(data)
        except IntercomConnectionError as _err:  # pragma: no cover
            _error = _err

        with contextlib.suppress(IntercomConnectionError):
            await self.client.streams()

        if _error:  # pragma: no cover
            if self._is_first_update and retry <= DEFAULT_RETRY:
                await asyncio.sleep(retry)

                _LOGGER.debug("Error start. retry (%r): %r", retry, _error)

                return await self._async_prepare(data, retry + 1)

            raise _error

    async def _async_prepare_intercoms(self, data: dict) -> None:
        """Prepare intercoms.

        :param data: dict
        """

        response: dict = await self.client.intercoms()

        if "addresses" in response:
            for address, intercoms in response["addresses"].items():
                for intercom in intercoms:
                    if (
                        ATTR_STREAM_URL in intercom and ATTR_STREAM_URL_MPEG in intercom
                    ):  # pragma: no cover
                        intercom[ATTR_STREAM_URL] = intercom[ATTR_STREAM_URL_MPEG]

                    for attr in [ATTR_STREAM_URL, ATTR_MUTE, ATTR_SIP_LOGIN]:
                        data[f"{intercom['id']}_{attr}"] = intercom[attr]

                    if intercom["id"] in self.intercoms:
                        continue

                    self.code_map[intercom["sip_login"]] = intercom["id"]

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

        init: bool = False
        if "success" in response and response["success"]:
            del response["success"]

            init = (
                len(
                    [
                        code
                        for code, value in response.items()
                        if code not in data or data[code] != value
                    ]
                )
                > 0
            )

            data |= response

        if init:
            self.voip = IntercomVoip(
                self.hass,
                data[ATTR_SIP_ADDRESS],
                data[ATTR_SIP_PORT],
                data[ATTR_SIP_LOGIN],
                data[ATTR_SIP_PASSWORD],
                self._call_callback,
            )

            self.hass.loop.call_soon(
                lambda: self.hass.async_create_task(
                    self.voip.safe_start(SIP_DEFAULT_RETRY)
                )
            )

    async def _call_callback(self, call: Call) -> None:  # pragma: no cover
        """Call callback

        :param call: Call
        """

        self.last_call = call

        async_dispatcher_send(self.hass, SIGNAL_CALL_STATE)


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
