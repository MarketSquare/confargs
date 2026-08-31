# Copilot / AI contributor instructions

Guidance for AI agents (GitHub Copilot, coding agent, CLI) and human contributors
working on **confargs**. It captures the decisions already made so future work
stays consistent. Keep this file up to date when a convention changes.

## What this project is

`confargs` is a declarative CLI argument parser for Python 3.10+ that merges
three sources into one immutable configuration object:

**CLI args > environment variables > nearest TOML config > user-dir TOML > option default**

Users subclass `ArgConfig`, declare options, then call
`ConfigurationProcessor(MyArgs).process()` to get a `Namespace`. See `README.md`
for the user-facing API; this file is about *how we build and change the library*.

Status: **alpha, pre-1.0**. The public API may still change between `0.x` minor
releases.

## Golden rules

- **confargs only does light coercion.** It converts a raw source value into the
  option's declared type (`str`/`int`/`float`/`bool`/`list[...]`, `None`
  passthrough). All real parsing, validation and domain logic lives in the
  user's option method, which returns the final value. Do not add heavyweight
  parsing/validation to the library core.
- **Two ways to declare an option, one code path.** A decorated method
  (`@option`) for options that parse/validate; a plain attribute
  (`name = option(name=..., default=..., help=...)`) for pure pass-through
  values. `@option(...)` builds a method-less `Option` and binds the method via
  `Option.__call__`, so both spellings share one implementation. Preserve this
  unification — don't fork the paths.
- **Prefer declarative options** in examples/tests whenever an option would just
  `return value` with no parsing or validation.
- **Keep the three living examples in sync.** Whenever you change something
  fundamental (option API, naming, sources, precedence, recommended usage), you
  MUST update all three demonstrations to use the currently recommended
  approach:
  1. `examples/demo.py` (the self-contained copy-pasteable example),
  2. `src/confargs/demo.py` (the packaged `confargs-demo` script), and
  3. `tests/robot_cli.py` (the realistic Robot Framework-style fixture).
  They double as living documentation, so they must always model current best
  practice — not a legacy style.
- **Keep the source layered.** Each source (CLI, env, TOML) is an independent
  module that produces raw values; the processor merges them by precedence.
  Don't entangle sources with each other or with coercion.
- **Everything is typed.** `mypy --strict` must pass. Public API is exported from
  `src/confargs/__init__.py` and the package ships `py.typed`.

## Architecture map (`src/confargs/`)

| Module | Responsibility |
|--------|----------------|
| `base.py` | `ArgConfig` base class + builtin options (`help`, `config`, `no-config`, `ignore-git`, `profile`). Class attrs: `tool_name`, `config_names`, `default_config_section`, `env_var_template`, `options_env_var`, `strict_config`. |
| `options.py` | `Option` descriptor, the `option()` factory, name/short derivation, `resolve_names`, `collect_options`. |
| `arguments.py` | `Argument` descriptor + `argument()` factory for positionals (`nargs` 1/`?`/`*`/`+`), `collect_arguments` (variadic must be last). |
| `coercion.py` | `resolve_value_type` (building a `ValueType`) + `coerce_value` + `parse_bool` — the only place that converts raw values into declared types (incl. `Literal[...]` choices). |
| `processor.py` | `ConfigurationProcessor` — orchestrates discovery, eager expansion, merge by precedence, calls user methods. |
| `cli.py` | argv tokenising, flag negation (`--no-*`), short/long parsing. |
| `env_source.py` | Opt-in env var reading (`option(env=...)`), name templating, `options_env_var` splitting. |
| `toml_source.py` | TOML discovery (cwd upward, stop at `.git`), section lookup, key mapping, `extends` resolution. |
| `profiles.py` | Named config overlays (`<section>.profiles.<name>`): selection/globbing, `inherits`, `precedence`, `enabled`. |
| `argfile.py` | `read_argument_file` / `split_argument_file` for eager `--argumentfile`. |
| `namespace.py` | Immutable `Namespace` result object. |
| `exceptions.py` | Error hierarchy + `MISSING` sentinel + `Exit`. |
| `help.py` | `--help` text generation from docstrings/`help=`. |
| `demo.py` | The `confargs-demo` console script (packaged example). |

## Key design decisions (already settled)

- **Option naming:** `name=` is the long name (no dashes; underscores→dashes if
  derived from the method/attribute name). `short=` is a single character.
  A short is auto-derived from the first letter **only when `name` is not given
  explicitly** — passing `name` opts out of the implicit short. Short-name
  collisions are resolved/skipped in `resolve_names`; long-name collisions raise.
