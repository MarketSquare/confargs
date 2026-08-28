"""A Robot Framework-style CLI parser modelled with :mod:`argconfig`.

This mirrors a representative subset of the real ``robot`` command-line
interface — the option names, short flags, repeatable ("``*``") options, boolean
switches, help text and the eager ``--argumentfile`` handling — so that the
behaviour of argconfig can be exercised against realistic Robot Framework
command lines.

Option help strings are lifted from Robot Framework's own usage text so the
generated ``--help`` output reads like the tool it emulates. Only the light
parsing/validation Robot Framework performs up front is reproduced here; the
heavy lifting is intentionally left to argconfig's shared coercion path.
"""

from __future__ import annotations

import sys

from argconfig import ArgConfig, Exit, OptionValueError, option, read_argument_file, split_argument_file

CONSOLE_CHOICES = ("verbose", "dotted", "quiet", "none")
LOG_LEVELS = ("TRACE", "DEBUG", "INFO", "WARN", "ERROR", "NONE")


class RobotArgs(ArgConfig):
    """Robot Framework -- a generic automation framework.

    Usage: robot [options] data_sources

    Executes Robot Framework test/task data. This parser is a faithful subset
    of the real command-line interface, rebuilt with argconfig.
    """

    name = "robot"
    config_names = ["pyproject.toml", "robot.toml"]  # noqa: RUF012 - per-subclass override

    # --- Eager option: expands an argument file into more options -----------
    @option(names="--argumentfile/-A", cli_only=True, is_eager=True)
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
    @option(names="--name/-N")
    def name_(self, value: str | None = None) -> str | None:
        """Set the name of the top level suite. By default the name is created
        based on the executed file or directory.
        """
        return value

    @option(names="--doc/-D")
    def doc(self, value: str | None = None) -> str | None:
        """Set the documentation of the top level suite."""
        return value

    @option(names="--metadata/-M")
    def metadata(self, value: list[str] | None = None) -> list[str]:
        """Set metadata of the top level suite. Value can contain formatting."""
        return value or []

    @option(names="--settag/-G")
    def settag(self, value: list[str] | None = None) -> list[str]:
        """Sets given tag(s) to all executed tests."""
        return value or []

    @option(names="--test/-t")
    def test(self, value: list[str] | None = None) -> list[str]:
        """Select tests by name or by long name containing also parent suite
        name like `Parent.Test`. Name is case and space insensitive.
        """
        return value or []

    @option(names="--suite/-s")
    def suite(self, value: list[str] | None = None) -> list[str]:
        """Select suites by name."""
        return value or []

    @option(names="--include/-i")
    def include(self, value: list[str] | None = None) -> list[str]:
        """Select tests by tag."""
        return value or []

    @option(names="--exclude/-e")
    def exclude(self, value: list[str] | None = None) -> list[str]:
        """Select tests not matching by tag."""
        return value or []

    # --- Variables ----------------------------------------------------------
    @option(names="--variable/-v")
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

    @option(names="--variablefile/-V")
    def variablefile(self, value: list[str] | None = None) -> list[str]:
        """Python or YAML file to read variables from."""
        return value or []

    # --- Output files -------------------------------------------------------
    @option(names="--outputdir/-d")
    def outputdir(self, value: str = ".") -> str:
        """Where to create output files. The default is the directory where
        tests are run from and the given path is considered relative to that.
        """
        return value

    @option(names="--output/-o")
    def output(self, value: str = "output.xml") -> str:
        """XML output file."""
        return value

    @option(names="--log/-l")
    def log(self, value: str | None = "log.html") -> str | None:
        """HTML log file. Can be disabled by giving a special value `NONE`.
        Examples: `--log mylog.html`, `-l NONE`.
        """
        if value is None or value.upper() == "NONE":
            return None
        return value

    @option(names="--report/-r")
    def report(self, value: str | None = "report.html") -> str | None:
        """HTML report file. Can be disabled with `NONE` similarly as --log."""
        if value is None or value.upper() == "NONE":
            return None
        return value

    @option(names="--xunit/-x")
    def xunit(self, value: str | None = None) -> str | None:
        """xUnit compatible result file. Not created unless this option is
        specified.
        """
        return value

    @option(names="--loglevel/-L")
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
    @option(names="--dryrun")
    def dryrun(self, value: bool = False) -> bool:
        """Verifies test data and runs tests so that library keywords are not
        executed.
        """
        return value

    @option(names="--exitonfailure/-X")
    def exitonfailure(self, value: bool = False) -> bool:
        """Stops test execution if any critical test fails."""
        return value

    @option(names="--skiponfailure")
    def skiponfailure(self, value: list[str] | None = None) -> list[str]:
        """Tests having given tag will be skipped if they fail."""
        return value or []

    @option(names="--rpa")
    def rpa(self, value: bool = False) -> bool:
        """Turn on the generic automation mode. Negate with --no-rpa."""
        return value

    @option(names="--statusrc")
    def statusrc(self, value: bool = True) -> bool:
        """Set the return code to zero regardless of failures with --no-statusrc.
        Error codes are returned normally.
        """
        return value

    @option(names="--console")
    def console(self, value: str = "verbose") -> str:
        """How to report execution on the console. Valid values are `verbose`,
        `dotted`, `quiet` and `none`.
        """
        if value not in CONSOLE_CHOICES:
            raise OptionValueError(f"invalid --console value {value!r}; choose from {', '.join(CONSOLE_CHOICES)}")
        return value

    @option(names="--dotted/-.")
    def dotted(self, value: bool = False) -> bool:
        """Shortcut for `--console dotted`."""
        return value

    @option(names="--quiet")
    def quiet(self, value: bool = False) -> bool:
        """Shortcut for `--console quiet`."""
        return value

    @option(names="--pythonpath/-P")
    def pythonpath(self, value: list[str] | None = None) -> list[str]:
        """Additional locations (directories, ZIPs) where to search libraries
        and other extensions when they are imported.
        """
        return value or []

    @option(names="--version", cli_only=True)
    def version(self, value: bool = False) -> bool:
        """Print version information and exit."""
        if value:
            print("Robot Framework 7.0 (argconfig demo)")
            raise Exit(0)
        return value
