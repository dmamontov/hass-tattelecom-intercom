"""Tattelecom Intercom sip."""

# pylint: disable=too-many-lines,line-too-long

from __future__ import annotations

import asyncio
import hashlib
import logging
import random
import re
import select
import socket
import time
import uuid
from asyncio import Lock
from collections.abc import Callable
from functools import cached_property
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.util.read_only_dict import ReadOnlyDict

from .const import (
    SIP_EXPIRES,
    SIP_PING_TIMEOUT,
    SIP_PORT,
    SIP_RETRY_SLEEP,
    SIP_TIMEOUT,
    SIP_USER_AGENT,
    TAG_DEREGISTER,
    TAG_REGISTER,
)
from .enum import (
    MessageStatus,
    MessageType,
    RtpPayloadType,
    RtpProtocol,
    TransmitType,
    VoipState,
)
from .exceptions import (
    IntercomError,
    IntercomInvalidAccountInfoError,
    IntercomInvalidStateError,
    IntercomSipAlreadyStartedError,
    IntercomSipParseError,
    IntercomSipTimeoutError,
)
from .helper import Counter

_LOGGER = logging.getLogger(__name__)


class IntercomSip:
    """Intercom sip class"""

    hass: HomeAssistant

    _reg_urn_uuid: str

    _address: str
    _port: int
    _username: str
    _password: str

    _local_ip: str
    _local_port: int

    _started: bool = False
    _internet_connect: bool = True

    _callback: Callable
    _status_callback: Callable
    _debug_callback: Callable

    _recv_lock: Lock
    _tags: list = []

    _cnt_call_id: Counter
    _cnt_register: Counter

    register_loop: asyncio.TimerHandle | None = None
    recv_loop: asyncio.Task | None = None
    ping_loop: asyncio.Task | None = None

    def __init__(  # pylint: disable=too-many-arguments
        self,
        hass: HomeAssistant,
        address: str,
        port: int,
        username: str,
        password: str,
        local_ip: str,
        callback: Callable,
        status_callback: Callable,
        debug_callback: Callable,
    ) -> None:
        """Initialize Intercom Sip

        :param hass: HomeAssistant: Home Assistant object
        :param address: str: SIP address
        :param port: int: SIP port
        :param username: str: SIP username
        :param password: str: SIP password
        :param local_ip: str: Local IP address
        :param callback: Callable: Voip callback
        :param status_callback: Callable: Voip status callback
        :param debug_callback: Callable: Voip debug callback
        """

        self.hass = hass

        self.tags: dict[str, str] = {TAG_REGISTER: self._tag, TAG_DEREGISTER: self._tag}

        self._address = address
        self._port = port
        self._username = username
        self._password = password
        self._local_ip = local_ip
        self._local_port = SIP_PORT
        self._reg_urn_uuid = self._urn_uuid

        self._in: socket.socket | None = None
        self._out: socket.socket | None = None

        self._callback = callback  # type: ignore
        self._status_callback = status_callback  # type: ignore
        self._debug_callback = debug_callback  # type: ignore

        self._recv_lock = Lock()

        self._cnt_call_id = Counter()
        self._cnt_register = Counter(20)

    @property
    def _branch(self) -> str:
        """Generate branch"""

        return f"z9hG4bK.{uuid.uuid4().hex[:9]}"

    @property
    def _call_id(self) -> str:
        """Generate call id"""

        return hashlib.sha256(str(self._cnt_call_id.next()).encode("utf8")).hexdigest()[
            :10
        ]

    @property
    def _urn_uuid(self) -> str:
        """Generate urn uui"""

        return str(uuid.uuid4())

    @property
    def _tag(self) -> str:
        """Generate tag"""

        while True:
            tag = hashlib.md5(
                str(random.randint(1, 4294967296)).encode("utf8")
            ).hexdigest()[:9]

            if tag not in self._tags:
                self._tags.append(tag)

                return tag

    async def start(self) -> None:
        """Start voip sip"""

        if self._started:
            raise IntercomSipAlreadyStartedError(
                "Attempted to start already started SIP."
            )

        self._started = True

        await self.open_sockets()

        try:
            await self._register()
        except TimeoutError as _err:
            self._started = False

            self._safe_release()

            raise IntercomSipTimeoutError(str(_err)) from _err
        except IntercomError as _err:
            self._started = False

            self._safe_release()

            raise IntercomError(str(_err)) from _err

        self.recv_loop = asyncio.ensure_future(self._recv(), loop=self.hass.loop)
        self.ping_loop = asyncio.ensure_future(self._ping(), loop=self.hass.loop)

    async def stop(self, force: bool = False, safe: bool = False) -> None:
        """Stop voip sip

        :param force: bool
        :param safe: bool
        """

        if self.register_loop and not safe:
            self.register_loop.cancel()

        _prev_state: bool = self._started
        self._started = False

        await asyncio.sleep(1)

        if self.recv_loop:
            self.recv_loop.cancel()

        if self.ping_loop:
            self.ping_loop.cancel()

        self._started = _prev_state

        if not self._started and not force:
            self.close_sockets()

            return

        if force:
            await self.open_sockets()

        self._safe_release()

        try:
            await self._deregister()
        except TimeoutError as _err:
            self._safe_release()

            raise IntercomSipTimeoutError(str(_err)) from _err
        except (IntercomError, TypeError) as _err:
            self._safe_release()

            raise IntercomError(str(_err)) from _err

        self._started = False

        if not force:
            self.close_sockets()

    def close_sockets(self) -> None:
        """Close sockets"""

        if self._in:
            self._in.close()

        if self._out:
            self._out.close()

    async def open_sockets(self) -> None:
        """Open sockets"""

        if not self._in:
            self._in = socket.socket(
                socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP
            )
            self._in.bind((self._local_ip, self._local_port))

            self._out = self._in

            self._in.setblocking(False)

            self._in.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._in.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

    async def answer(
        self,
        message: Message,
        session_id: str,
        medias: dict[int, dict[int, RtpPayloadType]],
    ) -> None:
        """Answer voip sip

        :param message: Message
        :param session_id: str
        :param medias: dict[int, dict[int, RtpPayloadType]]
        """

        await self._send(
            self._answer_payload(message, session_id, medias).encode("utf8")
        )

    async def hangup(self, message: Message) -> None:
        """Hangup voip sip

        :param message: Message
        """

        await self._send(self._bye_payload(message).encode("utf8"))

    async def decline(self, message: Message) -> None:
        """Decline voip sip

        :param message: Message
        """

        await self._send(self._decline_payload(message).encode("utf8"))

    async def _recv(self) -> None:
        while self._started and self._in:
            async with self._recv_lock:
                try:
                    raw = self._in.recv(8192)

                    if raw not in (b"\x00\x00\x00\x00", b"\r\n") and len(raw) > 0:
                        message = await MessageParser().parse(raw)
                        await self._handle(message)
                except BlockingIOError:  # pragma: no cover
                    await asyncio.sleep(0.01)
                except IntercomError as _err:
                    _LOGGER.debug("Recv error: %r", _err)

                    await asyncio.sleep(0.01)

    async def _ping(self) -> None:
        while self._started:
            await self._send(b"0d0a0d0a")

            await asyncio.sleep(SIP_PING_TIMEOUT)

    def _safe_release(self) -> None:
        """Safe release"""

        if self._recv_lock.locked():  # pragma: no cover
            self._recv_lock.release()

    async def _safe_register(self) -> None:
        """Register command"""

        try:
            self._status_callback(VoipState.DEREGISTERING)

            await self.stop(True, True)

            self._status_callback(VoipState.REGISTERING)

            await self.start()

            self._status_callback(VoipState.REGISTERED)
        except (IntercomError, TimeoutError) as _err:
            _LOGGER.debug("Re-registration error: %r", _err)

            self._safe_release()

            self._status_callback(VoipState.FAILED)

            self.register_loop = self.hass.loop.call_later(
                SIP_RETRY_SLEEP,
                lambda: self.hass.async_create_task(self._safe_register()),
            )

    async def _register(self) -> None:
        """Register command"""

        self._safe_release()

        async with self._recv_lock:
            await self._send(self._register_payload(self._reg_urn_uuid).encode("utf8"))

            ready: tuple = select.select([self._in], [], [], SIP_TIMEOUT)
            if not ready or not ready[0] or not self._in:
                raise TimeoutError("Registering on SIP Server timed out")

            message: Message = await MessageParser().parse(self._in.recv(8192))
            self._debug_message(message)

            if message.status == MessageStatus.TRYING:
                message = await MessageParser().parse(self._in.recv(8192))
                self._debug_message(message)

            if message.status == MessageStatus.BAD_REQUEST:
                raise IntercomInvalidStateError(MessageStatus.BAD_REQUEST.description)

            if message.status == MessageStatus.UNAUTHORIZED:
                await self._send(
                    self._register_payload(self._reg_urn_uuid, message).encode("utf8")
                )

                ready = select.select([self._in], [], [], SIP_TIMEOUT)
                if not ready or not ready[0] or not self._in:
                    raise TimeoutError("Registering on SIP Server timed out")

                message = await MessageParser().parse(self._in.recv(8192))
                self._debug_message(message)

            if message.status == MessageStatus.UNAUTHORIZED:
                raise IntercomInvalidAccountInfoError(
                    f"Invalid Username or Password for SIP server {self._address}:{self._local_port}"
                )

            if message.status == MessageStatus.BAD_REQUEST:
                raise IntercomInvalidStateError(MessageStatus.BAD_REQUEST.description)

        if message.status != MessageStatus.PROXY_AUTHENTICATION_REQUIRED:
            if not message.status or message.status.value >= 500:
                await asyncio.sleep(SIP_RETRY_SLEEP)

                return await self._register()

            await self._handle(message)

        if message.status != MessageStatus.OK:
            raise IntercomInvalidAccountInfoError(
                f"Invalid Username or Password for SIP server {self._address}:{self._local_port}"
            )

        if self._started:
            self.register_loop = self.hass.loop.call_later(
                SIP_EXPIRES - 10,
                lambda: self.hass.async_create_task(self._safe_register()),
            )

    async def _deregister(self) -> None:
        """Deregister command"""

        self._safe_release()

        async with self._recv_lock:
            await self._send(
                self._register_payload(self._reg_urn_uuid, register=False).encode(
                    "utf8"
                )
            )

            ready: tuple = select.select([self._in], [], [], SIP_TIMEOUT)
            if not ready or not ready[0] or not self._in:
                raise TimeoutError("Registering on SIP Server timed out")

            message: Message = await MessageParser().parse(self._in.recv(8192))
            self._debug_message(message)

            if message.status == MessageStatus.UNAUTHORIZED:
                await self._send(
                    self._register_payload(
                        self._reg_urn_uuid, message, register=False
                    ).encode("utf8")
                )

                ready = select.select([self._in], [], [], SIP_TIMEOUT)
                if not ready or not ready[0] or not self._in:
                    raise TimeoutError("Registering on SIP Server timed out")

                message = await MessageParser().parse(self._in.recv(8192))
                self._debug_message(message)

        if not message.status or message.status.value >= 500:
            await asyncio.sleep(SIP_RETRY_SLEEP)

            return await self._deregister()

    def _debug_message(self, message: Message) -> None:
        """Debug message

        :param message: Message
        """

        self._debug_callback(
            "sip_message", "SIP Message: %r", message.plain, append=True
        )

    async def _handle(self, message: Message) -> None:
        """Handle

        :param message: Message
        """

        self._debug_message(message)

        if message.type != MessageType.MESSAGE:
            return

        if message.method == "INVITE":
            await self._send(self._trying_payload(message).encode("utf8"))
            await self._send(self._ringing_payload(message).encode("utf8"))
        elif message.method == "CANCEL":
            await self._send(self._ok_payload(message).encode("utf8"))
            await self._send(self._terminated_payload(message).encode("utf8"))
        elif message.method == "BYE":
            await self._send(self._ok_payload(message).encode("utf8"))

        if message.method in ["INVITE", "ACK", "CANCEL", "BYE"]:
            await self._callback(message)

    async def _send(self, message: bytes) -> None:
        """Send message

        :param message: bytes
        """

        if message == b"0d0a0d0a":
            self._debug_callback(
                "sip_ping", "SIP Ping: %r", time.time(), increment=True
            )
        else:
            self._debug_callback("sip_send", "SIP Send: %r", message, append=True)

        try:
            if self._out:
                self._out.sendto(
                    message,
                    (self._address, self._port),
                )

                if not self._internet_connect:  # pragma: no cover
                    self._status_callback(VoipState.INACTIVE, True)
                self._internet_connect = True
        except OSError:  # pragma: no cover
            self._internet_connect = False
            self._status_callback(VoipState.FAILED)

    def generate_spd(
        self,
        session_id: str,
        medias: dict[int, dict[int, RtpPayloadType]],
        only_audio: bool = False,
    ) -> str:
        """Generate SDP

        :param session_id: str
        :param medias: dict[int, dict[int, RtpPayloadType]]
        :param only_audio: bool
        :return str
        """

        return str(
            "v=0\r\n"
            f"o={self._username} {session_id} {int(session_id) + 2} "
            f"IN IP4 {self._local_ip}\r\n"
            "s=Talk\r\n"
            f"c=IN IP4 {self._local_ip}\r\n"
            "t=0 0\r\n"
            f"{self._body_payload(medias, only_audio)}\r\n"
        )

    def _answer_payload(
        self,
        message: Message,
        session_id: str,
        medias: dict[int, dict[int, RtpPayloadType]],
    ) -> str:
        """Generate answer

        :param message: Message
        :param session_id: str
        :param medias: dict[int, dict[int, RtpPayloadType]]
        :return str
        """

        body: str = self.generate_spd(session_id, medias)

        header: str = self._default_payload(
            message, MessageStatus.OK, "INVITE"
        ).replace("\r\n\r\n", "\r\n")

        return str(
            f"{header}"
            "Allow: INVITE, ACK, CANCEL, OPTIONS, BYE, "
            "REFER, NOTIFY, MESSAGE, SUBSCRIBE, INFO, PRACK, UPDATE\r\n"
            f'Contact: <sip:{message.headers["To"]["raw"]}>;'
            f'expires={SIP_EXPIRES};+sip.instance="<urn:uuid:{self._urn_uuid}>"\r\n'
            "Content-Type: application/sdp\r\n"
            f"Content-Length: {len(body)}\r\n\r\n"
            f"{body}"
        )

    def _bye_payload(self, message: Message) -> str:
        """Generate bye payload

        :param message: Message
        :return str
        """

        if message.headers["Call-ID"] not in self.tags:  # pragma: no cover
            self.tags[message.headers["Call-ID"]] = self._tag

        _from_ip, _ = message.headers["To"]["host"].split(":")

        return str(
            f'BYE sip:{message.headers["From"]["number"]}@{self._address}:{self._port} SIP/2.0\r\n'
            f"Via: SIP/2.0/UDP {self._local_ip}:{self._local_port};branch={self._branch};rport\r\n"
            f'From: <sip:{self._username}@{_from_ip}>;tag={self.tags[message.headers["Call-ID"]]}\r\n'
            f'To: "{message.headers["From"]["number"]}" '
            f'<sip:{message.headers["From"]["number"]}@{self._address}>;'
            f'tag={message.headers["From"]["tag"]}\r\n'
            f'CSeq: {message.headers["CSeq"]["check"]} BYE\r\n'
            f'Call-ID: {message.headers["Call-ID"]}\r\n'
            "Max-Forwards: 70\r\n"
            f"User-Agent: {SIP_USER_AGENT}\r\n\r\n"
        )

    @staticmethod
    def _body_payload(
        medias: dict[int, dict[int, RtpPayloadType]], only_audio: bool = False
    ) -> str:
        """Generate body

        :param medias: dict[int, dict[int, RtpPayloadType]]
        :param only_audio: bool
        :return str
        """

        body: str = ""
        for port, codecs in medias.items():
            media_type: str = (
                "video" if RtpPayloadType.H264.value in codecs else "audio"
            )

            if only_audio and media_type == "video":  # pragma: no cover
                continue

            body += f"m={media_type} {port} RTP/AVP"
            for codec in codecs.values():
                body += f" {codec.value}"

                if codec not in [RtpPayloadType.PCMA, RtpPayloadType.PCMU]:
                    body += (
                        f"\r\na=rtpmap:{codec.value} {codec.description}/{codec.rate}"
                    )

                if media_type == "video":
                    body += f"\r\na=fmtp:{codec.value} profile-level-id=42801F; packetization-mode=1"

            body += "\r\n"

        return body

    def _terminated_payload(self, message: Message) -> str:
        """Generate ok payload

        :param message: Message: Prev message
        :return str
        """

        return self._default_payload(
            message, MessageStatus.REQUEST_TERMINATED, "INVITE"
        )

    def _ok_payload(self, message: Message) -> str:
        """Generate ok payload

        :param message: Message: Prev message
        :return str
        """

        return self._default_payload(message, MessageStatus.OK)

    def _decline_payload(self, message: Message) -> str:
        """Generate decline payload

        :param message: Message: Prev message
        :return str
        """

        return self._default_payload(message, MessageStatus.DECLINE)

    def _ringing_payload(self, message: Message) -> str:
        """Generate ringing payload

        :param message: Message: Prev message
        :return str
        """

        return self._default_payload(message, MessageStatus.RINGING)

    def _default_payload(
        self, message: Message, status: MessageStatus, method: str | None = None
    ) -> str:
        """Generate default payload

        :param message: Message: Prev message
        :param status: MessageStatus
        :param method: str | None
        :return str
        """

        if not method:
            method = message.headers["CSeq"]["method"]

        if message.headers["Call-ID"] not in self.tags:
            self.tags[message.headers["Call-ID"]] = self._tag

        return str(
            f"SIP/2.0 {status.value} {status.phrase}\r\n"
            f'Via: SIP/2.0/UDP {self._address}:{self._port};branch={message.via["branch"]};rport\r\n'
            f'From: {message.headers["From"]["raw"]};tag={message.headers["From"]["tag"]}\r\n'
            f'To: {message.headers["To"]["raw"]};tag={self.tags[message.headers["Call-ID"]]}\r\n'
            f'Call-ID: {message.headers["Call-ID"]}\r\n'
            f'CSeq: {message.headers["CSeq"]["check"]} {method}\r\n'
            f"User-Agent: {SIP_USER_AGENT}\r\n"
            "Supported: replaces, outbound, gruu\r\n\r\n"
        )

    def _trying_payload(self, message: Message) -> str:
        """Generate trying payload

        :param message: Message: Prev message
        :return str
        """

        status: MessageStatus = MessageStatus.TRYING

        return str(
            f"SIP/2.0 {status.value} {status.phrase}\r\n"
            f'Via: SIP/2.0/UDP {self._address}:{self._port};branch={message.via["branch"]};rport\r\n'
            f'From: {message.headers["From"]["raw"]};tag={message.headers["From"]["tag"]}\r\n'
            f'To: {message.headers["From"]["raw"]}\r\n'
            f'Call-ID: {message.headers["Call-ID"]}\r\n'
            f'CSeq: {message.headers["CSeq"]["check"]} {message.headers["CSeq"]["method"]}\r\n\r\n'
        )

    def _register_payload(
        self, urn_uuid: str, message: Message | None = None, register: bool = True
    ) -> str:
        """Generate register payload

        :param urn_uuid: str: URN uuid
        :param message: Message | None: Prev message
        :param register: bool: Is register
        :return str
        """

        call_id: str = self._call_id
        contact_ip: str = self._local_ip
        contact_port: int = self._local_port

        authorization: str = ""
        if message:
            response: str = str(self._calc_response_hash(message), "utf8")
            realm: str = message.auth["realm"]
            nonce: str = message.auth["nonce"]

            authorization = str(
                "\r\n"
                f'Authorization:  Digest realm="{realm}", '
                f'nonce="{nonce}",algorithm=MD5, '
                f'username="{self._username}",  '
                f'uri="sip:{self._address}:{self._port}", '
                f'response="{response}"'
            )

            call_id = message.headers["Call-ID"]
            contact_ip = message.via["received"]
            contact_port = int(message.via["rport"])

        return str(
            f"REGISTER sip:{self._address}:{self._port} SIP/2.0\r\n"
            f"Via: SIP/2.0/UDP {self._local_ip}:{self._local_port};"
            f"branch={self._branch};rport\r\n"
            f"From: <sip:{self._username}@{self._address}>;"
            f"tag={self.tags[TAG_REGISTER if register else TAG_DEREGISTER]}\r\n"
            f"To: sip:{self._username}@{self._address}\r\n"
            f"CSeq: {self._cnt_register.next()} REGISTER\r\n"
            f"Call-ID: {call_id}\r\n"
            "Max-Forwards: 70\r\n"
            "Supported: replaces, outbound, gruu\r\n"
            "Accept: application/sdp\r\n"
            "Accept: text/plain\r\n"
            "Accept: application/vnd.gsma.rcs-ft-http+xml\r\n"
            f"Contact: <sip:{self._username}@{contact_ip}:{contact_port};"
            f'transport=udp>;+sip.instance="<urn:uuid:{urn_uuid}>"\r\n'
            f"Expires: {SIP_EXPIRES if register else 0}\r\n"
            f"User-Agent: {SIP_USER_AGENT}"
            f"{authorization}"
            "\r\n\r\n"
        )

    def _calc_response_hash(self, message: Message) -> bytes:
        """Calc response hash

        :param message: Message
        :return bytes
        """

        first_path: str = hashlib.md5(
            f"{self._username}:{message.auth['realm']}:{self._password}".encode("utf8")
        ).hexdigest()

        second_path: str = hashlib.md5(
            f"{message.headers['CSeq']['method']}:sip:{self._address}:{self._port}".encode(
                "utf8"
            )
        ).hexdigest()

        return bytes(
            hashlib.md5(
                f"{first_path}:{message.auth['nonce']}:{second_path}".encode("utf8")
            )
            .hexdigest()
            .encode("utf8")
        )


