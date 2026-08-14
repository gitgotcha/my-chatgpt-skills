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

test("MCP exposes only submit_event", async () => {
  const response = await handleRequest(request("tools/list"), env());
  const payload = await response.json();
  assert.deepEqual(payload.result.tools.map((tool) => tool.name), ["submit_event"]);
  assert.equal(payload.result.tools[0].inputSchema.additionalProperties, false);
  assert.equal(payload.result.tools[0].inputSchema.properties.payload.additionalProperties, false);
});

test("MCP rejects an incorrect bearer token", async () => {
  const response = await handleRequest(request("tools/list", {}, "wrong"), env());
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

test("submit_event rejects an allowed event without a registered handler", async () => {
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
  assert.match(payload.error.message, /invalid_event_type/);
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
