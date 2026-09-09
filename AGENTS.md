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
  "operation": "account.current | account.register | account.find | ... | business.write",
  "bindingContext": { "userId": "<uuid>", "bindingRevision": "<opaque>", "principal": "<opaque>" },
  "namespace": "system | algorithm | interview | resume-knowledge",
  "eventType": "algorithm.learning.completed | interview.session.completed | ...",
  "identity": { "username": "乔炳源", "userId": "<uuid>" },
  "payload": {},
  "requestId": "<non-empty request id>"
}
```

## Identity rules

姓名不是认证。默认身份来自当前 Windows 用户的本机设备绑定；Worker 每次个人请求仍以凭据派生
`userId` 并校验账户状态、绑定修订号和请求中的一致性字段。Agent 只能复用最近一次
`account.current` 返回的完整 `bindingContext`，不能凭聊天姓名、UUID 或记忆恢复授权。

新账户与设备迁移必须走 `account.register`/`account.transfer.*` 的专用流程；账户管理状态不伪装成学习事件。
用户明确要求切换时才执行 `account.switch`/`account.unbind`，遇到绑定变化或凭据失效立即停止个人读写并重新获取
current。每个账户可有独立 UUID，同名账户不自动合并，也不提供按姓名接管。

Every cloud write lands below the single canonical root:

```text
DriveRoot/my-chatGPT-skills/users/<userId>/<domain>/events/
DriveRoot/my-chatGPT-skills/users/<userId>/<domain>/profile/snapshots/
```

The Worker exposes exactly one public tool, `submit_event`; account management,
read-only queries, and business writes are operation variants behind the same
gateway. New records are append-only JSON in a Google Shared Drive. A successful
write is reported only according to the returned cloud/D1/Drive receipt; an
Outbox-local acknowledgement is not a Drive sync claim. Never claim persistence
after an error or a pending receipt.

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
