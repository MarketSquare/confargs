# Changelog

All notable changes to **confargs** are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **Pre-1.0 note:** while the version is `0.x.y`, the public API is still
> stabilising. Minor (`0.X.0`) releases may include breaking changes; patch
> (`0.x.Y`) releases are reserved for backwards-compatible fixes.

## [0.2.0](https://github.com/MarketSquare/confargs/compare/v0.1.0...v0.2.0) (2026-08-28)


### Features

* add argconfig-demo console entry-point ([8c1c986](https://github.com/MarketSquare/confargs/commit/8c1c986119b5fcb6fb418202ac6ac80821ad3d9b))
* add ConfigurationProcessor, Namespace and discovery controls ([19637b2](https://github.com/MarketSquare/confargs/commit/19637b21d24bc47537ba0ee65c66c7a94d9eccb8))
* add core option model and ArgConfig base ([1b0c0c9](https://github.com/MarketSquare/confargs/commit/1b0c0c91d9b849c9847906ced0f60c17337082c7))
* add eager options and argument-file expansion ([2d15a48](https://github.com/MarketSquare/confargs/commit/2d15a48c7a120373c517311a5b28b2cfaa382a98))
* add environment-variable source ([a31c7a1](https://github.com/MarketSquare/confargs/commit/a31c7a148e2aca5ac27f2cb27fb76cddfdde24cd))
* add minimal command-line tokenizer ([1012350](https://github.com/MarketSquare/confargs/commit/10123507c0ebe40afc9d2ceaad691c2369ec2dcd))
* add TOML loading and config file discovery ([3b44edd](https://github.com/MarketSquare/confargs/commit/3b44edd20566c151065c4c3d3d2395ab576e6fbc))
* add type resolution and value coercion ([b13aa53](https://github.com/MarketSquare/confargs/commit/b13aa530fc5fa451247d0af5c4e1f5270fcaf609))
* generate help text from docstrings ([364fd6a](https://github.com/MarketSquare/confargs/commit/364fd6acf3960d8ea09903cb33a80b9e647f4656))
* support boolean flag negation with --no- prefix ([335a592](https://github.com/MarketSquare/confargs/commit/335a592d9f5a4498fcf482b17d2cda21b2883793))
* validate config keys with strict_config mode ([77ef0db](https://github.com/MarketSquare/confargs/commit/77ef0db4a289aa57184ec38cb00ea9ab2ec8462e))


### Documentation

* add publishing workflow, example and expanded README ([e07a267](https://github.com/MarketSquare/confargs/commit/e07a2672ee9c9b738fb5faaa75e64732f2ef04f7))


### Build System

* single-source version and add CHANGELOG ([b3f1e77](https://github.com/MarketSquare/confargs/commit/b3f1e773e2cacba62b1e6b6d07949767ec42ffab))

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
