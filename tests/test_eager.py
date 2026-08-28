"""Tests for eager options, argv injection and argument-file parsing."""

from __future__ import annotations

from pathlib import Path

import pytest

from confargs import (
    ArgConfig,
    ConfigurationProcessor,
    OptionDefinitionError,
    option,
    read_argument_file,
    split_argument_file,
)
from confargs.exceptions import CliUsageError


class ArgFileConfig(ArgConfig):
    name = "afdemo"

    @option(names="--argumentfile/-A", cli_only=True, is_eager=True)
    def argumentfile(self, value: str | None = None) -> list[str] | None:
        """Read more arguments from a file (eager)."""
        if not value:
            return None
        return read_argument_file(value)

    @option
    def name_opt(self, value: str = "default") -> str:
        return value

    @option
    def tags(self, value: list[str] | None = None) -> list[str]:
        return value or []

    @option
    def verbose(self, value: bool = False) -> bool:
        return value


def process(argv: list[str], **kwargs: object) -> object:
    return ConfigurationProcessor(ArgFileConfig, argv=argv, **kwargs).process()


def test_split_argument_file_basic() -> None:
    text = "--name-opt hello\n--verbose\n# a comment\n\npositional\n"
    assert split_argument_file(text) == ["--name-opt", "hello", "--verbose", "positional"]


def test_split_argument_file_equals_separator() -> None:
    assert split_argument_file("--name-opt=hello") == ["--name-opt", "hello"]


def test_split_argument_file_prefers_first_separator() -> None:
    # A space before the '=' means the space is the separator.
    assert split_argument_file("--name-opt a=b") == ["--name-opt", "a=b"]
    # An '=' before any space means '=' is the separator.
    assert split_argument_file("--name-opt=a b") == ["--name-opt", "a b"]


def test_read_argument_file(tmp_path: Path) -> None:
    af = tmp_path / "args.txt"
    af.write_text("--name-opt fromfile\n--verbose\n", encoding="utf-8")
    assert read_argument_file(af) == ["--name-opt", "fromfile", "--verbose"]


def test_argumentfile_injects_options(tmp_path: Path) -> None:
    af = tmp_path / "args.txt"
    af.write_text("--name-opt injected\n--verbose\n", encoding="utf-8")

    ns = process(["-A", str(af)])
    assert ns.name_opt == "injected"
    assert ns.verbose is True
    # The eager option itself leaves no value behind.
    assert ns.argumentfile is None


def test_argumentfile_position_is_preserved(tmp_path: Path) -> None:
    af = tmp_path / "args.txt"
    af.write_text("--name-opt fromfile\n", encoding="utf-8")

    # CLI value after the argument file wins because it appears later.
    ns = process(["-A", str(af), "--name-opt", "cli"])
    assert ns.name_opt == "cli"

    # CLI value before the argument file is overridden by the file's value.
    ns = process(["--name-opt", "cli", "-A", str(af)])
    assert ns.name_opt == "fromfile"


def test_argumentfile_equals_form(tmp_path: Path) -> None:
    af = tmp_path / "args.txt"
    af.write_text("--verbose\n", encoding="utf-8")
    ns = process([f"--argumentfile={af}"])
    assert ns.verbose is True


def test_nested_argument_files(tmp_path: Path) -> None:
    inner = tmp_path / "inner.txt"
    inner.write_text("--verbose\n--tags c\n", encoding="utf-8")
    outer = tmp_path / "outer.txt"
    outer.write_text(f"--tags a\n--tags b\n--argumentfile {inner}\n", encoding="utf-8")

    ns = process(["-A", str(outer)])
    assert ns.verbose is True
    assert ns.tags == ["a", "b", "c"]


def test_argumentfile_repeated(tmp_path: Path) -> None:
    first = tmp_path / "first.txt"
    first.write_text("--tags one\n", encoding="utf-8")
    second = tmp_path / "second.txt"
    second.write_text("--tags two\n", encoding="utf-8")

    ns = process(["-A", str(first), "-A", str(second)])
    assert ns.tags == ["one", "two"]


def test_cyclic_argument_file_is_detected(tmp_path: Path) -> None:
    loop = tmp_path / "loop.txt"
    loop.write_text(f"--argumentfile {loop}\n", encoding="utf-8")
    with pytest.raises(CliUsageError, match="cyclic"):
        process(["-A", str(loop)])


def test_eager_after_double_dash_is_not_expanded(tmp_path: Path) -> None:
    af = tmp_path / "args.txt"
    af.write_text("--verbose\n", encoding="utf-8")
    ns = process(["--", "-A", str(af)])
    assert ns.verbose is False


def test_eager_option_returning_bare_string_is_rejected() -> None:
    class BadConfig(ArgConfig):
        name = "bad"

        @option(is_eager=True)
        def broken(self, value: str | None = None) -> str | None:
            return "oops"

    with pytest.raises(OptionDefinitionError, match="bare string"):
        ConfigurationProcessor(BadConfig, argv=["--broken", "x"]).process()
