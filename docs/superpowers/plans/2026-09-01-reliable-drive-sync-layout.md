# Reliable Drive Sync Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the obsolete multi-tool WorkBuddy surface and separate the required Reliable Drive Sync Worker from its local one-tool stdio bridge.

**Architecture:** The cloud Worker remains the authoritative identity, event, Drive, idempotency, and profile-projection runtime under `services/reliable-drive-sync-worker/`. The local MCP process becomes a small forwarding adapter under `tools/reliable-drive-sync-mcp/` and exposes only `submit_event`. Existing schema-1.2 consumers remain compatible; schema-1 migration is not part of this layout refactor.

**Tech Stack:** Node.js ESM, Node `node:test`, Cloudflare Worker, JSON-RPC stdio, Markdown documentation.

**Spec:** `docs/superpowers/specs/2026-08-29-java-resume-knowledge-design.md` and the approved chat design on 2026-09-01.

## Global Constraints

- All cloud persistence uses only `submit_event`.
- The public MCP tool allowlist is exactly `submit_event`.
- Do not delete or mutate any Google Drive data.
- Do not commit secrets or a user-specific WorkBuddy configuration.
- Keep schemaVersion `1.2` for this refactor so current Skills remain compatible.
- Preserve historical plan documents as historical records; update active documentation and executable paths.

---

### Task 1: Lock the new repository layout with failing tests

**Files:**
- Modify: `tests/test_repository_storage_contract.py`
- Create: `tools/reliable-drive-sync-mcp/test/layout.test.mjs`

**Interfaces:**
- Consumes: the repository tree and the existing bridge behavior.
- Produces: executable assertions requiring the Worker and bridge to live at their new paths and requiring the bridge tool list to contain only `submit_event`.

- [x] **Step 1: Change the repository contract test to require new paths**

Replace executable-path expectations `cloud-mcp/...` with `services/reliable-drive-sync-worker/...`; require `tools/reliable-drive-sync-mcp/stdio-bridge.mjs`; and assert `cloud-mcp` is absent.

- [x] **Step 2: Add the bridge layout test**

Import `handleRequest` from `../stdio-bridge.mjs`, call `tools/list`, and assert the returned names equal `["submit_event"]`.

- [x] **Step 3: Run the focused tests and verify the expected failure**

Run: `python -m unittest tests.test_repository_storage_contract` and `node --test tools/reliable-drive-sync-mcp/test/layout.test.mjs`.

Expected: the tests fail because the new directories and files do not exist yet.

### Task 2: Move the Worker and one-tool bridge

**Files:**
- Move: `cloud-mcp/*` to `services/reliable-drive-sync-worker/*`, excluding the bridge file and its bridge test
- Move: `cloud-mcp/local-mcp-bridge.mjs` to `tools/reliable-drive-sync-mcp/stdio-bridge.mjs`
- Move: `cloud-mcp/test/local-mcp-bridge.test.mjs` to `tools/reliable-drive-sync-mcp/test/stdio-bridge.test.mjs`
- Modify: `tools/reliable-drive-sync-mcp/test/stdio-bridge.test.mjs`
- Create: `tools/reliable-drive-sync-mcp/package.json`

**Interfaces:**
- Consumes: the failing layout contract from Task 1.
- Produces: `services/reliable-drive-sync-worker/package.json` for Worker tests and `tools/reliable-drive-sync-mcp/stdio-bridge.mjs` as the only local MCP entry point.

- [x] **Step 1: Move tracked files without changing contents**

Create `services/` and `tools/reliable-drive-sync-mcp/test/`, then use `git mv` for the Worker files and bridge files. Do not use recursive deletion.

- [x] **Step 2: Update the moved bridge test import**

Change its import from `../local-mcp-bridge.mjs` to `../stdio-bridge.mjs`.

- [x] **Step 3: Add the bridge package metadata**

Create `tools/reliable-drive-sync-mcp/package.json` with `{"name":"reliable-drive-sync-mcp","private":true,"type":"module","scripts":{"test":"node --test"}}`.

- [x] **Step 4: Run Worker and bridge tests**

The bridge and MCP contract tests pass. The complete Worker run is 219/221: two
legacy migration tests fail identically in a clean pre-change `HEAD` checkout,
so they are recorded as pre-existing and are not attributed to this move.

Run: `npm test --prefix services/reliable-drive-sync-worker` and `npm test --prefix tools/reliable-drive-sync-mcp`.

Expected: all existing Worker tests and both bridge tests pass.

### Task 3: Add a stable Windows launcher and update active documentation

**Files:**
- Create: `tools/reliable-drive-sync-mcp/start.cmd`
- Create: `tools/reliable-drive-sync-mcp/README.md`
- Modify: `AGENTS.md`
- Modify: active Skill/reference files that point to `cloud-mcp/`
- Modify: `tests/test_repository_storage_contract.py`

**Interfaces:**
- Consumes: `RELIABLE_DRIVE_SYNC_NODE_PATH`, `RELIABLE_DRIVE_SYNC_INGRESS_URL`, and `RELIABLE_DRIVE_SYNC_INGRESS_SHARED_SECRET` supplied by the WorkBuddy environment.
- Produces: a launcher that starts `stdio-bridge.mjs` from its own stable directory and never prints secrets.

- [x] **Step 1: Write the launcher**

Use `%~dp0stdio-bridge.mjs` and `%RELIABLE_DRIVE_SYNC_NODE_PATH%`; fall back to `node` only when the variable is absent. Exit nonzero with a short configuration error when the ingress URL or shared secret is missing. Do not echo environment values.

- [x] **Step 2: Update active path references**

Replace executable references in `AGENTS.md`, current Skill references, current profile/runtime docs, and repository contract tests. Leave dated historical plans unchanged.

- [x] **Step 3: Document WorkBuddy configuration without secrets**

Document a `stdio` entry that points to the stable launcher and states that `tools/list` must return only `submit_event`; explicitly warn against the old `.worktrees/.../packages/mcp-server/dist/index.js`.

### Task 4: Verify no obsolete public tools or live path dependencies remain

**Files:**
- Modify: active documentation or tests found by the verification search

**Interfaces:**
- Consumes: the moved Worker, bridge, launcher, and documentation.
- Produces: a clean repository contract and evidence suitable for configuring WorkBuddy.

- [x] **Step 1: Run the complete executable test set**

Run: `npm test --prefix services/reliable-drive-sync-worker`, `npm test --prefix tools/reliable-drive-sync-mcp`, and `python -m unittest discover -s tests`.

- [x] **Step 2: Verify the public tool allowlist**

Run: `rg -n "submit_artifact|list_candidates|get_candidate_context|read_artifact" services/reliable-drive-sync-worker tools/reliable-drive-sync-mcp` and require no matches in executable files.

- [x] **Step 3: Verify the old layout is gone from active files**

Run: `rg -n "cloud-mcp/|\.worktrees/.*/packages/mcp-server" AGENTS.md algorithm-learning conducting-java-backend-mock-interviews reviewing-java-backend-interviews java-knowledge-based-on-resume-learn-skill services tools tests` and require no matches.

- [x] **Step 4: Commit the refactor**

Run: `git add AGENTS.md services tools algorithm-learning conducting-java-backend-mock-interviews reviewing-java-backend-interviews java-knowledge-based-on-resume-learn-skill tests docs/superpowers/plans/2026-09-01-reliable-drive-sync-layout.md && git commit -m "refactor: separate reliable drive sync worker and bridge"`.
