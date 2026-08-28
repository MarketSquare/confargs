"""Ensure the shipped example / console entry-point stays correct."""

from __future__ import annotations

from pathlib import Path

import pytest

import confargs
from confargs import demo


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


def test_examples_wrapper_reexports_symbols() -> None:
    wrapper = Path(__file__).resolve().parent.parent / "examples" / "demo.py"
    assert wrapper.is_file()
    assert "from confargs.demo import" in wrapper.read_text(encoding="utf-8")
