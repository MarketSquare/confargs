"""The :class:`ConfigurationProcessor` that ties every source together."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from confargs.base import ArgConfig
from confargs.cli import parse_cli
from confargs.coercion import coerce_value, resolve_value_type
from confargs.env_source import collect_env_values
from confargs.exceptions import MISSING, CliUsageError, ConfigDiscoveryError, OptionDefinitionError, OptionValueError
from confargs.namespace import Namespace
from confargs.options import collect_options, resolve_names
from confargs.toml_source import (
    find_project_config_files,
    find_user_config_files,
    first_section_with_path,
)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from confargs.options import Option


class ConfigurationProcessor:
    """Resolve a config class into a :class:`Namespace` of final values.

    Values are merged from, in decreasing priority:

    1. command-line arguments,
    2. environment variables,
    3. the nearest project TOML config,
    4. the per-user TOML config,
    5. each option's declared default.

    Each resolved raw value is passed through the option's own method for
    parsing and validation before being stored.
    """

    _MAX_EAGER_PASSES = 1000

    def __init__(
        self,
        config: type[ArgConfig] | ArgConfig,
        *,
        argv: Sequence[str] | None = None,
        environ: Mapping[str, str] | None = None,
        cwd: Path | str | None = None,
    ) -> None:
        self.instance = config() if isinstance(config, type) else config
        self.argv = list(sys.argv[1:] if argv is None else argv)
        self.environ = dict(os.environ if environ is None else environ)
        self.cwd = Path.cwd() if cwd is None else Path(cwd)

        self.options: dict[str, Option] = collect_options(type(self.instance))
        self.table = resolve_names(self.options)
        self.value_types = {attr: resolve_value_type(opt) for attr, opt in self.options.items()}
        self.flags = {attr for attr, vt in self.value_types.items() if vt.is_flag}
        self.lists = {attr for attr, vt in self.value_types.items() if vt.is_list}
        self.cli_only = {attr for attr, opt in self.options.items() if opt.cli_only}
        self.eager = {attr for attr, opt in self.options.items() if opt.is_eager}
        self.positionals: list[str] = []

    def process(self) -> Namespace:
        """Parse every source, merge them and return resolved values."""
        argv = self._expand_eager(self.argv)
        cli_result = parse_cli(argv, self.table, self.flags, self.lists)
        self.positionals = cli_result.positionals

        nearest, user = self._load_toml(cli_result.values)
        env_values = collect_env_values(
            self.options,
            self.instance.tool_name,
            auto_env_vars=self.instance.auto_env_vars,
            environ=self.environ,
        )

        sources: list[Mapping[str, Any]] = [cli_result.values, env_values, nearest, user]
        resolved: dict[str, Any] = {}
        for attr, opt in self.options.items():
            raw = self._pick(attr, sources)
            resolved[attr] = self._resolve(opt, attr, raw)
        return Namespace(resolved)

    @staticmethod
    def _pick(attr: str, sources: Sequence[Mapping[str, Any]]) -> Any:
        for source in sources:
            if attr in source:
                return source[attr]
        return MISSING

    def _expand_eager(self, argv: Sequence[str]) -> list[str]:
        """Resolve eager options against ``argv`` before anything else.

        Each eager option occurrence is located directly in ``argv`` and its
        method is invoked with the coerced value. Whatever the method returns
        (an iterable of tokens, or ``None``) replaces that option's own tokens
        in ``argv``. This lets an ``--argumentfile`` option read a file and
        splice its contents in place — repeatedly, so nested argument files are
        expanded too. A guard bounds the number of expansions to catch cyclic
        argument files.
        """
        expanded = list(argv)
        if not self.eager:
            return expanded

        passes = 0
        while True:
            occurrence = self._scan_first_eager(expanded)
            if occurrence is None:
                return expanded
            passes += 1
            if passes > self._MAX_EAGER_PASSES:
                raise CliUsageError(
                    "eager option expansion exceeded its limit; check for a cyclic --argumentfile reference"
                )
            attr, raw, start, end = occurrence
            value_type = self.value_types[attr]
            value = True if value_type.is_flag else coerce_value(raw, value_type)
            method = getattr(self.instance, attr)
            result = method(value)
            if isinstance(result, str):
                display = self.table.attr_to_names.get(attr, [attr])[0]
                raise OptionDefinitionError(
                    f"eager option {display} must return an iterable of tokens or None, not a bare string"
                )
            injected = [str(token) for token in result] if result else []
            expanded[start:end] = injected

    def _scan_first_eager(self, argv: Sequence[str]) -> tuple[str, Any, int, int] | None:
        """Find the first eager-option occurrence in ``argv``.

        Returns ``(attr, raw_value, start, end)`` where ``argv[start:end]`` is
        the span to replace, or ``None`` when no eager option remains. Option
        parsing stops at a ``--`` terminator.
        """
        index = 0
        while index < len(argv):
            token = argv[index]
            if token == "--":
                return None
            if token.startswith("--"):
                found = self._scan_long_eager(argv, index, token)
                if found is not None:
                    return found
            elif token.startswith("-") and token != "-":
                found = self._scan_short_eager(argv, index, token)
                if found is not None:
                    return found
            index += 1
        return None

    def _scan_long_eager(self, argv: Sequence[str], index: int, token: str) -> tuple[str, Any, int, int] | None:
        name, sep, inline = token.partition("=")
        attr = self.table.long_to_attr.get(name)
        if attr not in self.eager:
            return None
        if attr in self.flags:
            return attr, True, index, index + 1
        if sep:
            return attr, inline, index, index + 1
        if index + 1 >= len(argv):
            raise CliUsageError(f"option {name!r} expects a value")
        return attr, argv[index + 1], index, index + 2

    def _scan_short_eager(self, argv: Sequence[str], index: int, token: str) -> tuple[str, Any, int, int] | None:
        name = token[:2]
        attr = self.table.short_to_attr.get(name)
        if attr not in self.eager:
            return None
        if attr in self.flags:
            return attr, True, index, index + 1
        attached = token[2:]
        if attached:
            return attr, attached, index, index + 1
        if index + 1 >= len(argv):
            raise CliUsageError(f"option {name!r} expects a value")
        return attr, argv[index + 1], index, index + 2

    def _resolve(self, opt: Option, attr: str, raw: Any) -> Any:
        method = getattr(self.instance, attr)
        if raw is MISSING:
            default = opt.default
            if default is MISSING:
                display = self.table.attr_to_names.get(attr, [attr])[0]
                raise OptionValueError(f"option {display} is required")
            return method(default)
        value = coerce_value(raw, self.value_types[attr])
        return method(value)

    def _load_toml(self, cli_values: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        if cli_values.get("no_config"):
            return {}, {}

        section = self.instance.config_section
        config_names = self.instance.config_names

        explicit = cli_values.get("config")
        if explicit:
            path, data = first_section_with_path([Path(explicit)], section)
            return self._map_toml(data or {}, path), {}

        ignore_git = bool(cli_values.get("ignore_git"))
        project_files = find_project_config_files(self.cwd, config_names, ignore_git=ignore_git)
        nearest_path, nearest = first_section_with_path(project_files, section)

        user_files = find_user_config_files(self.instance.tool_name, config_names)
        user_path, user = first_section_with_path(user_files, section)
        return (
            self._map_toml(nearest or {}, nearest_path),
            self._map_toml(user or {}, user_path),
        )

    def _map_toml(self, section: Mapping[str, Any], path: Path | None) -> dict[str, Any]:
        """Map raw TOML keys to option attribute names, dropping cli-only keys.

        In strict mode, unknown keys and ``cli_only`` options are reported as
        errors instead of being silently ignored.
        """
        key_map = self._toml_key_map()
        mapped: dict[str, Any] = {}
        invalid: list[str] = []
        for key, value in section.items():
            attr = key_map.get(key)
            if attr is None:
                invalid.append(f"{key!r} (unknown option)")
                continue
            if attr in self.cli_only:
                invalid.append(f"{key!r} (command-line only)")
                continue
            mapped[attr] = value

        if invalid and self.instance.strict_config:
            location = f" in {path}" if path is not None else ""
            joined = ", ".join(invalid)
            raise ConfigDiscoveryError(f"invalid configuration keys{location}: {joined}")
        return mapped

    def _toml_key_map(self) -> dict[str, str]:
        mapping: dict[str, str] = {}
        for attr, opt in self.options.items():
            mapping[attr] = attr
            mapping[attr.replace("_", "-")] = attr
            for long in opt.long_names:
                mapping[long.lstrip("-")] = attr
        return mapping
