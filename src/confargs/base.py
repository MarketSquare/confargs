"""The :class:`ArgConfig` base class that tool authors subclass."""

from __future__ import annotations

from confargs.exceptions import Exit
from confargs.options import option


class ArgConfig:
    """Base class for a tool's configuration.

    Subclass this and declare options as methods decorated with
    :func:`confargs.option`. Class attributes configure discovery and naming:

    Attributes:
        tool_name: The tool name. Used for the default TOML section
            (``[tool.<tool_name>]``) and, for options declared with
            ``env=True``, as the ``{name}`` part of the environment variable
            name.
        config_names: File names to look for when discovering TOML config,
            in priority order.
        default_config_section: Dotted path of the TOML table to read
            (e.g. ``"tool.mytool"``). When unset, ``tool.<tool_name>`` is used.
        env_var_template: Template used to build the environment variable name
            for options declared with ``env=True``. Formatted with ``name``
            (the tool name) and ``option`` (the attribute name), then
            upper-cased. Defaults to ``"{name}_{option}"``.
        options_env_var: Name of an environment variable holding extra
            command-line arguments (in the style of ``ROBOT_OPTIONS`` /
            ``PYTEST_ADDOPTS``). When set and present in the environment, its
            value is split with shell-like quoting and prepended to ``argv``, so
            real command-line arguments still take precedence. ``None`` (the
            default) disables the feature.
        strict_config: When true (the default), unknown keys or options declared
            with ``config=False`` found in a TOML config section raise an error
            instead of being ignored.
        cli_case_insensitive: When true, long options are matched
            case-insensitively on the command line (``--VariableFile`` resolves
            to ``--variablefile``). Disabled by default. Config-file keys are
            always matched exactly, regardless of this setting.
        cli_ignore_hyphens: When true, hyphens in long option names are ignored
            on the command line (``--variable-file`` resolves to
            ``--variablefile``, and ``--nostatusrc`` negates ``--statusrc``).
            Disabled by default. Config-file keys are always matched exactly.
    """

    tool_name: str | None = None
    config_names: list[str] = ["pyproject.toml"]  # noqa: RUF012 - documented, per-subclass override
    default_config_section: str | None = None
    env_var_template: str = "{name}_{option}"
    options_env_var: str | None = None
    strict_config: bool = True
    cli_case_insensitive: bool = False
    cli_ignore_hyphens: bool = False

    @option(name="help", short="h", config=False)
    def help(self, value: bool = False) -> bool:
        """Show this help message and exit."""
        if value:
            from confargs.help import format_help

            print(format_help(self))
            raise Exit(0)
        return value

    @option(name="config", config=False)
    def config(self, value: str | None = None) -> str | None:
        """Read configuration from this file only, skipping discovery."""
        return value

    @option(name="no-config", config=False)
    def no_config(self, value: bool = False) -> bool:
        """Do not read any configuration file."""
        return value

    @option(name="ignore-git", config=False)
    def ignore_git(self, value: bool = False) -> bool:
        """Keep searching for config files above the project's .git directory."""
        return value

    @option(name="profile", config=False)
    def profile(self, value: list[str] | None = None) -> list[str]:
        """Activate one or more configuration profiles (glob patterns allowed)."""
        return value or []

    @property
    def config_section(self) -> tuple[str, ...]:
        """The TOML table path to read configuration from."""
        if self.default_config_section:
            return tuple(self.default_config_section.split("."))
        base = self.resolved_tool_name
        return ("tool", base)

    @property
    def resolved_tool_name(self) -> str:
        """A non-optional tool name, falling back to the class name."""
        return self.tool_name or type(self).__name__.lower()
