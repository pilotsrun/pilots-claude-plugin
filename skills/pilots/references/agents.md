# Connecting an agent to pilots

Two ways in, and the difference is what the agent can reach.

## Hosted: every host serves `/mcp`

```
pilot setup
```

One command for a machine: it detects the coding agents installed, shows the
plan, asks once, installs the skill where each loads skills from, registers
the hosted server in each one's config, and says whether the machine is
signed in (`pilot login` if not; setup opens no browser itself). Idempotent.
`--agent a,b` narrows it, `--skip-skills` and `--skip-mcp` leave a half out,
`--json` answers per agent.

One agent at a time:

```
pilot mcp install <harness>
```

`pilot mcp install --list` names the harnesses it knows: `claude-code`,
`codex`, `cursor`, `vscode`, `opencode`, `windsurf`, `gemini`, `zed`,
`copilot`, `droid`, `antigravity`, `pi`, `claude-desktop`, and `generic` for
anything else. Each writes the server entry into that agent's own config
file, in that agent's own shape, merged with what is already there.
`--project` writes the repository-scoped file instead of the user-wide one,
`--print` shows the entry without writing, and `pilot mcp remove <harness>`
takes it out again.

The entry carries no key where the agent signs in itself (every harness
above except VS Code, Windsurf, Claude Desktop and `generic`): the fleet's
401 starts a browser sign-in inside the agent, and the token it gets is the
agent's own, limited to what was granted on the consent screen. `--key`
writes the key from `pilot login` into the file instead, for a machine with
no browser.

Any MCP client can also be pointed at the URL by hand:

```json
{ "mcpServers": { "pilots": { "type": "http", "url": "https://api.pilotrun.app/mcp",
  "headers": { "Authorization": "Bearer $PILOT_API_KEY" } } } }
```

The endpoint is Streamable HTTP, stateless, on every host of the fleet. There
is no gateway and no session pinned to one machine, so a client that reconnects
to a different host loses nothing.

**The hosted tools** are everything that needs only the API: `create_machine`,
`list_machines`, `status`, `exec`, `exec_stream`, `logs`, `metrics`,
`checkpoint`, `restore`, `fork`, `preview_url`, `promote`, `destroy_machine`, `build_logs`,
`list_services`, `service`, `releases`, `rollback`, `delete_service`, `domains`, `volumes`,
`delete_volume`, `database`, `grant`, `grants`, `diagnose`, `init`, `docs`; the processes API,
`process_start`, `process_status`, `processes`, `process_output`,
`process_signal`, `process_remove`; and the files API, `file_read`,
`file_write`, `file_list`, `file_remove`. `process_start` takes no `env`, on
purpose: a value there would pass through the model, so a secret reaches a
process from `pilot process start --env`, which the user runs.

## Stdio: `pilot mcp`, and seven more tools

```
pilot mcp install <harness> --stdio
```

Runs the server as a local process, which adds the tools that read the agent's
own filesystem: `deploy` (a directory to a URL in one call), `build`, `plan`,
`generate_dockerfile`, `add_database` (`pilot add`: the password stays on this
computer and never appears in the answer), `push_file` and `pull_file`. Use this one when the agent
is working in a checkout. The hosted server's `init` tool says so too, so an
agent that finds `deploy` missing is told where it is rather than guessing.

## Logging in without a token

A client that dials the URL with no credential gets a 401 naming
`/.well-known/oauth-protected-resource`, which names the dashboard as the
authorization server. The client registers itself, opens a browser, and the
person approves it on a consent screen. What comes back is an ordinary pilots
token, so nothing on the fleet learns a second credential type and revoking it
on the tokens page stops it everywhere.

The consent screen offers two restrictions, and the fleet enforces both:

| Restriction | What it does |
| --- | --- |
| name prefix | Every machine and service this token names must start with it. The default is `mcp-`. |
| expiry | When the token stops authenticating, checked on every request. |

A refusal says which one was hit and what would work instead: a name outside
the prefix comes back with the prefixed name spelled out. There is no machine
count: no token, team or plan is held to one.

The same two limits are minted from the terminal with `pilot key create
<name> --prefix <p> --expires 7d`, and `pilot whoami` shows the current key's
prefix and expiry, which is how an agent reads what it was granted. `--scope
read` mints a key that sees the whole team and changes nothing.

