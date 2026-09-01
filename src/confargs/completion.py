"""Shell completion support (bash, zsh, fish, PowerShell).

confargs implements completion with its own code — it does not depend on Click,
argparse or a third-party completer. The mechanism mirrors the well-known
protocol Click/Typer use, which every major shell already knows how to drive:

* A small **source script** (printed by ``--show-completion <shell>`` and
  installed by ``--install-completion <shell>``) is registered with the shell.
  The script is generic: it only re-invokes the program.
* At completion time the shell re-runs the program with a special environment
  variable set (``_<PROG>_COMPLETE=<shell>_complete``) plus ``COMP_WORDS`` /
  ``COMP_CWORD`` describing the current command line. The program answers with
  one ``type,value`` record per candidate, which the source script feeds back
  to the shell.

Because confargs already knows every option name, short name and
``Literal[...]`` choice set, the dynamic side can be answered directly from a
resolved :class:`~confargs.options.NameTable` and the option value types — no
parser introspection shim is needed.
"""

from __future__ import annotations

import os
import re
import shlex
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from confargs.cli import negation_name
from confargs.exceptions import CliUsageError

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from confargs.coercion import ValueType
    from confargs.options import NameTable, Option

SUPPORTED_SHELLS: tuple[str, ...] = ("bash", "zsh", "fish", "powershell")
"""Shells confargs can generate completion scripts for."""


@dataclass(frozen=True)
class Completion:
    """A single completion candidate returned to the shell.

    ``type`` is ``"plain"`` for a literal value, or ``"file"`` / ``"dir"`` to
    ask the shell to perform its own path completion.
    """

    value: str
    type: str = "plain"
    help: str | None = None


# --------------------------------------------------------------------------- #
# Program name / environment variable naming
# --------------------------------------------------------------------------- #


