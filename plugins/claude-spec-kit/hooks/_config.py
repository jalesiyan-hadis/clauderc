#!/usr/bin/env python3
"""Shared config resolver for the claude-spec-kit loop hooks.

The spec-driven-dev workflow needs a handful of project-specific values: how to
run the fast test suite, the full/coverage suite, the linter; which bash
prefixes are safe to auto-approve; which paths are protected; and how commits /
tickets are formatted. This module resolves those values from, in priority
order:

  1. `.claude/spec-workflow.json` in the project (explicit override), then
  2. auto-detection from the project's manifest (pyproject.toml / package.json /
     go.mod / Cargo.toml), then
  3. built-in defaults for any keys still missing.

`standards_file` (the project's coding-standards doc, read by the
standards-reviewer agent) is detected by file presence, not by stack: the first
of `_STANDARDS_CANDIDATES` that exists, else ``None``. `compose_standards()`
layers it over the plugin's `standards/base.md` (see that function).

If there is NO config file AND no recognized manifest, `resolve()` returns
``None`` — the signal for the loop hooks to **safe-disarm** (behave as if the
plugin were not installed) rather than wedge an unconfigured project.

No third-party dependencies: stdlib only, so the hooks run anywhere `python3`
does.
"""
from __future__ import annotations

import json
import pathlib
import re
from typing import Optional

CONFIG_REL = ".claude/spec-workflow.json"
BASE_STANDARDS = pathlib.Path(__file__).resolve().parent.parent / "standards" / "base.md"

# Keys every consumer can rely on existing once resolve() returns a dict.
_BASE_DEFAULTS = {
    "commit_prefix": "feat",
    "ticket_regex": r"[A-Z]{2,}-\d+",
    "safe_bash_prefixes": [
        "git add",
        "git commit",
        "git status",
        "git diff",
        "git log",
        "git rev-parse",
        "git restore --staged",
    ],
    "protected_paths": [".env", ".env.", "credentials", "service-account"],
    "spec_dir": ".claude/spec",
}

# Coding-standards docs, in priority order. CONTRIBUTING.md is last because it
# is often about PR process rather than code.
_STANDARDS_CANDIDATES = (
    "CODING_STANDARDS.md",
    ".claude/docs/coding-standards.md",
    ".claude/docs/coding-standard.md",
    "CONTRIBUTING.md",
)

# Per-stack auto-detected command defaults. Each entry supplies the test/lint
# commands; the base defaults above fill in the rest.
_STACK_DEFAULTS = {
    "poetry": {
        "test_fast": "poetry run pytest -q -x",
        "test_full": "poetry run pytest --cov",
        "lint": "poetry run pre-commit run --all-files",
        "lint_file": "poetry run pre-commit run --files {file}",
        "safe_bash_prefixes": _BASE_DEFAULTS["safe_bash_prefixes"]
        + ["poetry run pytest", "poetry run pre-commit"],
    },
    "pytest": {
        "test_fast": "pytest -q -x",
        "test_full": "pytest --cov",
        "lint": "pre-commit run --all-files",
        "lint_file": "pre-commit run --files {file}",
        "safe_bash_prefixes": _BASE_DEFAULTS["safe_bash_prefixes"]
        + ["pytest", "pre-commit"],
    },
    "npm": {
        "test_fast": "npm test",
        "test_full": "npm test",
        "lint": "npm run lint",
        "lint_file": "npm run lint",
        "safe_bash_prefixes": _BASE_DEFAULTS["safe_bash_prefixes"]
        + ["npm test", "npm run", "npx"],
    },
    "go": {
        "test_fast": "go test ./...",
        "test_full": "go test -cover ./...",
        "lint": "gofmt -l .",
        "lint_file": "gofmt -l {file}",
        "safe_bash_prefixes": _BASE_DEFAULTS["safe_bash_prefixes"]
        + ["go test", "go build", "go vet", "gofmt"],
    },
    "cargo": {
        "test_fast": "cargo test",
        "test_full": "cargo test",
        "lint": "cargo clippy --all-targets",
        "lint_file": "cargo clippy",
        "safe_bash_prefixes": _BASE_DEFAULTS["safe_bash_prefixes"]
        + ["cargo test", "cargo build", "cargo check", "cargo clippy"],
    },
}


