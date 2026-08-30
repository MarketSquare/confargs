"""Tests for reading an option/argument's type from its attribute annotation."""

from __future__ import annotations

import confargs
from confargs import ArgConfig, argument, option


def _run(cls: type[ArgConfig], argv: list[str], **kw: object) -> confargs.Namespace:
    return confargs.ConfigurationProcessor(cls, argv=argv, environ={}, **kw).process()


class Annotated(ArgConfig):
    """A tool whose declarative options carry attribute annotations."""

    tool_name = "annotated"

    title: str = option(name="title", default="report")
    retries: int = option(name="retries", default=3)
    ratio: float = option(name="ratio", default=1.0)
    verbose: bool = option(name="verbose", default=False)
    tags: list[str] = option(name="tags", default=[])
    out: str | None = option(name="out", default=None)

    src: str = argument(name="src")


def test_int_annotation_coerces() -> None:
    ns = _run(Annotated, ["--retries", "5", "file"])
    assert ns.retries == 5
    assert isinstance(ns.retries, int)


def test_float_annotation_coerces() -> None:
    ns = _run(Annotated, ["--ratio", "2.5", "file"])
    assert ns.ratio == 2.5


def test_bool_annotation_becomes_flag() -> None:
    assert _run(Annotated, ["--verbose", "file"]).verbose is True
    assert _run(Annotated, ["--no-verbose", "file"]).verbose is False


def test_list_annotation_is_repeatable() -> None:
    ns = _run(Annotated, ["--tags", "a", "--tags", "b", "file"])
    assert ns.tags == ["a", "b"]


def test_optional_annotation_allows_none() -> None:
    assert _run(Annotated, ["file"]).out is None


def test_argument_annotation_used() -> None:
    class Nums(ArgConfig):
        tool_name = "nums"
        count: int = argument(name="count")

    assert _run(Nums, ["7"]).count == 7


def test_explicit_type_overrides_annotation() -> None:
    class Mixed(ArgConfig):
        tool_name = "mixed"
        # Annotation says str, but explicit type= wins.
        value: str = option(name="value", type=int, default=0)

    assert _run(Mixed, ["--value", "42"]).value == 42


def test_annotation_absent_falls_back_to_default_inference() -> None:
    class NoAnno(ArgConfig):
        tool_name = "noanno"
        count = option(name="count", default=3)

    assert _run(NoAnno, ["--count", "9"]).count == 9
