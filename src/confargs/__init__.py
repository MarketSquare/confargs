"""confargs: declarative CLI parsing that merges CLI, env vars and TOML config.

Declare options as methods on an :class:`ArgConfig` subclass, decorate them with
:func:`option`, then resolve everything with ``ConfigurationProcessor``.
"""

from __future__ import annotations

from confargs.argfile import read_argument_file, split_argument_file
from confargs.arguments import Argument, argument, collect_arguments
from confargs.base import ArgConfig
from confargs.env_source import split_env_args
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
from confargs.profiles import build_profile_overlay, select_profiles

__version__ = "0.5.0"  # x-release-please-version

__all__ = [
    "MISSING",
    "ArgConfig",
    "ArgConfigError",
    "Argument",
    "CliUsageError",
    "ConfigDiscoveryError",
    "ConfigurationProcessor",
    "Exit",
    "Namespace",
    "Option",
    "OptionDefinitionError",
    "OptionValueError",
    "__version__",
    "argument",
    "build_profile_overlay",
    "collect_arguments",
    "collect_options",
    "option",
    "read_argument_file",
    "resolve_names",
    "select_profiles",
    "split_argument_file",
    "split_env_args",
]
