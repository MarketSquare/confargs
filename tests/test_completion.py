"""Tests for shell completion (script generation and dynamic completion)."""

from __future__ import annotations

from typing import Literal

import pytest

from confargs import ArgConfig, ConfigurationProcessor, option
from confargs.completion import (
    SUPPORTED_SHELLS,
    Completion,
    complete_var,
    compute_completions,
    format_completion,
    install_completion,
    prog_name,
    render_source,
    split_arg_string,
)
from confargs.exceptions import CliUsageError, Exit
from confargs.options import collect_options, resolve_names


class CompletionConfig(ArgConfig):
    tool_name = "mytool"

    name: str = option(name="name", default="anon", help="The name to greet.")

    @option(name="console", short="c")
    def console(self, value: Literal["verbose", "quiet", "dotted"] = "verbose") -> str:
        """Console output mode."""
        return value

    @option
    def verbose(self, value: bool = False) -> bool:
        """Enable verbose output."""
        return value

    @option
    def retries(self, value: int = 3) -> int:
        """Retry count."""
        return value


def _table_and_meta(cls: type[ArgConfig]):
    options = collect_options(cls)
    table = resolve_names(options)
    from confargs.coercion import resolve_value_type

    value_types = {attr: resolve_value_type(opt) for attr, opt in options.items()}
    flags = {attr for attr, vt in value_types.items() if vt.is_flag}
    return options, table, value_types, flags


def _complete(cls: type[ArgConfig], args: list[str], incomplete: str) -> list[Completion]:
    options, table, value_types, flags = _table_and_meta(cls)
    return compute_completions(
        args,
        incomplete,
        table=table,
        options=options,
        value_types=value_types,
        flags=flags,
    )


# --------------------------------------------------------------------------- #
# Naming helpers
# --------------------------------------------------------------------------- #


def test_complete_var_normalises_program_name() -> None:
    assert complete_var("my-tool") == "_MY_TOOL_COMPLETE"
    assert complete_var("robot.py") == "_ROBOT_PY_COMPLETE"


def test_prog_name_strips_suffix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["/usr/bin/mytool.exe", "--flag"])
    assert prog_name() == "mytool"


def test_split_arg_string_tolerates_open_quote() -> None:
    assert split_arg_string("mytool --name 'value") == ["mytool", "--name", "value"]
    assert split_arg_string("mytool --name val") == ["mytool", "--name", "val"]


# --------------------------------------------------------------------------- #
# Source-script rendering
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("shell", SUPPORTED_SHELLS)
def test_render_source_contains_prog_and_var(shell: str) -> None:
    script = render_source(shell, "mytool")
    assert "mytool" in script
    assert "_MYTOOL_COMPLETE" in script
    assert f"{shell}_complete" in script


def test_render_source_rejects_unknown_shell() -> None:
    with pytest.raises(CliUsageError):
        render_source("tcsh", "mytool")


# --------------------------------------------------------------------------- #
# Dynamic completion
# --------------------------------------------------------------------------- #


def test_completes_long_option_names() -> None:
    values = {c.value for c in _complete(CompletionConfig, [], "--con")}
    assert values == {"--console", "--config"}  # --config is a builtin option


def test_completes_all_option_names_on_dash() -> None:
    values = {c.value for c in _complete(CompletionConfig, [], "--")}
    assert "--console" in values
    assert "--name" in values
    assert "--verbose" in values


def test_flag_offers_negation() -> None:
    values = {c.value for c in _complete(CompletionConfig, [], "--no-verb")}
    assert values == {"--no-verbose"}


def test_completes_literal_choices_as_option_value() -> None:
    values = {c.value for c in _complete(CompletionConfig, ["--console"], "")}
    assert values == {"verbose", "quiet", "dotted"}


def test_completes_literal_choices_partial() -> None:
    values = {c.value for c in _complete(CompletionConfig, ["--console"], "q")}
    assert values == {"quiet"}


def test_short_option_value_uses_choices() -> None:
    values = {c.value for c in _complete(CompletionConfig, ["-c"], "")}
    assert values == {"verbose", "quiet", "dotted"}


def test_value_without_choices_falls_back_to_file() -> None:
    completions = _complete(CompletionConfig, ["--name"], "")
    assert [c.type for c in completions] == ["file"]


def test_inline_equals_completes_choices() -> None:
    values = {c.value for c in _complete(CompletionConfig, [], "--console=q")}
    assert values == {"--console=quiet"}


