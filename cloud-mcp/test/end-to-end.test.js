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

function request(id, eventType, payload, namespace = "interview") {
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
          payload,
          requestId: `99999999-9999-4999-8999-${String(id).padStart(12, "0")}`
        }
      }
    })
  });
}

async function call(drive, id, eventType, payload) {
  const response = await handleRequest(request(id, eventType, payload), {
    MCP_BEARER_TOKEN: "secret",
    GOOGLE_DRIVE_FOLDER_ID: "root"
  }, { drive });
  const body = await response.json();
  assert.equal(response.status, 200);
  assert.equal(body.error, undefined, JSON.stringify(body));
  return JSON.parse(body.result.content[0].text);
}

test("new identity, session, new-conversation verification, review, and snapshot complete", async () => {
  const drive = fakeDrive();
  const created = await call(drive, 1, "identity.create", { username: "验收用户" });
  assert.equal(created.status, "ok");
  const identity = created.identity;
  assert.equal(identity.username, "验收用户");
  assert.match(identity.userId, /^[0-9a-f-]{36}$/i);

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
  const session = await call(drive, 2, "interview.session.completed", {
    userId: identity.userId, username: identity.username, event: sessionEvent
  });
  assert.equal(session.status, "ok");

  const verified = await call(drive, 3, "identity.verify", identity);
  assert.deepEqual(verified.identity, identity);
  const listed = await call(drive, 4, "interview.session.list", identity);
  assert.equal(listed.data.sessions.length, 1);
  assert.equal(listed.data.sessions[0].sessionId, SESSION_ID);

  const loaded = await call(drive, 5, "interview.session.load", {
    userId: identity.userId, username: identity.username, sessionId: SESSION_ID
  });
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
  const reviewed = await call(drive, 6, "interview.review.completed", {
    userId: identity.userId, username: identity.username, event: reviewEvent
  });
  assert.equal(reviewed.status, "ok", JSON.stringify(reviewed));
  assert.equal(drive.filesByPrefix("snapshot-").length, 1);
});
