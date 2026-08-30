"""Tests for configuration profiles (``--profile`` overlays)."""

from __future__ import annotations

from pathlib import Path

import pytest

import confargs
from confargs import ArgConfig, option
from confargs.exceptions import ConfigDiscoveryError

TOML = """
[tool.myapp]
loglevel = "INFO"
console = "verbose"
tags = ["base"]

[tool.myapp.profiles.ci]
loglevel = "DEBUG"
console = "dotted"
tags = ["ci"]

[tool.myapp.profiles.dev]
inherits = ["ci"]
console = "verbose"

[tool.myapp.profiles.high]
precedence = 10
loglevel = "TRACE"

[tool.myapp.profiles.off]
enabled = false
loglevel = "ERROR"

[tool.myapp.profiles.ci-linux]
loglevel = "WARN"
"""


class App(ArgConfig):
    tool_name = "myapp"

    loglevel: str = option(name="loglevel", default="INFO")
    console: str = option(name="console", default="verbose")
    tags: list[str] = option(name="tags", default=list)


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").write_text(TOML, encoding="utf-8")
    return tmp_path


def run(argv: list[str], cwd: Path) -> confargs.Namespace:
    return confargs.ConfigurationProcessor(App, argv=argv, environ={}, cwd=cwd).process()


def test_no_profile_uses_base(project: Path) -> None:
    ns = run([], project)
    assert (ns.loglevel, ns.console, ns.tags) == ("INFO", "verbose", ["base"])


def test_single_profile_overrides_base(project: Path) -> None:
    ns = run(["--profile", "ci"], project)
    assert (ns.loglevel, ns.console, ns.tags) == ("DEBUG", "dotted", ["ci"])


def test_list_values_are_replaced_not_appended(project: Path) -> None:
    assert run(["--profile", "ci"], project).tags == ["ci"]


def test_inherits_merges_parent_first(project: Path) -> None:
    ns = run(["--profile", "dev"], project)
    # dev inherits ci (DEBUG, tags=ci) then overrides console back to verbose.
    assert (ns.loglevel, ns.console, ns.tags) == ("DEBUG", "verbose", ["ci"])


def test_cli_overrides_profile(project: Path) -> None:
    assert run(["--profile", "ci", "--loglevel", "WARN"], project).loglevel == "WARN"


def test_precedence_orders_multiple_profiles(project: Path) -> None:
    # high has precedence 10 so it is applied last regardless of selection order.
    assert run(["--profile", "high", "--profile", "ci"], project).loglevel == "TRACE"
    assert run(["--profile", "ci", "--profile", "high"], project).loglevel == "TRACE"


def test_disabled_profile_is_skipped(project: Path) -> None:
    assert run(["--profile", "off"], project).loglevel == "INFO"


def test_glob_selection(project: Path) -> None:
    # ci-* matches only ci-linux.
    assert run(["--profile", "ci-*"], project).loglevel == "WARN"


def test_glob_star_selects_all_enabled(project: Path) -> None:
    ns = run(["--profile", "*"], project)
    # off is disabled; high (precedence 10) wins for loglevel.
    assert ns.loglevel == "TRACE"


def test_unknown_profile_errors(project: Path) -> None:
    with pytest.raises(ConfigDiscoveryError, match="unknown profile 'nope'"):
        run(["--profile", "nope"], project)


def test_profile_requested_without_config_errors(tmp_path: Path) -> None:
    with pytest.raises(ConfigDiscoveryError, match="no configuration file was found"):
        run(["--profile", "ci"], tmp_path)


def test_profiles_table_is_not_a_config_key(project: Path) -> None:
    # The reserved 'profiles' table must not trip strict-config validation.
    ns = run([], project)
    assert ns.loglevel == "INFO"


def test_circular_inheritance_errors(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        """
[tool.myapp]
loglevel = "INFO"

[tool.myapp.profiles.a]
inherits = ["b"]

[tool.myapp.profiles.b]
inherits = ["a"]
""",
        encoding="utf-8",
    )
    with pytest.raises(ConfigDiscoveryError, match="circular profile inheritance"):
        run(["--profile", "a"], tmp_path)


def test_inherits_unknown_profile_errors(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        """
[tool.myapp]
loglevel = "INFO"

[tool.myapp.profiles.a]
inherits = ["ghost"]
""",
        encoding="utf-8",
    )
    with pytest.raises(ConfigDiscoveryError, match="inherits from unknown profile 'ghost'"):
        run(["--profile", "a"], tmp_path)


def test_profile_from_explicit_config(project: Path) -> None:
    config = project / "pyproject.toml"
    ns = confargs.ConfigurationProcessor(
        App, argv=["--config", str(config), "--profile", "ci"], environ={}, cwd=project
    ).process()
    assert ns.loglevel == "DEBUG"


def test_profile_value_still_below_cli_and_above_default(project: Path) -> None:
    # console default is "verbose"; ci sets "dotted"; no CLI override -> profile wins.
    assert run(["--profile", "ci"], project).console == "dotted"
