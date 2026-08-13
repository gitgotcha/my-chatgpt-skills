import assert from "node:assert/strict";
import test from "node:test";
import { handleRequest } from "../src/index.js";

function env() {
  return {
    MCP_BEARER_TOKEN: "secret",
    DB: { prepare: () => ({ bind: () => ({ run: async () => ({ success: true }) }) }) }
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

test("MCP create_candidate returns content", async () => {
  const response = await handleRequest(request("tools/call", { name: "create_candidate", arguments: { displayName: "小明" } }), env(), { uuid: () => "id", now: () => "2026-08-13T00:00:00.000Z" });
  const payload = await response.json();
  assert.match(payload.result.content[0].text, /CAND-id/);
});
