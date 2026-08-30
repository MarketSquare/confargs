"""A Robot Framework-style CLI parser modelled with :mod:`confargs`.

This mirrors a representative subset of the real ``robot`` command-line
interface — the option names, short flags, repeatable ("``*``") options, boolean
switches, help text and the eager ``--argumentfile`` handling — so that the
behaviour of confargs can be exercised against realistic Robot Framework
command lines.

Option help strings are lifted from Robot Framework's own usage text so the
generated ``--help`` output reads like the tool it emulates. Only the light
parsing/validation Robot Framework performs up front is reproduced here; the
heavy lifting is intentionally left to confargs's shared coercion path.

The example models current confargs best practice:

* pure pass-through values are declared as **plain attributes** with an explicit
  type annotation (``name: str = option(...)``) rather than as methods;
* repeatable options default to an empty list via ``default=list`` so the
  attribute type is a clean ``list[str]`` (no ``| None`` / ``value or []``);
* fixed choice sets are expressed with ``typing.Literal[...]`` so confargs
  validates them and shows them in ``--help``;
* only options that genuinely parse or validate (``--variable``, ``--log``,
  ``--loglevel``, ``--argumentfile`` ...) keep a decorated method.
"""

from __future__ import annotations

import sys
from typing import Literal

from confargs import (
    ArgConfig,
    Exit,
    OptionValueError,
    argument,
    option,
    read_argument_file,
    split_argument_file,
)

RANDOMIZE_CHOICES = ("all", "suites", "tests", "none")
LOG_LEVELS = ("TRACE", "DEBUG", "INFO", "WARN", "ERROR", "NONE")


