"""Tests for choice validation via ``typing.Literal`` annotations."""

from __future__ import annotations

from typing import Literal

import pytest

import confargs
from confargs import ArgConfig, argument, option
from confargs.exceptions import OptionValueError


def _run(cls: type[ArgConfig], argv: list[str], **kw: object) -> confargs.Namespace:
    return confargs.ConfigurationProcessor(cls, argv=argv, environ={}, **kw).process()


class Choices(ArgConfig):
    """A tool with Literal-constrained options."""

    name = "choices"

    console: Literal["verbose", "dotted", "quiet", "none"] = option(name="console", default="verbose")
    level: Literal[1, 2, 3] = option(name="level", type=Literal[1, 2, 3], default=1)
    langs: list[Literal["en", "pl"]] = option(name="langs", default=list)
    mode: Literal["a", "b"] | None = option(name="mode", default=None)

    @option(name="fmt")
    def fmt(self, value: Literal["json", "yaml"] = "json") -> str:
        """Output format."""
        return value


def test_valid_scalar_choice() -> None:
    assert _run(Choices, ["--console", "dotted"]).console == "dotted"


def test_invalid_scalar_choice_rejected() -> None:
    with pytest.raises(OptionValueError, match="invalid value 'fancy'; choose from"):
        _run(Choices, ["--console", "fancy"])


def test_int_literal_coerced_and_validated() -> None:
    assert _run(Choices, ["--level", "2"]).level == 2
    with pytest.raises(OptionValueError, match="choose from 1, 2, 3"):
        _run(Choices, ["--level", "9"])


def test_list_of_literals() -> None:
    assert _run(Choices, ["--langs", "en", "--langs", "pl"]).langs == ["en", "pl"]
    with pytest.raises(OptionValueError, match="invalid value 'de'"):
        _run(Choices, ["--langs", "de"])


def test_optional_literal_allows_none() -> None:
    assert _run(Choices, []).mode is None
    assert _run(Choices, ["--mode", "a"]).mode == "a"
    with pytest.raises(OptionValueError):
        _run(Choices, ["--mode", "c"])


def test_literal_on_method_parameter() -> None:
    assert _run(Choices, ["--fmt", "yaml"]).fmt == "yaml"
    with pytest.raises(OptionValueError, match="choose from 'json', 'yaml'"):
        _run(Choices, ["--fmt", "xml"])


def test_argument_literal_validated() -> None:
    class Cmd(ArgConfig):
        name = "cmd"
        action: Literal["run", "list"] = argument(name="action")

    assert _run(Cmd, ["run"]).action == "run"
    with pytest.raises(OptionValueError, match="invalid value 'stop'"):
        _run(Cmd, ["stop"])


def test_choices_shown_in_help() -> None:
    from confargs.help import format_help

    text = format_help(Choices())
    assert "{verbose,dotted,quiet,none}" in text


def test_literal_from_toml_config(tmp_path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[tool.choices]\nconsole = "quiet"\n',
        encoding="utf-8",
    )
    assert _run(Choices, [], cwd=tmp_path).console == "quiet"


def test_invalid_literal_from_toml_rejected(tmp_path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[tool.choices]\nconsole = "bogus"\n',
        encoding="utf-8",
    )
    with pytest.raises(OptionValueError, match="invalid value 'bogus'"):
        _run(Choices, [], cwd=tmp_path)
