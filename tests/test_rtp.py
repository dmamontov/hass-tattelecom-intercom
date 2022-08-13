"""Tests for the tattelecom_intercom component."""

# pylint: disable=no-member,too-many-statements,protected-access,too-many-lines,line-too-long

from __future__ import annotations

import asyncio
import logging
import wave
from datetime import timedelta
from typing import Final
from unittest.mock import Mock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.util.dt import utcnow
from pytest_homeassistant_custom_component.common import (
    async_fire_time_changed,
    load_fixture,
)

from custom_components.tattelecom_intercom.enum import RtpPayloadType
from custom_components.tattelecom_intercom.helper import Counter
from custom_components.tattelecom_intercom.rtp import RtpClient, RtpMessage
from tests.setup import (
    MOCK_ADDRESS,
    MOCK_IP,
    MOCK_LOCAL_PORT,
    MOCK_PORT,
    get_audio_fixture_path,
)

_LOGGER = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations"""

    yield


ASSOC: Final = {8: RtpPayloadType.PCMA, 101: RtpPayloadType.EVENT}
PACKETS: Final = [
    {
        "assoc": ASSOC,
        "csrc": 0,
        "csrc_list": [],
        "extension": False,
        "marker": True,
        "padding": False,
        "payload": b"\xd5UUUUU\xd5\xd5\xd5\xd5\xd5UUUUU\xd5\xd5\xd5\xd5UUUU"
        b"U\xd5\xd5\xd5\xd5\xd5UUUU\xd5\xd5\xd5\xd5\xd5UU\xd5\xd5\xd5"
        b"\xd5\xd5UUUU\xd5\xd5\xd5\xd5\xd5UUUUU\xd5\xd5\xd5\xd5UUUU"
        b"U\xd5\xd5\xd5\xd5\xd5UUUUU\xd5\xd5\xd5\xd5\xd5UUUUU\xd5\xd5\xd5"
        b"\xd5\xd5UUUU\xd5\xd5\xd5\xd5\xd5UUUUUUUU\xd5UU\xd5UU\xd5UU"
        b"\xd5\xd5\xd5\xd5\xd5UUUUUU\xd5\xd5\xd5\xd5UUUUU\xd5\xd5\xd5\xd5"
        b"\xd5UUUUU\xd5U\xd5\xd5U\xd5UUUU",
        "payload_type": RtpPayloadType.PCMA,
        "sequence": 3882,
        "ssrc": 1920045575,
        "timestamp": 160,
        "version": 2,
    },
    {
        "assoc": ASSOC,
        "csrc": 0,
        "csrc_list": [],
        "extension": False,
        "marker": False,
        "padding": False,
        "payload": b"U\xd5\xd5\xd5\xd5\xd5UUUUU\xd5\xd5U\xd5UUUUU\xd5\xd5\xd5\xd5"
        b"\xd5UUUUU\xd5\xd5\xd5\xd5\xd5U\xd5\xd5U\xd5\xd5\xd5\xd5\xd5"
        b"\xd5UUUUUUU\xd5\xd5U\xd5\xd5UUUU\xd5\xd5\xd5\xd5\xd5UUUUUU"
        b"\xd5U\xd5\xd5U\xd5\xd5UU\xd5U\xd5\xd5\xd5\xd5\xd5UUUU"
        b"U\xd5\xd5\xd5\xd5UUU\xd5U\xd5\xd5\xd5\xd5UUUUU\xd5\xd5\xd5UUUUUU"
        b"UU\xd5\xd5\xd5\xd5\xd5\xd5\xd5\xd5\xd5\xd5\xd5UU\xd5\xd5U\xd5U"
        b"U\xd5UU\xd5\xd5\xd5\xd5\xd5U\xd5UUUUUU\xd5\xd5U",
        "payload_type": RtpPayloadType.PCMA,
        "sequence": 3883,
        "ssrc": 1920045575,
        "timestamp": 320,
        "version": 2,
    },
    {
        "assoc": ASSOC,
        "csrc": 0,
        "csrc_list": [],
        "extension": False,
        "marker": False,
        "padding": False,
        "payload": b"UUUUUU\xd5\xd5\xd5\xd5UUUUU\xd5\xd5\xd5\xd5\xd5UUUUU\xd5\xd5\xd5"
        b"\xd5\xd5UUUUU\xd5\xd5\xd5\xd5\xd5UUUUU\xd5U\xd5\xd5\xd5\xd5UUUUU"
        b"\xd5\xd5\xd5\xd5UUUUUU\xd5\xd5\xd5\xd5\xd5UUUUU\xd5\xd5\xd5\xd5"
        b"\xd5UUUUU\xd5\xd5\xd5\xd5UUUUUU\xd5\xd5\xd5\xd5\xd5UUUUUU\xd5"
        b"\xd5\xd5\xd5UUUUU\xd5\xd5\xd5\xd5\xd5UUUUU\xd5\xd5\xd5\xd5\xd5U"
        b"UUUU\xd5\xd5\xd5\xd5\xd5UUUUU\xd5\xd5\xd5\xd5\xd5UUUUU"
        b"U\xd5\xd5\xd5",
        "payload_type": RtpPayloadType.PCMA,
        "sequence": 3884,
        "ssrc": 1920045575,
        "timestamp": 480,
        "version": 2,
    },
    {
        "assoc": ASSOC,
        "csrc": 0,
        "csrc_list": [],
        "extension": False,
        "marker": False,
        "padding": False,
        "payload": b"\xd5\xd5UUUUU\xd5\xd5\xd5\xd5\xd5UUUU\xd5\xd5\xd5\xd5\xd5UUU"
        b"UUU\xd5\xd5\xd5\xd5\xd5UUUU\xd5\xd5\xd5\xd5\xd5\xd5UUUUU\xd5"
        b"\xd5\xd5\xd5UUTUUU\xd5\xd5\xd5\xd5UUUUU\xd5\xd5\xd5\xd5\xd5\xd5"
        b"UUUUU\xd5\xd5\xd5\xd5\xd5UUUUU\xd5\xd5\xd5\xd5\xd5UUUU"
        b"U\xd5\xd5\xd5\xd5\xd5UUTUU\xd5\xd5\xd5\xd5\xd5UUTUU\xd5\xd5\xd5"
        b"\xd5\xd5UUUUU\xd5\xd5\xd5\xd5\xd5UTUUU\xd5\xd5\xd5\xd5\xd5UU"
        b"UU\xd5\xd5\xd5\xd5\xd5UUUUUU\xd5\xd5\xd5",
        "payload_type": RtpPayloadType.PCMA,
        "sequence": 3885,
        "ssrc": 1920045575,
        "timestamp": 640,
        "version": 2,
    },
    {
        "assoc": ASSOC,
        "csrc": 0,
        "csrc_list": [],
        "extension": False,
        "marker": False,
        "padding": False,
        "payload": b"\xd5UUUUUU\xd5\xd5\xd5\xd5UUUUU\xd5\xd5\xd5\xd5\xd5\xd5UU"
        b"UU\xd5\xd5\xd5\xd5\xd5\xd5UUUUU\xd5\xd5\xd5\xd5\xd5UUUUU\xd5"
        b"\xd5\xd5\xd5\xd5UUUUU\xd5\xd5\xd5\xd5UUUUU\xd5\xd5\xd5\xd5\xd5U"
        b"UUUUU\xd5\xd5\xd5\xd5UUUUUU\xd5\xd5\xd5\xd5\xd5UUUUU\xd5\xd5\xd5"
        b"\xd5\xd5UUUUU\xd5\xd5\xd5\xd5\xd5UUUUU\xd5\xd5\xd5\xd5\xd5UU"
        b"UUU\xd5\xd5\xd5\xd5\xd5UUUUU\xd5\xd5\xd5\xd5\xd5UUUU\xd5\xd5"
        b"\xd5\xd5\xd5UUUUUU\xd5\xd5\xd5",
        "payload_type": RtpPayloadType.PCMA,
        "sequence": 3886,
        "ssrc": 1920045575,
        "timestamp": 800,
        "version": 2,
    },
    {
        "assoc": ASSOC,
        "csrc": 0,
        "csrc_list": [],
        "extension": False,
        "marker": False,
        "padding": False,
        "payload": b"\xd5UUUUUU\xd5\xd5\xd5UUUUUU\xd5\xd5\xd5\xd5\xd5UUUUU\xd5\xd5"
        b"\xd5\xd5\xd5UUUUU\xd5\xd5\xd5\xd5\xd5UUUUU\xd5\xd5\xd5\xd5\xd5U"
        b"UUUUU\xd5\xd5\xd5\xd5\xd5UUUUU\xd5\xd5UU\xd5UUUUU\xd5\xd5\xd5"
        b"\xd5\xd5UUUUU\xd5\xd5\xd5\xd5\xd5UUUUU\xd5\xd5\xd5\xd5\xd5UU"
        b"UUU\xd5\xd5\xd5\xd5\xd5UUUUU\xd5\xd5\xd5\xd5\xd5UUUUU\xd5"
        b"\xd5\xd5\xd5\xd5UUUUU\xd5\xd5\xd5\xd5\xd5UUUUU\xd5\xd5\xd5\xd5U"
        b"UUUU\xd5\xd5\xd5\xd5",
        "payload_type": RtpPayloadType.PCMA,
        "sequence": 3887,
        "ssrc": 1920045575,
        "timestamp": 960,
        "version": 2,
    },
]


async def test_messages(hass: HomeAssistant) -> None:
    """Test messages"""

    messages: list = load_fixture("rtp_packets.txt").split("\n")

    for index in range(6):
        encoded = bytes.fromhex(messages[index])
        rtp_message: RtpMessage = RtpMessage(encoded, ASSOC)

        assert rtp_message.as_dict() == PACKETS[index]

        if index == 5:
            break


async def test_start_stop(hass: HomeAssistant) -> None:
    """Test start stop"""

    with patch(
        "custom_components.tattelecom_intercom.rtp.socket.socket"
    ) as mock_socket:
        mock_socket.return_value.setblocking = Mock(return_value=None)
        mock_socket.return_value.sendto = Mock(return_value=None)
        mock_socket.return_value.recv = Mock(return_value=None)

        rtp: RtpClient = get_client(hass)

        await rtp.start()
        assert rtp._started

        await rtp.stop()
        assert not rtp._started


async def test_write(hass: HomeAssistant) -> None:
    """Test write"""

    with patch(
        "custom_components.tattelecom_intercom.rtp.socket.socket"
    ) as mock_socket:
        mock_socket.return_value.setblocking = Mock(return_value=None)
        mock_socket.return_value.recv = Mock(return_value=b"")

        rtp: RtpClient | None = None

        messages: list = load_fixture("rtp_write_payload.txt").split("\n")

        counter: Counter = Counter()

        def write(data: bytes, address: tuple) -> int:
            assert address == (MOCK_ADDRESS, MOCK_PORT)

            rtp_message: RtpMessage = RtpMessage(data, ASSOC)

            index: int = counter.next()

            assert rtp_message.payload.hex() == messages[index - 1]

            if index == len(messages):
                hass.loop.call_soon(lambda: hass.async_create_task(rtp.stop()))  # type: ignore

            return 1

        mock_socket.return_value.sendto = Mock(side_effect=write)

        file: wave.Wave_read = wave.open(get_audio_fixture_path("rtp_write.wav"), "rb")
        data: bytes = file.readframes(file.getnframes())
        file.close()

        rtp = get_client(hass)

        await rtp.start()
        assert rtp._started
        rtp._receiver_loop.cancel()  # type: ignore

        await rtp.write(data)

        while rtp._started:
            await asyncio.sleep(1)
            async_fire_time_changed(hass, utcnow() + timedelta(seconds=1))

        await hass.async_block_till_done()


async def test_read(hass: HomeAssistant) -> None:
    """Test read"""

    with patch(
        "custom_components.tattelecom_intercom.rtp.socket.socket"
    ) as mock_socket:
        mock_socket.return_value.setblocking = Mock(return_value=None)
        mock_socket.return_value.sendto = Mock(return_value=None)

        rtp: RtpClient | None = None

        messages: list = load_fixture("rtp_packets.txt").split("\n")

        counter: Counter = Counter()

        def read(length: int) -> bytes:
            index: int = counter.next()

            if index == len(messages):
                hass.loop.call_soon(lambda: hass.async_create_task(rtp.stop()))  # type: ignore

            return bytes.fromhex(messages[index - 1])

        mock_socket.return_value.recv = Mock(side_effect=read)

        rtp = get_client(hass)

        await rtp.start()
        assert rtp._started
        rtp._transmitter_loop.cancel()  # type: ignore

        while rtp._started:
            await asyncio.sleep(1)
            async_fire_time_changed(hass, utcnow() + timedelta(seconds=1))

        full_message: str = ""
        for _ in range(len(messages)):
            packet: bytes = await rtp.read()
            full_message += packet.hex()

        assert full_message == load_fixture("rtp_read_payload.txt")

        await hass.async_block_till_done()


async def _dtmf_callback() -> None:
    """Callback"""


def get_client(hass: HomeAssistant) -> RtpClient:
    """Get Rtp Client"""

    return RtpClient(
        hass,
        ASSOC,
        MOCK_IP,
        MOCK_LOCAL_PORT,
        MOCK_ADDRESS,
        MOCK_PORT,
        _dtmf_callback,
    )
