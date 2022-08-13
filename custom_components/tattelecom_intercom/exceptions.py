"""Tattelecom intercom API client exceptions."""


class IntercomError(BaseException):
    """Intercom error"""


class IntercomConnectionError(IntercomError):
    """Intercom connection error"""


class IntercomRequestError(IntercomError):
    """Intercom request error"""


class IntercomNotFoundError(IntercomError):
    """Intercom not found error"""


class IntercomUnauthorizedError(IntercomError):
    """Intercom unauthorized error"""


class IntercomInvalidRangeError(IntercomError):
    """Intercom invalid range error"""


class IntercomInvalidStateError(IntercomError):
    """Intercom invalid state error"""


class IntercomInvalidAccountInfoError(IntercomError):
    """Intercom invalid account info error"""


class IntercomSipParseError(IntercomError):
    """Intercom sip parse error"""


class IntercomSipAlreadyStartedError(IntercomError):
    """Intercom sip already started error"""


class IntercomSipTimeoutError(IntercomError):
    """Intercom timeout error"""
