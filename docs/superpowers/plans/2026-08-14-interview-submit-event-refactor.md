# Interview Single `submit_event` Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the public multi-tool candidate/artifact MCP with one schema-1.2 `submit_event` gateway, migrate algorithm identity calls for compatibility, and rebuild mock interview/review persistence around verified identities, immutable Drive JSON events, reconstructable profile snapshots, and local JSON/Word outputs.

**Architecture:** `cloud-mcp` exposes one JSON-RPC tool and routes a strict envelope to namespace-aware identity and event stores. Drive files remain append-only and are read back after creation; interview sessions and reviews are authoritative events, profile snapshots are rebuildable caches, and Word reports are local derivatives of review JSON. The two interview Skills own conversational behavior, while deterministic JavaScript/Python helpers own validation, event construction, local output, and report rendering.

**Tech Stack:** Cloudflare Worker JavaScript (ES modules), Google Drive v3 REST API, Node.js built-in test runner, Python 3, `unittest`, `python-docx`, Superpowers skill contract tests, Documents `render_docx.py` visual QA.

## Global Constraints

- New cloud records use `schemaVersion: "1.2"`.
- MCP `tools/list` exposes exactly one tool named `submit_event`.
- Allowed namespaces are exactly `algorithm` and `interview`; callers cannot supply paths, file names, folder IDs, MIME types, Base64, Markdown, or DOCX.
- The `interview/` and `algorithm/` identity registries are independent.
- Every new conversation performs `identity.list` followed by `identity.verify` or `identity.create`; no binding survives into a new conversation.
- `userId` is the primary key; normalized `username` is a display and secondary validation field.
- Drive event and snapshot files are created once, read back, never overwritten, moved, appended, or deleted.
- Event files are the source of truth; profile snapshots are discardable caches.
- Session and review core JSON are stored both as cloud events and local portable copies.
- Word is generated only from local review JSON and never uploaded to Drive.
- Local outputs use `outputs/interview/<userId>/interview-<sessionId>-{session|report}.{json|docx}`.
- Existing root-level name folders are not scanned, migrated, modified, or deleted.
- Algorithm answering behavior and backend-project-learning behavior remain unchanged.
- Implement every behavior test-first: write the failing test, verify the expected failure, add the minimum implementation, verify the focused suite, then commit.

---

## File Responsibility Map

### Cloud MCP

- `cloud-mcp/src/index.js`: JSON-RPC authentication, initialization, one-tool declaration, and dispatch only.
- `cloud-mcp/src/protocol.js`: envelope constants, validation, canonical JSON, hashes, and public status errors.
- `cloud-mcp/src/google-drive.js`: generic Shared Drive folder/JSON primitives; no candidate or artifact concepts.
- `cloud-mcp/src/namespace-store.js`: namespace roots, registration records, identity creation, and identity verification.
- `cloud-mcp/src/event-store.js`: append-only event creation, readback, idempotency, and verified event listing.
- `cloud-mcp/src/interview-store.js`: session list/load, session submission, review submission, and snapshot creation.
- `cloud-mcp/src/profile-model.js`: pure deterministic interview profile reconstruction.
- `cloud-mcp/src/submit-event.js`: fixed `eventType` routing across algorithm and interview namespaces.

### Skills and local output

- `algorithm-learning/SKILL.md`: migrate persistence calls to the one-tool envelope without changing coaching behavior.
- `conducting-java-backend-mock-interviews/SKILL.md`: conversation identity gate and one session-event handoff.
- `conducting-java-backend-mock-interviews/scripts/mock_handoff.py`: deterministic schema-1.2 session event and local session JSON.
- `reviewing-java-backend-interviews/SKILL.md`: verified session load, review event, profile boundary, and local report flow.
- `reviewing-java-backend-interviews/scripts/interview_core.py`: deterministic review-event validation/construction and local report JSON.
- `reviewing-java-backend-interviews/scripts/create_review_report.py`: Word generation from the new report JSON only.
- Both `schemas/contracts.schema.json` files: byte-identical schema-1.2 identity/session/review/snapshot contract.

### Tests and docs

- `cloud-mcp/test/*.test.js`: protocol, Drive, identity, event, profile, and end-to-end behavior.
- Skill-local `tests/*.py`: contract, deterministic event, local output, Word, and cross-skill compatibility.
- `cloud-mcp/README.md` and `AGENTS.md`: one-tool runtime and identity-gate instructions.

---

### Task 1: Lock the MCP to One Validated Public Tool

**Files:**
- Create: `cloud-mcp/src/protocol.js`
- Create: `cloud-mcp/src/submit-event.js`
- Modify: `cloud-mcp/src/index.js`
- Modify: `cloud-mcp/test/mcp.test.js`

**Interfaces:**
- Consumes: JSON-RPC `tools/call` arguments.
- Produces: `validateEnvelope(args)`, `dispatchSubmitEvent(env, args, deps)`, and a `tools/list` result containing only `submit_event`.

- [ ] **Step 1: Replace the old MCP expectations with failing one-tool and envelope tests**

```javascript
test("MCP exposes only submit_event", async () => {
  const response = await handleRequest(request("tools/list"), env());
  const payload = await response.json();
  assert.deepEqual(payload.result.tools.map((tool) => tool.name), ["submit_event"]);
});

test("MCP rejects removed tools", async () => {
  const response = await handleRequest(request("tools/call", {
    name: "find_or_create_candidate",
    arguments: { displayName: "旧用户" }
  }), env());
  const payload = await response.json();
  assert.equal(payload.error.code, -32601);
});

test("submit_event rejects a path-like namespace", async () => {
  const response = await handleRequest(request("tools/call", {
    name: "submit_event",
    arguments: {
      schemaVersion: "1.2",
      namespace: "../interview",
      eventType: "identity.list",
      payload: {},
      requestId: "00000000-0000-4000-8000-000000000001"
    }
  }), env());
  const payload = await response.json();
  assert.match(payload.error.message, /invalid_namespace/);
});
```

