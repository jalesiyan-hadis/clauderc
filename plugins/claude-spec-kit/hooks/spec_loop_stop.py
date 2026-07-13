#!/usr/bin/env python3
"""Stop hook for the spec-implement skill — the completion-driven loop.

While the loop is armed (see spec_loop_arm.py), at each turn end this hook:
  * runs the fast suite as a DETERMINISTIC gate (the model cannot lie about it),
  * blocks Claude from stopping (forcing another turn) while work remains,
  * disarms and allows stop only when tests are green AND the model has written
    the completion marker (which it does only after the full suite run, a clean
    reviewer pass, and the implementation commit).

The fast/full test commands and the linter come from the resolved per-project
config (`hooks/_config.py`). If the project is unconfigured (no
`.claude/spec-workflow.json` and no recognized stack), the loop **safe-disarms**:
it allows the stop and tells the user to add config, rather than wedging.

A persisted iteration counter caps the loop so a stuck run can never spin
forever. The completion marker alone can NEVER end the loop while tests are
red, so the model cannot shortcut the gate.
"""
import json
import os
import pathlib
import shlex
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _config  # noqa: E402

MAX_ITERS = 30
TEST_TIMEOUT = 1200  # seconds


def allow() -> None:
    """Let Claude stop normally."""
    sys.exit(0)


def block(reason: str) -> None:
    """Prevent stopping; Claude continues with `reason` as guidance."""
    print(json.dumps({"decision": "block", "reason": reason}))
    sys.exit(0)


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}

    proj = os.environ.get("CLAUDE_PROJECT_DIR", ".")
    d = pathlib.Path(proj) / ".claude" / ".spec-loop"
    active = d / "active"
    if not active.exists():
        allow()  # loop not armed — never interfere with normal sessions

    # The loop belongs to the session that armed it. Any OTHER concurrent
    # session in this project must be allowed to stop normally — otherwise the
    # loop hijacks unrelated parallel work.
    armed_sid = active.read_text().strip()
    if armed_sid not in ("", "1") and data.get("session_id") != armed_sid:
        allow()

    cfg = _config.resolve(proj)
    if cfg is None:
        active.unlink(missing_ok=True)
        print(
            "[spec-implement] no runnable test command resolved (no "
            ".claude/spec-workflow.json and no recognized project stack) — "
            "disarming the loop. Add a config file with a `test_fast` command to "
            "enable autonomous mode.",
            file=sys.stderr,
        )
        allow()

    test_cmd = shlex.split(cfg["test_fast"])
    full_cmd = cfg.get("test_full", cfg["test_fast"])
    lint_cmd = cfg.get("lint", "")

    iterf = d / "iter"
    try:
        n = int((iterf.read_text().strip() or "0"))
    except Exception:
        n = 0
    n += 1
    iterf.write_text(str(n))
    if n > MAX_ITERS:
        active.unlink(missing_ok=True)
        print(
            f"[spec-implement] max iterations ({MAX_ITERS}) reached — disarming the "
            "loop. Finish the remaining steps manually.",
            file=sys.stderr,
        )
        allow()

    try:
        r = subprocess.run(
            test_cmd, cwd=proj, capture_output=True, text=True, timeout=TEST_TIMEOUT
        )
        tests_green = r.returncode == 0
        tail = (r.stdout or "")[-1500:]
    except subprocess.TimeoutExpired:
        tests_green = False
        tail = f"test run exceeded {TEST_TIMEOUT}s timeout"
    except Exception as e:  # noqa: BLE001
        tests_green = False
        tail = f"could not run tests ({test_cmd!r}): {e}"

    complete = (d / "complete").exists()

    if tests_green and complete:
        active.unlink(missing_ok=True)
        (d / "complete").unlink(missing_ok=True)
        iterf.write_text("0")
        allow()

    if not tests_green:
        block(
            f"spec-implement loop active: the fast suite (`{cfg['test_fast']}`) is "
            "NOT green. "
            "Continue Phase 3 — implement to green WITHOUT modifying the committed "
            f"tests. Latest output tail:\n{tail}"
        )

    block(
        "spec-implement loop active: the fast suite is green but the workflow is "
        f"not finished. Now (1) run the full regression gate `{full_cmd}` and "
        "paste its output, (2) run the spec-reviewer subagent until it returns "
        "NO ISSUES and fix any gaps, "
        + (f"(3) run `{lint_cmd}` and " if lint_cmd else "(3) ")
        + "commit the implementation, then (4) as your FINAL action create the "
        "marker file `.claude/.spec-loop/complete`."
    )


main()
