"""The ``option`` decorator, the :class:`Option` descriptor and name handling.

An option is declared as a *method* on an :class:`~confargs.base.ArgConfig`
subclass and decorated with :func:`option`. The method receives the raw value
coming from whichever source supplied it (CLI, environment or TOML), validates
and/or parses it, and returns the final value.

The decorated attribute becomes an :class:`Option` descriptor. Accessing it on
an instance still yields the bound method, so ``instance.log("x")`` works, while
accessing it on the class yields the :class:`Option` object for introspection.
"""

from __future__ import annotations

import inspect
import typing
from collections.abc import Callable
from dataclasses import dataclass, field
from types import MethodType
from typing import TYPE_CHECKING, Any, overload

from confargs.exceptions import MISSING, OptionDefinitionError

if TYPE_CHECKING:
    from collections.abc import Mapping

OptionMethod = Callable[..., Any]


def _normalise_long(name: str) -> str:
    """Return the canonical ``--long`` form of a bare or dashed long name."""
    bare = name.lstrip("-")
    if not bare:
        raise OptionDefinitionError(f"invalid option name {name!r}")
    return f"--{bare}"


def _normalise_short(short: str) -> str:
    """Return the canonical ``-s`` form of a bare or dashed short name."""
    bare = short.lstrip("-")
    if len(bare) != 1:
        raise OptionDefinitionError(f"short option {short!r} must be a single character")
    return f"-{bare}"


class Option:
    """Metadata and descriptor for a single declared option."""

    def __init__(
        self,
        func: OptionMethod | None = None,
        *,
        name: str | None = None,
        short: str | None = None,
        help: str | None = None,
        default: Any = MISSING,
        type: Any = MISSING,
        cli: bool = True,
        config: bool = True,
        env: bool | str = False,
        is_eager: bool = False,
    ) -> None:
        self.func = func
        self.explicit_name = name
        self.explicit_short = short
        self.explicit_help = help
        self.declared_default = default
        self.declared_type = type
        self.cli = cli
        self.config = config
        self.env = env
        self.is_eager = is_eager
        self.attr_name: str = func.__name__ if func is not None else (name or "")
        self.owner: type | None = None
        # Names the option *wants*; short-name collisions are resolved later.
        self.long_names: list[str] = []
        self.explicit_shorts: list[str] = []
        self.auto_short: str | None = None
        self._derive_default_names()

    def __set_name__(self, owner: type, name: str) -> None:
        self.owner = owner
        self.attr_name = name
        self._derive_default_names()

    def __call__(self, func: OptionMethod) -> Option:
        """Bind a method to a decorator-created option.

        This lets ``@option(name=...)`` and the declarative
        ``attr = option(name=...)`` share one code path: the former simply
        invokes the returned :class:`Option` on the decorated method.
        """
        if self.func is not None:
            raise OptionDefinitionError(f"option {self.attr_name!r} already has a method bound")
        self.func = func
        if self.explicit_name is None:
            self.attr_name = func.__name__
        self._derive_default_names()
        return self

    def __get__(self, instance: object, owner: type | None = None) -> Any:
        if instance is None:
            return self
        if self.func is None:
            # A declarative option has no user method: the value passes through
            # coercion unchanged.
            return lambda value: value
        return MethodType(self.func, instance)

    def _derive_default_names(self) -> None:
        # Long name: explicit ``name`` wins, otherwise derive from the method
        # (or, for a declarative option, the class attribute) name.
        if self.explicit_name is not None:
            long = _normalise_long(self.explicit_name)
        elif self.attr_name:
            long = f"--{self.attr_name.replace('_', '-')}"
        else:
            # A declarative option before ``__set_name__`` has run: names are
            # filled in once the attribute is bound to its class.
            self.long_names = []
            self.explicit_shorts = []
            self.auto_short = None
            return
        self.long_names = [long]

        # Short name: explicit ``short`` wins. Otherwise auto-derive from the
        # first letter, but only when the long name is itself method-derived
        # (an explicit ``name`` opts out of the implicit short).
        self.explicit_shorts = []
        self.auto_short = None
        if self.explicit_short is not None:
            self.explicit_shorts = [_normalise_short(self.explicit_short)]
        elif self.explicit_name is None:
            first = long[2:3]
            if first.isalnum():
                self.auto_short = f"-{first}"

    @property
    def doc(self) -> str:
        if self.func is None:
            return (self.explicit_help or "").strip()
        return inspect.getdoc(self.func) or ""

    @property
    def value_parameter(self) -> inspect.Parameter:
        """The parameter that receives the incoming value (after ``self``)."""
        if self.func is None:
            msg = f"declarative option {self.attr_name!r} has no value parameter"
            raise OptionDefinitionError(msg)
        params = list(inspect.signature(self.func).parameters.values())
        candidates = [p for p in params if p.name != "self"]
        if not candidates:
            msg = f"option method {self.func.__qualname__!r} must accept a value parameter"
            raise OptionDefinitionError(msg)
        return candidates[0]

    @property
    def default(self) -> Any:
        """The option's default value, or :data:`MISSING` if none is declared."""
        if self.func is None:
            return self.declared_default
        param = self.value_parameter
        if param.default is inspect.Parameter.empty:
            return MISSING
        return param.default

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
        """Resolve the class attribute annotation, e.g. ``name: str = option(...)``.

        Returns :data:`MISSING` when the owner has no annotation for this
        attribute (or the annotations cannot be resolved), so type inference
        falls back to the declared default.
        """
        if self.owner is None:
            return MISSING
        try:
            hints = typing.get_type_hints(self.owner)
        except Exception:  # unresolved forward refs fall back to inference
            return MISSING
        return hints.get(self.attr_name, MISSING)

    def __repr__(self) -> str:
        names = "|".join([*self.long_names, *self.explicit_shorts])
        return (
            f"Option({self.attr_name!r}, names={names!r}, "
            f"cli={self.cli}, config={self.config}, is_eager={self.is_eager})"
        )


