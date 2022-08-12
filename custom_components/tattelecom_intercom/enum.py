"""Enums."""

from __future__ import annotations

from enum import Enum


class Method(str, Enum):
    """Method enum"""

    GET = "GET"
    POST = "POST"


class ApiVersion(str, Enum):
    """Api version enum"""

    V1 = "v1"
    V2 = "v2"
