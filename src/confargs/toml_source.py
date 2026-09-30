"""TOML configuration loading and file discovery.

Discovery walks up from a starting directory (by default the current working
directory) looking for the configured file names, stopping at the project root
(a directory containing ``.git``) unless that behaviour is disabled. If no
project configuration is found, a per-user configuration directory is consulted
as a fallback.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from confargs.exceptions import ConfigDiscoveryError

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - exercised only on Python 3.10
    import tomli as tomllib

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Mapping, Sequence

    KeyNormalizer = Callable[[Mapping[str, Any], Path | None], dict[str, Any]]
    TopLevelPredicate = Callable[[Path], bool]


EXTENDS_KEY = "extends"
# Top-level table reserved for other tools' settings in a dedicated config file.
TOOL_KEY = "tool"


def _extend_paths(extends: Any, source: Path) -> list[Path]:
    """Resolve the raw ``extends`` value of ``source`` to a list of files.

    Accepts a single string or a list of strings. Relative paths are resolved
    against the directory containing ``source``; absolute paths are used as-is.
    """
    if isinstance(extends, str):
        names = [extends]
    elif isinstance(extends, list) and all(isinstance(item, str) for item in extends):
        names = extends
    else:
        raise ConfigDiscoveryError(f"'extends' in {source} must be a string or a list of strings")
    base_dir = source.parent
    resolved: list[Path] = []
    for name in names:
        candidate = Path(name)
        if not candidate.is_absolute():
            candidate = base_dir / candidate
        if not candidate.is_file():
            raise ConfigDiscoveryError(f"extended config file not found: {candidate} (referenced from {source})")
        resolved.append(candidate)
    return resolved


def resolve_extends(
    section: Mapping[str, Any],
    path: Path,
    section_keys: Sequence[str],
    *,
    normalize: KeyNormalizer | None = None,
    top_level: TopLevelPredicate | None = None,
    _seen: frozenset[Path] = frozenset(),
) -> dict[str, Any]:
    """Merge ``section`` with the config files it ``extends``, own keys winning.

    ``extends`` lists other config files (relative to ``path`` or absolute)
    whose same-named ``section_keys`` table is merged in first, in listed order,
    so later files — and finally ``section`` itself — override earlier ones.
    Merging is a shallow override (no list concatenation), matching the rest of
    the precedence model. Extended files may themselves ``extends`` others;
    cycles raise :class:`ConfigDiscoveryError`. The reserved ``extends`` key is
    stripped from the result so it never reaches option mapping. When given,
    ``normalize(table, path)`` rewrites each file's keys before merging, and
    ``top_level(path)`` decides whether an extended file lacking the section
    may be read from its top level (see :func:`read_section`).
    """
    seen = _seen | {path.resolve()}
    own = {key: value for key, value in section.items() if key != EXTENDS_KEY}
    if normalize is not None:
        own = normalize(own, path)
    extends = section.get(EXTENDS_KEY)
    if not extends:
        return own
    merged: dict[str, Any] = {}
    for ext_path in _extend_paths(extends, path):
        if ext_path.resolve() in seen:
            raise ConfigDiscoveryError(f"circular extends detected: {ext_path} (referenced from {path})")
        allow_top_level = top_level is not None and top_level(ext_path)
        ext_section = read_section(load_toml(ext_path), section_keys, ext_path, top_level=allow_top_level)
        if ext_section is None:
            joined = ".".join(section_keys)
            alternative = " or top-level keys" if allow_top_level else ""
            raise ConfigDiscoveryError(f"extended config {ext_path} has no [{joined}] section{alternative}")
        merged.update(
            resolve_extends(ext_section, ext_path, section_keys, normalize=normalize, top_level=top_level, _seen=seen)
        )
    merged.update(own)
    return merged


def load_toml(path: Path) -> dict[str, Any]:
    """Read and parse a TOML file, raising :class:`ConfigDiscoveryError`."""
    try:
        with path.open("rb") as handle:
            return tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigDiscoveryError(f"could not read config file {path}: {exc}") from exc


def get_section(data: dict[str, Any], section: Sequence[str]) -> dict[str, Any] | None:
    """Return the nested TOML table at ``section``, or ``None`` if absent."""
    node: Any = data
    for key in section:
        if not isinstance(node, dict) or key not in node:
            return None
        node = node[key]
    if not isinstance(node, dict):
        raise ConfigDiscoveryError(f"config section {'.'.join(section)} is not a table")
    return node


def read_section(
    data: dict[str, Any],
    section: Sequence[str],
    path: Path | None = None,
    *,
    top_level: bool = False,
) -> dict[str, Any] | None:
    """Return the config table of a parsed file, optionally falling back to its top level.

    The ``section`` table (e.g. ``[tool.mytool]``) always wins. When it is
    absent and ``top_level`` is true — a file dedicated to the tool, like
    ``ruff.toml`` — the file's top-level keys are used instead, ignoring the
    ``tool`` table that holds other tools' settings. A file that has both the
    section and other top-level keys is ambiguous and raises an error.
    """
    found = get_section(data, section)
    if not top_level:
        return found
    rest = {key: value for key, value in data.items() if key != TOOL_KEY}
    if found is None:
        return rest or None
    if rest:
        joined = ".".join(section)
        keys = ", ".join(repr(key) for key in rest)
        location = f" in {path}" if path is not None else ""
        raise ConfigDiscoveryError(
            f"configuration{location} has both a [{joined}] table and top-level keys ({keys}); use only one"
        )
    return found


def find_project_config_files(
    start: Path,
    config_names: Sequence[str],
    *,
    ignore_git: bool = False,
) -> list[Path]:
    """Find candidate config files by walking up from ``start``.

    Returns existing files ordered nearest-first, and within a directory by the
    order of ``config_names``. The walk stops at the first directory containing
    ``.git`` (inclusive) unless ``ignore_git`` is true.
    """
    start = start.resolve()
    found: list[Path] = []
    for directory in [start, *start.parents]:
        for name in config_names:
            candidate = directory / name
            if candidate.is_file():
                found.append(candidate)
        if not ignore_git and (directory / ".git").exists():
            break
    return found


def user_config_dir(tool_name: str) -> Path:
    """Return the per-user configuration directory for ``tool_name``."""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / tool_name
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base_path = Path(xdg) if xdg else Path.home() / ".config"
    return base_path / tool_name


def find_user_config_files(tool_name: str, config_names: Sequence[str]) -> list[Path]:
    """Find existing config files in the per-user configuration directory."""
    directory = user_config_dir(tool_name)
    return [directory / name for name in config_names if (directory / name).is_file()]


def first_section_with_path(
    files: Iterable[Path],
    section: Sequence[str],
    top_level: TopLevelPredicate | None = None,
) -> tuple[Path | None, dict[str, Any] | None]:
    """Return the first file defining ``section`` together with its path.

    Files for which ``top_level(path)`` is true may define it through their
    top-level keys instead (see :func:`read_section`).
    """
    for path in files:
        data = load_toml(path)
        found = read_section(data, section, path, top_level=top_level is not None and top_level(path))
        if found is not None:
            return path, found
    return None, None
