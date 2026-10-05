---
name: review-assist
description: Prepare a guided review of a GitLab merge request for the developer — intent from the Jira ticket and MR description, a change map with a reading order, /code-review and standards-reviewer findings, intent-vs-implementation gaps, diagrams where they help, and a "not checked by AI" list — as a local HTML file, then walk through each finding with the developer. Never posts anything to GitLab or Jira. Every review is logged under ~/.claude/retro_review/.
argument-hint: "<gitlab-mr-url>"
disable-model-invocation: true
---

# Review Assist — prepare a GitLab MR review, the developer decides

You prepare a review so the developer reviews faster **and still understands
what changed**. The value is comprehension: intent, reading order, diagrams, an
honest "not checked" list. Bug finding is delegated to `/code-review`. You
prepare; the developer decides every finding.

MR: `$ARGUMENTS`

## Hard rules

- **Never post anything.** No GitLab comments, approvals, labels, or
  discussions; no Jira comments, edits, or transitions. GitLab (`glab`) and
  Jira are read-only. Draft comments go into the HTML and the terminal for the
  developer to copy.
- **Never pass `--comment` or `--fix`** to `/code-review`. Without `--comment`
  it only reports; GitLab MRs are exactly what `--comment` would post to.
- **Never edit files in the review worktree.** It is the code under review.
- **Never touch the developer's current branch.** All checkout work happens in
  a separate `git worktree`.
- If a step fails or is skipped, say so and list it under **not checked by AI**
  in the HTML. Never paper over a missing step.

## Step 1 — Resolve the MR

1. Parse `$ARGUMENTS`: host, project path, MR iid
   (`https://<host>/<group>/<project>/-/merge_requests/<iid>`). No usable URL →
   ask for it and stop.
2. `glab mr view <url> -F json` for title, description, source and target
   branch, author, `diff_refs` (base / head SHAs), web URL. `glab` missing or
   not authenticated → tell the developer (`glab auth login`) and stop.
3. Check that this session's repo has a remote whose URL matches the project
   path (`git remote -v`). If none matches, stop and ask the developer to start
   the session in the right checkout. Use that remote's name below (shown here
   as `origin`).
4. Read the review config:
   `python3 "${CLAUDE_PLUGIN_ROOT}/hooks/_config.py" --review --project .`
   (`risk_paths`, `skim_paths`, `review_guide`, `review_guide_found`,
   `retro_root`). It works even in a repo the spec-implement loop would
   safe-disarm.

## Step 2 — Retro dir and worktree

1. `RETRO = <retro_root>/<repo>/<iid>-<YYYY-MM-DD>/` (`<repo>` = last segment
   of the project path, today's date). Create it. If it already exists from an
   earlier review today, reuse it and say so.
2. Write the session marker so the transcript is saved at session end:
   `~/.claude/retro_review/.active/${CLAUDE_SESSION_ID}.json` containing
   `{"retro_dir": "<RETRO absolute path>"}` (this path is fixed, even when
   `retro_root` is overridden). If `${CLAUDE_SESSION_ID}` above was not
   replaced by an id, skip the marker and note "transcript not saved" in the
   HTML header.
3. Fetch and check out without touching the current branch:
   ```
   git fetch origin merge-requests/<iid>/head:review/mr-<iid>
   git fetch origin <target>
   git worktree add <RETRO>/worktree review/mr-<iid>
   ```
   If `review/mr-<iid>` already exists, update it with
   `git fetch origin +merge-requests/<iid>/head:review/mr-<iid>` only when it
   is not checked out anywhere; otherwise reuse the existing worktree.
4. `RANGE = origin/<target>...review/mr-<iid>`. Always pass this range
   explicitly; a bare branch name's base is undefined for `/code-review`.
   Every later file read, `_config.py` call (`--project <RETRO>/worktree`),
   and diff uses the worktree or the range.

This review log is **mandatory and automatic** (it is how the workflow is
improved later), so the global "ask before saving the discussion" prompt does
not apply to the review itself.

## Step 3 — Intent

1. Find the Jira key: the repo's `ticket_regex` (from
   `.claude/spec-workflow.json` if set, else `[A-Z]{2,}-\d+`) on the MR title,
   then the source branch.
2. Found → read the ticket through the Atlassian MCP (read-only: get the
   issue; never comment, edit, or transition). Not found, or the MCP is
   unavailable → say so and use the MR description only.
3. Write **2–3 sentences of intent**: what the change is meant to achieve and
   for whom, from the ticket and the description. Keep the ticket lines you
   relied on; step 6 points at them.

## Step 4 — Change map and reading order

