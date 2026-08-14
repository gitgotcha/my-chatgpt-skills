import { ProtocolError } from "./protocol.js";
import { dispatchSubmitEvent } from "./submit-event.js";

const tools = [{
  name: "submit_event",
  description: "Submit a validated interview or algorithm event.",
  inputSchema: {
    type: "object",
    additionalProperties: false,
    required: ["schemaVersion", "namespace", "eventType", "requestId"],
    properties: {
      schemaVersion: { type: "string" },
      namespace: { type: "string" },
      eventType: { type: "string" },
      payload: { type: "object", additionalProperties: false },
      requestId: { type: "string" }
    }
  }
}];

const result = (id, value) => Response.json({ jsonrpc: "2.0", id, result: value });
const error = (id, code, message) => Response.json({ jsonrpc: "2.0", id, error: { code, message } });

export async function handleRequest(request, env, deps = {}) {
  if (request.method !== "POST") return new Response("Method Not Allowed", { status: 405 });
  if (request.headers.get("authorization") !== `Bearer ${env.MCP_BEARER_TOKEN}`) return new Response("Unauthorized", { status: 401 });
  const message = await request.json();
  if (message.method === "initialize") return result(message.id, { protocolVersion: "2024-11-05", capabilities: { tools: {} }, serverInfo: { name: "reliable-drive-sync", version: "1.0.0" } });
  if (message.method === "tools/list") return result(message.id, { tools });
  if (message.method !== "tools/call") return error(message.id, -32601, "Method not found");
  if (message.params?.name !== "submit_event") {
    return error(message.id, -32601, "Tool not implemented");
  }
  try {
    const args = message.params?.arguments ?? {};
    const value = await dispatchSubmitEvent(env, args, deps);
    return result(message.id, {
      content: [{ type: "text", text: JSON.stringify(value) }]
    });
  } catch (cause) {
    if (cause instanceof ProtocolError) return error(message.id, -32602, cause.message);
    return error(message.id, -32603, cause instanceof Error ? cause.message : String(cause));
  }
}

export default { fetch: (request, env) => handleRequest(request, env) };
