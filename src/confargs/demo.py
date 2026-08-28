"""A small, runnable example tool built with confargs.

This module doubles as the ``confargs-demo`` console script (see
``[project.scripts]`` in ``pyproject.toml``). Try it once installed::

    confargs-demo --console quiet --retries 5
    confargs-demo --log NONE
    MYTOOL_CONSOLE=dotted confargs-demo
    confargs-demo --help

Or without installing::

    uv run confargs-demo --console quiet

Configuration is also read from ``[tool.mytool]`` in a discovered
``pyproject.toml`` and from ``MYTOOL_*`` environment variables.
"""

from __future__ import annotations

import confargs
from confargs import ArgConfig

__all__ = ["MyArgs", "main"]


class MyArgs(ArgConfig):
    """mytool - a tiny demo CLI built with confargs.

    Shows how command line arguments, environment variables and TOML config are
    merged into one configuration object.
    """

    name = "mytool"

    @confargs.option(env=True)
    def log(self, value: str | None = "log.html") -> str | None:
        """HTML log file. Disable with the special value 'NONE'."""
        if value == "NONE":
            return None
        return value

    @confargs.option(names="--console/-c", env=True)
    def console(self, value: str = "verbose") -> str:
        """Console output mode: verbose, dotted, quiet or none."""
        choices = ["verbose", "dotted", "quiet", "none"]
        if value not in choices:
            raise confargs.OptionValueError(f"console must be one of {choices}, got {value!r}")
        return value

    @confargs.option(env=True)
    def retries(self, value: int = 3) -> int:
        """Number of retries on failure."""
        if value < 0:
            raise confargs.OptionValueError("retries must be >= 0")
        return value


def main(argv: list[str] | None = None) -> int:
    """Entry point for the ``confargs-demo`` console script."""
    try:
        config = confargs.ConfigurationProcessor(MyArgs, argv=argv).process()
    except confargs.Exit as exit_signal:
        return exit_signal.code
    except confargs.ArgConfigError as error:
        print(f"error: {error}")
        return 2

    print("log     =", config.log)
    print("console =", config.console)
    print("retries =", config.retries)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
