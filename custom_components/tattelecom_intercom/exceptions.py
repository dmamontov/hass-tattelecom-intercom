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
