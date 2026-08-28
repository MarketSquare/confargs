"""Tests for the core option model: decorator, Option, name resolution."""

from __future__ import annotations

import pytest

import confargs
from confargs import ArgConfig, Option, collect_options, option, resolve_names
from confargs.exceptions import MISSING, OptionDefinitionError


class Sample(ArgConfig):
    """A sample tool."""

    name = "sample"

    @option
    def log(self, value: str | None = "log.html") -> str | None:
        """HTML log file."""
        return value

    @option(names="--console/-c")
    def console(self, value: str = "verbose") -> str:
        """Console output mode."""
        return value

    @option(config=False, envvar="SAMPLE_VERBOSE")
    def verbose(self, value: bool = False) -> bool:
        """Be verbose."""
        return value


def test_option_bare_and_called_forms_are_equivalent() -> None:
    assert isinstance(Sample.__dict__["log"], Option)
    assert isinstance(Sample.__dict__["console"], Option)


def test_descriptor_returns_bound_method_on_instance() -> None:
    instance = Sample()
    assert instance.log("x.html") == "x.html"
    assert instance.console("quiet") == "quiet"


def test_descriptor_returns_option_on_class() -> None:
    assert isinstance(Sample.log, Option)  # type: ignore[arg-type]


def test_attr_name_and_derived_long_name() -> None:
    log = Sample.__dict__["log"]
    assert log.attr_name == "log"
    assert log.long_names == ["--log"]
    assert log.auto_short == "-l"


def test_underscore_method_becomes_dashed_long_name() -> None:
    class T(ArgConfig):
        @option
        def dry_run(self, value: bool = False) -> bool:
            return value

    assert T.__dict__["dry_run"].long_names == ["--dry-run"]


def test_explicit_names_parsing() -> None:
    console = Sample.__dict__["console"]
    assert console.long_names == ["--console"]
    assert console.explicit_shorts == ["-c"]
    assert console.auto_short is None


def test_option_metadata_flags() -> None:
    verbose = Sample.__dict__["verbose"]
    assert verbose.cli is True
    assert verbose.config is False
    assert verbose.envvar == "SAMPLE_VERBOSE"


def test_default_and_missing_default() -> None:
    assert Sample.__dict__["log"].default == "log.html"

    class T(ArgConfig):
        @option
        def required(self, value: str) -> str:
            return value

    assert T.__dict__["required"].default is MISSING


def test_collect_options_includes_inherited_help() -> None:
    options = collect_options(Sample)
    assert "help" in options  # inherited from ArgConfig
    assert set(options) >= {"help", "log", "console", "verbose"}


def test_subclass_overrides_base_option() -> None:
    class Overridden(Sample):
        @option
        def log(self, value: str = "override.html") -> str:
            return value

    options = collect_options(Overridden)
    assert options["log"].default == "override.html"


def test_resolve_names_assigns_long_and_short() -> None:
    options = collect_options(Sample)
    table = resolve_names(options)
    assert table.long_to_attr["--log"] == "log"
    assert table.long_to_attr["--console"] == "console"
    assert table.short_to_attr["-c"] == "console"
    assert table.attr_for("--log") == "log"
    assert table.attr_for("-c") == "console"
    assert table.attr_for("positional") is None


def test_cli_false_option_has_no_cli_names() -> None:
    class T(ArgConfig):
        @option(cli=False)
        def secret(self, value: str = "") -> str:
            return value

    table = resolve_names(collect_options(T))
    assert table.attr_for("--secret") is None
    assert table.short_to_attr.get("-s") != "secret"
    assert table.attr_to_names["secret"] == []


def test_resolve_names_skips_short_collision() -> None:
    class T(ArgConfig):
        @option
        def cat(self, value: str = "") -> str:
            return value

        @option
        def car(self, value: str = "") -> str:
            return value

    table = resolve_names(collect_options(T))
    # First option grabs -c; second falls back to -C, then long-only if taken.
    assert table.short_to_attr.get("-c") == "cat"
    assert table.short_to_attr.get("-C") == "car"


def test_resolve_names_long_collision_raises() -> None:
    class T(ArgConfig):
        @option(names="--dup")
        def a(self, value: str = "") -> str:
            return value

        @option(names="--dup")
        def b(self, value: str = "") -> str:
            return value

    with pytest.raises(OptionDefinitionError):
        resolve_names(collect_options(T))


def test_invalid_names_spec_raises() -> None:
    with pytest.raises(OptionDefinitionError):

        class T(ArgConfig):
            @option(names="console")  # missing leading dashes
            def console(self, value: str = "") -> str:
                return value


def test_config_section_defaults_to_tool_name() -> None:
    assert Sample().config_section == ("tool", "sample")


def test_config_section_uses_default_section_override() -> None:
    class T(ArgConfig):
        name = "t"
        default_config_section = "tool.custom.sub"

    assert T().config_section == ("tool", "custom", "sub")


def test_help_option_raises_exit_when_true() -> None:
    with pytest.raises(confargs.Exit) as exc:
        Sample().help(True)
    assert exc.value.code == 0
