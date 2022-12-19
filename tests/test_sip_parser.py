"""Tests for the tattelecom_intercom component."""

# pylint: disable=no-member,too-many-statements,protected-access,too-many-lines,line-too-long

from __future__ import annotations

import logging

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import load_fixture

from custom_components.tattelecom_intercom.enum import (
    MessageStatus,
    MessageType,
    RtpProtocol,
    TransmitType,
)
from custom_components.tattelecom_intercom.sip import Message, MessageParser
from tests.setup import MOCK_ADDRESS, MOCK_IP, MOCK_LOCAL_PORT, MOCK_PORT

_LOGGER = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations"""

    yield


@pytest.mark.asyncio
async def test_parser_register(hass: HomeAssistant) -> None:
    """Parser register"""

    message: Message = await MessageParser().parse(
        load_fixture("register_data.txt").encode("utf8")
    )
    assert message.as_dict() == {
        "auth": {},
        "body": {"a": {}, "c": [], "m": []},
        "headers": {
            "Allow": [
                "INVITE",
                "ACK",
                "CANCEL",
                "OPTIONS",
                "BYE",
                "REFER",
                "SUBSCRIBE",
                "NOTIFY",
                "INFO",
                "PUBLISH",
                "MESSAGE",
            ],
            "CSeq": {"check": "21", "method": "REGISTER"},
            "Call-ID": "6b86b273ff",
            "Contact": "<sip:D100000@172.0.0.1:61486;transport=udp>;expires=3600",
            "Content-Length": 0,
            "Date": "Sun, 14 Aug 2022 13:39:18 GMT",
            "Expires": "3600",
            "From": {
                "address": "D100000@217.0.0.1",
                "caller": "",
                "host": MOCK_ADDRESS,
                "number": "D100000",
                "raw": "<sip:D100000@217.0.0.1>",
                "tag": "dd30f82e",
            },
            "Server": "df",
            "Supported": ["replaces", "timer"],
            "To": {
                "address": "D100000@217.0.0.1",
                "caller": "",
                "host": MOCK_ADDRESS,
                "number": "D100000",
                "raw": "sip:D100000@217.0.0.1",
                "tag": "as217d587e",
            },
            "Via": [
                {
                    "address": (MOCK_IP, MOCK_LOCAL_PORT),
                    "branch": "z9hG4bK.aac48cdde",
                    "received": "172.0.0.1",
                    "rport": "61486",
                    "type": "SIP/2.0/UDP",
                }
            ],
        },
        "method": None,
        "status": MessageStatus.OK,
        "type": MessageType.RESPONSE,
        "version": "SIP/2.0",
    }


@pytest.mark.asyncio
async def test_parser_register_unauth(hass: HomeAssistant) -> None:
    """Parser register test"""

    message: Message = await MessageParser().parse(
        load_fixture("register_first_data.txt").encode("utf8")
    )
    assert message.as_dict() == {
        "auth": {"algorithm": "MD5", "nonce": "003af036", "realm": "test-1"},
        "body": {"a": {}, "c": [], "m": []},
        "headers": {
            "Allow": [
                "INVITE",
                "ACK",
                "CANCEL",
                "OPTIONS",
                "BYE",
                "REFER",
                "SUBSCRIBE",
                "NOTIFY",
                "INFO",
                "PUBLISH",
                "MESSAGE",
            ],
            "CSeq": {"check": "20", "method": "REGISTER"},
            "Call-ID": "6b86b273ff",
            "Content-Length": 0,
            "From": {
                "address": "D100000@217.0.0.1",
                "caller": "",
                "host": "217.0.0.1",
                "number": "D100000",
                "raw": "<sip:D100000@217.0.0.1>",
                "tag": "d8b09abe",
            },
            "Server": "df",
            "Supported": ["replaces", "timer"],
            "To": {
                "address": "D100000@217.0.0.1",
                "caller": "",
                "host": "217.0.0.1",
                "number": "D100000",
                "raw": "sip:D100000@217.0.0.1",
                "tag": "as10f64d14",
            },
            "Via": [
                {
                    "address": (MOCK_IP, MOCK_LOCAL_PORT),
                    "branch": "z9hG4bK.cbc43c166",
                    "received": "172.0.0.1",
                    "rport": "61486",
                    "type": "SIP/2.0/UDP",
                }
            ],
            "WWW-Authenticate": {
                "algorithm": "MD5",
                "nonce": "003af036",
                "realm": "test-1",
            },
        },
        "method": None,
        "status": MessageStatus.UNAUTHORIZED,
        "type": MessageType.RESPONSE,
        "version": "SIP/2.0",
    }


@pytest.mark.asyncio
async def test_parser_invite(hass: HomeAssistant) -> None:
    """Parser invite"""

    message: Message = await MessageParser().parse(
        load_fixture("invite_data.txt").encode("utf8")
    )
    assert message.as_dict() == {
        "auth": {},
        "body": {
            "a": {"maxptime": "150", "transmit_type": TransmitType.SENDRECV},
            "b": {"bandwidth": "384", "type": "CT"},
            "c": [
                {
                    "address": MOCK_ADDRESS,
                    "address_count": 1,
                    "address_type": "IP4",
                    "network_type": "IN",
                    "ttl": None,
                }
            ],
            "m": [
                {
                    "attributes": {"101": {}, "8": {}},
                    "methods": ["8", "101"],
                    "port": 40564,
                    "port_count": 1,
                    "protocol": RtpProtocol.AVP,
                    "type": "audio",
                },
                {
                    "attributes": {
                        "99": {
                            "fmtp": {"id": "99", "settings": ["packetization-mode"]},
                            "rtpmap": {
                                "encoding": None,
                                "frequency": "90000",
                                "id": "99",
                                "name": "H264",
                            },
                        }
                    },
                    "methods": ["99"],
                    "port": 40378,
                    "port_count": 1,
                    "protocol": RtpProtocol.AVP,
                    "type": "video",
                },
            ],
            "o": {
                "address": MOCK_ADDRESS,
                "address_type": "IP4",
                "id": "1265828173",
                "network_type": "IN",
                "username": "root",
                "version": "1265828173",
            },
            "s": "Asterisk PBX 16.10.0",
            "t": {"start": "0", "stop": "0"},
            "v": 0,
        },
        "headers": {
            "Allow": [
                "INVITE",
                "ACK",
                "CANCEL",
                "OPTIONS",
                "BYE",
                "REFER",
                "SUBSCRIBE",
                "NOTIFY",
                "INFO",
                "PUBLISH",
                "MESSAGE",
            ],
            "CSeq": {"check": "102", "method": "INVITE"},
            "Call-ID": "42707deb5c366d722cf1ae041d97ac1d@217.0.0.1:9740",
            "Contact": "<sip:G0001@217.0.0.1:9740>",
            "Content-Length": 372,
            "Content-Type": "application/sdp",
            "Date": "Sat, 13 Aug 2022 13:39:28 GMT",
            "From": {
                "address": "G0001@217.0.0.1:9740",
                "caller": 'G0001" ',
                "host": "217.0.0.1:9740",
                "number": "G0001",
                "raw": '"G0001" <sip:G0001@217.0.0.1:9740>',
                "tag": "as79e57a2a",
            },
            "Max-Forwards": "70",
            "Remote-Party-ID": '"G0001" '
            "<sip:G0001@217.0.0.1>;party=calling;privacy=off;screen=no",
            "Supported": ["replaces", "timer"],
            "To": {
                "address": "D100000@172.0.0.1:17702;transport=udp",
                "caller": "",
                "host": "172.0.0.1:17702;transport=udp",
                "number": "D100000",
                "raw": "<sip:D100000@172.0.0.1:17702;transport=udp>",
                "tag": "",
            },
            "User-Agent": "df",
            "Via": [
                {
                    "address": (MOCK_ADDRESS, MOCK_PORT),
                    "branch": "z9hG4bK3383e7bf",
                    "rport": None,
                    "type": "SIP/2.0/UDP",
                }
            ],
        },
        "method": "INVITE",
        "status": None,
        "type": MessageType.MESSAGE,
        "version": "SIP/2.0",
    }


@pytest.mark.asyncio
async def test_parser_ack(hass: HomeAssistant) -> None:
    """Parser ack"""

    message: Message = await MessageParser().parse(
        load_fixture("ack_data.txt").encode("utf8")
    )
    assert message.as_dict() == {
        "auth": {},
        "body": {"a": {}, "c": [], "m": []},
        "headers": {
            "CSeq": {"check": "102", "method": "ACK"},
            "Call-ID": "42707deb5c366d722cf1ae041d97ac1d@217.0.0.1:9740",
            "Contact": "<sip:G0001@217.0.0.1:9740>",
            "Content-Length": 0,
            "From": {
                "address": "G0001@217.0.0.1:9740",
                "caller": 'G0001" ',
                "host": "217.0.0.1:9740",
                "number": "G0001",
                "raw": '"G0001" <sip:G0001@217.0.0.1:9740>',
                "tag": "as79e57a2a",
            },
            "Max-Forwards": "70",
            "To": {
                "address": "D100000@172.0.0.1:17702;transport=udp",
                "caller": "",
                "host": "172.0.0.1:17702;transport=udp",
                "number": "D100000",
                "raw": "<sip:D100000@172.0.0.1:17702;transport=udp>",
                "tag": "Hiv5H8B",
            },
            "User-Agent": "df",
            "Via": [
                {
                    "address": (MOCK_ADDRESS, MOCK_PORT),
                    "branch": "z9hG4bK56591fc7",
                    "rport": None,
                    "type": "SIP/2.0/UDP",
                }
            ],
        },
        "method": "ACK",
        "status": None,
        "type": MessageType.MESSAGE,
        "version": "SIP/2.0",
    }


@pytest.mark.asyncio
async def test_parser_bye(hass: HomeAssistant) -> None:
    """Parser bye"""

    message: Message = await MessageParser().parse(
        load_fixture("bye_data.txt").encode("utf8")
    )
    assert message.as_dict() == {
        "auth": {},
        "body": {"a": {}, "c": [], "m": []},
        "headers": {
            "CSeq": {"check": "103", "method": "BYE"},
            "Call-ID": "42707deb5c366d722cf1ae041d97ac1d@217.0.0.1:9740",
            "Content-Length": 0,
            "From": {
                "address": "G0001@217.0.0.1:9740",
                "caller": 'G0001" ',
                "host": "217.0.0.1:9740",
                "number": "G0001",
                "raw": '"G0001" <sip:G0001@217.0.0.1:9740>',
                "tag": "as15941c76",
            },
            "Max-Forwards": "70",
            "To": {
                "address": "D100000@172.0.0.1:23582;transport=udp",
                "caller": "",
                "host": "172.0.0.1:23582;transport=udp",
                "number": "D100000",
                "raw": "<sip:D100000@172.0.0.1:23582;transport=udp>",
                "tag": "w1wzwTF",
            },
            "User-Agent": "df",
            "Via": [
                {
                    "address": ("217.0.0.1", 9740),
                    "branch": "z9hG4bK6a9c995d",
                    "rport": None,
                    "type": "SIP/2.0/UDP",
                }
            ],
            "X-Asterisk-HangupCause": "Normal Clearing",
            "X-Asterisk-HangupCauseCode": "16",
        },
        "method": "BYE",
        "status": None,
        "type": MessageType.MESSAGE,
        "version": "SIP/2.0",
    }


@pytest.mark.asyncio
async def test_parser_cancel(hass: HomeAssistant) -> None:
    """Parser cancel"""

    message: Message = await MessageParser().parse(
        load_fixture("cancel_data.txt").encode("utf8")
    )
    assert message.as_dict() == {
        "auth": {},
        "body": {"a": {}, "c": [], "m": []},
        "headers": {
            "CSeq": {"check": "102", "method": "CANCEL"},
            "Call-ID": "42707deb5c366d722cf1ae041d97ac1d@217.0.0.1:9740",
            "Content-Length": 0,
            "From": {
                "address": "G0001@217.0.0.1:9740",
                "caller": 'G0001" ',
                "host": "217.0.0.1:9740",
                "number": "G0001",
                "raw": '"G0001" <sip:G0001@217.0.0.1:9740>',
                "tag": "as47d4d103",
            },
            "Max-Forwards": "70",
            "To": {
                "address": "D100000@172.0.0.1:23582;transport=udp",
                "caller": "",
                "host": "172.0.0.1:23582;transport=udp",
                "number": "D100000",
                "raw": "<sip:D100000@172.0.0.1:23582;transport=udp>",
                "tag": "",
            },
            "User-Agent": "df",
            "Via": [
                {
                    "address": ("217.0.0.1", 9740),
                    "branch": "z9hG4bK5b4f3518",
                    "rport": None,
                    "type": "SIP/2.0/UDP",
                }
            ],
        },
        "method": "CANCEL",
        "status": None,
        "type": MessageType.MESSAGE,
        "version": "SIP/2.0",
    }
