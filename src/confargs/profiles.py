"""Configuration *profiles* — named overlays merged onto the base config.

A profile is a table under ``<section>.profiles.<name>`` in the same TOML file
that provides the tool's base section. Selecting one or more profiles (via the
builtin ``--profile`` option) merges their values on top of the base section
before the usual key mapping and precedence handling run, so the resulting
values still sit *below* environment variables and command-line arguments.

Only a deliberately small subset of a full profile model is supported:

* selection by exact name or glob pattern (``fnmatch``);
* multiple profiles, applied in ``precedence`` order (lower first, higher wins),
  ties broken by selection order;
* ``inherits`` — a profile pulls in one or more parent profiles first;
* ``enabled = false`` — a *directly selected* profile is skipped.

Values override the base (and earlier profiles): scalars and lists alike are
*replaced*, never appended. The meta keys ``inherits``, ``precedence`` and
``enabled`` are consumed here and never treated as option values.
"""

from __future__ import annotations

from fnmatch import fnmatch
from typing import TYPE_CHECKING, Any

from confargs.exceptions import ConfigDiscoveryError

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

META_KEYS = frozenset({"inherits", "precedence", "enabled"})


def _location(path: Any) -> str:
    return f" in {path}" if path is not None else ""


def _profile_table(profiles: Mapping[str, Any], name: str, path: Any) -> dict[str, Any]:
    table = profiles[name]
    if not isinstance(table, dict):
        raise ConfigDiscoveryError(f"profile {name!r} is not a table{_location(path)}")
    return table


def _inherits(table: Mapping[str, Any], name: str, path: Any) -> list[str]:
    raw = table.get("inherits")
    if raw is None:
        return []
    if isinstance(raw, str):
        return [raw]
    if isinstance(raw, list) and all(isinstance(item, str) for item in raw):
        return list(raw)
    raise ConfigDiscoveryError(f"profile {name!r} has an invalid 'inherits'{_location(path)}; expected a name or list")


def _precedence(table: Mapping[str, Any], name: str, path: Any) -> int:
    raw = table.get("precedence", 0)
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise ConfigDiscoveryError(f"profile {name!r} has a non-integer 'precedence'{_location(path)}")
    return raw


def _enabled(table: Mapping[str, Any], name: str, path: Any) -> bool:
    raw = table.get("enabled", True)
    if not isinstance(raw, bool):
        raise ConfigDiscoveryError(f"profile {name!r} has a non-boolean 'enabled'{_location(path)}")
    return raw


def select_profiles(profiles: Mapping[str, Any], requested: Sequence[str], path: Any = None) -> list[str]:
    """Expand requested names/globs into concrete profile names, in order.

    Each requested pattern must match at least one defined profile; duplicates
    are removed while preserving first-seen order.
    """
    available = list(profiles)
    selected: list[str] = []
    for pattern in requested:
        matches = [name for name in available if name == pattern or fnmatch(name, pattern)]
        if not matches:
            known = ", ".join(available) or "none"
            raise ConfigDiscoveryError(f"unknown profile {pattern!r}{_location(path)}; available profiles: {known}")
        for name in matches:
            if name not in selected:
                selected.append(name)
    return selected


def _resolve_one(
    name: str,
    profiles: Mapping[str, Any],
    path: Any,
    stack: tuple[str, ...],
) -> dict[str, Any]:
    if name in stack:
        chain = " -> ".join([*stack, name])
        raise ConfigDiscoveryError(f"circular profile inheritance{_location(path)}: {chain}")
    table = _profile_table(profiles, name, path)
    resolved: dict[str, Any] = {}
    for parent in _inherits(table, name, path):
        if parent not in profiles:
            raise ConfigDiscoveryError(f"profile {name!r} inherits from unknown profile {parent!r}{_location(path)}")
        resolved.update(_resolve_one(parent, profiles, path, (*stack, name)))
    for key, value in table.items():
        if key in META_KEYS:
            continue
        resolved[key] = value
    return resolved


def build_profile_overlay(profiles: Mapping[str, Any], requested: Sequence[str], path: Any = None) -> dict[str, Any]:
    """Build the merged overlay for the ``requested`` profiles.

    Selected profiles are ordered by ``precedence`` (lower first), ties broken
    by selection order, then merged. Directly selected profiles with
    ``enabled = false`` are skipped; inherited parents always contribute.
    """
    selected = select_profiles(profiles, requested, path)
    active = [name for name in selected if _enabled(_profile_table(profiles, name, path), name, path)]
    ordered = sorted(
        active, key=lambda name: (_precedence(_profile_table(profiles, name, path), name, path), active.index(name))
    )
    overlay: dict[str, Any] = {}
    for name in ordered:
        overlay.update(_resolve_one(name, profiles, path, ()))
    return overlay
