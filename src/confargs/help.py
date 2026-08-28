"""Help-text generation from class and option docstrings."""

from __future__ import annotations

import inspect
from textwrap import shorten
from typing import TYPE_CHECKING

from confargs.cli import negation_name
from confargs.coercion import resolve_value_type
from confargs.options import collect_options, resolve_names

if TYPE_CHECKING:
    from confargs.base import ArgConfig
    from confargs.options import NameTable, Option

_MAX_INVOCATION_WIDTH = 30


def _order_names(names: list[str]) -> list[str]:
    """Short names first (``-h, --help``), each group kept stable."""
    shorts = [n for n in names if not n.startswith("--")]
    longs = [n for n in names if n.startswith("--")]
    return shorts + longs


def _metavar(attr: str, opt: Option) -> str:
    vt = resolve_value_type(opt)
    if vt.is_flag:
        return ""
    base = attr.upper()
    return f" {base}..." if vt.is_list else f" {base}"


def _invocation(attr: str, opt: Option, table: NameTable) -> str:
    names = _order_names(table.attr_to_names.get(attr, [f"--{attr}"]))
    vt = resolve_value_type(opt)
    if vt.is_flag:
        longs = [n for n in names if n.startswith("--")]
        if longs and not longs[0].startswith("--no-"):
            names = [*names, negation_name(longs[0])]
    return ", ".join(names) + _metavar(attr, opt)


def _summary(opt: Option) -> str:
    doc = opt.doc.strip()
    if not doc:
        return ""
    first_paragraph = doc.split("\n\n", 1)[0].replace("\n", " ")
    return shorten(first_paragraph, width=200, placeholder="...")


def format_help(instance: ArgConfig) -> str:
    """Build the full ``--help`` text for a config instance."""
    cls = type(instance)
    options = collect_options(cls)
    table = resolve_names(options)

    lines: list[str] = []
    doc = inspect.getdoc(cls)
    if doc:
        lines.append(doc)
        lines.append("")

    invocations = {attr: _invocation(attr, opt, table) for attr, opt in options.items() if opt.cli}
    pad = min(max((len(text) for text in invocations.values()), default=0), _MAX_INVOCATION_WIDTH)

    lines.append("Options:")
    for attr, opt in options.items():
        if not opt.cli:
            continue
        invocation = invocations[attr]
        summary = _summary(opt)
        if not summary:
            lines.append(f"  {invocation}")
        elif len(invocation) <= pad:
            lines.append(f"  {invocation.ljust(pad)}  {summary}")
        else:
            lines.append(f"  {invocation}")
            lines.append(f"  {' ' * pad}  {summary}")
    return "\n".join(lines)
