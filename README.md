# clauderc

A personal [Claude Code](https://claude.com/claude-code) plugin marketplace, built the native
way — no dotfile symlink farms, no hand-rolled command prefixes. Two plugins:

- **`clauderc`** — a small toolkit: a research-scratchpad browser (`/clauderc:scratch`), a
  config-driven Jira ticket creator (`/clauderc:create-jira-ticket`), and a desktop
  notification hook.
- **`claude-spec-kit`** — spec-driven development: an interview-driven `spec-define`, a gated
  TDD `spec-implement` with an optional autonomous completion loop, and a read-only
  `spec-reviewer` conformance agent.

Everything here is generic and reusable. The author's own org/machine-specific values
(Jira board, team IDs, vault paths) live outside this repo in a single gitignored config file
— so the public toolkit and one person's daily-driver config are cleanly separated.

## Install

```
/plugin marketplace add hadisjalesiyan/clauderc
/plugin install clauderc@clauderc
/plugin install claude-spec-kit@clauderc
```

Or, from a local checkout:

```
/plugin marketplace add ~/Codes/clauderc
```

Commands after install: `/clauderc:scratch`, `/clauderc:create-jira-ticket`,
`/claude-spec-kit:spec-define`, `/claude-spec-kit:spec-implement`.

## Configuration — `~/.claude/clauderc.private.json`

The `scratch` and `create-jira-ticket` skills ship generic: they contain the *how*, and read
the *values* from a user-level config file at `~/.claude/clauderc.private.json`. This file is
org/user-wide (Jira board, vault path), deliberately unlike spec-kit's per-project
`.claude/spec-workflow.json`.

Copy [`plugins/clauderc/clauderc.config.example.json`](plugins/clauderc/clauderc.config.example.json)
to `~/.claude/clauderc.private.json` and fill in your values:

```json
{
  "jira": {
    "cloudId": "your-atlassian-cloud-id",
    "projectKey": "ABC",
    "site": "https://your-org.atlassian.net",
    "teams": { "TeamName": "team-uuid" },
    "epics": { "internallyFoundBugs": "ABC-1234" },
    "epicGuideUrl": "https://www.notion.so/...",
    "fields": { "sprint": "customfield_10020", "team": "customfield_10001", "epic": "customfield_10014" }
  },
  "scratch": { "vaultPath": "/absolute/path/to/your/notes/vault" },
  "ticketPrefix": "ABC"
}
```

If the file is absent, the skills degrade gracefully: `scratch` falls back to local project
scope, and `create-jira-ticket` stops with a message telling you which values to set. Nothing
crashes and no placeholder values are used.

## License

MIT — see [LICENSE](LICENSE).