- [ ] **Step 2: Run the focused test and verify RED**

Run: `node --test cloud-mcp/test/mcp.test.js`

Expected: FAIL because six tools are still exposed and the current handler accepts the legacy argument shape.

- [ ] **Step 3: Add the strict protocol envelope**

```javascript
export const SCHEMA_VERSION = "1.2";
export const ALLOWED_NAMESPACES = new Set(["algorithm", "interview"]);
export const ALLOWED_EVENT_TYPES = new Set([
  "identity.list",
  "identity.create",
  "identity.verify",
  "algorithm.learning.completed",
  "interview.session.list",
  "interview.session.load",
  "interview.session.completed",
  "interview.review.completed"
]);

export class ProtocolError extends Error {
  constructor(status, message = status) {
    super(message);
    this.status = status;
  }
}

export function validateEnvelope(input) {
  if (!input || input.schemaVersion !== SCHEMA_VERSION) {
    throw new ProtocolError("invalid_schema_version");
  }
  if (!ALLOWED_NAMESPACES.has(input.namespace)) {
    throw new ProtocolError("invalid_namespace");
  }
  if (!ALLOWED_EVENT_TYPES.has(input.eventType)) {
    throw new ProtocolError("invalid_event_type");
  }
  if (typeof input.requestId !== "string" || !input.requestId.trim()) {
    throw new ProtocolError("invalid_request_id");
  }
  if (input.payload !== undefined && (input.payload === null || Array.isArray(input.payload) || typeof input.payload !== "object")) {
    throw new ProtocolError("invalid_payload");
  }
  return structuredClone(input);
}
```

`dispatchSubmitEvent` validates first, then calls an injected handler keyed by `eventType`. Until later tasks register production handlers, unsupported calls return `invalid_event_type` instead of reaching Drive.

- [ ] **Step 4: Replace `index.js` routing with one branch**

```javascript
if (message.params?.name !== "submit_event") {
  return error(message.id, -32601, "Tool not implemented");
}
const value = await dispatchSubmitEvent(env, args, deps);
return result(message.id, {
  content: [{ type: "text", text: JSON.stringify(value) }]
});
```

Map `ProtocolError` to JSON-RPC `-32602`; preserve unexpected Drive/service errors as `-32603`.

- [ ] **Step 5: Run the focused suite and verify GREEN**

Run: `node --test cloud-mcp/test/mcp.test.js`

Expected: PASS for one-tool listing, authorization, removed-tool rejection, and envelope validation.

- [ ] **Step 6: Commit the protocol boundary**

```powershell
git add cloud-mcp/src/protocol.js cloud-mcp/src/submit-event.js cloud-mcp/src/index.js cloud-mcp/test/mcp.test.js
git commit -m "refactor: expose only submit-event MCP tool"
```

---

### Task 2: Replace Candidate-Specific Drive Code with JSON Repository Primitives

**Files:**
- Modify: `cloud-mcp/src/google-drive.js`
- Modify: `cloud-mcp/test/google-drive.test.js`

**Interfaces:**
- Consumes: `GOOGLE_DRIVE_FOLDER_ID`, service-account credentials, parent folder IDs, exact child names, and JSON objects.
- Produces: `createDriveRepository(env, deps)` with `listChildren`, `findFolder`, `ensureFolder`, `createJson`, `readJson`, and `listJson` methods.

- [ ] **Step 1: Write failing repository tests**

```javascript
test("createJson reads the created file back with its parent", async () => {
  const calls = [];
  const repository = createDriveRepository(env, {
    uploadFile: async (parentId, name, content, mimeType) => {
      calls.push({ parentId, name, content, mimeType });
      return { id: "event-file-1", name, parents: [parentId] };
    },
    readJsonFile: async (fileId) => ({
      id: fileId,
      name: "event-11111111-1111-4111-8111-111111111111.json",
      parents: ["events-folder"],
      value: { schemaVersion: "1.2", eventId: "11111111-1111-4111-8111-111111111111" }
    })
  });
  const created = await repository.createJson(
    "events-folder",
    "event-11111111-1111-4111-8111-111111111111.json",
    { schemaVersion: "1.2", eventId: "11111111-1111-4111-8111-111111111111" }
  );
  assert.deepEqual(created.parents, ["events-folder"]);
  assert.equal(calls[0].mimeType, "application/json");
});

test("repository never falls back to the configured root for an unknown parent", async () => {
  const repository = createDriveRepository(env, {
    uploadFile: async () => { throw new Error("must not write"); }
  });
  await assert.rejects(
    () => repository.createJson("", "identity.json", { schemaVersion: "1.2" }),
    /parentId/
  );
});
```

- [ ] **Step 2: Run the Drive suite and verify RED**

Run: `node --test cloud-mcp/test/google-drive.test.js`

Expected: FAIL because `createDriveRepository` does not exist and current exports are candidate-name operations.

- [ ] **Step 3: Implement the generic repository**

Keep `accessToken`, `googleGet`, `googleUpload`, `withSharedDriveSupport`, and Drive error formatting. Add exact-name folder queries scoped to a verified parent and generic JSON reads:

