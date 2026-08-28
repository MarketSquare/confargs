# Changelog

All notable changes to **confargs** are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **Pre-1.0 note:** while the version is `0.x.y`, the public API is still
> stabilising. Minor (`0.X.0`) releases may include breaking changes; patch
> (`0.x.Y`) releases are reserved for backwards-compatible fixes.

## [Unreleased]

### Changed

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
