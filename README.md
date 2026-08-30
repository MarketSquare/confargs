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

    tool_name = "mytool"

    # Declarative option: no method needed when there's nothing to parse.
    title = confargs.option(name="title", default="report", help="Report title.")

    @confargs.option
    def log(self, value: str | None = "log.html") -> str | None:
        """HTML log file. Disable with the special value 'NONE'."""
        if value == "NONE":
            return None
        return value

    @confargs.option(name="console", short="c")
    def console(self, value: str = "verbose") -> str:
        choices = ["verbose", "dotted", "quiet", "none"]
        if value not in choices:
            raise confargs.OptionValueError(f"console must be one of {choices}")
        return value


config = confargs.ConfigurationProcessor(MyArgs).process()
print(config.title, config.log, config.console)
```

## Declaring options

Options come in two flavours:

- **Method-based** (`@confargs.option`): the decorated method receives the raw
  value and returns the parsed/validated result. Use this whenever you need to
  transform or validate the value.
- **Declarative** (`attr = confargs.option(name=..., help=...)`): a plain class
  attribute with no method, for simple values that need no custom handling. The
  value passes straight through coercion. Set `default=` (a `bool` makes it a
  flag, `None` makes it optional) and `type=` to control the value type — or
  annotate the attribute directly (`attr: int = confargs.option(...)`), which
  confargs reads as the value type. A **callable** `default` is treated as a
  factory (called to build the value), so `tags: list[str] = option(default=list)`
  gives a fresh `[]` — handy for list options that would otherwise need a
  mutable default.

## Precedence

Highest wins: **CLI > environment variables > nearest TOML > user-directory TOML > option default**.

## Configuration sources

### TOML files

Config is read from a table named after your tool. By default that is
`[tool.<tool_name>]` (e.g. `[tool.mytool]`); override it with
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

### Profiles

A **profile** is a named set of config overrides declared under
`<section>.profiles.<name>` in the same TOML file as your base section. Select
one or more at runtime with the built-in `--profile` option to layer them on top
of the base config:

```toml
[tool.mytool]
loglevel = "INFO"
console = "verbose"

[tool.mytool.profiles.ci]
loglevel = "DEBUG"
console = "dotted"

[tool.mytool.profiles.dev]
inherits = ["ci"]      # pull in ci's values first...
console = "verbose"    # ...then override
```

```console
$ mytool --profile ci            # exact name
$ mytool --profile 'ci-*'        # glob pattern
$ mytool --profile ci --profile extra   # multiple, merged in order
```

Semantics (a deliberately small subset of what a full profile system offers):

- **Selection** is by exact name or `fnmatch` glob; every pattern must match at
  least one profile or a `ConfigDiscoveryError` is raised.
- **Override, not extend** — a profile's values replace the base (and earlier
  profiles); this holds for lists too (they are replaced, not appended).
- **`inherits`** (a name or list of names) merges the parent profile(s) first,
  then the profile's own keys. Inheritance is resolved recursively; cycles are
  rejected.
- **`precedence`** (integer, default `0`) orders multiple selected profiles:
  lower is applied first, so a higher `precedence` wins on conflicts. Ties keep
  selection order.
- **`enabled = false`** skips a *directly selected* profile (inherited parents
  always contribute).

Profiles sit in the TOML layer of the precedence chain, so command-line
arguments and environment variables still win over any profile value. Profiles
are read from the nearest project config only; `inherits`, `precedence` and
`enabled` are reserved keys, not options.

### Inheriting other config files (`extends`)

A config section can pull in one or more *other* config files with the reserved
`extends` key, so shared settings live in one place and each project overrides
only what it needs:

```toml
# pyproject.toml
[tool.mytool]
extends = ["../shared/base.toml", "/etc/mytool/global.toml"]
loglevel = "DEBUG"   # overrides whatever the extended files set
```

Semantics:

- **Paths** may be relative (resolved against the file that declares `extends`)
  or absolute. A single string is accepted as shorthand for a one-item list.
- **Order** — extended files are merged in the order listed, then the declaring
  file's own keys are applied last. So later files override earlier ones, and
  the declaring file always wins.
- **Override, not extend** — like profiles, values (including lists) are
  *replaced*, never concatenated.
- **Recursive** — an extended file may itself `extends` further files; every
  file must contain the same section (`[tool.<tool_name>]`). Cycles are
  rejected with a `ConfigDiscoveryError`.

`extends` is a reserved key (stripped before option mapping) and applies to
whichever config layer declares it. Because it stays in the TOML layer,
environment variables and command-line arguments still take precedence.

### Environment variables

Reading from the environment is **opt-in per option**. Pass `env=True` to use a
generated name, or `env="MY_NAME"` for an explicit one:

```python
@option(env=True)  # reads $MYTOOL_LOG (from the class template)
def log(self, value: str = "log.html") -> str: ...


@option(env="LOG_FILE")  # reads $LOG_FILE
def log2(self, value: str = "log.html") -> str: ...
```

The generated name comes from the class `env_var_template` (default
`"{name}_{option}"`), formatted with the tool name and the `option` attribute
name and upper-cased — e.g. `MYTOOL_LOG`. Override it per class:

```python
class Args(ArgConfig):
    tool_name = "mytool"
    env_var_template = "MYTOOL_CFG_{option}"  # -> MYTOOL_CFG_LOG
```

#### Extra arguments from an environment variable

Some tools accept a whole *command line* from an environment variable —
`ROBOT_OPTIONS`, `PYTEST_ADDOPTS`, `GREP_OPTIONS` and similar. Opt in by setting
`options_env_var` on your class:

```python
class Args(ArgConfig):
    tool_name = "mytool"
    options_env_var = "MYTOOL_OPTIONS"
