"""A runnable argconfig example.

Try it:

    python examples/demo.py --console quiet --retries 5
    python examples/demo.py --log NONE
    MYTOOL_CONSOLE=dotted python examples/demo.py
    python examples/demo.py --help

Configuration is also read from ``[tool.mytool]`` in a discovered
``pyproject.toml`` and from ``MYTOOL_*`` environment variables.
"""

from __future__ import annotations

import argconfig
from argconfig import ArgConfig


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


def main() -> None:
    try:
        config = argconfig.ConfigurationProcessor(MyArgs).process()
    except argconfig.Exit as exit_signal:
        raise SystemExit(exit_signal.code) from None
    except argconfig.ArgConfigError as error:
        raise SystemExit(f"error: {error}") from None

    print("log     =", config.log)
    print("console =", config.console)
    print("retries =", config.retries)


if __name__ == "__main__":
    main()
