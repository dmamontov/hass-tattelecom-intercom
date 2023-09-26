"""Enums."""

# pylint: disable=invalid-name

from __future__ import annotations

from enum import Enum, IntEnum

from homeassistant.backports.enum import StrEnum

from custom_components.tattelecom_intercom.const import DOMAIN


class DeviceClass(StrEnum):
    """DeviceClass enum"""

    SIP_STATE = f"{DOMAIN}__sip_state"
    CALL_STATE = f"{DOMAIN}__call_state"


class Method(StrEnum):
    """Method enum"""

    GET = "GET"
    POST = "POST"


class ApiVersion(StrEnum):
    """Api version enum"""

    V1 = "v1"
    V2 = "v2"


class CallState(StrEnum):
    """Call state enum"""

    DIALING = "dialing"
    RINGING = "ringing"
    ANSWERED = "answered"
    ENDED = "ended"


class VoipState(StrEnum):
    """Voip state enum"""

    INACTIVE = "inactive"
    REGISTERING = "registering"
    REGISTERED = "registered"
    DEREGISTERING = "deregistering"
    FAILED = "failed"


class MessageType(IntEnum):
    """SIP message type"""

    def __new__(cls, value: int):
        obj = int.__new__(cls, value)  # type: ignore
        obj._value_ = value

        return obj

    MESSAGE = 1
    RESPONSE = 0


class RtpProtocol(StrEnum):
    """Rtp protocol"""

    UDP = "udp"
    AVP = "RTP/AVP"
    SAVP = "RTP/SAVP"


class SendMode(StrEnum):
    """Send mode"""

    RECV_ONLY = "recvonly"
    SEND_RECV = "sendrecv"
    SEND_ONLY = "sendonly"
    INACTIVE = "inactive"


class RtpPayloadType(Enum):
    """Rtp payload type"""

    _rate: int
    _channel: int
    _description: str

    def __new__(
        cls, value: int | str, clock: int = 0, channel: int = 0, description: str = ""
    ) -> RtpPayloadType:
        obj = object.__new__(cls)  # type: ignore

        obj._value_ = value  # type: ignore
        obj.rate = clock  # type: ignore
        obj.channel = channel  # type: ignore
        obj.description = description  # type: ignore

        return obj

    @property
    def rate(self) -> int:
        """Property rate getter

        :return int
        """

        return self._rate

    @rate.setter
    def rate(self, value: int) -> None:
        """Property rate setter

        :param value: int
        """

        self._rate = value

    @property
    def channel(self) -> int:
        """Property channel getter

        :return int
        """

        return self._channel

    @channel.setter
    def channel(self, value: int) -> None:
        """Property channel setter

        :param value: int
        """

        self._channel = value

    @property
    def description(self) -> str:
        """Property channel description

        :return str
        """

        return self._description

    @description.setter
    def description(self, value: str) -> None:
        """Property channel setter

        :param value: str
        """

        self._description = value

    def __int__(self) -> int:
        """Cast to int

        :return int
        """

        try:
            return int(self.value)
        except ValueError:
            return 0

    def __str__(self) -> str:
        """Cast to str

        :return str
        """

        return self.description if isinstance(self.value, int) else str(self.value)

    PCMU = 0, 8000, 1, "PCMU"
    GSM = 3, 8000, 1, "GSM"
    G723 = 4, 8000, 1, "G723"
    DVI4_8000 = 5, 8000, 1, "DVI4"
    DVI4_16000 = 6, 16000, 1, "DVI4"
    LPC = 7, 8000, 1, "LPC"
    PCMA = 8, 8000, 1, "PCMA"
    G722 = 9, 8000, 1, "G722"
    L16_2 = 10, 44100, 2, "L16"
    L16 = 11, 44100, 1, "L16"
    QCELP = 12, 8000, 1, "QCELP"
    CN = 13, 8000, 1, "CN"
    MPA = 14, 90000, 0, "MPA"
    G728 = 15, 8000, 1, "G728"
    DVI4_11025 = 16, 11025, 1, "DVI4"
    DVI4_22050 = 17, 22050, 1, "DVI4"
    G729 = 18, 8000, 1, "G729"
    CELB = 25, 90000, 0, "CelB"
    JPEG = 26, 90000, 0, "JPEG"
    NV = 28, 90000, 0, "nv"
    H261 = 31, 90000, 0, "H261"
    MPV = 32, 90000, 0, "MPV"
    MP2T = 33, 90000, 1, "MP2T"
    H263 = 34, 90000, 0, "H263"
    H264 = 99, 90000, 0, "H264"
    EVENT = 101, 8000, 0, "telephone-event"
    UNKNOWN = "UNKNOWN", 0, 0, "UNKNOWN CODEC"