```

When that variable is set, its value is split with shell-like quoting and
**prepended** to `argv`, so anything typed on the real command line still wins
for scalar options, while repeatable options accumulate (env first, then CLI).
The injected tokens go through the normal pipeline, so they may even contain an
eager `--argumentfile`:

```bash
MYTOOL_OPTIONS="--log NONE --tag ci" mytool --tag smoke   # log=None, tags=[ci, smoke]
```

Quoting follows POSIX shell rules (`shlex`), so quote values containing spaces —
and, on Windows, quote paths so their backslashes survive
(`MYTOOL_OPTIONS='--out "C:\build\out"'`).

### Restricting where an option is read from

Two independent toggles control which sources feed an option:

- `@option(cli=False)` hides the option from the command line (no CLI names, not
  shown in `--help`) — use for options that should only come from config files
  or the environment.
- `@option(config=False)` stops the option being loaded from TOML config files —
  use for switches that control the tool run itself (the built-in discovery
  options above are defined this way).

Combine them as needed, e.g. a CLI-only switch is `@option(config=False)` with
`env` left off.

## Options in depth

- Long names come from the method name (`dry_run` → `--dry-run`); a short name
  is derived from the first letter when it is still free. Override either with
  `name="console"` and/or `short="c"` (passing `name` opts out of the implicit
  short — add `short=` to keep one).
- The value type is taken from the `value` parameter annotation. `bool` becomes
  a flag; `list[...]` becomes a repeatable option; `int`/`float`/`str` are
  coerced from strings. confargs performs this coercion *before* calling your
  method, so the `value` you receive already matches the annotated type.
- Your method receives the coerced value and returns the final one. Whatever it
  returns is stored as-is — including `None`, which is a legitimate value (e.g.
  a `--log NONE` that disables a file). There is no special "return nothing to
  keep the input" behaviour: if the method has no parsing or validation to do,
  declare the option as a plain attribute instead so the coerced value passes
  straight through. Raise `confargs.OptionValueError` to reject a value.
- Boolean options can be negated on the command line: `--verbose` sets it to
  `True`, `--no-verbose` sets it to `False`.
- A value that itself looks like a registered option (e.g. passing `-v` as the
  value of `--name` when `-v` is a known short option) is otherwise read as the
  next option. Use the attached form to force it as a value: `--name=-v` (or
  `-n-v` for a short option).

### Restricting a value to a set of choices

Annotate an option (or argument) with `typing.Literal[...]` to constrain it to a
fixed set of allowed values. confargs coerces the incoming value to the members'
type and then rejects anything outside the set with an `OptionValueError`; the
allowed values are also shown in `--help`:

```python
from typing import Literal

from confargs import ArgConfig, option


class Args(ArgConfig):
    console: Literal["verbose", "dotted", "quiet", "none"] = option(name="console", default="verbose")
    level: Literal[1, 2, 3] = option(name="level", default=1)
    langs: list[Literal["en", "pl"]] = option(name="langs", default=list)
```

The Literal may be optional (`Literal["a", "b"] | None`), wrapped in `list[...]`
for repeatable options, or supplied on a method's `value` parameter. Non-string
members (e.g. `Literal[1, 2, 3]`) are coerced before the membership check.

### Eager options and argument files

Mark an option `is_eager=True` to resolve it *before* every other source,
directly against `argv`. The method's return value — an iterable of tokens or
`None` — replaces the option's own arguments, so it can inject more options.
This is how an `--argumentfile` option expands a file (Robot Framework style)
into extra arguments, including nested argument files:

```python
from confargs import ArgConfig, option, read_argument_file


class Args(ArgConfig):
    @option(name="argumentfile", short="A", config=False, is_eager=True)
    def argumentfile(self, value: str | None = None) -> list[str] | None:
        return read_argument_file(value) if value else None
```

`ConfigurationProcessor(Args, argv=[...])` accepts an explicit argument list;
when omitted it falls back to `sys.argv[1:]`.

## Positional arguments

Options are addressed by name; **arguments** are positional — filled from the
leftover, non-option tokens in declaration order. They mirror the two option
spellings (a method for parsing/validation, or a plain attribute for
pass-through) and share the same coercion path. Declare them with
`confargs.argument(...)`:

```python
import confargs
from confargs import ArgConfig, argument


class Runner(ArgConfig):
    tool_name = "runner"

    # A required single positional.
    suite = argument(name="suite", help="Suite file to run.")

    # An optional one (used only when present).
    tag = argument(name="tag", nargs="?", default=None, help="Only run this tag.")

    # A variadic one that collects the rest into a list.
    @argument(nargs="*")
    def data_sources(self, value: list[str]) -> list[str]:
        """Extra data source paths."""
        return value
```

`nargs` controls how many positionals an argument consumes:

- `1` (default) — exactly one; required unless a `default` is given.
- `"?"` — at most one; the `default` is used when it is absent.
- `"*"` — zero or more, collected into a list (default `[]`).
- `"+"` — one or more, collected into a list; required.

Only one variadic argument (`"*"`/`"+"`) is allowed and it must be declared
last. Arguments are also read from TOML config by their **name**
(`suite = "smoke.robot"` in the tool's section), with command-line positionals
taking precedence. Resolved values appear on the `Namespace` alongside options —
so avoid names that clash with `Namespace` methods (`keys`, `values`, `items`,
`as_dict`).

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
