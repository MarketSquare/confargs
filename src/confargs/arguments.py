"""Positional *argument* support.

Where an :class:`~confargs.options.Option` is addressed by name on the command
line, an :class:`Argument` is positional: it is filled from the leftover,
non-option tokens in declaration order. Arguments mirror the two option
spellings — a decorated method for values that need parsing/validation, and a
plain attribute for pure pass-through — and share the same coercion path.

``nargs`` controls how many positionals an argument consumes:

* ``1`` (the default) — exactly one; required unless a default is given.
* ``"?"`` — at most one; the default is used when it is absent.
* ``"*"`` — zero or more, collected into a list (default ``[]``).
* ``"+"`` — one or more, collected into a list; required.

Only one variadic argument (``"*"`` / ``"+"``) is allowed and it must be the
last one declared, so the positional-to-argument assignment stays unambiguous.
"""

from __future__ import annotations

import inspect
import typing
from collections.abc import Callable
from types import MethodType
from typing import Any, overload

from confargs.exceptions import MISSING, OptionDefinitionError

ArgumentMethod = Callable[..., Any]

_VARIADIC = ("*", "+")
_VALID_NARGS: tuple[Any, ...] = (1, "?", "*", "+")


class Argument:
    """Metadata and descriptor for a single positional argument."""

    def __init__(
        self,
        func: ArgumentMethod | None = None,
        *,
        name: str | None = None,
        help: str | None = None,
        default: Any = MISSING,
        type: Any = MISSING,
        nargs: int | str = 1,
        config: bool = True,
        metavar: str | None = None,
    ) -> None:
        if nargs not in _VALID_NARGS:
            raise OptionDefinitionError(f"invalid nargs {nargs!r}; expected one of {_VALID_NARGS}")
        self.func = func
        self.explicit_name = name
        self.explicit_help = help
        self.declared_default = default
        self.declared_type = type
        self.nargs = nargs
        self.config = config
        self.explicit_metavar = metavar
        self.attr_name: str = func.__name__ if func is not None else (name or "")
        self.owner: type | None = None

    def __set_name__(self, owner: type, name: str) -> None:
        self.owner = owner
        self.attr_name = name

    def __call__(self, func: ArgumentMethod) -> Argument:
        """Bind a method to a decorator-created argument.

        Lets ``@argument(name=...)`` and the declarative
        ``attr = argument(name=...)`` share one implementation.
        """
        if self.func is not None:
            raise OptionDefinitionError(f"argument {self.attr_name!r} already has a method bound")
        self.func = func
        if self.explicit_name is None:
            self.attr_name = func.__name__
        return self

    def __get__(self, instance: object, owner: type | None = None) -> Any:
        if instance is None:
            return self
        if self.func is None:
            # A declarative argument has no user method: the value passes
            # through coercion unchanged.
            return lambda value: value
        return MethodType(self.func, instance)

    @property
    def arg_name(self) -> str:
        """The argument's configuration/display name."""
        return self.explicit_name or self.attr_name

    @property
    def is_variadic(self) -> bool:
        return self.nargs in _VARIADIC

    @property
    def metavar(self) -> str:
        base = self.explicit_metavar or self.arg_name
        return base.upper().replace("-", "_")

    @property
    def doc(self) -> str:
        if self.func is None:
            return (self.explicit_help or "").strip()
        return inspect.getdoc(self.func) or ""

    @property
    def value_parameter(self) -> inspect.Parameter:
        """The parameter that receives the incoming value (after ``self``)."""
        if self.func is None:
            msg = f"declarative argument {self.attr_name!r} has no value parameter"
            raise OptionDefinitionError(msg)
        params = list(inspect.signature(self.func).parameters.values())
        candidates = [p for p in params if p.name != "self"]
        if not candidates:
            msg = f"argument method {self.func.__qualname__!r} must accept a value parameter"
            raise OptionDefinitionError(msg)
        return candidates[0]

    @property
    def default(self) -> Any:
        """The argument's default value, or :data:`MISSING` if none is declared.

        A ``"*"`` argument defaults to an empty list when nothing is declared.
        """
        if self.func is None:
            base = self.declared_default
        else:
            param = self.value_parameter
            base = MISSING if param.default is inspect.Parameter.empty else param.default
        if base is MISSING and self.nargs == "*":
            return []
        return base

    @property
    def required(self) -> bool:
        """Whether a value must be supplied from some source."""
        if self.nargs in ("?", "*"):
            return False
        return self.default is MISSING

    @property
    def raw_annotation(self) -> Any:
        if self.func is None:
            if self.declared_type is not MISSING:
                return self.declared_type
            return self._attribute_annotation()
        param = self.value_parameter
        if param.annotation is inspect.Parameter.empty:
            return MISSING
        return param.annotation

    def _attribute_annotation(self) -> Any:
        """Resolve the class attribute annotation, e.g. ``port: int = argument(...)``."""
        if self.owner is None:
            return MISSING
        try:
            hints = typing.get_type_hints(self.owner)
        except Exception:  # unresolved forward refs fall back to inference
            return MISSING
        return hints.get(self.attr_name, MISSING)

    def __repr__(self) -> str:
        return f"Argument({self.attr_name!r}, nargs={self.nargs!r}, config={self.config})"


