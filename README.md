# clauderc

A personal [Claude Code](https://claude.com/claude-code) plugin marketplace. Two plugins:

- **`clauderc`** — a small toolkit: a research-scratchpad browser and saver
  (`/clauderc:scratch-list`, `/clauderc:scratch-save`), a config-driven Jira ticket creator
  (`/clauderc:create-jira-ticket`), and a desktop notification hook.
- **`claude-spec-kit`** — spec-driven development: an interview-driven `spec-define`, a gated
  TDD `spec-implement` with an optional autonomous completion loop, and a read-only
  `spec-reviewer` conformance agent.

Everything here is generic and reusable. The author's own org/machine-specific values
(Jira board, team IDs, vault paths) live outside this repo in a single gitignored config file
— so the public toolkit and one person's daily-driver config are cleanly separated.

## Install

```
/plugin marketplace add jalesiyan-hadis/clauderc
/plugin install clauderc@clauderc
/plugin install claude-spec-kit@clauderc
```

Or, from a local checkout:

```
/plugin marketplace add ~/Codes/clauderc
```

Commands after install: `/clauderc:scratch-list`, `/clauderc:scratch-save`,
`/clauderc:create-jira-ticket`, `/claude-spec-kit:spec-define`, `/claude-spec-kit:spec-implement`.

## Configuration — `~/.claude/clauderc.private.json`

The `scratch-list`, `scratch-save`, and `create-jira-ticket` skills ship generic: they contain the *how*, and read
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

If the file is absent, the skills degrade gracefully: `scratch-list` falls back to local project
scope, `scratch-save` defaults to local scope, and `create-jira-ticket` stops with a message
telling you which values to set. Nothing crashes and no placeholder values are used.

## Updating

The plugins are **copied** into a version-keyed plugin cache on install
(`~/.claude/plugins/cache/clauderc/…`) — they are *not* run live from this checkout. So editing
files here does **not** change what Claude runs until you update the plugin:

```
/plugin update clauderc
/plugin update claude-spec-kit
```

Because the cache is keyed by version, the reliable way to force a refresh after changing plugin
prompts/hooks is to **bump `version`** in the plugin's `.claude-plugin/plugin.json` (keep
`.claude-plugin/marketplace.json` in sync), commit, then run `/plugin update`. If an update ever
doesn't take effect, remove and reinstall the plugin. Restart Claude Code to load the new version.

Your `~/.claude/clauderc.private.json` is separate config, not part of the plugin — edits to it
take effect on the next session start, no plugin update needed.

## License

MIT — see [LICENSE](LICENSE).
