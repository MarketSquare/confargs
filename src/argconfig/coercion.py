"""Type resolution and coercion of raw source values.

argconfig only performs *basic* coercion so that the value handed to a user's
option method matches the type they annotated. All domain validation and
parsing is left to the method itself.

Values arrive in two shapes:

* **strings** from the command line and environment variables, and
* **already-typed** values from TOML (``int``, ``float``, ``bool``, ``str``,
  ``list``).

:func:`coerce_value` normalises both into the option's declared type.
"""

from __future__ import annotations

import types
import typing
from dataclasses import dataclass
from typing import Any, Union, get_args, get_origin

from argconfig.exceptions import MISSING, OptionValueError

if typing.TYPE_CHECKING:
    from argconfig.options import Option

_TRUE = {"1", "true", "yes", "on", "y", "t"}
_FALSE = {"0", "false", "no", "off", "n", "f"}

_UNION_ORIGINS = {Union, types.UnionType}


@dataclass(frozen=True)
class ValueType:
    """A simplified description of an option's declared value type."""

    base: type
    is_list: bool = False
    allows_none: bool = False

    @property
    def is_flag(self) -> bool:
        """A boolean, non-list option — a command line flag."""
        return self.base is bool and not self.is_list


def resolve_value_type(option: Option) -> ValueType:
    """Inspect an option method and describe the type its value expects."""
    annotation = option.raw_annotation
    if annotation is MISSING:
        return ValueType(base=str)

    hints = typing.get_type_hints(option.func)
    hint = hints.get(option.value_parameter.name, str)
    return _analyse(hint)


def _analyse(hint: Any) -> ValueType:
    allows_none = False
    origin = get_origin(hint)

    if origin in _UNION_ORIGINS:
        args = [arg for arg in get_args(hint) if arg is not type(None)]
        allows_none = len(args) != len(get_args(hint))
        # Take the first concrete member as the representative type.
        hint = args[0] if args else str
        origin = get_origin(hint)

    if origin in (list, set, tuple):
        elem_args = get_args(hint)
        element = elem_args[0] if elem_args else str
        base = element if isinstance(element, type) else str
        return ValueType(base=base, is_list=True, allows_none=allows_none)

    base = hint if isinstance(hint, type) else str
    return ValueType(base=base, is_list=False, allows_none=allows_none)


def parse_bool(raw: str) -> bool:
    """Parse a boolean from a string, accepting common spellings."""
    lowered = raw.strip().lower()
    if lowered in _TRUE:
        return True
    if lowered in _FALSE:
        return False
    raise OptionValueError(f"cannot interpret {raw!r} as a boolean")


def _coerce_scalar(raw: Any, base: type) -> Any:
    if base is bool:
        if isinstance(raw, bool):
            return raw
        return parse_bool(str(raw))
    if base is str:
        return raw if isinstance(raw, str) else str(raw)
    if base in (int, float):
        try:
            return base(raw)
        except (TypeError, ValueError) as exc:
            raise OptionValueError(f"cannot interpret {raw!r} as {base.__name__}") from exc
    # Unknown/custom base type: pass the raw value through untouched.
    return raw


def _as_list(raw: Any) -> list[Any]:
    if isinstance(raw, (list, tuple, set)):
        return list(raw)
    if isinstance(raw, str):
        return [item.strip() for item in raw.split(",") if item.strip()]
    return [raw]


def coerce_value(raw: Any, value_type: ValueType) -> Any:
    """Coerce a raw source value into the option's declared type.

    ``None`` is passed through when the option allows it. List options accept
    native sequences (TOML arrays, repeated CLI flags) or comma-separated
    strings (environment variables).
    """
    if raw is None:
        if value_type.allows_none:
            return None
        raise OptionValueError("value may not be null")

    if value_type.is_list:
        return [_coerce_scalar(item, value_type.base) for item in _as_list(raw)]

    return _coerce_scalar(raw, value_type.base)
