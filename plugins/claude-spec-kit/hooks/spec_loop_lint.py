#!/usr/bin/env python3
"""PostToolUse(Edit|Write|MultiEdit) hook — lint-on-save during the loop ONLY.

This is a convenience that lints a file right after it is written, but ONLY
while the spec-implement loop is armed for THIS session. In any normal session
(loop not armed) it is a silent no-op, so installing the plugin never imposes a
lint pass on a stranger's ordinary edits.

The lint command comes from `lint_file` in the resolved per-project config; if
no command resolves, the hook does nothing. Failures are swallowed (exit 0) —
this hook never blocks an edit; the real lint gate is the commit step in the
skill.
"""
import json
import os
import pathlib
import shlex
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _config  # noqa: E402


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    proj = os.environ.get("CLAUDE_PROJECT_DIR", ".")
    active = pathlib.Path(proj) / ".claude" / ".spec-loop" / "active"
    if not active.exists():
        sys.exit(0)  # loop not armed — never lint normal edits

    armed_sid = active.read_text().strip()
    if armed_sid not in ("", "1") and data.get("session_id") != armed_sid:
        sys.exit(0)

    cfg = _config.resolve(proj)
    if not cfg:
        sys.exit(0)
    tmpl = cfg.get("lint_file")
    if not tmpl or "{file}" not in tmpl:
        sys.exit(0)

    fpath = ((data.get("tool_input") or {}).get("file_path") or "").strip()
    if not fpath:
        sys.exit(0)

    cmd = shlex.split(tmpl.replace("{file}", shlex.quote(fpath)))
    try:
        subprocess.run(cmd, cwd=proj, capture_output=True, text=True, timeout=120)
    except Exception:
        pass
    sys.exit(0)


main()