```javascript
export function createDriveRepository(env, deps = {}) {
  const createFolderImpl = deps.createFolder ?? ((parentId, name) =>
    googleUpload(env, parentId, name, "", "application/vnd.google-apps.folder", deps.fetch ?? fetch));
  const uploadFileImpl = deps.uploadFile ?? ((parentId, name, content, mimeType) =>
    googleUpload(env, parentId, name, content, mimeType, deps.fetch ?? fetch));

  return {
    rootFolderId: env.GOOGLE_DRIVE_FOLDER_ID,
    async ensureFolder(parentId, name) {
      if (!parentId || !name || name.includes("/") || name.includes("\\")) throw new Error("invalid folder input");
      const matches = await this.listChildren(parentId, { name, foldersOnly: true });
      if (matches.length > 0) return matches[0];
      const created = await createFolderImpl(parentId, name);
      if (!created?.id) throw new Error("Google Drive write failed: missing folder id");
      return { ...created, name, parents: [parentId] };
    },
    async createJson(parentId, name, value) {
      if (!parentId || !/^((identity)|(registration-[0-9a-f-]+)|(event-[0-9a-f-]+)|(snapshot-[0-9TZ:.-]+-[0-9a-f-]+))\.json$/i.test(name)) {
        throw new Error("invalid JSON target");
      }
      const file = await uploadFileImpl(parentId, name, JSON.stringify(value), "application/json");
      if (!file?.id) throw new Error("Google Drive write failed: missing file id");
      return this.readJson(file.id);
    }
  };
}
```

Implement `listChildren`, `listJson`, and `readJson` with Drive `fields` including `id,name,mimeType,parents,createdTime`; `readJson` fetches `alt=media`, parses JSON, and returns `{id,name,parents,createdTime,value}`.

- [ ] **Step 4: Remove candidate-specific exports and update tests**

Delete `findOrCreateCandidateFolder`, `listCandidates`, `getCandidateContext`, and `readArtifact` after `index.js` no longer imports them. Preserve Shared Drive URL tests and add tests for exact-parent queries, malformed JSON, missing file IDs, and read failures.

- [ ] **Step 5: Run the Drive suite and verify GREEN**

Run: `node --test cloud-mcp/test/google-drive.test.js`

Expected: PASS with no candidate-name API remaining.

- [ ] **Step 6: Commit the Drive repository**

```powershell
git add cloud-mcp/src/google-drive.js cloud-mcp/test/google-drive.test.js
git commit -m "refactor: add append-only Drive JSON repository"
```

---

### Task 3: Implement Namespace-Scoped Identity Creation and Verification

**Files:**
- Create: `cloud-mcp/src/namespace-store.js`
- Create: `cloud-mcp/test/namespace-store.test.js`
- Modify: `cloud-mcp/src/submit-event.js`

**Interfaces:**
- Consumes: `createNamespaceStore({ namespace, drive, now, uuid })`, normalized usernames, and optional `{userId, username}` bindings.
- Produces: `listIdentities()`, `createIdentity({username})`, and `verifyIdentity({userId, username})`.

- [ ] **Step 1: Write failing identity tests**

```javascript
test("identity creation writes registration last and returns a verified binding", async () => {
  const operations = [];
  const store = createNamespaceStore({
    namespace: "interview",
    drive: fakeDrive(operations),
    now: () => "2026-08-14T00:00:00.000Z",
    uuid: () => "11111111-1111-4111-8111-111111111111"
  });
  const result = await store.createIdentity({ username: " 乔炳源 " });
  assert.equal(result.status, "ok");
  assert.deepEqual(result.identity, {
    userId: "11111111-1111-4111-8111-111111111111",
    username: "乔炳源"
  });
  assert.equal(operations.at(-1).name, "registration-11111111-1111-4111-8111-111111111111.json");
});

test("identity verification rejects a wrong parent", async () => {
  const store = createNamespaceStore({ namespace: "interview", drive: fakeDriveWithWrongIdentityParent() });
  await assert.rejects(
    () => store.verifyIdentity({ userId: "11111111-1111-4111-8111-111111111111", username: "乔炳源" }),
    /identity_mismatch/
  );
});

test("duplicate active usernames return username_conflict", async () => {
  const store = createNamespaceStore({ namespace: "interview", drive: fakeDriveWithDuplicateRegistrations() });
  await assert.rejects(() => store.createIdentity({ username: "乔炳源" }), /username_conflict/);
});
```

- [ ] **Step 2: Run the identity suite and verify RED**

Run: `node --test cloud-mcp/test/namespace-store.test.js`

Expected: FAIL because the namespace store and fake helpers are absent.

- [ ] **Step 3: Implement namespace roots and registration filtering**

```javascript
const normalizeUsername = (value) => value.normalize("NFKC").trim();

export function createNamespaceStore({ namespace, drive, now = () => new Date().toISOString(), uuid = () => crypto.randomUUID() }) {
  if (!new Set(["algorithm", "interview"]).has(namespace)) throw new Error("invalid_namespace");

  async function roots({ create }) {
    const root = create
      ? await drive.ensureFolder(drive.rootFolderId, namespace)
      : await drive.findFolder(drive.rootFolderId, namespace);
    if (!root) return null;
    const registry = create ? await drive.ensureFolder(root.id, "user-registry") : await drive.findFolder(root.id, "user-registry");
    const users = create ? await drive.ensureFolder(root.id, "users") : await drive.findFolder(root.id, "users");
    return { root, registry, users };
  }
```

`listIdentities` reads only `registration-*.json`, accepts only schema `1.2`, status `active`, UUID `userId`, non-empty `username`, and a parent equal to the registry folder. It returns `{status:"ok", data:{registrations:[...]}}` sorted by `createdAt`.

- [ ] **Step 4: Implement create and verify with readback**

Creation order is `users/<userId>` folder, `events`, `profile`, `profile/snapshots`, `identity.json`, identity readback validation, a second username-conflict check, then registration creation/readback. Verification finds exactly one `users/<userId>` folder and exactly one `identity.json`, then validates schema, ID, normalized username, and parent.

- [ ] **Step 5: Register the three identity event types**

