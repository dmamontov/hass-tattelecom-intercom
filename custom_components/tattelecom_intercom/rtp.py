"""Tattelecom Intercom rtp."""

from __future__ import annotations

import asyncio
import audioop
import contextlib
import logging
import random
import socket
from asyncio import Lock
from collections.abc import Callable
from functools import cached_property
from io import BytesIO
from typing import Any, Optional

from homeassistant.core import HomeAssistant
from homeassistant.util.read_only_dict import ReadOnlyDict

from .const import PHONE_EVENT_KEYS
from .enum import RtpPayloadType
from .helper import add_bytes, byte_to_bits

_LOGGER = logging.getLogger(__name__)


class RtpClient:
    """Intercom rtp client"""

    hass: HomeAssistant

    _started: bool = False

    in_ip: str
    in_port: int
    out_ip: str
    out_port: int

    _out_offset: int
    _out_sequence: int
    _out_timestamp: int

    _ssrc: int

    _debug_callback: Callable

    def __init__(  # pylint: disable=(too-many-arguments
        self,
        hass: HomeAssistant,
        assoc: dict[int, RtpPayloadType],
        in_ip: str,
        in_port: int,
        out_ip: str,
        out_port: int,
        dtmf: Optional[Callable] = None,
        debug_callback: Optional[Callable] = None,
    ) -> None:
        """Initialize Rtp Client

        :param hass: HomeAssistant: Home Assistant object
        :param assoc: dict[int, RtpPayloadType],
        :param in_ip: str,
        :param in_port: int,
        :param out_ip: str,
        :param out_port: int,
        :param dtmf: Callable | None = None,
        :param debug_callback: Callable: Voip debug callback
        """

        self.hass = hass

        self._in: socket.socket | None = None
        self._out: socket.socket | None = None

        self._receiver_loop: asyncio.Task | None = None
        self._transmitter_loop: asyncio.Task | None = None

        self.assoc: dict[int, RtpPayloadType] = assoc

        self.in_ip = in_ip
        self.in_port = in_port
        self.out_ip = out_ip
        self.out_port = out_port

        self._debug_callback = debug_callback  # type: ignore
        self._dtmf: Callable = dtmf  # type: ignore

        self._pm_out: RtpPacketManager = RtpPacketManager()
        self._pm_in: RtpPacketManager = RtpPacketManager()

        self._ssrc = random.randint(1000, 65530)

        self._out_offset = random.randint(1, 5000)
        self._out_sequence = random.randint(1, 100)
        self._out_timestamp = random.randint(1, 10000)

    @cached_property
    def is_audio(self) -> bool:
        """Is audio

        :return bool
        """

        return self.preference in [RtpPayloadType.PCMU, RtpPayloadType.PCMA]

    @cached_property
    def preference(self) -> RtpPayloadType | None:
        """Preference getter

        :return RtpPayloadType | None
        """

        return next(
            (
                payload_type
                for payload_type in self.assoc.values()
                if isinstance(payload_type.value, int)
            ),
            None,
        )

    async def start(self) -> None:
        """Start client"""

        if self._started:  # pragma: no cover
            return

        self._started = True

        self._in = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self._in.bind((self.in_ip, self.in_port))
        self._in.setblocking(False)

        self._out = self._in

        self._receiver_loop = asyncio.ensure_future(self._recv(), loop=self.hass.loop)
        self._transmitter_loop = asyncio.ensure_future(
            self._trans(), loop=self.hass.loop
        )

    async def stop(self) -> None:
        """Stop client"""

        self._started = False

        await asyncio.sleep(1)

        if self._receiver_loop:
            self._receiver_loop.cancel()

        if self._transmitter_loop:
            self._transmitter_loop.cancel()

        if self._in:
            self._in.close()

        if self._out:
            self._out.close()

    async def read(self, length: int = 160, blocking: bool = True) -> bytes:
        """Read

        :param length: int
        :param blocking: bool
        :return bytes
        """

        if not blocking:  # pragma: no cover
            return await self._pm_in.read(length)

        packet = await self._pm_in.read(length)
        while packet == (b"\x80" * length) and self._started:  # pragma: no cover
            await asyncio.sleep(0.01)
            packet = await self._pm_in.read(length)

        return packet

    async def write(self, data: bytes) -> None:
        """Write

        :param data: bytes
        """

        await self._pm_out.write(self._out_offset, data)
        self._out_offset += len(data)

    async def _recv(self) -> None:
        """Receiver"""

        while self._started and self._in:
            try:
                if raw := self._in.recv(8192):
                    if self._debug_callback is not None:  # pragma: no cover
                        self._debug_callback(
                            "rtp_recv", "RTP Recv: %r", raw.hex(), increment=True
                        )

                    await self._parse_packet(raw)
            except OSError:  # pragma: no cover
                await asyncio.sleep(0.01)

    async def _trans(self) -> None:
        """Transmitter"""

        while self._started and self._out:
            packet, length = await self._encode_packet(
                await self._pm_out.read(), self._out_sequence, self._out_timestamp
            )

            with contextlib.suppress(OSError):
                if self._debug_callback is not None:
                    self._debug_callback(
                        "rtp_trans", "RTP Trans: %r", packet.hex(), increment=True
                    )

                self._out.sendto(packet, (self.out_ip, self.out_port))

                self._out_sequence += 1
                self._out_timestamp += length

            await asyncio.sleep(
                ((1 / self.preference.rate) * 160) if self.preference else 1
            )

    async def _parse_packet(self, packet: bytes) -> bytes:
        """Parse packet

        :param packet: bytes
        :return bytes
        """

        msg = RtpMessage(packet, self.assoc)

        if msg.payload_type == RtpPayloadType.PCMA:
            payload = audioop.bias(audioop.alaw2lin(msg.payload, 1), 1, 128)
            await self._pm_in.write(msg.timestamp, payload)

            return payload

        # TODO: Not yet supported by the manufacturer.
        if msg.payload_type == RtpPayloadType.PCMU:  # pragma: no cover
            payload = audioop.bias(audioop.ulaw2lin(msg.payload, 1), 1, 128)
            await self._pm_in.write(msg.timestamp, payload)

            return payload

        # TODO: Not yet supported by the manufacturer.
        if (
            msg.payload_type == RtpPayloadType.EVENT
            and msg.marker
            and self._dtmf is not None
        ):  # pragma: no cover
            await self._dtmf(PHONE_EVENT_KEYS[msg.payload[0]])

        return b""  # pragma: no cover

    async def _encode_packet(
        self, payload: bytes, sequence: int, timestamp: int
    ) -> tuple[bytes, int]:
        """Encode packet

        :param payload: bytes
        :param sequence: int
        :param timestamp: int
        """

        packet = b"\x80" + chr(int(self.preference or 0)).encode("utf8")

        with contextlib.suppress(OverflowError):
            packet += sequence.to_bytes(2, byteorder="big")

        with contextlib.suppress(OverflowError):
            packet += timestamp.to_bytes(4, byteorder="big")

        packet += self._ssrc.to_bytes(4, byteorder="big")

        if self.preference == RtpPayloadType.PCMA:
            enc_payload = audioop.lin2alaw(audioop.bias(payload, 1, -128), 1)
            return packet + enc_payload, len(enc_payload)

        # TODO: Not yet supported by the manufacturer.
        if self.preference == RtpPayloadType.PCMU:  # pragma: no cover
            enc_payload = audioop.lin2ulaw(audioop.bias(payload, 1, -128), 1)
            return packet + enc_payload, len(enc_payload)

        return b"", 0  # pragma: no cover


