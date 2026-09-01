---
name: reviewing-java-backend-interviews
description: Use when reviewing a mock or real interview for a user resolved by display name, through one immutable submit_event handoff with local JSON and Word output.
---

# Java 后端面试复盘

本 Skill 负责按姓名解析用户、历史会话选择、逐题复盘、结构化画像变化和本地报告生成。所有远端交互只能使用唯一的 `submit_event` MCP 工具；写事件时先落本机 SQLite Outbox，再由 Worker `/v1/jobs` 接收入 D1 Outbox 并异步写 Drive。本 Skill 不调用其他远端工具，也不把本地报告作为画像输入。

所有云端数据只写入唯一规范插件根 `DriveRoot/my-chatGPT-skills/`。复盘事件由 Worker 追加到 `users/<userId>/interview/events/`，画像快照由 Worker 物化到 `users/<userId>/interview/profile/snapshots/`；本 Skill 只生成事件内容，不直接写 Drive。

## 按姓名解析用户

每次新对话都重新解析身份，不沿用上一段对话的身份：

1. 先取得用户姓名；姓名缺失时先询问，不得猜测或用占位姓名提交。
2. 调用 `submit_event`，发送 `schemaVersion: "1.2"`、`namespace: "system"`、`eventType: "system.user-registered"`，payload 为 `{displayName: "<姓名>"}`。注册阶段按机械标准化（Unicode NFKC 与去除首尾空白）后的姓名匹配全局注册表。
3. 命中唯一用户时返回已有 `userId`；不存在时创建稳定独立的新 `userId` 并返回；存在无法消解的同名冲突时停止并要求人工选择，不自动合并、不静默挑选。
4. `submit_event` 响应返回规范化的 `identity`（`username` 与 `userId`）。把它绑定到当前对话后，才允许读取会话摘要或会话详情。
5. 不再展示候选用户列表让用户选择，也不再单独调用身份列举、校验或创建接口：解析与注册由 `submit_event` 在一次调用内完成。本轮绑定只在当前对话有效；用户切换身份时重新按姓名解析。

身份解析回执没有 `identity` 时暂停后续读取与写入；`deliveryState: "pending"` 只表示注册事件仍在 SQLite 排队，不得自行猜测 `userId`。

## 会话读取与复盘

身份解析成功后依次调用：

1. `submit_event(interview.session.list)`，只展示时间、领域、类型和复盘状态摘要。
2. 用户选择会话后调用 `submit_event(interview.session.load)`，读取目标 schema-1.2 会话及有效复盘事件。
3. 保留原问题、原回答、追问关联、正确性、完整性、错误、遗漏、失分原因、更好的口述回答、参考答案、表达分析和变式复测。

复盘事件必须包含 `sourceSessionEventId`、`sourceType`、`evidenceType`、`evidenceConfidence`、`questionReviews`、`profileChanges`、`recommendations` 和 `applyProfileChanges`。`reviewVersion` 从 1 开始；修订时创建更高版本，不覆盖旧事件。

模拟会话的画像变化默认允许应用。真实会话必须明确询问用户是否确认：未确认时保存 `applyProfileChanges: false`；确认后创建下一不可变版本并设置为 `true`。只有结构化字段进入画像重建，自然语言报告不会改变画像。

## 唯一提交与本地输出

构造完整 `interview.review.completed` JSON 后只调用一次 `submit_event`。按回执 `deliveryState` 记录本地状态：`cloud_accepted` 表示 SQLite 已落盘且 D1 Outbox 已接收，保存 `outboxReceipt`，但 `persistence.drive` 仍为 `pending`；`pending` 表示仅确认 SQLite 持久排队。`persistenceStatus` 只能是 `cloud_accepted` 或 `pending`。不得将任一状态解释为 Drive 已完成，也不得由 Skill 绕过 Outbox 手工重发；QStash/Worker 负责异步投递和画像重建重试。

本地复盘文件统一保存为：

```text
outputs/interview/<userId>/interview-<sessionId>-report.json
outputs/interview/<userId>/interview-<sessionId>-report.docx
```

本地报告只保留为本地派生输出，不上传云端，也永不作为画像输入。先用 `save_review_json` 写完整事件副本，再以该 JSON 作为 `create_review_report(report_json, report_docx)` 的唯一输入生成 Word，并执行渲染检查。Word 生成失败不回滚 JSON 或已提交事件；明确说明失败原因并保留可重试文件。
