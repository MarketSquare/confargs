"""Helpers for reading *argument files* — text files that contain more options.

This mirrors the well-known Robot Framework ``--argumentfile`` format so that an
eager option (see :func:`argconfig.option`) can expand a file into extra CLI
tokens:

* each line is stripped of surrounding whitespace,
* blank lines and ``#`` comment lines are ignored,
* a line starting with ``-`` is an option; it is split into a name and value on
  the first space or ``=`` (whichever comes first), and
* any other non-empty line is passed through as a positional token.

Only the parsing is provided here; the decision to inject the resulting tokens
is made by the eager option's method, which returns them to the processor.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def _option_separator(line: str) -> str | None:
    """Return the separator (space or ``=``) between an option and its value."""
    if " " not in line and "=" not in line:
        return None
    if "=" not in line:
        return " "
    if " " not in line:
        return "="
    return " " if line.index(" ") < line.index("=") else "="


def _split_option(line: str) -> list[str]:
    separator = _option_separator(line)
    if separator is None:
        return [line]
    name, value = line.split(separator, 1)
    if separator == " ":
        value = value.strip()
    return [name, value]


def split_argument_file(text: str) -> list[str]:
    """Tokenize the *contents* of an argument file into a list of argv tokens.

    Args:
        text: The full text of an argument file.

    Returns:
        The tokens to splice into ``argv``.
    """
    tokens: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("-"):
            tokens.extend(_split_option(line))
        elif line and not line.startswith("#"):
            tokens.append(line)
    return tokens


def read_argument_file(path: str | Path, *, encoding: str = "utf-8") -> list[str]:
    """Read an argument file from disk and tokenize it.

    Args:
        path: Path to the argument file.
        encoding: Text encoding used to read the file.

    Returns:
        The tokens to splice into ``argv``.
    """
    from pathlib import Path as _Path

    return split_argument_file(_Path(path).read_text(encoding=encoding))
