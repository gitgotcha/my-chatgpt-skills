---
name: reviewing-java-backend-interviews
description: Use when reviewing a mock or real interview for the authenticated device account, through one immutable submit_event handoff with local JSON and Word output.
---

# Java 后端面试复盘

本 Skill 负责设备账户授权、历史会话选择、逐题复盘、结构化画像变化和本地报告生成。所有远端交互只能使用唯一的 `submit_event` MCP 工具；本 Skill 不调用其他远端工具，也不把本地报告作为画像输入。

所有云端数据只写入唯一规范插件根 `DriveRoot/my-chatGPT-skills/`。复盘事件由 Worker 追加到 `users/<userId>/interview/events/`，画像快照由 Worker 物化到 `users/<userId>/interview/profile/snapshots/`；本 Skill 只生成事件内容，不直接写 Drive。

## V2 设备账户授权

每次新对话先取得设备账户状态，不把姓名或聊天记忆当作凭据：

1. 调用 `submit_event` 的 `account.current`；只有 `state:"authenticated"` 与完整 `bindingContext` 有效时，才允许读取会话摘要或详情。
2. `interview.session.list/load` 和复盘写入均携带最近一次上下文；切换只能由用户明确发起。
3. 遇到 `binding_changed`、`reauth_required` 或 `verification_unavailable`，暂停读取与写入并重新查询 current。

账户授权失败或远端状态不是云端接收时暂停后续读取与写入，并如实说明尚未持久化。

## 会话读取与复盘

账户授权成功后依次调用：

1. `submit_event(interview.session.list)`，只展示时间、领域、类型和复盘状态摘要。
2. 用户选择会话后调用 `submit_event(interview.session.load)`，读取目标 schema-1.2 会话及有效复盘事件。
3. 保留原问题、原回答、追问关联、正确性、完整性、错误、遗漏、失分原因、更好的口述回答、参考答案、表达分析和变式复测。

复盘事件必须包含 `sourceSessionEventId`、`sourceType`、`evidenceType`、`evidenceConfidence`、`questionReviews`、`profileChanges`、`recommendations` 和 `applyProfileChanges`。`reviewVersion` 从 1 开始；修订时创建更高版本，不覆盖旧事件。

模拟会话的画像变化默认允许应用。真实会话必须明确询问用户是否确认：未确认时保存 `applyProfileChanges: false`；确认后创建下一不可变版本并设置为 `true`。只有结构化字段进入画像重建，自然语言报告不会改变画像。

## 唯一提交与本地输出

构造完整 `interview.review.completed` JSON 后只调用一次 `submit_event`，并携带当前 `bindingContext`。响应包含云端接收回执时记录对应状态；写入失败仍生成本地 JSON 并标记待处理，不得假称远端已保存。

本地复盘文件统一保存为：

```text
outputs/interview/<userId>/interview-<sessionId>-report.json
outputs/interview/<userId>/interview-<sessionId>-report.docx
```

本地报告只保留为本地派生输出，不上传云端，也永不作为画像输入。先用 `save_review_json` 写完整事件副本，再以该 JSON 作为 `create_review_report(report_json, report_docx)` 的唯一输入生成 Word，并执行渲染检查。Word 生成失败不回滚 JSON 或已提交事件；明确说明失败原因并保留可重试文件。
