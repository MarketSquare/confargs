"""argconfig: declarative CLI parsing that merges CLI, env vars and TOML config.

Declare options as methods on an :class:`ArgConfig` subclass, decorate them with
:func:`option`, then resolve everything with ``ConfigurationProcessor``.
"""

from __future__ import annotations

from argconfig.base import ArgConfig
from argconfig.exceptions import (
    MISSING,
    ArgConfigError,
    ConfigDiscoveryError,
    Exit,
    OptionDefinitionError,
    OptionValueError,
)
from argconfig.options import Option, collect_options, option, resolve_names

__version__ = "0.1.0"

__all__ = [
    "MISSING",
    "ArgConfig",
    "ArgConfigError",
    "ConfigDiscoveryError",
    "Exit",
    "Option",
    "OptionDefinitionError",
    "OptionValueError",
    "__version__",
    "collect_options",
    "option",
    "resolve_names",
]