```javascript
handlers["identity.list"] = ({ namespace }) => namespaceStore(namespace).listIdentities();
handlers["identity.create"] = ({ namespace, payload }) => namespaceStore(namespace).createIdentity(payload);
handlers["identity.verify"] = ({ namespace, identity }) => namespaceStore(namespace).verifyIdentity(identity);
```

- [ ] **Step 6: Run identity and MCP suites**

Run: `node --test cloud-mcp/test/namespace-store.test.js cloud-mcp/test/mcp.test.js`

Expected: PASS, including empty registries, duplicate names, registration-last ordering, parent mismatches, and both allowed namespaces.

- [ ] **Step 7: Commit the identity gate**

```powershell
git add cloud-mcp/src/namespace-store.js cloud-mcp/src/submit-event.js cloud-mcp/test/namespace-store.test.js
git commit -m "feat: add submit-event identity gate"
```

---

### Task 4: Add Immutable Event Storage and Cross-Conversation Session Reads

**Files:**
- Create: `cloud-mcp/src/event-store.js`
- Create: `cloud-mcp/src/interview-store.js`
- Create: `cloud-mcp/test/event-store.test.js`
- Create: `cloud-mcp/test/interview-store.test.js`
- Modify: `cloud-mcp/src/protocol.js`
- Modify: `cloud-mcp/src/submit-event.js`

**Interfaces:**
- Consumes: verified `{userId, username}`, schema-1.2 session events, `sessionId`, and Drive event folders.
- Produces: `appendEvent(identity, event)`, `listVerifiedEvents(identity)`, `listSessions(identity)`, and `loadSession(identity, sessionId)`.

- [ ] **Step 1: Write failing idempotency and session-isolation tests**

```javascript
test("same event key and content reuses the earliest verified event", async () => {
  const store = createEventStore({ namespaceStore, drive, canonicalHash });
  const first = await store.appendEvent(identity, sessionEvent);
  const second = await store.appendEvent(identity, structuredClone(sessionEvent));
  assert.equal(second.receipt.fileId, first.receipt.fileId);
  assert.equal(drive.createdJsonFiles.length, 1);
});

test("same event key with different content is rejected", async () => {
  const store = createEventStore({ namespaceStore, drive, canonicalHash });
  await store.appendEvent(identity, sessionEvent);
  await assert.rejects(
    () => store.appendEvent(identity, { ...sessionEvent, domain: "distributed-systems" }),
    /event_key_conflict/
  );
});

test("one user cannot load another user's session", async () => {
  await assert.rejects(
    () => interviewStore.loadSession(otherIdentity, sessionEvent.sessionId),
    /not_found/
  );
});
```

- [ ] **Step 2: Run event tests and verify RED**

Run: `node --test cloud-mcp/test/event-store.test.js cloud-mcp/test/interview-store.test.js`

Expected: FAIL because append-only event storage and session queries do not exist.

- [ ] **Step 3: Add canonical JSON and SHA-256 hashing**

`canonicalJson` recursively sorts object keys, preserves array order, and serializes primitives with `JSON.stringify`. `canonicalHash` clones the event, removes `contentHash`, hashes the remaining canonical UTF-8 bytes with `crypto.subtle.digest("SHA-256", bytes)`, and returns lowercase hexadecimal.

Store the computed `contentHash` after hashing. Duplicate comparison repeats the same hash-without-`contentHash` procedure and removes Drive-only metadata; never use `eventKey` as a file name.

- [ ] **Step 4: Implement verified event append/list**

`appendEvent` verifies identity on every call, validates `schemaVersion`, `eventId`, `eventKey`, `eventType`, `userId`, and `username`, lists the bound user's event directory, and keeps the earliest valid event for duplicate keys. New files use only `event-<eventId>.json`. Readback must match event ID, key, hash, identity, and the exact events parent.

- [ ] **Step 5: Implement session list/load**

`listSessions` filters verified `interview.session.completed` events and returns only `sessionId`, `interviewType`, `domain`, `completedAt`, and whether a valid review exists. `loadSession` validates a `MOCK-` or `REAL-` session ID and returns the selected session plus its verified review versions, sorted numerically.

- [ ] **Step 6: Register session event types**

```javascript
handlers["interview.session.list"] = ({ identity }) => interviewStore.listSessions(identity);
handlers["interview.session.load"] = ({ identity, payload }) => interviewStore.loadSession(identity, payload.sessionId);
handlers["interview.session.completed"] = ({ identity, payload }) => interviewStore.submitSession(identity, payload.event);
```

- [ ] **Step 7: Run focused and combined JavaScript tests**

Run: `node --test cloud-mcp/test/event-store.test.js cloud-mcp/test/interview-store.test.js cloud-mcp/test/mcp.test.js`

Expected: PASS for retry, conflict, readback, cross-user isolation, session summary, version ordering, and invalid session IDs.

- [ ] **Step 8: Commit event and session storage**

```powershell
git add cloud-mcp/src/protocol.js cloud-mcp/src/event-store.js cloud-mcp/src/interview-store.js cloud-mcp/src/submit-event.js cloud-mcp/test/event-store.test.js cloud-mcp/test/interview-store.test.js
git commit -m "feat: persist immutable interview session events"
```

---

### Task 5: Rebuild Interview Profiles from Approved Review Events

**Files:**
- Create: `cloud-mcp/src/profile-model.js`
- Create: `cloud-mcp/test/profile-model.test.js`
- Modify: `cloud-mcp/src/interview-store.js`
- Modify: `cloud-mcp/test/interview-store.test.js`
- Modify: `cloud-mcp/src/submit-event.js`

**Interfaces:**
- Consumes: verified `interview.review.completed` events.
- Produces: `rebuildInterviewProfile(events)`, append-only snapshot JSON, and `ok` or `profile_cache_pending` responses.

- [ ] **Step 1: Write failing profile-source and recovery tests**

