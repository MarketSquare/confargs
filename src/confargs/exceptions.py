"""Exceptions and sentinels used across confargs."""

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
    """Base class for every error raised by confargs."""


class OptionDefinitionError(ArgConfigError):
    """Raised when an option/config class is defined incorrectly.

    This signals a *programming* error in the tool that uses confargs (for
    example, two options claiming the same name), not bad user input.
    """


class OptionValueError(ArgConfigError):
    """Raised when a supplied option value is invalid.

    Tool authors raise this from their option methods to reject a value; the
    processor turns it into a friendly command-line error.
    """


class ConfigDiscoveryError(ArgConfigError):
    """Raised when configuration files cannot be read or parsed."""


class CliUsageError(ArgConfigError):
    """Raised for malformed command-line input (unknown or incomplete options)."""


class Exit(Exception):
    """Raised to stop processing and exit cleanly (e.g. after printing ``--help``).

    This is intentionally **not** a subclass of :class:`ArgConfigError`. It
    signals a *successful* early exit (``--help``, ``--show-completion``,
    ``--install-completion`` ...), not a failure, so a host application's broad
    ``except ArgConfigError`` cannot accidentally swallow it and report it as an
    error. Catch it explicitly and use its :attr:`code`::

        try:
            config = ConfigurationProcessor(MyArgs, argv=argv).process()
        except Exit as exit_signal:
            return exit_signal.code
        except ArgConfigError as error:
            print(f"error: {error}")
            return 2
    """

    def __init__(self, code: int = 0) -> None:
        super().__init__(f"exit with code {code}")
        self.code = code
