# claude-spec-kit

Spec-driven development for [Claude Code](https://code.claude.com), packaged as
a plugin. It gives you two skills, one agent, and an optional autonomous TDD
loop:

- **`/claude-spec-kit:spec-define`** — an interview-driven skill that turns a
  vague intent into ONE agent-optimized spec (Bug / Feature / Refactor / Spike),
  one question at a time, grounded in your real code.
- **`/claude-spec-kit:spec-implement`** — turns a spec into a reviewed plan +
  approved test scenarios (one human gate), then implements TDD-style until the
  full suite is green with no regressions.
- **`spec-reviewer`** — a read-only conformance agent that checks the diff
  delivers exactly what was approved.
- **Optional autonomous loop** — once you approve the plan, hooks drive
  implementation to "green + reviewed + committed" without further prompts.

## Install

```shell
/plugin marketplace add hadisjalesiyan/claude-spec-kit
/plugin install claude-spec-kit@claude-spec-kit
```

> Replace `hadisjalesiyan/claude-spec-kit` with your actual GitHub `owner/repo`
> if you forked or renamed it.

## First-run setup (per project)

The workflow needs to know how YOUR project runs tests, lints, and formats
commits. The first time you run `spec-define` or `spec-implement` in a project,
the skill auto-detects your stack and proposes a `.claude/spec-workflow.json`,
which you confirm or tweak. You can also create it by hand from
[`spec-workflow.example.json`](./spec-workflow.example.json):

```jsonc
{
  "test_fast": "poetry run pytest -q -x",          // fast suite — the loop's gate
  "test_full": "poetry run pytest --cov",          // full regression gate
  "lint":      "poetry run pre-commit run --all-files",
  "lint_file": "poetry run pre-commit run --files {file}",
  "commit_prefix": "feat",                          // Conventional Commits type
  "ticket_regex":  "[A-Z]{2,}-\\d+",               // parse ticket from branch
  "safe_bash_prefixes": ["git add", "git commit", "poetry run pytest", "..."],
  "protected_paths": [".env", "migrations/"],
  "spec_dir": ".claude/spec"
}
```

Every key is optional. Omitted keys are auto-detected from your project manifest
(`pyproject.toml` → poetry/pytest, `package.json` → npm, `go.mod` → go,
`Cargo.toml` → cargo) or fall back to built-in defaults.

Add these to your project's `.gitignore`:

```
.claude/spec-workflow.json   # optional — local; commit it if you want it shared
.claude/spec/                # generated specs (local working artifacts)
.claude/.spec-loop/          # loop runtime state
```

## Usage

```shell
# 1. Define a spec
/claude-spec-kit:spec-define add rate limiting to the upload endpoint

# 2. (new terminal) implement it
claude "/claude-spec-kit:spec-implement .claude/spec/<your-spec>.md"
```

`spec-define` prints the exact `spec-implement` command when it finishes.

## The autonomous loop (opt-in by design)

The loop is **dormant until you arm it**. Installing the plugin registers four
hooks, but they do nothing in normal sessions. The loop only activates when you
approve a `spec-implement` plan — that plan carries a sentinel
(`<!-- spec-implement-loop -->`), and approving it (an explicit human action)
arms the loop *for that session only*.

While armed, in the arming session:
- the **Stop hook** re-runs your `test_fast` at each turn end and blocks stopping
  until tests are green **and** a completion marker exists;
- the **PreToolUse gate** auto-approves only known-safe commands (your
  `safe_bash_prefixes`, implementation edits, the reviewer subagent) — chained
  commands, redirects, and writes to `protected_paths` still prompt;
- a hard iteration cap disarms a stuck loop.

If a project has no `.claude/spec-workflow.json` and no recognized stack, the
loop **safe-disarms** — it behaves as if not installed, so it can never wedge an
unconfigured project. You can also simply never arm it and drive `spec-implement`
interactively.

> **Security note:** the gate auto-approves shell/edit operations while armed.
> Read [`hooks/`](./hooks/) before enabling on a sensitive repo. A hook `allow`
> can never override your project's `deny`/`ask` permission rules.

## Requirements

- Claude Code with plugin support.
- `python3` on PATH (the hooks are dependency-free stdlib scripts).
- Your project's own test/lint toolchain installed (whatever `test_fast`/`lint`
  invoke).

## License

[MIT](./LICENSE)
