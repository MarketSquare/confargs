"""Unit tests for the immutable :class:`~confargs.Namespace` result object."""

from __future__ import annotations

import pytest

from confargs import Namespace


def _ns() -> Namespace:
    return Namespace({"log": "out.html", "retries": 3})


def test_attribute_and_item_access() -> None:
    ns = _ns()
    assert ns.log == "out.html"
    assert ns["retries"] == 3


def test_unknown_attribute_raises_attribute_error() -> None:
    with pytest.raises(AttributeError):
        _ = _ns().missing


def test_contains() -> None:
    ns = _ns()
    assert "log" in ns
    assert "missing" not in ns


def test_iteration_yields_keys() -> None:
    assert sorted(_ns()) == ["log", "retries"]


def test_keys_values_items() -> None:
    ns = _ns()
    assert set(ns.keys()) == {"log", "retries"}
    assert set(ns.values()) == {"out.html", 3}
    assert dict(ns.items()) == {"log": "out.html", "retries": 3}


def test_as_dict_returns_shallow_copy() -> None:
    ns = _ns()
    data = ns.as_dict()
    assert data == {"log": "out.html", "retries": 3}
    data["log"] = "mutated"
    assert ns.log == "out.html"  # the copy is independent


def test_immutable_setattr() -> None:
    with pytest.raises(AttributeError):
        _ns().log = "nope"


def test_immutable_delattr() -> None:
    with pytest.raises(AttributeError):
        del _ns().log


def test_equality_and_hash() -> None:
    a = Namespace({"a": 1, "b": 2})
    b = Namespace({"b": 2, "a": 1})
    assert a == b
    assert hash(a) == hash(b)


def test_equality_with_non_namespace_is_not_implemented() -> None:
    assert (Namespace({"a": 1}) == {"a": 1}) is False


def test_repr_round_trips_values() -> None:
    text = repr(Namespace({"log": "out.html"}))
    assert text == "Namespace(log='out.html')"
