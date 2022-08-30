"""Tattelecom Intercom voip."""


from __future__ import annotations

import asyncio
import logging
import random
import socket
import traceback
from asyncio import Lock
from collections.abc import Callable
from functools import cached_property
from io import StringIO
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.util.read_only_dict import ReadOnlyDict

from .const import (
    SIGNAL_SIP_STATE,
    SIP_DEFAULT_RETRY,
    SIP_RETRY_SLEEP,
    VOIP_CLEAN_DELAY,
)
from .enum import CallState, RtpPayloadType, SendMode, VoipState
from .exceptions import IntercomError, IntercomInvalidStateError
from .rtp import RtpClient
from .sip import IntercomSip, Message

_LOGGER = logging.getLogger(__name__)


class IntercomVoip:
    """Intercom voip class"""

    hass: HomeAssistant

    status: VoipState = VoipState.INACTIVE

    _call_callback: Callable
    _synchronous: bool = False

    _address: str
    _port: int

    sip: IntercomSip

    assigned_ports: list[int] = []
    session_ids: list[int] = []

    def __init__(  # pylint: disable=too-many-arguments
        self,
        hass: HomeAssistant,
        address: str,
        port: int,
        username: str,
        password: str,
        callback: Callable,
        synchronous: bool = False,
    ) -> None:
        """Initialize Intercom Voip

        :param hass: HomeAssistant: Home Assistant object
        :param address: str: SIP address
        :param port: int: SIP port
        :param username: str: SIP username
        :param password: str: SIP password
        :param callback: Callable: Voip callback
        :param synchronous: bool: Synchronous call callback
        """

        self.hass = hass

        self.diagnostics: dict[str, Any] = {}

        self.calls: dict[str, Call] = {}

        self._address = address
        self._port = port

        self._call_callback = callback  # type: ignore
        self._synchronous = synchronous

        self.sip = IntercomSip(
            hass,
            address,
            port,
            username,
            password,
            self._local_ip,
            self._callback,
            self._change_status,
            self.debug,
        )

    @cached_property
    def _local_ip(self) -> str:
        """Get real local ip"""

        ip_address: str | None = next(
            (
                _ip
                for _ip in socket.gethostbyname_ex(socket.gethostname())[2]
                if not _ip.startswith("127.")
            ),
            None,
        )

        if not ip_address:
            dns_socket: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            dns_socket.connect(("8.8.8.8", 53))
            ip_address = dns_socket.getsockname()[0]
            dns_socket.close()

        return ip_address or "0.0.0.0"

    @property
    def session_id(self) -> int:
        """Generate session ID"""

        while True:
            proposed: int = random.randint(1, 100000)
            if proposed not in self.session_ids:
                self.session_ids.append(proposed)

                return proposed

    async def clean_call(self, call_id: str) -> None:
        """Clean calls

        :param call_id
        """

        if call_id in self.calls:
            call: Call = self.calls[call_id]
            await call.stop_rtp()

            if int(call.session_id) in self.session_ids:
                self.session_ids.remove(int(call.session_id))

            del self.calls[call_id]

    async def _callback(self, message: Message) -> None:
        """Voip callback

        :param message: Message
        """

        call: Call | None = None
        if message.method == "INVITE":
            call = await self._callback_invite(message)
        elif message.method == "ACK":
            call = await self._callback_ack(message)
        elif message.method in ("BYE", "CANCEL"):
            call = await self._callback_bye_or_cancel(message)

        if call:
            if self._synchronous:
                await self._call_callback(call)

                return

            self.hass.loop.call_soon(  # pragma: no cover
                lambda: self.hass.async_create_task(self._call_callback(call)),
            )

    async def _callback_bye_or_cancel(self, message: Message) -> Call | None:
        """Voip bye or cancel callback

        :param message: Message
        :return Call | None
        """

        call_id = message.headers["Call-ID"]
        if call_id not in self.calls:  # pragma: no cover
            return None

        call: Call = self.calls[call_id]
        call.state = CallState.ENDED

        await call.stop_rtp()
        await self.clean_call(call_id)

        return call

    async def _callback_ack(self, message: Message) -> Call | None:
        """Voip ack callback

        :param message: Message
        :return Call | None
        """

        call_id = message.headers["Call-ID"]
        if call_id not in self.calls:  # pragma: no cover
            return None

        call: Call = self.calls[call_id]

        if call.state == CallState.RINGING:
            call.state = CallState.ANSWERED

        return call

    async def _callback_invite(self, message: Message) -> Call:
        """Voip invite callback

        :param message: Message
        :return Call
        """

        call_id = message.headers["Call-ID"]

        if call_id in self.calls:  # pragma: no cover
            if self.calls[call_id].state != CallState.RINGING:
                await self.calls[call_id].renegotiate(message)

            return self.calls[call_id]

        self.calls[call_id] = Call(
            self, CallState.RINGING, message, self.session_id, self._local_ip
        )

        self.hass.loop.call_later(
            VOIP_CLEAN_DELAY,
            lambda: self.hass.async_create_task(self.clean_call(call_id)),
        )

        return self.calls[call_id]

    async def safe_start(
        self, total_retry: int = 0, sleep: int = SIP_RETRY_SLEEP, retry: int = 1
    ) -> bool:
        """Safe start voip

        :param total_retry: int
        :param sleep: int
        :param retry: int
        :return bool
        """

        try:
            await self.sip.stop(True)

            return await self.start()
        except IntercomError as _err:
            _LOGGER.debug("Failed to stop/start VoIP (%r): %r", retry, _err)

            if retry <= total_retry:
                await asyncio.sleep(SIP_RETRY_SLEEP)

                return await self.safe_start(total_retry, sleep, retry + 1)

        return False

    async def start(self) -> bool:
        """Start voip

        :return bool
        """

        self._change_status(VoipState.REGISTERING)

        try:
            await self.sip.start()

            self._change_status(VoipState.REGISTERED)
        except IntercomError as _err:
            traceback.print_exc()
            _LOGGER.debug("Failed to start VoIP: %r", _err)

            self._change_status(VoipState.FAILED)

            return False

        return True

    async def stop(self) -> bool:
        """Stop voip

        :return bool
        """

        self._change_status(VoipState.DEREGISTERING)

        state: bool = True

        try:
            await self.sip.stop()
        except IntercomError as _err:
            _LOGGER.debug("Failed to stop VoIP: %r", _err)

            state = False

        self._change_status(VoipState.INACTIVE)

        call_ids: list = []
        for call_id, call in self.calls.items():  # pragma: no cover
            call.state = CallState.ENDED

            await call.stop_rtp()
            call_ids.append(call_id)

        for call_id in call_ids:  # pragma: no cover
            await self.clean_call(call_id)

        return state

    def _change_status(self, status: VoipState, register: bool = False) -> None:
        """Change status

        :param status: VoipState
        :param register: bool
        """

        self.status = status

        async_dispatcher_send(self.hass, SIGNAL_SIP_STATE)

        if register:  # pragma: no cover
            self.hass.loop.call_soon(
                lambda: self.hass.async_create_task(self.safe_start(SIP_DEFAULT_RETRY))
            )

    def debug(  # pylint: disable=too-many-arguments
        self,
        key: str,
        message: str,
        args: Any,
        increment: bool = False,
        append: bool = False,
    ) -> None:
        """Log debug and diagnostic

        :param key: str
        :param message: str
        :param args: Any
        :param increment: bool
        :param append: bool
        """

        if isinstance(args, bytes):
            args = args.decode("utf-8")

        _LOGGER.debug(message, args)

        if increment:
            if key not in self.diagnostics:
                self.diagnostics[key.lower()] = 0

            self.diagnostics[key.lower()] += 1

            return

        if append:
            if key not in self.diagnostics:
                self.diagnostics[key.lower()] = []

            self.diagnostics[key.lower()].append(args)

            if len(self.diagnostics[key.lower()]) > 20:  # pragma: no cover
                self.diagnostics[key.lower()] = self.diagnostics[key.lower()][-20:]

            return

        self.diagnostics[key.lower()] = args  # pragma: no cover


