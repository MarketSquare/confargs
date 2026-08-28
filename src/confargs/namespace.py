"""The immutable result object returned by the processor."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping


class Namespace:
    """Read-only container exposing resolved option values.

    Values are reachable both as attributes (``config.log``) and by key
    (``config["log"]``). Instances are immutable.
    """

    __slots__ = ("_values",)

    _values: dict[str, Any]

    def __init__(self, values: Mapping[str, Any]) -> None:
        object.__setattr__(self, "_values", dict(values))

    def __getattr__(self, name: str) -> Any:
        try:
            return self._values[name]
        except KeyError:
            raise AttributeError(name) from None

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("Namespace is immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("Namespace is immutable")

    def __getitem__(self, name: str) -> Any:
        return self._values[name]

    def __contains__(self, name: object) -> bool:
        return name in self._values

    def __iter__(self) -> Iterator[str]:
        return iter(self._values)

    def keys(self) -> Any:
        return self._values.keys()

    def values(self) -> Any:
        return self._values.values()

    def items(self) -> Any:
        return self._values.items()

    def as_dict(self) -> dict[str, Any]:
        """Return a shallow copy of the resolved values as a plain dict."""
        return dict(self._values)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Namespace):
            return self._values == other._values
        return NotImplemented

    def __hash__(self) -> int:
        return hash(tuple(sorted(self._values.items())))

    def __repr__(self) -> str:
        inner = ", ".join(f"{key}={value!r}" for key, value in self._values.items())
        return f"Namespace({inner})"
