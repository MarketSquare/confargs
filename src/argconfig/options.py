"""The ``option`` decorator, the :class:`Option` descriptor and name handling.

An option is declared as a *method* on an :class:`~argconfig.base.ArgConfig`
subclass and decorated with :func:`option`. The method receives the raw value
coming from whichever source supplied it (CLI, environment or TOML), validates
and/or parses it, and returns the final value.

The decorated attribute becomes an :class:`Option` descriptor. Accessing it on
an instance still yields the bound method, so ``instance.log("x")`` works, while
accessing it on the class yields the :class:`Option` object for introspection.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass, field
from types import MethodType
from typing import TYPE_CHECKING, Any, overload

from argconfig.exceptions import MISSING, OptionDefinitionError

if TYPE_CHECKING:
    from collections.abc import Mapping

OptionMethod = Callable[..., Any]


def _parse_names(spec: str) -> tuple[list[str], list[str]]:
    """Split an explicit names spec such as ``"--console/-c"``.

    Returns a ``(long_names, short_names)`` tuple. Long names start with ``--``
    and short names with a single ``-``.
    """
    longs: list[str] = []
    shorts: list[str] = []
    for raw in spec.split("/"):
        token = raw.strip()
        if not token:
            continue
        if token.startswith("--"):
            longs.append(token)
        elif token.startswith("-"):
            shorts.append(token)
        else:
            msg = f"invalid option name {token!r} in spec {spec!r}; names must start with '-' or '--'"
            raise OptionDefinitionError(msg)
    if not longs and not shorts:
        raise OptionDefinitionError(f"names spec {spec!r} does not contain any option names")
    return longs, shorts


class Option:
    """Metadata and descriptor for a single declared option."""

    def __init__(
        self,
        func: OptionMethod,
        *,
        names: str | None = None,
        cli_only: bool = False,
        envvar: str | None = None,
        is_eager: bool = False,
    ) -> None:
        self.func = func
        self.explicit_names = names
        self.cli_only = cli_only
        self.envvar = envvar
        self.is_eager = is_eager
        self.attr_name: str = func.__name__
        # Names the option *wants*; short-name collisions are resolved later.
        self.long_names: list[str] = []
        self.explicit_shorts: list[str] = []
        self.auto_short: str | None = None
        if names is not None:
            self.long_names, self.explicit_shorts = _parse_names(names)
        self._derive_default_names()

    def __set_name__(self, owner: type, name: str) -> None:
        self.attr_name = name
        if self.explicit_names is None:
            # Re-derive now that we know the attribute name.
            self.long_names = []
            self.auto_short = None
            self._derive_default_names()

    def __get__(self, instance: object, owner: type | None = None) -> Any:
        if instance is None:
            return self
        return MethodType(self.func, instance)

    def _derive_default_names(self) -> None:
        if self.explicit_names is not None:
            return
        self.long_names = [f"--{self.attr_name.replace('_', '-')}"]
        first = self.attr_name[0]
        if first.isalnum():
            self.auto_short = f"-{first}"

    @property
    def doc(self) -> str:
        return inspect.getdoc(self.func) or ""

    @property
    def value_parameter(self) -> inspect.Parameter:
        """The parameter that receives the incoming value (after ``self``)."""
        params = list(inspect.signature(self.func).parameters.values())
        candidates = [p for p in params if p.name != "self"]
        if not candidates:
            msg = f"option method {self.func.__qualname__!r} must accept a value parameter"
            raise OptionDefinitionError(msg)
        return candidates[0]

    @property
    def default(self) -> Any:
        """The option's default value, or :data:`MISSING` if none is declared."""
        param = self.value_parameter
        if param.default is inspect.Parameter.empty:
            return MISSING
        return param.default

    @property
    def raw_annotation(self) -> Any:
        param = self.value_parameter
        if param.annotation is inspect.Parameter.empty:
            return MISSING
        return param.annotation

    def __repr__(self) -> str:
        names = "|".join([*self.long_names, *self.explicit_shorts])
        return f"Option({self.attr_name!r}, names={names!r}, cli_only={self.cli_only}, is_eager={self.is_eager})"


