"""Tests for the core option model: decorator, Option, name resolution."""

from __future__ import annotations

import pytest

import confargs
from confargs import ArgConfig, Option, collect_options, option, resolve_names
from confargs.exceptions import MISSING, OptionDefinitionError


class Sample(ArgConfig):
    """A sample tool."""

    tool_name = "sample"

    @option
    def log(self, value: str | None = "log.html") -> str | None:
        """HTML log file."""
        return value

    @option(name="console", short="c")
    def console(self, value: str = "verbose") -> str:
        """Console output mode."""
        return value

    @option(config=False, env="SAMPLE_VERBOSE")
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


def test_explicit_name_and_short() -> None:
    console = Sample.__dict__["console"]
    assert console.long_names == ["--console"]
    assert console.explicit_shorts == ["-c"]
    assert console.auto_short is None


def test_explicit_name_opts_out_of_auto_short() -> None:
    class T(ArgConfig):
        @option(name="verbose")
        def verbose(self, value: bool = False) -> bool:
            return value

    opt = T.__dict__["verbose"]
    assert opt.long_names == ["--verbose"]
    assert opt.explicit_shorts == []
    assert opt.auto_short is None


def test_explicit_short_only_keeps_derived_long() -> None:
    class T(ArgConfig):
        @option(short="x")
        def execute(self, value: str = "") -> str:
            return value

    opt = T.__dict__["execute"]
    assert opt.long_names == ["--execute"]
    assert opt.explicit_shorts == ["-x"]
    assert opt.auto_short is None


def test_option_metadata_flags() -> None:
    verbose = Sample.__dict__["verbose"]
    assert verbose.cli is True
    assert verbose.config is False
    assert verbose.env == "SAMPLE_VERBOSE"


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
        @option(name="dup")
        def a(self, value: str = "") -> str:
            return value

        @option(name="dup")
        def b(self, value: str = "") -> str:
            return value

    with pytest.raises(OptionDefinitionError):
        resolve_names(collect_options(T))


def test_invalid_short_name_raises() -> None:
    with pytest.raises(OptionDefinitionError):

        class T(ArgConfig):
            @option(short="too-long")  # short names must be a single character
            def console(self, value: str = "") -> str:
                return value


def test_config_section_defaults_to_tool_name() -> None:
    assert Sample().config_section == ("tool", "sample")


def test_config_section_uses_default_section_override() -> None:
    class T(ArgConfig):
        tool_name = "t"
        default_config_section = "tool.custom.sub"

    assert T().config_section == ("tool", "custom", "sub")


def test_help_option_raises_exit_when_true() -> None:
    with pytest.raises(confargs.Exit) as exc:
        Sample().help(True)
    assert exc.value.code == 0


def test_exit_is_not_an_argconfigerror() -> None:
    # Exit is a clean-exit control-flow signal, so a broad ``except
    # ArgConfigError`` in a host app must not swallow it.
    assert not issubclass(confargs.Exit, confargs.ArgConfigError)
    with pytest.raises(confargs.Exit):
        try:
            raise confargs.Exit(0)
        except confargs.ArgConfigError:  # pragma: no cover - must NOT catch
            pytest.fail("Exit was caught by except ArgConfigError")


class Declared(ArgConfig):
    """A tool using declarative (method-less) options."""

    tool_name = "declared"
    config_names: list[str] = []  # noqa: RUF012

    foo = option(name="foo", help="Foo doc", default="")
    count = option(name="count", default=3)
    verbose = option(name="verbose", short="V", default=False)
    tag = option(name="tag", default=None)


def test_declarative_option_is_an_option() -> None:
    assert isinstance(Declared.__dict__["foo"], Option)
    assert Declared.__dict__["foo"].func is None


def test_declarative_option_derives_name_from_attribute() -> None:
    class T(ArgConfig):
        dry_run = option(help="Dry run.", default=False)

    opt = T.__dict__["dry_run"]
    assert opt.long_names == ["--dry-run"]


def test_declarative_descriptor_returns_identity_on_instance() -> None:
    passthrough = Declared().foo
    assert passthrough("hello") == "hello"


def test_declarative_help_text_used_as_doc() -> None:
    assert Declared.__dict__["foo"].doc == "Foo doc"


def test_declarative_default_and_type_inference() -> None:
    from confargs.coercion import resolve_value_type

    assert Declared.__dict__["count"].default == 3
    assert resolve_value_type(Declared.__dict__["count"]).base is int
    assert resolve_value_type(Declared.__dict__["verbose"]).is_flag is True
    tag_type = resolve_value_type(Declared.__dict__["tag"])
    assert tag_type.base is str
    assert tag_type.allows_none is True


def test_declarative_explicit_type_wins() -> None:
    class T(ArgConfig):
        nums = option(name="nums", type=list[int], default=None)

    from confargs.coercion import resolve_value_type

    vt = resolve_value_type(T.__dict__["nums"])
    assert vt.is_list is True
    assert vt.base is int


def test_declarative_options_process_end_to_end() -> None:
    config = confargs.ConfigurationProcessor(Declared, argv=["--foo", "hi", "--count", "7", "--verbose"]).process()
    assert config.foo == "hi"
    assert config.count == 7
    assert config.verbose is True
    assert config.tag is None


def test_declarative_flag_negation() -> None:
    class T(ArgConfig):
        tool_name = "t"
        config_names: list[str] = []  # noqa: RUF012
        color = option(name="color", short="C", default=True)

    config = confargs.ConfigurationProcessor(T, argv=["--no-color"]).process()
    assert config.color is False


def test_decorator_with_kwargs_binds_method() -> None:
    # ``@option(name=...)`` builds a method-less Option and then binds the
    # decorated method via ``__call__``; the result is still an Option.
    console = Sample.__dict__["console"]
    assert console.func is not None
    assert Sample().console("quiet") == "quiet"


def test_double_binding_raises() -> None:
    def method(self: object, value: str = "") -> str:
        return value

    opt = option(name="x")
    opt(method)
    with pytest.raises(OptionDefinitionError):
        opt(method)
