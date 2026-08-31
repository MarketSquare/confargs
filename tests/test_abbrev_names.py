"""Tests for unambiguous-prefix abbreviation of long CLI options."""

from __future__ import annotations

from pathlib import Path

import pytest

from confargs import ArgConfig, argument, collect_options, option, resolve_names
from confargs.cli import parse_cli
from confargs.coercion import resolve_value_type
from confargs.exceptions import ArgConfigError, CliUsageError
from confargs.processor import ConfigurationProcessor


class Tool(ArgConfig):
    cli_allow_abbrev = True
    strict_config = False

    removekeywords: list[str] = option(name="removekeywords", short="r", default=list)
    reportbackground: str | None = option(name="reportbackground", default=None)
    dryrun: bool = option(name="dryrun", default=None)  # type: ignore[assignment]
    name: str | None = option(name="name", default=None)
    data: list[str] = argument(name="data", nargs="*")


def _table(cls: type[ArgConfig]):  # type: ignore[no-untyped-def]
    opts = collect_options(cls)
    table = resolve_names(
        opts,
        case_insensitive=getattr(cls, "cli_case_insensitive", False),
        ignore_hyphens=getattr(cls, "cli_ignore_hyphens", False),
        allow_abbrev=getattr(cls, "cli_allow_abbrev", False),
    )
    flags = {a for a, o in opts.items() if resolve_value_type(o).is_flag}
    lists = {a for a, o in opts.items() if resolve_value_type(o).is_list}
    return table, flags, lists


def run_cli(cls: type[ArgConfig], argv: list[str]):  # type: ignore[no-untyped-def]
    table, flags, lists = _table(cls)
    return parse_cli(argv, table, flags, lists)


@pytest.mark.parametrize("spelling", ["--name", "--nam", "--na"])
def test_unambiguous_prefix_resolves(spelling: str) -> None:
    assert run_cli(Tool, [spelling, "Suite"]).values == {"name": "Suite"}


def test_prefix_of_list_option() -> None:
    assert run_cli(Tool, ["--removek", "WUKS"]).values == {"removekeywords": ["WUKS"]}


def test_prefix_equals_syntax() -> None:
    assert run_cli(Tool, ["--removek=WUKS"]).values == {"removekeywords": ["WUKS"]}


def test_prefix_flag_and_negation() -> None:
    assert run_cli(Tool, ["--dry"]).values == {"dryrun": True}
    assert run_cli(Tool, ["--no-dry"]).values == {"dryrun": False}


def test_joined_negation_abbreviates_with_ignore_hyphens() -> None:
    class Runner(ArgConfig):
        cli_allow_abbrev = True
        cli_case_insensitive = True
        cli_ignore_hyphens = True
        statusrc: bool = option(name="statusrc", default=True)

    # ``--nostatusrc`` is the joined negation; abbreviated + case-insensitive
    # forms must reach the same flag (RF uses ``--NoStatus`` / ``--NoStatusRC``).
    assert run_cli(Runner, ["--nostatusrc"]).values == {"statusrc": False}
    assert run_cli(Runner, ["--nostatus"]).values == {"statusrc": False}
    assert run_cli(Runner, ["--NoStatus"]).values == {"statusrc": False}
    assert run_cli(Runner, ["--no-status"]).values == {"statusrc": False}


def test_ambiguous_prefix_raises() -> None:
    # ``--re`` is a prefix of both ``--removekeywords`` and ``--reportbackground``.
    with pytest.raises(CliUsageError) as exc:
        run_cli(Tool, ["--re", "x"])
    message = str(exc.value)
    assert "ambiguous option '--re'" in message
    assert "--removekeywords" in message
    assert "--reportbackground" in message


def test_exact_match_wins_over_longer_option() -> None:
    class ExactWins(ArgConfig):
        cli_allow_abbrev = True
        log: str | None = option(name="log", default=None)
        loglevel: str | None = option(name="loglevel", default=None)

    # ``--log`` is an exact option even though it is a prefix of ``--loglevel``.
    assert run_cli(ExactWins, ["--log", "l.html"]).values == {"log": "l.html"}
    # A prefix that is not itself an exact name is still ambiguous.
    with pytest.raises(CliUsageError):
        run_cli(ExactWins, ["--lo", "x"])


def test_abbreviation_is_opt_in() -> None:
    class Strict(ArgConfig):
        removekeywords: list[str] = option(name="removekeywords", default=list)

    opts = collect_options(Strict)
    table = resolve_names(opts)
    with pytest.raises(CliUsageError, match="unknown option '--removek'"):
        parse_cli(["--removek", "x"], table, set(), {"removekeywords"})


def test_shorts_are_not_abbreviated() -> None:
    table, _flags, _lists = _table(Tool)
    # Abbreviation is a ``--long`` concept: an exact long prefix resolves...
    assert table.long_attr("--removek") == "removekeywords"
    # ...but a single-dash token is a short cluster, never a long abbreviation.
    assert table.abbrev_matches("-remove") == []
    assert table.long_attr("-removek") is None


def test_abbrev_composes_with_case_and_hyphen_leniency() -> None:
    class Lenient(ArgConfig):
        cli_allow_abbrev = True
        cli_case_insensitive = True
        cli_ignore_hyphens = True
        removekeywords: list[str] = option(name="removekeywords", default=list)

    for spelling in ("--removek", "--RemoveK", "--Remove-K", "--REMOVE-KEY"):
        assert run_cli(Lenient, [spelling, "WUKS"]).values == {"removekeywords": ["WUKS"]}


def test_config_keys_are_not_abbreviated(tmp_path: Path) -> None:
    class Configurable(ArgConfig):
        tool_name = "mytool"
        config_names = ["conf.toml"]  # noqa: RUF012
        cli_allow_abbrev = True
        removekeywords: list[str] = option(name="removekeywords", default=list)
        data: list[str] = argument(name="data", nargs="*")

    cfg = tmp_path / "conf.toml"

    # Exact key works from config.
    cfg.write_text('[tool.mytool]\nremovekeywords = ["WUKS"]\n')
    ns = ConfigurationProcessor(Configurable, argv=[], environ={}, cwd=tmp_path).process()
    assert ns.as_dict()["removekeywords"] == ["WUKS"]

    # An abbreviated key is rejected even though the CLI accepts abbreviations.
    cfg.write_text('[tool.mytool]\nremovek = ["WUKS"]\n')
    with pytest.raises(ArgConfigError):
        ConfigurationProcessor(Configurable, argv=[], environ={}, cwd=tmp_path).process()


def test_processor_end_to_end_abbrev() -> None:
    ns = ConfigurationProcessor(
        Tool,
        argv=["--removek", "WUKS", "--dry", "--nam", "Suite", "d1"],
        environ={},
        cwd=Path.cwd(),
    ).process()
    data = ns.as_dict()
    assert data["removekeywords"] == ["WUKS"]
    assert data["dryrun"] is True
    assert data["name"] == "Suite"
    assert data["data"] == ["d1"]
