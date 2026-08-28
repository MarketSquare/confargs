"""Integration tests for ConfigurationProcessor and Namespace."""

from __future__ import annotations

from pathlib import Path

import pytest

import confargs
from confargs import ArgConfig, ConfigurationProcessor, Namespace, option
from confargs.exceptions import OptionValueError


class MyArgs(ArgConfig):
    """My CLI tool.

    Extended docs here.
    """

    name = "mytool"
    config_names = ["pyproject.toml"]  # noqa: RUF012

    @option(env=True)
    def log(self, value: str | None = "log.html") -> str | None:
        """HTML log file. 'NONE' disables it."""
        if value == "NONE":
            return None
        return value

    @option(names="--console/-c")
    def console(self, value: str = "verbose") -> str:
        choices = ["verbose", "dotted", "quiet", "none"]
        if value not in choices:
            raise OptionValueError(f"console must be one of {choices}")
        return value

    @option(env=True)
    def retries(self, value: int = 3) -> int:
        return value

    @option
    def tags(self, value: list[str] | None = None) -> list[str] | None:
        return value


def make(argv: list[str], *, environ=None, cwd=None) -> Namespace:  # type: ignore[no-untyped-def]
    return ConfigurationProcessor(
        MyArgs,
        argv=argv,
        environ=environ or {},
        cwd=cwd,
    ).process()


def write_pyproject(tmp_path: Path, body: str) -> None:
    (tmp_path / "pyproject.toml").write_text(body, encoding="utf-8")


# --- defaults & basic resolution -------------------------------------------


def test_defaults_when_nothing_supplied(tmp_path: Path) -> None:
    config = make([], cwd=tmp_path)
    assert config.log == "log.html"
    assert config.console == "verbose"
    assert config.retries == 3
    assert config.tags is None


def test_cli_value_overrides_default(tmp_path: Path) -> None:
    config = make(["--log", "out.html", "-c", "quiet"], cwd=tmp_path)
    assert config.log == "out.html"
    assert config.console == "quiet"


def test_user_method_runs_special_none_value(tmp_path: Path) -> None:
    config = make(["--log", "NONE"], cwd=tmp_path)
    assert config.log is None


def test_int_coercion_from_cli(tmp_path: Path) -> None:
    config = make(["--retries", "7"], cwd=tmp_path)
    assert config.retries == 7


def test_repeatable_list_option(tmp_path: Path) -> None:
    config = make(["--tags", "a", "--tags", "b"], cwd=tmp_path)
    assert config.tags == ["a", "b"]


def test_validation_error_propagates(tmp_path: Path) -> None:
    with pytest.raises(OptionValueError):
        make(["--console", "bogus"], cwd=tmp_path)


# --- TOML source ------------------------------------------------------------


def test_toml_values_are_used(tmp_path: Path) -> None:
    write_pyproject(tmp_path, "[tool.mytool]\nlog = 'from-toml.html'\nretries = 9\n")
    config = make([], cwd=tmp_path)
    assert config.log == "from-toml.html"
    assert config.retries == 9


def test_toml_accepts_dashed_keys(tmp_path: Path) -> None:
    class T(ArgConfig):
        name = "t"

        @option
        def dry_run(self, value: bool = False) -> bool:
            return value

    (tmp_path / "pyproject.toml").write_text("[tool.t]\ndry-run = true\n", encoding="utf-8")
    config = ConfigurationProcessor(T, argv=[], environ={}, cwd=tmp_path).process()
    assert config.dry_run is True


def test_toml_native_list(tmp_path: Path) -> None:
    write_pyproject(tmp_path, "[tool.mytool]\ntags = ['x', 'y']\n")
    config = make([], cwd=tmp_path)
    assert config.tags == ["x", "y"]


# --- precedence -------------------------------------------------------------


def test_cli_beats_env_beats_toml(tmp_path: Path) -> None:
    write_pyproject(tmp_path, "[tool.mytool]\nlog = 'toml.html'\n")
    environ = {"MYTOOL_LOG": "env.html"}
    # CLI wins
    assert make(["--log", "cli.html"], environ=environ, cwd=tmp_path).log == "cli.html"
    # env beats toml
    assert make([], environ=environ, cwd=tmp_path).log == "env.html"
    # toml beats default
    assert make([], environ={}, cwd=tmp_path).log == "toml.html"


def test_env_int_coercion(tmp_path: Path) -> None:
    config = make([], environ={"MYTOOL_RETRIES": "5"}, cwd=tmp_path)
    assert config.retries == 5


