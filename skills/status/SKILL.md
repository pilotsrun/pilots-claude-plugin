---
name: status
description: Check whether the pilots MCP server is reachable and the key works, then list the machines and services it can see, without creating or changing anything.
disable-model-invocation: true
---

# pilots status

A read-only health check. Nothing here creates, mutates, restores or destroys.

1. Confirm the pilots MCP tools are available (`status`, `list_machines`,
   `list_services`). If they are missing, the server is not connected, and
   `/mcp` says which of three it is:
   - **needs authentication**: there is no stored key, so the plugin sent
     none. The user selects the server in `/mcp` and finishes the browser
     login. Someone who has the CLI can run `pilot login` instead and
     reconnect in `/mcp`.
   - **failed, with a 401**: the key `pilot login` stored was refused, because
     it expired or was revoked. The user runs `pilot login` again and
     reconnects in `/mcp`. There is no browser login in this state, since a
     key was sent.
   - **not listed**: the plugin is not loaded. Check `/plugin`, then run
     `/reload-plugins`.

   There is no variable to export. The plugin reads the key from
   `~/.config/pilots/credentials`, the file `pilot login` writes, and only when
   that file is for the fleet being dialled. Claude Code does not show
   `PILOT_API_KEY` to a plugin, so setting it changes nothing here;
   `PILOT_API_URL` is read, and points the plugin at a self-hosted fleet. Do
   not install a CLI or register a second server.
2. Call `status`. A 401 on the call itself means the key was revoked during
   the session: the same fix as a failed connection above. Retry once after
   they fix it.
3. Call `list_machines` and `list_services`.
4. Report in this compact form. An empty list is a successful result.

```text
pilots status
- MCP tools: available | missing
- Key: OK | needs login | unknown
- Fleet: <api url>, <n> hosts
- Machines: <n> (name, state, url)
- Services: <n> (name, url)
- Next: one concrete action, or "nothing to do"
```