```javascript
test("session events and report prose do not change the profile", () => {
  const snapshot = rebuildInterviewProfile([
    sessionEvent,
    { ...approvedReview, applyProfileChanges: false },
    {
      ...approvedReview,
      eventId: "33333333-3333-4333-8333-333333333333",
      eventKey: "review-2",
      profileChanges: [],
      narrative: "擅长所有并发问题"
    }
  ]);
  assert.deepEqual(snapshot.domainProfiles, {});
});

test("a weakness closes only after two sessions and two variants pass", () => {
  const snapshot = rebuildInterviewProfile([failedReview, passedReviewA, passedReviewSameVariant, passedReviewB]);
  assert.equal(snapshot.domainProfiles.java_backend.weaknesses["W-001"].status, "closed");
  assert.deepEqual(
    snapshot.domainProfiles.java_backend.weaknesses["W-001"].passingVariantIds.sort(),
    ["scenario-a", "scenario-b"]
  );
});

test("snapshot failure preserves the verified review receipt", async () => {
  const result = await interviewStore.submitReview(identity, reviewEvent, {
    createSnapshot: async () => { throw new Error("Drive unavailable"); }
  });
  assert.equal(result.status, "profile_cache_pending");
  assert.equal(result.receipt.eventKey, reviewEvent.eventKey);
});
```

- [ ] **Step 2: Run profile tests and verify RED**

Run: `node --test cloud-mcp/test/profile-model.test.js cloud-mcp/test/interview-store.test.js`

Expected: FAIL because profile reconstruction and review submission are missing.

- [ ] **Step 3: Implement the pure profile reducer**

Accept only schema-1.2 review events with `applyProfileChanges === true`. Sort by `completedAt`, then `eventId`; apply structured `profileChanges` only. Track weakness evidence by domain, session ID, variant ID, evidence reference, and confidence. A failure opens a weakness; passing evidence moves it to `improving`; at least two distinct passing sessions and variants closes it.

Return:

```javascript
{
  schemaVersion: "1.2",
  userId,
  username,
  generatedAt,
  headEventId,
  sourceEventKeys,
  domainProfiles,
  generalCompetencies
}
```

- [ ] **Step 4: Append review first, then create/read back a snapshot**

`submitReview` validates that the source session belongs to the same user and that `reviewVersion` matches the event key. It appends and reads back the review before profile work. It then rebuilds from every verified review event and creates `snapshot-<UTC-safe>-<headEventId>.json` under the verified snapshots folder.

If review append/readback fails, throw `cloud_persistence_pending`. If only snapshot creation/readback fails, return `{status:"profile_cache_pending", receipt, data:{profileRebuildRequired:true}}`. A real review first saved with `applyProfileChanges:false` stays immutable; later user approval creates the next review version with `applyProfileChanges:true` and never rewrites the pending event.

- [ ] **Step 5: Register review submission**

```javascript
handlers["interview.review.completed"] = ({ identity, payload }) =>
  interviewStore.submitReview(identity, payload.event);
```

- [ ] **Step 6: Run the full Cloud MCP suite**

Run: `npm test --prefix cloud-mcp`

Expected: PASS with event-source isolation, real-review pending behavior, versioned corrections, weakness closure, snapshot readback, and cache-failure recovery.

- [ ] **Step 7: Commit review and profile persistence**

```powershell
git add cloud-mcp/src/profile-model.js cloud-mcp/src/interview-store.js cloud-mcp/src/submit-event.js cloud-mcp/test/profile-model.test.js cloud-mcp/test/interview-store.test.js
git commit -m "feat: rebuild interview profiles from review events"
```

---

### Task 6: Migrate Algorithm Identity and Learning Events to the Same Tool

**Files:**
- Modify: `algorithm-learning/SKILL.md`
- Modify: `algorithm-learning/tests/test_skill_contract.py`
- Modify: `cloud-mcp/src/submit-event.js`
- Modify: `cloud-mcp/test/mcp.test.js`

**Interfaces:**
- Consumes: algorithm `identity.*` envelopes and `algorithm.learning.completed` events.
- Produces: algorithm identity selection/verification and append-only learning events without any removed MCP call.

- [ ] **Step 1: Add failing static and MCP compatibility tests**

```python
def test_algorithm_uses_only_submit_event_for_persistence(self):
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    self.assertIn("identity.list", skill)
    self.assertIn("identity.create", skill)
    self.assertIn("identity.verify", skill)
    self.assertIn("algorithm.learning.completed", skill)
    self.assertIn("submit_event", skill)
    for removed in ("find_or_create_candidate", "list_candidates", "submit_artifact"):
        self.assertNotIn(removed, skill)
```

Add an MCP test that submits a verified schema-1.2 algorithm event and asserts it is written under `algorithm/users/<userId>/events/`.

- [ ] **Step 2: Run tests and verify RED**

Run: `python -m unittest algorithm-learning.tests.test_skill_contract -v`

Run: `node --test cloud-mcp/test/mcp.test.js`

Expected: FAIL because the Skill still calls `find_or_create_candidate` and the algorithm event handler is absent.

- [ ] **Step 3: Rewrite only the algorithm identity/persistence sections**

New conversations temporarily hold the first request, call `submit_event` with `namespace:"algorithm", eventType:"identity.list"`, show `A/B/新建`, and verify or create before answering. Subsequent calls use the bound `{userId,username}`. Learning completion submits:

```json
{
  "schemaVersion": "1.2",
  "namespace": "algorithm",
  "eventType": "algorithm.learning.completed",
  "identity": {"userId": "UUID", "username": "用户名"},
  "payload": {"event": {"schemaVersion": "1.2", "eventId": "UUID", "eventKey": "<userId>:algorithm-learning:<problem-slug>:<ISO-8601>"}},
  "requestId": "UUID"
}
```

