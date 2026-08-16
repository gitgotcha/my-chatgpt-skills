# Cloud task router

Read exactly one workflow before responding:

- LeetCode、算法、动态规划、回溯、代码复杂度：`algorithm-learning/SKILL.md`
- 学习后端源码、业务流程、项目面试：`backend-project-learning/SKILL.md`
- Java 后端模拟面试：`conducting-java-backend-mock-interviews/SKILL.md`
- 面试记录复盘、报告或画像更新：`reviewing-java-backend-interviews/SKILL.md`

## Interview persistence contract

Interview and algorithm persistence uses only the `reliable-drive-sync` MCP tool
`submit_event`. Every call is a schema-1.2 envelope:

```json
{
  "schemaVersion": "1.2",
  "namespace": "algorithm | interview",
  "eventType": "identity.list | identity.create | identity.verify | ...",
  "payload": {},
  "requestId": "<non-empty request id>"
}
```

The `algorithm` and `interview` namespaces have independent identity registries.
At the start of every conversation, call `identity.list`, show the minimal
`A. existing user / B. new user` choices, then call `identity.verify` or
`identity.create`. Do not read sessions or write learning/interview events until
the current conversation has a verified `{userId, username}` binding. A new
conversation must repeat this gate.

The Worker exposes exactly one public tool, `submit_event`; removed candidate and
artifact tools are not supported. New records are append-only JSON in a Google
Shared Drive. A successful write is reported only after Drive readback returns a
real file ID. `status: "ok"` means the event and any requested cache work
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
Existing root-level name folders and their old artifacts are intentionally not
scanned, migrated, modified, or deleted.
