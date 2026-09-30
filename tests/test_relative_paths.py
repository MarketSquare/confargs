"""Tests for resolving config-file paths relative to the file that sets them."""

from __future__ import annotations

from pathlib import Path

import pytest

from confargs import ArgConfig, OptionDefinitionError, argument, option
from confargs.processor import ConfigurationProcessor


class Tool(ArgConfig):
    tool_name = "mytool"
    config_names = ["mytool.toml"]  # noqa: RUF012
    top_level_config_names = ["mytool.toml"]  # noqa: RUF012

    outdir: str | None = option(name="outdir", default=None, relative_to_config=True)
    libs: list[str] = option(name="libs", default=list, relative_to_config=True)
    name: str | None = option(name="name", default=None)
    listener: list[str] = option(name="listener", default=list, relative_to_config="existing")
    paths: list[str] = argument(name="paths", nargs="*", relative_to_config=True)


def run(cwd: Path, argv: list[str] | None = None) -> dict[str, object]:
    return ConfigurationProcessor(Tool, argv=argv or [], environ={}, cwd=cwd).process().as_dict()


def project(tmp_path: Path, body: str) -> Path:
    root = tmp_path / "project"
    (root / ".git").mkdir(parents=True)
    (root / "mytool.toml").write_text(body)
    return root


def test_relative_paths_resolve_against_config_dir_from_a_subdirectory(tmp_path: Path) -> None:
    root = project(tmp_path, 'paths = ["tests", "more/*.robot"]\noutdir = "out"\nlibs = ["lib"]\nname = "x/y"\n')
    sub = root / "tests" / "nested"
    sub.mkdir(parents=True)
    result = run(sub)
    root = root.resolve()
    assert result["paths"] == [str(root / "tests"), str(root / "more/*.robot")]
    assert result["outdir"] == str(root / "out")
    assert result["libs"] == [str(root / "lib")]
    assert result["name"] == "x/y"  # not marked relative_to_config


def test_absolute_paths_are_kept(tmp_path: Path) -> None:
    absolute = (tmp_path / "elsewhere").resolve()
    root = project(tmp_path, f"outdir = '{absolute}'\n")
    assert run(root)["outdir"] == str(absolute)


def test_command_line_values_are_not_resolved(tmp_path: Path) -> None:
    root = project(tmp_path, 'paths = ["tests"]\n')
    sub = root / "sub"
    sub.mkdir()
    assert run(sub, ["--outdir", "cli-out", "cli-tests"]) == {**run(sub), "outdir": "cli-out", "paths": ["cli-tests"]}


def test_extended_file_paths_resolve_against_that_file(tmp_path: Path) -> None:
    shared = tmp_path / "shared"
    shared.mkdir()
    (shared / "base.toml").write_text('libs = ["lib"]\n')
    root = project(tmp_path, 'extends = "../shared/base.toml"\npaths = ["tests"]\n')
    result = run(root)
    assert result["libs"] == [str(shared.resolve() / "lib")]
    assert result["paths"] == [str(root.resolve() / "tests")]


def test_profile_paths_resolve_against_config_dir(tmp_path: Path) -> None:
    root = project(tmp_path, '[profiles.ci]\npaths = ["ci-tests"]\n')
    sub = root / "sub"
    sub.mkdir()
    assert run(sub, ["--profile", "ci"])["paths"] == [str(root.resolve() / "ci-tests")]


def test_explicit_config_paths_resolve_against_its_dir(tmp_path: Path) -> None:
    conf_dir = tmp_path / "conf"
    conf_dir.mkdir()
    (conf_dir / "custom.toml").write_text('outdir = "out"\n')
    (tmp_path / ".git").mkdir()
    assert run(tmp_path, ["--config", str(conf_dir / "custom.toml")])["outdir"] == str(conf_dir.resolve() / "out")


def test_existing_mode_resolves_only_values_that_exist_under_config_dir(tmp_path: Path) -> None:
    root = project(
        tmp_path,
        "listener = ['MyListener', 'tools/listener.py', 'tools/listener.py:a:b', "
        "'tools/listener.py;a', 'missing.py', 'pkg.Mod:arg']\n",
    )
    (root / "tools").mkdir()
    (root / "tools" / "listener.py").write_text("")
    sub = root / "sub"
    sub.mkdir()
    listener = str(root.resolve() / "tools" / "listener.py")
    assert run(sub)["listener"] == [
        "MyListener",
        listener,
        listener + ":a:b",
        listener + ";a",
        "missing.py",
        "pkg.Mod:arg",
    ]


def test_existing_mode_resolves_directories(tmp_path: Path) -> None:
    root = project(tmp_path, "listener = ['pkg:x']\n")
    (root / "pkg").mkdir()
    assert run(root / "pkg")["listener"] == [str(root.resolve() / "pkg") + ":x"]


def test_existing_mode_keeps_windows_drive_paths(tmp_path: Path) -> None:
    absolute = (tmp_path / "abs.py").resolve()
    root = project(tmp_path, f"listener = ['{absolute}:arg']\n")
    assert run(root)["listener"] == [f"{absolute}:arg"]


@pytest.mark.parametrize("value", ["yes", 1, None])
def test_invalid_relative_to_config_is_rejected(value: object) -> None:
    with pytest.raises(OptionDefinitionError, match="relative_to_config"):
        option(name="x", relative_to_config=value)  # type: ignore[arg-type]
    with pytest.raises(OptionDefinitionError, match="relative_to_config"):
        argument(name="x", relative_to_config=value)  # type: ignore[arg-type]
