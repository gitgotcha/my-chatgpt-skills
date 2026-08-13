import assert from "node:assert/strict";
import test from "node:test";
import { handleRequest } from "../src/index.js";

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

const candidate = { displayName: "小明", folderId: "folder-1", created: false };

test("MCP tools/list exposes the name-folder entrypoint", async () => {
  const response = await handleRequest(request("tools/list"), env());
  const payload = await response.json();
  assert.equal(payload.result.tools.some((tool) => tool.name === "find_or_create_candidate"), true);
});

test("MCP rejects an incorrect bearer token", async () => {
  const response = await handleRequest(request("tools/list", {}, "wrong"), env());
  assert.equal(response.status, 401);
});

test("MCP finds or creates a user from displayName", async () => {
  const response = await handleRequest(request("tools/call", { name: "find_or_create_candidate", arguments: { displayName: "小明" } }), env(), {
    drive: { findOrCreateCandidateFolder: async () => candidate }
  });
  const payload = await response.json();
  assert.match(payload.result.content[0].text, /folder-1/);
});

test("MCP submit_artifact resolves a name to its Drive folder", async () => {
  let parentId;
  const response = await handleRequest(request("tools/call", { name: "submit_artifact", arguments: {
    displayName: "小明", fileName: "session.json", contentBase64: btoa("{}"), contentType: "application/json"
  } }), env(), { drive: {
    findOrCreateCandidateFolder: async () => candidate,
    uploadDriveFile: async (_env, parent, name) => { parentId = parent; assert.equal(name, "session.json"); return { id: "file-1" }; }
  } });
  const payload = await response.json();
  assert.equal(parentId, "folder-1");
  assert.match(payload.result.content[0].text, /file-1/);
});

test("MCP submit_event resolves a name to its Drive folder", async () => {
  let parentId;
  const response = await handleRequest(request("tools/call", { name: "submit_event", arguments: {
    displayName: "小明", event: { eventKey: "EVT-1" }
  } }), env(), { drive: {
    findOrCreateCandidateFolder: async () => candidate,
    uploadDriveFile: async (_env, parent) => { parentId = parent; return { id: "event-file-1" }; }
  } });
  const payload = await response.json();
  assert.equal(parentId, "folder-1");
  assert.match(payload.result.content[0].text, /event-file-1/);
});

test("MCP get_candidate_context resolves displayName", async () => {
  const response = await handleRequest(request("tools/call", { name: "get_candidate_context", arguments: { displayName: "小明" } }), env(), {
    drive: { getCandidateContext: async () => ({ ...candidate, artifacts: [] }) }
  });
  const payload = await response.json();
  assert.match(payload.result.content[0].text, /folder-1/);
});

test("MCP read_artifact resolves displayName", async () => {
  const response = await handleRequest(request("tools/call", { name: "read_artifact", arguments: { displayName: "小明", artifactKey: "session" } }), env(), {
    drive: { readArtifact: async () => ({ fileId: "file-1", content: "{}" }) }
  });
  const payload = await response.json();
  assert.match(payload.result.content[0].text, /file-1/);
});