def test_flag_is_not_treated_as_pending_value() -> None:
    # After a boolean flag, the next word completes fresh option names.
    values = {c.value for c in _complete(CompletionConfig, ["--verbose"], "--na")}
    assert values == {"--name"}


def test_empty_word_offers_options_and_file() -> None:
    completions = _complete(CompletionConfig, [], "")
    assert any(c.value == "--console" for c in completions)
    assert any(c.type == "file" for c in completions)


# --------------------------------------------------------------------------- #
# Record formatting
# --------------------------------------------------------------------------- #


def test_format_bash() -> None:
    assert format_completion("bash", Completion("--console", help="mode")) == "plain,--console"


def test_format_zsh_includes_help_and_escapes_colon() -> None:
    formatted = format_completion("zsh", Completion("a:b", help="desc"))
    assert formatted == "plain\na\\:b\ndesc"


def test_format_zsh_without_help_uses_sentinel() -> None:
    assert format_completion("zsh", Completion("verbose")) == "plain\nverbose\n_"


def test_format_fish_with_help_uses_tab() -> None:
    assert format_completion("fish", Completion("--x", help="h")) == "plain,--x\th"


def test_format_pwsh_matches_powershell_triple() -> None:
    item = Completion("verbose", help="mode")
    assert format_completion("pwsh", item) == format_completion("powershell", item)
    assert format_completion("pwsh", item) == "plain\nverbose\nmode"


def test_render_pwsh_advertises_pwsh_instruction() -> None:
    ps = render_source("powershell", "mytool")
    pwsh = render_source("pwsh", "mytool")
    assert "pwsh_complete" in pwsh
    assert "powershell_complete" not in pwsh
    # The only difference between the two scripts is the advertised instruction.
    assert pwsh.replace("pwsh_complete", "powershell_complete") == ps


# --------------------------------------------------------------------------- #
# End-to-end request handling through the processor
# --------------------------------------------------------------------------- #


def test_processor_answers_completion_request(capsys: pytest.CaptureFixture[str]) -> None:
    environ = {
        "_MYTOOL_COMPLETE": "bash_complete",
        "COMP_WORDS": "mytool --con",
        "COMP_CWORD": "1",
    }
    monkey_argv = ["mytool"]
    import sys

    original = sys.argv
    sys.argv = monkey_argv
    try:
        with pytest.raises(Exit) as excinfo:
            ConfigurationProcessor(CompletionConfig, environ=environ).process()
    finally:
        sys.argv = original
    assert excinfo.value.code == 0
    out = capsys.readouterr().out
    assert "plain,--console" in out


def test_no_completion_request_runs_normally() -> None:
    config = ConfigurationProcessor(CompletionConfig, argv=["--console", "quiet"], environ={}).process()
    assert config.console == "quiet"


# --------------------------------------------------------------------------- #
# Installation
# --------------------------------------------------------------------------- #


def test_install_bash_writes_script_and_wires_rc(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    message = install_completion("bash", "mytool")
    script = tmp_path / ".bash_completions" / "mytool.sh"
    assert script.exists()
    assert "complete -o nosort" in script.read_text()
    assert f"source {script}" in (tmp_path / ".bashrc").read_text()
    assert str(script) in message


def test_install_is_idempotent(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    install_completion("fish", "mytool")
    install_completion("fish", "mytool")
    rc = tmp_path / ".config" / "fish" / "completions" / "mytool.fish"
    assert rc.exists()


def test_install_rejects_unknown_shell() -> None:
    with pytest.raises(CliUsageError):
        install_completion("tcsh", "mytool")


def test_install_pwsh_and_powershell_use_distinct_profiles(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    # Force the conventional-location fallback (don't query a real interpreter).
    import subprocess

    def _boom(*args: object, **kwargs: object) -> None:
        raise OSError("no shell")

    monkeypatch.setattr(subprocess, "run", _boom)

    install_completion("pwsh", "mytool")
    install_completion("powershell", "mytool")

    pwsh_profile = tmp_path / "Documents" / "PowerShell" / "Microsoft.PowerShell_profile.ps1"
    ps_profile = tmp_path / "Documents" / "WindowsPowerShell" / "Microsoft.PowerShell_profile.ps1"
    assert "pwsh_complete" in pwsh_profile.read_text()
    assert "powershell_complete" in ps_profile.read_text()
    assert "pwsh_complete" not in ps_profile.read_text()