class MessageParser:  # pylint: disable=too-few-public-methods
    """Message parser"""

    _message: Message

    async def parse(self, data: bytes) -> Message:
        """Parse sip data

        :param data: bytes
        :return Message
        """

        if not data:  # pragma: no cover
            raise IntercomSipParseError("Unable to parse content.")

        _LOGGER.debug("SIP (plain): %r", data)

        plain_headers, plain_body = self._split(data.replace(b"\\r\\n", b"\r\n"))

        headers: list[bytes] = plain_headers.split(b"\r\n")

        self._message = Message(data, headers.pop(0))

        self._parse_headers(headers)

        if plain_body:
            if "Content-Encoding" in self._message.headers:  # pragma: no cover
                raise IntercomSipParseError("Unable to parse encoded content.")

            self._parse_body(plain_body)

        _LOGGER.debug("SIP (parsed): %r", self._message.as_dict())

        return self._message

    def _parse_body(  # pylint: disable=too-many-branches
        self, plain_body: bytes
    ) -> None:  # pylint: disable=too-many-branches
        """Parse body

        :param plain_body: bytes
        """

        body = plain_body.split(b"\r\n")
        for _data in body:
            data = str(_data, "utf8").split("=")
            if data == [""]:
                continue

            if (
                "Content-Type" not in self._message.headers
                or self._message.headers["Content-Type"] != "application/sdp"
                or data[0] not in ["v", "o", "c", "b", "t", "r", "z", "k", "m", "a"]
            ):
                self._message.add_body(data[0], data[1])  # type: ignore

                continue

            if data[0] == "v":
                self._message.add_body(data[0], int(data[1]))  # type: ignore

                continue

            if data[0] == "o":
                self._parse_o(data[0], data[1])  # type: ignore

                continue

            if data[0] == "c":
                self._parse_c(data[0], data[1])  # type: ignore

                continue

            if data[0] == "b":
                self._parse_b(data[0], data[1])  # type: ignore

                continue

            if data[0] == "t":
                self._parse_t(data[0], data[1])  # type: ignore

                continue

            if data[0] == "r":  # pragma: no cover
                self._parse_r(data[0], data[1])  # type: ignore

                continue

            if data[0] == "z":  # pragma: no cover
                self._parse_z(data[0], data[1])  # type: ignore

                continue

            if data[0] == "k":  # pragma: no cover
                self._parse_k(data[0], data[1])  # type: ignore

                continue

            if data[0] == "m":
                self._parse_m(data[0], data[1])  # type: ignore

                continue

            if data[0] == "a":
                self._parse_a(data[0], data[1])  # type: ignore

    def _parse_a(self, header: str, data: str) -> None:
        """Parse a

        a=<attribute>
        a=<attribute>:<value>

        :param header: str
        :param data: str
        """

        attribute: str = data
        value: str | None = None

        if ":" in data:
            chunk: list[str] = data.split(":")

            attribute = chunk[0]
            value = chunk[1]

        if not value:
            if attribute in ["recvonly", "sendrecv", "sendonly", "inactive"]:
                self._message.add_body(
                    header, {"transmit_type": TransmitType(attribute)}
                )

            return

        if attribute == "rtpmap":
            values = re.split(" |/", value)

            self._message.add_media_attr(
                values[0],
                "rtpmap",
                {
                    "id": values[0],
                    "name": values[1],
                    "frequency": values[2],
                    "encoding": values[3] if len(values) == 4 else None,
                },
            )

            return

        if attribute == "fmtp":
            values = value.split(" ")

            self._message.add_media_attr(
                values[0],
                "fmtp",
                {
                    "id": values[0],
                    "settings": values[1:],
                },
            )

            return

        self._message.add_body(header, {attribute: value})

    def _parse_m(self, header: str, data: str) -> None:
        """Parse m

        m=<media> <port>/<number of ports> <proto> <fmt> ...

        :param header: str
        :param data: str
        """

        chunk: list[str] = data.split(" ")

        port: str = chunk[1]
        count: int = 1

        if "/" in chunk[1]:  # pragma: no cover
            ports: list[str] = chunk[1].split("/")
            port = ports[0]
            count = int(ports[1])

        methods: list[str] = chunk[3:]

        self._message.add_body(
            header,
            {
                "type": chunk[0],
                "port": int(port),
                "port_count": count,
                "protocol": RtpProtocol(chunk[2]),
                "methods": methods,
                "attributes": {attr: {} for attr in methods},
            },
        )

    def _parse_k(self, header: str, data: str) -> None:  # pragma: no cover
        """Parse k

        k=<method>
        k=<method>:<encryption key>

        :param header: str
        :param data: str
        """

        if ":" not in data:
            self._message.add_body(
                header,
                ReadOnlyDict({"method": data}),
            )

            return

        chunk: list[str] = data.split(":")
        self._message.add_body(
            header,
            ReadOnlyDict({"method": chunk[0], "key": chunk[1]}),
        )

    def _parse_z(self, header: str, data: str) -> None:  # pragma: no cover
        """Parse r

        z=<adjustment time> <offset> <adjustment time> <offset> ....

        :param header: str
        :param data: str
        """

        chunk: list[str] = data.split()
        amount: int = len(chunk) // 2

        body_data: dict = {}

        for index in range(amount):
            body_data[f"adjustment-time{str(index)}"] = chunk[index * 2]
            body_data[f"offset{str(index)}"] = chunk[index * 2 + 1]

        self._message.add_body(
            header,
            ReadOnlyDict(body_data),
        )

    def _parse_r(self, header: str, data: str) -> None:  # pragma: no cover
        """Parse r

        r=<repeat interval> <active duration> <offsets from start-time>

        :param header: str
        :param data: str
        """

        chunk: list[str] = data.split(" ")
        self._message.add_body(
            header,
            ReadOnlyDict(
                {
                    "repeat": chunk[0],
                    "duration": chunk[1],
                    "offset1": chunk[2],
                    "offset2": chunk[3],
                }
            ),
        )

    def _parse_t(self, header: str, data: str) -> None:
        """Parse t

        t=<start-time> <stop-time>

        :param header: str
        :param data: str
        """

        chunk: list[str] = data.split(" ")
        self._message.add_body(
            header, ReadOnlyDict({"start": chunk[0], "stop": chunk[1]})
        )

    def _parse_b(self, header: str, data: str) -> None:
        """Parse b

        b=<bwtype>:<bandwidth>

        :param header: str
        :param data: str
        """

        chunk: list[str] = data.split(":")
        self._message.add_body(
            header, ReadOnlyDict({"type": chunk[0], "bandwidth": chunk[1]})
        )

    def _parse_c(self, header: str, data: str) -> None:  # pragma: no cover
        """Parse c

        c=<nettype> <addrtype> <connection-address>

        :param header: str
        :param data: str
        """

        chunk: list[str] = data.split(" ")

        general: dict = {
            "network_type": chunk[0],
            "address_type": chunk[1],
            "ttl": None,
            "address_count": 1,
        }

        if "/" not in chunk[2]:
            self._message.add_body(
                header,
                ReadOnlyDict(
                    general
                    | {
                        "address": chunk[2],
                    }
                ),
            )

            return

        if chunk[1] == "IP6":
            self._message.add_body(
                header,
                ReadOnlyDict(
                    general
                    | {
                        "address": chunk[2].split("/")[0],
                        "address_count": int(chunk[2].split("/")[1]),
                    }
                ),
            )

            return

        address_data: list[str] = chunk[2].split("/")

        if len(address_data) == 2:
            self._message.add_body(
                header,
                ReadOnlyDict(
                    general
                    | {
                        "address": address_data[0],
                        "ttl": int(address_data[1]),
                    }
                ),
            )

            return

        self._message.add_body(
            header,
            ReadOnlyDict(
                general
                | {
                    "address": address_data[0],
                    "ttl": int(address_data[1]),
                    "address_count": int(address_data[2]),
                }
            ),
        )

    def _parse_o(self, header: str, data: str) -> None:
        """Parse o

        o=<username> <sess-id> <sess-version> <nettype> <addrtype> <unicast-address>

        :param header: str
        :param data: str
        """

        chunk: list[str] = data.split(" ")
        self._message.add_body(
            header,
            ReadOnlyDict(
                {
                    "username": chunk[0],
                    "id": chunk[1],
                    "version": chunk[2],
                    "network_type": chunk[3],
                    "address_type": chunk[4],
                    "address": chunk[5],
                }
            ),
        )

    def _parse_headers(self, headers: list[bytes]) -> None:
        """Parse headers

        :param headers: list[bytes]
        """

        prepared: dict[str, Any] = {"Via": []}

        for header in headers:
            chunk = str(header, "utf8").split(": ")
            if chunk[0] == "Via":
                prepared["Via"].append(chunk[1])
                continue

            if chunk[0] not in prepared:
                prepared[chunk[0]] = chunk[1]

        for header, data in prepared.items():  # type: ignore
            if header == "Via":
                self._parse_via(header, data)  # type: ignore

                continue

            if header in ["From", "To"]:
                self._parse_from_or_to(header, data)  # type: ignore

                continue

            if header == "CSeq":
                self._parse_cseq(header, data)  # type: ignore

                continue

            if header in ["WWW-Authenticate", "Authorization"]:
                self._parse_auth(header, data)  # type: ignore

                continue

            if header in ["Allow", "Supported"]:
                self._message.add_header(header, data.split(", "))  # type: ignore

                continue

            if header == "Content-Length":
                self._message.add_header(header, int(data))  # type: ignore

                continue

            self._message.add_header(header, data)  # type: ignore

    def _parse_auth(self, header: str, data: bytes) -> None:
        """Parse WWW-Authenticate or Authorization

        :param header: str
        :param data: bytes
        """

        data: bytes = data.replace("Digest", "")  # type: ignore
        info: list[bytes] = data.split(", ")  # type: ignore

        auth = {}
        for field in info:
            field = field.strip()
            auth[str(field.split("=")[0])] = field.split("=")[1].strip('"')  # type: ignore

        self._message.add_header(header, ReadOnlyDict(auth))

    def _parse_cseq(self, header: str, data: bytes) -> None:
        """Parse CSeq

        :param header: str
        :param data: bytes
        """

        check, method = data.split(" ")  # type: ignore

        self._message.add_header(
            header, ReadOnlyDict({"check": check, "method": method})
        )

    def _parse_from_or_to(self, header: str, data: bytes) -> None:
        """Parse From or To header

        :param header: str
        :param data: bytes
        """

        info: list[bytes] = data.split(";tag=")  # type: ignore

        contact: list[str] = re.split(r"<?sip:", str(info[0]))

        if len(contact) > 1:
            address: str = contact[1].strip(">")

            try:
                number, host = address.split("@")
            except ValueError:  # pragma: no cover
                number, host = None, address
        else:
            address, host, number = "", "", ""

        self._message.add_header(
            header,
            ReadOnlyDict(
                {
                    "raw": info[0],
                    "tag": info[1] if len(info) >= 2 else "",
                    "address": address,
                    "number": number,
                    "caller": contact[0].strip('"').strip("'"),
                    "host": host,
                }
            ),
        )

    def _parse_via(self, header: str, data: list) -> None:
        """Parse Via header

        :param header: str
        :param data: list
        """

        for plain_via in data:
            _info: list[bytes] = re.split(r" |;", plain_via)  # type: ignore

            _address: list[bytes] = _info[1].split(":")  # type: ignore

            via: dict[str, Any] = {
                "type": _info[0],
                "address": (
                    _address[0],
                    int(_address[1]) if len(_address) > 1 else 60266,
                ),
            }

            for field in _info[2:]:
                if "=" in field:  # type: ignore
                    via[str(field.split("=")[0])] = field.split("=")[1]  # type: ignore
                else:
                    via[str(field)] = None

            self._message.add_header(header, ReadOnlyDict(via))

    @staticmethod
    def _split(data: bytes) -> tuple[bytes, bytes | None]:
        """Split data

        :param data: bytes
        :return tuple[bytes, bytes | None]
        """

        try:
            headers, body = data.split(b"\r\n\r\n")

            return headers, body
        except ValueError:  # pragma: no cover
            return data.split(b"\r\n\r\n")[0], None


