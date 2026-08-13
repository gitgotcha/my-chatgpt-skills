import { createCandidate, InputError } from "./candidates.js";

const tools = [
  { name: "create_candidate", description: "Create a candidate and return a summary requiring user confirmation.", inputSchema: { type: "object", required: ["displayName"], properties: { displayName: { type: "string" }, distinguishingNote: { type: "string" } } } },
  { name: "list_candidates", description: "List candidate summaries only.", inputSchema: { type: "object", properties: { query: { type: "string" }, limit: { type: "integer" } } } },
  { name: "get_candidate_context", description: "Read context after explicit confirmation.", inputSchema: { type: "object", required: ["candidateId"], properties: { candidateId: { type: "string" } } } },
  { name: "submit_artifact", description: "Submit an immutable artifact.", inputSchema: { type: "object" } },
  { name: "read_artifact", description: "Read a synchronized artifact.", inputSchema: { type: "object" } },
  { name: "submit_event", description: "Submit a replayable profile event.", inputSchema: { type: "object" } }
];

const result = (id, value) => Response.json({ jsonrpc: "2.0", id, result: value });
const error = (id, code, message) => Response.json({ jsonrpc: "2.0", id, error: { code, message } });

export async function handleRequest(request, env, deps = {}) {
  if (request.method !== "POST") return new Response("Method Not Allowed", { status: 405 });
  if (request.headers.get("authorization") !== `Bearer ${env.MCP_BEARER_TOKEN}`) return new Response("Unauthorized", { status: 401 });
  const message = await request.json();
  if (message.method === "initialize") return result(message.id, { protocolVersion: "2024-11-05", capabilities: { tools: {} }, serverInfo: { name: "reliable-drive-sync", version: "1.0.0" } });
  if (message.method === "tools/list") return result(message.id, { tools });
  if (message.method !== "tools/call") return error(message.id, -32601, "Method not found");
  if (message.params?.name !== "create_candidate") return error(message.id, -32601, "Tool not implemented");
  try {
    const candidate = await createCandidate(env.DB, message.params.arguments ?? {}, deps.now?.() ?? new Date().toISOString(), deps.uuid ?? crypto.randomUUID);
    return result(message.id, { content: [{ type: "text", text: JSON.stringify(candidate) }] });
  } catch (cause) {
    return error(message.id, cause instanceof InputError ? -32602 : -32603, cause.message);
  }
}

export default { fetch: (request, env) => handleRequest(request, env) };
