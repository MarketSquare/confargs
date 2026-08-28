"""Runnable example wrapper.

The implementation lives in :mod:`confargs.demo` (installed as the
``confargs-demo`` console script). This file lets you run the same example
directly from a checkout:

    uv run python examples/demo.py --console quiet --retries 5
    uv run python examples/demo.py --help
"""

from __future__ import annotations

from confargs.demo import MyArgs, main

__all__ = ["MyArgs", "main"]


if __name__ == "__main__":
    raise SystemExit(main())
