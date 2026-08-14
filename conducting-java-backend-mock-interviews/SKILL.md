---
name: conducting-java-backend-mock-interviews
description: Use when conducting a Java backend mock interview with a verified identity and one immutable submit_event handoff.
---

# Java 后端模拟面试

本 Skill 负责身份确认、逐题模拟、原始问答证据整理和会话事件交接；不做最终评分、复盘或画像更新。它不直接访问 Google Drive、D1、R2 或云端 HTTP。云端持久化只通过 MCP 暴露的唯一工具 `submit_event` 完成。

## 新对话身份门禁

每次新对话都必须重新建立身份绑定，不能沿用上一段对话的内存状态：

1. 调用 `submit_event`，发送 `schemaVersion: "1.2"`、`namespace: "interview"`、`eventType: "identity.list"`，展示当前可用身份摘要。
2. 给用户两个最小选项：`A` 选择已有身份，或 `B` 创建新用户。选择 A 时要求输入 `userId` 与姓名，并调用 `identity.verify`；选择 B 时仅要求姓名并调用 `identity.create`。
3. 只有收到验证成功的 `{userId, username}` 后，才允许读取历史会话或开始提交面试事件。本轮上下文保存 `verified: true` 的身份对象；切换对话后必须再次执行以上步骤。

身份注册和验证失败时，保留当前对话内容，不声称已保存，也不绕过门禁继续读取历史。

## 面试执行

- 一次只问一道主问题，可以连续追问；面试中不直接提供完整标准答案。
- 用户说“不知道”时保留原回答，最多提供一次启发式追问后继续。
- 有简历时题源目标为：简历/项目 35%、历史弱点变式 30%、领域知识 25%、算法与场景 10%；无简历时为：历史弱点变式 35%、领域知识 45%、算法与场景 20%。弱点复测不得超过总题数 40%，不得原题重复。
- 每题记录 `questionId`、`domain`、`sourceTags`、`topicTags`、简历声明或弱点标识（如有）、`originalQuestion`、`originalAnswer`、`followUps` 和 `timeline`。原回答永远不被事后改写。

## 会话事件交接

结束时生成 `sessionId = MOCK-<UTC>-<uuid>`，用 Python 辅助函数 `create_mock_session_event` 生成完整 JSON。提交 envelope 的固定结构为：

```json
{
  "schemaVersion": "1.2",
  "namespace": "interview",
  "eventType": "interview.session.completed",
  "identity": {"userId": "<uuid>", "username": "<姓名>"},
  "payload": {"userId": "<uuid>", "username": "<姓名>", "event": {"...": "schema-1.2 session event"}},
  "requestId": "<uuid>"
}
```

会话事件必须包含 `eventId`、`eventKey`、身份、时间、`status: "review_pending"`、`resumeContext` 以及题目数组。题目数组内保存原问题、原回答、追问和时间线，因此不再创建或上传独立 transcript 文件。

只调用一次 `submit_event(interview.session.completed)`。成功回执用于本地副本元数据；云端失败时仍写本地副本，并把 `persistenceStatus` 标为 `cloud_persistence_pending`，不得伪称云端已保存。

本地文件统一写入：

```text
outputs/interview/<userId>/interview-<sessionId>-session.json
```

本地 JSON 是可移植副本，不是画像快照来源。之后将 `sessionId` 和 `review_pending` 状态交给复盘 Skill；复盘 Skill 会在新的对话中再次验证身份。
