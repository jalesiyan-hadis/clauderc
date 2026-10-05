#!/usr/bin/env python3
"""SessionEnd hook for the review-assist skill.

Copies the session transcript into the review's retro dir, so every guided
review keeps its raw session next to `review.html` and `retro.md`.

Dormant unless marked: review-assist writes
`~/.claude/retro_review/.active/<session_id>.json` (`{"retro_dir": ...}`) when
it creates the retro dir. No marker for THIS session → silent no-op, so every
other session that ends is untouched. With a marker: copy `transcript_path` to
`<retro_dir>/transcript.jsonl`, then delete the marker.

The marker lives at that fixed path even when `review.retro_root` points
elsewhere, because a SessionEnd hook has no reliable project config to read.
"""
import json
import pathlib
import shutil
import sys

ACTIVE_DIR = pathlib.Path.home() / ".claude" / "retro_review" / ".active"


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    sid = (data.get("session_id") or "").strip()
    if not sid or "/" in sid or sid.startswith("."):
        sys.exit(0)
    marker = ACTIVE_DIR / f"{sid}.json"
    if not marker.is_file():
        sys.exit(0)  # not a review-assist session — do nothing

    try:
        retro_dir = pathlib.Path(json.loads(marker.read_text(encoding="utf-8"))["retro_dir"])
    except (OSError, ValueError, KeyError, TypeError):
        marker.unlink(missing_ok=True)
        sys.exit(0)

    transcript = pathlib.Path(data.get("transcript_path") or "")
    if transcript.is_file() and retro_dir.is_dir():
        try:
            shutil.copyfile(transcript, retro_dir / "transcript.jsonl")
        except OSError as exc:
            print(f"[review-assist] transcript not saved: {exc}", file=sys.stderr)
    marker.unlink(missing_ok=True)
    sys.exit(0)


main()
