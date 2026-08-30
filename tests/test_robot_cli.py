"""Data-driven tests exercising confargs against Robot Framework CLI data.

The command lines below are shaped like real ``robot`` invocations. Each case
lists the arguments and the expected resolved values, so the suite doubles as a
specification of how confargs models Robot Framework's options.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import pytest

from confargs import ConfigurationProcessor, Exit
from confargs.exceptions import CliUsageError, OptionValueError

from .robot_cli import RobotArgs


def run(argv: list[str], tmp_path: Path) -> tuple[ConfigurationProcessor, Any]:
    processor = ConfigurationProcessor(RobotArgs, argv=argv, environ={}, cwd=tmp_path)
    return processor, processor.process()


# (id, argv, expected {attr: value})
CASES: list[tuple[str, list[str], dict[str, Any]]] = [
    (
        "top-level-name",
        ["--name", "My Suite", "tests/"],
        {"name_": "My Suite"},
    ),
    (
        "repeatable-include",
        ["-N", "Suite", "-i", "smoke", "-i", "regression", "tests"],
        {"include": ["smoke", "regression"]},
    ),
    (
        "variables-parsed",
        ["--variable", "BROWSER:chrome", "--variable", "ENV:ci", "tests"],
        {"variable": [("BROWSER", "chrome"), ("ENV", "ci")]},
    ),
    (
        "variable-value-with-colon",
        ["-v", "URL:http://example.com", "tests"],
        {"variable": [("URL", "http://example.com")]},
    ),
    (
        "disable-log-and-report",
        ["--log", "NONE", "--report", "NONE", "tests"],
        {"log": None, "report": None},
    ),
    (
        "output-files",
        ["-d", "results", "-o", "res.xml", "-x", "xunit.xml", "tests"],
        {"outputdir": "results", "output": "res.xml", "xunit": "xunit.xml"},
    ),
    (
        "execution-switches",
        ["--dryrun", "--exitonfailure", "tests"],
        {"dryrun": True, "exitonfailure": True},
    ),
    (
        "short-exitonfailure",
        ["-X", "tests"],
        {"exitonfailure": True},
    ),
    (
        "flag-negation",
        ["--rpa", "--no-statusrc", "tests"],
        {"rpa": True, "statusrc": False},
    ),
    (
        "console-mode",
        ["--console", "dotted", "tests"],
        {"console": "dotted"},
    ),
    (
        "dotted-shortcut",
        ["-.", "tests"],
        {"dotted": True},
    ),
    (
        "metadata-repeatable",
        ["-M", "Version:1.0", "-M", "Author:me", "tests"],
        {"metadata": ["Version:1.0", "Author:me"]},
    ),
    (
        "loglevel-with-default",
        ["-L", "DEBUG:INFO", "tests"],
        {"loglevel": "DEBUG:INFO"},
    ),
    (
        "selection-combo",
        ["--suite", "s1", "--test", "t1", "--exclude", "slow", "tests"],
        {"suite": ["s1"], "test": ["t1"], "exclude": ["slow"]},
    ),
    (
        "attached-short-value",
        ["-Nmyname", "tests"],
        {"name_": "myname"},
    ),
    (
        "long-equals-form",
        ["--name=Equals Suite", "tests"],
        {"name_": "Equals Suite"},
    ),
    (
        "data-sources-argument",
        ["--dryrun", "tests/suite_a", "tests/suite_b"],
        {"data_sources": ["tests/suite_a", "tests/suite_b"]},
    ),
    (
        "int-options-coerced",
        ["--maxerrorlines", "10", "--consolewidth", "120", "--suitestatlevel", "2", "tests"],
        {"maxerrorlines": 10, "consolewidth": 120, "suitestatlevel": 2},
    ),
    (
        "console-color-and-markers",
        ["-C", "on", "-K", "off", "tests"],
        {"consolecolors": "on", "consolemarkers": "off"},
    ),
    (
        "randomize-mode",
        ["--randomize", "suites", "tests"],
        {"randomize": "suites"},
    ),
    (
        "rerun-and-tagstats",
        ["-R", "out.xml", "--tagstatinclude", "smoke", "--skip", "wip", "tests"],
        {"rerunfailed": "out.xml", "tagstatinclude": ["smoke"], "skip": ["wip"]},
    ),
    (
        "new-flags",
        ["--timestampoutputs", "--splitlog", "--runemptysuite", "tests"],
        {"timestampoutputs": True, "splitlog": True, "runemptysuite": True},
    ),
    (
        "defaults-only",
        ["tests"],
        {
            "log": "log.html",
            "report": "report.html",
            "output": "output.xml",
            "outputdir": ".",
            "console": "verbose",
            "loglevel": "INFO",
            "statusrc": True,
            "rpa": False,
            "dryrun": False,
            "include": [],
            "variable": [],
            "data_sources": ["tests"],
            "maxerrorlines": 40,
            "consolewidth": 78,
            "consolecolors": "auto",
            "randomize": "none",
            "skip": [],
        },
    ),
]


@pytest.mark.parametrize(
    ("argv", "expected"),
    [(argv, expected) for _, argv, expected in CASES],
    ids=[c[0] for c in CASES],
)
def test_robot_command_lines(argv: list[str], expected: dict[str, Any], tmp_path: Path) -> None:
    _, ns = run(argv, tmp_path)
    for attr, value in expected.items():
        assert getattr(ns, attr) == value, attr


def test_positional_data_sources_are_collected(tmp_path: Path) -> None:
    _, ns = run(["--dryrun", "tests/suite_a", "tests/suite_b"], tmp_path)
    assert ns.data_sources == ["tests/suite_a", "tests/suite_b"]


def test_double_dash_terminates_options(tmp_path: Path) -> None:
    processor, ns = run(["--name", "S", "--", "--not-an-option", "tests"], tmp_path)
    assert ns.name_ == "S"
    assert ns.data_sources == ["--not-an-option", "tests"]
    assert processor.positionals == []


@pytest.mark.parametrize(
    ("argv", "match"),
    [
        (["--console", "fancy", "tests"], "invalid value 'fancy'"),
        (["--variable", "novalue", "tests"], "variable"),
        (["--loglevel", "BOGUS", "tests"], "loglevel"),
        (["--randomize", "maybe", "tests"], "randomize"),
        (["--consolecolors", "rainbow", "tests"], "invalid value 'rainbow'"),
        (["--consolemarkers", "sometimes", "tests"], "invalid value 'sometimes'"),
    ],
)
def test_invalid_values_are_rejected(argv: list[str], match: str, tmp_path: Path) -> None:
    with pytest.raises(OptionValueError, match=match):
        run(argv, tmp_path)


def test_unknown_option_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(CliUsageError, match="unknown option"):
        run(["--nonexistent", "tests"], tmp_path)


def test_version_exits(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(Exit) as excinfo:
        run(["--version"], tmp_path)
    assert excinfo.value.code == 0
    assert "Robot Framework" in capsys.readouterr().out


# --- Argument-file (eager) behaviour -----------------------------------------


def test_argumentfile_expands_options(tmp_path: Path) -> None:
    argfile = tmp_path / "args.robot"
    argfile.write_text(
        "# common CI arguments\n--name CI Suite\n--include smoke\n--variable ENV:ci\n--dryrun\n",
        encoding="utf-8",
    )

    _, ns = run(["-A", str(argfile), "tests"], tmp_path)
    assert ns.name_ == "CI Suite"
    assert ns.include == ["smoke"]
    assert ns.variable == [("ENV", "ci")]
    assert ns.dryrun is True


def test_argumentfile_then_cli_override(tmp_path: Path) -> None:
    argfile = tmp_path / "args.robot"
    argfile.write_text("--name FromFile\n--include base\n", encoding="utf-8")

    _, ns = run(["-A", str(argfile), "--name", "FromCli", "--include", "extra", "tests"], tmp_path)
    # Scalar: the later CLI value wins.
    assert ns.name_ == "FromCli"
    # Repeatable: both the file's and the CLI's values are kept, in order.
    assert ns.include == ["base", "extra"]


def test_nested_argument_files(tmp_path: Path) -> None:
    base = tmp_path / "base.robot"
    base.write_text("--variable SHARED:yes\n--loglevel DEBUG\n", encoding="utf-8")
    top = tmp_path / "top.robot"
    top.write_text(f"--name Nested\n--argumentfile {base}\n--include smoke\n", encoding="utf-8")

    _, ns = run(["-A", str(top), "tests"], tmp_path)
    assert ns.name_ == "Nested"
    assert ns.variable == [("SHARED", "yes")]
    assert ns.loglevel == "DEBUG"
    assert ns.include == ["smoke"]


def test_argumentfile_equals_and_name_value_forms(tmp_path: Path) -> None:
    argfile = tmp_path / "args.robot"
    # Mix of `name value`, `name=value` and a bare positional line.
    argfile.write_text("--name=Equals Name\n--loglevel DEBUG\ntests/from_file\n", encoding="utf-8")

    processor, ns = run([f"--argumentfile={argfile}"], tmp_path)
    assert ns.name_ == "Equals Name"
    assert ns.loglevel == "DEBUG"
    assert ns.data_sources == ["tests/from_file"]
    assert processor.positionals == []


def test_argumentfile_from_stdin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("--name FromStdin\n--dryrun\n"))
    _, ns = run(["-A", "STDIN", "tests"], tmp_path)
    assert ns.name_ == "FromStdin"
    assert ns.dryrun is True
