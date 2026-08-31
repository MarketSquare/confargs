"""Tests for lenient (case- and hyphen-insensitive) CLI option matching."""

from __future__ import annotations

from pathlib import Path

import pytest

from confargs import ArgConfig, argument, collect_options, option, resolve_names
from confargs.cli import parse_cli
from confargs.coercion import resolve_value_type
from confargs.exceptions import ArgConfigError, CliUsageError
from confargs.processor import ConfigurationProcessor


class Tool(ArgConfig):
    cli_case_insensitive = True
    cli_ignore_hyphens = True
    strict_config = False

    variablefile: list[str] = option(name="variablefile", default=list)
    statusrc: bool = option(name="statusrc", default=None)  # type: ignore[assignment]
    name: str | None = option(name="name", default=None)
    data: list[str] = argument(name="data", nargs="*")


def _lenient_table(cls: type[ArgConfig]):  # type: ignore[no-untyped-def]
    opts = collect_options(cls)
    table = resolve_names(
        opts,
        case_insensitive=cls.cli_case_insensitive,
        ignore_hyphens=cls.cli_ignore_hyphens,
    )
    flags = {a for a, o in opts.items() if resolve_value_type(o).is_flag}
    lists = {a for a, o in opts.items() if resolve_value_type(o).is_list}
    return table, flags, lists


def run_cli(cls: type[ArgConfig], argv: list[str]):  # type: ignore[no-untyped-def]
    table, flags, lists = _lenient_table(cls)
    return parse_cli(argv, table, flags, lists)


@pytest.mark.parametrize(
    "spelling",
    ["--variablefile", "--variable-file", "--VariableFile", "--VARIABLE-FILE", "--Variable-File"],
)
def test_long_value_option_lenient_spellings(spelling: str) -> None:
    assert run_cli(Tool, [spelling, "v.py"]).values == {"variablefile": ["v.py"]}


def test_lenient_equals_syntax() -> None:
    assert run_cli(Tool, ["--Variable-File=v.py"]).values == {"variablefile": ["v.py"]}


@pytest.mark.parametrize("spelling", ["--no-statusrc", "--nostatusrc", "--No-StatusRc", "--NOSTATUSRC"])
def test_flag_negation_lenient(spelling: str) -> None:
    assert run_cli(Tool, [spelling]).values == {"statusrc": False}


def test_flag_positive_lenient() -> None:
    assert run_cli(Tool, ["--StatusRc"]).values == {"statusrc": True}


def test_lenient_matching_is_opt_in() -> None:
    class Strict(ArgConfig):
        variablefile: list[str] = option(name="variablefile", default=list)

    opts = collect_options(Strict)
    table = resolve_names(opts)
    with pytest.raises(CliUsageError):
        parse_cli(["--variable-file", "x"], table, set(), {"variablefile"})


def test_case_insensitive_only_keeps_hyphens_significant() -> None:
    class CaseOnly(ArgConfig):
        cli_case_insensitive = True
        variablefile: list[str] = option(name="variablefile", default=list)

    table, _flags, lists = _lenient_table(CaseOnly)
    assert parse_cli(["--VariableFile", "x"], table, set(), lists).values == {"variablefile": ["x"]}
    with pytest.raises(CliUsageError):
        parse_cli(["--variable-file", "x"], table, set(), lists)


def test_hyphen_insensitive_only_keeps_case_significant() -> None:
    class HyphenOnly(ArgConfig):
        cli_ignore_hyphens = True
        variablefile: list[str] = option(name="variablefile", default=list)

    table, _flags, lists = _lenient_table(HyphenOnly)
    assert parse_cli(["--variable-file", "x"], table, set(), lists).values == {"variablefile": ["x"]}
    with pytest.raises(CliUsageError):
        parse_cli(["--VariableFile", "x"], table, set(), lists)


def test_ambiguous_normalized_names_keep_exact_only() -> None:
    class Ambiguous(ArgConfig):
        cli_ignore_hyphens = True
        foobar: str | None = option(name="foo-bar", default=None)
        foobar2: str | None = option(name="foobar", default=None)

    opts = collect_options(Ambiguous)
    table = resolve_names(opts, ignore_hyphens=True)
    # Both exact spellings still resolve to their own option...
    assert table.long_attr("--foo-bar") == "foobar"
    assert table.long_attr("--foobar") == "foobar2"
    # ...but the shared normalised form is dropped, so a third spelling is unknown.
    assert table.long_attr("--foo--bar") is None


def test_config_keys_stay_exact_with_lenient_cli(tmp_path: Path) -> None:
    class Configurable(ArgConfig):
        tool_name = "mytool"
        config_names = ["conf.toml"]  # noqa: RUF012
        cli_case_insensitive = True
        cli_ignore_hyphens = True
        variable_file: list[str] = option(name="variable_file", default=list)
        data: list[str] = argument(name="data", nargs="*")

    cfg = tmp_path / "conf.toml"

    # Exact name (underscore) and its dash variant are accepted in config.
    for key in ("variable_file", "variable-file"):
        cfg.write_text(f'[tool.mytool]\n{key} = ["x"]\n')
        ns = ConfigurationProcessor(Configurable, argv=[], environ={}, cwd=tmp_path).process()
        assert ns.as_dict()["variable_file"] == ["x"]

    # A case-variant is NOT accepted in config even though the CLI is lenient.
    cfg.write_text('[tool.mytool]\nVariableFile = ["x"]\n')
    with pytest.raises(ArgConfigError):
        ConfigurationProcessor(Configurable, argv=[], environ={}, cwd=tmp_path).process()


def test_processor_end_to_end_lenient() -> None:
    ns = ConfigurationProcessor(
        Tool,
        argv=["--Variable-File", "a.py", "--no-statusrc", "--NAME", "Suite", "d1", "d2"],
        environ={},
        cwd=Path.cwd(),
    ).process()
    data = ns.as_dict()
    assert data["variablefile"] == ["a.py"]
    assert data["statusrc"] is False
    assert data["name"] == "Suite"
    assert data["data"] == ["d1", "d2"]
