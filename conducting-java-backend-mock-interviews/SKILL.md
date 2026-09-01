---
name: conducting-java-backend-mock-interviews
description: Use when conducting a Java backend mock interview for a user resolved by display name, with one immutable submit_event handoff.
---

# Java 后端模拟面试

本 Skill 负责按姓名解析用户、逐题模拟、原始问答证据整理和会话事件交接；不做最终评分、整场复盘或画像更新。它不直接访问 Google Drive、D1、R2 或云端 HTTP。唯一工具 `submit_event` 先把事件写入本机 SQLite Outbox，再由 Worker `/v1/jobs` 接收入 D1 Outbox 并异步写 Drive。

所有云端数据只写入唯一规范插件根 `DriveRoot/my-chatGPT-skills/`。模拟会话事件由 Worker 追加到 `users/<userId>/interview/events/`；本 Skill 不生成画像快照，也不在会话中更新画像。

## 按姓名解析用户

每次新对话都必须重新解析身份，不能沿用上一段对话的内存状态：

1. 先暂存用户请求，再取得用户姓名；姓名缺失时先询问，不得猜测或用占位姓名提交。
2. 调用 `submit_event`，发送 `schemaVersion: "1.2"`、`namespace: "system"`、`eventType: "system.user-registered"`，payload 为 `{displayName: "<姓名>"}`。注册阶段按机械标准化（Unicode NFKC 与去除首尾空白）后的姓名匹配全局注册表。
3. 命中唯一用户时返回已有 `userId`；不存在时创建稳定独立的新 `userId` 并返回；存在无法消解的同名冲突时停止并要求人工选择，不自动合并、不静默挑选。
4. `submit_event` 响应返回规范化的 `identity`（`username` 与 `userId`）。把它绑定到当前对话后，才允许读取历史会话或开始提交面试事件。
5. 不再展示候选用户列表让用户选择，也不再单独调用身份列举、校验或创建接口：解析与注册由 `submit_event` 在一次调用内完成。
6. 同一对话后续请求沿用绑定身份，除非用户明确要求切换用户；切换时解除绑定并重新按姓名解析。

身份解析或注册失败时，保留当前对话内容，不声称已保存，也不绕过解析继续读取历史。

## 面试执行

- 一次只问一道主问题，可以连续追问；面试中不直接提供完整标准答案。
- 用户说“不知道”时保留原回答，最多提供一次启发式追问后继续。
- 有简历或项目材料时，题源主来源采用互斥配额：简历/项目 55%、历史弱点变式 15%、领域知识 10%、算法与场景 20%。领域知识和八股可以结合项目或场景出题，但只按主来源计数，使用 `topicTags` 标记重叠主题；无简历时为：历史弱点变式 35%、领域知识 45%、算法与场景 20%。题目数量不是 20 的倍数时按最大余数法取整，弱点复测不得超过总题数 40%，不得原题重复。
- 每题记录 `questionId`、`domain`、`sourceTags`、`topicTags`、简历声明或弱点标识（如有）、`originalQuestion`、`originalAnswer`、`followUps` 和 `timeline`。原回答永远不被事后改写。

## 会话事件交接

结束时生成 `sessionId = MOCK-<UTC>-<uuid>`，用 Python 辅助函数 `create_mock_session_event` 生成完整 JSON。提交 envelope 的固定结构为：

```json
{
  "schemaVersion": "1.2",
  "namespace": "interview",
  "eventType": "interview.session.completed",
  "identity": {"username": "<姓名>", "userId": "<uuid>"},
  "payload": {"event": {"...": "schema-1.2 session event"}},
  "requestId": "<uuid>"
}
```

会话事件必须包含 `eventId`、`eventKey`、身份、时间、`status: "review_pending"`、`resumeContext` 以及题目数组。题目数组内保存原问题、原回答、追问和时间线，因此不再创建或上传独立 transcript 文件。

只调用一次 `submit_event(interview.session.completed)`。按回执 `deliveryState` 写本地副本元数据：`cloud_accepted` 表示 SQLite 已落盘且 D1 Outbox 已接收，保存 `outboxReceipt`，但 `persistence.drive` 仍是 `pending`；`pending` 表示仅确认 SQLite 持久排队。对应的 `persistenceStatus` 只能是 `cloud_accepted` 或 `pending`。两者都不得伪称 Drive 已保存，也不由 Skill 手工重发；QStash/Worker 负责异步投递和重试。

本地文件统一写入：

```text
outputs/interview/<userId>/interview-<sessionId>-session.json
```

本地 JSON 是可移植副本，不是画像快照来源，也不会被拼入任何云端事件路径。之后将 `sessionId` 和 `review_pending` 状态交给复盘 Skill；复盘 Skill 会在新的对话中再次按姓名解析同一用户。
