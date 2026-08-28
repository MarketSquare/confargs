"""Tests for the environment-variable source."""

from __future__ import annotations

from confargs import ArgConfig, collect_options, option
from confargs.env_source import collect_env_values, env_var_name


class Tool(ArgConfig):
    name = "mytool"

    @option(env="EXPLICIT_LOG")
    def log(self, value: str = "log.html") -> str:
        return value

    @option(env=True)
    def console(self, value: str = "verbose") -> str:
        return value

    @option
    def quiet(self, value: bool = False) -> bool:
        return value

    @option(config=False, env="FORCE_ENV")
    def forced(self, value: str = "") -> str:
        return value


OPTIONS = collect_options(Tool)


def test_explicit_env_name_used_verbatim() -> None:
    assert env_var_name(OPTIONS["log"], "mytool") == "EXPLICIT_LOG"


def test_no_env_when_not_opted_in() -> None:
    assert env_var_name(OPTIONS["quiet"], "mytool") is None


def test_auto_env_name_from_template() -> None:
    assert env_var_name(OPTIONS["console"], "mytool") == "MYTOOL_CONSOLE"


def test_custom_template() -> None:
    assert env_var_name(OPTIONS["console"], "mytool", template="cfg_{name}__{option}") == "CFG_MYTOOL__CONSOLE"


def test_env_works_regardless_of_config_toggle() -> None:
    assert env_var_name(OPTIONS["forced"], "mytool") == "FORCE_ENV"


def test_collect_reads_explicit_and_auto() -> None:
    environ = {"EXPLICIT_LOG": "a.html", "MYTOOL_CONSOLE": "quiet"}
    values = collect_env_values(OPTIONS, "mytool", environ=environ)
    assert values == {"log": "a.html", "console": "quiet"}


def test_collect_ignores_absent_vars() -> None:
    values = collect_env_values(OPTIONS, "mytool", environ={})
    assert values == {}


def test_collect_ignores_options_not_opted_in() -> None:
    environ = {"MYTOOL_QUIET": "true"}
    values = collect_env_values(OPTIONS, "mytool", environ=environ)
    assert values == {}
