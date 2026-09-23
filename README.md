# pilots for Claude Code

Sandboxes and production services on Firecracker microVMs, from Claude Code.

[pilots](https://pilots.run) runs both on one primitive: a **machine** is a
microVM with a permanent https URL that suspends when idle, costs nothing
asleep, and wakes on the next request or exec. A sandbox and a production
service are the same machine with different lifecycle knobs.

## Install

```
/plugin marketplace add pilotsrun/pilots-claude-plugin
/plugin install pilots@pilots
```

Then `/pilots:status` to check the result.

## What you get

- **The MCP toolset** — create machines, exec, checkpoint and restore, deploy,
  promote, logs, metrics, volumes, domains, secrets. Served over HTTP from the
  fleet, so there is nothing to run locally.
- **A guard** (`hooks/hooks.json` + `scripts/guard.py`) that asks before
  `destroy_machine`, `restore` and `rollback`, and before an `exec` that should
  be checkpointed first.
- **Skills** — `pilots` loads itself when the task is about pilots; `/pilots:status`
  and `/pilots:smoke` are yours to invoke.

## Credentials

Nothing here carries one. `.mcp.json` has no static token: its `headersHelper`,
`scripts/mcp-headers.py`, hands Claude Code the key that `pilot login` stored in
`~/.config/pilots/credentials`, and only when that file is for the fleet being
dialled.

With no stored key it sends no header at all — which is what lets the fleet's
401 start a browser login from `/mcp`. A machine with no `python3` behaves the
same way. Headless, `pilot login --token <key>` writes the file.

`PILOT_API_URL` points the plugin at a self-hosted fleet.

## Other agents

The same skills and MCP server work anywhere. Point any MCP client at
`https://api.pilotrun.app/mcp` with `Authorization: Bearer <key>`, or run
`pilot mcp install <harness>` — `pilot mcp install --list` names the harnesses
it knows.

## Source

This repository is generated. The skills and manifests are maintained in the
pilots repository and mirrored here; `pilot init` copies the same skill into a
project's `.agents/skills/pilots/`, and the MCP servers serve the same pages
through the `docs` tool, so every surface ships one set of words.

Issues and questions: <https://pilots.run/agents>

Apache-2.0.