- **Per-option source toggles:** `cli=False` hides an option from the command
  line; `config=False` stops it loading from TOML. Combine them (plus `env`) to
  build, e.g., a CLI-only switch. There is no `cli_only` flag (removed).
- **Env vars are opt-in per option:** `env=True` generates a name from the class
  `env_var_template` (default `"{name}_{option}"`, upper-cased); `env="NAME"`
  sets an explicit one; default `False` means never read from env. No automatic
  env-var conversion.
- **Eager options:** `is_eager=True` resolves an option *before* all others,
  directly against argv; its return value (iterable of tokens or `None`)
  replaces its own argv span. This is how `--argumentfile` injects more args.
- **Strict config:** `strict_config=True` (default) rejects unknown keys and
  `config=False` keys found in a TOML section.
- **Boolean flags negate** with `--no-<name>` automatically.

## Workflow for changes

1. **One logical change per PR**, branched off `main` (or stacked on a
   dependency branch when work builds on an open PR). Use descriptive branch
   names like `feat/...`, `fix/...`, `docs/...`, `test/...`.
2. **Validate locally before committing** (all must pass):
   ```
   uv run ruff check .
   uv run ruff format --check .
   uv run mypy
   uv run pytest -q
   ```
   Apply formatting with `uv run ruff format .` if the check fails.
3. **Add/adjust tests** for any behaviour change; update `README.md` and a
   `CHANGELOG.md` `[Unreleased]` entry when the public API or behaviour changes.
4. **Commit and PR title use Conventional Commits** (enforced by the
   `pr-title` workflow and consumed by release-please):
   `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`,
   `chore`, `revert`. Example: `feat: add eager option support`.

### Pre-1.0 versioning & breaking changes

- release-please is configured with `bump-minor-pre-major: true`, so **breaking
  changes bump the minor version (`0.x`), never to `1.0.0`**.
- While in alpha we **avoid `feat!:` / `BREAKING CHANGE:`** footers (they add a
  scary "⚠ BREAKING CHANGES" release-notes section). Use a plain `feat:`/`fix:`
  and document migration inline in the CHANGELOG under a short
  "Migration (pre-1.0)" note. There are no stability guarantees yet.
- Changelog sections come from commit types (`feat`→Features, `fix`→Bug Fixes,
  `docs`→Documentation; `ci`/`chore`/`style`/`test` are hidden).

## Tooling & conventions

- **uv** manages the environment and lockfile. Run everything via `uv run ...`.
  After changing dependencies, run `uv sync` and commit the updated `uv.lock`;
  CI uses `uv sync --locked`.
- **Ruff** for lint + format: line length **120**, target **py310**, rule sets
  `E, F, I, UP, B, SIM, C4, PTH, RUF`. Tests may ignore `B011`.
- **mypy** `strict = true` over `src/confargs`.
- **pre-commit** enforces the above plus `check-toml`, `check-yaml`,
  end-of-file/trailing-whitespace, and **LF line endings** (`.gitattributes`
  normalises to LF; `mixed-line-ending --fix=lf`). Note: on Windows the editor
  may write CRLF — the `.gitattributes`/pre-commit setup normalises it, and a
  "CRLF will be replaced by LF" warning on commit is harmless.
- **CI matrix decision:** test every supported Python (3.10–3.13) on Linux; on
  the costlier Windows runners cover only the oldest and newest. `setup-uv` has
  no `python-version` input, so the interpreter is selected via `UV_PYTHON` per
  matrix entry. `uv` version is pinned in the workflow `env` for reproducibility.

## Code style for the library

- Small, single-responsibility modules; keep sources decoupled (see map above).
- Full type annotations; module/function docstrings explain intent. Add inline
  comments only where the reasoning is non-obvious.
- Raise the project's own exceptions: `OptionDefinitionError` for author
  mistakes (bad names, double-bound methods), `OptionValueError` for bad values,
  `CliUsageError` for malformed argv, `ConfigDiscoveryError` for config lookup.
- Use the `MISSING` sentinel (not `None`) to mean "no value supplied", since
  `None` is a legitimate option value.

## Where to look / update when you change X

- **New option capability** → `options.py` (declaration) + `coercion.py` (typing)
  + `processor.py` (merge) + tests + `README.md` + `CHANGELOG.md`.
- **New source or precedence tweak** → the relevant `*_source.py` + `processor.py`.
- **User-facing behaviour or recommended usage** → update `README.md` **and all
  three living examples together**: `examples/demo.py`, `src/confargs/demo.py`,
  and `tests/robot_cli.py`. Any fundamental change must leave all three modelling
  the current best-recommended approach.
