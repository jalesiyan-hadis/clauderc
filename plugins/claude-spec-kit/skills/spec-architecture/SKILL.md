---
name: spec-architecture
description: Scan an area of the codebase (or the files a spec will touch) for shallow modules that are hard to change or test, and write a ranked report of "deepening" refactor candidates — each one must delete something. Never edits code; the chosen candidate becomes its own Refactor spec via spec-define. Run before a large Feature spec or periodically on active areas, not as part of any ticket's Done. (spec-define can offer a scoped version of this scan while writing a Feature or Refactor spec.)
argument-hint: "[optional: spec path or directory]"
disable-model-invocation: true
---

# Spec Architecture — find deepening candidates, out of the build loop

You look for places where the code's shape makes changes and tests harder than
they need to be, and write a short, ranked report. You **never edit code**. A
refactor you recommend happens later as its own spec, its own branch, and its
own run of `spec-implement` with characterisation tests first.

This skill sits **outside** `spec-implement`'s loop on purpose: the agent that
just wrote the code is the wrong one to judge its shape, and structural
refactors tangled into a feature change make both harder to review.

## Vocabulary

- **Deep module:** a lot of behavior behind a small interface. Callers and
  tests learn little and get a lot.
- **Shallow module:** its interface is nearly as complex as what it does, so it
  adds a concept without hiding anything.
- **Seam:** the interface callers and tests cross.
- **Deletion test:** delete the module in your head. If its complexity vanishes,
  it was a pass-through. If it reappears across several callers, it earns its
  place.

Depth is about **fewer things to know**, not bigger files and not more parts. A
"deeper" design that adds classes, layers, or interfaces is not deeper.

## Phase 0 — Config

Read `.claude/spec-workflow.json` if present for `spec_dir` (default
`.claude/spec`). Do not write a config here; if it is missing, use the default
and say so. Run `python3 "${CLAUDE_PLUGIN_ROOT}/hooks/_config.py" --standards`
for the effective coding standard and pass it to the scan agent: candidates
that would violate a MUST FIX rule are dropped.

## Phase 1 — Pick the hot spots

From `$ARGUMENTS`:
- **A spec path:** the files its "Affected files & interfaces" block names,
  plus their direct callers. The question becomes "how do we make this change
  easy before implementing it?"
- **A directory:** files under it, ranked by recent change frequency.
- **Nothing:** the ~10 most-changed source files in the last 30 days
  (`git log --since=30.days --name-only --pretty=format:`), excluding tests,
  generated files, and lockfiles.

State the list you chose in one line before scanning.

## Phase 2 — Scan (one read-only agent)

Spawn ONE read-only search agent (an `Explore` agent if your setup has one,
model `sonnet`), scoped tightly to the hot-spot files and their direct
neighbors. Ask it to return candidates with `file:line` refs, not file dumps.
Its prompt asks it to look for:

1. **One concept spread across many small modules** — a change to the concept
   means touching several files.
2. **An interface nearly as complex as its implementation** — wrappers,
   pass-throughs, managers that forward calls.
3. **Pure functions extracted "for testability" while the bugs live in the
   call sites** that glue them together, untested.
4. **Code that is untested because it is untestable through its interface** —
   tests reach into internals or mock the module's own collaborators.

For each candidate it applies the deletion test and reports what would be
removed by deepening it.

## Phase 3 — Filter (before anything reaches the report)

Drop a candidate when any of these hold:
- Its "after" has more modules, classes, layers, or interfaces than its
  "before".
- It cannot name what gets deleted (modules merged, pass-throughs removed,
  tests retired at old seams).
- It adds a port, interface, or dependency-injection parameter with only one
  implementation (production code plus a test stand-in counts as two).

Rate the rest:
- **Strong** — states what is removed AND recent `git log` shows real change
  pain in those files (frequent edits, co-changing files, fix-on-fix commits).
- **Worth exploring** — clear removal, weaker change evidence.
- **Speculative** — plausible, but evidence is thin. Keep at most two.

## Phase 4 — Write the report

Write `<spec_dir>/architecture-<YYYY-MM-DD>.md` (local only, like specs; never
commit it). Create the dir if missing. Shape:

```
# Architecture scan — <date>
Scope: <spec path | directory | git hot spots, last 30 days>
Standards: <the "Layers:" line from --standards>

## Top recommendation
<candidate name> — <one line why this one first>

## Candidates
### 1. <name>   (Strong | Worth exploring | Speculative)
- Files: `a.py:10-80`, `b.py:5-40`
- Problem: <what makes changes/tests hard today, one or two lines>
- Deeper interface: `fn new_seam(...) -> ...` <what it hides>
- Removed: <modules merged / pass-throughs deleted / tests retired>
- Tests that move to the new seam: <which, and which old ones are retired>
- Evidence: <git log facts>
```

Keep it short: three to six candidates is typical. If nothing survives
Phase 3, say so — "no deepening candidates" is a valid, useful result.

## Phase 5 — Handoff (manual)

Show the report path and the top recommendation. For the candidate the user
picks, print the command that turns it into its own Refactor spec, and let the
user run it:

```
/claude-spec-kit:spec-define refactor: <candidate name> — see <report path>
```

Do not start `spec-define` yourself and do not edit code.

## Done

You are done when the report exists in the spec dir, every candidate in it
passed Phase 3, and you have printed the handoff command (or reported that no
candidate survived).
