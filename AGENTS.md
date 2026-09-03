# Cloud task router

Read exactly one workflow before responding:

- LeetCode、算法、动态规划、回溯、代码复杂度：`algorithm-learning/SKILL.md`
- 学习后端源码、业务流程、项目面试：`backend-project-learning/SKILL.md`
- Java 后端模拟面试：`conducting-java-backend-mock-interviews/SKILL.md`
- 面试记录复盘、报告或画像更新：`reviewing-java-backend-interviews/SKILL.md`
- 简历驱动的 Java 后端八股学习与每日练习：`java-knowledge-based-on-resume-learn-skill/SKILL.md`
- 儿童摄影后期（模板图学风格、选片、精修、统一色调）：`child-photoShop-skill/SKILL.md`
- 显式创建或更新可复用 Skill（仅显式调用，不隐式触发）：`profile-aware-skill-creator/SKILL.md`

## Persistence contract

All cloud persistence uses only the `reliable-drive-sync` MCP tool
`submit_event`. No skill, script or scheduled task writes to Drive directly.
Every call is a schema-1.2 envelope:

```json
{
  "schemaVersion": "1.2",
  "namespace": "system | algorithm | interview | resume-knowledge | profile",
  "eventType": "system.user-registered | algorithm.learning.completed | ...",
  "identity": { "username": "乔炳源" },
  "payload": {},
  "requestId": "<non-empty request id>"
}
```

## Persistence paths (Phase 1)

There are two persistence paths and they do not migrate into each other:

1. Existing Skill-owned events (`algorithm`, `interview`, `resume-knowledge`
   namespaces) keep their current per-Skill contracts, output paths and
   reducers. Phase 1 does not migrate them, and legacy data rules below stay
   unchanged.
2. The new generic profile path uses the external `reliable-drive-sync` MCP
   with the `profile` namespace. A generated profile-aware Skill first calls
   `system.capabilities.read` for capability negotiation, then
   `system.user.resolve` for identity; profile reads use
   `profile.snapshot.read` and evidence writes use
   `profile.evidence.recorded` (registration still uses the existing
   `system.user-registered` event). Generic-profile acknowledgements use the
   asynchronous `pending` / `cloud_accepted` receipt semantics and carry no
   immediate Drive `fileId` promise: `pending` means the local outbox has the
   event, `cloud_accepted` means the cloud outbox accepted it while Drive
   synchronizes in the background.

`cloud-mcp/` remains a frozen legacy compatibility copy kept for its existing
tests; it must not receive `profile.*` events and is not the profile runtime.

## Identity rules

Identity is global and resolved by name. The Worker applies NFKC normalization
and trims surrounding whitespace, then resolves or registers one stable `userId`
in the global registry. The same name always returns the same `userId` across
every domain, and different names stay isolated. A conflict that cannot be
resolved must stop instead of guessing.

Callers pass a display name; they never pick a `userId`. Registration may be
submitted explicitly through `system.user-registered` or triggered implicitly by
the resolution phase of any business event. Every cloud write lands below the
single canonical root:

```text
DriveRoot/my-chatGPT-skills/users/<userId>/<domain>/events/
DriveRoot/my-chatGPT-skills/users/<userId>/<domain>/profile/snapshots/
```

The local stdio MCP exposes exactly one tool, `submit_event`; removed candidate
and artifact tools are not supported. Every write is staged in the local SQLite
Outbox, accepted through Worker `/v1/jobs` into the D1 Outbox, and delivered
asynchronously by QStash/Worker. `deliveryState: "cloud_accepted"` means D1
accepted a durable job, not that Drive finished; `deliveryState: "pending"`
means SQLite still holds the event for retry. Skills must never require a Drive
file ID, claim Drive completion from either receipt, or bypass the Outboxes.

Local portable outputs are not profile inputs:

```text
outputs/interview/<userId>/interview-<sessionId>-session.json
outputs/interview/<userId>/interview-<sessionId>-report.json
outputs/interview/<userId>/interview-<sessionId>-report.docx
```

The Word report is derived from the local report JSON and is never uploaded.

## Legacy data and migration

Pre-normalization namespace directories are read-only. They are reached only by
the compatibility reader and the migration implementation, and migration is only
offered as a `system.legacy-migration-requested` dry-run plus an explicitly
approved execute. Legacy objects are never moved, overwritten or deleted, and no
migration runs automatically.