class Message:
    """SIP message"""

    _plain: bytes
    _heading: bytes | None = None

    def __init__(self, plain: bytes, heading: bytes) -> None:
        """Init message

        :param plain: bytes
        :param heading: bytes
        """

        self._plain = plain
        self._heading = heading

        self._headers: dict = {"Via": []}
        self._body: dict = {"c": [], "m": [], "a": {}}

    @property
    def plain(self) -> bytes:  # pragma: no cover
        """Property plain

        :return bytes
        """

        return self._plain

    @property
    def heading(self) -> bytes:  # pragma: no cover
        """Property heading

        :return bytes
        """

        return self._heading or b""

    @property
    def headers(self) -> ReadOnlyDict:
        """Property headers

        :return ReadOnlyDict
        """

        return ReadOnlyDict(self._headers)

    @property
    def body(self) -> ReadOnlyDict:
        """Property body

        :return ReadOnlyDict
        """

        return ReadOnlyDict(self._body)

    @cached_property
    def type(self) -> MessageType:
        """Property type

        :return MessageType
        """

        if self._heading:
            code: str = str(self._heading.split(b" ")[0], "utf8")
            if code == "SIP/2.0":
                return MessageType.RESPONSE

            if code in {"INVITE", "ACK", "BYE", "CANCEL"}:
                return MessageType.MESSAGE

        raise IntercomSipParseError(
            f"Unable to decipher SIP request: {str(self._heading)}"
        )

    @cached_property
    def version(self) -> str:
        """Property version

        :return str
        """

        index: int = 0 if self.type == MessageType.RESPONSE else 2

        return str(self._heading.split(b" ")[index], "utf8") if self._heading else ""

    @cached_property
    def method(self) -> str | None:
        """Property method

        :return str | None
        """

        if self.type == MessageType.RESPONSE or not self._heading:
            return None

        return str(self._heading.split(b" ")[0], "utf8")

    @cached_property
    def status(self) -> MessageStatus | None:
        """Property status

        :return MessageStatus | None
        """

        if self.type == MessageType.MESSAGE or not self._heading:
            return None

        return MessageStatus(int(self._heading.split(b" ")[1]))

    @cached_property
    def auth(self) -> ReadOnlyDict:
        """Property auth

        :return ReadOnlyDict
        """

        return ReadOnlyDict(
            self._headers.get(
                "WWW-Authenticate", self._headers.get("Authorization", {})
            )
        )

    @property
    def via(self) -> ReadOnlyDict:
        """Property via

        :return ReadOnlyDict
        """

        return ReadOnlyDict(self._headers.get("Via", [{}])[0])

    def add_header(self, header: str, data: Any) -> None:
        """Add header

        :param header: str
        :param data: Any
        """

        if header == "Via":
            self._headers[header].append(data)

            return

        self._headers[header] = data

    def add_body(self, header: str, data: Any) -> None:
        """Add body

        :param header: str
        :param data: Any
        """

        if header == "a":
            self._body[header] |= data

            return

        if header in {"c", "m"}:
            self._body[header].append(data)

            return

        self._body[header] = data

    def add_media_attr(self, attr_index: Any, attr_code: str, value: Any) -> None:
        """Add media attr

        :param attr_index: Any
        :param attr_code: str
        :param value: Any
        """

        media_index: int | None = next(
            (
                int(self._body["m"].index(media))
                for media in self._body["m"]
                if attr_index in media["methods"]
            ),
            None,
        )

        if not media_index or media_index > (len(self._body["m"]) - 1):
            return

        if (
            attr_index not in self._body["m"][media_index]["attributes"]
        ):  # pragma: no cover
            self._body["m"][media_index]["attributes"][attr_index] = {}

        self._body["m"][media_index]["attributes"][attr_index][attr_code] = value

    def as_dict(self) -> ReadOnlyDict[str, Any]:
        """As dict

        :return ReadOnlyDict[str, Any]
        """

        return ReadOnlyDict(
            {
                "type": self.type,
                "version": self.version,
                "method": self.method,
                "status": self.status,
                "auth": self.auth,
                "headers": ReadOnlyDict(self._headers),
                "body": ReadOnlyDict(self._body),
            }
        )