class Call:
    """Intercom call class"""

    state: CallState
    session_id: str
    call_id: str
    login: str
    local_ip: str
    port: int

    _phone: IntercomVoip
    _message: Message
    _session_id: str

    _port_high: int
    _port_low: int

    _send_mode: SendMode

    _dtmf_lock: Lock
    _dtmf: StringIO

    _connections: int = 0
    _audio_ports: int = 0
    _video_ports: int = 0

    def __init__(  # pylint: disable=too-many-arguments
        self,
        phone: IntercomVoip,
        state: CallState,
        message: Message,
        session_id: int,
        local_ip: str,
        port_range: tuple = (10000, 20000),
        medias: dict[int, RtpPayloadType] | None = None,
        send_mode: SendMode = SendMode.SEND_RECV,
    ) -> None:
        """Initialize Intercom Call

        :param phone: IntercomVoip
        :param state: CallState
        :param message: Message
        :param session_id: int
        :param local_ip: str
        :param port_range: tuple
        :param medias: dict[int, RtpPayloadType] | None
        :param send_mode: SendMode
        """

        self.state = state

        self._phone = phone
        self._message = message

        self.call_id = message.headers["Call-ID"]
        self.login = message.headers["From"]["number"]
        self.session_id = str(session_id)
        self.local_ip = local_ip

        self._port_low, self._port_high = port_range

        self._send_mode = send_mode

        self._clients: list[RtpClient] = []
        self._medias: dict[int, RtpPayloadType] | None = medias
        self._ms: dict[int, dict[int, RtpPayloadType]] = {}

        self._dtmf_lock = Lock()
        self._dtmf = StringIO()

        self._assigned_ports: dict = {}

        self._fill()

    def _fill(self) -> None:
        """Fill class"""

        if self.state == CallState.DIALING:  # pragma: no cover
            if self._medias is None:
                _LOGGER.debug("Media assignments are required when initiating a call")

                return

            for port, data in self._medias.items():
                self.port = int(port)
                self._assigned_ports[port] = data

            return

        if self.state == CallState.RINGING:
            for _x in self._message.body["c"]:
                self._connections += _x["address_count"]

            _audio, _video = self._get_audio_video()

            if not (
                (
                    (self._audio_ports / len(_audio) if _audio else 0)
                    == self._connections
                    or self._audio_ports == 0
                )
                and (
                    (self._video_ports / len(_video) if _video else 0)
                    == self._connections
                    or self._video_ports == 0
                )
            ):  # pragma: no cover
                _LOGGER.debug("Unable to assign ports for RTP.")

                return

            for _i in self._message.body["m"]:
                codecs: dict = self._get_codecs(_i)

                port = None  # type: ignore
                while port is None:
                    proposed = random.randint(self._port_low, self._port_high)
                    if proposed not in self._phone.assigned_ports:
                        self._phone.assigned_ports.append(proposed)
                        self._assigned_ports[proposed] = codecs
                        port = proposed

                for number in range(len(self._message.body["c"])):
                    self._clients.append(
                        RtpClient(
                            self._phone.hass,
                            codecs,
                            self.local_ip,
                            port,
                            self._message.body["c"][number]["address"],
                            _i["port"] + number,
                            self._dtmf_callback,
                            self._phone.debug,
                        )
                    )

    def _get_audio_video(self) -> tuple[list, list]:
        """Get audio and video

        :return tuple[list, list]
        """

        _audio: list = []
        _video: list = []

        for _x in self._message.body["m"]:
            if _x["type"] == "audio":
                self._audio_ports += _x["port_count"]
                _audio.append(_x)

                continue

            if _x["type"] == "video":
                self._video_ports += _x["port_count"]
                _video.append(_x)

                continue

            _LOGGER.debug(
                "Unknown media description: %r", _x["type"]
            )  # pragma: no cover

        return _audio, _video

    @staticmethod
    def _get_codecs(number: Any) -> dict:
        """Get codecs

        :param number: Any
        :return dict
        """

        assoc: dict = {}

        for _x in number["methods"]:
            try:
                assoc[int(_x)] = RtpPayloadType(int(_x))
            except (ValueError, KeyError):  # pragma: no cover
                try:
                    assoc[int(_x)] = RtpPayloadType(
                        number["attributes"][_x]["rtpmap"]["name"]
                    )
                except (ValueError, KeyError):
                    assoc[int(_x)] = RtpPayloadType.UNKNOWN

        return {
            index: codec
            for index, codec in assoc.items()
            if codec
            in (
                RtpPayloadType.PCMU,
                RtpPayloadType.PCMA,
                RtpPayloadType.H264,
                RtpPayloadType.EVENT,
            )
        }

    # TODO: Not yet supported by the manufacturer.
    async def _dtmf_callback(self, code: str) -> None:  # pragma: no cover
        """Dtmf callback

        :param code: str
        """

        async with self._dtmf_lock:
            offset: int = self._dtmf.tell()
            self._dtmf.seek(0, 2)
            self._dtmf.write(code)
            self._dtmf.seek(offset, 0)

    async def _gen_ms(self) -> dict[int, dict[int, RtpPayloadType]]:
        """Generate m SDP attribute for answering originally and for re-negotiations

        :return dict[int, dict[int, RtpPayloadType]]
        """

        attr = {}
        for client in self._clients:
            if client.is_audio:
                await client.stop()
                await client.start()

            attr[client.in_port] = client.assoc

        return attr

    async def stop_rtp(self) -> None:
        """Stop clients"""

        for client in self._clients:
            await client.stop()

    async def renegotiate(self, message: Message) -> None:  # pragma: no cover
        """Renegotiate call

        :param message: Message
        """

        self._ms = await self._gen_ms()

        await self._phone.sip.answer(message, self.session_id, self._ms)

        for media in message.body["m"]:
            for index, client in zip(range(len(message.body["c"])), self._clients):
                client.out_ip = message.body["c"][index]["address"]
                client.out_port = media["port"]

    async def _re_answer(self) -> None:  # pragma: no cover
        """Re answer"""

        if self.state != CallState.RINGING:
            return

        await self.answer()

    async def answer(self) -> bool:
        """Answer call

        :return bool
        """

        if self.state != CallState.RINGING:  # pragma: no cover
            _LOGGER.debug("Call %r is not ringing", self.call_id)

            raise IntercomInvalidStateError(f"Call {self.call_id} is not ringing")

        self._ms = await self._gen_ms()

        await self._phone.sip.answer(self._message, self.session_id, self._ms)

        self._phone.hass.loop.call_later(
            2,
            lambda: self._phone.hass.async_create_task(self._re_answer()),
        )

        return True

    async def decline(self) -> bool:
        """Decline call

        :return bool
        """

        if self.state != CallState.RINGING:  # pragma: no cover
            _LOGGER.debug("Call %r is not ringing", self.call_id)

            raise IntercomInvalidStateError(f"Call {self.call_id} is not ringing")

        await self._phone.sip.decline(self._message)

        self.state = CallState.ENDED

        return True

    async def hangup(self) -> bool:
        """Hangup call

        :return bool
        """

        if self.state != CallState.ANSWERED:  # pragma: no cover
            _LOGGER.debug("Call %r is not answered", self.call_id)

            raise IntercomInvalidStateError(f"Call {self.call_id} is not answered")

        await self.stop_rtp()

        await self._phone.sip.hangup(self._message)

        self.state = CallState.ENDED

        await self._phone.clean_call(self.call_id)

        return True

    async def write_audio(self, data: bytes) -> None:  # pragma: no cover
        """Write audio

        :data: bytes
        """

        if self.state != CallState.ANSWERED:  # pragma: no cover
            _LOGGER.debug("Call %r is not answered", self.call_id)

            raise IntercomInvalidStateError(f"Call {self.call_id} is not answered")

        if _client := self.get_audio_client():
            await _client.write(data)

    async def read_audio(
        self, length: int = 160, blocking: bool = True
    ) -> bytes | None:  # pragma: no cover
        """Read audio

        :param length: int
        :param blocking: bool
        :return bytes | None
        """

        if _client := self.get_audio_client():
            return await _client.read(length, blocking)

        return None

    def get_audio_client(self) -> RtpClient | None:  # pragma: no cover
        """Get audio client

        :return RtpClient | None
        """

        return next((client for client in self._clients if client.is_audio), None)

    # TODO: Not yet supported by the manufacturer.
    async def read_dtmf(self, length: int = 1) -> str | None:  # pragma: no cover
        """Read dtmf

        :param length: int
        :return str | None
        """

        async with self._dtmf_lock:
            packet = self._dtmf.read(length)

        return packet or None

    def as_dict(self) -> ReadOnlyDict[str, Any]:
        """As dict

        :return ReadOnlyDict[str, Any]
        """

        return ReadOnlyDict(self.__dict__)
