"""confargs: declarative CLI parsing that merges CLI, env vars and TOML config.

Declare options as methods on an :class:`ArgConfig` subclass, decorate them with
:func:`option`, then resolve everything with ``ConfigurationProcessor``.
"""

from __future__ import annotations

from confargs.argfile import read_argument_file, split_argument_file
from confargs.base import ArgConfig
from confargs.exceptions import (
    MISSING,
    ArgConfigError,
    CliUsageError,
    ConfigDiscoveryError,
    Exit,
    OptionDefinitionError,
    OptionValueError,
)
from confargs.namespace import Namespace
from confargs.options import Option, collect_options, option, resolve_names
from confargs.processor import ConfigurationProcessor

__version__ = "0.2.0"  # x-release-please-version

__all__ = [
    "MISSING",
    "ArgConfig",
    "ArgConfigError",
    "CliUsageError",
    "ConfigDiscoveryError",
    "ConfigurationProcessor",
    "Exit",
    "Namespace",
    "Option",
    "OptionDefinitionError",
    "OptionValueError",
    "__version__",
    "collect_options",
    "option",
    "read_argument_file",
    "resolve_names",
    "split_argument_file",
]