@overload
def option(func: OptionMethod) -> Option: ...


@overload
def option(
    *,
    names: str | None = ...,
    cli_only: bool = ...,
    envvar: str | None = ...,
    is_eager: bool = ...,
) -> Callable[[OptionMethod], Option]: ...


def option(
    func: OptionMethod | None = None,
    *,
    names: str | None = None,
    cli_only: bool = False,
    envvar: str | None = None,
    is_eager: bool = False,
) -> Option | Callable[[OptionMethod], Option]:
    """Mark a method as an argconfig option.

    Usable bare (``@option``) or with keyword arguments
    (``@option(names="--console/-c", cli_only=True, envvar="MY_CONSOLE")``).

    Args:
        names: Explicit names spec, e.g. ``"--console/-c"``. When omitted the
            long name is derived from the method name and a short name from its
            first letter (if free).
        cli_only: If true, the option is only read from the command line and is
            never loaded from TOML config files or environment variables.
        envvar: Name of an environment variable that provides this option's
            value.
        is_eager: If true, the option is resolved *before* any other option,
            directly against ``argv``. The method's return value (an iterable of
            strings, or ``None``) replaces the option's own tokens in ``argv``,
            allowing it to inject further arguments — this is how an
            ``--argumentfile`` option expands a file into more options.
    """

    def wrap(f: OptionMethod) -> Option:
        return Option(f, names=names, cli_only=cli_only, envvar=envvar, is_eager=is_eager)

    if func is not None:
        return wrap(func)
    return wrap


@dataclass
class NameTable:
    """Resolved mapping between CLI tokens and option attribute names."""

    long_to_attr: dict[str, str] = field(default_factory=dict)
    short_to_attr: dict[str, str] = field(default_factory=dict)
    attr_to_names: dict[str, list[str]] = field(default_factory=dict)

    def attr_for(self, token: str) -> str | None:
        if token.startswith("--"):
            return self.long_to_attr.get(token)
        if token.startswith("-"):
            return self.short_to_attr.get(token)
        return None


def resolve_names(options: Mapping[str, Option]) -> NameTable:
    """Assign final CLI names to options, resolving short-name collisions.

    Long names and explicitly requested short names are authoritative and must
    be unique. Auto-derived short names (first letter of the method name) are
    only assigned when still free; otherwise they are silently skipped so that
    an option still works through its long name.
    """
    table = NameTable()

    # Pass 1: long names and explicit short names (must be unique).
    for attr, opt in options.items():
        display: list[str] = []
        for long in opt.long_names:
            if long in table.long_to_attr:
                other = table.long_to_attr[long]
                raise OptionDefinitionError(f"long option {long!r} is used by both {other!r} and {attr!r}")
            table.long_to_attr[long] = attr
            display.append(long)
        for short in opt.explicit_shorts:
            if short in table.short_to_attr:
                other = table.short_to_attr[short]
                raise OptionDefinitionError(f"short option {short!r} is used by both {other!r} and {attr!r}")
            table.short_to_attr[short] = attr
            display.append(short)
        table.attr_to_names[attr] = display

    # Pass 2: auto short names, skipping collisions.
    for attr, opt in options.items():
        if opt.explicit_names is not None or opt.auto_short is None:
            continue
        for candidate in _short_candidates(opt.auto_short):
            if candidate not in table.short_to_attr:
                table.short_to_attr[candidate] = attr
                table.attr_to_names[attr].append(candidate)
                break

    return table


def _short_candidates(auto_short: str) -> list[str]:
    letter = auto_short[1:]
    candidates = [auto_short]
    upper = f"-{letter.upper()}"
    if upper != auto_short:
        candidates.append(upper)
    return candidates


def collect_options(cls: type) -> dict[str, Option]:
    """Collect every :class:`Option` declared on ``cls`` and its bases.

    Options are returned keyed by attribute name in definition order, with
    subclasses overriding options of the same name defined on their bases.
    """
    collected: dict[str, Option] = {}
    for klass in reversed(cls.__mro__):
        for name, value in vars(klass).items():
            if isinstance(value, Option):
                collected.pop(name, None)  # move overridden option to the end
                collected[name] = value
    return collected
