import assert from "node:assert/strict";
import test from "node:test";
import { handleRequest } from "../src/index.js";
import { validateEnvelope } from "../src/protocol.js";

function env() {
  return { MCP_BEARER_TOKEN: "secret", GOOGLE_DRIVE_FOLDER_ID: "root" };
}

function request(method, params, token = "secret") {
  return new Request("https://example.test/mcp", {
    method: "POST",
    headers: { authorization: `Bearer ${token}`, "content-type": "application/json" },
    body: JSON.stringify({ jsonrpc: "2.0", id: 1, method, params })
  });
}

function algorithmDrive() {
  const folders = new Map();
  const files = new Map();
  let sequence = 0;
  const children = (parentId, name) => [...folders.values(), ...files.values()]
    .filter((item) => item.parents?.length === 1 && item.parents[0] === parentId && (!name || item.name === name));
  return {
    rootFolderId: "root",
    folders,
    createdJsonFiles: [],
    async findFolder(parentId, name) { return children(parentId, name).find((item) => item.mimeType === "application/vnd.google-apps.folder") ?? null; },
    async ensureFolder(parentId, name) {
      const found = await this.findFolder(parentId, name);
      if (found) return found;
      const folder = { id: `folder-${++sequence}`, name, parents: [parentId], mimeType: "application/vnd.google-apps.folder" };
      folders.set(folder.id, folder);
      return folder;
    },
    async listChildren(parentId, { name, foldersOnly } = {}) {
      return children(parentId, name).filter((item) => !foldersOnly || item.mimeType === "application/vnd.google-apps.folder");
    },
    async listJson(parentId) { return children(parentId).filter((item) => item.mimeType === "application/json"); },
    async createJson(parentId, name, value) {
      const file = { id: `file-${++sequence}`, name, parents: [parentId], mimeType: "application/json", value: structuredClone(value) };
      files.set(file.id, file);
      this.createdJsonFiles.push(file);
      return structuredClone(file);
    },
    async readJson(id) { return structuredClone(files.get(id)); }
  };
}

test("MCP exposes only submit_event", async () => {
  const response = await handleRequest(request("tools/list"), env());
  const payload = await response.json();
  assert.deepEqual(payload.result.tools.map((tool) => tool.name), ["submit_event"]);
  assert.equal(payload.result.tools[0].inputSchema.additionalProperties, false);
  assert.equal(payload.result.tools[0].inputSchema.properties.payload.type, "object");
  assert.deepEqual(payload.result.tools[0].inputSchema.properties.identity.required, ["userId", "username"]);
});

test("MCP rejects an incorrect bearer token", async () => {
  const response = await handleRequest(request("tools/list", {}, "wrong"), env());
  assert.equal(response.status, 401);
});

test("MCP fails closed when the bearer secret is missing", async () => {
  const response = await handleRequest(request("tools/list", {}, "undefined"), {
    GOOGLE_DRIVE_FOLDER_ID: "root"
  });
  assert.equal(response.status, 401);
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
  assert.equal(payload.error.code, -32602);
  assert.match(payload.error.message, /invalid_namespace/);
});

test("submit_event rejects an incomplete session payload", async () => {
  const response = await handleRequest(request("tools/call", {
    name: "submit_event",
    arguments: {
      schemaVersion: "1.2",
      namespace: "interview",
      eventType: "interview.session.load",
      payload: {},
      requestId: "00000000-0000-4000-8000-000000000002"
    }
  }), env());
  const payload = await response.json();
  assert.equal(payload.error.code, -32602);
  assert.match(payload.error.message, /invalid_payload/);
});

test("protocol accepts the identity-bound payload needed to load an interview session", () => {
  assert.deepEqual(validateEnvelope({
    schemaVersion: "1.2",
    namespace: "interview",
    eventType: "interview.session.load",
    payload: { userId: "00000000-0000-4000-8000-000000000001", username: "Ada", sessionId: "MOCK-1" },
    requestId: "00000000-0000-4000-8000-000000000006"
  }).payload, { userId: "00000000-0000-4000-8000-000000000001", username: "Ada", sessionId: "MOCK-1" });
});

test("protocol rejects interview session events in another namespace", () => {
  assert.throws(() => validateEnvelope({
    schemaVersion: "1.2", namespace: "algorithm", eventType: "interview.session.list",
    payload: { userId: "00000000-0000-4000-8000-000000000001", username: "Ada" },
    requestId: "00000000-0000-4000-8000-000000000007"
  }), /invalid_event_type/);
});

