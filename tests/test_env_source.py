"""Tests for the environment-variable source."""

from __future__ import annotations

from confargs import ArgConfig, collect_options, option
from confargs.env_source import collect_env_values, env_var_name


class Tool(ArgConfig):
    name = "mytool"

    @option(envvar="EXPLICIT_LOG")
    def log(self, value: str = "log.html") -> str:
        return value

    @option
    def console(self, value: str = "verbose") -> str:
        return value

    @option(config=False)
    def no_config(self, value: bool = False) -> bool:
        return value

    @option(config=False, envvar="FORCE_ENV")
    def forced(self, value: str = "") -> str:
        return value


OPTIONS = collect_options(Tool)


def test_explicit_envvar_name() -> None:
    assert env_var_name(OPTIONS["log"], "mytool", auto_env_vars=False) == "EXPLICIT_LOG"


def test_no_envvar_without_auto() -> None:
    assert env_var_name(OPTIONS["console"], "mytool", auto_env_vars=False) is None


def test_auto_envvar_name() -> None:
    assert env_var_name(OPTIONS["console"], "mytool", auto_env_vars=True) == "MYTOOL_CONSOLE"


def test_non_config_excluded_from_auto() -> None:
    assert env_var_name(OPTIONS["no_config"], "mytool", auto_env_vars=True) is None


def test_explicit_envvar_honoured_even_for_non_config() -> None:
    assert env_var_name(OPTIONS["forced"], "mytool", auto_env_vars=True) == "FORCE_ENV"


def test_collect_reads_explicit_and_auto() -> None:
    environ = {"EXPLICIT_LOG": "a.html", "MYTOOL_CONSOLE": "quiet"}
    values = collect_env_values(OPTIONS, "mytool", auto_env_vars=True, environ=environ)
    assert values == {"log": "a.html", "console": "quiet"}


def test_collect_ignores_absent_vars() -> None:
    values = collect_env_values(OPTIONS, "mytool", auto_env_vars=True, environ={})
    assert values == {}


def test_collect_without_auto_only_explicit() -> None:
    environ = {"EXPLICIT_LOG": "a.html", "MYTOOL_CONSOLE": "quiet"}
    values = collect_env_values(OPTIONS, "mytool", auto_env_vars=False, environ=environ)
    assert values == {"log": "a.html"}
