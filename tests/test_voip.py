"""Tests for the tattelecom_intercom component."""

# pylint: disable=no-member,too-many-statements,protected-access,too-many-lines,line-too-long,too-many-locals

from __future__ import annotations

import asyncio
import logging
import re
from datetime import timedelta
from unittest.mock import Mock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.util.dt import utcnow
from pytest_homeassistant_custom_component.common import (
    async_fire_time_changed,
    load_fixture,
)

from custom_components.tattelecom_intercom.const import SIP_EXPIRES, SIP_RETRY_SLEEP
from custom_components.tattelecom_intercom.enum import (
    CallState,
    RtpPayloadType,
    SendMode,
)
from custom_components.tattelecom_intercom.exceptions import IntercomError
from custom_components.tattelecom_intercom.voip import Call, IntercomVoip
from tests.setup import (
    MOCK_ADDRESS,
    MOCK_IP,
    MOCK_LOCAL_PORT,
    MOCK_PASSWORD,
    MOCK_PORT,
    MOCK_USERNAME,
    MultipleSideEffect,
)

_LOGGER = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations"""

    yield


@pytest.mark.asyncio
async def test_start(hass: HomeAssistant) -> None:
    """Start start"""

    async def _callback() -> None:
        """Callback"""

    with patch(
        "custom_components.tattelecom_intercom.sip.socket.socket"
    ) as mock_socket, patch(
        "custom_components.tattelecom_intercom.sip.select.select",
        return_value=(True, True, True),
    ) as mock_select, patch(
        "custom_components.tattelecom_intercom.voip.socket.gethostbyname_ex",
        return_value=[[], [], [MOCK_IP]],
    ):
        mock_socket.return_value.setblocking = Mock(return_value=None)
        mock_socket.return_value.getsockname = Mock(
            return_value=(MOCK_IP, MOCK_LOCAL_PORT)
        )

        def out_1(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8")) == clean_request(
                load_fixture("register_first_out_data.txt").replace("\\r\\n", "\r\n")
            )

            return 1

        def out_2(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8")) == clean_request(
                load_fixture("register_out_data.txt").replace("\\r\\n", "\r\n")
            )

            return 1

        mock_socket.return_value.sendto = Mock(
            side_effect=MultipleSideEffect(out_1, out_2)
        )

        def in_1(*args) -> bytes:
            return str.encode(load_fixture("register_first_data.txt"))

        def in_2(*args) -> bytes:
            return str.encode(load_fixture("register_data.txt"))

        mock_socket.return_value.recv = Mock(side_effect=MultipleSideEffect(in_1, in_2))

        voip: IntercomVoip = IntercomVoip(
            hass, MOCK_ADDRESS, MOCK_PORT, MOCK_USERNAME, MOCK_PASSWORD, _callback
        )

        assert await voip.start()

        soft_stop(voip)

        assert len(mock_select.mock_calls) == 2


@pytest.mark.asyncio
async def test_start_already_start(hass: HomeAssistant) -> None:
    """Start already start"""

    async def _callback() -> None:
        """Callback"""

    with patch(
        "custom_components.tattelecom_intercom.sip.socket.socket"
    ) as mock_socket, patch(
        "custom_components.tattelecom_intercom.sip.select.select",
        return_value=(True, True, True),
    ) as mock_select:
        mock_socket.return_value.sendto = Mock(return_value=None)
        mock_socket.return_value.setblocking = Mock(return_value=None)
        mock_socket.return_value.getsockname = Mock(
            return_value=(MOCK_IP, MOCK_LOCAL_PORT)
        )

        def first(*args) -> bytes:
            return str.encode(load_fixture("register_first_data.txt"))

        def second(*args) -> bytes:
            return str.encode(load_fixture("register_data.txt"))

        mock_socket.return_value.recv = Mock(
            side_effect=MultipleSideEffect(first, second)
        )

        voip: IntercomVoip = IntercomVoip(
            hass, MOCK_ADDRESS, MOCK_PORT, MOCK_USERNAME, MOCK_PASSWORD, _callback
        )

        assert await voip.start()
        assert not await voip.start()

        soft_stop(voip)

        assert len(mock_select.mock_calls) == 2


@pytest.mark.asyncio
async def test_start_timeout_error(hass: HomeAssistant) -> None:
    """Start timeout error"""

    async def _callback() -> None:
        """Callback"""

    with patch(
        "custom_components.tattelecom_intercom.sip.socket.socket"
    ) as mock_socket, patch(
        "custom_components.tattelecom_intercom.sip.select.select", return_value=[]
    ) as mock_select:
        mock_socket.return_value.sendto = Mock(return_value=None)
        mock_socket.return_value.setblocking = Mock(return_value=None)
        mock_socket.return_value.getsockname = Mock(
            return_value=(MOCK_IP, MOCK_LOCAL_PORT)
        )

        mock_socket.return_value.recv = Mock(
            return_value=str.encode(load_fixture("register_first_data.txt"))
        )

        voip: IntercomVoip = IntercomVoip(
            hass, MOCK_ADDRESS, MOCK_PORT, MOCK_USERNAME, MOCK_PASSWORD, _callback
        )

        assert not await voip.start()

        soft_stop(voip)

        assert len(mock_select.mock_calls) == 1


@pytest.mark.asyncio
async def test_start_timeout_error_two(hass: HomeAssistant) -> None:
    """Start timeout error"""

    async def _callback() -> None:
        """Callback"""

    def timeout_1(*args) -> tuple:
        return [True], [True], [True]

    def timeout_2(*args) -> tuple:
        return [], [], []

    with patch(
        "custom_components.tattelecom_intercom.sip.socket.socket"
    ) as mock_socket, patch(
        "custom_components.tattelecom_intercom.sip.select.select",
        side_effect=MultipleSideEffect(timeout_1, timeout_2),
    ) as mock_select:
        mock_socket.return_value.sendto = Mock(return_value=None)
        mock_socket.return_value.setblocking = Mock(return_value=None)
        mock_socket.return_value.getsockname = Mock(
            return_value=(MOCK_IP, MOCK_LOCAL_PORT)
        )

        mock_socket.return_value.recv = Mock(
            return_value=str.encode(load_fixture("register_first_data.txt"))
        )

        voip: IntercomVoip = IntercomVoip(
            hass, MOCK_ADDRESS, MOCK_PORT, MOCK_USERNAME, MOCK_PASSWORD, _callback
        )

        assert not await voip.start()

        soft_stop(voip)

        assert len(mock_select.mock_calls) == 2


@pytest.mark.asyncio
async def test_start_trying(hass: HomeAssistant) -> None:
    """Start start trying"""

    async def _callback() -> None:
        """Callback"""

    with patch(
        "custom_components.tattelecom_intercom.sip.socket.socket"
    ) as mock_socket, patch(
        "custom_components.tattelecom_intercom.sip.select.select",
        return_value=(True, True, True),
    ) as mock_select, patch(
        "custom_components.tattelecom_intercom.voip.socket.gethostbyname_ex",
        return_value=[[], [], [MOCK_IP]],
    ):
        mock_socket.return_value.setblocking = Mock(return_value=None)
        mock_socket.return_value.getsockname = Mock(
            return_value=(MOCK_IP, MOCK_LOCAL_PORT)
        )

        def out_1(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8")) == clean_request(
                load_fixture("register_first_out_data.txt").replace("\\r\\n", "\r\n")
            )

            return 1

        def out_2(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8")) == clean_request(
                load_fixture("register_out_data.txt").replace("\\r\\n", "\r\n")
            )

            return 1

        mock_socket.return_value.sendto = Mock(
            side_effect=MultipleSideEffect(out_1, out_2)
        )

        def in_1(*args) -> bytes:
            return str.encode(load_fixture("trying_data.txt"))

        def in_2(*args) -> bytes:
            return str.encode(load_fixture("register_first_data.txt"))

        def in_3(*args) -> bytes:
            return str.encode(load_fixture("register_data.txt"))

        mock_socket.return_value.recv = Mock(
            side_effect=MultipleSideEffect(in_1, in_2, in_3)
        )

        voip: IntercomVoip = IntercomVoip(
            hass, MOCK_ADDRESS, MOCK_PORT, MOCK_USERNAME, MOCK_PASSWORD, _callback
        )

        assert await voip.start()

        soft_stop(voip)

        assert len(mock_select.mock_calls) == 2


@pytest.mark.asyncio
async def test_start_bad_request(hass: HomeAssistant) -> None:
    """Start start bad request"""

    async def _callback() -> None:
        """Callback"""

    with patch(
        "custom_components.tattelecom_intercom.sip.socket.socket"
    ) as mock_socket, patch(
        "custom_components.tattelecom_intercom.sip.select.select",
        return_value=(True, True, True),
    ) as mock_select, patch(
        "custom_components.tattelecom_intercom.voip.socket.gethostbyname_ex",
        return_value=[[], [], [MOCK_IP]],
    ):
        mock_socket.return_value.setblocking = Mock(return_value=None)
        mock_socket.return_value.getsockname = Mock(
            return_value=(MOCK_IP, MOCK_LOCAL_PORT)
        )

        def out_1(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8")) == clean_request(
                load_fixture("register_first_out_data.txt").replace("\\r\\n", "\r\n")
            )

            return 1

        mock_socket.return_value.sendto = Mock(side_effect=out_1)

        mock_socket.return_value.recv = Mock(
            return_value=str.encode(load_fixture("bad_request_data.txt"))
        )

        voip: IntercomVoip = IntercomVoip(
            hass, MOCK_ADDRESS, MOCK_PORT, MOCK_USERNAME, MOCK_PASSWORD, _callback
        )

        assert not await voip.start()

        soft_stop(voip)

        assert len(mock_select.mock_calls) == 1


@pytest.mark.asyncio
async def test_start_bad_request_two(hass: HomeAssistant) -> None:
    """Start start bad request"""

    async def _callback() -> None:
        """Callback"""

    with patch(
        "custom_components.tattelecom_intercom.sip.socket.socket"
    ) as mock_socket, patch(
        "custom_components.tattelecom_intercom.sip.select.select",
        return_value=(True, True, True),
    ) as mock_select, patch(
        "custom_components.tattelecom_intercom.voip.socket.gethostbyname_ex",
        return_value=[[], [], [MOCK_IP]],
    ):
        mock_socket.return_value.setblocking = Mock(return_value=None)
        mock_socket.return_value.getsockname = Mock(
            return_value=(MOCK_IP, MOCK_LOCAL_PORT)
        )

        def out_1(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8")) == clean_request(
                load_fixture("register_first_out_data.txt").replace("\\r\\n", "\r\n")
            )

            return 1

        def out_2(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8")) == clean_request(
                load_fixture("register_out_data.txt").replace("\\r\\n", "\r\n")
            )

            return 1

        mock_socket.return_value.sendto = Mock(
            side_effect=MultipleSideEffect(out_1, out_2)
        )

        def in_1(*args) -> bytes:
            return str.encode(load_fixture("register_first_data.txt"))

        def in_2(*args) -> bytes:
            return str.encode(load_fixture("bad_request_data.txt"))

        mock_socket.return_value.recv = Mock(side_effect=MultipleSideEffect(in_1, in_2))

        voip: IntercomVoip = IntercomVoip(
            hass, MOCK_ADDRESS, MOCK_PORT, MOCK_USERNAME, MOCK_PASSWORD, _callback
        )

        assert not await voip.start()

        soft_stop(voip)

        assert len(mock_select.mock_calls) == 2


@pytest.mark.asyncio
async def test_start_unauthorized(hass: HomeAssistant) -> None:
    """Start start unauthorized"""

    async def _callback() -> None:
        """Callback"""

    with patch(
        "custom_components.tattelecom_intercom.sip.socket.socket"
    ) as mock_socket, patch(
        "custom_components.tattelecom_intercom.sip.select.select",
        return_value=(True, True, True),
    ) as mock_select, patch(
        "custom_components.tattelecom_intercom.voip.socket.gethostbyname_ex",
        return_value=[[], [], [MOCK_IP]],
    ):
        mock_socket.return_value.setblocking = Mock(return_value=None)
        mock_socket.return_value.getsockname = Mock(
            return_value=(MOCK_IP, MOCK_LOCAL_PORT)
        )

        def out_1(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8")) == clean_request(
                load_fixture("register_first_out_data.txt").replace("\\r\\n", "\r\n")
            )

            return 1

        def out_2(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8")) == clean_request(
                load_fixture("register_out_data.txt").replace("\\r\\n", "\r\n")
            )

            return 1

        mock_socket.return_value.sendto = Mock(
            side_effect=MultipleSideEffect(out_1, out_2)
        )

        mock_socket.return_value.recv = Mock(
            return_value=str.encode(load_fixture("register_first_data.txt"))
        )

        voip: IntercomVoip = IntercomVoip(
            hass, MOCK_ADDRESS, MOCK_PORT, MOCK_USERNAME, MOCK_PASSWORD, _callback
        )

        assert not await voip.start()

        soft_stop(voip)

        assert len(mock_select.mock_calls) == 2


@pytest.mark.asyncio
async def test_start_server_error(hass: HomeAssistant) -> None:
    """Start start server error"""

    async def _callback() -> None:
        """Callback"""

    with patch(
        "custom_components.tattelecom_intercom.sip.socket.socket"
    ) as mock_socket, patch(
        "custom_components.tattelecom_intercom.sip.select.select",
        return_value=(True, True, True),
    ) as mock_select, patch(
        "custom_components.tattelecom_intercom.voip.socket.gethostbyname_ex",
        return_value=[[], [], [MOCK_IP]],
    ), patch(
        "custom_components.tattelecom_intercom.sip.asyncio.sleep", return_value=None
    ):
        mock_socket.return_value.setblocking = Mock(return_value=None)
        mock_socket.return_value.getsockname = Mock(
            return_value=(MOCK_IP, MOCK_LOCAL_PORT)
        )

        def out_1(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8"), True) == clean_request(
                load_fixture("register_first_out_data.txt").replace("\\r\\n", "\r\n"),
                True,
            )

            return 1

        def out_2(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8"), True) == clean_request(
                load_fixture("register_out_data.txt").replace("\\r\\n", "\r\n"), True
            )

            return 1

        mock_socket.return_value.sendto = Mock(
            side_effect=MultipleSideEffect(out_1, out_2, out_1, out_2)
        )

        def in_1(*args) -> bytes:
            return str.encode(load_fixture("register_first_data.txt"))

        def in_2(*args) -> bytes:
            return str.encode(load_fixture("server_error_data.txt"))

        def in_3(*args) -> bytes:
            return str.encode(load_fixture("register_data.txt"))

        mock_socket.return_value.recv = Mock(
            side_effect=MultipleSideEffect(in_1, in_2, in_1, in_3)
        )

        voip: IntercomVoip = IntercomVoip(
            hass, MOCK_ADDRESS, MOCK_PORT, MOCK_USERNAME, MOCK_PASSWORD, _callback
        )

        assert await voip.start()

        soft_stop(voip)

        assert len(mock_select.mock_calls) == 4


@pytest.mark.asyncio
async def test_start_bad_package(hass: HomeAssistant) -> None:
    """Start start bad package"""

    async def _callback() -> None:
        """Callback"""

    with patch(
        "custom_components.tattelecom_intercom.sip.socket.socket"
    ) as mock_socket, patch(
        "custom_components.tattelecom_intercom.sip.select.select",
        return_value=(True, True, True),
    ) as mock_select, patch(
        "custom_components.tattelecom_intercom.voip.socket.gethostbyname_ex",
        return_value=[[], [], [MOCK_IP]],
    ):
        mock_socket.return_value.setblocking = Mock(return_value=None)
        mock_socket.return_value.getsockname = Mock(
            return_value=(MOCK_IP, MOCK_LOCAL_PORT)
        )

        def out_1(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8")) == clean_request(
                load_fixture("register_first_out_data.txt").replace("\\r\\n", "\r\n")
            )

            return 1

        def out_2(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8")) == clean_request(
                load_fixture("register_out_data.txt").replace("\\r\\n", "\r\n")
            )

            return 1

        mock_socket.return_value.sendto = Mock(
            side_effect=MultipleSideEffect(out_1, out_2)
        )

        def in_1(*args) -> bytes:
            return str.encode(load_fixture("register_first_data.txt"))

        def in_2(*args) -> bytes:
            return str.encode(load_fixture("bad_package_data.txt"))

        mock_socket.return_value.recv = Mock(side_effect=MultipleSideEffect(in_1, in_2))

        voip: IntercomVoip = IntercomVoip(
            hass, MOCK_ADDRESS, MOCK_PORT, MOCK_USERNAME, MOCK_PASSWORD, _callback
        )

        assert not await voip.start()

        soft_stop(voip)

        assert len(mock_select.mock_calls) == 2


@pytest.mark.asyncio
async def test_stop(hass: HomeAssistant) -> None:
    """Start stop"""

    async def _callback() -> None:
        """Callback"""

    with patch(
        "custom_components.tattelecom_intercom.sip.socket.socket"
    ) as mock_socket, patch(
        "custom_components.tattelecom_intercom.sip.select.select",
        return_value=(True, True, True),
    ) as mock_select, patch(
        "custom_components.tattelecom_intercom.voip.socket.gethostbyname_ex",
        return_value=[[], [], [MOCK_IP]],
    ):
        mock_socket.return_value.setblocking = Mock(return_value=None)
        mock_socket.return_value.getsockname = Mock(
            return_value=(MOCK_IP, MOCK_LOCAL_PORT)
        )

        def out_1(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8")) == clean_request(
                load_fixture("register_first_out_data.txt").replace("\\r\\n", "\r\n")
            )

            return 1

        def out_2(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8")) == clean_request(
                load_fixture("register_out_data.txt").replace("\\r\\n", "\r\n")
            )

            return 1

        def out_3(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8"), True) == clean_request(
                load_fixture("deregister_first_out_data.txt").replace("\\r\\n", "\r\n"),
                True,
            )

            return 1

        def out_4(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8"), True) == clean_request(
                load_fixture("deregister_out_data.txt").replace("\\r\\n", "\r\n"), True
            )

            return 1

        mock_socket.return_value.sendto = Mock(
            side_effect=MultipleSideEffect(out_1, out_2, out_3, out_4)
        )

        def in_1(*args) -> bytes:
            return str.encode(load_fixture("register_first_data.txt"))

        def in_2(*args) -> bytes:
            return str.encode(load_fixture("register_data.txt"))

        def in_3(*args) -> bytes:
            return str.encode(load_fixture("deregister_data.txt"))

        mock_socket.return_value.recv = Mock(
            side_effect=MultipleSideEffect(in_1, in_2, in_1, in_3)
        )

        voip: IntercomVoip = IntercomVoip(
            hass, MOCK_ADDRESS, MOCK_PORT, MOCK_USERNAME, MOCK_PASSWORD, _callback
        )

        assert await voip.start()
        assert await voip.stop()

        assert len(mock_select.mock_calls) == 4


@pytest.mark.asyncio
async def test_stop_error(hass: HomeAssistant) -> None:
    """Start stop error"""

    async def _callback() -> None:
        """Callback"""

    with patch(
        "custom_components.tattelecom_intercom.sip.socket.socket"
    ) as mock_socket, patch(
        "custom_components.tattelecom_intercom.sip.select.select",
        return_value=(True, True, True),
    ) as mock_select, patch(
        "custom_components.tattelecom_intercom.voip.socket.gethostbyname_ex",
        return_value=[[], [], [MOCK_IP]],
    ):
        mock_socket.return_value.setblocking = Mock(return_value=None)
        mock_socket.return_value.getsockname = Mock(
            return_value=(MOCK_IP, MOCK_LOCAL_PORT)
        )

        def out_1(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8")) == clean_request(
                load_fixture("register_first_out_data.txt").replace("\\r\\n", "\r\n")
            )

            return 1

        def out_2(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8")) == clean_request(
                load_fixture("register_out_data.txt").replace("\\r\\n", "\r\n")
            )

            return 1

        def out_3(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8"), True) == clean_request(
                load_fixture("deregister_first_out_data.txt").replace("\\r\\n", "\r\n"),
                True,
            )

            return 1

        def out_4(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8"), True) == clean_request(
                load_fixture("deregister_out_data.txt").replace("\\r\\n", "\r\n"), True
            )

            return 1

        mock_socket.return_value.sendto = Mock(
            side_effect=MultipleSideEffect(out_1, out_2, out_3, out_4)
        )

        def in_1(*args) -> bytes:
            return str.encode(load_fixture("register_first_data.txt"))

        def in_2(*args) -> bytes:
            return str.encode(load_fixture("register_data.txt"))

        def in_3(*args) -> bytes:
            raise IntercomError()

        mock_socket.return_value.recv = Mock(
            side_effect=MultipleSideEffect(in_1, in_2, in_1, in_3)
        )

        voip: IntercomVoip = IntercomVoip(
            hass, MOCK_ADDRESS, MOCK_PORT, MOCK_USERNAME, MOCK_PASSWORD, _callback
        )

        assert await voip.start()
        assert not await voip.stop()

        assert len(mock_select.mock_calls) == 4


@pytest.mark.asyncio
async def test_stop_not_started(hass: HomeAssistant) -> None:
    """Start stop not started"""

    async def _callback() -> None:
        """Callback"""

    with patch(
        "custom_components.tattelecom_intercom.sip.socket.socket"
    ) as mock_socket, patch(
        "custom_components.tattelecom_intercom.sip.select.select",
        return_value=(True, True, True),
    ) as mock_select, patch(
        "custom_components.tattelecom_intercom.voip.socket.gethostbyname_ex",
        return_value=[[], [], [MOCK_IP]],
    ):
        mock_socket.return_value.setblocking = Mock(return_value=None)
        mock_socket.return_value.getsockname = Mock(
            return_value=(MOCK_IP, MOCK_LOCAL_PORT)
        )

        voip: IntercomVoip = IntercomVoip(
            hass, MOCK_ADDRESS, MOCK_PORT, MOCK_USERNAME, MOCK_PASSWORD, _callback
        )

        assert await voip.stop()

        assert len(mock_select.mock_calls) == 0


@pytest.mark.asyncio
async def test_stop_timeout_error(hass: HomeAssistant) -> None:
    """Start stop timeout error"""

    async def _callback() -> None:
        """Callback"""

    def timeout_ok(*args) -> tuple:
        return [True], [True], [True]

    def timeout_err(*args) -> tuple:
        return [], [], []

    with patch(
        "custom_components.tattelecom_intercom.sip.socket.socket"
    ) as mock_socket, patch(
        "custom_components.tattelecom_intercom.sip.select.select",
        side_effect=MultipleSideEffect(timeout_ok, timeout_ok, timeout_err),
    ) as mock_select, patch(
        "custom_components.tattelecom_intercom.voip.socket.gethostbyname_ex",
        return_value=[[], [], [MOCK_IP]],
    ):
        mock_socket.return_value.setblocking = Mock(return_value=None)
        mock_socket.return_value.getsockname = Mock(
            return_value=(MOCK_IP, MOCK_LOCAL_PORT)
        )

        def out_1(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8")) == clean_request(
                load_fixture("register_first_out_data.txt").replace("\\r\\n", "\r\n")
            )

            return 1

        def out_2(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8")) == clean_request(
                load_fixture("register_out_data.txt").replace("\\r\\n", "\r\n")
            )

            return 1

        def out_3(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8"), True) == clean_request(
                load_fixture("deregister_first_out_data.txt").replace("\\r\\n", "\r\n"),
                True,
            )

            return 1

        mock_socket.return_value.sendto = Mock(
            side_effect=MultipleSideEffect(out_1, out_2, out_3)
        )

        def in_1(*args) -> bytes:
            return str.encode(load_fixture("register_first_data.txt"))

        def in_2(*args) -> bytes:
            return str.encode(load_fixture("register_data.txt"))

        mock_socket.return_value.recv = Mock(
            side_effect=MultipleSideEffect(in_1, in_2, in_1)
        )

        voip: IntercomVoip = IntercomVoip(
            hass, MOCK_ADDRESS, MOCK_PORT, MOCK_USERNAME, MOCK_PASSWORD, _callback
        )

        assert await voip.start()
        assert not await voip.stop()

        assert len(mock_select.mock_calls) == 3


@pytest.mark.asyncio
async def test_stop_timeout_error_two(hass: HomeAssistant) -> None:
    """Start stop timeout error"""

    async def _callback() -> None:
        """Callback"""

    def timeout_ok(*args) -> tuple:
        return [True], [True], [True]

    def timeout_err(*args) -> tuple:
        return [], [], []

    with patch(
        "custom_components.tattelecom_intercom.sip.socket.socket"
    ) as mock_socket, patch(
        "custom_components.tattelecom_intercom.sip.select.select",
        side_effect=MultipleSideEffect(timeout_ok, timeout_ok, timeout_ok, timeout_err),
    ) as mock_select, patch(
        "custom_components.tattelecom_intercom.voip.socket.gethostbyname_ex",
        return_value=[[], [], [MOCK_IP]],
    ):
        mock_socket.return_value.setblocking = Mock(return_value=None)
        mock_socket.return_value.getsockname = Mock(
            return_value=(MOCK_IP, MOCK_LOCAL_PORT)
        )

        def out_1(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8")) == clean_request(
                load_fixture("register_first_out_data.txt").replace("\\r\\n", "\r\n")
            )

            return 1

        def out_2(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8")) == clean_request(
                load_fixture("register_out_data.txt").replace("\\r\\n", "\r\n")
            )

            return 1

        def out_3(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8"), True) == clean_request(
                load_fixture("deregister_first_out_data.txt").replace("\\r\\n", "\r\n"),
                True,
            )

            return 1

        def out_4(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8"), True) == clean_request(
                load_fixture("deregister_out_data.txt").replace("\\r\\n", "\r\n"), True
            )

            return 1

        mock_socket.return_value.sendto = Mock(
            side_effect=MultipleSideEffect(out_1, out_2, out_3, out_4)
        )

        def in_1(*args) -> bytes:
            return str.encode(load_fixture("register_first_data.txt"))

        def in_2(*args) -> bytes:
            return str.encode(load_fixture("register_data.txt"))

        def in_3(*args) -> bytes:
            return str.encode(load_fixture("deregister_data.txt"))

        mock_socket.return_value.recv = Mock(
            side_effect=MultipleSideEffect(in_1, in_2, in_1, in_3)
        )

        voip: IntercomVoip = IntercomVoip(
            hass, MOCK_ADDRESS, MOCK_PORT, MOCK_USERNAME, MOCK_PASSWORD, _callback
        )

        assert await voip.start()
        assert not await voip.stop()

        assert len(mock_select.mock_calls) == 4


@pytest.mark.asyncio
async def test_stop_server_error(hass: HomeAssistant) -> None:
    """Start stop server error"""

    async def _callback() -> None:
        """Callback"""

    with patch(
        "custom_components.tattelecom_intercom.sip.socket.socket"
    ) as mock_socket, patch(
        "custom_components.tattelecom_intercom.sip.select.select",
        return_value=(True, True, True),
    ) as mock_select, patch(
        "custom_components.tattelecom_intercom.voip.socket.gethostbyname_ex",
        return_value=[[], [], [MOCK_IP]],
    ), patch(
        "custom_components.tattelecom_intercom.sip.asyncio.sleep", return_value=None
    ):
        mock_socket.return_value.setblocking = Mock(return_value=None)
        mock_socket.return_value.getsockname = Mock(
            return_value=(MOCK_IP, MOCK_LOCAL_PORT)
        )

        def out_1(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8")) == clean_request(
                load_fixture("register_first_out_data.txt").replace("\\r\\n", "\r\n")
            )

            return 1

        def out_2(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8")) == clean_request(
                load_fixture("register_out_data.txt").replace("\\r\\n", "\r\n")
            )

            return 1

        def out_3(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8"), True) == clean_request(
                load_fixture("deregister_first_out_data.txt").replace("\\r\\n", "\r\n"),
                True,
            )

            return 1

        def out_4(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8"), True) == clean_request(
                load_fixture("deregister_out_data.txt").replace("\\r\\n", "\r\n"), True
            )

            return 1

        mock_socket.return_value.sendto = Mock(
            side_effect=MultipleSideEffect(out_1, out_2, out_3, out_4, out_3, out_4)
        )

        def in_1(*args) -> bytes:
            return str.encode(load_fixture("register_first_data.txt"))

        def in_2(*args) -> bytes:
            return str.encode(load_fixture("register_data.txt"))

        def in_3(*args) -> bytes:
            return str.encode(load_fixture("deregister_data.txt"))

        def in_4(*args) -> bytes:
            return str.encode(load_fixture("server_error_data.txt"))

        mock_socket.return_value.recv = Mock(
            side_effect=MultipleSideEffect(in_1, in_2, in_1, in_4, in_1, in_3)
        )

        voip: IntercomVoip = IntercomVoip(
            hass, MOCK_ADDRESS, MOCK_PORT, MOCK_USERNAME, MOCK_PASSWORD, _callback
        )

        assert await voip.start()
        assert await voip.stop()

        assert len(mock_select.mock_calls) == 6


@pytest.mark.asyncio
async def test_safe_start(hass: HomeAssistant) -> None:
    """Start safe start"""

    async def _callback() -> None:
        """Callback"""

    with patch(
        "custom_components.tattelecom_intercom.sip.socket.socket"
    ) as mock_socket, patch(
        "custom_components.tattelecom_intercom.sip.select.select",
        return_value=(True, True, True),
    ) as mock_select, patch(
        "custom_components.tattelecom_intercom.voip.socket.gethostbyname_ex",
        return_value=[[], [], [MOCK_IP]],
    ):
        mock_socket.return_value.setblocking = Mock(return_value=None)
        mock_socket.return_value.getsockname = Mock(
            return_value=(MOCK_IP, MOCK_LOCAL_PORT)
        )

        def out_1(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8")) == clean_request(
                load_fixture("register_first_out_data.txt").replace("\\r\\n", "\r\n")
            )

            return 1

        def out_2(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8")) == clean_request(
                load_fixture("register_out_data.txt").replace("\\r\\n", "\r\n")
            )

            return 1

        def out_3(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8"), True) == clean_request(
                load_fixture("deregister_first_out_data.txt").replace("\\r\\n", "\r\n"),
                True,
            )

            return 1

        def out_4(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8"), True) == clean_request(
                load_fixture("deregister_out_data.txt").replace("\\r\\n", "\r\n"), True
            )

            return 1

        mock_socket.return_value.sendto = Mock(
            side_effect=MultipleSideEffect(out_3, out_4, out_1, out_2)
        )

        def in_1(*args) -> bytes:
            return str.encode(load_fixture("register_first_data.txt"))

        def in_2(*args) -> bytes:
            return str.encode(load_fixture("register_data.txt"))

        def in_3(*args) -> bytes:
            return str.encode(load_fixture("deregister_data.txt"))

        mock_socket.return_value.recv = Mock(
            side_effect=MultipleSideEffect(in_1, in_3, in_1, in_2)
        )

        voip: IntercomVoip = IntercomVoip(
            hass, MOCK_ADDRESS, MOCK_PORT, MOCK_USERNAME, MOCK_PASSWORD, _callback
        )

        assert await voip.safe_start()

        soft_stop(voip)

        assert len(mock_select.mock_calls) == 4


@pytest.mark.asyncio
async def test_safe_start_retry(hass: HomeAssistant) -> None:
    """Start safe start retry"""

    async def _callback() -> None:
        """Callback"""

    with patch(
        "custom_components.tattelecom_intercom.sip.socket.socket"
    ) as mock_socket, patch(
        "custom_components.tattelecom_intercom.sip.select.select",
        return_value=(True, True, True),
    ) as mock_select, patch(
        "custom_components.tattelecom_intercom.voip.socket.gethostbyname_ex",
        return_value=[[], [], [MOCK_IP]],
    ):
        mock_socket.return_value.setblocking = Mock(return_value=None)
        mock_socket.return_value.getsockname = Mock(
            return_value=(MOCK_IP, MOCK_LOCAL_PORT)
        )

        def out_1(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8")) == clean_request(
                load_fixture("register_first_out_data.txt").replace("\\r\\n", "\r\n")
            )

            return 1

        def out_2(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8")) == clean_request(
                load_fixture("register_out_data.txt").replace("\\r\\n", "\r\n")
            )

            return 1

        def out_3(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8"), True) == clean_request(
                load_fixture("deregister_first_out_data.txt").replace("\\r\\n", "\r\n"),
                True,
            )

            return 1

        def out_4(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8"), True) == clean_request(
                load_fixture("deregister_out_data.txt").replace("\\r\\n", "\r\n"), True
            )

            return 1

        mock_socket.return_value.sendto = Mock(
            side_effect=MultipleSideEffect(out_3, out_4, out_3, out_4, out_1, out_2)
        )

        def in_1(*args) -> bytes:
            return str.encode(load_fixture("register_first_data.txt"))

        def in_2(*args) -> bytes:
            return str.encode(load_fixture("register_data.txt"))

        def in_3(*args) -> bytes:
            return str.encode(load_fixture("deregister_data.txt"))

        def in_4(*args) -> bytes:
            raise IntercomError()

        mock_socket.return_value.recv = Mock(
            side_effect=MultipleSideEffect(in_1, in_4, in_1, in_3, in_1, in_2)
        )

        voip: IntercomVoip = IntercomVoip(
            hass, MOCK_ADDRESS, MOCK_PORT, MOCK_USERNAME, MOCK_PASSWORD, _callback
        )

        assert await voip.safe_start(1, 0)

        soft_stop(voip)

        assert len(mock_select.mock_calls) == 6


@pytest.mark.asyncio
async def test_safe_start_error(hass: HomeAssistant) -> None:
    """Start safe start error"""

    async def _callback() -> None:
        """Callback"""

    with patch(
        "custom_components.tattelecom_intercom.sip.socket.socket"
    ) as mock_socket, patch(
        "custom_components.tattelecom_intercom.sip.select.select",
        return_value=(True, True, True),
    ) as mock_select, patch(
        "custom_components.tattelecom_intercom.voip.socket.gethostbyname_ex",
        return_value=[[], [], [MOCK_IP]],
    ):
        mock_socket.return_value.setblocking = Mock(return_value=None)
        mock_socket.return_value.getsockname = Mock(
            return_value=(MOCK_IP, MOCK_LOCAL_PORT)
        )

        def out_1(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8"), True) == clean_request(
                load_fixture("deregister_first_out_data.txt").replace("\\r\\n", "\r\n"),
                True,
            )

            return 1

        def out_2(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8"), True) == clean_request(
                load_fixture("deregister_out_data.txt").replace("\\r\\n", "\r\n"), True
            )

            return 1

        mock_socket.return_value.sendto = Mock(
            side_effect=MultipleSideEffect(out_1, out_2)
        )

        def in_1(*args) -> bytes:
            return str.encode(load_fixture("register_first_data.txt"))

        def in_2(*args) -> bytes:
            raise IntercomError()

        mock_socket.return_value.recv = Mock(side_effect=MultipleSideEffect(in_1, in_2))

        voip: IntercomVoip = IntercomVoip(
            hass, MOCK_ADDRESS, MOCK_PORT, MOCK_USERNAME, MOCK_PASSWORD, _callback
        )

        assert not await voip.safe_start()

        soft_stop(voip)

        assert len(mock_select.mock_calls) == 2


@pytest.mark.asyncio
async def test_safe_register(hass: HomeAssistant) -> None:
    """Safe register test"""

    async def _callback() -> None:
        """Callback"""

    with patch(
        "custom_components.tattelecom_intercom.sip.socket.socket"
    ) as mock_socket, patch(
        "custom_components.tattelecom_intercom.sip.select.select",
        return_value=(True, True, True),
    ) as mock_select, patch(
        "custom_components.tattelecom_intercom.voip.socket.gethostbyname_ex",
        return_value=[[], [], [MOCK_IP]],
    ), patch(
        "custom_components.tattelecom_intercom.sip.asyncio.sleep", return_value=None
    ):
        mock_socket.return_value.setblocking = Mock(return_value=None)
        mock_socket.return_value.getsockname = Mock(
            return_value=(MOCK_IP, MOCK_LOCAL_PORT)
        )

        def out_1(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8"), True) == clean_request(
                load_fixture("register_first_out_data.txt").replace("\\r\\n", "\r\n"),
                True,
            )

            return 1

        def out_2(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8"), True) == clean_request(
                load_fixture("register_out_data.txt").replace("\\r\\n", "\r\n"), True
            )

            return 1

        mock_socket.return_value.sendto = Mock(
            side_effect=MultipleSideEffect(out_1, out_2, out_1, out_2)
        )

        def in_1(*args) -> bytes:
            return str.encode(load_fixture("register_first_data.txt"))

        def in_2(*args) -> bytes:
            return str.encode(load_fixture("register_data.txt"))

        mock_socket.return_value.recv = Mock(
            side_effect=MultipleSideEffect(in_1, in_2, in_1, in_2)
        )

        voip: IntercomVoip = IntercomVoip(
            hass, MOCK_ADDRESS, MOCK_PORT, MOCK_USERNAME, MOCK_PASSWORD, _callback
        )

        assert await voip.start()
        voip.sip.recv_loop.cancel()  # type: ignore
        voip.sip.ping_loop.cancel()  # type: ignore

        async_fire_time_changed(hass, utcnow() + timedelta(seconds=SIP_EXPIRES))
        await hass.async_block_till_done()

        assert len(mock_select.mock_calls) == 5


@pytest.mark.asyncio
async def test_safe_register_error(hass: HomeAssistant) -> None:
    """Safe register test error"""

    async def _callback() -> None:
        """Callback"""

    with patch(
        "custom_components.tattelecom_intercom.sip.socket.socket"
    ) as mock_socket, patch(
        "custom_components.tattelecom_intercom.sip.select.select",
        return_value=(True, True, True),
    ) as mock_select, patch(
        "custom_components.tattelecom_intercom.voip.socket.gethostbyname_ex",
        return_value=[[], [], [MOCK_IP]],
    ), patch(
        "custom_components.tattelecom_intercom.sip.asyncio.sleep", return_value=None
    ):
        mock_socket.return_value.setblocking = Mock(return_value=None)
        mock_socket.return_value.getsockname = Mock(
            return_value=(MOCK_IP, MOCK_LOCAL_PORT)
        )

        def out_1(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8"), True) == clean_request(
                load_fixture("register_first_out_data.txt").replace("\\r\\n", "\r\n"),
                True,
            )

            return 1

        def out_2(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8"), True) == clean_request(
                load_fixture("register_out_data.txt").replace("\\r\\n", "\r\n"), True
            )

            return 1

        def out_3(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8"), True) == clean_request(
                load_fixture("deregister_first_out_data.txt").replace("\\r\\n", "\r\n"),
                True,
            )

            return 1

        def out_4(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8"), True) == clean_request(
                load_fixture("deregister_out_data.txt").replace("\\r\\n", "\r\n"), True
            )

            return 1

        mock_socket.return_value.sendto = Mock(
            side_effect=MultipleSideEffect(
                out_1, out_2, out_3, out_4, out_3, out_4, out_1, out_2
            )
        )

        voip: IntercomVoip | None = None

        def in_1(*args) -> bytes:
            return str.encode(load_fixture("register_first_data.txt"))

        def in_2(*args) -> bytes:
            return str.encode(load_fixture("register_data.txt"))

        def in_2f(*args) -> bytes:
            soft_stop(voip)
            return str.encode(load_fixture("register_data.txt"))

        def in_3(*args) -> bytes:
            return str.encode(load_fixture("deregister_data.txt"))

        def in_4(*args) -> bytes:
            return str.encode(load_fixture("bad_request_data.txt"))

        mock_socket.return_value.recv = Mock(
            side_effect=MultipleSideEffect(
                in_1, in_2, in_1, in_4, in_1, in_3, in_1, in_2f
            )
        )

        voip = IntercomVoip(
            hass, MOCK_ADDRESS, MOCK_PORT, MOCK_USERNAME, MOCK_PASSWORD, _callback
        )

        assert await voip.start()
        voip.sip.recv_loop.cancel()  # type: ignore
        voip.sip.ping_loop.cancel()  # type: ignore

        async_fire_time_changed(hass, utcnow() + timedelta(seconds=SIP_EXPIRES))
        await hass.async_block_till_done()

        async_fire_time_changed(hass, utcnow() + timedelta(seconds=SIP_RETRY_SLEEP))
        await hass.async_block_till_done()

        assert len(mock_select.mock_calls) == 6


@pytest.mark.asyncio
async def test_invite(hass: HomeAssistant) -> None:
    """Invite test"""

    with patch(
        "custom_components.tattelecom_intercom.sip.socket.socket"
    ) as mock_socket, patch(
        "custom_components.tattelecom_intercom.sip.select.select",
        return_value=(True, True, True),
    ) as mock_select, patch(
        "custom_components.tattelecom_intercom.voip.socket.gethostbyname_ex",
        return_value=[[], [], [MOCK_IP]],
    ), patch(
        "custom_components.tattelecom_intercom.sip.asyncio.sleep", return_value=None
    ):
        mock_socket.return_value.setblocking = Mock(return_value=None)
        mock_socket.return_value.getsockname = Mock(
            return_value=(MOCK_IP, MOCK_LOCAL_PORT)
        )

        def out_1(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8"), True) == clean_request(
                load_fixture("register_first_out_data.txt").replace("\\r\\n", "\r\n"),
                True,
            )

            return 1

        def out_2(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8"), True) == clean_request(
                load_fixture("register_out_data.txt").replace("\\r\\n", "\r\n"), True
            )

            return 1

        def out_3(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_cseq_request(data.decode("utf-8")) == clean_cseq_request(
                load_fixture("trying_out_data.txt").replace("\\r\\n", "\r\n")
            )

            return 1

        def out_4(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_cseq_request(data.decode("utf-8"), True) == clean_cseq_request(
                load_fixture("ringing_out_data.txt").replace("\\r\\n", "\r\n"), True
            )

            return 1

        mock_socket.return_value.sendto = Mock(
            side_effect=MultipleSideEffect(out_1, out_2, out_3, out_4)
        )

        def in_1(*args) -> bytes:
            return str.encode(load_fixture("register_first_data.txt"))

        def in_2(*args) -> bytes:
            return str.encode(load_fixture("register_data.txt"))

        def in_3(*args) -> bytes:
            return str.encode(load_fixture("invite_data.txt"))

        mock_socket.return_value.recv = Mock(
            side_effect=MultipleSideEffect(in_1, in_2, in_3)
        )

        voip: IntercomVoip | None = None

        async def _callback(call: Call) -> None:
            """Callback"""

            call_dict: dict = call.as_dict()
            assert call_dict["state"] == CallState.RINGING
            assert call_dict["_phone"] == voip
            assert (
                call_dict["call_id"]
                == "42707deb5c366d722cf1ae041d97ac1d@217.0.0.1:9740"
            )
            assert call_dict["local_ip"] == MOCK_IP
            assert call_dict["_send_mode"] == SendMode.SEND_RECV
            assert list(call_dict["_assigned_ports"].values())[0] == {
                8: RtpPayloadType.PCMA,
                101: RtpPayloadType.EVENT,
            }
            assert call_dict["_connections"] == 1
            assert call_dict["_audio_ports"] == 1
            assert call_dict["_video_ports"] == 1

            soft_stop(voip)

        voip = IntercomVoip(
            hass, MOCK_ADDRESS, MOCK_PORT, MOCK_USERNAME, MOCK_PASSWORD, _callback, True
        )

        assert await voip.start()

        async_fire_time_changed(hass, utcnow() + timedelta(seconds=1))
        await hass.async_block_till_done()

        assert len(mock_select.mock_calls) == 2


@pytest.mark.asyncio
async def test_invite_stop(hass: HomeAssistant) -> None:
    """Invite stop test"""

    with patch(
        "custom_components.tattelecom_intercom.sip.socket.socket"
    ) as mock_socket, patch(
        "custom_components.tattelecom_intercom.sip.select.select",
        return_value=(True, True, True),
    ) as mock_select, patch(
        "custom_components.tattelecom_intercom.voip.socket.gethostbyname_ex",
        return_value=[[], [], [MOCK_IP]],
    ), patch(
        "custom_components.tattelecom_intercom.sip.asyncio.sleep", return_value=None
    ):
        mock_socket.return_value.setblocking = Mock(return_value=None)
        mock_socket.return_value.getsockname = Mock(
            return_value=(MOCK_IP, MOCK_LOCAL_PORT)
        )

        def out_1(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8"), True) == clean_request(
                load_fixture("register_first_out_data.txt").replace("\\r\\n", "\r\n"),
                True,
            )

            return 1

        def out_2(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8"), True) == clean_request(
                load_fixture("register_out_data.txt").replace("\\r\\n", "\r\n"), True
            )

            return 1

        def out_3(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_cseq_request(data.decode("utf-8")) == clean_cseq_request(
                load_fixture("trying_out_data.txt").replace("\\r\\n", "\r\n")
            )

            return 1

        def out_4(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_cseq_request(data.decode("utf-8"), True) == clean_cseq_request(
                load_fixture("ringing_out_data.txt").replace("\\r\\n", "\r\n"), True
            )

            return 1

        def out_5(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8"), True) == clean_request(
                load_fixture("deregister_first_out_data.txt").replace("\\r\\n", "\r\n"),
                True,
            )

            return 1

        def out_6(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8"), True) == clean_request(
                load_fixture("deregister_out_data.txt").replace("\\r\\n", "\r\n"), True
            )

            return 1

        mock_socket.return_value.sendto = Mock(
            side_effect=MultipleSideEffect(out_1, out_2, out_3, out_4, out_5, out_6)
        )

        def in_1(*args) -> bytes:
            return str.encode(load_fixture("register_first_data.txt"))

        def in_2(*args) -> bytes:
            return str.encode(load_fixture("register_data.txt"))

        def in_3(*args) -> bytes:
            return str.encode(load_fixture("invite_data.txt"))

        def in_4(*args) -> bytes:
            return str.encode(load_fixture("deregister_data.txt"))

        mock_socket.return_value.recv = Mock(
            side_effect=MultipleSideEffect(in_1, in_2, in_3, in_1, in_4)
        )

        voip: IntercomVoip | None = None

        async def _callback(call: Call) -> None:
            """Callback"""

            call_dict: dict = call.as_dict()
            assert call_dict["state"] == CallState.RINGING
            assert call_dict["_phone"] == voip
            assert (
                call_dict["call_id"]
                == "42707deb5c366d722cf1ae041d97ac1d@217.0.0.1:9740"
            )
            assert call_dict["local_ip"] == MOCK_IP
            assert call_dict["_send_mode"] == SendMode.SEND_RECV
            assert list(call_dict["_assigned_ports"].values())[0] == {
                8: RtpPayloadType.PCMA,
                101: RtpPayloadType.EVENT,
            }
            assert call_dict["_connections"] == 1
            assert call_dict["_audio_ports"] == 1
            assert call_dict["_video_ports"] == 1

            assert await voip.stop()

            soft_stop(voip)

        voip = IntercomVoip(
            hass, MOCK_ADDRESS, MOCK_PORT, MOCK_USERNAME, MOCK_PASSWORD, _callback, True
        )

        assert await voip.start()

        async_fire_time_changed(hass, utcnow() + timedelta(seconds=1))
        await hass.async_block_till_done()

        assert len(mock_select.mock_calls) == 2


@pytest.mark.asyncio
async def test_invite_cancel(hass: HomeAssistant) -> None:
    """Invite cancel test"""

    with patch(
        "custom_components.tattelecom_intercom.sip.socket.socket"
    ) as mock_socket, patch(
        "custom_components.tattelecom_intercom.sip.select.select",
        return_value=(True, True, True),
    ) as mock_select, patch(
        "custom_components.tattelecom_intercom.voip.socket.gethostbyname_ex",
        return_value=[[], [], [MOCK_IP]],
    ):
        mock_socket.return_value.setblocking = Mock(return_value=None)
        mock_socket.return_value.getsockname = Mock(
            return_value=(MOCK_IP, MOCK_LOCAL_PORT)
        )

        def out_1(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8"), True) == clean_request(
                load_fixture("register_first_out_data.txt").replace("\\r\\n", "\r\n"),
                True,
            )

            return 1

        def out_2(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8"), True) == clean_request(
                load_fixture("register_out_data.txt").replace("\\r\\n", "\r\n"), True
            )

            return 1

        def out_3(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_cseq_request(data.decode("utf-8")) == clean_cseq_request(
                load_fixture("trying_out_data.txt").replace("\\r\\n", "\r\n")
            )

            return 1

        def out_4(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_cseq_request(data.decode("utf-8"), True) == clean_cseq_request(
                load_fixture("ringing_out_data.txt").replace("\\r\\n", "\r\n"), True
            )

            return 1

        def out_5(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_cseq_request(data.decode("utf-8"), True) == clean_cseq_request(
                load_fixture("cancel_out_data.txt").replace("\\r\\n", "\r\n"), True
            )

            return 1

        def out_6(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_cseq_request(data.decode("utf-8"), True) == clean_cseq_request(
                load_fixture("terminated_out_data.txt").replace("\\r\\n", "\r\n"), True
            )

            return 1

        mock_socket.return_value.sendto = Mock(
            side_effect=MultipleSideEffect(out_1, out_2, out_3, out_4, out_5, out_6)
        )

        def in_1(*args) -> bytes:
            return str.encode(load_fixture("register_first_data.txt"))

        def in_2(*args) -> bytes:
            return str.encode(load_fixture("register_data.txt"))

        def in_3(*args) -> bytes:
            return str.encode(load_fixture("invite_data.txt"))

        def in_4(*args) -> bytes:
            return str.encode(load_fixture("cancel_data.txt"))

        mock_socket.return_value.recv = Mock(
            side_effect=MultipleSideEffect(in_1, in_2, in_3, in_4)
        )

        voip: IntercomVoip | None = None

        async def _callback(call: Call) -> None:
            """Callback"""

            call_dict: dict = call.as_dict()

            if call.state == CallState.RINGING:
                assert call_dict["state"] == CallState.RINGING
                assert call_dict["_phone"] == voip
                assert (
                    call_dict["call_id"]
                    == "42707deb5c366d722cf1ae041d97ac1d@217.0.0.1:9740"
                )
                assert call_dict["local_ip"] == MOCK_IP
                assert call_dict["_send_mode"] == SendMode.SEND_RECV
                assert list(call_dict["_assigned_ports"].values())[0] == {
                    8: RtpPayloadType.PCMA,
                    101: RtpPayloadType.EVENT,
                }
                assert call_dict["_connections"] == 1
                assert call_dict["_audio_ports"] == 1
                assert call_dict["_video_ports"] == 1

                return

            if call.state == CallState.ENDED:
                assert call_dict["state"] == CallState.ENDED
                assert call_dict["_phone"] == voip
                assert (
                    call_dict["call_id"]
                    == "42707deb5c366d722cf1ae041d97ac1d@217.0.0.1:9740"
                )

                soft_stop(voip)

        voip = IntercomVoip(
            hass, MOCK_ADDRESS, MOCK_PORT, MOCK_USERNAME, MOCK_PASSWORD, _callback, True
        )

        assert await voip.start()
        voip.sip.ping_loop.cancel()  # type: ignore

        while voip.sip._started:
            await asyncio.sleep(1)
            async_fire_time_changed(hass, utcnow() + timedelta(seconds=1))

        await hass.async_block_till_done()

        assert len(mock_select.mock_calls) == 2


@pytest.mark.asyncio
async def test_invite_bye(hass: HomeAssistant) -> None:
    """Invite bye test"""

    with patch(
        "custom_components.tattelecom_intercom.sip.socket.socket"
    ) as mock_socket, patch(
        "custom_components.tattelecom_intercom.sip.select.select",
        return_value=(True, True, True),
    ) as mock_select, patch(
        "custom_components.tattelecom_intercom.voip.socket.gethostbyname_ex",
        return_value=[[], [], [MOCK_IP]],
    ):
        mock_socket.return_value.setblocking = Mock(return_value=None)
        mock_socket.return_value.getsockname = Mock(
            return_value=(MOCK_IP, MOCK_LOCAL_PORT)
        )

        def out_1(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8"), True) == clean_request(
                load_fixture("register_first_out_data.txt").replace("\\r\\n", "\r\n"),
                True,
            )

            return 1

        def out_2(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8"), True) == clean_request(
                load_fixture("register_out_data.txt").replace("\\r\\n", "\r\n"), True
            )

            return 1

        def out_3(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_cseq_request(data.decode("utf-8")) == clean_cseq_request(
                load_fixture("trying_out_data.txt").replace("\\r\\n", "\r\n")
            )

            return 1

        def out_4(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_cseq_request(data.decode("utf-8"), True) == clean_cseq_request(
                load_fixture("ringing_out_data.txt").replace("\\r\\n", "\r\n"), True
            )

            return 1

        def out_5(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_cseq_request(data.decode("utf-8"), True) == clean_cseq_request(
                load_fixture("bye_ok_out_data.txt").replace("\\r\\n", "\r\n"), True
            )

            return 1

        mock_socket.return_value.sendto = Mock(
            side_effect=MultipleSideEffect(out_1, out_2, out_3, out_4, out_5)
        )

        def in_1(*args) -> bytes:
            return str.encode(load_fixture("register_first_data.txt"))

        def in_2(*args) -> bytes:
            return str.encode(load_fixture("register_data.txt"))

        def in_3(*args) -> bytes:
            return str.encode(load_fixture("invite_data.txt"))

        def in_4(*args) -> bytes:
            return str.encode(load_fixture("bye_data.txt"))

        mock_socket.return_value.recv = Mock(
            side_effect=MultipleSideEffect(in_1, in_2, in_3, in_4)
        )

        voip: IntercomVoip | None = None

        async def _callback(call: Call) -> None:
            """Callback"""
            call_dict: dict = call.as_dict()

            if call.state == CallState.RINGING:
                assert call_dict["state"] == CallState.RINGING
                assert call_dict["_phone"] == voip
                assert (
                    call_dict["call_id"]
                    == "42707deb5c366d722cf1ae041d97ac1d@217.0.0.1:9740"
                )
                assert call_dict["local_ip"] == MOCK_IP
                assert call_dict["_send_mode"] == SendMode.SEND_RECV
                assert list(call_dict["_assigned_ports"].values())[0] == {
                    8: RtpPayloadType.PCMA,
                    101: RtpPayloadType.EVENT,
                }
                assert call_dict["_connections"] == 1
                assert call_dict["_audio_ports"] == 1
                assert call_dict["_video_ports"] == 1

            if call.state == CallState.ENDED:
                assert call_dict["state"] == CallState.ENDED
                assert call_dict["_phone"] == voip
                assert (
                    call_dict["call_id"]
                    == "42707deb5c366d722cf1ae041d97ac1d@217.0.0.1:9740"
                )

                soft_stop(voip)

        voip = IntercomVoip(
            hass, MOCK_ADDRESS, MOCK_PORT, MOCK_USERNAME, MOCK_PASSWORD, _callback, True
        )

        assert await voip.start()
        voip.sip.ping_loop.cancel()  # type: ignore

        while voip.sip._started:
            await asyncio.sleep(1)
            async_fire_time_changed(hass, utcnow() + timedelta(seconds=1))

        await hass.async_block_till_done()

        assert len(mock_select.mock_calls) == 2


@pytest.mark.asyncio
async def test_invite_decline(hass: HomeAssistant) -> None:
    """Invite decline test"""

    with patch(
        "custom_components.tattelecom_intercom.sip.socket.socket"
    ) as mock_socket, patch(
        "custom_components.tattelecom_intercom.sip.select.select",
        return_value=(True, True, True),
    ) as mock_select, patch(
        "custom_components.tattelecom_intercom.voip.socket.gethostbyname_ex",
        return_value=[[], [], [MOCK_IP]],
    ):
        mock_socket.return_value.setblocking = Mock(return_value=None)
        mock_socket.return_value.getsockname = Mock(
            return_value=(MOCK_IP, MOCK_LOCAL_PORT)
        )

        def out_1(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8"), True) == clean_request(
                load_fixture("register_first_out_data.txt").replace("\\r\\n", "\r\n"),
                True,
            )

            return 1

        def out_2(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8"), True) == clean_request(
                load_fixture("register_out_data.txt").replace("\\r\\n", "\r\n"), True
            )

            return 1

        def out_3(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_cseq_request(data.decode("utf-8")) == clean_cseq_request(
                load_fixture("trying_out_data.txt").replace("\\r\\n", "\r\n")
            )

            return 1

        def out_4(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_cseq_request(data.decode("utf-8"), True) == clean_cseq_request(
                load_fixture("ringing_out_data.txt").replace("\\r\\n", "\r\n"), True
            )

            return 1

        def out_5(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_cseq_request(data.decode("utf-8"), True) == clean_cseq_request(
                load_fixture("decline_out_data.txt").replace("\\r\\n", "\r\n"), True
            )

            return 1

        mock_socket.return_value.sendto = Mock(
            side_effect=MultipleSideEffect(out_1, out_2, out_3, out_4, out_5)
        )

        def in_1(*args) -> bytes:
            return str.encode(load_fixture("register_first_data.txt"))

        def in_2(*args) -> bytes:
            return str.encode(load_fixture("register_data.txt"))

        def in_3(*args) -> bytes:
            return str.encode(load_fixture("invite_data.txt"))

        mock_socket.return_value.recv = Mock(
            side_effect=MultipleSideEffect(in_1, in_2, in_3)
        )

        voip: IntercomVoip | None = None

        async def _callback(call: Call) -> None:
            """Callback"""
            call_dict: dict = call.as_dict()

            assert call_dict["state"] == CallState.RINGING
            assert call_dict["_phone"] == voip
            assert (
                call_dict["call_id"]
                == "42707deb5c366d722cf1ae041d97ac1d@217.0.0.1:9740"
            )
            assert call_dict["local_ip"] == MOCK_IP
            assert call_dict["_send_mode"] == SendMode.SEND_RECV
            assert list(call_dict["_assigned_ports"].values())[0] == {
                8: RtpPayloadType.PCMA,
                101: RtpPayloadType.EVENT,
            }
            assert call_dict["_connections"] == 1
            assert call_dict["_audio_ports"] == 1
            assert call_dict["_video_ports"] == 1

            assert await call.decline()

            assert call.state == CallState.ENDED

            soft_stop(voip)

        voip = IntercomVoip(
            hass, MOCK_ADDRESS, MOCK_PORT, MOCK_USERNAME, MOCK_PASSWORD, _callback, True
        )

        assert await voip.start()
        voip.sip.ping_loop.cancel()  # type: ignore

        while voip.sip._started:
            await asyncio.sleep(1)
            async_fire_time_changed(hass, utcnow() + timedelta(seconds=1))

        await hass.async_block_till_done()

        assert len(mock_select.mock_calls) == 2


@pytest.mark.asyncio
async def test_recv_error(hass: HomeAssistant) -> None:
    """Recv test"""

    with patch(
        "custom_components.tattelecom_intercom.sip.socket.socket"
    ) as mock_socket, patch(
        "custom_components.tattelecom_intercom.sip.select.select",
        return_value=(True, True, True),
    ) as mock_select, patch(
        "custom_components.tattelecom_intercom.voip.socket.gethostbyname_ex",
        return_value=[[], [], [MOCK_IP]],
    ), patch(
        "custom_components.tattelecom_intercom.sip.asyncio.sleep", return_value=None
    ):
        mock_socket.return_value.setblocking = Mock(return_value=None)
        mock_socket.return_value.getsockname = Mock(
            return_value=(MOCK_IP, MOCK_LOCAL_PORT)
        )

        def out_1(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8"), True) == clean_request(
                load_fixture("register_first_out_data.txt").replace("\\r\\n", "\r\n"),
                True,
            )

            return 1

        def out_2(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8"), True) == clean_request(
                load_fixture("register_out_data.txt").replace("\\r\\n", "\r\n"), True
            )

            return 1

        mock_socket.return_value.sendto = Mock(
            side_effect=MultipleSideEffect(out_1, out_2)
        )

        def in_1(*args) -> bytes:
            return str.encode(load_fixture("register_first_data.txt"))

        def in_2(*args) -> bytes:
            return str.encode(load_fixture("register_data.txt"))

        def in_3(*args) -> bytes:
            return b"error"

        mock_socket.return_value.recv = Mock(
            side_effect=MultipleSideEffect(in_1, in_2, in_3)
        )

        async def _callback(call: Call) -> None:
            """Callback"""

        voip: IntercomVoip = IntercomVoip(
            hass, MOCK_ADDRESS, MOCK_PORT, MOCK_USERNAME, MOCK_PASSWORD, _callback, True
        )

        assert await voip.start()

        async_fire_time_changed(hass, utcnow() + timedelta(seconds=1))
        await hass.async_block_till_done()

        assert len(mock_select.mock_calls) == 2


@pytest.mark.asyncio
async def test_renegotiate(hass: HomeAssistant) -> None:
    """Renegotiate test"""

    with patch(
        "custom_components.tattelecom_intercom.sip.socket.socket"
    ) as mock_socket, patch(
        "custom_components.tattelecom_intercom.sip.select.select",
        return_value=(True, True, True),
    ) as mock_select, patch(
        "custom_components.tattelecom_intercom.voip.socket.gethostbyname_ex",
        return_value=[[], [], [MOCK_IP]],
    ):
        mock_socket.return_value.setblocking = Mock(return_value=None)
        mock_socket.return_value.getsockname = Mock(
            return_value=(MOCK_IP, MOCK_LOCAL_PORT)
        )

        def out_1(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8"), True) == clean_request(
                load_fixture("register_first_out_data.txt").replace("\\r\\n", "\r\n"),
                True,
            )

            return 1

        def out_2(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8"), True) == clean_request(
                load_fixture("register_out_data.txt").replace("\\r\\n", "\r\n"), True
            )

            return 1

        def out_3(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_cseq_request(data.decode("utf-8")) == clean_cseq_request(
                load_fixture("trying_out_data.txt").replace("\\r\\n", "\r\n")
            )

            return 1

        def out_4(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_cseq_request(data.decode("utf-8"), True) == clean_cseq_request(
                load_fixture("ringing_out_data.txt").replace("\\r\\n", "\r\n"), True
            )

            return 1

        def out_5(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_cseq_request(data.decode("utf-8"), True) == clean_cseq_request(
                load_fixture("answer_out_data.txt").replace("\\r\\n", "\r\n"), True
            )

            return 1

        def out_6(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8"), True) == clean_request(
                load_fixture("deregister_first_out_data.txt").replace("\\r\\n", "\r\n"),
                True,
            )

            return 1

        def out_7(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8"), True) == clean_request(
                load_fixture("deregister_out_data.txt").replace("\\r\\n", "\r\n"), True
            )

            return 1

        mock_socket.return_value.sendto = Mock(
            side_effect=MultipleSideEffect(
                out_1, out_2, out_3, out_4, out_3, out_4, out_5, out_6, out_7
            )
        )

        def in_1(*args) -> bytes:
            return str.encode(load_fixture("register_first_data.txt"))

        def in_2(*args) -> bytes:
            return str.encode(load_fixture("register_data.txt"))

        def in_3(*args) -> bytes:
            return str.encode(load_fixture("invite_data.txt"))

        def in_4(*args) -> bytes:
            return str.encode(load_fixture("ack_data.txt"))

        def in_5(*args) -> bytes:
            return str.encode(load_fixture("deregister_data.txt"))

        mock_socket.return_value.recv = Mock(
            side_effect=MultipleSideEffect(
                in_1, in_2, in_3, in_4, in_3, in_4, in_1, in_5
            )
        )

        voip: IntercomVoip | None = None

        async def _callback(call: Call) -> None:
            """Callback"""

            call_dict: dict = call.as_dict()

            if call.state == CallState.RINGING:
                assert call_dict["state"] == CallState.RINGING
                assert call_dict["_phone"] == voip
                assert (
                    call_dict["call_id"]
                    == "42707deb5c366d722cf1ae041d97ac1d@217.0.0.1:9740"
                )
                assert call_dict["local_ip"] == MOCK_IP
                assert call_dict["_send_mode"] == SendMode.SEND_RECV
                assert list(call_dict["_assigned_ports"].values())[0] == {
                    8: RtpPayloadType.PCMA,
                    101: RtpPayloadType.EVENT,
                }
                assert call_dict["_connections"] == 1
                assert call_dict["_audio_ports"] == 1
                assert call_dict["_video_ports"] == 1

                assert await call.answer()

                return

            if call.state == CallState.ANSWERED:
                assert call.state == CallState.ANSWERED

                await voip.clean_call(call_dict["call_id"])  # type: ignore
                soft_stop(voip)

        voip = IntercomVoip(
            hass, MOCK_ADDRESS, MOCK_PORT, MOCK_USERNAME, MOCK_PASSWORD, _callback, True
        )

        assert await voip.start()

        while voip.sip._started:
            await asyncio.sleep(1)
            async_fire_time_changed(hass, utcnow() + timedelta(seconds=1))

        await hass.async_block_till_done()

        assert len(mock_select.mock_calls) == 2


@pytest.mark.asyncio
async def test_answer(hass: HomeAssistant) -> None:
    """Answer test"""

    with patch(
        "custom_components.tattelecom_intercom.sip.socket.socket"
    ) as mock_socket, patch(
        "custom_components.tattelecom_intercom.sip.select.select",
        return_value=(True, True, True),
    ) as mock_select, patch(
        "custom_components.tattelecom_intercom.voip.socket.gethostbyname_ex",
        return_value=[[], [], [MOCK_IP]],
    ):
        mock_socket.return_value.setblocking = Mock(return_value=None)
        mock_socket.return_value.getsockname = Mock(
            return_value=(MOCK_IP, MOCK_LOCAL_PORT)
        )

        def out_1(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8"), True) == clean_request(
                load_fixture("register_first_out_data.txt").replace("\\r\\n", "\r\n"),
                True,
            )

            return 1

        def out_2(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8"), True) == clean_request(
                load_fixture("register_out_data.txt").replace("\\r\\n", "\r\n"), True
            )

            return 1

        def out_3(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_cseq_request(data.decode("utf-8")) == clean_cseq_request(
                load_fixture("trying_out_data.txt").replace("\\r\\n", "\r\n")
            )

            return 1

        def out_4(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_cseq_request(data.decode("utf-8"), True) == clean_cseq_request(
                load_fixture("ringing_out_data.txt").replace("\\r\\n", "\r\n"), True
            )

            return 1

        def out_5(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(
                data.decode("utf-8"), clean_body=True
            ) == clean_request(
                load_fixture("answer_out_data.txt").replace("\\r\\n", "\r\n"),
                clean_body=True,
            )

            return 1

        def out_6(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8"), True) == clean_request(
                load_fixture("deregister_first_out_data.txt").replace("\\r\\n", "\r\n"),
                True,
            )

            return 1

        def out_7(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8"), True) == clean_request(
                load_fixture("deregister_out_data.txt").replace("\\r\\n", "\r\n"), True
            )

            return 1

        mock_socket.return_value.sendto = Mock(
            side_effect=MultipleSideEffect(
                out_1, out_2, out_3, out_4, out_5, out_6, out_7
            )
        )

        def in_1(*args) -> bytes:
            return str.encode(load_fixture("register_first_data.txt"))

        def in_2(*args) -> bytes:
            return str.encode(load_fixture("register_data.txt"))

        def in_3(*args) -> bytes:
            return str.encode(load_fixture("invite_data.txt"))

        def in_4(*args) -> bytes:
            return str.encode(load_fixture("ack_data.txt"))

        def in_5(*args) -> bytes:
            return str.encode(load_fixture("deregister_data.txt"))

        mock_socket.return_value.recv = Mock(
            side_effect=MultipleSideEffect(in_1, in_2, in_3, in_4, in_1, in_5)
        )

        voip: IntercomVoip | None = None

        async def _callback(call: Call) -> None:
            """Callback"""

            call_dict: dict = call.as_dict()

            if call.state == CallState.RINGING:
                assert call_dict["state"] == CallState.RINGING
                assert call_dict["_phone"] == voip
                assert (
                    call_dict["call_id"]
                    == "42707deb5c366d722cf1ae041d97ac1d@217.0.0.1:9740"
                )
                assert call_dict["local_ip"] == MOCK_IP
                assert call_dict["_send_mode"] == SendMode.SEND_RECV
                assert list(call_dict["_assigned_ports"].values())[0] == {
                    8: RtpPayloadType.PCMA,
                    101: RtpPayloadType.EVENT,
                }
                assert call_dict["_connections"] == 1
                assert call_dict["_audio_ports"] == 1
                assert call_dict["_video_ports"] == 1

                assert await call.answer()

                return

            if call.state == CallState.ANSWERED:
                assert call.state == CallState.ANSWERED

                await voip.clean_call(call_dict["call_id"])  # type: ignore

                soft_stop(voip)

        voip = IntercomVoip(
            hass, MOCK_ADDRESS, MOCK_PORT, MOCK_USERNAME, MOCK_PASSWORD, _callback, True
        )

        assert await voip.start()
        voip.sip.ping_loop.cancel()  # type: ignore

        while voip.sip._started:
            await asyncio.sleep(1)
            async_fire_time_changed(hass, utcnow() + timedelta(seconds=1))

        await hass.async_block_till_done()

        assert len(mock_select.mock_calls) == 2


@pytest.mark.asyncio
async def test_hangup(hass: HomeAssistant, socket_enabled) -> None:
    """Hangup test"""

    with patch(
        "custom_components.tattelecom_intercom.sip.socket.socket"
    ) as mock_socket, patch(
        "custom_components.tattelecom_intercom.sip.select.select",
        return_value=(True, True, True),
    ) as mock_select, patch(
        "custom_components.tattelecom_intercom.voip.socket.gethostbyname_ex",
        return_value=[[], [], [MOCK_IP]],
    ):
        mock_socket.return_value.setblocking = Mock(return_value=None)
        mock_socket.return_value.getsockname = Mock(
            return_value=(MOCK_IP, MOCK_LOCAL_PORT)
        )

        def out_1(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8"), True) == clean_request(
                load_fixture("register_first_out_data.txt").replace("\\r\\n", "\r\n"),
                True,
            )

            return 1

        def out_2(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8"), True) == clean_request(
                load_fixture("register_out_data.txt").replace("\\r\\n", "\r\n"), True
            )

            return 1

        def out_3(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_cseq_request(data.decode("utf-8")) == clean_cseq_request(
                load_fixture("trying_out_data.txt").replace("\\r\\n", "\r\n")
            )

            return 1

        def out_4(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_cseq_request(data.decode("utf-8"), True) == clean_cseq_request(
                load_fixture("ringing_out_data.txt").replace("\\r\\n", "\r\n"), True
            )

            return 1

        def out_5(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(
                data.decode("utf-8"), clean_body=True
            ) == clean_request(
                load_fixture("answer_out_data.txt").replace("\\r\\n", "\r\n"),
                clean_body=True,
            )

            return 1

        def out_6(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8"), True) == clean_request(
                load_fixture("bye_out_data.txt").replace("\\r\\n", "\r\n"),
                True,
            )

            return 1

        def out_7(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8"), True) == clean_request(
                load_fixture("deregister_first_out_data.txt").replace("\\r\\n", "\r\n"),
                True,
            )

            return 1

        def out_8(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)
            assert clean_request(data.decode("utf-8"), True) == clean_request(
                load_fixture("deregister_out_data.txt").replace("\\r\\n", "\r\n"), True
            )

            return 1

        mock_socket.return_value.sendto = Mock(
            side_effect=MultipleSideEffect(
                out_1, out_2, out_3, out_4, out_5, out_6, out_7, out_8
            )
        )

        def in_1(*args) -> bytes:
            return str.encode(load_fixture("register_first_data.txt"))

        def in_2(*args) -> bytes:
            return str.encode(load_fixture("register_data.txt"))

        def in_3(*args) -> bytes:
            return str.encode(load_fixture("invite_data.txt"))

        def in_4(*args) -> bytes:
            return str.encode(load_fixture("ack_data.txt"))

        def in_5(*args) -> bytes:
            return str.encode(load_fixture("deregister_data.txt"))

        mock_socket.return_value.recv = Mock(
            side_effect=MultipleSideEffect(in_1, in_2, in_3, in_4, in_1, in_5)
        )

        voip: IntercomVoip | None = None

        async def _callback(call: Call) -> None:
            """Callback"""

            call_dict: dict = call.as_dict()

            if call.state == CallState.RINGING:
                assert call_dict["state"] == CallState.RINGING
                assert call_dict["_phone"] == voip
                assert (
                    call_dict["call_id"]
                    == "42707deb5c366d722cf1ae041d97ac1d@217.0.0.1:9740"
                )
                assert call_dict["local_ip"] == MOCK_IP
                assert call_dict["_send_mode"] == SendMode.SEND_RECV
                assert list(call_dict["_assigned_ports"].values())[0] == {
                    8: RtpPayloadType.PCMA,
                    101: RtpPayloadType.EVENT,
                }
                assert call_dict["_connections"] == 1
                assert call_dict["_audio_ports"] == 1
                assert call_dict["_video_ports"] == 1

                assert await call.answer()

                return

            if call.state == CallState.ANSWERED:
                assert call.state == CallState.ANSWERED

                assert await call.hangup()
                assert call.state == CallState.ENDED

                soft_stop(voip)  # type: ignore

        voip = IntercomVoip(
            hass, MOCK_ADDRESS, MOCK_PORT, MOCK_USERNAME, MOCK_PASSWORD, _callback, True
        )

        assert await voip.start()
        voip.sip.ping_loop.cancel()  # type: ignore

        while voip.sip._started:
            await asyncio.sleep(1)
            async_fire_time_changed(hass, utcnow() + timedelta(seconds=1))

        await hass.async_block_till_done()

        assert len(mock_select.mock_calls) == 2


def clean_request(data: str, clean_call: bool = False, clean_body: bool = False) -> str:
    """Clean first request"""

    data = re.sub(r";branch=(.*);rport", r";branch=;rport", data)
    data = re.sub(r"Content-Length: (\d+)\r\n", r"Content-Length: \r\n", data)
    data = clean_tags_request(data)

    if clean_call:
        data = clean_cseq_request(data)
        data = re.sub(r"Call-ID: (.*)\r\n", r"Call-ID: \r\n", data)

    if clean_body:
        data = re.sub(r"o=(.*) (\d+) (\d+) IN (.*)\r\n", r"o=\1 IN \4 \r\n", data)
        data = re.sub(
            r"m=audio (\d+) RTP/AVP 8 101\r\n", r"m=audio RTP/AVP 8 101\r\n", data
        )
        data = re.sub(r"m=video (\d+) RTP/AVP 99\r\n", r"m=video RTP/AVP 99\r\n", data)

    return re.sub(r'<urn:uuid:(.*)>"', r'<urn:uuid:>"', data)


def clean_cseq_request(data: str, clean_tag: bool = False) -> str:
    """Clean cseq request"""

    if clean_tag:
        data = clean_tags_request(data)

    return re.sub(r"CSeq: (\d+) (.*)\r\n", r"CSeq: \2\r\n", data)


def clean_tags_request(data: str) -> str:
    """Clean tags request"""

    return re.sub(r";tag=(.*)\r\n", r";tag=\r\n", data)


def soft_stop(voip: IntercomVoip | None) -> None:
    """Soft stop"""

    if voip:
        voip.sip._started = False

        if voip.sip.register_loop:
            voip.sip.register_loop.cancel()

        if voip.sip.recv_loop:
            voip.sip.recv_loop.cancel()

        if voip.sip.ping_loop:
            voip.sip.ping_loop.cancel()

        voip.sip.close_sockets()
