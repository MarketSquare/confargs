"""The :class:`ConfigurationProcessor` that ties every source together."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from argconfig.base import ArgConfig
from argconfig.cli import parse_cli
from argconfig.coercion import coerce_value, resolve_value_type
from argconfig.env_source import collect_env_values
from argconfig.exceptions import MISSING, OptionValueError
from argconfig.namespace import Namespace
from argconfig.options import collect_options, resolve_names
from argconfig.toml_source import (
    find_project_config_files,
    find_user_config_files,
    first_section,
)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from argconfig.options import Option


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
        self.positionals: list[str] = []

    def process(self) -> Namespace:
        """Parse every source, merge them and return resolved values."""
        cli_result = parse_cli(self.argv, self.table, self.flags, self.lists)
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
            nearest = first_section([Path(explicit)], section) or {}
            return self._map_toml(nearest), {}

        ignore_git = bool(cli_values.get("ignore_git"))
        project_files = find_project_config_files(self.cwd, config_names, ignore_git=ignore_git)
        nearest = first_section(project_files, section) or {}

        user_files = find_user_config_files(self.instance.tool_name, config_names)
        user = first_section(user_files, section) or {}
        return self._map_toml(nearest), self._map_toml(user)

    def _map_toml(self, section: Mapping[str, Any]) -> dict[str, Any]:
        """Map raw TOML keys to option attribute names, dropping cli-only keys."""
        key_map = self._toml_key_map()
        mapped: dict[str, Any] = {}
        for key, value in section.items():
            attr = key_map.get(key)
            if attr is None or attr in self.cli_only:
                continue
            mapped[attr] = value
        return mapped

    def _toml_key_map(self) -> dict[str, str]:
        mapping: dict[str, str] = {}
        for attr, opt in self.options.items():
            mapping[attr] = attr
            mapping[attr.replace("_", "-")] = attr
            for long in opt.long_names:
                mapping[long.lstrip("-")] = attr
        return mapping
