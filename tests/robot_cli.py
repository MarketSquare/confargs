"""A Robot Framework-style CLI parser modelled with :mod:`confargs`.

This mirrors a representative subset of the real ``robot`` command-line
interface — the option names, short flags, repeatable ("``*``") options, boolean
switches, help text and the eager ``--argumentfile`` handling — so that the
behaviour of confargs can be exercised against realistic Robot Framework
command lines.

Option help strings are lifted from Robot Framework's own usage text so the
generated ``--help`` output reads like the tool it emulates. Only the light
parsing/validation Robot Framework performs up front is reproduced here; the
heavy lifting is intentionally left to confargs's shared coercion path. Options
that need no parsing or validation are declared in the short attribute form
(``name_ = option(...)``); the rest use decorated methods.
"""

from __future__ import annotations

import sys

from confargs import (
    ArgConfig,
    Exit,
    OptionValueError,
    argument,
    option,
    read_argument_file,
    split_argument_file,
)

CONSOLE_CHOICES = ("verbose", "dotted", "quiet", "none")
CONSOLE_COLOR_CHOICES = ("auto", "on", "ansi", "off")
CONSOLE_MARKER_CHOICES = ("auto", "on", "off")
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
    # A pure pass-through variadic argument needs no method.
    data_sources = argument(
        name="data-sources",
        nargs="*",
        type=list[str],
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
    # Pure pass-through options (no parsing/validation) are declared as plain
    # attributes rather than methods.
    name_ = option(
        name="name",
        short="N",
        default=None,
        help="Set the name of the top level suite. By default the name is "
        "created based on the executed file or directory.",
    )

    doc = option(
        name="doc",
        short="D",
        default=None,
        help="Set the documentation of the top level suite.",
    )

    @option(name="metadata", short="M")
    def metadata(self, value: list[str] | None = None) -> list[str]:
        """Set metadata of the top level suite. Value can contain formatting."""
        return value or []

    @option(name="settag", short="G")
    def settag(self, value: list[str] | None = None) -> list[str]:
        """Sets given tag(s) to all executed tests."""
        return value or []

    @option(name="test", short="t")
    def test(self, value: list[str] | None = None) -> list[str]:
        """Select tests by name or by long name containing also parent suite
        name like `Parent.Test`. Name is case and space insensitive.
        """
        return value or []

    @option(name="suite", short="s")
    def suite(self, value: list[str] | None = None) -> list[str]:
        """Select suites by name."""
        return value or []

    @option(name="include", short="i")
    def include(self, value: list[str] | None = None) -> list[str]:
        """Select tests by tag."""
        return value or []

    @option(name="exclude", short="e")
    def exclude(self, value: list[str] | None = None) -> list[str]:
        """Select tests not matching by tag."""
        return value or []

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

    @option(name="variablefile", short="V")
    def variablefile(self, value: list[str] | None = None) -> list[str]:
        """Python or YAML file to read variables from."""
        return value or []

    # --- Output files -------------------------------------------------------
    outputdir = option(
        name="outputdir",
        short="d",
        default=".",
        help="Where to create output files. The default is the directory where "
        "tests are run from and the given path is considered relative to that.",
    )

    output = option(
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

    xunit = option(
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
    dryrun = option(
        name="dryrun",
        default=False,
        help="Verifies test data and runs tests so that library keywords are not executed.",
    )

    exitonfailure = option(
        name="exitonfailure",
        short="X",
        default=False,
        help="Stops test execution if any critical test fails.",
    )

    @option(name="skiponfailure")
    def skiponfailure(self, value: list[str] | None = None) -> list[str]:
        """Tests having given tag will be skipped if they fail."""
        return value or []

    rpa = option(
        name="rpa",
        default=False,
        help="Turn on the generic automation mode. Negate with --no-rpa.",
    )

    statusrc = option(
        name="statusrc",
        default=True,
        help="Set the return code to zero regardless of failures with "
        "--no-statusrc. Error codes are returned normally.",
    )

    @option(name="console")
    def console(self, value: str = "verbose") -> str:
        """How to report execution on the console. Valid values are `verbose`,
        `dotted`, `quiet` and `none`.
        """
        if value not in CONSOLE_CHOICES:
            raise OptionValueError(f"invalid --console value {value!r}; choose from {', '.join(CONSOLE_CHOICES)}")
        return value

    dotted = option(
        name="dotted",
        short=".",
        default=False,
        help="Shortcut for `--console dotted`.",
    )

    quiet = option(
        name="quiet",
        default=False,
        help="Shortcut for `--console quiet`.",
    )

    @option(name="pythonpath", short="P")
    def pythonpath(self, value: list[str] | None = None) -> list[str]:
        """Additional locations (directories, ZIPs) where to search libraries
        and other extensions when they are imported.
        """
        return value or []

    # --- Re-running and ordering -------------------------------------------
    rerunfailed = option(
        name="rerunfailed",
        short="R",
        default=None,
        help="Select failed tests from an earlier output file to re-execute.",
    )

    rerunfailedsuites = option(
        name="rerunfailedsuites",
        short="S",
        default=None,
        help="Select failed suites from an earlier output file to re-execute.",
    )

    @option(name="randomize")
    def randomize(self, value: str = "none") -> str:
        """Randomize the test execution order. Valid values are `all`,
        `suites`, `tests` and `none` (default).
        """
        normalized = value.split(":", 1)[0].lower()
        if normalized not in RANDOMIZE_CHOICES:
            raise OptionValueError(f"invalid --randomize {value!r}; choose from {', '.join(RANDOMIZE_CHOICES)}")
        return value

    # --- Output tuning ------------------------------------------------------
    logtitle = option(name="logtitle", default=None, help="Title for the generated log file.")

    reporttitle = option(name="reporttitle", default=None, help="Title for the generated report.")

    debugfile = option(
        name="debugfile",
        short="b",
        default=None,
        help="Debug file written during execution. Not created unless given.",
    )

    timestampoutputs = option(
        name="timestampoutputs",
        short="T",
        default=False,
        help="Add a timestamp to all generated output files.",
    )

    splitlog = option(
        name="splitlog",
        default=False,
        help="Split the log file into smaller pieces that open in browsers transparently.",
    )

    @option(name="removekeywords")
    def removekeywords(self, value: list[str] | None = None) -> list[str]:
        """Remove keyword data from the generated log file. Data can be removed
        e.g. based on keyword status, name or type.
        """
        return value or []

    @option(name="flattenkeywords")
    def flattenkeywords(self, value: list[str] | None = None) -> list[str]:
        """Flatten matching keywords in the generated log file."""
        return value or []

    @option(name="expandkeywords")
    def expandkeywords(self, value: list[str] | None = None) -> list[str]:
        """Matching keywords are automatically expanded in the log file."""
        return value or []

    maxerrorlines = option(
        name="maxerrorlines",
        default=40,
        help="Maximum number of error message lines to show in the report and log.",
    )

    maxassignlength = option(
        name="maxassignlength",
        default=200,
        help="Maximum number of characters to show in log for assigned variables.",
    )

    # --- Tag statistics -----------------------------------------------------
    @option(name="tagstatinclude")
    def tagstatinclude(self, value: list[str] | None = None) -> list[str]:
        """Include only matching tags in the generated statistics."""
        return value or []

    @option(name="tagstatexclude")
    def tagstatexclude(self, value: list[str] | None = None) -> list[str]:
        """Exclude matching tags from the generated statistics."""
        return value or []

    @option(name="tagstatcombine")
    def tagstatcombine(self, value: list[str] | None = None) -> list[str]:
        """Create combined statistics based on tags."""
        return value or []

    suitestatlevel = option(
        name="suitestatlevel",
        default=0,
        help="How many levels to show in the `Statistics by Suite` table. 0 shows all.",
    )

    # --- Extensions ---------------------------------------------------------
    @option(name="listener")
    def listener(self, value: list[str] | None = None) -> list[str]:
        """A listener interface to monitor test execution."""
        return value or []

    @option(name="prerunmodifier")
    def prerunmodifier(self, value: list[str] | None = None) -> list[str]:
        """Programmatic modifier for the test data before execution."""
        return value or []

    @option(name="prerebotmodifier")
    def prerebotmodifier(self, value: list[str] | None = None) -> list[str]:
        """Programmatic modifier for the results before report/log creation."""
        return value or []

    @option(name="parser")
    def parser(self, value: list[str] | None = None) -> list[str]:
        """Custom parser for parsing data in non-default formats."""
        return value or []

    @option(name="language")
    def language(self, value: list[str] | None = None) -> list[str]:
        """Activate localization by giving one or more language codes or names."""
        return value or []

    # --- Skipping and empty suites -----------------------------------------
    @option(name="skip")
    def skip(self, value: list[str] | None = None) -> list[str]:
        """Tests having the given tag will be skipped unconditionally."""
        return value or []

    runemptysuite = option(
        name="runemptysuite",
        default=False,
        help="Execute test suite even if it contains no tests.",
    )

    exitonerror = option(
        name="exitonerror",
        default=False,
        help="Stop execution if any error occurs when parsing test data or importing libraries.",
    )

    # --- Console output -----------------------------------------------------
    @option(name="consolecolors", short="C")
    def consolecolors(self, value: str = "auto") -> str:
        """Use colors on console output. Valid values are `auto`, `on`, `ansi`
        and `off`.
        """
        if value.lower() not in CONSOLE_COLOR_CHOICES:
            raise OptionValueError(f"invalid --consolecolors {value!r}; choose from {', '.join(CONSOLE_COLOR_CHOICES)}")
        return value.lower()

    @option(name="consolemarkers", short="K")
    def consolemarkers(self, value: str = "auto") -> str:
        """Show markers on the console when top-level keywords in a test end.
        Valid values are `auto`, `on` and `off`.
        """
        if value.lower() not in CONSOLE_MARKER_CHOICES:
            raise OptionValueError(
                f"invalid --consolemarkers {value!r}; choose from {', '.join(CONSOLE_MARKER_CHOICES)}"
            )
        return value.lower()

    consolewidth = option(
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
