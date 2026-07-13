#!/usr/bin/env python3
"""PreToolUse gate for the spec-implement skill.

While the completion loop is armed (`.claude/.spec-loop/active` exists), this
auto-approves ONLY the workflow's known-safe operations so Phases 2-3 run
without permission prompts. When the loop is not armed it stays silent and
normal permission handling applies.

The set of auto-approved bash prefixes and the protected-path list come from the
resolved per-project config (`hooks/_config.py`): they default to git + the
detected stack's test/lint commands, and can be overridden in
`.claude/spec-workflow.json`.

Safety boundaries:
  * Bash is allow-listed by command prefix and rejected if it contains shell
    chaining/redirection (so an allowed prefix can't smuggle a second command).
  * Writes to protected paths are never auto-approved here.
  * A hook `allow` cannot override settings `deny`/`ask` rules, so any project
    deny list still applies on top of everything below.
"""
import json
import os
import pathlib
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _config  # noqa: E402

# shell features that could chain a second command past an allowed prefix
UNSAFE_SHELL = ("&&", "||", ";", "|", "`", "$(", ">", "<", "\n")


def allow(reason: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                    "permissionDecisionReason": reason,
                }
            }
        )
    )
    sys.exit(0)


def passthrough() -> None:
    """No opinion — let normal permission handling decide."""
    sys.exit(0)


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        passthrough()

    proj = os.environ.get("CLAUDE_PROJECT_DIR", ".")
    active = pathlib.Path(proj) / ".claude" / ".spec-loop" / "active"
    if not active.exists():
        passthrough()  # loop not armed — do not touch normal sessions

    # Only the session that armed the loop may be auto-approved. Other
    # concurrent sessions in this project get normal permission handling.
    armed_sid = active.read_text().strip()
    if armed_sid not in ("", "1") and data.get("session_id") != armed_sid:
        passthrough()

    cfg = _config.resolve(proj)
    if cfg is None:
        passthrough()  # unconfigured project — never auto-approve blindly

    safe_prefixes = tuple(cfg.get("safe_bash_prefixes", ()))
    protected = tuple(cfg.get("protected_paths", ()))

    tool = data.get("tool_name", "")
    ti = data.get("tool_input") or {}

    if tool == "Bash":
        cmd = (ti.get("command") or "").strip()
        if any(s in cmd for s in UNSAFE_SHELL):
            passthrough()  # compound/redirected — require manual approval
        if any(cmd.startswith(p) for p in safe_prefixes):
            allow("spec-implement loop: safe workflow command")
        passthrough()

    if tool in ("Write", "Edit", "MultiEdit"):
        rel = (ti.get("file_path") or "").replace(proj + "/", "")
        if any(seg in rel for seg in protected):
            passthrough()  # protected path — defer to deny/ask rules
        allow("spec-implement loop: implementation edit")

    if tool in ("Task", "Agent"):
        allow("spec-implement loop: reviewer subagent")

    passthrough()


main()
