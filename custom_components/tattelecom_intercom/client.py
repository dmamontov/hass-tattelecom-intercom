"""Tattelecom intercom API client."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from httpx import AsyncClient, ConnectError, HTTPError, Response, TransportError

from .const import (
    CLIENT_URL,
    DEFAULT_TIMEOUT,
    DEVICE_CODE,
    DEVICE_OS,
    DIAGNOSTIC_CONTENT,
    DIAGNOSTIC_DATE_TIME,
    DIAGNOSTIC_MESSAGE,
    HEADERS,
)
from .enum import ApiVersion, Method
from .exceptions import (
    IntercomConnectionError,
    IntercomNotFoundError,
    IntercomRequestError,
    IntercomUnauthorizedError,
)

_LOGGER = logging.getLogger(__name__)


# pylint: disable=too-many-public-methods,too-many-arguments
class IntercomClient:
    """Tattelecom intercom API Client."""

    _client: AsyncClient
    _timeout: int

    _token: str | None = None
    _phone: int

    def __init__(
        self,
        client: AsyncClient,
        phone: int,
        token: str | None = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize API client.

        :param client: AsyncClient: AsyncClient object
        :param token: str | None: Auth token
        :param phone: int: Phone number
        :param timeout: int: Query execution timeout
        """

        self._client = client
        self._timeout = timeout

        self._token = token
        self._phone = phone

        self.diagnostics: dict[str, Any] = {}

    async def request(
        self,
        path: str,
        method: Method = Method.GET,
        body: dict | None = None,
        params: dict | None = None,
        api_version: ApiVersion = ApiVersion.V1,
    ) -> dict:
        """Request method.

        :param path: str: Api path
        :param method: Method: Api method
        :param body: dict | None: Api body
        :param params: dict | None: Api query
        :param api_version: ApiVersion: Api version
        :return dict: Api data.
        """

        _url: str = CLIENT_URL.format(api_version=api_version, path=path)
        _headers: dict = HEADERS

        if self._token:
            _headers["access-token"] = self._token

        try:
            async with self._client as client:
                response: Response = await client.request(
                    method,
                    _url,
                    json=body,
                    params=params,
                    headers=_headers,
                    timeout=self._timeout,
                )

            self._debug("Successful request", _url, response.content, path)

            _data: dict = json.loads(response.content)
        except (
            HTTPError,
            ConnectError,
            TransportError,
            ValueError,
            TypeError,
            json.JSONDecodeError,
        ) as _e:
            self._debug("Connection error", _url, _e, path)

            raise IntercomConnectionError("Connection error") from _e

        if response.status_code == 404:
            raise IntercomNotFoundError("Not found")

        if response.status_code == 401:
            raise IntercomUnauthorizedError("Unauthorized")

        if response.status_code > 400 or (
            "status" in _data and int(_data["status"]) > 400
        ):
            raise IntercomRequestError(
                _data.get("error_text", _data.get("message", "Request error"))
            )

        return _data

    async def signin(self) -> dict:
        """Signin

        :return dict: Response data
        """

        return await self.request(
            "subscriber/signin",
            Method.POST,
            {
                "device_code": DEVICE_CODE,
                "device_os": DEVICE_OS,
                "phone": str(self._phone),
            },
        )

    async def register(self, login: str) -> dict:
        """Register

        :param login: str: Login
        :return dict: Response data
        """

        return await self.request(
            "subscriber/register",
            Method.POST,
            {
                "device_code": DEVICE_CODE,
                "device_os": DEVICE_OS,
                "phone": str(self._phone),
                "registration_token": login,
            },
        )

    async def sms_confirm(self, code: str) -> dict:
        """Sms confirm

        :param code: str: Sms code
        :return dict: Response data
        """

        return await self.request(
            "subscriber/smsconfirm",
            Method.POST,
            {"device_code": DEVICE_CODE, "phone": str(self._phone), "sms_code": code},
        )

    async def update_push_token(self, token: str) -> dict:
        """Update push token

        :param token: str: Api token
        :return dict: Response data
        """

        self._token = token

        return await self.request(
            "subscriber/update-push-token",
            Method.POST,
            {
                "device_code": DEVICE_CODE,
                "phone": str(self._phone),
                "push_token": DEVICE_CODE,
            },
        )

    async def sip_settings(self) -> dict:
        """Get sip settings

        :return dict: Response data
        """

        return await self.request(
            "subscriber/sipsettings",
            params={
                "device_code": DEVICE_CODE,
                "phone": str(self._phone),
            },
        )

    async def intercoms(self) -> dict:
        """Get available intercoms

        :return dict: Response data
        """

        return await self.request(
            "subscriber/available-intercoms",
            params={
                "device_code": DEVICE_CODE,
                "phone": str(self._phone),
            },
        )

    # TODO: Not yet supported by the manufacturer.
    async def streams(self) -> dict:  # pragma: no cover
        """Get available streams

        :return dict: Response data
        """

        return await self.request(
            "subscriber/available-streams",
            params={
                "device_code": DEVICE_CODE,
                "phone": str(self._phone),
            },
            api_version=ApiVersion.V2,
        )

    async def open(self, intercom_id: int) -> dict:
        """Open intercom

        :param intercom_id: int: Intercom ID
        :return dict: Response data
        """

        return await self.request(
            "subscriber/open-intercom",
            Method.POST,
            {
                "device_code": DEVICE_CODE,
                "phone": str(self._phone),
                "intercom_id": intercom_id,
            },
        )

    async def mute(self, intercom_id: int) -> dict:
        """Disable calls

        :param intercom_id: int: Intercom ID
        :return dict: Response data
        """

        return await self.request(
            "subscriber/disable-intercom-calls",
            Method.POST,
            {
                "device_code": DEVICE_CODE,
                "phone": str(self._phone),
                "intercom_id": intercom_id,
            },
        )

    async def unmute(self, intercom_id: int) -> dict:
        """Enable calls

        :param intercom_id: int: Intercom ID
        :return dict: Response data
        """

        return await self.request(
            "subscriber/enable-intercom-calls",
            Method.POST,
            {
                "device_code": DEVICE_CODE,
                "phone": str(self._phone),
                "intercom_id": intercom_id,
            },
        )

    async def schedule(
        self,
        intercom_id: int,
        start_h: int = 0,
        start_m: int = 0,
        finish_h: int = 0,
        finish_m: int = 0,
        monday: bool = True,
        tuesday: bool = True,
        wednesday: bool = True,
        thursday: bool = True,
        friday: bool = True,
        saturday: bool = True,
        sunday: bool = True,
    ) -> dict:
        """Set schedule

        :param intercom_id: int: Intercom ID
        :param start_h: int: Start hours
        :param start_m: int: Start minutes
        :param finish_h: int: Finish hours
        :param finish_m: int: Finish minutes
        :param monday: bool: Monday
        :param tuesday: bool: Tuesday
        :param wednesday: bool: Wednesday
        :param thursday: bool: Thursday
        :param friday: bool: Friday
        :param saturday: bool: Saturday
        :param sunday: bool: Sunday
        :return dict: Response data
        """

        return await self.request(
            "subscriber/set-schedule",
            Method.POST,
            {
                "device_code": DEVICE_CODE,
                "phone": str(self._phone),
                "intercom_id": intercom_id,
                "start_h": start_h,
                "start_m": start_m,
                "finish_h": finish_h,
                "finish_m": finish_m,
                "monday": monday,
                "tuesday": tuesday,
                "wednesday": wednesday,
                "thursday": thursday,
                "friday": friday,
                "saturday": saturday,
                "sunday": sunday,
            },
        )

    def _debug(self, message: str, url: str, content: Any, path: str) -> None:
        """Debug log

        :param message: str: Message
        :param url: str: URL
        :param content: Any: Content
        :param path: str: Path
        """

        _LOGGER.debug("%s (%s): %s", message, url, str(content))

        _content: dict | str = {}

        try:
            _content = json.loads(content)
        except (ValueError, TypeError):  # pragma: no cover
            _content = str(content)

        self.diagnostics[path] = {
            DIAGNOSTIC_DATE_TIME: datetime.now().replace(microsecond=0).isoformat(),
            DIAGNOSTIC_MESSAGE: message,
            DIAGNOSTIC_CONTENT: _content,
        }
