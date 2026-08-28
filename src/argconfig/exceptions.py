"""Exceptions and sentinels used across argconfig."""

from __future__ import annotations

from typing import Any


class _Missing:
    """Sentinel for "no value supplied" (distinct from ``None``)."""

    _instance: _Missing | None = None

    def __new__(cls) -> _Missing:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "MISSING"

    def __bool__(self) -> bool:
        return False


MISSING: Any = _Missing()
"""Singleton sentinel meaning "this source did not provide a value"."""


class ArgConfigError(Exception):
    """Base class for every error raised by argconfig."""


class OptionDefinitionError(ArgConfigError):
    """Raised when an option/config class is defined incorrectly.

    This signals a *programming* error in the tool that uses argconfig (for
    example, two options claiming the same name), not bad user input.
    """


class OptionValueError(ArgConfigError):
    """Raised when a supplied option value is invalid.

    Tool authors raise this from their option methods to reject a value; the
    processor turns it into a friendly command-line error.
    """


class ConfigDiscoveryError(ArgConfigError):
    """Raised when configuration files cannot be read or parsed."""


class Exit(ArgConfigError):
    """Raised to stop processing and exit (e.g. after printing ``--help``)."""

    def __init__(self, code: int = 0) -> None:
        super().__init__(f"exit with code {code}")
        self.code = code
