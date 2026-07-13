---
name: scratch-list
description: List or search saved research scratchpad threads (personal reference, not KB or project docs). Use when the user runs /clauderc:scratch-list or asks to find/resume/review a previously saved investigation thread.
argument-hint: [optional keyword or topic to filter by]
---

Read-only retrieval across the scratchpad scopes. Never treat any of this content as
knowledge-base material or project documentation — don't link it from MOCs, don't fold it
into a knowledge base, don't treat a local one as project docs, unless the user explicitly
asks you to extract something.

## Step 0 — Resolve the vault path from config

Before anything else, read `~/.claude/clauderc.private.json` (use the Read tool on the
absolute path, expanding `~` to the user's home directory).

- If the file exists and has a non-empty `scratch.vaultPath`, use that value as `<vaultPath>`
  below. The vault index is `<vaultPath>/_scratch/_index.md` and vault threads live in
  `<vaultPath>/_scratch/threads/`.
- If the file is missing, or has no `scratch.vaultPath` (or it's empty/still the placeholder
  `/absolute/path/to/your/notes/vault`), **skip the vault scope entirely** and operate in
  local-only mode. Note this to the user once, briefly: "No vault configured
  (`scratch.vaultPath` in `~/.claude/clauderc.private.json`) — showing local project threads
  only." Do not error out.

## Sources to check

- **Local** — `<cwd-project-root>/.claude/scratchpad/_index.md`, if it exists. Only relevant
  when the current working directory is inside a project.
- **Vault** — `<vaultPath>/_scratch/_index.md`, checked only when a vault path was resolved in
  Step 0. If the current working directory IS the vault path, there is no separate "local"
  scope — just use the vault one.

## No argument

1. Read whichever index file(s) apply per the rules above.
2. Print each as its own labeled table ("Local (this project)" / "Vault (general)"), as-is.

## With a keyword/topic argument

1. Read the applicable index file(s).
2. Filter rows whose title or hook match the keyword (case-insensitive substring match), across both sources.
3. If no matches, say so and show the full list(s) instead.
4. If exactly one match, read the corresponding `threads/<file>.md` (from whichever scope it came from) and:
   - Show its full content.
   - Surface the `resume:` frontmatter value prominently, and explain how to use it:
     - a filesystem path → tell the user to run `claude --resume` (or `--continue`) from that directory.
     - a chat URL → tell the user to open that URL.
     - a surface note → relay it as-is.
5. If multiple matches (within or across scopes), list them (scope, title, date, status) and ask which one to open.
