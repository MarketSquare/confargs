"""Tests for positional argument support."""

from __future__ import annotations

import pytest

import confargs
from confargs import ArgConfig, Argument, argument, collect_arguments, option
from confargs.exceptions import OptionDefinitionError, OptionValueError


def _process(cls: type[ArgConfig], argv: list[str], **kwargs: object) -> confargs.Namespace:
    return confargs.ConfigurationProcessor(cls, argv=argv, environ={}, **kwargs).process()


class Basic(ArgConfig):
    """A tool with positional arguments."""

    tool_name = "basic"

    src = argument(name="src", help="Source path.")
    count = argument(name="count", type=int, nargs="?", default=0, help="Optional count.")

    @argument(nargs="*")
    def rest(self, value: list[str]) -> list[str]:
        """Remaining files, upper-cased."""
        return [item.upper() for item in value]


def test_single_argument_assigned_by_position() -> None:
    config = _process(Basic, ["a.py"])
    assert config.src == "a.py"
    assert config.count == 0
    assert config.rest == []


def test_optional_and_variadic_arguments() -> None:
    config = _process(Basic, ["a.py", "3", "b", "c"])
    assert config.src == "a.py"
    assert config.count == 3
    assert config.rest == ["B", "C"]


def test_required_argument_missing_raises() -> None:
    with pytest.raises(OptionValueError, match="argument SRC is required"):
        _process(Basic, [])


def test_options_and_arguments_together() -> None:
    class Mixed(ArgConfig):
        tool_name = "mixed"
        verbose = option(name="verbose", default=False, help="Verbose.")
        path = argument(name="path", help="A path.")

    config = _process(Mixed, ["--verbose", "here"])
    assert config.verbose is True
    assert config.path == "here"


def test_arguments_after_double_dash() -> None:
    config = _process(Basic, ["--", "-weird", "2", "x"])
    assert config.src == "-weird"
    assert config.count == 2
    assert config.rest == ["X"]


def test_unexpected_positionals_raise() -> None:
    class OneArg(ArgConfig):
        tool_name = "onearg"
        only = argument(name="only")

    with pytest.raises(confargs.CliUsageError, match="unexpected argument"):
        _process(OneArg, ["a", "b"])


def test_plus_nargs_requires_at_least_one() -> None:
    class Plus(ArgConfig):
        tool_name = "plus"
        files = argument(name="files", nargs="+", type=str)

    assert _process(Plus, ["a", "b"]).files == ["a", "b"]
    with pytest.raises(OptionValueError, match="argument FILES is required"):
        _process(Plus, [])


def test_argument_from_toml_config(tmp_path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[tool.basic]\nsrc = "from_config.py"\nrest = ["x", "y"]\n',
        encoding="utf-8",
    )
    config = _process(Basic, [], cwd=tmp_path)
    assert config.src == "from_config.py"
    assert config.rest == ["X", "Y"]


def test_cli_positionals_override_config(tmp_path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[tool.basic]\nsrc = "from_config.py"\n',
        encoding="utf-8",
    )
    config = _process(Basic, ["cli.py"], cwd=tmp_path)
    assert config.src == "cli.py"


def test_declarative_argument_coercion() -> None:
    class Nums(ArgConfig):
        tool_name = "nums"
        numbers = argument(name="numbers", nargs="*", type=list[int])

    assert _process(Nums, ["1", "2", "3"]).numbers == [1, 2, 3]


def test_method_argument_can_reject_value() -> None:
    class Guard(ArgConfig):
        tool_name = "guard"

        @argument(name="port")
        def port(self, value: int) -> int:
            if value < 0:
                raise OptionValueError("port must be >= 0")
            return value

    assert _process(Guard, ["8080"]).port == 8080
    with pytest.raises(OptionValueError, match="port must be >= 0"):
        _process(Guard, ["--", "-1"])


def test_variadic_must_be_last() -> None:
    class Bad(ArgConfig):
        tool_name = "bad"
        many = argument(name="many", nargs="*")
        tail = argument(name="tail")

    with pytest.raises(OptionDefinitionError, match="must be the last argument"):
        _process(Bad, ["a"])


def test_invalid_nargs_rejected() -> None:
    with pytest.raises(OptionDefinitionError, match="invalid nargs"):
        argument(name="x", nargs=2)


def test_option_and_argument_with_same_config_name_coexist() -> None:
    class Mix(ArgConfig):
        tool_name = "mix"
        thing = option(name="thing", default="")
        thing_arg = argument(name="thing")  # same config name, different attribute

    config = _process(Mix, ["positional"])
    assert config.thing_arg == "positional"


def test_collect_arguments_returns_in_order() -> None:
    args = collect_arguments(Basic)
    assert list(args) == ["src", "count", "rest"]
    assert all(isinstance(value, Argument) for value in args.values())


def test_argument_appears_in_help() -> None:
    from confargs.help import format_help

    text = format_help(Basic())
    assert "Arguments:" in text
    assert "SRC" in text
    assert "[COUNT]" in text
    assert "REST..." in text


def test_argument_double_bound_method_rejected() -> None:
    def method(self: object, value: str) -> str:
        return value

    arg = argument(name="dup")(method)
    with pytest.raises(OptionDefinitionError, match="already has a method bound"):
        arg(method)


def test_argument_method_without_value_parameter_rejected() -> None:
    class Bad(ArgConfig):
        tool_name = "bad"

        @argument(name="thing")
        def thing(self) -> str:  # type: ignore[empty-body]
            """Missing the value parameter."""

    with pytest.raises(OptionDefinitionError, match="must accept a value parameter"):
        _process(Bad, ["x"])


def test_declarative_argument_has_no_value_parameter() -> None:
    arg = argument(name="thing")
    with pytest.raises(OptionDefinitionError, match="has no value parameter"):
        _ = arg.value_parameter


def test_argument_explicit_metavar_used_in_help() -> None:
    class WithMeta(ArgConfig):
        tool_name = "withmeta"
        src = argument(name="src", metavar="PATH", help="A path.")

    from confargs.help import format_help

    assert "PATH" in format_help(WithMeta())


def test_declarative_argument_doc_from_help() -> None:
    arg = argument(name="thing", help="  A thing.  ")
    assert arg.doc == "A thing."


def test_method_argument_doc_from_docstring() -> None:
    args = collect_arguments(Basic)
    assert args["rest"].doc.startswith("Remaining files")
