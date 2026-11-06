# Compose

## What this covers

Describing more than one service: a web app with a database, a worker, a shared app name, volumes and secret references. Not covered: single-directory deploys, which need no file at all (deploy.md).

## The command to copy

    pilot deploy            # picks up compose.pilots.yaml, else compose.yaml, in the directory

A file that covers the common case:

    name: shop
    services:
      web:
        build: .
        environment:
          DATABASE_URL: secret://database_url
        depends_on: [postgres]
      postgres:
        image: postgres:17
        volumes:
          - pgdata:/var/lib/postgresql/data
    volumes:
      pgdata:
        driver_opts:
          size: 10G

## What happens

1. The file's text and the directory's `.env` go to `POST /v1/compose/plan`. The CLI interpolates nothing; one parser, in Go, beside the daemon.
2. The plan is an ordered list of steps: build, volume, service, deploy, per service, in dependency order.
3. Services in the same app find each other at `<name>.internal`, which is why `DATABASE_URL` above points at `postgres.internal`. The app is scoped to the organization: another organization using the same app name can neither resolve nor connect to it.

## The `x-pilots` keys

Everything pilots needs that compose has no word for goes under `x-pilots:` on a service (or at the top level for `app`). Unknown keys are ignored, so a typo is silent: copy these.

| Key | Meaning |
| --- | --- |
| `domain` | the label the URL is minted from (default: the service name) |
| `private: true` | no URL; peers reach it at `<name>.internal` |
| `custom_domain` | a hostname you own (domains.md) |
| `auto_stop: off\|suspend` | `suspend` (default) sleeps an idle replica; `off` never does |
| `auto_start: true\|false` | wake on a request (default true; `false` is a dead URL) |
| `min_machines_running` | replicas kept resident, default 0 (scale to zero) |
| `max_machines_running` | the ceiling: replicas the autoscaler may run at once, default 0 (no ceiling) |
| `soft_limit` | concurrent requests per replica before more start (default 20); a burst adds ceil(in flight / soft_limit) replicas in one pass |
| `hard_limit` | concurrent requests a replica queues at and then refuses with 503 + Retry-After (default 0, none) |
| `idle_timeout` | quiet before a machine suspends, `1500ms`, `30m` or seconds, 0.5s..1h (default 2s); the sandbox timer, carried by a promoted machine -- a service replica's scale-down window is the autoscaler's |
| `schedules` | cron jobs, a list of `{ cron, path }` or `{ cron, cmd }` (services.md); a `cmd` runs from the app user's home, so use absolute paths; `[]` clears the previous release's |
| `size_gib` | a volume's size, on the volume |
| (changing knobs) | a deploy whose only change is a knob keeps its release and applies the knobs in place, with no restart; `pilot service set --min-machines/--max-machines/--soft-limit/--hard-limit/--idle-timeout/--auto-stop` does the same by hand |
| `pre_deploy` | a command run on a throwaway machine before any replica is replaced (a migration) |
| `app` | top level only: the app name |

## The rules

| Rule | Why |
| --- | --- |
| the `.env` FILE, never the process environment | a deploy has to be reproducible from the checkout |
| one `build:` context per service | each service is its own image |
| a volume-backed service runs one replica | a volume is mounted by one machine at a time |
| a `secret://` reference, never a value | the file is committed (secrets.md) |
| `compose.pilots.yaml` wins over `compose.yaml` | a repo that also runs under docker compose writes `compose.yaml` for a laptop: host ports, a local database. How it deploys HERE goes in `compose.pilots.yaml`, which `pilot deploy` and a `git push` both use |
| a `git push` deploys the service the repo is linked to, by name | a compose file may describe several; the push builds the one named after the linked service, with the build context, Dockerfile and overrides `pilot deploy` would use |

## Each answer and what to do

| Answer | Meaning | Do |
| --- | --- | --- |
| `plan_unsupported` | the file asks for something pilots does not do | fix every key in `details.unsupported`; they are all listed at once, so one pass is enough |
| `compose_invalid` | the file does not parse, or a variable is unset | the message names the file and the problem |
| `bad_request` about the app name | nothing names the app | add a top-level `name:`, set `COMPOSE_PROJECT_NAME`, or pass `--app` |

## Do not

- Do not write a compose file for a single app the platform already recognises. `deploy` handles it.
- Do not fix one unsupported key at a time. Every one is in the answer.
- Do not interpolate variables yourself. Put them in `.env` and let the planner do it.
