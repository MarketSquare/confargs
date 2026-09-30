"""Resolving relative paths set in config files against the file's directory."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, Union

from confargs.exceptions import OptionDefinitionError

RelativeToConfig = Union[bool, Literal["existing"]]  # noqa: UP007 - runtime alias on Python 3.10


def check_relative_to_config(value: object, owner: str) -> RelativeToConfig:
    """Validate a ``relative_to_config`` declaration value."""
    if value is True or value is False:
        return value
    if value == "existing":
        return "existing"
    raise OptionDefinitionError(f"{owner}: relative_to_config must be True, False or 'existing', got {value!r}")


def resolve_relative(value: Any, base: Path, mode: RelativeToConfig) -> Any:
    """Resolve relative path strings in a config ``value`` against ``base``.

    Handles a single string or the string items of a list; anything else (and
    absolute or empty paths) is returned unchanged for coercion to handle.

    With ``mode="existing"`` a value is rewritten only when it names something
    that exists under ``base`` - either the whole value or the part before a
    trailing ``:args``/``;args`` suffix - so values that may also be, e.g.,
    module names are left alone.
    """
    if isinstance(value, list):
        return [resolve_relative(item, base, mode) for item in value]
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        return value
    if mode != "existing":
        return str(base / value)
    if (base / value).exists():
        return str(base / value)
    index = _arg_separator_index(value)
    if index > 0 and not Path(value[:index]).is_absolute() and (base / value[:index]).exists():
        return str(base / value[:index]) + value[index:]
    return value


def _arg_separator_index(value: str) -> int:
    """Index of the first ``:`` or ``;`` that starts an argument suffix, or -1.

    A colon right after a Windows drive letter (``C:/`` or ``C:\\``) is part of
    the path, not a separator.
    """
    colon = value.find(":")
    if colon == 1 and value[0].isalpha() and value[2:3] in ("/", "\\"):
        colon = value.find(":", 2)
    semicolon = value.find(";")
    candidates = [i for i in (colon, semicolon) if i != -1]
    return min(candidates) if candidates else -1
