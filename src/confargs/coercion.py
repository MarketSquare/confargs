"""Type resolution and coercion of raw source values.

confargs only performs *basic* coercion so that the value handed to a user's
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
from dataclasses import dataclass, replace
from typing import Any, Literal, Union, get_args, get_origin

from confargs.exceptions import MISSING, OptionValueError

if typing.TYPE_CHECKING:
    from confargs.arguments import Argument
    from confargs.options import Option

_TRUE = {"1", "true", "yes", "on", "y", "t"}
_FALSE = {"0", "false", "no", "off", "n", "f"}

_UNION_ORIGINS = {Union, types.UnionType}


@dataclass(frozen=True)
class ValueType:
    """A simplified description of an option's declared value type."""

    base: type
    is_list: bool = False
    allows_none: bool = False
    choices: tuple[Any, ...] | None = None
    ignore_case: bool = False

    @property
    def is_flag(self) -> bool:
        """A boolean, non-list option — a command line flag."""
        return self.base is bool and not self.is_list


def resolve_value_type(option: Option | Argument) -> ValueType:
    """Inspect an option (or argument) and describe the type its value expects."""
    value_type = _resolve_declared_type(option)
    if getattr(option, "ignore_case", False) and not value_type.ignore_case:
        value_type = replace(value_type, ignore_case=True)
    return value_type


def _resolve_declared_type(option: Option | Argument) -> ValueType:
    """Describe the value type declared by an option/argument (before flags)."""
    if option.func is None:
        return _resolve_declarative(option)

    annotation = option.raw_annotation
    if annotation is MISSING:
        return ValueType(base=str)

    try:
        hints = typing.get_type_hints(option.func)
    except Exception:
        # Unresolved forward refs: fall back to analysing the raw annotation
        # instead of surfacing a bare NameError from ``get_type_hints``.
        return _analyse(annotation)
    hint = hints.get(option.value_parameter.name, str)
    return _analyse(hint)


def _resolve_declarative(option: Option | Argument) -> ValueType:
    """Describe the value type of a declarative option (one without a method).

    An explicit ``type=`` wins; otherwise the type is inferred from the
    declared ``default`` (a ``bool`` default becomes a flag, ``None`` makes the
    value optional), falling back to ``str``.
    """
    if option.raw_annotation is not MISSING:
        return _analyse(option.raw_annotation)
    default = option.default
    if isinstance(default, bool):
        return ValueType(base=bool)
    if default is None:
        return ValueType(base=str, allows_none=True)
    if default is not MISSING:
        # A callable default is a *factory* (see ``_materialize_default``), so
        # infer the type from the value it builds rather than from the callable
        # itself (``type(list)`` is ``type``, which would collapse a list option
        # to a scalar). Fall back to ``str`` if the factory cannot be sampled.
        sample = default
        if callable(default):
            try:
                sample = default()
            except Exception:
                return ValueType(base=str)
        return _analyse(type(sample))
    return ValueType(base=str)


def _analyse(hint: Any) -> ValueType:
    allows_none = False
    origin = get_origin(hint)

    if origin in _UNION_ORIGINS:
        args = [arg for arg in get_args(hint) if arg is not type(None)]
        allows_none = len(args) != len(get_args(hint))
        # Take the first concrete member as the representative type.
        hint = args[0] if args else str
        origin = get_origin(hint)

    if origin is Literal:
        return _analyse_literal(get_args(hint), is_list=False, allows_none=allows_none)

    if origin in (list, set, tuple) or hint in (list, set, tuple):
        elem_args = get_args(hint)
        element = elem_args[0] if elem_args else str
        if get_origin(element) is Literal:
            return _analyse_literal(get_args(element), is_list=True, allows_none=allows_none)
        base = element if isinstance(element, type) else str
        return ValueType(base=base, is_list=True, allows_none=allows_none)

    base = hint if isinstance(hint, type) else str
    return ValueType(base=base, is_list=False, allows_none=allows_none)


def _analyse_literal(members: tuple[Any, ...], *, is_list: bool, allows_none: bool) -> ValueType:
    """Describe a ``Literal[...]`` annotation as a choice-constrained type."""
    base = type(members[0]) if members else str
    return ValueType(base=base, is_list=is_list, allows_none=allows_none, choices=tuple(members))


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


def _check_choice(value: Any, choices: tuple[Any, ...], *, ignore_case: bool = False) -> Any:
    """Return ``value`` if it matches one of ``choices``, else raise.

    With ``ignore_case`` a string value matches a choice regardless of case, and
    the *canonical* choice (as declared in the ``Literal[...]``) is returned so
    downstream code always sees the declared spelling. A case-insensitive match
    is only honoured when it is unambiguous.
    """
    if value in choices:
        return value
    if ignore_case and isinstance(value, str):
        folded = value.casefold()
        matches = [choice for choice in choices if isinstance(choice, str) and choice.casefold() == folded]
        if len(matches) == 1:
            return matches[0]
    allowed = ", ".join(repr(choice) for choice in choices)
    raise OptionValueError(f"invalid value {value!r}; choose from {allowed}")


def coerce_value(raw: Any, value_type: ValueType) -> Any:
    """Coerce a raw source value into the option's declared type.

    ``None`` is passed through when the option allows it. List options accept
    native sequences (TOML arrays, repeated CLI flags) or comma-separated
    strings (environment variables). When the type was declared with
    ``Literal[...]``, each coerced value is validated against the allowed set.
    """
    if raw is None:
        if value_type.allows_none:
            return None
        raise OptionValueError("value may not be null")

    if value_type.is_list:
        items = [_coerce_scalar(item, value_type.base) for item in _as_list(raw)]
        if value_type.choices is not None:
            items = [_check_choice(item, value_type.choices, ignore_case=value_type.ignore_case) for item in items]
        return items

    value = _coerce_scalar(raw, value_type.base)
    if value_type.choices is not None:
        return _check_choice(value, value_type.choices, ignore_case=value_type.ignore_case)
    return value
