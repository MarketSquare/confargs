"""Tests for type resolution and value coercion."""

from __future__ import annotations

import pytest

from confargs import ArgConfig, collect_options, option
from confargs.coercion import ValueType, coerce_value, parse_bool, resolve_value_type
from confargs.exceptions import OptionValueError


class Types(ArgConfig):
    @option
    def text(self, value: str = "x") -> str:
        return value

    @option
    def maybe(self, value: str | None = None) -> str | None:
        return value

    @option
    def count(self, value: int = 0) -> int:
        return value

    @option
    def ratio(self, value: float = 1.0) -> float:
        return value

    @option
    def flag(self, value: bool = False) -> bool:
        return value

    @option
    def tags(self, value: list[str] | None = None) -> list[str] | None:
        return value

    @option
    def nums(self, value: list[int] = []) -> list[int]:  # noqa: B006 - test fixture
        return value

    @option
    def untyped(self, value="d"):  # type: ignore[no-untyped-def]
        return value


OPTIONS = collect_options(Types)


def _vt(name: str) -> ValueType:
    return resolve_value_type(OPTIONS[name])


def test_resolve_str() -> None:
    vt = _vt("text")
    assert vt.base is str
    assert vt.is_flag is False
    assert vt.allows_none is False


def test_resolve_optional_str() -> None:
    vt = _vt("maybe")
    assert vt.base is str
    assert vt.allows_none is True


def test_resolve_int_and_float() -> None:
    assert _vt("count").base is int
    assert _vt("ratio").base is float


def test_resolve_flag() -> None:
    vt = _vt("flag")
    assert vt.base is bool
    assert vt.is_flag is True


def test_resolve_list_types() -> None:
    tags = _vt("tags")
    assert tags.is_list is True
    assert tags.base is str
    assert tags.allows_none is True
    nums = _vt("nums")
    assert nums.is_list is True
    assert nums.base is int


def test_resolve_untyped_defaults_to_str() -> None:
    assert _vt("untyped").base is str


@pytest.mark.parametrize("raw", ["1", "true", "YES", "on", "t"])
def test_parse_bool_true(raw: str) -> None:
    assert parse_bool(raw) is True


@pytest.mark.parametrize("raw", ["0", "false", "No", "off", "f"])
def test_parse_bool_false(raw: str) -> None:
    assert parse_bool(raw) is False


def test_parse_bool_invalid() -> None:
    with pytest.raises(OptionValueError):
        parse_bool("maybe")


def test_coerce_int_from_string() -> None:
    assert coerce_value("42", _vt("count")) == 42


def test_coerce_int_invalid() -> None:
    with pytest.raises(OptionValueError):
        coerce_value("notanint", _vt("count"))


def test_coerce_float() -> None:
    assert coerce_value("3.5", _vt("ratio")) == 3.5


def test_coerce_bool_from_string() -> None:
    assert coerce_value("yes", _vt("flag")) is True


def test_coerce_str_passthrough() -> None:
    assert coerce_value("hello", _vt("text")) == "hello"


def test_coerce_none_allowed() -> None:
    assert coerce_value(None, _vt("maybe")) is None


def test_coerce_none_disallowed() -> None:
    with pytest.raises(OptionValueError):
        coerce_value(None, _vt("text"))


def test_coerce_list_from_native() -> None:
    assert coerce_value(["a", "b"], _vt("tags")) == ["a", "b"]


def test_coerce_list_from_csv_string() -> None:
    assert coerce_value("a, b ,c", _vt("tags")) == ["a", "b", "c"]


def test_coerce_list_of_ints() -> None:
    assert coerce_value(["1", "2"], _vt("nums")) == [1, 2]
    assert coerce_value([1, 2], _vt("nums")) == [1, 2]


def test_coerce_str_from_toml_int() -> None:
    # TOML may supply an int where the option wants a string.
    assert coerce_value(7, _vt("text")) == "7"
