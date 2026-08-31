"""Tests for callable ``default`` factories on options and arguments."""

from __future__ import annotations

import confargs
from confargs import ArgConfig, argument, option


def _run(cls: type[ArgConfig], argv: list[str], **kw: object) -> confargs.Namespace:
    return confargs.ConfigurationProcessor(cls, argv=argv, environ={}, **kw).process()


class Factories(ArgConfig):
    """A tool using factory defaults."""

    tool_name = "factories"

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
        tool_name = "custom"
        entries: list[str] = option(name="entries", default=lambda: ["seed"])

    assert _run(Custom, []).entries == ["seed"]


def test_non_callable_default_unchanged() -> None:
    class Plain(ArgConfig):
        tool_name = "plain"
        title: str = option(name="title", default="report")
        count: int = option(name="count", default=3)

    ns = _run(Plain, [])
    assert ns.title == "report"
    assert ns.count == 3


def test_method_option_with_factory_default() -> None:
    class Method(ArgConfig):
        tool_name = "method"

        @option(name="names")
        def names(self, value: list[str] = list) -> list[str]:  # type: ignore[assignment]
            return value

    assert _run(Method, []).names == []


def test_unannotated_list_factory_is_repeatable() -> None:
    # A factory default (``default=list``) is a list even without an annotation:
    # type inference samples the factory rather than using ``type(list)``.
    class Bare(ArgConfig):
        tool_name = "bare"
        tags = option(name="tags", default=list)

    assert _run(Bare, []).tags == []
    assert _run(Bare, ["--tags", "a", "--tags", "b"]).tags == ["a", "b"]


def test_unannotated_lambda_list_factory_is_repeatable() -> None:
    class Seeded(ArgConfig):
        tool_name = "seeded"
        tags = option(name="tags", default=lambda: ["seed"])

    assert _run(Seeded, []).tags == ["seed"]
    assert _run(Seeded, ["--tags", "x", "--tags", "y"]).tags == ["x", "y"]


def test_unannotated_variadic_argument_factory_is_list() -> None:
    class Args(ArgConfig):
        tool_name = "args"
        extra = argument(name="extra", nargs="*", default=list)

    assert _run(Args, []).extra == []
    assert _run(Args, ["p", "q"]).extra == ["p", "q"]
