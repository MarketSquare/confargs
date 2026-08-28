"""Environment-variable configuration source.

Each option can read from an environment variable in one of two ways:

* explicitly, via ``@option(envvar="MY_TOOL_LOG")``, or
* implicitly, when the config class sets ``auto_env_vars = True``, in which case
  every non-``cli_only`` option gets an implicit variable named
  ``<TOOL_NAME>_<OPTION>`` (upper-cased).

An explicit ``envvar`` always wins over the auto-generated name.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

    from confargs.options import Option


def env_var_name(
    option: Option,
    tool_name: str,
    *,
    auto_env_vars: bool,
) -> str | None:
    """Return the environment variable name for ``option``, or ``None``."""
    if option.envvar:
        return option.envvar
    if auto_env_vars and not option.cli_only:
        return f"{tool_name.upper()}_{option.attr_name.upper()}"
    return None


def collect_env_values(
    options: Mapping[str, Option],
    tool_name: str,
    *,
    auto_env_vars: bool,
    environ: Mapping[str, str],
) -> dict[str, str]:
    """Collect raw option values present in ``environ``."""
    values: dict[str, str] = {}
    for attr, option in options.items():
        name = env_var_name(option, tool_name, auto_env_vars=auto_env_vars)
        if name is not None and name in environ:
            values[attr] = environ[name]
    return values
