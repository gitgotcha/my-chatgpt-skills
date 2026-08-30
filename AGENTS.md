# Cloud task router

Read exactly one workflow before responding:

- LeetCode、算法、动态规划、回溯、代码复杂度：`algorithm-learning/SKILL.md`
- 学习后端源码、业务流程、项目面试：`backend-project-learning/SKILL.md`
- Java 后端模拟面试：`conducting-java-backend-mock-interviews/SKILL.md`
- 面试记录复盘、报告或画像更新：`reviewing-java-backend-interviews/SKILL.md`
- 简历驱动的 Java 后端八股学习与每日练习：`java-knowledge-based-on-resume-learn-skill/SKILL.md`

## Persistence contract

All cloud persistence uses only the `reliable-drive-sync` MCP tool
`submit_event`. No skill, script or scheduled task writes to Drive directly.
Every call is a schema-1.2 envelope:

```json
{
  "schemaVersion": "1.2",
  "namespace": "system | algorithm | interview | resume-knowledge",
  "eventType": "system.user-registered | algorithm.learning.completed | ...",
  "identity": { "username": "乔炳源" },
  "payload": {},
  "requestId": "<non-empty request id>"
}
```

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

The Worker exposes exactly one public tool, `submit_event`; removed candidate and
artifact tools are not supported. New records are append-only JSON in a Google
Shared Drive. A successful write is reported only after Drive readback returns a
real file ID. `status: "ok"` means the event and any requested projection
completed; `cloud_persistence_pending` means the local copy exists but the cloud
event did not; `profile_cache_pending` means the event is durable but rebuilding
the snapshot failed. Never claim persistence after an error.

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
