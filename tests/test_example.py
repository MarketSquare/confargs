"""Ensure the shipped example / console entry-point stays correct."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

import confargs
from confargs import demo

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


def _load_example() -> ModuleType:
    """Import ``examples/demo.py`` by path so the example is actually executed."""
    path = EXAMPLES_DIR / "demo.py"
    spec = importlib.util.spec_from_file_location("confargs_example_demo", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_example_resolves_overrides(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    config = confargs.ConfigurationProcessor(
        demo.MyArgs,
        argv=["--no-config", "-c", "quiet", "--retries", "5", "--log", "NONE"],
        environ={},
        cwd=tmp_path,
    ).process()
    assert config.console == "quiet"
    assert config.retries == 5
    assert config.log is None


def test_main_success_returns_zero(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert demo.main(["--no-config", "--console", "dotted"]) == 0


def test_main_help_returns_zero(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert demo.main(["--help"]) == 0


def test_main_invalid_value_returns_error_code(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert demo.main(["--no-config", "--console", "bogus"]) == 2


def test_example_runs_and_greets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    example = _load_example()
    assert example.main(["--no-config", "--who", "Ada", "--repeat", "2", "--no-color"]) == 0
    out = capsys.readouterr().out
    assert out.count("Hello, Ada!") == 2
    assert "\033[" not in out  # --no-color disabled the color codes


def test_example_reads_argument_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    example = _load_example()
    argfile = EXAMPLES_DIR / "example.args"
    assert example.main(["--no-config", "-A", str(argfile)]) == 0
    out = capsys.readouterr().out
    # example.args sets --who Ada --repeat 2 --no-color
    assert out.count("Hello, Ada!") == 2
    assert "\033[" not in out
