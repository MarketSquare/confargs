"""A minimal command-line tokenizer.

This is deliberately tiny: it only splits ``argv`` into raw per-option values.
It does **no** type conversion, defaulting or validation — those happen later so
that the same coercion/validation path is shared by every source (CLI, env,
TOML). Supported forms:

* ``--long value`` and ``--long=value``
* ``-s value``, ``-svalue`` (attached) and combined flags ``-abc``
* boolean flags: ``--flag`` / ``-f`` (and ``--flag=false``)
* boolean negation: ``--no-flag`` sets a boolean option to ``False``
* ``--`` terminates option parsing; the rest are positionals
* a lone ``-`` is treated as a positional (stdin convention)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from argconfig.exceptions import CliUsageError

if TYPE_CHECKING:
    from collections.abc import Sequence

    from argconfig.options import NameTable


@dataclass
class CliResult:
    """The outcome of tokenizing ``argv``."""

    values: dict[str, Any] = field(default_factory=dict)
    positionals: list[str] = field(default_factory=list)


def _store(result: CliResult, attr: str, value: Any, list_opts: set[str]) -> None:
    if attr in list_opts:
        result.values.setdefault(attr, []).append(value)
    else:
        result.values[attr] = value


def negation_name(long_name: str) -> str:
    """Return the ``--no-`` negation form of a long option name."""
    return f"--no-{long_name[2:]}"


def _negated_flag_attr(name: str, table: NameTable, flags: set[str]) -> str | None:
    """If ``name`` is a ``--no-<flag>`` negation of a known flag, return its attr."""
    if not name.startswith("--no-"):
        return None
    base = f"--{name[len('--no-'):]}"
    attr = table.long_to_attr.get(base)
    if attr is not None and attr in flags:
        return attr
    return None


def parse_cli(
    argv: Sequence[str],
    table: NameTable,
    flags: set[str],
    list_opts: set[str],
) -> CliResult:
    """Tokenize ``argv`` into raw per-option values.

    Args:
        argv: Arguments to parse (without the program name).
        table: Resolved name-to-attribute mapping.
        flags: Attribute names of boolean flag options.
        list_opts: Attribute names of repeatable (list) options.
    """
    result = CliResult()
    args = list(argv)
    index = 0
    positional_only = False

    while index < len(args):
        token = args[index]
        index += 1

        if positional_only:
            result.positionals.append(token)
            continue
        if token == "--":
            positional_only = True
            continue
        if token == "-" or not token.startswith("-"):
            result.positionals.append(token)
            continue

        if token.startswith("--"):
            index = _handle_long(token, args, index, result, table, flags, list_opts)
        else:
            index = _handle_short(token, args, index, result, table, flags, list_opts)

    return result


def _consume_value(name: str, args: list[str], index: int, table: NameTable) -> tuple[str, int]:
    if index >= len(args) or table.attr_for(args[index]) is not None or args[index] == "--":
        raise CliUsageError(f"option {name!r} expects a value")
    return args[index], index + 1


def _handle_long(
    token: str,
    args: list[str],
    index: int,
    result: CliResult,
    table: NameTable,
    flags: set[str],
    list_opts: set[str],
) -> int:
    name, sep, inline = token.partition("=")
    attr = table.long_to_attr.get(name)
    if attr is None:
        negated = _negated_flag_attr(name, table, flags)
        if negated is not None:
            if sep:
                raise CliUsageError(f"option {name!r} does not take a value")
            _store(result, negated, False, list_opts)
            return index
        raise CliUsageError(f"unknown option {name!r}")

    if attr in flags:
        _store(result, attr, inline if sep else True, list_opts)
        return index

    if sep:
        _store(result, attr, inline, list_opts)
        return index
    value, index = _consume_value(name, args, index, table)
    _store(result, attr, value, list_opts)
    return index


def _handle_short(
    token: str,
    args: list[str],
    index: int,
    result: CliResult,
    table: NameTable,
    flags: set[str],
    list_opts: set[str],
) -> int:
    body = token[1:]
    position = 0
    while position < len(body):
        name = f"-{body[position]}"
        attr = table.short_to_attr.get(name)
        if attr is None:
            raise CliUsageError(f"unknown option {name!r}")
        if attr in flags:
            _store(result, attr, True, list_opts)
            position += 1
            continue
        # Value option: the remainder of the cluster is the value, else the next token.
        attached = body[position + 1 :]
        if attached:
            _store(result, attr, attached, list_opts)
        else:
            value, index = _consume_value(name, args, index, table)
            _store(result, attr, value, list_opts)
        return index
    return index
