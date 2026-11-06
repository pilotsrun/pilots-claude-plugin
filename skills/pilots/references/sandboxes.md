# Sandboxes

## What this covers

A throwaway environment to run commands in: creating one, running commands, running detached processes, moving files, reading its console, capturing and restoring it. Not covered: turning one into a durable service (promote.md), deploying an app (deploy.md).

## The command to copy

    pilot machine create scratch
    pilot machine exec scratch -- ls /

MCP: `create_machine` with `{ "name": "scratch" }`, then `exec` with `{ "machine": "scratch", "cmd": "ls /" }`.

## What happens

1. A create is a RESTORE from a template, not a boot, so it is fast and the number is independent of the machine's size.
2. The machine gets a permanent URL derived from its name. The URL survives suspend, wake, checkpoint, restore and promote.
3. It suspends 2 seconds after its last request, exec or stream byte (`idle_timeout`, 0.5 s to an hour): snapshotted to its host's disk with its process ended, so a sandbox nobody is using holds no memory and costs nothing, and the next request, exec or attach restores it in a fraction of a second with every process where it was. A request that arrives while the suspend is being written cancels it. Quiet means no request, exec or stream byte, no console session running a command, no traffic to it and no CPU to speak of; see "Background work" below.

## The tools

| I need to... | Tool | Note |
| --- | --- | --- |
| a machine | `create_machine` | `name` is optional; pass one when the URL has to be predictable |
| run a command and read the output | `exec` | waits; returns stdout, stderr and the exit code |
| run something long or noisy | `exec_stream` | collects output as it arrives |
| leave something running (a dev server, a build, an agent run) | `process_start` | named and detached; outlives the call; see "Processes" below |
| read a file, write one, list a directory | `file_read`, `file_write`, `file_list`, `file_remove` | raw bytes, no shell quoting |
| read the console | `logs` | `tail` limits it to the last lines |
| capture it, memory included | `checkpoint` | returns a checkpoint id |
| put a checkpoint back | `restore` | IN PLACE: same machine, same id, same URL |
| keep a state as a base that outlives the machine | `template` | then `create_machine` with `template`, or `fork` with `template`, makes machines from it, processes already running |
| list or delete templates | `templates`, `template_delete` | deleting one leaves the machines made from it running |
| more disk room | `resize_machine` with `disk_gib` | grows in place, processes keep running; or ask up front with `disk_gib` on `create_machine` and `fork` |
| get rid of it | `destroy_machine` | irreversible, and it takes the checkpoints with it |

## Each answer and what to do

| Answer | Meaning | Do |
| --- | --- | --- |
| a non-zero `exit_code` from `exec` | the command ran and failed | decide what it means; this is a result, not a tool error |
| `not_found` | the machine is gone, or this key sees a different org | check the id; `list_machines` shows what the key can see |
| `no_capacity`, 507 | the fleet has no room right now; not an account limit, there is none | retry shortly, or ask for a smaller machine |
| `busy`, 503 | a host had no room this moment and held the create or fork in its line first | wait `details.retry_after_ms`, then call `create_machine` or `fork` again with the same arguments |
| `No space left on device`, or `df -h /` near 100% | the root disk (2 GiB by default) is full | `resize_machine` with a larger `disk_gib` (up to 64); it grows with nothing restarted |

## Do not

- Do not create a machine to deploy an app. `deploy` makes the machines a service needs.
- Do not treat a non-zero exit as a broken tool. A `grep` that found nothing exits 1.
- Do not destroy a machine without asking the user. It is irreversible and it takes every checkpoint with it.
  A `template` made from it first survives it.
- Do not keep a "golden" machine alive just to fork from it. Make a `template` from it and destroy it.

## Disk

