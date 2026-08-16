# Direct Drive Cloud Candidate MCP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Provide a remote `reliable-drive-sync` MCP that creates candidates and writes interview artifacts directly to a fixed Google Drive folder, stopping immediately whenever Drive returns an error.

**Architecture:** The Worker authenticates MCP calls with a bearer token and exchanges its service-account credential for a Google OAuth access token. A candidate is a folder under the configured Drive root containing `candidate.json`; artifacts are uploaded directly into that folder. A successful Drive API response is the only persistence success condition.

**Tech Stack:** Cloudflare Workers, Google Drive v3 REST API, Web Crypto, Node.js built-in tests.

## Global Constraints

- Never commit Cloudflare, Google, or bearer-token credentials.
- No D1, R2, queue, asynchronous sync, hash comparison, idempotency store, or retry state.
- Every candidate creation and artifact upload must return a Drive file/folder ID before the MCP reports success.
- Any Drive failure returns an MCP error and prevents the calling workflow from continuing.
- Candidate context and artifact submission require explicit user confirmation of the candidate ID.

---

### Task 1: Direct Drive client

**Files:**
- Create: `cloud-mcp/src/google-drive.js`
- Modify: `cloud-mcp/test/google-drive.test.js`

**Interfaces:**
- Produces: `createCandidateFolder(env, input, deps)` and `uploadDriveFile(env, parentId, name, content, mimeType, deps)`.

- [ ] **Step 1: Write failing tests for the Drive success and failure boundaries**

```js
test("createCandidateFolder returns only after Drive creates both folder and metadata", async () => {
  const candidate = await createCandidateFolder(env, { displayName: "小明" }, deps);
  assert.equal(candidate.candidateId.startsWith("CAND-"), true);
});

test("createCandidateFolder rejects when Drive cannot create metadata", async () => {
  await assert.rejects(() => createCandidateFolder(env, { displayName: "小明" }, failingDeps));
});
```

- [ ] **Step 2: Run the Drive tests to verify they fail because the module is absent**

Run: `node --test test/google-drive.test.js`

Expected: module-not-found failure for `src/google-drive.js`.

- [ ] **Step 3: Implement the minimal Drive client**

Implement access-token acquisition from `GOOGLE_SERVICE_ACCOUNT_JSON`, Drive folder creation, JSON metadata upload, and multipart file upload. Throw on every non-2xx response or missing Google file ID.

- [ ] **Step 4: Run the Drive tests to verify they pass**

Run: `node --test test/google-drive.test.js`

Expected: all tests pass.

### Task 2: Replace stateful Worker code with direct Drive MCP tools

**Files:**
- Delete: `cloud-mcp/src/candidates.js`
- Delete: `cloud-mcp/migrations/0001_initial.sql`
- Modify: `cloud-mcp/src/index.js`
- Modify: `cloud-mcp/test/mcp.test.js`
- Modify: `cloud-mcp/wrangler.toml`

**Interfaces:**
- Consumes: direct Drive client from Task 1 and Worker secrets `MCP_BEARER_TOKEN`, `GOOGLE_SERVICE_ACCOUNT_JSON`, `GOOGLE_DRIVE_FOLDER_ID`.
- Produces: `create_candidate`, `submit_artifact`, `list_candidates`, and `read_artifact` MCP behavior backed solely by Drive.

- [ ] **Step 1: Write failing MCP tests for direct candidate creation and direct artifact upload**

```js
test("tools/call create_candidate delegates to Drive and returns its candidate ID", async () => {
  const payload = await mcpCall("create_candidate", { displayName: "小明" });
  assert.match(payload.result.content[0].text, /CAND-/);
});

test("tools/call submit_artifact returns an error when Drive upload fails", async () => {
  const payload = await mcpCall("submit_artifact", artifact, failingDrive);
  assert.equal(payload.error.code, -32603);
});
```

- [ ] **Step 2: Run the MCP tests and observe the required failure**

Run: `node --test test/mcp.test.js`

Expected: tests fail because stateful candidate storage is still wired.

- [ ] **Step 3: Implement only direct-Drive tool behavior**

Remove D1 and R2 bindings; make `create_candidate` call Drive; accept `candidateFolderId` for confirmed context and artifact tools; make `submit_artifact` decode and upload content directly. Do not report success after a failed Drive call.

- [ ] **Step 4: Run all Worker tests**

Run: `node --test`

Expected: all tests pass.

### Task 3: Align skill instructions and deployment documentation

**Files:**
- Modify: `AGENTS.md`
- Modify: `conducting-java-backend-mock-interviews/SKILL.md`
- Modify: `reviewing-java-backend-interviews/SKILL.md`
- Modify: `cloud-mcp/README.md`
- Modify: `.gitignore`

**Interfaces:**
- Produces: a cloud task flow that calls `create_candidate`, asks for confirmation, and stops if any Drive-backed MCP tool errors.

- [ ] **Step 1: Add the direct-write success rule to each interview skill**

State that a Drive-backed MCP call returning an error is terminal for that persistence step: retain the interview content in chat and do not continue to the next persistent action.

- [ ] **Step 2: Document direct deployment only**

Document Worker secret setup and Drive folder sharing; remove D1/R2 migration and binding instructions.

- [ ] **Step 3: Run the final verification**

Run: `node --test && git diff --check`

Expected: tests pass and no whitespace errors are reported.

- [ ] **Step 4: Commit, push, and update Draft PR #5**

Run:

```powershell
git add AGENTS.md cloud-mcp docs conducting-java-backend-mock-interviews/SKILL.md reviewing-java-backend-interviews/SKILL.md
git commit -m "refactor: write interview records directly to Drive"
git push
```

Expected: PR #5 contains the direct-Drive design and implementation.
