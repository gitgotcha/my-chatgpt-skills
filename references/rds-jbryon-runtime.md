# RDS-JBryon runtime contract for Skills

RDS-JBryon is the single-user store for 乔炳源. Skills call the registered MCP tool `rds`; they do not resolve an account, send user identity, call the retired `reliable_drive_sync` tool, or access Drive, D1, or remote HTTP directly. The user's readable folder path is the routing key. Internal node IDs, request IDs, revisions, and workspace epochs are tool-managed values and are never prerequisites the user must provide.

## Path routing

- Existing project: `project/12306/学习快照.json`; alias `project-12306` maps to `project/12306`.
- Other projects: `project/<user-chosen-name>/学习快照.json`.
- Java knowledge: `knowledge/java/jvm/学习快照.json`, `knowledge/java/juc/学习快照.json`.
- Other skill state: choose a readable path under `knowledge/` or another user-confirmed top-level domain. Preserve the user's explicit spelling and hierarchy.
- For a user-confirmed or explicitly named route, automatically create any missing directory levels and its empty skill-appropriate snapshot on first use; users never need to create folders manually. Confirm an unapproved new top-level domain or ambiguous route by showing its full path first. An explicit request such as “use project/12306” or “create knowledge/java/jvm” confirms that route. A read-only/no-write request always suppresses automatic creation.

### Profile and project ownership

- Algorithm learning uses `knowledge/algorithm-learning/学习快照.json`.
- Java resume knowledge uses `knowledge/java/resume-interview/学习快照.json`; the original resume file is not uploaded by default.
- Study planning uses `knowledge/study-planning/规划快照.json`.
- Project learning, project mock interviews, and their reviews share `project/<project-name>/学习快照.json`.
- A non-project mock interview uses a user-confirmed `interview/mock/<name>.json` route.
- Non-project interview reviews use a user-confirmed `interview/reviews/<name>.json` route.

These are separate evidence scopes. Do not merge project assessments into a global person profile, infer personality or stable ability from one answer, or copy the same answer into multiple Skills' snapshots. Keep user answers separate from model feedback, and apply real-interview profile changes only after the review Skill's explicit confirmation gate.

## Tool calls

The MCP tool is `rds` and has one operation-oriented input:

```json
{"kind":"query","operation":"capabilities","params":{}}
```

Use `kind=query` for `directory.list`, `directory.resolve`, `snapshot.read`, `snapshot.query`, `snapshot.history`, `request.status`, and `conflict.list`. For provisioning-safe lookup, walk the route with `directory.list`: pass `parentId:null` at the root and each returned `nodeId` for the next level, paging to completion and matching the exact segment. This distinguishes existing from missing levels without relying on a not-found resolver response. Once present, read the snapshot with `snapshot.read` and its returned internal `nodeId`. For example:

```json
{"kind":"query","operation":"directory.resolve","params":{"path":["knowledge","java","jvm","学习快照.json"]}}
```

For a write, read the current snapshot and revision, then call `kind=request` with a new unique `requestId`, the current `workspaceEpoch`, and the smallest required patch. The caller supplies all protocol fields shown below; the MCP validates and durably queues the request before sending it. The logical request shape is:

```json
{
  "kind":"request",
  "request":{
    "protocol":"rds-jbryon",
    "apiVersion":1,
    "workspaceEpoch":"<current value returned by capabilities>",
    "requestId":"<new unique request id>",
    "operation":"snapshot.patch",
    "target":{"nodeId":"<node resolved from the readable path>"},
    "baseRevision":7,
    "changes":[{"op":"set","path":["records","latest"],"value":{"...":"only facts observed in this conversation"}}]
  }
}
```

Use the real values returned by the tool; the placeholders above are explanatory and must never be sent literally. For a confirmed writable route, create missing levels automatically and in order: the top-level node is a `domain`, intermediate nodes are `directory`, and the leaf is `snapshot`. Use the exact path segment as `name`, the preceding node ID as `parentId`, and dependencies on earlier create requests. Wait for each create to reach `projected` before proceeding. Do not auto-create for read-only requests, an unapproved new top-level domain, incomplete directory pagination, ambiguous matches, or failed tool calls. Never ask the user to create the folders manually.

## Evidence, retries, and conflicts

- Store only facts the Skill is allowed to persist. Keep original user answers, corrections, evaluations, and derived summaries distinguishable; never rewrite an original answer into a polished version.
- Retry an uncertain request with the same `requestId` and identical contents. Do not invent a second ID to make an unknown result disappear.
- Check `kind=status` or `request.status` for the real state. `projected` means the snapshot is readable; `local_pending`, `waiting_dependency`, `delivery_blocked`, and `d1_committed` do not prove projection.
- When independent paths change, allow the service merge. If the same path has conflicting values, read the conflict and ask the user which value to keep; retain both candidates until resolved.
- If the store is unavailable, continue only work that does not require past snapshots, say that the snapshot was not read or saved, and keep a concise handoff locally in the conversation. Never claim a save without a projected result.
- A next-day recap is read-only unless the user starts new learning or explicitly asks to save a new fact.