class RtpPacketManager:
    """Intercom rtp packet manager"""

    _offset: int = 4294967296

    _buffer: BytesIO
    _buffer_lock: Lock

    _rebuilding: bool = False

    def __init__(self) -> None:
        """Initialize Rtp Packet Manager"""

        self._history: dict = {}
        self._buffer = BytesIO()
        self._buffer_lock = Lock()

    async def read(self, length: int = 160) -> bytes:
        """Read

        :param length: int
        :return bytes
        """

        while self._rebuilding:  # pragma: no cover
            await asyncio.sleep(0.01)

        async with self._buffer_lock:
            packet: bytes = self._buffer.read(length)

            if len(packet) < length:  # pragma: no cover
                packet += b"\x80" * (length - len(packet))

            return packet

    async def rebuild(
        self, reset: bool, offset: int = 0, data: bytes = b""
    ) -> None:  # pragma: no cover
        """Rebuild

        :param reset: bool
        :param offset: int
        :param data: bytes
        """

        self._rebuilding = True

        if reset:
            self._history = {offset: data}
            self._buffer = BytesIO(data)

            self._rebuilding = False

            return

        buffer_offset: int = self._buffer.tell()
        self._buffer = BytesIO()

        for _offset, packet in self._history.items():
            await self.write(_offset, packet)

        self._buffer.seek(buffer_offset, 0)

        self._rebuilding = False

    async def write(self, offset: int, data: bytes) -> None:
        """Write

        :param offset: int
        :param data: bytes
        """

        async with self._buffer_lock:
            self._history[offset] = data

            buffer_offset: int = self._buffer.tell()

            if offset < self._offset:
                reset = abs(offset - self._offset) >= 100000
                self._offset = offset

                await self.rebuild(reset, offset, data)

                return

            offset -= self._offset
            self._buffer.seek(offset, 0)
            self._buffer.write(data)
            self._buffer.seek(buffer_offset, 0)