1. `git diff -M -C --stat <RANGE>` and `git diff -M -C --color-moved=zebra -w <RANGE>`
   (read the second in chunks; don't dump it all into context at once).
2. Group files into **logical units** (one concept each) and order the groups
   by dependency: schema → logic → call sites → UI → tests.
3. Tag each group:
   - 🔴 **must read** — matches a `risk_paths` glob, or changes behaviour;
   - 🟡 **careful** — non-trivial logic;
   - 🟢 **skim** — matches a `skim_paths` glob, pure renames/moves, or
     whitespace-only.
   One line per group saying what it does and why it is in that slot.

## Step 5 — Reviews, in parallel

Start both in one message:

- **Correctness:** invoke `/code-review <RANGE>` (the range only; never
  `--comment`, never `--fix`). It runs as a background forked subagent and
  returns prose. The `review/mr-<iid>` branch is shared by every worktree of
  this repo, so the range resolves from this session's checkout; if its
  findings turn out to cite the current checkout's files rather than the MR's,
  note that under "not checked by AI".
- **Standards and tests:** spawn the `standards-reviewer` agent with
  `DIFF` = `<RANGE>`, the worktree path as the place to read files, and
  `STANDARDS` = the full output of
  `python3 "${CLAUDE_PLUGIN_ROOT}/hooks/_config.py" --standards --project <RETRO>/worktree`.
  If `review_guide_found` is true, also pass `REVIEW_GUIDE` = the contents of
  `<RETRO>/worktree/<review_guide>`. `/code-review` reads only `CLAUDE.md`, so
  the review guide reaches the review through this agent alone.

While they run, do step 6.

## Step 6 — Intent vs implementation

Compare the intent (step 3) with the change map (step 4):

- **Stated but missing** — the ticket or description asks for it; the diff
  doesn't do it.
- **Done but unstated** — the diff does it; nothing asked for it.

Each gap must cite **a ticket or description line** and a **`file:line`** (or
"absent" for a missing piece). A gap that can't cite both is dropped.

## Step 7 — Merge findings

1. Parse `/code-review`'s prose into `file:line` + summary + failure scenario.
   If parsing fails, keep its output as-is under its own heading in the HTML
   and say so.
2. Parse `SMELL:` lines from `standards-reviewer`.
3. Deduplicate by `file:line`, rank by severity (correctness failures and
   `[standard]` first, then intent gaps, then `[baseline]`, then
   `[judgement]`), and keep each finding's **source tag** (`code-review` /
   `standards` / `intent`) and its failure scenario or rule id.

## Step 8 — Diagrams, only where they help

Add a diagram only when it explains something the diff makes hard to see:

- a new flow → sequence or data-flow diagram;
- a schema or migration change → ER diff (before/after);
- a changed state machine → state diagram.

None for small or mechanical changes. Use Mermaid. Every node must name a real
module, table, or state from the diff.

## Step 9 — Write `review.html`

Write `<RETRO>/review.html`: one self-contained file, inline CSS, readable in
light and dark mode, Mermaid loaded from
`https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js` only if a diagram
exists (the file then needs network to render diagrams). Sections, in order:

1. **Header** — MR title and link, author, ticket (or "none found"), source →
   target, base/head SHAs, review guide used (path, or "none"), transcript
   saved or not.
2. **Intent**.
3. **Intent gaps**.
4. **Change map + reading order** — the tagged groups from step 4, each with
   its files.
5. **Diagrams** (omit the section when there are none).
6. **Findings** — each with source tag, `file:line`, summary, failure scenario
   or rule id, and a decision slot.
7. **Test assessment** — test-rule findings plus behaviours the tests don't
   cover (from the intent and the change map).
8. **Not checked by AI** — always: security, runtime performance, UX, business
   correctness; plus anything a step skipped or couldn't do. Point at the 🔴
   groups as the human's must-read.

Open it (`open <RETRO>/review.html` on macOS, `xdg-open` elsewhere) and give
the developer the path.

## Step 10 — Walk through with the developer

Go through the findings in ranked order, one at a time (batch 🟢-level or
`[judgement]` ones if there are many). For each, the developer chooses:

- **accept** → becomes a **draft comment**: `file:line` plus the comment text,
  written for a human reviewer to post;
- **reject** → record a short reason;
- **edit** → take their wording, then it's a draft comment.

Update `review.html` with each decision and a **Draft comments** section, and
print the draft comments in the terminal for copying. **Never post them.**

## Step 11 — Close

1. Ask once (optional): "What did you have to dig into yourself?"
2. Write `<RETRO>/retro.md`:
   ```markdown
   ---
   repo: <project path>
   mr: <iid>
   ticket: <key or none>
   date: <YYYY-MM-DD>
   findings_total: <n>
   accepted: <n>
   rejected: <n>
   edited: <n>
   by_source:
     code-review: {total: <n>, accepted: <n>, rejected: <n>, edited: <n>}
     standards: {total: <n>, accepted: <n>, rejected: <n>, edited: <n>}
     intent: {total: <n>, accepted: <n>, rejected: <n>, edited: <n>}
   ---
   ```
   Body: the intent; each finding with its source, decision and reason; the
   intent gaps; "What I had to dig into myself" (the answer, or "not
   answered").
3. Ask whether to remove the worktree (default **yes**). On yes:
   `git worktree remove <RETRO>/worktree` then `git branch -D review/mr-<iid>`.
   `review.html` and `retro.md` stay.
4. Tell the developer the session transcript is copied to
   `<RETRO>/transcript.jsonl` when the session ends (or that it won't be, if
   the marker was skipped).
