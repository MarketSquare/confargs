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
    from collections.abc import Iterable, Sequence


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
) -> tuple[Path | None, dict[str, Any] | None]:
    """Return the first file defining ``section`` together with its path."""
    for path in files:
        data = load_toml(path)
        found = get_section(data, section)
        if found is not None:
            return path, found
    return None, None


def first_section(files: Iterable[Path], section: Sequence[str]) -> dict[str, Any] | None:
    """Return the section table from the first file that defines it."""
    _, found = first_section_with_path(files, section)
    return found
