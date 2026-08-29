"""Tests for loading extra CLI arguments from an environment variable."""

from __future__ import annotations

import shlex

import confargs
from confargs import ArgConfig, option, split_env_args


class Tool(ArgConfig):
    """A tool that reads extra options from TOOL_OPTIONS."""

    name = "tool"
    options_env_var = "TOOL_OPTIONS"

    log = option(name="log", default="log.html", help="Log file.")

    @option(name="tag")
    def tag(self, value: list[str] | None = None) -> list[str]:
        """Repeatable tag."""
        return value or []

    dryrun = option(name="dryrun", default=False, help="Dry run.")


def _run(argv: list[str], environ: dict[str, str]) -> confargs.Namespace:
    return confargs.ConfigurationProcessor(Tool, argv=argv, environ=environ).process()


def test_split_env_args_respects_quoting() -> None:
    assert split_env_args("--log NONE --dryrun") == ["--log", "NONE", "--dryrun"]
    assert split_env_args("--log 'my log.html'") == ["--log", "my log.html"]
    assert split_env_args("") == []


def test_env_var_supplies_arguments() -> None:
    ns = _run([], {"TOOL_OPTIONS": "--log out.html --dryrun"})
    assert ns.log == "out.html"
    assert ns.dryrun is True


def test_cli_overrides_env_scalar() -> None:
    ns = _run(["--log", "cli.html"], {"TOOL_OPTIONS": "--log env.html"})
    assert ns.log == "cli.html"


def test_env_and_cli_lists_accumulate_in_order() -> None:
    ns = _run(["--tag", "cli"], {"TOOL_OPTIONS": "--tag env1 --tag env2"})
    assert ns.tag == ["env1", "env2", "cli"]


def test_env_var_absent_is_ignored() -> None:
    ns = _run([], {})
    assert ns.log == "log.html"
    assert ns.dryrun is False


def test_feature_disabled_by_default() -> None:
    class Plain(ArgConfig):
        name = "plain"
        log = option(name="log", default="log.html")

    ns = confargs.ConfigurationProcessor(Plain, argv=[], environ={"PLAIN_OPTIONS": "--log hacked.html"}).process()
    assert ns.log == "log.html"


def test_env_args_participate_in_eager_expansion(tmp_path) -> None:
    argfile = tmp_path / "extra.args"
    argfile.write_text("--log from_file.html\n", encoding="utf-8")

    class Eager(ArgConfig):
        name = "eager"
        options_env_var = "EAGER_OPTIONS"
        log = option(name="log", default="log.html")

        @option(name="argumentfile", short="A", config=False, is_eager=True)
        def argumentfile(self, value: str | None = None) -> list[str] | None:
            return confargs.read_argument_file(value) if value else None

    ns = confargs.ConfigurationProcessor(
        Eager, argv=[], environ={"EAGER_OPTIONS": f"--argumentfile {shlex.quote(str(argfile))}"}
    ).process()
    assert ns.log == "from_file.html"
