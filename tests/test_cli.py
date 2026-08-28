"""Tests for the command-line tokenizer."""

from __future__ import annotations

import pytest

from argconfig import ArgConfig, collect_options, option, resolve_names
from argconfig.cli import parse_cli
from argconfig.coercion import resolve_value_type
from argconfig.exceptions import CliUsageError


class Tool(ArgConfig):
    @option
    def log(self, value: str | None = "log.html") -> str | None:
        return value

    @option(names="--console/-c")
    def console(self, value: str = "verbose") -> str:
        return value

    @option
    def verbose(self, value: bool = False) -> bool:
        return value

    @option
    def tag(self, value: list[str] | None = None) -> list[str] | None:
        return value


OPTIONS = collect_options(Tool)
TABLE = resolve_names(OPTIONS)
FLAGS = {attr for attr, opt in OPTIONS.items() if resolve_value_type(opt).is_flag}
LISTS = {attr for attr, opt in OPTIONS.items() if resolve_value_type(opt).is_list}


def run(argv: list[str]):  # type: ignore[no-untyped-def]
    return parse_cli(argv, TABLE, FLAGS, LISTS)


def test_long_with_separate_value() -> None:
    assert run(["--log", "out.html"]).values == {"log": "out.html"}


def test_long_with_equals_value() -> None:
    assert run(["--log=out.html"]).values == {"log": "out.html"}


def test_short_separate_value() -> None:
    assert run(["-c", "quiet"]).values == {"console": "quiet"}


def test_short_attached_value() -> None:
    assert run(["-cquiet"]).values == {"console": "quiet"}


def test_flag_long() -> None:
    assert run(["--verbose"]).values == {"verbose": True}


def test_flag_short() -> None:
    # -v is the derived short for verbose
    assert run(["-v"]).values == {"verbose": True}


def test_flag_with_explicit_value() -> None:
    assert run(["--verbose=false"]).values == {"verbose": "false"}


def test_combined_flags() -> None:
    class T(ArgConfig):
        @option
        def a(self, value: bool = False) -> bool:
            return value

        @option
        def b(self, value: bool = False) -> bool:
            return value

    opts = collect_options(T)
    table = resolve_names(opts)
    flags = {n for n, o in opts.items() if resolve_value_type(o).is_flag}
    res = parse_cli(["-ab"], table, flags, set())
    assert res.values == {"a": True, "b": True}


def test_repeatable_list_option() -> None:
    assert run(["--tag", "x", "--tag", "y"]).values == {"tag": ["x", "y"]}


def test_positionals_and_double_dash() -> None:
    res = run(["--log", "a", "pos1", "--", "--log", "notopt"])
    assert res.values == {"log": "a"}
    assert res.positionals == ["pos1", "--log", "notopt"]


def test_single_dash_is_positional() -> None:
    assert run(["-"]).positionals == ["-"]


def test_unknown_long_option_raises() -> None:
    with pytest.raises(CliUsageError):
        run(["--nope"])


def test_unknown_short_option_raises() -> None:
    with pytest.raises(CliUsageError):
        run(["-z"])


def test_missing_value_raises() -> None:
    with pytest.raises(CliUsageError):
        run(["--log"])


def test_missing_value_when_followed_by_option_raises() -> None:
    with pytest.raises(CliUsageError):
        run(["--log", "--verbose"])


def test_value_that_looks_like_negative_is_consumed() -> None:
    assert run(["--log", "NONE"]).values == {"log": "NONE"}


def test_flag_negation_sets_false() -> None:
    assert run(["--no-verbose"]).values == {"verbose": False}


def test_flag_negation_overrides_earlier_true() -> None:
    assert run(["--verbose", "--no-verbose"]).values == {"verbose": False}


def test_negation_with_value_raises() -> None:
    with pytest.raises(CliUsageError):
        run(["--no-verbose=1"])


def test_negation_of_non_flag_is_unknown() -> None:
    # --log is not a flag, so --no-log is not a valid negation.
    with pytest.raises(CliUsageError):
        run(["--no-log"])


def test_real_option_named_no_config_is_not_negation() -> None:
    # A genuinely-registered --no-config must match itself, not negate --config.
    class T(ArgConfig):
        @option
        def config_flag(self, value: bool = False) -> bool:
            return value

    opts = collect_options(T)
    table = resolve_names(opts)
    flags = {n for n, o in opts.items() if resolve_value_type(o).is_flag}
    # --no-config is a real cli-only flag on the base class.
    res = parse_cli(["--no-config"], table, flags, set())
    assert res.values == {"no_config": True}
