---
name: create-jira-ticket
description: Create a Jira ticket following team conventions. Use when the user asks to create, log, or file a bug, task, or ticket in Jira.
user-invocable: true
allowed-tools:
  - mcp__claude_ai_Atlassian__searchJiraIssuesUsingJql
  - mcp__claude_ai_Atlassian__createJiraIssue
  - mcp__claude_ai_Atlassian__editJiraIssue
  - mcp__claude_ai_Atlassian__createIssueLink
  - mcp__claude_ai_Atlassian__getIssueLinkTypes
  - mcp__claude_ai_Notion__notion-fetch
---

# /create-jira-ticket

Creates a Jira ticket on your team's board following team conventions.
Always draft first, wait for user approval, then create.

Arguments: `$ARGUMENTS` (optional pre-filled title or context)

---

## Step 0 — Load configuration

Before anything else, read `~/.claude/clauderc.private.json` (use the Read tool on the absolute
path, expanding `~` to the user's home directory). This file holds all org-specific values.

**If the file is missing, unreadable, or `jira.cloudId`/`jira.projectKey` are absent or still
the placeholder values** (`00000000-...`, `"ABC"`), **stop immediately** — do not attempt to
create anything. Tell the user:

> No Jira config found. Copy `clauderc.config.example.json` (shipped in the `clauderc` plugin) to
> `~/.claude/clauderc.private.json` and fill in your `jira` values: `cloudId`, `projectKey`,
> `site`, `teams`, `epics`, `epicGuideUrl`, and `fields`. Then run this again.

Otherwise, bind these values for the rest of the workflow (fall back to the standard Jira
custom-field IDs shown if `jira.fields.*` is not set):

- `CLOUD_ID`     ← `jira.cloudId`
- `PROJECT_KEY`  ← `jira.projectKey` (also used as the ticket prefix; `ticketPrefix` is an alias)
- `SITE`         ← `jira.site`
- `TEAMS`        ← `jira.teams` (map of team name → UUID)
- `BUGS_EPIC`    ← `jira.epics.internallyFoundBugs`
- `EPIC_GUIDE`   ← `jira.epicGuideUrl`
- `F_SPRINT`     ← `jira.fields.sprint` (default `customfield_10020`)
- `F_TEAM`       ← `jira.fields.team` (default `customfield_10001`)
- `F_EPIC`       ← `jira.fields.epic` (default `customfield_10014`)

Everywhere below that a value appears in `<ANGLE_BRACKETS_CAPS>`, substitute the bound value.

---

## Step 1 — Gather information from the user

If the user has not already provided the following, ask before proceeding:

- **Team** (one of the keys in `TEAMS`, or other)
- **Component** (e.g. a subsystem name)
- **Issue type** (Task / Bug / Story)
- All content needed for the description (see Step 3)
- **Priority** — ask: "What priority should this ticket have? (Low / Medium / High / Critical)"
- **Sprint** — ask: "Should this be added to the current sprint, the next sprint, or no sprint?"
- **Technical hints** — ask: "Do you want to include technical hints for the development team? (Yes / No)" — if Yes, follow up: "Please provide the technical details (reproduction steps, root cause pointers, relevant file paths, API payloads, etc.)"
- **Linked tickets** — ask: "Should this ticket be linked to any existing tickets? (Yes / No)" — if Yes, follow up: "Please provide the ticket keys (e.g. <PROJECT_KEY>-1234, <PROJECT_KEY>-5678)"

---

## Step 2 — Look up epic and sprint in parallel

Run all lookups at the same time:

**Epic:** Fetch the Notion page at `<EPIC_GUIDE>` to decide which epic applies.

Mapping:
- Found by product/engineering, customer-facing impact → **`<BUGS_EPIC>`** (Internally Found Bugs)
- Reported by customer / CS / Sales → Maintenance bucket (search for it)
- No customer-facing impact (refactor, infra, alerts) → Technical Debt bucket (search for it)
- Belongs to an open feature epic → use that epic

**Sprint ID:**

- If user chose **next sprint**, run:
  ```
  project = <PROJECT_KEY> AND sprint in futureSprints() ORDER BY created DESC
  ```
  Read `<F_SPRINT>[0].id` from the first result.

- If user chose **current sprint**, run:
  ```
  project = <PROJECT_KEY> AND sprint in openSprints() ORDER BY created DESC
  ```
  Read `<F_SPRINT>[0].id` from the first result.

- If user chose **no sprint**, skip the sprint lookup.

---

## Step 3 — Draft the ticket

Compose the ticket using this exact structure:

### Title
Must start with `[E]` followed by a clear, non-technical description a project manager can understand.
Example: `[E] Online Extraction API: Reliability and Documentation Issues`

### Description body

Write a high-level explanation of the problem or goal from the **user or business perspective**. Focus on what value is delivered or what problem is solved. Avoid code, file names, and implementation details. If multiple sub-items exist, use a numbered or bulleted list.

```
<High-level, non-technical explanation of the problem or goal.
Focus on user/business perspective and the value delivered or problem solved.
Avoid code references, file names, and implementation details.
Use a numbered or bulleted list if there are multiple sub-items.>

## Acceptance Criteria
- [ ] <Expected visible or business outcome 1>
- [ ] <Expected visible or business outcome 2>
- [ ] ...

## Technical Hints
<Only include this section if the user requested it and provided content.
Include the user-supplied technical context verbatim or lightly structured:
reproduction steps, root cause pointers, file paths, API payloads, etc.
Omit this entire section if technical hints were not requested.>
```

Rules:
- **Description body**: must be understandable by non-technical stakeholders — no code, no file paths, no system internals
- **Acceptance Criteria**: each item must be a user-observable or business-observable outcome that a product owner can verify without reading code; no steps, tool names, or technical jargon; use checkboxes (`- [ ]`), one line per item, no sub-bullets
- **Technical Hints**: include only if the user said Yes and provided content; this section is the right place for all technical depth — reproduction steps, root cause analysis, file paths, API payloads, etc.; omit entirely otherwise

### Draft metadata summary (display to user)
Also show:
- **Priority**: `<Low|Medium|High|Critical>`
- **Sprint**: `<current sprint name | next sprint name | none>`
- **Linked tickets**: `<PROJECT_KEY-XXXX, PROJECT_KEY-YYYY | none>`

---

## Step 4 — Show draft to user and wait for approval

Display the full draft (title + description + metadata summary) in a readable format.
Do **not** create the ticket yet.
Ask: "Does this look good, or would you like any changes before I create it?"

---

## Step 5 — Create the ticket (only after approval)

### 5a — Create the issue

Call `createJiraIssue` with:
```json
{
  "cloudId": "<CLOUD_ID>",
  "projectKey": "<PROJECT_KEY>",
  "issueTypeName": "<Task|Bug|Story>",
  "summary": "<title>",
  "contentFormat": "markdown",
  "description": "<full description markdown>",
  "additional_fields": {
    "<F_SPRINT>": <sprint_id_integer>,
    "<F_EPIC>": "<epic_key>",
    "components": [{"name": "<component>"}],
    "priority": {"name": "<Low|Medium|High|Critical>"}
  }
}
```

Omit the `<F_SPRINT>` field entirely if the user chose no sprint.

### 5b — Set the team field

Immediately after creation, call `editJiraIssue` to set the team:
```json
{
  "cloudId": "<CLOUD_ID>",
  "issueIdOrKey": "<new_issue_key>",
  "fields": {
    "<F_TEAM>": "<team_uuid>"
  }
}
```

The `<team_uuid>` is `TEAMS[<chosen team name>]` from config.

> **Why two calls?** The Jira API rejects the team field if included in the create payload. It must be set separately via edit.

### 5c — Link tickets (only if user provided linked ticket keys)

1. Call `getIssueLinkTypes` once to confirm the "Relates" link type is available.
2. For each linked ticket key, call `createIssueLink`:
```json
{
  "cloudId": "<CLOUD_ID>",
  "inwardIssue": "<new_issue_key>",
  "outwardIssue": "<PROJECT_KEY-XXXX>",
  "linkTypeName": "Relates"
}
```
Run all link calls in parallel after step 5b completes.

---

## Step 6 — Confirm

Report the ticket key and URL:
`<SITE>/browse/<KEY>`

Also confirm:
- Priority set: `<Low|Medium|High|Critical>`
- Sprint: `<assigned sprint name | none>`
- Linked tickets: `<PROJECT_KEY-XXXX, PROJECT_KEY-YYYY | none>`