def _detect_stack(proj: pathlib.Path) -> Optional[str]:
    """Best-effort detection of the project's toolchain from its manifest."""
    pyproject = proj / "pyproject.toml"
    if pyproject.exists():
        try:
            text = pyproject.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            text = ""
        if "[tool.poetry]" in text or "poetry" in text:
            return "poetry"
        return "pytest"
    if (proj / "package.json").exists():
        return "npm"
    if (proj / "go.mod").exists():
        return "go"
    if (proj / "Cargo.toml").exists():
        return "cargo"
    return None


def _detect_standards_file(proj: pathlib.Path) -> Optional[str]:
    """First existing coding-standards doc (relative path), or None."""
    for rel in _STANDARDS_CANDIDATES:
        if (proj / rel).is_file():
            return rel
    return None


def detect_defaults(proj: pathlib.Path) -> Optional[dict]:
    """Return auto-detected config for the project's stack, or None if unknown."""
    stack = _detect_stack(proj)
    if stack is None:
        return None
    merged = dict(_BASE_DEFAULTS)
    merged.update(_STACK_DEFAULTS[stack])
    merged["_detected_stack"] = stack
    return merged


def resolve(proj: pathlib.Path) -> Optional[dict]:
    """Resolve effective config for ``proj``.

    Returns a dict with all required keys, or ``None`` to signal safe-disarm
    (no config file and no recognized stack).
    """
    proj = pathlib.Path(proj)
    cfg_path = proj / CONFIG_REL

    detected = detect_defaults(proj)

    if cfg_path.exists():
        try:
            user_cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            user_cfg = {}
        base = detected if detected is not None else dict(_BASE_DEFAULTS)
        # A file may omit test commands; only fall through to disarm if neither
        # the file nor detection can supply a runnable test command.
        merged = dict(base)
        merged.update(user_cfg)
        if "test_fast" not in merged:
            return None
        # ensure base-level keys exist
        for k, v in _BASE_DEFAULTS.items():
            merged.setdefault(k, v)
        merged.setdefault("standards_file", _detect_standards_file(proj))
        return merged

    if detected is not None:
        detected["standards_file"] = _detect_standards_file(proj)
    return detected  # may be None -> safe-disarm


def _standards_file_for(proj: pathlib.Path) -> Optional[str]:
    """`standards_file` from the config file if set there, else detection.

    Read directly rather than via resolve(), so standards still compose in a
    project whose loop would safe-disarm.
    """
    cfg_path = proj / CONFIG_REL
    if cfg_path.exists():
        try:
            user_cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            user_cfg = {}
        if "standards_file" in user_cfg:
            return user_cfg["standards_file"]
    return _detect_standards_file(proj)


