"""Self-contained example CLI built with confargs.

Unlike the packaged ``confargs-demo`` console script (which lives in
``confargs.demo``), this file is a complete, copy-pasteable tool: everything a
reader needs is in one place. It demonstrates the main features in one go —
value options, a repeatable flag with ``--no-`` negation, environment variables
and an eager ``--argumentfile``.

Run it directly from a checkout, no install required::

    uv run python examples/demo.py --who Ada --repeat 3
    uv run python examples/demo.py --no-color          # boolean flag negation
    GREETER_WHO=Ada uv run python examples/demo.py      # environment variable
    uv run python examples/demo.py -A examples/example.args   # argument file
    uv run python examples/demo.py --help

Values are merged from, highest priority first: command line, then
``GREETER_*`` environment variables, then a ``[tool.greeter]`` table in a
discovered ``pyproject.toml``, and finally each option's default.
"""

from __future__ import annotations

import confargs
from confargs import ArgConfig


class Greeter(ArgConfig):
    """greeter - a tiny self-contained CLI built with confargs."""

    name = "greeter"
    # Expose GREETER_<OPTION> for every option that is not cli_only.
    auto_env_vars = True

    @confargs.option(names="--argumentfile/-A", cli_only=True, is_eager=True)
    def argumentfile(self, value: str | None = None) -> list[str] | None:
        """Read more command-line arguments from a file (resolved first)."""
        return confargs.read_argument_file(value) if value else None

    @confargs.option
    def who(self, value: str = "World") -> str:
        """Who to greet."""
        return value

    @confargs.option
    def repeat(self, value: int = 1) -> int:
        """How many times to print the greeting."""
        if value < 1:
            raise confargs.OptionValueError("repeat must be >= 1")
        return value

    @confargs.option
    def color(self, value: bool = True) -> bool:
        """Colorize the output. Disable with --no-color."""
        return value


def main(argv: list[str] | None = None) -> int:
    """Resolve configuration and print the greeting."""
    try:
        config = confargs.ConfigurationProcessor(Greeter, argv=argv).process()
    except confargs.Exit as exit_signal:
        return exit_signal.code
    except confargs.ArgConfigError as error:
        print(f"error: {error}")
        return 2

    greeting = f"Hello, {config.who}!"
    if config.color:
        greeting = f"\033[36m{greeting}\033[0m"
    for _ in range(config.repeat):
        print(greeting)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
