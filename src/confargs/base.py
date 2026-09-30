"""The :class:`ArgConfig` base class that tool authors subclass."""

from __future__ import annotations

from typing import Literal

from confargs.exceptions import Exit
from confargs.options import option

_Shell = Literal["bash", "zsh", "fish", "powershell", "pwsh"]


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
        top_level_config_names: Config file names dedicated to this tool (e.g.
            ``["mytool.toml"]``). When such a file has no config section, its
            top-level keys are read instead (``[tool.*]`` tables are skipped),
            like ``ruff.toml``. The section still wins when present; having
            both is an error. Files passed with ``--config`` or via ``extends``
            may also use the top level, unless their name is one of the other
            ``config_names`` (such as ``pyproject.toml``). Empty by default.
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
            always case-sensitive, regardless of this setting.
        ignore_hyphens: When true, hyphens in long option names are ignored on
            the command line (``--variable-file`` resolves to
            ``--variablefile``, and ``--nostatusrc`` negates ``--statusrc``),
            and both hyphens and underscores are ignored in config-file keys
            (``variable-file`` / ``variable_file``). Disabled by default.
        cli_allow_abbrev: When true, an unambiguous prefix of a long option
            name is accepted on the command line (``--rem`` resolves to
            ``--removekeywords``). An exact match always wins over a prefix, and
            an ambiguous prefix raises an error. Composes with the case- and
            hyphen-insensitive settings. Disabled by default. Short options are
            never abbreviated, and config-file keys are never abbreviated.
    """

    tool_name: str | None = None
    config_names: list[str] = ["pyproject.toml"]  # noqa: RUF012 - documented, per-subclass override
    default_config_section: str | None = None
    top_level_config_names: list[str] = []  # noqa: RUF012 - documented, per-subclass override
    env_var_template: str = "{name}_{option}"
    options_env_var: str | None = None
    strict_config: bool = True
    cli_case_insensitive: bool = False
    ignore_hyphens: bool = False
    cli_allow_abbrev: bool = False

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

    @option(name="show-completion", config=False)
    def show_completion(self, value: _Shell | None = None) -> _Shell | None:
        """Print the shell completion script for the given shell and exit."""
        if value is None:
            return value
        from confargs.completion import prog_name, render_source

        print(render_source(value, prog_name()))
        raise Exit(0)

    @option(name="install-completion", config=False)
    def install_completion(self, value: _Shell | None = None) -> _Shell | None:
        """Install shell completion for the given shell and exit."""
        if value is None:
            return value
        from confargs.completion import install_completion as _install
        from confargs.completion import prog_name

        print(_install(value, prog_name()))
        raise Exit(0)

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
