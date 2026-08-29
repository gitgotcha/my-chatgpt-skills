import assert from "node:assert/strict";
import test from "node:test";
import { handleRequest } from "../src/index.js";

const SESSION_EVENT_ID = "22222222-2222-4222-8222-222222222222";
const REVIEW_EVENT_ID = "33333333-3333-4333-8333-333333333333";
const SESSION_ID = "MOCK-20260814T000000Z-44444444-4444-4444-8444-444444444444";

function fakeDrive() {
  const folders = new Map();
  const files = new Map();
  let sequence = 0;
  const childItems = (parentId, name) => [...folders.values(), ...files.values()]
    .filter((item) => item.parents?.length === 1 && item.parents[0] === parentId
      && (!name || item.name === name));
  const folder = (id, name, parentId) => ({
    id, name, parents: [parentId], mimeType: "application/vnd.google-apps.folder"
  });
  return {
    rootFolderId: "root",
    filesByPrefix(prefix) {
      return [...files.values()].filter((file) => file.name.startsWith(prefix));
    },
    async findFolder(parentId, name) {
      return childItems(parentId, name).find((item) => item.mimeType === "application/vnd.google-apps.folder") ?? null;
    },
    async ensureFolder(parentId, name) {
      const existing = await this.findFolder(parentId, name);
      if (existing) return existing;
      const created = folder(`folder-${++sequence}`, name, parentId);
      folders.set(created.id, created);
      return created;
    },
    async listChildren(parentId, { name, foldersOnly } = {}) {
      return childItems(parentId, name)
        .filter((item) => !foldersOnly || item.mimeType === "application/vnd.google-apps.folder");
    },
    async listJson(parentId) {
      return childItems(parentId).filter((item) => item.mimeType === "application/json");
    },
    async createJson(parentId, name, value) {
      const created = {
        id: `file-${++sequence}`,
        name,
        parents: [parentId],
        mimeType: "application/json",
        value: structuredClone(value)
      };
      files.set(created.id, created);
      return structuredClone(created);
    },
    async readJson(id) {
      const file = files.get(id);
      return file ? structuredClone(file) : null;
    }
  };
}

function request(id, eventType, payload, namespace = "interview", identity) {
  return new Request("https://example.test/mcp", {
    method: "POST",
    headers: { authorization: "Bearer secret", "content-type": "application/json" },
    body: JSON.stringify({
      jsonrpc: "2.0",
      id,
      method: "tools/call",
      params: {
        name: "submit_event",
        arguments: {
          schemaVersion: "1.2",
          namespace,
          eventType,
          ...(identity ? { identity } : {}),
          payload,
          requestId: `99999999-9999-4999-8999-${String(id).padStart(12, "0")}`
        }
      }
    })
  });
}

async function call(drive, id, eventType, payload, { namespace, identity } = {}) {
  const response = await handleRequest(request(id, eventType, payload, namespace, identity), {
    MCP_BEARER_TOKEN: "secret",
    GOOGLE_DRIVE_FOLDER_ID: "root"
  }, { drive });
  const body = await response.json();
  assert.equal(response.status, 200);
  assert.equal(body.error, undefined, JSON.stringify(body));
  return JSON.parse(body.result.content[0].text);
}

test("name registration, session, review, and snapshot share one resolved userId", async () => {
  const drive = fakeDrive();
  const name = "验收用户";

  const registered = await call(drive, 1, "system.user-registered", { displayName: name }, { namespace: "system" });
  assert.equal(registered.status, "ok");
  const identity = registered.identity;
  assert.equal(identity.username, name);
  assert.match(identity.userId, /^[0-9a-f-]{36}$/i);

  // Re-submitting the same name must resolve to the same user.
  const reresolved = await call(drive, 7, "system.user-registered", { displayName: ` ${name} ` }, { namespace: "system" });
  assert.equal(reresolved.identity.userId, identity.userId);

  const sessionEvent = {
    schemaVersion: "1.2",
    eventId: SESSION_EVENT_ID,
    eventKey: `${identity.userId}:interview:session:${SESSION_ID}:v1`,
    eventType: "interview.session.completed",
    userId: identity.userId,
    username: identity.username,
    sessionId: SESSION_ID,
    interviewType: "mock",
    domain: "java-backend",
    startedAt: "2026-08-14T00:00:00.000Z",
    completedAt: "2026-08-14T00:30:00.000Z",
    status: "review_pending",
    resumeContext: { used: false, source: "current_conversation", claims: [] },
    questions: []
  };
  const session = await call(drive, 2, "interview.session.completed", { event: sessionEvent }, { identity: { username: name } });
  assert.equal(session.status, "ok");
  assert.equal(session.identity.userId, identity.userId);

  const listed = await call(drive, 4, "interview.session.list", {}, { identity: { username: name } });
  assert.equal(listed.data.sessions.length, 1);
  assert.equal(listed.data.sessions[0].sessionId, SESSION_ID);

  const loaded = await call(drive, 5, "interview.session.load", { sessionId: SESSION_ID }, { identity: { username: name } });
  assert.equal(loaded.data.session.eventId, SESSION_EVENT_ID);

  const reviewEvent = {
    schemaVersion: "1.2",
    eventId: REVIEW_EVENT_ID,
    eventKey: `${identity.userId}:interview:review:${SESSION_ID}:v1`,
    eventType: "interview.review.completed",
    userId: identity.userId,
    username: identity.username,
    sessionId: SESSION_ID,
    reviewVersion: 1,
    interviewType: "mock",
    domain: "java-backend",
    sourceSessionEventId: loaded.data.session.eventId,
    sourceType: "mock",
    evidenceType: "full_transcript",
    evidenceConfidence: "high",
    questionReviews: [],
    profileChanges: [{
      kind: "weakness",
      weaknessId: "W-001",
      domain: "java-backend",
      outcome: "failed",
      evidenceRefs: [SESSION_EVENT_ID],
      variantId: "initial"
    }],
    recommendations: ["复测并发基础"],
    applyProfileChanges: true,
    completedAt: "2026-08-14T01:00:00.000Z"
  };
  const reviewed = await call(drive, 6, "interview.review.completed", { event: reviewEvent }, { identity: { username: name } });
  assert.equal(reviewed.status, "ok", JSON.stringify(reviewed));
  assert.equal(drive.filesByPrefix("snapshot-").length, 1);

  // The same resolved user must be reused by another domain.
  const algorithmEvent = {
    schemaVersion: "1.2",
    eventId: "44444444-4444-4444-8444-444444444444",
    eventKey: `${identity.userId}:algorithm-learning:two-sum:2026-08-14T10:00:00.000Z`,
    eventType: "algorithm.learning.completed",
    userId: identity.userId,
    username: identity.username,
    observedAt: "2026-08-14T10:00:00.000Z",
    source: "qa",
    topic: "two-sum",
    problem: { title: "Two Sum", source: "Hot100", url: "" },
    outcome: "consulted",
    evidence: "用户请求讲解两数之和。",
    tags: ["hash-map"],
    confidence: "medium"
  };
  const algorithm = await call(drive, 8, "algorithm.learning.completed", { event: algorithmEvent }, {
    namespace: "algorithm",
    identity: { username: name }
  });
  assert.equal(algorithm.status, "ok");
  assert.equal(algorithm.identity.userId, identity.userId);
});
