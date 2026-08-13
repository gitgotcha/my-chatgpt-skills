import assert from "node:assert/strict";
import test from "node:test";
import { handleRequest } from "../src/index.js";

function env() {
  return {
    MCP_BEARER_TOKEN: "secret",
    GOOGLE_DRIVE_FOLDER_ID: "root"
  };
}

function request(method, params, token = "secret") {
  return new Request("https://example.test/mcp", {
    method: "POST",
    headers: { authorization: `Bearer ${token}`, "content-type": "application/json" },
    body: JSON.stringify({ jsonrpc: "2.0", id: 1, method, params })
  });
}

test("MCP tools/list exposes create_candidate", async () => {
  const response = await handleRequest(request("tools/list"), env(), { uuid: () => "id", now: () => "2026-08-13T00:00:00.000Z" });
  const payload = await response.json();
  assert.equal(payload.result.tools.some((tool) => tool.name === "create_candidate"), true);
});

test("MCP rejects an incorrect bearer token", async () => {
  const response = await handleRequest(request("tools/list", {}, "wrong"), env());
  assert.equal(response.status, 401);
});

test("MCP create_candidate returns the summary written by Drive", async () => {
  const response = await handleRequest(request("tools/call", { name: "create_candidate", arguments: { displayName: "小明" } }), env(), {
    drive: { createCandidateFolder: async () => ({ candidateId: "CAND-id", displayName: "小明", folderId: "folder-1" }) }
  });
  const payload = await response.json();
  assert.match(payload.result.content[0].text, /CAND-id/);
});

test("MCP submit_artifact stops when direct Drive upload fails", async () => {
  const response = await handleRequest(request("tools/call", { name: "submit_artifact", arguments: {
    candidateFolderId: "folder-1", fileName: "session.json", contentBase64: btoa("{}"), contentType: "application/json"
  } }), env(), { drive: { uploadDriveFile: async () => { throw new Error("Drive unavailable"); } } });
  const payload = await response.json();
  assert.equal(payload.error.code, -32603);
});

test("MCP list_candidates returns only Drive summaries", async () => {
  const response = await handleRequest(request("tools/call", { name: "list_candidates", arguments: { query: "小" } }), env(), {
    drive: { listCandidates: async () => [{ candidateId: "CAND-id", displayName: "小明" }] }
  });
  const payload = await response.json();
  assert.match(payload.result.content[0].text, /小明/);
});

test("MCP get_candidate_context passes through the direct Drive result", async () => {
  const response = await handleRequest(request("tools/call", { name: "get_candidate_context", arguments: { candidateId: "CAND-id" } }), env(), {
    drive: { getCandidateContext: async () => ({ candidateId: "CAND-id", folderId: "folder-1", artifacts: [] }) }
  });
  const payload = await response.json();
  assert.match(payload.result.content[0].text, /folder-1/);
});

test("MCP read_artifact returns a direct Drive artifact", async () => {
  const response = await handleRequest(request("tools/call", { name: "read_artifact", arguments: { candidateFolderId: "folder-1", artifactKey: "session" } }), env(), {
    drive: { readArtifact: async () => ({ fileId: "file-1", content: "{}" }) }
  });
  const payload = await response.json();
  assert.match(payload.result.content[0].text, /file-1/);
});

test("MCP submit_event writes the event directly to the confirmed candidate folder", async () => {
  const response = await handleRequest(request("tools/call", { name: "submit_event", arguments: {
    candidateFolderId: "folder-1", event: { eventKey: "EVT-1" }
  } }), env(), { drive: { uploadDriveFile: async () => ({ id: "event-file-1" }) } });
  const payload = await response.json();
  assert.match(payload.result.content[0].text, /event-file-1/);
});