class TransmitType(StrEnum):
    """Rtp transmit type"""

    RECVONLY = "recvonly"
    SENDRECV = "sendrecv"
    SENDONLY = "sendonly"
    INACTIVE = "inactive"


class MessageStatus(Enum):
    """Sip message status"""

    _phrase: str
    _description: str

    def __new__(
        cls, value: int, phrase: str = "", description: str = ""
    ) -> MessageStatus:
        """New

        :param value: int
        :param phrase: str
        :param description: str
        """

        obj = object.__new__(cls)  # type: ignore
        obj._value_ = value

        obj.phrase = phrase  # type: ignore
        obj.description = description  # type: ignore

        return obj

    def __int__(self) -> int:
        """Cast int

        :return int
        """

        return self._value_

    def __str__(self) -> str:
        """Cast string

        :return str
        """

        return f"{self._value_} {self.phrase}"

    @property
    def phrase(self) -> str:
        """Get phrase

        :return str
        """

        return self._phrase

    @phrase.setter
    def phrase(self, value: str) -> None:
        """Set phrase

        :param value: str
        """

        self._phrase = value

    @property
    def description(self) -> str:
        """Get description

        :return str
        """

        return self._description

    @description.setter
    def description(self, value: str) -> None:
        """Set description

        :param value: str
        """

        self._description = value

    TRYING = (
        100,
        "Trying",
        "Extended search being performed, may take a significant time",
    )
    RINGING = (
        180,
        "Ringing",
        "Destination user agent received INVITE, and is alerting user of call",
    )
    FORWARDED = 181, "Call is Being Forwarded"
    QUEUED = 182, "Queued"
    SESSION_PROGRESS = 183, "Session Progress"
    TERMINATED = 199, "Early Dialog Terminated"
    OK = 200, "Ok", "Request successful"
    ACCEPTED = (202, "Accepted", "Request accepted, processing continues (Deprecated.)")
    NO_NOTIFICATION = (204, "No Notification", "Request fulfilled, nothing follows")
    MULTIPLE_CHOICES = (
        300,
        "Multiple Choices",
        "Object has several resources -- see URI list",
    )
    MOVED_PERMANENTLY = (
        301,
        "Moved Permanently",
        "Object moved permanently -- see URI list",
    )
    MOVED_TEMPORARILY = (
        302,
        "Moved Temporarily",
        "Object moved temporarily -- see URI list",
    )
    USE_PROXY = (
        305,
        "Use Proxy",
        "You must use proxy specified in Location to access this resource",
    )
    ALTERNATE_SERVICE = (
        380,
        "Alternate Service",
        "The call failed, but alternatives are available -- see URI list",
    )
    BAD_REQUEST = (400, "Bad Request", "Bad request syntax or unsupported method")
    UNAUTHORIZED = (401, "Unauthorized", "No permission -- see authorization schemes")
    PAYMENT_REQUIRED = (402, "Payment Required", "No payment -- see charging schemes")
    FORBIDDEN = (403, "Forbidden", "Request forbidden -- authorization will not help")
    NOT_FOUND = (404, "Not Found", "Nothing matches the given URI")
    METHOD_NOT_ALLOWED = (
        405,
        "Method Not Allowed",
        "Specified method is invalid for this resource",
    )
    NOT_ACCEPTABLE = (406, "Not Acceptable", "URI not available in preferred format")
    PROXY_AUTHENTICATION_REQUIRED = (
        407,
        "Proxy Authentication Required",
        "You must authenticate with this proxy before proceeding",
    )
    REQUEST_TIMEOUT = (408, "Request Timeout", "Request timed out; try again later")
    CONFLICT = 409, "Conflict", "Request conflict"
    GONE = (410, "Gone", "URI no longer exists and has been permanently removed")
    LENGTH_REQUIRED = (411, "Length Required", "Client must specify Content-Length")
    CONDITIONAL_REQUEST_FAILED = 412, "Conditional Request Failed"
    REQUEST_ENTITY_TOO_LARGE = (413, "Request Entity Too Large", "Entity is too large")
    REQUEST_URI_TOO_LONG = 414, "Request-URI Too Long", "URI is too long"
    UNSUPPORTED_MEDIA_TYPE = (
        415,
        "Unsupported Media Type",
        "Entity body in unsupported format",
    )
    UNSUPPORTED_URI_SCHEME = (416, "Unsupported URI Scheme", "Cannot satisfy request")
    UNKOWN_RESOURCE_PRIORITY = (
        417,
        "Unkown Resource-Priority",
        "There was a resource-priority option tag, but no Resource-Priority header",
    )
    BAD_EXTENSION = (
        420,
        "Bad Extension",
        "Bad SIP Protocol Extension used, not understood by the server.",
    )
    EXTENSION_REQUIRED = (
        421,
        "Extension Required",
        "Server requeires a specific extension to be listed in the Supported header.",
    )
    SESSION_INTERVAL_TOO_SMALL = 422, "Session Interval Too Small"
    SESSION_INTERVAL_TOO_BRIEF = 423, "Session Interval Too Breif"
    BAD_LOCATION_INFORMATION = 424, "Bad Location Information"
    USE_IDENTITY_HEADER = (
        428,
        "Use Identity Header",
        "The server requires an Identity header, and one has not been provided.",
    )
    PROVIDE_REFERRER_IDENTITY = 429, "Provide Referrer Identity"
    """
    This response is intended for use between proxy devices,
    and should not be seen by an endpoint. If it is seen by one,
    it should be treated as a 400 Bad Request response.
    """
    FLOW_FAILED = (
        430,
        "Flow Failed",
        "A specific flow to a user agent has failed, although other flows may succeed.",
    )
    ANONYMITY_DISALLOWED = 433, "Anonymity Disallowed"
    BAD_IDENTITY_INFO = 436, "Bad Identity-Info"
    UNSUPPORTED_CERTIFICATE = 437, "Unsupported Certificate"
    INVALID_IDENTITY_HEADER = 438, "Invalid Identity Header"
    FIRST_HOP_LACKS_OUTBOUND_SUPPORT = 439, "First Hop Lacks Outbound Support"
    MAX_BREADTH_EXCEEDED = 440, "Max-Breadth Exceeded"
    BAD_INFO_PACKAGE = 469, "Bad info package"
    CONSENT_NEEDED = 470, "Consent Needed"
    TEMPORARILY_UNAVAILABLE = 480, "Temporarily Unavailable"
    CALL_OR_TRANSACTION_DOESNT_EXIST = 481, "Call/Transaction Does Not Exist"
    LOOP_DETECTED = 482, "Loop Detected"
    TOO_MANY_HOPS = 483, "Too Many Hops"
    ADDRESS_INCOMPLETE = 484, "Address Incomplete"
    AMBIGUOUS = 485, "Ambiguous"
    BUSY_HERE = 486, "Busy Here", "Callee is busy"
    REQUEST_TERMINATED = 487, "Request terminated"
    NOT_ACCEPTABLE_HERE = 488, "Not Acceptable Here"
    BAD_EVENT = 489, "Bad Event"
    REQUEST_PENDING = 491, "Request Pending"
    UNDECIPHERABLE = 493, "Undecipherable"
    SECURITY_AGREEMENT_REQUIRED = 494, "Security Agreement Required"
    INTERNAL_SERVER_ERROR = (
        500,
        "Internal Server Error",
        "Server got itself in trouble",
    )
    NOT_IMPLEMENTED = (501, "Not Implemented", "Server does not support this operation")
    BAD_GATEWAY = (502, "Bad Gateway", "Invalid responses from another server/proxy")
    SERVICE_UNAVAILABLE = (
        503,
        "Service unavailable",
        "The server cannot process the request due to a high load",
    )
    GATEWAY_TIMEOUT = (
        504,
        "Server Timeout",
        "The server did not receive a timely response",
    )
    SIP_VERSION_NOT_SUPPORTED = (
        505,
        "SIP Version Not Supported",
        "Cannot fulfill request",
    )
    MESSAGE_TOO_LONG = 513, "Message Too Long"
    PUSH_NOTIFICATION_SERVICE_NOT_SUPPORTED = (
        555,
        "Push Notification Service Not Supported",
    )
    PRECONDITION_FAILURE = 580, "Precondition Failure"
    BUSY_EVERYWHERE = 600, "Busy Everywhere"
    DECLINE = 603, "Decline"
    DOES_NOT_EXIST_ANYWHERE = 604, "Does Not Exist Anywhere"
    GLOBAL_NOT_ACCEPTABLE = 606, "Not Acceptable"
    UNWANTED = 607, "Unwanted"
    REJECTED = 608, "Rejected"
