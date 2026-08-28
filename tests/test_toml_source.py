"""Tests for TOML loading and config discovery."""

from __future__ import annotations

from pathlib import Path

import pytest

from argconfig.exceptions import ConfigDiscoveryError
from argconfig.toml_source import (
    find_project_config_files,
    find_user_config_files,
    first_section,
    get_section,
    load_toml,
    user_config_dir,
)


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_load_toml(tmp_path: Path) -> None:
    cfg = write(tmp_path / "c.toml", "[tool.x]\nlog = 'a.html'\n")
    assert load_toml(cfg) == {"tool": {"x": {"log": "a.html"}}}


def test_load_toml_invalid(tmp_path: Path) -> None:
    bad = write(tmp_path / "bad.toml", "not = = valid")
    with pytest.raises(ConfigDiscoveryError):
        load_toml(bad)


def test_load_toml_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigDiscoveryError):
        load_toml(tmp_path / "nope.toml")


def test_get_section_present() -> None:
    data = {"tool": {"mytool": {"log": "x"}}}
    assert get_section(data, ("tool", "mytool")) == {"log": "x"}


def test_get_section_absent() -> None:
    assert get_section({"tool": {}}, ("tool", "mytool")) is None


def test_get_section_not_a_table() -> None:
    with pytest.raises(ConfigDiscoveryError):
        get_section({"tool": {"x": 5}}, ("tool", "x"))


def test_discovery_walks_up_to_nearest(tmp_path: Path) -> None:
    write(tmp_path / "pyproject.toml", "[tool.x]\na = 1\n")
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    files = find_project_config_files(nested, ["pyproject.toml"])
    assert files == [tmp_path / "pyproject.toml"]


def test_discovery_prefers_nearest_directory(tmp_path: Path) -> None:
    write(tmp_path / "pyproject.toml", "[tool.x]\na = 1\n")
    nested = tmp_path / "a"
    write(nested / "pyproject.toml", "[tool.x]\na = 2\n")
    files = find_project_config_files(nested, ["pyproject.toml"])
    assert files[0] == nested / "pyproject.toml"


def test_discovery_config_name_priority(tmp_path: Path) -> None:
    write(tmp_path / "pyproject.toml", "[tool.x]\na = 1\n")
    write(tmp_path / "mytool.toml", "[tool.x]\na = 2\n")
    files = find_project_config_files(tmp_path, ["mytool.toml", "pyproject.toml"])
    assert files == [tmp_path / "mytool.toml", tmp_path / "pyproject.toml"]


def test_discovery_stops_at_git_root(tmp_path: Path) -> None:
    write(tmp_path / "pyproject.toml", "[tool.x]\na = 1\n")
    project = tmp_path / "proj"
    (project / ".git").mkdir(parents=True)
    write(project / "pyproject.toml", "[tool.x]\na = 2\n")
    nested = project / "src"
    nested.mkdir()
    files = find_project_config_files(nested, ["pyproject.toml"])
    # Should not escape past the .git root to the outer pyproject.
    assert files == [project / "pyproject.toml"]


def test_discovery_ignore_git_keeps_walking(tmp_path: Path) -> None:
    write(tmp_path / "pyproject.toml", "[tool.x]\na = 1\n")
    project = tmp_path / "proj"
    (project / ".git").mkdir(parents=True)
    write(project / "pyproject.toml", "[tool.x]\na = 2\n")
    files = find_project_config_files(project, ["pyproject.toml"], ignore_git=True)
    assert (tmp_path / "pyproject.toml") in files


def test_first_section_skips_files_without_section(tmp_path: Path) -> None:
    a = write(tmp_path / "a.toml", "[tool.other]\nx = 1\n")
    b = write(tmp_path / "b.toml", "[tool.x]\nlog = 'hit'\n")
    assert first_section([a, b], ("tool", "x")) == {"log": "hit"}


def test_first_section_none_when_absent(tmp_path: Path) -> None:
    a = write(tmp_path / "a.toml", "[tool.other]\nx = 1\n")
    assert first_section([a], ("tool", "x")) is None


def test_user_config_dir_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.platform", "win32")
    monkeypatch.setenv("APPDATA", r"C:\Users\me\AppData\Roaming")
    assert user_config_dir("mytool") == Path(r"C:\Users\me\AppData\Roaming") / "mytool"


def test_user_config_dir_xdg(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("sys.platform", "linux")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert user_config_dir("mytool") == tmp_path / "mytool"


def test_find_user_config_files(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("sys.platform", "linux")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    write(tmp_path / "mytool" / "pyproject.toml", "[tool.x]\na = 1\n")
    files = find_user_config_files("mytool", ["pyproject.toml"])
    assert files == [tmp_path / "mytool" / "pyproject.toml"]
