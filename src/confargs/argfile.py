"""Helpers for reading *argument files* — text files that contain more options.

This mirrors the well-known Robot Framework ``--argumentfile`` format so that an
eager option (see :func:`confargs.option`) can expand a file into extra CLI
tokens:

* a leading UTF-8 BOM is ignored (files are read as ``utf-8-sig``),
* an optional ``# expandvars: <bool>`` pragma on the first line enables
  environment-variable expansion of the whole file (see below),
* each line is stripped of surrounding whitespace,
* blank lines and ``#`` comment lines are ignored,
* a line starting with ``-`` is an option; it is split into a name and value on
  the first space or ``=`` (whichever comes first), and
* any other non-empty line is passed through as a positional token.

**Variable expansion.** When the first line is a truthy ``# expandvars:`` pragma
(e.g. ``# expandvars: true``), the file contents are expanded *before* being
split into lines, using these rules (matching Robot Framework):

* ``$NAME`` and ``${NAME}`` are replaced with the environment variable ``NAME``,
* ``${NAME=default}`` uses ``default`` when ``NAME`` is unset,
* ``$$`` is an escaped literal ``$``,
* a reference to an unset variable without a default raises an error, and
* a malformed reference (e.g. ``$1abc``) raises an error.

Only the parsing is provided here; the decision to inject the resulting tokens
is made by the eager option's method, which returns them to the processor.
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from string import Template
from typing import TYPE_CHECKING

from confargs.exceptions import CliUsageError

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

# Strings considered "false" for the ``# expandvars:`` pragma (case-insensitive),
# matching Robot Framework's ``is_truthy`` semantics.
_FALSE_VALUES = frozenset({"FALSE", "NO", "OFF", "0", "NONE", ""})

_EXPANDVARS_PRAGMA = re.compile(r"#\s*expandvars:\s*(.*)\s*\n", flags=re.IGNORECASE)


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


class _TemplateWithDefaults(Template):
    """``string.Template`` that also accepts ``${NAME=default}`` references."""

    braceidpattern = r"(?a:[_a-z][_a-z0-9]*(=[^}]*)?)"


class _EnvWithDefaults(Mapping[str, str]):
    """Mapping wrapper resolving ``NAME=default`` keys against ``environ``."""

    def __init__(self, environ: Mapping[str, str]) -> None:
        self._environ = environ

    def __getitem__(self, key: str) -> str:
        if "=" in key:
            name, default = key.split("=", 1)
            return self._environ.get(name, default)
        return self._environ[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._environ)

    def __len__(self) -> int:
        return len(self._environ)


def _expand_variables(text: str, environ: Mapping[str, str]) -> str:
    """Expand ``$NAME`` / ``${NAME}`` / ``${NAME=default}`` references in ``text``.

    Raises:
        ValueError: If a referenced variable is unset (and has no default) or a
            reference is malformed.
    """
    try:
        return _TemplateWithDefaults(text).substitute(_EnvWithDefaults(environ))
    except KeyError as err:
        raise ValueError(f"Variable '{err.args[0]}' does not exist.") from err


def _expandvars_enabled(text: str) -> bool:
    match = _EXPANDVARS_PRAGMA.match(text)
    if match is None:
        return False
    return match.group(1).strip().upper() not in _FALSE_VALUES


def _tokenize(text: str, environ: Mapping[str, str]) -> list[str]:
    if _expandvars_enabled(text):
        text = _expand_variables(text, environ)
    tokens: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("-"):
            tokens.extend(_split_option(line))
        elif line and not line.startswith("#"):
            tokens.append(line)
    return tokens


def split_argument_file(text: str, *, environ: Mapping[str, str] | None = None) -> list[str]:
    """Tokenize the *contents* of an argument file into a list of argv tokens.

    Args:
        text: The full text of an argument file.
        environ: Environment mapping used when the ``# expandvars:`` pragma is
            enabled. Defaults to :data:`os.environ`.

    Returns:
        The tokens to splice into ``argv``.

    Raises:
        CliUsageError: If variable expansion fails (unset or malformed variable).
    """
    try:
        return _tokenize(text, os.environ if environ is None else environ)
    except ValueError as err:
        raise CliUsageError(f"Processing argument file failed: {err}") from err


def read_argument_file(
    path: str | Path,
    *,
    encoding: str = "utf-8-sig",
    environ: Mapping[str, str] | None = None,
) -> list[str]:
    """Read an argument file from disk and tokenize it.

    A leading UTF-8 BOM is ignored (the default ``utf-8-sig`` encoding strips it).

    Args:
        path: Path to the argument file.
        encoding: Text encoding used to read the file.
        environ: Environment mapping used when the ``# expandvars:`` pragma is
            enabled. Defaults to :data:`os.environ`.

    Returns:
        The tokens to splice into ``argv``.

    Raises:
        CliUsageError: If variable expansion fails (unset or malformed variable).
    """
    from pathlib import Path as _Path

    text = _Path(path).read_text(encoding=encoding)
    try:
        return _tokenize(text, os.environ if environ is None else environ)
    except ValueError as err:
        raise CliUsageError(f"Processing argument file '{path}' failed: {err}") from err
