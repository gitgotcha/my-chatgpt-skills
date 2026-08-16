import assert from "node:assert/strict";
import test from "node:test";
import { deriveWorkerUrl, handleRequest } from "../local-mcp-bridge.mjs";

test("derives Worker origin from the legacy ingress URL", () => {
  assert.equal(deriveWorkerUrl("https://reliable-drive-sync.qiaobingyuan886.workers.dev/v1/jobs"), "https://reliable-drive-sync.qiaobingyuan886.workers.dev");
});

test("tools/list exposes only submit_event", async () => {
  const response = await handleRequest({ jsonrpc: "2.0", id: 1, method: "tools/list" });
  assert.deepEqual(response.result.tools.map(({ name }) => name), ["submit_event"]);
  assert.equal(response.result.tools[0].inputSchema.additionalProperties, false);
});

test("legacy tool names are rejected", async () => {
  const response = await handleRequest({ jsonrpc: "2.0", id: 2, method: "tools/call", params: { name: "list_candidates", arguments: {} } });
  assert.equal(response.error.code, -32601);
});

test("submit_event forwards the envelope with bearer authentication", async () => {
  let request;
  const fetchImpl = async (url, init) => {
    request = { url, init };
    return new Response(JSON.stringify({ jsonrpc: "2.0", id: 3, result: { content: [{ type: "text", text: "ok" }] } }), { status: 200 });
  };
  const response = await handleRequest({
    jsonrpc: "2.0", id: 3, method: "tools/call",
    params: { name: "submit_event", arguments: { schemaVersion: "1.2", namespace: "interview", eventType: "identity.list", payload: {}, requestId: "req-1" } }
  }, { workerUrl: "https://worker.example", token: "secret", fetchImpl });
  assert.equal(response.result.content[0].text, "ok");
  assert.equal(request.url, "https://worker.example");
  assert.equal(request.init.headers.authorization, "Bearer secret");
  assert.deepEqual(JSON.parse(request.init.body).params.arguments.payload, {});
});

test("notifications do not produce a response", async () => {
  assert.equal(await handleRequest({ jsonrpc: "2.0", method: "notifications/initialized" }), null);
});