test("protocol validates the concrete session event schema at the Worker boundary", () => {
  assert.throws(() => validateEnvelope({
    schemaVersion: "1.2", namespace: "interview", eventType: "interview.session.completed",
    payload: {
      userId: "00000000-0000-4000-8000-000000000001", username: "Ada",
      event: { schemaVersion: "1.2", eventType: "interview.review.completed" }
    },
    requestId: "00000000-0000-4000-8000-000000000009"
  }), /invalid_event/);
});

test("submit_event rejects unknown top-level envelope fields", async () => {
  const response = await handleRequest(request("tools/call", {
    name: "submit_event",
    arguments: {
      schemaVersion: "1.2",
      namespace: "algorithm",
      eventType: "identity.list",
      payload: {},
      requestId: "00000000-0000-4000-8000-000000000004",
      folderId: "drive-folder"
    }
  }), env());
  const payload = await response.json();
  assert.equal(payload.error.code, -32602);
  assert.match(payload.error.message, /invalid_envelope/);
});

for (const field of ["folderId", "path", "mimeType", "contentBase64", "markdown", "docx"]) {
  test(`submit_event rejects the ${field} payload control field`, async () => {
    const response = await handleRequest(request("tools/call", {
      name: "submit_event",
      arguments: {
        schemaVersion: "1.2",
        namespace: "algorithm",
        eventType: "identity.list",
        payload: { [field]: "untrusted-content" },
        requestId: "00000000-0000-4000-8000-000000000005"
      }
    }), env());
    const payload = await response.json();
    assert.equal(payload.error.code, -32602);
    assert.match(payload.error.message, /invalid_payload/);
  });
}

test("submit_event dispatches the validated envelope to its event handler", async () => {
  const response = await handleRequest(request("tools/call", {
    name: "submit_event",
    arguments: {
      schemaVersion: "1.2",
      namespace: "algorithm",
      eventType: "identity.list",
      payload: {},
      requestId: "00000000-0000-4000-8000-000000000003"
    }
  }), env(), {
    handlers: {
      "identity.list": async (_env, envelope) => ({ received: envelope })
    }
  });
  const payload = await response.json();
  assert.deepEqual(JSON.parse(payload.result.content[0].text), {
    received: {
      schemaVersion: "1.2",
      namespace: "algorithm",
      eventType: "identity.list",
      payload: {},
      requestId: "00000000-0000-4000-8000-000000000003"
    }
  });
});

test("algorithm learning events use the algorithm namespace event folder", async () => {
  const drive = algorithmDrive();
  const identity = { userId: "00000000-0000-4000-8000-000000000001", username: "算法用户" };
  const event = {
    schemaVersion: "1.2",
    eventId: "10000000-0000-4000-8000-000000000001",
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
  const response = await handleRequest(request("tools/call", {
    name: "submit_event",
    arguments: {
      schemaVersion: "1.2",
      namespace: "algorithm",
      eventType: "algorithm.learning.completed",
      identity,
      payload: { event },
      requestId: "00000000-0000-4000-8000-000000000008"
    }
  }), env(), {
    drive,
    namespaceStores: { algorithm: { verifyIdentity: async (value) => ({ status: "ok", identity: structuredClone(value) }) } }
  });
  const payload = await response.json();
  assert.equal(payload.result.content[0].type, "text");
  const result = JSON.parse(payload.result.content[0].text);
  assert.equal(result.status, "ok");
  assert.match(result.receipt.fileId, /^file-/);
  const algorithmEventsFile = drive.createdJsonFiles.find((file) => file.name === `event-${event.eventId}.json`);
  const algorithmEventsFolder = algorithmEventsFile && drive.folders.get(algorithmEventsFile.parents[0]);
  assert.ok(algorithmEventsFolder);
  assert.equal(algorithmEventsFolder.name, "events");
  const userFolder = drive.folders.get(algorithmEventsFolder.parents[0]);
  const usersFolder = drive.folders.get(userFolder.parents[0]);
  const namespaceFolder = drive.folders.get(usersFolder.parents[0]);
  assert.equal(usersFolder.name, "users");
  assert.equal(namespaceFolder.name, "algorithm");
  assert.equal(result.event.eventType, "algorithm.learning.completed");
});
