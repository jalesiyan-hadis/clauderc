---
name: spec-define
description: Interactively develop a high-quality, agent-optimized specification
  for a Bug, Feature, Refactor, or Spike — through a grounded one-question-at-a-time
  interview — then write it to the spec dir and optionally hand off to
  spec-implement in a fresh session. Use when starting a new piece of work that
  needs a spec before implementation.
argument-hint: "[optional: short description of the task]"
---

# Spec Define — interview → agent-optimized spec → handoff

Your job is to turn a vague intent into ONE well-defined spec file that
`spec-implement` can consume directly. You do this by interviewing the user,
grounding every question in the real codebase, and writing the spec only after
the user confirms a playback.

The output spec is short-lived and feeds an implementation **agent**, so it is
optimized for that agent: named files, key interface signatures, and testable
Given-When-Then acceptance criteria — not a durable prose PRD. `spec-implement`
re-validates every concrete reference against live code, so concrete-but-current
beats vague-but-durable here.

Spec written by this skill is for LOCAL use only. Write it to the project's spec
dir (`spec_dir` in config, default `.claude/spec/`), as
`<spec_dir>/<ticket>-<slug>.md` when a ticket is found, else `<slug>.md`. The
spec dir should be git-ignored. Never commit it.

If `$ARGUMENTS` holds a task description, use it to seed the opener. Otherwise
ask what the user wants to build/fix.

## Phase 0 — Project config (first-run setup)

Before interviewing, ensure the project is configured. Check for
`.claude/spec-workflow.json` in the project root.

- **If it exists**, read it: you need `spec_dir`, `ticket_regex`, and
  `commit_prefix`.
- **If it is missing**, this is first use. Run the bundled detector to propose a
  config, e.g.:
  `python3 "${CLAUDE_PLUGIN_ROOT}/hooks/_config.py" --print-example` *(if the
  helper exposes a CLI; otherwise import it: `from hooks import _config;
  _config.example_config(project_dir)`)*. Show the proposed JSON, ask the user to
  confirm or tweak it (especially the test/lint commands), then write it to
  `.claude/spec-workflow.json`. This config is also what `spec-implement`'s
  autonomous loop reads, so getting it right now pays off later. Tell the user to
  git-ignore `.claude/spec-workflow.json` and `.claude/.spec-loop/` if they
  aren't already.

A Spike that won't feed `spec-implement` does not strictly need the config; you
may skip Phase 0 for a pure-investigation Spike.

---

## Core interview rules (follow these the whole way through)

1. **One substantive question per turn**, and **always offer your recommended
   answer** so the user ratifies or corrects rather than drafting from scratch.
   Asking several open questions at once makes the user drop the hard ones.
   Small batches are allowed ONLY for closed, low-effort confirmations near the
   end (use AskUserQuestion there if helpful).
2. **Never ask what you can verify.** Read the repo inline (Read/Grep/Glob are
   free and expected) to answer your own questions before asking the user.
3. **Funnel: broad → narrow.** Open broad (problem, who has it, what "done"
   means), follow threads, close on specifics LAST. Do not lead with
   solution-shaped questions — priming corrupts later answers.
4. **Terminology discipline, concurrently.** Sharpen every fuzzy or overloaded
   term the moment it appears ("'record' — a DB row or a register entry?").
   Stress-test claims with concrete edge-case scenarios. Cross-check anything
   the user asserts against the actual code and surface contradictions.
5. **Reflect & confirm** each topic: "So what I'm hearing is X — correct?" Keep
   an editable running summary of decisions so far.
6. **Flag, don't bury.** Anything unresolved goes into an explicit
   "Open Questions & Assumptions" section — never silently resolve an
   assumption.