Preserve the existing Chinese coaching, progressive hints, minimal-change debugging, evidence rules, and answer-level control verbatim.

- [ ] **Step 4: Route algorithm learning events through the generic event store**

Verify namespace identity, require `eventType:"algorithm.learning.completed"`, and append under the algorithm user's events folder. Return a real Drive receipt; do not invoke interview profile logic.

- [ ] **Step 5: Run algorithm and MCP tests**

Run: `python -m unittest discover -s algorithm-learning/tests -v`

Run: `npm test --prefix cloud-mcp`

Expected: PASS and no published Skill references a removed MCP tool.

- [ ] **Step 6: Commit algorithm compatibility**

```powershell
git add algorithm-learning/SKILL.md algorithm-learning/tests/test_skill_contract.py cloud-mcp/src/submit-event.js cloud-mcp/test/mcp.test.js
git commit -m "refactor: route algorithm identity through submit-event"
```

---

### Task 7: Refactor the Mock Interview Skill and Local Session JSON

**Files:**
- Modify: `conducting-java-backend-mock-interviews/SKILL.md`
- Modify: `conducting-java-backend-mock-interviews/scripts/mock_handoff.py`
- Modify: `conducting-java-backend-mock-interviews/tests/test_mock_handoff.py`
- Modify: `conducting-java-backend-mock-interviews/tests/test_cross_skill_contract.py`
- Modify: `conducting-java-backend-mock-interviews/schemas/contracts.schema.json`
- Modify: `reviewing-java-backend-interviews/schemas/contracts.schema.json`

**Interfaces:**
- Consumes: verified `{userId, username}`, question records, timestamps, a UUID source, cloud status, and an optional receipt.
- Produces: `create_mock_session_event(...)` and `save_session_copy(...)` with schema-1.2 camelCase JSON.

- [ ] **Step 1: Replace candidate-lock tests with failing identity/event tests**

```python
def test_unverified_identity_cannot_create_session_event(self) -> None:
    with self.assertRaisesRegex(HandoffValidationError, "verified identity"):
        create_mock_session_event(
            {"userId": USER_ID, "username": "乔炳源", "verified": False},
            [],
            started_at="2026-08-14T00:00:00Z",
            completed_at="2026-08-14T00:30:00Z",
            event_id="11111111-1111-4111-8111-111111111111",
            session_id="MOCK-20260814T000000Z-22222222-2222-4222-8222-222222222222",
        )

def test_session_copy_uses_the_required_local_path(self) -> None:
    path = save_session_copy(event, output_root, "ok", {"fileId": "drive-1"})
    self.assertEqual(
        path,
        output_root / "interview" / USER_ID / f"interview-{event['sessionId']}-session.json",
    )
    saved = json.loads(path.read_text(encoding="utf-8"))
    self.assertEqual(saved["persistenceStatus"], "ok")
```

- [ ] **Step 2: Run the conducting suite and verify RED**

Run: `python -m unittest discover -s conducting-java-backend-mock-interviews/tests -v`

Expected: FAIL because helpers use candidate IDs, schema 1.0, Markdown transcript checksums, and old output concepts.

- [ ] **Step 3: Replace the shared schema copies with schema 1.2**

Define byte-identical `$defs` for `Identity`, `Registration`, `Question`, `SessionEvent`, `QuestionReview`, `ReviewEvent`, and `ProfileSnapshot`. Require UUID IDs, camelCase fields, session prefixes, `applyProfileChanges`, evidence fields, and structured `profileChanges`. Reject path separators in session IDs.

- [ ] **Step 4: Implement the deterministic session event**

```python
def create_mock_session_event(identity, questions, *, started_at, completed_at, event_id, session_id):
    _assert_verified_identity(identity)
    return {
        "schemaVersion": "1.2",
        "eventId": event_id,
        "eventKey": f"{identity['userId']}:interview:session:{session_id}:v1",
        "eventType": "interview.session.completed",
        "userId": identity["userId"],
        "username": identity["username"],
        "sessionId": session_id,
        "interviewType": "mock",
        "domain": "java-backend",
        "startedAt": started_at,
        "completedAt": completed_at,
        "status": "review_pending",
        "resumeContext": {"used": False, "source": "current_conversation", "claims": []},
        "questions": deepcopy(questions),
    }
```

Keep question-source distribution and the 40% weakness-retest ceiling. Store original answers and follow-up timelines inside `questions`; do not create a Markdown transcript.

- [ ] **Step 5: Implement local session JSON and rewrite the Skill**

`save_session_copy` writes UTF-8 JSON under the required path and adds only `persistenceStatus` and `driveReceipt` outside the core event. The Skill performs the new-conversation A/B/new identity gate, runs the interview, calls one `submit_event(interview.session.completed)`, then writes the local copy. Cloud failure still writes the local copy with `cloud_persistence_pending`.

- [ ] **Step 6: Run conducting and cross-skill tests**

Run: `python -m unittest discover -s conducting-java-backend-mock-interviews/tests -v`

Expected: PASS, including byte-identical schema copies, identity rejection, original answer preservation, local path, cloud-pending metadata, and no old MCP/tool/artifact language.

- [ ] **Step 7: Commit the mock interview refactor**

```powershell
git add conducting-java-backend-mock-interviews reviewing-java-backend-interviews/schemas/contracts.schema.json
git commit -m "refactor: submit mock interviews as JSON events"
```

---

### Task 8: Refactor Review Events and Generate Local JSON/Word Reports

**Files:**
- Modify: `reviewing-java-backend-interviews/SKILL.md`
- Modify: `reviewing-java-backend-interviews/scripts/interview_core.py`
- Modify: `reviewing-java-backend-interviews/scripts/create_review_report.py`
- Modify: `reviewing-java-backend-interviews/tests/test_interview_core.py`
- Modify: `reviewing-java-backend-interviews/tests/test_create_review_report.py`
- Modify: `reviewing-java-backend-interviews/tests/test_end_to_end.py`

