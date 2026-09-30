"""Tests for reading dedicated config files from their top level."""

from __future__ import annotations

from pathlib import Path

import pytest

from confargs import ArgConfig, option
from confargs.exceptions import ConfigDiscoveryError
from confargs.processor import ConfigurationProcessor


class Tool(ArgConfig):
    tool_name = "mytool"
    config_names = ["mytool.toml", "pyproject.toml"]  # noqa: RUF012
    top_level_config_names = ["mytool.toml"]  # noqa: RUF012

    name: str | None = option(name="name", default=None)
    level: str = option(name="level", default="INFO")


def run(tmp_path: Path, argv: list[str] | None = None, cls: type[ArgConfig] = Tool) -> dict[str, object]:
    (tmp_path / ".git").mkdir(exist_ok=True)
    return ConfigurationProcessor(cls, argv=argv or [], environ={}, cwd=tmp_path).process().as_dict()


def test_dedicated_file_is_read_from_top_level(tmp_path: Path) -> None:
    (tmp_path / "mytool.toml").write_text('name = "top"\nlevel = "DEBUG"\n')
    result = run(tmp_path)
    assert (result["name"], result["level"]) == ("top", "DEBUG")


def test_section_is_still_accepted_in_dedicated_file(tmp_path: Path) -> None:
    (tmp_path / "mytool.toml").write_text('[tool.mytool]\nname = "section"\n')
    assert run(tmp_path)["name"] == "section"


def test_other_tools_tables_are_ignored_at_top_level(tmp_path: Path) -> None:
    (tmp_path / "mytool.toml").write_text('name = "top"\n[tool.other]\nx = 1\n')
    assert run(tmp_path)["name"] == "top"


def test_section_and_top_level_keys_together_is_an_error(tmp_path: Path) -> None:
    (tmp_path / "mytool.toml").write_text('level = "DEBUG"\n[tool.mytool]\nname = "section"\n')
    with pytest.raises(ConfigDiscoveryError, match=r"both a \[tool.mytool\] table and top-level keys \('level'\)"):
        run(tmp_path)


def test_top_level_is_not_read_from_other_config_names(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('name = "top"\n[project]\nname = "pkg"\n')
    assert run(tmp_path)["name"] is None


def test_dedicated_file_with_only_other_tools_falls_through(tmp_path: Path) -> None:
    (tmp_path / "mytool.toml").write_text("[tool.other]\nx = 1\n")
    (tmp_path / "pyproject.toml").write_text('[tool.mytool]\nname = "pyproject"\n')
    assert run(tmp_path)["name"] == "pyproject"


def test_top_level_is_ignored_when_feature_is_disabled(tmp_path: Path) -> None:
    class Plain(Tool):
        top_level_config_names = []  # noqa: RUF012

    (tmp_path / "mytool.toml").write_text('name = "top"\n')
    assert run(tmp_path, cls=Plain)["name"] is None


def test_profiles_live_at_top_level(tmp_path: Path) -> None:
    (tmp_path / "mytool.toml").write_text('name = "base"\n[profiles.ci]\nname = "ci"\n')
    assert run(tmp_path, ["--profile", "ci"])["name"] == "ci"


def test_explicit_config_file_may_use_top_level(tmp_path: Path) -> None:
    (tmp_path / "custom.toml").write_text('name = "custom"\n')
    assert run(tmp_path, ["--config", str(tmp_path / "custom.toml")])["name"] == "custom"


def test_explicit_pyproject_does_not_use_top_level(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('name = "top"\n')
    assert run(tmp_path, ["--config", str(tmp_path / "pyproject.toml")])["name"] is None


def test_extended_file_may_use_top_level(tmp_path: Path) -> None:
    (tmp_path / "base.toml").write_text('level = "TRACE"\nname = "base"\n')
    (tmp_path / "mytool.toml").write_text('extends = "base.toml"\nname = "own"\n')
    result = run(tmp_path)
    assert (result["name"], result["level"]) == ("own", "TRACE")


def test_extended_file_without_section_or_top_level_keys_is_an_error(tmp_path: Path) -> None:
    (tmp_path / "base.toml").write_text("[tool.other]\nx = 1\n")
    (tmp_path / "mytool.toml").write_text('extends = "base.toml"\n')
    with pytest.raises(ConfigDiscoveryError, match=r"has no \[tool.mytool\] section or top-level keys"):
        run(tmp_path)


def test_shared_file_name_is_only_top_level_for_its_own_tool(tmp_path: Path) -> None:
    class Other(ArgConfig):
        tool_name = "other"
        config_names = ["other.toml", "mytool.toml"]  # noqa: RUF012
        top_level_config_names = ["other.toml"]  # noqa: RUF012
        name: str | None = option(name="name", default=None)

    (tmp_path / "mytool.toml").write_text('name = "mytool-top"\n[tool.other]\nname = "other-section"\n')
    # For "other", mytool.toml is a shared file: only its [tool.other] table counts.
    assert run(tmp_path, cls=Other)["name"] == "other-section"