class RtpMessage:  # pylint: disable=too-few-public-methods
    """Intercom rtp message"""

    version: int = 0
    padding: bool = False
    extension: bool = False
    marker: bool = False
    payload: bytes = b""
    payload_type: RtpPayloadType = RtpPayloadType.UNKNOWN
    sequence: int = 0
    timestamp: int = 0
    ssrc: int = 0
    csrc: int = 0
    csrc_list: list = []

    def __init__(self, data: bytes, assoc: dict[int, RtpPayloadType]) -> None:
        """Initialize Rtp Packet Manager

        :param data: bytes
        :param assoc: dict[int, RtpPayloadType]
        """

        self.assoc: dict[int, RtpPayloadType] = assoc

        self._parse(data)

    def _parse(self, packet: bytes) -> None:
        """Parse packet

        :param packet: bytes
        """

        byte: str = byte_to_bits(packet[:1])
        if not byte:  # pragma: no cover
            return

        self.version = int(byte[:2], 2)
        if self.version != 2:  # pragma: no cover
            _LOGGER.debug("RTP Version {self.version} not compatible.")
            return

        self.padding = bool(int(byte[2], 2))
        self.extension = bool(int(byte[3], 2))
        self.csrc = int(byte[4:], 2)

        byte = byte_to_bits(packet[1:2])
        self.marker = bool(int(byte[0], 2))

        index: int = int(byte[1:], 2)
        if index in self.assoc:
            self.payload_type = self.assoc[index]
        else:  # pragma: no cover
            try:
                self.payload_type = RtpPayloadType(index)
            except ValueError:
                _LOGGER.debug("RTP Payload type %r not found.", index)
                return

        self.sequence = add_bytes(packet[2:4])
        self.timestamp = add_bytes(packet[4:8])
        self.ssrc = add_bytes(packet[8:12])

        self.csrc_list = []

        i = 12
        for _ in range(self.csrc):  # pragma: no cover
            self.csrc_list.append(packet[i : i + 4])
            i += 4

        if self.extension:  # pragma: no cover
            return

        self.payload = packet[i:]

    def as_dict(self) -> ReadOnlyDict[str, Any]:
        """As dict

        :return ReadOnlyDict[str, Any]
        """

        return ReadOnlyDict(self.__dict__)
