#!/usr/bin/env python3
"""Hand Claude Code the Authorization header for the hosted pilots MCP server.

This is the `headersHelper` of `.mcp.json`. Claude Code runs it at every
connect and merges the JSON object it prints into the request headers.

It exists because the header cannot be written into `.mcp.json` itself. A
static `"Authorization": "Bearer ${PILOT_API_KEY}"` is sent even when the
variable is unset, the fleet answers 401, and Claude Code does NOT fall back to
the browser login once an Authorization header is configured. `pilot login`
sets no variable, it writes a file, so that was the state of every user who
followed /agents.

So the key comes from where `pilot login` put it, and when there is none this
prints `{}`: no header at all, which is what lets the fleet's 401 and its
`resource_metadata` pointer start the browser login in `/mcp`. A helper that
cannot run (no python3) ends the same way, so the worst case is a sign-in
page, never a dead server.

Precedence is the CLI's (apps/pilot/internal/config): PILOT_API_KEY, then the
credentials file. Inside a plugin the first never fires: Claude Code strips
every credential-looking variable from a plugin's helper, on purpose. It is
read for the entry copied into a user-scope config, where it is kept.
"""

from __future__ import annotations

import json
import os
import sys
from urllib.parse import urlsplit

DEFAULT_API_URL = "https://api.pilotrun.app"


def origin(url: str) -> tuple[str, str]:
    parts = urlsplit(url.strip())
    return parts.scheme.lower(), parts.netloc.lower()


def credentials_path() -> str:
    # $XDG_CONFIG_HOME/pilots/credentials, falling back to ~/.config: the same
    # rule as config.Path in the CLI.
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "pilots", "credentials")


def api_key() -> str:
    key = os.environ.get("PILOT_API_KEY", "").strip()
    if key:
        return key
    try:
        with open(credentials_path(), encoding="utf-8") as f:
            creds = json.load(f)
    except (OSError, ValueError):
        return ""
    if not isinstance(creds, dict):
        return ""
    # A key is only ever sent to the fleet it was minted for. The file may
    # belong to a self-hosted fleet while this server entry points at the
    # public one (or the reverse, under PILOT_API_URL); a mismatch stays
    # silent and the user signs in to the fleet actually being asked.
    target = (
        os.environ.get("CLAUDE_CODE_MCP_SERVER_URL")
        or os.environ.get("PILOT_API_URL")
        or DEFAULT_API_URL
    )
    if origin(str(creds.get("api_url") or DEFAULT_API_URL)) != origin(target):
        return ""
    return str(creds.get("api_key") or "").strip()


def main() -> int:
    key = api_key()
    json.dump({"Authorization": f"Bearer {key}"} if key else {}, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
