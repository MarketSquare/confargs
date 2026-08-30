"""Tests for callable ``default`` factories on options and arguments."""

from __future__ import annotations

import confargs
from confargs import ArgConfig, argument, option


def _run(cls: type[ArgConfig], argv: list[str], **kw: object) -> confargs.Namespace:
    return confargs.ConfigurationProcessor(cls, argv=argv, environ={}, **kw).process()


class Factories(ArgConfig):
    """A tool using factory defaults."""

    name = "factories"

    tags: list[str] = option(name="tags", default=list)
    meta: dict = option(name="meta", type=dict, default=dict)
    extra: list[str] = argument(name="extra", nargs="*", default=list)


def test_list_factory_default_is_empty() -> None:
    ns = _run(Factories, [])
    assert ns.tags == []
    assert ns.extra == []


def test_dict_factory_default_is_empty() -> None:
    assert _run(Factories, []).meta == {}


def test_factory_default_not_used_when_value_supplied() -> None:
    ns = _run(Factories, ["--tags", "a", "--tags", "b", "p"])
    assert ns.tags == ["a", "b"]
    assert ns.extra == ["p"]


def test_factory_produces_fresh_value_each_time() -> None:
    first = _run(Factories, [])
    first.tags.append("mutated")
    second = _run(Factories, [])
    assert second.tags == []


def test_lambda_factory() -> None:
    class Custom(ArgConfig):
        name = "custom"
        entries: list[str] = option(name="entries", default=lambda: ["seed"])

    assert _run(Custom, []).entries == ["seed"]


def test_non_callable_default_unchanged() -> None:
    class Plain(ArgConfig):
        name = "plain"
        title: str = option(name="title", default="report")
        count: int = option(name="count", default=3)

    ns = _run(Plain, [])
    assert ns.title == "report"
    assert ns.count == 3


def test_method_option_with_factory_default() -> None:
    class Method(ArgConfig):
        name = "method"

        @option(name="names")
        def names(self, value: list[str] = list) -> list[str]:  # type: ignore[assignment]
            return value

    assert _run(Method, []).names == []
