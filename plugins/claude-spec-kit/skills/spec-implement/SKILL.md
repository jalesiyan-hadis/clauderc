---
name: spec-implement
description: Turn a spec into a reviewed plan and approved test scenarios, then
  autonomously implement with TDD until the full suite is green with no
  regressions and new tests are added. Use when given a spec/analysis doc to
  implement end-to-end.
argument-hint: "[path-to-spec.md]"
---

# Spec → Plan → Autonomous Implementation

You are running a gated workflow with exactly ONE human checkpoint: approval
of the plan AND the test scenarios. Do not pass it without explicit user
approval. After approval, implement autonomously: commit locally, but NEVER
push or open a PR/MR — that is the developer's manual step.

If `$ARGUMENTS` is empty, ask the user for the spec path before starting.

## Phase 0 — Project config

Read `.claude/spec-workflow.json` to learn how this project runs tests, lints,
and formats commits. The keys you rely on:

- `test_fast` — fast test command (the autonomous loop's deterministic gate).
- `test_full` — full/coverage regression command.
- `lint` — lint/format command run before committing.
- `commit_prefix` — commit type prefix (default `feat`).
- `ticket_regex` — to derive the ticket from the branch for commit scopes.

If the file is missing, this is first use: run the bundled detector
(`hooks/_config.py` — `example_config(project_dir)`) to propose a config from the
project's stack, show it, let the user confirm/tweak the commands, and write
`.claude/spec-workflow.json`. **Without a runnable `test_fast`, the autonomous
loop safe-disarms** (it will not gate), so do not skip this. Throughout this
skill, wherever a command appears as `{test_fast}`, `{test_full}`, or `{lint}`,
substitute the resolved config value.

Derive the commit message format: `{commit_prefix}({ticket}): <desc>` when a
ticket matches the branch, else `{commit_prefix}: <desc>` (Conventional Commits).
Choose the **type from the commit's actual content**: a test-only commit is
`test`, a docs-only commit is `docs`, etc. `{commit_prefix}` (default `feat`) is
the type for the *implementation* commit — not a fixed prefix for every checkpoint.

## Phase 1 — Plan + test scenarios (HUMAN-GATED)

Enter plan mode (EnterPlanMode) so this phase is read-only and tool-enforced.

1. Read the spec at `$ARGUMENTS`. Read the files it references to ground the
   plan in real code — lazily, only what each decision needs, not everything
   up front.
2. Verify the spec's assumptions against the actual code. Quote the current
   signature of any helper the spec claims is reusable. Flag every mismatch
   between spec and reality, and every outdated or ambiguous item.
3. **Challenge the spec's proposed implementation — don't inherit it.** The
   spec describes the *problem* authoritatively, but its suggested *approach*
   is just one option; validate the approach, not only the assumptions. Before
   accepting any new method, traversal, pass, or call-site, find the **most
   local, minimal fix**:
   - Ask "where is this data already in hand?" Fix at the site that already
     holds the relevant state instead of a new pass that re-discovers it. A
     recursive re-walk is a red flag when existing code already holds the
     parent/values.
   - Prefer **widening or correcting an existing invariant** (e.g. a too-narrow
     loop bound) over adding a new enforcement step or normalization stage.
   - A one-line change at an existing write site beats a new method + new call
     site + extra tests. Plan the smallest change that fully fixes the bug.
   If the spec's approach is heavier than the minimal fix, plan the minimal fix
   and note in the plan why it supersedes the spec's suggestion.
4. If anything is ambiguous, ASK the user now — this is the only phase where
   you ask questions. Cadence:
   - If an answer determines your *next* question (true branching), ask it
     alone, wait, then continue.
   - Batch independent, closed confirmations into one `AskUserQuestion` call
     (max ~3-4 questions), each with your recommended answer.
   - For open design questions you can attach a recommendation to, prefer one
     per turn so the user ratifies rather than drafting from scratch.
5. Produce a plan covering:
   - Files created/modified, with per-file changes.
   - New function signatures and the data flow between them.
   - How regressions are checked and which existing suites run.
6. Produce explicit **test scenarios** for the developer to approve: for each
   behavior, the case name, the input/precondition, and the expected outcome
   (including edge cases and failure paths). These are the contract the tests
   will encode — the developer must sign off on them, not just the plan.
7. Present the plan and the test scenarios together via ExitPlanMode. Include
   the literal line `<!-- spec-implement-loop -->` at the END of the plan text —
   approving the plan arms the autonomous completion loop (a Stop hook), so this
   marker MUST be present. Wait for explicit approval. If the user gives notes,
   address them and re-present (keep the marker). Repeat until the user approves
   both the plan and the scenarios.

## Phase 2 — Failing tests (after approval)

8. Write tests first for every approved scenario. Encode exactly the approved
   cases — no extra scope. Tests must check **behavior**, not structure, so a
   refactor that keeps behavior never breaks them:
   - **Assert observable outcomes through the interface** callers use. Never
     assert call counts, call order, or private state, and never query a side
     channel (e.g. the database) to verify what the interface itself can return.
   - **Expected values come from the spec or a worked literal** — never
     recomputed the way the code computes them. A test that re-derives its
     expected value repeats the implementation's logic and passes by
     construction. (Exception: Refactor characterisation tests, which
     intentionally lock in current output.)
   - **Mock only at boundaries you don't own** — external APIs, the clock,
     randomness, the network. Do not mock your own modules or internal
     collaborators, and never the thing under test. Prefer a real stand-in
     (temp dir, in-memory DB) over a mock where one exists.
   - **One behavior per test**; the test name says what behavior, not how.
   - No stubbed-out imaginary code. Traceability (AC ids, ticket ids, scenario
     numbers) belongs in the plan/spec test-mapping table and in descriptive
     test names — **never in code comments or docstrings**. Keep comments short
     and useful: explain behavior/intent ("only same-source groups are reused"),
     not spec references.
9. Run them and confirm they ALL fail for the right reason (missing behavior,
   not import/syntax errors): `{test_fast}` scoped to the new test paths.
10. Run the linter, then commit the failing tests as a checkpoint:
   `{lint}`
   `test(<ticket>): add failing tests for <feature>` (use the branch's ticket
   if any). This checkpoint is test-only, so the type is `test`, not
   `{commit_prefix}`.

## Phase 3 — Implement to green (Red → Green → Refactor)

11. Implement until all tests pass. Do NOT modify the committed tests (the
    only exception is step 13).
    Inner loop: `{test_fast}`
    **Stuck-loop escalation:** if the SAME test(s) stay red after ~3 honest fix
    attempts and you are not converging, do not keep grinding. If a
    second-opinion / different-model rescue tool is available in this
    environment (e.g. a codex-style rescue plugin), delegate a fresh root-cause
    pass to it — describe the failing test, the relevant files, and what you have
    already tried, then evaluate its diagnosis before applying anything.
    Otherwise, step back and re-examine your assumptions from scratch, or ask the
    user. You remain responsible for the fix and must not commit changes you do
    not understand.
12. REFACTOR only after green, and keep it small. In-loop refactoring is
    limited to:
    - removing duplication introduced **by this change**;
    - renaming to match the domain terms used in the spec (or `GLOSSARY.md`,
      if the project has one);
    - deleting speculative generality — parameters, hooks, or options the
      approved scenarios don't need.
    **Simplicity rule:** a refactor must not add files, public symbols,
    abstraction layers, or configuration knobs unless the new thing pulls
    together complexity that currently exists in at least two places. "Will
    need it later" never counts. Deeper means *fewer things to know*: turning
    one function into a class plus an interface plus a factory makes the
    interface bigger, not deeper.
    Anything structural (moving code between modules, changing the interface
    tests go through) is out of scope here — note it for the final report under
    "Architecture follow-ups" instead of doing it. Re-run `{test_fast}` to
    confirm it stays green. Do not touch the committed tests.
13. **Mutation smoke check.** Pick the core assertion of one or two of the new
    tests. In the implementation, flip the condition or operator that assertion
    depends on (with Edit, not git), run `{test_fast}` scoped to the new tests,
    confirm at least one fails, then revert the mutation with Edit and confirm
    green again. Revert in the same turn — never end a turn with a mutation in
    place.
    If nothing fails, the test is tautological. This is the ONLY case where a
    committed test may change: strengthen that assertion so it fails on the
    mutation (the scenario and its expected outcome stay exactly as approved),
    then commit it on its own: `test(<ticket>): strengthen assertions`. Never
    add new tests or test infrastructure here — strengthen, don't multiply.
14. If implementation reveals the approved plan or scenarios were wrong, STOP.
    A material deviation — new/removed files, changed public signatures, or any
    dropped/added requirement or scenario — requires re-gating: return to plan
    mode (Phase 1) and get re-approval. Trivial local refactors that don't
    change the contract do not.
15. Run the FULL suite as the regression gate. Paste the exact command and full
    output: `{test_full}`
16. Spawn the **`spec-reviewer`** subagent (Agent tool). It is read-only and
    encodes the gap contract itself. Give it `APPROVED_PLAN` (the approved plan),
    `APPROVED_SCENARIOS` (the approved test scenarios), and `DIFF` (the working
    diff or base ref). It reports ONLY gaps affecting correctness or stated
    requirements, one per line as `GAP: <file:line> — <what's missing or out of
    scope>`, or the single line `NO ISSUES` when clean.
    Fix every reported gap and re-review until it returns `NO ISSUES`.
17. Run the linter and commit the implementation:
    `{lint}`
    `{commit_prefix}(<ticket>): implement <feature>`

## Done

Report done ONLY when: implementation matches the approved plan and scenarios,
the full suite is green with no regressions, new tests exist and pass, the
step-12 refactor criteria were applied, the mutation smoke check (step 13) was
performed, and the reviewer returned `NO ISSUES`. Show the `{test_full}`
command and its full output as evidence — never assert success without it. Do
NOT push or open a PR/MR; leave that to the developer.

The final report also includes:
- One line: `Concepts added / removed: +N / −M (files, public symbols,
  layers)`. If N > M for a Bug, or N > M for a Feature/Refactor without a
  justification in the approved plan, flag it explicitly. This is a visibility
  measure, not a gate.
- An "Architecture follow-ups" list, if step 12 deferred anything structural.

As your FINAL action, create the marker file `.claude/.spec-loop/complete` (its
contents don't matter). This signals the completion loop that the workflow is
finished. The loop will not release until tests are green AND this marker
exists, so write it only when every Done condition above truly holds.
