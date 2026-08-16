# Local MCP Bridge Replacement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the stale candidate-management stdio MCP process with a local bridge that exposes only `submit_event` and forwards schema-1.2 calls to the deployed Worker root.

**Architecture:** A dependency-free Node.js stdio JSON-RPC adapter will read the existing Windows registry environment variables, derive the Worker origin from the configured ingress URL, and forward authenticated `tools/call` requests. The Codex command wrapper will launch this adapter instead of the old worktree server; no Drive data or Worker deployment configuration will be changed.

**Tech Stack:** Node.js built-in `readline`, `fetch`, JSON-RPC 2.0, Windows `.cmd`, existing Cloudflare Worker HTTP endpoint.

## Global Constraints

- Expose exactly one MCP tool: `submit_event`.
- Do not expose or call legacy `list_candidates`, `get_candidate_context`, `read_artifact`, or `submit_artifact` routes.
- Use the existing local `RELIABLE_DRIVE_SYNC_INGRESS_SHARED_SECRET` without printing it.
- Forward to the Worker origin `https://reliable-drive-sync.qiaobingyuan886.workers.dev` (derived from the configured `/v1/jobs` URL).
- Validate with `tools/list`, then read-only `identity.list`; do not read the supplied resume or submit interview data during bridge verification.

---

### Task 1: Add the dependency-free stdio bridge

**Files:**
- Create: `cloud-mcp/local-mcp-bridge.mjs`
- Test: `cloud-mcp/test/local-mcp-bridge.test.mjs`

**Interfaces:**
- Consumes: newline-delimited MCP JSON-RPC requests on stdin and the registry-provided URL/token environment variables.
- Produces: MCP `initialize`, `tools/list`, `tools/call`, `ping`, and notification responses; one `submit_event` tool whose arguments are forwarded unchanged to Worker `tools/call`.

- [x] **Step 1: Write bridge contract tests**

Test the exported pure helpers with a fake fetch: `deriveWorkerUrl('/v1/jobs')` returns the origin; `tools/list` returns one tool named `submit_event`; unsupported tool names return JSON-RPC `-32601`; a successful call forwards `Authorization: Bearer <token>` and Worker JSON unchanged.

- [x] **Step 2: Run the focused test and verify it fails**

Run: `node --test cloud-mcp/test/local-mcp-bridge.test.mjs`

Expected: FAIL because `local-mcp-bridge.mjs` does not exist yet.

- [x] **Step 3: Implement the bridge**

Implement `deriveWorkerUrl(configuredUrl)`, `handleRequest(request, options)`, and a stdin loop. `handleRequest` must return `initialize` capabilities, exactly one `tools/list` entry, ignore `notifications/initialized`, reject unknown methods/tools, and POST `{jsonrpc:'2.0',id,method:'tools/call',params:{name:'submit_event',arguments}}` to the derived origin with `Authorization: Bearer ${token}` and `Content-Type: application/json`.

- [x] **Step 4: Run the focused test and verify it passes**

Run: `node --test cloud-mcp/test/local-mcp-bridge.test.mjs`

Expected: PASS for framing, tool allowlist, forwarding, and error mapping.

- [x] **Step 5: Commit**

Run: `git add cloud-mcp/local-mcp-bridge.mjs cloud-mcp/test/local-mcp-bridge.test.mjs && git commit -m "feat: add submit-event stdio bridge"`

### Task 2: Switch the Codex command wrapper

**Files:**
- Modify: `C:/Users/27846/.codex/mcp/reliable-drive-sync.cmd`

**Interfaces:**
- Consumes: existing registry values `RELIABLE_DRIVE_SYNC_NODE_PATH`, `RELIABLE_DRIVE_SYNC_INGRESS_URL`, and `RELIABLE_DRIVE_SYNC_INGRESS_SHARED_SECRET`.
- Produces: a stdio process running `cloud-mcp/local-mcp-bridge.mjs`, with no old worktree dependency.

- [x] **Step 1: Replace the old executable path**

Keep the existing registry lookup and fail-closed checks, remove outbox creation and the old `packages/mcp-server/dist/index.js` invocation, and launch the new bridge with the configured Node executable. Do not echo token values.

- [x] **Step 2: Verify command resolution without starting Codex**

Run the wrapper with a short `tools/list` JSON-RPC input through the configured Node process and assert its output contains exactly one tool named `submit_event` and no legacy tool names.

- [x] **Step 3: Commit repository documentation**

Run: `git add docs/superpowers/plans/2026-08-15-local-mcp-bridge.md cloud-mcp && git commit -m "docs: record local MCP bridge execution"`

### Task 3: Verify the deployed Worker end to end

**Files:**
- Modify: none
- Test: `cloud-mcp/test/local-mcp-bridge-live.test.mjs`

**Interfaces:**
- Consumes: the installed command wrapper and existing local secret.
- Produces: evidence that the live Worker accepts the bridge and that `identity.list` is read-only.

- [x] **Step 1: Run `tools/list` through the installed command**

Start the command wrapper with `initialize`, `notifications/initialized`, and `tools/list`; assert one tool only.

- [x] **Step 2: Run read-only `identity.list`**

Send a schema-1.2 `submit_event` call with `namespace:'interview'`, `eventType:'identity.list'`, `payload:{}`, and a generated UUID requestId. Record only HTTP/JSON-RPC success and the returned identity count; never print the bearer token.

- [x] **Step 3: Run final regression tests**

Run: `npm test --prefix cloud-mcp`; expected `52+` passing tests including the bridge tests. Run the three bundled Python suites with `C:\Users\27846\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe` and expect 13, 9, and 12 passes.

- [x] **Step 4: Commit verification updates**

Run: `git add cloud-mcp/test && git commit -m "test: verify live submit-event bridge"`.

### Task 4: Handoff and restart instruction

- [x] **Step 1: Report exact installed path and verified outputs**

State that the next full Codex restart is required because the current process has cached the old MCP tool list; after restart, only `submit_event` should appear and the prior 405 candidate error is no longer reachable.
