"""Tests for ``extends`` — inheriting/overriding other config files."""

from __future__ import annotations

from pathlib import Path

import pytest

import confargs
from confargs import ArgConfig, option
from confargs.exceptions import ConfigDiscoveryError


class App(ArgConfig):
    tool_name = "myapp"

    loglevel: str = option(name="loglevel", default="INFO")
    console: str = option(name="console", default="verbose")
    tags: list[str] = option(name="tags", default=list)


def run(argv: list[str], cwd: Path) -> confargs.Namespace:
    return confargs.ConfigurationProcessor(App, argv=argv, environ={}, cwd=cwd).process()


def write(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


def test_extends_inherits_and_overrides(tmp_path: Path) -> None:
    write(
        tmp_path / "base.toml",
        '[tool.myapp]\nloglevel = "WARN"\nconsole = "dotted"\ntags = ["base"]\n',
    )
    write(
        tmp_path / "pyproject.toml",
        '[tool.myapp]\nextends = ["base.toml"]\nloglevel = "DEBUG"\n',
    )
    ns = run([], tmp_path)
    assert ns.loglevel == "DEBUG"  # overridden by the extending file
    assert ns.console == "dotted"  # inherited from base
    assert ns.tags == ["base"]  # inherited from base


def test_extends_replaces_lists_not_merges(tmp_path: Path) -> None:
    write(tmp_path / "base.toml", '[tool.myapp]\ntags = ["a", "b"]\n')
    write(
        tmp_path / "pyproject.toml",
        '[tool.myapp]\nextends = ["base.toml"]\ntags = ["c"]\n',
    )
    ns = run([], tmp_path)
    assert ns.tags == ["c"]


def test_extends_string_form(tmp_path: Path) -> None:
    write(tmp_path / "base.toml", '[tool.myapp]\nloglevel = "TRACE"\n')
    write(tmp_path / "pyproject.toml", '[tool.myapp]\nextends = "base.toml"\n')
    ns = run([], tmp_path)
    assert ns.loglevel == "TRACE"


def test_extends_multiple_later_wins(tmp_path: Path) -> None:
    write(tmp_path / "a.toml", '[tool.myapp]\nloglevel = "A"\nconsole = "from-a"\n')
    write(tmp_path / "b.toml", '[tool.myapp]\nloglevel = "B"\n')
    write(
        tmp_path / "pyproject.toml",
        '[tool.myapp]\nextends = ["a.toml", "b.toml"]\n',
    )
    ns = run([], tmp_path)
    assert ns.loglevel == "B"  # b listed after a
    assert ns.console == "from-a"  # only a set it


def test_extends_relative_subdirectory(tmp_path: Path) -> None:
    (tmp_path / "conf").mkdir()
    write(tmp_path / "conf" / "shared.toml", '[tool.myapp]\nloglevel = "SHARED"\n')
    write(
        tmp_path / "pyproject.toml",
        '[tool.myapp]\nextends = ["conf/shared.toml"]\n',
    )
    ns = run([], tmp_path)
    assert ns.loglevel == "SHARED"


def test_extends_absolute_path(tmp_path: Path) -> None:
    shared = write(tmp_path / "shared.toml", '[tool.myapp]\nloglevel = "ABS"\n')
    write(
        tmp_path / "pyproject.toml",
        f'[tool.myapp]\nextends = ["{shared.as_posix()}"]\n',
    )
    ns = run([], tmp_path)
    assert ns.loglevel == "ABS"


def test_extends_is_recursive(tmp_path: Path) -> None:
    write(tmp_path / "base.toml", '[tool.myapp]\nloglevel = "BASE"\nconsole = "base"\n')
    write(
        tmp_path / "mid.toml",
        '[tool.myapp]\nextends = ["base.toml"]\nconsole = "mid"\n',
    )
    write(
        tmp_path / "pyproject.toml",
        '[tool.myapp]\nextends = ["mid.toml"]\n',
    )
    ns = run([], tmp_path)
    assert ns.loglevel == "BASE"  # from the deepest file
    assert ns.console == "mid"  # mid overrode base


def test_extends_key_does_not_trip_strict_validation(tmp_path: Path) -> None:
    write(tmp_path / "base.toml", '[tool.myapp]\nloglevel = "OK"\n')
    write(tmp_path / "pyproject.toml", '[tool.myapp]\nextends = ["base.toml"]\n')
    ns = run([], tmp_path)  # strict_config is True by default
    assert ns.loglevel == "OK"


def test_cli_overrides_extended_config(tmp_path: Path) -> None:
    write(tmp_path / "base.toml", '[tool.myapp]\nloglevel = "FROMFILE"\n')
    write(tmp_path / "pyproject.toml", '[tool.myapp]\nextends = ["base.toml"]\n')
    ns = run(["--loglevel", "FROMCLI"], tmp_path)
    assert ns.loglevel == "FROMCLI"


def test_extends_missing_file_raises(tmp_path: Path) -> None:
    write(tmp_path / "pyproject.toml", '[tool.myapp]\nextends = ["nope.toml"]\n')
    with pytest.raises(ConfigDiscoveryError, match="extended config file not found"):
        run([], tmp_path)


def test_extends_missing_section_raises(tmp_path: Path) -> None:
    write(tmp_path / "base.toml", '[tool.other]\nloglevel = "X"\n')
    write(tmp_path / "pyproject.toml", '[tool.myapp]\nextends = ["base.toml"]\n')
    with pytest.raises(ConfigDiscoveryError, match=r"no \[tool\.myapp\] section"):
        run([], tmp_path)


def test_extends_cycle_raises(tmp_path: Path) -> None:
    write(tmp_path / "a.toml", '[tool.myapp]\nextends = ["b.toml"]\n')
    write(tmp_path / "b.toml", '[tool.myapp]\nextends = ["a.toml"]\n')
    write(tmp_path / "pyproject.toml", '[tool.myapp]\nextends = ["a.toml"]\n')
    with pytest.raises(ConfigDiscoveryError, match="circular extends"):
        run([], tmp_path)


def test_extends_self_cycle_raises(tmp_path: Path) -> None:
    write(
        tmp_path / "pyproject.toml",
        '[tool.myapp]\nextends = ["pyproject.toml"]\n',
    )
    with pytest.raises(ConfigDiscoveryError, match="circular extends"):
        run([], tmp_path)


def test_extends_invalid_type_raises(tmp_path: Path) -> None:
    write(tmp_path / "pyproject.toml", "[tool.myapp]\nextends = 5\n")
    with pytest.raises(ConfigDiscoveryError, match="must be a string or a list of strings"):
        run([], tmp_path)


def test_extends_inherits_profiles_from_base(tmp_path: Path) -> None:
    write(
        tmp_path / "base.toml",
        '[tool.myapp]\nloglevel = "INFO"\n\n[tool.myapp.profiles.ci]\nloglevel = "DEBUG"\n',
    )
    write(tmp_path / "pyproject.toml", '[tool.myapp]\nextends = ["base.toml"]\n')
    ns = run(["--profile", "ci"], tmp_path)
    assert ns.loglevel == "DEBUG"
