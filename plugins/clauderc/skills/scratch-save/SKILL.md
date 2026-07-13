---
name: scratch-save
description: Save the current conversation/investigation as a scratchpad thread for later reference. Use when the user says "save this for further investigation" (or a clear paraphrase), or when invoked directly as /clauderc:scratch-save.
argument-hint: [optional title or short note]
---

Write-only capture into the scratchpad scopes (personal reference, not KB or project docs).
Never treat any of this content as knowledge-base material or project documentation — don't
link it from MOCs, don't fold it into a knowledge base, don't treat a local one as project
docs, unless the user explicitly asks you to extract something.

## Step 0 — Resolve the vault path from config

Before anything else, read `~/.claude/clauderc.private.json` (use the Read tool on the
absolute path, expanding `~` to the user's home directory).

- If the file exists and has a non-empty `scratch.vaultPath`, use that value as `<vaultPath>`
  below. The vault index is `<vaultPath>/_scratch/_index.md` and vault threads live in
  `<vaultPath>/_scratch/threads/`.
- If the file is missing, or has no `scratch.vaultPath` (or it's empty/still the placeholder
  `/absolute/path/to/your/notes/vault`), **skip the vault scope entirely** and operate in
  local-only mode. Note this to the user once, briefly: "No vault configured
  (`scratch.vaultPath` in `~/.claude/clauderc.private.json`) — saving to local project scope
  only." Do not error out.

## Step 1 — Classify scope

Decide where the thread belongs using: *"Would this thread make sense divorced from the
current codebase/repo — i.e. is it general research/ideas, or is it tied to this specific
project's code, config, or decisions?"*

- If a vault path was resolved in Step 0 **and** the current working directory equals it,
  everything is vault-scoped — skip classification (there's no separate local scope when
  you're already inside the vault).
- If vault scope is unavailable (Step 0 degraded to local-only), default straight to local
  scope — no need to ask.
- Otherwise:
  - **Tied to this project** (debugging notes, architecture decisions, TODOs specific to the
    repo you're in) → **local scope**.
  - **General/portable** (ideas, research, cross-project investigation) → **vault scope**.
  - If genuinely unclear, ask once rather than guessing.

## Step 2 — Write a structured summary

Not a raw transcript dump. Sections:
- `# <Title>` — short, descriptive (use the explicit-invocation argument as a hint if one was
  given — see "Explicit invocation" below)
- One-line description
- **Context** — what problem/question prompted this, why it came up
- **Key discussion points & decisions** — what was actually concluded, in prose/bullets
- **Open questions / next steps**

The result must be readable and useful to a person with zero prior context on this session,
and clean enough to paste into a future LLM session as context.

## Step 3 — Determine a resume pointer

- Claude CLI session → current working directory (resumable via `claude --resume`/`--continue`
  from that path).
- claude.ai / Cowork session → the chat URL, if available.
- Otherwise → note the surface/app name.

## Step 4 — Write the file

Kebab-case slug from the title; on filename collision append `-2`, `-3`, ...

- **Vault scope** → `<vaultPath>/_scratch/threads/<slug>-YYYY-MM-DD.md`
- **Local scope** → `<project-root>/.claude/scratchpad/threads/<slug>-YYYY-MM-DD.md` (create
  `threads/`, `notes/`, and `_index.md` in `.claude/scratchpad/` if they don't exist yet —
  mirror the vault's `_scratch/` layout exactly)

Frontmatter (same for both):

```yaml
---
status: active
scope: vault | local
resume: <cwd-path-or-chat-url-or-surface-note>
created: YYYY-MM-DD
---
```

## Step 5 — Append the index row

Append one row to the matching `_index.md` (vault's `_scratch/_index.md`, or the project's
`.claude/scratchpad/_index.md`):

`| [Title](threads/<file>.md) | <one-line hook> | active | YYYY-MM-DD | <resume pointer> |`

## Step 6 — Gitignore check (local scope only)

If local scope, check whether the project's `.gitignore` excludes `.claude/` or
`.claude/scratchpad/`. If not, mention this in the confirmation (don't edit `.gitignore`
yourself) so the user can decide whether to keep these notes out of version control.

## Step 7 — Confirm

Confirm where it was saved (file path) and which scope was used.

## Explicit invocation

If invoked directly with `$ARGUMENTS` (e.g. `/clauderc:scratch-save <title or note>`), treat
the argument as a title/topic hint feeding Step 2 — it doesn't skip Step 1's scope
classification (unless the CWD-is-vault shortcut in Step 1 applies).

## Isolation

This scratchpad (both vault and local) is personal reference only — it must never be treated
as knowledge-base source material. The same isolation applies to a project's local
`.claude/scratchpad/` — it is not code, not documentation, and other tooling in that repo
should not treat it as either.
