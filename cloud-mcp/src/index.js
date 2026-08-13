import * as driveClient from "./google-drive.js";

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
  try {
    const drive = deps.drive ?? driveClient;
    const args = message.params?.arguments ?? {};
    if (message.params?.name === "create_candidate") {
      const candidate = await drive.createCandidateFolder(env, args, deps);
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
      if (!args.candidateFolderId || !args.event?.eventKey) throw new Error("candidateFolderId and event.eventKey are required");
      const file = await drive.uploadDriveFile(env, args.candidateFolderId, `${args.event.eventKey}.json`, JSON.stringify(args.event), "application/json", deps);
      return result(message.id, { content: [{ type: "text", text: JSON.stringify({ fileId: file.id, eventKey: args.event.eventKey }) }] });
    }
    if (message.params?.name === "submit_artifact") {
      if (!args.candidateFolderId || !args.fileName || !args.contentBase64 || !args.contentType) throw new Error("candidateFolderId, fileName, contentBase64 and contentType are required");
      const content = atob(args.contentBase64);
      const artifactName = args.artifactKey ?? args.fileName;
      const file = await drive.uploadDriveFile(env, args.candidateFolderId, artifactName, content, args.contentType, deps);
      return result(message.id, { content: [{ type: "text", text: JSON.stringify({ fileId: file.id, artifactKey: artifactName }) }] });
    }
    return error(message.id, -32601, "Tool not implemented");
  } catch (cause) {
    return error(message.id, -32603, cause.message);
  }
}

export default { fetch: (request, env) => handleRequest(request, env) };
