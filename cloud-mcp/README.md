# reliable-drive-sync cloud MCP

This Cloudflare Worker exposes one JSON-RPC tool: `submit_event`. It stores
schema-1.2 JSON events in a Google Shared Drive and verifies every created file
by reading it back. The `algorithm` and `interview` namespaces use separate
identity registries under the configured root; existing root-level name folders
are not scanned or migrated.

## Envelope and identity gate

```json
{
  "schemaVersion": "1.2",
  "namespace": "interview",
  "eventType": "identity.create",
  "payload": {"username": "乔炳源"},
  "requestId": "<uuid>"
}
```

At the start of every conversation, call `identity.list`, display `A. choose an
existing user / B. create a new user`, and then call `identity.verify` or
`identity.create`. The verified `{userId, username}` binding is valid only for
the current conversation. The same gate is required independently for both
namespaces.

Supported event types are identity list/create/verify, algorithm learning
completion, interview session list/load/completion, and interview review
completion. Calling a removed tool returns JSON-RPC `-32601`.

## Runtime setup

1. Create or select a Google Shared Drive folder and add the service-account
   email as Writer. Service accounts do not have My Drive storage quota.
2. Configure Worker secrets (never commit them):

   ```text
   wrangler secret put MCP_BEARER_TOKEN
   wrangler secret put GOOGLE_SERVICE_ACCOUNT_JSON
   wrangler secret put GOOGLE_DRIVE_FOLDER_ID
   ```

3. Deploy with `npx wrangler deploy`.
4. Configure the published HTTPS endpoint as the `reliable-drive-sync` remote
   MCP in the eligible Codex workspace.

## Statuses and outputs

`status: "ok"` is returned only after the event and any profile snapshot are
confirmed by Drive readback. If the event cannot be written, local Skills still
write JSON with `cloud_persistence_pending`. If the event is durable but the
rebuildable profile cache fails, the response is `profile_cache_pending` and the
event remains the source of truth.

Session and review copies are saved locally at:

```text
outputs/interview/<userId>/interview-<sessionId>-session.json
outputs/interview/<userId>/interview-<sessionId>-report.json
outputs/interview/<userId>/interview-<sessionId>-report.docx
```

Only the JSON event is uploaded. Markdown transcripts, Base64 payloads, and DOCX
reports are never uploaded; the Word file is generated locally from report JSON.
