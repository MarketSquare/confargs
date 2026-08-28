# confargs

> ⚠️ Early development. APIs may change.

**confargs** is a small, declarative CLI argument parser for Python 3.10+ that
merges configuration from three sources into one result:

1. **Command line** arguments (`--log out.html`, `-l NONE`)
2. **Environment variables** (per-option or auto-generated)
3. **TOML config files** (discovered by walking up from the current directory,
   `pyproject.toml`-style)

You describe options as **methods** on a class. Each method receives the raw
value from whichever source supplied it, performs any parsing/validation you
like, and returns the final value. confargs handles discovery, precedence and
basic type coercion; your code owns the domain logic.

```python
import confargs
from confargs import ArgConfig


class MyArgs(ArgConfig):
    """My CLI tool.

    Longer description shown in --help.
    """

    name = "mytool"

    @confargs.option
    def log(self, value: str | None = "log.html") -> str | None:
        """HTML log file. Disable with the special value 'NONE'."""
        if value == "NONE":
            return None
        return value

    @confargs.option(names="--console/-c")
    def console(self, value: str = "verbose") -> str:
        choices = ["verbose", "dotted", "quiet", "none"]
        if value not in choices:
            raise confargs.OptionValueError(f"console must be one of {choices}")
        return value


config = confargs.ConfigurationProcessor(MyArgs).process()
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

By default (`strict_config = True`) unknown keys — and any option declared with
`config=False` — found in the config section raise an error, which catches typos
early. Set `strict_config = False` on your class to silently ignore them instead.

### Environment variables

Set a name per option with `@option(envvar="MYTOOL_LOG")`, or enable
`auto_env_vars = True` on the class to expose every configurable option as
`<NAME>_<OPTION>` (e.g. `MYTOOL_CONSOLE`).

### Restricting where an option is read from

Two independent toggles control which sources feed an option:

- `@option(cli=False)` hides the option from the command line (no CLI names, not
  shown in `--help`) — use for options that should only come from config files
  or the environment.
- `@option(config=False)` stops the option being loaded from TOML config files —
  use for switches that control the tool run itself (the built-in discovery
  options above are defined this way).

Combine them as needed, e.g. a CLI-only switch is `@option(config=False)` with
no `envvar`.

## Options in depth

- Long names come from the method name (`dry_run` → `--dry-run`); a short name
  is derived from the first letter when it is still free. Override with
  `names="--console/-c"`.
- The value type is taken from the `value` parameter annotation. `bool` becomes
  a flag; `list[...]` becomes a repeatable option; `int`/`float`/`str` are
  coerced from strings. Your method receives the coerced value and returns the
  final one — raise `confargs.OptionValueError` to reject it.
- Boolean options can be negated on the command line: `--verbose` sets it to
  `True`, `--no-verbose` sets it to `False`.

### Eager options and argument files

Mark an option `is_eager=True` to resolve it *before* every other source,
directly against `argv`. The method's return value — an iterable of tokens or
`None` — replaces the option's own arguments, so it can inject more options.
This is how an `--argumentfile` option expands a file (Robot Framework style)
into extra arguments, including nested argument files:

```python
from confargs import ArgConfig, option, read_argument_file


class Args(ArgConfig):
    @option(names="--argumentfile/-A", config=False, is_eager=True)
    def argumentfile(self, value: str | None = None) -> list[str] | None:
        return read_argument_file(value) if value else None
```

`ConfigurationProcessor(Args, argv=[...])` accepts an explicit argument list;
when omitted it falls back to `sys.argv[1:]`.

## Example

A complete, self-contained example lives in [`examples/demo.py`](examples/demo.py)
(with a sample [`examples/example.args`](examples/example.args) and
[`examples/README.md`](examples/README.md)). It's a single copy-pasteable file
showing value options, `--no-` flag negation, environment variables and an
eager `--argumentfile`. Run it from a checkout without installing anything:

```bash
uv run python examples/demo.py --who Ada --repeat 3
uv run python examples/demo.py -A examples/example.args
uv run python examples/demo.py --help
```

Separately, the packaged [`confargs.demo`](src/confargs/demo.py) module is
installed as the `confargs-demo` console script via `[project.scripts]`:

```bash
uv run confargs-demo --console quiet --retries 5
uv run confargs-demo --help
```

To ship your own tool, point a console script at a `main()` that runs the
processor, for example in `pyproject.toml`:

```toml
[project.scripts]
mytool = "mytool.cli:main"
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

## Versioning

confargs follows [Semantic Versioning](https://semver.org/). The version is
single-sourced from `__version__` in `src/confargs/__init__.py` (hatchling reads
it at build time). While the project is `0.x.y` the API is still stabilising, so
minor releases may include breaking changes. Notable changes are recorded in
[`CHANGELOG.md`](CHANGELOG.md).

Releases are automated with
[release-please](https://github.com/googleapis/release-please): merging
[Conventional Commits](https://www.conventionalcommits.org/) to `main` keeps an
open release PR that bumps `__version__`, updates the changelog and, once merged,
tags the release and publishes to PyPI. Pre-1.0, breaking changes bump the minor
version (`bump-minor-pre-major`).

## License

MIT
