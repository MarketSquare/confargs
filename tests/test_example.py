"""Ensure the shipped example stays importable and correct."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import argconfig

EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "demo.py"


def load_example():  # type: ignore[no-untyped-def]
    spec = importlib.util.spec_from_file_location("argconfig_demo", EXAMPLE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_example_resolves_overrides(tmp_path: Path) -> None:
    demo = load_example()
    config = argconfig.ConfigurationProcessor(
        demo.MyArgs,
        argv=["--no-config", "-c", "quiet", "--retries", "5", "--log", "NONE"],
        environ={},
        cwd=tmp_path,
    ).process()
    assert config.console == "quiet"
    assert config.retries == 5
    assert config.log is None