# --- discovery-control options ---------------------------------------------


def test_no_config_skips_toml(tmp_path: Path) -> None:
    write_pyproject(tmp_path, "[tool.mytool]\nlog = 'toml.html'\n")
    config = make(["--no-config"], cwd=tmp_path)
    assert config.log == "log.html"


def test_explicit_config_path(tmp_path: Path) -> None:
    other = tmp_path / "custom.toml"
    other.write_text("[tool.mytool]\nlog = 'custom.html'\n", encoding="utf-8")
    config = make(["--config", str(other)], cwd=tmp_path)
    assert config.log == "custom.html"


def test_cli_only_option_in_toml_is_rejected_when_strict(tmp_path: Path) -> None:
    # no_config is config=False; setting it in TOML is an error under strict mode.
    write_pyproject(tmp_path, "[tool.mytool]\nno_config = true\nlog = 'toml.html'\n")
    with pytest.raises(confargs.ConfigDiscoveryError):
        make([], cwd=tmp_path)


def test_unknown_toml_key_rejected_when_strict(tmp_path: Path) -> None:
    write_pyproject(tmp_path, "[tool.mytool]\nnope = 1\n")
    with pytest.raises(confargs.ConfigDiscoveryError):
        make([], cwd=tmp_path)


def test_non_strict_ignores_invalid_toml_keys(tmp_path: Path) -> None:
    class Lax(MyArgs):
        strict_config = False

    (tmp_path / "pyproject.toml").write_text(
        "[tool.mytool]\nno_config = true\nnope = 1\nlog = 'toml.html'\n",
        encoding="utf-8",
    )
    config = ConfigurationProcessor(Lax, argv=[], environ={}, cwd=tmp_path).process()
    assert config.no_config is False
    assert config.log == "toml.html"


def test_explicit_config_skips_discovery(tmp_path: Path) -> None:
    # A discoverable pyproject with an invalid key would raise if it were read;
    # --config must bypass discovery and use only the given file.
    write_pyproject(tmp_path, "[tool.mytool]\nbad_key = 1\n")
    other = tmp_path / "custom.toml"
    other.write_text("[tool.mytool]\nlog = 'custom.html'\n", encoding="utf-8")
    config = make(["--config", str(other)], cwd=tmp_path)
    assert config.log == "custom.html"


# --- help & namespace -------------------------------------------------------


def test_help_raises_exit(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(confargs.Exit) as exc:
        make(["--help"], cwd=tmp_path)
    assert exc.value.code == 0
    assert "My CLI tool" in capsys.readouterr().out


def test_namespace_attr_and_item_access(tmp_path: Path) -> None:
    config = make(["--log", "x.html"], cwd=tmp_path)
    assert config.log == config["log"] == "x.html"
    assert "log" in config
    assert config.as_dict()["console"] == "verbose"


def test_namespace_is_immutable(tmp_path: Path) -> None:
    config = make([], cwd=tmp_path)
    with pytest.raises(AttributeError):
        config.log = "nope"  # type: ignore[misc]


def test_namespace_unknown_attr_raises(tmp_path: Path) -> None:
    config = make([], cwd=tmp_path)
    with pytest.raises(AttributeError):
        _ = config.does_not_exist


def test_positionals_captured(tmp_path: Path) -> None:
    proc = ConfigurationProcessor(MyArgs, argv=["file1", "file2"], environ={}, cwd=tmp_path)
    proc.process()
    assert proc.positionals == ["file1", "file2"]


def test_required_option_without_default_raises(tmp_path: Path) -> None:
    class R(ArgConfig):
        name = "r"

        @option
        def token(self, value: str) -> str:
            return value

    with pytest.raises(OptionValueError):
        ConfigurationProcessor(R, argv=[], environ={}, cwd=tmp_path).process()


def test_flag_negation_overrides_toml_true(tmp_path: Path) -> None:
    class Flags(ArgConfig):
        name = "flags"

        @option
        def color(self, value: bool = True) -> bool:
            return value

    (tmp_path / "pyproject.toml").write_text("[tool.flags]\ncolor = true\n", encoding="utf-8")

    default_cfg = ConfigurationProcessor(Flags, argv=[], environ={}, cwd=tmp_path).process()
    assert default_cfg.color is True

    negated = ConfigurationProcessor(Flags, argv=["--no-color"], environ={}, cwd=tmp_path).process()
    assert negated.color is False