The root disk is 2 GiB unless asked for. Installing a lot (node_modules, a headless browser, a mobile toolchain) wants more: pass `disk_gib` (up to 64) to `create_machine` or `fork`, or `resize_machine` an existing one. The filesystem fills the disk before the call returns, and only written blocks are billed, never the size, so asking for room costs nothing until it is used. A fork keeps its source's size and may ask for more, never less. A disk only grows.

    pilot machine create build-box --disk 16GiB
    pilot machine fork golden --disk 8GiB
    pilot machine resize build-box --disk 32GiB

## Processes

`exec` waits for its command. A process is the same command left running under a name, which you come back to.

    pilot process start scratch dev --restart always -- npm run dev
    pilot process start scratch build --keep-awake -- npm run build
    pilot process output scratch build --follow
    pilot process get scratch build
    pilot process signal scratch build INT
    pilot process rm scratch build

MCP: `process_start` with `{ "machine": "scratch", "name": "build", "argv": ["npm", "run", "build"], "keep_awake": true }`, then `process_output` with `{ "machine": "scratch", "name": "build", "offset": 0 }` until the state is no longer `running`, then `process_status`. `processes`, `process_signal`, `process_remove`.

| Answer | Meaning | Do |
| --- | --- | --- |
| `state: running` / `restarting` | alive, or about to be restarted by its policy | read more output from the offset you reached |
| `state: exited` | ended with status 0 | done |
| `state: failed` | non-zero `exit_code`, a `signal` nobody sent, or `error` (could not start, or a cold boot) | read stderr; decide |
| `state: stopped` | ended because it was asked to | nothing |
| `conflict` on start | that name is running | another name, or stop it first |

- Output is stdout and stderr kept separately on the machine's disk, addressed by BYTE OFFSET. Remember the offset you reached and ask from there: you get exactly the next byte, across a dropped connection or a suspend. The start answers `stdout_offset`, where this run begins.
- `restart`: `never` (default), `on-failure`, `always`. It also decides what happens after a cold boot.
- `keep_awake` keeps the machine from sleeping while the process runs. Give it to builds and agent runs, not to dev servers.
- `env` is held in the process's memory only, never on disk. The MCP tool takes no `env`: a secret must not pass through you. The user passes it with `pilot process start --env`.
- A checkpoint, a restore and a fork of a running machine carry its processes still running, so a dev server keeps serving in a fork.

## Files, ports and sessions from the CLI

- `pilot file push <local> <machine>:<dest>` / `pilot file pull <machine>:<src> <local>` /
  `pilot file edit <machine>:<path>` / `pilot file ls|cat|rm <machine>:<path>` use the
  files API: raw bytes, atomic writes, directories as a streamed archive. A relative
  path is relative to the machine user's home.
- `pilot proxy <port>|<local:remote>...` reaches any TCP port inside a machine from
  localhost (Postgres, a debugger, ssh via `-W host:port` as a ProxyCommand). The URL
  serves 8080 over HTTP only; proxy is for everything else.
