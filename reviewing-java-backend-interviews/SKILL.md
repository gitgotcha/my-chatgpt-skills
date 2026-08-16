---
name: reviewing-java-backend-interviews
description: Use when reviewing a verified mock or real interview through one immutable submit_event handoff, with local JSON and Word output.
---

# Java 后端面试复盘

本 Skill 负责跨对话身份确认、历史会话选择、逐题复盘、结构化画像变化和本地报告生成。所有远端交互只能使用唯一的 `submit_event` MCP 工具；本 Skill 不调用其他远端工具，也不把本地报告作为画像输入。

## 新对话身份门禁

每次新对话都从身份门禁开始，不沿用上一段对话的身份：

1. 调用 `submit_event`，发送 `schemaVersion: "1.2"`、`namespace: "interview"`、`eventType: "identity.list"`。
2. 展示最小身份选项：`A` 选择已有身份，或 `B` 创建新用户。
3. 选择 A 时要求用户提供 `userId` 和姓名，再调用 `identity.verify`；选择 B 时仅询问姓名，再调用 `identity.create`。
4. 只有收到 `{userId, username, verified: true}` 后，才允许读取会话摘要或会话详情。本轮绑定只在当前对话有效；用户切换身份时重新执行门禁。

身份失败或远端状态不是 `ok` 时暂停后续读取与写入，并如实说明尚未持久化。

## 会话读取与复盘

身份验证成功后依次调用：

1. `submit_event(interview.session.list)`，只展示时间、领域、类型和复盘状态摘要。
2. 用户选择会话后调用 `submit_event(interview.session.load)`，读取目标 schema-1.2 会话及有效复盘事件。
3. 保留原问题、原回答、追问关联、正确性、完整性、错误、遗漏、失分原因、更好的口述回答、参考答案、表达分析和变式复测。

复盘事件必须包含 `sourceSessionEventId`、`sourceType`、`evidenceType`、`evidenceConfidence`、`questionReviews`、`profileChanges`、`recommendations` 和 `applyProfileChanges`。`reviewVersion` 从 1 开始；修订时创建更高版本，不覆盖旧事件。

模拟会话的画像变化默认允许应用。真实会话必须明确询问用户是否确认：未确认时保存 `applyProfileChanges: false`；确认后创建下一不可变版本并设置为 `true`。只有结构化字段进入画像重建，自然语言报告不会改变画像。

## 唯一提交与本地输出

构造完整 `interview.review.completed` JSON 后只调用一次 `submit_event`。响应包含真实回执时记录 `persistenceStatus: "ok"`；写入失败仍生成本地 JSON 并标记 `cloud_persistence_pending`，不得假称远端已保存。事件已保存但画像缓存失败时标记 `profile_cache_pending`。

本地复盘文件统一保存为：

```text
outputs/interview/<userId>/interview-<sessionId>-report.json
outputs/interview/<userId>/interview-<sessionId>-report.docx
```

先用 `save_review_json` 写完整事件副本，再以该 JSON 作为 `create_review_report(report_json, report_docx)` 的唯一输入生成 Word，并执行渲染检查。Word 生成失败不回滚 JSON 或已提交事件；明确说明失败原因并保留可重试文件。