@overload
def argument(func: ArgumentMethod) -> Argument: ...


@overload
def argument(
    *,
    name: str | None = ...,
    help: str | None = ...,
    default: Any = ...,
    type: Any = ...,
    nargs: int | str = ...,
    config: bool = ...,
    metavar: str | None = ...,
) -> Argument: ...


def argument(
    func: ArgumentMethod | None = None,
    *,
    name: str | None = None,
    help: str | None = None,
    default: Any = MISSING,
    type: Any = MISSING,
    nargs: int | str = 1,
    config: bool = True,
    metavar: str | None = None,
) -> Argument:
    """Declare a positional argument.

    Like :func:`~confargs.option`, an argument can be spelled three ways:

    * as a bare decorator, ``@argument``;
    * as a decorator with keyword arguments, ``@argument(nargs="+")``; and
    * as a plain class attribute, ``sources = argument(nargs="*", help=...)`` —
      a *declarative* argument whose value passes straight through coercion.

    Args:
        name: The argument's name, used as its TOML config key and its ``--help``
            metavar. Defaults to the method or attribute name.
        help: Help text for a declarative argument (one without a method).
        default: Default value used when no positional (and no config value) is
            supplied. A ``"*"`` argument defaults to an empty list.
        type: Explicit value type for a declarative argument (e.g. ``int`` or
            ``list[str]``). When omitted the type is taken from the attribute
            annotation (``count: int = argument(...)``) if present, then inferred
            from the annotation/``default``, and otherwise falls back to ``str``.
        nargs: How many positionals to consume: ``1`` (exactly one, the
            default), ``"?"`` (optional), ``"*"`` (zero or more) or ``"+"`` (one
            or more). ``"*"``/``"+"`` collect into a list.
        config: When false, the argument is never loaded from TOML config.
        metavar: Override the ``--help`` metavar (defaults to the upper-cased
            name).
    """
    return Argument(
        func,
        name=name,
        help=help,
        default=default,
        type=type,
        nargs=nargs,
        config=config,
        metavar=metavar,
    )


def collect_arguments(cls: type) -> dict[str, Argument]:
    """Collect every :class:`Argument` declared on ``cls`` and its bases.

    Arguments are returned keyed by attribute name in definition order, with
    subclasses overriding arguments of the same name defined on their bases.
    A variadic argument (``"*"``/``"+"``) is only allowed as the final one.
    """
    collected: dict[str, Argument] = {}
    for klass in reversed(cls.__mro__):
        for name, value in vars(klass).items():
            if isinstance(value, Argument):
                collected.pop(name, None)  # move overridden argument to the end
                collected[name] = value

    items = list(collected.values())
    for arg in items[:-1]:
        if arg.is_variadic:
            raise OptionDefinitionError(
                f"variadic argument {arg.arg_name!r} (nargs={arg.nargs!r}) must be the last argument declared"
            )
    return collected