def prog_name() -> str:
    """Return the command name the program is invoked as.

    Derived from ``sys.argv[0]`` (its base name, with a trailing ``.exe`` or
    ``.py`` stripped) so the name matches what the user types in the shell.
    """
    name = Path(sys.argv[0]).name if sys.argv and sys.argv[0] else ""
    for suffix in (".exe", ".py"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
    return name or "confargs"


def complete_var(program: str) -> str:
    """Return the environment variable that carries a completion instruction.

    ``my-tool`` maps to ``_MY_TOOL_COMPLETE``; the same transformation is used
    when generating the source script and when reading the request, so both
    ends always agree.
    """
    safe = re.sub(r"\W", "_", program).upper()
    return f"_{safe}_COMPLETE"


def _func_name(program: str) -> str:
    """Return the shell function name defined by the source script."""
    safe = re.sub(r"\W", "_", program)
    return f"_{safe}_completion"


# --------------------------------------------------------------------------- #
# Source-script templates
# --------------------------------------------------------------------------- #
# ``str.replace`` is used instead of ``%``/``str.format`` because the scripts
# are full of ``$``, ``%``, ``{`` and ``}`` that those would misinterpret.

_BASH_TEMPLATE = """\
@@FUNC@@() {
    local IFS=$'\\n'
    local response
    response=$(env COMP_WORDS="${COMP_WORDS[*]}" COMP_CWORD="$COMP_CWORD" @@VAR@@=bash_complete "$1")

    COMPREPLY=()
    for line in $response; do
        local kind="${line%%,*}"
        local value="${line#*,}"
        case "$kind" in
            dir) compopt -o dirnames 2>/dev/null ;;
            file) compopt -o default 2>/dev/null ;;
            plain) COMPREPLY+=("$value") ;;
        esac
    done
    return 0
}

complete -o nosort -F @@FUNC@@ @@PROG@@
"""

_ZSH_TEMPLATE = """\
#compdef @@PROG@@

@@FUNC@@() {
    local -a completions
    local -a completions_with_help
    local -a response
    response=("${(@f)$(env COMP_WORDS="${words[*]}" COMP_CWORD=$((CURRENT-1)) @@VAR@@=zsh_complete @@PROG@@)}")

    local kind value descr
    for kind value descr in ${response}; do
        case "$kind" in
            plain)
                if [[ "$descr" == "_" ]]; then
                    completions+=("$value")
                else
                    completions_with_help+=("$value":"$descr")
                fi
                ;;
            dir) _path_files -/ ;;
            file) _path_files -f ;;
        esac
    done

    (( $#completions_with_help )) && _describe -V unsorted completions_with_help -U
    (( $#completions )) && compadd -U -V unsorted -a completions
}

compdef @@FUNC@@ @@PROG@@
"""

_FISH_TEMPLATE = """\
function @@FUNC@@
    set -l response (env @@VAR@@=fish_complete COMP_WORDS=(commandline -cp) COMP_CWORD=(commandline -t) @@PROG@@)

    for completion in $response
        set -l parts (string split -m 1 "," -- $completion)
        switch $parts[1]
            case dir
                __fish_complete_directories $parts[2]
            case file
                __fish_complete_path $parts[2]
            case plain
                echo $parts[2]
        end
    end
end

complete --command @@PROG@@ --no-files --arguments "(@@FUNC@@)"
"""

# Compatible with Windows PowerShell 5.1+ and PowerShell (pwsh) 7+. The command
# text is forwarded verbatim through COMP_WORDS so the Python side can reuse the
# same shlex-based splitting as the POSIX shells.
_POWERSHELL_TEMPLATE = """\
Register-ArgumentCompleter -Native -CommandName @@PROG@@ -ScriptBlock {
    param($wordToComplete, $commandAst, $cursorPosition)

    $env:@@VAR@@ = 'powershell_complete'
    $env:COMP_WORDS = $commandAst.ToString()
    if ($wordToComplete) {
        $env:COMP_CWORD = $commandAst.CommandElements.Count - 1
    } else {
        $env:COMP_CWORD = $commandAst.CommandElements.Count
    }

    try {
        $response = & @@PROG@@ 2>$null
    } finally {
        Remove-Item Env:\\@@VAR@@ -ErrorAction SilentlyContinue
        Remove-Item Env:\\COMP_WORDS -ErrorAction SilentlyContinue
        Remove-Item Env:\\COMP_CWORD -ErrorAction SilentlyContinue
    }

    if (-not $response) { return }

    $prefix = "$wordToComplete*"
    $lines = $response -split "`n"
    for ($i = 0; $i + 2 -lt $lines.Count; $i += 3) {
        $kind = $lines[$i]
        $value = $lines[$i + 1]
        $descr = $lines[$i + 2]
        if (-not $kind) { continue }

        if ($kind -eq 'plain') {
            $tip = if ($descr -and $descr -ne '_') { $descr } else { $value }
            [System.Management.Automation.CompletionResult]::new($value, $value, 'ParameterValue', $tip)
        } elseif ($kind -eq 'dir') {
            Get-ChildItem -Directory -Path $prefix -ErrorAction SilentlyContinue | ForEach-Object {
                $r = [System.Management.Automation.CompletionResult]
                $r::new($_.FullName, $_.Name, 'ProviderContainer', $_.FullName)
            }
        } elseif ($kind -eq 'file') {
            Get-ChildItem -Path $prefix -ErrorAction SilentlyContinue | ForEach-Object {
                $kindResult = if ($_.PSIsContainer) { 'ProviderContainer' } else { 'ProviderItem' }
                $r = [System.Management.Automation.CompletionResult]
                $r::new($_.FullName, $_.Name, $kindResult, $_.FullName)
            }
        }
    }
}
"""

_TEMPLATES: dict[str, str] = {
    "bash": _BASH_TEMPLATE,
    "zsh": _ZSH_TEMPLATE,
    "fish": _FISH_TEMPLATE,
    "powershell": _POWERSHELL_TEMPLATE,
}


def render_source(shell: str, program: str | None = None) -> str:
    """Return the completion source script for ``shell``.

    Args:
        shell: One of :data:`SUPPORTED_SHELLS`.
        program: The command name to register. Defaults to :func:`prog_name`.
    """
    template = _TEMPLATES.get(shell)
    if template is None:
        raise CliUsageError(f"unsupported shell {shell!r}; choose from {', '.join(SUPPORTED_SHELLS)}")
    program = program or prog_name()
    return (
        template.replace("@@FUNC@@", _func_name(program))
        .replace("@@VAR@@", complete_var(program))
        .replace("@@PROG@@", program)
    )


# --------------------------------------------------------------------------- #
# Installation
# --------------------------------------------------------------------------- #


def install_completion(shell: str, program: str | None = None) -> str:
    """Install the completion script for ``shell`` and return a status message.

    The script is written to the shell's conventional location and, where
    needed, the shell's startup file is wired up to load it.
    """
    if shell not in _TEMPLATES:
        raise CliUsageError(f"unsupported shell {shell!r}; choose from {', '.join(SUPPORTED_SHELLS)}")
    program = program or prog_name()
    script = render_source(shell, program)
    home = Path.home()

    if shell == "bash":
        path = home / ".bash_completions" / f"{program}.sh"
        _write_script(path, script)
        _ensure_line(home / ".bashrc", f"source {path}")
        return f"bash completion installed to {path} (restart your shell to activate)"

    if shell == "zsh":
        path = home / ".zfunc" / f"_{program}"
        _write_script(path, script)
        rc = home / ".zshrc"
        _ensure_line(rc, f"fpath+={path.parent}")
        _ensure_line(rc, "autoload -Uz compinit && compinit")
        return f"zsh completion installed to {path} (restart your shell to activate)"

    if shell == "fish":
        path = home / ".config" / "fish" / "completions" / f"{program}.fish"
        _write_script(path, script)
        return f"fish completion installed to {path} (restart your shell to activate)"

    # powershell
    profile = _powershell_profile()
    _append_block(profile, script)
    return f"powershell completion appended to {profile} (restart your shell to activate)"


def _write_script(path: Path, script: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(script, encoding="utf-8")


def _ensure_line(path: Path, line: str) -> None:
    """Append ``line`` to ``path`` unless it is already present."""
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if line in existing.splitlines():
        return
    prefix = "" if not existing or existing.endswith("\n") else "\n"
    path.write_text(f"{existing}{prefix}{line}\n", encoding="utf-8")


def _append_block(path: Path, block: str) -> None:
    """Append a script ``block`` to ``path`` if not already present."""
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if block.strip() and block.strip() in existing:
        return
    prefix = "" if not existing or existing.endswith("\n") else "\n"
    path.write_text(f"{existing}{prefix}{block}\n", encoding="utf-8")


def _powershell_profile() -> Path:
    """Locate the PowerShell profile path, best-effort."""
    for exe in ("pwsh", "powershell"):
        try:
            import subprocess

            result = subprocess.run(
                [exe, "-NoProfile", "-Command", "$PROFILE"],
                capture_output=True,
                text=True,
                timeout=15,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        candidate = result.stdout.strip()
        if candidate:
            return Path(candidate)
    # Fallback to the conventional pwsh profile location.
    return Path.home() / "Documents" / "PowerShell" / "Microsoft.PowerShell_profile.ps1"


# --------------------------------------------------------------------------- #
# Dynamic completion (answering a request from the shell)
# --------------------------------------------------------------------------- #


def split_arg_string(string: str) -> list[str]:
    """Split a command line like :func:`shlex.split`, tolerating an open quote.

    A trailing unterminated quote or escape (which is common while the user is
    still typing) yields the partial token rather than raising.
    """
    lexer = shlex.shlex(string, posix=True)
    lexer.whitespace_split = True
    lexer.commenters = ""
    out: list[str] = []
    try:
        out.extend(lexer)
    except ValueError:
        if lexer.token:
            out.append(lexer.token)
    return out


def _read_comp_env(shell: str, environ: Mapping[str, str]) -> tuple[list[str], str]:
    """Extract ``(args, incomplete)`` from the completion environment.

    ``args`` are the tokens before the word being completed (program name
    dropped); ``incomplete`` is the partial word under the cursor.
    """
    if shell == "fish":
        words = split_arg_string(environ.get("COMP_WORDS", ""))
        raw_incomplete = environ.get("COMP_CWORD", "")
        incomplete = split_arg_string(raw_incomplete)[0] if raw_incomplete else ""
        args = words[1:]
        if incomplete and args and args[-1] == incomplete:
            args.pop()
        return args, incomplete

    words = split_arg_string(environ.get("COMP_WORDS", ""))
    try:
        cword = int(environ.get("COMP_CWORD", "") or 0)
    except ValueError:
        cword = 0
    args = words[1:cword]
    incomplete = words[cword] if 0 <= cword < len(words) else ""
    return args, incomplete


def _summary(opt: Option) -> str:
    """Return a one-line help summary for an option, if any."""
    doc = opt.doc.strip()
    if not doc:
        return ""
    first = doc.split("\n\n", 1)[0].replace("\n", " ")
    return textwrap.shorten(first, width=80, placeholder="...")


def _choice_completions(choices: Sequence[Any], incomplete: str) -> list[Completion]:
    return [Completion(str(choice)) for choice in choices if str(choice).startswith(incomplete)]


def _value_completions(value_type: ValueType, incomplete: str) -> list[Completion]:
    """Complete the value of an option: its choices, else fall back to files."""
    if value_type.choices is not None:
        return _choice_completions(value_type.choices, incomplete)
    return [Completion(incomplete, type="file")]


def _pending_value_attr(args: Sequence[str], table: NameTable, flags: set[str]) -> str | None:
    """Return the attr whose value is being completed, if the last token wants one."""
    if not args:
        return None
    attr = table.attr_for(args[-1])
    if attr is None or attr in flags:
        return None
    return attr


def _option_name_completions(
    incomplete: str,
    options: Mapping[str, Option],
    table: NameTable,
    flags: set[str],
) -> list[Completion]:
    """Complete option names (and ``--no-`` negations for flags)."""
    result: list[Completion] = []
    seen: set[str] = set()

    def add(name: str, summary: str) -> None:
        if name.startswith(incomplete) and name not in seen:
            seen.add(name)
            result.append(Completion(name, help=summary or None))

    for attr, opt in options.items():
        if not opt.cli:
            continue
        summary = _summary(opt)
        names = table.attr_to_names.get(attr, [])
        for name in names:
            add(name, summary)
        if attr in flags:
            for name in names:
                if name.startswith("--") and not name.startswith("--no-"):
                    add(negation_name(name), summary)
    return result


def compute_completions(
    args: Sequence[str],
    incomplete: str,
    *,
    table: NameTable,
    options: Mapping[str, Option],
    value_types: Mapping[str, ValueType],
    flags: set[str],
) -> list[Completion]:
    """Compute completion candidates for a partially typed command line."""
    # Completing the value of the preceding option.
    pending = _pending_value_attr(args, table, flags)
    if pending is not None:
        return _value_completions(value_types[pending], incomplete)

    # Inline ``--name=partial`` form: offer choice values joined to the name.
    if incomplete.startswith("--") and "=" in incomplete:
        name, _sep, partial = incomplete.partition("=")
        attr = table.long_attr(name)
        if attr is not None and attr not in flags:
            value_type = value_types.get(attr)
            if value_type is not None and value_type.choices is not None:
                return [
                    Completion(f"{name}={choice}") for choice in value_type.choices if str(choice).startswith(partial)
                ]
        return []

    # An option name, or the empty word (offer options plus file fallback).
    if incomplete.startswith("-"):
        return _option_name_completions(incomplete, options, table, flags)
    if incomplete == "":
        return [*_option_name_completions(incomplete, options, table, flags), Completion("", type="file")]

    # A positional value.
    return [Completion(incomplete, type="file")]


def format_completion(shell: str, item: Completion) -> str:
    """Format one candidate into the record format the source script expects."""
    if shell in ("zsh", "powershell"):
        help_ = item.help or "_"
        value = item.value.replace(":", r"\:") if shell == "zsh" and item.help else item.value
        return f"{item.type}\n{value}\n{help_}"
    if shell == "fish" and item.help:
        help_ = item.help.replace("\n", " ").replace("\t", " ")
        return f"{item.type},{item.value}\t{help_}"
    return f"{item.type},{item.value}"


def handle_request(
    instruction: str,
    *,
    table: NameTable,
    options: Mapping[str, Option],
    value_types: Mapping[str, ValueType],
    flags: set[str],
    environ: Mapping[str, str] | None = None,
) -> str:
    """Answer a completion request described by ``instruction`` (``<shell>_complete``).

    Returns the newline-joined records for the shell, or an empty string when
    the instruction is not a recognised completion request.
    """
    shell, _sep, action = instruction.partition("_")
    if action != "complete" or shell not in _TEMPLATES:
        return ""
    env = os.environ if environ is None else environ
    args, incomplete = _read_comp_env(shell, env)
    completions = compute_completions(
        args,
        incomplete,
        table=table,
        options=options,
        value_types=value_types,
        flags=flags,
    )
    return "\n".join(format_completion(shell, item) for item in completions)
