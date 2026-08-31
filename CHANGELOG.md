# Changelog

All notable changes to **confargs** are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **Pre-1.0 note:** while the version is `0.x.y`, the public API is still
> stabilising. Minor (`0.X.0`) releases may include breaking changes; patch
> (`0.x.Y`) releases are reserved for backwards-compatible fixes.

## [0.6.0](https://github.com/MarketSquare/confargs/compare/v0.5.0...v0.6.0) (2026-08-31)


### Features

* add opt-in case- and hyphen-insensitive CLI option matching ([#36](https://github.com/MarketSquare/confargs/issues/36)) ([8b318ec](https://github.com/MarketSquare/confargs/commit/8b318ecfe08859bf1a8604bc466bd9032c4effa0))

## [0.5.0](https://github.com/MarketSquare/confargs/compare/v0.4.0...v0.5.0) (2026-08-31)


### Features

* support extends to inherit other config files ([#30](https://github.com/MarketSquare/confargs/issues/30)) ([168c339](https://github.com/MarketSquare/confargs/commit/168c339f5017bbacf796be4510cb775efbfceccb)), closes [#5](https://github.com/MarketSquare/confargs/issues/5)


### Bug Fixes

* infer factory default value type from the produced value ([#32](https://github.com/MarketSquare/confargs/issues/32)) ([4071a0e](https://github.com/MarketSquare/confargs/commit/4071a0e716549ebdd2f1b9821b9c8606cc279420))


### Documentation

* note dash-value workaround and refresh architecture map ([#35](https://github.com/MarketSquare/confargs/issues/35)) ([0810872](https://github.com/MarketSquare/confargs/commit/08108720a046a45e6bb6332705cfd8479b02f276))


### Refactoring

* drop unused first_section helper ([#33](https://github.com/MarketSquare/confargs/issues/33)) ([0fb6618](https://github.com/MarketSquare/confargs/commit/0fb66185def6ca5ef568c1aac933a1ad51afcc29))

## [0.4.0](https://github.com/MarketSquare/confargs/compare/v0.3.0...v0.4.0) (2026-08-30)


### Features

* add configuration profiles ([#26](https://github.com/MarketSquare/confargs/issues/26)) ([44ed0ca](https://github.com/MarketSquare/confargs/commit/44ed0cacd7a56aadd8b6cce0b28c97313ae74127))
* add positional argument support ([#19](https://github.com/MarketSquare/confargs/issues/19)) ([553a2f6](https://github.com/MarketSquare/confargs/commit/553a2f65439a68251b41e8535ab2c780507b93ec)), closes [#15](https://github.com/MarketSquare/confargs/issues/15)
* load extra CLI arguments from an environment variable ([#21](https://github.com/MarketSquare/confargs/issues/21)) ([6f1ecba](https://github.com/MarketSquare/confargs/commit/6f1ecba13b6bb7e08f053c3be257d4a4a49a46b4)), closes [#3](https://github.com/MarketSquare/confargs/issues/3)
* read option/argument value type from attribute annotation ([#23](https://github.com/MarketSquare/confargs/issues/23)) ([3085da3](https://github.com/MarketSquare/confargs/commit/3085da3c8f984b8e76932c4003cb7f8ee6186160)), closes [#14](https://github.com/MarketSquare/confargs/issues/14)
* rename the tool-name attribute from name to tool_name ([#28](https://github.com/MarketSquare/confargs/issues/28)) ([d98c293](https://github.com/MarketSquare/confargs/commit/d98c293e28d70820e5587980c458fd4090bac84d))
* treat a callable option/argument default as a factory ([#24](https://github.com/MarketSquare/confargs/issues/24)) ([787356b](https://github.com/MarketSquare/confargs/commit/787356b5e65bd8fdf200c91f84680b55806817f1)), closes [#14](https://github.com/MarketSquare/confargs/issues/14)
* validate Literal[...] annotations as choices ([#25](https://github.com/MarketSquare/confargs/issues/25)) ([196464b](https://github.com/MarketSquare/confargs/commit/196464b9a670703f1c3e2899d3e4ed6cf55e2bf0)), closes [#22](https://github.com/MarketSquare/confargs/issues/22)


### Documentation

* add Copilot/AI contributor instructions ([#16](https://github.com/MarketSquare/confargs/issues/16)) ([b517488](https://github.com/MarketSquare/confargs/commit/b517488adb1066f804e4502b45b3a269fc47d9ca))
* clarify option method return value is always final ([#18](https://github.com/MarketSquare/confargs/issues/18)) ([6aa157a](https://github.com/MarketSquare/confargs/commit/6aa157a6c6a4e017013e8b1a30a26f7739ddfee7)), closes [#13](https://github.com/MarketSquare/confargs/issues/13)

## [0.3.0](https://github.com/MarketSquare/confargs/compare/v0.2.0...v0.3.0) (2026-08-28)


### Features

* allow declaring options as plain class attributes ([#9](https://github.com/MarketSquare/confargs/issues/9)) ([a75afff](https://github.com/MarketSquare/confargs/commit/a75afff617987e55669a8b0e3039a14d347e4d4f))
* make environment variables opt-in via option(env=...) ([#7](https://github.com/MarketSquare/confargs/issues/7)) ([daa5773](https://github.com/MarketSquare/confargs/commit/daa5773287bbb08bf9082687ea0a375c5b17d322))
* replace cli_only with independent cli and config toggles ([#6](https://github.com/MarketSquare/confargs/issues/6)) ([90ddb12](https://github.com/MarketSquare/confargs/commit/90ddb12fd6e4e5dc325bb23e1128f38a59dd31e6))
* replace names spec with separate name and short arguments ([#8](https://github.com/MarketSquare/confargs/issues/8)) ([85e9b03](https://github.com/MarketSquare/confargs/commit/85e9b03bda14a60bcb4c6cb92f0fb5019e14b61a))

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

[0.1.0]: https://github.com/MarketSquare/confargs/releases/tag/v0.1.0