## The Claude Code plugin

```
/plugin marketplace add pilotsrun/pilots-claude-plugin
/plugin install pilots@pilots
```

Nothing to export afterwards. The plugin uses the key `pilot login` stored; with
no stored key, `/mcp` offers the browser login described above. It does not
read `PILOT_API_KEY` (Claude Code hides it from a plugin); headless, run
`pilot login --token <key>`. `PILOT_API_URL` points it at a self-hosted fleet.

Adds the hosted server, this skill, `/pilots:status`, `/pilots:smoke`, and a
hook that asks before `destroy_machine`, `delete_service`, `delete_volume`,
`delete_checkpoint`, `restore`, `restore_volume`, `secret_remove`
and `rollback`, and before
an `exec` that ought to be checkpointed first (a migration, a package upgrade,
a recursive delete). Cursor, Codex, Copilot and Kiro read the portable Agent
Plugins v1 manifest in the same directory.

## SDKs

| Language | Install | Notes |
| --- | --- | --- |
| TypeScript | `npm i @pilots/sdk` | Zero dependencies. Also `@pilots/sdk/tanstack` and `@pilots/sdk/sprites-compat`. |
| Python | `pip install pilots-sdk` | Extras: `[adk]`, `[openai-agents]`, `[anthropic]`. Also `pilots.sprites_compat`. |
| Go | `go get github.com/pilotsrun/pilots/sdks/go` | One dependency. |
| Elixir | `{:pilots, "~> 0.1"}` | One dependency. HTTP through OTP's own `:httpc`. |

The first three keep their own copy of the wire types, and each has a test
that parses hostd's Go source and fails when the two disagree, so a field the
platform added cannot go missing from a client. The Elixir one returns plain
maps with the server's own keys, so its drift test checks the route table
instead: a path it calls that hostd no longer serves fails the build.

## Framework adapters

- **Google ADK**: `pilots.adk.PilotsPlugin` gives an agent seven tools, with a
  restore that refuses without an explicit confirmation.
- **OpenAI Agents SDK**: `pilots.openai_agents.PilotsSandboxClient`, an
  ephemeral machine per session or a named one that outlives it.
- **Claude Managed Agents**: `pilots.managed_agents.run_worker`, which runs
  each session's tool calls inside a machine you own.
- **TanStack AI**: `pilotsSandbox()` from `@pilots/sdk/tanstack`.

## Claude Code inside a machine

Two different things, and only one of them needs anything:

- **You, driving a machine from outside.** This is the normal case and needs
  no Anthropic credential anywhere: you are already signed in where you run,
  and `create_machine`, `exec` and the file tools are your hands in the
  sandbox. Do not install or sign in a second agent to do what you can do.
- **An agent living inside the machine** -- working on its own there, with
  every permission, because there is nothing of the user's to wreck. That one
  has to be signed in, and a machine is a different computer.

For the second, tell the user to run this themselves, in their own terminal:

```
pilot claude <machine>
```

The first run sets the credential up once per computer (on a subscription it
runs `claude setup-token` and reads the token off its screen); every run
after that, on any machine, opens Claude Code already signed in. It installs
Claude Code in the machine the first time.

It is a user-only command, and the reason is the same as `pilot secret set`:
the credential is the user's and must not pass through a model. So never put
an Anthropic key or token in an `exec` call's env -- it would travel through
your own context -- and never ask the user to log in inside the machine: that
writes the login onto its disk, where every checkpoint and fork carries it.
`pilot claude` hands the credential to one process and writes it to no file.

Two things worth saying to the user when they apply: a machine under 1024 MiB
is tight for Claude Code (`pilot machine resize <machine> --mem 2048`), and
while Claude Code is running its credential is in the machine's memory, so
they should exit it before forking the machine for somebody else.

## The editor

Two editors open a machine as a folder, on the same address,
`pilot://<name>/<path>`:

- **VS Code**: the extension mounts a machine as a workspace folder and opens a
  shell in it.
- **Neovim**: the plugin opens the same address with `:e pilot://<name>/` or
  `:PilotsOpen <name>`, and `:PilotsTerminal <name>` is the shell. A path that
  does not exist yet opens as a new file, and `:w` creates it.

Every read and write in both is a command over the exec route, so there is
nothing to install in the guest and no port to open. A write to a suspended
machine wakes it.