def _split_frontmatter(text: str) -> tuple:
    """Return ({key: str | list}, body) for a minimal YAML-style frontmatter.

    Supports `key: value`, `key: [a, b]`, and `key:` followed by `- item` lines.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    meta: dict = {}
    key = None
    for i, line in enumerate(lines[1:], start=1):
        stripped = line.strip()
        if stripped == "---":
            return meta, "\n".join(lines[i + 1 :]).strip()
        if stripped.startswith("- ") and key is not None:
            meta.setdefault(key, [])
            if isinstance(meta[key], list):
                meta[key].append(stripped[2:].strip())
            continue
        if ":" in stripped:
            key, _, value = stripped.partition(":")
            key, value = key.strip(), value.split("#", 1)[0].strip()
            if value.startswith("[") and value.endswith("]"):
                meta[key] = [v.strip() for v in value[1:-1].split(",") if v.strip()]
            elif value:
                meta[key] = value
    return {}, text  # unterminated frontmatter: treat the whole file as body


def _base_rules() -> list:
    """[(id, block_text)] from standards/base.md, in file order."""
    text = BASE_STANDARDS.read_text(encoding="utf-8")
    parts = re.split(r"^### ", text, flags=re.M)[1:]
    rules = []
    for part in parts:
        rule_id = part.split(" ", 1)[0].strip()
        rules.append((rule_id, "### " + part.strip()))
    return rules


def compose_standards(proj: pathlib.Path) -> str:
    """The effective coding standard for ``proj``, as text for standards-reviewer.

    Layers the repo's `standards_file` over the plugin's base rules. The repo
    file's frontmatter may set `extends: none` (drop the base), `disable: [ids]`
    and `enforce: [ids]`. Output sections: MUST FIX (repo rules + enforced base
    rules) and FIX OR DEFER (the remaining base rules).
    """
    proj = pathlib.Path(proj)
    rel = _standards_file_for(proj)
    meta, body, warnings = {}, "", []
    if rel:
        path = proj / rel
        try:
            meta, body = _split_frontmatter(path.read_text(encoding="utf-8"))
        except OSError:
            warnings.append(f"standards_file {rel!r} not readable; using base only")
            rel = None

    def as_list(v):
        return v if isinstance(v, list) else ([v] if v else [])

    use_base = str(meta.get("extends", "base")).lower() != "none"
    disable = set(as_list(meta.get("disable")))
    enforce = set(as_list(meta.get("enforce")))
    rules = _base_rules() if use_base else []
    known = {rid for rid, _ in _base_rules()}
    for rid in sorted((disable | enforce) - known):
        warnings.append(f"unknown base rule id {rid!r} in {rel}")

    must = [block for rid, block in rules if rid in enforce and rid not in disable]
    defer = [block for rid, block in rules if rid not in enforce and rid not in disable]

    out = ["# Effective coding standards",
           f"Layers: {'base' if use_base else 'no base'}"
           + (f" + {rel}" if rel else "")
           + (f"; disabled: {', '.join(sorted(disable & known))}" if disable & known else "")]
    out += [f"WARNING: {w}" for w in warnings]
    out.append("## MUST FIX (report as [standard])")
    if body:
        out.append(f"### Repository rules ({rel})\n{body}")
    out += must
    if not body and not must:
        out.append("(none)")
    out.append("## FIX OR DEFER (report as [baseline])")
    out += defer or ["(none)"]
    return "\n\n".join(out) + "\n"


def example_config(proj: pathlib.Path) -> dict:
    """A fully-populated config suitable for writing as a first-run template."""
    detected = detect_defaults(proj)
    base = detected if detected is not None else dict(_BASE_DEFAULTS)
    out = dict(_BASE_DEFAULTS)
    out.update(base)
    # surface the test keys even when undetected, as editable placeholders
    out.setdefault("test_fast", "<command to run the fast test suite>")
    out.setdefault("test_full", "<command to run the full/coverage suite>")
    out.setdefault("lint", "<command to run lint/format checks>")
    out.setdefault("lint_file", "<command to lint a single file: use {file}>")
    out["standards_file"] = _detect_standards_file(proj)
    out.pop("_detected_stack", None)
    return out


if __name__ == "__main__":
    import argparse
    import os

    parser = argparse.ArgumentParser(description="claude-spec-kit config resolver")
    parser.add_argument(
        "--print-example",
        action="store_true",
        help="Print a populated config template for the project (for first-run setup).",
    )
    parser.add_argument(
        "--resolve",
        action="store_true",
        help="Print the effective resolved config, or 'null' if the loop would safe-disarm.",
    )
    parser.add_argument(
        "--standards",
        action="store_true",
        help="Print the effective coding standard (base + the repo's standards_file).",
    )
    parser.add_argument(
        "--project",
        default=os.environ.get("CLAUDE_PROJECT_DIR", "."),
        help="Project root (defaults to $CLAUDE_PROJECT_DIR or cwd).",
    )
    ns = parser.parse_args()
    proj = pathlib.Path(ns.project)
    if ns.standards:
        print(compose_standards(proj), end="")
    elif ns.resolve:
        print(json.dumps(resolve(proj), indent=2))
    else:
        print(json.dumps(example_config(proj), indent=2))
