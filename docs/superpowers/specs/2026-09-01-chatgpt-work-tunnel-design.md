# ChatGPT Work Reliable Drive Sync Tunnel Design

## Goal

Make the existing Reliable Drive Sync `submit_event` tool available to ChatGPT
Work without exposing the Drive-writing Worker as an unauthenticated public MCP
endpoint.

This design is the development-mode bridge. A public plugin release remains a
separate OAuth 2.1 and Streamable HTTP project.

## Boundaries

- Keep the schema-1.2 event envelope and Worker behavior unchanged.
- Expose exactly one MCP tool: `submit_event`.
- Keep the Worker bearer secret on the user's Windows machine.
- Do not commit API keys, bearer tokens, tunnel IDs, or user-specific absolute
  paths.
- Preserve the existing Codex and WorkBuddy stdio entry point.
- Do not add a public no-auth `/mcp` route.

## Architecture

```text
ChatGPT Work developer app
  -> OpenAI Secure MCP Tunnel
  -> tunnel-client on Windows
  -> tools/reliable-drive-sync-mcp/start.cmd
  -> stdio-bridge.mjs
  -> authenticated Reliable Drive Sync Worker
  -> Google Drive
```

The tunnel is transport only. `stdio-bridge.mjs` remains the MCP server and the
deployed Worker remains the validation, identity, persistence, and projection
boundary.

## Local configuration

`start.cmd` first uses process environment variables. If Codex, WorkBuddy, or
`tunnel-client` was started before the variables were configured, it may read
the same two values from the current user's persistent Windows environment:

- `RELIABLE_DRIVE_SYNC_INGRESS_URL`
- `RELIABLE_DRIVE_SYNC_INGRESS_SHARED_SECRET`

The launcher never prints their values. `RELIABLE_DRIVE_SYNC_NODE_PATH` remains
optional.

The stdio server must complete MCP initialization even when Worker delivery
configuration is missing. Only `submit_event` fails in that condition, with a
clear configuration error. This keeps the MCP client loaded and makes the
failure diagnosable.

## Tunnel setup

A PowerShell helper accepts a `tunnel_id`, the path to `tunnel-client`, and an
optional profile name. It initializes a stdio profile pointing at `start.cmd`,
runs `doctor`, and prints the separate `run` command. It receives the runtime
OpenAI API key through `CONTROL_PLANE_API_KEY`; it never writes that key itself.

The user performs two account-bound actions that cannot be committed to source:

1. Create/associate a tunnel in OpenAI Platform and provide a runtime API key to
   the local process.
2. In ChatGPT Work developer mode, create a Tunnel connection and select that
   tunnel.

After ChatGPT creates the developer app, its `plugin_asdk_app...` technical ID
can be wired into the personal plugin in a later packaging step. The tunnel
connection itself is sufficient for immediate tool testing.

## Tool contract correction

The bridge advertises the same schema as the Worker: `identity.username` is
required and `identity.userId` is optional. Callers never invent a user ID. The
Worker resolves or registers the stable ID by normalized display name.

## Verification

Automated tests cover:

- initialization and `tools/list` without delivery configuration;
- the single-tool surface;
- matching Worker and bridge identity schemas;
- clear failure when delivery configuration is absent;
- Windows launcher fallback without printing secrets;
- tunnel helper validation and dry-run command construction.

Manual acceptance is:

1. `tunnel-client doctor` reports ready.
2. ChatGPT Work discovers exactly `submit_event`.
3. A new `system.user-registered` request returns Worker JSON.
4. A duplicate `requestId` remains idempotent.

## Deferred production work

A distributable public plugin requires a stable Streamable HTTP `/mcp` endpoint,
OAuth 2.1 authorization, rate limits, audit logging, and the final ChatGPT app
technical ID in the plugin package. Secure MCP Tunnel is intentionally limited
to private/developer-mode use.
