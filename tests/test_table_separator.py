"""Tests for list options that accept a TOML table via ``table_separator``."""

from __future__ import annotations

from pathlib import Path

import pytest

import confargs
from confargs import ArgConfig, option
from confargs.exceptions import OptionDefinitionError, OptionValueError


class Tool(ArgConfig):
    tool_name = "tool"

    variable: list[str] = option(name="variable", short="v", default=list, table_separator=":")
    include: list[str] = option(name="include", default=list)
    name: str | None = option(name="name", default=None)


def _run(tmp_path: Path, body: str, argv: list[str] | None = None, cls: type[ArgConfig] = Tool) -> confargs.Namespace:
    (tmp_path / "pyproject.toml").write_text(body, encoding="utf-8")
    return confargs.ConfigurationProcessor(cls, argv=argv or [], environ={}, cwd=tmp_path).process()


def test_inline_table_is_flattened(tmp_path: Path) -> None:
    ns = _run(tmp_path, '[tool.tool]\nvariable = { NAME = "Robot", URL = "http://x:1" }\n')
    assert ns.variable == ["NAME:Robot", "URL:http://x:1"]


def test_sub_table_is_flattened(tmp_path: Path) -> None:
    ns = _run(tmp_path, '[tool.tool.variable]\nNAME = "Robot"\n"count: int" = "5"\n')
    assert ns.variable == ["NAME:Robot", "count: int:5"]


def test_table_scalar_values_are_stringified(tmp_path: Path) -> None:
    ns = _run(tmp_path, "[tool.tool.variable]\nN = 5\nF = 1.5\nB = true\n")
    assert ns.variable == ["N:5", "F:1.5", "B:True"]


def test_list_form_still_works(tmp_path: Path) -> None:
    ns = _run(tmp_path, '[tool.tool]\nvariable = ["NAME:Robot"]\n')
    assert ns.variable == ["NAME:Robot"]


def test_cli_overrides_table(tmp_path: Path) -> None:
    ns = _run(tmp_path, '[tool.tool.variable]\nNAME = "Robot"\n', ["-v", "NAME:Cli"])
    assert ns.variable == ["NAME:Cli"]


def test_nested_table_value_rejected(tmp_path: Path) -> None:
    with pytest.raises(
        OptionValueError,
        match=r"Invalid value for option '--variable': Expected a string, number or boolean "
        r"for table entry 'NAME', got list\.",
    ):
        _run(tmp_path, '[tool.tool.variable]\nNAME = ["a"]\n')


def test_table_rejected_for_list_option_without_separator(tmp_path: Path) -> None:
    with pytest.raises(OptionValueError, match=r"Invalid value for option '--include': Expected a list, got a table\."):
        _run(tmp_path, '[tool.tool.include]\nsmoke = "x"\n')


def test_table_inside_list_rejected(tmp_path: Path) -> None:
    with pytest.raises(OptionValueError, match=r"got a table inside the list\."):
        _run(tmp_path, "[tool.tool]\ninclude = [{ a = 1 }]\n")


def test_table_rejected_for_scalar_option(tmp_path: Path) -> None:
    with pytest.raises(
        OptionValueError, match=r"Invalid value for option '--name': Expected a single value, got a table\."
    ):
        _run(tmp_path, '[tool.tool.name]\nfirst = "x"\n')


def test_table_separator_requires_list_option(tmp_path: Path) -> None:
    class Bad(ArgConfig):
        tool_name = "bad"
        name: str | None = option(name="name", default=None, table_separator=":")

    with pytest.raises(OptionDefinitionError, match="table_separator requires a list option"):
        _run(tmp_path, "", cls=Bad)


def test_empty_table_separator_rejected() -> None:
    with pytest.raises(OptionDefinitionError, match="non-empty"):
        option(name="variable", default=list, table_separator="")
