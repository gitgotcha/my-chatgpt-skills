import * as driveClient from "./google-drive.js";

const tools = [
  { name: "find_or_create_candidate", description: "Find the exact-name Drive folder, or create it when absent.", inputSchema: { type: "object", required: ["displayName"], properties: { displayName: { type: "string" } } } },
  { name: "list_candidates", description: "List direct name-folder summaries from Drive.", inputSchema: { type: "object", properties: { query: { type: "string" }, limit: { type: "integer" } } } },
  { name: "get_candidate_context", description: "Read context for a name-folder user.", inputSchema: { type: "object", required: ["displayName"], properties: { displayName: { type: "string" } } } },
  { name: "submit_artifact", description: "Write an artifact directly to a name-folder user.", inputSchema: { type: "object", required: ["displayName", "fileName", "contentBase64", "contentType"], properties: { displayName: { type: "string" }, fileName: { type: "string" }, contentBase64: { type: "string" }, contentType: { type: "string" } } } },
  { name: "read_artifact", description: "Read an artifact directly from a name-folder user.", inputSchema: { type: "object", required: ["displayName", "artifactKey"], properties: { displayName: { type: "string" }, artifactKey: { type: "string" } } } },
  { name: "submit_event", description: "Write an event directly to a name-folder user.", inputSchema: { type: "object", required: ["displayName", "event"], properties: { displayName: { type: "string" }, event: { type: "object" } } } }
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
  try {
    const drive = deps.drive ?? driveClient;
    const args = message.params?.arguments ?? {};
    if (message.params?.name === "find_or_create_candidate") {
      const candidate = await drive.findOrCreateCandidateFolder(env, args, deps);
      return result(message.id, { content: [{ type: "text", text: JSON.stringify(candidate) }] });
    }
    if (message.params?.name === "list_candidates") {
      const candidates = await drive.listCandidates(env, args, deps);
      return result(message.id, { content: [{ type: "text", text: JSON.stringify(candidates) }] });
    }
    if (message.params?.name === "get_candidate_context") {
      const context = await drive.getCandidateContext(env, args, deps);
      return result(message.id, { content: [{ type: "text", text: JSON.stringify(context) }] });
    }
    if (message.params?.name === "read_artifact") {
      const artifact = await drive.readArtifact(env, args, deps);
      return result(message.id, { content: [{ type: "text", text: JSON.stringify(artifact) }] });
    }
    if (message.params?.name === "submit_event") {
      if (!args.displayName || !args.event?.eventKey) throw new Error("displayName and event.eventKey are required");
      const candidate = await drive.findOrCreateCandidateFolder(env, args, deps);
      const file = await drive.uploadDriveFile(env, candidate.folderId, `${args.event.eventKey}.json`, JSON.stringify(args.event), "application/json", deps);
      return result(message.id, { content: [{ type: "text", text: JSON.stringify({ displayName: candidate.displayName, fileId: file.id, eventKey: args.event.eventKey }) }] });
    }
    if (message.params?.name === "submit_artifact") {
      if (!args.displayName || !args.fileName || !args.contentBase64 || !args.contentType) throw new Error("displayName, fileName, contentBase64 and contentType are required");
      const content = atob(args.contentBase64);
      const artifactName = args.artifactKey ?? args.fileName;
      const candidate = await drive.findOrCreateCandidateFolder(env, args, deps);
      const file = await drive.uploadDriveFile(env, candidate.folderId, artifactName, content, args.contentType, deps);
      return result(message.id, { content: [{ type: "text", text: JSON.stringify({ displayName: candidate.displayName, fileId: file.id, artifactKey: artifactName }) }] });
    }
    return error(message.id, -32601, "Tool not implemented");
  } catch (cause) {
    return error(message.id, -32603, cause.message);
  }
}

export default { fetch: (request, env) => handleRequest(request, env) };
