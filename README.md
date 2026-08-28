# argconfig

> ⚠️ Early development. APIs may change.

**argconfig** is a small, declarative CLI argument parser for Python 3.10+ that
merges configuration from three sources into one result:

1. **Command line** arguments (`--log out.html`, `-l NONE`)
2. **Environment variables** (per-option or auto-generated)
3. **TOML config files** (discovered by walking up from the current directory,
   `pyproject.toml`-style)

You describe options as **methods** on a class. Each method receives the raw
value from whichever source supplied it, performs any parsing/validation you
like, and returns the final value. argconfig handles discovery, precedence and
basic type coercion; your code owns the domain logic.

```python
import argconfig
from argconfig import ArgConfig


class MyArgs(ArgConfig):
    """My CLI tool.

    Longer description shown in --help.
    """

    name = "mytool"

    @argconfig.option
    def log(self, value: str | None = "log.html") -> str | None:
        """HTML log file. Disable with the special value 'NONE'."""
        if value == "NONE":
            return None
        return value

    @argconfig.option(names="--console/-c")
    def console(self, value: str = "verbose") -> str:
        choices = ["verbose", "dotted", "quiet", "none"]
        if value not in choices:
            raise argconfig.OptionValueError(f"console must be one of {choices}")
        return value


config = argconfig.ConfigurationProcessor(MyArgs).process()
print(config.log, config.console)
```

## Precedence

Highest wins: **CLI > environment variables > nearest TOML > user-directory TOML > option default**.

## Development

This project uses [uv](https://docs.astral.sh/uv/).

```bash
uv sync                 # create the environment
uv run pytest           # run the tests
uv run ruff check       # lint
uv run ruff format      # format
uv run mypy             # type-check
pre-commit install      # enable git hooks
```

## License

MIT