@overload
def option(func: OptionMethod) -> Option: ...


@overload
def option(
    *,
    name: str | None = ...,
    short: str | None = ...,
    help: str | None = ...,
    default: Any = ...,
    type: Any = ...,
    cli: bool = ...,
    config: bool = ...,
    env: bool | str = ...,
    is_eager: bool = ...,
) -> Option: ...


def option(
    func: OptionMethod | None = None,
    *,
    name: str | None = None,
    short: str | None = None,
    help: str | None = None,
    default: Any = MISSING,
    type: Any = MISSING,
    cli: bool = True,
    config: bool = True,
    env: bool | str = False,
    is_eager: bool = False,
) -> Option:
    """Declare an confargs option.

    There are three equivalent spellings:

    * as a bare decorator, ``@option``;
    * as a decorator with keyword arguments,
      ``@option(name="console", short="c", config=False, env=True)``; and
    * as a plain class attribute (no method),
      ``console = option(name="console", help="Console output mode")`` — a
      *declarative* option whose value passes straight through coercion.

    Args:
        name: The long option name, without leading dashes (e.g. ``"console"``
            gives ``--console``). When omitted it is derived from the method or
            attribute name (underscores become dashes).
        short: The short option name, e.g. ``"c"`` gives ``-c``. When omitted a
            short name is auto-derived from the first letter of the long name —
            but only if ``name`` was not given explicitly; passing ``name``
            opts out of the implicit short.
        help: Help text for a declarative option (an option declared without a
            method). Ignored for decorated options, which use the method's
            docstring instead.
        default: Default value for a declarative option. A ``bool`` default
            makes the option a flag; a ``None`` default makes the value
            optional (``str | None``).
        type: Explicit value type for a declarative option (e.g. ``int`` or
            ``list[str]``). When omitted the type is taken from the attribute
            annotation (``attr: int = option(...)``) if present, then inferred
            from ``default``, and otherwise falls back to ``str``.
        cli: When false, the option is not exposed on the command line (it has
            no CLI names and is skipped in ``--help``). Use for options that
            should only come from config files or the environment.
        config: When false, the option is never loaded from TOML config files.
            Combine with the environment/CLI toggles to build, for example, a
            CLI-only switch (``config=False``, no ``env``) that controls the
            tool run itself.
        env: Opt this option into the environment-variable source. ``True`` uses
            a name generated from the class ``env_var_template`` (by default
            ``"{name}_{option}"`` upper-cased, e.g. ``MYTOOL_LOG``); a string
            sets an explicit variable name. ``False`` (the default) means the
            option is never read from the environment.
        is_eager: If true, the option is resolved *before* any other option,
            directly against ``argv``. The method's return value (an iterable of
            strings, or ``None``) replaces the option's own tokens in ``argv``,
            allowing it to inject further arguments — this is how an
            ``--argumentfile`` option expands a file into more options.
    """

    opt = Option(
        func,
        name=name,
        short=short,
        help=help,
        default=default,
        type=type,
        cli=cli,
        config=config,
        env=env,
        is_eager=is_eager,
    )
    return opt


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
        if not opt.cli:
            table.attr_to_names[attr] = []
            continue
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
        if not opt.cli or opt.auto_short is None:
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