- A console is a session that outlives its connection: `ctrl-\` detaches, `pilot attach`
  returns and replays what was printed meanwhile, `pilot session ls` lists them,
  `pilot session kill` ends one.
- `pilot url [target]` shows a URL's auth mode; `pilot url update --auth org` makes it
  require an API key of the org; `--auth token` also lets in a short-lived preview link from
  `pilot url token` (MCP `preview_url`), which works in a browser or an iframe; `--label k=v` on create and `ls --label` find machines again.
- `pilot use <machine>` sets a directory-local default so none of these need a name.

## Background work

A suspend is a freeze, not a kill: the memory is snapshotted and every process resumes exactly where it was on the next request, exec or attach. So the question is only what keeps a machine awake, and there are four signals:

- A request, exec or stream in flight. A long silent build under `exec` is never suspended.
- A console session with a command running, even after you detach. The guest reads its process tree, so a build whose output goes to a file still counts; a shell sitting at its prompt does not. `pilot session ls` shows `busy` per session.
- A process started with `keep_awake` (`--keep-awake`), while it runs.
- The guest using CPU with nobody connected (a detached install or test run).
- Traffic that carries bytes, into or out of the machine: guest-to-guest on `.internal`, a download, an upload, a reply to a connection it opened.

An open connection that carries nothing is NOT activity, in either direction. An idle outbound connection (npm's update check, a keep-alive HTTP client, a database pool) does not keep the machine up, even with TCP keepalive probes on it: a probe and its answer carry no bytes. Likewise a dev server's live-reload stream to an open tab lets the machine suspend. The tab's connection is held open while it sleeps and closed when the machine next wakes (or when the tab sends a byte), so the client reconnects to a machine that is awake. Make such a client re-check its state on reconnect (reload if the build changed): an event the server sent while the old stream was being closed is not replayed.

What none of them see is a process idle between bursts of its own, such as a worker that polls an outside queue every minute: a suspended guest fires no timers. Start such a worker as a process with `keep_awake`, or set how long the machine waits after its last activity:

    pilot machine create worker --idle-timeout 30m

MCP: `create_machine` with `{ "idle_timeout": 1800 }` (`fork` takes it too). The cap is an hour, so a forgotten value costs at most an hour per idle cycle. A worker that must run forever is a service, not a sandbox: `promote` it, then `x-pilots: min_machines_running: 1` in its compose file keeps one replica resident.

Two things to know: a process that calls `setsid` leaves the session tree by definition, so only its CPU use keeps the machine up; and a snapshot drops outbound connections, so a client that wakes after one should expect to reconnect.

## What a machine is using

| I need to... | Do |
| --- | --- |
| one machine's CPU and memory | `metrics` tool, or `pilot machine metrics <m>` |
| every machine of a team | `GET /v1/metrics`, Prometheus text, with a `machines` key |
| the end of a log, not the boot | `pilot machine logs <m> --tail 50` |
| resume a follow that dropped | `?offset=` with the `X-Pilot-Log-Offset` you last saw |

CPU is a TOTAL in seconds, not a rate. Take two readings and divide by the time
between them. It never goes down, including across a suspend, so a difference is
always real work.

Memory is zero while a machine is suspended. That is the truth rather than a
gap: a suspended machine holds no memory, which is the point of suspending it.

Memory near the ceiling is why a process was killed. CPU flat while a request
hangs means it is waiting on something, not computing.

```
# Prometheus, scraping one team's machines from any host:
scrape_configs:
  - job_name: pilots
    metrics_path: /v1/metrics
    authorization:
      credentials: <a machines-scoped key>
    static_configs:
      - targets: ['api.example.test']
```

A host that did not answer appears as `pilots_metrics_hosts_unreachable`. The
scrape is still a 200: what could be read is more useful than nothing, and the
line names what could not.

Console logs are bounded at 16 MiB per machine and are NOT state. Wipe a host
and the logs are gone while every machine restores exactly as before.

## What a restore promises

A restore never fails because a memory image is gone. Memory snapshots carry raw CPUID, so one is portable within a CPU vendor pool and never across it. When no host of that pool is live, the machine COLD-BOOTS from its own disk instead.

| Survives a cold boot | Does not |
| --- | --- |
| the id, the name, the URL | the processes that were running |
| the volume and every byte on disk | the memory they held |
| the agent token | |

The machine reports `last_start: cold_boot`, so tell the difference from that rather than from behaviour: a machine that came back without its running process is not broken, it is a machine whose pool had no live host.

A request that arrives while a machine is asleep is HELD, not bounced, for up to 120 seconds. That is one number for a machine on the host you reached and for a machine one host over, so nothing a client can measure tells it where a sandbox lives.

## Do not

- Do not treat a `cold_boot` start as a failure. It is the documented outcome when a vendor pool has no live host, and everything on disk is intact.
- Do not retry a request to a sleeping machine faster than the hold. It is already being held; a second request wakes nothing sooner and doubles the work.
