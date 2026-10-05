# claude-spec-kit

Spec-driven development for [Claude Code](https://code.claude.com), packaged as
a plugin. It gives you three skills, two agents, and an optional autonomous TDD
loop:

- **`/claude-spec-kit:spec-define`** — an interview-driven skill that turns a
  vague intent into ONE agent-optimized spec (Bug / Feature / Refactor / Spike),
  one question at a time, grounded in your real code.
- **`/claude-spec-kit:spec-implement`** — turns a spec into a reviewed plan +
  approved test scenarios (one human gate), then implements TDD-style until the
  full suite is green with no regressions.
- **`/claude-spec-kit:spec-architecture`** — an out-of-loop scan that looks
  for shallow modules in an area of the code (or the files a spec will touch)
  and writes a ranked report of refactor candidates. It never edits code; you
  turn the chosen candidate into its own Refactor spec with `spec-define`.
- **`spec-reviewer`** — a read-only conformance agent that checks the diff
  delivers exactly what was approved.
- **`standards-reviewer`** — a read-only agent that runs alongside
  `spec-reviewer` and checks the diff against the plugin's base coding
  standard layered with your repo's own rules (see
  [Coding standards](#coding-standards)). Every finding must name what the fix
  removes; base-rule findings are fixed or listed as deferred and never block
  the loop.
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
  "spec_dir": ".claude/spec",
  "standards_file": "CODING_STANDARDS.md"     // for standards-reviewer; auto-detected
}
```

Every key is optional. Omitted keys are auto-detected from your project manifest
(`pyproject.toml` → poetry/pytest, `package.json` → npm, `go.mod` → go,
`Cargo.toml` → cargo) or fall back to built-in defaults. `standards_file` is
detected from `CODING_STANDARDS.md`, `.claude/docs/coding-standards.md`,
`.claude/docs/coding-standard.md`, then `CONTRIBUTING.md`; it stays `null` if none exist.

Add these to your project's `.gitignore`:

```
.claude/spec-workflow.json   # optional — local; commit it if you want it shared
.claude/spec/                # generated specs (local working artifacts)
.claude/.spec-loop/          # loop runtime state
```

## Coding standards

`standards-reviewer` applies two layers:

1. **Base** — [`standards/base.md`](./standards/base.md), shipped with the
   plugin: twelve code smells, each with a stable id (`duplicated-code`,
   `speculative-generality`, …). Base findings are *fix or defer*.
2. **Your repo** — the file `standards_file` points to (default detection:
   `CODING_STANDARDS.md`, `.claude/docs/coding-standards.md`,
   `.claude/docs/coding-standard.md`, `CONTRIBUTING.md`). Its body is your own
   rules; they are *must fix* and win over the base on conflict. Optional
   frontmatter adjusts the base:

```markdown
---
extends: base                          # or "none" to drop the base entirely
disable: [primitive-obsession]         # base rules that don't fit this repo
enforce: [duplicated-code]             # base rules raised to must-fix here
---
- Use `pathlib`, never `os.path`.
- Every public function has a docstring.
```

See what the reviewer will get with
`python3 <plugin>/hooks/_config.py --standards --project .` — the first line
lists the layers in effect, and unknown rule ids are flagged as warnings.

## Usage

```shell
# 1. Define a spec
/claude-spec-kit:spec-define add rate limiting to the upload endpoint

# 2. (new terminal) implement it
claude "/claude-spec-kit:spec-implement .claude/spec/<your-spec>.md"
```

`spec-define` prints the exact `spec-implement` command when it finishes.

### When to run `spec-architecture`

It is **not** part of any ticket's Done, and the implement loop never runs it.
Run it yourself:

- **before a large Feature spec**, pointed at that spec, to ask "how do we make
  this change easy?" — `/claude-spec-kit:spec-architecture .claude/spec/<spec>.md`;
- **periodically on active areas** (every week or two) —
  `/claude-spec-kit:spec-architecture src/billing/`, or with no argument to scan
  the most-changed files of the last 30 days.

`spec-define` also offers a scoped version of the scan while writing a Feature
or Refactor spec, when the change touches 3+ files for one concept or proposes
a new module. If a Strong candidate comes back and you choose to do it first,
the spec records a `Preparatory refactor:` line and the handoff prints the
refactor's `spec-define` command before the `spec-implement` one.

Every candidate it reports has to delete something (merged modules, removed
pass-throughs, retired tests); candidates that would add structure are dropped
before the report. The report is written to `<spec_dir>/architecture-<date>.md`.

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
