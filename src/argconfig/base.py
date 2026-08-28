"""The :class:`ArgConfig` base class that tool authors subclass."""

from __future__ import annotations

from argconfig.exceptions import Exit
from argconfig.options import option


class ArgConfig:
    """Base class for a tool's configuration.

    Subclass this and declare options as methods decorated with
    :func:`argconfig.option`. Class attributes configure discovery and naming:

    Attributes:
        name: The tool name. Used for the default TOML section
            (``[tool.<name>]``) and, when ``auto_env_vars`` is enabled, for the
            environment variable prefix.
        config_names: File names to look for when discovering TOML config,
            in priority order.
        default_config_section: Dotted path of the TOML table to read
            (e.g. ``"tool.mytool"``). When unset, ``tool.<name>`` is used.
        auto_env_vars: When true, every option (that is not ``cli_only``) gets
            an implicit environment variable named ``<NAME>_<OPTION>``.
    """

    name: str | None = None
    config_names: list[str] = ["pyproject.toml"]  # noqa: RUF012 - documented, per-subclass override
    default_config_section: str | None = None
    auto_env_vars: bool = False

    @option(names="--help/-h", cli_only=True)
    def help(self, value: bool = False) -> bool:
        """Show this help message and exit."""
        if value:
            print(self.__doc__ or "")
            raise Exit(0)
        return value

    @option(names="--config", cli_only=True)
    def config(self, value: str | None = None) -> str | None:
        """Read configuration from this file only, skipping discovery."""
        return value

    @option(names="--no-config", cli_only=True)
    def no_config(self, value: bool = False) -> bool:
        """Do not read any configuration file."""
        return value

    @option(names="--ignore-git", cli_only=True)
    def ignore_git(self, value: bool = False) -> bool:
        """Keep searching for config files above the project's .git directory."""
        return value

    @property
    def config_section(self) -> tuple[str, ...]:
        """The TOML table path to read configuration from."""
        if self.default_config_section:
            return tuple(self.default_config_section.split("."))
        base = self.name or type(self).__name__.lower()
        return ("tool", base)

    @property
    def tool_name(self) -> str:
        """A non-optional tool name, falling back to the class name."""
        return self.name or type(self).__name__.lower()
