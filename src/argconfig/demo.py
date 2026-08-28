"""A small, runnable example tool built with argconfig.

This module doubles as the ``argconfig-demo`` console script (see
``[project.scripts]`` in ``pyproject.toml``). Try it once installed::

    argconfig-demo --console quiet --retries 5
    argconfig-demo --log NONE
    MYTOOL_CONSOLE=dotted argconfig-demo
    argconfig-demo --help

Or without installing::

    uv run argconfig-demo --console quiet

Configuration is also read from ``[tool.mytool]`` in a discovered
``pyproject.toml`` and from ``MYTOOL_*`` environment variables.
"""

from __future__ import annotations

import argconfig
from argconfig import ArgConfig

__all__ = ["MyArgs", "main"]


class MyArgs(ArgConfig):
    """mytool - a tiny demo CLI built with argconfig.

    Shows how command line arguments, environment variables and TOML config are
    merged into one configuration object.
    """

    name = "mytool"
    auto_env_vars = True

    @argconfig.option
    def log(self, value: str | None = "log.html") -> str | None:
        """HTML log file. Disable with the special value 'NONE'."""
        if value == "NONE":
            return None
        return value

    @argconfig.option(names="--console/-c")
    def console(self, value: str = "verbose") -> str:
        """Console output mode: verbose, dotted, quiet or none."""
        choices = ["verbose", "dotted", "quiet", "none"]
        if value not in choices:
            raise argconfig.OptionValueError(f"console must be one of {choices}, got {value!r}")
        return value

    @argconfig.option
    def retries(self, value: int = 3) -> int:
        """Number of retries on failure."""
        if value < 0:
            raise argconfig.OptionValueError("retries must be >= 0")
        return value


def main(argv: list[str] | None = None) -> int:
    """Entry point for the ``argconfig-demo`` console script."""
    try:
        config = argconfig.ConfigurationProcessor(MyArgs, argv=argv).process()
    except argconfig.Exit as exit_signal:
        return exit_signal.code
    except argconfig.ArgConfigError as error:
        print(f"error: {error}")
        return 2

    print("log     =", config.log)
    print("console =", config.console)
    print("retries =", config.retries)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
