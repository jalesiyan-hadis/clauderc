#!/usr/bin/env python3
"""PostToolUse(ExitPlanMode) hook for the spec-implement skill.

Arms the completion-driven loop ONLY when an approved plan carries the
spec-implement sentinel. PostToolUse fires for ExitPlanMode only after the
user approves the plan, so arming here means "the gate was passed". The
sentinel check scopes arming to the spec-implement skill so ordinary
plan-mode usage never starts the loop.

Runtime state lives under the PROJECT's `.claude/.spec-loop/` (via
CLAUDE_PROJECT_DIR) — not the plugin dir — so per-project loops stay isolated.
"""
import json
import os
import pathlib
import sys

SENTINEL = "<!-- spec-implement-loop -->"


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    plan = (data.get("tool_input") or {}).get("plan") or ""
    if SENTINEL not in plan:
        sys.exit(0)  # not our plan — do nothing

    # Scope the loop to THIS session. Every hook event carries session_id on
    # stdin; storing it lets the gate/stop hooks ignore other concurrent
    # sessions in the same project (which otherwise get hijacked by the loop).
    sid = (data.get("session_id") or "").strip()

    proj = os.environ.get("CLAUDE_PROJECT_DIR", ".")
    d = pathlib.Path(proj) / ".claude" / ".spec-loop"
    d.mkdir(parents=True, exist_ok=True)
    (d / "active").write_text(sid or "1")
    (d / "iter").write_text("0")
    complete = d / "complete"
    if complete.exists():
        complete.unlink()

    print(
        "[spec-implement] loop armed — Phases 2-3 will run autonomously until the "
        "fast suite is green and the completion marker is written.",
        file=sys.stderr,
    )
    sys.exit(0)


main()
