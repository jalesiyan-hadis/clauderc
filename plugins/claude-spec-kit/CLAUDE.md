# CLAUDE.md

Guidance for Claude Code when working **on this plugin** (`claude-spec-kit`).
For how end users *install and use* it, see [README.md](./README.md).

## What this repo is

A Claude Code **plugin** that ships a spec-driven-development workflow. It lives
as one plugin inside the `clauderc` monorepo marketplace (at
`plugins/claude-spec-kit/`); the marketplace listing that points at it is the
monorepo's `.claude-plugin/marketplace.json`, not one in this directory. It is
content + small Python scripts — there is
no application and no pytest suite. "Testing" a change means installing the
plugin into a scratch project and exercising the workflow.

## Architecture — the 7 artifacts

| Path | Role |
|------|------|
| `.claude-plugin/plugin.json` | Plugin identity. `name` = `claude-spec-kit` → skills are namespaced `/claude-spec-kit:<skill>`. Content dirs are auto-discovered; do NOT list them here. |
| (monorepo) `../../.claude-plugin/marketplace.json` | The `clauderc` monorepo marketplace lists this plugin with `source: "./plugins/claude-spec-kit"`. No marketplace.json lives in this plugin dir. |
| `skills/spec-define/SKILL.md` | Interview → one agent-optimized spec. No hooks; its only side effect is writing one spec file. |
| `skills/spec-implement/SKILL.md` | Gated TDD workflow. Phase 1 is the single human checkpoint; Phases 2-3 run autonomously when the loop is armed. |
| `agents/spec-reviewer.md` | Read-only conformance reviewer. Sonnet-pinned. Emits `GAP:` lines or `NO ISSUES`. |
| `hooks/hooks.json` | Wires the 4 hooks via `${CLAUDE_PLUGIN_ROOT}`. |
| `hooks/_config.py` | **Single source of project-specific values.** Everything coupling-related lives here. |
| `hooks/spec_loop_arm.py` | `PostToolUse(ExitPlanMode)` — arms the loop iff the approved plan carries `<!-- spec-implement-loop -->`. |
| `hooks/spec_loop_stop.py` | `Stop` — deterministic test gate; blocks stop until green + completion marker. |
| `hooks/spec_loop_gate.py` | `PreToolUse` — auto-approves only known-safe ops while armed. |
| `hooks/spec_loop_lint.py` | `PostToolUse(Edit\|Write)` — lint-on-save, **armed-loop-only** (no-op otherwise). |
| `spec-workflow.example.json` | Per-project config template users copy. |

## The two invariants that keep it safe

1. **Dormant until armed.** Every loop hook first checks
   `${CLAUDE_PROJECT_DIR}/.claude/.spec-loop/active`. No `active` file → the hook
   is a silent no-op. The file is created ONLY by `spec_loop_arm.py`, ONLY when
   an approved plan contains the sentinel. So a normal session in any project
   with this plugin installed is never auto-approved, never gated, never linted.
2. **Session-scoped.** `active` stores the arming `session_id`; other concurrent
   sessions in the same project fall through to normal handling.

If you touch a hook, preserve both invariants. A hook that acts before the
`active` check, or ignores `session_id`, will hijack unrelated sessions.

## All project coupling goes through `_config.py`

There must be **no** hardcoded test/lint/commit commands in the hooks or skills.
The hooks call `_config.resolve(project_dir)`; the skills reference `{test_fast}`
/ `{test_full}` / `{lint}` / `{commit_prefix}` and substitute resolved values.
`resolve()` returns `None` (→ safe-disarm) when neither a config file nor stack
detection yields a runnable `test_fast`. When adding support for a new stack, add
it to `_STACK_DEFAULTS` and `_detect_stack` only — nowhere else.

## Runtime state (created in the consuming project, not here)

`.claude/.spec-loop/active` (armed + session id) · `iter` (iteration counter,
capped by `MAX_ITERS` in `spec_loop_stop.py`) · `complete` (model's done-marker).
All git-ignored in the consuming project.

## Conventions when editing

- Hooks are **stdlib-only** Python 3 — no third-party imports (they must run
  wherever `python3` does).
- Keep skill cross-references namespaced (`/claude-spec-kit:spec-implement`),
  since plugin skills are invoked by their namespaced name.
- Bump `version` in `plugin.json` when you want installed users to update
  (omitting it pins to commit SHA = every push updates).

## Manual test checklist for a change

1. `/plugin marketplace add <local path or owner/repo>` then install.
2. In a scratch Python project (with `pyproject.toml`): run `spec-define`,
   confirm first-run config write; run `spec-implement`, approve a plan, confirm
   the loop arms, drives to green, runs the reviewer, commits, and disarms.
3. In a project with NO config and an unknown stack: confirm the loop
   safe-disarms (allows stop) instead of wedging.
4. In a normal session (no armed plan): confirm no hook auto-approves or lints.
