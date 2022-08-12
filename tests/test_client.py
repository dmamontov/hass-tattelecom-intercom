"""Tests for the tattelecom_intercom component."""

# pylint: disable=no-member,too-many-statements,protected-access,too-many-lines,line-too-long

from __future__ import annotations

import json
import logging

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.httpx_client import get_async_client
from httpx import HTTPError, Request
from pytest_homeassistant_custom_component.common import load_fixture
from pytest_httpx import HTTPXMock

from custom_components.tattelecom_intercom.client import IntercomClient
from custom_components.tattelecom_intercom.const import DEVICE_CODE
from custom_components.tattelecom_intercom.enum import Method
from custom_components.tattelecom_intercom.exceptions import (
    IntercomConnectionError,
    IntercomNotFoundError,
    IntercomRequestError,
    IntercomUnauthorizedError,
)
from tests.setup import (
    MOCK_CODE,
    MOCK_INTERCOM_ID,
    MOCK_LOGIN,
    MOCK_PHONE,
    MOCK_TOKEN,
    get_url,
)

_LOGGER = logging.getLogger(__name__)


async def test_signin(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """Signin test"""

    httpx_mock.add_response(text=load_fixture("signin_data.json"), method=Method.POST)

    client: IntercomClient = IntercomClient(get_async_client(hass, False), MOCK_PHONE)

    assert await client.signin() == json.loads(load_fixture("signin_data.json"))

    request: Request | None = httpx_mock.get_request(method=Method.POST)
    assert request is not None
    assert request.url == get_url("subscriber/signin")
    assert request.method == Method.POST


async def test_signin_connection_error(
    hass: HomeAssistant, httpx_mock: HTTPXMock
) -> None:
    """Signin connection error test"""

    httpx_mock.add_exception(exception=HTTPError)  # type: ignore

    client: IntercomClient = IntercomClient(get_async_client(hass, False), MOCK_PHONE)

    with pytest.raises(IntercomConnectionError):
        await client.signin()


async def test_signin_not_found_error(
    hass: HomeAssistant, httpx_mock: HTTPXMock
) -> None:
    """Signin not found error test"""

    httpx_mock.add_response(
        text=load_fixture("error_data.json"), method=Method.POST, status_code=404
    )

    client: IntercomClient = IntercomClient(get_async_client(hass, False), MOCK_PHONE)

    with pytest.raises(IntercomNotFoundError):
        await client.signin()


async def test_signin_unauthorized_error(
    hass: HomeAssistant, httpx_mock: HTTPXMock
) -> None:
    """Signin unauthorized error test"""

    httpx_mock.add_response(
        text=load_fixture("error_data.json"), method=Method.POST, status_code=401
    )

    client: IntercomClient = IntercomClient(get_async_client(hass, False), MOCK_PHONE)

    with pytest.raises(IntercomUnauthorizedError):
        await client.signin()


async def test_signin_request(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """Signin request error test"""

    httpx_mock.add_response(
        text=load_fixture("error_data.json"), method=Method.POST, status_code=406
    )

    client: IntercomClient = IntercomClient(get_async_client(hass, False), MOCK_PHONE)

    with pytest.raises(IntercomRequestError):
        await client.signin()


async def test_register(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """Register test"""

    httpx_mock.add_response(text=load_fixture("register_data.json"), method=Method.POST)

    client: IntercomClient = IntercomClient(get_async_client(hass, False), MOCK_PHONE)

    assert await client.register(MOCK_LOGIN) == json.loads(
        load_fixture("register_data.json")
    )

    request: Request | None = httpx_mock.get_request(method=Method.POST)
    assert request is not None
    assert request.url == get_url("subscriber/register")
    assert request.method == Method.POST


async def test_register_connection_error(
    hass: HomeAssistant, httpx_mock: HTTPXMock
) -> None:
    """Register connection error test"""

    httpx_mock.add_exception(exception=HTTPError)  # type: ignore

    client: IntercomClient = IntercomClient(get_async_client(hass, False), MOCK_PHONE)

    with pytest.raises(IntercomConnectionError):
        await client.register(MOCK_LOGIN)


async def test_register_not_found_error(
    hass: HomeAssistant, httpx_mock: HTTPXMock
) -> None:
    """Register not found error test"""

    httpx_mock.add_response(
        text=load_fixture("error_data.json"), method=Method.POST, status_code=404
    )

    client: IntercomClient = IntercomClient(get_async_client(hass, False), MOCK_PHONE)

    with pytest.raises(IntercomNotFoundError):
        await client.register(MOCK_LOGIN)


async def test_register_unauthorized_error(
    hass: HomeAssistant, httpx_mock: HTTPXMock
) -> None:
    """Register unauthorized error test"""

    httpx_mock.add_response(
        text=load_fixture("error_data.json"), method=Method.POST, status_code=401
    )

    client: IntercomClient = IntercomClient(get_async_client(hass, False), MOCK_PHONE)

    with pytest.raises(IntercomUnauthorizedError):
        await client.register(MOCK_LOGIN)


async def test_sms_confirm(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """Sms confirm test"""

    httpx_mock.add_response(
        text=load_fixture("sms_confirm_data.json"), method=Method.POST
    )

    client: IntercomClient = IntercomClient(get_async_client(hass, False), MOCK_PHONE)

    assert await client.sms_confirm(MOCK_CODE) == json.loads(
        load_fixture("sms_confirm_data.json")
    )

    request: Request | None = httpx_mock.get_request(method=Method.POST)
    assert request is not None
    assert request.url == get_url("subscriber/smsconfirm")
    assert request.method == Method.POST


async def test_sms_confirm_connection_error(
    hass: HomeAssistant, httpx_mock: HTTPXMock
) -> None:
    """Sms confirm connection error test"""

    httpx_mock.add_exception(exception=HTTPError)  # type: ignore

    client: IntercomClient = IntercomClient(get_async_client(hass, False), MOCK_PHONE)

    with pytest.raises(IntercomConnectionError):
        await client.sms_confirm(MOCK_CODE)


async def test_sms_confirm_not_found_error(
    hass: HomeAssistant, httpx_mock: HTTPXMock
) -> None:
    """Sms confirm not found error test"""

    httpx_mock.add_response(
        text=load_fixture("error_data.json"), method=Method.POST, status_code=404
    )

    client: IntercomClient = IntercomClient(get_async_client(hass, False), MOCK_PHONE)

    with pytest.raises(IntercomNotFoundError):
        await client.sms_confirm(MOCK_CODE)


async def test_sms_confirm_unauthorized_error(
    hass: HomeAssistant, httpx_mock: HTTPXMock
) -> None:
    """Sms confirm unauthorized error test"""

    httpx_mock.add_response(
        text=load_fixture("error_data.json"), method=Method.POST, status_code=401
    )

    client: IntercomClient = IntercomClient(get_async_client(hass, False), MOCK_PHONE)

    with pytest.raises(IntercomUnauthorizedError):
        await client.sms_confirm(MOCK_LOGIN)


async def test_update_push_token(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """Update push token test"""

    httpx_mock.add_response(
        text=load_fixture("update_push_token_data.json"), method=Method.POST
    )

    client: IntercomClient = IntercomClient(
        get_async_client(hass, False), MOCK_PHONE, MOCK_TOKEN
    )

    assert await client.update_push_token("test") == json.loads(
        load_fixture("update_push_token_data.json")
    )

    request: Request | None = httpx_mock.get_request(method=Method.POST)
    assert request is not None
    assert request.url == get_url("subscriber/update-push-token")
    assert request.method == Method.POST


async def test_update_push_token_connection_error(
    hass: HomeAssistant, httpx_mock: HTTPXMock
) -> None:
    """Update push token connection error test"""

    httpx_mock.add_exception(exception=HTTPError)  # type: ignore

    client: IntercomClient = IntercomClient(
        get_async_client(hass, False), MOCK_PHONE, MOCK_TOKEN
    )

    with pytest.raises(IntercomConnectionError):
        await client.update_push_token("test")


async def test_update_push_token_not_found_error(
    hass: HomeAssistant, httpx_mock: HTTPXMock
) -> None:
    """Update push token not found error test"""

    httpx_mock.add_response(
        text=load_fixture("error_data.json"), method=Method.POST, status_code=404
    )

    client: IntercomClient = IntercomClient(
        get_async_client(hass, False), MOCK_PHONE, MOCK_TOKEN
    )

    with pytest.raises(IntercomNotFoundError):
        await client.update_push_token("test")


async def test_update_push_token_unauthorized_error(
    hass: HomeAssistant, httpx_mock: HTTPXMock
) -> None:
    """Update push token unauthorized error test"""

    httpx_mock.add_response(
        text=load_fixture("error_data.json"), method=Method.POST, status_code=401
    )

    client: IntercomClient = IntercomClient(
        get_async_client(hass, False), MOCK_PHONE, MOCK_TOKEN
    )

    with pytest.raises(IntercomUnauthorizedError):
        await client.update_push_token("test")


async def test_sip_settings(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """Sip settings test"""

    httpx_mock.add_response(
        text=load_fixture("sip_settings_data.json"), method=Method.GET
    )

    client: IntercomClient = IntercomClient(
        get_async_client(hass, False), MOCK_PHONE, MOCK_TOKEN
    )

    assert await client.sip_settings() == json.loads(
        load_fixture("sip_settings_data.json")
    )

    request: Request | None = httpx_mock.get_request(method=Method.GET)
    assert request is not None
    assert request.url == get_url(
        "subscriber/sipsettings", {"device_code": DEVICE_CODE, "phone": str(MOCK_PHONE)}
    )
    assert request.method == Method.GET


async def test_sip_settings_connection_error(
    hass: HomeAssistant, httpx_mock: HTTPXMock
) -> None:
    """Sip settings connection error test"""

    httpx_mock.add_exception(exception=HTTPError)  # type: ignore

    client: IntercomClient = IntercomClient(
        get_async_client(hass, False), MOCK_PHONE, MOCK_TOKEN
    )

    with pytest.raises(IntercomConnectionError):
        await client.sip_settings()


async def test_sip_settings_not_found_error(
    hass: HomeAssistant, httpx_mock: HTTPXMock
) -> None:
    """Sip settings not found error test"""

    httpx_mock.add_response(
        text=load_fixture("error_data.json"), method=Method.GET, status_code=404
    )

    client: IntercomClient = IntercomClient(
        get_async_client(hass, False), MOCK_PHONE, MOCK_TOKEN
    )

    with pytest.raises(IntercomNotFoundError):
        await client.sip_settings()


async def test_sip_settings_unauthorized_error(
    hass: HomeAssistant, httpx_mock: HTTPXMock
) -> None:
    """Sip settings unauthorized error test"""

    httpx_mock.add_response(
        text=load_fixture("error_data.json"), method=Method.GET, status_code=401
    )

    client: IntercomClient = IntercomClient(
        get_async_client(hass, False), MOCK_PHONE, MOCK_TOKEN
    )

    with pytest.raises(IntercomUnauthorizedError):
        await client.sip_settings()


async def test_intercoms(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """Intercoms test"""

    httpx_mock.add_response(text=load_fixture("intercoms_data.json"), method=Method.GET)

    client: IntercomClient = IntercomClient(
        get_async_client(hass, False), MOCK_PHONE, MOCK_TOKEN
    )

    assert await client.intercoms() == json.loads(load_fixture("intercoms_data.json"))

    request: Request | None = httpx_mock.get_request(method=Method.GET)
    assert request is not None
    assert request.url == get_url(
        "subscriber/available-intercoms",
        {"device_code": DEVICE_CODE, "phone": str(MOCK_PHONE)},
    )
    assert request.method == Method.GET


async def test_intercoms_connection_error(
    hass: HomeAssistant, httpx_mock: HTTPXMock
) -> None:
    """Intercoms connection error test"""

    httpx_mock.add_exception(exception=HTTPError)  # type: ignore

    client: IntercomClient = IntercomClient(
        get_async_client(hass, False), MOCK_PHONE, MOCK_TOKEN
    )

    with pytest.raises(IntercomConnectionError):
        await client.intercoms()


async def test_intercoms_not_found_error(
    hass: HomeAssistant, httpx_mock: HTTPXMock
) -> None:
    """Intercoms not found error test"""

    httpx_mock.add_response(
        text=load_fixture("error_data.json"), method=Method.GET, status_code=404
    )

    client: IntercomClient = IntercomClient(
        get_async_client(hass, False), MOCK_PHONE, MOCK_TOKEN
    )

    with pytest.raises(IntercomNotFoundError):
        await client.intercoms()


async def test_intercoms_unauthorized_error(
    hass: HomeAssistant, httpx_mock: HTTPXMock
) -> None:
    """Intercoms unauthorized error test"""

    httpx_mock.add_response(
        text=load_fixture("error_data.json"), method=Method.GET, status_code=401
    )

    client: IntercomClient = IntercomClient(
        get_async_client(hass, False), MOCK_PHONE, MOCK_TOKEN
    )

    with pytest.raises(IntercomUnauthorizedError):
        await client.intercoms()


async def test_open(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """Open test"""

    httpx_mock.add_response(text=load_fixture("open_data.json"), method=Method.POST)

    client: IntercomClient = IntercomClient(
        get_async_client(hass, False), MOCK_PHONE, MOCK_TOKEN
    )

    assert await client.open(MOCK_INTERCOM_ID) == json.loads(
        load_fixture("open_data.json")
    )

    request: Request | None = httpx_mock.get_request(method=Method.POST)
    assert request is not None
    assert request.url == get_url("subscriber/open-intercom")
    assert request.method == Method.POST


async def test_open_connection_error(
    hass: HomeAssistant, httpx_mock: HTTPXMock
) -> None:
    """Open connection error test"""

    httpx_mock.add_exception(exception=HTTPError)  # type: ignore

    client: IntercomClient = IntercomClient(
        get_async_client(hass, False), MOCK_PHONE, MOCK_TOKEN
    )

    with pytest.raises(IntercomConnectionError):
        await client.open(MOCK_INTERCOM_ID)


async def test_open_not_found_error(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """Open not found error test"""

    httpx_mock.add_response(
        text=load_fixture("error_data.json"), method=Method.POST, status_code=404
    )

    client: IntercomClient = IntercomClient(
        get_async_client(hass, False), MOCK_PHONE, MOCK_TOKEN
    )

    with pytest.raises(IntercomNotFoundError):
        await client.open(MOCK_INTERCOM_ID)


async def test_open_unauthorized_error(
    hass: HomeAssistant, httpx_mock: HTTPXMock
) -> None:
    """Open unauthorized error test"""

    httpx_mock.add_response(
        text=load_fixture("error_data.json"), method=Method.POST, status_code=401
    )

    client: IntercomClient = IntercomClient(
        get_async_client(hass, False), MOCK_PHONE, MOCK_TOKEN
    )

    with pytest.raises(IntercomUnauthorizedError):
        await client.open(MOCK_INTERCOM_ID)


async def test_mute(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """Mute test"""

    httpx_mock.add_response(text=load_fixture("mute_data.json"), method=Method.POST)

    client: IntercomClient = IntercomClient(
        get_async_client(hass, False), MOCK_PHONE, MOCK_TOKEN
    )

    assert await client.mute(MOCK_INTERCOM_ID) == json.loads(
        load_fixture("mute_data.json")
    )

    request: Request | None = httpx_mock.get_request(method=Method.POST)
    assert request is not None
    assert request.url == get_url("subscriber/disable-intercom-calls")
    assert request.method == Method.POST


async def test_mute_connection_error(
    hass: HomeAssistant, httpx_mock: HTTPXMock
) -> None:
    """Mute connection error test"""

    httpx_mock.add_exception(exception=HTTPError)  # type: ignore

    client: IntercomClient = IntercomClient(
        get_async_client(hass, False), MOCK_PHONE, MOCK_TOKEN
    )

    with pytest.raises(IntercomConnectionError):
        await client.mute(MOCK_INTERCOM_ID)


async def test_mute_not_found_error(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """Mute not found error test"""

    httpx_mock.add_response(
        text=load_fixture("error_data.json"), method=Method.POST, status_code=404
    )

    client: IntercomClient = IntercomClient(
        get_async_client(hass, False), MOCK_PHONE, MOCK_TOKEN
    )

    with pytest.raises(IntercomNotFoundError):
        await client.mute(MOCK_INTERCOM_ID)


async def test_mute_unauthorized_error(
    hass: HomeAssistant, httpx_mock: HTTPXMock
) -> None:
    """Mute unauthorized error test"""

    httpx_mock.add_response(
        text=load_fixture("error_data.json"), method=Method.POST, status_code=401
    )

    client: IntercomClient = IntercomClient(
        get_async_client(hass, False), MOCK_PHONE, MOCK_TOKEN
    )

    with pytest.raises(IntercomUnauthorizedError):
        await client.mute(MOCK_INTERCOM_ID)


async def test_unmute(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """Unmute test"""

    httpx_mock.add_response(text=load_fixture("unmute_data.json"), method=Method.POST)

    client: IntercomClient = IntercomClient(
        get_async_client(hass, False), MOCK_PHONE, MOCK_TOKEN
    )

    assert await client.unmute(MOCK_INTERCOM_ID) == json.loads(
        load_fixture("unmute_data.json")
    )

    request: Request | None = httpx_mock.get_request(method=Method.POST)
    assert request is not None
    assert request.url == get_url("subscriber/enable-intercom-calls")
    assert request.method == Method.POST


async def test_unmute_connection_error(
    hass: HomeAssistant, httpx_mock: HTTPXMock
) -> None:
    """Unmute connection error test"""

    httpx_mock.add_exception(exception=HTTPError)  # type: ignore

    client: IntercomClient = IntercomClient(
        get_async_client(hass, False), MOCK_PHONE, MOCK_TOKEN
    )

    with pytest.raises(IntercomConnectionError):
        await client.unmute(MOCK_INTERCOM_ID)


async def test_unmute_not_found_error(
    hass: HomeAssistant, httpx_mock: HTTPXMock
) -> None:
    """Unmute not found error test"""

    httpx_mock.add_response(
        text=load_fixture("error_data.json"), method=Method.POST, status_code=404
    )

    client: IntercomClient = IntercomClient(
        get_async_client(hass, False), MOCK_PHONE, MOCK_TOKEN
    )

    with pytest.raises(IntercomNotFoundError):
        await client.unmute(MOCK_INTERCOM_ID)


async def test_unmute_unauthorized_error(
    hass: HomeAssistant, httpx_mock: HTTPXMock
) -> None:
    """Unmute unauthorized error test"""

    httpx_mock.add_response(
        text=load_fixture("error_data.json"), method=Method.POST, status_code=401
    )

    client: IntercomClient = IntercomClient(
        get_async_client(hass, False), MOCK_PHONE, MOCK_TOKEN
    )

    with pytest.raises(IntercomUnauthorizedError):
        await client.unmute(MOCK_INTERCOM_ID)


async def test_schedule(hass: HomeAssistant, httpx_mock: HTTPXMock) -> None:
    """Schedule test"""

    httpx_mock.add_response(text=load_fixture("schedule_data.json"), method=Method.POST)

    client: IntercomClient = IntercomClient(
        get_async_client(hass, False), MOCK_PHONE, MOCK_TOKEN
    )

    assert await client.schedule(MOCK_INTERCOM_ID) == json.loads(
        load_fixture("schedule_data.json")
    )

    request: Request | None = httpx_mock.get_request(method=Method.POST)
    assert request is not None
    assert request.url == get_url("subscriber/set-schedule")
    assert request.method == Method.POST


async def test_schedule_connection_error(
    hass: HomeAssistant, httpx_mock: HTTPXMock
) -> None:
    """Schedule connection error test"""

    httpx_mock.add_exception(exception=HTTPError)  # type: ignore

    client: IntercomClient = IntercomClient(
        get_async_client(hass, False), MOCK_PHONE, MOCK_TOKEN
    )

    with pytest.raises(IntercomConnectionError):
        await client.schedule(MOCK_INTERCOM_ID)


async def test_schedule_not_found_error(
    hass: HomeAssistant, httpx_mock: HTTPXMock
) -> None:
    """Schedule not found error test"""

    httpx_mock.add_response(
        text=load_fixture("error_data.json"), method=Method.POST, status_code=404
    )

    client: IntercomClient = IntercomClient(
        get_async_client(hass, False), MOCK_PHONE, MOCK_TOKEN
    )

    with pytest.raises(IntercomNotFoundError):
        await client.schedule(MOCK_INTERCOM_ID)


async def test_schedule_unauthorized_error(
    hass: HomeAssistant, httpx_mock: HTTPXMock
) -> None:
    """Schedule unauthorized error test"""

    httpx_mock.add_response(
        text=load_fixture("error_data.json"), method=Method.POST, status_code=401
    )

    client: IntercomClient = IntercomClient(
        get_async_client(hass, False), MOCK_PHONE, MOCK_TOKEN
    )

    with pytest.raises(IntercomUnauthorizedError):
        await client.schedule(MOCK_INTERCOM_ID)