**Interfaces:**
- Consumes: verified identity, a loaded schema-1.2 session event, structured question reviews/profile changes, cloud status, and receipt.
- Produces: `create_review_event(...)`, `save_review_json(...)`, and `create_review_report(report_json, report_docx)`.

- [ ] **Step 1: Write failing review-event and local-output tests**

```python
def test_real_review_without_confirmation_cannot_apply_profile_changes(self) -> None:
    event = create_review_event(
        identity,
        real_session,
        question_reviews=[],
        profile_changes=[{"kind": "weakness", "weaknessId": "W-001", "outcome": "failed"}],
        recommendations=["复测缓存一致性"],
        apply_profile_changes=False,
        review_version=1,
        event_id="33333333-3333-4333-8333-333333333333",
        completed_at="2026-08-14T01:00:00Z",
    )
    self.assertFalse(event["applyProfileChanges"])

def test_report_json_is_the_only_docx_input(self) -> None:
    report_json = save_review_json(review_event, output_root, "ok", {"fileId": "drive-review-1"})
    report_docx = report_json.with_suffix(".docx")
    create_review_report(report_json, report_docx)
    self.assertTrue(report_docx.exists())
    self.assertIn("缓存一致性", "\n".join(p.text for p in Document(report_docx).paragraphs))
```

- [ ] **Step 2: Run review tests and verify RED**

Run: `python -m unittest reviewing-java-backend-interviews.tests.test_interview_core reviewing-java-backend-interviews.tests.test_create_review_report -v`

Expected: FAIL because current helpers require candidate IDs, separate profile-update artifacts, schema 1.0, and old report keys.

- [ ] **Step 3: Implement schema-1.2 review construction**

`create_review_event` verifies identity/session equality, review version, evidence type/confidence, question IDs, and the source session event ID. It returns one `interview.review.completed` event containing `questionReviews`, `profileChanges`, `recommendations`, and `applyProfileChanges`. Mock reviews default to true; real reviews must receive an explicit boolean and remain false until user confirmation. If confirmation happens after a false event was saved, create the next immutable review version with `applyProfileChanges:true`.

- [ ] **Step 4: Implement local report JSON**

`save_review_json` writes:

```text
outputs/interview/<userId>/interview-<sessionId>-report.json
```

The JSON contains the complete review event plus `persistenceStatus` and `driveReceipt`. It never reads a snapshot and is never used by the profile reducer.

- [ ] **Step 5: Update the Word renderer to the new JSON contract**

At execution time, read the Documents references `references/design_presets.md`, `references/header_templates.md`, `tasks/create_edit.md`, and `tasks/verify_render.md`. Use `standard_business_brief` with US Letter, 1-inch margins, explicit styles, real headings/lists, and explicit DXA table geometry. Render identity/session metadata, evidence quality, overall assessment, per-question review, structured profile changes, and next-interview recommendations. Do not render cloud implementation details or treat missing snapshot data as missing report content.

Immediately before the first execution-time Word authoring command, call `codex_app__load_workspace_dependencies`, use the returned absolute Node and Python executables, and run the Documents artifact marker exactly once with `--operation-kind create --expected-output-count 1 --output-format docx`. After generating a fixture DOCX, assign the returned Python path to `$workspacePython` and render with the bundled renderer:

```powershell
& $workspacePython C:\Users\27846\.codex\plugins\cache\openai-primary-runtime\documents\26.813.12317\skills\documents\render_docx.py reviewing-java-backend-interviews\tests\output\interview-test-report.docx --output_dir reviewing-java-backend-interviews\tests\output\rendered
```

Inspect every `page-*.png` at 100% zoom. Fix and repeat until there is no clipping, overlap, broken table, missing glyph, or header/footer defect. If only LibreOffice is unavailable, record the structural-only fallback in the test report; other renderer failures must be fixed.

- [ ] **Step 6: Rewrite the reviewing Skill flow**

The Skill performs identity list/verify, session list/load, review generation, one `submit_event(interview.review.completed)`, local report JSON, Word generation, and render verification. It distinguishes `cloud_persistence_pending`, `profile_cache_pending`, and Word failure. It never mentions or calls candidate/artifact tools, direct Drive, Markdown transcript upload, Base64, or cloud DOCX.

- [ ] **Step 7: Run review tests and inspect the fixture render**

Run: `python -m unittest discover -s reviewing-java-backend-interviews/tests -v`

Expected: PASS for real/mock confirmation, immutable review versions, local paths, JSON-source Word generation, report sections, and error isolation; all rendered fixture pages pass visual inspection.

- [ ] **Step 8: Commit the review/report refactor**

```powershell
git add reviewing-java-backend-interviews/SKILL.md reviewing-java-backend-interviews/scripts/interview_core.py reviewing-java-backend-interviews/scripts/create_review_report.py reviewing-java-backend-interviews/tests
git commit -m "refactor: create review events and local Word reports"
```

---

### Task 9: Remove Legacy Paths, Run End-to-End Acceptance, Deploy, and Push

**Files:**
- Modify: `AGENTS.md`
- Modify: `cloud-mcp/README.md`
- Create: `cloud-mcp/test/end-to-end.test.js`
- Modify: `conducting-java-backend-mock-interviews/tests/test_cross_skill_contract.py`
- Delete: `conducting-java-backend-mock-interviews/scripts/create_interview_report.py`
- Delete: `conducting-java-backend-mock-interviews/tests/test_create_interview_report.py`
- Delete: `reviewing-java-backend-interviews/scripts/drive_protocol.py`
- Delete: `reviewing-java-backend-interviews/scripts/storage_protocol.py`
- Delete: `reviewing-java-backend-interviews/tests/test_drive_protocol.py`
- Delete: `reviewing-java-backend-interviews/tests/test_storage_protocol.py`
- Delete: `reviewing-java-backend-interviews/tests/fixtures/cloud_smoke_raw_transcript.md`

