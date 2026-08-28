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

## Configuration sources

### TOML files

Config is read from a table named after your tool. By default that is
`[tool.<name>]` (e.g. `[tool.mytool]`); override it with
`default_config_section = "tool.custom"`. The file names searched are set with
`config_names` (default `["pyproject.toml"]`). Both `dashed-keys` and
`snake_case_keys` are accepted.

```toml
[tool.mytool]
log = "results.html"
console = "dotted"
tags = ["ci", "nightly"]
```

**Discovery** walks up from the current directory looking for those files and
stops at the project root (a directory containing `.git`). If nothing is found,
a per-user config directory is consulted (`%APPDATA%\<name>` on Windows,
`$XDG_CONFIG_HOME/<name>` otherwise). Discovery is controlled by built-in,
CLI-only options:

- `--config PATH` — use only this file, skip discovery.
- `--no-config` — ignore config files entirely.
- `--ignore-git` — keep searching above the `.git` project root.

By default (`strict_config = True`) unknown keys — and any `cli_only` option —
found in the config section raise an error, which catches typos early. Set
`strict_config = False` on your class to silently ignore them instead.

### Environment variables

Set a name per option with `@option(envvar="MYTOOL_LOG")`, or enable
`auto_env_vars = True` on the class to expose every non-`cli_only` option as
`<NAME>_<OPTION>` (e.g. `MYTOOL_CONSOLE`).

### CLI-only options

Options marked `@option(cli_only=True)` are never read from TOML or the
environment — use this for switches that control the tool run itself (the
built-in discovery options above are defined this way).

## Options in depth

- Long names come from the method name (`dry_run` → `--dry-run`); a short name
  is derived from the first letter when it is still free. Override with
  `names="--console/-c"`.
- The value type is taken from the `value` parameter annotation. `bool` becomes
  a flag; `list[...]` becomes a repeatable option; `int`/`float`/`str` are
  coerced from strings. Your method receives the coerced value and returns the
  final one — raise `argconfig.OptionValueError` to reject it.
- Boolean options can be negated on the command line: `--verbose` sets it to
  `True`, `--no-verbose` sets it to `False`.

## Example

A runnable example lives in [`examples/demo.py`](examples/demo.py):

```bash
uv run python examples/demo.py --console quiet --retries 5
uv run python examples/demo.py --help
```

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

## Publishing

Releases are published to PyPI by `.github/workflows/publish.yml` when a GitHub
Release is published. It uses [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/)
(OIDC), so no API token is stored in the repository — configure the project as a
trusted publisher on PyPI (workflow `publish.yml`, environment `pypi`) once.

## License

MIT