### Anti-patterns to avoid
Multi-question walls · leading/loaded questions ("you'll want this on mobile,
right?") · premature solutioning · silently resolving assumptions · a spec so
verbose it's costlier to review than the code · presenting file paths/snippets
as permanent truth (mark them "guidance — re-validated at implement time") ·
skipping the playback-confirm gate.

---

## Research depth (token-conscious)

- Reading files inline needs no approval — do it freely to ground questions.
- Read-only search/architecture subagents (e.g. an `Explore` or `Plan` agent if
  your setup has them) may be spawned freely when a question needs broad search
  ("where are all call sites of X?") or architecture-weighing (compare 2–3
  approaches) that inline reading would make expensive. State briefly why.
- A heavier general-purpose subagent that can edit/run requires the user's
  approval first. Ask: state the type, the purpose, and why inline / read-only
  subagents won't do.

---

## Phase 1 — Classify the task

First question always: is this a **Bug**, **Feature**, **Refactor**, or
**Spike**? This selects the template and the depth of interview. If
`$ARGUMENTS` makes it obvious, state your classification and ask the user to
confirm rather than asking cold.

## Phase 2 — Ground in the repo

Derive the ticket id from the current branch by matching `ticket_regex` from
config against `git branch --show-current` (e.g. with the default
`[A-Z]{2,}-\d+`, `PROJ-123-add-foo` → `PROJ-123`). If there is no match, proceed
without a ticket — the spec filename and commits simply omit it. Read the files
the task obviously touches. Build a mental map before interviewing so your
questions and recommendations are concrete.

## Phase 3 — Interview to fill the template

Walk the template for the classified type (below), one question per turn with a
recommendation, applying the Core interview rules. Resolve dependencies between
decisions one at a time. Right-size depth to risk: a one-line bug needs few
questions; a cross-cutting feature needs many.

## Phase 3.5 — Minimal-approach gate (do this before playback)

**Mandatory for every task type — Bug, Feature, Refactor, and Spike.** Before
the spec proposes *any* implementation, challenge your own approach for
minimalism. Avoiding over-engineering is a non-negotiable goal of this skill: the
spec must NEVER inherit the first solution that comes to mind — an over-engineered
spec forces costly back-and-forth later in `spec-implement`.

Ask these out loud (one per turn, with your recommendation) and resolve them
before writing:

1. **Where is the data already available?** Prefer fixing at the site that
   already holds the data (the existing write/read point) over adding a new pass
   that re-discovers it. A new recursive walk / traversal when the existing code
   already holds the parent + value is a **red flag**.
2. **Can we change an existing invariant or bound** (e.g. widen a loop bound,
   relax a too-narrow condition) instead of **adding a new enforcement step,
   method, or call-site**? Local edit beats new stage.
3. **Is the new method / class / pipeline step actually load-bearing**, or is
   this a one-line edit to existing code? Smallest viable change wins.

If, after these questions, you still propose a *new* method/pass/call-site, the
spec must record in one line **why a local edit to existing code won't work**.
That justification is mandatory — it is the artifact `spec-implement` checks the
approach against, instead of discovering the simpler fix mid-implementation.

## Phase 4 — Playback & confirm (stopping gate)

Replay the fully assembled spec to the user. Stop interviewing only when ALL of:
the template is fully covered, the user confirms the playback, new questions
stop yielding new facts, and no undefined term or unresolved assumption remains
(any leftover goes to Open Questions & Assumptions). When playing back the
proposed approach, state explicitly that **this is the simplest approach
considered** (per Phase 3.5) and let the user ratify that, not just the
requirements. Get explicit confirmation before writing.

## Phase 5 — Write the spec

Create the spec dir if missing. Derive `<slug>` from the task (kebab-case,
short). Write `<spec_dir>/<ticket>-<slug>.md` (or `<spec_dir>/<slug>.md` with no
ticket) using the matching template.

## Phase 6 — Handoff (manual, by design)

Implementation runs in a FRESH session so the current one stays clean. **Do NOT
auto-spawn a terminal** — print the exact command and let the user run it
themselves.

Why manual: programmatically opening a GUI terminal from inside an agent is
unreliable — it gives no clean success signal, and a new window may re-trigger
OS "trust this terminal" plus external-tool approval prompts in the fresh
session. With no confirmation to read, the agent can mistake that for failure
and retry, spawning window after window. A printed one-liner avoids all of that
and costs the user a single paste.

Print this, substituting the real absolute project dir and spec path:

```
cd <ABS_PROJECT_DIR> && claude "/claude-spec-kit:spec-implement <spec-path>"
```

Tell the user to paste it into a new terminal window. Note that `spec-implement`
keeps its own one-time human approval gate (plan + test scenarios) — that runs
in the new session by design and is not something this handoff skips.

Spike specs usually do NOT feed `spec-implement` (their deliverable is a
recommendation, not code) — for a Spike, skip the handoff entirely unless the
user asks.

---

## Templates

All acceptance criteria use **Given-When-Then**. Every template starts with the
ticket id (or title only, if no ticket) and a one-line title.

### Shared block — "Affected files & interfaces"
Embedded by Bug, Feature, and Refactor. Keep it at the right altitude, and keep
it **minimal** — describe the smallest viable change that satisfies Phase 3.5,
not the first design that came to mind. If you list a *new* method/class/pass,
include the one-line "why a local edit won't work" justification.

```
## Affected files & interfaces
> Guidance, not gospel — spec-implement re-validates against live code.
- `path/to/file.ext` — <what changes here — prefer editing existing code>
- Key signatures (current or proposed):
  - `fn foo(x: T) -> R`  — <role>
  - (If proposing anything NEW: one line on why an edit to existing code can't do it)
- Pattern to imitate: `path/to/similar.ext` (<why it's the right model>)
```

### Bug
```
# <TICKET> — <title>   (Bug)

## Summary
<one paragraph>

## Current behavior
<what happens now>

## Expected behavior
<what should happen>

## Repro steps
1. ...

## Root cause (if known)
<analysis, or "unknown — to be confirmed during implementation">

<Shared "Affected files & interfaces" block>

## Acceptance criteria
- Given <precondition>, When <action>, Then <expected outcome>.
- (include the failing case and at least one adjacent edge case)

## Regression-test note
<which test encodes the fix; which existing suite must stay green>

## Open Questions & Assumptions
- ...
```

### Feature
```
# <TICKET> — <title>   (Feature)

## User story
As a <role>, I want <capability>, so that <benefit>.

## In scope
- ...
## Out of scope / Non-goals
- ...

<Shared "Affected files & interfaces" block>

## Acceptance criteria
### Happy path
- Given ..., When ..., Then ...
### Edge cases
- Given ..., When ..., Then ...
### Error handling
- Given ..., When ..., Then ...

## Test mapping
<1:1 baseline: each acceptance criterion → one test scenario.
 spec-implement may expand, not drop.>

## Non-functional constraints
<versions, performance, security, conventions — omit if none>

## Open Questions & Assumptions
- ...
```

### Refactor
```
# <TICKET> — <title>   (Refactor)

## Summary / Motivation
<why refactor; what's painful today>

<Shared "Affected files & interfaces" block>

## Current vs. target structure
- Current: ...
- Target: ...

## Behavior-preservation guarantee
No functional/observable behavior changes. Public contracts unchanged unless
listed here.

## Existing test-coverage check
<Inspect whether the code being refactored is already covered by tests.>
- Covered by: `tests/...` (these MUST stay green), OR
- NOT covered → define characterization tests below as GWT so spec-implement
  writes them FIRST, before refactoring, to lock current behavior:
  - Given <current input>, When <call>, Then <current output>.

## Acceptance criteria
- All existing covering suites stay green.
- New characterization tests (if any) pass against current code, then still
  pass after the refactor.

## In scope / Out of scope
- ...

## Risk areas
- ...

## Open Questions & Assumptions
- ...
```

### Spike
```
# <TICKET> — <title>   (Spike)

## Question(s)
<the unknowns this spike resolves>

## Time box
<e.g. 1 day>

## Approach
<how we'll investigate>

## Deliverable
<doc / prototype / recommendation — what gets produced>

## "Done when"
- ...

## Decision / Recommendation
<filled in at the end of the spike>
```

---

## Done

You are done when the spec file exists in the configured spec dir, matches the
confirmed playback, and you have printed the `spec-implement` handoff command
(unless it's a Spike). Report the spec path.