class RobotArgs(ArgConfig):
    """Robot Framework -- a generic automation framework.

    Usage: robot [options] data_sources

    Executes Robot Framework test/task data. This parser is a faithful subset
    of the real command-line interface, rebuilt with confargs.
    """

    name = "robot"
    config_names = ["pyproject.toml", "robot.toml"]  # noqa: RUF012 - per-subclass override

    # --- Positional arguments ----------------------------------------------
    # The data sources (suite files or directories) Robot Framework executes.
    # A pure pass-through variadic argument needs no method; the annotation
    # documents its resolved type.
    data_sources: list[str] = argument(
        name="data-sources",
        nargs="*",
        help="Paths to the test data (suite files or directories) to execute.",
    )

    # --- Eager option: expands an argument file into more options -----------
    @option(name="argumentfile", short="A", config=False, is_eager=True)
    def argumentfile(self, value: str | None = None) -> list[str] | None:
        """Text file to read more arguments from. Use special value `STDIN` to
        read arguments from the standard input stream.
        """
        if not value:
            return None
        if value.upper() == "STDIN":
            return split_argument_file(sys.stdin.read())
        return read_argument_file(value)

    # --- Suite / test selection --------------------------------------------
    # Pure pass-through options are plain attributes. Optional scalars annotate
    # ``str | None``; repeatable options use ``default=list`` for a clean
    # ``list[str]`` with an empty-list default.
    name_: str | None = option(
        name="name",
        short="N",
        default=None,
        help="Set the name of the top level suite. By default the name is "
        "created based on the executed file or directory.",
    )

    doc: str | None = option(
        name="doc",
        short="D",
        default=None,
        help="Set the documentation of the top level suite.",
    )

    metadata: list[str] = option(
        name="metadata",
        short="M",
        default=list,
        help="Set metadata of the top level suite. Value can contain formatting.",
    )

    settag: list[str] = option(
        name="settag",
        short="G",
        default=list,
        help="Sets given tag(s) to all executed tests.",
    )

    test: list[str] = option(
        name="test",
        short="t",
        default=list,
        help="Select tests by name or by long name containing also parent "
        "suite name like `Parent.Test`. Name is case and space insensitive.",
    )

    suite: list[str] = option(
        name="suite",
        short="s",
        default=list,
        help="Select suites by name.",
    )

    include: list[str] = option(
        name="include",
        short="i",
        default=list,
        help="Select tests by tag.",
    )

    exclude: list[str] = option(
        name="exclude",
        short="e",
        default=list,
        help="Select tests not matching by tag.",
    )

    # --- Variables ----------------------------------------------------------
    @option(name="variable", short="v")
    def variable(self, value: list[str] | None = None) -> list[tuple[str, str]]:
        """Set variables in the test data. Only scalar variables with string
        value are supported. Example: --variable name:value.
        """
        parsed: list[tuple[str, str]] = []
        for item in value or []:
            if ":" not in item:
                raise OptionValueError(f"invalid --variable value {item!r}; expected NAME:VALUE")
            key, _, val = item.partition(":")
            parsed.append((key, val))
        return parsed

    variablefile: list[str] = option(
        name="variablefile",
        short="V",
        default=list,
        help="Python or YAML file to read variables from.",
    )

    # --- Output files -------------------------------------------------------
    outputdir: str = option(
        name="outputdir",
        short="d",
        default=".",
        help="Where to create output files. The default is the directory where "
        "tests are run from and the given path is considered relative to that.",
    )

    output: str = option(
        name="output",
        short="o",
        default="output.xml",
        help="XML output file.",
    )

    @option(name="log", short="l")
    def log(self, value: str | None = "log.html") -> str | None:
        """HTML log file. Can be disabled by giving a special value `NONE`.
        Examples: `--log mylog.html`, `-l NONE`.
        """
        if value is None or value.upper() == "NONE":
            return None
        return value

    @option(name="report", short="r")
    def report(self, value: str | None = "report.html") -> str | None:
        """HTML report file. Can be disabled with `NONE` similarly as --log."""
        if value is None or value.upper() == "NONE":
            return None
        return value

    xunit: str | None = option(
        name="xunit",
        short="x",
        default=None,
        help="xUnit compatible result file. Not created unless this option is specified.",
    )

    @option(name="loglevel", short="L")
    def loglevel(self, value: str = "INFO") -> str:
        """Threshold level for logging. Available levels: TRACE, DEBUG, INFO
        (default), WARN, ERROR and NONE. Use syntax `LOGLEVEL:DEFAULT` to
        also set the default visible level.
        """
        threshold = value.split(":", 1)[0].upper()
        if threshold not in LOG_LEVELS:
            raise OptionValueError(f"invalid --loglevel {value!r}; available levels: {', '.join(LOG_LEVELS)}")
        return value

    # --- Execution switches -------------------------------------------------
    dryrun: bool = option(
        name="dryrun",
        default=False,
        help="Verifies test data and runs tests so that library keywords are not executed.",
    )

    exitonfailure: bool = option(
        name="exitonfailure",
        short="X",
        default=False,
        help="Stops test execution if any critical test fails.",
    )

    skiponfailure: list[str] = option(
        name="skiponfailure",
        default=list,
        help="Tests having given tag will be skipped if they fail.",
    )

    rpa: bool = option(
        name="rpa",
        default=False,
        help="Turn on the generic automation mode. Negate with --no-rpa.",
    )

    statusrc: bool = option(
        name="statusrc",
        default=True,
        help="Set the return code to zero regardless of failures with "
        "--no-statusrc. Error codes are returned normally.",
    )

    # Fixed choice sets are expressed with ``Literal[...]``: confargs validates
    # the value and lists the choices in ``--help``.
    console: Literal["verbose", "dotted", "quiet", "none"] = option(
        name="console",
        default="verbose",
        help="How to report execution on the console.",
    )

    dotted: bool = option(
        name="dotted",
        short=".",
        default=False,
        help="Shortcut for `--console dotted`.",
    )

    quiet: bool = option(
        name="quiet",
        default=False,
        help="Shortcut for `--console quiet`.",
    )

    pythonpath: list[str] = option(
        name="pythonpath",
        short="P",
        default=list,
        help="Additional locations (directories, ZIPs) where to search "
        "libraries and other extensions when they are imported.",
    )

    # --- Re-running and ordering -------------------------------------------
    rerunfailed: str | None = option(
        name="rerunfailed",
        short="R",
        default=None,
        help="Select failed tests from an earlier output file to re-execute.",
    )

    rerunfailedsuites: str | None = option(
        name="rerunfailedsuites",
        short="S",
        default=None,
        help="Select failed suites from an earlier output file to re-execute.",
    )

    @option(name="randomize")
    def randomize(self, value: str = "none") -> str:
        """Randomize the test execution order. Valid values are `all`,
        `suites`, `tests` and `none` (default). An optional `:seed` suffix
        pins the randomization, e.g. `--randomize all:12345`.
        """
        normalized = value.split(":", 1)[0].lower()
        if normalized not in RANDOMIZE_CHOICES:
            raise OptionValueError(f"invalid --randomize {value!r}; choose from {', '.join(RANDOMIZE_CHOICES)}")
        return value

    # --- Output tuning ------------------------------------------------------
    logtitle: str | None = option(name="logtitle", default=None, help="Title for the generated log file.")

    reporttitle: str | None = option(name="reporttitle", default=None, help="Title for the generated report.")

    debugfile: str | None = option(
        name="debugfile",
        short="b",
        default=None,
        help="Debug file written during execution. Not created unless given.",
    )

    timestampoutputs: bool = option(
        name="timestampoutputs",
        short="T",
        default=False,
        help="Add a timestamp to all generated output files.",
    )

    splitlog: bool = option(
        name="splitlog",
        default=False,
        help="Split the log file into smaller pieces that open in browsers transparently.",
    )

    removekeywords: list[str] = option(
        name="removekeywords",
        default=list,
        help="Remove keyword data from the generated log file. Data can be "
        "removed e.g. based on keyword status, name or type.",
    )

    flattenkeywords: list[str] = option(
        name="flattenkeywords",
        default=list,
        help="Flatten matching keywords in the generated log file.",
    )

    expandkeywords: list[str] = option(
        name="expandkeywords",
        default=list,
        help="Matching keywords are automatically expanded in the log file.",
    )

    maxerrorlines: int = option(
        name="maxerrorlines",
        default=40,
        help="Maximum number of error message lines to show in the report and log.",
    )

    maxassignlength: int = option(
        name="maxassignlength",
        default=200,
        help="Maximum number of characters to show in log for assigned variables.",
    )

    # --- Tag statistics -----------------------------------------------------
    tagstatinclude: list[str] = option(
        name="tagstatinclude",
        default=list,
        help="Include only matching tags in the generated statistics.",
    )

    tagstatexclude: list[str] = option(
        name="tagstatexclude",
        default=list,
        help="Exclude matching tags from the generated statistics.",
    )

    tagstatcombine: list[str] = option(
        name="tagstatcombine",
        default=list,
        help="Create combined statistics based on tags.",
    )

    suitestatlevel: int = option(
        name="suitestatlevel",
        default=0,
        help="How many levels to show in the `Statistics by Suite` table. 0 shows all.",
    )

    # --- Extensions ---------------------------------------------------------
    listener: list[str] = option(
        name="listener",
        default=list,
        help="A listener interface to monitor test execution.",
    )

    prerunmodifier: list[str] = option(
        name="prerunmodifier",
        default=list,
        help="Programmatic modifier for the test data before execution.",
    )

    prerebotmodifier: list[str] = option(
        name="prerebotmodifier",
        default=list,
        help="Programmatic modifier for the results before report/log creation.",
    )

    parser: list[str] = option(
        name="parser",
        default=list,
        help="Custom parser for parsing data in non-default formats.",
    )

    language: list[str] = option(
        name="language",
        default=list,
        help="Activate localization by giving one or more language codes or names.",
    )

    # --- Skipping and empty suites -----------------------------------------
    skip: list[str] = option(
        name="skip",
        default=list,
        help="Tests having the given tag will be skipped unconditionally.",
    )

    runemptysuite: bool = option(
        name="runemptysuite",
        default=False,
        help="Execute test suite even if it contains no tests.",
    )

    exitonerror: bool = option(
        name="exitonerror",
        default=False,
        help="Stop execution if any error occurs when parsing test data or importing libraries.",
    )

    # --- Console output -----------------------------------------------------
    consolecolors: Literal["auto", "on", "ansi", "off"] = option(
        name="consolecolors",
        short="C",
        default="auto",
        help="Use colors on console output.",
    )

    consolemarkers: Literal["auto", "on", "off"] = option(
        name="consolemarkers",
        short="K",
        default="auto",
        help="Show markers on the console when top-level keywords in a test end.",
    )

    consolewidth: int = option(
        name="consolewidth",
        short="W",
        default=78,
        help="Width of the console output.",
    )

    @option(name="version", config=False)
    def version(self, value: bool = False) -> bool:
        """Print version information and exit."""
        if value:
            print("Robot Framework 7.0 (confargs demo)")
            raise Exit(0)
        return value
