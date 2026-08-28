"""Tests for help-text generation."""

from __future__ import annotations

from argconfig import ArgConfig, option
from argconfig.help import format_help


class Tool(ArgConfig):
    """My tool.

    A longer description that spans the summary.
    """

    name = "mytool"

    @option
    def log(self, value: str | None = "log.html") -> str | None:
        """HTML log file. 'NONE' disables it."""
        return value

    @option(names="--console/-c")
    def console(self, value: str = "verbose") -> str:
        """Console output mode."""
        return value

    @option
    def verbose(self, value: bool = False) -> bool:
        """Enable verbose output."""
        return value

    @option
    def tags(self, value: list[str] | None = None) -> list[str] | None:
        """Repeatable tag."""
        return value


def test_help_includes_class_docstring() -> None:
    text = format_help(Tool())
    assert "My tool." in text
    assert "longer description" in text


def test_help_lists_options_and_summaries() -> None:
    text = format_help(Tool())
    assert "--log LOG" in text
    assert "HTML log file" in text
    assert "-c, --console CONSOLE" in text


def test_help_flag_has_no_metavar() -> None:
    text = format_help(Tool())
    lines = [line for line in text.splitlines() if "--verbose" in line]
    assert lines
    assert "VERBOSE" not in lines[0]


def test_help_list_option_metavar_has_ellipsis() -> None:
    text = format_help(Tool())
    assert "--tags TAGS..." in text


def test_help_includes_builtin_options() -> None:
    text = format_help(Tool())
    assert "-h, --help" in text
    assert "--no-config" in text
    assert "--config" in text
