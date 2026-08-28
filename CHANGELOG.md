# Changelog

All notable changes to **confargs** are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **Pre-1.0 note:** while the version is `0.x.y`, the public API is still
> stabilising. Minor (`0.X.0`) releases may include breaking changes; patch
> (`0.x.Y`) releases are reserved for backwards-compatible fixes.

## [0.2.0](https://github.com/MarketSquare/confargs/compare/v0.1.0...v0.2.0) (2026-08-28)


### Features

* add argconfig-demo console entry-point ([d0249d8](https://github.com/MarketSquare/confargs/commit/d0249d83c0d37ab1e71d10ef41d4a9d79ad80b0a))
* add ConfigurationProcessor, Namespace and discovery controls ([8395145](https://github.com/MarketSquare/confargs/commit/83951450a7b9b81d6f47bb72cd2b0da64f61a373))
* add core option model and ArgConfig base ([a5e1c4d](https://github.com/MarketSquare/confargs/commit/a5e1c4d15c0bc6a4d1a4ce79a7cd69a12c6361a5))
* add eager options and argument-file expansion ([b6837bd](https://github.com/MarketSquare/confargs/commit/b6837bd4fda7c10efccb4bacd5fab420475ca7f9))
* add environment-variable source ([8b34439](https://github.com/MarketSquare/confargs/commit/8b34439eb153be00fd443eff0dcaba4ced96b4f2))
* add minimal command-line tokenizer ([e2c07bd](https://github.com/MarketSquare/confargs/commit/e2c07bd00c4ea8b3cb4f793b37b041dbce90ffd0))
* add TOML loading and config file discovery ([3e8171c](https://github.com/MarketSquare/confargs/commit/3e8171c18b3da3e49b658453fb7dc1a785ddfddf))
* add type resolution and value coercion ([3976797](https://github.com/MarketSquare/confargs/commit/397679794170b008feb256d320b72022069c0450))
* generate help text from docstrings ([13cd88c](https://github.com/MarketSquare/confargs/commit/13cd88c1738ebc480ef2575072140b431f70294a))
* support boolean flag negation with --no- prefix ([3d44e05](https://github.com/MarketSquare/confargs/commit/3d44e05746bfa050dbb436160b61c83564b21aab))
* validate config keys with strict_config mode ([f707858](https://github.com/MarketSquare/confargs/commit/f7078587200155f8122c725f9dc8b30fa4cec64e))


### Documentation

* add publishing workflow, example and expanded README ([6f266d8](https://github.com/MarketSquare/confargs/commit/6f266d88cebdd66f55833eae7badecb0ab837cae))
* make examples/ a self-contained runnable example ([73a0948](https://github.com/MarketSquare/confargs/commit/73a094831a85cd0e86a00b570fd03e2f4cbc608d))


### Build System

* single-source version and add CHANGELOG ([690efd9](https://github.com/MarketSquare/confargs/commit/690efd9b7017270a262ab13d75641891c73ca959))

## [Unreleased]

### Added

- Options can now be declared **without a method**, as a plain class attribute:
  `title = option(name="title", default="report", help="Report title.")`. Such
  declarative options pass their value straight through coercion — use them for
  simple values that need no custom parsing or validation. `default=` sets the
  default (a `bool` makes it a flag, `None` makes it optional) and `type=`
  overrides the inferred value type. Method-based `@option` declarations are
  unchanged.

### Changed

- Reworked option naming: `@option` now takes `name=` (the long option name,
  without dashes) and `short=` (a single-character short name) instead of the
  combined `names="--long/-s"` spec. An explicit `name` opts out of the
  auto-derived short — pass `short=` to keep one. **Migration (pre-1.0):**
  replace `names="--console/-c"` with `name="console", short="c"`.
- Environment-variable reading is now **opt-in per option** via `@option(env=...)`:
  `env=True` uses a name from the class `env_var_template` (default
  `"{name}_{option}"`, upper-cased), and `env="NAME"` sets an explicit name.
  **Breaking:** the `envvar=` option argument and the `auto_env_vars` class
  attribute are removed; add `env=` to each option that should read the
  environment. The new `env_var_template` class attribute customises generated
  names.
- Replaced the single `@option(cli_only=True)` flag with two independent
  toggles: `@option(cli=False)` hides an option from the command line, and
  `@option(config=False)` stops it being loaded from TOML config files. The
  built-in discovery options now use `config=False`. **Breaking:** `cli_only` is
  no longer accepted.
- Renamed the distribution and import package from `argconfig` to **`confargs`**
  (the `argconfig` name was already taken on PyPI). The `ArgConfig` base class
  keeps its name.

### Added

- Eager options (`@option(is_eager=True)`): resolved before every other source,
  directly against `argv`. An eager option's method returns tokens that replace
  its own arguments, enabling argument-file expansion.
- `confargs.split_argument_file` / `confargs.read_argument_file` helpers that
  parse Robot Framework-style argument files (comment lines, `name value` and
  `name=value` forms) into argv tokens, including nested argument files.

## [0.1.0] - 2026-08-28

Initial development release.

### Added

- Declarative option model: options are methods on an `ArgConfig` subclass
  decorated with `@option`, receiving the raw value and returning the final one.
- `ConfigurationProcessor` that merges sources with precedence
  **CLI > environment variables > nearest TOML > user-directory TOML > default**
  and returns an immutable `Namespace` (attribute and item access).
- Minimal command-line tokenizer: long/short options, `--opt=value`, attached
  and combined short flags, repeatable list options, `--` terminator and
  positional collection.
- Boolean flag negation via `--no-<flag>`.
- Type coercion from strings and native TOML values (`str`, `int`, `float`,
  `bool`, `list[...]`, `Optional`).
- TOML discovery that walks up to the `.git` project root, with `--config`,
  `--no-config` and `--ignore-git` controls and a per-user config fallback.
- `strict_config` mode (default on) that rejects unknown or cli-only keys in a
  config section.
- Environment-variable source via explicit `envvar=` or `auto_env_vars`.
- Help generation from class and option docstrings; built-in `--help`.
- `confargs-demo` console entry-point and runnable example.
- Tooling: uv project, ruff, mypy (strict), pytest, pre-commit, CI matrix
  (Python 3.10-3.13 on Linux and Windows) and a PyPI trusted-publishing
  workflow.

[Unreleased]: https://github.com/MarketSquare/confargs/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/MarketSquare/confargs/releases/tag/v0.1.0