**Interfaces:**
- Consumes: the complete one-tool MCP and all three migrated Skills.
- Produces: green local suites, a deployed Worker, one real Shared Drive smoke identity/session/review path, and an updated GitHub branch/PR.

- [ ] **Step 1: Add a failing in-memory end-to-end test**

```javascript
test("new identity, session, new-conversation verification, review, and snapshot complete", async () => {
  const created = await call("identity.create", { username: "验收用户" });
  const identity = created.identity;
  const session = await call("interview.session.completed", { event: sessionEvent(identity) }, identity);
  const verified = await call("identity.verify", {}, identity);
  const listed = await call("interview.session.list", {}, identity);
  const loaded = await call("interview.session.load", { sessionId: SESSION_ID }, identity);
  const reviewed = await call("interview.review.completed", { event: reviewEvent(identity, loaded.data.session) }, identity);
  assert.equal(session.status, "ok");
  assert.equal(verified.status, "ok");
  assert.equal(listed.data.sessions.length, 1);
  assert.equal(reviewed.status, "ok");
  assert.equal(fakeDrive.filesByPrefix("snapshot-").length, 1);
});
```

- [ ] **Step 2: Run the end-to-end test and verify RED if any integration is missing**

Run: `node --test cloud-mcp/test/end-to-end.test.js`

Expected: FAIL on the first missing route, response shape, or directory invariant; fix the integration using the already-tested components, then rerun until PASS.

- [ ] **Step 3: Remove obsolete local-storage/artifact code and update contract scans**

Use `git rm` for the listed obsolete files. Update the cross-skill contract test to scan all three `SKILL.md` files and assert:

```python
for skill in skills:
    self.assertIn("submit_event", skill)
    for removed in (
        "find_or_create_candidate",
        "list_candidates",
        "get_candidate_context",
        "read_artifact",
        "submit_artifact",
        "contentBase64",
        "raw_transcript.md",
    ):
        self.assertNotIn(removed, skill)
```

Update `AGENTS.md` and `cloud-mcp/README.md` with the one-tool envelope, identity A/B/new gate, namespaces, statuses, Shared Drive requirement, local output paths, and explicit no-migration boundary.

- [ ] **Step 4: Run every local test suite**

Run: `npm test --prefix cloud-mcp`

Run: `python -m unittest discover -s algorithm-learning/tests -v`

Run: `python -m unittest discover -s conducting-java-backend-mock-interviews/tests -v`

Run: `python -m unittest discover -s reviewing-java-backend-interviews/tests -v`

Run: `git diff --check`

Expected: all tests PASS, no warnings from project code, and no whitespace errors.

- [ ] **Step 5: Verify the public tool list locally**

Start the Worker locally with its existing secret configuration, call `tools/list`, and assert the returned tool-name array is exactly `["submit_event"]`. Call a removed tool and verify JSON-RPC `-32601`.

- [ ] **Step 6: Deploy the Cloudflare Worker**

Run from `cloud-mcp`:

```powershell
npx wrangler deploy
```

Expected: successful deployment of `reliable-drive-sync` with the production URL `https://reliable-drive-sync.qiaobingyuan886.workers.dev`.

- [ ] **Step 7: Run a real Shared Drive smoke flow with a new test identity**

Use PowerShell to create a unique username and call `identity.create`, `identity.verify`, `interview.session.completed`, `interview.session.load`, and `interview.review.completed` through the production URL. Use the existing bearer secret from `$env:MCP_BEARER_TOKEN`; never print it.

Verify the Drive readbacks show:

```text
interview/user-registry/registration-<userId>.json
interview/users/<userId>/identity.json
interview/users/<userId>/events/event-<sessionEventId>.json
interview/users/<userId>/events/event-<reviewEventId>.json
interview/users/<userId>/profile/snapshots/snapshot-<UTC>-<reviewEventId>.json
```

Create the smoke username with the exact PowerShell expression below so retries do not collide:

```powershell
$smokeUsername = "自动验收用户-$([DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ'))"
```

Do not delete the append-only smoke records. Confirm that no old root-level name folder was read or changed.

- [ ] **Step 8: Commit cleanup and acceptance documentation**

```powershell
git add -A
git commit -m "test: verify submit-event interview lifecycle"
```

- [ ] **Step 9: Push the branch and update the existing draft PR**

```powershell
git push origin cloud-candidate-mcp
```

Expected: draft PR `#5` contains the design, this plan, all implementation commits, green test evidence, deployment URL, and Shared Drive smoke results.

---

## Final Verification Checklist

- [ ] `tools/list` exposes only `submit_event`.
- [ ] Algorithm, mock interview, and review Skills contain no removed MCP calls.
- [ ] New conversations show minimal identity choices and reverify before data access.
- [ ] Identity creation writes and verifies registration last.
- [ ] Session and review events are full schema-1.2 JSON and are readable in a later conversation.
- [ ] Same event retries reuse the earliest valid file; conflicting content is rejected.
- [ ] Session events and report prose cannot alter profiles.
- [ ] Approved review changes rebuild a new immutable snapshot.
- [ ] Cloud event failure still leaves a local JSON with truthful pending status.
- [ ] Snapshot failure returns `profile_cache_pending` without losing the review event.
- [ ] Report JSON generates a visually verified local Word file.
- [ ] Drive contains no uploaded Markdown, Base64 payload artifact, or DOCX report.
- [ ] Old name folders remain untouched and unscanned.
- [ ] All JavaScript and Python suites pass and the Worker production smoke flow succeeds.
